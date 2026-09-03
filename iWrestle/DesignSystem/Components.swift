//
//  Components.swift
//  iWrestle
//
//  Shared Slate Sky Gold building blocks. Sizes and radii come straight from
//  the design handoff; screens compose these rather than restating them.
//

import SwiftUI

// MARK: - Cards

struct CardStyle: ViewModifier {
    var padding: CGFloat
    var radius: CGFloat
    var fill: Color
    var border: Color

    func body(content: Content) -> some View {
        content
            .padding(padding)
            .background(fill)
            .clipShape(RoundedRectangle(cornerRadius: radius, style: .continuous))
            .overlay(
                RoundedRectangle(cornerRadius: radius, style: .continuous)
                    .strokeBorder(border, lineWidth: 1)
            )
    }
}

extension View {
    /// Slate-950 surface, hairline border, 16pt radius.
    func card(padding: CGFloat = 14,
              radius: CGFloat = Theme.Radius.card,
              fill: Color = Theme.slate950,
              border: Color = Theme.borderSubtle) -> some View {
        modifier(CardStyle(padding: padding, radius: radius, fill: fill, border: border))
    }

    /// Card shell for content that draws its own rows edge to edge.
    func cardContainer(radius: CGFloat = Theme.Radius.card,
                       fill: Color = Theme.slate950,
                       border: Color = Theme.borderSubtle) -> some View {
        modifier(CardStyle(padding: 0, radius: radius, fill: fill, border: border))
    }
}

struct HairlineDivider: View {
    var color: Color = Theme.borderSubtle
    var body: some View {
        Rectangle().fill(color).frame(height: 1)
    }
}

// MARK: - Dot grid + gold feature card

/// The signature dot-grid texture: `radial-gradient(dot 1.4px)` on a 14px grid.
struct DotGrid: View {
    var step: CGFloat = 14
    var dotDiameter: CGFloat = 2.8
    var color: Color

    var body: some View {
        Canvas { context, size in
            var y: CGFloat = step / 2
            while y < size.height {
                var x: CGFloat = step / 2
                while x < size.width {
                    let rect = CGRect(x: x - dotDiameter / 2, y: y - dotDiameter / 2,
                                      width: dotDiameter, height: dotDiameter)
                    context.fill(Path(ellipseIn: rect), with: .color(color))
                    x += step
                }
                y += step
            }
        }
        .allowsHitTesting(false)
    }
}

/// Full-width gold card with ink text and the dot pattern.
struct GoldFeatureCard<Content: View>: View {
    var padding: EdgeInsets = EdgeInsets(top: 18, leading: 18, bottom: 16, trailing: 18)
    var radius: CGFloat = Theme.Radius.feature
    @ViewBuilder var content: Content

    var body: some View {
        content
            .padding(padding)
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(
                ZStack {
                    Theme.gold
                    DotGrid(color: Theme.slate950.opacity(0.12))
                }
            )
            .foregroundStyle(Theme.onAccent)
            .clipShape(RoundedRectangle(cornerRadius: radius, style: .continuous))
            .shadow(color: .black.opacity(0.5), radius: 12, y: 8)
    }
}

// MARK: - Monogram tile

/// Slate-800 tile with gold Geist Mono initials. The placeholder / loading
/// treatment for event logos, and the map pin glyph.
struct MonogramTile: View {
    let text: String
    var size: CGFloat = 48
    var radius: CGFloat = Theme.Radius.tile48
    var font: Font = .monoTile14
    var fill: Color = Theme.slate800
    var showsBorder = true
    /// Override on light surfaces — the default white@8% is invisible on gold.
    var borderColor: Color = Theme.borderSubtle

    var body: some View {
        Text(text)
            .font(font)
            .foregroundStyle(Theme.gold)
            .frame(width: size, height: size)
            .background(fill)
            .clipShape(RoundedRectangle(cornerRadius: radius, style: .continuous))
            .overlay(
                RoundedRectangle(cornerRadius: radius, style: .continuous)
                    .strokeBorder(showsBorder ? borderColor : .clear, lineWidth: 1)
            )
    }
}

// MARK: - Chips & pills

/// Selectable chip: pill, 12pt Medium. Selected = gold with ink text.
struct SelectChip: View {
    let label: String
    let selected: Bool
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            Text(label)
                .font(.body12Medium)
                .foregroundStyle(selected ? Theme.onAccent : Theme.textSecondary)
                .padding(.horizontal, 13)
                .padding(.vertical, 8)
                .background(Capsule().fill(selected ? Theme.gold : Theme.slate950))
                .overlay(Capsule().strokeBorder(selected ? Theme.gold : Theme.borderDefault, lineWidth: 1))
                .contentShape(Capsule())
        }
        .buttonStyle(PressableButtonStyle())
        .animation(Motion.fast, value: selected)
        .accessibilityAddTraits(selected ? .isSelected : [])
    }
}

