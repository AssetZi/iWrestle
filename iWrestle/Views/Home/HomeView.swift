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
    @State private var viewState: HomeViewState = .loading
    @State private var isFetching = false
    @State private var showFilter = false
    var body: some View {
        NavigationStack {
            Group{
                switch viewState {
                case .loading:
                    iWrestleProgressViewHome()
                case .loaded(let events):
                    EventsListView(events: events, userLocation: lm.userLocation)
                case .error(let error):
                    ErrorViewiWrestle(error: error, action: {
                        viewState = .loading
                        loadEvents()
                    })
                }
            }
            .navigationTitle(Text("iWrestle"))
            .task(id: lm.userCoordinates?.latitude) {
                if case .loading = viewState { loadEvents() }
            }
            .onChange(of: lm.isPermissionDenied) { _, denied in
                if denied == true, case .loading = viewState {
                    viewState = .error(.locationError)
                }
            }
            .refreshable {
                loadEvents()
            }
            .scrollIndicators(.hidden)
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button {
                        showFilter = true
                    } label: {
                        Image(systemName: "slider.horizontal.3")
                    }
                }
            }
            .sheet(isPresented: $showFilter) {
                EventsFilterView(viewState: $viewState)
            }
        }
    }

    func loadEvents() {
        guard !isFetching else { return }
        Task {
            isFetching = true
            defer { isFetching = false }
            do {
                guard let userLocation = lm.userLocation else {
                    if lm.isPermissionDenied == true {
                        viewState = .error(.locationError)
                    }
                    return
                }
                let events = try await fetchWithExpandingRadius(from: userLocation)
                if !events.isEmpty {
                    viewState = .loaded(events)
                } else {
                    viewState = .error(.noData)
                }
            } catch {
                viewState = .error(.noData)
            }
        }
    }

    func fetchWithExpandingRadius(from location: CLLocation) async throws -> [Event] {
        let radii: [Double] = [250, 500, 999]
        for radius in radii {
            var predicates = [NSPredicate]()
            let distancePredicate = NSPredicate(
                format: "distanceToLocation:fromLocation:(location, %@) < %f",
                location,
                radius.milesToMeters
            )
            predicates.append(distancePredicate)
            if let interval = DateOptionsIWrestle.thisMonth.dateInterval() {
                let datePredicate = NSPredicate(
                    format: "date >= %@ AND date < %@",
                    interval.start as CVarArg,
                    interval.end as CVarArg
                )
                predicates.append(datePredicate)
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

//#Preview {
//    HomeView()
//}

