//
//  EventLogoView.swift
//  iWrestle
//
//  Created by Brock Zacherl on 12/12/25.
//

import SwiftUI

/// The event logo from CloudKit, with the slate-800 + gold monogram tile as
/// the loading / failure placeholder.
///
/// Built from an event, it shows the logo `LogoManager` has for it and
/// swaps the monogram for the image when a list event's logo arrives.
struct EventLogoView: View {
    @Environment(LogoManager.self) private var logos: LogoManager?
    var url: URL? = nil
    var event: Event? = nil
    let name: String
    var size: CGFloat = 48
    var radius: CGFloat = Theme.Radius.tile48
    var font: Font = .monoTile14
    var fill: Color = Theme.slate800
    var showsBorder = true
    /// Override on light surfaces — the default white@8% is invisible on gold.
    var borderColor: Color = Theme.borderSubtle

    private var resolvedURL: URL? {
        url ?? event.flatMap { logos?.url(for: $0) ?? $0.logo }
    }

    var body: some View {
        // Keyed on the URL so a logo that arrives late replaces the tile.
        AsyncImage(url: resolvedURL) { phase in
            switch phase {
            case .success(let image):
                image
                    .resizable()
                    .scaledToFill()
                    .frame(width: size, height: size)
                    .clipShape(RoundedRectangle(cornerRadius: radius, style: .continuous))
                    .overlay(
                        RoundedRectangle(cornerRadius: radius, style: .continuous)
                            .strokeBorder(showsBorder ? borderColor : .clear, lineWidth: 1)
                    )
            default:
                MonogramTile(text: name.monogram, size: size, radius: radius, font: font,
                             fill: fill, showsBorder: showsBorder, borderColor: borderColor)
            }
        }
        .id(resolvedURL)
        .frame(width: size, height: size)
        .accessibilityHidden(true)
    }
}

#Preview {
    HStack(spacing: 12) {
        EventLogoView(url: URL(string: "https://example.invalid/none.png")!, name: "Interstate Classic")
        EventLogoView(url: URL(string: "https://example.invalid/none.png")!, name: "Knights Novice Tournament",
                      size: 64, radius: Theme.Radius.tile64, font: .monoTile18)
    }
    .padding()
    .background(Theme.ink)
}
