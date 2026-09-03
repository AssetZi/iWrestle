//
//  Typography.swift
//  iWrestle
//
//  Geist + Geist Mono, sized per the design handoff. Every style is a named
//  accessor so screens never spell out a size twice.
//

import SwiftUI
import UIKit

enum AppFont {
    /// Geist. Semibold and bold fall back to Medium because only Light,
    /// Regular and Medium are bundled for the sans face.
    static func sans(_ size: CGFloat, _ weight: Font.Weight = .regular) -> Font {
        let name: String
        switch weight {
        case .ultraLight, .thin, .light: name = "Geist-Light"
        case .regular: name = "Geist-Regular"
        default: name = "Geist-Medium"
        }
        return custom(name, size: size, weight: weight, mono: false)
    }

    /// Geist Mono. Regular, Medium and SemiBold are bundled.
    static func mono(_ size: CGFloat, _ weight: Font.Weight = .regular) -> Font {
        let name: String
        switch weight {
        case .ultraLight, .thin, .light, .regular: name = "GeistMono-Regular"
        case .medium: name = "GeistMono-Medium"
        default: name = "GeistMono-SemiBold"
        }
        return custom(name, size: size, weight: weight, mono: true)
    }

    /// Wraps `Font.custom` so a missing font binary degrades to a system font
    /// of matching weight and design rather than rendering nothing.
    private static func custom(_ name: String, size: CGFloat, weight: Font.Weight, mono: Bool) -> Font {
        if UIFont(name: name, size: size) != nil {
            return .custom(name, size: size)
        }
        return .system(size: size, weight: weight, design: mono ? .monospaced : .default)
    }
}

extension Font {
    // MARK: Display
    /// Screen title: Light 28, -0.03em. Pair with `.tracked(-0.03, 28)`.
    static var screenTitle: Font   { AppFont.sans(28, .light) }
    /// Pushed-screen title ("Events dashboard"): Light 20, -0.02em.
    static var pushedTitle: Font   { AppFont.sans(20, .light) }
    /// Event detail title: Regular 23, -0.02em.
    static var detailTitle: Font   { AppFont.sans(23, .regular) }
    /// Success headline: Light 23, -0.02em.
    static var successTitle: Font  { AppFont.sans(23, .light) }
    /// Hero card event name: Regular 24, -0.02em.
    static var heroTitle: Font     { AppFont.sans(24, .regular) }
    /// Gold feature card headline / pricing figure: Regular 19.
    static var featureTitle: Font  { AppFont.sans(19, .regular) }
    /// Sheet title ("Filter events"): Regular 17.
    static var sheetTitle: Font    { AppFont.sans(17, .regular) }

    // MARK: Body
    static var cardTitle: Font     { AppFont.sans(15, .medium) }   // event card name
    static var rowTitle: Font      { AppFont.sans(14.5, .medium) } // map card / dashboard row name
    static var row: Font           { AppFont.sans(14.5, .regular) }
    static var buttonLabel: Font   { AppFont.sans(14.5, .medium) }
    static var body14: Font        { AppFont.sans(14, .regular) }
    static var body14Medium: Font  { AppFont.sans(14, .medium) }
    static var body13_5: Font      { AppFont.sans(13.5, .regular) }
    static var body13_5Medium: Font { AppFont.sans(13.5, .medium) }
    static var body13: Font        { AppFont.sans(13, .regular) }
    static var body12_5: Font      { AppFont.sans(12.5, .regular) }
    static var body12: Font        { AppFont.sans(12, .regular) }
    static var body12Medium: Font  { AppFont.sans(12, .medium) }
    static var caption11_5: Font   { AppFont.sans(11.5, .regular) }
    static var caption11_5Medium: Font { AppFont.sans(11.5, .medium) }
    static var caption11: Font     { AppFont.sans(11, .regular) }
    static var caption10_5: Font   { AppFont.sans(10.5, .regular) }
    static var pill: Font          { AppFont.sans(10.5, .medium) }
    static var tabLabel: Font      { AppFont.sans(10, .medium) }

    // MARK: Mono
    static var eyebrow: Font       { AppFont.mono(10.5, .medium) }
    static var eyebrowSmall: Font  { AppFont.mono(10, .medium) }
    static var eyebrowStrong: Font { AppFont.mono(10, .semibold) }
    static var distance: Font      { AppFont.mono(10, .semibold) }
    static var monoIndex: Font     { AppFont.mono(10, .regular) }
    static var monoTag: Font       { AppFont.mono(10, .regular) }
    static var monoBadge: Font     { AppFont.mono(9.5, .semibold) }
    static var monoCaption: Font   { AppFont.mono(11, .regular) }
    static var monoPin: Font       { AppFont.mono(11, .semibold) }
    static var monoTile13: Font    { AppFont.mono(13, .regular) }
    static var monoTile14: Font    { AppFont.mono(14, .medium) }
    static var monoTile18: Font    { AppFont.mono(18, .medium) }
}

extension Text {
    /// Letter-spacing in em, resolved against the point size.
    func tracked(_ em: CGFloat, _ size: CGFloat) -> Text { kerning(em * size) }
}

// MARK: - Eyebrow label

/// Geist Mono, uppercase, wide-tracked. Gold for screen eyebrows and numbered
/// form sections; tertiary for group / date labels.
struct Eyebrow: View {
    let text: String
    var color: Color = Theme.gold
    var size: CGFloat = 10.5
    var tracking: CGFloat = 0.16
    var weight: Font.Weight = .medium

    init(_ text: String,
         color: Color = Theme.gold,
         size: CGFloat = 10.5,
         tracking: CGFloat = 0.16,
         weight: Font.Weight = .medium) {
        self.text = text
        self.color = color
        self.size = size
        self.tracking = tracking
        self.weight = weight
    }

    var body: some View {
        Text(text.uppercased())
            .font(AppFont.mono(size, weight))
            .kerning(size * tracking)
            .foregroundStyle(color)
    }
}

/// Group / section label above a card group: tertiary, 10pt, 0.18em.
struct SectionLabel: View {
    let text: String
    init(_ text: String) { self.text = text }

    var body: some View {
        Eyebrow(text, color: Theme.textTertiary, size: 10, tracking: 0.18)
            .padding(.leading, 2)
    }
}
