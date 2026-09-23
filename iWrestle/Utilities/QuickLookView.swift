//
//  QuickLookView.swift
//  iWrestle
//
//  Created by Brock Zacherl on 12/12/25.
//

import SwiftUI
import Foundation
import UIKit
import QuickLook


struct QuickLookPreview: UIViewControllerRepresentable {
    let url: URL

    func makeUIViewController(context: Context) -> QLPreviewController {
        let controller = QLPreviewController()
        controller.dataSource = context.coordinator
        return controller
    }

    func updateUIViewController(_ controller: QLPreviewController, context: Context) {}

    func makeCoordinator() -> Coordinator {
        Coordinator(url: url)
    }

    final class Coordinator: NSObject, QLPreviewControllerDataSource {
        let url: URL
        init(url: URL) { self.url = url }

        func numberOfPreviewItems(in controller: QLPreviewController) -> Int { 1 }

        func previewController(_ controller: QLPreviewController, previewItemAt index: Int) -> QLPreviewItem {
            url as NSURL
        }
    }
}

struct PDFQuickLookView: View {
    let url: URL // remote URL

    @State private var localURL: URL?

    var body: some View {
        VStack(spacing: 0) {
            HStack(spacing: 12) {
                BackButton()
                VStack(alignment: .leading, spacing: 2) {
                    Eyebrow("Flyer", size: 10)
                    Text("Event flyer")
                        .font(.pushedTitle)
                        .tracked(-0.02, 20)
                        .foregroundStyle(Theme.textPrimary)
                }
                Spacer()
            }
            .padding(.horizontal, Theme.gutter)
            .padding(.top, 6)
            .padding(.bottom, 10)

            Group {
                if let localURL {
                    QuickLookPreview(url: localURL)
                        .clipShape(RoundedRectangle(cornerRadius: Theme.Radius.feature, style: .continuous))
                        .overlay(
                            RoundedRectangle(cornerRadius: Theme.Radius.feature, style: .continuous)
                                .strokeBorder(Theme.borderSubtle, lineWidth: 1)
                        )
                        .padding(.horizontal, Theme.gutter)
                        .padding(.bottom, 16)
                } else {
                    iWrestleProgressView()
                        .task {
                            localURL = try? await downloadToTemp(url)
                        }
                }
            }
        }
        .canvas()
        .toolbar(.hidden, for: .navigationBar)
        .enableSwipeBack()
    }

    func downloadToTemp(_ remote: URL) async throws -> URL {
        let (data, _) = try await URLSession.shared.data(from: remote)
        let tmp = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString).appendingPathExtension("pdf")
        try data.write(to: tmp)
        return tmp
    }
}
