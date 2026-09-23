//
//  PromotedApp.swift
//  iWrestle
//
//  Brock's other apps, cross-promoted in the "Also by the maker of iWrestle"
//  row. No ad network: just a name, an App Store ID and taglines.
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

    var appStoreURL: URL { URL(string: "https://apps.apple.com/us/app/id\(id)")! }

    static let catalog: [PromotedApp] = [
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
        PromotedApp(id: "6759719992", name: "PinPoint Recruiting", taglines: [
            "Every recruit. Every coach. One board.",
            "Your recruiting board, in your pocket.",
            "Stop recruiting from a spreadsheet.",
            "Know where every scholarship dollar is going.",
            "Built by a wrestling coach, for wrestling coaches.",
            "The whole staff on the same page. Literally.",
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
}
