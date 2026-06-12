import SwiftUI

@MainActor
final class DashboardViewModel: ObservableObject {
    @Published var title: Title?
    @Published var decks: [Deck] = []
    @Published var pveOpponents: [Deck] = []
    @Published var games: [GameSummary] = []
    @Published var topPlayers: [LeaderboardPlayer] = []
    @Published var notifications: [TitleNotification] = []
    @Published var friends: [Friendship] = []
    @Published var pendingOutgoingChallenges: [FriendlyChallenge] = []
    @Published var selectedDeckId: Int?
    @Published var selectedOpponentId: Int?
    @Published var selectedFriendId: Int?
    @Published var leaderboardLadder: LadderType = .daily
    @Published var gameMode: GameMode = .pvp
    @Published var rapidQueueEntry: RankedQueueEntry?
    @Published var dailyQueueEntry: RankedQueueEntry?
    @Published var isLoading = false
    @Published var isLeaderboardLoading = false
    @Published var isRankedQueueLoading = false
    @Published var isNotificationActionLoading = false
    @Published var isFriendChallengeLoading = false
    @Published var errorMessage: String?
    @Published var statusMessage: String?
    @Published var leaderboardErrorMessage: String?
    @Published var rankedQueueErrorMessage: String?
    @Published var notificationErrorMessage: String?
    @Published var friendsErrorMessage: String?
    @Published var challengeErrorMessage: String?
    @Published var matchedGameId: Int?

    private var lastUsedFriendId: Int?

    var selectedDeck: Deck? {
        decks.first { $0.id == selectedDeckId }
    }

    var selectedOpponent: Deck? {
        pveOpponents.first { $0.id == selectedOpponentId }
    }

    var selectedFriend: Friendship? {
        friends.first { $0.friendData.id == selectedFriendId }
    }

    func queuedEntry(id: Int) -> RankedQueueEntry? {
        [rapidQueueEntry, dailyQueueEntry]
            .compactMap { $0 }
            .first { $0.id == id }
    }

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
            lastUsedFriendId = deckResponse.lastUsedFriendId

            if selectedDeckId == nil || !self.decks.contains(where: { $0.id == selectedDeckId }) {
                selectedDeckId = deckResponse.lastUsedDeckId ?? self.decks.first?.id
            }

            if selectedOpponentId == nil || !self.pveOpponents.contains(where: { $0.id == selectedOpponentId }) {
                selectedOpponentId = self.pveOpponents.first?.id
            }
        } catch {
            errorMessage = error.localizedDescription
        }

        isLoading = false
        await loadLeaderboard(using: authStore)
        await loadRankedQueueStatuses(using: authStore)
        await loadNotifications(using: authStore)
        await loadFriends(using: authStore)
        await loadPendingChallenges(using: authStore)
    }

    func loadFriends(using authStore: AuthStore) async {
        friendsErrorMessage = nil

        do {
            let allFriendships: [Friendship] = try await authStore.authenticatedGet("/auth/friends/")
            friends = allFriendships
                .filter { $0.status == .accepted }
                .sorted { first, second in
                    first.friendData.displayLabel.localizedCaseInsensitiveCompare(
                        second.friendData.displayLabel
                    ) == .orderedAscending
                }

            if selectedFriendId == nil || !friends.contains(where: { $0.friendData.id == selectedFriendId }) {
                selectedFriendId = lastUsedFriendId.flatMap { id in
                    friends.first { $0.friendData.id == id }?.friendData.id
                } ?? friends.first?.friendData.id
            }
        } catch {
            friendsErrorMessage = error.localizedDescription
            friends = []
            selectedFriendId = nil
        }
    }

    func loadPendingChallenges(using authStore: AuthStore) async {
        challengeErrorMessage = nil

        do {
            let response: PendingChallengesResponse = try await authStore.authenticatedGet(
                "/gameplay/challenges/pending/\(AppConfig.titleSlug)/"
            )
            pendingOutgoingChallenges = response.outgoing
        } catch {
            challengeErrorMessage = error.localizedDescription
            pendingOutgoingChallenges = []
        }
    }

    func loadNotifications(using authStore: AuthStore) async {
        notificationErrorMessage = nil

        do {
            let response: [TitleNotification] = try await authStore.authenticatedGet(
                "/titles/\(AppConfig.titleSlug)/notifications/"
            )
            notifications = response
        } catch {
            notificationErrorMessage = error.localizedDescription
            notifications = []
        }
    }

    func loadLeaderboard(using authStore: AuthStore) async {
        isLeaderboardLoading = true
        leaderboardErrorMessage = nil

        do {
            let players: [LeaderboardPlayer] = try await authStore.authenticatedGet(
                "/gameplay/\(AppConfig.titleSlug)/leaderboard/",
                queryItems: [
                    URLQueryItem(name: "limit", value: "3"),
                    URLQueryItem(name: "ladder_type", value: leaderboardLadder.rawValue),
                ]
            )
            topPlayers = players
        } catch {
            leaderboardErrorMessage = error.localizedDescription
            topPlayers = []
        }

        isLeaderboardLoading = false
    }

    func setLeaderboardLadder(_ ladder: LadderType, using authStore: AuthStore) async {
        guard leaderboardLadder != ladder else {
            return
        }
        leaderboardLadder = ladder
        await loadLeaderboard(using: authStore)
    }

    func loadRankedQueueStatuses(using authStore: AuthStore) async {
        isRankedQueueLoading = true
        rankedQueueErrorMessage = nil

        do {
            rapidQueueEntry = try await rankedQueueEntry(.rapid, using: authStore)
            dailyQueueEntry = try await rankedQueueEntry(.daily, using: authStore)
        } catch {
            rankedQueueErrorMessage = error.localizedDescription
        }

        isRankedQueueLoading = false
    }

    @discardableResult
    func queueForRanked(_ ladder: LadderType, using authStore: AuthStore) async -> Bool {
        guard let selectedDeckId else {
            errorMessage = "Choose one of your decks before queueing."
            return false
        }

        isRankedQueueLoading = true
        errorMessage = nil
        statusMessage = nil
        rankedQueueErrorMessage = nil

        do {
            let response: RankedQueueEntry = try await authStore.authenticatedPost(
                "/gameplay/matchmaking/queue/",
                body: RankedQueueRequest(deckId: selectedDeckId, ladderType: ladder)
            )
            statusMessage = response.message
                ?? "Queued for \(ladder.label.lowercased()) ranked match."
            await loadRankedQueueStatuses(using: authStore)
            return true
        } catch {
            rankedQueueErrorMessage = error.localizedDescription
            isRankedQueueLoading = false
            return false
        }
    }

    func leaveRankedQueue(_ ladder: LadderType, using authStore: AuthStore) async {
        isRankedQueueLoading = true
        errorMessage = nil
        statusMessage = nil
        rankedQueueErrorMessage = nil

        do {
            let _: JSONValue = try await authStore.authenticatedPost(
                "/gameplay/matchmaking/leave/\(AppConfig.titleSlug)/",
                queryItems: [URLQueryItem(name: "ladder_type", value: ladder.rawValue)],
                body: EmptyBody()
            )
            statusMessage = "Left \(ladder.label.lowercased()) ranked queue."
            await loadRankedQueueStatuses(using: authStore)
        } catch {
            rankedQueueErrorMessage = error.localizedDescription
            isRankedQueueLoading = false
        }
    }

    private func rankedQueueEntry(
        _ ladder: LadderType,
        using authStore: AuthStore
    ) async throws -> RankedQueueEntry? {
        let response: RankedQueueStatusResponse = try await authStore.authenticatedGet(
            "/gameplay/matchmaking/status/\(AppConfig.titleSlug)/",
            queryItems: [URLQueryItem(name: "ladder_type", value: ladder.rawValue)]
        )

        if let error = response.error {
            rankedQueueErrorMessage = error
        }

        return response.inQueue ? response.queueEntry : nil
    }

    func acceptChallenge(_ notification: TitleNotification, using authStore: AuthStore) async -> Int? {
        guard let selectedDeckId else {
            notificationErrorMessage = "Choose one of your decks before accepting."
            return nil
        }

        isNotificationActionLoading = true
        notificationErrorMessage = nil
        statusMessage = nil

        do {
            let response: ChallengeAcceptResponse = try await authStore.authenticatedPost(
                "/gameplay/challenges/\(notification.refId)/accept/",
                body: ChallengeAcceptRequest(challengeeDeckId: selectedDeckId)
            )
            notifications.removeAll { $0.id == notification.id }
            statusMessage = "Challenge accepted."
            isNotificationActionLoading = false
            return response.gameId
        } catch {
            notificationErrorMessage = error.localizedDescription
            isNotificationActionLoading = false
            await loadNotifications(using: authStore)
            return nil
        }
    }

    func declineChallenge(_ notification: TitleNotification, using authStore: AuthStore) async {
        isNotificationActionLoading = true
        notificationErrorMessage = nil
        statusMessage = nil

        do {
            let _: JSONValue = try await authStore.authenticatedPost(
                "/gameplay/challenges/\(notification.refId)/decline/",
                body: EmptyBody()
            )
            notifications.removeAll { $0.id == notification.id }
            statusMessage = "Challenge declined."
        } catch {
            notificationErrorMessage = error.localizedDescription
            await loadNotifications(using: authStore)
        }

        isNotificationActionLoading = false
    }

    func outgoingChallenge(for friendship: Friendship) -> FriendlyChallenge? {
        pendingOutgoingChallenges.first { challenge in
            challenge.challengee.id == friendship.friendData.id
        }
    }

    func challengeSelectedFriend(using authStore: AuthStore) async {
        guard let selectedDeckId else {
            challengeErrorMessage = "Choose one of your decks before sending a challenge."
            return
        }

        guard let selectedFriend else {
            challengeErrorMessage = "Choose a friend before sending a challenge."
            return
        }

        isFriendChallengeLoading = true
        challengeErrorMessage = nil
        statusMessage = nil

        do {
            let challenge: FriendlyChallenge = try await authStore.authenticatedPost(
                "/gameplay/challenges/",
                body: FriendlyChallengeCreateRequest(
                    titleSlug: AppConfig.titleSlug,
                    challengeeUserId: selectedFriend.friendData.id,
                    challengerDeckId: selectedDeckId
                )
            )
            upsertOutgoingChallenge(challenge)
            statusMessage = "Challenge sent to \(selectedFriend.friendData.displayLabel)."
            await loadPendingChallenges(using: authStore)
        } catch {
            challengeErrorMessage = error.localizedDescription
        }

        isFriendChallengeLoading = false
    }

    func cancelChallenge(_ challenge: FriendlyChallenge, using authStore: AuthStore) async {
        isFriendChallengeLoading = true
        challengeErrorMessage = nil
        statusMessage = nil

        do {
            let response: ChallengeActionResponse = try await authStore.authenticatedPost(
                "/gameplay/challenges/\(challenge.id)/cancel/",
                body: EmptyBody()
            )
            pendingOutgoingChallenges.removeAll { $0.id == challenge.id }
            statusMessage = response.message ?? "Challenge withdrawn."
            await loadPendingChallenges(using: authStore)
        } catch {
            challengeErrorMessage = error.localizedDescription
        }

        isFriendChallengeLoading = false
    }

    private func upsertOutgoingChallenge(_ challenge: FriendlyChallenge) {
        if let index = pendingOutgoingChallenges.firstIndex(where: { $0.id == challenge.id }) {
            pendingOutgoingChallenges[index] = challenge
        } else {
            pendingOutgoingChallenges.append(challenge)
        }
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

    func handleUserWebSocketText(_ text: String, using authStore: AuthStore) async {
        guard
            let data = text.data(using: .utf8),
            let event = try? JSONDecoder().decode(UserSocketEvent.self, from: data),
            event.type == "matchmaking_success",
            event.titleSlug == AppConfig.titleSlug,
            let gameId = event.gameId
        else {
            return
        }

        statusMessage = "Match found. Opening game."
        matchedGameId = gameId

        await load(using: authStore)
    }
}

