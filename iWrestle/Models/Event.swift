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
    var photo: UIImage? // Optional if some events have no photo
    
    init(id: CKRecord.ID = CKRecord.ID(recordName: UUID().uuidString),
         eventType: String,
         name: String,
         date: Date,
         photo: UIImage? = nil) {
        self.id = id
        self.eventType = eventType
        self.name = name
        self.date = date
        self.photo = photo
    }
}

extension Event {
    static let recordType = "Event"          // CloudKit Record Type
    enum Field {
        static let type = "eventType"
        static let name = "name"             // String
        static let date = "date"             // Date
        static let photo = "photo"           // Asset
    }
}

extension Event {
    // Create a CKRecord from Event (writes photo to temp file -> CKAsset)
    func toCKRecord(existing: CKRecord? = nil) throws -> CKRecord {
        let record = existing ?? CKRecord(recordType: Event.recordType, recordID: id)
        record[Event.Field.name] = name as CKRecordValue
        record[Event.Field.date] = date as CKRecordValue
        
        if let photo = photo, let data = photo.jpegData(compressionQuality: 0.9) {
            let url = try FileManager.default.createTempFile(with: data, suggestedFilename: "event.jpg")
            record[Event.Field.photo] = CKAsset(fileURL: url)
        } else {
            // Clear the asset if no photo
            record[Event.Field.photo] = nil
        }
        return record
    }
    
    // Build an Event from a CKRecord (loads image from CKAsset)
    static func fromCKRecord(_ record: CKRecord) -> Event {
        let type = record[Field.type] as? String ?? ""
        let name = record[Field.name] as? String ?? ""
        let date = record[Field.date] as? Date ?? .distantPast
        
        var image: UIImage? = nil
        if let asset = record[Field.photo] as? CKAsset,
           let url = asset.fileURL,
           let data = try? Data(contentsOf: url) {
            image = UIImage(data: data)
        }
        
        return Event(id: record.recordID, eventType: type, name: name, date: date, photo: image)
    }
}
