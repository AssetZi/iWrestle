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
    @State private var showFilter = false
    var body: some View {
        NavigationStack {
            Group{
                switch viewState {
                case .loading:
                    iWrestleProgressView()
                case .loaded(let events):
                    EventsListView(events: events, userLocation: lm.userLocation)
                case .error(let error):
                    ErrorViewiWrestle(error: error)
                
                }
            }
            .navigationTitle(Text("iWrestle"))
            .task {
                if case .loading = viewState { loadEvents() }
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
        Task {
            let predicates = setPredicates()
            let events = try await ck.fetchEvents(predicates: predicates)
            if !events.isEmpty {
                viewState = .loaded(events)
            } else {viewState = .error(.noData)}
        }
    }
    func setPredicates() -> [NSPredicate] {
        var predicates = [NSPredicate]()
        guard let userLocation = lm.userLocation else {viewState = .error(.locationError); return []}
        
        let radiusInMeters = 250.milesToMeters
        let distancePredicate = NSPredicate(
            format: "distanceToLocation:fromLocation:(location, %@) < %f",
            userLocation,
            radiusInMeters
        )
        predicates.append(distancePredicate)
        
        if let interval = DateOptionsIWrestle.thisMonth.dateInterval() {
            let datePredicate = NSPredicate(format: "date >= %@ AND date < %@", interval.start as CVarArg, interval.end as CVarArg)
            predicates.append(datePredicate)
        }
        return predicates
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

