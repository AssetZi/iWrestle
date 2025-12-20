//
//  EventsListView.swift
//  iWrestle
//
//  Created by Brock Zacherl on 12/17/25.
//

import SwiftUI
import MapKit

struct EventsListView: View {
    let events: [Event]
    let userLocation: CLLocation?
    var body: some View {
        ScrollView {
            ForEach(events.sorted(by: { lhs, rhs in
                // 1) Group by calendar day (earliest first)
                let cal = Calendar.current
                let lhsDay = cal.startOfDay(for: lhs.date)
                let rhsDay = cal.startOfDay(for: rhs.date)
                if lhsDay != rhsDay { return lhsDay < rhsDay }

                // 2) Within the same day, sort by distance (closest first) if we have a user location
                if let userLocation {
                    let lhsDistance = lhs.location.distance(from: userLocation)
                    let rhsDistance = rhs.location.distance(from: userLocation)
                    if lhsDistance != rhsDistance { return lhsDistance < rhsDistance }
                }

                // 3) Final stable tiebreaker
                return lhs.name < rhs.name
            })) { event in
                NavigationLink{
                    EventDetailView(event: event)
                } label:{
                    EventCell(event: event, userLocation: userLocation)
                }
            }
        }
    }
}


