//
//  SettingsView.swift
//  iWrestle
//
//  Created by Brock Zacherl on 11/26/25.
//

import SwiftUI

struct SettingsView: View {
    @Environment(\.colorScheme) var cs
    @State private var showAddSheet: Bool = false
    var body: some View {
        Form {
            SupportView()
            iWrestleButton(title: "Add Event") {
                showAddSheet = true
            }
            
        }
        .sheet(isPresented: $showAddSheet) {
            AddEventScreen()
        }
    }
 
}

#Preview {
    SettingsView()
        .tint(.primary)
}
