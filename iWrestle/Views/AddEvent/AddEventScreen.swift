//
//  AddEventScreen.swift
//  iWrestle
//
//  Created by Brock Zacherl on 11/30/25.
//

import SwiftUI
import MapKit

struct AddEventScreen: View {
    @State private var eventName: String = ""
    @State private var eventContactFirstName: String = ""
    @State private var eventContactLastName: String = ""
    @State private var eventContactEmail: String = ""
    @State private var eventContactPhone: String = ""
    @State private var eventType: EventType = .tournament
    @State private var eventDate: Date = Date()
    @State private var wantsImagesMade: Bool = false
    @State private var selectedLocation: CLLocationCoordinate2D?
    @State private var selectedAgeGroups: Set<AgeGroup> = []
    var body: some View {
        Form {
            Section(header: Text("Event Information")) {
                TextField("Event Name", text: $eventName)
                    .autocorrectionDisabled(true)
                EventTypePicker(eventType: $eventType)
                DatePicker("Event Date", selection: $eventDate,displayedComponents: .date)
                MapView(selectedLocation: $selectedLocation)
                AgeGroupPicker(selectedAgeGroups: $selectedAgeGroups)
                
                
            }
            Section(header: Text("Event Contact Information")) {
                TextField("Event Contact First Name", text: $eventContactFirstName)
                    .autocorrectionDisabled(true)
                    .accessibilityLabel(Text("First Name"))
                TextField("Event Contact Last Name", text: $eventContactLastName)
                    .autocorrectionDisabled(true)
                TextField("Event Contact Email", text: $eventContactEmail)
                    .autocorrectionDisabled(true)
                    .keyboardType(.emailAddress)
                TextField("Event Contact Phone", text: $eventContactPhone)
                    .autocorrectionDisabled(true)
                    .keyboardType(.phonePad)
            }
            Section(header: Text("File Uploads")){
                Label("Upload Flyer", systemImage: "doc.text")
                Label("Custom event images by iWrestle (+$50)", systemImage: wantsImagesMade ? "checkmark.square" : "square")
                    .onTapGesture {
                        withAnimation {
                            wantsImagesMade.toggle()
                        }
                        
                    }
                    
                Group{
                    if !wantsImagesMade{
                        Label("Upload Event Logo", systemImage: "seal")
                        Label("Upload Event Banner", systemImage: "photo.artframe")
                    }
                }.animation(.easeInOut, value: wantsImagesMade)
            }
            iWrestleButton(title: "Create Event") {
                // 1. PAY:
                
                // 2 DATA FLOW:
                if wantsImagesMade{
                    // send work flow to me
                } else {
                    // create on cloud kit
                }

            }
        }
    }
}

#Preview {
    AddEventScreen()
}



