//
//  LogoManagerTests.swift
//  iWrestleTests
//
//  Logos load after the list: in chunks, once per logo, and
//  from the cache folder on later launches.
//

import XCTest
import CloudKit
@testable import iWrestle

/// Stands in for CloudKit: hands back a file per requested ID and records
/// what was asked.
@MainActor
private final class FakeLogoServer {
    private(set) var requests: [[CKRecord.ID]] = []
    var fails = false
    /// Runs when the first request arrives.
    var onFirstRequest: (() -> Void)?

    nonisolated deinit {}

    func fetch(_ ids: [CKRecord.ID]) async throws -> [CKRecord.ID: URL] {
        requests.append(ids)
        if requests.count == 1 { onFirstRequest?() }
        if fails { throw CKError(.networkUnavailable) }
        var logos: [CKRecord.ID: URL] = [:]
        for id in ids { logos[id] = TestRecords.tempFile("logo.png") }
        return logos
    }
}

@MainActor
final class LogoManagerTests: XCTestCase {
    private var directory: URL!

    override func setUp() async throws {
        directory = FileManager.default.temporaryDirectory
            .appendingPathComponent("logo-tests-" + UUID().uuidString, isDirectory: true)
    }

    override func tearDown() async throws {
        try? FileManager.default.removeItem(at: directory)
    }

    private func listEvents(_ count: Int) throws -> [Event] {
        try (0..<count).map { try XCTUnwrap(Event(safeRecord: TestRecords.eventWithoutLogo(name: "Event \($0)"))) }
    }

    private func manager(_ server: FakeLogoServer) -> LogoManager {
        LogoManager(directory: directory) { try await server.fetch($0) }
    }

    func testAListEventHasNoLogoUntilItIsLoaded() async throws {
        let server = FakeLogoServer()
        let logos = manager(server)
        let events = try listEvents(1)

        XCTAssertNil(logos.url(for: events[0]))
        await logos.load(events)

        let url = try XCTUnwrap(logos.url(for: events[0]))
        XCTAssertTrue(FileManager.default.fileExists(atPath: url.path))
        XCTAssertEqual(url.deletingLastPathComponent().lastPathComponent, directory.lastPathComponent)
    }

    func testEveryLogoIsFetchedOnceInChunks() async throws {
        let server = FakeLogoServer()
        let events = try listEvents(LogoManager.chunkSize * 2 + 5)

        await manager(server).load(events)

        // Requests overlap, so only the first is sure of its place.
        XCTAssertEqual(server.requests.map(\.count).sorted(), [5, LogoManager.chunkSize, LogoManager.chunkSize])
        XCTAssertEqual(Set(server.requests.flatMap { $0 }), Set(events.map(\.id)))
        XCTAssertEqual(server.requests.flatMap { $0 }.count, events.count)
    }

    func testALoadedLogoIsNotFetchedAgain() async throws {
        let server = FakeLogoServer()
        let logos = manager(server)
        let events = try listEvents(3)

        await logos.load(events)
        await logos.load(events)

        XCTAssertEqual(server.requests.count, 1)
    }

    /// The next launch has a new manager and the same folder.
    func testCachedLogosAreReadFromDiskWithoutARequest() async throws {
        let events = try listEvents(3)
        await manager(FakeLogoServer()).load(events)

        let server = FakeLogoServer()
        let relaunched = manager(server)
        await relaunched.load(events)

        XCTAssertTrue(server.requests.isEmpty)
        XCTAssertNotNil(relaunched.url(for: events[2]))
    }

    /// The user's own events are fetched with every field.
    func testAnEventWithItsOwnLogoUsesItAndIsNotFetched() async throws {
        let server = FakeLogoServer()
        let logos = manager(server)
        let event = try XCTUnwrap(Event(safeRecord: TestRecords.event()))

        await logos.load([event])

        XCTAssertTrue(server.requests.isEmpty)
        XCTAssertEqual(logos.url(for: event), event.logo)
    }

    func testAFailedFetchLeavesTheLogoToBeTriedAgain() async throws {
        let server = FakeLogoServer()
        let logos = manager(server)
        let events = try listEvents(1)

        server.fails = true
        await logos.load(events)
        XCTAssertNil(logos.url(for: events[0]))

        server.fails = false
        await logos.load(events)
        XCTAssertNotNil(logos.url(for: events[0]))
    }

    /// A new list replaces the old one mid-download: the old load stops and
    /// the new one still gets every logo, including ones the old had asked for.
    func testACancelledLoadStopsAndTheNextLoadFetchesWhatIsLeft() async throws {
        let server = FakeLogoServer()
        let logos = manager(server)
        let events = try listEvents(LogoManager.chunkSize * 8)

        let first = Task { await logos.load(events) }
        server.onFirstRequest = { first.cancel() }
        await first.value
        // Requests already under way finish; the rest never start.
        XCTAssertGreaterThan(server.requests.count, 0)
        XCTAssertLessThanOrEqual(server.requests.count, LogoManager.concurrentRequests + 1)

        await logos.load(events)
        XCTAssertTrue(events.allSatisfy { logos.url(for: $0) != nil })
    }

    func testTheCacheNameIsSafeAsAFileName() {
        let record = CKRecord(recordType: Event.recordType, recordID: CKRecord.ID(recordName: "flo/2026 open"))
        XCTAssertEqual(LogoManager.cacheName(for: record), "flo%2F2026%20open-0")
    }
}
