import SwiftUI

struct DeckCardListItem: Identifiable, Equatable {
    let id: Int
    let slug: String
    let name: String
    let description: String?
    let cardType: String
    let cost: Int
    let attack: Int
    let health: Int
    let traits: [JSONValue]
    let faction: String?
    let artUrl: String?
    let heroSlugs: [String]?
    let count: Int?

    init(card: CardTemplate, deckCard: DeckCard?) {
        id = card.id
        slug = card.slug
        name = deckCard?.name ?? card.name
        description = deckCard?.description ?? card.description
        cardType = deckCard?.cardType ?? card.cardType
        cost = deckCard?.cost ?? card.cost
        attack = deckCard?.attack ?? card.attack
        health = deckCard?.health ?? card.health
        traits = deckCard?.traits ?? card.traits
        faction = deckCard?.faction ?? card.faction
        artUrl = deckCard?.artUrl ?? card.artUrl
        heroSlugs = deckCard?.heroSlugs ?? card.heroSlugs
        count = deckCard?.count
    }

    init(deckCard: DeckCard) {
        id = deckCard.id
        slug = deckCard.slug
        name = deckCard.name
        description = deckCard.description
        cardType = deckCard.cardType
        cost = deckCard.cost
        attack = deckCard.attack
        health = deckCard.health
        traits = deckCard.traits
        faction = deckCard.faction
        artUrl = deckCard.artUrl
        heroSlugs = deckCard.heroSlugs
        count = deckCard.count
    }

    var isInDeck: Bool {
        count != nil
    }

    var isSpell: Bool {
        cardType == "spell"
    }

    var isUnique: Bool {
        traitTypes.contains("unique")
    }

    var resolvedArtUrl: String? {
        if let artUrl, !artUrl.isEmpty {
            return artUrl
        }

        return AppConfig.cardArtURL(slug: slug)
    }

    var traitTypes: [String] {
        traits.compactMap { trait in
            trait["type"]?.stringValue ?? trait["slug"]?.stringValue
        }
    }

    var primaryTrait: String? {
        let priority = ["stealth", "taunt", "deathrattle", "battlecry", "ranged", "charge", "unique"]
        return priority.first { traitTypes.contains($0) }
    }
}

@MainActor
final class DeckDetailViewModel: ObservableObject {
    @Published var deck: DeckDetail?
    @Published var isLoading = false
    @Published var isMutating = false
    @Published var isArchiving = false
    @Published var errorMessage: String?
    @Published var statusMessage: String?
    @Published var selectedCard: DeckCardListItem?

    let deckId: Int

    init(deckId: Int) {
        self.deckId = deckId
    }

    var sortedDeckCards: [DeckCard] {
        (deck?.cards ?? []).sorted { first, second in
            if first.cost != second.cost {
                return first.cost < second.cost
            }
            return first.name.localizedCaseInsensitiveCompare(second.name) == .orderedAscending
        }
    }

    var displayItems: [DeckCardListItem] {
        sortedDeckCards.map(DeckCardListItem.init(deckCard:))
    }

    var deckCardMap: [Int: DeckCard] {
        Dictionary(uniqueKeysWithValues: (deck?.cards ?? []).map { ($0.id, $0) })
    }

    func displayItems(includeAvailableCards: Bool) -> [DeckCardListItem] {
        guard includeAvailableCards, let deck else {
            return displayItems
        }

        let map = deckCardMap
        return (deck.allCards ?? [])
            .map { card in
                DeckCardListItem(card: card, deckCard: map[card.id])
            }
            .sorted { first, second in
                if first.cost != second.cost {
                    return first.cost < second.cost
                }
                return first.name.localizedCaseInsensitiveCompare(second.name) == .orderedAscending
            }
    }

    var averageCost: Double {
        guard let deck, deck.totalCards > 0 else {
            return 0
        }

        let total = deck.cards.reduce(0) { result, card in
            result + (card.cost * card.count)
        }
        return Double(total) / Double(deck.totalCards)
    }

