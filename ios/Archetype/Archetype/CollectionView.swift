import SwiftUI

@MainActor
final class CollectionViewModel: ObservableObject {
    @Published var title: Title?
    @Published var decks: [Deck] = []
    @Published var cards: [CardTemplate] = []
    @Published var typeFilter: CardTypeFilter = .all
    @Published var isLoading = false
    @Published var errorMessage: String?
    @Published var selectedCard: CardTemplate?

    var filteredCards: [CardTemplate] {
        cards.filter { card in
            switch typeFilter {
            case .all:
                return true
            case .creature:
                return card.cardType == "creature"
            case .spell:
                return card.cardType == "spell"
            }
        }
    }

    var commonCards: [CardTemplate] {
        filteredCards
            .filter { $0.isCollectibleCard && ($0.faction == nil || $0.faction?.isEmpty == true) }
    }

    var factionCardGroups: [(name: String, cards: [CardTemplate])] {
        groupedCards(
            from: filteredCards.filter { $0.isCollectibleCard && !($0.faction ?? "").isEmpty }
        )
    }

    var uncollectibleCards: [CardTemplate] {
        filteredCards.filter { !$0.isCollectibleCard }
    }

    var uncollectibleCommonCards: [CardTemplate] {
        uncollectibleCards.filter { $0.faction == nil || $0.faction?.isEmpty == true }
    }

    var uncollectibleFactionCardGroups: [(name: String, cards: [CardTemplate])] {
        groupedCards(
            from: uncollectibleCards.filter { !($0.faction ?? "").isEmpty }
        )
    }

    var webComparableFirstCard: CardTemplate? {
        cards
            .filter(\.isCollectibleCard)
            .sorted { first, second in
                if first.cost != second.cost {
                    return first.cost < second.cost
                }
                return first.name.localizedCaseInsensitiveCompare(second.name) == .orderedAscending
            }
            .first
    }

    func load(using authStore: AuthStore) async {
        isLoading = true
        errorMessage = nil

        do {
            async let titleRequest: Title = authStore.authenticatedGet("/titles/\(AppConfig.titleSlug)/")
            async let deckRequest: DeckListResponse = authStore.authenticatedGet("/collection/titles/\(AppConfig.titleSlug)/decks/")
            async let cardRequest: [CardTemplate] = authStore.authenticatedGet("/titles/\(AppConfig.titleSlug)/cards/")

            let (title, deckResponse, cards) = try await (titleRequest, deckRequest, cardRequest)
            self.title = title
            self.decks = deckResponse.decks
            self.cards = cards
            prefetchArt(title: title, decks: deckResponse.decks, cards: cards)
        } catch {
            errorMessage = error.localizedDescription
        }

        isLoading = false
    }

    private func prefetchArt(title: Title, decks: [Deck], cards: [CardTemplate]) {
        let urlStrings =
            [title.resolvedArtUrl]
            + decks.map { $0.hero.resolvedArtUrl }
            + cards.map { $0.resolvedArtUrl }
        let urls = urlStrings.compactMap { $0 }.compactMap(URL.init(string:))

        RemoteImageCache.shared.prefetch(urls)
    }

    private func groupedCards(from cards: [CardTemplate]) -> [(name: String, cards: [CardTemplate])] {
        let grouped = Dictionary(grouping: cards) { card in
            card.faction ?? "Common"
        }

        return grouped
            .map { (name: $0.key, cards: $0.value) }
            .sorted { $0.name.localizedCaseInsensitiveCompare($1.name) == .orderedAscending }
    }
}

struct CollectionView: View {
    @EnvironmentObject private var authStore: AuthStore
    @StateObject private var model = CollectionViewModel()
    @State private var hasLoaded = false
    #if DEBUG
    @State private var didApplyInitialCardPreview = false
    #endif

    let openDeck: (Int) -> Void
    let createDeck: () -> Void

    init(
        openDeck: @escaping (Int) -> Void = { _ in },
        createDeck: @escaping () -> Void = {}
    ) {
        self.openDeck = openDeck
        self.createDeck = createDeck
    }

    private let cardColumns = [
        GridItem(.adaptive(minimum: 148, maximum: 220), spacing: 32),
    ]

