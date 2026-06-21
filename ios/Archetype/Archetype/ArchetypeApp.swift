import GoogleSignIn
import SwiftUI

@main
struct ArchetypeApp: App {
    @StateObject private var authStore = AuthStore()

    init() {
        FontRegistry.registerBundledFonts()
        #if DEBUG
        if let initialTheme = AppConfig.initialThemePreference {
            UserDefaults.standard.set(initialTheme, forKey: "archetype.theme")
        }
        #endif
    }

    var body: some Scene {
        WindowGroup {
            RootView()
                .environmentObject(authStore)
                .onOpenURL { url in
                    if GIDSignIn.sharedInstance.handle(url) {
                        return
                    }

                    handleLoginURL(url)
                }
                .onContinueUserActivity(NSUserActivityTypeBrowsingWeb) { activity in
                    guard let url = activity.webpageURL else {
                        return
                    }

                    handleLoginURL(url)
                }
                .task {
                    await authStore.restoreSession()
                    #if DEBUG
                    if AppConfig.localAutoSignInEnabled && !authStore.isAuthenticated {
                        await authStore.signInWithLocalAccount()
                    }
                    #endif
                }
        }
    }

    private func handleLoginURL(_ url: URL) {
        Task {
            await authStore.confirmEmail(fromLoginURL: url)
        }
    }
}
