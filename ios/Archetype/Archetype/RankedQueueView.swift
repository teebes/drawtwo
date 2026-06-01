import SwiftUI

@MainActor
final class RankedQueueViewModel: ObservableObject {
    @Published var queueEntry: RankedQueueEntry?
    @Published var inQueue = false
    @Published var isLoading = false
    @Published var isLeaving = false
    @Published var isRequeueing = false
    @Published var timedOut = false
    @Published var elapsedSeconds = 0
    @Published var errorMessage: String?
    @Published var statusMessage: String?
    @Published var matchedGameId: Int?

    let ladder: LadderType
    let deckId: Int?

    private let queueTimeoutSeconds = 60
    private var timerTask: Task<Void, Never>?
    private var pollTask: Task<Void, Never>?

    init(ladder: LadderType, deckId: Int?) {
        self.ladder = ladder
        self.deckId = deckId
    }

    var isDaily: Bool {
        ladder == .daily
    }

    var formattedElapsedTime: String {
        let minutes = elapsedSeconds / 60
        let seconds = elapsedSeconds % 60
        return "\(minutes):\(String(format: "%02d", seconds))"
    }

    var remainingSeconds: Int {
        max(0, queueTimeoutSeconds - elapsedSeconds)
    }

    var progress: Double {
        min(Double(elapsedSeconds) / Double(queueTimeoutSeconds), 1)
    }

    func start(using authStore: AuthStore) async {
        stopLoops()
        isLoading = true
        errorMessage = nil
        statusMessage = nil

        await refreshStatus(using: authStore)
        isLoading = false

        if inQueue {
            startLoops(using: authStore)
        } else if errorMessage == nil {
            errorMessage = "You are not currently in the \(ladder.label.lowercased()) queue."
        }
    }

    func refreshStatus(using authStore: AuthStore) async {
        do {
            let response: RankedQueueStatusResponse = try await authStore.authenticatedGet(
                "/gameplay/matchmaking/status/\(AppConfig.titleSlug)/",
                queryItems: [URLQueryItem(name: "ladder_type", value: ladder.rawValue)]
            )

            if let error = response.error {
                errorMessage = error
            }

            inQueue = response.inQueue
            queueEntry = response.queueEntry

            if response.inQueue {
                syncElapsedTimeFromQueueEntry()
                if !isDaily && elapsedSeconds >= queueTimeoutSeconds {
                    timedOut = true
                    stopLoops()
                    await leaveQueueAfterTimeout(using: authStore)
                    return
                }
            }

            if !response.inQueue && !timedOut {
                stopLoops()
                await openLatestRankedGameIfAvailable(using: authStore)
            }
        } catch {
            if queueEntry == nil {
                errorMessage = error.localizedDescription
            }
        }
    }

    func leaveQueue(using authStore: AuthStore) async -> Bool {
        isLeaving = true
        errorMessage = nil
        statusMessage = nil

        do {
            let _: JSONValue = try await authStore.authenticatedPost(
                "/gameplay/matchmaking/leave/\(AppConfig.titleSlug)/",
                queryItems: [URLQueryItem(name: "ladder_type", value: ladder.rawValue)],
                body: EmptyBody()
            )
            stopLoops()
            inQueue = false
            queueEntry = nil
            statusMessage = "Left matchmaking queue."
            isLeaving = false
            return true
        } catch {
            errorMessage = error.localizedDescription
            isLeaving = false
            return false
        }
    }

    func requeue(using authStore: AuthStore) async {
        guard let deckId else {
            errorMessage = "No deck selected for requeue."
            return
        }

        isRequeueing = true
        errorMessage = nil
        statusMessage = nil

        do {
            let entry: RankedQueueEntry = try await authStore.authenticatedPost(
                "/gameplay/matchmaking/queue/",
                body: RankedQueueRequest(deckId: deckId, ladderType: ladder)
            )
            queueEntry = entry
            inQueue = true
            timedOut = false
            syncElapsedTimeFromQueueEntry()
            statusMessage = "Requeued for \(ladder.label.lowercased()) ranked."
            await refreshStatus(using: authStore)
            startLoops(using: authStore)
        } catch {
            errorMessage = error.localizedDescription
        }

        isRequeueing = false
    }

    func handleWebSocketText(_ text: String) {
        guard
            let data = text.data(using: .utf8),
            let payload = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
            payload["type"] as? String == "matchmaking_success",
            payload["title_slug"] as? String == AppConfig.titleSlug,
            let gameId = payload["game_id"] as? Int
        else {
            return
        }

        stopLoops()
        matchedGameId = gameId
    }

