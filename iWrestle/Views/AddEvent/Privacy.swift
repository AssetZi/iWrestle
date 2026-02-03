//
//  Privacy.swift
//  iWrestle
//
//  Created by Brock Zacherl on 12/20/25.
//

import SwiftUI

struct PrivacyPolicyView: View {
    private let effectiveDate = "Effective: Jan 1, 2026"

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {

                // Header
                VStack(alignment: .leading, spacing: 6) {
                    Text("iWrestle Privacy Policy")
                        .font(.title.bold())

                    Text(effectiveDate)
                        .font(.subheadline)
                        .foregroundStyle(.secondary)
                }
                .padding(.bottom, 4)

                TermsCard {
                    SectionHeader("1. Our Commitment to Privacy")
                    BodyText("""
                    iWrestle respects your privacy. This Privacy Policy explains what information we collect, how we use it, and the choices you have when using iWrestle, a directory for youth wrestling events.
                    """)
                }

                TermsCard {
                    SectionHeader("2. Information We Collect")
                    BodyText("""
                    Depending on how you use the App, we may collect:
                    • Event search and usage information (for example, what screens you view and features you use) to improve the App.
                    • Approximate or precise location (only if you grant permission) to show events near you.
                    • Account information (if you create an account), such as email or sign-in identifiers.
                    • User submissions (if enabled), such as event listings, edits, photos, flyers, notes, or reports you provide.
                    """)
                    BodyText("""
                    If you do not create an account and you do not grant location permission, you can still browse events manually, but some features may be limited.
                    """)
                }

                TermsCard {
                    SectionHeader("3. Location Data")
                    BodyText("""
                    If you allow location access, iWrestle uses your location to power features like “events near me,” distance sorting, and region-based recommendations. You can change location permissions at any time in iOS Settings.
                    """)
                    BodyText("""
                    We do not sell location data. If we store location at all, it is limited to what’s necessary to provide the feature (for example, saving a preferred region or last-searched area).
                    """)
                }

                TermsCard {
                    SectionHeader("4. How We Use Information")
                    BodyText("""
                    We use information to:
                    • Provide core functionality (search, filtering, distance, maps, saving favorites).
                    • Improve reliability and performance (fix bugs, reduce crashes).
                    • Prevent abuse (spam submissions, malicious activity).
                    • Provide customer support if you contact us.
                    """)
                }

                TermsCard {
                    SectionHeader("5. Sharing of Information")
                    BodyText("""
                    We do not sell your personal information.
                    """)
                    BodyText("""
                    We may share limited information in the following cases:
                    • Service providers that help operate the App (for example, hosting, database, or crash reporting) under appropriate safeguards.
                    • Legal and safety reasons (to comply with law or protect users and the App).
                    • Business transfers (if the App is acquired or merged, information may be transferred as part of that transaction).
                    """)
                }

                TermsCard {
                    SectionHeader("6. Third-Party Links and Services")
                    BodyText("""
                    iWrestle may link to third-party services such as event registration platforms, organizer websites, or map providers. Your interactions with those third parties are governed by their own terms and privacy policies. We are not responsible for third-party practices.
                    """)
                }

                TermsCard {
                    SectionHeader("7. Children’s Privacy")
                    BodyText("""
                    iWrestle is a directory for youth wrestling events, but the App is intended for use by users who meet the minimum age requirements in their region. We do not knowingly collect personal information directly from children under 13 (or the equivalent minimum age in your jurisdiction).
                    """)
                    BodyText("""
                    We recommend that parents or guardians supervise children’s use of the App. If you believe a child has provided personal information, please contact us so we can take appropriate action.
                    """)
                }

                TermsCard {
                    SectionHeader("8. Data Retention")
                    BodyText("""
                    We keep information only as long as necessary to operate the App, comply with legal obligations, resolve disputes, and enforce agreements.
                    """)
                }

                TermsCard {
                    SectionHeader("9. Your Choices and Controls")
                    BodyText("""
                    You can:
                    • Turn location access on/off in iOS Settings.
                    • Request deletion of your account data (if accounts are enabled) through the App’s support channel.
                    • Remove your submitted content where supported, or request removal by contacting support.
                    """)
                }

                TermsCard {
                    SectionHeader("10. Payments and Subscriptions")
                    BodyText("""
                    If iWrestle offers subscriptions, purchases are processed by Apple via the App Store. iWrestle does not receive your full payment information. You can manage or cancel subscriptions in your Apple ID account settings.
                    """)
                }

                TermsCard {
                    SectionHeader("11. Security")
                    BodyText("""
                    We use reasonable administrative, technical, and organizational safeguards designed to protect information. No system is 100% secure, so we cannot guarantee absolute security.
                    """)
                }

                TermsCard {
                    SectionHeader("12. Changes to This Policy")
                    BodyText("""
                    We may update this Privacy Policy from time to time. If changes are material, we will provide notice within the App or by other reasonable means. The “Effective” date above reflects the latest version.
                    """)
                }

                TermsCard {
                    SectionHeader("13. Contact")
                    BodyText("""
                    If you have questions about this Privacy Policy, please reach out via the support options in the App Store listing or within the App’s support section.
                    """)
                }
            }
            .textSelection(.enabled)
            .padding()
        }
        .navigationTitle("Privacy Policy")
        .navigationBarTitleDisplayMode(.inline)
    }
}

// MARK: - UI helpers (same vibe as Terms)

private struct TermsCard<Content: View>: View {
    @ViewBuilder var content: Content

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            content
        }
        .padding(14)
        .background(.thinMaterial)
        .clipShape(RoundedRectangle(cornerRadius: 16, style: .continuous))
    }
}

private struct SectionHeader: View {
    let title: String
    init(_ title: String) { self.title = title }

    var body: some View {
        Text(title)
            .font(.headline)
            .padding(.bottom, 2)
    }
}

private struct BodyText: View {
    let text: String
    init(_ text: String) { self.text = text }

    var body: some View {
        Text(text)
            .font(.body)
            .foregroundStyle(.primary)
            .fixedSize(horizontal: false, vertical: true)
    }
}

#Preview {
    NavigationStack {
        PrivacyPolicyView()
    }
}