    var curveBuckets: [(cost: Int, count: Int, ratio: Double)] {
        guard let deck, !deck.cards.isEmpty else {
            return []
        }

        var counts: [Int: Int] = [:]
        for card in deck.cards {
            let cost = max(0, card.cost)
            counts[cost, default: 0] += card.count
        }

        let maxCost = counts.keys.max() ?? 0
        let maxCount = max(counts.values.max() ?? 1, 1)
        guard maxCost > 0 else {
            return []
        }

        return (1...maxCost).map { cost in
            let count = counts[cost] ?? 0
            return (cost: cost, count: count, ratio: Double(count) / Double(maxCount))
        }
    }

    func load(using authStore: AuthStore) async {
        isLoading = true
        errorMessage = nil

        do {
            let loadedDeck: DeckDetail = try await authStore.authenticatedGet("/collection/decks/\(deckId)/")
            deck = loadedDeck
            prefetchArt(in: loadedDeck)
        } catch {
            errorMessage = error.localizedDescription
        }

        isLoading = false
    }

    func canAddCard(_ item: DeckCardListItem) -> Bool {
        guard let deck else {
            return false
        }

        if item.isInDeck {
            return canIncrementCard(item)
        }

        return deck.totalCards < deck.config.deckSizeLimit
    }

    func canIncrementCard(_ item: DeckCardListItem) -> Bool {
        let currentCount = item.count ?? 0
        return currentCount < maxCount(for: item)
    }

    func maxCount(for item: DeckCardListItem) -> Int {
        guard let deck else {
            return 0
        }

        let currentCount = item.count ?? 0
        let availableDeckSlots = deck.config.deckSizeLimit - (deck.totalCards - currentCount)
        let cardLimit = item.isUnique ? 1 : deck.config.deckCardMaxCount
        return max(0, min(cardLimit, availableDeckSlots))
    }

    func addCard(_ item: DeckCardListItem, using authStore: AuthStore) async {
        guard canAddCard(item) else {
            errorMessage = "Deck cannot have more than \(deck?.config.deckSizeLimit ?? 0) cards."
            return
        }

        await mutate(using: authStore) {
            try await authStore.authenticatedPost(
                "/collection/decks/\(deckId)/cards/add/",
                body: DeckCardAddRequest(cardSlug: item.slug, count: 1)
            )
        }
    }

    func updateCardCount(_ item: DeckCardListItem, count: Int, using authStore: AuthStore) async {
        guard count >= 1 else {
            return
        }

        let maxCount = maxCount(for: item)
        guard count <= maxCount else {
            errorMessage = "This deck can only use \(maxCount) \(copyLabel(maxCount)) of \(item.name)."
            return
        }

        await mutate(using: authStore) {
            try await authStore.authenticatedPut(
                "/collection/decks/\(deckId)/cards/\(item.id)/",
                body: DeckCardCountRequest(count: count)
            )
        }
    }

    func incrementCard(_ item: DeckCardListItem, using authStore: AuthStore) async {
        guard let count = item.count else {
            await addCard(item, using: authStore)
            return
        }

        await updateCardCount(item, count: count + 1, using: authStore)
    }

    func decrementCard(_ item: DeckCardListItem, using authStore: AuthStore) async {
        guard let count = item.count, count > 1 else {
            return
        }

        await updateCardCount(item, count: count - 1, using: authStore)
    }

    func removeCard(_ item: DeckCardListItem, using authStore: AuthStore) async {
        await mutate(using: authStore) {
            try await authStore.authenticatedDelete(
                "/collection/decks/\(deckId)/cards/\(item.id)/delete/"
            )
        }
    }

    func archive(using authStore: AuthStore) async -> Bool {
        guard !isArchiving else {
            return false
        }

        isArchiving = true
        errorMessage = nil
        statusMessage = nil

        do {
            let response: DeckArchiveResponse = try await authStore.authenticatedDelete(
                "/collection/decks/\(deckId)/"
            )
            statusMessage = response.message
            isArchiving = false
            return true
        } catch {
            errorMessage = error.localizedDescription
            isArchiving = false
            return false
        }
    }

    private func mutate(
        using authStore: AuthStore,
        operation: () async throws -> DeckCardMutationResponse
    ) async {
        guard !isMutating else {
            return
        }

        isMutating = true
        errorMessage = nil
        statusMessage = nil

        do {
            let response = try await operation()
            await load(using: authStore)
            statusMessage = response.message
        } catch {
            errorMessage = error.localizedDescription
        }

        isMutating = false
    }

