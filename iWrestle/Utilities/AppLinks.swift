//
//  AppLinks.swift
//  iWrestle
//
//  External URLs the app hands off to the system.
//

import Foundation

enum AppLinks {
    /// TODO: replace `id0000000000` with the numeric Apple ID from
    /// App Store Connect (App Information → General → Apple ID) before shipping.
    /// Used in the event share text and on the shared event PDF.
    static let appStore = URL(string: "https://apps.apple.com/app/id0000000000")!
}

extension URL {
    /// A `mailto:` URL with an optional pre-filled subject.
    ///
    /// `.urlQueryAllowed` leaves `&`, `+`, `=` and `?` unescaped, any of which
    /// truncate or corrupt the subject, so they are removed from the allowed set.
    static func mailto(_ address: String, subject: String? = nil) -> URL? {
        let trimmed = address.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { return nil }

        var string = "mailto:\(trimmed)"
        if let subject, !subject.isEmpty {
            var allowed = CharacterSet.urlQueryAllowed
            allowed.remove(charactersIn: "&+=?")
            string += "?subject=" + (subject.addingPercentEncoding(withAllowedCharacters: allowed) ?? "")
        }
        return URL(string: string)
    }
}
