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
/// and download comfortably, not about CloudKit quota. A list event costs
/// roughly 26 KB, nearly all of it the logo (the flyer, another ~20 KB on
/// average and up to 5 MB, is left out; see `Event.Field.listKeys`).
/// Counting costs almost nothing, because it fetches no fields at all.
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
    /// The user's own events, with every field, because the editor saves
    /// these records back.
    func fetchUserEvents() async throws -> [Event] {
        guard let userRef = await getUserReference() else {return []}
        let predicates = [NSPredicate(format: "%K == %@", Event.Field.userID, userRef)]
        return try await query(predicates: predicates, ceiling: FetchLimits.filtered,
                               desiredKeys: nil, decode: Event.init(safeRecord:))
    }

    /// Events for a list or map: every field except the flyer.
    func fetchEvents(predicates: [NSPredicate], limit: Int? = nil) async throws -> [Event] {
        try await query(predicates: predicates, ceiling: limit ?? FetchLimits.filtered,
                        desiredKeys: Event.Field.listKeys, decode: Event.init(safeRecord:))
    }

    /// How many events match, up to `ceiling`. Asks for no fields, so only
    /// record IDs cross the network: no logos, no flyers.
    func countEvents(predicates: [NSPredicate], ceiling: Int = FetchLimits.filtered) async throws -> Int {
        try await query(predicates: predicates, ceiling: ceiling,
                        desiredKeys: [], decode: { $0.recordID }).count
    }

    /// - Parameter desiredKeys: nil fetches every field, including both
    ///   assets; an empty array fetches none.
    private func query<Item>(predicates: [NSPredicate],
                             ceiling: Int,
                             desiredKeys: [CKRecord.FieldKey]?,
                             decode: (CKRecord) -> Item?) async throws -> [Item] {
        let predicate = predicates.isEmpty
            ? NSPredicate(value: true)
            : NSCompoundPredicate(andPredicateWithSubpredicates: predicates)
        let query = CKQuery(recordType: "Event", predicate: predicate)
        query.sortDescriptors = [NSSortDescriptor(key: Event.Field.date, ascending: true)]

        let database = CKContainer.default().publicCloudDatabase

        // The page-following loop lives in EventPager so it can be tested
        // without a container; this closure is the only CloudKit-specific part.
        return try await EventPager.collect(ceiling: ceiling, decode: decode) { (cursor: CKQueryOperation.Cursor?, remaining) in
            let result: (matchResults: [(CKRecord.ID, Result<CKRecord, Error>)], queryCursor: CKQueryOperation.Cursor?)
            // The cursor does not remember desiredKeys, so every page must
            // ask again or pages after the first come back with the assets.
            if let cursor {
                result = try await database.records(continuingMatchFrom: cursor, desiredKeys: desiredKeys, resultsLimit: remaining)
            } else {
                result = try await database.records(matching: query, desiredKeys: desiredKeys, resultsLimit: remaining)
            }
            let records = result.matchResults.compactMap { _, match -> CKRecord? in
                if case let .success(record) = match { return record }
                return nil
            }
            return EventPage(records: records, cursor: result.queryCursor)
        }
    }

    /// The flyer for one event. List queries leave it out because it is the
    /// heaviest field and only the detail screen shows it.
    func fetchFlyer(for id: CKRecord.ID) async throws -> URL? {
        let database = CKContainer.default().publicCloudDatabase
        let results = try await database.records(for: [id], desiredKeys: [Event.Field.flyer])
        guard let result = results[id] else { return nil }
        return (try result.get()[Event.Field.flyer] as? CKAsset)?.fileURL
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