private struct UserSocketEvent: Decodable {
    let type: String
    let gameId: Int?
    let titleSlug: String?

    private enum CodingKeys: String, CodingKey {
        case type
        case gameId = "game_id"
        case titleSlug = "title_slug"
    }
}

struct DashboardView: View {
    @EnvironmentObject private var authStore: AuthStore
    @Environment(\.scenePhase) private var scenePhase
    @StateObject private var model = DashboardViewModel()
    @StateObject private var userSocket = DrawTwoWebSocket()
    @State private var path = NavigationPath()
    @State private var isProfileMenuOpen = false
    @State private var dashboardScrollTarget: DashboardSection?
    @State private var appliedInitialDashboardSection = false

    var body: some View {
        NavigationStack(path: $path) {
            ArchetypeScreen {
                ZStack(alignment: .topTrailing) {
                    ScrollViewReader { proxy in
                        ScrollView {
                            VStack(spacing: 16) {
                                topBar
                                TitleArtworkBanner(title: model.title)
                                titleDescriptionPanel
                                dashboardLinks
                                dashboardSummaryPanels
                                newGamePanel
                                notificationsPanel
                                leaderboardPanel
                                    .id(DashboardSection.leaderboard)
                                howToPanel
                            }
                            .padding(.horizontal, 18)
                            .padding(.top, 10)
                            .padding(.bottom, 144)
                        }
                        .refreshable {
                            await model.load(using: authStore)
                        }
                        .onChange(of: dashboardScrollTarget) { _, target in
                            guard let target else {
                                return
                            }

                            withAnimation(.snappy) {
                                proxy.scrollTo(target, anchor: .top)
                            }

                            DispatchQueue.main.asyncAfter(deadline: .now() + 0.65) {
                                withAnimation(.snappy) {
                                    proxy.scrollTo(target, anchor: .top)
                                }
                            }
                            dashboardScrollTarget = nil
                        }
                    }

                    TopSafeAreaScrim()

                    if isProfileMenuOpen {
                        Color.black.opacity(0.001)
                            .ignoresSafeArea()
                            .onTapGesture {
                                withAnimation(.easeOut(duration: 0.14)) {
                                    isProfileMenuOpen = false
                                }
                            }

                        ProfileMenuDropdown(
                            signedInLabel: signedInLabel,
                            openProfile: {
                                isProfileMenuOpen = false
                                path.append(DashboardRoute.profile)
                            },
                            openFriends: {
                                isProfileMenuOpen = false
                                path.append(DashboardRoute.friends)
                            },
                            signOut: {
                                isProfileMenuOpen = false
                                Task {
                                    await authStore.signOut()
                                }
                            }
                        )
                        .padding(.top, 68)
                        .padding(.trailing, 18)
                        .transition(.opacity.combined(with: .move(edge: .top)))
                        .zIndex(1)
                    }
                }
            }
            .toolbar(.hidden, for: .navigationBar)
            .navigationDestination(for: DashboardRoute.self) { route in
                switch route {
                case .newGame:
                    NewGameView(
                        model: model,
                        openGame: { gameId in
                            path.append(DashboardRoute.game(gameId))
                        },
                        openRankedQueue: { ladder, deckId in
                            path.append(DashboardRoute.rankedQueue(ladder, deckId))
                        },
                        openFriends: {
                            path.append(DashboardRoute.friends)
                        }
                    )
                case .game(let gameId):
                    GameDetailView(
                        gameId: gameId,
                        onOpenGame: { nextGameId in
                            if !path.isEmpty {
                                path.removeLast()
                            }
                            path.append(DashboardRoute.game(nextGameId))
                        }
                    )
                case .collection:
                    CollectionView(
                        openDeck: { deckId in
                            path.append(DashboardRoute.deck(deckId))
                        }
                    )
                case .games:
                    GamesHistoryView(
                        onOpenGame: { gameId in
                            path.append(DashboardRoute.game(gameId))
                        },
                        onNewGame: openNewGame
                    )
                case .leaderboard:
                    LeaderboardView()
                case .friends:
                    FriendsView()
                case .profile:
                    ProfileView()
                case .rankedQueue(let ladder, let deckId):
                    RankedQueueView(ladder: ladder, deckId: deckId) { gameId in
                        if !path.isEmpty {
                            path.removeLast()
                        }
                        path.append(DashboardRoute.game(gameId))
                    }
                case .deck(let deckId):
                    DeckDetailView(deckId: deckId)
                case .howTo:
                    HowToView()
                }
            }
            .task {
                await model.load(using: authStore)
                connectUserSocketIfPossible()
                applyInitialDashboardSectionIfNeeded()
                applyInitialProfileMenuIfNeeded()
                recordDashboardCaptureState()
            }
            .task {
                await refreshNotificationsWhileVisible()
            }
            .onDisappear {
                userSocket.disconnect()
            }
            .onChange(of: model.matchedGameId) { _, gameId in
                guard let gameId else {
                    return
                }
                path.append(DashboardRoute.game(gameId))
                model.matchedGameId = nil
            }
            .onChange(of: isProfileMenuOpen) { _, _ in
                recordDashboardCaptureState()
            }
            .onChange(of: scenePhase) { _, phase in
                guard phase == .active else {
                    return
                }
                Task {
                    await model.load(using: authStore)
                    connectUserSocketIfPossible()
                    recordDashboardCaptureState()
                }
            }
        }
    }

