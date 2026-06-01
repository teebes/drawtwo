#!/usr/bin/env swift

import AppKit
import Foundation

private struct CaptureMetric {
    let name: String
    let webSize: NSSize?
    let iosSize: NSSize?
    let verticalOffset: Int?
    let meanDeltaPercent: Double?
    let changedPixelsPercent: Double?
    let contentCropTop: Int?
    let contentMeanDeltaPercent: Double?
    let contentChangedPixelsPercent: Double?
    let heightDelta: Int?
    let status: String
}

private struct PixelBuffer {
    let width: Int
    let height: Int
    let rgba: [UInt8]
}

private func usage() -> Never {
    fputs(
        "Usage: build-ui-comparison-metrics.swift <web-dir> <ios-dir> <output-tsv> <output-html> <image-name>...\n",
        stderr
    )
    exit(2)
}

private let arguments = Array(CommandLine.arguments.dropFirst())
guard arguments.count >= 5 else {
    usage()
}

private let webDir = URL(fileURLWithPath: arguments[0], isDirectory: true)
private let iosDir = URL(fileURLWithPath: arguments[1], isDirectory: true)
private let tsvURL = URL(fileURLWithPath: arguments[2])
private let htmlURL = URL(fileURLWithPath: arguments[3])
private let imageNames = Array(arguments[4...])
private let fileManager = FileManager.default

private func bitmap(from url: URL) -> NSBitmapImageRep? {
    guard let data = try? Data(contentsOf: url) else {
        return nil
    }

    return NSBitmapImageRep(data: data)
}

private func imageSize(_ bitmap: NSBitmapImageRep?) -> NSSize? {
    guard let bitmap else {
        return nil
    }

    return NSSize(width: bitmap.pixelsWide, height: bitmap.pixelsHigh)
}

private func pixelBuffer(from bitmap: NSBitmapImageRep) -> PixelBuffer? {
    guard let image = bitmap.cgImage else {
        return nil
    }

    let width = image.width
    let height = image.height
    let bytesPerRow = width * 4
    var rgba = [UInt8](repeating: 0, count: height * bytesPerRow)

    let colorSpace = CGColorSpaceCreateDeviceRGB()
    let bitmapInfo = CGImageAlphaInfo.premultipliedLast.rawValue
        | CGBitmapInfo.byteOrder32Big.rawValue

    let drewImage = rgba.withUnsafeMutableBytes { buffer in
        guard let baseAddress = buffer.baseAddress,
              let context = CGContext(
                  data: baseAddress,
                  width: width,
                  height: height,
                  bitsPerComponent: 8,
                  bytesPerRow: bytesPerRow,
                  space: colorSpace,
                  bitmapInfo: bitmapInfo
              ) else {
            return false
        }

        context.draw(image, in: CGRect(x: 0, y: 0, width: width, height: height))
        return true
    }

    guard drewImage else {
        return nil
    }

    return PixelBuffer(width: width, height: height, rgba: rgba)
}

private func compare(
    web: PixelBuffer,
    ios: PixelBuffer,
    verticalOffset: Int = 0,
    sampleStride: Int = 1,
    cropTop: Int = 0,
    cropBottom: Int = 0
) -> (meanDeltaPercent: Double, changedPixelsPercent: Double) {
    let width = min(web.width, ios.width)
    let webStartY = max(0, -verticalOffset)
    let iosStartY = max(0, verticalOffset)
    let sharedHeight = min(web.height - webStartY, ios.height - iosStartY)
    let compareStartY = min(max(cropTop, 0), sharedHeight)
    let compareEndY = max(compareStartY, sharedHeight - max(cropBottom, 0))
    let height = compareEndY - compareStartY
    guard width > 0, height > 0 else {
        return (0, 0)
    }

    var deltaTotal = 0.0
    var changedPixels = 0
    var pixelCount = 0

    for y in stride(from: compareStartY, to: compareEndY, by: sampleStride) {
        for x in stride(from: 0, to: width, by: sampleStride) {
            let webOffset = (((webStartY + y) * web.width) + x) * 4
            let iosOffset = (((iosStartY + y) * ios.width) + x) * 4
            let redDelta = abs(Int(web.rgba[webOffset]) - Int(ios.rgba[iosOffset]))
            let greenDelta = abs(Int(web.rgba[webOffset + 1]) - Int(ios.rgba[iosOffset + 1]))
            let blueDelta = abs(Int(web.rgba[webOffset + 2]) - Int(ios.rgba[iosOffset + 2]))
            let pixelDelta = Double(redDelta + greenDelta + blueDelta) / 3
            deltaTotal += pixelDelta
            pixelCount += 1

            if pixelDelta > 31 {
                changedPixels += 1
            }
        }
    }

    guard pixelCount > 0 else {
        return (0, 0)
    }

    return (
        meanDeltaPercent: (deltaTotal / (Double(pixelCount) * 255)) * 100,
        changedPixelsPercent: (Double(changedPixels) / Double(pixelCount)) * 100
    )
}

