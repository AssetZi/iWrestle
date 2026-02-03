//
//  RootView.swift
//  iWrestle
//
//  Created by Brock Zacherl on 11/26/25.
//

import SwiftUI

struct RootView: View {
    @Environment(LocationManager.self) var locationManager
    @Environment(NotificationManager.self) var nm
    var body: some View {
        TabView {
            HomeView()
                .tabItem {
                    Image(systemName: "sparkle.text.clipboard")
                }
            
            SettingsView()
                .tabItem {
                    Image(systemName: "gearshape")
                }
        }
        .tint(.primary)
        .onAppear(perform: locationManager.requestUserLocaiton)
        .task {
            nm.requestPermission()
            guard let loc = locationManager.userLocation else { return }
            nm.scheduleWeeklyNotification(userLocation: loc)
        }
    }
}

#Preview {
    RootView()
}
