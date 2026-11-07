// Draw the app icon: a voice waveform above two subtitle lines.
// Usage: swift macos/make_icon.swift macos/AppIcon.icns

import AppKit

func color(_ hex: UInt32) -> CGColor {
    CGColor(
        srgbRed: CGFloat(hex >> 16 & 255) / 255,
        green: CGFloat(hex >> 8 & 255) / 255,
        blue: CGFloat(hex & 255) / 255,
        alpha: 1
    )
}

func pill(_ context: CGContext, _ rect: CGRect, fill: UInt32) {
    let radius = min(rect.width, rect.height) / 2
    context.addPath(CGPath(roundedRect: rect, cornerWidth: radius, cornerHeight: radius, transform: nil))
    context.setFillColor(color(fill))
    context.fillPath()
}

func draw(_ context: CGContext) {
    // Apple's icon grid leaves a 100 px margin around the 824 px tile.
    let tile = CGPath(
        roundedRect: CGRect(x: 100, y: 100, width: 824, height: 824),
        cornerWidth: 185, cornerHeight: 185, transform: nil
    )
    context.saveGState()
    context.addPath(tile)
    context.clip()
    let gradient = CGGradient(
        colorsSpace: CGColorSpace(name: CGColorSpace.sRGB),
        colors: [color(0x14575A), color(0x0A2A2E)] as CFArray,
        locations: [0, 1]
    )!
    context.drawLinearGradient(
        gradient, start: CGPoint(x: 512, y: 924), end: CGPoint(x: 512, y: 100), options: []
    )
    context.restoreGState()

    let width: CGFloat = 68
    let step: CGFloat = 118
    let left: CGFloat = 512 - (step * 4 + width) / 2
    for (index, height) in [130, 260, 360, 230, 120].enumerated() {
        let height = CGFloat(height)
        let rect = CGRect(x: left + step * CGFloat(index), y: 620 - height / 2, width: width, height: height)
        pill(context, rect, fill: 0xF4F1EA)
    }
    pill(context, CGRect(x: 242, y: 318, width: 540, height: 64), fill: 0xFFB020)
    pill(context, CGRect(x: 342, y: 216, width: 340, height: 64), fill: 0xFFB020)
}

func png(size: Int) -> Data {
    let rep = NSBitmapImageRep(
        bitmapDataPlanes: nil, pixelsWide: size, pixelsHigh: size, bitsPerSample: 8,
        samplesPerPixel: 4, hasAlpha: true, isPlanar: false,
        colorSpaceName: .deviceRGB, bytesPerRow: 0, bitsPerPixel: 0
    )!
    let context = NSGraphicsContext(bitmapImageRep: rep)!.cgContext
    context.scaleBy(x: CGFloat(size) / 1024, y: CGFloat(size) / 1024)
    draw(context)
    return rep.representation(using: .png, properties: [:])!
}

let output = URL(fileURLWithPath: CommandLine.arguments[1])
let iconset = FileManager.default.temporaryDirectory
    .appendingPathComponent(UUID().uuidString + ".iconset")
try FileManager.default.createDirectory(at: iconset, withIntermediateDirectories: true)
for size in [16, 32, 128, 256, 512] {
    try png(size: size).write(to: iconset.appendingPathComponent("icon_\(size)x\(size).png"))
    try png(size: size * 2).write(to: iconset.appendingPathComponent("icon_\(size)x\(size)@2x.png"))
}
let iconutil = Process()
iconutil.executableURL = URL(fileURLWithPath: "/usr/bin/iconutil")
iconutil.arguments = ["-c", "icns", iconset.path, "-o", output.path]
try iconutil.run()
iconutil.waitUntilExit()
try FileManager.default.removeItem(at: iconset)
