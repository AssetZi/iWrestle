//
//  TermsOfServiceView.swift
//  iWrestle
//
//  Created by Brock Zacherl on 12/20/25.
//

import SwiftUI

struct TermsOfServiceView: View {
    let effectiveDate: String

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {

                // Header
                VStack(alignment: .leading, spacing: 6) {
                    Text("iWrestle Terms of Service")
                        .font(.title.bold())

                    Text("Effective: \(effectiveDate)")
                        .font(.subheadline)
                        .foregroundStyle(.secondary)
                }
                .padding(.bottom, 4)

                TermsCard {
                    SectionHeader("1. Overview")
                    BodyText("""
                    iWrestle (the “App”) helps users discover, track, and share wrestling events (such as tournaments, duals, clinics, and camps). The App may show event details, locations, dates, fees, contact information, and links to third-party registration or event websites. By using the App, you agree to these Terms of Service (“Terms”). If you do not agree, do not use the App.
                    """)
                }

                TermsCard {
                    SectionHeader("2. Eligibility")
                    BodyText("""
                    You must be at least 13 years old (or the minimum age required in your jurisdiction) to use the App. If you are under the age of majority, a parent or legal guardian must review and accept these Terms on your behalf.
                    """)
                }

                TermsCard {
                    SectionHeader("3. Event Information & Accuracy")
                    BodyText("""
                    iWrestle aggregates and displays event information that may come from third parties and/or user submissions. We do not guarantee that event listings are accurate, complete, current, or error-free. Event details can change (dates, locations, costs, weigh-in rules, divisions, registration links, etc.). You are responsible for verifying details with the event organizer before traveling, registering, or paying any fees.
                    """)
                }

                TermsCard {
                    SectionHeader("4. Third-Party Services & Links")
                    BodyText("""
                    The App may link to third-party websites and services (for example, registration platforms, ticketing, maps, or organizer pages). We do not control and are not responsible for third-party content, policies, or practices. Your use of third-party services is governed by their terms and privacy policies.
                    """)
                }

                TermsCard {
                    SectionHeader("5. User Accounts")
                    BodyText("""
                    Some features may require an account. You are responsible for maintaining the confidentiality of your account and for all activity that occurs under it. You agree to provide accurate information and keep it up to date.
                    """)
                }

                TermsCard {
                    SectionHeader("6. User Submissions")
                    BodyText("""
                    If the App allows you to submit content (such as events, edits, photos, descriptions, or reports), you represent that you have the rights to submit it and that it is accurate to the best of your knowledge. You retain ownership of your submissions, but you grant iWrestle a non-exclusive, worldwide, royalty-free license to host, display, reproduce, modify (for formatting), and distribute that content for operating and improving the App.
                    """)
                    BodyText("""
                    We may remove or edit submissions at our discretion (for example, spam, duplicates, inaccurate info, or policy violations).
                    """)
                }

                TermsCard {
                    SectionHeader("7. Acceptable Use")
                    BodyText("""
                    You agree not to misuse the App, including by: (a) attempting to access data or accounts without authorization; (b) reverse-engineering, interfering with, or disrupting the App; (c) submitting unlawful, harmful, deceptive, or infringing content; (d) scraping the App or using automated tools to extract data without permission; or (e) using the App in a way that violates applicable laws or regulations.
                    """)
                }

                TermsCard {
                    SectionHeader("8. Subscriptions, Billing, and Trials")
                    BodyText("""
                    The App may offer optional auto-renewing subscriptions (monthly or yearly) to unlock premium features. Pricing and available plans are shown at purchase and may vary by region.
                    """)
                    BodyText("""
                    Payment is charged to your Apple ID at confirmation of purchase. Subscriptions automatically renew unless canceled at least 24 hours before the end of the current period. Your Apple ID account is charged for renewal within 24 hours prior to the end of the current period. You can manage or cancel subscriptions in your App Store account settings. Partial periods are not refunded, except where required by law.
                    """)
                }

                TermsCard {
                    SectionHeader("9. Refunds")
                    BodyText("""
                    Purchases are handled by Apple and refunds are subject to App Store policies. To request a refund, visit reportaproblem.apple.com or use Apple’s support channels available in your region.
                    """)
                }

                TermsCard {
                    SectionHeader("10. Privacy")
                    BodyText("""
                    Your use of the App is governed by our Privacy Policy, which explains how we collect, use, and share information. Please review it alongside these Terms. By using the App, you consent to our data practices as described in the Privacy Policy.
                    """)
                }

                TermsCard {
                    SectionHeader("11. Intellectual Property")
                    BodyText("""
                    iWrestle and its content, features, and functionality (excluding your submissions) are owned by iWrestle and its licensors and are protected by intellectual property laws. Except as expressly permitted, you may not copy, modify, distribute, sell, or lease any part of the App.
                    """)
                }

                TermsCard {
                    SectionHeader("12. Changes to the App")
                    BodyText("""
                    We may modify, suspend, or discontinue the App (in whole or in part) at any time. We are not liable to you or any third party for any modification, suspension, or discontinuation.
                    """)
                }

                TermsCard {
                    SectionHeader("13. Disclaimers")
                    BodyText("""
                    THE APP IS PROVIDED ON AN “AS IS” AND “AS AVAILABLE” BASIS WITHOUT WARRANTIES OF ANY KIND, EXPRESS OR IMPLIED. TO THE MAXIMUM EXTENT PERMITTED BY LAW, IWRESTLE DISCLAIMS ALL WARRANTIES, INCLUDING IMPLIED WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE, AND NON-INFRINGEMENT.
                    """)
                }

                TermsCard {
                    SectionHeader("14. Limitation of Liability")
                    BodyText("""
                    TO THE MAXIMUM EXTENT PERMITTED BY LAW, IWRESTLE AND ITS AFFILIATES, OFFICERS, EMPLOYEES, AGENTS, AND LICENSORS WILL NOT BE LIABLE FOR ANY INDIRECT, INCIDENTAL, SPECIAL, CONSEQUENTIAL, EXEMPLARY, OR PUNITIVE DAMAGES, OR ANY LOSS OF PROFITS, REVENUES, DATA, USE, GOODWILL, OR OTHER INTANGIBLE LOSSES, ARISING FROM OR RELATED TO YOUR USE OF (OR INABILITY TO USE) THE APP, THIRD-PARTY SERVICES, OR EVENT PARTICIPATION.
                    """)
                }

                TermsCard {
                    SectionHeader("15. Indemnification")
                    BodyText("""
                    You agree to indemnify and hold harmless iWrestle and its affiliates, officers, employees, agents, and licensors from and against claims, liabilities, damages, losses, and expenses (including reasonable attorney fees) arising out of or related to your use of the App, your submissions, or violation of these Terms.
                    """)
                }

                TermsCard {
                    SectionHeader("16. Termination")
                    BodyText("""
                    We may suspend or terminate your access to the App if we believe you violated these Terms or pose risk to other users or the App. You may stop using the App at any time. Provisions that should survive termination will survive.
                    """)
                }

                TermsCard {
                    SectionHeader("17. Governing Law")
                    BodyText("""
                    These Terms are governed by the laws of your place of residence to the extent required by applicable law; otherwise, the laws of the State of California, without regard to conflict-of-law principles.
                    """)
                }

                TermsCard {
                    SectionHeader("18. Changes to These Terms")
                    BodyText("""
                    We may update these Terms from time to time. If we make material changes, we will provide notice within the App or by other reasonable means. Your continued use of the App after changes take effect constitutes acceptance of the updated Terms.
                    """)
                }

                TermsCard {
                    SectionHeader("19. Contact")
                    BodyText("""
                    For support or questions, use the support options in the App Store listing or within the App’s support section.
                    """)
                }
            }
            .textSelection(.enabled)
            .padding()
        }
        .navigationTitle("Terms")
        .navigationBarTitleDisplayMode(.inline)
    }
}

// MARK: - Small UI helpers

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
    let text: String
    init(_ text: String) { self.text = text }

    var body: some View {
        Text(text)
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


