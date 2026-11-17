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
    @State private var loads = LatestLoad<HomeLoad>()
    @State private var showFilter = false
    @State private var filters: EventFilters = .default
    @State private var viewMode: ViewMode = .list
    @State private var selectedPin: Event.ID?
    /// Which promo the "No events found" screen shows, set with it: nothing
    /// nearby and filters that match nothing are tracked apart. A failed
    /// fetch shows none: it is usually no network, where the App Store card
    /// a tap opens can't load, and those taps would muddy both campaigns.
    @State private var emptyCampaign: PromoCampaign?

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
                if error == .noData, let emptyCampaign, !dynamicTypeSize.isAccessibilitySize {
                    PromoSlot(campaign: emptyCampaign)
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
        loads.start { await loadEvents() } deliver: { load in
            guard let state = load.state else { return }
            emptyCampaign = load.emptyCampaign
            viewState = state
        }
    }

    /// What a fresh load ends in. A nil state leaves the screen as is (no
    /// location yet and permission not denied).
    private func loadEvents() async -> HomeLoad {
        #if DEBUG
        if MockEvents.isEnabled {
            return HomeLoad(state: .loaded(EventList(MockEvents.feed, userLocation: lm.userLocation)))
        }
        #endif

        guard let userLocation = lm.userLocation else {
            return HomeLoad(state: lm.isPermissionDenied == true ? .error(.locationError) : nil)
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
        // Nothing nearby and filters that match nothing are tracked apart;
        // a failed fetch gets no promo (see `emptyCampaign`).
        let campaign: PromoCampaign? = switch result {
        case .success: requested.isDefault ? .empty : .filtered
        case .failure: nil
        }
        return HomeLoad(state: HomeViewState.after(result, userLocation: userLocation),
                        emptyCampaign: campaign)
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

/// One finished home-feed load: the state to show and, for "No events
/// found", which promo campaign it belongs to.
struct HomeLoad {
    var state: HomeViewState?
    var emptyCampaign: PromoCampaign? = nil
}

enum HomeViewState {
    case loading
    case loaded(EventList)
    case error(iWrestleError)

    /// What a finished home-feed load shows. A superseded load's state is
    /// never delivered (`LatestLoad` drops it), so an error shown here is a
    /// real one. Keep this free of side effects: it runs for dropped loads.
    static func after(_ result: Result<[Event], Error>, userLocation: CLLocation) -> HomeViewState {
        switch result {
        case .success(let events):
            return events.isEmpty ? .error(.noData) : .loaded(EventList(events, userLocation: userLocation))
        case .failure:
            return .error(.noData)
        }
    }
}
