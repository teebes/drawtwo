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
    @Published var errorMessage: String?
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
    #if DEBUG
    @State private var didApplyInitialCardPreview = false
    #endif

    init(deckId: Int) {
        _model = StateObject(wrappedValue: DeckDetailViewModel(deckId: deckId))
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

    private func cardListPanel(_ deck: DeckDetail) -> some View {
        VStack(alignment: .leading, spacing: 10) {
            if let error = model.errorMessage {
                DeckNotice(text: error, color: ArchetypeTheme.red)
            }

            ArchetypeWebPanel(padding: 24) {
                if model.isLoading && model.displayItems.isEmpty {
                    DeckProgressRow(text: "Loading cards...")
                } else if model.displayItems.isEmpty {
                    EmptyState(
                        title: "No cards yet.",
                        detail: "Deck changes are managed on drawtwo.com.",
                        systemImage: "rectangle.stack.badge.plus"
                    )
                    .padding(.horizontal, 16)
                } else {
                    VStack(spacing: 8) {
                        ForEach(model.displayItems) { item in
                            DeckCardListRow(
                                item: item,
                                onOpen: { model.selectedCard = item }
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
    let onOpen: () -> Void

    var body: some View {
        Button(action: onOpen) {
            HStack(spacing: 10) {
                Text("\(item.cost)")
                    .font(.archetypeBody(13, weight: .black))
                    .foregroundStyle(Color.white)
                    .frame(width: 32, height: 32)
                    .background(ArchetypeTheme.sky)
                    .clipShape(Circle())

                Text("\(item.count ?? 0)x")
                    .font(.archetypeBody(13, weight: .black))
                    .foregroundStyle(ArchetypeTheme.text)
                    .frame(width: 34)

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
            .padding(.horizontal, 0)
            .padding(.vertical, 0)
            .background(ArchetypeTheme.ink2)
            .clipShape(RoundedRectangle(cornerRadius: 8))
            .contentShape(Rectangle())
            .accessibilityElement(children: .combine)
            .accessibilityLabel(
                "\(item.name), \(item.count ?? 0)x, cost \(item.cost), \(item.isSpell ? "spell" : "\(item.attack) attack, \(item.health) health")"
            )
        }
        .buttonStyle(.plain)
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
