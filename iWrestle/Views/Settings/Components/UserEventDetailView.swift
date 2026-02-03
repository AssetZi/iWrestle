//
//  UserEventDetailView.swift
//  iWrestle
//
//  Created by Brock Zacherl on 12/13/25.
//

import SwiftUI
import MapKit

struct UserEventDetailView: View {
    @Environment(CloudKitManager.self) var ck
    @Environment(\.dismiss) var dismiss
    @Binding var ogEvent: Event
    @State var event: Event
    @State private var newLogo: UIImage?
    @State private var newFlyer: URL?
    @State private var isLoading = false
    @State private var location: CLLocationCoordinate2D?
    @State private var isEditing: Bool = false
    let ageGroups = ["Novice","Youth","Jr High","High School","Open"]
    
    var cantChangeDate: Bool {
        // True if we're within 7 days of the event (i.e., after eventDate - 7 days)
        guard let sevenDaysBefore = Calendar.current.date(byAdding: .day, value: -7, to: event.date) else {
            return false
        }
        return Date() >= sevenDaysBefore
    }
    var body: some View {
        NavigationStack{
            ZStack{
                Form {
                    Section {
                        NavigationLink {
                            EventDetailView(event: event)
                        } label: {
                            Text("Preview Event")
                                .buttonStyle(BorderlessButtonStyle())
                        }
                        .buttonStyle(BorderlessButtonStyle())
                        .onTapGesture(count: 99){}
                        

                    }
                    Section(header: Text("Event Information")) {
                        TextField("Event Name", text: $event.name)
                            .autocorrectionDisabled(true)
                            
                        if !cantChangeDate {
                            DatePickeriWrestle(eventDate: $event.date)
                        }
                        
                        
                        MapView(selectedLocation: $location, address: $event.address)
                            .buttonStyle(BorderlessButtonStyle())
                        AgeGroupPickerString(selectedAgeGroups: $event.ageGroups, ageGroups: ageGroups)
                        TextField("Registration Link (Optional)", text: Binding(
                            get: { event.registration ?? "" },
                            set: { event.registration = $0.isEmpty ? nil : $0 }
                        ))
                        .autocorrectionDisabled(true)
                        
                    }.disabled(!isEditing)
                    Section(header: Text("Event Contact Information")) {
                        TextField("Event Contact First Name", text: $event.eventContactFirstName)
                            .autocorrectionDisabled(true)
                            .accessibilityLabel(Text("First Name"))
                        TextField("Event Contact Last Name", text: $event.eventContactLastName)
                            .autocorrectionDisabled(true)
                        TextField("Event Contact Email", text: $event.eventContactEmail)
                            .autocorrectionDisabled(true)
                            .keyboardType(.emailAddress)
                        TextField("Event Contact Phone (Optional)", text: $event.eventContactPhone)
                            .autocorrectionDisabled(true)
                            .keyboardType(.phonePad)
                    }.disabled(!isEditing)
                    Section(header: Text("File Uploads")){
                        HStack{
                            iWrestlePDFPicker(title: "Event Flyer", importedURL: $newFlyer)
                                .buttonStyle(BorderlessButtonStyle())
                            if let flyer = newFlyer{
                                PDFThumbnailView(url: flyer, size: CGSize(width: 75, height: 100))
                            } else {
                                PDFThumbnailView(url: event.flyer, size: CGSize(width: 75, height: 100))
                            }
                        }
                        HStack{
                            iWrestlePhotoPicker(image: $newLogo)
                                .buttonStyle(BorderlessButtonStyle())
                            if newLogo == nil {
                                EventLogoView(url: event.logo)
                                    .frame(height: 50)
                                    .clipShape(RoundedRectangle(cornerRadius: 12))
                            }
                        }
                    }.disabled(!isEditing)
                }
                .scrollIndicators(.hidden)
                .disabled(isLoading)
                .opacity(isLoading ? 0.3 : 1)
                if isLoading{
                    iWrestleProgressView()
                }
                    
            }
            .hideKeyboardOnTap()
            .task {
                location = CLLocationCoordinate2D(latitude: event.location.coordinate.latitude, longitude: event.location.coordinate.longitude)
            }
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    HStack(spacing: 20){
                        Button(isEditing ?  "Save":"Edit"){
                            if isEditing {
                                saveEvent()
                                
                            } else {
                                isEditing = true
                            }
                        }
                        if isEditing{
                            Button("Cancel"){
                                event = ogEvent
                                isEditing = false
                            }
                        }
                    }
                }
            }
        }
    }
    
    
    func saveEvent(){
        Task {
            var logo: URL? = nil
            isLoading = true
            if event.address != ogEvent.address{
                guard let location = location else {return}
                event.location = CLLocation(latitude: location.latitude, longitude: location.longitude)
            }
            if let newLogo = newLogo{
                if let photoUrl = ck.getPhotoURL(image: newLogo) {
                    logo = photoUrl
                    event.logo = photoUrl
                }
                
            }
            if let newFlyer = newFlyer{
                event.flyer = newFlyer
            }
            try await ck.updateEvent(event, newFlyer: newFlyer, newLogo: logo)
            ogEvent = event
            dismiss()
        }
    }
}

//#Preview {
//    UserEventDetailView()
//}
