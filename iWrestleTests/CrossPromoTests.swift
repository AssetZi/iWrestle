//
//  CrossPromoTests.swift
//  iWrestleTests
//
//  The cross-promo banner picks one app per launch. These pin the rotation,
//  the two-week dismissal and the no-repeat tagline rule.
//

import XCTest
@testable import iWrestle

final class CrossPromoTests: XCTestCase {
    private var defaults: UserDefaults!
    private let suite = "CrossPromoTests"

    private let apps = [
        PromotedApp(id: "1", name: "One", taglines: ["a", "b", "c"]),
        PromotedApp(id: "2", name: "Two", taglines: ["only"]),
        PromotedApp(id: "3", name: "Three", taglines: ["x", "y"]),
    ]

    override func setUp() {
        super.setUp()
        defaults = UserDefaults(suiteName: suite)
        defaults.removePersistentDomain(forName: suite)
    }

    override func tearDown() {
        defaults.removePersistentDomain(forName: suite)
        super.tearDown()
    }

    private func launch(_ apps: [PromotedApp]? = nil, now: Date = .now) -> CrossPromo {
        CrossPromo(apps: apps ?? self.apps, defaults: defaults, now: now, fetchIcon: false)
    }

    func testRotatesOneAppPerLaunchAndWraps() {
        let shown = (0..<4).map { _ in launch().current?.app.id }
        XCTAssertEqual(shown, ["1", "2", "3", "1"])
    }

    func testWeightRepeatsAnAppInTheCycle() {
        var weighted = apps
        weighted[0].weight = 2
        let shown = (0..<4).map { _ in launch(weighted).current?.app.id }
        XCTAssertEqual(shown, ["1", "1", "2", "3"])
    }

    func testDismissedAppSitsOutForTwoWeeks() {
        let start = Date()
        let first = launch(now: start)
        XCTAssertEqual(first.current?.app.id, "1")
        first.dismiss()
        XCTAssertNil(first.current)

        let later = (0..<3).map { _ in launch(now: start.addingTimeInterval(60)).current?.app.id }
        XCTAssertFalse(later.contains("1"))

        let afterTwoWeeks = start.addingTimeInterval(CrossPromo.dismissalPeriod + 1)
        let ids = (0..<3).map { _ in launch(now: afterTwoWeeks).current?.app.id }
        XCTAssertTrue(ids.contains("1"))
    }

    func testNothingShowsWhenEveryAppIsDismissed() {
        for _ in apps { launch().dismiss() }
        XCTAssertNil(launch().current)
    }

    func testTaglineNeverRepeatsBackToBack() {
        let one = [apps[0]]
        var previous: String?
        for _ in 0..<20 {
            let tagline = launch(one).current?.tagline
            XCTAssertNotNil(tagline)
            XCTAssertNotEqual(tagline, previous)
            previous = tagline
        }
    }

    func testSingleTaglineAppStillShows() {
        let two = [apps[1]]
        XCTAssertEqual(launch(two).current?.tagline, "only")
        XCTAssertEqual(launch(two).current?.tagline, "only")
    }
}