    var body: some View {
        ArchetypeScreen {
            ScrollView {
                VStack(spacing: 0) {
                    topBar
                        .padding(.horizontal, 16)
                        .padding(.top, 6)
                        .padding(.bottom, 16)

                    ArchetypePageBanner(title: "Collection")

                    VStack(spacing: 48) {
                        decksPanel
                        if shouldShowCardFilters {
                            cardFilters
                        }
                        cardsContent
                            .padding(.top, shouldShowCardFilters ? 16 : 0)
                    }
                    .padding(.horizontal, 16)
                    .padding(.top, 32)
                    .padding(.bottom, 40)
                }
            }
            .refreshable {
                await model.load(using: authStore)
            }
        }
        .toolbar(.hidden, for: .navigationBar)
        .navigationBarBackButtonHidden(true)
        .fullScreenCover(item: $model.selectedCard) { card in
            CardPreviewScreen(card: card) {
                model.selectedCard = nil
            }
        }
        .task {
            await loadInitialData()
        }
        .onChange(of: model.selectedCard?.id) { _, _ in
            recordCaptureState()
        }
        .onAppear {
            guard hasLoaded else {
                return
            }

            Task {
                await model.load(using: authStore)
                recordCaptureState()
            }
        }
    }

    private func recordCaptureState() {
        CaptureStateRecorder.record(model.selectedCard == nil ? "collection" : "collection-card-detail")
    }

    private var shouldShowCardFilters: Bool {
        !model.isLoading && model.errorMessage == nil && !model.cards.isEmpty
    }

    private var topBar: some View {
        ArchetypeTopBar {
            ArchetypeProfileLink(user: authStore.user) {
                ProfileView()
            }
        }
    }

    private func applyInitialCardPreviewIfNeeded() {
        #if DEBUG
        guard !didApplyInitialCardPreview else {
            return
        }
        didApplyInitialCardPreview = true

        guard let slug = AppConfig.initialCollectionCardSlug else {
            return
        }

        let card: CardTemplate?
        if slug == "first" {
            card = model.webComparableFirstCard
        } else {
            card = model.cards.first { $0.slug.lowercased() == slug }
        }

        guard let card else {
            return
        }

        DispatchQueue.main.asyncAfter(deadline: .now() + 0.35) {
            model.selectedCard = card
        }
        #endif
    }

    private func loadInitialData() async {
        guard !hasLoaded else {
            return
        }

        hasLoaded = true
        await model.load(using: authStore)
        applyInitialCardPreviewIfNeeded()
        recordCaptureState()
    }

    private var decksPanel: some View {
        ArchetypeWebPanel(padding: 24) {
            VStack(alignment: .leading, spacing: 16) {
                HStack(spacing: 12) {
                    Text("Your Decks")
                        .font(.archetypeBody(18, weight: .semibold))
                        .foregroundStyle(ArchetypeTheme.text)

                    Spacer()

                    Button(action: createDeck) {
                        Label("New Deck", systemImage: "plus")
                            .labelStyle(.titleAndIcon)
                    }
                    .buttonStyle(SecondaryGameButtonStyle())
                    .accessibilityLabel("Create new deck")
                }

                if model.isLoading && model.decks.isEmpty {
                    CollectionProgressRow(text: "Loading decks...")
                } else if model.decks.isEmpty {
                    VStack(spacing: 16) {
                        EmptyState(
                            title: "No decks found.",
                            detail: "Create a deck to start building your collection.",
                            systemImage: "rectangle.stack.badge.plus"
                        )
                        .padding(.horizontal, 16)

                        Button(action: createDeck) {
                            Label("Create Your First Deck", systemImage: "plus")
                                .frame(maxWidth: .infinity)
                        }
                        .buttonStyle(PrimaryGameButtonStyle())
                    }
                } else {
                    VStack(spacing: 0) {
                        ForEach(Array(model.decks.enumerated()), id: \.element.id) { index, deck in
                            Button {
                                openDeck(deck.id)
                            } label: {
                                CollectionDeckRow(deck: deck)
                            }
                            .buttonStyle(.plain)

                            if index < model.decks.count - 1 {
                                Spacer()
                                    .frame(height: 10)
                            }
                        }

                        Button(action: createDeck) {
                            Label("New Deck", systemImage: "plus")
                                .frame(maxWidth: .infinity)
                        }
                        .buttonStyle(DashedActionButtonStyle())
                        .padding(.top, 12)
                    }
                }
            }
        }
    }

