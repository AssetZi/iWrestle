import CoreGraphics
import SwiftUI

/// Minimal SVG path-data parser. The Lucide icons use elliptical arc commands,
/// so the `d` strings are parsed as-is rather than hand-converted to Path calls.
enum SVGPath {

    static func path(from d: String) -> Path {
        var path = Path()
        var current = CGPoint.zero
        var subpathStart = CGPoint.zero
        var lastControl: CGPoint?
        var lastCommand: Character = " "

        let tokens = tokenize(d)
        var i = 0

        func nextValue() -> CGFloat? {
            guard i < tokens.count, case .number(let v) = tokens[i] else { return nil }
            i += 1
            return v
        }
        func point(relative: Bool) -> CGPoint? {
            guard let x = nextValue(), let y = nextValue() else { return nil }
            return relative ? CGPoint(x: current.x + x, y: current.y + y) : CGPoint(x: x, y: y)
        }

        while i < tokens.count {
            var command: Character
            if case .command(let c) = tokens[i] {
                command = c
                i += 1
            } else {
                // Repeated coordinate set: an implicit repeat of the last command
                // (moveto repeats as lineto, per the SVG spec).
                command = lastCommand == "M" ? "L" : (lastCommand == "m" ? "l" : lastCommand)
                // Z consumes no operands, so an implicit repeat of it would spin forever.
                if command == " " || command == "Z" || command == "z" { break }
            }

            let relative = command.isLowercase
            switch Character(command.uppercased()) {
            case "M":
                guard let p = point(relative: relative) else { break }
                path.move(to: p)
                current = p
                subpathStart = p
                lastControl = nil
            case "L":
                guard let p = point(relative: relative) else { break }
                path.addLine(to: p)
                current = p
                lastControl = nil
            case "H":
                guard let x = nextValue() else { break }
                let p = CGPoint(x: relative ? current.x + x : x, y: current.y)
                path.addLine(to: p)
                current = p
                lastControl = nil
            case "V":
                guard let y = nextValue() else { break }
                let p = CGPoint(x: current.x, y: relative ? current.y + y : y)
                path.addLine(to: p)
                current = p
                lastControl = nil
            case "C":
                guard let c1 = point(relative: relative),
                      let c2 = point(relative: relative),
                      let p = point(relative: relative) else { break }
                path.addCurve(to: p, control1: c1, control2: c2)
                current = p
                lastControl = c2
            case "S":
                guard let c2 = point(relative: relative),
                      let p = point(relative: relative) else { break }
                let c1 = reflect(lastControl, about: current, when: "CS", lastCommand: lastCommand)
                path.addCurve(to: p, control1: c1, control2: c2)
                current = p
                lastControl = c2
            case "Q":
                guard let c = point(relative: relative),
                      let p = point(relative: relative) else { break }
                path.addQuadCurve(to: p, control: c)
                current = p
                lastControl = c
            case "T":
                guard let p = point(relative: relative) else { break }
                let c = reflect(lastControl, about: current, when: "QT", lastCommand: lastCommand)
                path.addQuadCurve(to: p, control: c)
                current = p
                lastControl = c
            case "A":
                guard let rx = nextValue(), let ry = nextValue(), let rot = nextValue(),
                      let large = nextValue(), let sweep = nextValue(),
                      let p = point(relative: relative) else { break }
                addArc(to: &path, from: current, rx: rx, ry: ry, rotationDegrees: rot,
                       largeArc: large != 0, sweep: sweep != 0, end: p)
                current = p
                lastControl = nil
            case "Z":
                path.closeSubpath()
                current = subpathStart
                lastControl = nil
            default:
                break
            }
            lastCommand = command
        }
        return path
    }

    // MARK: - Circles and rects (SVG shape elements, not path data)

    static func circle(cx: CGFloat, cy: CGFloat, r: CGFloat) -> Path {
        Path(ellipseIn: CGRect(x: cx - r, y: cy - r, width: r * 2, height: r * 2))
    }

    static func rect(x: CGFloat, y: CGFloat, width: CGFloat, height: CGFloat, radius: CGFloat) -> Path {
        Path(roundedRect: CGRect(x: x, y: y, width: width, height: height), cornerRadius: radius)
    }

    // MARK: - Tokenizer

    private enum Token {
        case command(Character)
        case number(CGFloat)
    }

