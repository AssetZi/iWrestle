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
    @State var promo = CrossPromo()
    @State var logos: LogoManager
    @Environment(\.scenePhase) private var scenePhase

    init() {
        LaunchTiming.mark("app init")
        AppFonts.registerAll()
        // One CloudKitManager for the whole app; the weekly digest counts
        // events through the same instance the screens use.
        let ck = CloudKitManager()
        _ck = State(initialValue: ck)
        _nm = State(initialValue: NotificationManager { predicates in
            try await ck.countEvents(predicates: predicates)
        })
        _logos = State(initialValue: LogoManager { ids in
            try await ck.fetchLogos(for: ids)
        })
    }

    var body: some Scene {
        WindowGroup {
            RootView()
                .environment(ck)
                .environment(locationManager)
                .environment(nm)
                .environment(promo)
                .environment(logos)
                // Slate Sky Gold is dark-first; the app commits to it.
                .preferredColorScheme(.dark)
        }
        // Picks the promoted app only once the user can see the app, so
        // the background refresh below does not use up a rotation slot.
        .onChange(of: scenePhase, initial: true) { _, phase in
            if phase == .active { promo.activate() }
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
