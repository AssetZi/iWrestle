//
//  Event.swift
//  iWrestle
//
//  Created by Brock Zacherl on 11/26/25.
//

import Foundation
import CloudKit
import UIKit

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
    var flyer: URL
    
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
    }
}


extension Event {
    init (record: CKRecord) {
        let logoAsset = record[Event.Field.logo] as! CKAsset
        let flyerAsset = record[Event.Field.flyer] as! CKAsset
        
        let logo = logoAsset.fileURL
        let flyer = flyerAsset.fileURL
        self.record = record
        self.userID = record[Event.Field.userID] as! CKRecord.Reference
        self.eventType = record[Event.Field.type] as! String
        self.name = record[Event.Field.name] as! String
        self.date = record[Event.Field.date] as! Date
        self.location = record[Event.Field.location] as! CLLocation
        self.address = record[Event.Field.address] as! String
        self.ageGroups = record[Event.Field.ageGroups] as! [String]
        self.logo = logo!
        self.flyer = flyer!
        
        self.eventContactFirstName = record[Event.Field.eventContactFirstName] as! String
        self.eventContactLastName = record[Event.Field.eventContactLastName] as! String
        self.eventContactEmail = record[Event.Field.eventContactEmail] as! String
        self.eventContactPhone = record[Event.Field.eventContactPhone] as! String
    }
}