    private func copyLabel(_ count: Int) -> String {
        count == 1 ? "copy" : "copies"
    }

    private func prefetchArt(in deck: DeckDetail) {
        let urlStrings =
            [deck.hero.resolvedArtUrl]
            + deck.cards.map { $0.resolvedArtUrl }
            + (deck.allCards?.map { $0.resolvedArtUrl } ?? [])
        let urls = urlStrings.compactMap { $0 }.compactMap(URL.init(string:))

        RemoteImageCache.shared.prefetch(urls)
    }

}

struct DeckDetailView: View {
    @EnvironmentObject private var authStore: AuthStore
    @StateObject private var model: DeckDetailViewModel
    @State private var isEditingCards = false
    @State private var isConfirmingArchive = false
    @State private var pendingRemoval: DeckCardListItem?
    #if DEBUG
    @State private var didApplyInitialCardPreview = false
    #endif

    let editDeck: (Int) -> Void
    let onArchived: () -> Void

    init(
        deckId: Int,
        editDeck: @escaping (Int) -> Void = { _ in },
        onArchived: @escaping () -> Void = {}
    ) {
        _model = StateObject(wrappedValue: DeckDetailViewModel(deckId: deckId))
        self.editDeck = editDeck
        self.onArchived = onArchived
    }

    var body: some View {
        ArchetypeScreen {
            ZStack {
                ScrollView {
                    VStack(spacing: 0) {
                        topBar
                            .padding(.horizontal, 18)
                            .padding(.top, 6)
                            .padding(.bottom, 16)

                        if let deck = model.deck {
                            deckHeroBanner(deck)

                            VStack(spacing: 20) {
                                deckStatsPanel(deck)
                                deckActionsPanel(deck)
                                cardListPanel(deck)
                            }
                            .padding(.horizontal, 18)
                            .padding(.top, 32)
                            .padding(.bottom, 34)
                        } else if model.isLoading {
                            VStack {
                                ArchetypeWebPanel {
                                    DeckProgressRow(text: "Loading deck...")
                                }
                            }
                            .padding(18)
                        } else if let error = model.errorMessage {
                            VStack {
                                ArchetypeWebPanel {
                                    ErrorBlock(error: error) {
                                        Task { await model.load(using: authStore) }
                                    }
                                }
                            }
                            .padding(18)
                        }
                    }
                }
                .refreshable {
                    await model.load(using: authStore)
                }

                if let selectedCard = model.selectedCard {
                    DeckCardDetailOverlay(card: selectedCard) {
                        model.selectedCard = nil
                    }
                    .zIndex(2)
                    .transition(.opacity)
                }
            }
        }
        .toolbar(.hidden, for: .navigationBar)
        .navigationBarBackButtonHidden(true)
        .task {
            await model.load(using: authStore)
            applyInitialCardPreviewIfNeeded()
            recordCaptureState()
        }
        .onChange(of: model.selectedCard?.id) { _, _ in
            recordCaptureState()
        }
        .confirmationDialog(
            "Remove card?",
            isPresented: Binding(
                get: { pendingRemoval != nil },
                set: { isPresented in
                    if !isPresented {
                        pendingRemoval = nil
                    }
                }
            ),
            presenting: pendingRemoval
        ) { item in
            Button("Remove \(item.name)", role: .destructive) {
                Task {
                    await model.removeCard(item, using: authStore)
                    pendingRemoval = nil
                }
            }

            Button("Cancel", role: .cancel) {
                pendingRemoval = nil
            }
        } message: { item in
            Text("Remove \(item.name) from \(model.deck?.name ?? "this deck")?")
        }
        .confirmationDialog(
            "Archive deck?",
            isPresented: $isConfirmingArchive
        ) {
            Button("Archive Deck", role: .destructive) {
                Task {
                    if await model.archive(using: authStore) {
                        onArchived()
                    }
                }
            }

            Button("Cancel", role: .cancel) {}
        } message: {
            Text("The deck will be removed from deck lists and game setup, while past games keep their history.")
        }
    }

    private func recordCaptureState() {
        CaptureStateRecorder.record(model.selectedCard == nil ? "deck" : "deck-card-detail")
    }

