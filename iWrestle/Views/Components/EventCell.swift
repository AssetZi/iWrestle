//
//  EventCell.swift
//  iWrestle
//
//  Created by Brock Zacherl on 11/26/25.
//

import SwiftUI
import MapKit

struct EventCell: View {
    let event: Event
    
    let userLocation: CLLocation?
    
    let weighInType: String = weightInTypes.randomElement()!
    let style = tournamentFormat.randomElement()!
    var distance: Int {
        guard let userLocation = userLocation else { return 0 }
        let meters = userLocation.distance(from: event.location)
        return Int(meters.metersToMiles)
    }
    var body: some View {
        HStack{
            EventLogoView(url: event.logo)
            VStack(alignment: .leading){
                HStack{
                    Text(event.name).font(.headline)
                    Spacer()
                    distanceChip(distance: distance)
                }
                let formattedDate = event.date.formatted(date: .abbreviated, time: .omitted)
                Label(formattedDate, systemImage: "calendar.circle")
                    .font(.caption).foregroundStyle(.secondary)
                Label(event.address, systemImage: "mappin.circle")
                    .font(.caption).foregroundStyle(.secondary)
                Label(event.ageGroups.joined(separator: ", "), systemImage: "figure.wrestling.circle")
                    .font(.caption).foregroundStyle(.secondary)
//                Label("\(style)", systemImage: "trophy.circle")
//                    .font(.caption).foregroundStyle(.secondary)
                
            }
        }
        .padding()
    }
    
    func distanceChip(distance: Int) -> some View {
        HStack{
            Text("\(distance) mi")
                .font(.caption)
                .padding(5)
                .background(Color(.systemGray6))
                .cornerRadius(10)
        }
    }
}

//#Preview {
//    EventCell(event: )
//}


