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
    @Environment(LogoManager.self) var logos
    @Binding var path: NavigationPath
    @Environment(\.tabBarInset) private var tabBarInset
    @Environment(\.dynamicTypeSize) private var dynamicTypeSize

    @State private var viewState: HomeViewState = .loading
    /// A new load cancels the one in flight, so the latest location or
    /// filters always win and a superseded load never shows its result.
    @State private var loads = LatestLoad<HomeLoad>()
    /// Where the latest load searched from: the live fix, or the last
    /// session's when this one has none yet.
    @State private var loadLocation: CLLocation?
    /// The logo fetch for the list on screen; a new list cancels it so its
    /// own logos are not queued behind rows that are gone.
    @State private var logoLoad: Task<Void, Never>?
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
                if let fix = lm.userLocation {
                    // A load from the last session's location is already
                    // running or shown. Restarting it for a fix a few miles
                    // away would throw that work out for the same events.
                    guard HomeReload.isNeeded(for: fix, loadedFrom: loadLocation) else { return }
                    await reload().value
                } else if case .loading = viewState {
                    await reload().value
                }
            }
            .onChange(of: lm.isPermissionDenied) { _, denied in
                // Reloads so a search started from the last session's
                // location does not show after permission was taken away.
                if denied == true, lm.userLocation == nil { reload() }
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
                EventsListView(list: list, userLocation: distanceOrigin)
                    .refreshable { await reload().value }
                    .transition(.opacity)
            case .map:
                EventsMapView(events: list.events, userLocation: distanceOrigin, selected: $selectedPin)
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

    /// Where distances are measured from: the fix, or until it arrives the
    /// location the list was loaded for.
    private var distanceOrigin: CLLocation? {
        lm.userLocation ?? loadLocation
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
            if case .loaded(let list) = state { LaunchTiming.mark("list shown (\(list.events.count) events)") }
            emptyCampaign = load.emptyCampaign
            viewState = state
            if case .loaded(let list) = state {
                logoLoad?.cancel()
                logoLoad = Task { await logos.load(list.events) }
            }
        }
    }

    /// What a fresh load ends in. A nil state leaves the screen as is (no
    /// location yet and permission not denied).
    ///
    /// Searches from the last session's location until this one has a fix,
    /// so a returning user's query goes out at launch and not after GPS.
    private func loadEvents() async -> HomeLoad {
        #if DEBUG
        if MockEvents.isEnabled {
            return HomeLoad(state: .loaded(EventList(MockEvents.feed, userLocation: lm.userLocation)))
        }
        #endif

        let denied = lm.isPermissionDenied == true
        guard let userLocation = lm.userLocation ?? (denied ? nil : LocationManager.lastKnownLocation) else {
            return HomeLoad(state: denied ? .error(.locationError) : nil)
        }
        loadLocation = userLocation

        LaunchTiming.mark("home load started")
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

/// Whether a new location fix calls for loading the feed again.
nonisolated enum HomeReload {
    /// About ten miles. The feed searches 250 miles out, so a smaller move
    /// brings back the same events.
    static let moveThreshold: CLLocationDistance = 16_000

    static func isNeeded(for fix: CLLocation, loadedFrom: CLLocation?) -> Bool {
        guard let loadedFrom else { return true }
        return fix.distance(from: loadedFrom) > moveThreshold
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