    private func applyInitialCardPreviewIfNeeded() {
        #if DEBUG
        guard !didApplyInitialCardPreview else {
            return
        }
        didApplyInitialCardPreview = true

        guard let slug = AppConfig.initialDeckCardSlug else {
            return
        }

        let card: DeckCardListItem?
        if slug == "first" {
            card = model.displayItems.first
        } else {
            card = model.displayItems.first { $0.slug.lowercased() == slug }
        }

        guard let card else {
            return
        }

        DispatchQueue.main.asyncAfter(deadline: .now() + 0.35) {
            model.selectedCard = card
        }
        #endif
    }

    private var topBar: some View {
        ArchetypeTopBar {
            ArchetypeProfileLink(user: authStore.user) {
                ProfileView()
            }
        }
    }

    private func deckHeroBanner(_ deck: DeckDetail) -> some View {
        HStack(spacing: 16) {
            heroArt(deck.hero)
                .frame(width: 64, height: 88)
                .clipShape(RoundedRectangle(cornerRadius: 8))
                .overlay(
                    RoundedRectangle(cornerRadius: 8)
                        .stroke(Color.black.opacity(0.65), lineWidth: 2)
                )

            Text(deck.name)
                .font(.archetypeTitle(32))
                .foregroundStyle(Color(hex: 0x111827))
                .lineLimit(2)
                .minimumScaleFactor(0.72)
        }
        .padding(.horizontal, 18)
        .frame(maxWidth: .infinity, minHeight: 96)
        .background(Color(hex: 0xD1D5DB))
    }

    private func deckStatsPanel(_ deck: DeckDetail) -> some View {
        ArchetypeWebPanel {
            VStack(spacing: 18) {
                HStack(spacing: 12) {
                    DeckMetric(value: "\(deck.totalCards)/\(deck.config.deckSizeLimit)", label: "Total Cards")
                    DeckMetric(value: "\(deck.cards.count)", label: "Unique Cards")
                    DeckMetric(value: "\(deck.hero.health)", label: "Hero Health")
                    DeckMetric(value: String(format: "%.1f", model.averageCost), label: "Avg. Cost")
                }

                if !model.curveBuckets.isEmpty {
                    Divider()
                        .overlay(ArchetypeTheme.border)

                    VStack(spacing: 12) {
                        Text("Cards by energy cost".uppercased())
                            .font(.archetypeBody(11, weight: .bold))
                            .foregroundStyle(ArchetypeTheme.muted)
                            .frame(maxWidth: .infinity)

                        HStack(alignment: .bottom, spacing: 8) {
                            ForEach(model.curveBuckets, id: \.cost) { bucket in
                                VStack(spacing: 5) {
                                    Text("\(bucket.count)")
                                        .font(.archetypeBody(10, weight: .bold))
                                        .foregroundStyle(ArchetypeTheme.muted)
                                    RoundedRectangle(cornerRadius: 4)
                                        .fill(bucket.count == 0 ? ArchetypeTheme.sky.opacity(0.22) : ArchetypeTheme.sky)
                                        .frame(width: 20, height: max(8, CGFloat(bucket.ratio) * 44))
                                    Text("\(bucket.cost)")
                                        .font(.archetypeBody(10, weight: .bold))
                                        .foregroundStyle(Color(hex: 0xD1D5DB))
                                }
                            }
                        }
                        .frame(maxWidth: .infinity)
                    }
                }
            }
        }
    }

    private func deckActionsPanel(_ deck: DeckDetail) -> some View {
        ArchetypeWebPanel(padding: 16) {
            VStack(spacing: 10) {
                HStack(spacing: 10) {
                    Button {
                        isConfirmingArchive = true
                    } label: {
                        Label(model.isArchiving ? "Archiving..." : "Archive Deck", systemImage: "archivebox")
                            .frame(maxWidth: .infinity)
                    }
                    .buttonStyle(FilledGameButtonStyle(color: ArchetypeTheme.red))
                    .disabled(model.isArchiving || model.isMutating)
                    .opacity(model.isArchiving ? 0.65 : 1)

                    Button {
                        editDeck(deck.id)
                    } label: {
                        Label("Edit Deck", systemImage: "pencil")
                            .frame(maxWidth: .infinity)
                    }
                    .buttonStyle(SecondaryGameButtonStyle())
                    .disabled(model.isArchiving || model.isMutating)
                }

                if isEditingCards {
                    Button {
                        withAnimation(.snappy) {
                            isEditingCards = false
                        }
                    } label: {
                        Label("Done", systemImage: "checkmark")
                            .frame(maxWidth: .infinity)
                    }
                    .buttonStyle(SecondaryGameButtonStyle())
                    .disabled(model.isArchiving)
                } else {
                    Button {
                        withAnimation(.snappy) {
                            isEditingCards = true
                        }
                    } label: {
                        Label("Edit Cards", systemImage: "rectangle.stack.badge.plus")
                            .frame(maxWidth: .infinity)
                    }
                    .buttonStyle(PrimaryGameButtonStyle())
                    .disabled(model.isArchiving)
                }
            }
        }
    }

