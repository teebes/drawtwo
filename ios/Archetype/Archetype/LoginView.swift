import SwiftUI

struct LoginView: View {
    @EnvironmentObject private var authStore: AuthStore
    @Environment(\.openURL) private var openURL

    @State private var email = ""
    @State private var confirmationKey = ""

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 24) {
                    header
                    loginCard
                    helpCard
                }
                .padding(20)
            }
            .background(Color(.systemGroupedBackground))
            .navigationTitle("Archetype")
        }
    }

    private var header: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("Archetype")
                .font(.largeTitle.bold())
            Text("Sign in with your DrawTwo account to load decks, games, and live match updates from drawtwo.com.")
                .font(.body)
                .foregroundStyle(.secondary)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }

    private var loginCard: some View {
        VStack(alignment: .leading, spacing: 16) {
            Text("DrawTwo Account")
                .font(.headline)

            TextField("Email", text: $email)
                .keyboardType(.emailAddress)
                .textInputAutocapitalization(.never)
                .autocorrectionDisabled()
                .textContentType(.emailAddress)
                .padding(12)
                .background(Color(.secondarySystemGroupedBackground))
                .clipShape(RoundedRectangle(cornerRadius: 10))

            Button {
                Task { await authStore.sendLoginLink(email: email) }
            } label: {
                Label("Send Login Link", systemImage: "envelope")
                    .frame(maxWidth: .infinity)
            }
            .buttonStyle(.borderedProminent)
            .disabled(email.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty || authStore.isLoading)

            Divider()

            TextField("Paste confirmation URL or key", text: $confirmationKey, axis: .vertical)
                .textInputAutocapitalization(.never)
                .autocorrectionDisabled()
                .lineLimit(2...4)
                .padding(12)
                .background(Color(.secondarySystemGroupedBackground))
                .clipShape(RoundedRectangle(cornerRadius: 10))

            Button {
                Task { await authStore.confirmEmail(key: confirmationKey) }
            } label: {
                Label("Continue", systemImage: "arrow.right.circle")
                    .frame(maxWidth: .infinity)
            }
            .buttonStyle(.bordered)
            .disabled(confirmationKey.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty || authStore.isLoading)

            if authStore.isLoading {
                ProgressView()
                    .frame(maxWidth: .infinity)
            }

            if let status = authStore.statusMessage {
                Text(status)
                    .font(.callout)
                    .foregroundStyle(.green)
            }

            if let error = authStore.errorMessage {
                Text(error)
                    .font(.callout)
                    .foregroundStyle(.red)
            }
        }
        .padding(18)
        .background(Color(.systemBackground))
        .clipShape(RoundedRectangle(cornerRadius: 16))
    }

    private var helpCard: some View {
        VStack(alignment: .leading, spacing: 10) {
            Text("Prototype login note")
                .font(.headline)
            Text("The current backend sends a web login URL by email. For this first native build, copy the full email-confirm URL or just the final confirmation key into the field above.")
                .font(.callout)
                .foregroundStyle(.secondary)

            Button {
                openURL(AppConfig.backendBaseURL.appendingPathComponent("login"))
            } label: {
                Label("Open drawtwo.com Login", systemImage: "safari")
            }
            .buttonStyle(.borderless)
        }
        .padding(18)
        .background(Color(.systemBackground))
        .clipShape(RoundedRectangle(cornerRadius: 16))
    }
}
