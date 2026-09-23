//
//  WeeklyDigestTests.swift
//  iWrestleTests
//
//  The Monday notification used to count a single Sunday (next week's
//  start plus one day) and said "0 Events" nearly every week. These pin
//  the Monday-through-Sunday window and the zero/failure rules.
//

import XCTest
import CoreLocation
import UserNotifications
import BackgroundTasks
@testable import iWrestle

final class WeeklyDigestTests: XCTestCase {

    /// US-style calendar: weeks start Sunday, which is what broke the old math.
    private let calendar: Calendar = {
        var calendar = Calendar(identifier: .gregorian)
        calendar.firstWeekday = 1
        calendar.timeZone = TimeZone(identifier: "America/New_York")!
        return calendar
    }()

    private func date(_ year: Int, _ month: Int, _ day: Int, _ hour: Int = 0, _ minute: Int = 0) -> Date {
        calendar.date(from: DateComponents(year: year, month: month, day: day, hour: hour, minute: minute))!
    }

    private struct Boom: Error {}

    // 2026-09-23 is a Wednesday; 2026-09-28 is the following Monday.

    func testNextFireDateIsTheFollowingMondayAtNine() {
        XCTAssertEqual(WeeklyDigest.nextFireDate(after: date(2026, 9, 23, 14), calendar: calendar),
                       date(2026, 9, 28, 9))
        XCTAssertEqual(WeeklyDigest.nextFireDate(after: date(2026, 9, 28, 8, 59), calendar: calendar),
                       date(2026, 9, 28, 9))
        XCTAssertEqual(WeeklyDigest.nextFireDate(after: date(2026, 9, 28, 9), calendar: calendar),
                       date(2026, 10, 5, 9))
    }

    func testWindowRunsMondayThroughSunday() {
        let window = WeeklyDigest.window(firingAt: date(2026, 9, 28, 9), calendar: calendar)
        XCTAssertEqual(window.start, date(2026, 9, 28))
        XCTAssertEqual(window.end, date(2026, 10, 5))
        XCTAssertTrue(window.contains(date(2026, 10, 4, 23)))    // Sunday night
        XCTAssertFalse(window.contains(date(2026, 9, 27, 12)))   // the Sunday before delivery
    }

    func testDatePredicateMatchesOnlyTheAnnouncedWeek() {
        let window = WeeklyDigest.window(firingAt: date(2026, 9, 28, 9), calendar: calendar)
        let predicates = WeeklyDigest.predicates(location: CLLocation(latitude: 41.2, longitude: -79.4), window: window)
        XCTAssertEqual(predicates.count, 2)

        let datePredicate = predicates[1]
        XCTAssertTrue(datePredicate.evaluate(with: ["date": date(2026, 9, 30, 10)]))   // Wednesday
        XCTAssertTrue(datePredicate.evaluate(with: ["date": date(2026, 10, 3, 8)]))    // Saturday
        XCTAssertFalse(datePredicate.evaluate(with: ["date": date(2026, 9, 27, 10)]))  // prior Sunday
        XCTAssertFalse(datePredicate.evaluate(with: ["date": date(2026, 10, 5)]))      // next Monday
    }

    func testTitleText() {
        XCTAssertEqual(WeeklyDigest.title(count: 7), "7 Events in your area this Week!")
        XCTAssertEqual(WeeklyDigest.title(count: 1), "1 Event in your area this Week!")
    }

    func testScheduledRequestFiresOnceAtTheAnnouncedMonday() throws {
        let fireDate = date(2026, 9, 28, 9)
        let request = try XCTUnwrap(WeeklyDigest.request(count: 4, fireDate: fireDate, calendar: calendar))
        XCTAssertEqual(request.identifier, WeeklyDigest.requestIdentifier)
        XCTAssertEqual(request.content.title, "4 Events in your area this Week!")

        let trigger = try XCTUnwrap(request.trigger as? UNCalendarNotificationTrigger)
        XCTAssertFalse(trigger.repeats)
        XCTAssertEqual(calendar.date(from: trigger.dateComponents), fireDate)
    }

    func testZeroEventsWithdrawsTheDigest() {
        XCTAssertNil(WeeklyDigest.request(count: 0, fireDate: date(2026, 9, 28, 9), calendar: calendar))
        XCTAssertEqual(WeeklyDigest.outcome(for: .success(0), fireDate: date(2026, 9, 28, 9), calendar: calendar),
                       .removePending)
    }

    func testFetchFailureKeepsTheExistingDigest() {
        XCTAssertEqual(WeeklyDigest.outcome(for: .failure(Boom()), fireDate: date(2026, 9, 28, 9), calendar: calendar),
                       .keepExisting)
    }

    func testBackgroundRefreshIsRequestedTheEveningBefore() {
        let request = WeeklyDigest.backgroundRefreshRequest(fireDate: date(2026, 9, 28, 9))
        XCTAssertEqual(request.identifier, "zacherlInvestmentsLLC.iWrestle.weeklyEvents")
        XCTAssertEqual(request.earliestBeginDate, date(2026, 9, 27, 18))
    }
}
