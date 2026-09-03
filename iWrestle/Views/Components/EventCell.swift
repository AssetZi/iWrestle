//
//  EventCell.swift
//  iWrestle
//
//  Created by Brock Zacherl on 11/26/25.
//

import SwiftUI
import MapKit

/// Event card: logo tile, name, "venue · city", age groups, gold distance
/// and chevron. Lightens to slate-900 and scales 0.99 while pressed.
struct EventCell: View {
    @Environment(\.isPressed) private var isPressed
    let event: Event
    let userLocation: CLLocation?

    var body: some View {
        let parts = AddressParts(event.address)
        HStack(spacing: 13) {
            EventLogoView(url: event.logo, name: event.name, size: 48)

            VStack(alignment: .leading, spacing: 3) {
                Text(event.name)
                    .font(.cardTitle)
                    .tracked(-0.01, 15)
                    .foregroundStyle(Theme.textPrimary)
                    .lineLimit(1)
                Text(parts.city.isEmpty ? parts.venue : "\(parts.venue) · \(parts.city)")
                    .font(.body12)
                    .foregroundStyle(Theme.textTertiary)
                    .lineLimit(1)
                Text(event.ageGroups.joined(separator: " · "))
                    .font(.caption11)
                    .foregroundStyle(Theme.textTertiary)
                    .lineLimit(1)
            }
            .frame(maxWidth: .infinity, alignment: .leading)

            VStack(alignment: .trailing, spacing: 8) {
                if let miles = event.miles(from: userLocation) {
                    Text("\(miles) MI")
                        .font(.distance)
                        .foregroundStyle(Theme.gold)
                }
                Chevron()
            }
        }
        .padding(.horizontal, 14)
        .padding(.vertical, 13)
        .background(isPressed ? Theme.slate900 : Theme.slate950)
        .clipShape(RoundedRectangle(cornerRadius: Theme.Radius.card, style: .continuous))
        .overlay(
            RoundedRectangle(cornerRadius: Theme.Radius.card, style: .continuous)
                .strokeBorder(Theme.borderSubtle, lineWidth: 1)
        )
        .contentShape(RoundedRectangle(cornerRadius: Theme.Radius.card, style: .continuous))
    }
}