    private func recordDashboardCaptureState() {
        CaptureStateRecorder.record(isProfileMenuOpen ? "profile-menu" : "dashboard")
    }

    private var topBar: some View {
        HStack(spacing: 10) {
            ArchetypeBreadcrumb(title: model.title?.name ?? "Archetype")

            Spacer()

            profileButton
        }
    }

    private var profileButton: some View {
        Button {
            withAnimation(.easeOut(duration: 0.14)) {
                isProfileMenuOpen.toggle()
            }
        } label: {
            ArchetypeProfileAvatar(user: authStore.user, size: 44)
        }
        .buttonStyle(.plain)
        .accessibilityLabel("Profile menu")
    }

    private var signedInLabel: String {
        authStore.user?.username
            ?? authStore.user?.email
            ?? authStore.user?.displayName
            ?? "Player"
    }

    private var titleDescriptionPanel: some View {
        Group {
            if let description = model.title?.description, !description.isEmpty {
                ArchetypeWebPanel(title: "Description", padding: 24) {
                    Text(description)
                        .font(.archetypeBody(15))
                        .foregroundStyle(Color(hex: 0xD1D5DB))
                        .fixedSize(horizontal: false, vertical: true)
                }
            }
        }
    }

    private var dashboardLinks: some View {
        LazyVGrid(
            columns: [
                GridItem(.flexible(), spacing: 12),
                GridItem(.flexible(), spacing: 12),
            ],
            spacing: 10
        ) {
            DashboardLinkButton(title: "Collection") {
                path.append(DashboardRoute.collection)
            }
            DashboardLinkButton(title: "Games") {
                path.append(DashboardRoute.games)
            }
        }
    }

    private var dashboardSummaryPanels: some View {
        VStack(spacing: 12) {
            if let error = model.errorMessage {
                DashboardNotice(text: error, color: ArchetypeTheme.red)
            }

            if let error = userSocket.errorMessage {
                DashboardNotice(text: "Live notifications unavailable: \(error)", color: ArchetypeTheme.muted)
            }

            if let error = model.rankedQueueErrorMessage {
                DashboardNotice(text: error, color: ArchetypeTheme.red)
            }

            if let error = model.notificationErrorMessage {
                DashboardNotice(text: error, color: ArchetypeTheme.red)
            }

            if let error = model.friendsErrorMessage {
                DashboardNotice(text: error, color: ArchetypeTheme.red)
            }

            if let error = model.challengeErrorMessage {
                DashboardNotice(text: error, color: ArchetypeTheme.red)
            }

            if let status = model.statusMessage {
                DashboardNotice(text: status, color: ArchetypeTheme.green)
            }
        }
    }

    private var newGamePanel: some View {
        Button {
            openNewGame()
        } label: {
            Label("New Game", systemImage: "plus")
                .frame(maxWidth: .infinity)
        }
        .buttonStyle(DashedActionButtonStyle())
    }

    private var notificationsPanel: some View {
        Group {
            if !model.notifications.isEmpty {
                VStack(spacing: 10) {
                    ForEach(model.notifications) { notification in
                        NotificationRow(
                            notification: notification,
                            isActionLoading: model.isNotificationActionLoading,
                            canAcceptChallenge: model.selectedDeckId != nil,
                            openGame: { gameId in
                                path.append(DashboardRoute.game(gameId))
                            },
                            openQueue: { queueId in
                                openRankedQueueNotification(queueId: queueId)
                            },
                            openFriends: {
                                path.append(DashboardRoute.friends)
                            },
                            accept: {
                                Task {
                                    if let gameId = await model.acceptChallenge(notification, using: authStore) {
                                        await model.load(using: authStore)
                                        path.append(DashboardRoute.game(gameId))
                                    }
                                }
                            },
                            decline: {
                                Task {
                                    await model.declineChallenge(notification, using: authStore)
                                }
                            }
                        )
                    }
                }
            }
        }
    }

    private var howToPanel: some View {
        VStack(spacing: 24) {
            Text("How to Play")
                .font(.archetypeBody(28, weight: .bold))
                .foregroundStyle(ArchetypeTheme.text)
                .frame(maxWidth: .infinity)
                .id(DashboardSection.howTo)

            HowToGuideContent(horizontalInset: 14)
        }
        .frame(maxWidth: 672)
        .padding(.top, 20)
    }

