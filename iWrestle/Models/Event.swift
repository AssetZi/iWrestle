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
    var id: CKRecord.ID
    let userID: CKRecord.ID // using this now bc record.creatorUserRecordID
    var eventType: String // Tournament,Camp,Clinic
    var name: String
    var date: Date
    var location: CLLocation
    var address: String
    var ageGroups: [String]
    var photo: UIImage? // Optional if some events have no photo
    
}

extension Event {
    static let recordType = "Event"          // CloudKit Record Type
    enum Field {
        static let type = "eventType"
        static let name = "name"             // String
        static let date = "date"             // Date
        static let photo = "photo"           // Asset
        static let location = "location"
        static let address = "address"
        static let ageGroups = "ageGroups"
    }
}


extension Event {
    init (record: CKRecord) {
        self.id = record.recordID
        self.userID = record.creatorUserRecordID!
        self.eventType = record[Event.Field.type] as! String
        self.name = record[Event.Field.name] as! String
        self.date = record[Event.Field.date] as! Date
        self.location = record[Event.Field.location] as! CLLocation
        self.address = record[Event.Field.address] as! String
        self.ageGroups = record[Event.Field.ageGroups] as! [String]
//        self.photo = record[Event.Field.photo]?.image // not sure how to best do photo yet
        
        
        
        
    }
}
