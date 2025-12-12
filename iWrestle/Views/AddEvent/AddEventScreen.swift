//
//  AddEventScreen.swift
//  iWrestle
//
//  Created by Brock Zacherl on 11/30/25.
//

import SwiftUI
import MapKit

struct AddEventScreen: View {
    @Environment(CloudKitManager.self) var ck
    @Environment(\.dismiss) var dismiss
    @Binding var userEvents: [Event]
    @State private var eventData = EventData()
    
    @State private var wantsImagesMade: Bool = false
    @State private var eventLogo: UIImage?
    
    var formIsValid: Bool {
        eventInfoValid && eventContactValid && logoValidation
    }
    var eventInfoValid: Bool {
        !eventData.name.isEmpty && eventData.location != nil && !eventData.ageGroups.isEmpty && eventData.flyer != nil
    }
    var eventContactValid: Bool {
        !eventData.eventContactFirstName.isEmpty && !eventData.eventContactLastName.isEmpty && !eventData.eventContactEmail.isEmpty
    }
    var logoValidation: Bool {
        return true
//        wantsImagesMade && eventLogo == nil
    }
    var body: some View {
        NavigationStack{
            Form {
                Section(header: Text("Event Information")) {
                    TextField("Event Name", text: $eventData.name)
                        .autocorrectionDisabled(true)
                    EventTypePicker(eventType: $eventData.eventType)
                    DatePicker("Event Date", selection: $eventData.date,displayedComponents: .date)
                        
                    MapView(selectedLocation: $eventData.location, address: $eventData.address)
                        .buttonStyle(BorderlessButtonStyle())
                    AgeGroupPicker(selectedAgeGroups: $eventData.ageGroups)
                    
                    
                }
                Section(header: Text("Event Contact Information")) {
                    TextField("Event Contact First Name", text: $eventData.eventContactFirstName)
                        .autocorrectionDisabled(true)
                        .accessibilityLabel(Text("First Name"))
                    TextField("Event Contact Last Name", text: $eventData.eventContactLastName)
                        .autocorrectionDisabled(true)
                    TextField("Event Contact Email", text: $eventData.eventContactEmail)
                        .autocorrectionDisabled(true)
                        .keyboardType(.emailAddress)
                    TextField("Event Contact Phone", text: $eventData.eventContactPhone)
                        .autocorrectionDisabled(true)
                        .keyboardType(.phonePad)
                }
                Section(header: Text("File Uploads")){
                    iWrestlePDFPicker(title: "Event Flyer", importedURL: $eventData.flyer)
                        .buttonStyle(BorderlessButtonStyle())
                    
                    CreateMyLogosToggle()
                        
                    Group{
                        if !wantsImagesMade{
                            iWrestlePhotoPicker(image: $eventLogo)
                                .buttonStyle(BorderlessButtonStyle())
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
                        createEvent()
                    }

                }
                .disabled(!formIsValid)
                .buttonStyle(BorderlessButtonStyle())
            }
            .navigationTitle(Text("Add Event"))
            .hideKeyboardOnTap()
        }
    }
    
    @ViewBuilder
    func CreateMyLogosToggle() -> some View {
        Label("Custom logo by iWrestle (+$50)", systemImage: wantsImagesMade ? "checkmark.square" : "square")
            .onTapGesture {
                withAnimation {
                    wantsImagesMade.toggle()
                }
                
            }
    }
    
    private func createEvent() {
        Task {
            guard let photo = eventLogo else {return}
            guard let photoUrl = ck.getPhotoURL(image: photo) else {return}
            eventData.logo = photoUrl
            if let event = await ck.createEvent(data: eventData){
                userEvents.append(event)
            }
            dismiss()
        }
    }
}

//#Preview {
//    AddEventScreen()
//}



