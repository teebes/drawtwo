import CoreText
import Foundation

enum FontRegistry {
    private static var didRegister = false

    static func registerBundledFonts() {
        guard !didRegister else {
            return
        }

        didRegister = true

        for fontName in ["Cinzel", "Inter"] {
            guard let url = Bundle.main.url(forResource: fontName, withExtension: "ttf", subdirectory: "Fonts")
                ?? Bundle.main.url(forResource: fontName, withExtension: "ttf")
            else {
                continue
            }

            var error: Unmanaged<CFError>?
            CTFontManagerRegisterFontsForURL(url as CFURL, .process, &error)
        }
    }
}
