//
//  ActivityShareSheet.swift
//  iWrestle
//
//  The event share is a single PDF, but Mail's subject has to come from a
//  `UIActivityItemSource`, so it goes through `UIActivityViewController`.
//

import SwiftUI
import UIKit

struct SharePayload: Identifiable {
    let id = UUID()
    let items: [Any]
}

struct ActivityShareSheet: UIViewControllerRepresentable {
    let items: [Any]

    func makeUIViewController(context: Context) -> UIActivityViewController {
        UIActivityViewController(activityItems: items, applicationActivities: nil)
    }

    func updateUIViewController(_ controller: UIActivityViewController, context: Context) {}
}

/// A shared URL that also supplies Mail's subject line. Used for the flyer's
/// file URL, which keeps Mail from titling the message with the PDF filename.
final class ShareURLItem: NSObject, UIActivityItemSource {
    let url: URL
    let subject: String

    init(url: URL, subject: String) {
        self.url = url
        self.subject = subject
    }

    func activityViewControllerPlaceholderItem(_ controller: UIActivityViewController) -> Any { url }

    func activityViewController(_ controller: UIActivityViewController,
                                itemForActivityType activityType: UIActivity.ActivityType?) -> Any? { url }

    func activityViewController(_ controller: UIActivityViewController,
                                subjectForActivityType activityType: UIActivity.ActivityType?) -> String { subject }
}
