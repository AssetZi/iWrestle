//
//  EventListTests.swift
//  iWrestleTests
//
//  The home list is sorted and grouped once when events load. These pin
//  the order (day, then distance, then name), the hero, and the grouping.
//

import XCTest
import CoreLocation
@testable import iWrestle

final class EventListTests: XCTestCase {
    private let home = CLLocation(latitude: 41.2, longitude: -79.4)
    private let saturday = Date(timeIntervalSince1970: 1_792_000_000)
    private var sunday: Date { saturday.addingTimeInterval(24 * 60 * 60) }

    private func event(_ name: String, on date: Date, milesNorth: Double = 0) throws -> Event {
        let location = CLLocation(latitude: home.coordinate.latitude + milesNorth / 69,
                                  longitude: home.coordinate.longitude)
        return try XCTUnwrap(Event(safeRecord: TestRecords.event(name: name, date: date, location: location)))
    }

    func testOrdersByDayThenDistanceThenName() throws {
        let events = [
            try event("Sunday Near", on: sunday),
            try event("Saturday Far", on: saturday, milesNorth: 80),
            try event("Saturday Near B", on: saturday, milesNorth: 5),
            try event("Saturday Near A", on: saturday.addingTimeInterval(3600), milesNorth: 5),
        ]
        let sorted = events.sortedForList(userLocation: home).map(\.name)
        XCTAssertEqual(sorted, ["Saturday Near A", "Saturday Near B", "Saturday Far", "Sunday Near"])
    }

    func testWithoutALocationTiesBreakByName() throws {
        let events = [try event("B", on: saturday, milesNorth: 1), try event("A", on: saturday, milesNorth: 90)]
        XCTAssertEqual(events.sortedForList(userLocation: nil).map(\.name), ["A", "B"])
    }

    func testHeroIsFirstAndTheRestGroupByDay() throws {
        let list = EventList([
            try event("Sun 1", on: sunday),
            try event("Sat 2", on: saturday, milesNorth: 10),
            try event("Sat 1", on: saturday, milesNorth: 1),
            try event("Sun 2", on: sunday, milesNorth: 10),
        ], userLocation: home)

        XCTAssertEqual(list.hero?.name, "Sat 1")
        XCTAssertEqual(list.events.count, 4)
        XCTAssertEqual(list.groups.map { $0.events.map(\.name) }, [["Sat 2"], ["Sun 1", "Sun 2"]])
        XCTAssertLessThan(list.groups[0].day, list.groups[1].day)
    }

    func testAnEmptyListHasNoHero() {
        let list = EventList([], userLocation: home)
        XCTAssertNil(list.hero)
        XCTAssertTrue(list.groups.isEmpty)
    }
}
