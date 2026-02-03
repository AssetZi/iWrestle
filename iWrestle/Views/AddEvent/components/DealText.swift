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
            Text("First 100 Events Get 90% Off!").font(.headline).fontWeight(.heavy)
            Spacer()
                
        }
        .listRowBackground(Color.clear)
        .listRowSeparator(.hidden)
    }
}

#Preview {
    DealText()
}
