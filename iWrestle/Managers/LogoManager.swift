//
//  LogoManager.swift
//  iWrestle
//
//  Event logos, loaded after the list is on screen. List queries leave the
//  logo out (see `Event.Field.listKeys`), so rows appear on text alone and
//  each logo replaces its monogram tile as it arrives. Files are kept in
//  Caches, so a logo is downloaded once, not once per launch.
//

import Foundation
import CloudKit
import Observation
import os

@Observable
class LogoManager {
    /// Given record IDs, returns the logo file CloudKit downloaded for each.
    typealias Fetch = ([CKRecord.ID]) async throws -> [CKRecord.ID: URL]

    /// How many logos one request asks for. Small enough that the rows on
    /// screen get theirs in the first round trip.
    nonisolated static let chunkSize = 10
    /// How many requests run at once.
    nonisolated static let concurrentRequests = 4

    private static let log = Logger(subsystem: "zacherlInvestmentsLLC.iWrestle", category: "LogoManager")

    /// Logo files on disk, by cache name.
    private var files: [String: URL] = [:]

    @ObservationIgnored private let directory: URL
    @ObservationIgnored private let fetch: Fetch

    init(directory: URL = LogoManager.defaultDirectory, fetch: @escaping Fetch) {
        self.directory = directory
        self.fetch = fetch
    }

    // Nothing to tear down; see LatestLoad for why this is spelled out.
    nonisolated deinit {}

    nonisolated static var defaultDirectory: URL {
        FileManager.default.urls(for: .cachesDirectory, in: .userDomainMask)[0]
            .appendingPathComponent("logos", isDirectory: true)
    }

    /// The event's logo: its own file if the record came with one, else the
    /// cached copy. Nil until `load` has fetched it.
    func url(for event: Event) -> URL? {
        event.logo ?? files[Self.cacheName(for: event.record)]
    }

    /// Fetches the logos these events are missing, in list order, a few
    /// chunks at a time. Logos already in the cache are picked up without a request.
    ///
    /// Cancel the task to stop: requests under way end and no more start.
    /// The caller runs one load at a time (HomeView cancels the last list's).
    func load(_ events: [Event]) async {
        try? FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)

        var missing: [(id: CKRecord.ID, name: String)] = []
        var onDisk: [String: URL] = [:]
        for event in events where event.logo == nil {
            let name = Self.cacheName(for: event.record)
            guard files[name] == nil else { continue }
            let file = directory.appendingPathComponent(name)
            if FileManager.default.fileExists(atPath: file.path) {
                onDisk[name] = file
            } else {
                missing.append((event.id, name))
            }
        }
        if !onDisk.isEmpty { files.merge(onDisk) { _, new in new } }
        LaunchTiming.mark("logos: \(onDisk.count) from cache, \(missing.count) to fetch")
        guard !missing.isEmpty else { return }

        // A few requests at a time, started in list order: the rows on
        // screen go first, and all the logos land about a quarter sooner than
        // one request after another (measured on a fresh install).
        let chunks = Self.chunks(of: missing, size: Self.chunkSize)
        await withTaskGroup(of: Void.self) { group in
            var running = 0
            for chunk in chunks {
                if Task.isCancelled { break }
                if running == Self.concurrentRequests {
                    await group.next()
                    running -= 1
                }
                group.addTask { await self.fetchAndStore(chunk) }
                running += 1
            }
        }
        LaunchTiming.mark("logos: fetch finished")
    }

    private func fetchAndStore(_ chunk: [(id: CKRecord.ID, name: String)]) async {
        do {
            let fetched = try await fetch(chunk.map(\.id))
            var stored: [String: URL] = [:]
            for (id, name) in chunk {
                guard let source = fetched[id] else { continue }
                let file = directory.appendingPathComponent(name)
                try? FileManager.default.removeItem(at: file)
                do {
                    try FileManager.default.copyItem(at: source, to: file)
                    stored[name] = file
                } catch {
                    Self.log.error("Could not cache a logo: \(error.localizedDescription)")
                }
            }
            files.merge(stored) { _, new in new }
            LaunchTiming.mark("logos: \(stored.count) stored")
        } catch {
            // The tiles keep their monograms; the next load tries again.
            // A cancelled load ends its requests this way too: not an error.
            guard !Task.isCancelled else { return }
            Self.log.error("Logo fetch failed: \(error.localizedDescription)")
        }
    }

    /// `<record name>-<change tag>`. The change tag moves when the record is
    /// saved, so an edited logo gets a new file and the old one is not shown.
    nonisolated static func cacheName(for record: CKRecord) -> String {
        let allowed = CharacterSet.alphanumerics.union(CharacterSet(charactersIn: "-_"))
        let name = record.recordID.recordName.addingPercentEncoding(withAllowedCharacters: allowed)
            ?? record.recordID.recordName
        return "\(name)-\(record.recordChangeTag ?? "0")"
    }

    nonisolated static func chunks<Item>(of items: [Item], size: Int) -> [[Item]] {
        guard size > 0 else { return [items] }
        return stride(from: 0, to: items.count, by: size).map {
            Array(items[$0..<min($0 + size, items.count)])
        }
    }
}
