import AuthenticationServices
import SwiftUI

struct ProfileView: View {
    @EnvironmentObject private var authStore: AuthStore
    @State private var isEditingUsername = false
    @State private var usernameDraft = ""
    @State private var profileStatusMessage: String?
    @State private var didApplyInitialEdit = false
    @State private var didApplyInitialUsername = false
    @State private var showDeleteAccountConfirmation = false

    var body: some View {
        ArchetypeScreen {
            ScrollView {
                VStack(spacing: 0) {
                    topBar
                        .padding(.horizontal, 18)
                        .padding(.top, 6)
                        .padding(.bottom, 16)

                    ArchetypePageBanner(title: "Profile")

                    VStack(spacing: 20) {
                        accountPanel
                        noticePanel
                    }
                    .frame(maxWidth: 760)
                    .padding(.horizontal, 18)
                    .padding(.top, 32)
                    .padding(.bottom, 36)
                }
            }
            .refreshable {
                await refresh()
            }
        }
        .toolbar(.hidden, for: .navigationBar)
        .navigationBarBackButtonHidden(true)
        .task {
            await refresh()
            applyInitialEditIfNeeded()
            await applyInitialUsernameIfNeeded()
            recordCaptureState()
        }
        .onChange(of: isEditingUsername) { _, _ in
            recordCaptureState()
        }
        .confirmationDialog(
            "Delete your Draw Two account?",
            isPresented: $showDeleteAccountConfirmation,
            titleVisibility: .visible
        ) {
            Button("Delete Account", role: .destructive) {
                Task {
                    await deleteAccount()
                }
            }
            Button("Cancel", role: .cancel) {}
        } message: {
            Text("This removes your login access and profile information.")
        }
    }

    private func recordCaptureState() {
        CaptureStateRecorder.record(
            isEditingUsername ? "profile-edit" : "profile",
            detail: ["username": currentUsername]
        )
    }

    private var topBar: some View {
        DrawTwoTopBar {
            ArchetypeProfileAvatar(user: authStore.user)
        }
    }

    private var accountPanel: some View {
        VStack(alignment: .leading, spacing: 0) {
            VStack(spacing: 0) {
                ProfilePanelHeader()
                    .padding(.bottom, 18)

                ProfileInfoRow(label: "Email", value: authStore.user?.email ?? "Unknown")

                Divider().overlay(ArchetypeTheme.border)

                usernameRow

                if let createdAt = authStore.user?.createdAt {
                    Divider().overlay(ArchetypeTheme.border)
                    ProfileInfoRow(label: "Member Since", value: formattedDate(createdAt))
                }

                Divider().overlay(ArchetypeTheme.border)
                appleRow

                Divider().overlay(ArchetypeTheme.border)
                googleRow

                Divider().overlay(ArchetypeTheme.border)
                accountActionsRow
            }
        }
        .padding(24)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(ArchetypeTheme.panel2)
        .clipShape(RoundedRectangle(cornerRadius: 16))
        .shadow(color: Color.black.opacity(0.12), radius: 3, x: 0, y: 1)
    }

