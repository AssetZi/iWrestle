//
//  RootView.swift
//  iWrestle
//
//  Created by Brock Zacherl on 11/26/25.
//

import SwiftUI

struct RootView: View {
    @Environment(LocationManager.self) var locationManager
    
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
    }
}

#Preview {
    RootView()
}
