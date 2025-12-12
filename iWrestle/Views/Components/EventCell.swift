//
//  EventCell.swift
//  iWrestle
//
//  Created by Brock Zacherl on 11/26/25.
//

import SwiftUI

struct EventCell: View {
    let event: Event
    
    
    
    let weighInType: String = weightInTypes.randomElement()!
    let style = tournamentFormat.randomElement()!
    let distance: Int = Int.random(in: 10...300)
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


