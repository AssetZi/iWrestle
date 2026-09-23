//
//  EventPDFExporter.swift
//  iWrestle
//
//  Renders `EventSharePDFPage` to a vector PDF for the share sheet. Text stays
//  selectable and the Geist faces are embedded by CoreGraphics; only the event
//  logo and the QR code are raster.
//

import SwiftUI
import UIKit

enum EventPDFExporter {
    /// Writes the event's share flyer to a temp file and returns its URL.
    /// Nil if the PDF context could not be created.
    static func makePDF(for event: Event) -> URL? {
        // `event.logo` is a CKAsset file URL on disk, so this loads synchronously.
        let logo = UIImage(contentsOfFile: event.logo.path)
        let qr = event.registration.flatMap { QRCode.image(for: $0) }

        // Filled in while the page lays out; read back after `draw` to stamp
        // the link annotations that make the URLs tappable.
        let sink = PDFLinkSink()
        let page = EventSharePDFPage(event: event, logo: logo, qr: qr, linkSink: sink)
        let renderer = ImageRenderer(content: page)
        // Fixed width, natural height: a long name, many age groups or a long
        // registration URL can run past a page, and the render closure reports
        // the height that resulted so it can be scaled to fit below.
        renderer.proposedSize = ProposedViewSize(width: EventSharePDFPage.pageSize.width, height: nil)

        guard let url = destination(for: event) else { return nil }

        var mediaBox = CGRect(origin: .zero, size: EventSharePDFPage.pageSize)
        guard let consumer = CGDataConsumer(url: url as CFURL),
              let context = CGContext(consumer: consumer, mediaBox: &mediaBox, nil)
        else { return nil }

        var didRender = false
        renderer.render { size, draw in
            context.beginPDFPage(nil)
            context.saveGState()

            // The page bleeds to the edges, so paint the sheet before any
            // scale leaves slivers at the sides.
            context.setFillColor(red: 10 / 255, green: 11 / 255, blue: 12 / 255, alpha: 1)
            context.fill(mediaBox)

            let scale = min(1, EventSharePDFPage.pageSize.height / max(size.height, 1))
            let inset = (EventSharePDFPage.pageSize.width * (1 - scale)) / 2
            if scale < 1 {
                context.translateBy(x: inset, y: 0)
                context.scaleBy(x: scale, y: scale)
            }
            draw(context)

            context.restoreGState()
            // Outside the fit-to-page transform on purpose: link annotations are
            // recorded in the page's own space and ignore the CTM, so the scale
            // has to be folded into the rects instead.
            stampLinks(sink.links(forHeight: size.height), in: context,
                       renderedHeight: size.height, scale: scale, inset: scale < 1 ? inset : 0)
            context.endPDFPage()
            didRender = true
        }
        context.closePDF()

        guard didRender else {
            try? FileManager.default.removeItem(at: url)
            return nil
        }
        return url
    }

    /// Adds a `/Link` annotation over each rect the page reported. Without
    /// these the URLs are just glyphs: viewers do not linkify PDF text.
    ///
    /// `setURL` records the rect in the page's coordinate space and does not
    /// apply the current transform, so the fit-to-page scale and inset are
    /// applied here by hand.
    private static func stampLinks(_ links: [(url: URL, rect: CGRect)],
                                   in context: CGContext,
                                   renderedHeight: CGFloat,
                                   scale: CGFloat,
                                   inset: CGFloat) {
        // The page reports top-left origin coordinates; PDF space is
        // bottom-left, so mirror against the height that was rendered.
        let transform = CGAffineTransform(translationX: inset, y: 0)
            .scaledBy(x: scale, y: scale)

        for link in links {
            let flipped = CGRect(x: link.rect.minX,
                                 y: renderedHeight - link.rect.maxY,
                                 width: link.rect.width,
                                 height: link.rect.height)
            let rect = flipped.applying(transform)
            guard rect.width > 0, rect.height > 0 else { continue }
            context.setURL(link.url as CFURL, for: rect)
        }
    }

    /// `tmp/share/<slug>.pdf`, cleared of any previous render.
    private static func destination(for event: Event) -> URL? {
        let directory = FileManager.default.temporaryDirectory
            .appendingPathComponent("share", isDirectory: true)
        do {
            try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
        } catch {
            return nil
        }
        let url = directory.appendingPathComponent("\(event.name.fileSlug).pdf")
        try? FileManager.default.removeItem(at: url)
        return url
    }
}

extension String {
    /// "Knights Novice Tournament!" → "knights-novice-tournament"
    var fileSlug: String {
        var slug = ""
        var pendingDash = false
        for character in lowercased() {
            if character.isLetter || character.isNumber {
                if pendingDash, !slug.isEmpty { slug.append("-") }
                slug.append(character)
                pendingDash = false
            } else {
                pendingDash = true
            }
        }
        return slug.isEmpty ? "event" : slug
    }
}
