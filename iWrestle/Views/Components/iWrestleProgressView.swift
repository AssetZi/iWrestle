//
//  iWrestleProgressView.swift
//  iWrestle
//
//  Created by Brock Zacherl on 12/11/25.
//

import SwiftUI

struct iWrestleProgressView: View {
    @Environment(\.colorScheme) var cs
    @State private var rotation: Double = 0
    @State private var pulse: Bool = false
    var colors : [Color] {
        cs == .dark ? [.white,.gray]: [.black,.gray]
    }
    var body: some View {
        VStack(spacing: 30) {
            ZStack {
                // Outer ring
                Circle()
                    .stroke(Color.gray.opacity(0.2), lineWidth: 8)
                    .frame(width: 120, height: 120)
                
                // Animated ring
                Circle()
                    .trim(from: 0, to: 0.7)
                    .stroke(
                        LinearGradient(
                            colors: colors,
                            startPoint: .leading,
                            endPoint: .trailing
                        ),
                        style: StrokeStyle(lineWidth: 8, lineCap: .round)
                    )
                    .frame(width: 120, height: 120)
                    .rotationEffect(.degrees(rotation))
                    .animation(
                        .linear(duration: 1.5)
                        .repeatForever(autoreverses: false),
                        value: rotation
                    )
                
                // Center logo
                Image(cs == .dark ? "iWrestleWhite" : "iWrestleBlack")
                    .resizable()
                    .scaledToFit()
                    .frame(width: 90, height: 90)
                    .scaleEffect(pulse ? 1.06 : 0.94)
                    .shadow(color: .black.opacity(0.12), radius: pulse ? 14 : 6, y: 6)
                    .onAppear {
                        withAnimation(.easeInOut(duration: 1.0).repeatForever(autoreverses: true)) {
                            pulse = true
                        }
                        withAnimation(.linear(duration: 2.2).repeatForever(autoreverses: false)) {
                            
                        }
                    }
            }
        }
        .onAppear {rotation = 360}
    }
}


struct iWrestleProgressViewHome: View {
    @Environment(\.colorScheme) var cs
    @State private var pulse: Bool = false
    var colors : [Color] {
        cs == .dark ? [.white,.gray]: [.black,.gray]
    }
    var body: some View {
        // Center logo
        Image(cs == .dark ? "iWrestleWhite" : "iWrestleBlack")
            .resizable()
            .scaledToFit()
            .frame(width: 180, height: 180)
            .scaleEffect(pulse ? 1.06 : 0.94)
            .shadow(color: .black.opacity(0.12), radius: pulse ? 14 : 6, y: 6)
            .onAppear {
                withAnimation(.easeInOut(duration: 1.0).repeatForever(autoreverses: true)) {
                    pulse = true
                }
                withAnimation(.linear(duration: 2.2).repeatForever(autoreverses: false)) {
                    
                }
            }
    }
}

// Preview
#Preview {
    iWrestleProgressViewHome()
}
