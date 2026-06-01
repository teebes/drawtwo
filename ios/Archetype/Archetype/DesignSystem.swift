import SwiftUI
import UIKit

enum ArchetypeTheme {
    static var ink: Color { adaptive(light: 0xFFFFFF, dark: 0x111827) }
    static var ink2: Color { adaptive(light: 0xF3F4F6, dark: 0x1F2937) }
    static var panel: Color { adaptive(light: 0xFFFFFF, dark: 0x1F2937) }
    static var panel2: Color { adaptive(light: 0xFFFFFF, dark: 0x111827) }
    static var border: Color { adaptive(light: 0xE5E7EB, dark: 0x374151) }
    static var text: Color { adaptive(light: 0x111827, dark: 0xF8FAFC) }
    static var muted: Color { adaptive(light: 0x6B7280, dark: 0x9CA3AF) }
    static let gold = Color(hex: 0xD97706)
    static let gold2 = Color(hex: 0xF59E0B)
    static let sky = Color(hex: 0x0EA5E9)
    static let sky600 = Color(hex: 0x0284C7)
    static let violet = Color(hex: 0x8B5CF6)
    static let green = Color(hex: 0x22C55E)
    static let green600 = Color(hex: 0x16A34A)
    static let red = Color(hex: 0xEF4444)
    static let surfaceRadius: CGFloat = 8
    static let controlRadius: CGFloat = 8

    static var background: Color { adaptive(light: 0xF9FAFB, dark: 0x111827) }
    static var subtleSurface: Color {
        adaptive(light: 0xF3F4F6, dark: 0xFFFFFF, lightAlpha: 1, darkAlpha: 0.055)
    }
    static var inputSurface: Color {
        adaptive(light: 0xFFFFFF, dark: 0x000000, lightAlpha: 1, darkAlpha: 0.22)
    }
    static var pressedSurface: Color {
        adaptive(light: 0xF3F4F6, dark: 0xFFFFFF, lightAlpha: 1, darkAlpha: 0.07)
    }
    static var secondaryText: Color { adaptive(light: 0x374151, dark: 0xE5E7EB) }
    static var bannerBackground: Color { adaptive(light: 0xE5E7EB, dark: 0xD1D5DB) }
    static var bannerForeground: Color { Color(hex: 0x111827) }

    static var panelGradient: LinearGradient {
        LinearGradient(
            colors: [
                panel,
                panel,
            ],
            startPoint: .topLeading,
            endPoint: .bottomTrailing
        )
    }

    static let goldGradient = LinearGradient(
        colors: [gold2, gold],
        startPoint: .topLeading,
        endPoint: .bottomTrailing
    )

    private static func adaptive(
        light: UInt,
        dark: UInt,
        lightAlpha: CGFloat = 1,
        darkAlpha: CGFloat = 1
    ) -> Color {
        Color(
            uiColor: UIColor { traits in
                traits.userInterfaceStyle == .dark
                    ? UIColor(hex: dark, alpha: darkAlpha)
                    : UIColor(hex: light, alpha: lightAlpha)
            }
        )
    }
}

extension Color {
    init(hex: UInt, alpha: Double = 1) {
        self.init(
            .sRGB,
            red: Double((hex >> 16) & 0xFF) / 255,
            green: Double((hex >> 8) & 0xFF) / 255,
            blue: Double(hex & 0xFF) / 255,
            opacity: alpha
        )
    }
}

extension UIColor {
    convenience init(hex: UInt, alpha: CGFloat = 1) {
        self.init(
            red: CGFloat((hex >> 16) & 0xFF) / 255,
            green: CGFloat((hex >> 8) & 0xFF) / 255,
            blue: CGFloat(hex & 0xFF) / 255,
            alpha: alpha
        )
    }
}

enum ArchetypeFontWeight {
    case regular
    case medium
    case semibold
    case bold
    case black
}

extension Font {
    static func archetypeTitle(_ size: CGFloat) -> Font {
        .custom("CinzelRoman-Black", size: size)
    }

    static func archetypeDisplay(_ size: CGFloat, weight: ArchetypeFontWeight = .bold) -> Font {
        switch weight {
        case .regular, .medium:
            return .custom("Cinzel-Regular", size: size)
        case .semibold, .bold:
            return .custom("CinzelRoman-Bold", size: size)
        case .black:
            return .custom("CinzelRoman-Black", size: size)
        }
    }