private func bestVerticalOffset(web: PixelBuffer, ios: PixelBuffer) -> Int {
    let maximumOffset = 96
    let offsetStep = 2
    let sampleStride = 4
    var bestOffset = 0
    var bestScore = Double.greatestFiniteMagnitude

    for offset in stride(from: -maximumOffset, through: maximumOffset, by: offsetStep) {
        let score = compare(
            web: web,
            ios: ios,
            verticalOffset: offset,
            sampleStride: sampleStride
        ).meanDeltaPercent

        if score < bestScore {
            bestScore = score
            bestOffset = offset
        }
    }

    return bestOffset
}

private func metricClass(_ value: Double?) -> String {
    guard let value else {
        return "metric-drift"
    }

    if value < 8 {
        return "metric-ok"
    }

    if value < 18 {
        return "metric-watch"
    }

    return "metric-drift"
}

private func formatPercent(_ value: Double?) -> String {
    guard let value else {
        return "-"
    }

    return String(format: "%.1f%%", value)
}

private func formatSize(_ size: NSSize?) -> String {
    guard let size else {
        return "-"
    }

    return "\(Int(size.width))x\(Int(size.height))"
}

private func contentCropTop(for name: String) -> Int {
    let pageBannerScreens: Set<String> = [
        "collection",
        "deck",
        "games",
        "leaderboard",
        "new-game",
        "new-game-ai",
        "profile",
        "profile-edit",
        "ranked-queue-daily",
        "ranked-queue-rapid",
    ]

    if pageBannerScreens.contains(name) {
        return 180
    }

    if name == "collection-card-detail" || name == "deck-card-detail" {
        return 136
    }

    return 64
}

private func isIOSOnlyCapture(_ name: String) -> Bool {
    name == "login-confirm"
}

private func shouldSortBefore(_ lhs: CaptureMetric, _ rhs: CaptureMetric) -> Bool {
    let leftValue = lhs.contentMeanDeltaPercent ?? lhs.meanDeltaPercent
    let rightValue = rhs.contentMeanDeltaPercent ?? rhs.meanDeltaPercent

    switch (leftValue, rightValue) {
    case let (left?, right?):
        if left != right {
            return left > right
        }
        return lhs.name < rhs.name
    case (_?, nil):
        return true
    case (nil, _?):
        return false
    case (nil, nil):
        return lhs.name < rhs.name
    }
}

private func escapeHTML(_ value: String) -> String {
    value
        .replacingOccurrences(of: "&", with: "&amp;")
        .replacingOccurrences(of: "<", with: "&lt;")
        .replacingOccurrences(of: ">", with: "&gt;")
        .replacingOccurrences(of: "\"", with: "&quot;")
}

private let metrics: [CaptureMetric] = imageNames.map { imageName in
    let displayName = imageName.replacingOccurrences(of: ".png", with: "")
    let webURL = webDir.appendingPathComponent(imageName)
    let iosURL = iosDir.appendingPathComponent(imageName)

    guard fileManager.fileExists(atPath: webURL.path) else {
        let iosBitmap = bitmap(from: iosURL)
        return CaptureMetric(
            name: displayName,
            webSize: nil,
            iosSize: imageSize(iosBitmap),
            verticalOffset: nil,
            meanDeltaPercent: nil,
            changedPixelsPercent: nil,
            contentCropTop: nil,
            contentMeanDeltaPercent: nil,
            contentChangedPixelsPercent: nil,
            heightDelta: nil,
            status: isIOSOnlyCapture(displayName) ? "iOS only" : "missing web"
        )
    }

    guard fileManager.fileExists(atPath: iosURL.path) else {
        let webBitmap = bitmap(from: webURL)
        return CaptureMetric(
            name: displayName,
            webSize: imageSize(webBitmap),
            iosSize: nil,
            verticalOffset: nil,
            meanDeltaPercent: nil,
            changedPixelsPercent: nil,
            contentCropTop: nil,
            contentMeanDeltaPercent: nil,
            contentChangedPixelsPercent: nil,
            heightDelta: nil,
            status: "missing iOS"
        )
    }

    guard let webBitmap = bitmap(from: webURL), let iosBitmap = bitmap(from: iosURL) else {
        return CaptureMetric(
            name: displayName,
            webSize: nil,
            iosSize: nil,
            verticalOffset: nil,
            meanDeltaPercent: nil,
            changedPixelsPercent: nil,
            contentCropTop: nil,
            contentMeanDeltaPercent: nil,
            contentChangedPixelsPercent: nil,
            heightDelta: nil,
            status: "unreadable"
        )
    }

    guard let webPixels = pixelBuffer(from: webBitmap),
          let iosPixels = pixelBuffer(from: iosBitmap) else {
        return CaptureMetric(
            name: displayName,
            webSize: imageSize(webBitmap),
            iosSize: imageSize(iosBitmap),
            verticalOffset: nil,
            meanDeltaPercent: nil,
            changedPixelsPercent: nil,
            contentCropTop: nil,
            contentMeanDeltaPercent: nil,
            contentChangedPixelsPercent: nil,
            heightDelta: iosBitmap.pixelsHigh - webBitmap.pixelsHigh,
            status: "unreadable pixels"
        )
    }

    let offset = bestVerticalOffset(web: webPixels, ios: iosPixels)
    let comparison = compare(web: webPixels, ios: iosPixels, verticalOffset: offset)
    let cropTop = contentCropTop(for: displayName)
    let contentComparison = compare(
        web: webPixels,
        ios: iosPixels,
        verticalOffset: offset,
        cropTop: cropTop,
        cropBottom: 34
    )
    return CaptureMetric(
        name: displayName,
        webSize: imageSize(webBitmap),
        iosSize: imageSize(iosBitmap),
        verticalOffset: offset,
        meanDeltaPercent: comparison.meanDeltaPercent,
        changedPixelsPercent: comparison.changedPixelsPercent,
        contentCropTop: cropTop,
        contentMeanDeltaPercent: contentComparison.meanDeltaPercent,
        contentChangedPixelsPercent: contentComparison.changedPixelsPercent,
        heightDelta: iosBitmap.pixelsHigh - webBitmap.pixelsHigh,
        status: "ok"
    )
}

