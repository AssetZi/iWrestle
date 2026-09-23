//
//  Theme.swift
//  iWrestle
//
//  Slate Sky Gold tokens. The app is dark-first and forced dark at the root,
//  so only the dark aliases exist here. Values are copied verbatim from the
//  design handoff (`_ds/.../tokens/colors.css`).
//

import SwiftUI

enum Theme {
    // MARK: Surfaces
    static let ink       = Color(hex: 0x0A0B0C) // page background
    static let slate950  = Color(hex: 0x131618) // card surface, map background
    static let slate900  = Color(hex: 0x1F2429) // hover surface, filter sheet, inputs on canvas
    static let slate800  = Color(hex: 0x2F363D) // logo tiles, elevated surfaces
    static let slate700  = Color(hex: 0x3E4851) // switch off-track
    static let slate600  = Color(hex: 0x4E5A66) // chevrons, drag handle
    static let slate500  = Color(hex: 0x5D6C7A) // input placeholder
    static let slate400  = Color(hex: 0x788590) // tertiary icon stroke
    static let slate300  = Color(hex: 0x939DA6) // user-location dot
    static let slate200  = Color(hex: 0xAEB6BD) // secondary text

    // MARK: Gold — the single accent
    static let gold      = Color(hex: 0xFBDBAC) // gold-500
    static let gold300   = Color(hex: 0xFCE7C8)
    static let gold400   = Color(hex: 0xFCE1BA) // focus ring
    static let gold600   = Color(hex: 0xD1B78F) // pin tail
    static let gold700   = Color(hex: 0xA79273) // pin ring, Live badge border, filled upload border
    static let gold800   = Color(hex: 0x7E6E56)

    // MARK: Text
    static let textPrimary   = Color.white
    static let textSecondary = slate200
    static let textTertiary  = slate400
    static let textDisabled  = slate600
    static let onAccent      = slate950          // ink text on gold

    /// Ink text on gold at the opacities the handoff uses on gold cards.
    static let inkOnGold62 = slate950.opacity(0.62)
    static let inkOnGold66 = slate950.opacity(0.66)
    static let inkOnGold70 = slate950.opacity(0.70)
    static let inkOnGold72 = slate950.opacity(0.72)

    // MARK: Lines
    static let borderSubtle  = Color.white.opacity(0.08)
    static let borderDefault = Color.white.opacity(0.14)
    static let borderStrong  = Color.white.opacity(0.24)

    // MARK: Overlays
    static let scrim = ink.opacity(0.72)
    static let tabBarFill = ink.opacity(0.78)

    // MARK: Status
    static let success = Color(hex: 0x6E9A72)
    static let danger  = Color(hex: 0xB5645A)

    // MARK: Radii
    enum Radius {
        static let card: CGFloat = 16
        static let feature: CGFloat = 20
        static let control: CGFloat = 12
        static let input: CGFloat = 11
        static let button: CGFloat = 12
        static let sheet: CGFloat = 24
        static let tile48: CGFloat = 13
        static let tile44: CGFloat = 12
        static let tile64: CGFloat = 16
    }

    /// Screen gutter.
    static let gutter: CGFloat = 20
}

extension Color {
    init(hex: UInt32) {
        self.init(.sRGB,
                  red: Double((hex >> 16) & 0xFF) / 255,
                  green: Double((hex >> 8) & 0xFF) / 255,
                  blue: Double(hex & 0xFF) / 255)
    }
}
