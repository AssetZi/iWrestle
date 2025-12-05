//
//  MapView.swift
//  iWrestle
//
//  Created by Brock Zacherl on 12/4/25.
//

import SwiftUI
import MapKit

struct MapView: View {
    @State private var showPicker: Bool = false
    @Binding var selectedLocation: CLLocationCoordinate2D?
    var body: some View {
        Button("Pick a location"){
            showPicker.toggle()
        }
        .locationPicker(isPresented: $showPicker) { coordinates in
            if let coordinates {
                print(coordinates)
            }
        }
    }
}

//#Preview {
//    MapView()
//}