    private var leaderboardPanel: some View {
        VStack(alignment: .leading, spacing: 10) {
            LeaderboardHeader(
                selected: model.leaderboardLadder,
                isLoading: model.isLeaderboardLoading
            ) { ladder in
                Task {
                    await model.setLeaderboardLadder(ladder, using: authStore)
                }
            }

            ArchetypeWebPanel(padding: 0) {
                if model.isLeaderboardLoading {
                    ProgressRow(text: "Loading leaderboard...")
                } else if let error = model.leaderboardErrorMessage {
                    DashboardNotice(text: "Leaderboard unavailable: \(error)", color: ArchetypeTheme.muted)
                        .padding(14)
                } else if model.topPlayers.isEmpty {
                    VStack(spacing: 6) {
                        Text("No ranked players yet.")
                            .font(.archetypeBody(15))
                            .foregroundStyle(Color(hex: 0xD1D5DB))
                        Text("Play five ranked games to appear on the ladder.")
                            .font(.archetypeBody(13))
                            .foregroundStyle(ArchetypeTheme.muted)
                            .multilineTextAlignment(.center)
                    }
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, 28)
                    .padding(.horizontal, 16)
                } else {
                    VStack(spacing: 0) {
                        ForEach(Array(model.topPlayers.enumerated()), id: \.element.id) { index, player in
                            LeaderboardRow(rank: index + 1, player: player)

                            if index < model.topPlayers.count - 1 {
                                Divider()
                                    .overlay(ArchetypeTheme.border)
                            }
                        }

                        Divider()
                            .overlay(ArchetypeTheme.border)

                        Button {
                            path.append(DashboardRoute.leaderboard)
                        } label: {
                            HStack {
                                Text("Full Ladder")
                                    .font(.archetypeBody(12, weight: .bold))
                                    .foregroundStyle(ArchetypeTheme.muted)
                                    .textCase(.uppercase)
                                Spacer()
                                Image(systemName: "chevron.right")
                                    .font(.system(size: 12, weight: .bold))
                                    .foregroundStyle(ArchetypeTheme.muted)
                            }
                            .padding(.horizontal, 14)
                            .padding(.vertical, 12)
                        }
                        .buttonStyle(.plain)
                    }
                }
            }
        }
    }

    private func connectUserSocketIfPossible() {
        guard let accessToken = authStore.currentAccessToken else {
            return
        }
        userSocket.onTextMessage = { text in
            Task {
                await model.handleUserWebSocketText(text, using: authStore)
            }
        }
        userSocket.connect(
            path: "/ws/user/",
            accessToken: accessToken,
            heartbeatEnabled: false
        )
    }

    private func refreshNotificationsWhileVisible() async {
        while !Task.isCancelled {
            do {
                try await Task.sleep(nanoseconds: 10_000_000_000)
            } catch {
                return
            }

            await model.loadNotifications(using: authStore)
            await model.loadRankedQueueStatuses(using: authStore)
        }
    }

    private func openNewGame() {
        if !path.isEmpty {
            path.removeLast()
        }

        path.append(DashboardRoute.newGame)
    }

    private func openRankedQueueNotification(queueId: Int) {
        model.gameMode = .pvp

        if let entry = model.queuedEntry(id: queueId) {
            path.append(DashboardRoute.rankedQueue(entry.ladderType, entry.deck.id))
            return
        }

        path.append(DashboardRoute.newGame)
    }

    private func applyInitialDashboardSectionIfNeeded() {
        #if DEBUG
        guard !appliedInitialDashboardSection else {
            return
        }
        appliedInitialDashboardSection = true

        if let gameId = AppConfig.initialGameId {
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.35) {
                path.append(DashboardRoute.game(gameId))
            }
            return
        }

        let section: DashboardSection?
        switch AppConfig.initialDashboardSection {
        case "collection":
            section = nil
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.35) {
                path.append(DashboardRoute.collection)
            }
        case "deck", "deck_detail", "deck-detail", "first_deck", "first-deck":
            section = nil
            let deckId = AppConfig.initialDeckId ?? model.selectedDeckId
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.35) {
                if let deckId {
                    path.append(DashboardRoute.deck(deckId))
                } else {
                    path.append(DashboardRoute.collection)
                }
            }
        case "games":
            section = nil
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.35) {
                path.append(DashboardRoute.games)
            }
        case "leaderboard":
            section = nil
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.35) {
                path.append(DashboardRoute.leaderboard)
            }
        case "friends":
            section = nil
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.35) {
                path.append(DashboardRoute.friends)
            }
        case "profile":
            section = nil
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.35) {
                path.append(DashboardRoute.profile)
            }
        case "how_to", "how-to", "howto":
            section = nil
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.35) {
                path.append(DashboardRoute.howTo)
            }
        case "new_game", "new-game", "newgame":
            section = nil
            model.gameMode = .pvp
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.35) {
                path.append(DashboardRoute.newGame)
            }
        case "new_game_ai", "new-game-ai", "new_game_pve", "new-game-pve", "pve_new_game", "pve-new-game":
            section = nil
            model.gameMode = .pve
            model.selectedOpponentId = nil
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.35) {
                path.append(DashboardRoute.newGame)
            }
        case "ranked_queue_daily", "ranked-queue-daily", "daily_queue", "daily-queue":
            section = nil
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.35) {
                path.append(DashboardRoute.rankedQueue(.daily, model.selectedDeckId))
            }
        case "ranked_queue_rapid", "ranked-queue-rapid", "rapid_queue", "rapid-queue":
            section = nil
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.35) {
                path.append(DashboardRoute.rankedQueue(.rapid, model.selectedDeckId))
            }
        case "scroll_how_to", "scroll-how-to", "scroll_howto", "scroll-howto":
            section = .howTo
        case "scroll_leaderboard", "scroll-leaderboard":
            section = .leaderboard
        default:
            section = nil
        }

        guard let section else {
            return
        }

        DispatchQueue.main.asyncAfter(deadline: .now() + 0.35) {
            dashboardScrollTarget = section
        }
        #endif
    }

    private func applyInitialProfileMenuIfNeeded() {
        #if DEBUG
        guard AppConfig.initialProfileMenuOpen else {
            return
        }

        DispatchQueue.main.asyncAfter(deadline: .now() + 0.45) {
            withAnimation(.easeOut(duration: 0.14)) {
                isProfileMenuOpen = true
            }
        }
        #endif
    }
}

private enum DashboardSection: Hashable {
    case leaderboard
    case howTo
}

private enum DashboardRoute: Hashable {
    case newGame
    case game(Int)
    case collection
    case games
    case leaderboard
    case friends
    case profile
    case rankedQueue(LadderType, Int?)
    case deck(Int)
    case howTo
}

private struct NewGameView: View {
    @EnvironmentObject private var authStore: AuthStore
    @ObservedObject var model: DashboardViewModel

    let openGame: (Int) -> Void
    let openRankedQueue: (LadderType, Int?) -> Void
    let openFriends: () -> Void