    private func cardListPanel(_ deck: DeckDetail) -> some View {
        let items = model.displayItems(includeAvailableCards: isEditingCards)

        return VStack(alignment: .leading, spacing: 10) {
            if let error = model.errorMessage {
                DeckNotice(text: error, color: ArchetypeTheme.red)
            }

            if let status = model.statusMessage {
                DeckNotice(text: status, color: ArchetypeTheme.green)
            }

            ArchetypeWebPanel(padding: 24) {
                if model.isLoading && items.isEmpty {
                    DeckProgressRow(text: "Loading cards...")
                } else if items.isEmpty {
                    EmptyState(
                        title: "No cards yet.",
                        detail: isEditingCards ? "No collectible cards are available for this hero." : "Use Edit Cards to add cards to this deck.",
                        systemImage: "rectangle.stack.badge.plus"
                    )
                    .padding(.horizontal, 16)
                } else {
                    VStack(spacing: 8) {
                        ForEach(items) { item in
                            DeckCardListRow(
                                item: item,
                                isEditing: isEditingCards,
                                canAdd: model.canAddCard(item),
                                canIncrement: model.canIncrementCard(item),
                                isMutating: model.isMutating,
                                onOpen: { model.selectedCard = item },
                                onAdd: {
                                    Task {
                                        await model.addCard(item, using: authStore)
                                    }
                                },
                                onIncrement: {
                                    Task {
                                        await model.incrementCard(item, using: authStore)
                                    }
                                },
                                onDecrement: {
                                    if (item.count ?? 0) <= 1 {
                                        pendingRemoval = item
                                    } else {
                                        Task {
                                            await model.decrementCard(item, using: authStore)
                                        }
                                    }
                                },
                                onRemove: {
                                    pendingRemoval = item
                                }
                            )
                        }
                    }
                }
            }
        }
    }

    @ViewBuilder
    private func heroArt(_ hero: DeckDetailHero) -> some View {
        if let artUrl = hero.resolvedArtUrl, let url = URL(string: artUrl) {
            CachedRemoteImage(url: url) { image in
                image
                    .resizable()
                    .scaledToFill()
            } placeholder: {
                heroFallback(hero)
            }
        } else {
            heroFallback(hero)
        }
    }

    private func heroFallback(_ hero: DeckDetailHero) -> some View {
        ZStack {
            Color(hex: 0x9CA3AF)
            Text(hero.name.prefix(1).uppercased())
                .font(.archetypeBody(22, weight: .black))
                .foregroundStyle(Color.white)
        }
    }
}

private struct DeckMetric: View {
    let value: String
    let label: String

    var body: some View {
        VStack(spacing: 5) {
            Text(value)
                .font(.archetypeBody(18, weight: .black))
                .foregroundStyle(ArchetypeTheme.text)
                .lineLimit(1)
                .minimumScaleFactor(0.7)
            Text(label)
                .font(.archetypeBody(9, weight: .bold))
                .foregroundStyle(ArchetypeTheme.muted)
                .multilineTextAlignment(.center)
                .lineLimit(2)
        }
        .frame(maxWidth: .infinity)
    }
}

private struct DeckCardListRow: View {
    let item: DeckCardListItem
    let isEditing: Bool
    let canAdd: Bool
    let canIncrement: Bool
    let isMutating: Bool
    let onOpen: () -> Void
    let onAdd: () -> Void
    let onIncrement: () -> Void
    let onDecrement: () -> Void
    let onRemove: () -> Void

