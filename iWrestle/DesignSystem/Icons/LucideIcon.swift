//
//  LucideIcon.swift
//  iWrestle
//
//  Lucide icons drawn as SwiftUI shapes. Path data is copied verbatim from the
//  design prototype so the strokes match the mock exactly.
//

import SwiftUI

/// One drawable piece of an icon. Lucide icons mix path data with `<circle>`,
/// `<rect>` and `<line>` elements, so all four are represented.
enum IconShape {
    case path(String)
    case circle(cx: CGFloat, cy: CGFloat, r: CGFloat)
    case rect(x: CGFloat, y: CGFloat, w: CGFloat, h: CGFloat, radius: CGFloat)
    case line(x1: CGFloat, y1: CGFloat, x2: CGFloat, y2: CGFloat)
}

/// All icons live in a 24×24 viewBox and are stroked at 1.75 units with round
/// caps and joins unless a call site asks for a heavier stroke.
enum Lucide {
    case map, list, slidersHorizontal
    case chevronLeft, chevronRight
    case share, calendar, mapPin, users, fileText, file, image
    case mail, phone, bell, settings, trophy
    case plus, check, x, navigation, arrowUpRight
    case alertCircle, cloudOff, search, refreshCw

    var shapes: [IconShape] {
        switch self {
        case .map:
            return [.path("M9 3 3.6 5.1a1 1 0 0 0-.6.9v12.5a1 1 0 0 0 1.3.9L9 17.5l6 2.5 5.4-2.1a1 1 0 0 0 .6-.9V4.5a1 1 0 0 0-1.3-.9L15 5.5 9 3z"),
                    .line(x1: 9, y1: 3, x2: 9, y2: 17.5),
                    .line(x1: 15, y1: 5.5, x2: 15, y2: 20)]
        case .list:
            return [.line(x1: 4, y1: 6, x2: 20, y2: 6),
                    .line(x1: 4, y1: 12, x2: 20, y2: 12),
                    .line(x1: 4, y1: 18, x2: 20, y2: 18)]
        case .slidersHorizontal:
            return [.line(x1: 21, y1: 5, x2: 14, y2: 5),
                    .line(x1: 10, y1: 5, x2: 3, y2: 5),
                    .line(x1: 21, y1: 12, x2: 12, y2: 12),
                    .line(x1: 8, y1: 12, x2: 3, y2: 12),
                    .line(x1: 21, y1: 19, x2: 16, y2: 19),
                    .line(x1: 12, y1: 19, x2: 3, y2: 19),
                    .line(x1: 14, y1: 3, x2: 14, y2: 7),
                    .line(x1: 8, y1: 10, x2: 8, y2: 14),
                    .line(x1: 16, y1: 17, x2: 16, y2: 21)]
        case .chevronLeft:
            return [.path("M15 18l-6-6 6-6")]
        case .chevronRight:
            return [.path("M9 18l6-6-6-6")]
        case .share:
            return [.path("M12 2v13"),
                    .path("m16 6-4-4-4 4"),
                    .path("M4 12v7a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-7")]
        case .calendar:
            return [.rect(x: 3, y: 4, w: 18, h: 17, radius: 2),
                    .line(x1: 16, y1: 2, x2: 16, y2: 6),
                    .line(x1: 8, y1: 2, x2: 8, y2: 6),
                    .line(x1: 3, y1: 10, x2: 21, y2: 10)]
        case .mapPin:
            return [.path("M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 0 1 16 0z"),
                    .circle(cx: 12, cy: 10, r: 3)]
        case .users:
            return [.path("M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"),
                    .circle(cx: 9, cy: 7, r: 4),
                    .path("M22 21v-2a4 4 0 0 0-3-3.87"),
                    .path("M16 3.13a4 4 0 0 1 0 7.75")]
        case .fileText:
            return [.path("M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"),
                    .path("M14 2v6h6"),
                    .line(x1: 16, y1: 13, x2: 8, y2: 13),
                    .line(x1: 16, y1: 17, x2: 8, y2: 17)]
        case .file:
            return [.path("M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"),
                    .path("M14 2v6h6")]
        case .image:
            return [.rect(x: 3, y: 3, w: 18, h: 18, radius: 2),
                    .circle(cx: 9, cy: 9, r: 2),
                    .path("m21 15-3.086-3.086a2 2 0 0 0-2.828 0L6 21")]
        case .mail:
            return [.rect(x: 2, y: 4, w: 20, h: 16, radius: 2),
                    .path("m22 7-10 6L2 7")]
        case .phone:
            return [.path("M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72c.127.96.361 1.903.7 2.81a2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45c.907.339 1.85.573 2.81.7A2 2 0 0 1 22 16.92z")]
        case .bell:
            return [.path("M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9"),
                    .path("M10.3 21a1.94 1.94 0 0 0 3.4 0")]
        case .settings:
            return [.path("M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z"),
                    .circle(cx: 12, cy: 12, r: 3)]
        case .trophy:
            return [.path("M6 9H4.5a2.5 2.5 0 0 1 0-5H6"),
                    .path("M18 9h1.5a2.5 2.5 0 0 0 0-5H18"),
                    .path("M4 22h16"),
                    .path("M10 14.66V17c0 .55-.47.98-.97 1.21C7.85 18.75 7 20.24 7 22"),
                    .path("M14 14.66V17c0 .55.47.98.97 1.21C16.15 18.75 17 20.24 17 22"),
                    .path("M18 2H6v7a6 6 0 0 0 12 0V2Z")]
        case .plus:
            return [.line(x1: 12, y1: 5, x2: 12, y2: 19),
                    .line(x1: 5, y1: 12, x2: 19, y2: 12)]
        case .check:
            return [.path("M20 6 9 17 4 12")]
        case .x:
            return [.line(x1: 18, y1: 6, x2: 6, y2: 18),
                    .line(x1: 6, y1: 6, x2: 18, y2: 18)]
        case .navigation:
            return [.path("M3 11 22 2 13 21 11 13 3 11z")]
        case .arrowUpRight:
            return [.path("M7 17 17 7"),
                    .path("M8 7h9v9")]
        case .alertCircle:
            return [.circle(cx: 12, cy: 12, r: 10),
                    .line(x1: 12, y1: 8, x2: 12, y2: 12),
                    .line(x1: 12, y1: 16, x2: 12.01, y2: 16)]
        case .cloudOff:
            return [.path("m2 2 20 20"),
                    .path("M5.782 5.782A7 7 0 0 0 9 19h8.5a4.5 4.5 0 0 0 1.307-.193"),
                    .path("M21.532 16.5A4.5 4.5 0 0 0 17.5 10h-1.79A7.008 7.008 0 0 0 10 5.07")]
        case .search:
            return [.circle(cx: 11, cy: 11, r: 7),
                    .path("m21 21-4-4")]
        case .refreshCw:
            return [.path("M21 12a9 9 0 1 1-9-9c2.52 0 4.93 1 6.74 2.74L21 8"),
                    .path("M21 3v5h-5")]
        }
    }
}

