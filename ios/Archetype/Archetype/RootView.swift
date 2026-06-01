import SwiftUI

struct RootView: View {
    @EnvironmentObject private var authStore: AuthStore

    var body: some View {
        Group {
            if authStore.isRestoringSession {
                ArchetypeScreen {
                    VStack(spacing: 16) {
                        ProgressView()
                            .tint(ArchetypeTheme.gold2)
                        Text("Restoring Session")
                            .font(.archetypeBody(16, weight: .bold))
                            .foregroundStyle(ArchetypeTheme.text)
                    }
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
                }
            } else if authStore.isAuthenticated {
                DashboardView()
            } else {
                LoginView()
            }
        }
    }
}
