import SwiftUI

@MainActor
final class DashboardViewModel: ObservableObject {
    @Published var title: Title?
    @Published var decks: [Deck] = []
    @Published var pveOpponents: [Deck] = []
    @Published var games: [GameSummary] = []
    @Published var selectedDeckId: Int?
    @Published var selectedOpponentId: Int?
    @Published var isLoading = false
    @Published var errorMessage: String?
    @Published var statusMessage: String?

    func load(using authStore: AuthStore) async {
        isLoading = true
        errorMessage = nil

        do {
            async let titleRequest: Title = authStore.authenticatedGet("/titles/\(AppConfig.titleSlug)/")
            async let deckRequest: DeckListResponse = authStore.authenticatedGet("/collection/titles/\(AppConfig.titleSlug)/decks/")
            async let pveRequest: [Deck] = authStore.authenticatedGet("/titles/\(AppConfig.titleSlug)/pve/")
            async let gameRequest: GameListResponse = authStore.authenticatedGet("/titles/\(AppConfig.titleSlug)/games/")

            let (title, deckResponse, pveOpponents, gameResponse) = try await (
                titleRequest,
                deckRequest,
                pveRequest,
                gameRequest
            )

            self.title = title
            self.decks = deckResponse.decks
            self.pveOpponents = pveOpponents
            self.games = gameResponse.games

            if selectedDeckId == nil {
                selectedDeckId = deckResponse.lastUsedDeckId ?? self.decks.first?.id
            }

            if selectedOpponentId == nil {
                selectedOpponentId = self.pveOpponents.first?.id
            }
        } catch {
            errorMessage = error.localizedDescription
        }

        isLoading = false
    }

    func startPracticeGame(using authStore: AuthStore) async -> Int? {
        guard let selectedDeckId, let selectedOpponentId else {
            errorMessage = "Choose one of your decks and a practice opponent first."
            return nil
        }

        isLoading = true
        errorMessage = nil
        statusMessage = nil

        do {
            let response: CreateGameResponse = try await authStore.authenticatedPost(
                "/gameplay/games/new/",
                body: CreateGameRequest(
                    playerDeckId: selectedDeckId,
                    aiDeckId: selectedOpponentId,
                    opponentDeckId: nil
                )
            )
            statusMessage = response.message ?? "Practice game created."
            isLoading = false
            return response.id
        } catch {
            errorMessage = error.localizedDescription
            isLoading = false
            return nil
        }
    }
}

struct DashboardView: View {
    @EnvironmentObject private var authStore: AuthStore
    @StateObject private var model = DashboardViewModel()
    @StateObject private var userSocket = DrawTwoWebSocket()
    @State private var path = NavigationPath()

    var body: some View {
        NavigationStack(path: $path) {
            List {
                titleSection
                connectionSection
                practiceSection
                gamesSection
                decksSection
            }
            .listStyle(.insetGrouped)
            .navigationTitle("Archetype")
            .toolbar {
                ToolbarItem(placement: .topBarLeading) {
                    Button {
                        authStore.signOut()
                    } label: {
                        Label("Sign Out", systemImage: "rectangle.portrait.and.arrow.right")
                    }
                }

                ToolbarItem(placement: .topBarTrailing) {
                    Button {
                        Task { await model.load(using: authStore) }
                    } label: {
                        Label("Refresh", systemImage: "arrow.clockwise")
                    }
                    .disabled(model.isLoading)
                }
            }
            .navigationDestination(for: Int.self) { gameId in
                GameDetailView(gameId: gameId)
            }
            .task {
                await model.load(using: authStore)
                connectUserSocketIfPossible()
            }
            .onDisappear {
                userSocket.disconnect()
            }
        }
    }

    private var titleSection: some View {
        Section {
            VStack(alignment: .leading, spacing: 8) {
                Text(model.title?.name ?? "Archetype")
                    .font(.title2.bold())
                Text(model.title?.description ?? "Native iOS prototype connected to the DrawTwo backend.")
                    .font(.callout)
                    .foregroundStyle(.secondary)
                Text(authStore.user?.displayName ?? authStore.user?.email ?? "Signed in")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
            .padding(.vertical, 6)
        }
    }

    private var connectionSection: some View {
        Section("Backend") {
            Label("drawtwo.com", systemImage: "network")
            Label(userSocket.status.rawValue, systemImage: "dot.radiowaves.left.and.right")
                .foregroundStyle(userSocket.status == .connected ? .green : .secondary)

            if userSocket.messagesReceived > 0 {
                Text("User notifications received: \(userSocket.messagesReceived)")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }

            if let error = model.errorMessage {
                Text(error)
                    .font(.callout)
                    .foregroundStyle(.red)
            }

            if let error = userSocket.errorMessage {
                Text("Live notifications unavailable: \(error)")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }

            if let status = model.statusMessage {
                Text(status)
                    .font(.callout)
                    .foregroundStyle(.green)
            }
        }
    }

    private var practiceSection: some View {
        Section("Practice") {
            Picker("Your deck", selection: $model.selectedDeckId) {
                Text("Choose a deck").tag(Optional<Int>.none)
                ForEach(model.decks) { deck in
                    Text(deck.name).tag(Optional(deck.id))
                }
            }

            Picker("Opponent", selection: $model.selectedOpponentId) {
                Text("Choose opponent").tag(Optional<Int>.none)
                ForEach(model.pveOpponents) { deck in
                    Text(deck.name).tag(Optional(deck.id))
                }
            }

            Button {
                Task {
                    if let gameId = await model.startPracticeGame(using: authStore) {
                        await model.load(using: authStore)
                        path.append(gameId)
                    }
                }
            } label: {
                Label("Start Practice Game", systemImage: "play.circle")
            }
            .disabled(model.isLoading || model.selectedDeckId == nil || model.selectedOpponentId == nil)

            if model.decks.isEmpty {
                Text("No playable decks were returned for this account.")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
        }
    }

    private var gamesSection: some View {
        Section("Active Games") {
            if model.games.isEmpty {
                Text("No active games.")
                    .foregroundStyle(.secondary)
            } else {
                ForEach(model.games) { game in
                    NavigationLink(value: game.id) {
                        VStack(alignment: .leading, spacing: 4) {
                            Text(game.name)
                                .font(.headline)
                            HStack(spacing: 8) {
                                Text(game.type.uppercased())
                                if game.isUserTurn {
                                    Text("Your turn")
                                        .foregroundStyle(.green)
                                }
                            }
                            .font(.caption)
                            .foregroundStyle(.secondary)
                        }
                    }
                }
            }
        }
    }

    private var decksSection: some View {
        Section("Decks") {
            if model.decks.isEmpty {
                Text("No decks found.")
                    .foregroundStyle(.secondary)
            } else {
                ForEach(model.decks) { deck in
                    VStack(alignment: .leading, spacing: 4) {
                        Text(deck.name)
                            .font(.headline)
                        Text("\(deck.hero.name) / \(deck.cardCount ?? 0) cards")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    }
                }
            }
        }
    }

    private func connectUserSocketIfPossible() {
        guard let accessToken = authStore.currentAccessToken else {
            return
        }
        userSocket.connect(path: "/ws/user/", accessToken: accessToken)
    }
}