private struct LucideShape: Shape {
    let shapes: [IconShape]

    func path(in rect: CGRect) -> Path {
        let scale = min(rect.width, rect.height) / 24
        var combined = Path()
        for shape in shapes {
            switch shape {
            case .path(let d):
                combined.addPath(SVGPath.path(from: d))
            case .circle(let cx, let cy, let r):
                combined.addPath(SVGPath.circle(cx: cx, cy: cy, r: r))
            case .rect(let x, let y, let w, let h, let radius):
                combined.addPath(SVGPath.rect(x: x, y: y, width: w, height: h, radius: radius))
            case .line(let x1, let y1, let x2, let y2):
                var line = Path()
                line.move(to: CGPoint(x: x1, y: y1))
                line.addLine(to: CGPoint(x: x2, y: y2))
                combined.addPath(line)
            }
        }
        return combined.applying(CGAffineTransform(scaleX: scale, y: scale))
    }
}

struct LucideIcon: View {
    let icon: Lucide
    var size: CGFloat = 18
    /// Stroke width in viewBox units, scaled with the icon like an SVG would.
    var strokeWidth: CGFloat = 1.75

    init(_ icon: Lucide, size: CGFloat = 18, strokeWidth: CGFloat = 1.75) {
        self.icon = icon
        self.size = size
        self.strokeWidth = strokeWidth
    }

    var body: some View {
        LucideShape(shapes: icon.shapes)
            .stroke(style: StrokeStyle(lineWidth: strokeWidth * size / 24,
                                       lineCap: .round,
                                       lineJoin: .round))
            .frame(width: size, height: size)
    }
}

#Preview {
    let all: [Lucide] = [.map, .list, .slidersHorizontal, .chevronLeft, .chevronRight, .share,
                         .calendar, .mapPin, .users, .fileText, .file, .image, .mail, .phone,
                         .bell, .settings, .trophy, .plus, .check, .x, .navigation, .arrowUpRight,
                         .alertCircle, .cloudOff, .search, .refreshCw]
    return LazyVGrid(columns: Array(repeating: GridItem(.flexible()), count: 6), spacing: 16) {
        ForEach(Array(all.enumerated()), id: \.offset) { _, icon in
            LucideIcon(icon, size: 22)
        }
    }
    .foregroundStyle(Theme.gold)
    .padding()
    .background(Theme.ink)
}
