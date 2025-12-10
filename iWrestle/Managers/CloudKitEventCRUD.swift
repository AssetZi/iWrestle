//
//  CloudKitEventCRUD.swift
//  iWrestle
//
//  Created by Brock Zacherl on 12/10/25.
//

import Foundation
import CloudKit

extension CloudKitManager {
    func createEvent(data: EventData) async -> Event? {
        let newEvent = CKRecord(recordType: "Event")
        guard let userId = newEvent.creatorUserRecordID else { return nil}
        newEvent[Event.Field.userID] = userId.recordName
        newEvent[Event.Field.type] = data.eventType
        newEvent[Event.Field.name] = data.name
        newEvent[Event.Field.date] = data.date
        newEvent[Event.Field.location] = data.location
        newEvent[Event.Field.address] = data.address
        newEvent[Event.Field.ageGroups] = data.ageGroups
        newEvent[Event.Field.logo] = CKAsset(fileURL: data.logo)
        newEvent[Event.Field.flyer] = CKAsset(fileURL: data.flyer)
        
        let result = await saveCkRecord(newEvent)
        if result {
            return Event(record: newEvent)
        } else {
            return nil
        }
    }
}