    func stopLoops() {
        timerTask?.cancel()
        timerTask = nil
        pollTask?.cancel()
        pollTask = nil
    }

    private func startLoops(using authStore: AuthStore) {
        stopLoops()

        pollTask = Task { [weak self] in
            while !Task.isCancelled {
                do {
                    try await Task.sleep(nanoseconds: 3_000_000_000)
                } catch {
                    return
                }
                await self?.refreshStatus(using: authStore)
            }
        }

        guard !isDaily else {
            return
        }

        timerTask = Task { [weak self] in
            while !Task.isCancelled {
                do {
                    try await Task.sleep(nanoseconds: 1_000_000_000)
                } catch {
                    return
                }
                await self?.tick(using: authStore)
            }
        }
    }

    private func tick(using authStore: AuthStore) async {
        if queueEntry?.queuedAt != nil {
            syncElapsedTimeFromQueueEntry()
        } else {
            elapsedSeconds += 1
        }

        guard elapsedSeconds >= queueTimeoutSeconds else {
            return
        }

        timedOut = true
        stopLoops()
        await leaveQueueAfterTimeout(using: authStore)
    }

    private func leaveQueueAfterTimeout(using authStore: AuthStore) async {
        do {
            let _: JSONValue = try await authStore.authenticatedPost(
                "/gameplay/matchmaking/leave/\(AppConfig.titleSlug)/",
                queryItems: [URLQueryItem(name: "ladder_type", value: ladder.rawValue)],
                body: EmptyBody()
            )
        } catch {
            errorMessage = error.localizedDescription
        }

        inQueue = false
        queueEntry = nil
    }

    private func syncElapsedTimeFromQueueEntry(now: Date = Date()) {
        guard !isDaily, let queuedAt = queueEntry?.queuedAt else {
            return
        }

        #if DEBUG
        if let override = AppConfig.queueElapsedSecondsOverride {
            elapsedSeconds = min(max(override, 0), queueTimeoutSeconds)
            return
        }
        #endif

        guard let queuedDate = Self.date(fromQueueTimestamp: queuedAt) else {
            return
        }

        let elapsed = Int(now.timeIntervalSince(queuedDate))
        elapsedSeconds = min(max(elapsed, 0), queueTimeoutSeconds)
    }

    private static func date(fromQueueTimestamp timestamp: String) -> Date? {
        let fractionalFormatter = ISO8601DateFormatter()
        fractionalFormatter.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        if let date = fractionalFormatter.date(from: timestamp) {
            return date
        }

        let formatter = ISO8601DateFormatter()
        formatter.formatOptions = [.withInternetDateTime]
        return formatter.date(from: timestamp)
    }

    private func openLatestRankedGameIfAvailable(using authStore: AuthStore) async {
        do {
            let response: GameListResponse = try await authStore.authenticatedGet(
                "/titles/\(AppConfig.titleSlug)/games/"
            )
            if let game = response.games.first(where: { $0.type == "ranked" }) {
                matchedGameId = game.id
            }
        } catch {
            statusMessage = "Queue ended. Refresh games from the dashboard."
        }
    }
}

struct RankedQueueView: View {
    @EnvironmentObject private var authStore: AuthStore
    @Environment(\.dismiss) private var dismiss
    @Environment(\.scenePhase) private var scenePhase
    @StateObject private var model: RankedQueueViewModel
    @StateObject private var socket = DrawTwoWebSocket()
    @State private var pulse = false

    private let onOpenGame: (Int) -> Void

    init(
        ladder: LadderType,
        deckId: Int?,
        onOpenGame: @escaping (Int) -> Void
    ) {
        _model = StateObject(
            wrappedValue: RankedQueueViewModel(ladder: ladder, deckId: deckId)
        )
        self.onOpenGame = onOpenGame
    }

    var body: some View {
        ArchetypeScreen {
            ScrollView {
                VStack(spacing: 0) {
                    topBar
                        .padding(.horizontal, 18)
                        .padding(.top, 6)
                        .padding(.bottom, 16)

                    ArchetypePageBanner(
                        title: "\(model.ladder.label.uppercased()) QUEUE",
                        foregroundColor: ArchetypeTheme.text
                    )

                    VStack(spacing: 18) {
                        content
                    }
                    .frame(maxWidth: 640)
                    .padding(.horizontal, 18)
                    .padding(.top, 32)
                    .padding(.bottom, 36)
                }
            }
            .refreshable {
                await model.refreshStatus(using: authStore)
            }
        }
        .toolbar(.hidden, for: .navigationBar)
        .navigationBarBackButtonHidden(true)
        .task {
            await model.start(using: authStore)
            recordCaptureState()
            connectSocketIfPossible()
            #if DEBUG
            if AppConfig.visualCaptureModeEnabled {
                pulse = false
                return
            }
            #endif
            withAnimation(.easeInOut(duration: 1.2).repeatForever(autoreverses: true)) {
                pulse = true
            }
        }
        .onChange(of: model.matchedGameId) { _, gameId in
            guard let gameId else {
                return
            }
            onOpenGame(gameId)
        }
        .onChange(of: model.inQueue) { _, _ in
            recordCaptureState()
        }
        .onDisappear {
            model.stopLoops()
            socket.disconnect()
        }
        .onChange(of: scenePhase) { _, phase in
            guard phase == .active else {
                return
            }
            Task {
                await model.refreshStatus(using: authStore)
                recordCaptureState()
                connectSocketIfPossible()
            }
        }
    }

