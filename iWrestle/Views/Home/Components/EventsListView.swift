//
//  EventsListView.swift
//  iWrestle
//
//  Created by Brock Zacherl on 12/17/25.
//

import SwiftUI
import MapKit

struct EventsListView: View {
    let events: [Event]
    let userLocation: CLLocation?

    var body: some View {
        let sorted = events.sortedForList(userLocation: userLocation)
        let hero = sorted.first
        let groups = Array(sorted.dropFirst()).groupedByDay()

        ScrollView {
            LazyVStack(alignment: .leading, spacing: 18) {
                if let hero {
                    NavigationLink(value: AppRoute.eventDetail(hero)) {
                        HeroEventCard(event: hero, userLocation: userLocation)
                    }
                    .buttonStyle(PressableButtonStyle(scale: 0.98))
                    .entrance()
                }

                ForEach(Array(groups.enumerated()), id: \.element.day) { index, group in
                    VStack(alignment: .leading, spacing: 9) {
                        SectionLabel(group.day.groupLabel)
                        ForEach(group.events) { event in
                            NavigationLink(value: AppRoute.eventDetail(event)) {
                                EventCell(event: event, userLocation: userLocation)
                            }
                            .buttonStyle(SurfaceButtonStyle())
                        }
                    }
                    .entrance(delay: Double(min(index, 4)) * 0.04)
                }
            }
            .padding(.horizontal, Theme.gutter)
            .padding(.top, 6)
            .padding(.bottom, 24)
        }
        .scrollIndicators(.hidden)
    }
}

/// "Next up" — the earliest upcoming event as a full-width gold card.
struct HeroEventCard: View {
    let event: Event
    let userLocation: CLLocation?

    var body: some View {
        let parts = AddressParts(event.address)
        GoldFeatureCard {
            VStack(alignment: .leading, spacing: 10) {
                HStack(alignment: .top, spacing: 12) {
                    VStack(alignment: .leading, spacing: 10) {
                        Eyebrow("Next up · \(event.date.shortDayLabel)", color: Theme.inkOnGold62, size: 10, weight: .semibold)
                        Text(event.name)
                            .font(.heroTitle)
                            .tracked(-0.02, 24)
                            .lineLimit(2)
                            .fixedSize(horizontal: false, vertical: true)
                    }
                    .frame(maxWidth: .infinity, alignment: .leading)

                    VStack(alignment: .trailing, spacing: 6) {
                        EventLogoView(url: event.logo, name: event.name, size: 44,
                                      radius: Theme.Radius.tile44, font: .monoTile13,
                                      borderColor: Theme.slate950.opacity(0.14))
                        if let miles = event.miles(from: userLocation) {
                            Text("\(miles) MI")
                                .font(.distance)
                                .foregroundStyle(Theme.inkOnGold62)
                        }
                    }
                }
                Text(parts.city.isEmpty ? parts.venue : "\(parts.venue) · \(parts.city)")
                    .font(.body12_5)
                    .foregroundStyle(Theme.inkOnGold72)
                    .lineLimit(1)
                HStack(spacing: 6) {
                    ChipFlow(spacing: 6) {
                        ForEach(event.ageGroups, id: \.self) { AgePill(text: $0, onGold: true) }
                    }
                    Spacer(minLength: 8)
                    LucideIcon(.chevronRight, size: 16, strokeWidth: 2)
                        .foregroundStyle(Theme.inkOnGold70)
                }
            }
        }
        .contentShape(RoundedRectangle(cornerRadius: Theme.Radius.feature, style: .continuous))
    }
}
