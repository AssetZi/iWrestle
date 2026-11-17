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

    /// List queries leave the logo out too, so rows can show before any
    /// file downloads; LogoManager fetches it afterwards.
    func testARecordWithoutALogoDecodesWithNilLogo() throws {
        let event = try XCTUnwrap(Event(safeRecord: TestRecords.eventWithoutLogo()))
        XCTAssertNil(event.logo)
    }

    func testARecordWithoutANameIsDropped() {
        XCTAssertNil(Event(safeRecord: TestRecords.undecodable()))
    }

    func testARecordWithALogoKeepsIt() throws {
        let event = try XCTUnwrap(Event(safeRecord: TestRecords.event()))
        XCTAssertNotNil(event.logo)
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
        XCTAssertNil(event.logo)
        XCTAssertEqual(event.eventContactPhone, "814-555-0100")
    }

    /// CloudKit downloads an asset before it returns the record, so either
    /// one in a list query holds the rows back until the files are down.
    func testListKeysLeaveOutBothAssets() {
        XCTAssertFalse(Event.Field.listKeys.contains(Event.Field.flyer))
        XCTAssertFalse(Event.Field.listKeys.contains(Event.Field.logo))
    }
}
