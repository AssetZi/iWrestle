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
    ///
    /// Each event's day and distance are worked out once up front instead
    /// of twice per comparison.
    func sortedForList(userLocation: CLLocation?) -> [Event] {
        let cal = Calendar.current
        let keyed: [(event: Event, day: Date, distance: CLLocationDistance)] = map { event in
            (event, cal.startOfDay(for: event.date), userLocation.map { event.location.distance(from: $0) } ?? 0)
        }
        return keyed.sorted { lhs, rhs in
            if lhs.day != rhs.day { return lhs.day < rhs.day }
            if lhs.distance != rhs.distance { return lhs.distance < rhs.distance }
            return lhs.event.name < rhs.event.name
        }.map { $0.event }
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

// MARK: - List layout

/// The home list, sorted and grouped once when the events arrive rather
/// than on every redraw of the list.
struct EventList {
    /// Every event in list order. The map uses these too.
    let events: [Event]
    /// The "Next up" card: the first event in list order.
    let hero: Event?
    /// Everything after the hero, in runs of the same day.
    let groups: [(day: Date, events: [Event])]

    init(_ events: [Event], userLocation: CLLocation?) {
        let sorted = events.sortedForList(userLocation: userLocation)
        self.events = sorted
        self.hero = sorted.first
        self.groups = Array(sorted.dropFirst()).groupedByDay()
    }
}