    var body: some View {
        HStack(spacing: 10) {
            Button(action: onOpen) {
                HStack(spacing: 10) {
                    Text("\(item.cost)")
                        .font(.archetypeBody(13, weight: .black))
                        .foregroundStyle(Color.white)
                        .frame(width: 32, height: 32)
                        .background(ArchetypeTheme.sky)
                        .clipShape(Circle())

                    HStack(spacing: 12) {
                        Text(item.name)
                            .font(.archetypeBody(15, weight: .semibold))
                            .foregroundStyle(ArchetypeTheme.text)
                            .lineLimit(1)
                            .layoutPriority(1)

                        if let heroSlugs = item.heroSlugs, !heroSlugs.isEmpty {
                            Text(heroSlugs.joined(separator: ", "))
                                .font(.archetypeBody(9, weight: .bold))
                                .foregroundStyle(ArchetypeTheme.sky)
                                .lineLimit(1)
                                .padding(.horizontal, 6)
                                .padding(.vertical, 3)
                                .background(ArchetypeTheme.sky.opacity(0.16))
                                .clipShape(Capsule())
                        }

                        Text(item.isSpell ? "Spell" : "\(item.attack)/\(item.health)")
                            .font(.archetypeBody(12, weight: .medium))
                            .foregroundStyle(ArchetypeTheme.muted)
                            .lineLimit(1)
                    }
                    .padding(.leading, 8)
                    .frame(maxWidth: .infinity, alignment: .leading)
                }
            }
            .buttonStyle(.plain)
            .frame(maxWidth: .infinity, alignment: .leading)

            if isEditing {
                editControls
            } else {
                Text("\(item.count ?? 0)x")
                    .font(.archetypeBody(13, weight: .black))
                    .foregroundStyle(ArchetypeTheme.text)
                    .frame(width: 34)
            }
        }
        .padding(.horizontal, 0)
        .padding(.vertical, 0)
        .background(ArchetypeTheme.ink2)
        .clipShape(RoundedRectangle(cornerRadius: 8))
        .contentShape(Rectangle())
        .accessibilityElement(children: isEditing ? .contain : .combine)
        .accessibilityLabel(accessibilityLabel)
    }

    @ViewBuilder
    private var editControls: some View {
        if item.isInDeck {
            HStack(spacing: 4) {
                Button(action: onDecrement) {
                    Image(systemName: "minus")
                }
                .buttonStyle(DeckIconControlStyle(tint: ArchetypeTheme.muted))
                .disabled(isMutating)

                Text("\(item.count ?? 0)x")
                    .font(.archetypeBody(13, weight: .black))
                    .foregroundStyle(ArchetypeTheme.text)
                    .frame(width: 34)

                Button(action: onIncrement) {
                    Image(systemName: "plus")
                }
                .buttonStyle(DeckIconControlStyle(tint: ArchetypeTheme.sky))
                .disabled(isMutating || !canIncrement)
                .opacity(canIncrement ? 1 : 0.38)

                Button(action: onRemove) {
                    Image(systemName: "trash")
                }
                .buttonStyle(DeckIconControlStyle(tint: ArchetypeTheme.red))
                .disabled(isMutating)
            }
            .padding(.trailing, 6)
        } else {
            Button(action: onAdd) {
                Label("Add", systemImage: "plus")
                    .labelStyle(.iconOnly)
            }
            .buttonStyle(DeckIconControlStyle(tint: ArchetypeTheme.gold2))
            .disabled(isMutating || !canAdd)
            .opacity(canAdd ? 1 : 0.38)
            .padding(.trailing, 6)
            .accessibilityLabel("Add \(item.name)")
        }
    }

    private var accessibilityLabel: String {
        let count = item.count.map { "\($0)x, " } ?? ""
        let stats = item.isSpell ? "spell" : "\(item.attack) attack, \(item.health) health"
        return "\(item.name), \(count)cost \(item.cost), \(stats)"
    }
}

private struct DeckIconControlStyle: ButtonStyle {
    let tint: Color

    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .font(.system(size: 13, weight: .bold))
            .foregroundStyle(tint)
            .frame(width: 30, height: 30)
            .background(configuration.isPressed ? ArchetypeTheme.pressedSurface : ArchetypeTheme.panel)
            .overlay(
                RoundedRectangle(cornerRadius: 7)
                    .stroke(ArchetypeTheme.border, lineWidth: 1)
            )
            .clipShape(RoundedRectangle(cornerRadius: 7))
            .scaleEffect(configuration.isPressed ? 0.96 : 1)
    }
}

