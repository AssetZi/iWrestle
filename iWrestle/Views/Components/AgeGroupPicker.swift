//
//  AgeGroupPicker.swift
//  iWrestle
//
//  Created by Brock Zacherl on 12/5/25.
//

import SwiftUI

enum AgeGroup: String, CaseIterable, Identifiable, Equatable {
    case novice = "Novice"
    case youth = "Youth"
    case jrHigh = "Jr High"
    case hs = "High School"
    case open = "Open"

    var id: String { self.rawValue }
}

/// Multi-select age-group chips for the add screens.
struct AgeGroupPicker: View {
    @Binding var selectedAgeGroups: Set<AgeGroup>
    var title: String = "Age groups (required)"
    var isInvalid = false

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(title)
                .font(.caption11)
                .foregroundStyle(isInvalid ? Theme.danger : Theme.textTertiary)
            ChipFlow {
                ForEach(AgeGroup.allCases) { ageGroup in
                    SelectChip(label: ageGroup.rawValue, selected: selectedAgeGroups.contains(ageGroup)) {
                        if selectedAgeGroups.contains(ageGroup) {
                            selectedAgeGroups.remove(ageGroup)
                        } else {
                            selectedAgeGroups.insert(ageGroup)
                        }
                    }
                }
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }
}

/// Same chips over the `[String]` the edit screen stores.
struct AgeGroupPickerString: View {
    @Binding var selectedAgeGroups: [String]
    let ageGroups: [String]
    var title: String = "Age groups"

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(title)
                .font(.caption11)
                .foregroundStyle(Theme.textTertiary)
            ChipFlow {
                ForEach(ageGroups, id: \.self) { ageGroup in
                    SelectChip(label: ageGroup, selected: selectedAgeGroups.contains(ageGroup)) {
                        if let idx = selectedAgeGroups.firstIndex(of: ageGroup) {
                            selectedAgeGroups.remove(at: idx)
                        } else {
                            selectedAgeGroups.append(ageGroup)
                        }
                    }
                }
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }
}

#Preview {
    @Previewable @State var selectedAgeGroups: Set<AgeGroup> = [.youth]
    AgeGroupPicker(selectedAgeGroups: $selectedAgeGroups)
        .padding()
        .background(Theme.ink)
}
