//
//  PromotedAppBanner.swift
//  iWrestle
//
//  "Also by the maker of iWrestle" row. Same shape as an event cell so it
//  sits in the list without shouting; the mono eyebrow is the only tell.
//  Tapping anywhere opens Apple's App Store overlay inside the app.
//

import SwiftUI
import StoreKit

struct PromotedAppBanner: View {
    let placement: CrossPromo.Placement
    let iconURL: URL?
    /// Campaign token for App Analytics, e.g. "iwrestle-list".
    let campaign: String
    let onDismiss: () -> Void

    @State private var showOverlay = false

    private var app: PromotedApp { placement.app }

    var body: some View {
        Button { showOverlay = true } label: {
            Row(app: app, tagline: placement.tagline, iconURL: iconURL)
        }
        .buttonStyle(SurfaceButtonStyle())
        .cardContainer()
        .overlay(alignment: .topTrailing) { dismissButton }
        .accessibilityLabel("\(app.name). \(placement.tagline). Get it on the App Store.")
        .appStoreOverlay(isPresented: $showOverlay) {
            let config = SKOverlay.AppConfiguration(appIdentifier: app.id, position: .bottom)
            config.campaignToken = campaign
            config.providerToken = AppLinks.appStoreProviderToken
            return config
        }
    }

    /// The row body. Lightens to slate-900 while pressed, like `EventCell`.
    private struct Row: View {
        @Environment(\.isPressed) private var isPressed
        let app: PromotedApp
        let tagline: String
        let iconURL: URL?

        var body: some View {
            HStack(spacing: 13) {
                if let iconURL {
                    EventLogoView(url: iconURL, name: app.name)
                } else {
                    MonogramTile(text: app.name.monogram)
                }

                VStack(alignment: .leading, spacing: 3) {
                    Eyebrow("From the same maker", size: 10)
                        .lineLimit(1)
                    Text(app.name)
                        .font(.cardTitle)
                        .tracked(-0.01, 15)
                        .foregroundStyle(Theme.textPrimary)
                        .lineLimit(1)
                    Text(tagline)
                        .font(.body12)
                        .foregroundStyle(Theme.textTertiary)
                        .lineLimit(2)
                        .fixedSize(horizontal: false, vertical: true)
                }
                .frame(maxWidth: .infinity, alignment: .leading)
                // Keeps the eyebrow clear of the × in the corner.
                .padding(.trailing, 6)

                Text("Get")
                    .font(.body12Medium)
                    .foregroundStyle(Theme.onAccent)
                    .padding(.horizontal, 12)
                    .padding(.vertical, 6)
                    .background(Capsule().fill(Theme.gold))
            }
            .padding(.horizontal, 14)
            .padding(.vertical, 13)
            .background(isPressed ? Theme.slate900 : Theme.slate950)
            .contentShape(Rectangle())
        }
    }

    private var dismissButton: some View {
        Button(action: onDismiss) {
            LucideIcon(.x, size: 12, strokeWidth: 2)
                .foregroundStyle(Theme.slate600)
                .frame(width: 32, height: 32)
                .contentShape(Rectangle())
        }
        .buttonStyle(.plain)
        .padding(2)
        .accessibilityLabel("Hide")
    }
}

#Preview {
    VStack(spacing: 12) {
        PromotedAppBanner(
            placement: .init(app: PromotedApp.catalog[0], tagline: PromotedApp.catalog[0].taglines[1]),
            iconURL: nil,
            campaign: "preview"
        ) {}
        PromotedAppBanner(
            placement: .init(app: PromotedApp.catalog[3], tagline: PromotedApp.catalog[3].taglines[0]),
            iconURL: nil,
            campaign: "preview"
        ) {}
    }
    .padding(Theme.gutter)
    .background(Theme.ink)
}