    @ViewBuilder
    private var usernameRow: some View {
        if isEditingUsername {
            VStack(alignment: .leading, spacing: 8) {
                Text("Username:")
                    .font(.archetypeBody(15, weight: .medium))
                    .foregroundStyle(Color(hex: 0xD1D5DB))

                ProfileUsernameField(
                    placeholder: "Enter username",
                    text: $usernameDraft
                )
                .textContentType(.username)
                .submitLabel(.done)
                .onSubmit(saveUsername)
                .disabled(authStore.isLoading)

                HStack(spacing: 8) {
                    Button("Save") {
                        saveUsername()
                    }
                    .font(.archetypeBody(13, weight: .semibold))
                    .foregroundStyle(Color.white)
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, 8)
                    .background(Color(hex: 0x4F46E5))
                    .clipShape(RoundedRectangle(cornerRadius: 6))
                    .disabled(authStore.isLoading || usernameDraft.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)

                    Button("Cancel") {
                        cancelUsernameEdit()
                    }
                    .font(.archetypeBody(13, weight: .semibold))
                    .foregroundStyle(ArchetypeTheme.text)
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, 8)
                    .background(Color(hex: 0x374151))
                    .clipShape(RoundedRectangle(cornerRadius: 6))
                    .disabled(authStore.isLoading)
                }
                .padding(.top, 1)
            }
            .padding(.vertical, 13)
        } else {
            HStack(alignment: .firstTextBaseline, spacing: 12) {
                Text("Username:")
                    .font(.archetypeBody(15, weight: .medium))
                    .foregroundStyle(Color(hex: 0xD1D5DB))

                Spacer(minLength: 12)

                HStack(spacing: 8) {
                    Text(currentUsername.isEmpty ? "Not set" : currentUsername)
                        .font(.archetypeBody(15))
                        .foregroundStyle(ArchetypeTheme.text)
                        .multilineTextAlignment(.trailing)

                    Button(currentUsername.isEmpty ? "Set" : "Edit") {
                        startUsernameEdit()
                    }
                    .font(.archetypeBody(13, weight: .medium))
                    .foregroundStyle(Color(hex: 0x818CF8))
                    .disabled(authStore.isLoading)
                }
            }
            .padding(.vertical, 13)
        }
    }

    private var appleRow: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack(alignment: .firstTextBaseline, spacing: 12) {
                Text("Apple:")
                    .font(.archetypeBody(15, weight: .medium))
                    .foregroundStyle(Color(hex: 0xD1D5DB))

                Spacer(minLength: 12)

                if appleConnected {
                    HStack(spacing: 10) {
                        Label("Connected", systemImage: "checkmark.circle.fill")
                            .font(.archetypeBody(15, weight: .medium))
                            .foregroundStyle(ArchetypeTheme.green)

                        Button("Disconnect") {
                            Task {
                                await disconnectProvider("apple")
                            }
                        }
                        .font(.archetypeBody(13, weight: .medium))
                        .foregroundStyle(Color(hex: 0xF87171))
                        .disabled(authStore.isLoading)
                    }
                }
            }

            if !appleConnected {
                SignInWithAppleButton(.continue) { request in
                    request.requestedScopes = [.email]
                } onCompletion: { result in
                    handleAppleLinkCompletion(result)
                }
                .signInWithAppleButtonStyle(.white)
                .frame(height: 42)
                .clipShape(RoundedRectangle(cornerRadius: ArchetypeTheme.controlRadius))
                .allowsHitTesting(!authStore.isLoading)
                .opacity(authStore.isLoading ? 0.55 : 1)
            }
        }
        .padding(.vertical, 13)
    }

    private var googleRow: some View {
        HStack(alignment: .firstTextBaseline, spacing: 12) {
            Text("Google:")
                .font(.archetypeBody(15, weight: .medium))
                .foregroundStyle(Color(hex: 0xD1D5DB))

            Spacer(minLength: 12)

            if googleConnected {
                HStack(spacing: 10) {
                    Label("Connected", systemImage: "checkmark.circle.fill")
                        .font(.archetypeBody(15, weight: .medium))
                        .foregroundStyle(ArchetypeTheme.green)

                    Button("Disconnect") {
                        Task {
                            await disconnectProvider("google")
                        }
                    }
                    .font(.archetypeBody(13, weight: .medium))
                    .foregroundStyle(Color(hex: 0xF87171))
                    .disabled(authStore.isLoading)
                }
            } else {
                Text("Not connected")
                    .font(.archetypeBody(15))
                    .foregroundStyle(ArchetypeTheme.muted)
            }
        }
        .padding(.vertical, 13)
    }

    private var accountActionsRow: some View {
        HStack(alignment: .center, spacing: 12) {
            Text("Account:")
                .font(.archetypeBody(15, weight: .medium))
                .foregroundStyle(Color(hex: 0xD1D5DB))

            Spacer(minLength: 12)

            Button(role: .destructive) {
                showDeleteAccountConfirmation = true
            } label: {
                Label("Delete Account", systemImage: "trash")
                    .font(.archetypeBody(13, weight: .semibold))
                    .foregroundStyle(Color.white)
                    .padding(.horizontal, 12)
                    .padding(.vertical, 8)
                    .background(ArchetypeTheme.red)
                    .clipShape(RoundedRectangle(cornerRadius: ArchetypeTheme.controlRadius))
            }
            .buttonStyle(.plain)
            .disabled(authStore.isLoading)
        }
        .padding(.vertical, 13)
    }

    @ViewBuilder
    private var noticePanel: some View {
        if let error = authStore.errorMessage {
            ProfileNotice(text: error, color: ArchetypeTheme.red)
        } else if let status = profileStatusMessage {
            ProfileNotice(text: status, color: ArchetypeTheme.green)
        }
    }

    private func refresh() async {
        _ = await authStore.reloadProfile()
    }

    private var currentUsername: String {
        authStore.user?.username ?? ""
    }

    private var appleConnected: Bool {
        authStore.user?.appleConnected == true
    }

    private var googleConnected: Bool {
        authStore.user?.googleConnected == true
    }

    private func startUsernameEdit() {
        profileStatusMessage = nil
        usernameDraft = currentUsername
        isEditingUsername = true
    }

    private func cancelUsernameEdit() {
        profileStatusMessage = nil
        usernameDraft = ""
        isEditingUsername = false
    }

    private func saveUsername() {
        let username = usernameDraft.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !username.isEmpty else {
            return
        }

        Task {
            await saveUsername(username)
        }
    }

    private func saveUsername(_ username: String) async {
        profileStatusMessage = nil
        if await authStore.updateProfile(username: username) {
            isEditingUsername = false
            usernameDraft = ""
            profileStatusMessage = "Profile updated."
        }
        recordCaptureState()
    }

    private func handleAppleLinkCompletion(_ result: Result<ASAuthorization, Error>) {
        profileStatusMessage = nil

        switch result {
        case .success(let authorization):
            guard
                let credential = authorization.credential as? ASAuthorizationAppleIDCredential,
                let tokenData = credential.identityToken,
                let identityToken = String(data: tokenData, encoding: .utf8)
            else {
                authStore.statusMessage = nil
                authStore.errorMessage = "Apple sign-in did not return an identity token."
                return
            }
            let authorizationCode = credential.authorizationCode.flatMap {
                String(data: $0, encoding: .utf8)
            }

            Task {
                if await authStore.linkApple(
                    identityToken: identityToken,
                    authorizationCode: authorizationCode
                ) {
                    profileStatusMessage = authStore.statusMessage ?? "Apple sign-in connected."
                }
            }

        case .failure(let error):
            let nsError = error as NSError
            if
                nsError.domain == ASAuthorizationError.errorDomain,
                nsError.code == ASAuthorizationError.Code.canceled.rawValue
            {
                return
            }

            authStore.statusMessage = nil
            authStore.errorMessage = error.localizedDescription
        }
    }

    private func disconnectProvider(_ provider: String) async {
        profileStatusMessage = nil
        if await authStore.disconnectSocial(provider: provider) {
            profileStatusMessage = authStore.statusMessage
        }
    }

    private func deleteAccount() async {
        profileStatusMessage = nil
        _ = await authStore.deleteAccount()
    }

    private func applyInitialEditIfNeeded() {
        #if DEBUG
        guard AppConfig.initialProfileEditOpen, !didApplyInitialEdit else {
            return
        }

        didApplyInitialEdit = true
        startUsernameEdit()
        #endif
    }

    private func applyInitialUsernameIfNeeded() async {
        #if DEBUG
        guard !didApplyInitialUsername,
              let username = AppConfig.initialProfileUsername?.trimmingCharacters(in: .whitespacesAndNewlines),
              !username.isEmpty else {
            return
        }

        didApplyInitialUsername = true
        usernameDraft = username
        isEditingUsername = true

        if AppConfig.initialProfileUsernameSaveEnabled {
            await saveUsername(username)
        } else {
            recordCaptureState()
        }
        #endif
    }

    private func formattedDate(_ value: String) -> String {
        let formatter = ISO8601DateFormatter()
        formatter.formatOptions = [.withInternetDateTime, .withFractionalSeconds]

        let date = formatter.date(from: value) ?? ISO8601DateFormatter().date(from: value)
        guard let date else {
            return value
        }

        return date.formatted(date: .abbreviated, time: .omitted)
    }
}

