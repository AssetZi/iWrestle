//
//  iWrestleProgressView.swift
//  iWrestle
//
//  Created by Brock Zacherl on 12/11/25.
//

import SwiftUI

/// Quiet mark over a gold ring: sheets and pushed screens. The home feed
/// uses EventsListSkeleton instead.
struct iWrestleProgressView: View {
    var body: some View {
        VStack(spacing: 16) {
            Image("iWrestleWhite")
                .renderingMode(.template)
                .resizable()
                .scaledToFit()
                .frame(width: 40, height: 40)
                .foregroundStyle(Theme.slate400)
            GoldSpinner(size: 28)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .accessibilityElement(children: .ignore)
        .accessibilityLabel("Loading")
    }
}

#Preview {
    iWrestleProgressView()
        .background(Theme.ink)
}
