//
//  EventFormValidation.swift
//  iWrestle
//
//  Validation rules for AddEventScreen (both the paid and admin modes).
//

import Foundation
import UIKit

/// One case per required field on the add-event form, in the order the fields
/// appear on screen.
///
/// An enum rather than display strings on purpose: row and message code both key
/// off these cases, so re-wording the user-facing text can't silently break a
/// caller the way string matching would.
enum RequiredField: CaseIterable {
    case name
    case location
    case ageGroups
    case flyer
    case contactInfo
    case logo

    var displayName: String {
        switch self {
        case .name:        return "event name"
        case .location:    return "location"
        case .ageGroups:   return "age groups"
        case .flyer:       return "event flyer"
        case .contactInfo: return "contact information"
        case .logo:        return "event logo"
        }
    }
}

/// Every unfilled required field, in form order.
///
/// Replaces a sequential `guard` chain that could only ever report the first
/// failure, so someone with three empty fields had to submit three times to
/// discover all three. The `wantsImagesMade ||` operand is currently always
/// false (the paid-logo toggle never shipped); see TODOS.md for retiring it.
func missingFields(data: EventData, logo: UIImage?, wantsImagesMade: Bool) -> [RequiredField] {
    var missing: [RequiredField] = []

    if data.name.isEmpty { missing.append(.name) }
    if data.location == nil { missing.append(.location) }
    if data.ageGroups.isEmpty { missing.append(.ageGroups) }
    if data.flyer == nil { missing.append(.flyer) }
    if data.eventContactFirstName.isEmpty
        || data.eventContactLastName.isEmpty
        || data.eventContactEmail.isEmpty {
        missing.append(.contactInfo)
    }
    if !(wantsImagesMade || logo != nil) { missing.append(.logo) }

    return missing
}

/// The one-line "still to do" summary, or nil when the form is complete.
func validationMessage(for missing: [RequiredField]) -> String? {
    guard !missing.isEmpty else { return nil }
    return "Please complete: " + missing.map(\.displayName).joined(separator: ", ")
}
