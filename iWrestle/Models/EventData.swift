//
//  EventData.swift
//  iWrestle
//
//  Created by Brock Zacherl on 12/10/25.
//

import Foundation
import CoreLocation

struct EventData{
    var eventType: EventType = .tournament
    var name: String = ""
    
    var eventContactFirstName: String = ""
    var eventContactLastName: String = ""
    var eventContactEmail: String = ""
    var eventContactPhone: String = ""
    
    var date: Date = Date()
    var location: CLLocationCoordinate2D?
    var address: String = ""
    var ageGroups: Set<AgeGroup> = []
    var logo: URL?
    var flyer: URL?
    var registration: String = ""
    
    var ageGroupStrings: [String] {
        ageGroups.map { $0.rawValue }
    }
}


