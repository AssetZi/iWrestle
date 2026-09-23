//
//  DealText.swift
//  iWrestle
//
//  Created by Brock Zacherl on 12/20/25.
//

import SwiftUI

/// Display copy for the launch price. The charged amount always comes from
/// StoreKit at purchase time; this only labels buttons before products load.
let launchPriceLabel = "$1"

/// "LAUNCH PRICING · $1 per event · Price grows with the app…"
struct LaunchPricingCard: View {
    var price: String = launchPriceLabel

    var body: some View {
        VStack(alignment: .leading, spacing: 5) {
            Eyebrow("Launch pricing", size: 10)
            Text("\(price) per event")
                .font(.featureTitle)
                .foregroundStyle(Theme.textPrimary)
            Text("Price grows with the app. Capped at $50, always.")
                .font(.caption11_5)
                .foregroundStyle(Theme.textTertiary)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(.horizontal, 16)
        .padding(.vertical, 15)
        .background(Theme.slate950)
        .clipShape(RoundedRectangle(cornerRadius: 14, style: .continuous))
        .overlay(
            RoundedRectangle(cornerRadius: 14, style: .continuous)
                .strokeBorder(Theme.borderSubtle, lineWidth: 1)
        )
    }
}

#Preview {
    LaunchPricingCard()
        .padding()
        .background(Theme.ink)
}
