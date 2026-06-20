import Foundation

enum AppConfig {
    static let titleSlug = "archetype"
    static let introScenarioSlug = "intro-archetype-v1"
    static var backendBaseURL: URL {
        configuredURL(named: "ARCHETYPE_BACKEND_BASE_URL")
            ?? URL(string: "https://drawtwo.com")!
    }

    static var apiBaseURL: URL {
        backendBaseURL.appendingPathComponent("api")
    }

    static var websocketBaseURL: URL {
        if let configured = configuredURL(named: "ARCHETYPE_WEBSOCKET_BASE_URL") {
            return configured
        }

        var components = URLComponents(url: backendBaseURL, resolvingAgainstBaseURL: false)
        components?.scheme = backendBaseURL.scheme == "http" ? "ws" : "wss"
        return components?.url ?? URL(string: "wss://drawtwo.com")!
    }

    static var assetBaseURL: URL {
        configuredURL(named: "ARCHETYPE_ASSET_BASE_URL")
            ?? URL(string: "https://assets.drawtwo.com")!
    }

    static var isLocalBackend: Bool {
        guard let host = backendBaseURL.host?.lowercased() else {
            return false
        }

        if host == "localhost" ||
            host == "::1" ||
            host == "host.docker.internal" ||
            host.hasSuffix(".local") {
            return true
        }

        if host.hasPrefix("127.") ||
            host.hasPrefix("10.") ||
            host.hasPrefix("192.168.") ||
            host.hasPrefix("169.254.") {
            return true
        }

        let parts = host.split(separator: ".")
        if
            parts.count == 4,
            parts[0] == "172",
            let secondOctet = Int(parts[1]),
            (16...31).contains(secondOctet)
        {
            return true
        }

        return false
    }

    #if DEBUG
    static var allowsLocalAccountShortcut: Bool {
        isLocalBackend
    }

    static var showsLocalAccountShortcut: Bool {
        allowsLocalAccountShortcut && environmentFlag(named: "ARCHETYPE_SHOW_LOCAL_ACCOUNT_SHORTCUT")
    }

    static var showsManualLoginLinkShortcut: Bool {
        environmentFlag(named: "ARCHETYPE_SHOW_MANUAL_LOGIN_LINK_SHORTCUT")
    }

    static var localAutoSignInEnabled: Bool {
        environmentFlag(named: "ARCHETYPE_AUTO_LOGIN")
    }

    static var localClearSessionOnLaunchEnabled: Bool {
        isLocalBackend && environmentFlag(named: "ARCHETYPE_CLEAR_SESSION")
    }

    static var localTestEmail: String {
        environmentValue(named: "ARCHETYPE_LOCAL_TEST_EMAIL") ?? "ios@devdata.local"
    }

    static var localTestPassword: String {
        environmentValue(named: "ARCHETYPE_LOCAL_TEST_PASSWORD") ?? "password"
    }

    static var initialDashboardSection: String? {
        environmentValue(named: "ARCHETYPE_INITIAL_DASHBOARD_SECTION")?.lowercased()
    }

    static var initialDeckId: Int? {
        environmentValue(named: "ARCHETYPE_INITIAL_DECK_ID").flatMap(Int.init)
    }

    static var initialDeckCardSlug: String? {
        environmentValue(named: "ARCHETYPE_INITIAL_DECK_CARD_SLUG")?.lowercased()
    }

    static var initialCollectionCardSlug: String? {
        environmentValue(named: "ARCHETYPE_INITIAL_COLLECTION_CARD_SLUG")?.lowercased()
    }

    static var initialGameId: Int? {
        environmentValue(named: "ARCHETYPE_INITIAL_GAME_ID").flatMap(Int.init)
    }

    static var initialGameOverlay: String? {
        environmentValue(named: "ARCHETYPE_INITIAL_GAME_OVERLAY")?.lowercased()
    }

    static var initialGameCommand: String? {
        environmentValue(named: "ARCHETYPE_INITIAL_GAME_COMMAND")?.lowercased()
    }

