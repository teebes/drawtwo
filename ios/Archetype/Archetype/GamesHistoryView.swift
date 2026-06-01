import SwiftUI

@MainActor
final class GamesHistoryViewModel: ObservableObject {
    @Published var stats = GameHistoryStats(
        ranked: GameHistoryRankedStats(total: 0, wins: 0, losses: 0),
        friendly: GameHistoryFriendlyStats(total: 0),
        currentRating: 1200,
        ladderType: .daily
    )
    @Published var games: [GameHistoryItem] = []
    @Published var pagination = GameHistoryPagination(
        page: 1,
        totalPages: 1,
        totalGames: 0,
        hasNext: false,
        hasPrevious: false
    )
    @Published var ladder: LadderType = .daily
    @Published var isLoading = false
    @Published var errorMessage: String?

    var currentRating: Int {
        stats.currentRating ?? 1200
    }

    func load(page: Int = 1, using authStore: AuthStore) async {
        isLoading = true
        errorMessage = nil

        do {
            let response: GameHistoryResponse = try await authStore.authenticatedGet(
                "/titles/\(AppConfig.titleSlug)/games/history/",
                queryItems: [
                    URLQueryItem(name: "page", value: "\(page)"),
                    URLQueryItem(name: "page_size", value: "20"),
                    URLQueryItem(name: "ladder_type", value: ladder.rawValue),
                ]
            )
            stats = response.stats
            games = response.games
            pagination = response.pagination
        } catch {
            errorMessage = error.localizedDescription
        }

        isLoading = false
    }

    func setLadder(_ ladder: LadderType, using authStore: AuthStore) async {
        guard self.ladder != ladder else {
            return
        }

        self.ladder = ladder
        await load(page: 1, using: authStore)
    }
}

struct GamesHistoryView: View {
    @EnvironmentObject private var authStore: AuthStore
    @StateObject private var model = GamesHistoryViewModel()

    let onOpenGame: (Int) -> Void
    let onNewGame: () -> Void

    var body: some View {
        ArchetypeScreen {
            ScrollView {
                VStack(spacing: 0) {
                    topBar
                        .padding(.horizontal, 18)
                        .padding(.top, 6)
                        .padding(.bottom, 16)

                    ArchetypePageBanner(title: "Games")

                    VStack(spacing: 32) {
                        statsPanel
                        newGameButton
                        gamesPanel
                        paginationControls
                    }
                    .padding(.horizontal, 16)
                    .padding(.top, 32)
                    .padding(.bottom, 32)
                }
            }
            .refreshable {
                await model.load(page: model.pagination.page, using: authStore)
            }
        }
        .toolbar(.hidden, for: .navigationBar)
        .navigationBarBackButtonHidden(true)
        .task {
            await model.load(using: authStore)
            CaptureStateRecorder.record("games")
        }
    }

    private var topBar: some View {
        ArchetypeTopBar {
            ArchetypeProfileLink(user: authStore.user) {
                ProfileView()
            }
        }
    }

    private var statsPanel: some View {
        VStack(spacing: 12) {
            HStack(spacing: 32) {
                ArchetypeWebPanel(padding: 24) {
                    VStack(spacing: 7) {
                        Text("Ranked Play")
                            .font(.archetypeBody(18, weight: .medium))
                            .foregroundStyle(ArchetypeTheme.gold2)

                        HistoryLadderToggle(selected: model.ladder, isLoading: model.isLoading) { ladder in
                            Task {
                                await model.setLadder(ladder, using: authStore)
                            }
                        }

                        Text("\(model.stats.ranked.wins)W - \(model.stats.ranked.losses)L")
                            .font(.archetypeBody(16, weight: .medium))
                            .foregroundStyle(ArchetypeTheme.text)

                        Text("[ " + String(model.currentRating) + " ]")
                            .font(.archetypeBody(13, weight: .medium))
                            .foregroundStyle(ArchetypeTheme.muted)
                    }
                    .frame(maxWidth: .infinity, minHeight: 124, alignment: .top)
                }

                ArchetypeWebPanel(padding: 24) {
                    VStack(spacing: 7) {
                        Text("Friendly Play")
                            .font(.archetypeBody(18, weight: .medium))
                            .foregroundStyle(ArchetypeTheme.sky)
                            .multilineTextAlignment(.center)
                            .frame(maxWidth: 96)

                        Text("\(model.stats.friendly.total) Games Played")
                            .font(.archetypeBody(16, weight: .medium))
                            .foregroundStyle(ArchetypeTheme.text)
                            .multilineTextAlignment(.center)
                            .frame(maxWidth: 112)
                    }
                    .frame(maxWidth: .infinity, minHeight: 124, alignment: .top)
                }
            }

            if let error = model.errorMessage {
                Text(error)
                    .font(.archetypeBody(12))
                    .foregroundStyle(ArchetypeTheme.red)
                    .padding(11)
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .background(ArchetypeTheme.red.opacity(0.11))
                    .clipShape(RoundedRectangle(cornerRadius: ArchetypeTheme.controlRadius))
            }
        }
    }