    private var cardFilters: some View {
        HStack(alignment: .center, spacing: 8) {
            Text("Type:")
                .font(.archetypeBody(14, weight: .medium))
                .foregroundStyle(ArchetypeTheme.text)

            HStack(spacing: 0) {
                ForEach(CardTypeFilter.allCases) { filter in
                    Button {
                        model.typeFilter = filter
                    } label: {
                        Text(filter.label)
                            .font(.archetypeBody(14, weight: .medium))
                            .foregroundStyle(model.typeFilter == filter ? Color.white : Color(hex: 0xD1D5DB))
                            .padding(.horizontal, 12)
                            .padding(.vertical, 6)
                            .background(model.typeFilter == filter ? ArchetypeTheme.sky : Color.clear)
                    }
                    .buttonStyle(.plain)

                    if filter != CardTypeFilter.allCases.last! {
                        Divider()
                            .overlay(ArchetypeTheme.border)
                    }
                }
            }
            .background(ArchetypeTheme.panel)
            .overlay(
                RoundedRectangle(cornerRadius: ArchetypeTheme.controlRadius)
                    .stroke(ArchetypeTheme.border, lineWidth: 1)
            )
            .clipShape(RoundedRectangle(cornerRadius: ArchetypeTheme.controlRadius))

            Spacer(minLength: 0)
        }
        .padding(.vertical, 16)
    }

    @ViewBuilder
    private var cardsContent: some View {
        if let error = model.errorMessage {
            Text(error)
                .font(.archetypeBody(12))
                .foregroundStyle(ArchetypeTheme.red)
                .padding(11)
                .frame(maxWidth: .infinity, alignment: .leading)
                .background(ArchetypeTheme.red.opacity(0.11))
                .clipShape(RoundedRectangle(cornerRadius: ArchetypeTheme.controlRadius))
        } else if model.isLoading && model.cards.isEmpty {
            CollectionProgressRow(text: "Loading cards...")
        } else if model.filteredCards.isEmpty {
            ArchetypeWebPanel {
                EmptyState(
                    title: "No cards found.",
                    detail: model.cards.isEmpty ? "No cards found for this title." : "Try a different card type filter.",
                    systemImage: "rectangle.stack"
                )
            }
        } else {
            VStack(spacing: 30) {
                CardGridSection(
                    title: "Common Cards",
                    cards: model.commonCards,
                    columns: cardColumns,
                    isDimmed: false,
                    showsDetails: true,
                    onSelect: { model.selectedCard = $0 }
                )

                ForEach(model.factionCardGroups, id: \.name) { group in
                    CardGridSection(
                        title: "\(group.name.capitalized) Cards",
                        cards: group.cards,
                        columns: cardColumns,
                        isDimmed: false,
                        showsDetails: false,
                        onSelect: { model.selectedCard = $0 }
                    )
                }

                if !model.uncollectibleCards.isEmpty {
                    VStack(spacing: 24) {
                        ArchetypeWebSectionTitle(
                            title: "Uncollectible Cards",
                            accessory: "\(model.uncollectibleCards.count)"
                        )

                        CardGridSection(
                            title: "Common",
                            cards: model.uncollectibleCommonCards,
                            columns: cardColumns,
                            isDimmed: true,
                            showsDetails: true,
                            onSelect: { model.selectedCard = $0 }
                        )

                        ForEach(model.uncollectibleFactionCardGroups, id: \.name) { group in
                            CardGridSection(
                                title: group.name.capitalized,
                                cards: group.cards,
                                columns: cardColumns,
                                isDimmed: true,
                                showsDetails: false,
                                onSelect: { model.selectedCard = $0 }
                            )
                        }
                    }
                    .padding(.top, 18)
                }
            }
        }
    }

}

