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
    @State var loadedMapItem: MKMapItem?
    var body: some View {
        Button("Pick a location"){
            showPicker.toggle()
        }
        .locationPicker(isPresented: $showPicker) { coordinates in
            if let coordinates {
                print(coordinates)
                
                
                if let request = MKReverseGeocodingRequest(location: CLLocation(latitude: coordinates.latitude, longitude: coordinates.longitude)) {
                    Task{
                        let mapitems = try? await request.mapItems
                        if let mapitem = mapitems?.first {
                            loadedMapItem = mapitem
                        }
                        loadedMapItem?.openInMaps()
                        
                        print(loadedMapItem?.address?.fullAddress ?? ":(")
                        
                    }
                }
            }
        }
    }
}

//#Preview {
//    MapView()
//}
