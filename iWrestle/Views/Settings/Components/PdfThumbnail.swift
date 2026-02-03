//
//  PdfThumbnail.swift
//  iWrestle
//
//  Created by Brock Zacherl on 12/14/25.
//

import SwiftUI
import PDFKit

struct PDFThumbnailView: View {
    let url: URL
    let size: CGSize

    var body: some View {
        if let image = thumbnail(from: url, size: size) {
            Image(uiImage: image)
                .resizable()
                .aspectRatio(contentMode: .fill)
                .frame(width: size.width, height: size.height)
                .clipped()
        } else {
            Color.secondary.opacity(0.1)
                .overlay(
                    Image(systemName: "doc.richtext")
                        .imageScale(.large)
                        .foregroundStyle(.secondary)
                )
                .frame(width: size.width, height: size.height)
        }
    }

    private func thumbnail(from url: URL, size: CGSize) -> UIImage? {
        guard let doc = PDFDocument(url: url), let page = doc.page(at: 0) else { return nil }
        let pageRect = page.bounds(for: .mediaBox)
        let scale = min(size.width / pageRect.width, size.height / pageRect.height)
        let scaledSize = CGSize(width: pageRect.width * scale, height: pageRect.height * scale)

        let renderer = UIGraphicsImageRenderer(size: scaledSize)
        return renderer.image { ctx in
            UIColor.clear.set()
            ctx.fill(CGRect(origin: .zero, size: scaledSize))

            ctx.cgContext.saveGState()
            // Flip context because PDF pages are rendered upside down in UIKit coordinates
            ctx.cgContext.translateBy(x: 0, y: scaledSize.height)
            ctx.cgContext.scaleBy(x: 1.0, y: -1.0)

            // Compute scale to fit the page into the target rect while preserving aspect ratio
            let mediaBox = page.bounds(for: .mediaBox)
            let sx = scaledSize.width / mediaBox.width
            let sy = scaledSize.height / mediaBox.height
            let s = min(sx, sy)

            // Center the page in the target rect
            let tx = (scaledSize.width - mediaBox.width * s) / 2.0
            let ty = (scaledSize.height - mediaBox.height * s) / 2.0

            // Apply centering translation, then scale, then translate to page origin
            ctx.cgContext.translateBy(x: tx, y: ty)
            ctx.cgContext.scaleBy(x: s, y: s)
            ctx.cgContext.translateBy(x: -mediaBox.origin.x, y: -mediaBox.origin.y)

            page.draw(with: .mediaBox, to: ctx.cgContext)
            ctx.cgContext.restoreGState()
        }
    }
}