    var body: some View {
        ArchetypeScreen {
            ScrollView {
                VStack(spacing: 0) {
                    topBar
                        .padding(.horizontal, 16)
                        .padding(.top, 6)
                        .padding(.bottom, 16)

                    ArchetypePageBanner(title: "NEW GAME")

                    VStack(spacing: 24) {
                        GameModeToggle(selection: $model.gameMode)
                            .frame(maxWidth: 250)
                            .frame(maxWidth: .infinity)

                        statusMessages

                        deckPanel

                        if model.gameMode == .pve {
                            pvePanel
                        } else {
                            pvpPanel
                        }
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
        .onAppear {
            if model.gameMode == .pve {
                model.selectedOpponentId = nil
            }
            recordCaptureState()
        }
        .onChange(of: model.gameMode) { _, newMode in
            if newMode == .pve {
                model.selectedOpponentId = nil
            }
            recordCaptureState()
        }
    }

    private func recordCaptureState() {
        CaptureStateRecorder.record(model.gameMode == .pve ? "new-game-ai" : "new-game")
    }

    private var topBar: some View {
        ArchetypeTopBar {
            ArchetypeProfileLink(user: authStore.user) {
                ProfileView()
            }
        }
    }

    @ViewBuilder
    private var statusMessages: some View {
        if hasStatusMessages {
            VStack(spacing: 8) {
                if let error = model.errorMessage {
                    DashboardNotice(text: error, color: ArchetypeTheme.red)
                }

                if let error = model.rankedQueueErrorMessage {
                    DashboardNotice(text: error, color: ArchetypeTheme.red)
                }

                if let error = model.friendsErrorMessage {
                    DashboardNotice(text: error, color: ArchetypeTheme.red)
                }

                if let error = model.challengeErrorMessage {
                    DashboardNotice(text: error, color: ArchetypeTheme.red)
                }

                if let status = model.statusMessage {
                    DashboardNotice(text: status, color: ArchetypeTheme.green)
                }
            }
        }
    }

    private var hasStatusMessages: Bool {
        model.errorMessage != nil
            || model.rankedQueueErrorMessage != nil
            || model.friendsErrorMessage != nil
            || model.challengeErrorMessage != nil
            || model.statusMessage != nil
    }

    private var deckPanel: some View {
        ArchetypeWebPanel(title: "Your Deck", padding: 24) {
            if model.isLoading && model.decks.isEmpty {
                ProgressRow(text: "Loading your decks...")
            } else if model.decks.isEmpty {
                EmptyState(
                    title: "No decks found.",
                    detail: "Decks created on drawtwo.com appear here automatically.",
                    systemImage: "rectangle.stack.badge.plus"
                )
            } else {
                SelectionMenu(
                    title: "Your Deck",
                    value: model.selectedDeck?.name ?? "Choose deck",
                    detail: model.selectedDeck.map(deckDetail),
                    systemImage: "rectangle.stack.fill",
                    thumbnailURL: nil,
                    badgeText: model.selectedDeck.map(deckInitial),
                    options: model.decks.map { ($0.id, $0.name, deckDetail($0)) },
                    selectedId: $model.selectedDeckId
                )
            }
        }
        .frame(minHeight: 176)
    }

    private var pvePanel: some View {
        ArchetypeWebPanel(title: "Choose AI Opponent", padding: 24) {
            VStack(spacing: 12) {
                if model.isLoading && model.pveOpponents.isEmpty {
                    ProgressRow(text: "Loading AI opponents...")
                } else if model.pveOpponents.isEmpty {
                    EmptyState(
                        title: "No AI opponents found.",
                        detail: "AI decks published on drawtwo.com appear here automatically.",
                        systemImage: "cpu"
                    )
                } else {
                    ForEach(model.pveOpponents) { opponent in
                        Button {
                            model.selectedOpponentId = opponent.id
                        } label: {
                            PveOpponentRow(
                                opponent: opponent,
                                detail: deckDetail(opponent),
                                isSelected: opponent.id == model.selectedOpponentId
                            )
                        }
                        .buttonStyle(.plain)
                    }
                }

                Button {
                    Task {
                        if let gameId = await model.startPracticeGame(using: authStore) {
                            await model.load(using: authStore)
                            openGame(gameId)
                        }
                    }
                } label: {
                    Text(model.isLoading ? "Creating Game..." : "Create PvE Game")
                        .frame(maxWidth: .infinity)
                }
                .buttonStyle(WebActionButtonStyle(color: ArchetypeTheme.green600))
                .disabled(model.isLoading || model.selectedDeckId == nil || model.selectedOpponentId == nil)
            }
        }
    }

    private var pvpPanel: some View {
        ArchetypeWebPanel(padding: 24) {
            VStack(spacing: 12) {
                RankedQueueControls(
                    dailyQueueEntry: model.dailyQueueEntry,
                    rapidQueueEntry: model.rapidQueueEntry,
                    isLoading: model.isRankedQueueLoading,
                    canQueue: model.selectedDeckId != nil,
                    queue: { ladder in
                        Task {
                            let queued = await model.queueForRanked(ladder, using: authStore)
                            if queued && ladder == .rapid {
                                openRankedQueue(ladder, model.selectedDeckId)
                            }
                        }
                    },
                    leave: { ladder in
                        Task {
                            await model.leaveRankedQueue(ladder, using: authStore)
                        }
                    },
                    open: { ladder in
                        openRankedQueue(ladder, model.selectedDeckId)
                    }
                )

                NewGameDivider()

                NewGameSubsection(title: "Play a Friend", subtitle: "Unranked") {
                    if model.friends.isEmpty {
                        VStack(spacing: 12) {
                            EmptyState(
                                title: "No Friends Yet",
                                detail: "Add a friend before sending a friendly challenge.",
                                systemImage: "person.badge.plus"
                            )

                            Button {
                                openFriends()
                            } label: {
                                Label("Manage Friends", systemImage: "person.2.fill")
                                    .frame(maxWidth: .infinity)
                            }
                            .buttonStyle(SecondaryGameButtonStyle())
                        }
                    } else {
                        FriendChallengePickerRow(
                            friends: model.friends,
                            selectedFriend: model.selectedFriend,
                            selectedFriendId: $model.selectedFriendId,
                            challenge: model.selectedFriend.flatMap { model.outgoingChallenge(for: $0) },
                            isLoading: model.isFriendChallengeLoading,
                            canChallenge: model.selectedDeckId != nil && model.selectedFriendId != nil,
                            challengeAction: {
                                Task {
                                    await model.challengeSelectedFriend(using: authStore)
                                }
                            },
                            withdrawAction: { challenge in
                                Task {
                                    await model.cancelChallenge(challenge, using: authStore)
                                }
                            }
                        )
                    }
                }
            }
        }
    }

    private func deckDetail(_ deck: Deck) -> String {
        "\(deck.hero.name) • \(deck.cardCount ?? 0) cards"
    }

    private func deckInitial(_ deck: Deck) -> String {
        String(deck.name.prefix(1)).uppercased()
    }
}

private struct PveOpponentRow: View {
    let opponent: Deck
    let detail: String
    let isSelected: Bool

    var body: some View {
        HStack(spacing: 12) {
            Text("🤖")
                .font(.system(size: 16, weight: .bold))
                .frame(width: 40, height: 40)
                .background(Color(hex: 0xDCFCE7))
                .clipShape(RoundedRectangle(cornerRadius: ArchetypeTheme.controlRadius))

            VStack(alignment: .leading, spacing: 2) {
                Text(opponent.name)
                    .font(.archetypeBody(16, weight: .medium))
                    .foregroundStyle(ArchetypeTheme.text)
                    .lineLimit(1)

                Text(detail)
                    .font(.archetypeBody(14))
                    .foregroundStyle(ArchetypeTheme.muted)
                    .lineLimit(1)
            }

            Spacer()

            if isSelected {
                Image(systemName: "checkmark")
                    .font(.system(size: 14, weight: .bold))
                    .foregroundStyle(ArchetypeTheme.green600)
            }
        }
        .padding(16)
        .frame(minHeight: 74)
        .background(isSelected ? Color(hex: 0x14532D, alpha: 0.20) : Color.clear)
        .overlay(
            RoundedRectangle(cornerRadius: ArchetypeTheme.controlRadius)
                .stroke(isSelected ? ArchetypeTheme.green.opacity(0.82) : ArchetypeTheme.border, lineWidth: isSelected ? 2 : 1)
        )
        .clipShape(RoundedRectangle(cornerRadius: ArchetypeTheme.controlRadius))
    }
}

private struct TitleArtworkBanner: View {
    let title: Title?

    var body: some View {
        ZStack {
            if let artUrl = title?.resolvedArtUrl, let url = URL(string: artUrl) {
                AsyncImage(url: url) { phase in
                    switch phase {
                    case .success(let image):
                        image
                            .resizable()
                            .scaledToFit()
                    default:
                        heroFallback
                    }
                }
            } else {
                heroFallback
            }
        }
        .frame(height: 192)
        .frame(maxWidth: .infinity)
        .background(Color.clear)
        .clipped()
    }

    private var heroFallback: some View {
        ZStack {
            Color(hex: 0xD1D5DB)
            Text(title?.name ?? "Archetype")
                .font(.archetypeTitle(36))
                .foregroundStyle(Color(hex: 0x111827))
                .lineLimit(1)
                .minimumScaleFactor(0.72)
                .padding(.horizontal, 18)
        }
    }
}

private struct DashboardLinkButton: View {
    let title: String
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            Text(title)
                .font(.archetypeBody(18, weight: .bold))
                .foregroundStyle(ArchetypeTheme.text)
                .underline(pattern: .dot, color: ArchetypeTheme.muted)
                .lineLimit(1)
                .minimumScaleFactor(0.82)
                .frame(maxWidth: .infinity)
                .frame(minHeight: 52)
        }
        .buttonStyle(.plain)
    }
}

private struct ProfileMenuDropdown: View {
    @AppStorage("archetype.theme") private var themePreference = "dark"

    let signedInLabel: String
    let openProfile: () -> Void
    let openFriends: () -> Void
    let signOut: () -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            VStack(alignment: .leading, spacing: 3) {
                Text("Signed in as")
                    .font(.archetypeBody(12))
                    .foregroundStyle(ArchetypeTheme.muted)

                Text(signedInLabel)
                    .font(.archetypeBody(14, weight: .semibold))
                    .foregroundStyle(ArchetypeTheme.text)
                    .lineLimit(1)
            }
            .padding(.horizontal, 16)
            .padding(.vertical, 13)

            VStack(spacing: 4) {
                ProfileMenuRow(title: "Profile", action: openProfile)
                ProfileMenuRow(title: "Friends", action: openFriends)
            }
            .padding(.horizontal, 8)
            .padding(.bottom, 8)

            ProfileMenuThemeRow(
                isDark: themePreference != "light",
                toggleTheme: toggleTheme
            )
            .padding(.horizontal, 8)
            .padding(.bottom, 8)

            Divider()
                .overlay(ArchetypeTheme.border)
                .padding(.horizontal, 8)

            ProfileMenuRow(
                title: "Sign Out",
                tint: ArchetypeTheme.red,
                action: signOut
            )
            .padding(.horizontal, 8)
            .padding(.vertical, 0)
        }
        .frame(width: 260)
        .background(ArchetypeTheme.panel2)
        .overlay(
            RoundedRectangle(cornerRadius: 16)
                .stroke(ArchetypeTheme.border, lineWidth: 1)
        )
        .clipShape(RoundedRectangle(cornerRadius: 16))
        .shadow(color: Color.black.opacity(0.35), radius: 20, x: 0, y: 14)
    }

    private func toggleTheme() {
        themePreference = themePreference == "light" ? "dark" : "light"
    }
}

private struct ProfileMenuThemeRow: View {
    let isDark: Bool
    let toggleTheme: () -> Void

    var body: some View {
        HStack(spacing: 12) {
            Text("Light / Dark")
                .font(.archetypeBody(14, weight: .medium))
                .foregroundStyle(ArchetypeTheme.text)

            Spacer()

            Button(action: toggleTheme) {
                Image(systemName: isDark ? "sun.max" : "moon")
                    .font(.system(size: 15, weight: .medium))
                    .foregroundStyle(ArchetypeTheme.gold2)
                    .frame(width: 38, height: 38)
                    .background(ArchetypeTheme.panel)
                    .overlay(
                        RoundedRectangle(cornerRadius: 8)
                            .stroke(ArchetypeTheme.border, lineWidth: 1)
                    )
                    .clipShape(RoundedRectangle(cornerRadius: 8))
            }
            .buttonStyle(.plain)
            .accessibilityLabel("Toggle light and dark mode")
        }
        .padding(.leading, 16)
        .padding(.trailing, 10)
        .padding(.vertical, 10)
        .background(ArchetypeTheme.panel)
        .clipShape(RoundedRectangle(cornerRadius: 10))
    }
}

