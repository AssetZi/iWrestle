//
//  Event.swift
//  iWrestle
//
//  Created by Brock Zacherl on 11/26/25.
//

import Foundation
import CloudKit


struct Event: Identifiable, Hashable {
    let record: CKRecord
    let userID: CKRecord.Reference
    var eventType: String // Tournament,Camp,Clinic
    var name: String
    var date: Date
    var location: CLLocation
    var address: String
    var ageGroups: [String]
    var logo: URL
    /// Nil when the record came from a list query, which leaves the flyer
    /// out; `CloudKitManager.fetchFlyer(for:)` loads it on demand.
    var flyer: URL?
    var registration: String?
    
    var eventContactFirstName: String
    var eventContactLastName: String
    var eventContactEmail: String
    var eventContactPhone: String
    
    var id: CKRecord.ID {record.recordID}
}

extension Event {
    static let recordType = "Event"          // CloudKit Record Type
    enum Field {
        static let userID = "userID"
        static let type = "eventType"
        static let name = "name"             // String
        static let date = "date"             // Date
        static let photo = "photo"           // Asset
        static let location = "location"
        static let address = "address"
        static let ageGroups = "ageGroups"
        static let logo = "logo"
        static let flyer = "flyer"
        static let eventContactFirstName = "eventContactFirstName"
        static let eventContactLastName = "eventContactLastName"
        static let eventContactEmail = "eventContactEmail"
        static let eventContactPhone = "eventContactPhone"
        static let registration = "registration"

        /// What list and map queries fetch: every field `init?(safeRecord:)`
        /// reads, minus the flyer. A key missing here makes every event fail
        /// to decode and every list come back empty, so
        /// EventDecodingTests pins it.
        static let listKeys: [CKRecord.FieldKey] = [
            userID, type, name, date, location, address, ageGroups, logo,
            registration, eventContactFirstName, eventContactLastName,
            eventContactEmail, eventContactPhone,
        ]
    }
}


extension Event {
    init (record: CKRecord) {
        let logoAsset = record[Event.Field.logo] as! CKAsset
        let logo = logoAsset.fileURL
        self.record = record
        self.userID = record[Event.Field.userID] as! CKRecord.Reference
        self.eventType = record[Event.Field.type] as! String
        self.registration = record[Event.Field.registration] as? String
        self.name = record[Event.Field.name] as! String
        self.date = record[Event.Field.date] as! Date
        self.location = record[Event.Field.location] as! CLLocation
        self.address = record[Event.Field.address] as! String
        self.ageGroups = record[Event.Field.ageGroups] as! [String]
        self.logo = logo!
        self.flyer = (record[Event.Field.flyer] as? CKAsset)?.fileURL

        self.eventContactFirstName = record[Event.Field.eventContactFirstName] as! String
        self.eventContactLastName = record[Event.Field.eventContactLastName] as! String
        self.eventContactEmail = record[Event.Field.eventContactEmail] as! String
        self.eventContactPhone = record[Event.Field.eventContactPhone] as? String ?? ""
    }

    init?(safeRecord record: CKRecord) {
        guard let logoAsset = record[Event.Field.logo] as? CKAsset,
              let logoURL = logoAsset.fileURL,
              let userID = record[Event.Field.userID] as? CKRecord.Reference,
              let eventType = record[Event.Field.type] as? String,
              let name = record[Event.Field.name] as? String,
              let date = record[Event.Field.date] as? Date,
              let location = record[Event.Field.location] as? CLLocation,
              let address = record[Event.Field.address] as? String,
              let ageGroups = record[Event.Field.ageGroups] as? [String],
              let contactFirstName = record[Event.Field.eventContactFirstName] as? String,
              let contactLastName = record[Event.Field.eventContactLastName] as? String,
              let contactEmail = record[Event.Field.eventContactEmail] as? String
        else { return nil }

        self.record = record
        self.userID = userID
        self.eventType = eventType
        self.registration = record[Event.Field.registration] as? String
        self.name = name
        self.date = date
        self.location = location
        self.address = address
        self.ageGroups = ageGroups
        self.logo = logoURL
        self.flyer = (record[Event.Field.flyer] as? CKAsset)?.fileURL
        self.eventContactFirstName = contactFirstName
        self.eventContactLastName = contactLastName
        self.eventContactEmail = contactEmail
        // Phone is optional; the detail screen hides an empty row.
        self.eventContactPhone = record[Event.Field.eventContactPhone] as? String ?? ""
    }
}
