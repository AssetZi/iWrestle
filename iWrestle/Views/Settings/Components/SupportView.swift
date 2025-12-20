//
//  SupportView.swift
//  iWrestle
//
//  Created by Brock Zacherl on 11/26/25.
//

import SwiftUI

struct SupportView: View {
    @Environment(\.openURL) private var openURL
    @Environment(NotificationManager.self) var nm
    var body: some View {
        Section {
            NotificationButton()
            Text("💡 Feature Request")
                .onTapGesture {
                    openEmail(subject: "iWrestle Feature Request 💡")
                }
            Text("🐛 Report a Bug")
                .onTapGesture {
                    openEmail(subject: "iWrestle Bug Report 🐛")
                }
            
        } header: {
            Label("Support", systemImage: "envelope")
        }
    }
    private func openEmail(subject: String) {
        let email = "zacherlinvestments@gmail.com"
        let subjectEncoded = subject.addingPercentEncoding(withAllowedCharacters: .urlQueryAllowed) ?? subject
        guard let url = URL(string: "mailto:\(email)?subject=\(subjectEncoded)") else { return }
        openURL(url)
    }
    
    func NotificationButton() -> some View {
        Group {
            if nm.permissionGranted {
                Text("🔕 Remove Notifications")
                    .onTapGesture {
                        nm.openAppSettings()
                    }
            } else {
                Text("🔔 Allow Notifications")
                    .onTapGesture {
                        nm.requestPermission()
                    }
            }
        }
    }
}

#Preview {
    SupportView()
}