    private static func tokenize(_ d: String) -> [Token] {
        var tokens: [Token] = []
        let chars = Array(d)
        var i = 0
        while i < chars.count {
            let c = chars[i]
            if c.isLetter {
                tokens.append(.command(c))
                i += 1
            } else if c == "-" || c == "+" || c == "." || c.isNumber {
                var s = ""
                var seenDot = false
                if c == "-" || c == "+" { s.append(chars[i]); i += 1 }
                while i < chars.count {
                    let ch = chars[i]
                    if ch.isNumber {
                        s.append(ch); i += 1
                    } else if ch == "." && !seenDot {
                        seenDot = true; s.append(ch); i += 1
                    } else if ch == "e" || ch == "E" {
                        s.append(ch); i += 1
                        if i < chars.count, chars[i] == "-" || chars[i] == "+" { s.append(chars[i]); i += 1 }
                    } else {
                        break
                    }
                }
                if let v = Double(s) { tokens.append(.number(CGFloat(v))) }
            } else {
                i += 1 // whitespace or comma
            }
        }
        return tokens
    }

    private static func reflect(_ control: CGPoint?, about current: CGPoint,
                                when valid: String, lastCommand: Character) -> CGPoint {
        guard let control, valid.contains(Character(lastCommand.uppercased())) else { return current }
        return CGPoint(x: 2 * current.x - control.x, y: 2 * current.y - control.y)
    }

    // MARK: - Elliptical arc → cubic beziers (SVG spec F.6.5)

    private static func addArc(to path: inout Path, from p0: CGPoint,
                               rx: CGFloat, ry: CGFloat, rotationDegrees: CGFloat,
                               largeArc: Bool, sweep: Bool, end p1: CGPoint) {
        if p0 == p1 { return }
        var rx = abs(rx), ry = abs(ry)
        if rx == 0 || ry == 0 {
            path.addLine(to: p1)
            return
        }

        let phi = rotationDegrees * .pi / 180
        let cosPhi = cos(phi), sinPhi = sin(phi)

        let dx = (p0.x - p1.x) / 2, dy = (p0.y - p1.y) / 2
        let x1 = cosPhi * dx + sinPhi * dy
        let y1 = -sinPhi * dx + cosPhi * dy

        // Scale up radii that are too small to span the endpoints.
        let lambda = (x1 * x1) / (rx * rx) + (y1 * y1) / (ry * ry)
        if lambda > 1 {
            let s = sqrt(lambda)
            rx *= s
            ry *= s
        }

        let sign: CGFloat = (largeArc != sweep) ? 1 : -1
        let numerator = max(0, rx * rx * ry * ry - rx * rx * y1 * y1 - ry * ry * x1 * x1)
        let denominator = rx * rx * y1 * y1 + ry * ry * x1 * x1
        let coef = denominator == 0 ? 0 : sign * sqrt(numerator / denominator)
        let cx1 = coef * rx * y1 / ry
        let cy1 = -coef * ry * x1 / rx

        let cx = cosPhi * cx1 - sinPhi * cy1 + (p0.x + p1.x) / 2
        let cy = sinPhi * cx1 + cosPhi * cy1 + (p0.y + p1.y) / 2

        func angle(_ ux: CGFloat, _ uy: CGFloat, _ vx: CGFloat, _ vy: CGFloat) -> CGFloat {
            let dot = ux * vx + uy * vy
            let len = sqrt(ux * ux + uy * uy) * sqrt(vx * vx + vy * vy)
            guard len != 0 else { return 0 }
            let a = acos(min(1, max(-1, dot / len)))
            return (ux * vy - uy * vx) < 0 ? -a : a
        }

        let sx = (x1 - cx1) / rx, sy = (y1 - cy1) / ry
        let ex = (-x1 - cx1) / rx, ey = (-y1 - cy1) / ry
        var theta = angle(1, 0, sx, sy)
        var delta = angle(sx, sy, ex, ey)
        if !sweep && delta > 0 { delta -= 2 * .pi }
        if sweep && delta < 0 { delta += 2 * .pi }

        // Split into segments of at most 90° for an accurate bezier fit.
        let segments = max(1, Int(ceil(abs(delta) / (.pi / 2))))
        let step = delta / CGFloat(segments)
        let alpha = 4.0 / 3.0 * tan(step / 4)

        func pointOn(_ t: CGFloat) -> CGPoint {
            CGPoint(x: cx + rx * cos(t) * cosPhi - ry * sin(t) * sinPhi,
                    y: cy + rx * cos(t) * sinPhi + ry * sin(t) * cosPhi)
        }
        func derivativeAt(_ t: CGFloat) -> CGPoint {
            CGPoint(x: -rx * sin(t) * cosPhi - ry * cos(t) * sinPhi,
                    y: -rx * sin(t) * sinPhi + ry * cos(t) * cosPhi)
        }

        for _ in 0..<segments {
            let t2 = theta + step
            let start = pointOn(theta), endPoint = pointOn(t2)
            let d1 = derivativeAt(theta), d2 = derivativeAt(t2)
            path.addCurve(to: endPoint,
                          control1: CGPoint(x: start.x + alpha * d1.x, y: start.y + alpha * d1.y),
                          control2: CGPoint(x: endPoint.x - alpha * d2.x, y: endPoint.y - alpha * d2.y))
            theta = t2
        }
    }
}
