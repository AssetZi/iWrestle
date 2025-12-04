//
//  MapView.swift
//  iWrestle
//
//  Created by Brock Zacherl on 12/4/25.
//

import SwiftUI

struct MapView: View {
    @State private var showPicker: Bool = false
    var body: some View {
        List{
            Button("Pick a location"){
                showPicker.toggle()
            }
            .locationPicker(isPresented: $showPicker) { coordinates in
                
            }
        }
    }
}

#Preview {
    MapView()
}
