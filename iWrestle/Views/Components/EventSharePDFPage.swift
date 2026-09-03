//
//  EventSharePDFPage.swift
//  iWrestle
//
//  The one-page flyer attached to an event share. Rendered by
//  `EventPDFExporter`, so everything here must draw synchronously:
//  `Image(uiImage:)` only — no `AsyncImage`, no `Map`.
//

import SwiftUI

struct EventSharePDFPage: View {
    /// US Letter at 72dpi.
    static let pageSize = CGSize(width: 612, height: 792)

    let event: Event
    let logo: UIImage?
    let qr: UIImage?

    private var parts: AddressParts { AddressParts(event.address) }

    /// The address minus the venue name (already shown above it) and the
    /// trailing country: "499 Mayfield Rd, Clarion, PA 16214".
    private var streetLine: String {
        var components = event.address
            .split(separator: ",")
            .map { $0.trimmingCharacters(in: .whitespaces) }
            .filter { !$0.isEmpty }
        if !components.isEmpty { components.removeFirst() }
        if let last = components.last?.lowercased(),
           ["united states", "usa", "us", "canada"].contains(last) {
            components.removeLast()
        }
        return components.isEmpty ? parts.city : components.joined(separator: ", ")
    }

    private var registration: String? {
        guard let link = event.registration?.trimmingCharacters(in: .whitespacesAndNewlines),
              !link.isEmpty else { return nil }
        return link
    }

    private let margin: CGFloat = 48

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            brandBar
            heroBand
            VStack(alignment: .leading, spacing: 18) {
                whenAndWhere
                if let registration { registrationBlock(registration) }
                organizer
            }
            .padding(.horizontal, margin)
            .padding(.top, 24)