@MainActor
final class DeckEditorViewModel: ObservableObject {
    @Published var heroes: [Hero] = []
    @Published var deckName = ""
    @Published var deckDescription = ""
    @Published var selectedHeroId: Int?
    @Published var isLoading = false
    @Published var isSaving = false
    @Published var errorMessage: String?
    @Published var statusMessage: String?

    let deckId: Int?

    init(deckId: Int?) {
        self.deckId = deckId
    }

    var isEditMode: Bool {
        deckId != nil
    }

    var selectedHero: Hero? {
        guard let selectedHeroId else {
            return nil
        }

        return heroes.first { $0.id == selectedHeroId }
    }

    var canSave: Bool {
        !deckName.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty &&
            selectedHeroId != nil &&
            !isLoading &&
            !isSaving
    }

    func selectHero(_ hero: Hero) {
        guard !isSaving else {
            return
        }

        selectedHeroId = hero.id
    }

    func load(using authStore: AuthStore) async {
        isLoading = true
        errorMessage = nil
        statusMessage = nil

        do {
            if let deckId {
                async let heroesRequest: [Hero] = authStore.authenticatedGet(
                    "/titles/\(AppConfig.titleSlug)/heroes/"
                )
                async let deckRequest: DeckDetail = authStore.authenticatedGet(
                    "/collection/decks/\(deckId)/"
                )

                let (loadedHeroes, deck) = try await (heroesRequest, deckRequest)
                heroes = loadedHeroes
                deckName = deck.name
                deckDescription = deck.description ?? ""
                selectedHeroId = deck.hero.id
            } else {
                let loadedHeroes: [Hero] = try await authStore.authenticatedGet(
                    "/titles/\(AppConfig.titleSlug)/heroes/"
                )
                heroes = loadedHeroes

                if selectedHeroId == nil, loadedHeroes.count == 1 {
                    selectedHeroId = loadedHeroes[0].id
                }
            }
        } catch {
            errorMessage = error.localizedDescription
        }

        isLoading = false
    }

    func save(using authStore: AuthStore) async -> Int? {
        let trimmedName = deckName.trimmingCharacters(in: .whitespacesAndNewlines)
        let trimmedDescription = deckDescription.trimmingCharacters(in: .whitespacesAndNewlines)

        guard !trimmedName.isEmpty else {
            errorMessage = "Deck name is required."
            return nil
        }

        guard let selectedHeroId else {
            errorMessage = "Choose a hero for this deck."
            return nil
        }

        isSaving = true
        errorMessage = nil
        statusMessage = nil

        do {
            let request = DeckSaveRequest(
                name: trimmedName,
                description: trimmedDescription,
                heroId: selectedHeroId
            )
            let response: DeckSaveResponse

            if let deckId {
                response = try await authStore.authenticatedPut(
                    "/collection/decks/\(deckId)/",
                    body: request
                )
            } else {
                response = try await authStore.authenticatedPost(
                    "/collection/titles/\(AppConfig.titleSlug)/decks/",
                    body: request
                )
            }

            statusMessage = response.message
            isSaving = false
            return response.id
        } catch {
            errorMessage = error.localizedDescription
            isSaving = false
            return nil
        }
    }
}

struct DeckEditorView: View {
    @EnvironmentObject private var authStore: AuthStore
    @StateObject private var model: DeckEditorViewModel
    @State private var hasLoaded = false

    let onSaved: (Int) -> Void
    let onCancel: () -> Void

    init(
        deckId: Int?,
        onSaved: @escaping (Int) -> Void,
        onCancel: @escaping () -> Void
    ) {
        _model = StateObject(wrappedValue: DeckEditorViewModel(deckId: deckId))
        self.onSaved = onSaved
        self.onCancel = onCancel
    }

