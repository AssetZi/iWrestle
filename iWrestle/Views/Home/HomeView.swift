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
    @Environment(\.dynamicTypeSize) private var dynamicTypeSize

    @State private var viewState: HomeViewState = .loading
    /// A new load cancels the one in flight, so the latest location or
    /// filters always win and a superseded load never shows its result.
    @State private var loads = LatestLoad<HomeViewState?>()
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
                default:
                    EmptyView()
                }
            }
            .task(id: lm.userCoordinates?.latitude) {
                if case .loading = viewState { await reload().value }
            }
            .onChange(of: lm.isPermissionDenied) { _, denied in
                if denied == true, case .loading = viewState {
                    viewState = .error(.locationError)
                }
            }
            .sheet(isPresented: $showFilter) {
                EventsFilterView(filters: filters, currentCount: loadedCount) { applied in
                    filters = applied
                    viewState = .loading
                    reload()
                }
            }
        }
    }

    @ViewBuilder
    private var content: some View {
        switch viewState {
        case .loading:
            EventsListSkeleton()
                .transition(.opacity)
        case .loaded(let list):
            switch viewMode {
            case .list:
                EventsListView(list: list, userLocation: lm.userLocation)
                    .refreshable { await reload().value }
                    .transition(.opacity)
            case .map:
                EventsMapView(events: list.events, userLocation: lm.userLocation, selected: $selectedPin)
                    .transition(.opacity)
            }
        case .error(let error):
            ErrorViewiWrestle(error: error, retryTitle: error == .noData ? "Try again" : nil) {
                viewState = .loading
                reload()
            }
            // Nothing nearby is a dead end, so offer something else to try.
            // Left out at accessibility text sizes, where the message and
            // "Try again" need the whole screen.
            .safeAreaInset(edge: .bottom) {
                if error == .noData && !dynamicTypeSize.isAccessibilitySize {
                    PromoSlot(campaign: .empty)
                        .padding(.horizontal, Theme.gutter)
                        .padding(.bottom, 12)
                        .entrance(delay: 0.2)
                }
            }
        }
    }

    /// How many events are on screen, or nil when no list is showing.
    private var loadedCount: Int? {
        if case .loaded(let list) = viewState { return list.events.count }
        return nil
    }

    // MARK: - Loading

    /// Starts a load, cancelling any still in flight.
    @discardableResult
    private func reload() -> Task<Void, Never> {
        loads.start { await loadEvents() } deliver: { state in
            if let state { viewState = state }
        }
    }

    /// The state a fresh load ends in, or nil to leave the screen as is
    /// (no location yet and permission not denied).
    private func loadEvents() async -> HomeViewState? {
        #if DEBUG
        if MockEvents.isEnabled {
            return .loaded(EventList(MockEvents.nearby, userLocation: lm.userLocation))
        }
        #endif

        guard let userLocation = lm.userLocation else {
            return lm.isPermissionDenied == true ? .error(.locationError) : nil
        }

        let requested = filters
        let result: Result<[Event], Error>
        do {
            if requested.isDefault {
                result = .success(try await fetchWithExpandingRadius(from: userLocation))
            } else if let predicates = requested.predicates(userLocation: userLocation) {
                result = .success(try await ck.fetchEvents(predicates: predicates))
            } else {
                result = .success([])
            }
        } catch {
            result = .failure(error)
        }
        return HomeViewState.after(result, userLocation: userLocation)
    }

    func fetchWithExpandingRadius(from location: CLLocation) async throws -> [Event] {
        let radii: [Double] = [250, 500, 999]
        for radius in radii {
            // A newer load replaced this one; don't widen the search for it.
            try Task.checkCancellation()
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
            let events = try await ck.fetchEvents(predicates: predicates, limit: FetchLimits.home)
            if !events.isEmpty { return events }
        }
        return []
    }
}

enum HomeViewState {
    case loading
    case loaded(EventList)
    case error(iWrestleError)

    /// What a finished home-feed load shows. Superseded loads never get
    /// here (`LatestLoad` drops them), so any error is a real one.
    static func after(_ result: Result<[Event], Error>, userLocation: CLLocation) -> HomeViewState {
        switch result {
        case .success(let events):
            return events.isEmpty ? .error(.noData) : .loaded(EventList(events, userLocation: userLocation))
        case .failure:
            return .error(.noData)
        }
    }
}
