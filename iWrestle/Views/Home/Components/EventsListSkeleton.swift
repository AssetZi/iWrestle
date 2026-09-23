//
//  EventsListSkeleton.swift
//  iWrestle
//
//  Placeholder shapes of the home feed shown while events load. Uses the
//  same outer layout as EventsListView so the real cards fade in over it
//  without a jump.
//

import SwiftUI

struct EventsListSkeleton: View {
    var body: some View {
        ScrollView {
            LazyVStack(alignment: .leading, spacing: 18) {
                hero
                VStack(alignment: .leading, spacing: 9) {
                    Bar(width: 64, height: 10, color: Theme.slate800)
                        .padding(.vertical, 2)
                    ForEach(0..<4, id: \.self) { _ in cell }
                }
            }
            .padding(.horizontal, Theme.gutter)
            .padding(.top, 6)
            .padding(.bottom, 24)
            .shimmer()
        }
        .scrollIndicators(.hidden)
        .scrollDisabled(true)
        .allowsHitTesting(false)
        .accessibilityElement(children: .ignore)
        .accessibilityLabel("Loading events")
    }

    private var hero: some View {
        let fill = Theme.gold.opacity(0.18)
        return VStack(alignment: .leading, spacing: 12) {
            HStack(alignment: .top, spacing: 12) {
                VStack(alignment: .leading, spacing: 12) {
                    Bar(width: 90, height: 9, color: fill)
                    Bar(fraction: 0.85, height: 20, color: fill)
                    Bar(fraction: 0.55, height: 20, color: fill)
                }
                .frame(maxWidth: .infinity, alignment: .leading)
                RoundedRectangle(cornerRadius: Theme.Radius.tile44, style: .continuous)
                    .fill(fill)
                    .frame(width: 44, height: 44)
            }
            Bar(fraction: 0.6, height: 10, color: fill)
            HStack(spacing: 6) {
                ForEach(0..<3, id: \.self) { _ in
                    Capsule().fill(fill).frame(width: 40, height: 20)
                }
            }
        }
        .padding(EdgeInsets(top: 18, leading: 18, bottom: 16, trailing: 18))
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(Theme.gold.opacity(0.10))
        .clipShape(RoundedRectangle(cornerRadius: Theme.Radius.feature, style: .continuous))
    }

    private var cell: some View {
        HStack(spacing: 13) {
            RoundedRectangle(cornerRadius: Theme.Radius.tile48, style: .continuous)
                .fill(Theme.slate800)
                .frame(width: 48, height: 48)
            VStack(alignment: .leading, spacing: 12) {
                Bar(fraction: 0.7, height: 11, color: Theme.slate800)
                Bar(fraction: 0.5, height: 9, color: Theme.slate900)
                Bar(fraction: 0.35, height: 8, color: Theme.slate900)
            }
            .frame(maxWidth: .infinity, alignment: .leading)
            Bar(width: 34, height: 9, color: Theme.slate800)
        }
        .padding(.horizontal, 14)
        .padding(.vertical, 13)
        .background(Theme.slate950)
        .clipShape(RoundedRectangle(cornerRadius: Theme.Radius.card, style: .continuous))
        .overlay(
            RoundedRectangle(cornerRadius: Theme.Radius.card, style: .continuous)
                .strokeBorder(Theme.borderSubtle, lineWidth: 1)
        )
    }
}

/// A rounded placeholder bar, either a fixed width or a fraction of the
/// space it is offered.
private struct Bar: View {
    var width: CGFloat? = nil
    var fraction: CGFloat? = nil
    let height: CGFloat
    let color: Color

    var body: some View {
        let shape = RoundedRectangle(cornerRadius: height / 2, style: .continuous).fill(color)
        if let fraction {
            GeometryReader { geo in
                shape.frame(width: geo.size.width * fraction)
            }
            .frame(height: height)
        } else {
            shape.frame(width: width, height: height)
        }
    }
}

// MARK: - Shimmer

/// A faint light that sweeps left to right across the content's shapes,
/// then rests briefly. Static under Reduce Motion.
private struct Shimmer: ViewModifier {
    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    private let sweep: Double = 1.4
    private let rest: Double = 0.4

    func body(content: Content) -> some View {
        if reduceMotion {
            content
        } else {
            content.overlay {
                TimelineView(.animation) { timeline in
                    let t = timeline.date.timeIntervalSinceReferenceDate
                        .truncatingRemainder(dividingBy: sweep + rest)
                    let progress = min(t / sweep, 1)
                    GeometryReader { geo in
                        let band = geo.size.width * 0.6
                        LinearGradient(
                            colors: [.clear, .white.opacity(0.06), .clear],
                            startPoint: .leading, endPoint: .trailing
                        )
                        .frame(width: band)
                        .rotationEffect(.degrees(12))
                        .offset(x: -band + (geo.size.width + band) * progress)
                        .frame(maxHeight: .infinity)
                    }
                }
                .mask(content)
            }
        }
    }
}

private extension View {
    func shimmer() -> some View { modifier(Shimmer()) }
}

#Preview {
    EventsListSkeleton()
        .background(Theme.ink)
}
