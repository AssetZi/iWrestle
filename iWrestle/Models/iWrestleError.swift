//
//  iWrestleError.swift
//  iWrestle
//
//  Created by Brock Zacherl on 12/11/25.
//

import Foundation

public enum iWrestleError {
    case noData
    case noUserEvents
    case locationError
    
    
    var title: String {
        switch self {
        case .noData:
            return "No Events Found"
        case .noUserEvents:
            return "No User Events Found"
        case .locationError:
            return "iWrestle is Better with Location"
        }
    }
    
    var description: String {
        switch self {
        case .noData:
            return "We will Update you when they are available."
        case .noUserEvents:
            return "Add an Event to Get Started"
        case .locationError:
            return "For the best experience enable Location Services"
        }
    }
    var image: String {
        switch self {
        case .noData:
            return "icloud.slash"
        case .noUserEvents:
            return "magnifyingglass.circle"
        case .locationError:
            return "mappin.slash"
        }
    }
}