    var body: some View {
        ArchetypeScreen {
            ScrollView {
                VStack(spacing: 0) {
                    topBar
                        .padding(.horizontal, 18)
                        .padding(.top, 6)
                        .padding(.bottom, 16)

                    ArchetypePageBanner(title: model.isEditMode ? "Edit Deck" : "New Deck")

                    VStack(spacing: 20) {
                        ArchetypeWebPanel(padding: 24) {
                            if model.isLoading && model.heroes.isEmpty {
                                CollectionProgressRow(text: "Loading deck...")
                            } else {
                                deckForm
                            }
                        }

                        if let error = model.errorMessage {
                            DeckEditorNotice(text: error, color: ArchetypeTheme.red)
                        }

                        if let status = model.statusMessage {
                            DeckEditorNotice(text: status, color: ArchetypeTheme.green)
                        }
                    }
                    .frame(maxWidth: 620)
                    .padding(.horizontal, 18)
                    .padding(.top, 32)
                    .padding(.bottom, 40)
                }
            }
        }
        .toolbar(.hidden, for: .navigationBar)
        .navigationBarBackButtonHidden(true)
        .task {
            await loadInitialData()
        }
    }

    private var topBar: some View {
        ArchetypeTopBar(title: "Collection", showsBackButton: true) {
            ArchetypeProfileLink(user: authStore.user) {
                ProfileView()
            }
        }
    }

    private var deckForm: some View {
        VStack(alignment: .leading, spacing: 24) {
            DeckFormField(label: "Deck Name") {
                TextField("Enter deck name", text: $model.deckName)
                    .font(.archetypeBody(15))
                    .textInputAutocapitalization(.words)
                    .autocorrectionDisabled()
                    .foregroundStyle(ArchetypeTheme.text)
                    .tint(ArchetypeTheme.gold2)
                    .submitLabel(.done)
                    .disabled(model.isSaving)
            }

            VStack(alignment: .leading, spacing: 12) {
                Text("Hero")
                    .font(.archetypeBody(14, weight: .semibold))
                    .foregroundStyle(ArchetypeTheme.secondaryText)

                if let selectedHero = model.selectedHero {
                    Text("Selected hero: \(selectedHero.name)")
                        .font(.archetypeBody(13))
                        .foregroundStyle(ArchetypeTheme.muted)
                }

                if model.heroes.isEmpty {
                    EmptyState(
                        title: "No heroes available.",
                        detail: "This title needs a hero before decks can be created.",
                        systemImage: "person.crop.rectangle.stack"
                    )
                } else {
                    VStack(spacing: 10) {
                        ForEach(model.heroes) { hero in
                            Button {
                                model.selectHero(hero)
                            } label: {
                                DeckHeroChoiceRow(
                                    hero: hero,
                                    isSelected: model.selectedHeroId == hero.id
                                )
                            }
                            .buttonStyle(.plain)
                            .disabled(model.isSaving)
                        }
                    }
                }
            }

            DeckFormField(label: "Description", isOptional: true) {
                TextField("Enter deck description", text: $model.deckDescription, axis: .vertical)
                    .font(.archetypeBody(15))
                    .textInputAutocapitalization(.sentences)
                    .foregroundStyle(ArchetypeTheme.text)
                    .tint(ArchetypeTheme.gold2)
                    .lineLimit(3...5)
                    .disabled(model.isSaving)
            }

            HStack(spacing: 12) {
                Button {
                    Task {
                        if let deckId = await model.save(using: authStore) {
                            onSaved(deckId)
                        }
                    }
                } label: {
                    HStack(spacing: 8) {
                        if model.isSaving {
                            ProgressView()
                                .tint(.white)
                        }

                        Text(model.isEditMode ? "Update Deck" : "Create Deck")
                    }
                    .frame(maxWidth: .infinity)
                }
                .buttonStyle(PrimaryGameButtonStyle())
                .disabled(!model.canSave)
                .opacity(model.canSave ? 1 : 0.55)

                Button(action: onCancel) {
                    Text("Cancel")
                        .frame(maxWidth: .infinity)
                }
                .buttonStyle(SecondaryGameButtonStyle())
                .disabled(model.isSaving)
            }
        }
    }

    private func loadInitialData() async {
        guard !hasLoaded else {
            return
        }

        hasLoaded = true
        await model.load(using: authStore)
    }
}

private struct DeckFormField<Content: View>: View {
    let label: String
    var isOptional = false
    let content: Content