            Spacer(minLength: 28)
            footer
        }
        .frame(width: Self.pageSize.width, alignment: .top)
        .frame(minHeight: Self.pageSize.height, alignment: .top)
        .background(Theme.ink)
        .environment(\.colorScheme, .dark)
    }

    // MARK: - Sections

    private var brandBar: some View {
        HStack(spacing: 9) {
            Image("iWrestleWhite")
                .resizable()
                .scaledToFit()
                .frame(width: 20, height: 20)
            Eyebrow("iWrestle", color: Theme.textPrimary, size: 11, tracking: 0.2)
            Spacer(minLength: 12)
            Eyebrow("Event flyer", color: Theme.textTertiary, size: 10, tracking: 0.18)
        }
        .padding(.horizontal, margin)
        .padding(.top, 34)
        .padding(.bottom, 18)
    }

    /// The gold card, same recipe as `GoldFeatureCard` but sized for print.
    private var heroBand: some View {
        HStack(alignment: .top, spacing: 20) {
            logoTile(size: 72, radius: Theme.Radius.tile64)

            VStack(alignment: .leading, spacing: 8) {
                Eyebrow("\(event.typeTitle) · \(event.date.shortDayLabel)",
                        color: Theme.inkOnGold62, size: 10, weight: .semibold)
                Text(event.name)
                    .font(AppFont.sans(34, .regular))
                    .tracked(-0.02, 34)
                    .fixedSize(horizontal: false, vertical: true)
                Text(parts.city.isEmpty ? parts.venue : "\(parts.venue) · \(parts.city)")
                    .font(.body14)
                    .foregroundStyle(Theme.inkOnGold72)
                    .fixedSize(horizontal: false, vertical: true)
                if !event.ageGroups.isEmpty {
                    ChipFlow(spacing: 6) {
                        ForEach(event.ageGroups, id: \.self) { AgePill(text: $0, onGold: true) }
                    }
                    .padding(.top, 4)
                }
            }
            Spacer(minLength: 0)
        }
        .padding(EdgeInsets(top: 22, leading: 26, bottom: 22, trailing: 26))
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(
            ZStack {
                Theme.gold
                DotGrid(color: Theme.slate950.opacity(0.12))
            }
        )
        .foregroundStyle(Theme.onAccent)
        .clipShape(RoundedRectangle(cornerRadius: Theme.Radius.feature, style: .continuous))
        .padding(.horizontal, margin)
    }

    private func logoTile(size: CGFloat, radius: CGFloat) -> some View {
        Group {
            if let logo {
                Image(uiImage: logo)
                    .resizable()
                    .scaledToFill()
                    .frame(width: size, height: size)
                    .clipShape(RoundedRectangle(cornerRadius: radius, style: .continuous))
                    .overlay(
                        RoundedRectangle(cornerRadius: radius, style: .continuous)
                            .strokeBorder(Theme.slate950.opacity(0.14), lineWidth: 1)
                    )
            } else {
                MonogramTile(text: event.name.monogram, size: size, radius: radius,
                             font: .monoTile18, borderColor: Theme.slate950.opacity(0.14))
            }
        }
    }

    private var whenAndWhere: some View {
        VStack(alignment: .leading, spacing: 9) {
            SectionLabel("When & where")
            VStack(alignment: .leading, spacing: 0) {
                row(icon: .calendar, text: event.date.longDateLabel)
                HairlineDivider()
                HStack(alignment: .top, spacing: 12) {
                    LucideIcon(.mapPin, size: 16)
                        .foregroundStyle(Theme.textTertiary)
                    VStack(alignment: .leading, spacing: 3) {
                        Text(parts.venue)
                            .font(.body14)
                            .foregroundStyle(Theme.textPrimary)
                        Text(streetLine)
                            .font(.caption11_5)
                            .foregroundStyle(Theme.textTertiary)
                    }
                    .fixedSize(horizontal: false, vertical: true)
                    Spacer(minLength: 0)
                }
                .padding(.horizontal, 16)
                .padding(.vertical, 11)
            }
            .cardContainer()
        }
    }

    private func registrationBlock(_ link: String) -> some View {
        VStack(alignment: .leading, spacing: 9) {
            SectionLabel("Registration")
            HStack(alignment: .center, spacing: 16) {
                VStack(alignment: .leading, spacing: 6) {
                    Text(qr == nil ? "Register online" : "Scan to register")
                        .font(.body14Medium)
                        .foregroundStyle(Theme.textPrimary)
                    Text(link)
                        .font(.monoCaption)
                        .foregroundStyle(Theme.gold)
                        .fixedSize(horizontal: false, vertical: true)
                }
                .frame(maxWidth: .infinity, alignment: .leading)

                if let qr {
                    Image(uiImage: qr)
                        .interpolation(.none)
                        .resizable()
                        .frame(width: 84, height: 84)
                        .padding(8)
                        .background(
                            RoundedRectangle(cornerRadius: Theme.Radius.tile44, style: .continuous)
                                .fill(Color.white)
                        )
                }
            }
            .padding(16)
            .cardContainer()
        }
    }

    private var organizer: some View {
        VStack(alignment: .leading, spacing: 9) {
            SectionLabel("Contact")
            VStack(alignment: .leading, spacing: 0) {
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
                .padding(.vertical, 11)

                if !event.eventContactEmail.isEmpty {
                    HairlineDivider()
                    row(icon: .mail, text: event.eventContactEmail, color: Theme.gold)
                }
                if !event.eventContactPhone.isEmpty {
                    HairlineDivider()
                    row(icon: .phone, text: event.eventContactPhone, color: Theme.gold)
                }
            }
            .cardContainer()
        }
    }

    private func row(icon: Lucide, text: String, color: Color = Theme.textPrimary) -> some View {
        HStack(spacing: 12) {
            LucideIcon(icon, size: 16)
                .foregroundStyle(Theme.textTertiary)
            Text(text)
                .font(.body14)
                .foregroundStyle(color)
                .fixedSize(horizontal: false, vertical: true)
            Spacer(minLength: 0)
        }
        .padding(.horizontal, 16)
        .padding(.vertical, 11)
    }

    private var footer: some View {
        VStack(alignment: .leading, spacing: 11) {
            Rectangle()
                .fill(Theme.gold)
                .frame(height: 2)
            HStack(alignment: .firstTextBaseline, spacing: 12) {
                Text("Found on iWrestle")
                    .font(.body13)
                    .foregroundStyle(Theme.textSecondary)
                Spacer(minLength: 0)
                Text("Get the app: \(AppLinks.appStore.absoluteString)")
                    .font(.monoCaption)
                    .foregroundStyle(Theme.gold)
            }
        }
        .padding(.horizontal, margin)
        .padding(.bottom, 34)
    }
}
