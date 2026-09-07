//
//  CloudKitEventCRUD.swift
//  iWrestle
//
//  Created by Brock Zacherl on 12/10/25.
//

import Foundation
import CloudKit
import CoreLocation

/// How many events a screen is willing to load at once.
///
/// The directory is national, so these are about what a phone can render
/// and download comfortably, not about CloudKit quota. An event costs
/// roughly 25 KB with its logo and flyer.
enum FetchLimits {
    /// Home: a month within 250 miles. Dense in the Northeast, never near
    /// this on a normal weekend.
    static let home = 150
    /// A filtered search can span the country and a whole season.
    static let filtered = 300
}

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
    func fetchUserEvents() async throws -> [Event] {
        guard let userRef = await getUserReference() else {return []}
        let predicates = [NSPredicate(format: "%K == %@", Event.Field.userID, userRef)]
        return try await fetchEvents(predicates: predicates)
    }

    func fetchEvents(predicates: [NSPredicate], limit: Int? = nil) async throws -> [Event] {
        let predicate = predicates.isEmpty
            ? NSPredicate(value: true)
            : NSCompoundPredicate(andPredicateWithSubpredicates: predicates)
        let query = CKQuery(recordType: "Event", predicate: predicate)
        query.sortDescriptors = [NSSortDescriptor(key: Event.Field.date, ascending: true)]

        let database = CKContainer.default().publicCloudDatabase
        let ceiling = limit ?? FetchLimits.filtered

        // CloudKit answers in pages. Without following the cursor a busy
        // weekend silently loses every event past the first page.
        var events: [Event] = []
        var cursor: CKQueryOperation.Cursor?

        repeat {
            let remaining = ceiling - events.count
            let result: (matchResults: [(CKRecord.ID, Result<CKRecord, Error>)], queryCursor: CKQueryOperation.Cursor?)
            if let cursor {
                result = try await database.records(continuingMatchFrom: cursor, resultsLimit: remaining)
            } else {
                result = try await database.records(matching: query, resultsLimit: remaining)
            }

            for (_, matchResult) in result.matchResults {
                if case let .success(record) = matchResult {
                    if let event = Event(safeRecord: record) {
                        events.append(event)
                    }
                }
            }
            cursor = result.queryCursor
        } while cursor != nil && events.count < ceiling

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
        
        // Rethrows so the edit screen can show the failure instead of
        // reporting a save that never happened.
        _ = try await db.save(record)
    }
    func deleteEvent(_ event: Event) async throws {
        let db = CKContainer.default().publicCloudDatabase
        do {
            try await db.deleteRecord(withID: event.record.recordID)
        } catch {print("Error deleting event:\(error)")}
    }
    
}
