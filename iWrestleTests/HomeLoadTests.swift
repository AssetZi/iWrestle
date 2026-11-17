//
//  HomeLoadTests.swift
//  iWrestleTests
//
//  The home feed's loads. A load the view replaced (say, on a new location
//  fix) must not show its result, and a real error still reads as empty.
//

import XCTest
import CloudKit
import CoreLocation
@testable import iWrestle

/// A load that waits until the test lets it finish.
@MainActor
private final class Gate {
    private var continuation: CheckedContinuation<Void, Never>?
    private var opened = false

    nonisolated deinit {}

    func wait() async {
        if opened { return }
        await withCheckedContinuation { continuation = $0 }
    }

    func open() {
        opened = true
        continuation?.resume()
        continuation = nil
    }
}

@MainActor
final class HomeLoadTests: XCTestCase {
    private let home = CLLocation(latitude: 41.2, longitude: -79.4)

    private func isNoData(_ state: HomeViewState) -> Bool {
        if case .error(.noData) = state { return true }
        return false
    }

    // MARK: - LatestLoad

    func testASupersededLoadIsDroppedEvenWhenItFinishesLast() async {
        let loads = LatestLoad<String>()
        let first = Gate(), second = Gate()
        var shown: [String] = []

        let a = loads.start({ await first.wait(); return "old location" }) { shown.append($0) }
        let b = loads.start({ await second.wait(); return "new location" }) { shown.append($0) }
        second.open(); await b.value
        first.open(); await a.value

        XCTAssertEqual(shown, ["new location"])
    }

    func testASupersededLoadIsDroppedWhenItFinishesFirst() async {
        let loads = LatestLoad<String>()
        let first = Gate(), second = Gate()
        var shown: [String] = []

        let a = loads.start({ await first.wait(); return "old location" }) { shown.append($0) }
        let b = loads.start({ await second.wait(); return "new location" }) { shown.append($0) }
        first.open(); await a.value
        second.open(); await b.value

        XCTAssertEqual(shown, ["new location"])
    }

    func testALoneLoadIsShown() async {
        let loads = LatestLoad<String>()
        var shown: [String] = []
        await loads.start({ "events" }) { shown.append($0) }.value
        XCTAssertEqual(shown, ["events"])
    }

    // MARK: - HomeViewState.after

    func testEventsLoad() throws {
        let event = try XCTUnwrap(Event(safeRecord: TestRecords.event(location: home)))
        guard case .loaded(let list) = HomeViewState.after(.success([event]), userLocation: home) else {
            return XCTFail("expected a loaded list")
        }
        XCTAssertEqual(list.events.count, 1)
    }

    func testNoEventsIsEmpty() {
        XCTAssertTrue(isNoData(HomeViewState.after(.success([]), userLocation: home)))
    }

    /// Superseded loads never reach `after`, so even a cancellation-type
    /// error here is real and must not leave the skeleton spinning.
    func testEveryErrorThatArrivesIsEmpty() {
        for error: Error in [CKError(.networkUnavailable), CKError(.operationCancelled),
                             URLError(.cancelled), CancellationError()] {
            XCTAssertTrue(isNoData(HomeViewState.after(.failure(error), userLocation: home)), "\(error)")
        }
    }
}
