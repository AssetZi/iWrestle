//
//  EventPagerTests.swift
//  iWrestleTests
//
//  fetchEvents used to take CloudKit's first page and stop, so a busy
//  weekend lost every event past it. These pin the page-following loop.
//

import XCTest
import CloudKit
@testable import iWrestle

final class EventPagerTests: XCTestCase {

    /// A fake CloudKit: fixed pages, an integer cursor, a log of what was asked.
    final class FakeDatabase {
        let pages: [[CKRecord]]
        var requests: [(cursor: Int?, limit: Int)] = []

        init(pages: [[CKRecord]]) { self.pages = pages }

        /// Like CloudKit, honors `limit` and hands back a cursor to the next page.
        func fetch(cursor: Int?, limit: Int) -> EventPage<Int> {
            requests.append((cursor, limit))
            let index = cursor ?? 0
            let next = index + 1 < pages.count ? index + 1 : nil
            return EventPage(records: Array(pages[index].prefix(limit)), cursor: next)
        }
    }

    private func records(_ count: Int, prefix: String = "E") -> [CKRecord] {
        (0..<count).map { TestRecords.event(name: "\(prefix)\($0)") }
    }

    func testFollowsTheCursorAcrossPages() async throws {
        let db = FakeDatabase(pages: [records(3, prefix: "A"), records(3, prefix: "B"), records(2, prefix: "C")])
        let events = try await EventPager.collect(ceiling: 150, fetch: db.fetch)
        XCTAssertEqual(events.map(\.name), ["A0", "A1", "A2", "B0", "B1", "B2", "C0", "C1"])
        XCTAssertEqual(db.requests.map(\.cursor), [nil, 1, 2])
    }

    func testStopsAtTheCeilingAndAsksOnlyForWhatRemains() async throws {
        let db = FakeDatabase(pages: [records(3), records(3), records(3)])
        let events = try await EventPager.collect(ceiling: 5, fetch: db.fetch)
        XCTAssertEqual(events.count, 5)
        XCTAssertEqual(db.requests.map(\.limit), [5, 2])
    }

    /// Records the app cannot decode do not count toward the ceiling, so the
    /// loop keeps going instead of returning short with a live cursor.
    func testUndecodableRecordsDoNotFillTheCeiling() async throws {
        let db = FakeDatabase(pages: [
            [TestRecords.brokenEvent(), TestRecords.brokenEvent(), TestRecords.event(name: "A")],
            [TestRecords.event(name: "B"), TestRecords.brokenEvent()],
            [TestRecords.event(name: "C")],
        ])
        let events = try await EventPager.collect(ceiling: 3, fetch: db.fetch)
        XCTAssertEqual(events.map(\.name), ["A", "B", "C"])
        XCTAssertEqual(db.requests.count, 3)
    }

    func testAnEmptyResultIsEmpty() async throws {
        let db = FakeDatabase(pages: [[]])
        let events = try await EventPager.collect(ceiling: 150, fetch: db.fetch)
        XCTAssertTrue(events.isEmpty)
        XCTAssertEqual(db.requests.count, 1)
    }

    func testAZeroCeilingFetchesNothing() async throws {
        let db = FakeDatabase(pages: [records(3)])
        let events = try await EventPager.collect(ceiling: 0, fetch: db.fetch)
        XCTAssertTrue(events.isEmpty)
        XCTAssertTrue(db.requests.isEmpty)
    }

    func testAFailingPagePropagates() async {
        struct Boom: Error {}
        do {
            _ = try await EventPager.collect(ceiling: 10) { (_: Int?, _) -> EventPage<Int> in throw Boom() }
            XCTFail("expected the error to propagate")
        } catch {
            XCTAssertTrue(error is Boom)
        }
    }
}
