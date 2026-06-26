import Foundation
import UIKit
import UserNotifications

enum PushNotificationRoute: Equatable {
    case game(Int)
    case friendChallenge
}

struct PushNotificationRouteRequest: Equatable, Identifiable {
    let id: UUID
    let route: PushNotificationRoute

    init(id: UUID = UUID(), route: PushNotificationRoute) {
        self.id = id
        self.route = route
    }
}

final class PushNotificationManager: NSObject, ObservableObject, UNUserNotificationCenterDelegate {
    static let shared = PushNotificationManager()
    static let routeRequestNotification = Notification.Name("PushNotificationRouteRequest")
    static let routeRequestUserInfoKey = "request"

    @Published private(set) var deviceTokenVersion = 0
    private(set) var pendingRouteRequest: PushNotificationRouteRequest?

    private var deviceToken: String?
    private var authorizationRequested = false
    private var lastRegisteredKey: String?

    private override init() {
        super.init()
    }

    func configure() {
        UNUserNotificationCenter.current().delegate = self
    }

    @MainActor
    func applicationDidFinishLaunching(launchOptions: [UIApplication.LaunchOptionsKey: Any]?) {
        configure()

        guard
            let userInfo = launchOptions?[.remoteNotification] as? [AnyHashable: Any]
        else {
            return
        }

        #if DEBUG
        print("Push notification launch userInfo: \(userInfo)")
        #endif

        guard let route = Self.route(from: userInfo) else {
            #if DEBUG
            print("Push notification launch had no route.")
            #endif
            return
        }

        enqueueRouteOnMain(route, source: "launch")
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

    @MainActor
    func completeRouteRequest(id: UUID) {
        guard pendingRouteRequest?.id == id else {
            return
        }
        pendingRouteRequest = nil
    }

    func userNotificationCenter(
        _ center: UNUserNotificationCenter,
        willPresent notification: UNNotification,
        withCompletionHandler completionHandler: @escaping (UNNotificationPresentationOptions) -> Void
    ) {
        completionHandler([.banner, .sound, .list])
    }

    func userNotificationCenter(
        _ center: UNUserNotificationCenter,
        didReceive response: UNNotificationResponse,
        withCompletionHandler completionHandler: @escaping () -> Void
    ) {
        defer {
            completionHandler()
        }

        let userInfo = response.notification.request.content.userInfo
        #if DEBUG
        print("Push notification tap userInfo: \(userInfo)")
        #endif

        guard let route = Self.route(from: userInfo) else {
            #if DEBUG
            print("Push notification tap had no route.")
            #endif
            return
        }

        enqueueRouteOnMain(route, source: "tap")
    }

    private func enqueueRouteOnMain(_ route: PushNotificationRoute, source: String) {
        DispatchQueue.main.async { [weak self] in
            self?.enqueueRoute(route, source: source)
        }
    }

    private func enqueueRoute(_ route: PushNotificationRoute, source: String) {
        let request = PushNotificationRouteRequest(route: route)
        #if DEBUG
        print(
            "Push notification route from \(source): \(route), "
            + "mainThread=\(Thread.isMainThread)"
        )
        #endif
        pendingRouteRequest = request
        NotificationCenter.default.post(
            name: Self.routeRequestNotification,
            object: self,
            userInfo: [Self.routeRequestUserInfoKey: request]
        )
    }

    private static func route(from userInfo: [AnyHashable: Any]) -> PushNotificationRoute? {
        let type = stringValue(
            value(for: "notification_type", in: userInfo)
                ?? value(for: "type", in: userInfo)
        )
        if let gameId = intValue(value(for: "game_id", in: userInfo)) {
            return .game(gameId)
        }
        if type == "friend_challenge" {
            return .friendChallenge
        }
        return nil
    }

    private static func value(for key: String, in userInfo: [AnyHashable: Any]) -> Any? {
        if let value = userInfo[key] {
            return value
        }

        if let data = userInfo["data"] as? [AnyHashable: Any],
           let value = data[key] {
            return value
        }

        if let data = userInfo["data"] as? [String: Any],
           let value = data[key] {
            return value
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
        didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]? = nil
    ) -> Bool {
        PushNotificationManager.shared.applicationDidFinishLaunching(
            launchOptions: launchOptions
        )
        return true
    }

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
