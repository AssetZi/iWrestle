//
//  EventDetailView.swift
//  iWrestle
//
//  Created by Brock Zacherl on 12/12/25.
//

import SwiftUI
import MapKit

struct EventDetailView: View {
    let event: Event
    var formattedDate: String{
        event.date.formatted(date: .abbreviated, time: .omitted)
    }
    var body: some View {
        Form{
            HStack{
                EventLogoView(url: event.logo)
                VStack(alignment: .leading){
                    Text(event.name)
                        .font(.largeTitle)
                        .bold()
                    Text(formattedDate).font(.caption).foregroundStyle(.secondary)
                    Text(event.ageGroups.joined(separator: ", ")).font(.caption).foregroundStyle(.secondary)
                }
            }
            Section {
                NavigationLink {
                    PDFQuickLookView(url: event.flyer)
                } label: {
                    Text("Event Flyer")
                }

            }
            Section(header: Label("Contact Info", systemImage: "trophy")){
                Text("\(event.eventContactFirstName) \(event.eventContactLastName)")
                Label(event.eventContactEmail, systemImage: "envelope" )
                if !event.eventContactPhone.isEmpty{
                    Label(event.eventContactEmail, systemImage: "phone" )
                }
            }
            Section(header: Label("Location Info", systemImage: "map")){
                Text(event.address)
                Text("Open In Maps")
                    .onTapGesture {
                        let loc = MKMapItem(location: event.location, address: MKAddress(fullAddress: event.address, shortAddress: nil))
                        loc.openInMaps()
                    }
            }
        }
        .scrollIndicators(.hidden)
        
    }
}


