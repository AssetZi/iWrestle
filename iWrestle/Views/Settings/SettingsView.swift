//
//  SettingsView.swift
//  iWrestle
//
//  Created by Brock Zacherl on 11/26/25.
//

import SwiftUI

struct SettingsView: View {
    @Environment(CloudKitManager.self) var ck
    @Binding var path: NavigationPath
    @Environment(\.tabBarInset) private var tabBarInset
    @State private var showAddSheet: Bool = false
    @State private var userEvents: [Event] = []
    @State private var loadedUserEvents = false

    private var appVersion: String {
        Bundle.main.infoDictionary?["CFBundleShortVersionString"] as? String ?? "1.0"
    }

    var body: some View {
        NavigationStack(path: $path) {
            VStack(spacing: 0) {
                ScreenHeader(eyebrow: "Account", title: "Settings.")

                ScrollView {
                    VStack(alignment: .leading, spacing: 18) {
                        organizerCard.entrance()
                        yourEvents.entrance(delay: 0.04)
                        SupportView().entrance(delay: 0.08)
                        footer.entrance(delay: 0.12)
                    }
                    .padding(.horizontal, Theme.gutter)
                    .padding(.top, 2)
                    .padding(.bottom, 24)
                }
                .scrollIndicators(.hidden)
            }
            .safeAreaPadding(.bottom, tabBarInset)
            .canvas()
            .toolbar(.hidden, for: .navigationBar)
            .navigationDestination(for: AppRoute.self) { route in
                switch route {
                case .dashboard:
                    UserEventsView(userEvents: $userEvents)
                case .editEvent(let id):
                    if let index = userEvents.firstIndex(where: { $0.id == id }) {
                        UserEventDetailView(ogEvent: $userEvents[index], event: userEvents[index])
                    }
                case .eventDetail(let event):
                    EventDetailView(event: event)
                case .flyer(let url):
                    PDFQuickLookView(url: url)
                }
            }
            .sheet(isPresented: $showAddSheet) {
                AddEventScreen(userEvents: $userEvents)
            }
            .task { await loadUserEventCount() }
        }
    }

    // MARK: - Sections

    private var organizerCard: some View {
        GoldFeatureCard(padding: EdgeInsets(top: 18, leading: 18, bottom: 18, trailing: 18)) {
            VStack(alignment: .leading, spacing: 10) {
                Eyebrow("For organizers", color: Theme.inkOnGold62, size: 10, weight: .semibold)
                Text("Put your event in front of local wrestling families.")
                    .font(.featureTitle)
                    .tracked(-0.02, 19)
                    .lineSpacing(3)
                    .frame(maxWidth: 280, alignment: .leading)
                    .fixedSize(horizontal: false, vertical: true)
                Text("Launch pricing — \(launchPriceLabel) per event. Price grows with the app. Capped at $50, always.")
                    .font(.caption11_5)
                    .foregroundStyle(Theme.inkOnGold66)
                    .fixedSize(horizontal: false, vertical: true)
                Button {
                    showAddSheet = true
                } label: {
                    HStack(spacing: 8) {
                        LucideIcon(.plus, size: 14, strokeWidth: 2)
                        Text("Add event · \(launchPriceLabel)")
                            .font(.body13_5Medium)
                    }
                    .foregroundStyle(Theme.gold)
                    .padding(.horizontal, 18)
                    .padding(.vertical, 10)
                    .background(RoundedRectangle(cornerRadius: 10, style: .continuous).fill(Theme.slate950))
                }
                .buttonStyle(PressableButtonStyle())
                .padding(.top, 2)
            }
        }
    }

    private var yourEvents: some View {
        VStack(alignment: .leading, spacing: 9) {
            SectionLabel("Your events")
            NavigationLink(value: AppRoute.dashboard) {
                RowSurface {
                    CardRow(icon: .trophy, label: "Events dashboard") {
                        if loadedUserEvents {
                            Text(String(format: "%02d", userEvents.count))
                                .font(.distance)
                                .foregroundStyle(Theme.gold)
                        }
                        Chevron()
                    }
                    .padding(.vertical, 1)
                }
            }
            .buttonStyle(SurfaceButtonStyle(scale: 1))
            .cardContainer()
        }
    }

    private var footer: some View {
        HStack(spacing: 8) {
            Image("iWrestleNoText")
                .resizable()
                .scaledToFit()
                .frame(height: 22)
            Text("iWrestle · v\(appVersion)")
                .font(.monoCaption)
                .foregroundStyle(Theme.textTertiary)
        }
        .opacity(0.5)
        .frame(maxWidth: .infinity)
        .padding(.top, 10)
    }

    // MARK: - Data

    /// Populates the dashboard count once; the dashboard reuses the binding.
    private func loadUserEventCount() async {
        guard !loadedUserEvents else { return }
        #if DEBUG
        if MockEvents.isEnabled, userEvents.isEmpty {
            userEvents = MockEvents.mine
            loadedUserEvents = true
            return
        }
        #endif
        if userEvents.isEmpty, let events = try? await ck.fetchUserEvents() {
            userEvents = events
        }
        loadedUserEvents = true
    }
}
