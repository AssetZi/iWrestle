//
//  AgeGroupPicker.swift
//  iWrestle
//
//  Created by Brock Zacherl on 12/5/25.
//

import SwiftUI

struct AgeGroupPicker: View {
    @Binding var selectedAgeGroups: Set<AgeGroup>
    /// Defaulted so any other caller is unaffected; the add screens mark it
    /// required. (The edit screen uses AgeGroupPickerString, not this type.)
    var title: String = "Select Age Groups"


    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text(title)
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

enum AgeGroup: String, CaseIterable, Identifiable,Equatable {
    case novice = "Novice"
    case youth = "Youth"
    case jrHigh = "Jr High"
    case hs = "High School"
    case open = "Open"

    var id: String { self.rawValue }
}


struct AgeGroupPickerString: View {
    @Binding var selectedAgeGroups: [String]
    let ageGroups: [String]
    
    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("Select Age Groups")
                .font(.headline)
            
            ForEach(ageGroups, id: \.self) { ageGroup in
                Button(action: {
                    if let idx = selectedAgeGroups.firstIndex(of: ageGroup) {
                        selectedAgeGroups.remove(at: idx)
                    } else {
                        selectedAgeGroups.append(ageGroup)
                    }
                }) {
                    HStack {
                        Image(systemName: selectedAgeGroups.contains(ageGroup) ? "checkmark.square.fill" : "square")
                            .foregroundColor(selectedAgeGroups.contains(ageGroup) ? .primary : .gray)
                        
                        Text(ageGroup)
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


