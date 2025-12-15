//
//  CloudKitEventCRUD.swift
//  iWrestle
//
//  Created by Brock Zacherl on 12/10/25.
//

import Foundation
import CloudKit
import CoreLocation

extension CloudKitManager {
    
    
    
    func createEvent(data: EventData) async -> Event? {
        let userRef = await getUserReference()
        let newEvent = CKRecord(recordType: "Event")
        newEvent[Event.Field.userID] = userRef
        
        
        guard let logoURL = data.logo else {  print("no logo url"); return nil}
        guard let flyerURL = data.flyer else { print("no flyer url"); return nil}
        guard let lat = data.location?.latitude else { print("no latitude"); return nil}
        guard let long = data.location?.longitude else { print("no longitude"); return nil}
        if !data.registration.isEmpty{
            newEvent[Event.Field.registration] = data.registration
        }
        newEvent[Event.Field.type] = data.eventType.rawValue
        newEvent[Event.Field.name] = data.name
        newEvent[Event.Field.date] = data.date
        newEvent[Event.Field.location] = CLLocation(latitude: lat, longitude: long)
        newEvent[Event.Field.address] = data.address
        newEvent[Event.Field.ageGroups] = data.ageGroupStrings
        newEvent[Event.Field.logo] = CKAsset(fileURL: logoURL)
        newEvent[Event.Field.flyer] = CKAsset(fileURL: flyerURL)
        
        newEvent[Event.Field.eventContactFirstName] = data.eventContactFirstName
        newEvent[Event.Field.eventContactLastName] = data.eventContactLastName
        newEvent[Event.Field.eventContactEmail] = data.eventContactEmail
        newEvent[Event.Field.eventContactPhone] = data.eventContactPhone
        
        
        let result = await saveCkRecord(newEvent)
        if result {
            return Event(record: newEvent)
        } else {
            return nil
        }
    }
    func fetchEvents() async throws -> [Event] {
        let container = CKContainer.default()
        let database = container.publicCloudDatabase
        
        let predicate = NSPredicate(value: true)
        let query = CKQuery(recordType: "Event", predicate: predicate)
        
        let result = try await database.records(matching: query)
        var events: [Event] = []
        
        for (_, matchResult) in result.matchResults {
            if case let .success(record) = matchResult {
                let returnedEvent = Event(record: record)
                events.append(returnedEvent)
            }
        }
        return events
        
    }
    func fetchUserEvents() async throws -> [Event] {
        guard let userRef = await getUserReference() else {return []}
        let container = CKContainer.default()
        let database = container.publicCloudDatabase
        
        let predicate = NSPredicate(format: "%K == %@", Event.Field.userID, userRef)
        let query = CKQuery(recordType: "Event", predicate: predicate)
        
        let result = try await database.records(matching: query)
        var events: [Event] = []

        for (_, matchResult) in result.matchResults {
            if case let .success(record) = matchResult {
                let event = Event(record: record)
                events.append(event)
            }
        }
        return events
    }
    
    func updateEvent(_ event: Event, newFlyer: URL?, newLogo: URL?) async throws {
        let db = CKContainer.default().publicCloudDatabase
        let record = event.record
        
        if let registration = event.registration{
            record[Event.Field.registration] = registration
        }
//        newEvent[Event.Field.type] = event.eventType  // this cant change
        record[Event.Field.name] = event.name
        record[Event.Field.date] = event.date
        record[Event.Field.location] = event.location
        record[Event.Field.address] = event.address
        record[Event.Field.ageGroups] = event.ageGroups
        if let logoURL = newLogo{
            record[Event.Field.logo] = CKAsset(fileURL: logoURL)
        }
        if let flyerURL = newFlyer{
            record[Event.Field.flyer] = CKAsset(fileURL: flyerURL)
        }
        
        record[Event.Field.eventContactFirstName] = event.eventContactFirstName
        record[Event.Field.eventContactLastName] = event.eventContactLastName
        record[Event.Field.eventContactEmail] = event.eventContactEmail
        record[Event.Field.eventContactPhone] = event.eventContactPhone
        
        do {
            let _ = try await db.save(record)
        } catch {print("Error updating event:\(error)")}
    }
    func deleteEvent(_ event: Event) async throws {
        let db = CKContainer.default().publicCloudDatabase
        do {
            try await db.deleteRecord(withID: event.record.recordID)
        } catch {print("Error deleting event:\(error)")}
    }
    
}
