import SwiftUI

struct RootView: View {
    @EnvironmentObject private var authStore: AuthStore

    var body: some View {
        Group {
            if authStore.isRestoringSession {
                ProgressView("Restoring session")
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
                    .background(Color(.systemGroupedBackground))
            } else if authStore.isAuthenticated {
                DashboardView()
            } else {
                LoginView()
            }
        }
    }
}
