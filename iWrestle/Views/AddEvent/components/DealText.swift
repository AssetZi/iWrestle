//
//  DealText.swift
//  iWrestle
//
//  Created by Brock Zacherl on 12/20/25.
//

import SwiftUI

struct DealText: View {
    var body: some View {
        HStack{
            Spacer()
            VStack{
                Text("Launch Pricing - $1").font(.headline).fontWeight(.heavy)
                Text("Price grows with the app. Capped at $50, always").font(.caption)
                
            }
            Spacer()
                
        }
        .listRowBackground(Color.clear)
        .listRowSeparator(.hidden)
    }
}

#Preview {
    DealText()
}