    private var newGameButton: some View {
        Button {
            onNewGame()
        } label: {
            Label("New Game", systemImage: "plus")
                .frame(maxWidth: .infinity)
        }
        .buttonStyle(DashedActionButtonStyle())
    }

    private var gamesPanel: some View {
        VStack(alignment: .leading, spacing: 10) {
            if model.isLoading && model.games.isEmpty {
                ArchetypeWebPanel(padding: 0) {
                    HistoryProgressRow(text: "Loading games...")
                }
            } else if model.games.isEmpty {
                ArchetypeWebPanel(padding: 0) {
                    EmptyState(
                        title: "No games yet.",
                        detail: "Play some games to see your history here.",
                        systemImage: "rectangle.stack"
                    )
                    .padding(.horizontal, 16)
                }
            } else {
                VStack(spacing: 10) {
                    ForEach(model.games) { game in
                        Button {
                            onOpenGame(game.id)
                        } label: {
                            GameHistoryRow(game: game)
                        }
                        .buttonStyle(.plain)
                    }
                }
            }
        }
    }

    @ViewBuilder
    private var paginationControls: some View {
        if model.pagination.totalPages > 1 {
            HStack(spacing: 12) {
                Button {
                    Task {
                        await model.load(page: max(1, model.pagination.page - 1), using: authStore)
                    }
                } label: {
                    Label("Previous", systemImage: "chevron.left")
                }
                .buttonStyle(SecondaryGameButtonStyle())
                .disabled(!model.pagination.hasPrevious || model.isLoading)
                .opacity(!model.pagination.hasPrevious || model.isLoading ? 0.55 : 1)

                Text("Page \(model.pagination.page) of \(model.pagination.totalPages)")
                    .font(.archetypeBody(13, weight: .medium))
                    .foregroundStyle(ArchetypeTheme.muted)
                    .frame(maxWidth: .infinity)

                Button {
                    Task {
                        await model.load(page: min(model.pagination.totalPages, model.pagination.page + 1), using: authStore)
                    }
                } label: {
                    Label("Next", systemImage: "chevron.right")
                }
                .buttonStyle(SecondaryGameButtonStyle())
                .disabled(!model.pagination.hasNext || model.isLoading)
                .opacity(!model.pagination.hasNext || model.isLoading ? 0.55 : 1)
            }
        }
    }
}

private struct HistoryLadderToggle: View {
    let selected: LadderType
    let isLoading: Bool
    let action: (LadderType) -> Void

    var body: some View {
        HStack(spacing: 6) {
            ForEach([LadderType.rapid, .daily]) { ladder in
                Button {
                    action(ladder)
                } label: {
                    Text(ladder.label)
                        .font(.archetypeBody(11, weight: .bold))
                        .foregroundStyle(selected == ladder ? Color(hex: 0x111827) : Color(hex: 0xD1D5DB))
                        .padding(.horizontal, 10)
                        .padding(.vertical, 6)
                        .background(selected == ladder ? Color.white : Color(hex: 0x374151))
                        .clipShape(Capsule())
                }
                .buttonStyle(.plain)
                .disabled(isLoading)
            }
        }
    }
}

private struct HistoryProgressRow: View {
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

private struct GameHistoryRow: View {
    let game: GameHistoryItem

