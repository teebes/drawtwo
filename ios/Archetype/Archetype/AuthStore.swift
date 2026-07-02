import Foundation
import GoogleSignIn
import UIKit

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

        #if DEBUG
        if AppConfig.localClearSessionOnLaunchEnabled {
            clearSession()
            return
        }
        #endif

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

    #if DEBUG
    func signInWithLocalAccount() async {
        guard AppConfig.allowsLocalAccountShortcut else {
            errorMessage = "Local test sign-in requires a local backend."
            return
        }

        await runLoading {
            let response: AuthResponse = try await api.post(
                "/auth/token/",
                body: PasswordSignInRequest(
                    email: AppConfig.localTestEmail,
                    password: AppConfig.localTestPassword
                )
            )

            guard
                let access = response.resolvedAccessToken,
                let refresh = response.resolvedRefreshToken
            else {
                throw APIError.decodingFailed("Local sign-in did not return tokens.")
            }

            let profile: User = try await api.get("/auth/profile/", accessToken: access)
            try storeSession(access: access, refresh: refresh, user: profile)
            statusMessage = "Signed in as \(profile.displayName ?? profile.email)."
        }
    }
    #endif

    @discardableResult
    func register(email: String, username: String?) async -> Bool {
        isLoading = true
        errorMessage = nil
        statusMessage = nil

        do {
            let normalizedUsername = username?
                .trimmingCharacters(in: .whitespacesAndNewlines)
            let response: RegistrationResponse = try await api.post(
                "/auth/register/",
                body: RegistrationRequest(
                    email: email,
                    username: normalizedUsername?.isEmpty == true ? nil : normalizedUsername
                )
            )
            statusMessage = response.message ?? "Registration successful. Please check your email."
            isLoading = false
            return true
        } catch {
            errorMessage = error.localizedDescription
            isLoading = false
            return false
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

    func confirmEmail(fromLoginURL url: URL) async {
        guard let key = Self.confirmationKey(from: url) else {
            errorMessage = "The login link is missing its confirmation code."
            statusMessage = nil
            return
        }

        await confirmEmail(key: key)
    }

    func signInWithGoogle(presenting viewController: UIViewController) async {
        isLoading = true
        errorMessage = nil
        statusMessage = nil
        defer { isLoading = false }

        do {
            let idToken = try await requestGoogleIDToken(presenting: viewController)
            let response: AuthResponse = try await api.post(
                "/auth/google/native/",
                body: GoogleNativeSignInRequest(idToken: idToken)
            )

            if response.requiresApproval == true {
                user = response.user
                isAuthenticated = false
                statusMessage = response.message
                    ?? "Google login succeeded, but your account is pending approval."
                return
            }

            guard
                let access = response.resolvedAccessToken,
                let refresh = response.resolvedRefreshToken,
                let user = response.user
            else {
                throw APIError.decodingFailed(
                    "Google sign-in did not return a complete session."
                )
            }

            try storeSession(access: access, refresh: refresh, user: user)
            statusMessage = response.message
                ?? "Signed in as \(user.displayName ?? user.email)."
        } catch {
            if Self.isGoogleSignInCancellation(error) {
                return
            }

            errorMessage = error.localizedDescription
        }
    }

    func signInWithApple(identityToken: String, authorizationCode: String? = nil) async {
        isLoading = true
        errorMessage = nil
        statusMessage = nil
        defer { isLoading = false }

        do {
            let response: AuthResponse = try await api.post(
                "/auth/apple/",
                body: AppleSignInRequest(
                    identityToken: identityToken,
                    authorizationCode: authorizationCode
                )
            )

            if response.requiresApproval == true {
                user = response.user
                isAuthenticated = false
                statusMessage = response.message
                    ?? "Apple login succeeded, but your account is pending approval."
                return
            }

            guard
                let access = response.resolvedAccessToken,
                let refresh = response.resolvedRefreshToken,
                let user = response.user
            else {
                throw APIError.decodingFailed(
                    "Apple sign-in did not return a complete session."
                )
            }

            try storeSession(access: access, refresh: refresh, user: user)
            statusMessage = response.message
                ?? "Signed in as \(user.displayName ?? user.email)."
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    @discardableResult
    func linkApple(identityToken: String, authorizationCode: String? = nil) async -> Bool {
        isLoading = true
        errorMessage = nil
        statusMessage = nil
        defer { isLoading = false }

        do {
            let response: AuthResponse = try await authenticatedPost(
                "/auth/apple/link/",
                body: AppleSignInRequest(
                    identityToken: identityToken,
                    authorizationCode: authorizationCode
                )
            )

            if let linkedUser = response.user {
                user = linkedUser
            }

            statusMessage = response.message ?? "Apple sign-in connected."
            return true
        } catch {
            errorMessage = error.localizedDescription
            return false
        }
    }

    @discardableResult
    func disconnectSocial(provider: String) async -> Bool {
        isLoading = true
        errorMessage = nil
        statusMessage = nil
        defer { isLoading = false }

        do {
            let response: AuthResponse = try await authenticatedDelete(
                "/auth/social/\(provider)/"
            )
            if let updatedUser = response.user {
                user = updatedUser
            }
            statusMessage = response.message ?? "\(provider.capitalized) sign-in disconnected."
            if provider == "google" {
                GIDSignIn.sharedInstance.signOut()
            }
            return true
        } catch {
            errorMessage = error.localizedDescription
            return false
        }
    }

    @discardableResult
    func deleteAccount() async -> Bool {
        isLoading = true
        errorMessage = nil
        statusMessage = nil
        defer { isLoading = false }

        do {
            await PushNotificationManager.shared.unregisterCurrentDevice(
                accessToken: accessToken
            )
            let _: EmptyResponse = try await authenticatedDelete("/auth/account/")
            GIDSignIn.sharedInstance.signOut()
            PushNotificationManager.shared.updateBadgeCount(0)
            clearSession()
            statusMessage = "Account deleted."
            return true
        } catch {
            errorMessage = error.localizedDescription
            return false
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

    func authenticatedGet<Response: Decodable>(
        _ path: String,
        queryItems: [URLQueryItem]
    ) async throws -> Response {
        do {
            return try await api.get(path, queryItems: queryItems, accessToken: accessToken)
        } catch APIError.unauthorized {
            guard await refreshAccessToken() else {
                throw APIError.unauthorized
            }
            return try await api.get(path, queryItems: queryItems, accessToken: accessToken)
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

    func authenticatedPost<Body: Encodable, Response: Decodable>(
        _ path: String,
        queryItems: [URLQueryItem],
        body: Body
    ) async throws -> Response {
        do {
            return try await api.post(
                path,
                queryItems: queryItems,
                body: body,
                accessToken: accessToken
            )
        } catch APIError.unauthorized {
            guard await refreshAccessToken() else {
                throw APIError.unauthorized
            }
            return try await api.post(
                path,
                queryItems: queryItems,
                body: body,
                accessToken: accessToken
            )
        }
    }

    func authenticatedPut<Body: Encodable, Response: Decodable>(
        _ path: String,
        body: Body
    ) async throws -> Response {
        do {
            return try await api.put(path, body: body, accessToken: accessToken)
        } catch APIError.unauthorized {
            guard await refreshAccessToken() else {
                throw APIError.unauthorized
            }
            return try await api.put(path, body: body, accessToken: accessToken)
        }
    }

    func authenticatedPatch<Body: Encodable, Response: Decodable>(
        _ path: String,
        body: Body
    ) async throws -> Response {
        do {
            return try await api.patch(path, body: body, accessToken: accessToken)
        } catch APIError.unauthorized {
            guard await refreshAccessToken() else {
                throw APIError.unauthorized
            }
            return try await api.patch(path, body: body, accessToken: accessToken)
        }
    }

    func authenticatedDelete<Response: Decodable>(_ path: String) async throws -> Response {
        do {
            return try await api.delete(path, accessToken: accessToken)
        } catch APIError.unauthorized {
            guard await refreshAccessToken() else {
                throw APIError.unauthorized
            }
            return try await api.delete(path, accessToken: accessToken)
        }
    }

    @discardableResult
    func reloadProfile() async -> Bool {
        do {
            let profile: User = try await authenticatedGet("/auth/profile/")
            user = profile
            return true
        } catch {
            errorMessage = error.localizedDescription
            return false
        }
    }

    @discardableResult
    func updateProfile(username: String) async -> Bool {
        isLoading = true
        errorMessage = nil
        statusMessage = nil

        do {
            let profile: User = try await authenticatedPatch(
                "/auth/profile/",
                body: ProfileUpdateRequest(username: username)
            )
            user = profile
            statusMessage = "Profile updated."
            isLoading = false
            return true
        } catch {
            errorMessage = error.localizedDescription
            isLoading = false
            return false
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

    func signOut() async {
        isLoading = true

        await PushNotificationManager.shared.unregisterCurrentDevice(
            accessToken: accessToken
        )

        if let refreshToken {
            do {
                let _: EmptyResponse = try await api.post(
                    "/auth/auth/logout/",
                    body: LogoutRequest(refresh: refreshToken),
                    accessToken: accessToken
                )
            } catch {
                // Match the web client: backend logout failure should not trap
                // the user in a stale local session.
            }
        }

        GIDSignIn.sharedInstance.signOut()
        PushNotificationManager.shared.updateBadgeCount(0)
        clearSession()
        statusMessage = "Signed out."
        isLoading = false
    }

    private func requestGoogleIDToken(presenting viewController: UIViewController) async throws -> String {
        try await withCheckedThrowingContinuation { continuation in
            GIDSignIn.sharedInstance.signIn(withPresenting: viewController) { result, error in
                if let error {
                    continuation.resume(throwing: error)
                    return
                }

                guard let idToken = result?.user.idToken?.tokenString else {
                    continuation.resume(
                        throwing: APIError.decodingFailed(
                            "Google sign-in did not return an ID token."
                        )
                    )
                    return
                }

                continuation.resume(returning: idToken)
            }
        }
    }

    private static func isGoogleSignInCancellation(_ error: Error) -> Bool {
        let nsError = error as NSError
        return nsError.domain == kGIDSignInErrorDomain && nsError.code == -5
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
        do {
            try keychain.set(access, for: "accessToken")
            try keychain.set(refresh, for: "refreshToken")
        } catch {
            #if DEBUG
            guard AppConfig.isLocalBackend else {
                throw error
            }
            #else
            throw error
            #endif
        }

        accessToken = access
        refreshToken = refresh
        self.user = user
        isAuthenticated = true
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

        if let url = URL(string: trimmed), let key = confirmationKey(from: url) {
            return key
        }

        return trimmed
    }

    private static func confirmationKey(from url: URL) -> String? {
        if
            let components = URLComponents(url: url, resolvingAgainstBaseURL: false),
            let key = components.queryItems?.first(where: { $0.name == "key" })?.value,
            !key.isEmpty
        {
            return key
        }

        let pathComponents = url.pathComponents.filter { $0 != "/" }

        if url.scheme?.lowercased() == "drawtwo" {
            if url.host?.lowercased() == "login", let key = pathComponents.last {
                return key
            }

            if let host = url.host, !host.isEmpty {
                return host
            }
        }

        if
            let index = pathComponents.firstIndex(of: "login"),
            pathComponents.indices.contains(index + 1)
        {
            return pathComponents[index + 1]
        }

        if
            let index = pathComponents.firstIndex(of: "email-confirm"),
            pathComponents.indices.contains(index + 1)
        {
            return pathComponents[index + 1]
        }

        return pathComponents.last
    }
}