/// Wrapping row of chips.
struct ChipFlow<Content: View>: View {
    var spacing: CGFloat = 7
    @ViewBuilder var content: Content

    var body: some View {
        FlowLayout(spacing: spacing) { content }
    }
}

/// Minimal wrapping layout for chip rows.
struct FlowLayout: Layout {
    var spacing: CGFloat = 7

    func sizeThatFits(proposal: ProposedViewSize, subviews: Subviews, cache: inout ()) -> CGSize {
        let width = proposal.width ?? .infinity
        var x: CGFloat = 0, y: CGFloat = 0, rowHeight: CGFloat = 0
        for view in subviews {
            let size = view.sizeThatFits(.unspecified)
            if x > 0, x + size.width > width {
                x = 0
                y += rowHeight + spacing
                rowHeight = 0
            }
            x += size.width + spacing
            rowHeight = max(rowHeight, size.height)
        }
        return CGSize(width: width == .infinity ? x : width, height: y + rowHeight)
    }

    func placeSubviews(in bounds: CGRect, proposal: ProposedViewSize, subviews: Subviews, cache: inout ()) {
        var x = bounds.minX, y = bounds.minY, rowHeight: CGFloat = 0
        for view in subviews {
            let size = view.sizeThatFits(.unspecified)
            if x > bounds.minX, x + size.width > bounds.maxX {
                x = bounds.minX
                y += rowHeight + spacing
                rowHeight = 0
            }
            view.place(at: CGPoint(x: x, y: y), proposal: ProposedViewSize(size))
            x += size.width + spacing
            rowHeight = max(rowHeight, size.height)
        }
    }
}

/// Age-group pill. `onGold` uses the ink-on-gold treatment from the hero card.
struct AgePill: View {
    let text: String
    var onGold = false

    var body: some View {
        Text(text)
            .font(.pill)
            .foregroundStyle(onGold ? Theme.onAccent : Theme.textSecondary)
            .padding(.horizontal, onGold ? 9 : 10)
            .padding(.vertical, 4)
            .background(Capsule().fill(onGold ? Theme.slate950.opacity(0.10) : Theme.slate900))
            .overlay(Capsule().strokeBorder(onGold ? Theme.slate950.opacity(0.14) : Theme.borderDefault, lineWidth: 1))
    }
}

/// "LIVE" badge on dashboard rows.
struct LiveBadge: View {
    var body: some View {
        Text("LIVE")
            .font(.monoBadge)
            .kerning(0.95)
            .foregroundStyle(Theme.gold)
            .padding(.horizontal, 9)
            .padding(.vertical, 4)
            .overlay(Capsule().strokeBorder(Theme.gold700, lineWidth: 1))
    }
}

// MARK: - Icon buttons

struct IconButtonLabel: View {
    let icon: Lucide
    var size: CGFloat = 40
    var radius: CGFloat = Theme.Radius.control
    var iconSize: CGFloat = 18
    var strokeWidth: CGFloat = 1.75
    var badge = false

    var body: some View {
        LucideIcon(icon, size: iconSize, strokeWidth: strokeWidth)
            .foregroundStyle(Theme.textSecondary)
            .frame(width: size, height: size)
            .background(RoundedRectangle(cornerRadius: radius, style: .continuous).fill(Theme.slate950))
            .overlay(RoundedRectangle(cornerRadius: radius, style: .continuous).strokeBorder(Theme.borderSubtle, lineWidth: 1))
            .overlay(alignment: .topTrailing) {
                if badge {
                    Circle()
                        .fill(Theme.gold)
                        .frame(width: 7, height: 7)
                        .shadow(color: Theme.gold.opacity(0.6), radius: 3)
                        .padding(8)
                }
            }
            .contentShape(RoundedRectangle(cornerRadius: radius, style: .continuous))
    }
}

struct IconButton: View {
    let icon: Lucide
    var size: CGFloat = 40
    var radius: CGFloat = Theme.Radius.control
    var iconSize: CGFloat = 18
    var strokeWidth: CGFloat = 1.75
    var badge = false
    var accessibilityLabel: String
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            IconButtonLabel(icon: icon, size: size, radius: radius, iconSize: iconSize,
                            strokeWidth: strokeWidth, badge: badge)
        }
        .buttonStyle(PressableButtonStyle())
        .accessibilityLabel(accessibilityLabel)
    }
}

