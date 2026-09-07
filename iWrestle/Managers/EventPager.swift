//
//  EventPager.swift
//  iWrestle
//
//  The paging loop behind fetchEvents, kept apart from CloudKit so it can
//  be tested with hand-made records.
//

import CloudKit

/// One page of query results and the cursor to the next, if any.
struct EventPage<Cursor> {
    let records: [CKRecord]
    let cursor: Cursor?
}

enum EventPager {
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
        guard ceiling > 0 else { return [] }

        var events: [Event] = []
        var cursor: Cursor?

        repeat {
            let remaining = ceiling - events.count
            let page = try await fetch(cursor, remaining)
            for record in page.records {
                if let event = Event(safeRecord: record) {
                    events.append(event)
                }
            }
            cursor = page.cursor
        } while cursor != nil && events.count < ceiling

        return events
    }
}
