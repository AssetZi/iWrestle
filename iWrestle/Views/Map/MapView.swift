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
    @Binding var address: String
    @State var loadedMapItem: MKMapItem?
    var body: some View {
        Group{
            if let mapItem = loadedMapItem {
                Button(mapItem.address?.fullAddress ?? "Address not available"){
                    showPicker.toggle()
                }
            } else {
                Button("Pick a location"){
                    showPicker.toggle()
                }
            }
            
        }
        .locationPicker(isPresented: $showPicker) { mapItem in
            if let mapItem {
                loadedMapItem = mapItem
                selectedLocation = mapItem.location.coordinate
                address = mapItem.address?.fullAddress ?? "Address not available"
                
                
//                loadedMapItem?.openInMaps() // use this for events to open in maps
            }
        }
    }
}

//#Preview {
//    MapView()
//}
