import AuthenticationServices
import SwiftUI
import UIKit

enum LoginInitialMode {
    case login
    case signup
    case confirm

    static var configuredDefault: LoginInitialMode {
        #if DEBUG
        switch AppConfig.initialLoginMode {
        case "signup":
            return .signup
        case "confirm":
            return .confirm
        default:
            return .login
        }
        #else
        return .login
        #endif
    }
}

struct LoginView: View {
    @EnvironmentObject private var authStore: AuthStore

    private let onClose: (() -> Void)?

    @State private var email = ""
    @State private var username = ""
    @State private var confirmationKey = ""
    @State private var isSignUp: Bool
    @State private var showConfirmationForm: Bool

    init(initialMode: LoginInitialMode? = nil, onClose: (() -> Void)? = nil) {
        let resolvedMode = initialMode ?? LoginInitialMode.configuredDefault
        self.onClose = onClose
        _isSignUp = State(initialValue: resolvedMode == .signup)
        _showConfirmationForm = State(initialValue: resolvedMode == .confirm)
    }

    private var trimmedEmail: String {
        email.trimmingCharacters(in: .whitespacesAndNewlines)
    }

    private var trimmedUsername: String {
        username.trimmingCharacters(in: .whitespacesAndNewlines)
    }

    private var trimmedConfirmationKey: String {
        confirmationKey.trimmingCharacters(in: .whitespacesAndNewlines)
    }

    private var canSubmitEmail: Bool {
        !trimmedEmail.isEmpty && !authStore.isLoading
    }

    private var canConfirmEmail: Bool {
        !trimmedConfirmationKey.isEmpty && !authStore.isLoading
    }

    var body: some View {
        NavigationStack {
            ArchetypeScreen {
                ScrollView {
                    VStack(spacing: 0) {
                        loginTopBar
                            .padding(.horizontal, 18)
                            .padding(.top, 6)
                            .padding(.bottom, 16)

                        VStack(spacing: 18) {
                            LoginTitleMark(isSignUp: isSignUp)
                            authCard
                            loginUtilityActions
                        }
                        .frame(maxWidth: 390)
                        .frame(maxWidth: .infinity)
                        .padding(.horizontal, 18)
                        .padding(.top, 188)
                        .padding(.bottom, 36)
                    }
                }
            }
            .toolbar(.hidden, for: .navigationBar)
        }
        .onAppear {
            recordCaptureState()
        }
        .onChange(of: isSignUp) { _, _ in
            recordCaptureState()
        }
        .onChange(of: showConfirmationForm) { _, _ in
            recordCaptureState()
        }
    }

    private func recordCaptureState() {
        let screen = showConfirmationForm
            ? "login-confirm"
            : (isSignUp ? "login-signup" : "login")
        CaptureStateRecorder.record(screen)
    }

