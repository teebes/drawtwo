#!/usr/bin/env swift

import AppKit
import Foundation

private struct CapturePair {
    let name: String
    let webURL: URL?
    let iosURL: URL?
}

private func usage() -> Never {
    fputs(
        "Usage: build-ui-comparison-contact-sheet.swift <web-dir> <ios-dir> <output-png> <image-name>...\n",
        stderr
    )
    exit(2)
}

private let arguments = Array(CommandLine.arguments.dropFirst())
guard arguments.count >= 4 else {
    usage()
}

private let webDir = URL(fileURLWithPath: arguments[0], isDirectory: true)
private let iosDir = URL(fileURLWithPath: arguments[1], isDirectory: true)
private let outputURL = URL(fileURLWithPath: arguments[2])
private let imageNames = Array(arguments[3...])

private let fileManager = FileManager.default
private let pairs = imageNames.compactMap { name -> CapturePair? in
    let webURL = webDir.appendingPathComponent(name)
    let iosURL = iosDir.appendingPathComponent(name)
    let existingWebURL = fileManager.fileExists(atPath: webURL.path) ? webURL : nil
    let existingIOSURL = fileManager.fileExists(atPath: iosURL.path) ? iosURL : nil

    guard existingWebURL != nil || existingIOSURL != nil else {
        return nil
    }

    return CapturePair(
        name: name.replacingOccurrences(of: ".png", with: ""),
        webURL: existingWebURL,
        iosURL: existingIOSURL
    )
}

guard !pairs.isEmpty else {
    fputs("No screenshots found for contact sheet.\n", stderr)
    exit(1)
}

private let scale = NSScreen.main?.backingScaleFactor ?? 2
private let tileWidth: CGFloat = 190
private let imageWidth: CGFloat = 180
private let labelHeight: CGFloat = 42
private let tileHeight: CGFloat = 440
private let gutter: CGFloat = 12
private let columns = 3
private let rows = Int(ceil(Double(pairs.count) / Double(columns)))
private let sheetSize = NSSize(
    width: CGFloat(columns) * (tileWidth * 2 + gutter * 3),
    height: CGFloat(rows) * tileHeight
)

private let bitmap = NSBitmapImageRep(
    bitmapDataPlanes: nil,
    pixelsWide: Int(sheetSize.width * scale),
    pixelsHigh: Int(sheetSize.height * scale),
    bitsPerSample: 8,
    samplesPerPixel: 4,
    hasAlpha: true,
    isPlanar: false,
    colorSpaceName: .deviceRGB,
    bitmapFormat: .alphaFirst,
    bytesPerRow: 0,
    bitsPerPixel: 0
)

guard let bitmap else {
    fputs("Could not allocate contact sheet bitmap.\n", stderr)
    exit(1)
}

bitmap.size = sheetSize

NSGraphicsContext.saveGraphicsState()
NSGraphicsContext.current = NSGraphicsContext(bitmapImageRep: bitmap)

private let background = NSColor(calibratedRed: 17 / 255, green: 24 / 255, blue: 39 / 255, alpha: 1)
private let tileBackground = NSColor(calibratedRed: 31 / 255, green: 41 / 255, blue: 55 / 255, alpha: 1)
private let labelColor = NSColor(calibratedRed: 248 / 255, green: 250 / 255, blue: 252 / 255, alpha: 1)
private let mutedColor = NSColor(calibratedRed: 156 / 255, green: 163 / 255, blue: 175 / 255, alpha: 1)
private let borderColor = NSColor(calibratedRed: 55 / 255, green: 65 / 255, blue: 81 / 255, alpha: 1)

background.setFill()
NSRect(origin: .zero, size: sheetSize).fill()

private let titleAttributes: [NSAttributedString.Key: Any] = [
    .font: NSFont.boldSystemFont(ofSize: 12),
    .foregroundColor: labelColor,
]
private let captionAttributes: [NSAttributedString.Key: Any] = [
    .font: NSFont.systemFont(ofSize: 10),
    .foregroundColor: mutedColor,
]