    static func archetypeBody(_ size: CGFloat, weight: ArchetypeFontWeight = .regular) -> Font {
        switch weight {
        case .regular:
            return .custom("Inter-Regular", size: size)
        case .medium:
            return .custom("Inter-Regular_Medium", size: size)
        case .semibold:
            return .custom("Inter-Regular_SemiBold", size: size)
        case .bold:
            return .custom("Inter-Regular_Bold", size: size)
        case .black:
            return .custom("Inter-Regular_Black", size: size)
        }
    }

    static func archetypeSection() -> Font {
        .archetypeBody(13, weight: .bold)
    }
}

struct ArchetypeScreen<Content: View>: View {
    @AppStorage("archetype.theme") private var themePreference = "dark"
    private let content: Content

    init(@ViewBuilder content: () -> Content) {
        self.content = content()
    }

    var body: some View {
        ZStack {
            ArchetypeTheme.background
                .ignoresSafeArea()

            content
                .frame(maxWidth: .infinity, maxHeight: .infinity)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .preferredColorScheme(themePreference == "light" ? .light : .dark)
        .font(.archetypeBody(17))
    }
}

struct TopSafeAreaScrim: View {
    var body: some View {
        GeometryReader { proxy in
            ArchetypeTheme.background
                .frame(height: proxy.safeAreaInsets.top)
                .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .top)
                .ignoresSafeArea(edges: .top)
        }
        .allowsHitTesting(false)
    }
}

struct ArchetypePanel<Content: View>: View {
    private let content: Content
    private let padding: CGFloat

    init(padding: CGFloat = 16, @ViewBuilder content: () -> Content) {
        self.padding = padding
        self.content = content()
    }

    var body: some View {
        content
            .padding(padding)
            .background(ArchetypeTheme.panelGradient)
            .overlay(
                RoundedRectangle(cornerRadius: ArchetypeTheme.surfaceRadius)
                    .stroke(ArchetypeTheme.border, lineWidth: 1)
            )
            .clipShape(RoundedRectangle(cornerRadius: ArchetypeTheme.surfaceRadius))
            .shadow(color: Color.black.opacity(0.14), radius: 4, x: 0, y: 1)
    }
}

struct SectionTitle: View {
    let title: String
    var accessory: String?

    var body: some View {
        HStack {
            Text(title.uppercased())
                .font(.archetypeSection())
                .foregroundStyle(ArchetypeTheme.muted)

            Spacer()

            if let accessory {
                Text(accessory.uppercased())
                    .font(.archetypeBody(11, weight: .semibold))
                    .foregroundStyle(ArchetypeTheme.gold2)
            }
        }
        .padding(.horizontal, 2)
    }
}

struct StatusPill: View {
    let text: String
    var color: Color = ArchetypeTheme.sky

    var body: some View {
        Text(text.uppercased())
            .font(.archetypeBody(11, weight: .bold))
            .foregroundStyle(color)
            .padding(.horizontal, 10)
            .padding(.vertical, 6)
            .background(color.opacity(0.14))
            .overlay(
                Capsule()
                    .stroke(color.opacity(0.38), lineWidth: 1)
            )
            .clipShape(Capsule())
    }
}

struct MetricPill: View {
    let label: String
    let value: String

    var body: some View {
        VStack(alignment: .leading, spacing: 3) {
            Text(label.uppercased())
                .font(.archetypeBody(9, weight: .bold))
                .foregroundStyle(ArchetypeTheme.muted)
            Text(value)
                .font(.archetypeBody(17, weight: .bold))
                .foregroundStyle(ArchetypeTheme.text)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(12)
        .background(ArchetypeTheme.subtleSurface)
        .clipShape(RoundedRectangle(cornerRadius: ArchetypeTheme.controlRadius))
    }
}

struct EmptyState: View {
    let title: String
    let detail: String
    let systemImage: String

    var body: some View {
        VStack(spacing: 10) {
            Image(systemName: systemImage)
                .font(.system(size: 24, weight: .semibold))
                .foregroundStyle(ArchetypeTheme.gold2)
            Text(title)
                .font(.archetypeBody(17, weight: .semibold))
                .foregroundStyle(ArchetypeTheme.text)
            Text(detail)
                .font(.archetypeBody(12))
                .multilineTextAlignment(.center)
                .foregroundStyle(ArchetypeTheme.muted)
        }
        .frame(maxWidth: .infinity)
        .padding(.vertical, 24)
    }
}

struct ArchetypePageHeader: View {
    let title: String
    var subtitle: String?

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(title)
                .font(.archetypeTitle(42))
                .foregroundStyle(ArchetypeTheme.text)
                .frame(maxWidth: .infinity, alignment: .leading)

