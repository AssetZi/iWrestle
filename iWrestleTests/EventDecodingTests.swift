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

    /// List queries leave the flyer out, so a record without one must
    /// still decode; the detail screen fetches it on demand.
    func testARecordWithoutAFlyerDecodesWithNilFlyer() throws {
        let event = try XCTUnwrap(Event(safeRecord: TestRecords.eventWithoutFlyer()))
        XCTAssertNil(event.flyer)
    }

    func testARecordWithoutALogoIsDropped() {
        XCTAssertNil(Event(safeRecord: TestRecords.eventWithoutLogo()))
    }

    /// List queries fetch only `listKeys`. Strip everything else from a
    /// full record and it must still decode, or every list comes back empty.
    func testListKeysCoverEverythingSafeRecordNeeds() throws {
        let record = TestRecords.event()
        for key in record.allKeys() where !Event.Field.listKeys.contains(key) {
            record[key] = nil
        }
        let event = try XCTUnwrap(Event(safeRecord: record))
        XCTAssertNil(event.flyer)
        XCTAssertEqual(event.eventContactPhone, "814-555-0100")
    }

    func testListKeysLeaveOutTheFlyer() {
        XCTAssertFalse(Event.Field.listKeys.contains(Event.Field.flyer))
    }
}