private struct ProfileMenuRow: View {
    let title: String
    var tint: Color = ArchetypeTheme.secondaryText
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            HStack(spacing: 10) {
                Text(title)
                    .font(.archetypeBody(14, weight: .medium))
                    .foregroundStyle(tint)

                Spacer()
            }
            .padding(.horizontal, 12)
            .padding(.vertical, 11)
            .background(Color.white.opacity(0.001))
            .clipShape(RoundedRectangle(cornerRadius: 12))
        }
        .buttonStyle(ProfileMenuButtonStyle())
    }
}

private struct ProfileMenuButtonStyle: ButtonStyle {
    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .background(configuration.isPressed ? ArchetypeTheme.pressedSurface : Color.clear)
            .scaleEffect(configuration.isPressed ? 0.99 : 1)
    }
}

private struct DashboardNotice: View {
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

private struct LeaderboardHeader: View {
    let selected: LadderType
    let isLoading: Bool
    let action: (LadderType) -> Void

    var body: some View {
        HStack(alignment: .center) {
            Text("Ladder")
                .font(.archetypeDisplay(24, weight: .bold))
                .foregroundStyle(Color(hex: 0xE5E7EB))

            Spacer()

            LadderToggle(selected: selected, isLoading: isLoading, action: action)
        }
        .padding(.bottom, 6)
        .overlay(alignment: .bottom) {
            Rectangle()
                .fill(ArchetypeTheme.border)
                .frame(height: 1)
        }
    }
}

private struct LadderToggle: View {
    let selected: LadderType
    let isLoading: Bool
    let action: (LadderType) -> Void

    var body: some View {
        HStack(spacing: 6) {
            ForEach(LadderType.allCases) { ladder in
                Button {
                    action(ladder)
                } label: {
                    Text(ladder.label)
                        .font(.archetypeBody(12, weight: .bold))
                        .foregroundStyle(selected == ladder ? Color(hex: 0x111827) : Color(hex: 0xD1D5DB))
                        .padding(.horizontal, 11)
                        .padding(.vertical, 7)
                        .background(selected == ladder ? Color.white : Color(hex: 0x374151))
                        .clipShape(Capsule())
                }
                .buttonStyle(.plain)
                .disabled(isLoading)
            }
        }
    }
}

private struct ProgressRow: View {
    let text: String

    var body: some View {
        HStack(spacing: 10) {
            ProgressView()
                .tint(ArchetypeTheme.gold2)

            Text(text)
                .font(.archetypeBody(13))
                .foregroundStyle(ArchetypeTheme.muted)
        }
        .frame(maxWidth: .infinity, alignment: .center)
        .padding(.vertical, 28)
        .padding(.horizontal, 16)
    }
}

private struct GameModeToggle: View {
    @Binding var selection: GameMode
    private let modes: [GameMode] = [.pvp, .pve]

    var body: some View {
        HStack(spacing: 4) {
            ForEach(modes) { mode in
                Button {
                    selection = mode
                } label: {
                    HStack(spacing: 8) {
                        Text(icon(for: mode))
                            .font(.system(size: 17, weight: .semibold))

                        Text(mode.label)
                            .font(.archetypeBody(14, weight: .semibold))
                    }
                    .foregroundStyle(selection == mode ? Color.white : Color(hex: 0xD1D5DB))
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, 10)
                    .background(selection == mode ? ArchetypeTheme.sky600 : Color.clear)
                    .clipShape(RoundedRectangle(cornerRadius: 6))
                }
                .buttonStyle(.plain)
            }
        }
        .padding(4)
        .background(ArchetypeTheme.panel)
        .overlay(
            RoundedRectangle(cornerRadius: ArchetypeTheme.controlRadius)
                .stroke(ArchetypeTheme.border, lineWidth: 1)
        )
        .clipShape(RoundedRectangle(cornerRadius: ArchetypeTheme.controlRadius))
    }

    private func icon(for mode: GameMode) -> String {
        switch mode {
        case .pvp:
            return "⚔️"
        case .pve:
            return "🤖"
        }
    }
}

private struct NewGameSubsection<Content: View>: View {
    let title: String
    var subtitle: String?
    let content: Content

    init(
        title: String,
        subtitle: String? = nil,
        @ViewBuilder content: () -> Content
    ) {
        self.title = title
        self.subtitle = subtitle
        self.content = content()
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 40) {
            VStack(alignment: .leading, spacing: 4) {
                Text(title)
                    .font(.archetypeBody(14, weight: .semibold))
                    .foregroundStyle(ArchetypeTheme.text)
                    .frame(height: 20)

                if let subtitle {
                    Text(subtitle)
                        .font(.archetypeBody(11))
                        .foregroundStyle(ArchetypeTheme.muted)
                        .frame(height: 16)
                }
            }
            .frame(maxWidth: .infinity, alignment: .center)

            content
        }
    }
}

private struct NewGameDivider: View {
    var body: some View {
        HStack(spacing: 10) {
            Text("or")
                .font(.archetypeBody(11, weight: .bold))
                .foregroundStyle(ArchetypeTheme.muted)
                .textCase(.uppercase)
        }
        .padding(.vertical, 8)
    }
}

private struct WebActionButtonStyle: ButtonStyle {
    @Environment(\.isEnabled) private var isEnabled
    let color: Color

    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .font(.archetypeBody(14, weight: .semibold))
            .foregroundStyle(isEnabled ? Color.white : Color(hex: 0x6B7280))
            .padding(.vertical, 11)
            .frame(minHeight: 44)
            .background(background(isPressed: configuration.isPressed))
            .clipShape(RoundedRectangle(cornerRadius: ArchetypeTheme.controlRadius))
            .scaleEffect(configuration.isPressed && isEnabled ? 0.98 : 1)
    }

    private func background(isPressed: Bool) -> Color {
        guard isEnabled else {
            return Color(hex: 0xD1D5DB)
        }

        return isPressed ? color.opacity(0.82) : color
    }
}

private struct RankedQueueControls: View {
    let dailyQueueEntry: RankedQueueEntry?
    let rapidQueueEntry: RankedQueueEntry?
    let isLoading: Bool
    let canQueue: Bool
    let queue: (LadderType) -> Void
    let leave: (LadderType) -> Void
    let open: (LadderType) -> Void

    var body: some View {
        VStack(spacing: 8) {
            VStack(spacing: 4) {
                Text("Ladder")
                    .font(.archetypeBody(14, weight: .semibold))
                    .foregroundStyle(ArchetypeTheme.text)
                    .frame(height: 20)
                Text("Ranked Matches")
                    .font(.archetypeBody(11))
                    .foregroundStyle(ArchetypeTheme.muted)
                    .frame(height: 16)
            }
            .frame(maxWidth: .infinity)
            .padding(.bottom, 8)

            Button {
                queue(.daily)
            } label: {
                Text("Play Daily (24h)")
                    .frame(maxWidth: .infinity)
            }
            .buttonStyle(WebActionButtonStyle(color: ArchetypeTheme.gold))
            .disabled(isLoading || !canQueue || hasQueueEntry)

            Button {
                queue(.rapid)
            } label: {
                Text("Play Rapid (1 min)")
                    .frame(maxWidth: .infinity)
            }
            .buttonStyle(WebActionButtonStyle(color: ArchetypeTheme.sky600))
            .disabled(isLoading || !canQueue || hasQueueEntry)

            if isLoading {
                HStack(spacing: 8) {
                    ProgressView()
                        .tint(ArchetypeTheme.gold2)
                    Text("Checking ranked queue status...")
                        .font(.archetypeBody(12))
                        .foregroundStyle(ArchetypeTheme.muted)
                }
                .padding(.top, 2)
            }

            if let rapidQueueEntry {
                QueueStatusRow(
                    ladder: .rapid,
                    entry: rapidQueueEntry,
                    leave: leave,
                    open: open
                )
            }

            if let dailyQueueEntry {
                QueueStatusRow(
                    ladder: .daily,
                    entry: dailyQueueEntry,
                    leave: leave,
                    open: open
                )
            }
        }
        .padding(.top, 0)
    }