            if let subtitle, !subtitle.isEmpty {
                Text(subtitle)
                    .font(.archetypeBody(14))
                    .foregroundStyle(ArchetypeTheme.muted)
                    .fixedSize(horizontal: false, vertical: true)
            }
        }
        .padding(.top, 4)
    }
}

struct ArchetypePageBanner: View {
    let title: String
    var foregroundColor: Color = ArchetypeTheme.bannerForeground

    var body: some View {
        Text(title)
            .font(.archetypeDisplay(36, weight: .bold))
            .foregroundStyle(foregroundColor)
            .lineLimit(1)
            .minimumScaleFactor(0.72)
            .frame(maxWidth: .infinity)
            .frame(height: 96)
            .background(ArchetypeTheme.bannerBackground)
    }
}

struct ArchetypeCardDetailHeader: View {
    let title: String

    var body: some View {
        Text(title)
            .font(.archetypeDisplay(36, weight: .bold))
            .foregroundStyle(ArchetypeTheme.text)
            .lineLimit(1)
            .minimumScaleFactor(0.72)
            .frame(maxWidth: .infinity)
            .frame(height: 96)
            .background(ArchetypeTheme.panel)
    }
}

struct ArchetypeBreadcrumb: View {
    var title: String = "Archetype"

    var body: some View {
        HStack(spacing: 8) {
            DrawTwoLogoMark()

            Text("/")
                .font(.archetypeBody(15, weight: .semibold))
                .foregroundStyle(ArchetypeTheme.muted)

            Text(title.uppercased())
                .font(.archetypeDisplay(18, weight: .semibold))
                .foregroundStyle(Color(hex: 0x38BDF8))
                .lineLimit(1)
                .minimumScaleFactor(0.72)
        }
    }
}

struct DrawTwoLogoMark: View {
    var size: CGFloat = 32

    var body: some View {
        Group {
            if let logoImage = Self.logoImage {
                Image(uiImage: logoImage)
                    .resizable()
                    .scaledToFit()
            } else {
                Image(systemName: "rectangle.portrait.on.rectangle.portrait.angled")
                    .font(.system(size: size * 0.48, weight: .medium))
                    .foregroundStyle(ArchetypeTheme.muted)
            }
        }
        .frame(width: size, height: size)
        .clipShape(RoundedRectangle(cornerRadius: min(8, size * 0.25)))
        .accessibilityHidden(true)
    }

    private static let logoImage: UIImage? = {
        guard let url = Bundle.main.url(forResource: "drawtwo_logo", withExtension: "png") else {
            return UIImage(named: "drawtwo_logo")
        }

        return UIImage(contentsOfFile: url.path)
    }()
}

struct DrawTwoCardBackFill: View {
    var logoSize: CGFloat
    var showsWordmark = false

    var body: some View {
        GeometryReader { proxy in
            let width = proxy.size.width
            let height = proxy.size.height
            let insetX = width * 0.06
            let insetY = height * 0.043
            let strokeWidth = max(1.5, min(width, height) * 0.017)

            ZStack {
                Color(hex: 0xD1D5DB)

                RoundedRectangle(cornerRadius: min(width, height) * 0.047)
                    .fill(Color(hex: 0xF8FAFC))
                    .overlay(
                        RoundedRectangle(cornerRadius: min(width, height) * 0.047)
                            .stroke(Color(hex: 0x111827), lineWidth: strokeWidth)
                    )
                    .padding(.horizontal, insetX)
                    .padding(.vertical, insetY)

                DrawTwoPlaceholderMark()
                    .stroke(
                        Color(hex: 0x111827).opacity(0.82),
                        style: StrokeStyle(
                            lineWidth: max(2, min(width, height) * 0.033),
                            lineCap: .round,
                            lineJoin: .round
                        )
                    )
                    .padding(.horizontal, insetX)
                    .padding(.vertical, insetY)

                if showsWordmark {
                    Text("DRAWTWO")
                        .font(.archetypeBody(max(7, min(width, height) * 0.055), weight: .black))
                        .foregroundStyle(Color(hex: 0x111827))
                        .tracking(1.2)
                        .position(x: width / 2, y: height * 0.892)
                }
            }
        }
    }
}

