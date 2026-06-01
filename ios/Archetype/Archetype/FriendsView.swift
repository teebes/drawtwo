import SwiftUI

@MainActor
final class FriendsViewModel: ObservableObject {
    @Published var friendships: [Friendship] = []
    @Published var username = ""
    @Published var isLoading = false
    @Published var isMutating = false
    @Published var errorMessage: String?
    @Published var statusMessage: String?

    var acceptedFriends: [Friendship] {
        friendships
            .filter { $0.status == .accepted }
            .sorted(by: compareFriends)
    }

    var incomingRequests: [Friendship] {
        friendships
            .filter { $0.status == .pending && !$0.isInitiator }
            .sorted(by: compareFriends)
    }

    var sentRequests: [Friendship] {
        friendships
            .filter { $0.status == .pending && $0.isInitiator }
            .sorted(by: compareFriends)
    }

    func load(using authStore: AuthStore) async {
        isLoading = true
        errorMessage = nil

        do {
            friendships = try await authStore.authenticatedGet("/auth/friends/")
        } catch {
            errorMessage = error.localizedDescription
            friendships = []
        }

        isLoading = false
    }

    func sendRequest(using authStore: AuthStore) async {
        let trimmedUsername = username.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmedUsername.isEmpty else {
            errorMessage = "Enter a username."
            return
        }

        isMutating = true
        errorMessage = nil
        statusMessage = nil

        do {
            let friendship: Friendship = try await authStore.authenticatedPost(
                "/auth/friends/",
                body: FriendRequest(username: trimmedUsername)
            )
            upsert(friendship)
            username = ""
            statusMessage = "Friend request sent."
            await load(using: authStore)
        } catch {
            errorMessage = error.localizedDescription
        }

        isMutating = false
    }

    func accept(_ friendship: Friendship, using authStore: AuthStore) async {
        await patch(friendship, action: "accept", using: authStore) { updated in
            upsert(updated)
            statusMessage = "Friend request accepted."
        }
    }

    func decline(_ friendship: Friendship, using authStore: AuthStore) async {
        await patch(friendship, action: "decline", using: authStore) { _ in
            friendships.removeAll { $0.id == friendship.id }
            statusMessage = "Friend request declined."
        }
    }

    func remove(_ friendship: Friendship, using authStore: AuthStore) async {
        isMutating = true
        errorMessage = nil
        statusMessage = nil

        do {
            let _: EmptyResponse = try await authStore.authenticatedDelete(
                "/auth/friends/\(friendship.id)/"
            )
            friendships.removeAll { $0.id == friendship.id }
            statusMessage = friendship.status == .accepted ? "Friend removed." : "Friend request cancelled."
        } catch {
            errorMessage = error.localizedDescription
        }

        isMutating = false
    }

    private func patch(
        _ friendship: Friendship,
        action: String,
        using authStore: AuthStore,
        onSuccess: (Friendship) -> Void
    ) async {
        isMutating = true
        errorMessage = nil
        statusMessage = nil

        do {
            if action == "decline" {
                let _: EmptyResponse = try await authStore.authenticatedPatch(
                    "/auth/friends/\(friendship.id)/",
                    body: FriendshipActionRequest(action: action)
                )
                friendships.removeAll { $0.id == friendship.id }
                statusMessage = "Friend request declined."
            } else {
                let updated: Friendship = try await authStore.authenticatedPatch(
                    "/auth/friends/\(friendship.id)/",
                    body: FriendshipActionRequest(action: action)
                )
                onSuccess(updated)
            }
        } catch {
            errorMessage = error.localizedDescription
        }

        isMutating = false
    }

    private func upsert(_ friendship: Friendship) {
        if let index = friendships.firstIndex(where: { $0.id == friendship.id }) {
            friendships[index] = friendship
        } else {
            friendships.append(friendship)
        }
    }

    private func compareFriends(_ first: Friendship, _ second: Friendship) -> Bool {
        first.friendData.displayLabel.localizedCaseInsensitiveCompare(second.friendData.displayLabel) == .orderedAscending
    }
}

struct FriendsView: View {
    @EnvironmentObject private var authStore: AuthStore
    @StateObject private var model = FriendsViewModel()