    private var hasQueueEntry: Bool {
        dailyQueueEntry != nil || rapidQueueEntry != nil
    }
}

private struct QueueStatusRow: View {
    let ladder: LadderType
    let entry: RankedQueueEntry
    let leave: (LadderType) -> Void
    let open: (LadderType) -> Void

    var body: some View {
        VStack(spacing: 2) {
            Text("\(ladder.label) queued with \(entry.deck.name).")
                .font(.archetypeBody(11))
                .foregroundStyle(Color(hex: 0x4B5563))
                .multilineTextAlignment(.center)

            HStack(spacing: 8) {
                Button {
                    leave(ladder)
                } label: {
                    Text("Leave queue")
                        .lineLimit(2)
                        .multilineTextAlignment(.center)
                        .frame(width: 44)
                }
                .buttonStyle(QueueTextButtonStyle(tint: ArchetypeTheme.gold2))

                if ladder == .rapid {
                    Button {
                        open(ladder)
                    } label: {
                        Text("View status")
                    }
                    .buttonStyle(QueueTextButtonStyle(tint: ArchetypeTheme.muted))
                } else {
                    Text("You can leave this page and stay queued.")
                        .font(.archetypeBody(10))
                        .foregroundStyle(ArchetypeTheme.muted)
                        .lineLimit(2)
                        .fixedSize(horizontal: false, vertical: true)
                }
            }
            .frame(maxWidth: .infinity, alignment: .center)
        }
        .frame(maxWidth: .infinity, alignment: .center)
        .padding(.top, 0)
    }
}

private struct QueueTextButtonStyle: ButtonStyle {
    let tint: Color

    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .font(.archetypeBody(10, weight: .medium))
            .foregroundStyle(configuration.isPressed ? tint.opacity(0.72) : tint)
            .padding(.horizontal, 2)
            .padding(.vertical, 2)
    }
}

private struct FriendlyChallengeStatusRow: View {
    let challenge: FriendlyChallenge
    let isLoading: Bool
    let cancel: () -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack(spacing: 10) {
                Image(systemName: "paperplane.fill")
                    .font(.system(size: 15, weight: .bold))
                    .foregroundStyle(ArchetypeTheme.sky)
                    .frame(width: 34, height: 34)
                    .background(ArchetypeTheme.sky.opacity(0.16))
                    .clipShape(RoundedRectangle(cornerRadius: ArchetypeTheme.controlRadius))

                VStack(alignment: .leading, spacing: 3) {
                    Text("Challenge pending for \(challenge.challengee.displayName).")
                        .font(.archetypeBody(13, weight: .semibold))
                        .foregroundStyle(Color(hex: 0xD1D5DB))
                    Text("\(challenge.challengerDeck.name) - \(challenge.challengerDeck.hero)")
                        .font(.archetypeBody(12))
                        .foregroundStyle(ArchetypeTheme.muted)
                        .lineLimit(1)
                }

                Spacer(minLength: 8)
            }

            Button {
                cancel()
            } label: {
                Text(isLoading ? "Withdrawing..." : "Withdraw Challenge")
                    .frame(maxWidth: .infinity)
            }
            .buttonStyle(SecondaryGameButtonStyle())
            .disabled(isLoading)
            .opacity(isLoading ? 0.55 : 1)
        }
        .padding(12)
        .background(Color.white.opacity(0.05))
        .clipShape(RoundedRectangle(cornerRadius: ArchetypeTheme.controlRadius))
    }
}

private struct FriendChallengePickerRow: View {
    let friends: [Friendship]
    let selectedFriend: Friendship?
    @Binding var selectedFriendId: Int?
    let challenge: FriendlyChallenge?
    let isLoading: Bool
    let canChallenge: Bool
    let challengeAction: () -> Void
    let withdrawAction: (FriendlyChallenge) -> Void

    var body: some View {
        HStack(spacing: 10) {
            friendPicker

            Spacer(minLength: 6)

            if let challenge {
                Button {
                    withdrawAction(challenge)
                } label: {
                    Text(isLoading ? "Withdrawing..." : "Withdraw")
                }
                .buttonStyle(WebOutlineButtonStyle(tint: ArchetypeTheme.gold2))
                .disabled(isLoading)
            } else {
                Button {
                    challengeAction()
                } label: {
                    Text(isLoading ? "Sending..." : "Challenge")
                }
                .buttonStyle(WebOutlineButtonStyle(tint: ArchetypeTheme.sky))
                .disabled(isLoading || !canChallenge)
            }
        }
        .padding(10)
        .background(Color.white.opacity(0.03))
        .overlay(
            RoundedRectangle(cornerRadius: ArchetypeTheme.controlRadius)
                .stroke(ArchetypeTheme.sky.opacity(0.76), lineWidth: 1)
        )
        .clipShape(RoundedRectangle(cornerRadius: ArchetypeTheme.controlRadius))
    }

    @ViewBuilder
    private var friendPicker: some View {
        if friends.count > 1 {
            Menu {
                ForEach(friends, id: \.id) { friend in
                    Button {
                        selectedFriendId = friend.friendData.id
                    } label: {
                        Text(friend.friendData.displayLabel)
                    }
                }
            } label: {
                HStack(spacing: 6) {
                    friendText
                    Image(systemName: "chevron.up.chevron.down")
                        .font(.system(size: 10, weight: .bold))
                        .foregroundStyle(ArchetypeTheme.muted)
                }
            }
        } else {
            friendText
        }
    }

    private var friendText: some View {
        VStack(alignment: .leading, spacing: 2) {
            Text(selectedFriend?.friendData.displayLabel ?? "Choose friend")
                .font(.archetypeBody(14, weight: .semibold))
                .foregroundStyle(ArchetypeTheme.text)
                .lineLimit(1)

            if let username = selectedFriend?.friendData.username, !username.isEmpty {
                Text(username)
                    .font(.archetypeBody(11))
                    .foregroundStyle(ArchetypeTheme.muted)
                    .lineLimit(1)
            }
        }
    }
}

private struct WebOutlineButtonStyle: ButtonStyle {
    @Environment(\.isEnabled) private var isEnabled
    let tint: Color

    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .font(.archetypeBody(12, weight: .medium))
            .foregroundStyle(isEnabled ? tint : ArchetypeTheme.muted)
            .padding(.horizontal, 12)
            .padding(.vertical, 8)
            .background(tint.opacity(configuration.isPressed && isEnabled ? 0.18 : 0.05))
            .overlay(
                RoundedRectangle(cornerRadius: 7)
                    .stroke(isEnabled ? tint.opacity(0.85) : ArchetypeTheme.border, lineWidth: 1)
            )
            .clipShape(RoundedRectangle(cornerRadius: 7))
            .scaleEffect(configuration.isPressed && isEnabled ? 0.98 : 1)
    }
}

private struct NotificationRow: View {
    let notification: TitleNotification
    let isActionLoading: Bool
    let canAcceptChallenge: Bool
    let openGame: (Int) -> Void
    let openQueue: (Int) -> Void
    let openFriends: () -> Void
    let accept: () -> Void
    let decline: () -> Void

