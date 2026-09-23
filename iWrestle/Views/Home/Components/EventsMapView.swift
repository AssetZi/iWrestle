//
//  EventsMapView.swift
//  iWrestle
//
//  Map mode for the home tab: an inset dark map with gold monogram pins.
//  Selecting a pin raises a mini card that pushes the event detail.
//

import SwiftUI
import MapKit

struct EventsMapView: View {
    let events: [Event]
    let userLocation: CLLocation?
    @Binding var selected: Event.ID?
    @State private var position: MapCameraPosition = .automatic

    private var selectedEvent: Event? {
        guard let selected else { return nil }
        return events.first { $0.id == selected }
    }

    var body: some View {
        ZStack(alignment: .bottom) {
            Map(position: $position) {
                if let userLocation {
                    Annotation("You", coordinate: userLocation.coordinate) {
                        UserLocationDot()
                    }
                    .annotationTitles(.hidden)
                }
                ForEach(events) { event in
                    Annotation(event.name, coordinate: event.location.coordinate, anchor: .bottom) {
                        EventPin(monogram: event.name.monogram, selected: event.id == selected)
                            .onTapGesture {
                                withAnimation(Motion.normal) { selected = event.id }
                            }
                    }
                    .annotationTitles(.hidden)
                }
            }
            .mapStyle(.standard(elevation: .flat, emphasis: .muted, pointsOfInterest: .excludingAll, showsTraffic: false))
            .mapControlVisibility(.hidden)
            .saturation(0.25)
            .brightness(-0.04)

            if let event = selectedEvent {
                NavigationLink(value: AppRoute.eventDetail(event)) {
                    MapMiniCard(event: event, userLocation: userLocation)
                }
                .buttonStyle(PressableButtonStyle(scale: 0.99))
                .padding(12)
                .transition(.move(edge: .bottom).combined(with: .opacity))
            }
        }
        .animation(Motion.easeOut(0.22), value: selected)
        .clipShape(RoundedRectangle(cornerRadius: Theme.Radius.feature, style: .continuous))
        .overlay(
            RoundedRectangle(cornerRadius: Theme.Radius.feature, style: .continuous)
                .strokeBorder(Theme.borderSubtle, lineWidth: 1)
        )
        .padding(.horizontal, Theme.gutter)
        .padding(.top, 6)
        .padding(.bottom, 16)
    }
}

/// 32pt gold disc with an ink monogram, gold-700 ring and a 2×7 tail.
/// Selected: 40pt, white ring, gold glow.
struct EventPin: View {
    let monogram: String
    let selected: Bool

    var body: some View {
        VStack(spacing: 0) {
            Text(monogram)
                .font(.monoPin)
                .foregroundStyle(Theme.onAccent)
                .frame(width: selected ? 40 : 32, height: selected ? 40 : 32)
                .background(Circle().fill(Theme.gold))
                .overlay(Circle().strokeBorder(selected ? .white : Theme.gold700, lineWidth: 2))
                .shadow(color: selected ? Theme.gold.opacity(0.35) : .black.opacity(0.45),
                        radius: selected ? 14 : 4, y: selected ? 8 : 2)
            Rectangle()
                .fill(Theme.gold600)
                .frame(width: 2, height: 7)
        }
        .animation(Motion.fast, value: selected)
        .zIndex(selected ? 5 : 2)
    }
}

/// Pulsing slate user-location dot.
struct UserLocationDot: View {
    @State private var pulse = false

    var body: some View {
        ZStack {
            Circle()
                .fill(Theme.slate400.opacity(0.45))
                .frame(width: 12, height: 12)
                .scaleEffect(pulse ? 3.2 : 1)
                .opacity(pulse ? 0 : 1)
            Circle()
                .fill(Theme.slate300)
                .frame(width: 12, height: 12)
                .overlay(Circle().strokeBorder(.white, lineWidth: 2.5))
        }
        .onAppear {
            withAnimation(Motion.easeOut(2).repeatForever(autoreverses: false)) { pulse = true }
        }
    }
}

/// Elevated card raised above the map for the selected pin.
struct MapMiniCard: View {
    let event: Event
    let userLocation: CLLocation?

    var body: some View {
        HStack(spacing: 12) {
            EventLogoView(url: event.logo, name: event.name, size: 44, radius: Theme.Radius.tile44,
                          font: .monoTile13, fill: Theme.slate900, showsBorder: false)
            VStack(alignment: .leading, spacing: 2) {
                Text(event.name)
                    .font(.rowTitle)
                    .foregroundStyle(Theme.textPrimary)
                    .lineLimit(1)
                Text(subtitle)
                    .font(.caption11_5)
                    .foregroundStyle(Theme.textTertiary)
                    .lineLimit(1)
            }
            .frame(maxWidth: .infinity, alignment: .leading)
            Chevron(color: Theme.slate400)
        }
        .padding(.horizontal, 14)
        .padding(.vertical, 13)
        .background(Theme.slate800)
        .clipShape(RoundedRectangle(cornerRadius: Theme.Radius.card, style: .continuous))
        .overlay(
            RoundedRectangle(cornerRadius: Theme.Radius.card, style: .continuous)
                .strokeBorder(Theme.borderDefault, lineWidth: 1)
        )
        .shadow(color: .black.opacity(0.55), radius: 24, y: 18)
        .contentShape(RoundedRectangle(cornerRadius: Theme.Radius.card, style: .continuous))
    }

    private var subtitle: String {
        if let miles = event.miles(from: userLocation) {
            return "\(event.date.shortDayLabel) · \(miles) mi"
        }
        return event.date.shortDayLabel
    }
}
