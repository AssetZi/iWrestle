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
    var eventType: String // Tournament,Camp,Clinic
    var name: String
    var date: Date
    var location: CLLocation
    var address: String
    var ageGroups: [String]
    var photo: UIImage? // Optional if some events have no photo
    
    init(id: CKRecord.ID = CKRecord.ID(recordName: UUID().uuidString),
         eventType: String,
         name: String,
         date: Date,location: CLLocation,address: String,ageGroups: [String],
         photo: UIImage? = nil) {
        self.id = id
        self.eventType = eventType
        self.name = name
        self.date = date
        self.photo = photo
        self.address = address
        self.location = location
        self.ageGroups = ageGroups
    }
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

