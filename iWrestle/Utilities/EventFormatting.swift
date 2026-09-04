//
//  EventFormatting.swift
//  iWrestle
//
//  Display helpers shared by the list, map, detail and dashboard screens:
//  date labels, venue / city split, monograms, distances and list order.
//

import Foundation
import CoreLocation

// MARK: - Dates

extension Date {
    /// "Sat, Sep 12"
    var shortDayLabel: String {
        formatted(.dateTime.weekday(.abbreviated).month(.abbreviated).day())
    }

    /// "SAT · SEP 12" — the date-group label above event cards.
    var groupLabel: String {
        let weekday = formatted(.dateTime.weekday(.abbreviated)).uppercased()
        let monthDay = formatted(.dateTime.month(.abbreviated).day()).uppercased()
        return "\(weekday) · \(monthDay)"
    }

    /// "September 2026"
    var monthYearLabel: String {
        formatted(.dateTime.month(.wide).year())
    }

    /// "Saturday, September 12, 2026"
    var longDateLabel: String {
        formatted(.dateTime.weekday(.wide).month(.wide).day().year())
    }
}

// MARK: - Address

/// Splits a full postal address ("Knights Fieldhouse, 12 Main St, Butler, PA
/// 16001, United States") into the venue / street line and a "City, ST" line.
struct AddressParts {
    let venue: String
    let city: String

    init(_ address: String) {
        let parts = address
            .split(separator: ",")
            .map { $0.trimmingCharacters(in: .whitespaces) }
            .filter { !$0.isEmpty }

        guard let first = parts.first else {
            venue = address
            city = ""
            return
        }
        venue = first

        // Drop a trailing country and any leading street lines; keep the last
        // "City" + "ST ZIP" pair when it exists.
        var body = Array(parts.dropFirst())
        if let last = body.last, Self.looksLikeCountry(last) { body.removeLast() }

        if body.count >= 2 {
            let cityName = body[body.count - 2]
            let region = body[body.count - 1]
                .split(separator: " ")
                .first
                .map(String.init) ?? body[body.count - 1]
            city = "\(cityName), \(region)"
        } else if let only = body.first {
            city = only
        } else {
            city = ""
        }
    }

    private static func looksLikeCountry(_ s: String) -> Bool {
        let lowered = s.lowercased()
        return lowered == "united states" || lowered == "usa" || lowered == "us" || lowered == "canada"
    }
}

// MARK: - Monogram

extension String {
    /// "Interstate Classic" → "IC", "Christmas Bash 5" → "CB", "Open" → "OP".
    var monogram: String {
        let words = split(whereSeparator: { $0 == " " || $0 == "-" })
            .map(String.init)
            .filter { $0.first?.isLetter == true }
        if words.count >= 2 {
            return (String(words[0].prefix(1)) + String(words[1].prefix(1))).uppercased()
        }
        if let word = words.first {
            return String(word.prefix(2)).uppercased()
        }
        return String(prefix(2)).uppercased()
    }
}

// MARK: - Distance

extension Event {
    /// Whole miles from the user, or nil without a location.
    func miles(from userLocation: CLLocation?) -> Int? {
        guard let userLocation else { return nil }
        return Int(userLocation.distance(from: location).metersToMiles.rounded())
    }

    var contactName: String {
        "\(eventContactFirstName) \(eventContactLastName)".trimmingCharacters(in: .whitespaces)
    }

    var contactInitials: String { contactName.monogram }

    var typeTitle: String { EventType(rawValue: eventType)?.title ?? eventType.capitalized }
}

// MARK: - Ordering

extension Array where Element == Event {
    /// Day first (earliest), then distance (closest), then name.
    func sortedForList(userLocation: CLLocation?) -> [Event] {
        let cal = Calendar.current
        return sorted { lhs, rhs in
            let lhsDay = cal.startOfDay(for: lhs.date)
            let rhsDay = cal.startOfDay(for: rhs.date)
            if lhsDay != rhsDay { return lhsDay < rhsDay }
            if let userLocation {
                let lhsDistance = lhs.location.distance(from: userLocation)
                let rhsDistance = rhs.location.distance(from: userLocation)
                if lhsDistance != rhsDistance { return lhsDistance < rhsDistance }
            }
            return lhs.name < rhs.name
        }
    }

    /// Consecutive runs of the same calendar day, preserving order.
    func groupedByDay() -> [(day: Date, events: [Event])] {
        let cal = Calendar.current
        var groups: [(day: Date, events: [Event])] = []
        for event in self {
            let day = cal.startOfDay(for: event.date)
            if let last = groups.indices.last, groups[last].day == day {
                groups[last].events.append(event)
            } else {
                groups.append((day, [event]))
            }
        }
        return groups
    }
}