/// 38×38 back button used by every pushed screen.
struct BackButton: View {
    @Environment(\.dismiss) private var dismiss
    var body: some View {
        IconButton(icon: .chevronLeft, size: 38, iconSize: 17, strokeWidth: 2,
                   accessibilityLabel: "Back") { dismiss() }
    }
}

// MARK: - Primary CTA

struct PrimaryGoldButton: View {
    let title: String
    var icon: Lucide? = nil
    var leadingIcon: Lucide? = nil
    var isBusy = false
    var padding: CGFloat = 14
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            HStack(spacing: 8) {
                if let leadingIcon {
                    LucideIcon(leadingIcon, size: 15, strokeWidth: 2)
                }
                Text(title).font(.buttonLabel)
                if let icon {
                    LucideIcon(icon, size: 15, strokeWidth: 2)
                }
            }
            .foregroundStyle(Theme.onAccent)
            .frame(maxWidth: .infinity)
            .padding(.vertical, padding)
            .background(RoundedRectangle(cornerRadius: Theme.Radius.button, style: .continuous).fill(Theme.gold))
            .opacity(isBusy ? 0.6 : 1)
            .contentShape(RoundedRectangle(cornerRadius: Theme.Radius.button, style: .continuous))
        }
        .buttonStyle(PressableButtonStyle(scale: 0.99))
        .disabled(isBusy)
        .animation(Motion.fast, value: isBusy)
    }
}

/// Slate-900 secondary button ("Done").
struct SecondaryButton: View {
    let title: String
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            Text(title)
                .font(.body14Medium)
                .foregroundStyle(Theme.textPrimary)
                .padding(.horizontal, 32)
                .padding(.vertical, 12)
                .background(RoundedRectangle(cornerRadius: Theme.Radius.input, style: .continuous).fill(Theme.slate900))
                .overlay(RoundedRectangle(cornerRadius: Theme.Radius.input, style: .continuous).strokeBorder(Theme.borderDefault, lineWidth: 1))
        }
        .buttonStyle(PressableButtonStyle())
    }
}

// MARK: - Rows

/// Icon · label · trailing. 13/16 padding as in the mock's card rows.
struct CardRow<Trailing: View>: View {
    var icon: Lucide?
    var iconSize: CGFloat = 17
    let label: String
    var labelFont: Font = .row
    var labelColor: Color = Theme.textPrimary
    @ViewBuilder var trailing: Trailing

    var body: some View {
        HStack(spacing: 12) {
            if let icon {
                LucideIcon(icon, size: iconSize)
                    .foregroundStyle(Theme.textTertiary)
            }
            Text(label)
                .font(labelFont)
                .foregroundStyle(labelColor)
                .lineLimit(1)
                .frame(maxWidth: .infinity, alignment: .leading)
            trailing
        }
        .padding(.horizontal, 16)
        .padding(.vertical, 13)
        .contentShape(Rectangle())
    }
}

extension CardRow where Trailing == Chevron {
    init(icon: Lucide?, label: String) {
        self.icon = icon
        self.label = label
        self.trailing = Chevron()
    }
}

struct Chevron: View {
    var color: Color = Theme.slate600
    var size: CGFloat = 15
    var body: some View {
        LucideIcon(.chevronRight, size: size, strokeWidth: 2)
            .foregroundStyle(color)
    }
}

/// A card row that lightens to slate-900 while pressed.
struct PressableRow<Content: View>: View {
    let action: () -> Void
    @ViewBuilder var content: Content

    var body: some View {
        Button(action: action) {
            RowSurface { content }
        }
        .buttonStyle(SurfaceButtonStyle(scale: 1))
    }
}

struct RowSurface<Content: View>: View {
    @Environment(\.isPressed) private var isPressed
    @ViewBuilder var content: Content
    var body: some View {
        content.background(isPressed ? Theme.slate900 : .clear)
    }
}

// MARK: - Switch

/// 44×26 pill switch: gold track when on, slate-700 off, white 20pt knob.
struct GoldSwitch: View {
    let isOn: Bool
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            ZStack(alignment: isOn ? .trailing : .leading) {
                Capsule().fill(isOn ? Theme.gold : Theme.slate700)
                Circle()
                    .fill(.white)
                    .frame(width: 20, height: 20)
                    .shadow(color: .black.opacity(0.4), radius: 1, y: 1)
                    .padding(3)
            }
            .frame(width: 44, height: 26)
            .animation(Motion.easeOut(0.18), value: isOn)
        }
        .buttonStyle(.plain)
        .accessibilityAddTraits(.isToggle)
        .accessibilityValue(isOn ? "On" : "Off")
    }
}

