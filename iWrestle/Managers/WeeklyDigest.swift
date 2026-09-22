//
//  WeeklyDigest.swift
//  iWrestle
//
//  The Monday-morning "N Events in your area this Week!" notification,
//  as pure functions so the date math and zero/failure rules are testable.
//  NotificationManager does the I/O; this decides what to schedule.
//

import Foundation
import CoreLocation
import UserNotifications
import BackgroundTasks

nonisolated enum WeeklyDigest {
    static let requestIdentifier = "weekly-events-update"
    /// Must match BGTaskSchedulerPermittedIdentifiers in Info.plist.
    static let backgroundTaskIdentifier = "zacherlInvestmentsLLC.iWrestle.weeklyEvents"
    static let radiusMiles: Double = 200
    /// Monday 9:00 local time.
    static let fireComponents = DateComponents(hour: 9, minute: 0, weekday: 2)
    /// How long before delivery the background refresh may run (Sunday ~6pm).
    static let refreshLeadTime: TimeInterval = 15 * 60 * 60

    /// The next Monday 9:00 strictly after `now`.
    static func nextFireDate(after now: Date, calendar: Calendar = .current) -> Date? {
        calendar.nextDate(after: now, matching: fireComponents, matchingPolicy: .nextTime)
    }

    /// Monday 00:00 through the end of Sunday for the week the notification
    /// announces. Not `dateInterval(of: .weekOfYear)`: US calendars start the
    /// week on Sunday, which would count the day before delivery.
    static func window(firingAt fireDate: Date, calendar: Calendar = .current) -> DateInterval {
        let start = calendar.startOfDay(for: fireDate)
        let end = calendar.date(byAdding: .day, value: 7, to: start) ?? start.addingTimeInterval(7 * 86_400)
        return DateInterval(start: start, end: end)
    }

    /// Same predicate formats as `EventFilters.predicates(userLocation:)`.
    static func predicates(location: CLLocation, window: DateInterval) -> [NSPredicate] {
        [
            NSPredicate(
                format: "distanceToLocation:fromLocation:(location, %@) < %f",
                location,
                radiusMiles.milesToMeters
            ),
            NSPredicate(
                format: "date >= %@ AND date < %@",
                window.start as CVarArg,
                window.end as CVarArg
            ),
        ]
    }

    static func title(count: Int) -> String {
        "\(count) \(count == 1 ? "Event" : "Events") in your area this Week!"
    }

    /// Nil when there is nothing to announce: a week with no events sends nothing.
    static func request(count: Int, fireDate: Date, calendar: Calendar = .current) -> UNNotificationRequest? {
        guard count > 0 else { return nil }

        let content = UNMutableNotificationContent()
        content.title = title(count: count)
        content.body = "Check them out today!"
        content.sound = .default

        var components = calendar.dateComponents([.year, .month, .day, .hour, .minute], from: fireDate)
        components.calendar = calendar
        components.timeZone = calendar.timeZone
        var trigger: UNNotificationTrigger = UNCalendarNotificationTrigger(dateMatching: components, repeats: false)

        #if DEBUG
        // Set IWRESTLE_DIGEST_DEBUG_SECONDS in the scheme to see the banner quickly.
        if let raw = ProcessInfo.processInfo.environment["IWRESTLE_DIGEST_DEBUG_SECONDS"],
           let seconds = TimeInterval(raw), seconds > 0 {
            trigger = UNTimeIntervalNotificationTrigger(timeInterval: seconds, repeats: false)
        }
        #endif

        return UNNotificationRequest(identifier: requestIdentifier, content: content, trigger: trigger)
    }

    static func backgroundRefreshRequest(fireDate: Date) -> BGAppRefreshTaskRequest {
        let request = BGAppRefreshTaskRequest(identifier: backgroundTaskIdentifier)
        request.earliestBeginDate = fireDate.addingTimeInterval(-refreshLeadTime)
        return request
    }

    enum Outcome: Equatable {
        /// Add (or replace, same identifier) the pending digest.
        case schedule(UNNotificationRequest)
        /// No events this week: withdraw only the digest.
        case removePending
        /// The count could not be computed: leave whatever is pending alone.
        case keepExisting
    }

    static func outcome(for result: Result<Int, Error>, fireDate: Date, calendar: Calendar = .current) -> Outcome {
        switch result {
        case .failure:
            return .keepExisting
        case .success(let count):
            guard let request = request(count: count, fireDate: fireDate, calendar: calendar) else {
                return .removePending
            }
            return .schedule(request)
        }
    }
}
