//
//  LaunchTiming.swift
//  iWrestle
//
//  Timestamps for the path from launch to the first events on screen, so a
//  slow launch can be read out of the log instead of guessed at:
//
//      log stream --predicate 'subsystem == "zacherlInvestmentsLLC.iWrestle" AND category == "Launch"'
//

import Foundation
import os

nonisolated enum LaunchTiming {
    private static let log = Logger(subsystem: "zacherlInvestmentsLLC.iWrestle", category: "Launch")
    /// Set on first use, which is the app's init.
    private static let start = ProcessInfo.processInfo.systemUptime

    /// Seconds since the app started.
    static var elapsed: TimeInterval {
        ProcessInfo.processInfo.systemUptime - start
    }

    /// Logs `step` with the time since launch, e.g. "list shown +1.84s".
    static func mark(_ step: String) {
        let seconds = elapsed
        log.notice("\(step, privacy: .public) +\(seconds, format: .fixed(precision: 2), privacy: .public)s")
    }
}
