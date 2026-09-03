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
    @State var nm: NotificationManager = .init()

    init() {
        AppFonts.registerAll()
    }

    var body: some Scene {
        WindowGroup {
            RootView()
                .environment(ck)
                .environment(locationManager)
                .environment(nm)
                // Slate Sky Gold is dark-first; the app commits to it.
                .preferredColorScheme(.dark)
        }
    }
}
