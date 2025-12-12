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
    
    
    var title: String {
        switch self {
        case .noData:
            return "No Events Found"
        case .noUserEvents:
            return "No User Events Found"
        }
    }
    
    var description: String {
        switch self {
        case .noData:
            return "Try again later or with a different location."
        case .noUserEvents:
            return "Add an Event to Get Started"
        }
    }
    var image: String {
        switch self {
        case .noData:
            return "icloud.slash"
        case .noUserEvents:
            return "magnifyingglass.circle"
        }
    }
}
