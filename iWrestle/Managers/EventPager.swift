//
//  EventPager.swift
//  iWrestle
//
//  The paging loop behind fetchEvents, kept apart from CloudKit so it can
//  be tested with hand-made records.
//

import CloudKit
import os

/// One page of query results and the cursor to the next, if any.
struct EventPage<Cursor> {
    let records: [CKRecord]
    let cursor: Cursor?
}

enum EventPager {
    private static let log = Logger(subsystem: "zacherlInvestmentsLLC.iWrestle", category: "EventPager")

    /// Follow the cursor until `ceiling` decoded events are in hand or the
    /// results run out.
    ///
    /// CloudKit answers in pages. Without following the cursor a busy
    /// weekend silently loses every event past the first page. Records that
    /// fail to decode (`Event(safeRecord:)` returns nil) do not count toward
    /// the ceiling, so the loop keeps asking for more until it has
    /// `ceiling` real events or the cursor is nil.
    ///
    /// - Parameter fetch: given the cursor (nil for the first page) and how
    ///   many results are still wanted, returns the next page.
    static func collect<Cursor>(
        ceiling: Int,
        fetch: (Cursor?, Int) async throws -> EventPage<Cursor>
    ) async throws -> [Event] {
        try await collect(ceiling: ceiling, decode: Event.init(safeRecord:), fetch: fetch)
    }

    /// The same loop with a pluggable decoder, so a count can page through
    /// bare record IDs without building events.
    static func collect<Cursor, Item>(
        ceiling: Int,
        decode: (CKRecord) -> Item?,
        fetch: (Cursor?, Int) async throws -> EventPage<Cursor>
    ) async throws -> [Item] {
        guard ceiling > 0 else { return [] }

        var items: [Item] = []
        var cursor: Cursor?

        repeat {
            let remaining = ceiling - items.count
            let page = try await fetch(cursor, remaining)
            let before = items.count
            for record in page.records {
                if let item = decode(record) {
                    items.append(item)
                }
            }
            // A whole page that decodes to nothing usually means a query
            // asked for too few keys (see Event.Field.listKeys).
            if !page.records.isEmpty && items.count == before {
                log.error("A page of \(page.records.count) records decoded to nothing")
            }
            cursor = page.cursor
        } while cursor != nil && items.count < ceiling

        return items
    }
}
