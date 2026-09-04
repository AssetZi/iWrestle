//
//  RootView.swift
//  iWrestle
//
//  Created by Brock Zacherl on 11/26/25.
//

import SwiftUI

enum AppTab: Hashable {
    case events, settings
}

struct RootView: View {
    @Environment(LocationManager.self) var locationManager
    @Environment(NotificationManager.self) var nm
    @State private var selectedTab: AppTab = .events
    @State private var homePath = NavigationPath()
    @State private var settingsPath = NavigationPath()

    /// Pushed screens cover the tab bar, as in the design.
    private var tabBarHidden: Bool {
        switch selectedTab {
        case .events: return !homePath.isEmpty
        case .settings: return !settingsPath.isEmpty
        }
    }

    var body: some View {
        ZStack {
            // Both tabs stay alive so switching never refetches or loses scroll.
            HomeView(path: $homePath)
                .opacity(selectedTab == .events ? 1 : 0)
                .allowsHitTesting(selectedTab == .events)
                .accessibilityHidden(selectedTab != .events)

            SettingsView(path: $settingsPath)
                .opacity(selectedTab == .settings ? 1 : 0)
                .allowsHitTesting(selectedTab == .settings)
                .accessibilityHidden(selectedTab != .settings)
        }
        .canvas()
        // The bar overlays the content so lists scroll under the frosted
        // material; tab roots inset themselves by `tabBarInset`.
        .overlay(alignment: .bottom) {
            if !tabBarHidden {
                AppTabBar(selection: $selectedTab)
                    .transition(.move(edge: .bottom).combined(with: .opacity))
            }
        }
        .environment(\.tabBarInset, tabBarHidden ? 0 : AppTabBar.contentHeight)
        .animation(Motion.normal, value: tabBarHidden)
        .onAppear(perform: locationManager.requestUserLocaiton)
        .task {
            nm.requestPermission()
            guard let loc = locationManager.userLocation else { return }
            nm.scheduleWeeklyNotification(userLocation: loc)
        }
    }
}

/// Frosted two-tab bar: blur over ink at 78%, hairline top border, gold
/// active icon + label, tertiary inactive.
struct AppTabBar: View {
    @Binding var selection: AppTab

    /// Height of the bar above the device's bottom safe area.
    static let contentHeight: CGFloat = 60

    var body: some View {
        HStack(spacing: 0) {
            tab(.events, icon: .calendar, label: "Events")
            tab(.settings, icon: .settings, label: "Settings")
        }
        .padding(.horizontal, 56)
        .frame(maxWidth: .infinity)
        .frame(height: Self.contentHeight)
        .background {
            ZStack {
                Rectangle().fill(.ultraThinMaterial)
                Theme.tabBarFill
            }
            .ignoresSafeArea(edges: .bottom)
        }
        .overlay(alignment: .top) { HairlineDivider() }
    }

    private func tab(_ tab: AppTab, icon: Lucide, label: String) -> some View {
        let active = selection == tab
        return Button {
            withAnimation(Motion.fast) { selection = tab }
        } label: {
            VStack(spacing: 4) {
                LucideIcon(icon, size: 21)
                Text(label)
                    .font(.tabLabel)
                    .kerning(0.4)
            }
            .foregroundStyle(active ? Theme.gold : Theme.textTertiary)
            .frame(maxWidth: .infinity)
            .contentShape(Rectangle())
        }
        .buttonStyle(.plain)
        .accessibilityLabel(label)
        .accessibilityAddTraits(active ? [.isButton, .isSelected] : .isButton)
    }
}

private struct TabBarInsetKey: EnvironmentKey {
    static let defaultValue: CGFloat = 0
}

extension EnvironmentValues {
    /// Extra bottom inset a tab root applies so its content clears the bar.
    var tabBarInset: CGFloat {
        get { self[TabBarInsetKey.self] }
        set { self[TabBarInsetKey.self] = newValue }
    }
}
