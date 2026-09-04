//
//  ErrorViewiWrestle.swift
//  iWrestle
//
//  Created by Brock Zacherl on 12/11/25.
//

import SwiftUI

struct ErrorViewiWrestle: View {
    let error: iWrestleError
    /// Shown as a secondary button under the copy when set (e.g. "Try again").
    var retryTitle: String? = nil
    let action: () -> Void
    @State private var isLoading: Bool = false
    @Environment(\.openURL) private var openURL

    var body: some View {
        VStack(spacing: 14) {
            Spacer(minLength: 0)
            Image(systemName: error.image)
                .font(.system(size: 34, weight: .light))
                .foregroundStyle(Theme.textTertiary)
                .padding(.bottom, 4)
            Text(error.title)
                .font(.pushedTitle)
                .tracked(-0.02, 20)
                .foregroundStyle(Theme.textPrimary)
                .multilineTextAlignment(.center)
            Text(error.description)
                .font(.body13)
                .foregroundStyle(Theme.textSecondary)
                .multilineTextAlignment(.center)
                .lineSpacing(3)
                .frame(maxWidth: 260)

            if error == .locationError {
                locationErrorButtons
            } else if let retryTitle {
                SecondaryButton(title: retryTitle) {
                    isLoading = true
                    action()
                }
                .disabled(isLoading)
                .padding(.top, 8)
            }
            Spacer(minLength: 0)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .padding(.horizontal, 30)
        .entrance()
    }

    private var locationErrorButtons: some View {
        VStack(spacing: 12) {
            PrimaryGoldButton(title: "Go to Settings", icon: .arrowUpRight) {
                if let settingsURL = URL(string: UIApplication.openSettingsURLString) {
                    openURL(settingsURL)
                }
            }
            Button {
                isLoading = true
                action()
            } label: {
                if isLoading {
                    GoldSpinner(size: 18)
                } else {
                    Text("Continue without location")
                        .font(.body13)
                        .foregroundStyle(Theme.textTertiary)
                }
            }
            .buttonStyle(.plain)
            .disabled(isLoading)
        }
        .padding(.top, 10)
    }
}