private struct DrawTwoPlaceholderMark: Shape {
    func path(in rect: CGRect) -> Path {
        let scaleX = rect.width / 300
        let scaleY = rect.height / 420
        let transform = CGAffineTransform(
            translationX: rect.minX,
            y: rect.minY
        ).scaledBy(x: scaleX, y: scaleY)

        var path = Path()

        path.move(to: CGPoint(x: 96, y: 238))
        path.addCurve(
            to: CGPoint(x: 204, y: 165),
            control1: CGPoint(x: 120, y: 184),
            control2: CGPoint(x: 168, y: 156)
        )
        path.addCurve(
            to: CGPoint(x: 238, y: 235),
            control1: CGPoint(x: 236, y: 173),
            control2: CGPoint(x: 252, y: 203)
        )
        path.addCurve(
            to: CGPoint(x: 140, y: 282),
            control1: CGPoint(x: 224, y: 266),
            control2: CGPoint(x: 183, y: 287)
        )
        path.addCurve(
            to: CGPoint(x: 96, y: 238),
            control1: CGPoint(x: 111, y: 279),
            control2: CGPoint(x: 92, y: 264)
        )

        path.move(to: CGPoint(x: 87, y: 275))
        path.addCurve(
            to: CGPoint(x: 224, y: 288),
            control1: CGPoint(x: 123, y: 303),
            control2: CGPoint(x: 178, y: 310)
        )

        path.move(to: CGPoint(x: 112, y: 175))
        path.addCurve(
            to: CGPoint(x: 118, y: 109),
            control1: CGPoint(x: 99, y: 150),
            control2: CGPoint(x: 101, y: 126)
        )
        path.addCurve(
            to: CGPoint(x: 201, y: 114),
            control1: CGPoint(x: 140, y: 86),
            control2: CGPoint(x: 180, y: 89)
        )
        path.addCurve(
            to: CGPoint(x: 198, y: 187),
            control1: CGPoint(x: 219, y: 135),
            control2: CGPoint(x: 217, y: 165)
        )

        path.move(to: CGPoint(x: 139, y: 111))
        path.addCurve(
            to: CGPoint(x: 171, y: 182),
            control1: CGPoint(x: 134, y: 140),
            control2: CGPoint(x: 147, y: 165)
        )

        path.move(to: CGPoint(x: 202, y: 116))
        path.addCurve(
            to: CGPoint(x: 151, y: 191),
            control1: CGPoint(x: 176, y: 136),
            control2: CGPoint(x: 158, y: 160)
        )

        path.move(to: CGPoint(x: 108, y: 310))
        path.addCurve(
            to: CGPoint(x: 172, y: 334),
            control1: CGPoint(x: 127, y: 326),
            control2: CGPoint(x: 148, y: 334)
        )
        path.addCurve(
            to: CGPoint(x: 246, y: 302),
            control1: CGPoint(x: 203, y: 334),
            control2: CGPoint(x: 227, y: 323)
        )

        return path.applying(transform)
    }
}

struct ArchetypeTopBar<Trailing: View>: View {
    @Environment(\.dismiss) private var dismiss

    var title: String = "Archetype"
    var showsBackButton = false
    private let trailing: Trailing

    init(
        title: String = "Archetype",
        showsBackButton: Bool = false,
        @ViewBuilder trailing: () -> Trailing
    ) {
        self.title = title
        self.showsBackButton = showsBackButton
        self.trailing = trailing()
    }

    var body: some View {
        HStack(spacing: 10) {
            if showsBackButton {
                Button {
                    dismiss()
                } label: {
                    Image(systemName: "chevron.left")
                }
                .buttonStyle(IconGameButtonStyle())
                .accessibilityLabel("Back")
            }

            if showsBackButton {
                ArchetypeBreadcrumb(title: title)
            } else {
                Button {
                    dismiss()
                } label: {
                    ArchetypeBreadcrumb(title: title)
                }
                .buttonStyle(.plain)
                .accessibilityLabel("Archetype home")
            }

            Spacer(minLength: 10)

            trailing
        }
    }
}

