import Foundation

enum AppConfig {
    static let titleSlug = "archetype"
    static let backendBaseURL = URL(string: "https://drawtwo.com")!
    static let apiBaseURL = backendBaseURL.appendingPathComponent("api")
    static let websocketBaseURL = URL(string: "wss://drawtwo.com")!
}