    init(
        label: String,
        isOptional: Bool = false,
        @ViewBuilder content: () -> Content
    ) {
        self.label = label
        self.isOptional = isOptional
        self.content = content()
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack(spacing: 6) {
                Text(label)
                    .font(.archetypeBody(14, weight: .semibold))
                    .foregroundStyle(ArchetypeTheme.secondaryText)

                if isOptional {
                    Text("optional")
                        .font(.archetypeBody(11, weight: .medium))
                        .foregroundStyle(ArchetypeTheme.muted)
                }
            }

            content
                .padding(14)
                .background(ArchetypeTheme.inputSurface)
                .overlay(
                    RoundedRectangle(cornerRadius: ArchetypeTheme.controlRadius)
                        .stroke(ArchetypeTheme.border, lineWidth: 1)
                )
                .clipShape(RoundedRectangle(cornerRadius: ArchetypeTheme.controlRadius))
        }
    }
}

private struct DeckHeroChoiceRow: View {
    let hero: Hero
    let isSelected: Bool

    var body: some View {
        HStack(spacing: 14) {
            heroArt
                .frame(width: 46, height: 64)
                .clipShape(RoundedRectangle(cornerRadius: 7))
                .overlay(
                    RoundedRectangle(cornerRadius: 7)
                        .stroke(isSelected ? ArchetypeTheme.gold2 : ArchetypeTheme.border, lineWidth: isSelected ? 2 : 1)
                )

            VStack(alignment: .leading, spacing: 6) {
                Text(hero.name)
                    .font(.archetypeBody(16, weight: .semibold))
                    .foregroundStyle(ArchetypeTheme.text)
                    .lineLimit(1)

                if let detail = heroDetail {
                    Text(detail)
                        .font(.archetypeBody(12))
                        .foregroundStyle(ArchetypeTheme.muted)
                        .lineLimit(2)
                        .fixedSize(horizontal: false, vertical: true)
                }
            }

            Spacer(minLength: 8)

            if let health = hero.health {
                VStack(spacing: 2) {
                    Text("Health")
                        .font(.archetypeBody(9, weight: .bold))
                        .foregroundStyle(ArchetypeTheme.muted)
                    Text("\(health)")
                        .font(.archetypeBody(17, weight: .black))
                        .foregroundStyle(ArchetypeTheme.text)
                }
                .padding(.horizontal, 11)
                .padding(.vertical, 8)
                .background(ArchetypeTheme.subtleSurface)
                .clipShape(RoundedRectangle(cornerRadius: 8))
            }

            Image(systemName: isSelected ? "checkmark.circle.fill" : "circle")
                .font(.system(size: 20, weight: .semibold))
                .foregroundStyle(isSelected ? ArchetypeTheme.gold2 : ArchetypeTheme.muted)
        }
        .padding(12)
        .background(isSelected ? ArchetypeTheme.gold.opacity(0.09) : ArchetypeTheme.subtleSurface)
        .overlay(
            RoundedRectangle(cornerRadius: 8)
                .stroke(isSelected ? ArchetypeTheme.gold2.opacity(0.65) : ArchetypeTheme.border, lineWidth: 1)
        )
        .clipShape(RoundedRectangle(cornerRadius: 8))
        .contentShape(Rectangle())
    }

    private var heroDetail: String? {
        if let description = hero.heroPower?["description"]?.stringValue, !description.isEmpty {
            return description
        }

        if let name = hero.heroPower?["name"]?.stringValue, !name.isEmpty {
            return name
        }

        return hero.faction
    }

    @ViewBuilder
    private var heroArt: some View {
        if let artUrl = hero.resolvedArtUrl, let url = URL(string: artUrl) {
            CachedRemoteImage(url: url) { image in
                image
                    .resizable()
                    .scaledToFill()
            } placeholder: {
                fallbackHero
            }
        } else {
            fallbackHero
        }
    }

    private var fallbackHero: some View {
        ZStack {
            ArchetypeTheme.sky.opacity(0.16)
            Text(hero.name.prefix(1).uppercased())
                .font(.archetypeBody(18, weight: .black))
                .foregroundStyle(ArchetypeTheme.sky)
        }
    }
}

