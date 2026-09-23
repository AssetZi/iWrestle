//
//  TimeoutTests.swift
//  iWrestleTests
//
//  The filter sheet's count runs under withTimeout so a hung CloudKit
//  request becomes a Retry instead of a spinner that never ends.
//

import XCTest
@testable import iWrestle

final class TimeoutTests: XCTestCase {

    func testAFastOperationReturnsItsValue() async throws {
        let value = try await withTimeout(.seconds(5)) { 7 }
        XCTAssertEqual(value, 7)
    }

    func testASlowOperationThrowsTimeoutError() async {
        do {
            _ = try await withTimeout(.milliseconds(50)) {
                try await Task.sleep(for: .seconds(10))
                return 1
            }
            XCTFail("expected a timeout")
        } catch {
            XCTAssertTrue(error is TimeoutError)
        }
    }

    func testTheOperationsOwnErrorPassesThrough() async {
        struct Boom: Error {}
        do {
            _ = try await withTimeout(.seconds(5)) { () async throws -> Int in throw Boom() }
            XCTFail("expected the error to propagate")
        } catch {
            XCTAssertTrue(error is Boom)
        }
    }
}
