//
//  iWrestleApp.swift
//  iWrestle
//
//  Created by Brock Zacherl on 11/25/25.
//

import SwiftUI

@main
struct iWrestleApp: App {
    @State var ck: CloudKitManager
    @State var locationManager: LocationManager = .init()
    @State var nm: NotificationManager

    init() {
        AppFonts.registerAll()
        // One CloudKitManager for the whole app; the weekly digest counts
        // events through the same instance the screens use.
        let ck = CloudKitManager()
        _ck = State(initialValue: ck)
        _nm = State(initialValue: NotificationManager { predicates in
            try await ck.fetchEvents(predicates: predicates, limit: FetchLimits.filtered)
        })
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
        // Sunday evening: recount so Monday's number is current even if the
        // app has not been opened. Re-arm first so next week is covered too.
        .backgroundTask(.appRefresh(WeeklyDigest.backgroundTaskIdentifier)) {
            await nm.submitBackgroundRefresh()
            guard let location = LocationManager.lastKnownLocation else { return }
            await nm.refreshWeeklyDigest(location: location, force: true)
        }
    }
}