    private var loginTopBar: some View {
        HStack(spacing: 10) {
            if let onClose {
                Button(action: onClose) {
                    Image(systemName: "chevron.left")
                }
                .buttonStyle(IconGameButtonStyle())
                .accessibilityLabel("Back")
            }

            DrawTwoLogoMark()
                .frame(width: 34, height: 34, alignment: .leading)

            Spacer()

            Button {
                withAnimation(.snappy) {
                    isSignUp.toggle()
                    showConfirmationForm = false
                }
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

    private var authCard: some View {
        VStack(alignment: .leading, spacing: 22) {
            feedback

            VStack(alignment: .leading, spacing: 8) {
                WebLoginLabel("Email Address")
                WebLoginField(
                    placeholder: "Enter your email",
                    text: $email,
                    keyboardType: .emailAddress
                )
                .textContentType(.emailAddress)
                .submitLabel(.send)
                .onSubmit(submitEmail)
                .disabled(authStore.isLoading)
            }

            if isSignUp {
                VStack(alignment: .leading, spacing: 8) {
                    WebLoginLabel("Username (Optional)")
                    WebLoginField(
                        placeholder: "Choose a username for multiplayer",
                        text: $username
                    )
                    .textContentType(.username)
                    .submitLabel(.send)
                    .onSubmit(submitEmail)
                    .disabled(authStore.isLoading)

                    Text("Optional - you can add this later for multiplayer features")
                        .font(.archetypeBody(12))
                        .foregroundStyle(ArchetypeTheme.muted)
                }
            }

            Button {
                submitEmail()
            } label: {
                LoadingButtonLabel(
                    isLoading: authStore.isLoading,
                    loadingText: "Please wait...",
                    text: isSignUp ? "Sign Up" : "Send Login Link"
                )
            }
            .buttonStyle(PrimaryGameButtonStyle())
            .disabled(!canSubmitEmail)
            .opacity(canSubmitEmail ? 1 : 0.55)

            LoginDivider(text: "or")

            Button {
                startGoogleSignIn()
            } label: {
                GoogleLoginLabel()
            }
            .buttonStyle(GoogleLoginButtonStyle())
            .disabled(authStore.isLoading)

            appleSignInButton

            if showConfirmationForm {
                confirmationForm
            }

            Button {
                withAnimation(.snappy) {
                    isSignUp.toggle()
                    showConfirmationForm = false
                }
            } label: {
                Text(isSignUp ? "Already have an account? Sign in" : "New to DrawTwo? Create an account")
                    .font(.archetypeBody(14, weight: .medium))
                    .foregroundStyle(ArchetypeTheme.gold2)
                    .frame(maxWidth: .infinity)
            }
            .buttonStyle(.plain)
        }
        .padding(32)
        .background(ArchetypeTheme.panel)
        .overlay(
            RoundedRectangle(cornerRadius: 16)
                .stroke(ArchetypeTheme.border, lineWidth: 1)
        )
        .clipShape(RoundedRectangle(cornerRadius: 16))
        .shadow(color: Color.black.opacity(0.12), radius: 3, x: 0, y: 1)
    }

    private var loginUtilityActions: some View {
        VStack(spacing: 12) {
            #if DEBUG
            if AppConfig.showsManualLoginLinkShortcut && !showConfirmationForm {
                Button {
                    withAnimation(.snappy) {
                        showConfirmationForm = true
                    }
                } label: {
                    Text("I have a login link")
                        .font(.archetypeBody(13, weight: .medium))
                        .foregroundStyle(ArchetypeTheme.muted)
                }
                .buttonStyle(.plain)
                .disabled(authStore.isLoading)
            }

            if AppConfig.showsLocalAccountShortcut {
                Button {
                    Task {
                        await authStore.signInWithLocalAccount()
                    }
                } label: {
                    Text("Use Local Test Account")
                        .font(.archetypeBody(12, weight: .medium))
                        .foregroundStyle(ArchetypeTheme.muted.opacity(0.85))
                }
                .buttonStyle(.plain)
                .disabled(authStore.isLoading)
                .opacity(authStore.isLoading ? 0.55 : 1)
            }
            #endif
        }
        .frame(maxWidth: .infinity)
    }

    private var confirmationForm: some View {
        VStack(alignment: .leading, spacing: 14) {
            VStack(alignment: .leading, spacing: 8) {
                WebLoginLabel("Confirmation Key")
                WebLoginField(
                    placeholder: "Paste confirmation URL or key",
                    text: $confirmationKey,
                    axis: .vertical
                )
                .submitLabel(.go)
                .onSubmit(confirmEmail)
                .disabled(authStore.isLoading)
            }

            Button {
                confirmEmail()
            } label: {
                LoadingButtonLabel(
                    isLoading: authStore.isLoading,
                    loadingText: "Please wait...",
                    text: "Continue"
                )
            }
            .buttonStyle(SecondaryGameButtonStyle())
            .disabled(!canConfirmEmail)
            .opacity(canConfirmEmail ? 1 : 0.55)
        }
    }

    private var appleSignInButton: some View {
        SignInWithAppleButton(.continue) { request in
            request.requestedScopes = [.email]
        } onCompletion: { result in
            handleAppleSignInCompletion(result)
        }
        .signInWithAppleButtonStyle(.white)
        .frame(height: 46)
        .clipShape(RoundedRectangle(cornerRadius: ArchetypeTheme.controlRadius))
        .allowsHitTesting(!authStore.isLoading)
        .opacity(authStore.isLoading ? 0.55 : 1)
    }

    @ViewBuilder
    private var feedback: some View {
        if let status = authStore.statusMessage {
            AuthMessage(text: status, color: ArchetypeTheme.green)
        }

        if let error = authStore.errorMessage {
            AuthMessage(text: error, color: ArchetypeTheme.red)
        }
    }

    private func handleAppleSignInCompletion(_ result: Result<ASAuthorization, Error>) {
        switch result {
        case .success(let authorization):
            guard
                let credential = authorization.credential as? ASAuthorizationAppleIDCredential,
                let tokenData = credential.identityToken,
                let identityToken = String(data: tokenData, encoding: .utf8)
            else {
                authStore.statusMessage = nil
                authStore.errorMessage = "Apple sign-in did not return an identity token."
                return
            }

            Task {
                await authStore.signInWithApple(identityToken: identityToken)
            }

        case .failure(let error):
            let nsError = error as NSError
            if
                nsError.domain == ASAuthorizationError.errorDomain,
                nsError.code == ASAuthorizationError.Code.canceled.rawValue
            {
                return
            }

            authStore.statusMessage = nil
            authStore.errorMessage = error.localizedDescription
        }
    }

    private func submitEmail() {
        guard canSubmitEmail else {
            return
        }

        Task {
            if isSignUp {
                let registered = await authStore.register(
                    email: trimmedEmail,
                    username: trimmedUsername
                )
                if registered {
                    isSignUp = false
                    showConfirmationForm = true
                }
            } else {
                await authStore.sendLoginLink(email: trimmedEmail)
                showConfirmationForm = true
            }
        }
    }

    private func confirmEmail() {
        guard canConfirmEmail else {
            return
        }

        Task {
            await authStore.confirmEmail(key: trimmedConfirmationKey)
        }
    }

    private func startGoogleSignIn() {
        guard let viewController = UIApplication.shared.archetypeTopViewController else {
            authStore.statusMessage = nil
            authStore.errorMessage = "Google sign-in could not open."
            return
        }

        Task {
            await authStore.signInWithGoogle(presenting: viewController)
        }
    }
}

private extension UIApplication {
    var archetypeTopViewController: UIViewController? {
        connectedScenes
            .compactMap { $0 as? UIWindowScene }
            .flatMap(\.windows)
            .first(where: \.isKeyWindow)?
            .rootViewController?
            .archetypeTopPresentedViewController
    }
}

private extension UIViewController {
    var archetypeTopPresentedViewController: UIViewController {
        if let navigationController = self as? UINavigationController {
            return navigationController.visibleViewController?
                .archetypeTopPresentedViewController ?? navigationController
        }

        if let tabBarController = self as? UITabBarController {
            return tabBarController.selectedViewController?
                .archetypeTopPresentedViewController ?? tabBarController
        }

        if let presentedViewController {
            return presentedViewController.archetypeTopPresentedViewController
        }

        return self
    }
}

private struct LoginTitleMark: View {
    let isSignUp: Bool

    var body: some View {
        Text(isSignUp ? "Create your account" : "Welcome back")
            .font(.archetypeDisplay(24, weight: .bold))
            .foregroundStyle(ArchetypeTheme.text)
            .multilineTextAlignment(.center)
            .frame(maxWidth: .infinity)
    }
}

private struct LoginDivider: View {
    let text: String

    var body: some View {
        ZStack {
            Rectangle()
                .fill(ArchetypeTheme.border)
                .frame(height: 1)

            Text(text)
                .font(.archetypeBody(12, weight: .medium))
                .foregroundStyle(ArchetypeTheme.muted)
                .lineLimit(1)
                .padding(.horizontal, 8)
                .background(ArchetypeTheme.background)
        }
        .accessibilityHidden(true)
    }
}

private struct WebLoginLabel: View {
    let text: String

    init(_ text: String) {
        self.text = text
    }

    var body: some View {
        Text(text)
            .font(.archetypeBody(14, weight: .medium))
            .foregroundStyle(Color(hex: 0xD1D5DB))
    }
}

private struct WebLoginField: View {
    let placeholder: String
    @Binding var text: String
    var axis: Axis = .horizontal
    var keyboardType: UIKeyboardType = .default

    var body: some View {
        TextField(placeholder, text: $text, axis: axis)
            .font(.archetypeBody(14))
            .keyboardType(keyboardType)
            .textInputAutocapitalization(.never)
            .autocorrectionDisabled()
            .foregroundStyle(ArchetypeTheme.text)
            .tint(ArchetypeTheme.gold2)
            .lineLimit(axis == .vertical ? 2...4 : 1...1)
            .padding(.horizontal, 12)
            .padding(.vertical, 13)
            .background(ArchetypeTheme.panel)
            .overlay(
                RoundedRectangle(cornerRadius: ArchetypeTheme.controlRadius)
                    .stroke(Color(hex: 0x4B5563), lineWidth: 1)
            )
            .clipShape(RoundedRectangle(cornerRadius: ArchetypeTheme.controlRadius))
    }
}

private struct LegalLinks: View {
    var body: some View {
        HStack(spacing: 12) {
            Link("Privacy Policy", destination: URL(string: "https://drawtwo.com/privacy")!)
            Text("/")
                .foregroundStyle(ArchetypeTheme.muted.opacity(0.65))
            Link("Terms of Service", destination: URL(string: "https://drawtwo.com/terms")!)
        }
        .font(.archetypeBody(12, weight: .medium))
        .foregroundStyle(ArchetypeTheme.muted)
        .frame(maxWidth: .infinity)
        .padding(.top, 2)
    }
}

private struct GoogleLoginLabel: View {
    var body: some View {
        HStack(spacing: 10) {
            GoogleGlyph()

            Text("Continue with Google")
                .font(.archetypeBody(14, weight: .medium))
        }
        .frame(maxWidth: .infinity)
    }
}

private struct GoogleGlyph: View {
    var body: some View {
        Canvas { context, size in
            let lineWidth = size.width * 0.18
            let radius = min(size.width, size.height) * 0.36
            let center = CGPoint(x: size.width / 2, y: size.height / 2)
            let style = StrokeStyle(lineWidth: lineWidth, lineCap: .round, lineJoin: .round)

            func strokeArc(from start: Double, to end: Double, color: Color) {
                var path = Path()
                path.addArc(
                    center: center,
                    radius: radius,
                    startAngle: .degrees(start),
                    endAngle: .degrees(end),
                    clockwise: false
                )
                context.stroke(path, with: .color(color), style: style)
            }

            strokeArc(from: -30, to: 48, color: Color(hex: 0x4285F4))
            strokeArc(from: 48, to: 138, color: Color(hex: 0x34A853))
            strokeArc(from: 138, to: 206, color: Color(hex: 0xFBBC05))
            strokeArc(from: 206, to: 330, color: Color(hex: 0xEA4335))

            var crossbar = Path()
            crossbar.move(to: CGPoint(x: center.x + radius * 0.18, y: center.y))
            crossbar.addLine(to: CGPoint(x: size.width - lineWidth * 0.85, y: center.y))
            context.stroke(crossbar, with: .color(Color(hex: 0x4285F4)), style: style)
        }
        .frame(width: 20, height: 20)
        .accessibilityHidden(true)
    }
}

private struct GoogleLoginButtonStyle: ButtonStyle {
    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .foregroundStyle(Color(hex: 0xD1D5DB))
            .padding(.horizontal, 14)
            .padding(.vertical, 12)
            .background(configuration.isPressed ? ArchetypeTheme.pressedSurface : ArchetypeTheme.panel)
            .overlay(
                RoundedRectangle(cornerRadius: ArchetypeTheme.controlRadius)
                    .stroke(Color(hex: 0x4B5563), lineWidth: 1)
            )
            .clipShape(RoundedRectangle(cornerRadius: ArchetypeTheme.controlRadius))
            .scaleEffect(configuration.isPressed ? 0.98 : 1)
    }
}

private struct LoadingButtonLabel: View {
    let isLoading: Bool
    let loadingText: String
    let text: String

    var body: some View {
        HStack(spacing: 8) {
            if isLoading {
                ProgressView()
                    .tint(.white)
            }
            Text(isLoading ? loadingText : text)
        }
        .frame(maxWidth: .infinity)
    }
}

private struct AuthMessage: View {
    let text: String
    let color: Color

    var body: some View {
        Text(text)
            .font(.archetypeBody(14))
            .foregroundStyle(color)
            .padding(14)
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(color.opacity(0.14))
            .overlay(
                RoundedRectangle(cornerRadius: ArchetypeTheme.controlRadius)
                    .stroke(color.opacity(0.38), lineWidth: 1)
            )
            .clipShape(RoundedRectangle(cornerRadius: ArchetypeTheme.controlRadius))
    }
}