var tsv = "name\tweb_size\tios_size\theight_delta_px\tvertical_shift_px\taligned_mean_rgb_delta\taligned_changed_pixels\tcontent_crop_top_px\tcontent_mean_rgb_delta\tcontent_changed_pixels\tstatus\n"
for metric in metrics {
    tsv += [
        metric.name,
        formatSize(metric.webSize),
        formatSize(metric.iosSize),
        metric.heightDelta.map(String.init) ?? "-",
        metric.verticalOffset.map(String.init) ?? "-",
        formatPercent(metric.meanDeltaPercent),
        formatPercent(metric.changedPixelsPercent),
        metric.contentCropTop.map(String.init) ?? "-",
        formatPercent(metric.contentMeanDeltaPercent),
        formatPercent(metric.contentChangedPixelsPercent),
        metric.status,
    ].joined(separator: "\t")
    tsv += "\n"
}

var html = """
  <section class="metrics">
    <div class="metrics-header">
      <h2>Comparison Metrics</h2>
      <p>Scores compare scaled captures after choosing the best small vertical offset. Content scores ignore screen-specific top chrome plus the last 34px of the aligned frame so safe-area, page banners, and home-indicator space do not dominate triage. Rows are sorted by content RGB delta when available. They are a triage aid, not a pass/fail gate; native safe areas and dynamic island space can still require visual review.</p>
    </div>
    <div class="metrics-table-wrap">
      <table>
        <thead>
          <tr>
            <th>Rank</th>
            <th>Screen</th>
            <th>Web</th>
            <th>iOS</th>
            <th>Height Delta</th>
            <th>Vertical Shift</th>
            <th>Aligned RGB Delta</th>
            <th>Aligned Changed Pixels</th>
            <th>Content Crop Top</th>
            <th>Content RGB Delta</th>
            <th>Content Changed Pixels</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
"""

for (index, metric) in metrics.sorted(by: shouldSortBefore).enumerated() {
    let delta = formatPercent(metric.meanDeltaPercent)
    let changed = formatPercent(metric.changedPixelsPercent)
    let contentDelta = formatPercent(metric.contentMeanDeltaPercent)
    let contentChanged = formatPercent(metric.contentChangedPixelsPercent)
    html += """
          <tr>
            <td>\(index + 1)</td>
            <td>\(escapeHTML(metric.name))</td>
            <td>\(formatSize(metric.webSize))</td>
            <td>\(formatSize(metric.iosSize))</td>
            <td>\(metric.heightDelta.map(String.init) ?? "-")</td>
            <td>\(metric.verticalOffset.map(String.init) ?? "-")</td>
            <td class="\(metricClass(metric.meanDeltaPercent))">\(delta)</td>
            <td class="\(metricClass(metric.changedPixelsPercent))">\(changed)</td>
            <td>\(metric.contentCropTop.map(String.init) ?? "-")</td>
            <td class="\(metricClass(metric.contentMeanDeltaPercent))">\(contentDelta)</td>
            <td class="\(metricClass(metric.contentChangedPixelsPercent))">\(contentChanged)</td>
            <td>\(escapeHTML(metric.status))</td>
          </tr>
"""
}

html += """
        </tbody>
      </table>
    </div>
  </section>
"""

try fileManager.createDirectory(at: tsvURL.deletingLastPathComponent(), withIntermediateDirectories: true)
try tsv.write(to: tsvURL, atomically: true, encoding: .utf8)
try html.write(to: htmlURL, atomically: true, encoding: .utf8)

print("Saved UI comparison metrics to \(tsvURL.path)")
