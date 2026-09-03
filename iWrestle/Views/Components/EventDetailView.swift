//
//  EventDetailView.swift
//  iWrestle
//
//  Created by Brock Zacherl on 12/12/25.
//

import SwiftUI
import MapKit
import StoreKit

struct EventDetailView: View {
    @Environment(\.openURL) private var openURL
    @Environment(\.requestReview) private var requestReview
    @Environment(LocationManager.self) private var lm
    @AppStorage("eventDetailViewCount") private var eventDetailViewCount = 0
    @AppStorage("lastReviewRequestDate") private var lastReviewRequestDate = Date.distantPast.timeIntervalSince1970
    let event: Event

    @State private var sharePayload: SharePayload?
    @State private var isPreparingShare = false

    private var parts: AddressParts { AddressParts(event.address) }

    /// What the share sheet sends alongside the flyer PDF. There is no public
    /// event URL yet, so the text is the event's essentials, the registration
    /// link if any, and the App Store link.
    private var shareText: String {
        var lines = [event.name, event.date.longDateLabel, event.address]
        if let registration = event.registration, !registration.isEmpty {
            lines.append(registration)
        }
        lines.append("Found on iWrestle")
        lines.append("Get the iWrestle app: \(AppLinks.appStore.absoluteString)")
        return lines.joined(separator: "\n")
    }

    var body: some View {
        VStack(spacing: 0) {
            HStack {
                BackButton()
                Spacer()
                Button(action: prepareShare) {
                    IconButtonLabel(icon: .share, size: 38, iconSize: 16)
                        .overlay { if isPreparingShare { GoldSpinner(size: 16) } }
                }
                .buttonStyle(PressableButtonStyle())
                .disabled(isPreparingShare)
                .accessibilityLabel("Share event")
            }
            .padding(.horizontal, Theme.gutter)
            .padding(.top, 6)
            .padding(.bottom, 8)

            ScrollView {
                VStack(alignment: .leading, spacing: 16) {
                    header
                    ChipFlow(spacing: 6) {
                        ForEach(event.ageGroups, id: \.self) { AgePill(text: $0) }
                    }
                    if let registration = event.registration, let url = URL(string: registration) {
                        PrimaryGoldButton(title: "Register for this event", icon: .arrowUpRight) {
                            openURL(url)
                        }
                    }
                    flyerCard
                    whenAndWhere
                    contact
                }
                .padding(.horizontal, Theme.gutter)
                .padding(.top, 8)
                .padding(.bottom, 44)
            }
            .scrollIndicators(.hidden)
        }
        .canvas()
        .toolbar(.hidden, for: .navigationBar)
        .enableSwipeBack()
        .sheet(item: $sharePayload) { payload in
            ActivityShareSheet(items: payload.items)
                .presentationDetents([.medium, .large])
        }
        .onAppear { requestReviewIfAppropriate() }
    }

    // MARK: - Sections

    private var header: some View {
        HStack(spacing: 14) {
            EventLogoView(url: event.logo, name: event.name, size: 64,
                          radius: Theme.Radius.tile64, font: .monoTile18)
            VStack(alignment: .leading, spacing: 5) {
                Eyebrow("\(event.typeTitle) · \(event.date.shortDayLabel)", size: 10)
                Text(event.name)
                    .font(.detailTitle)
                    .tracked(-0.02, 23)
                    .foregroundStyle(Theme.textPrimary)
                    .fixedSize(horizontal: false, vertical: true)
            }
        }
    }

    private var flyerCard: some View {
        NavigationLink(value: AppRoute.flyer(event.flyer)) {
            RowSurface {
                CardRow(icon: .fileText, label: "Event flyer") {
                    Text("PDF")
                        .font(.monoTag)
                        .foregroundStyle(Theme.textTertiary)
                    Chevron()
                }
            }
        }
        .buttonStyle(SurfaceButtonStyle(scale: 1))
        .cardContainer()
    }

    private var whenAndWhere: some View {
        VStack(alignment: .leading, spacing: 9) {
            SectionLabel("When & where")
            VStack(spacing: 0) {
                MiniMapStrip(coordinate: event.location.coordinate)
                    .frame(height: 110)
                CardRow(icon: .calendar, iconSize: 16, label: event.date.longDateLabel, labelFont: .body13_5) {
                    EmptyView()
                }
                HairlineDivider()
                HStack(spacing: 12) {
                    LucideIcon(.mapPin, size: 16)
                        .foregroundStyle(Theme.textTertiary)
                    VStack(alignment: .leading, spacing: 2) {
                        Text(parts.venue)
                            .font(.body13_5)
                            .foregroundStyle(Theme.textPrimary)
                            .lineLimit(2)
                        Text(distanceLine)
                            .font(.caption11_5)
                            .foregroundStyle(Theme.textTertiary)
                            .lineLimit(1)
                    }
                    .frame(maxWidth: .infinity, alignment: .leading)
                    Button(action: openInMaps) {
                        HStack(spacing: 5) {
                            LucideIcon(.navigation, size: 13, strokeWidth: 2)
                            Text("Maps").font(.body12Medium)
                        }
                        .foregroundStyle(Theme.gold)
                        .contentShape(Rectangle())
                    }
                    .buttonStyle(PressableButtonStyle())
                    .accessibilityLabel("Open in Maps")
                }
                .padding(.horizontal, 16)
                .padding(.vertical, 13)
            }
            .cardContainer()
        }
    }

