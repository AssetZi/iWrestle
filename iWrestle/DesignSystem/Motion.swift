//
//  Motion.swift
//  iWrestle
//
//  Calm and precise: no bounce. Entrances fade + rise with the handoff's
//  ease-out curve; interaction feedback is quick.
//

import SwiftUI

enum Motion {
    /// `cubic-bezier(0.16, 1, 0.3, 1)` — the handoff's `--ease-out`.
    static func easeOut(_ duration: Double = 0.22) -> Animation {
        .timingCurve(0.16, 1, 0.3, 1, duration: duration)
    }
    /// Interaction feedback, 120ms.
    static let fast: Animation = .easeOut(duration: 0.12)
    static let normal: Animation = easeOut(0.22)
    static let sheet: Animation = easeOut(0.26)
}

/// Fade in over an 8pt rise, no bounce.
struct EntranceModifier: ViewModifier {
    let delay: Double
    @State private var shown = false

    func body(content: Content) -> some View {
        content
            .opacity(shown ? 1 : 0)
            .offset(y: shown ? 0 : 8)
            .onAppear {
                withAnimation(Motion.easeOut(0.22).delay(delay)) { shown = true }
            }
    }
}

/// Press = subtle scale-down. Surfaces that want to lighten one slate step
/// on press read `isPressed` via `PressStateButtonStyle` instead.
struct PressableButtonStyle: ButtonStyle {
    var scale: CGFloat = 0.98

    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .scaleEffect(configuration.isPressed ? scale : 1)
            .animation(Motion.fast, value: configuration.isPressed)
    }
}

/// Exposes the pressed state to the label so cards can swap their surface
/// colour (slate-950 → slate-900) while scaling 0.99.
struct SurfaceButtonStyle: ButtonStyle {
    var scale: CGFloat = 0.99

    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .environment(\.isPressed, configuration.isPressed)
            .scaleEffect(configuration.isPressed ? scale : 1)
            .animation(Motion.fast, value: configuration.isPressed)
    }
}

private struct IsPressedKey: EnvironmentKey {
    static let defaultValue = false
}

extension EnvironmentValues {
    var isPressed: Bool {
        get { self[IsPressedKey.self] }
        set { self[IsPressedKey.self] = newValue }
    }
}

extension View {
    func entrance(delay: Double = 0) -> some View { modifier(EntranceModifier(delay: delay)) }
}

// MARK: - Swipe back on screens with a hidden navigation bar

/// Restores the interactive edge-swipe-back gesture on screens that hide
/// the system navigation bar (which normally disables it).
struct SwipeBackEnabler: UIViewControllerRepresentable {
    private final class Controller: UIViewController, UIGestureRecognizerDelegate {
        override func didMove(toParent parent: UIViewController?) {
            super.didMove(toParent: parent)
            navigationController?.interactivePopGestureRecognizer?.delegate = self
        }

        func gestureRecognizerShouldBegin(_ gestureRecognizer: UIGestureRecognizer) -> Bool {
            (navigationController?.viewControllers.count ?? 0) > 1
        }
    }

    func makeUIViewController(context: Context) -> UIViewController { Controller() }
    func updateUIViewController(_ uiViewController: UIViewController, context: Context) {}
}

extension View {
    /// Re-enables swipe-from-left-edge to go back on pushed screens that draw
    /// their own top bar with the system navigation bar hidden.
    func enableSwipeBack() -> some View {
        background(SwipeBackEnabler())
    }
}
