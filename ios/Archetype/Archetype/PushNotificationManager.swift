import Foundation
import UIKit
import UserNotifications

enum PushNotificationRoute: Equatable {
    case game(Int)
    case friendChallenge
}

final class PushNotificationManager: NSObject, ObservableObject, UNUserNotificationCenterDelegate {
    static let shared = PushNotificationManager()

    @Published private(set) var deviceTokenVersion = 0
    @Published private(set) var pendingRoute: PushNotificationRoute?

    private var deviceToken: String?
    private var authorizationRequested = false
    private var lastRegisteredKey: String?

    private override init() {
        super.init()
    }

    func configure() {
        UNUserNotificationCenter.current().delegate = self
    }

    func requestAuthorizationAndRegister() async {
        if !authorizationRequested {
            authorizationRequested = true
            do {
                let granted = try await UNUserNotificationCenter.current()
                    .requestAuthorization(options: [.alert, .sound, .badge])
                guard granted else {
                    return
                }
            } catch {
                return
            }
        }

        await MainActor.run {
            UIApplication.shared.registerForRemoteNotifications()
        }
    }

    func updateDeviceToken(_ data: Data) {
        let token = data.map { String(format: "%02.2hhx", $0) }.joined()
        DispatchQueue.main.async {
            self.deviceToken = token
            self.lastRegisteredKey = nil
            self.deviceTokenVersion += 1
        }
    }

    func registerCurrentDevice(using authStore: AuthStore) async {
        guard
            let token = await MainActor.run(body: { deviceToken }),
            let userId = await MainActor.run(body: { authStore.user?.id })
        else {
            return
        }

        let key = "\(userId):\(token):\(apnsEnvironment):\(bundleId)"
        if await MainActor.run(body: { lastRegisteredKey == key }) {
            return
        }

        do {
            let _: PushDeviceRegistrationResponse = try await authStore.authenticatedPost(
                "/gameplay/push/devices/",
                body: PushDeviceRegistrationRequest(
                    token: token,
                    platform: "ios",
                    bundleId: bundleId,
                    environment: apnsEnvironment
                )
            )
            await MainActor.run {
                self.lastRegisteredKey = key
            }
        } catch {
            await MainActor.run {
                self.lastRegisteredKey = nil
            }
        }
    }

    func unregisterCurrentDevice(accessToken: String?) async {
        guard
            let accessToken,
            let token = await MainActor.run(body: { deviceToken })
        else {
            return
        }

        do {
            let _: PushDeviceDeactivationResponse = try await APIClient.shared.post(
                "/gameplay/push/devices/current/deactivate/",
                body: PushDeviceDeactivationRequest(
                    token: token,
                    bundleId: bundleId,
                    environment: apnsEnvironment
                ),
                accessToken: accessToken
            )
            await MainActor.run {
                self.lastRegisteredKey = nil
            }
        } catch {
            return
        }
    }

    func applicationDidFailToRegister(error: Error) {
        #if DEBUG
        print("APNs registration failed: \(error.localizedDescription)")
        #endif
    }

    func consumePendingRoute() -> PushNotificationRoute? {
        let route = pendingRoute
        pendingRoute = nil
        return route
    }

    func userNotificationCenter(
        _ center: UNUserNotificationCenter,
        willPresent notification: UNNotification
    ) async -> UNNotificationPresentationOptions {
        [.banner, .sound, .list]
    }

    func userNotificationCenter(
        _ center: UNUserNotificationCenter,
        didReceive response: UNNotificationResponse
    ) async {
        let userInfo = response.notification.request.content.userInfo
        guard let route = Self.route(from: userInfo) else {
            return
        }

        await MainActor.run {
            self.pendingRoute = route
        }
    }

    private static func route(from userInfo: [AnyHashable: Any]) -> PushNotificationRoute? {
        let type = stringValue(userInfo["notification_type"] ?? userInfo["type"])
        if let gameId = intValue(userInfo["game_id"]) {
            return .game(gameId)
        }
        if type == "friend_challenge" {
            return .friendChallenge
        }
        return nil
    }

    private static func intValue(_ value: Any?) -> Int? {
        if let intValue = value as? Int {
            return intValue
        }
        if let number = value as? NSNumber {
            return number.intValue
        }
        if let string = value as? String {
            return Int(string)
        }
        return nil
    }

    private static func stringValue(_ value: Any?) -> String? {
        if let string = value as? String {
            return string
        }
        if let number = value as? NSNumber {
            return number.stringValue
        }
        return nil
    }

    private var bundleId: String {
        Bundle.main.bundleIdentifier ?? ""
    }

    private var apnsEnvironment: String {
        #if DEBUG
        return "sandbox"
        #else
        return "production"
        #endif
    }
}

final class AppDelegate: NSObject, UIApplicationDelegate {
    func application(
        _ application: UIApplication,
        didRegisterForRemoteNotificationsWithDeviceToken deviceToken: Data
    ) {
        PushNotificationManager.shared.updateDeviceToken(deviceToken)
    }

    func application(
        _ application: UIApplication,
        didFailToRegisterForRemoteNotificationsWithError error: Error
    ) {
        PushNotificationManager.shared.applicationDidFailToRegister(error: error)
    }
}
