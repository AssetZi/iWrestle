//
//  Timeout.swift
//  iWrestle
//
//  CloudKit requests can hang on a bad connection without ever throwing.
//  Racing them against a timer turns a hang into an error a screen can show.
//

import Foundation

struct TimeoutError: Error {}

/// Runs `operation`, or throws `TimeoutError` if it takes longer than
/// `duration`. The loser is cancelled.
func withTimeout<T: Sendable>(_ duration: Duration,
                              operation: @escaping @Sendable () async throws -> T) async throws -> T {
    try await withThrowingTaskGroup(of: T.self) { group in
        group.addTask { try await operation() }
        group.addTask {
            try await Task.sleep(for: duration)
            throw TimeoutError()
        }
        defer { group.cancelAll() }
        guard let result = try await group.next() else { throw TimeoutError() }
        return result
    }
}
