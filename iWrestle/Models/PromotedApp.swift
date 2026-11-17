//
//  PromotedApp.swift
//  iWrestle
//
//  Brock's other apps, cross-promoted in the "From the same maker" row.
//  No ad network: just a name, an App Store ID and taglines. Taps are
//  attributed through `PromoCampaign` and `AppLinks.appStoreProviderToken`.
//

import Foundation

struct PromotedApp: Identifiable, Hashable {
    /// App Store ID, the number after `id` in the listing URL.
    let id: String
    let name: String
    /// One is drawn at random each time the banner is placed; see `CrossPromo`.
    let taglines: [String]
    /// Slots in the rotation. 2 shows the app twice per cycle.
    var weight: Int = 1

    nonisolated static let catalog: [PromotedApp] = [
        PromotedApp(id: "6810665499", name: "Matlas", taglines: [
            "Matlas. Practice, planned.",
            "Build the drill once. Run it all season.",
            "Run like a program.",
            "Practice doesn't live in your Notes app.",
            "Runs the clock. Blows the horn. Waits for you.",
            "One plan for the first-years. One for the studs.",
            "Extra work for one kid. Nobody else sees it.",
            "Plan Monday once. Reuse it in February.",
            "Tomorrow's practice takes two taps tonight.",
            "Coach, even when you're not there.",
            "Your practice runs on their phone. Film included.",
        ]),
        PromotedApp(id: "6740700573", name: "Weight Wingman", taglines: [
            "Cutting weight doesn't have to suck.",
            "Say goodbye to cotton mouth.",
            "Cut weight, feel great.",
            "Refuel right for multi-day tournaments.",
            "No more running till midnight.",
        ]),
        PromotedApp(id: "6504050060", name: "Fantasy Wrestling", taglines: [
            "Fantasy football has a wrestling problem. We fixed it.",
            "Your league. Your draft. Real wrestlers.",
            "Finally, fantasy for people who wrestle.",
            "The season just got personal.",
            "Every dual meet, now yours to win.",
            "College wrestling, drafted.",
            "Stop watching. Start owning.",
            "Draft the room.",
        ]),
    ]

    /// Matlas, the practice planner. Shown to organizers more often; see
    /// `CrossPromo.markOrganizer()`.
    nonisolated static let organizerAppID = "6810665499"
}

/// Where a banner sits. The raw value is the App Analytics campaign (`ct=`),
/// so installs can be compared per placement in App Store Connect.
enum PromoCampaign: String, CaseIterable {
    case list = "iWrestle-list"
    case detail = "iWrestle-detail"
    case empty = "iWrestle-empty"
    case filtered = "iWrestle-filtered"
    case settings = "iWrestle-settings"
}
