// Draw the menu bar template icons: the logo's waveform and subtitle, one variant per state.
// Usage: swift macos/make_menubar_icons.swift src/earfish/icons

import AppKit

let size = 40  // 20 pt at 2x.
let heights: [CGFloat] = [8, 16, 22, 14, 7]
let width: CGFloat = 4
let step: CGFloat = 7
let left: CGFloat = 20 - (step * 4 + width) / 2
let middle: CGFloat = 25

func pill(_ context: CGContext, _ rect: CGRect) {
    let radius = min(rect.width, rect.height) / 2
    context.addPath(CGPath(roundedRect: rect, cornerWidth: radius, cornerHeight: radius, transform: nil))
    context.fillPath()
}

func fill(_ context: CGContext, alpha: CGFloat) {
    context.setFillColor(CGColor(gray: 0, alpha: alpha))
}

func waveform(_ context: CGContext, alpha: CGFloat, heights: [CGFloat], middle: CGFloat = middle) {
    fill(context, alpha: alpha)
    for (index, height) in heights.enumerated() {
        pill(context, CGRect(x: left + step * CGFloat(index), y: middle - height / 2, width: width, height: height))
    }
}

func subtitle(_ context: CGContext, alpha: CGFloat) {
    fill(context, alpha: alpha)
    pill(context, CGRect(x: left, y: 6, width: step * 4 + width, height: 5))
}

let icons: [String: (CGContext) -> Void] = [
    "ready": { context in
        waveform(context, alpha: 1, heights: heights)
        subtitle(context, alpha: 1)
    },
    "loading": { context in
        waveform(context, alpha: 0.35, heights: heights)
        subtitle(context, alpha: 0.35)
    },
    "listening": { context in
        // A solid tile with the logo cut out, so it reads at a glance.
        fill(context, alpha: 1)
        let tile = CGRect(x: 0, y: 0, width: 40, height: 40).insetBy(dx: 1, dy: 1)
        context.addPath(CGPath(roundedRect: tile, cornerWidth: 9, cornerHeight: 9, transform: nil))
        context.fillPath()
        context.setBlendMode(.clear)
        waveform(context, alpha: 1, heights: heights.map { $0 * 0.8 })
        subtitle(context, alpha: 1)
    },
    "warning": { context in
        // The tallest bar splits into an exclamation mark.
        waveform(context, alpha: 0.35, heights: heights)
        subtitle(context, alpha: 0.35)
        context.setBlendMode(.clear)
        fill(context, alpha: 1)
        context.fill(CGRect(x: left + step * 2 - 2, y: 12, width: width + 4, height: 28))
        context.setBlendMode(.normal)
        pill(context, CGRect(x: left + step * 2, y: 21, width: width, height: 17))
        pill(context, CGRect(x: left + step * 2, y: 14, width: width, height: 4))
    },
]

let directory = URL(fileURLWithPath: CommandLine.arguments[1])
try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
for (name, draw) in icons {
    let rep = NSBitmapImageRep(
        bitmapDataPlanes: nil, pixelsWide: size, pixelsHigh: size, bitsPerSample: 8,
        samplesPerPixel: 4, hasAlpha: true, isPlanar: false,
        colorSpaceName: .deviceRGB, bytesPerRow: 0, bitsPerPixel: 0
    )!
    draw(NSGraphicsContext(bitmapImageRep: rep)!.cgContext)
    try rep.representation(using: .png, properties: [:])!
        .write(to: directory.appendingPathComponent("\(name).png"))
}
