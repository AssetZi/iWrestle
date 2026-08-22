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
    
    /// CloudKit failures only. Validation has its own row.
    @State private var purchaseError: String?
    /// Set on the first submit attempt; until then the form stays quiet.
    @State private var attemptedSubmit = false

    @FocusState private var focusedField: FocusField?

    var body: some View {
        // Evaluated once per render and reused by the message and the submit
        // handler, so they can never disagree.
        let missing = missingFields(data: eventData, logo: eventLogo, wantsImagesMade: wantsImagesMade)

        NavigationStack{
            ZStack{
                Form {
                    Section(header: Text("Event Information")) {
                        TextField("Event Name (Required)", text: $eventData.name)
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
                        
                        MapView(selectedLocation: $eventData.location, address: $eventData.address, isRequired: true)
                            .buttonStyle(BorderlessButtonStyle())
                        AgeGroupPicker(selectedAgeGroups: $eventData.ageGroups, title: "Select Age Groups (Required)")
                        TextField("Registration Link (Optional)", text: $eventData.registration)
                            .autocorrectionDisabled(true)
                            .focused($focusedField, equals: .registration)
                        
                    }
                    Section(header: Text("Event Contact Information")) {
                        TextField("Event Contact First Name (Required)", text: $eventData.eventContactFirstName)
                            .autocorrectionDisabled(true)
                            .accessibilityLabel(Text("First Name"))
                            .focused($focusedField, equals: .firstName)
                        TextField("Event Contact Last Name (Required)", text: $eventData.eventContactLastName)
                            .autocorrectionDisabled(true)
                            .focused($focusedField, equals: .lastName)
                        TextField("Event Contact Email (Required)", text: $eventData.eventContactEmail)
                            .autocorrectionDisabled(true)
                            .keyboardType(.emailAddress)
                            .focused($focusedField, equals: .email)
                        TextField("Event Contact Phone (Optional)", text: $eventData.eventContactPhone)
                            .autocorrectionDisabled(true)
                            .keyboardType(.phonePad)
                            .focused($focusedField, equals: .phone)
                    }
                    Section(header: Text("File Uploads")){
                        iWrestlePDFPicker(title: "Event Flyer (Required)", importedURL: $eventData.flyer)
                            .buttonStyle(BorderlessButtonStyle())
//                        CreateMyLogosToggle() // not gonna have this option in first iteration.
                        Group{
                            if !wantsImagesMade{
                                iWrestlePhotoPicker(image: $eventLogo, title: "Upload Event Logo (Required)")
                                    .buttonStyle(BorderlessButtonStyle())
                                    
                            }
                        }.animation(.easeInOut, value: wantsImagesMade)
                    }
                    .onChange(of: eventLogo){focusedField = nil}
                    .onChange(of: wantsImagesMade){focusedField = nil}
                    .onChange(of: eventData.flyer){focusedField = nil}
                    
                    if attemptedSubmit, let message = validationMessage(for: missing) {
                        HStack {
                            Spacer()
                            Text(message)
                                .foregroundStyle(.red)
                                .multilineTextAlignment(.center)
                            Spacer()
                        }
                        .listRowBackground(Color.clear)
                        .listRowInsets(EdgeInsets())
                        .listRowSeparator(.hidden)
                    }

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
                    
                    iWrestleButton(title: "Create Event") {
                        Task {
                            attemptedSubmit = true
                            guard missing.isEmpty else { return }
                            await buyThenCreateEvent()
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
