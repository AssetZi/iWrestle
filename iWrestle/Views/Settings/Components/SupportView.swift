//
//  SupportView.swift
//  iWrestle
//
//  Created by Brock Zacherl on 11/26/25.
//

import SwiftUI

struct SupportView: View {
    @Environment(\.openURL) private var openURL
    @Environment(\.scenePhase) private var scenePhase
    @Environment(NotificationManager.self) var nm
    @Environment(LocationManager.self) var lm

    private var locationOn: Bool {
        lm.isPermissionDenied == false
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 9) {
            SectionLabel("Support")
            VStack(spacing: 0) {
                CardRow(icon: .bell, label: "Notifications") {
                    GoldSwitch(isOn: nm.permissionGranted) { nm.openAppSettings() }
                }
                .accessibilityElement(children: .combine)
                HairlineDivider()
                CardRow(icon: .mapPin, label: "Location") {
                    GoldSwitch(isOn: locationOn) { openSystemSettings() }
                }
                .accessibilityElement(children: .combine)
                HairlineDivider()
                PressableRow {
                    openEmail(subject: "iWrestle feature request")
                } content: {
                    CardRow(icon: .share, label: "Feature request")
                }
                HairlineDivider()
                PressableRow {
                    openEmail(subject: "iWrestle bug report")
                } content: {
                    CardRow(icon: .mail, label: "Report a bug")
                }
            }
            .cardContainer()
        }
        .onChange(of: scenePhase) { _, phase in
            // Coming back from Settings: reflect whatever the user changed.
            if phase == .active { nm.refreshAuthorizationStatus() }
        }
    }

    private func openEmail(subject: String) {
        let email = "zacherlinvestments@gmail.com"
        let subjectEncoded = subject.addingPercentEncoding(withAllowedCharacters: .urlQueryAllowed) ?? subject
        guard let url = URL(string: "mailto:\(email)?subject=\(subjectEncoded)") else { return }
        openURL(url)
    }

    private func openSystemSettings() {
        if let settingsURL = URL(string: UIApplication.openSettingsURLString) {
            openURL(settingsURL)
        }
    }
}
