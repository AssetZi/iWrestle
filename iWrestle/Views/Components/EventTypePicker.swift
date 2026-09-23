//
//  EventTypePicker.swift
//  iWrestle
//
//  Created by Brock Zacherl on 12/8/25.
//

import SwiftUI

enum EventType: String, CaseIterable, Identifiable {
    case tournament, camp, clinic, Duals
    var id: String { self.rawValue }
    var title: String { rawValue.capitalized }
}

/// Single-select type chips.
struct EventTypePicker: View {
    @Binding var eventType: EventType

    var body: some View {
        ChipFlow {
            ForEach(EventType.allCases) { type in
                SelectChip(label: type.title, selected: eventType == type) {
                    eventType = type
                }
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }
}

#Preview {
    @Previewable @State var et = EventType.tournament
    EventTypePicker(eventType: $et)
        .padding()
        .background(Theme.ink)
}