private struct DeckProgressRow: View {
    let text: String

    var body: some View {
        HStack(spacing: 10) {
            ProgressView()
                .tint(ArchetypeTheme.gold2)
            Text(text)
                .font(.archetypeBody(13))
                .foregroundStyle(ArchetypeTheme.muted)
        }
        .frame(maxWidth: .infinity)
        .padding(.vertical, 28)
        .padding(.horizontal, 16)
    }
}

private struct ErrorBlock: View {
    let error: String
    let retry: () -> Void

    var body: some View {
        VStack(spacing: 12) {
            Text(error)
                .font(.archetypeBody(12))
                .foregroundStyle(ArchetypeTheme.red)
                .frame(maxWidth: .infinity, alignment: .leading)
            Button(action: retry) {
                Text("Try Again")
                    .frame(maxWidth: .infinity)
            }
            .buttonStyle(PrimaryGameButtonStyle())
        }
    }
}

private struct DeckNotice: View {
    let text: String
    let color: Color

    var body: some View {
        Text(text)
            .font(.archetypeBody(12))
            .foregroundStyle(color)
            .padding(11)
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(color.opacity(0.11))
            .clipShape(RoundedRectangle(cornerRadius: ArchetypeTheme.controlRadius))
    }
}

private struct DeckCardDetailOverlay: View {
    let card: DeckCardListItem
    let onClose: () -> Void

    var body: some View {
        ZStack(alignment: .top) {
            Color.black.opacity(0.62)
                .ignoresSafeArea()
                .onTapGesture(perform: onClose)

            ScrollView(showsIndicators: false) {
                modalPanel
                    .frame(maxWidth: 312)
                    .padding(.horizontal, 40)
                    .padding(.top, 78)
                    .padding(.bottom, 42)
            }
        }
        .accessibilityAddTraits(.isModal)
    }

    private var modalPanel: some View {
        ZStack(alignment: .topTrailing) {
            VStack(spacing: 0) {
                Text(card.name.uppercased())
                    .font(.archetypeDisplay(31, weight: .bold))
                    .foregroundStyle(ArchetypeTheme.text)
                    .lineLimit(1)
                    .minimumScaleFactor(0.72)
                    .frame(maxWidth: .infinity)
                    .frame(height: 94)
                    .background(ArchetypeTheme.panel)

                VStack(alignment: .leading, spacing: 32) {
                    Text(cardTypeLine)
                        .font(.archetypeBody(15, weight: .medium))
                        .foregroundStyle(ArchetypeTheme.muted)
                        .fixedSize(horizontal: false, vertical: true)

                    DeckCardDetailStatGrid(card: card)

                    if let description = card.description, !description.isEmpty {
                        Text(description)
                            .font(.archetypeBody(17))
                            .foregroundStyle(ArchetypeTheme.text)
                            .fixedSize(horizontal: false, vertical: true)
                            .padding(16)
                            .frame(maxWidth: .infinity, alignment: .leading)
                            .background(ArchetypeTheme.panel)
                            .overlay(
                                RoundedRectangle(cornerRadius: 8)
                                    .stroke(ArchetypeTheme.border, lineWidth: 1)
                            )
                            .clipShape(RoundedRectangle(cornerRadius: 8))
                    }

                    deckCardPreview
                        .frame(width: 180)
                        .frame(maxWidth: .infinity)
                }
                .padding(.horizontal, 16)
                .padding(.top, 18)
                .padding(.bottom, 22)
            }
            .background(ArchetypeTheme.panel2)
            .clipShape(RoundedRectangle(cornerRadius: 4))
            .shadow(color: Color.black.opacity(0.34), radius: 22, x: 0, y: 14)

            Button(action: onClose) {
                Image(systemName: "xmark")
                    .font(.system(size: 18, weight: .semibold))
                    .foregroundStyle(ArchetypeTheme.muted)
                    .frame(width: 34, height: 34)
                    .background(Color(hex: 0x111827))
                    .clipShape(Circle())
            }
            .buttonStyle(.plain)
            .offset(x: 14, y: -14)
            .accessibilityLabel("Close card details")
        }
    }