    var body: some View {
        ArchetypeScreen {
            ScrollView {
                VStack(spacing: 0) {
                    topBar
                        .padding(.horizontal, 18)
                        .padding(.top, 6)
                        .padding(.bottom, 16)

                    VStack(alignment: .leading, spacing: 32) {
                        Text("Friends")
                            .font(.archetypeBody(28, weight: .bold))
                            .foregroundStyle(ArchetypeTheme.text)
                            .frame(maxWidth: .infinity, alignment: .leading)

                        addFriendPanel
                        noticePanel
                        friendsSection
                        incomingSection
                        sentSection
                    }
                    .frame(maxWidth: 672)
                    .padding(.horizontal, 32)
                    .padding(.top, 20)
                    .padding(.bottom, 36)
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
            CaptureStateRecorder.record("friends")
        }
    }

    private var topBar: some View {
        DrawTwoTopBar {
            ArchetypeProfileLink(user: authStore.user) {
                ProfileView()
            }
        }
    }

    private var addFriendPanel: some View {
        ArchetypeWebPanel(title: "Add Friend", padding: 24) {
            HStack(spacing: 8) {
                StyledTextField(
                    title: "Enter username",
                    text: $model.username
                )
                .submitLabel(.send)
                .onSubmit {
                    Task { await model.sendRequest(using: authStore) }
                }

                Button {
                    Task { await model.sendRequest(using: authStore) }
                } label: {
                    Text(model.isMutating ? "Sending..." : "Send Request")
                        .multilineTextAlignment(.center)
                        .lineLimit(2)
                }
                .buttonStyle(
                    FilledGameButtonStyle(
                        color: Color(hex: 0x2563EB),
                        pressedColor: Color(hex: 0x1D4ED8)
                    )
                )
                .frame(width: 96)
                .disabled(model.isMutating)
                .opacity(model.isMutating ? 0.55 : 1)
            }
        }
    }

    @ViewBuilder
    private var noticePanel: some View {
        if let error = model.errorMessage {
            FriendNotice(text: error, color: ArchetypeTheme.red)
        } else if let status = model.statusMessage {
            FriendNotice(text: status, color: ArchetypeTheme.green)
        }
    }

    private var friendsSection: some View {
        FriendshipsSection(
            title: "Friends",
            count: model.acceptedFriends.count,
            friendships: model.acceptedFriends,
            emptyDetail: "No friends yet. Send a friend request to get started!",
            isMutating: model.isMutating,
            actions: { friendship in
                [FriendRowAction(title: "Remove", role: .destructive) {
                    Task { await model.remove(friendship, using: authStore) }
                }]
            }
        )
    }

    private var incomingSection: some View {
        FriendshipsSection(
            title: "Pending Requests",
            count: model.incomingRequests.count,
            friendships: model.incomingRequests,
            emptyDetail: "No pending friend requests",
            isMutating: model.isMutating,
            actions: { friendship in
                [
                    FriendRowAction(title: "Accept", role: .primary) {
                        Task { await model.accept(friendship, using: authStore) }
                    },
                    FriendRowAction(title: "Decline", role: .secondary) {
                        Task { await model.decline(friendship, using: authStore) }
                    },
                ]
            }
        )
    }

    private var sentSection: some View {
        FriendshipsSection(
            title: "Sent Requests",
            count: model.sentRequests.count,
            friendships: model.sentRequests,
            emptyDetail: "No pending sent requests",
            isMutating: model.isMutating,
            actions: { friendship in
                [FriendRowAction(title: "Cancel", role: .secondary) {
                    Task { await model.remove(friendship, using: authStore) }
                }]
            }
        )
    }
}

private struct FriendNotice: View {
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

private struct FriendshipsSection: View {
    let title: String
    let count: Int
    let friendships: [Friendship]
    let emptyDetail: String
    let isMutating: Bool
    let actions: (Friendship) -> [FriendRowAction]

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            FriendSectionTitle(title: "\(title) (\(count))")

            if friendships.isEmpty {
                Text(emptyDetail)
                    .font(.archetypeBody(14))
                    .foregroundStyle(ArchetypeTheme.muted)
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, 32)
            } else {
                VStack(spacing: 8) {
                    ForEach(friendships) { friendship in
                        FriendRow(
                            friendship: friendship,
                            isMutating: isMutating,
                            actions: actions(friendship)
                        )
                    }
                }
            }
        }
    }
}

private struct FriendSectionTitle: View {
    let title: String

    var body: some View {
        HStack(alignment: .lastTextBaseline) {
            Text(title)
                .font(.archetypeBody(20, weight: .semibold))
                .foregroundStyle(ArchetypeTheme.text)

            Spacer()
        }
        .padding(.bottom, 4)
    }
}

private struct FriendRowAction: Identifiable {
    enum Role {
        case primary
        case secondary
        case destructive
    }

    let id = UUID()
    let title: String
    let role: Role
    let action: () -> Void
}

