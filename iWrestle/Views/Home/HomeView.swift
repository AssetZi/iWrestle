//
//  HomeView.swift
//  iWrestle
//
//  Created by Brock Zacherl on 11/26/25.
//

import SwiftUI
import MapKit
import CloudKit

struct HomeView: View {
    @Environment(CloudKitManager.self) var ck
    @Environment(LocationManager.self) var lm
    @Binding var path: NavigationPath
    @Environment(\.tabBarInset) private var tabBarInset
    @Environment(\.dynamicTypeSize) private var dynamicTypeSize

    @State private var viewState: HomeViewState = .loading
    /// The load in flight. A new one cancels it, so the latest location or
    /// filters always win and a superseded load never shows its result.
    @State private var loadTask: Task<Void, Never>?
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
        loadTask?.cancel()
        let task = Task { await loadEvents() }
        loadTask = task
        return task
    }

    private func loadEvents() async {
        #if DEBUG
        if MockEvents.isEnabled {
            viewState = .loaded(EventList(MockEvents.nearby, userLocation: lm.userLocation))
            return
        }
        #endif

        guard let userLocation = lm.userLocation else {
            if lm.isPermissionDenied == true {
                viewState = .error(.locationError)
            }
            return
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
        // A newer load replaced this one; its answer is the one to show.
        guard !Task.isCancelled else { return }
        if let state = HomeViewState.after(result, userLocation: userLocation) {
            viewState = state
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

    /// What a finished home-feed load shows, or nil to leave the screen as is.
    /// A cancelled load was replaced by a newer one, so it says nothing about
    /// whether events exist.
    static func after(_ result: Result<[Event], Error>, userLocation: CLLocation) -> HomeViewState? {
        switch result {
        case .success(let events):
            return events.isEmpty ? .error(.noData) : .loaded(EventList(events, userLocation: userLocation))
        case .failure(let error):
            return error.isCancellation ? nil : .error(.noData)
        }
    }
}

extension Error {
    /// Swift task, CloudKit and URL loading each report cancellation their own way.
    var isCancellation: Bool {
        if self is CancellationError { return true }
        if let ck = self as? CKError, ck.code == .operationCancelled { return true }
        if let url = self as? URLError, url.code == .cancelled { return true }
        return false
    }
}