    var body: some View {
        HStack(spacing: 8) {
            HStack(spacing: 4) {
                badge(text: typeLabel, color: typeColor, shape: .circle)

                if game.type == "ranked", let ladderType = game.ladderType {
                    smallBadge(text: ladderType == .rapid ? "R" : "D")
                }
            }

            if game.status == "ended", let outcome = game.outcome {
                badge(text: outcomeLabel(outcome), color: outcomeColor(outcome), shape: .circle)
            } else if game.status == "in_progress" {
                badge(
                    text: game.isUserTurn == true ? "→" : "...",
                    color: game.isUserTurn == true ? Color(hex: 0x3B82F6) : Color(hex: 0x6B7280),
                    shape: .circle
                )
            }

            VStack(alignment: .leading, spacing: 5) {
                opponentLine
                    .lineLimit(1)
                    .layoutPriority(1)

                Text(heroLine)
                    .font(.archetypeBody(12))
                    .foregroundStyle(ArchetypeTheme.muted)
                    .lineLimit(1)
            }
            .padding(.leading, 8)
            .layoutPriority(1)

            Spacer(minLength: 6)

            VStack(alignment: .trailing, spacing: 5) {
                if let eloChange = game.eloChange {
                    Text("\(eloChange > 0 ? "+" : "")\(eloChange)")
                        .font(.archetypeBody(14, weight: .bold))
                        .foregroundStyle(eloChange >= 0 ? Color(hex: 0x4ADE80) : Color(hex: 0xF87171))
                }

                Text(Self.relativeDate(game.createdAt))
                    .font(.archetypeBody(11, weight: .medium))
                    .foregroundStyle(ArchetypeTheme.muted)
            }
            .fixedSize(horizontal: true, vertical: false)
        }
        .padding(.horizontal, 12)
        .padding(.vertical, 11)
        .frame(minHeight: 64)
        .background(ArchetypeTheme.panel)
        .clipShape(RoundedRectangle(cornerRadius: ArchetypeTheme.surfaceRadius))
        .contentShape(Rectangle())
    }

    private var typeLabel: String {
        switch game.type {
        case "ranked":
            return "R"
        case "friendly":
            return "F"
        case "pve":
            return "AI"
        default:
            return String(game.type.prefix(2)).uppercased()
        }
    }

    private var typeColor: Color {
        switch game.type {
        case "ranked":
            return ArchetypeTheme.gold2
        case "friendly":
            return ArchetypeTheme.sky
        default:
            return Color(hex: 0x6B7280)
        }
    }

    private var heroLine: String {
        let userHero = game.userHero ?? "You"
        let opponentHero = game.opponentHero ?? "Opponent"
        return "\(userHero) vs \(opponentHero)"
    }

    private var opponentLine: Text {
        let base = Text("vs \(game.opponentName)")
            .font(.archetypeBody(14, weight: .medium))
            .foregroundColor(ArchetypeTheme.text)

        guard game.status == "in_progress" else {
            return base
        }

        let status = game.isUserTurn == true ? "(Your turn)" : "(Opponent's turn)"
        let color = game.isUserTurn == true ? Color(hex: 0x60A5FA) : ArchetypeTheme.muted
        return base + Text(" \(status)")
            .font(.archetypeBody(10, weight: .semibold))
            .foregroundColor(color)
    }

    private func outcomeLabel(_ outcome: String) -> String {
        switch outcome {
        case "win":
            return "W"
        case "loss":
            return "L"
        default:
            return "D"
        }
    }

    private func outcomeColor(_ outcome: String) -> Color {
        switch outcome {
        case "win":
            return ArchetypeTheme.green
        case "loss":
            return ArchetypeTheme.red
        default:
            return Color(hex: 0x6B7280)
        }
    }

    private enum BadgeShape {
        case circle
        case rounded
    }

    private func badge(text: String, color: Color, shape: BadgeShape) -> some View {
        Text(text)
            .font(.archetypeBody(11, weight: .bold))
            .foregroundStyle(.white)
            .frame(width: 32, height: 32)
            .background(color)
            .clipShape(RoundedRectangle(cornerRadius: shape == .circle ? 16 : 7))
    }

    private func smallBadge(text: String) -> some View {
        Text(text)
            .font(.archetypeBody(10, weight: .bold))
            .foregroundStyle(ArchetypeTheme.gold2)
            .frame(width: 24, height: 24)
            .background(Color(hex: 0x78350F))
            .clipShape(RoundedRectangle(cornerRadius: 6))
    }

    private static func relativeDate(_ value: String) -> String {
        guard let date = parseDate(value) else {
            return ""
        }

        let seconds = max(0, Int(Date().timeIntervalSince(date)))
        let minutes = seconds / 60
        let hours = seconds / 3_600
        let days = seconds / 86_400

        if minutes < 1 {
            return "Just now"
        } else if minutes < 60 {
            return "\(minutes)m ago"
        } else if hours < 24 {
            return "\(hours)h ago"
        } else if days < 7 {
            return "\(days)d ago"
        }

        return date.formatted(date: .abbreviated, time: .omitted)
    }

    private static func parseDate(_ value: String) -> Date? {
        let fractionalFormatter = ISO8601DateFormatter()
        fractionalFormatter.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        if let date = fractionalFormatter.date(from: value) {
            return date
        }

        let formatter = ISO8601DateFormatter()
        formatter.formatOptions = [.withInternetDateTime]
        return formatter.date(from: value)
    }
}
