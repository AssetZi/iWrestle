//
//  iWrestleApp.swift
//  iWrestle
//
//  Created by Brock Zacherl on 11/25/25.
//

import SwiftUI

@main
struct iWrestleApp: App {
    @State var ck = CloudKitManager()
    @State var locationManager: LocationManager = .init()
    var body: some Scene {
        WindowGroup {
            RootView()
                .environment(ck)
                .environment(locationManager)
                
        }
    }
}
