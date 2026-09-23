//
//  TestRecords.swift
//  iWrestleTests
//
//  Hand-made CloudKit records. CKRecord and CKAsset work without a
//  container, so decoding can be tested offline.
//

import CloudKit
import CoreLocation
@testable import iWrestle

enum TestRecords {
    /// A record with every field Event(safeRecord:) requires.
    static func event(name: String = "Interstate Classic",
                      phone: String? = "814-555-0100",
                      date: Date = Date(timeIntervalSince1970: 1_792_000_000),
                      location: CLLocation = CLLocation(latitude: 41.2, longitude: -79.4)) -> CKRecord {
        let record = CKRecord(recordType: Event.recordType)
        record[Event.Field.userID] = CKRecord.Reference(recordID: CKRecord.ID(recordName: "_admin"), action: .none)
        record[Event.Field.type] = "tournament"
        record[Event.Field.name] = name
        record[Event.Field.date] = date
        record[Event.Field.location] = location
        record[Event.Field.address] = "Venue, 1 Main St, Clarion, PA 16214"
        record[Event.Field.ageGroups] = ["Youth", "Jr High"]
        record[Event.Field.logo] = CKAsset(fileURL: tempFile("logo.png"))
        record[Event.Field.flyer] = CKAsset(fileURL: tempFile("flyer.pdf"))
        record[Event.Field.eventContactFirstName] = "Jane"
        record[Event.Field.eventContactLastName] = "Coach"
        record[Event.Field.eventContactEmail] = "jane@club.org"
        if let phone {
            record[Event.Field.eventContactPhone] = phone
        }
        return record
    }

    /// A list query leaves the flyer out; the detail screen fetches it.
    static func eventWithoutFlyer() -> CKRecord {
        let record = event(name: "No Flyer")
        record[Event.Field.flyer] = nil
        return record
    }

    /// A record the app must drop: no logo asset.
    static func eventWithoutLogo() -> CKRecord {
        let record = event(name: "Broken")
        record[Event.Field.logo] = nil
        return record
    }

    private static func tempFile(_ name: String) -> URL {
        let url = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString + "-" + name)
        try? Data("x".utf8).write(to: url)
        return url
    }
}
