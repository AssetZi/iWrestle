//
//  EventFilters.swift
//  iWrestle
//
//  The applied / draft filter state behind the filter sheet, and the
//  NSPredicate builders it maps to. The sheet edits a draft copy; Apply
//  commits it back to HomeView.
//

import Foundation
import CoreLocation

struct EventFilters: Equatable {
    var eventType: EventTypeFilter = .all
    var ageGroup: AgeGroupFilter = .all
    var distance: DistanceOption = .any
    var date: DateOptionsIWrestle = .thisMonth

    static let `default` = EventFilters()

    var isDefault: Bool { self == .default }

    /// Nil when a distance filter is requested without a user location.
    func predicates(userLocation: CLLocation?) -> [NSPredicate]? {
        var predicates: [NSPredicate] = []

        if distance != .any {
            guard let userLocation else { return nil }
            predicates.append(NSPredicate(
                format: "distanceToLocation:fromLocation:(location, %@) < %f",
                userLocation,
                distance.rawValue.milesToMeters
            ))
        }
        if case .specific(let type) = eventType {
            predicates.append(NSPredicate(format: "eventType == %@", type.rawValue))
        }
        if case .specific(let age) = ageGroup {
            predicates.append(NSPredicate(format: "ANY ageGroups == %@", age.rawValue))
        }
        if let interval = date.dateInterval() {
            predicates.append(NSPredicate(format: "date >= %@ AND date < %@",
                                          interval.start as CVarArg,
                                          interval.end as CVarArg))
        }
        return predicates
    }
}

enum DistanceOption: Double, CaseIterable, Identifiable {
    case any = 100000
    case under50 = 50, under100 = 100, under200 = 200, under300 = 300

    var id: Double { rawValue }

    var title: String {
        switch self {
        case .any: return "Any"
        case .under50: return "Under 50 mi"
        case .under100: return "Under 100 mi"
        case .under200: return "Under 200 mi"
        case .under300: return "Under 300 mi"
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
        case .specific(let age): return age.rawValue
        }
    }
}

enum EventTypeFilter: Identifiable, CaseIterable, Hashable {
    case all
    case specific(EventType)

    var id: String {
        switch self {
        case .all: return "all"
        case .specific(let type): return type.rawValue
        }
    }

    static var allCases: [EventTypeFilter] {
        [.all] + EventType.allCases.map { .specific($0) }
    }

    var title: String {
        switch self {
        case .all: return "All"
        case .specific(let type): return type.title
        }
    }
}

enum DateOptionsIWrestle: String, CaseIterable, Identifiable {
    case thisWeek = "This week"
    case thisMonth = "This month"
    case nextThreeMonths = "Next 3 months"

    var id: String { rawValue }

    func dateInterval() -> DateInterval? {
        let calendar = Calendar.current
        let now = Date()

        switch self {
        case .thisWeek:
            guard
                let thisWeek = calendar.dateInterval(of: .weekOfYear, for: now),
                let endInclusive = calendar.date(byAdding: .day, value: 1, to: thisWeek.end)
            else { return nil }
            return DateInterval(start: thisWeek.start, end: endInclusive)

        case .thisMonth:
            guard let end = calendar.date(byAdding: .month, value: 1, to: now) else { return nil }
            return DateInterval(start: now, end: end)

        case .nextThreeMonths:
            guard let end = calendar.date(byAdding: .month, value: 3, to: now) else { return nil }
            return DateInterval(start: now, end: end)
        }
    }
}
