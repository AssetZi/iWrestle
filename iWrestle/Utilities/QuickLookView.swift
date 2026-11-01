//
//  QuickLookView.swift
//  iWrestle
//
//  Created by Brock Zacherl on 12/12/25.
//

import SwiftUI
import Foundation
import UIKit
import PDFKit

/// Renders a local PDF with PDFKit rather than Quick Look. An embedded
/// QLPreviewController reaches for the navigation controller's bars to host
/// its share and markup items, which this screen hides, and its white chrome
/// fought the dark canvas. PDFView has no bar behaviour and takes the slate
/// background. (The header bounce this screen used to have was the spinner's
/// leaked repeat-forever animation, fixed in GoldSpinner.)
struct PDFKitView: UIViewRepresentable {
    let url: URL

    func makeUIView(context: Context) -> PDFView {
        let view = PDFView()
        view.autoScales = true
        view.displayMode = .singlePageContinuous
        view.displayDirection = .vertical
        view.backgroundColor = UIColor(Theme.slate950)
        view.document = PDFDocument(url: url)
        return view
    }

    func updateUIView(_ view: PDFView, context: Context) {
        if view.document?.documentURL != url {
            view.document = PDFDocument(url: url)
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
                    PDFKitView(url: localURL)
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