    var body: some View {
        VStack(spacing: 12) {
            if notification.type == "game_challenge" {
                HStack(alignment: .center, spacing: 12) {
                    Text(notification.message)
                        .font(.archetypeBody(16))
                        .foregroundStyle(Color(hex: 0xD1D5DB))
                        .multilineTextAlignment(.leading)
                        .frame(maxWidth: .infinity, alignment: .leading)

                    VStack(spacing: 8) {
                        Button {
                            accept()
                        } label: {
                            Text(isActionLoading ? "Accepting..." : "Accept")
                                .frame(width: 94)
                        }
                        .buttonStyle(NotificationActionButtonStyle(kind: .primary))
                        .disabled(isActionLoading || !canAcceptChallenge)
                        .opacity(isActionLoading || !canAcceptChallenge ? 0.55 : 1)

                        Button {
                            decline()
                        } label: {
                            Text(isActionLoading ? "Declining..." : "Decline")
                                .frame(width: 94)
                        }
                        .buttonStyle(NotificationActionButtonStyle(kind: .secondary))
                        .disabled(isActionLoading)
                        .opacity(isActionLoading ? 0.55 : 1)
                    }
                }
            } else {
                Button {
                    handleTap()
                } label: {
                    HStack(spacing: 12) {
                        Text(notification.emoji)
                            .font(.system(size: 24))
                            .frame(width: 40, height: 40)
                            .background(Color(hex: 0xE0F2FE))
                            .clipShape(RoundedRectangle(cornerRadius: ArchetypeTheme.controlRadius))

                        Text(notification.message)
                            .font(.archetypeBody(16))
                            .foregroundStyle(notification.isUserTurn == true ? ArchetypeTheme.text : Color(hex: 0xD1D5DB))
                            .multilineTextAlignment(.leading)
                            .frame(maxWidth: .infinity, alignment: .leading)
                    }
                }
                .buttonStyle(.plain)
            }
        }
        .padding(14)
        .background(rowBackground)
        .overlay(
            RoundedRectangle(cornerRadius: ArchetypeTheme.controlRadius)
                .stroke(rowBorder, lineWidth: 1)
        )
        .clipShape(RoundedRectangle(cornerRadius: ArchetypeTheme.controlRadius))
    }

    private var rowBorder: Color {
        notification.isUserTurn == true ? Color(hex: 0x92400E) : Color(hex: 0x075985)
    }

    private var rowBackground: Color {
        notification.isUserTurn == true ? Color(hex: 0x451A03) : Color(hex: 0x082F49)
    }

    private func handleTap() {
        if notification.isGameNotification {
            openGame(notification.refId)
        } else if notification.type == "game_ranked_queued" {
            openQueue(notification.refId)
        } else if notification.type == "friend_request" {
            openFriends()
        }
    }
}

private enum NotificationActionButtonKind {
    case primary
    case secondary
}

private struct NotificationActionButtonStyle: ButtonStyle {
    let kind: NotificationActionButtonKind

    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .font(.archetypeBody(13, weight: .medium))
            .foregroundStyle(foreground)
            .frame(height: 38)
            .background(background(isPressed: configuration.isPressed))
            .overlay(
                RoundedRectangle(cornerRadius: ArchetypeTheme.controlRadius)
                    .stroke(border, lineWidth: kind == .secondary ? 1 : 0)
            )
            .clipShape(RoundedRectangle(cornerRadius: ArchetypeTheme.controlRadius))
            .scaleEffect(configuration.isPressed ? 0.98 : 1)
    }

    private var foreground: Color {
        switch kind {
        case .primary:
            return .white
        case .secondary:
            return Color(hex: 0x38BDF8)
        }
    }

    private var border: Color {
        switch kind {
        case .primary:
            return .clear
        case .secondary:
            return Color(hex: 0x0284C7)
        }
    }

    private func background(isPressed: Bool) -> Color {
        switch kind {
        case .primary:
            return isPressed ? Color(hex: 0x0369A1) : Color(hex: 0x0284C7)
        case .secondary:
            return isPressed ? Color(hex: 0x0C4A6E).opacity(0.64) : Color.clear
        }
    }
}

private struct SkyGameButtonStyle: ButtonStyle {
    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .font(.archetypeBody(15, weight: .semibold))
            .foregroundStyle(Color.white)
            .frame(maxWidth: .infinity)
            .padding(.vertical, 13)
            .background(configuration.isPressed ? Color(hex: 0x0284C7) : ArchetypeTheme.sky)
            .clipShape(RoundedRectangle(cornerRadius: ArchetypeTheme.controlRadius))
            .scaleEffect(configuration.isPressed ? 0.98 : 1)
    }
}

private struct LeaderboardRow: View {
    let rank: Int
    let player: LeaderboardPlayer

    var body: some View {
        HStack(spacing: 12) {
            Text("\(rank)")
                .font(.archetypeBody(15, weight: .semibold))
                .foregroundStyle(ArchetypeTheme.muted)
                .frame(width: 28, alignment: .leading)

            VStack(alignment: .leading, spacing: 3) {
                Text(player.displayName)
                    .font(.archetypeBody(17, weight: .bold))
                    .foregroundStyle(ArchetypeTheme.text)
                    .lineLimit(1)

                Text("\(player.wins)W / \(player.losses)L / \(player.totalGames) games")
                    .font(.archetypeBody(12))
                    .foregroundStyle(ArchetypeTheme.muted)
            }

            Spacer()

            Text(verbatim: "[ \(String(player.eloRating)) ]")
                .font(.archetypeBody(15, weight: .medium))
                .foregroundStyle(ArchetypeTheme.muted)
        }
        .padding(14)
    }
}

private struct SelectionMenu: View {
    let title: String
    let value: String
    let detail: String?
    let systemImage: String
    let thumbnailURL: String?
    let badgeText: String?
    let options: [(id: Int, title: String, detail: String)]
    @Binding var selectedId: Int?

    var body: some View {
        Menu {
            ForEach(options, id: \.id) { option in
                Button {
                    selectedId = option.id
                } label: {
                    Text("\(option.title) - \(option.detail)")
                }
            }
        } label: {
            HStack(spacing: 12) {
                SelectionThumbnail(
                    systemImage: systemImage,
                    tint: tint,
                    thumbnailURL: thumbnailURL,
                    badgeText: badgeText
                )

                VStack(alignment: .leading, spacing: 2) {
                    Text(value)
                        .font(.archetypeBody(16, weight: .medium))
                        .foregroundStyle(ArchetypeTheme.text)
                        .lineLimit(1)
                    if let detail {
                        Text(detail)
                            .font(.archetypeBody(14))
                            .foregroundStyle(ArchetypeTheme.muted)
                            .lineLimit(2)
                    }
                }

                Spacer()

                Image(systemName: selectedId == nil ? "chevron.up.chevron.down" : "checkmark")
                    .font(.system(size: 13, weight: .bold))
                    .foregroundStyle(selectedId == nil ? ArchetypeTheme.muted : tint)
            }
            .padding(16)
            .frame(minHeight: 80)
            .background(selectedId == nil ? ArchetypeTheme.panel : selectedBackground)
            .overlay(
                RoundedRectangle(cornerRadius: ArchetypeTheme.controlRadius)
                    .stroke(selectedId == nil ? ArchetypeTheme.border : tint.opacity(0.82), lineWidth: 2)
            )
            .clipShape(RoundedRectangle(cornerRadius: ArchetypeTheme.controlRadius))
        }
    }

    private var tint: Color {
        title == "Opponent" ? ArchetypeTheme.green : ArchetypeTheme.sky
    }

    private var selectedBackground: Color {
        title == "Opponent"
            ? Color(hex: 0x14532D, alpha: 0.20)
            : Color(hex: 0x0C4A6E, alpha: 0.20)
    }
}

private struct SelectionThumbnail: View {
    let systemImage: String
    let tint: Color
    let thumbnailURL: String?
    let badgeText: String?

    var body: some View {
        ZStack {
            RoundedRectangle(cornerRadius: ArchetypeTheme.controlRadius)
                .fill(badgeText == nil ? tint.opacity(0.16) : Color(hex: 0xE0F2FE))

            if let thumbnailURL, let url = URL(string: thumbnailURL) {
                AsyncImage(url: url) { phase in
                    switch phase {
                    case .success(let image):
                        image
                            .resizable()
                            .scaledToFill()
                    default:
                        fallbackIcon
                    }
                }
            } else {
                fallbackIcon
            }
        }
        .frame(width: 40, height: 40)
        .clipShape(RoundedRectangle(cornerRadius: ArchetypeTheme.controlRadius))
        .overlay(
            RoundedRectangle(cornerRadius: ArchetypeTheme.controlRadius)
                .stroke(badgeText == nil ? tint.opacity(0.36) : Color.clear, lineWidth: 1)
        )
    }

    private var fallbackIcon: some View {
        Group {
            if let badgeText {
                Text(badgeText)
                    .font(.archetypeBody(12, weight: .bold))
                    .foregroundStyle(tint)
            } else {
                Image(systemName: systemImage)
                    .font(.system(size: 15, weight: .black))
                    .foregroundStyle(tint)
            }
        }
    }
}
