//
//  CrossPromo.swift
//  iWrestle
//
//  Picks which of Brock's apps the banner shows this launch. One app per
//  session so the events list and Settings agree; the rotation advances one
//  slot per launch; a dismissed app sits out for two weeks; the tagline is
//  random but never the one shown last time for that app.
//

import Foundation
import Observation

@Observable
@MainActor
final class CrossPromo {
    struct Placement: Equatable {
        let app: PromotedApp
        let tagline: String
    }

    /// Nil when every app is dismissed, or after `dismiss()`.
    private(set) var current: Placement?
    /// App Store artwork for `current`, cached across launches so the tile
    /// draws on the first frame after the first successful lookup.
    private(set) var iconURL: URL?

    static let dismissalPeriod: TimeInterval = 14 * 24 * 60 * 60

    private let defaults: UserDefaults
    private let now: Date

    // Nothing to tear down, and an isolated deinit's executor hop crashes
    // libmalloc (Xcode 27.0) when a test releases an instance synchronously.
    nonisolated deinit {}

    init(apps: [PromotedApp] = PromotedApp.catalog,
         defaults: UserDefaults = .standard,
         now: Date = .now,
         fetchIcon: Bool = true) {
        self.defaults = defaults
        self.now = now

        #if DEBUG
        if ProcessInfo.processInfo.arguments.contains("-iWrestleResetPromo") {
            for key in defaults.dictionaryRepresentation().keys where key.hasPrefix(Keys.prefix) {
                defaults.removeObject(forKey: key)
            }
        }
        #endif

        let launch = defaults.integer(forKey: Keys.launchCount)
        defaults.set(launch + 1, forKey: Keys.launchCount)

        let rotation = apps
            .filter { !isDismissed($0) }
            .flatMap { app in Array(repeating: app, count: max(app.weight, 1)) }
        guard !rotation.isEmpty else { return }

        let app = rotation[launch % rotation.count]
        let tagline = pickTagline(for: app)
        current = Placement(app: app, tagline: tagline)

        if let cached = defaults.string(forKey: Keys.iconURL(app.id)) {
            iconURL = URL(string: cached)
        }
        if fetchIcon {
            Task { @MainActor in await lookupIcon(for: app) }
        }
    }

    /// Hides the current app for `dismissalPeriod` and clears both placements.
    func dismiss() {
        guard let app = current?.app else { return }
        defaults.set(now.timeIntervalSince1970, forKey: Keys.dismissed(app.id))
        current = nil
    }

    // MARK: - Selection

    private func isDismissed(_ app: PromotedApp) -> Bool {
        let stamp = defaults.double(forKey: Keys.dismissed(app.id))
        guard stamp > 0 else { return false }
        return now.timeIntervalSince1970 - stamp < Self.dismissalPeriod
    }

    private func pickTagline(for app: PromotedApp) -> String {
        let last = defaults.string(forKey: Keys.lastTagline(app.id))
        let pool = app.taglines.filter { $0 != last }
        let tagline = (pool.isEmpty ? app.taglines : pool).randomElement() ?? app.name
        defaults.set(tagline, forKey: Keys.lastTagline(app.id))
        return tagline
    }

    // MARK: - Icon

    private struct Lookup: Decodable {
        struct Result: Decodable { let artworkUrl512: String }
        let results: [Result]
    }

    @MainActor
    private func lookupIcon(for app: PromotedApp) async {
        guard let url = URL(string: "https://itunes.apple.com/lookup?id=\(app.id)") else { return }
        guard let (data, _) = try? await URLSession.shared.data(from: url),
              let lookup = try? JSONDecoder().decode(Lookup.self, from: data),
              let artwork = lookup.results.first?.artworkUrl512,
              let artworkURL = URL(string: artwork) else { return }
        defaults.set(artwork, forKey: Keys.iconURL(app.id))
        if current?.app.id == app.id { iconURL = artworkURL }
    }

    // MARK: - Keys

    private enum Keys {
        static let prefix = "crossPromo."
        static let launchCount = prefix + "launchCount"
        static func dismissed(_ id: String) -> String { prefix + "dismissed." + id }
        static func lastTagline(_ id: String) -> String { prefix + "lastTagline." + id }
        static func iconURL(_ id: String) -> String { prefix + "iconURL." + id }
    }
}
