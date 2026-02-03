//
//  AddEventAdmin.swift
//  iWrestle
//
//  Created by Brock Zacherl on 2/2/26.
//

import SwiftUI
import MapKit

struct AddEventScreenAdmin: View {
    @Environment(CloudKitManager.self) var ck
    @Environment(\.dismiss) var dismiss
    @Binding var userEvents: [Event]

    @State private var eventData = EventData()
    @State private var wantsImagesMade: Bool = false
    @State private var eventLogo: UIImage?
    @State private var isLoading: Bool = false
    @State private var isShowingDatePicker: Bool = false
    
    @State private var purchaseError: String?
    @State private var showRetry = false
    
    @FocusState private var focusedField: FocusField?
    
    var body: some View {
        NavigationStack{
            ZStack{
                Form {
                    Section(header: Text("Event Information")) {
                        TextField("Event Name", text: $eventData.name)
                            .autocorrectionDisabled(true)
                            .focused($focusedField, equals: .title)
                        EventTypePicker(eventType: $eventData.eventType)
                            
                        Button {
                            withAnimation {
                                isShowingDatePicker.toggle()
                            }
                        } label: {
                            HStack {
                                Text("Event Date")
                                Spacer()
                                Text(eventData.date.formatted(date: .abbreviated, time: .omitted))
                                    .foregroundStyle(.secondary)
                            }
                        }
                        .buttonStyle(BorderlessButtonStyle())

                        if isShowingDatePicker {
                            DatePicker("Event Date", selection: $eventData.date,displayedComponents: .date)
                                .datePickerStyle(.graphical)
                                .onChange(of: eventData.date) {
                                    withAnimation {
                                        isShowingDatePicker = false
                                    }
                                }
                                .onTapGesture(count: 99) {}
                        }
                        
                        MapView(selectedLocation: $eventData.location, address: $eventData.address)
                            .buttonStyle(BorderlessButtonStyle())
                        AgeGroupPicker(selectedAgeGroups: $eventData.ageGroups)
                        TextField("Registration Link (Optional)", text: $eventData.registration)
                            .autocorrectionDisabled(true)
                            .focused($focusedField, equals: .registration)
                        
                    }
                    Section(header: Text("Event Contact Information")) {
                        TextField("Event Contact First Name", text: $eventData.eventContactFirstName)
                            .autocorrectionDisabled(true)
                            .accessibilityLabel(Text("First Name"))
                            .focused($focusedField, equals: .firstName)
                        TextField("Event Contact Last Name", text: $eventData.eventContactLastName)
                            .autocorrectionDisabled(true)
                            .focused($focusedField, equals: .lastName)
                        TextField("Event Contact Email", text: $eventData.eventContactEmail)
                            .autocorrectionDisabled(true)
                            .keyboardType(.emailAddress)
                            .focused($focusedField, equals: .email)
                        TextField("Event Contact Phone (Optional)", text: $eventData.eventContactPhone)
                            .autocorrectionDisabled(true)
                            .keyboardType(.phonePad)
                            .focused($focusedField, equals: .phone)
                    }
                    Section(header: Text("File Uploads")){
                        iWrestlePDFPicker(title: "Event Flyer", importedURL: $eventData.flyer)
                            .buttonStyle(BorderlessButtonStyle())
//                        CreateMyLogosToggle() // not gonna have this option in first iteration.
                        Group{
                            if !wantsImagesMade{
                                iWrestlePhotoPicker(image: $eventLogo)
                                    .buttonStyle(BorderlessButtonStyle())
                                    
                            }
                        }.animation(.easeInOut, value: wantsImagesMade)
                    }
                    .onChange(of: eventLogo){focusedField = nil}
                    .onChange(of: wantsImagesMade){focusedField = nil}
                    .onChange(of: eventData.flyer){focusedField = nil}
                    
                    if let purchaseError {
                        HStack {
                            Spacer()
                            Text(purchaseError).foregroundStyle(.red)
                            Spacer()
                        }
                        .listRowBackground(Color.clear)
                        .listRowInsets(EdgeInsets())
                        .listRowSeparator(.hidden)
                        
                    } else {
                        DealText()
                    }
                    
                    iWrestleButton(title: showRetry ? "Retry" : "Create Event") {
                        Task {
                            let isValid = checkIfFormIsValid()
                            if isValid{
                                if showRetry{
                                    await createEvent()
                                } else {
                                    await buyThenCreateEvent()
                                }
                            }
                            
                            
                        }
                    }
                    .buttonStyle(BorderlessButtonStyle())
                    
                        
                    
                    
                }
                .disabled(isLoading)
                .opacity(isLoading ? 0.3 : 1)
                if isLoading{
                    iWrestleProgressView()
                }
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
    
    func checkIfFormIsValid() -> Bool {
        // event information
        guard !eventData.name.isEmpty else {purchaseError = "Please fill out Event Name" ;return false}
        guard eventData.location != nil else {purchaseError = "Please select a location" ;return false}
        guard !eventData.ageGroups.isEmpty else {purchaseError = "Please select age groups" ;return false}
        guard eventData.flyer != nil else {purchaseError = "Please upload an event flyer" ;return false}
        
        // event contact information
        guard !eventData.eventContactFirstName.isEmpty, !eventData.eventContactLastName.isEmpty, !eventData.eventContactEmail.isEmpty else {purchaseError = "Please fill out Event Contact Information" ;return false}
        
        // photo decision
//        guard wantsImagesMade || eventLogo != nil else {purchaseError = "Please either upload an event logo or opt to have one generated for you" ;return false} // not in MVP
        guard wantsImagesMade || eventLogo != nil else {purchaseError = "Please upload an event logo." ;return false}
        return true
    }
    
    private func createEvent() async {
        isLoading = true
        guard let photo = eventLogo else {isLoading = false ;return}
        guard let photoUrl = ck.getPhotoURL(image: photo) else {isLoading = false ;return}
        eventData.logo = photoUrl
        if let event = await ck.createEvent(data: eventData){
            userEvents.append(event)
        }
        dismiss()
    }
    
    private func buyThenCreateEvent() async {
        purchaseError = nil
        isLoading = true
        await createEvent()
    }
    
    enum FocusField {
        case title,registration,firstName,lastName,email, phone
    }
    
}
