//
//  AppRoute.swift
//  iWrestle
//
//  Value-based navigation so RootView can hide the tab bar whenever a tab's
//  path is non-empty (pushed screens cover the bar, as in the design).
//

import Foundation
import CloudKit

enum AppRoute: Hashable {
    case eventDetail(Event)
    case flyer(URL)
    case dashboard
    case editEvent(CKRecord.ID)
}
