import Foundation

@MainActor
final class AuthStore: ObservableObject {
    @Published private(set) var user: User?
    @Published private(set) var isAuthenticated = false
    @Published private(set) var isRestoringSession = true
    @Published var isLoading = false
    @Published var errorMessage: String?
    @Published var statusMessage: String?

    private let api: APIClient
    private let keychain: KeychainStore
    private var accessToken: String?
    private var refreshToken: String?

    var currentAccessToken: String? {
        accessToken
    }

    init(api: APIClient = .shared, keychain: KeychainStore = KeychainStore()) {
        self.api = api
        self.keychain = keychain
    }

    func restoreSession() async {
        defer { isRestoringSession = false }

        accessToken = try? keychain.string(for: "accessToken")
        refreshToken = try? keychain.string(for: "refreshToken")

        guard accessToken != nil || refreshToken != nil else {
            clearSession()
            return
        }

        do {
            let profile: User = try await authenticatedGet("/auth/profile/")
            user = profile
            isAuthenticated = true
        } catch {
            clearSession()
        }
    }

    func sendLoginLink(email: String) async {
        await runLoading {
            let response: LoginLinkResponse = try await api.post(
                "/auth/passwordless-login/",
                body: PasswordlessLoginRequest(email: email)
            )
            statusMessage = response.message ?? "Login link sent."
        }
    }

    func confirmEmail(key input: String) async {
        let key = Self.normalizedConfirmationKey(input)

        await runLoading {
            let response: AuthResponse = try await api.post(
                "/auth/email-confirm/",
                body: EmailConfirmationRequest(key: key)
            )

            guard
                let access = response.resolvedAccessToken,
                let refresh = response.resolvedRefreshToken,
                let user = response.user
            else {
                throw APIError.decodingFailed("Email confirmation did not return tokens.")
            }

            try storeSession(access: access, refresh: refresh, user: user)
            statusMessage = "Signed in as \(user.displayName ?? user.email)."
        }
    }

    func authenticatedGet<Response: Decodable>(_ path: String) async throws -> Response {
        do {
            return try await api.get(path, accessToken: accessToken)
        } catch APIError.unauthorized {
            guard await refreshAccessToken() else {
                throw APIError.unauthorized
            }
            return try await api.get(path, accessToken: accessToken)
        }
    }

    func authenticatedPost<Body: Encodable, Response: Decodable>(
        _ path: String,
        body: Body
    ) async throws -> Response {
        do {
            return try await api.post(path, body: body, accessToken: accessToken)
        } catch APIError.unauthorized {
            guard await refreshAccessToken() else {
                throw APIError.unauthorized
            }
            return try await api.post(path, body: body, accessToken: accessToken)
        }
    }

    func refreshAccessToken() async -> Bool {
        guard let refreshToken else {
            clearSession()
            return false
        }

        do {
            let response: TokenRefreshResponse = try await api.post(
                "/auth/token/refresh/",
                body: ["refresh": refreshToken]
            )
            accessToken = response.access
            try keychain.set(response.access, for: "accessToken")

            if let rotatedRefresh = response.refresh {
                self.refreshToken = rotatedRefresh
                try keychain.set(rotatedRefresh, for: "refreshToken")
            }

            return true
        } catch {
            clearSession()
            return false
        }
    }

    func signOut() {
        clearSession()
        statusMessage = "Signed out."
    }

    private func runLoading(_ operation: () async throws -> Void) async {
        isLoading = true
        errorMessage = nil
        statusMessage = nil

        do {
            try await operation()
        } catch {
            errorMessage = error.localizedDescription
        }

        isLoading = false
    }

    private func storeSession(access: String, refresh: String, user: User) throws {
        accessToken = access
        refreshToken = refresh
        self.user = user
        isAuthenticated = true

        try keychain.set(access, for: "accessToken")
        try keychain.set(refresh, for: "refreshToken")
    }

    private func clearSession() {
        accessToken = nil
        refreshToken = nil
        user = nil
        isAuthenticated = false
        keychain.delete("accessToken")
        keychain.delete("refreshToken")
    }

    private static func normalizedConfirmationKey(_ input: String) -> String {
        let trimmed = input.trimmingCharacters(in: .whitespacesAndNewlines)

        if
            let url = URL(string: trimmed),
            let lastComponent = url.pathComponents.last,
            lastComponent != "/"
        {
            return lastComponent
        }

        return trimmed
    }
}