private struct ProfilePanelHeader: View {
    var body: some View {
        HStack(spacing: 10) {
            Text("👤")
                .font(.system(size: 19))

            Text("Account\nInformation")
                .font(.archetypeDisplay(22, weight: .bold))
                .foregroundStyle(ArchetypeTheme.text)
                .lineLimit(2)
                .fixedSize(horizontal: false, vertical: true)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }
}

private struct ProfileInfoRow: View {
    let label: String
    let value: String

    var body: some View {
        HStack(alignment: .firstTextBaseline, spacing: 12) {
            Text("\(label):")
                .font(.archetypeBody(15, weight: .medium))
                .foregroundStyle(Color(hex: 0xD1D5DB))

            Spacer(minLength: 12)

            Text(value)
                .font(.archetypeBody(15))
                .foregroundStyle(ArchetypeTheme.text)
                .multilineTextAlignment(.trailing)
        }
        .padding(.vertical, 13)
    }
}

private struct ProfileUsernameField: View {
    let placeholder: String
    @Binding var text: String

    var body: some View {
        TextField(placeholder, text: $text)
            .font(.archetypeBody(14))
            .textInputAutocapitalization(.never)
            .autocorrectionDisabled()
            .foregroundStyle(ArchetypeTheme.text)
            .tint(Color(hex: 0x6366F1))
            .padding(.horizontal, 10)
            .padding(.vertical, 8)
            .background(Color(hex: 0x1F2937))
            .overlay(
                RoundedRectangle(cornerRadius: 6)
                    .stroke(Color(hex: 0x4B5563), lineWidth: 1)
            )
            .clipShape(RoundedRectangle(cornerRadius: 6))
    }
}

private struct ProfileNotice: View {
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
