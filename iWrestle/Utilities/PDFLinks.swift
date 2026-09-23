//
//  PDFLinks.swift
//  iWrestle
//
//  Lets a SwiftUI view report where its links landed so `EventPDFExporter` can
//  stamp real PDF link annotations over them. Drawing a URL as text is not
//  enough: viewers only make a URL tappable when the page carries a `/Link`
//  annotation, which CoreGraphics adds via `CGContext.setURL(_:for:)` and which
//  needs the rect of every link.
//

import SwiftUI

/// A URL plus the bounds of the view that carries it, resolved later against
/// the page's own coordinate space.
struct PDFLinkAnchor {
    let url: URL
    let anchor: Anchor<CGRect>
}

private struct PDFLinkKey: PreferenceKey {
    static var defaultValue: [PDFLinkAnchor] { [] }

    static func reduce(value: inout [PDFLinkAnchor], nextValue: () -> [PDFLinkAnchor]) {
        value.append(contentsOf: nextValue())
    }
}

/// Where the resolved rects land. A reference type so the exporter can read
/// what the render pass wrote without threading state back through the view.
final class PDFLinkSink {
    /// Link rects in page coordinates (top-left origin, points), keyed by the
    /// height of the layout that produced them.
    ///
    /// `ImageRenderer` lays the page out more than once — once at the proposed
    /// size and once at the natural height it settles on — and a taller layout
    /// wraps text differently, so the rects differ between passes. Keeping each
    /// pass lets the exporter ask for the one it actually drew.
    private var passes: [CGFloat: [(url: URL, rect: CGRect)]] = [:]
    private var lastHeight: CGFloat?

    func record(_ links: [(url: URL, rect: CGRect)], forHeight height: CGFloat) {
        passes[height.rounded()] = links
        lastHeight = height.rounded()
    }

    /// The rects from the layout that was `height` tall, or the most recent
    /// pass if none matches.
    func links(forHeight height: CGFloat) -> [(url: URL, rect: CGRect)] {
        if let match = passes[height.rounded()] { return match }
        return lastHeight.flatMap { passes[$0] } ?? []
    }
}

extension View {
    /// Marks this view as the tap target for `url` in the exported PDF.
    @ViewBuilder
    func pdfLink(_ url: URL?) -> some View {
        if let url {
            anchorPreference(key: PDFLinkKey.self, value: .bounds) {
                [PDFLinkAnchor(url: url, anchor: $0)]
            }
        } else {
            self
        }
    }

    /// Resolves every `pdfLink` below this view into `sink`. Apply once, on the
    /// page root, so the rects come out in page coordinates.
    ///
    /// The write happens while the overlay's body is evaluated rather than from
    /// `onAppear`: `ImageRenderer` lays out and draws synchronously and never
    /// runs the appearance callbacks.
    func collectPDFLinks(into sink: PDFLinkSink?) -> some View {
        overlayPreferenceValue(PDFLinkKey.self) { anchors in
            GeometryReader { proxy in
                let _ = sink?.record(anchors.map { (url: $0.url, rect: proxy[$0.anchor]) },
                                     forHeight: proxy.size.height)
                Color.clear
            }
            .allowsHitTesting(false)
        }
    }
}
