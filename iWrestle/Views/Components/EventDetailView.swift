//
//  EventDetailView.swift
//  iWrestle
//
//  Created by Brock Zacherl on 12/12/25.
//

import SwiftUI
import MapKit

struct EventDetailView: View {
    @Environment(\.openURL) private var openURL
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
                if let registration = event.registration{
                    Text("Registration Link")
                        .onTapGesture {
                            if let url = URL(string: registration){
                                openURL(url)
                            }
                        }
                        .foregroundStyle(.link)
                }

            }
            Section(header: Label("Contact Info", systemImage: "trophy")){
                Text("\(event.eventContactFirstName) \(event.eventContactLastName)")
                EmailLabel(email: event.eventContactEmail).foregroundStyle(.link)
                if !event.eventContactPhone.isEmpty{
                    PhoneLabel(number: event.eventContactPhone).foregroundStyle(.link)
                }
            }
            Section(header: Label("Location Info", systemImage: "map")){
                Text(event.address)
                Text("Open In Maps")
                    .onTapGesture {
                        let loc = MKMapItem(location: event.location, address: MKAddress(fullAddress: event.address, shortAddress: nil))
                        loc.openInMaps()
                    }
                    .foregroundStyle(.link)
            }
        }
        .scrollIndicators(.hidden)
        
    }
}


