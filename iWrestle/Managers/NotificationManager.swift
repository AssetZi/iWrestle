//
//  NotificationManager.swift
//  iWrestle
//
//  Created by Brock Zacherl on 12/18/25.
//

import Foundation
import Observation
import UserNotifications
import UIKit
import CoreLocation
import BackgroundTasks
import os

@Observable
final class NotificationManager {
    typealias EventFetch = ([NSPredicate]) async throws -> [Event]

    var permissionGranted: Bool = false

    private let fetch: EventFetch
    /// Last refresh that produced a decision, so launch + first location fix
    /// + foregrounding in quick succession query CloudKit once, not three times.
    private var lastRefresh: Date?
    private var isRefreshing = false
    private static let refreshThrottle: TimeInterval = 15 * 60
    private let log = Logger(subsystem: "zacherlInvestmentsLLC.iWrestle", category: "WeeklyDigest")

    init(fetch: @escaping EventFetch) {
        self.fetch = fetch
        refreshAuthorizationStatus()
    }

    func requestPermission() async {
        do {
            let granted = try await UNUserNotificationCenter.current()
                .requestAuthorization(options: [.alert, .badge, .sound])
            permissionGranted = granted
        } catch {
            log.error("Notification authorization failed: \(error.localizedDescription)")
        }
    }

    func refreshAuthorizationStatus() {
        Task {
            let settings = await UNUserNotificationCenter.current().notificationSettings()
            permissionGranted = Self.isAuthorized(settings.authorizationStatus)
        }
    }

    func openAppSettings() {
        guard let url = URL(string: UIApplication.openSettingsURLString) else { return }
        if UIApplication.shared.canOpenURL(url) {
            UIApplication.shared.open(url, options: [:], completionHandler: nil)
        }
    }

    // MARK: - Weekly digest

    /// Recounts next week's nearby events and schedules, replaces, or
    /// withdraws the Monday notification. A fetch failure changes nothing.
    func refreshWeeklyDigest(location: CLLocation, now: Date = .now, force: Bool = false) async {
        if !force, let lastRefresh, now.timeIntervalSince(lastRefresh) < Self.refreshThrottle { return }
        // The first location fix and the return to foreground often land together.
        guard !isRefreshing else { return }
        isRefreshing = true
        defer { isRefreshing = false }

        let center = UNUserNotificationCenter.current()
        let settings = await center.notificationSettings()
        guard Self.isAuthorized(settings.authorizationStatus) else { return }

        guard let fireDate = WeeklyDigest.nextFireDate(after: now) else { return }
        let window = WeeklyDigest.window(firingAt: fireDate)
        let predicates = WeeklyDigest.predicates(location: location, window: window)

        let result: Result<Int, Error>
        do {
            result = .success(try await fetch(predicates).count)
        } catch {
            result = .failure(error)
        }

        switch WeeklyDigest.outcome(for: result, fireDate: fireDate) {
        case .schedule(let request):
            do {
                try await center.add(request)
                lastRefresh = now
                log.info("Scheduled weekly digest for \(fireDate): \(request.content.title)")
            } catch {
                log.error("Could not schedule weekly digest: \(error.localizedDescription)")
            }
        case .removePending:
            center.removePendingNotificationRequests(withIdentifiers: [WeeklyDigest.requestIdentifier])
            lastRefresh = now
            log.info("No events next week; weekly digest withdrawn")
        case .keepExisting:
            if case .failure(let error) = result {
                log.error("Weekly digest count failed; keeping existing: \(error.localizedDescription)")
            }
        }
    }

    /// Asks iOS to wake the app shortly before the next digest so its count
    /// is fresh even if the app is not opened. Replaces any earlier request.
    func submitBackgroundRefresh(now: Date = .now) {
        guard let fireDate = WeeklyDigest.nextFireDate(after: now) else { return }
        do {
            try BGTaskScheduler.shared.submit(WeeklyDigest.backgroundRefreshRequest(fireDate: fireDate))
        } catch {
            // Expected on the Simulator (unavailable) and when Background App Refresh is off.
            log.error("Could not submit background refresh: \(error.localizedDescription)")
        }
    }

    private static func isAuthorized(_ status: UNAuthorizationStatus) -> Bool {
        status == .authorized || status == .provisional
    }
}