// MARK: - Form controls

/// Slate-950 input, default border, radius 11, gold focus ring.
struct FormTextField: View {
    let placeholder: String
    @Binding var text: String
    var keyboard: UIKeyboardType = .default
    var contentType: UITextContentType? = nil
    var capitalization: TextInputAutocapitalization = .sentences
    var isInvalid = false
    var focused: Bool = false

    var body: some View {
        TextField("", text: $text, prompt: Text(placeholder).foregroundColor(Theme.slate500))
            .font(.body14)
            .foregroundStyle(Theme.textPrimary)
            .keyboardType(keyboard)
            .textContentType(contentType)
            .textInputAutocapitalization(capitalization)
            .autocorrectionDisabled()
            .tint(Theme.gold)
            .padding(.horizontal, 14)
            .padding(.vertical, 13)
            .background(RoundedRectangle(cornerRadius: Theme.Radius.input, style: .continuous).fill(Theme.slate950))
            .overlay(
                RoundedRectangle(cornerRadius: Theme.Radius.input, style: .continuous)
                    .strokeBorder(isInvalid ? Theme.danger : (focused ? Theme.gold400 : Theme.borderDefault), lineWidth: 1)
            )
            .animation(Motion.fast, value: focused)
    }
}

/// Icon + text row that looks like an input (date and location pickers).
struct FormRowButton: View {
    let icon: Lucide
    let text: String
    var isPlaceholder = false
    var isInvalid = false
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            HStack(spacing: 10) {
                LucideIcon(icon, size: 15)
                    .foregroundStyle(Theme.slate400)
                Text(text)
                    .font(.body13)
                    .foregroundStyle(isPlaceholder ? Theme.slate500 : Theme.textPrimary)
                    .lineLimit(1)
                    .truncationMode(.tail)
                Spacer(minLength: 0)
            }
            .padding(.horizontal, 14)
            .padding(.vertical, 13)
            .background(RoundedRectangle(cornerRadius: Theme.Radius.input, style: .continuous).fill(Theme.slate950))
            .overlay(
                RoundedRectangle(cornerRadius: Theme.Radius.input, style: .continuous)
                    .strokeBorder(isInvalid ? Theme.danger : Theme.borderDefault, lineWidth: 1)
            )
            .contentShape(RoundedRectangle(cornerRadius: Theme.Radius.input, style: .continuous))
        }
        .buttonStyle(PressableButtonStyle())
    }
}

/// Dashed upload row. Filled: gold-700 border, primary text, gold check.
struct UploadRowLabel<Preview: View>: View {
    let icon: Lucide
    let label: String
    let filled: Bool
    var isInvalid = false
    @ViewBuilder var preview: Preview

    var body: some View {
        HStack(spacing: 12) {
            LucideIcon(icon, size: 17)
                .foregroundStyle(filled ? Theme.textPrimary : Theme.textTertiary)
            Text(label)
                .font(.body13_5)
                .foregroundStyle(filled ? Theme.textPrimary : Theme.textTertiary)
                .lineLimit(1)
                .truncationMode(.middle)
                .frame(maxWidth: .infinity, alignment: .leading)
            preview
            if filled {
                LucideIcon(.check, size: 16, strokeWidth: 2.25)
                    .foregroundStyle(Theme.gold)
            }
        }
        .padding(14)
        .background(RoundedRectangle(cornerRadius: Theme.Radius.button, style: .continuous).fill(Theme.slate950))
        .overlay(
            RoundedRectangle(cornerRadius: Theme.Radius.button, style: .continuous)
                .strokeBorder(style: StrokeStyle(lineWidth: 1, dash: [4, 3]))
                .foregroundStyle(isInvalid ? Theme.danger : (filled ? Theme.gold700 : Theme.borderStrong))
        )
        .contentShape(RoundedRectangle(cornerRadius: Theme.Radius.button, style: .continuous))
        .animation(Motion.fast, value: filled)
    }
}

extension UploadRowLabel where Preview == EmptyView {
    init(icon: Lucide, label: String, filled: Bool, isInvalid: Bool = false) {
        self.icon = icon
        self.label = label
        self.filled = filled
        self.isInvalid = isInvalid
        self.preview = EmptyView()
    }
}

// MARK: - Headers

