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

    /// A launch the user sees: the scene becomes active.
    private func launch(_ apps: [PromotedApp]? = nil, now: Date = .now) -> CrossPromo {
        let promo = backgroundLaunch(apps, now: now)
        promo.activate()
        return promo
    }

    /// A launch the user never sees, such as the Sunday app refresh.
    private func backgroundLaunch(_ apps: [PromotedApp]? = nil, now: Date = .now) -> CrossPromo {
        CrossPromo(apps: apps ?? self.apps, defaults: defaults, now: { now }, fetchIcon: false)
    }

    func testBackgroundLaunchesDoNotAdvanceTheRotation() {
        XCTAssertEqual(launch().current?.app.id, "1")
        _ = backgroundLaunch()
        _ = backgroundLaunch()
        XCTAssertEqual(launch().current?.app.id, "2")
    }

    /// A process started in the background just before a dismissal expires,
    /// then opened just after, must judge the dismissal by the time it opens.
    func testDismissalIsJudgedWhenTheAppOpensNotWhenItLaunched() {
        var clock = Date(timeIntervalSince1970: 1_000_000)
        let one = [apps[0]]
        let first = CrossPromo(apps: one, defaults: defaults, now: { clock }, fetchIcon: false)
        first.activate()
        first.dismiss()

        clock.addTimeInterval(CrossPromo.dismissalPeriod - 60)
        let promo = CrossPromo(apps: one, defaults: defaults, now: { clock }, fetchIcon: false)
        clock.addTimeInterval(120)
        promo.activate()

        XCTAssertEqual(promo.current?.app.id, "1")
    }

    func testNothingIsPickedUntilTheAppIsActive() {
        XCTAssertNil(backgroundLaunch().current)
    }

    func testBecomingActiveAgainKeepsTheSessionsPick() {
        let promo = launch()
        promo.activate()
        XCTAssertEqual(promo.current?.app.id, "1")
        XCTAssertEqual(launch().current?.app.id, "2")
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

    /// Matlas, Weight Wingman and Fantasy Wrestling, matching the campaign
    /// links in App Store Connect. PinPoint Recruiting is not promoted.
    func testCatalogPromotesTheThreeTrackedApps() {
        XCTAssertEqual(PromotedApp.catalog.map(\.id), ["6810665499", "6740700573", "6504050060"])
    }

    /// These are the `ct=` values App Analytics groups installs by; renaming
    /// one starts a new row there.
    func testCampaignTokensPerPlacement() {
        XCTAssertEqual(PromoCampaign.allCases.map(\.rawValue),
                       ["iWrestle-list", "iWrestle-detail", "iWrestle-empty", "iWrestle-settings"])
        XCTAssertEqual(AppLinks.appStoreProviderToken, "125547798")
    }
}
