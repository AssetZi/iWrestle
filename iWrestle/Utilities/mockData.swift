//
//  mockData.swift
//  iWrestle
//
//  Created by Brock Zacherl on 11/26/25.
//
//  DEBUG-only fixtures. Launch with the `-iWrestleMockEvents` argument (Edit
//  Scheme → Arguments) to fill the home feed and dashboard with local events
//  instead of querying CloudKit — for previews, screenshots and QA.
//

import Foundation

let mockImages = ["knights","chrsitmas","tiger","classic"]
let weightInTypes = ["Madison", "Weight Class"]
let tournamentFormat = ["Round Robin", "Double Elimination"]
let mockSquares = ["knightsSquare","christmasSquare","tigerSquare","classicSquare"]
let mockDistances = [10,20,50,60]
let mockAddresses = ["1600 Pennsylvania Ave NW, Washington, DC 20500", "1 Apple Park Way, Cupertino, CA 95014", "350 Fifth Ave, New York, NY 10118", "4059 Mt Lee Dr, Hollywood, CA 90068"]

let mockEventNames = ["Interstate Classic", "Tiger Invitational", "Christmas Bash 5", "Knights Novice Tournament"]

#if DEBUG
import CloudKit
import CoreLocation

enum MockEvents {
    static var isEnabled: Bool {
        ProcessInfo.processInfo.arguments.contains("-iWrestleMockEvents")
    }

    /// The five events from the design prototype, dated relative to today.
    static var nearby: [Event] {
        let cal = Calendar.current
        func day(_ offset: Int) -> Date {
            cal.date(byAdding: .day, value: offset, to: cal.startOfDay(for: Date())) ?? Date()
        }
        return [
            make("Interstate Classic", type: .tournament, date: day(2),
                 address: "Clarion County YMCA, 499 Mayfield Rd, Clarion, PA 16214, United States",
                 lat: 41.2098, lon: -79.3990, ages: ["Novice", "Youth", "Jr High"],
                 first: "Mike", last: "Deluca", email: "deluca.wrestling@gmail.com", phone: "(814) 555-0141",
                 registration: "https://example.com/interstate"),
            make("Tiger Invitational", type: .tournament, date: day(9),
                 address: "Brookville Area HS, 100 Blue and Silver Blvd, Brookville, PA 15825, United States",
                 lat: 41.1612, lon: -79.0831, ages: ["Youth", "Jr High", "High School"],
                 first: "Dana", last: "Reed", email: "dreed.tigerwrestling@gmail.com", phone: "(814) 555-0177",
                 registration: nil),
            make("Knights Novice Tournament", type: .tournament, date: day(9),
                 address: "Knights Fieldhouse, 120 Campus Ln, Butler, PA 16001, United States",
                 lat: 40.8612, lon: -79.8953, ages: ["Novice", "Youth"],
                 first: "Brock", last: "Zacherl", email: "zacherlinvestments@gmail.com", phone: "(814) 555-0102",
                 registration: "https://example.com/knights"),
            make("Christmas Bash 5", type: .tournament, date: day(16),
                 address: "Punxsutawney Area MS, 500 N Findley St, Punxsutawney, PA 15767, United States",
                 lat: 40.9437, lon: -78.9709, ages: ["Youth", "Jr High", "High School", "Open"],
                 first: "Tom", last: "Wallace", email: "punxywrestling@gmail.com", phone: "(814) 555-0163",
                 registration: nil),
            make("Golden Eagle Fall Camp", type: .camp, date: day(22),
                 address: "Tippin Gymnasium, 840 Wood St, Clarion, PA 16214, United States",
                 lat: 41.2107, lon: -79.3789, ages: ["Jr High", "High School"],
                 first: "Brock", last: "Zacherl", email: "zacherlinvestments@gmail.com", phone: "",
                 registration: "https://example.com/camp"),
        ]
    }

    /// The two "mine" events from the prototype.
    static var mine: [Event] {
        nearby.filter { $0.eventContactLastName == "Zacherl" }
    }

    /// Key-value object the filter predicates can evaluate locally (distance
    /// predicates are CloudKit-only and are skipped by the caller).
    static func predicateObject(_ event: Event) -> NSDictionary {
        ["eventType": event.eventType, "ageGroups": event.ageGroups, "date": event.date]
    }

    private static func make(_ name: String, type: EventType, date: Date, address: String,
                             lat: Double, lon: Double, ages: [String],
                             first: String, last: String, email: String, phone: String,
                             registration: String?) -> Event {
        let record = CKRecord(recordType: Event.recordType,
                              recordID: CKRecord.ID(recordName: "mock-\(name.lowercased().replacingOccurrences(of: " ", with: "-"))"))
        let owner = CKRecord.Reference(recordID: CKRecord.ID(recordName: "mock-user"), action: .none)
        let missing = URL(fileURLWithPath: "/dev/null")
        return Event(record: record, userID: owner, eventType: type.rawValue, name: name, date: date,
                     location: CLLocation(latitude: lat, longitude: lon), address: address,
                     ageGroups: ages, logo: missing, flyer: missing, registration: registration,
                     eventContactFirstName: first, eventContactLastName: last,
                     eventContactEmail: email, eventContactPhone: phone)
    }
}
#endif
