//
//  LatestLoad.swift
//  iWrestle
//
//  Runs one load at a time for a screen. Starting a new load cancels the
//  one in flight, and a cancelled load's result is dropped even if it
//  finishes, so the newest request is always the one shown.
//

import Foundation

@MainActor
final class LatestLoad<Value> {
    private var current: Task<Void, Never>?

    // Nothing to tear down, and an isolated deinit's executor hop crashes
    // libmalloc (Xcode 27.0) when a test releases an instance synchronously.
    nonisolated deinit {}

    /// Cancels the load in flight, runs `load`, and hands its value to
    /// `deliver` unless a newer load has started since.
    @discardableResult
    func start(_ load: @escaping @MainActor () async -> Value,
               deliver: @escaping @MainActor (Value) -> Void) -> Task<Void, Never> {
        current?.cancel()
        let task = Task { @MainActor in
            let value = await load()
            // A newer load started while this one ran; its answer wins.
            guard !Task.isCancelled else { return }
            deliver(value)
        }
        current = task
        return task
    }
}