private struct DeckEditorNotice: View {
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

private struct CollectionProgressRow: View {
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

private struct CollectionDeckRow: View {
    let deck: Deck

    var body: some View {
        HStack(spacing: 12) {
            heroArt
                .frame(width: 40, height: 56)
                .clipShape(RoundedRectangle(cornerRadius: 7))
                .overlay(
                    RoundedRectangle(cornerRadius: 7)
                        .stroke(ArchetypeTheme.border, lineWidth: 1)
                )

            VStack(alignment: .leading, spacing: 5) {
                Text(deck.name)
                    .font(.archetypeBody(16, weight: .medium))
                    .foregroundStyle(ArchetypeTheme.text)
                    .lineLimit(1)
            }

            Spacer()

            Text("\(deck.cardCount ?? 0) cards")
                .font(.archetypeBody(13, weight: .medium))
                .foregroundStyle(ArchetypeTheme.muted)
        }
        .padding(12)
        .contentShape(Rectangle())
    }

    @ViewBuilder
    private var heroArt: some View {
        if let artUrl = deck.hero.resolvedArtUrl, let url = URL(string: artUrl) {
            CachedRemoteImage(url: url) { image in
                image
                    .resizable()
                    .scaledToFit()
            } placeholder: {
                fallbackHero
            }
        } else {
            fallbackHero
        }
    }

    private var fallbackHero: some View {
        ZStack {
            ArchetypeTheme.sky.opacity(0.16)
            Text(deck.hero.name.prefix(1).uppercased())
                .font(.archetypeBody(16, weight: .black))
                .foregroundStyle(ArchetypeTheme.sky)
        }
    }
}

private struct CardGridSection: View {
    let title: String
    let cards: [CardTemplate]
    let columns: [GridItem]
    let isDimmed: Bool
    let showsDetails: Bool
    let onSelect: (CardTemplate) -> Void

    var body: some View {
        if !cards.isEmpty {
            VStack(alignment: .leading, spacing: 24) {
                Text(title)
                    .font(.archetypeDisplay(24, weight: .bold))
                    .foregroundStyle(ArchetypeTheme.text)
                    .frame(maxWidth: .infinity, alignment: .leading)

                LazyVGrid(columns: columns, spacing: 32) {
                    ForEach(cards) { card in
                        Button {
                            onSelect(card)
                        } label: {
                            CollectionCardView(
                                card: card,
                                isDimmed: isDimmed,
                                showsDetails: showsDetails
                            )
                        }
                        .buttonStyle(.plain)
                        .accessibilityLabel(card.name)
                    }
                }
                .padding(.bottom, 12)
            }
        }
    }
}

private struct CollectionCardView: View {
    let card: CardTemplate
    let isDimmed: Bool
    let showsDetails: Bool

    var body: some View {
        ZStack(alignment: .top) {
            RoundedRectangle(cornerRadius: 12)
                .fill(Color(hex: 0xD1D5DB))

            cardArt
                .frame(maxWidth: .infinity, maxHeight: .infinity)
                .clipShape(RoundedRectangle(cornerRadius: 12))

            if showsDetails {
                detailsOverlay
            }
        }
        .aspectRatio(5 / 7, contentMode: .fit)
        .overlay(
            RoundedRectangle(cornerRadius: 12)
                .stroke(Color(hex: 0x111827), lineWidth: 2)
        )
        .overlay(alignment: .topLeading) {
            if let traitGlyph {
                CollectionCardBadge(text: traitGlyph, color: Color.white, textColor: Color(hex: 0x111827))
                    .offset(x: -12, y: -12)
            }
        }
        .overlay(alignment: .topTrailing) {
            CollectionCardBadge(text: "\(card.cost)", color: ArchetypeTheme.sky)
                .offset(x: 12, y: -12)
        }
        .overlay(alignment: .bottomLeading) {
            if !card.isSpell {
                CollectionCardBadge(text: "\(card.attack)", color: ArchetypeTheme.red)
                    .offset(x: -12, y: 12)
            }
        }
        .overlay(alignment: .bottomTrailing) {
            if !card.isSpell {
                CollectionCardBadge(text: "\(card.health)", color: ArchetypeTheme.green)
                    .offset(x: 12, y: 12)
            }
        }
        .opacity(isDimmed ? 0.72 : 1)
    }

