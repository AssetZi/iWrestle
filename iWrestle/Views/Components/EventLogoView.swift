//
//  EventLogoView.swift
//  iWrestle
//
//  Created by Brock Zacherl on 12/12/25.
//

import SwiftUI

/// The event logo from CloudKit, with the slate-800 + gold monogram tile as
/// the loading / failure placeholder.
struct EventLogoView: View {
    let url: URL
    let name: String
    var size: CGFloat = 48
    var radius: CGFloat = Theme.Radius.tile48
    var font: Font = .monoTile14
    var fill: Color = Theme.slate800
    var showsBorder = true

    var body: some View {
        AsyncImage(url: url) { phase in
            switch phase {
            case .success(let image):
                image
                    .resizable()
                    .scaledToFill()
                    .frame(width: size, height: size)
                    .clipShape(RoundedRectangle(cornerRadius: radius, style: .continuous))
                    .overlay(
                        RoundedRectangle(cornerRadius: radius, style: .continuous)
                            .strokeBorder(showsBorder ? Theme.borderSubtle : .clear, lineWidth: 1)
                    )
            default:
                MonogramTile(text: name.monogram, size: size, radius: radius, font: font,
                             fill: fill, showsBorder: showsBorder)
            }
        }
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