/// Gold eyebrow over a Light 28pt title ending in a period, with trailing
/// controls bottom-aligned to the title.
struct ScreenHeader<Trailing: View>: View {
    let eyebrow: String
    let title: String
    @ViewBuilder var trailing: Trailing

    var body: some View {
        HStack(alignment: .bottom, spacing: 12) {
            VStack(alignment: .leading, spacing: 7) {
                Eyebrow(eyebrow)
                // Explicit line breaks become separate Texts so the 1.08
                // line-height of the mock can be matched (SwiftUI can't
                // tighten below a font's natural leading).
                VStack(alignment: .leading, spacing: -5) {
                    ForEach(Array(title.split(separator: "\n").enumerated()), id: \.offset) { _, line in
                        Text(String(line))
                            .font(.screenTitle)
                            .tracked(-0.03, 28)
                            .foregroundStyle(Theme.textPrimary)
                            .lineLimit(1)
                            .minimumScaleFactor(0.8)
                    }
                }
            }
            Spacer(minLength: 0)
            trailing
        }
        .padding(.horizontal, Theme.gutter)
        .padding(.top, 12)
        .padding(.bottom, 14)
    }
}

extension ScreenHeader where Trailing == EmptyView {
    init(eyebrow: String, title: String) {
        self.eyebrow = eyebrow
        self.title = title
        self.trailing = EmptyView()
    }
}

/// Back button beside a small eyebrow + Light 20pt title (dashboard style).
struct PushedHeader<Trailing: View>: View {
    let eyebrow: String
    let title: String
    @ViewBuilder var trailing: Trailing

    var body: some View {
        HStack(alignment: .center, spacing: 12) {
            BackButton()
            VStack(alignment: .leading, spacing: 2) {
                Eyebrow(eyebrow, size: 10)
                Text(title)
                    .font(.pushedTitle)
                    .tracked(-0.02, 20)
                    .foregroundStyle(Theme.textPrimary)
            }
            Spacer(minLength: 0)
            trailing
        }
        .padding(.horizontal, Theme.gutter)
        .padding(.top, 6)
        .padding(.bottom, 10)
    }
}

extension PushedHeader where Trailing == EmptyView {
    init(eyebrow: String, title: String) {
        self.eyebrow = eyebrow
        self.title = title
        self.trailing = EmptyView()
    }
}

// MARK: - Sheet chrome

struct DragHandle: View {
    var body: some View {
        Capsule()
            .fill(Theme.slate600)
            .frame(width: 38, height: 4)
            .frame(maxWidth: .infinity)
            .padding(.top, 10)
    }
}

// MARK: - Toast

struct ToastModifier: ViewModifier {
    @Binding var message: String?

    func body(content: Content) -> some View {
        content.overlay(alignment: .bottom) {
            if let message {
                Text(message)
                    .font(.body12_5)
                    .foregroundStyle(Theme.textPrimary)
                    .padding(.horizontal, 18)
                    .padding(.vertical, 10)
                    .background(Capsule().fill(Theme.slate800))
                    .overlay(Capsule().strokeBorder(Theme.borderDefault, lineWidth: 1))
                    .shadow(color: .black.opacity(0.55), radius: 18, y: 12)
                    .padding(.bottom, 24)
                    .transition(.opacity.combined(with: .offset(y: 24)))
                    .task {
                        try? await Task.sleep(for: .seconds(1.8))
                        withAnimation(Motion.normal) { self.message = nil }
                    }
            }
        }
        .animation(Motion.easeOut(0.2), value: message)
    }
}

extension View {
    /// Bottom-centre pill that clears itself after 1.8s.
    func toast(_ message: Binding<String?>) -> some View {
        modifier(ToastModifier(message: message))
    }
}

// MARK: - Loading

/// Gold-on-dark activity ring.
struct GoldSpinner: View {
    var size: CGFloat = 28
    @State private var rotation: Double = 0

    var body: some View {
        ZStack {
            Circle().stroke(Theme.borderDefault, lineWidth: 2.5)
            Circle()
                .trim(from: 0, to: 0.7)
                .stroke(Theme.gold, style: StrokeStyle(lineWidth: 2.5, lineCap: .round))
                .rotationEffect(.degrees(rotation))
        }
        .frame(width: size, height: size)
        .onAppear {
            withAnimation(.linear(duration: 1.1).repeatForever(autoreverses: false)) {
                rotation = 360
            }
        }
    }
}

// MARK: - Canvas background

extension View {
    /// Paints the ink canvas behind a screen, edge to edge.
    func canvas() -> some View {
        background(Theme.ink.ignoresSafeArea())
    }
}
