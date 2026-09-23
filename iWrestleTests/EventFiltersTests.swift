//
//  EventFiltersTests.swift
//  iWrestleTests
//
//  The filter sheet caches counts keyed by EventFilters, so equal filters
//  must hash alike and different ones must not collide.
//

import XCTest
import CoreLocation
@testable import iWrestle

final class EventFiltersTests: XCTestCase {

    func testEqualFiltersShareACachedCount() {
        var counts: [EventFilters: Int] = [.default: 42]
        var camps = EventFilters.default
        camps.eventType = .specific(.camp)
        counts[camps] = 3

        XCTAssertEqual(counts[EventFilters()], 42)
        XCTAssertEqual(counts[camps], 3)

        var back = camps
        back.eventType = .all
        XCTAssertEqual(counts[back], 42, "switching a chip back finds the first answer")
    }

    func testDistanceWithoutALocationNeedsOne() {
        var near = EventFilters.default
        near.distance = .under50
        XCTAssertNil(near.predicates(userLocation: nil))
        XCTAssertNotNil(near.predicates(userLocation: CLLocation(latitude: 41.2, longitude: -79.4)))
    }

    func testAnyDistanceNeedsNoLocation() {
        XCTAssertNotNil(EventFilters.default.predicates(userLocation: nil))
    }
}
