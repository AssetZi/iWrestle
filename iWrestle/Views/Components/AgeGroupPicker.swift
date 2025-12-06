//
//  AgeGroupPicker.swift
//  iWrestle
//
//  Created by Brock Zacherl on 12/5/25.
//

import SwiftUI

struct AgeGroupPicker: View {
    @Binding var selectedAgeGroups: Set<AgeGroup>
    
    
    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("Select Age Groups")
                .font(.headline)
            
            ForEach(AgeGroup.allCases) { ageGroup in
                Button(action: {
                    if selectedAgeGroups.contains(ageGroup) {
                        selectedAgeGroups.remove(ageGroup)
                    } else {
                        selectedAgeGroups.insert(ageGroup)
                    }
                }) {
                    HStack {
                        Image(systemName: selectedAgeGroups.contains(ageGroup) ? "checkmark.square.fill" : "square")
                            .foregroundColor(selectedAgeGroups.contains(ageGroup) ? .primary : .gray)
                        
                        Text(ageGroup.rawValue)
                            .foregroundColor(.primary)
                        
                        Spacer()
                    }
                    .contentShape(Rectangle())
                }
                .buttonStyle(.plain)
            }
        }
        .padding()
        
        
    }
}

#Preview {
    @Previewable @State var selectedAgeGroups: Set<AgeGroup> = []
    AgeGroupPicker(selectedAgeGroups: $selectedAgeGroups)
}

enum AgeGroup: String, CaseIterable, Identifiable {
    case novice = "Novice"
    case youth = "Youth"
    case jrHigh = "Jr High"
    case hs = "High School"
    case open = "Open"

    var id: String { self.rawValue }
}
