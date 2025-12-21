//
//  SettingsView.swift
//  iWrestle
//
//  Created by Brock Zacherl on 11/26/25.
//

import SwiftUI

struct SettingsView: View {
    @Environment(\.colorScheme) var cs
    @Environment(CloudKitManager.self) var ck
    @State private var showAddSheet: Bool = false
    @State private var userEvents: [Event] = []
    var body: some View {
        NavigationStack{
            Form {
                Section(header: Label("Settings", systemImage: "gearshape")) {
                    NavigationLink {
                        UserEventsView(userEvents: $userEvents)
                    } label: {
                        Text("🏆 Manage Events")
                    }
                    
                }
                SupportView()
                
                DealText()
                iWrestleButton(title: "Add Event") {
                    showAddSheet = true
                }
                
            }
            .sheet(isPresented: $showAddSheet) {
                AddEventScreen(userEvents: $userEvents)
            }
        }
    }
}

#Preview {
    SettingsView()
        .tint(.primary)
}
