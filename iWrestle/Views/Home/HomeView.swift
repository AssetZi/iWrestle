//
//  HomeView.swift
//  iWrestle
//
//  Created by Brock Zacherl on 11/26/25.
//

import SwiftUI

struct HomeView: View {
    var body: some View {
        NavigationStack {
            
            ScrollView{
                MapView().padding()
                ForEach(0..<10, id: \.self) { _ in
                    EventCell()
                }
            }
            .navigationTitle(Text("iWrestle"))
        }
    }
}

#Preview {
    HomeView()
}
