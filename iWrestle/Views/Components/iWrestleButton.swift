//
//  iWrestleButton.swift
//  iWrestle
//
//  Created by Brock Zacherl on 12/1/25.
//

import SwiftUI

struct iWrestleButton: View {
    @Environment(\.colorScheme) var cs
    let title: String
    let action: () -> Void
    var body: some View {
        Button(title) { action() }
            .frame(maxWidth: .infinity)
            .padding()
            .font(.headline).bold()
            .background(cs == .dark ? Color.white : Color.black)
            .foregroundStyle(cs == .dark ? .black : .white)
            .cornerRadius(25)
            .listRowBackground(Color.clear)
            .listRowInsets(EdgeInsets())
            .padding()
    }
}

#Preview {
    iWrestleButton(title: "Test", action: {})
}
