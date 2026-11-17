//
//  UserEventTallyTests.swift
//  iWrestleTests
//
//  The Settings badge: counted at launch, then kept right as events are
//  published, loaded by the dashboard, and deleted.
//

import XCTest
@testable import iWrestle

final class UserEventTallyTests: XCTestCase {

    func testTheLaunchCountIsShown() {
        var tally = UserEventTally()
        tally.counted(5, publishedSince: 0)
        XCTAssertEqual(tally.count, 5)
    }

    /// The list holds only the new event, so its size must not replace
    /// the five counted at launch.
    func testPublishingBeforeTheDashboardOpensAddsToTheLaunchCount() {
        var tally = UserEventTally()
        tally.counted(5, publishedSince: 0)
        tally.listChanged(from: 0, to: 1)
        XCTAssertEqual(tally.count, 6)
    }

    func testAnEventPublishedBeforeTheCountArrivesIsKept() {
        var tally = UserEventTally()
        tally.listChanged(from: 0, to: 1)
        tally.counted(5, publishedSince: 1)
        XCTAssertEqual(tally.count, 6)
    }

    /// The dashboard merges its fetch with the event published earlier:
    /// the list goes from one event to six and the count follows it.
    func testOnceTheDashboardHasLoadedTheCountIsTheList() {
        var tally = UserEventTally()
        tally.counted(5, publishedSince: 0)
        tally.listChanged(from: 0, to: 1)
        tally.loaded(listCount: 6)
        tally.listChanged(from: 1, to: 6)
        XCTAssertEqual(tally.count, 6)
    }

    func testDeletingAfterTheDashboardHasLoadedLowersTheCount() {
        var tally = UserEventTally()
        tally.loaded(listCount: 3)
        tally.listChanged(from: 3, to: 2)
        XCTAssertEqual(tally.count, 2)
    }

    /// Events deleted on another device: the launch count said three, the
    /// dashboard found none, and the list's size never changed from zero.
    func testAnEmptyDashboardClearsTheLaunchCount() {
        var tally = UserEventTally()
        tally.counted(3, publishedSince: 0)
        tally.loaded(listCount: 0)
        XCTAssertEqual(tally.count, 0)
    }

    func testALateLaunchCountDoesNotReplaceTheLoadedList() {
        var tally = UserEventTally()
        tally.loaded(listCount: 3)
        tally.counted(2, publishedSince: 0)
        XCTAssertEqual(tally.count, 3)
    }
}
