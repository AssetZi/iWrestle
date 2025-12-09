//
//  EventTypePicker.swift
//  iWrestle
//
//  Created by Brock Zacherl on 12/8/25.
//

import SwiftUI

struct EventTypePicker: View {
    @Binding var eventType: EventType
    var body: some View {
        Picker("Event Type", selection: $eventType) {
            ForEach(EventType.allCases, id: \.self) { eventType in
                Text(eventType.rawValue.capitalized)
            }
        }

    }
}

#Preview {
    @Previewable @State var et = EventType.tournament
    Form{
        EventTypePicker(eventType: $et)
    }
}


enum EventType: String, CaseIterable,Identifiable {
    case tournament,camp,clinic
    var id: String { self.rawValue }
}
