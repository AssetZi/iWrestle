//
//  iWrestleProgressView.swift
//  iWrestle
//
//  Created by Brock Zacherl on 12/11/25.
//

import SwiftUI

/// Gold ring around the white mark: sheets and pushed screens.
struct iWrestleProgressView: View {
    @State private var pulse: Bool = false

    var body: some View {
        ZStack {
            GoldSpinner(size: 96)
            Image("iWrestleWhite")
                .resizable()
                .scaledToFit()
                .frame(width: 56, height: 56)
                .scaleEffect(pulse ? 1.04 : 0.96)
                .onAppear {
                    withAnimation(.easeInOut(duration: 1.0).repeatForever(autoreverses: true)) {
                        pulse = true
                    }
                }
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }
}

/// Pulsing white mark used while the home feed loads.
struct iWrestleProgressViewHome: View {
    @State private var pulse: Bool = false

    var body: some View {
        VStack(spacing: 24) {
            Image("iWrestleWhite")
                .resizable()
                .scaledToFit()
                .frame(width: 140, height: 140)
                .scaleEffect(pulse ? 1.05 : 0.95)
                .shadow(color: .black.opacity(0.3), radius: pulse ? 14 : 6, y: 6)
            GoldSpinner(size: 22)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .onAppear {
            withAnimation(.easeInOut(duration: 1.0).repeatForever(autoreverses: true)) {
                pulse = true
            }
        }
    }
}

#Preview {
    iWrestleProgressViewHome()
        .background(Theme.ink)
}
