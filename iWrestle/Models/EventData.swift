//
//  EventData.swift
//  iWrestle
//
//  Created by Brock Zacherl on 12/10/25.
//

import Foundation
import CoreLocation

struct EventData{
    var eventType: String // Tournament,Camp,Clinic
    var name: String
    var date: Date
    var location: CLLocation
    var address: String
    var ageGroups: [String]
    var logo: URL
    var flyer: URL
}
