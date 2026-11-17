//
//  HomeLoadTests.swift
//  iWrestleTests
//
//  What the home feed shows when a load finishes. A cancelled load, such as
//  one the view restarted on a new location fix, must not read as empty.
//

import XCTest
import CloudKit
import CoreLocation
@testable import iWrestle

final class HomeLoadTests: XCTestCase {
    private let home = CLLocation(latitude: 41.2, longitude: -79.4)

    private func isNoData(_ state: HomeViewState?) -> Bool {
        if case .error(.noData) = state { return true }
        return false
    }

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

    func testAFailedFetchIsEmpty() {
        let error = CKError(.networkUnavailable)
        XCTAssertTrue(isNoData(HomeViewState.after(.failure(error), userLocation: home)))
    }

    func testATaskCancellationLeavesTheScreenAlone() {
        XCTAssertNil(HomeViewState.after(.failure(CancellationError()), userLocation: home))
    }

    func testACloudKitCancellationLeavesTheScreenAlone() {
        XCTAssertNil(HomeViewState.after(.failure(CKError(.operationCancelled)), userLocation: home))
    }

    func testAURLCancellationLeavesTheScreenAlone() {
        XCTAssertNil(HomeViewState.after(.failure(URLError(.cancelled)), userLocation: home))
    }
}
