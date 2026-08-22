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
/// "no address" on read, otherwise those events would display a ✓ asserting
/// the address is good.
private let legacyMissingAddress = "Address not available"

struct MapView: View {
    @State private var showPicker: Bool = false
    @Binding var selectedLocation: CLLocationCoordinate2D?
    @Binding var address: String
    /// Add-event screens pass true; the edit screen keeps the default so a saved
    /// event never renders in the red required state.
    var isRequired: Bool = false

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
        Button {
            showPicker.toggle()
        } label: {
            HStack {
                Text(rowTitle)
                Spacer()
                Text(usableAddress == nil ? "＋" : "✓")
            }
            // Set on the label's contents, not the row: the callers wrap this in
            // .buttonStyle(BorderlessButtonStyle()), whose accent tint would
            // otherwise repaint an inherited style and swallow the red.
            .foregroundStyle(needsAttention ? AnyShapeStyle(.red) : AnyShapeStyle(.tint))
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

    private var rowTitle: String {
        if let usableAddress { return usableAddress }
        return isRequired ? "Select a location (Required)" : "Pick a location"
    }

    private var accessibilityText: String {
        if let usableAddress { return "Location, \(usableAddress)" }
        return isRequired ? "Select a location, required" : "Pick a location"
    }
}

//#Preview {
//    MapView()
//}
