//
//  MetersToMiles.swift
//  iWrestle
//
//  Created by Brock Zacherl on 12/15/25.
//

import Foundation

extension Double {
    var milesToKilometers: Double { self * 1.609344 }
    var milesToMeters: Double { self * 1609.344 }
    var metersToMiles: Double { self / 1609.344 }
    var kilometersToMiles: Double { self / 1.609344 }
}
