//
//  EventDecodingTests.swift
//  iWrestleTests
//

import XCTest
import CloudKit
@testable import iWrestle

final class EventDecodingTests: XCTestCase {

    func testACompleteRecordDecodes() throws {
        let event = try XCTUnwrap(Event(safeRecord: TestRecords.event()))
        XCTAssertEqual(event.name, "Interstate Classic")
        XCTAssertEqual(event.ageGroups, ["Youth", "Jr High"])
        XCTAssertEqual(event.eventContactPhone, "814-555-0100")
        XCTAssertNil(event.registration)
    }

    /// The pipeline writes events without a phone; the detail screen hides
    /// the empty row. A missing field must not drop the whole record.
    func testAMissingPhoneDecodesAsEmpty() throws {
        let event = try XCTUnwrap(Event(safeRecord: TestRecords.event(phone: nil)))
        XCTAssertEqual(event.eventContactPhone, "")
    }

    func testARecordMissingAnAssetIsDropped() {
        XCTAssertNil(Event(safeRecord: TestRecords.brokenEvent()))
    }
}
