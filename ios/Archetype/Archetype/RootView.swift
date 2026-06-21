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
                IntroLandingView()
            }
        }
    }
}

private enum GuestRoute: Hashable {
    case introGame(id: Int, accessToken: String)
}

private struct IntroLandingView: View {
    @State private var path: [GuestRoute] = []
    @State private var isStartingIntro = false
    @State private var isShowingLogin = false
    @State private var loginMode: LoginInitialMode = .login
    @State private var errorMessage: String?

    var body: some View {
        NavigationStack(path: $path) {
            ArchetypeScreen {
                ScrollView {
                    VStack(spacing: 0) {
                        topBar
                            .padding(.horizontal, 18)
                            .padding(.top, 6)
                            .padding(.bottom, 20)

                        VStack(spacing: 26) {
                            Spacer(minLength: 42)

                            IntroTitleBanner()
                                .frame(maxWidth: 430)

                            Text("by DrawTwo")
                                .font(.archetypeBody(18, weight: .semibold))
                                .foregroundStyle(ArchetypeTheme.muted)
                                .frame(maxWidth: .infinity)

                            VStack(spacing: 12) {
                                Button(action: startIntroGame) {
                                    HStack(spacing: 10) {
                                        if isStartingIntro {
                                            ProgressView()
                                                .tint(.white)
                                        }

                                        Text(isStartingIntro ? "Loading..." : "Play")
                                    }
                                    .frame(maxWidth: .infinity)
                                }
                                .buttonStyle(PrimaryGameButtonStyle())
                                .disabled(isStartingIntro)
                                .opacity(isStartingIntro ? 0.7 : 1)

                                if let errorMessage {
                                    Text(errorMessage)
                                        .font(.archetypeBody(12))
                                        .foregroundStyle(ArchetypeTheme.red)
                                        .multilineTextAlignment(.center)
                                        .fixedSize(horizontal: false, vertical: true)
                                }
                            }
                            .frame(maxWidth: 290)

                            Spacer(minLength: 120)
                        }
                        .padding(.horizontal, 24)
                    }
                    .frame(maxWidth: .infinity)
                }
            }
            .toolbar(.hidden, for: .navigationBar)
            .navigationDestination(for: GuestRoute.self) { route in
                switch route {
                case .introGame(let id, let accessToken):
                    GameDetailView(
                        gameId: id,
                        guestAccessToken: accessToken,
                        onOpenIntroGame: replaceIntroGame,
                        onIntroSignUp: openSignUpFromIntro
                    )
                }
            }
            .onAppear {
                CaptureStateRecorder.record("intro-landing")
            }
            .fullScreenCover(isPresented: $isShowingLogin) {
                LoginView(initialMode: loginMode) {
                    isShowingLogin = false
                }
            }
        }
    }

    private var topBar: some View {
        HStack {
            DrawTwoLogoMark()
                .frame(width: 34, height: 34, alignment: .leading)

            Spacer()

            Button {
                showLogin(.login)
            } label: {
                Text("Login / Sign Up")
                    .font(.archetypeBody(14, weight: .semibold))
                    .foregroundStyle(Color.white)
                    .padding(.horizontal, 18)
                    .padding(.vertical, 10)
                    .background(ArchetypeTheme.gold)
                    .clipShape(RoundedRectangle(cornerRadius: ArchetypeTheme.controlRadius))
            }
            .buttonStyle(.plain)
        }
    }

    private func startIntroGame() {
        guard !isStartingIntro else {
            return
        }

        isStartingIntro = true
        errorMessage = nil

        Task {
            do {
                let response: IntroScenarioStartResponse = try await APIClient.shared.post(
                    "/gameplay/scenarios/\(AppConfig.introScenarioSlug)/start/",
                    body: EmptyBody()
                )
                path.append(.introGame(id: response.id, accessToken: response.accessToken))
            } catch {
                errorMessage = "Unable to start the intro game. Please try again."
            }

            isStartingIntro = false
        }
    }

    private func replaceIntroGame(id: Int, accessToken: String) {
        if !path.isEmpty {
            path.removeLast()
        }
        path.append(.introGame(id: id, accessToken: accessToken))
    }

    private func openSignUpFromIntro() {
        showLogin(.signup)
    }

    private func showLogin(_ mode: LoginInitialMode) {
        loginMode = mode
        isShowingLogin = true
    }
}

private struct IntroTitleBanner: View {
    private let bannerURL = URL(string: AppConfig.titleBannerURL)

    var body: some View {
        ZStack {
            if let bannerURL {
                AsyncImage(url: bannerURL) { phase in
                    switch phase {
                    case .success(let image):
                        image
                            .resizable()
                            .scaledToFit()
                    default:
                        fallback
                    }
                }
            } else {
                fallback
            }
        }
        .frame(height: 240)
        .frame(maxWidth: .infinity)
        .accessibilityLabel("Archetype")
    }

    private var fallback: some View {
        Text("Archetype")
            .font(.archetypeTitle(46))
            .foregroundStyle(ArchetypeTheme.text)
            .lineLimit(1)
            .minimumScaleFactor(0.72)
            .frame(maxWidth: .infinity)
    }
}
