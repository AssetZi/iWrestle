//
//  AppLinks.swift
//  iWrestle
//
//  External URLs the app hands off to the system.
//

import Foundation

enum AppLinks {
    /// The App Store listing. Printed in the shared event flyer's footer, where
    /// it is also stamped as a clickable link annotation.
    static let appStore = URL(string: "https://apps.apple.com/us/app/iwrestle-youth-wrestling-hub/id6756827197")!
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

    /// `https://example.com/register` from a link a user typed without a scheme.
    /// Nil for anything empty or unparseable.
    static func web(_ string: String) -> URL? {
        let trimmed = string.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { return nil }
        if let url = URL(string: trimmed), url.scheme != nil { return url }
        return URL(string: "https://" + trimmed)
    }

    /// `tel:` from a formatted phone number, keeping digits and a leading `+`.
    static func tel(_ number: String) -> URL? {
        var digits = number.filter { $0.isNumber }
        guard !digits.isEmpty else { return nil }
        if number.trimmingCharacters(in: .whitespaces).hasPrefix("+") { digits = "+" + digits }
        return URL(string: "tel:" + digits)
    }
}
