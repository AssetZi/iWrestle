//
//  EventsFilterView.swift
//  iWrestle
//
//  Created by Brock Zacherl on 12/17/25.
//

import SwiftUI

struct EventsFilterView: View {
    @Environment(CloudKitManager.self) var ck
    @Environment(LocationManager.self) var lm
    @Environment(\.dismiss) var dismiss
    @Binding var viewState: HomeViewState
    @State private var eventType: EventTypeFilter = .all
    @State private var ageGroup: AgeGroupFilter = .all
    @State private var distance: DistanceOption = .any
    @State private var dateSelection: DateOptionsIWrestle = .thisWeek
    @State private var isLoading: Bool = false
    @State private var customDate: Date = Date()
    var body: some View {
        ZStack{
            Form {
                
                Section(header: Text("Events")) {
                    Picker("Event Type", selection: $eventType) {
                        ForEach(EventTypeFilter.allCases) { option in
                            Text(option.title).tag(option)
                        }
                    }
                    Picker("Age Group", selection: $ageGroup) {
                        ForEach(AgeGroupFilter.allCases) { option in
                            Text(option.title).tag(option)
                        }
                    }
                    Picker("Distance", selection: $distance) {
                        ForEach(DistanceOption.allCases, id: \.self) { option in
                            Text(option.title).tag(option)
                        }
                    }
                }
                FilterDatePickeriWrestle(selection: $dateSelection, customDate: $customDate)
                
                iWrestleButton(title: "Apply") {
                    loadEvents()
                }
                HStack{
                    Spacer()
                    Button("Clear"){clearFilters()}
                }.foregroundStyle(.secondary).listRowBackground(Color.clear).listRowSeparator(.hidden)
                
                
            }
            .disabled(isLoading)
            .opacity(isLoading ? 0.3 : 1)
            if isLoading {
                iWrestleProgressView()
            }
        }

    }
    
    
    enum DistanceOption: Double, CaseIterable {
        case under50=50, under100=100, under200=200, under300=300, any = 100000
        
        var title: String {
            switch self {
            case .under50: return "Under 50m"
            case .under100: return "Under 100m"
            case .under200: return "Under 200m"
            case .under300: return "Under 300m"
            case .any: return "Any"
            }
        }
    }
    enum AgeGroupFilter: Identifiable, CaseIterable, Hashable {
        case all
        case specific(AgeGroup)

        var id: String {
            switch self {
            case .all: return "all"
            case .specific(let age): return age.rawValue
            }
        }

        static var allCases: [AgeGroupFilter] {
            [.all] + AgeGroup.allCases.map { .specific($0) }
        }

        var title: String {
            switch self {
            case .all: return "All"
            case .specific(let age): return age.rawValue.capitalized
            }
        }
    }
    enum EventTypeFilter: Identifiable, CaseIterable, Hashable {
        case all
        case specific(EventType)

        var id: String {
            switch self {
            case .all: return "all"
            case .specific(let age): return age.rawValue
            }
        }

        static var allCases: [EventTypeFilter] {
            [.all] + EventType.allCases.map { .specific($0) }
        }

        var title: String {
            switch self {
            case .all: return "All"
            case .specific(let age): return age.rawValue.capitalized
            }
        }
    }
    
    func loadEvents() {
        Task {
            isLoading = true
            let predicates = establishPredicates()
            let events = try await ck.fetchEvents(predicates: predicates)
            if !events.isEmpty {
                viewState = .loaded(events)
            } else {viewState = .error(.noData)}
            dismiss()
        }
    }
    func establishPredicates() -> [NSPredicate] {
        var predicates: [NSPredicate] = []
        
        if distance != .any {
            guard let userLocation = lm.userLocation else {viewState = .error(.locationError); return []}
            
            let radiusInMeters = distance.rawValue.milesToMeters
            let distancePredicate = NSPredicate(
                format: "distanceToLocation:fromLocation:(location, %@) < %f",
                userLocation,
                radiusInMeters
            )
            predicates.append(distancePredicate)
        }
        if eventType != .all {
            let typePredicate = NSPredicate(format: "eventType == %@", eventType.title.lowercased())
            predicates.append(typePredicate)
        }
        if ageGroup != .all {
            let agePredicate = NSPredicate(format: "ANY ageGroups == %@", ageGroup.title)
            predicates.append(agePredicate)
        }
        if let interval = dateSelection.dateInterval(customDate: customDate) {
            let datePredicate = NSPredicate(format: "date >= %@ AND date <= %@", interval.start as CVarArg, interval.end as CVarArg)
            predicates.append(datePredicate)
        }
        return predicates
    }
    func clearFilters() {
        self.distance = .any
        self.eventType = .all
        self.ageGroup = .all
        self.customDate = Date()
        self.dateSelection = .thisMonth
    }
}

//#Preview {
//    @Previewable @State var vs : HomeViewState = .loading
//    EventsFilterView(viewState: $vs)
//}
