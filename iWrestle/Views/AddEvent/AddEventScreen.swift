//
//  AddEventScreen.swift
//  iWrestle
//
//  Created by Brock Zacherl on 11/30/25.
//
//  One form for both the paid flow and the admin flow; only the submit path
//  differs (`mode`). Publishing keeps the sheet open on failure and offers a
//  retry that never charges twice.
//

import SwiftUI
import MapKit
import StoreKit

struct AddEventScreen: View {
    enum Mode { case paid, admin }

    @Environment(CloudKitManager.self) var ck
    @Environment(LocationManager.self) var lm
    @Environment(\.dismiss) var dismiss
    @Binding var userEvents: [Event]
    var mode: Mode = .paid

    @State private var storekit = StoreKitManager()
    @State private var eventData = EventData()
    @State private var wantsImagesMade: Bool = false
    @State private var eventLogo: UIImage?
    @State private var isLoading: Bool = false
    @State private var isShowingDatePicker: Bool = false
    @State private var isPublished = false
    @State private var showTerms = false
    @State private var showPrivacy = false

    /// StoreKit / CloudKit failures only. Validation has its own row so it can
    /// never hide the pricing line at the moment the user is deciding to buy.
    @State private var purchaseError: String?
    /// Set on the first submit attempt; until then the form stays quiet.
    @State private var attemptedSubmit = false
    /// The purchase finished but CloudKit failed: a retry must not charge again.
    @State private var hasPaid = false

    @FocusState private var focusedField: FocusField?

    enum FocusField {
        case title, registration, firstName, lastName, email, phone
    }

    private var priceLabel: String {
        storekit.product?.displayPrice ?? launchPriceLabel
    }

    var body: some View {
        // Evaluated once per render and reused by the message and the submit
        // handler, so they can never disagree.
        let missing = missingFields(data: eventData, logo: eventLogo, wantsImagesMade: wantsImagesMade)

        VStack(spacing: 0) {
            if isPublished {
                successView
                    .transition(.opacity)
            } else {
                header
                form(missing: missing)
            }
        }
        .canvas()
        .presentationBackground(Theme.ink)
        .presentationCornerRadius(Theme.Radius.sheet)
        .presentationDragIndicator(.hidden)
        .interactiveDismissDisabled(isLoading)
        .task {
            guard mode == .paid else { return }
            do { try await storekit.loadProducts() }
            catch { purchaseError = error.localizedDescription }
        }
        .sheet(isPresented: $showTerms) {
            TermsOfServiceView(effectiveDate: "Jan 1, 2026")
                .presentationBackground(Theme.ink)
        }
        .sheet(isPresented: $showPrivacy) {
            PrivacyPolicyView()
                .presentationBackground(Theme.ink)
        }
    }

    // MARK: - Chrome

    private var header: some View {
        HStack {
            IconButton(icon: .x, size: 34, radius: 10, iconSize: 15, strokeWidth: 2,
                       accessibilityLabel: "Close") { dismiss() }
            Spacer()
            Text("Add event")
                .font(.cardTitle)
                .foregroundStyle(Theme.textPrimary)
            Spacer()
            Color.clear.frame(width: 34, height: 34)
        }
        .padding(.horizontal, 16)
        .padding(.vertical, 14)
        .overlay(alignment: .bottom) { HairlineDivider() }
    }

