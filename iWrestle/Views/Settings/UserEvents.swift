//
//  UserEvents.swift
//  iWrestle
//
//  Created by Brock Zacherl on 12/11/25.
//

import SwiftUI
import CloudKit

struct UserEventsView: View {
    @Environment(CloudKitManager.self) var ck
    @Binding var userEvents: [Event]
    @State private var viewState: ViewState = .loading
    @State private var showAddSheet = false
    @State private var showAdminAdd = false

    enum ViewState {
        case loading
        case loaded
        case error(iWrestleError)
    }

    var body: some View {
        VStack(spacing: 0) {
            PushedHeader(eyebrow: "Organizer", title: "Events dashboard") {
                if ck.isAdmin {
                    IconButton(icon: .plus, size: 38, iconSize: 17, strokeWidth: 2,
                               accessibilityLabel: "Add event as admin") {
                        showAdminAdd = true
                    }
                }
            }

            switch viewState {
            case .loading:
                iWrestleProgressView()
            case .loaded:
                eventList
            case .error(let error):
                VStack(spacing: 0) {
                    ErrorViewiWrestle(error: error, action: {})
                    addButton
                        .padding(.horizontal, Theme.gutter)
                        .padding(.bottom, 24)
                }
            }
        }
        .canvas()
        .toolbar(.hidden, for: .navigationBar)
        .enableSwipeBack()
        .task { loadUserEvents() }
        .onChange(of: userEvents.count) { _, count in
            if count > 0 { viewState = .loaded }
        }
        .sheet(isPresented: $showAddSheet) {
            AddEventScreen(userEvents: $userEvents)
        }
        .sheet(isPresented: $showAdminAdd) {
            AddEventScreen(userEvents: $userEvents, mode: .admin)
        }
    }

    private var eventList: some View {
        let ordered = userEvents.sorted { $0.date < $1.date }
        return ScrollView {
            LazyVStack(spacing: 10) {
                ForEach(Array(ordered.enumerated()), id: \.element.id) { index, event in
                    NavigationLink(value: AppRoute.editEvent(event.id)) {
                        DashboardRow(index: index, event: event)
                    }
                    .buttonStyle(SurfaceButtonStyle(scale: 1))
                    .entrance(delay: Double(min(index, 5)) * 0.04)
                }
                addButton
                    .padding(.top, 8)
            }
            .padding(.horizontal, Theme.gutter)
            .padding(.top, 14)
            .padding(.bottom, 24)
        }
        .scrollIndicators(.hidden)
        .refreshable {
            userEvents = (try? await ck.fetchUserEvents()) ?? userEvents
        }
    }

    private var addButton: some View {
        PrimaryGoldButton(title: "Add event · \(launchPriceLabel)", leadingIcon: .plus, padding: 13) {
            showAddSheet = true
        }
    }

    func loadUserEvents() {
        Task {
            do {
                if userEvents.isEmpty {
                    userEvents = try await ck.fetchUserEvents()
                }
                viewState = userEvents.isEmpty ? .error(.noUserEvents) : .loaded
            } catch {
                viewState = .error(.noUserEvents)
            }
        }
    }
}

/// "01 · tile · name / date · city · LIVE · ›"
struct DashboardRow: View {
    @Environment(\.isPressed) private var isPressed
    let index: Int
    let event: Event

    private var isLive: Bool {
        event.date >= Calendar.current.startOfDay(for: Date())
    }

    var body: some View {
        let parts = AddressParts(event.address)
        HStack(spacing: 13) {
            Text(String(format: "%02d", index + 1))
                .font(.monoIndex)
                .foregroundStyle(Theme.textTertiary)
            EventLogoView(url: event.logo, name: event.name, size: 44,
                          radius: Theme.Radius.tile44, font: .monoTile13)
            VStack(alignment: .leading, spacing: 3) {
                Text(event.name)
                    .font(.rowTitle)
                    .foregroundStyle(Theme.textPrimary)
                    .lineLimit(1)
                Text(parts.city.isEmpty ? event.date.shortDayLabel : "\(event.date.shortDayLabel) · \(parts.city)")
                    .font(.caption11_5)
                    .foregroundStyle(Theme.textTertiary)
                    .lineLimit(1)
            }
            .frame(maxWidth: .infinity, alignment: .leading)
            if isLive {
                LiveBadge()
            } else {
                Text("PAST")
                    .font(.monoBadge)
                    .kerning(0.95)
                    .foregroundStyle(Theme.textTertiary)
                    .padding(.horizontal, 9)
                    .padding(.vertical, 4)
                    .overlay(Capsule().strokeBorder(Theme.borderDefault, lineWidth: 1))
            }
            Chevron()
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
