import SwiftUI
import UIKit

@MainActor
final class LeaderboardViewModel: ObservableObject {
    @Published var players: [LeaderboardPlayer] = []
    @Published var ladder: LadderType = .daily
    @Published var isLoading = false
    @Published var errorMessage: String?

    func load(using authStore: AuthStore) async {
        isLoading = true
        errorMessage = nil

        do {
            players = try await authStore.authenticatedGet(
                "/gameplay/\(AppConfig.titleSlug)/leaderboard/",
                queryItems: [URLQueryItem(name: "ladder_type", value: ladder.rawValue)]
            )
        } catch {
            errorMessage = error.localizedDescription
            players = []
        }

        isLoading = false
    }

    func setLadder(_ ladder: LadderType, using authStore: AuthStore) async {
        guard self.ladder != ladder else {
            return
        }

        self.ladder = ladder
        await load(using: authStore)
    }
}

struct LeaderboardView: View {
    @EnvironmentObject private var authStore: AuthStore
    @StateObject private var model = LeaderboardViewModel()

    var body: some View {
        ArchetypeScreen {
            ScrollView {
                VStack(spacing: 0) {
                    topBar
                        .padding(.horizontal, 18)
                        .padding(.top, 6)
                        .padding(.bottom, 16)

                    ArchetypePageBanner(title: "Leaderboard")

                    VStack(spacing: 24) {
                        ladderToggle
                        leaderboardContent
                    }
                    .frame(maxWidth: 980)
                    .padding(.horizontal, 18)
                    .padding(.top, 64)
                    .padding(.bottom, 32)
                }
            }
            .refreshable {
                await model.load(using: authStore)
            }
        }
        .toolbar(.hidden, for: .navigationBar)
        .navigationBarBackButtonHidden(true)
        .task {
            await model.load(using: authStore)
            CaptureStateRecorder.record("leaderboard")
        }
    }

    private var topBar: some View {
        ArchetypeTopBar {
            ArchetypeProfileLink(user: authStore.user) {
                ProfileView()
            }
        }
    }

    private var ladderToggle: some View {
        HStack(spacing: 8) {
            ForEach([LadderType.rapid, .daily]) { ladder in
                Button {
                    Task {
                        await model.setLadder(ladder, using: authStore)
                    }
                } label: {
                    Text(ladder.label)
                        .font(.archetypeBody(13, weight: .bold))
                        .foregroundStyle(model.ladder == ladder ? Color(hex: 0x111827) : Color(hex: 0xD1D5DB))
                        .padding(.horizontal, 17)
                        .padding(.vertical, 10)
                        .background(model.ladder == ladder ? Color.white : Color(hex: 0x374151))
                        .clipShape(Capsule())
                }
                .buttonStyle(.plain)
                .disabled(model.isLoading)
            }
        }
        .frame(maxWidth: .infinity)
    }

    @ViewBuilder
    private var leaderboardContent: some View {
        if model.isLoading && model.players.isEmpty {
            ArchetypeWebPanel {
                LeaderboardProgressRow(text: "Loading leaderboard...")
            }
        } else if let error = model.errorMessage {
            ArchetypeWebPanel {
                VStack(spacing: 14) {
                    Text(error)
                        .font(.archetypeBody(12))
                        .foregroundStyle(ArchetypeTheme.red)
                        .frame(maxWidth: .infinity, alignment: .leading)

                    Button {
                        Task { await model.load(using: authStore) }
                    } label: {
                        Text("Try Again")
                            .frame(maxWidth: .infinity)
                    }
                    .buttonStyle(PrimaryGameButtonStyle())
                }
            }
        } else if model.players.isEmpty {
            ArchetypeWebPanel {
                EmptyState(
                    title: "No Rankings Yet",
                    detail: "Be the first to play a ranked match and appear on the leaderboard.",
                    systemImage: "trophy.fill"
                )
            }
        } else {
            ArchetypeWebPanel(padding: 0) {
                VStack(spacing: 0) {
                    LeaderboardTableHeader()

                    Divider()
                        .overlay(ArchetypeTheme.border)

                    ForEach(Array(model.players.enumerated()), id: \.element.id) { index, player in
                        LeaderboardTableRow(
                            rank: index + 1,
                            player: player,
                            isCurrentUser: player.id == authStore.user?.id
                        )

                        if index < model.players.count - 1 {
                            Divider()
                                .overlay(ArchetypeTheme.border)
                        }
                    }
                }
            }
        }
    }
}

private struct LeaderboardTableHeader: View {
    var body: some View {
        HStack(spacing: 10) {
            Text("Rank")
                .frame(width: 42, alignment: .leading)

            Text("Player")
                .frame(maxWidth: .infinity, alignment: .leading)

            Text("Rating")
                .frame(width: 72, alignment: .trailing)
        }
        .font(.archetypeBody(13, weight: .bold))
        .foregroundStyle(ArchetypeTheme.text)
        .padding(.horizontal, 14)
        .padding(.vertical, 13)
        .background(LeaderboardPalette.headerBackground)
    }
}

