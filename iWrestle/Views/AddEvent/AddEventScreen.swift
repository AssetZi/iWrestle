//
//  AddEventScreen.swift
//  iWrestle
//
//  Created by Brock Zacherl on 11/30/25.
//

import SwiftUI

struct AddEventScreen: View {
    @State private var eventName: String = ""
    @State private var eventContactFirstName: String = ""
    @State private var eventContactLastName: String = ""
    @State private var eventContactEmail: String = ""
    @State private var eventContactPhone: String = ""
    @State private var eventDate: Date = Date()
    
    var body: some View {
        Form {
            Section(header: Text("Event Information")) {
                TextField("Event Name", text: $eventName)
                    .autocorrectionDisabled(true)
                DatePicker("Event Date", selection: $eventDate,displayedComponents: .date)
                
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
        }
    }
    
    
}

#Preview {
    AddEventScreen()
}