    private var detailsOverlay: some View {
        VStack(spacing: 0) {
            Text(card.name)
                .font(.archetypeBody(18, weight: .bold))
                .foregroundStyle(Color.white)
                .lineLimit(1)
                .minimumScaleFactor(0.66)
                .frame(height: 28)
                .frame(maxWidth: .infinity)
                .padding(.horizontal, 22)
                .padding(.vertical, 8)
                .background(Color.black.opacity(0.78))

            Spacer(minLength: 0)

            if let description = card.description, !description.isEmpty {
                Text(description)
                    .font(.archetypeBody(12, weight: .medium))
                    .foregroundStyle(Color.white)
                    .lineLimit(2)
                    .multilineTextAlignment(.leading)
                    .fixedSize(horizontal: false, vertical: true)
                    .padding(12)
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .background(Color.black.opacity(0.78))
                    .clipShape(RoundedRectangle(cornerRadius: 12))
                    .padding(12)
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

    @ViewBuilder
    private var cardArt: some View {
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

private struct CollectionCardBadge: View {
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

private struct CardPreviewScreen: View {
    @EnvironmentObject private var authStore: AuthStore

    let card: CardTemplate
    let onClose: () -> Void

    var body: some View {
        ArchetypeScreen {
            VStack(spacing: 0) {
                topBar
                    .padding(.horizontal, 18)
                    .padding(.top, 6)
                    .padding(.bottom, 16)

                backLink
                    .padding(.horizontal, 18)
                    .padding(.bottom, 8)

                ArchetypeCardDetailHeader(title: card.name)

                ScrollView {
                    VStack(alignment: .leading, spacing: 20) {
                        VStack(alignment: .leading, spacing: 20) {
                            Text(cardTypeLine)
                                .font(.archetypeBody(15, weight: .medium))
                                .foregroundStyle(ArchetypeTheme.muted)
                                .fixedSize(horizontal: false, vertical: true)

                            CardDetailStatGrid(card: card)

                            if let description = card.description, !description.isEmpty {
                                Text(description)
                                    .font(.archetypeBody(17))
                                    .foregroundStyle(ArchetypeTheme.text)
                                    .fixedSize(horizontal: false, vertical: true)
                                    .padding(16)
                                    .frame(maxWidth: .infinity, alignment: .leading)
                                    .background(ArchetypeTheme.panel)
                                    .overlay(
                                        RoundedRectangle(cornerRadius: 12)
                                            .stroke(ArchetypeTheme.border, lineWidth: 1)
                                    )
                                    .clipShape(RoundedRectangle(cornerRadius: 12))
                            }
                        }

                        CollectionCardView(
                            card: card,
                            isDimmed: !card.isCollectibleCard,
                            showsDetails: false
                        )
                        .frame(width: 180)
                        .frame(maxWidth: .infinity)
                    }
                    .frame(maxWidth: 560, alignment: .leading)
                    .padding(.horizontal, 18)
                    .padding(.top, 16)
                    .padding(.bottom, 34)
                }
            }
        }
    }

    private var topBar: some View {
        ArchetypeTopBar {
            ArchetypeProfileAvatar(user: authStore.user)
        }
    }

    private var backLink: some View {
        Button(action: onClose) {
            HStack(spacing: 5) {
                Image(systemName: "arrow.left")
                    .font(.system(size: 13, weight: .medium))
                Text("Back")
                    .font(.archetypeBody(13, weight: .medium))
            }
            .foregroundStyle(ArchetypeTheme.muted.opacity(0.42))
            .frame(maxWidth: .infinity, alignment: .leading)
        }
        .buttonStyle(.plain)
        .accessibilityLabel("Back to collection")
    }

    private var cardTypeLine: String {
        var parts = [card.cardType.capitalized]
        if !card.traitTypes.isEmpty {
            parts.append("[ \(card.traitTypes.map { $0.uppercased() }.joined(separator: ", ")) ]")
        }
        return parts.joined(separator: " ")
    }
}

private struct CardDetailStatGrid: View {
    let card: CardTemplate

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