extension ArchetypeTopBar where Trailing == EmptyView {
    init(title: String = "Archetype", showsBackButton: Bool = false) {
        self.title = title
        self.showsBackButton = showsBackButton
        self.trailing = EmptyView()
    }
}

struct DrawTwoTopBar<Trailing: View>: View {
    @Environment(\.dismiss) private var dismiss

    private let trailing: Trailing

    init(@ViewBuilder trailing: () -> Trailing) {
        self.trailing = trailing()
    }

    var body: some View {
        HStack {
            Button {
                dismiss()
            } label: {
                DrawTwoLogoMark()
                    .frame(width: 34, height: 34, alignment: .leading)
            }
            .buttonStyle(.plain)
            .accessibilityLabel("DrawTwo home")

            Spacer()

            trailing
        }
    }
}

extension DrawTwoTopBar where Trailing == EmptyView {
    init() {
        self.trailing = EmptyView()
    }
}

struct ArchetypeProfileAvatar: View {
    let user: User?
    var size: CGFloat = 44

    var body: some View {
        ZStack {
            Circle()
                .fill(ArchetypeTheme.panel)

            if let avatarURL, let url = URL(string: avatarURL) {
                AsyncImage(url: url) { phase in
                    switch phase {
                    case .success(let image):
                        image
                            .resizable()
                            .scaledToFill()
                    default:
                        initialView
                    }
                }
            } else {
                initialView
            }
        }
        .frame(width: size, height: size)
        .clipShape(Circle())
        .overlay(
            Circle()
                .stroke(ArchetypeTheme.border, lineWidth: 1)
        )
    }

    private var avatarURL: String? {
        guard let avatar = user?.avatar, !avatar.isEmpty else {
            return nil
        }

        return avatar
    }

    private var initialView: some View {
        Text(initial)
            .font(.archetypeBody(size > 44 ? 18 : 16, weight: .bold))
            .foregroundStyle(ArchetypeTheme.text)
    }

    private var initial: String {
        let source = user?.displayName
            ?? user?.username
            ?? user?.email
            ?? "P"

        return String(source.prefix(1)).uppercased()
    }
}

struct ArchetypeProfileLink<Destination: View>: View {
    let user: User?
    private let destination: Destination

    init(user: User?, @ViewBuilder destination: () -> Destination) {
        self.user = user
        self.destination = destination()
    }

    var body: some View {
        NavigationLink {
            destination
        } label: {
            ArchetypeProfileAvatar(user: user)
        }
        .buttonStyle(.plain)
        .accessibilityLabel("Profile")
    }
}

struct ArchetypeWebPanel<Content: View>: View {
    private let title: String?
    private let padding: CGFloat
    private let content: Content

    init(title: String? = nil, padding: CGFloat = 18, @ViewBuilder content: () -> Content) {
        self.title = title
        self.padding = padding
        self.content = content()
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            if let title {
                Text(title)
                    .font(.archetypeBody(18, weight: .semibold))
                    .foregroundStyle(ArchetypeTheme.text)
                    .frame(height: 28, alignment: .leading)
                    .padding(.bottom, 16)
            }

            content
        }
        .padding(padding)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(ArchetypeTheme.panel)
        .overlay(
            RoundedRectangle(cornerRadius: ArchetypeTheme.surfaceRadius)
                .stroke(ArchetypeTheme.border, lineWidth: 1)
        )
        .clipShape(RoundedRectangle(cornerRadius: ArchetypeTheme.surfaceRadius))
        .shadow(color: Color.black.opacity(0.12), radius: 3, x: 0, y: 1)
    }
}

struct ArchetypeWebSectionTitle: View {
    let title: String
    var accessory: String?

    var body: some View {
        HStack(alignment: .lastTextBaseline) {
            Text(title)
                .font(.archetypeDisplay(24, weight: .bold))
                .foregroundStyle(ArchetypeTheme.secondaryText)
            Spacer()
            if let accessory {
                Text(accessory)
                    .font(.archetypeBody(12, weight: .semibold))
                    .foregroundStyle(ArchetypeTheme.muted)
            }
        }
        .padding(.bottom, 6)
        .overlay(alignment: .bottom) {
            Rectangle()
                .fill(ArchetypeTheme.border)
                .frame(height: 1)
        }
    }
}

