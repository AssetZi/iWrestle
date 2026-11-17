//
//  UserEventTally.swift
//  iWrestle
//
//  How many events the user has published, for the Settings badge.
//
//  Settings counts them at launch without downloading them, and the
//  dashboard fetches the list when it opens. In between, the list in memory
//  holds only what was published this session, so its size is not the count.
//

import Foundation

nonisolated struct UserEventTally: Equatable {
    private(set) var count = 0
    /// True once the dashboard has fetched every event; from then on the
    /// count is the size of the list.
    var hasFullList = false

    /// The launch count came back. Events published while it was on its
    /// way are added: a query does not see a record saved a moment ago.
    mutating func counted(_ serverCount: Int, publishedSince: Int) {
        guard !hasFullList else { return }
        count = serverCount + publishedSince
    }

    /// The list in memory went from `old` to `new` events.
    mutating func listChanged(from old: Int, to new: Int) {
        count = hasFullList ? new : max(0, count + (new - old))
    }
}
