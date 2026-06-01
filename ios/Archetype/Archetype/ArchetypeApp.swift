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
}