private func drawImage(_ image: NSImage, in rect: NSRect) {
    let scale = min(rect.width / image.size.width, rect.height / image.size.height)
    let size = NSSize(width: image.size.width * scale, height: image.size.height * scale)
    let drawRect = NSRect(
        x: rect.midX - size.width / 2,
        y: rect.maxY - size.height,
        width: size.width,
        height: size.height
    )
    image.draw(in: drawRect, from: .zero, operation: .sourceOver, fraction: 1)
}

private func drawMissing(_ label: String, in rect: NSRect) {
    let missingAttributes: [NSAttributedString.Key: Any] = [
        .font: NSFont.systemFont(ofSize: 11, weight: .medium),
        .foregroundColor: mutedColor,
    ]
    let paragraph = NSMutableParagraphStyle()
    paragraph.alignment = .center
    var attributes = missingAttributes
    attributes[.paragraphStyle] = paragraph

    borderColor.setStroke()
    let path = NSBezierPath(rect: rect.insetBy(dx: 0.5, dy: 0.5))
    path.lineWidth = 1
    path.stroke()

    label.draw(
        in: NSRect(x: rect.minX + 8, y: rect.midY - 8, width: rect.width - 16, height: 16),
        withAttributes: attributes
    )
}

private func isIOSOnlyCapture(_ name: String) -> Bool {
    name == "login-confirm"
}

for (index, pair) in pairs.enumerated() {
    let column = index % columns
    let row = index / columns
    let tileGroupWidth = tileWidth * 2 + gutter * 3
    let originX = CGFloat(column) * tileGroupWidth
    let originY = sheetSize.height - CGFloat(row + 1) * tileHeight
    let groupRect = NSRect(x: originX, y: originY, width: tileGroupWidth, height: tileHeight)

    tileBackground.setFill()
    groupRect.fill()
    borderColor.setStroke()
    NSBezierPath(rect: groupRect.insetBy(dx: 0.5, dy: 0.5)).stroke()

    pair.name.draw(
        in: NSRect(x: originX + gutter, y: groupRect.maxY - 18, width: tileGroupWidth - gutter * 2, height: 14),
        withAttributes: titleAttributes
    )
    "web".draw(
        in: NSRect(x: originX + gutter, y: groupRect.maxY - 34, width: tileWidth, height: 12),
        withAttributes: captionAttributes
    )
    "iOS".draw(
        in: NSRect(x: originX + gutter * 2 + tileWidth, y: groupRect.maxY - 34, width: tileWidth, height: 12),
        withAttributes: captionAttributes
    )

    let imageTop = groupRect.maxY - labelHeight
    let imageHeight = tileHeight - labelHeight - gutter
    let webRect = NSRect(x: originX + gutter, y: originY + gutter, width: imageWidth, height: imageHeight)
    let iosRect = NSRect(x: originX + gutter * 2 + tileWidth, y: originY + gutter, width: imageWidth, height: imageHeight)

    if let webURL = pair.webURL, let webImage = NSImage(contentsOf: webURL) {
        drawImage(webImage, in: webRect)
    } else {
        drawMissing(isIOSOnlyCapture(pair.name) ? "Native-only screen" : "No web capture", in: webRect)
    }

    if let iosURL = pair.iosURL, let iosImage = NSImage(contentsOf: iosURL) {
        drawImage(iosImage, in: iosRect)
    } else {
        drawMissing("No iOS capture", in: iosRect)
    }

    _ = imageTop
}

NSGraphicsContext.restoreGraphicsState()

guard let pngData = bitmap.representation(using: NSBitmapImageRep.FileType.png, properties: [:]) else {
    fputs("Could not encode contact sheet PNG.\n", stderr)
    exit(1)
}

try fileManager.createDirectory(at: outputURL.deletingLastPathComponent(), withIntermediateDirectories: true)
try pngData.write(to: outputURL)
print("Saved UI comparison contact sheet to \(outputURL.path)")