    private func recordCaptureState() {
        CaptureStateRecorder.record("ranked-queue-\(model.ladder.rawValue)")
    }

    private var topBar: some View {
        ArchetypeTopBar {
            ArchetypeProfileLink(user: authStore.user) {
                ProfileView()
            }
        }
    }

    @ViewBuilder
    private var content: some View {
        if model.isLoading {
            ArchetypeWebPanel {
                RankedQueueProgressRow(text: "Loading queue status...")
            }
        } else if model.timedOut && !model.isDaily {
            timeoutPanel
        } else if model.inQueue, let entry = model.queueEntry {
            queuePanel(entry: entry)
        } else {
            notQueuedPanel
        }
    }

    private func queuePanel(entry: RankedQueueEntry) -> some View {
        VStack(spacing: 18) {
            searchingIcon

            Text("Searching for Opponent...")
                .font(.archetypeBody(23, weight: .bold))
                .foregroundStyle(ArchetypeTheme.text)
                .multilineTextAlignment(.center)

            VStack(spacing: 7) {
                QueueInfoLine(label: "Deck:", value: entry.deck.name)
                QueueInfoLine(label: "Your Rating:", value: "\(entry.eloRating)")
            }
            .padding(.bottom, 1)

            if model.isDaily {
                Text("You can leave this page and stay in the daily queue until a match is found.")
                    .font(.archetypeBody(14))
                    .foregroundStyle(ArchetypeTheme.muted)
                    .multilineTextAlignment(.center)
                    .frame(maxWidth: 320)
            } else {
                timerPanel
            }

            if let error = model.errorMessage {
                RankedQueueNotice(text: error, color: ArchetypeTheme.red)
            } else if let status = model.statusMessage {
                RankedQueueNotice(text: status, color: ArchetypeTheme.green)
            }

            Button {
                Task {
                    if await model.leaveQueue(using: authStore) {
                        dismiss()
                    }
                }
            } label: {
                Text(model.isLeaving ? "Leaving..." : "Leave Queue")
            }
            .buttonStyle(QueueWhiteButtonStyle())
            .disabled(model.isLeaving)
        }
        .frame(maxWidth: .infinity)
        .padding(.top, 0)
        .padding(.bottom, 48)
    }

    private var timeoutPanel: some View {
        VStack(spacing: 24) {
            Image(systemName: "clock.badge.exclamationmark")
                .font(.system(size: 72, weight: .regular))
                .foregroundStyle(ArchetypeTheme.muted)

            VStack(spacing: 12) {
                Text("Queue Timeout")
                    .font(.archetypeBody(24, weight: .bold))
                    .foregroundStyle(ArchetypeTheme.text)

                Text("No opponent found within 1 minute. Would you like to try again?")
                    .font(.archetypeBody(16))
                    .foregroundStyle(ArchetypeTheme.muted)
                    .multilineTextAlignment(.center)
                    .frame(maxWidth: 330)
            }

            if let error = model.errorMessage {
                RankedQueueNotice(text: error, color: ArchetypeTheme.red)
            }

            HStack(spacing: 12) {
                Button {
                    Task { await model.requeue(using: authStore) }
                } label: {
                    Text(model.isRequeueing ? "Requeueing..." : "Requeue")
                        .frame(maxWidth: .infinity)
                }
                .buttonStyle(PrimaryGameButtonStyle())
                .disabled(model.isRequeueing || model.deckId == nil)

                Button {
                    dismiss()
                } label: {
                    Text("Back to Game Setup")
                        .frame(maxWidth: .infinity)
                }
                .buttonStyle(QueueWhiteButtonStyle())
            }
        }
        .frame(maxWidth: .infinity)
        .padding(.vertical, 48)
    }