    static var initialProfileMenuOpen: Bool {
        environmentFlag(named: "ARCHETYPE_INITIAL_PROFILE_MENU")
    }

    static var initialProfileEditOpen: Bool {
        environmentFlag(named: "ARCHETYPE_INITIAL_PROFILE_EDIT")
    }

    static var initialProfileUsername: String? {
        environmentValue(named: "ARCHETYPE_INITIAL_PROFILE_USERNAME")
    }

    static var initialProfileUsernameSaveEnabled: Bool {
        environmentFlag(named: "ARCHETYPE_INITIAL_PROFILE_SAVE")
    }

    static var initialThemePreference: String? {
        let value = environmentValue(named: "ARCHETYPE_INITIAL_THEME")?.lowercased()
        guard value == "light" || value == "dark" else {
            return nil
        }

        return value
    }

    static var initialLoginMode: String? {
        let value = environmentValue(named: "ARCHETYPE_INITIAL_LOGIN_MODE")?.lowercased()
        if value == "signup" || value == "sign_up" || value == "register" {
            return "signup"
        }

        if value == "confirm" ||
            value == "confirmation" ||
            value == "login_link" ||
            value == "login-link" {
            return "confirm"
        }

        return nil
    }

    static var queueElapsedSecondsOverride: Int? {
        environmentValue(named: "ARCHETYPE_QUEUE_ELAPSED_SECONDS").flatMap(Int.init)
    }

    static var visualCaptureModeEnabled: Bool {
        environmentFlag(named: "ARCHETYPE_VISUAL_CAPTURE")
    }

    static var captureStateEnabled: Bool {
        environmentFlag(named: "ARCHETYPE_CAPTURE_STATE")
    }
    #endif

    static var titleBannerURL: String {
        assetBaseURL
            .appendingPathComponent("titles")
            .appendingPathComponent(titleSlug)
            .appendingPathComponent("banner.webp")
            .absoluteString
    }

    static func heroArtURL(slug: String?) -> String? {
        guard let slug, !slug.isEmpty else {
            return nil
        }

        return assetBaseURL
            .appendingPathComponent("titles")
            .appendingPathComponent(titleSlug)
            .appendingPathComponent("heroes")
            .appendingPathComponent("\(slug).webp")
            .absoluteString
    }

    static func cardArtURL(slug: String?) -> String? {
        guard let slug, !slug.isEmpty else {
            return nil
        }

        return assetBaseURL
            .appendingPathComponent("titles")
            .appendingPathComponent(titleSlug)
            .appendingPathComponent("cards")
            .appendingPathComponent("\(slug).webp")
            .absoluteString
    }

    private static func configuredURL(named name: String) -> URL? {
        guard let value = environmentValue(named: name) else {
            return nil
        }

        return URL(string: value)
    }

    private static func environmentValue(named name: String) -> String? {
        let trimmed = ProcessInfo.processInfo.environment[name]?
            .trimmingCharacters(in: .whitespacesAndNewlines)
        guard let trimmed, !trimmed.isEmpty else {
            return nil
        }

        return trimmed
    }

    private static func environmentFlag(named name: String) -> Bool {
        guard let value = environmentValue(named: name)?.lowercased() else {
            return false
        }

        return ["1", "true", "yes", "on"].contains(value)
    }
}

enum CaptureStateRecorder {
    static let fileName = "archetype_capture_state.json"

    static func record(_ screen: String, detail: [String: String] = [:]) {
        #if DEBUG
        guard AppConfig.captureStateEnabled else {
            return
        }

        var payload = detail
        payload["screen"] = screen
        payload["timestamp"] = ISO8601DateFormatter().string(from: Date())

        guard JSONSerialization.isValidJSONObject(payload),
              let data = try? JSONSerialization.data(
                withJSONObject: payload,
                options: [.sortedKeys]
              ),
              let directory = FileManager.default.urls(
                for: .documentDirectory,
                in: .userDomainMask
              ).first
        else {
            return
        }

        try? data.write(to: directory.appendingPathComponent(fileName), options: [.atomic])
        #endif
    }
}
