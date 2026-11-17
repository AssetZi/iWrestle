//
//  PromotedAppBanner.swift
//  iWrestle
//
//  "From the same maker" row. Same shape as an event cell so it sits in the
//  list without shouting; the mono eyebrow is the only tell. Tapping anywhere
//  opens Apple's App Store overlay inside the app.
//

import SwiftUI
import StoreKit

/// The session's promoted app, or nothing once it is dismissed. Every
/// placement uses this so they all show and hide the same app together.
struct PromoSlot: View {
    @Environment(CrossPromo.self) private var promo
    let campaign: PromoCampaign

    var body: some View {
        if let placement = promo.current {
            PromotedAppBanner(placement: placement, iconURL: promo.iconURL, campaign: campaign) {
                withAnimation(Motion.normal) { promo.dismiss() }
            }
        }
    }
}

struct PromotedAppBanner: View {
    let placement: CrossPromo.Placement
    let iconURL: URL?
    let campaign: PromoCampaign
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
            config.campaignToken = campaign.rawValue
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
                    // Pinned to the bottom of the row, under the × hit area
                    // (top 34pt), so a tap on Get never dismisses instead.
                    // A taller row only moves it further down.
                    .frame(maxHeight: .infinity, alignment: .bottom)
            }
            // At least 54pt of content puts the pill's top about 40pt down.
            .frame(minHeight: 54)
            // Sizes the row to its content so the pill's frame can fill it.
            .fixedSize(horizontal: false, vertical: true)
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
            campaign: .list
        ) {}
        PromotedAppBanner(
            placement: .init(app: PromotedApp.catalog[2], tagline: PromotedApp.catalog[2].taglines[0]),
            iconURL: nil,
            campaign: .list
        ) {}
    }
    .padding(Theme.gutter)
    .background(Theme.ink)
}