private struct LeaderboardProgressRow: View {
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
    }
}

private struct LeaderboardTableRow: View {
    let rank: Int
    let player: LeaderboardPlayer
    let isCurrentUser: Bool

    var body: some View {
        HStack(spacing: 12) {
            rankBadge

            VStack(alignment: .leading, spacing: 8) {
                HStack(spacing: 10) {
                    initialsBadge

                    VStack(alignment: .leading, spacing: 3) {
                        HStack(spacing: 7) {
                            Text(player.displayName)
                                .font(.archetypeBody(15, weight: .semibold))
                                .foregroundStyle(ArchetypeTheme.text)
                                .lineLimit(1)

                            if isCurrentUser {
                                Text("You")
                                    .font(.archetypeBody(10, weight: .bold))
                                    .foregroundStyle(LeaderboardPalette.currentUserText)
                                    .padding(.horizontal, 6)
                                    .padding(.vertical, 2)
                                    .background(LeaderboardPalette.currentUserBackground)
                                    .clipShape(Capsule())
                            }
                        }

                        if let username = player.username, !username.isEmpty {
                            Text("@\(username)")
                                .font(.archetypeBody(11, weight: .medium))
                                .foregroundStyle(ArchetypeTheme.muted)
                                .lineLimit(1)
                        }
                    }

                    Spacer(minLength: 8)

                    Text(verbatim: String(player.eloRating))
                        .font(.archetypeBody(15, weight: .black))
                        .foregroundStyle(rank <= 3 ? LeaderboardPalette.topRatingText : ArchetypeTheme.text)
                        .frame(width: 70)
                        .padding(.vertical, 6)
                        .background(rank <= 3 ? LeaderboardPalette.topRatingBackground : LeaderboardPalette.defaultRatingBackground)
                        .clipShape(Capsule())
                }

            }
        }
        .padding(.horizontal, 14)
        .padding(.vertical, 15)
        .background(rankBackground)
    }

    private var rankBadge: some View {
        Group {
            if let medal = rankMedal {
                Text(medal)
                    .font(.system(size: 28))
            } else {
                Text("#\(rank)")
                    .font(.archetypeBody(14, weight: .black))
                    .foregroundStyle(ArchetypeTheme.muted)
            }
        }
        .frame(width: 40, height: 40, alignment: .center)
    }

    private var initialsBadge: some View {
        ZStack {
            LinearGradient(
                colors: [ArchetypeTheme.gold, ArchetypeTheme.sky],
                startPoint: .topLeading,
                endPoint: .bottomTrailing
            )
            Text(initials(player.displayName))
                .font(.archetypeBody(11, weight: .black))
                .foregroundStyle(Color.white)
        }
        .frame(width: 34, height: 34)
        .clipShape(Circle())
    }

    private var rankMedal: String? {
        switch rank {
        case 1:
            return "🥇"
        case 2:
            return "🥈"
        case 3:
            return "🥉"
        default:
            return nil
        }
    }

    private var rankBackground: Color {
        switch rank {
        case 1:
            return LeaderboardPalette.firstRowBackground
        case 2:
            return LeaderboardPalette.secondRowBackground
        case 3:
            return LeaderboardPalette.thirdRowBackground
        default:
            return Color.clear
        }
    }

    private func initials(_ name: String) -> String {
        let parts = name.split(separator: " ")
        if parts.count >= 2 {
            return "\(parts[0].prefix(1))\(parts[1].prefix(1))".uppercased()
        }
        return String(name.prefix(2)).uppercased()
    }
}

private enum LeaderboardPalette {
    static var headerBackground: Color {
        adaptive(light: 0xF9FAFB, dark: 0x1F2937)
    }

    static var firstRowBackground: Color {
        adaptive(light: 0xFFFBEB, dark: 0x261E22)
    }

    static var secondRowBackground: Color {
        adaptive(light: 0xF9FAFB, dark: 0x1F2937)
    }

    static var thirdRowBackground: Color {
        adaptive(light: 0xFFF7ED, dark: 0x271C22)
    }

    static var topRatingBackground: Color {
        adaptive(light: 0xFEF3C7, dark: 0x78350F)
    }

    static var topRatingText: Color {
        adaptive(light: 0x92400E, dark: 0xFDE68A)
    }

    static var defaultRatingBackground: Color {
        adaptive(light: 0xF3F4F6, dark: 0x374151)
    }

    static var currentUserBackground: Color {
        adaptive(light: 0xDBEAFE, dark: 0x1E3A8A)
    }

    static var currentUserText: Color {
        adaptive(light: 0x1E40AF, dark: 0xBFDBFE)
    }

    private static func adaptive(light: UInt, dark: UInt) -> Color {
        Color(
            uiColor: UIColor { traits in
                traits.userInterfaceStyle == .dark
                    ? UIColor(hex: dark)
                    : UIColor(hex: light)
            }
        )
    }
}
