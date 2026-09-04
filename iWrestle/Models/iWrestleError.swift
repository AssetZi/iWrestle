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
            return "No events found."
        case .noUserEvents:
            return "No events yet."
        case .locationError:
            return "iWrestle is better with location."
        }
    }

    var description: String {
        switch self {
        case .noData:
            return "We'll let you know when new events are posted near you."
        case .noUserEvents:
            return "Add an event to get started."
        case .locationError:
            return "Enable Location Services for the best experience."
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
