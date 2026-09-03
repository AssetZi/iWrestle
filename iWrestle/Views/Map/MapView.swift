//
//  MapView.swift
//  iWrestle
//
//  Created by Brock Zacherl on 12/4/25.
//

import SwiftUI
import MapKit

/// Written into `address` by earlier versions whenever a picked place had no
/// street address, so existing CloudKit records still contain it. Treated as
/// "no address" on read, otherwise those events would display as filled in.
private let legacyMissingAddress = "Address not available"

/// The location row of the event forms; opens the full-screen place picker.
struct MapView: View {
    @State private var showPicker: Bool = false
    @Binding var selectedLocation: CLLocationCoordinate2D?
    @Binding var address: String
    /// Add-event screens pass true; the edit screen keeps the default so a saved
    /// event never renders in the error state.
    var isRequired: Bool = false
    /// The add screen passes its "attempted submit and still missing" state.
    var showsError: Bool = false

    /// Single source of truth for "this row is filled in". The picker refuses to
    /// return a place without an address, so a usable address and real
    /// coordinates always arrive together.
    private var usableAddress: String? {
        let trimmed = address.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty, trimmed != legacyMissingAddress else { return nil }
        return trimmed
    }

    private var needsAttention: Bool { usableAddress == nil && isRequired }

    var body: some View {
        FormRowButton(icon: .mapPin,
                      text: usableAddress ?? "Add location",
                      isPlaceholder: usableAddress == nil,
                      isInvalid: showsError && needsAttention) {
            showPicker.toggle()
        }
        .accessibilityLabel(accessibilityText)
        .locationPicker(isPresented: $showPicker) { mapItem in
            // The picker's Select button is disabled unless fullAddress exists;
            // this guard keeps the invariant true even if that ever changes.
            if let mapItem, let picked = mapItem.address?.fullAddress {
                selectedLocation = mapItem.location.coordinate
                address = picked
            }
        }
    }

    private var accessibilityText: String {
        if let usableAddress { return "Location, \(usableAddress)" }
        return isRequired ? "Add location, required" : "Add location"
    }
}