private struct FriendRow: View {
    let friendship: Friendship
    let isMutating: Bool
    let actions: [FriendRowAction]

    var body: some View {
        HStack(spacing: 14) {
            HStack(spacing: 12) {
                FriendAvatar(user: friendship.friendData)

                VStack(alignment: .leading, spacing: 4) {
                    Text(friendship.friendData.displayLabel)
                        .font(.archetypeBody(15, weight: .semibold))
                        .foregroundStyle(ArchetypeTheme.text)
                        .lineLimit(1)

                    Text(subtitle)
                        .font(.archetypeBody(12, weight: .medium))
                        .foregroundStyle(ArchetypeTheme.muted)
                        .lineLimit(1)

                    if isWaitingForResponse {
                        Text("Waiting for response...")
                            .font(.archetypeBody(11, weight: .medium))
                            .foregroundStyle(ArchetypeTheme.gold2)
                            .lineLimit(1)
                    }
                }
            }
            .frame(maxWidth: .infinity, alignment: .leading)

            HStack(spacing: 8) {
                ForEach(actions) { action in
                    Button(action: action.action) {
                        Text(action.title)
                            .lineLimit(1)
                            .fixedSize(horizontal: true, vertical: false)
                    }
                    .buttonStyle(FriendActionButtonStyle(role: action.role))
                    .disabled(isMutating)
                    .opacity(isMutating ? 0.55 : 1)
                }
            }
            .layoutPriority(1)
        }
        .padding(14)
        .background(ArchetypeTheme.panel)
        .overlay(
            RoundedRectangle(cornerRadius: ArchetypeTheme.surfaceRadius)
                .stroke(borderColor, lineWidth: 1)
        )
        .clipShape(RoundedRectangle(cornerRadius: ArchetypeTheme.surfaceRadius))
        .opacity(isWaitingForResponse ? 0.75 : 1)
    }

    private var borderColor: Color {
        if friendship.status == .pending && !friendship.isInitiator {
            return Color(hex: 0xA16207)
        }
        return ArchetypeTheme.border
    }

    private var subtitle: String {
        guard let username = friendship.friendData.username, !username.isEmpty else {
            return "Player \(friendship.friend)"
        }
        return username
    }

    private var isWaitingForResponse: Bool {
        friendship.status == .pending && friendship.isInitiator
    }

}

private struct FriendAvatar: View {
    let user: FriendUser

    var body: some View {
        ZStack {
            Circle()
                .fill(Color(hex: 0x374151))

            if let avatar = user.avatar, let url = URL(string: avatar) {
                AsyncImage(url: url) { phase in
                    switch phase {
                    case .success(let image):
                        image
                            .resizable()
                            .scaledToFill()
                    default:
                        initials
                    }
                }
            } else {
                initials
            }
        }
        .frame(width: 40, height: 40)
        .clipShape(Circle())
    }

    private var initials: some View {
        Text(user.displayLabel.prefix(1).uppercased())
            .font(.archetypeBody(16, weight: .black))
            .foregroundStyle(ArchetypeTheme.text)
    }
}

private struct FriendActionButtonStyle: ButtonStyle {
    let role: FriendRowAction.Role

    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .font(.archetypeBody(13, weight: .bold))
            .foregroundStyle(foreground)
            .padding(.horizontal, 12)
            .padding(.vertical, 10)
            .background(background(isPressed: configuration.isPressed))
            .overlay(
                RoundedRectangle(cornerRadius: ArchetypeTheme.controlRadius)
                    .stroke(border, lineWidth: 1)
            )
            .clipShape(RoundedRectangle(cornerRadius: ArchetypeTheme.controlRadius))
            .scaleEffect(configuration.isPressed ? 0.98 : 1)
    }

    private var foreground: Color {
        switch role {
        case .primary:
            return Color.white
        case .secondary:
            return Color.white
        case .destructive:
            return Color.white
        }
    }

    private func background(isPressed: Bool) -> Color {
        switch role {
        case .primary:
            return isPressed ? Color(hex: 0x15803D) : Color(hex: 0x16A34A)
        case .secondary:
            return isPressed ? Color(hex: 0x374151) : Color(hex: 0x4B5563)
        case .destructive:
            return isPressed ? Color(hex: 0xB91C1C) : Color(hex: 0xDC2626)
        }
    }

    private var border: Color {
        switch role {
        case .primary:
            return Color(hex: 0x16A34A)
        case .secondary:
            return Color(hex: 0x4B5563)
        case .destructive:
            return Color(hex: 0xDC2626)
        }
    }
}