    private var deckCardPreview: some View {
        ZStack {
            RoundedRectangle(cornerRadius: 12)
                .fill(Color(hex: 0xD1D5DB))

            deckCardArt
                .frame(maxWidth: .infinity, maxHeight: .infinity)
                .clipShape(RoundedRectangle(cornerRadius: 12))
        }
        .aspectRatio(5 / 7, contentMode: .fit)
        .overlay(
            RoundedRectangle(cornerRadius: 12)
                .stroke(Color(hex: 0x111827), lineWidth: 2)
        )
        .overlay(alignment: .topLeading) {
            if let traitGlyph {
                DeckPreviewCardBadge(text: traitGlyph, color: Color.white, textColor: Color(hex: 0x111827))
                    .offset(x: -12, y: -12)
            }
        }
        .overlay(alignment: .topTrailing) {
            DeckPreviewCardBadge(text: "\(card.cost)", color: ArchetypeTheme.sky)
                .offset(x: 12, y: -12)
        }
        .overlay(alignment: .bottomLeading) {
            if !card.isSpell {
                DeckPreviewCardBadge(text: "\(card.attack)", color: ArchetypeTheme.red)
                    .offset(x: -12, y: 12)
            }
        }
        .overlay(alignment: .bottomTrailing) {
            if !card.isSpell {
                DeckPreviewCardBadge(text: "\(card.health)", color: ArchetypeTheme.green)
                    .offset(x: 12, y: 12)
            }
        }
    }

    private var traitGlyph: String? {
        switch card.primaryTrait {
        case "stealth":
            return "👁️"
        case "taunt":
            return "🛡️"
        case "deathrattle":
            return "💀"
        case "battlecry":
            return "📣"
        case "ranged":
            return "🏹"
        case "charge":
            return "⚔️"
        case "unique":
            return "⭐"
        default:
            return nil
        }
    }

    private var cardTypeLine: String {
        var parts = [card.cardType.capitalized]
        if !card.traitTypes.isEmpty {
            parts.append("[ \(card.traitTypes.map { $0.uppercased() }.joined(separator: ", ")) ]")
        }
        return parts.joined(separator: " ")
    }

    @ViewBuilder
    private var deckCardArt: some View {
        GeometryReader { proxy in
            Group {
                if let artUrl = card.resolvedArtUrl, let url = URL(string: artUrl) {
                    CachedRemoteImage(url: url) { image in
                        image
                            .resizable()
                            .scaledToFill()
                    } placeholder: {
                        placeholder
                    }
                } else {
                    placeholder
                }
            }
            .frame(width: proxy.size.width, height: proxy.size.height)
            .clipped()
        }
    }

    private var placeholder: some View {
        RemoteImagePlaceholder()
    }

}

private struct DeckCardDetailStatGrid: View {
    let card: DeckCardListItem

    var body: some View {
        VStack(alignment: .leading, spacing: 5) {
            statRow(label: "Cost", value: "\(card.cost)", color: ArchetypeTheme.sky)

            if !card.isSpell {
                statRow(label: "Attack", value: "\(card.attack)", color: ArchetypeTheme.red)
                statRow(label: "Health", value: "\(card.health)", color: ArchetypeTheme.green)
            }
        }
        .frame(width: 116, alignment: .leading)
    }

    private func statRow(label: String, value: String, color: Color) -> some View {
        HStack {
            Text(label)
                .font(.archetypeBody(17, weight: .bold))
            Spacer(minLength: 12)
            Text(value)
                .font(.archetypeBody(17, weight: .bold))
        }
        .foregroundStyle(color)
    }
}

private struct DeckPreviewCardBadge: View {
    let text: String
    let color: Color
    var textColor: Color = .white

    var body: some View {
        Text(text)
            .font(.archetypeBody(14, weight: .black))
            .foregroundStyle(textColor)
            .frame(width: 32, height: 32)
            .background(color)
            .clipShape(Circle())
            .overlay(Circle().stroke(Color(hex: 0x111827), lineWidth: 1))
            .shadow(color: Color.black.opacity(0.26), radius: 5, x: 0, y: 2)
    }
}