    private var notQueuedPanel: some View {
        VStack(spacing: 18) {
            Text(model.errorMessage ?? "You are not currently in the \(model.ladder.label.lowercased()) queue.")
                .font(.archetypeBody(16))
                .foregroundStyle(model.errorMessage == nil ? ArchetypeTheme.muted : ArchetypeTheme.red)
                .multilineTextAlignment(.center)

            Button {
                dismiss()
            } label: {
                Text("Back to Game Setup")
            }
            .buttonStyle(PrimaryGameButtonStyle())
        }
        .frame(maxWidth: .infinity)
        .padding(.vertical, 48)
    }

    private var searchingIcon: some View {
        ZStack {
            if showsSearchPulseRing {
                Circle()
                    .stroke(ArchetypeTheme.panel.opacity(pulse ? 0.22 : 0.48), lineWidth: 10)
                    .frame(width: pulse ? 144 : 112, height: pulse ? 144 : 112)
            }

            Image(systemName: "magnifyingglass")
                .font(.system(size: 96, weight: .regular))
                .foregroundStyle(ArchetypeTheme.gold)
                .opacity(pulse && showsSearchPulseRing ? 0.62 : 1)
        }
        .frame(height: 96)
    }

    private var showsSearchPulseRing: Bool {
        #if DEBUG
        !AppConfig.visualCaptureModeEnabled
        #else
        true
        #endif
    }

    private var timerPanel: some View {
        VStack(spacing: 8) {
            Text(model.formattedElapsedTime)
                .font(.archetypeBody(48, weight: .bold))
                .foregroundStyle(ArchetypeTheme.gold2)

            Text("Time in queue")
                .font(.archetypeBody(14))
                .foregroundStyle(ArchetypeTheme.muted)

            QueueTimeoutProgress(progress: model.progress)
                .padding(.top, 6)

            Text("Queue timeout in \(model.remainingSeconds)s")
                .font(.archetypeBody(12, weight: .medium))
                .foregroundStyle(ArchetypeTheme.muted)
        }
    }

    private func connectSocketIfPossible() {
        guard let accessToken = authStore.currentAccessToken else {
            return
        }

        socket.onTextMessage = { text in
            model.handleWebSocketText(text)
        }
        socket.connect(
            path: "/ws/user/",
            accessToken: accessToken,
            heartbeatEnabled: false
        )
    }
}

private struct QueueTimeoutProgress: View {
    let progress: Double

    var body: some View {
        GeometryReader { proxy in
            let clampedProgress = min(max(progress, 0), 1)

            ZStack(alignment: .leading) {
                Capsule()
                    .fill(Color(hex: 0x374151))

                Capsule()
                    .fill(ArchetypeTheme.gold2)
                    .frame(width: max(proxy.size.width * clampedProgress, 8))
            }
        }
        .frame(width: 320, height: 8)
        .frame(maxWidth: .infinity)
    }
}

private struct RankedQueueProgressRow: View {
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
        .padding(.vertical, 26)
    }
}

private struct QueueInfoLine: View {
    let label: String
    let value: String

    var body: some View {
        HStack(spacing: 4) {
            Text(label)
                .font(.archetypeBody(16))
                .foregroundStyle(ArchetypeTheme.muted)

            Text(value)
                .font(.archetypeBody(16, weight: .semibold))
                .foregroundStyle(ArchetypeTheme.text)
        }
        .frame(maxWidth: .infinity, alignment: .center)
    }
}

private struct QueueWhiteButtonStyle: ButtonStyle {
    @Environment(\.isEnabled) private var isEnabled

    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .font(.archetypeBody(14, weight: .medium))
            .foregroundStyle(isEnabled ? Color(hex: 0x374151) : Color(hex: 0x9CA3AF))
            .padding(.horizontal, 24)
            .padding(.vertical, 12)
            .background(isEnabled ? Color.white.opacity(configuration.isPressed ? 0.86 : 1) : Color(hex: 0xD1D5DB))
            .overlay(
                RoundedRectangle(cornerRadius: ArchetypeTheme.controlRadius)
                    .stroke(Color(hex: 0xD1D5DB), lineWidth: 1)
            )
            .clipShape(RoundedRectangle(cornerRadius: ArchetypeTheme.controlRadius))
            .scaleEffect(configuration.isPressed && isEnabled ? 0.98 : 1)
    }
}

private struct RankedQueueNotice: View {
    let text: String
    let color: Color

    var body: some View {
        Text(text)
            .font(.archetypeBody(12, weight: .medium))
            .foregroundStyle(color)
            .padding(11)
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(color.opacity(0.11))
            .clipShape(RoundedRectangle(cornerRadius: ArchetypeTheme.controlRadius))
    }
}
