//
//  HomeView.swift
//  iWrestle
//
//  Created by Brock Zacherl on 11/26/25.
//

import SwiftUI
import MapKit

struct HomeView: View {
    @Environment(CloudKitManager.self) var ck
    @Environment(LocationManager.self) var lm
    @Binding var path: NavigationPath
    @Environment(\.tabBarInset) private var tabBarInset

    @State private var viewState: HomeViewState = .loading
    @State private var isFetching = false
    @State private var showFilter = false
    @State private var filters: EventFilters = .default
    @State private var viewMode: ViewMode = .list
    @State private var selectedPin: Event.ID?

    enum ViewMode { case list, map }

    private var title: String {
        "Events near\n\(lm.userCity ?? "you")."
    }

    var body: some View {
        NavigationStack(path: $path) {
            VStack(spacing: 0) {
                ScreenHeader(eyebrow: "Nearby · \(Date().monthYearLabel)", title: title) {
                    HStack(spacing: 8) {
                        IconButton(icon: viewMode == .list ? .map : .list,
                                   accessibilityLabel: viewMode == .list ? "Show map" : "Show list") {
                            withAnimation(Motion.normal) {
                                viewMode = viewMode == .list ? .map : .list
                                selectedPin = nil
                            }
                        }
                        IconButton(icon: .slidersHorizontal,
                                   badge: !filters.isDefault,
                                   accessibilityLabel: "Filter events") {
                            showFilter = true
                        }
                    }
                }

                content
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
            }
            .safeAreaPadding(.bottom, tabBarInset)
            .canvas()
            .toolbar(.hidden, for: .navigationBar)
            .navigationDestination(for: AppRoute.self) { route in
                switch route {
                case .eventDetail(let event):
                    EventDetailView(event: event)
                case .flyer(let url):
                    PDFQuickLookView(url: url)
                default:
                    EmptyView()
                }
            }
            .task(id: lm.userCoordinates?.latitude) {
                if case .loading = viewState { await loadEvents() }
            }
            .onChange(of: lm.isPermissionDenied) { _, denied in
                if denied == true, case .loading = viewState {
                    viewState = .error(.locationError)
                }
            }
            .sheet(isPresented: $showFilter) {
                EventsFilterView(filters: filters) { applied, events in
                    filters = applied
                    viewState = events.isEmpty ? .error(.noData) : .loaded(events)
                }
            }
        }
    }

    @ViewBuilder
    private var content: some View {
        switch viewState {
        case .loading:
            iWrestleProgressViewHome()
        case .loaded(let events):
            switch viewMode {
            case .list:
                EventsListView(events: events, userLocation: lm.userLocation)
                    .refreshable { await loadEvents() }
                    .transition(.opacity)
            case .map:
                EventsMapView(events: events, userLocation: lm.userLocation, selected: $selectedPin)
                    .transition(.opacity)
            }
        case .error(let error):
            ErrorViewiWrestle(error: error, retryTitle: error == .noData ? "Try again" : nil) {
                viewState = .loading
                Task { await loadEvents() }
            }
        }
    }

    // MARK: - Loading

    func loadEvents() async {
        guard !isFetching else { return }
        isFetching = true
        defer { isFetching = false }

        #if DEBUG
        if MockEvents.isEnabled {
            viewState = .loaded(MockEvents.nearby)
            return
        }
        #endif

        guard let userLocation = lm.userLocation else {
            if lm.isPermissionDenied == true {
                viewState = .error(.locationError)
            }
            return
        }

        do {
            let events: [Event]
            if filters.isDefault {
                events = try await fetchWithExpandingRadius(from: userLocation)
            } else if let predicates = filters.predicates(userLocation: userLocation) {
                events = try await ck.fetchEvents(predicates: predicates)
            } else {
                events = []
            }
            viewState = events.isEmpty ? .error(.noData) : .loaded(events)
        } catch {
            viewState = .error(.noData)
        }
    }

    func fetchWithExpandingRadius(from location: CLLocation) async throws -> [Event] {
        let radii: [Double] = [250, 500, 999]
        for radius in radii {
            var predicates = [NSPredicate]()
            predicates.append(NSPredicate(
                format: "distanceToLocation:fromLocation:(location, %@) < %f",
                location,
                radius.milesToMeters
            ))
            if let interval = DateOptionsIWrestle.thisMonth.dateInterval() {
                predicates.append(NSPredicate(
                    format: "date >= %@ AND date < %@",
                    interval.start as CVarArg,
                    interval.end as CVarArg
                ))
            }
            let events = try await ck.fetchEvents(predicates: predicates, limit: 20)
            if !events.isEmpty { return events }
        }
        return []
    }
}

enum HomeViewState {
    case loading
    case loaded([Event])
    case error(iWrestleError)
}
