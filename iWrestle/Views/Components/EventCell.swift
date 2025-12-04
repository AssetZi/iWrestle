//
//  EventCell.swift
//  iWrestle
//
//  Created by Brock Zacherl on 11/26/25.
//

import SwiftUI

struct EventCell: View {
    let image: String = mockSquares.randomElement()!
    let name: String = mockEventNames.randomElement()!
    let address: String = mockAddresses.randomElement()!
    let weighInType: String = weightInTypes.randomElement()!
    let style = tournamentFormat.randomElement()!
    let distance: Int = Int.random(in: 10...300)
    var body: some View {
        HStack{
            Image(image)
                .resizable()
                .scaledToFit()
                .cornerRadius(10)
                .frame(width: 100,height: 100)
            VStack(alignment: .leading){
                HStack{
                    Text(name).font(.headline)
                    Spacer()
                    distanceChip(distance: distance)
                }
                Label(address, systemImage: "mappin.circle")
                    .font(.caption).foregroundStyle(.secondary)
                Label("Open, Novice, & Girls Tournament", systemImage: "figure.wrestling.circle")
                    .font(.caption).foregroundStyle(.secondary)
                Label("\(weighInType) | \(style)", systemImage: "trophy.circle")
                    .font(.caption).foregroundStyle(.secondary)
                
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

#Preview {
    EventCell()
}