    private var contact: some View {
        VStack(alignment: .leading, spacing: 9) {
            SectionLabel("Contact")
            VStack(spacing: 0) {
                HStack(spacing: 12) {
                    Text(event.contactInitials)
                        .font(.caption11_5Medium)
                        .foregroundStyle(Theme.textSecondary)
                        .frame(width: 34, height: 34)
                        .background(Circle().fill(Theme.slate800))
                    Text(event.contactName)
                        .font(.body14)
                        .foregroundStyle(Theme.textPrimary)
                        .frame(maxWidth: .infinity, alignment: .leading)
                    Text("ORGANIZER")
                        .font(.monoTag)
                        .foregroundStyle(Theme.textTertiary)
                }
                .padding(.horizontal, 16)
                .padding(.vertical, 13)

                HairlineDivider()
                ContactRow(icon: .mail, text: event.eventContactEmail,
                           url: .mailto(event.eventContactEmail,
                                        subject: "Question about \(event.name)"))

                if !event.eventContactPhone.isEmpty {
                    HairlineDivider()
                    let digits = event.eventContactPhone.filter { $0.isNumber || $0 == "+" }
                    ContactRow(icon: .phone, text: event.eventContactPhone,
                               url: URL(string: "tel:\(digits)"))
                }
            }
            .cardContainer()
        }
    }

    private var distanceLine: String {
        if let miles = event.miles(from: lm.userLocation) {
            return parts.city.isEmpty ? "\(miles) mi away" : "\(parts.city) · \(miles) mi away"
        }
        return parts.city
    }

    // MARK: - Actions

    /// Renders the flyer, then opens the share sheet with text + PDF. If the
    /// render fails the text still goes out on its own.
    private func prepareShare() {
        guard !isPreparingShare else { return }
        isPreparingShare = true
        var items: [Any] = [ShareTextItem(text: shareText, subject: event.name)]
        if let pdf = EventPDFExporter.makePDF(for: event) {
            items.append(pdf)
        }
        isPreparingShare = false
        sharePayload = SharePayload(items: items)
    }

    private func openInMaps() {
        let item = MKMapItem(location: event.location,
                             address: MKAddress(fullAddress: event.address, shortAddress: nil))
        item.name = event.name
        item.openInMaps()
    }

    private func requestReviewIfAppropriate() {
        eventDetailViewCount += 1
        let thirtyDaysAgo = Date().addingTimeInterval(-30 * 24 * 60 * 60).timeIntervalSince1970
        guard eventDetailViewCount >= 3, lastReviewRequestDate < thirtyDaysAgo else { return }
        lastReviewRequestDate = Date().timeIntervalSince1970
        eventDetailViewCount = 0
        requestReview()
    }
}

/// Gold, tappable email / phone row.
struct ContactRow: View {
    let icon: Lucide
    let text: String
    let url: URL?

    var body: some View {
        Group {
            if let url {
                Link(destination: url) { label }
                    .buttonStyle(SurfaceButtonStyle(scale: 1))
            } else {
                label
            }
        }
    }

    private var label: some View {
        RowSurface {
            HStack(spacing: 12) {
                LucideIcon(icon, size: 15)
                    .foregroundStyle(Theme.textTertiary)
                Text(text)
                    .font(.body13)
                    .foregroundStyle(Theme.gold)
                    .lineLimit(1)
                    .truncationMode(.middle)
                    .frame(maxWidth: .infinity, alignment: .leading)
            }
            .padding(.horizontal, 16)
            .padding(.vertical, 12)
            .contentShape(Rectangle())
        }
    }
}

/// Non-interactive dark map strip with a gold pin at the event.
struct MiniMapStrip: View {
    let coordinate: CLLocationCoordinate2D

    var body: some View {
        Map(initialPosition: .region(MKCoordinateRegion(center: coordinate,
                                                        latitudinalMeters: 1600,
                                                        longitudinalMeters: 1600)),
            interactionModes: []) {
            Annotation("", coordinate: coordinate, anchor: .bottom) {
                VStack(spacing: 0) {
                    LucideIcon(.mapPin, size: 14, strokeWidth: 2)
                        .foregroundStyle(Theme.onAccent)
                        .frame(width: 30, height: 30)
                        .background(Circle().fill(Theme.gold))
                    Rectangle().fill(Theme.gold600).frame(width: 2, height: 7)
                }
            }
            .annotationTitles(.hidden)
        }
        .mapStyle(.standard(elevation: .flat, emphasis: .muted, pointsOfInterest: .excludingAll, showsTraffic: false))
        .mapControlVisibility(.hidden)
        .saturation(0.25)
        .brightness(-0.04)
        .allowsHitTesting(false)
        .accessibilityHidden(true)
    }
}