struct PrimaryGameButtonStyle: ButtonStyle {
    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .font(.archetypeBody(15, weight: .semibold))
            .foregroundStyle(Color.white)
            .frame(maxWidth: .infinity)
            .padding(.vertical, 13)
            .background(configuration.isPressed ? Color(hex: 0xB45309) : ArchetypeTheme.gold)
            .clipShape(RoundedRectangle(cornerRadius: ArchetypeTheme.controlRadius))
            .scaleEffect(configuration.isPressed ? 0.98 : 1)
    }
}

struct FilledGameButtonStyle: ButtonStyle {
    let color: Color
    let pressedColor: Color

    init(color: Color, pressedColor: Color? = nil) {
        self.color = color
        self.pressedColor = pressedColor ?? color.opacity(0.82)
    }

    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .font(.archetypeBody(15, weight: .semibold))
            .foregroundStyle(Color.white)
            .frame(maxWidth: .infinity)
            .padding(.vertical, 13)
            .background(configuration.isPressed ? pressedColor : color)
            .clipShape(RoundedRectangle(cornerRadius: ArchetypeTheme.controlRadius))
            .scaleEffect(configuration.isPressed ? 0.98 : 1)
    }
}

struct SecondaryGameButtonStyle: ButtonStyle {
    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .font(.archetypeBody(14, weight: .medium))
            .foregroundStyle(Color(hex: 0xE5E7EB))
            .padding(.horizontal, 16)
            .padding(.vertical, 8)
            .background(configuration.isPressed ? Color(hex: 0x374151) : Color(hex: 0x1F2937))
            .overlay(
                RoundedRectangle(cornerRadius: ArchetypeTheme.controlRadius)
                    .stroke(Color(hex: 0x4B5563), lineWidth: 1)
            )
            .clipShape(RoundedRectangle(cornerRadius: ArchetypeTheme.controlRadius))
            .scaleEffect(configuration.isPressed ? 0.98 : 1)
    }
}

struct DashedActionButtonStyle: ButtonStyle {
    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .font(.archetypeBody(15, weight: .medium))
            .foregroundStyle(ArchetypeTheme.gold2)
            .padding(.vertical, 13)
            .background(ArchetypeTheme.gold.opacity(configuration.isPressed ? 0.16 : 0.07))
            .overlay(
                RoundedRectangle(cornerRadius: ArchetypeTheme.controlRadius)
                    .stroke(
                        ArchetypeTheme.gold2,
                        style: StrokeStyle(lineWidth: 2, dash: [6, 4])
                    )
            )
            .clipShape(RoundedRectangle(cornerRadius: ArchetypeTheme.controlRadius))
            .scaleEffect(configuration.isPressed ? 0.98 : 1)
    }
}

struct IconGameButtonStyle: ButtonStyle {
    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .font(.system(size: 18, weight: .semibold))
            .foregroundStyle(ArchetypeTheme.muted)
            .frame(width: 34, height: 34)
            .contentShape(Rectangle())
            .opacity(configuration.isPressed ? 0.58 : 1)
            .scaleEffect(configuration.isPressed ? 0.96 : 1)
    }
}

struct StyledTextField: View {
    let title: String
    var systemImage: String?
    @Binding var text: String
    var axis: Axis = .horizontal
    var keyboardType: UIKeyboardType = .default

    var body: some View {
        HStack(alignment: axis == .vertical ? .top : .center, spacing: 12) {
            if let systemImage {
                Image(systemName: systemImage)
                    .font(.system(size: 16, weight: .semibold))
                    .foregroundStyle(ArchetypeTheme.gold2)
                    .frame(width: 20)
            }

            TextField(title, text: $text, axis: axis)
                .font(.archetypeBody(15))
                .keyboardType(keyboardType)
                .textInputAutocapitalization(.never)
                .autocorrectionDisabled()
                .foregroundStyle(ArchetypeTheme.text)
                .tint(ArchetypeTheme.gold2)
                .lineLimit(axis == .vertical ? 2...4 : 1...1)
        }
        .padding(14)
        .background(ArchetypeTheme.inputSurface)
        .overlay(
            RoundedRectangle(cornerRadius: ArchetypeTheme.controlRadius)
                .stroke(ArchetypeTheme.border, lineWidth: 1)
        )
        .clipShape(RoundedRectangle(cornerRadius: ArchetypeTheme.controlRadius))
    }
}