    private func form(missing: [RequiredField]) -> some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 20) {
                eventInformation(missing: missing)
                contact(missing: missing)
                files(missing: missing)

                if attemptedSubmit, let message = validationMessage(for: missing) {
                    Text(message)
                        .font(.body12)
                        .foregroundStyle(Theme.danger)
                        .fixedSize(horizontal: false, vertical: true)
                }

                if let purchaseError {
                    Text(purchaseError)
                        .font(.body12)
                        .foregroundStyle(Theme.danger)
                        .fixedSize(horizontal: false, vertical: true)
                }

                if mode == .paid {
                    LaunchPricingCard(price: priceLabel)
                }

                PrimaryGoldButton(title: ctaTitle, isBusy: isLoading) {
                    attemptedSubmit = true
                    focusedField = nil
                    guard missing.isEmpty else { return }
                    Task { await publish() }
                }

                termsLine
                    .padding(.top, -8)
            }
            .padding(.horizontal, Theme.gutter)
            .padding(.top, 18)
            .padding(.bottom, 40)
        }
        .scrollIndicators(.hidden)
        .scrollDismissesKeyboard(.interactively)
        .hideKeyboardOnTap()
        .onChange(of: eventLogo) { focusedField = nil }
        .onChange(of: eventData.flyer) { focusedField = nil }
    }

    private var ctaTitle: String {
        if isLoading { return "Publishing…" }
        if hasPaid { return "Retry publish" }
        return mode == .admin ? "Publish event" : "Publish event · \(priceLabel)"
    }

    private var termsLine: some View {
        Text("By publishing you agree to the [Terms of Service](iwrestle://terms) and [Privacy Policy](iwrestle://privacy).")
            .font(.caption10_5)
            .foregroundStyle(Theme.textTertiary)
            .tint(Theme.textSecondary)
            .multilineTextAlignment(.center)
            .frame(maxWidth: .infinity)
            .environment(\.openURL, OpenURLAction { url in
                switch url.host {
                case "terms": showTerms = true
                case "privacy": showPrivacy = true
                default: return .systemAction
                }
                return .handled
            })
    }

    // MARK: - Sections

    private func eventInformation(missing: [RequiredField]) -> some View {
        VStack(alignment: .leading, spacing: 12) {
            Eyebrow("01 — Event information", size: 10, tracking: 0.18)

            FormTextField(placeholder: "Event name (required)", text: $eventData.name,
                          capitalization: .words,
                          isInvalid: attemptedSubmit && missing.contains(.name),
                          focused: focusedField == .title)
                .focused($focusedField, equals: .title)

            EventTypePicker(eventType: $eventData.eventType)

            SplitHStack(weights: [1, 1.4], spacing: 10) {
                FormRowButton(icon: .calendar, text: eventData.date.shortDayLabel) {
                    focusedField = nil
                    withAnimation(Motion.normal) { isShowingDatePicker.toggle() }
                }
                MapView(selectedLocation: $eventData.location, address: $eventData.address,
                        isRequired: true, showsError: attemptedSubmit && missing.contains(.location))
            }

            if isShowingDatePicker {
                EventDateCalendar(date: $eventData.date)
                    .onChange(of: eventData.date) {
                        withAnimation(Motion.normal) { isShowingDatePicker = false }
                    }
                    .transition(.opacity.combined(with: .offset(y: -6)))
            }

            AgeGroupPicker(selectedAgeGroups: $eventData.ageGroups,
                           isInvalid: attemptedSubmit && missing.contains(.ageGroups))

            FormTextField(placeholder: "Registration link (optional)", text: $eventData.registration,
                          keyboard: .URL, contentType: .URL, capitalization: .never,
                          focused: focusedField == .registration)
                .focused($focusedField, equals: .registration)
        }
    }

    private func contact(missing: [RequiredField]) -> some View {
        let contactInvalid = attemptedSubmit && missing.contains(.contactInfo)
        return VStack(alignment: .leading, spacing: 12) {
            Eyebrow("02 — Contact", size: 10, tracking: 0.18)
            HStack(spacing: 10) {
                FormTextField(placeholder: "First name", text: $eventData.eventContactFirstName,
                              contentType: .givenName, capitalization: .words,
                              isInvalid: contactInvalid && eventData.eventContactFirstName.isEmpty,
                              focused: focusedField == .firstName)
                    .focused($focusedField, equals: .firstName)
                    .accessibilityLabel("First name")
                FormTextField(placeholder: "Last name", text: $eventData.eventContactLastName,
                              contentType: .familyName, capitalization: .words,
                              isInvalid: contactInvalid && eventData.eventContactLastName.isEmpty,
                              focused: focusedField == .lastName)
                    .focused($focusedField, equals: .lastName)
                    .accessibilityLabel("Last name")
            }
            FormTextField(placeholder: "Email (required)", text: $eventData.eventContactEmail,
                          keyboard: .emailAddress, contentType: .emailAddress, capitalization: .never,
                          isInvalid: contactInvalid && eventData.eventContactEmail.isEmpty,
                          focused: focusedField == .email)
                .focused($focusedField, equals: .email)
            FormTextField(placeholder: "Phone (optional)", text: $eventData.eventContactPhone,
                          keyboard: .phonePad, contentType: .telephoneNumber,
                          focused: focusedField == .phone)
                .focused($focusedField, equals: .phone)
        }
    }

    private func files(missing: [RequiredField]) -> some View {
        VStack(alignment: .leading, spacing: 12) {
            Eyebrow("03 — Files", size: 10, tracking: 0.18)
            iWrestlePDFPicker(title: "Upload event flyer (PDF, required)", importedURL: $eventData.flyer,
                              isInvalid: attemptedSubmit && missing.contains(.flyer))
            iWrestlePhotoPicker(image: $eventLogo, title: "Upload event logo (required)",
                                isInvalid: attemptedSubmit && missing.contains(.logo))
        }
    }

    private var successView: some View {
        VStack(spacing: 16) {
            Spacer()
            LucideIcon(.check, size: 28, strokeWidth: 2.5)
                .foregroundStyle(Theme.onAccent)
                .frame(width: 64, height: 64)
                .background(Circle().fill(Theme.gold))
                .overlay(Circle().strokeBorder(Theme.gold.opacity(0.35), lineWidth: 1))
                .shadow(color: Theme.gold.opacity(0.18), radius: 16, y: 8)
            Text("Event published.")
                .font(.successTitle)
                .tracked(-0.02, 23)
                .foregroundStyle(Theme.textPrimary)
            Text("Wrestling families near \(lm.userCity ?? "you") can find your event now.")
                .font(.body13)
                .foregroundStyle(Theme.textSecondary)
                .multilineTextAlignment(.center)
                .lineSpacing(4)
                .frame(maxWidth: 250)
            SecondaryButton(title: "Done") { dismiss() }
                .padding(.top, 8)
            Spacer()
        }
        .padding(40)
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .entrance()
    }

    // MARK: - Publishing

    private func publish() async {
        purchaseError = nil
        isLoading = true
        defer { isLoading = false }

        if mode == .paid, !hasPaid {
            do {
                let result = try await storekit.purchaseListing(logoGen: wantsImagesMade)
                switch result {
                case .success:
                    // Payment verified. From here on a failure must not re-charge.
                    hasPaid = true
                case .cancelled:
                    return
                case .pending:
                    purchaseError = "Purchase is pending approval."
                    return
                }
            } catch {
                purchaseError = error.localizedDescription
                return
            }
        }

        await createEvent()
    }

    private func createEvent() async {
        guard let photo = eventLogo, let photoUrl = ck.getPhotoURL(image: photo) else {
            purchaseError = "We couldn't prepare your logo image. Try choosing it again."
            return
        }
        eventData.logo = photoUrl

        if let event = await ck.createEvent(data: eventData) {
            userEvents.append(event)
            withAnimation(Motion.easeOut(0.3)) { isPublished = true }
        } else if hasPaid {
            purchaseError = "We couldn't publish your event. Your payment went through, so tap Retry publish — you won't be charged again."
        } else {
            purchaseError = "We couldn't publish your event. Check your connection and try again."
        }
    }
}

/// Two children laid out side by side with proportional widths (1 : 1.4 for
/// the date / location rows in the mock).
struct SplitHStack: Layout {
    var weights: [CGFloat]
    var spacing: CGFloat = 10

    func sizeThatFits(proposal: ProposedViewSize, subviews: Subviews, cache: inout ()) -> CGSize {
        let width = proposal.width ?? 0
        let height = subviews.map { $0.sizeThatFits(.unspecified).height }.max() ?? 0
        return CGSize(width: width, height: height)
    }

    func placeSubviews(in bounds: CGRect, proposal: ProposedViewSize, subviews: Subviews, cache: inout ()) {
        let total = weights.reduce(0, +)
        let available = bounds.width - spacing * CGFloat(max(subviews.count - 1, 0))
        var x = bounds.minX
        for (index, view) in subviews.enumerated() {
            let weight = index < weights.count ? weights[index] : 1
            let width = available * weight / total
            view.place(at: CGPoint(x: x, y: bounds.minY),
                       proposal: ProposedViewSize(width: width, height: bounds.height))
            x += width + spacing
        }
    }
}
