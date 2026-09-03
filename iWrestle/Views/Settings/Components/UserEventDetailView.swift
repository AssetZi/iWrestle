//
//  UserEventDetailView.swift
//  iWrestle
//
//  Created by Brock Zacherl on 12/13/25.
//

import SwiftUI
import MapKit

/// Organizer's view of one of their events: preview, or edit and save.
struct UserEventDetailView: View {
    @Environment(CloudKitManager.self) var ck
    @Environment(\.dismiss) var dismiss
    @Binding var ogEvent: Event
    @State var event: Event
    @State private var newLogo: UIImage?
    @State private var newFlyer: URL?
    @State private var isLoading = false
    @State private var location: CLLocationCoordinate2D?
    @State private var isEditing: Bool = false
    @State private var isShowingDatePicker = false
    @State private var saveError: String?
    @FocusState private var focusedField: FocusField?

    enum FocusField { case name, registration, firstName, lastName, email, phone }

    let ageGroups = AgeGroup.allCases.map(\.rawValue)

    var cantChangeDate: Bool {
        // True if we're within 7 days of the event (i.e., after eventDate - 7 days)
        guard let sevenDaysBefore = Calendar.current.date(byAdding: .day, value: -7, to: event.date) else {
            return false
        }
        return Date() >= sevenDaysBefore
    }

    var body: some View {
        VStack(spacing: 0) {
            topBar

            ZStack {
                ScrollView {
                    VStack(alignment: .leading, spacing: 20) {
                        NavigationLink(value: AppRoute.eventDetail(event)) {
                            RowSurface {
                                CardRow(icon: .calendar, label: "Preview event")
                            }
                        }
                        .buttonStyle(SurfaceButtonStyle(scale: 1))
                        .cardContainer()

                        eventInformation
                        contact
                        files

                        if let saveError {
                            Text(saveError)
                                .font(.body12)
                                .foregroundStyle(Theme.danger)
                                .fixedSize(horizontal: false, vertical: true)
                        }
                    }
                    .padding(.horizontal, Theme.gutter)
                    .padding(.top, 14)
                    .padding(.bottom, 40)
                }
                .scrollIndicators(.hidden)
                .scrollDismissesKeyboard(.interactively)
                .disabled(isLoading)
                .opacity(isLoading ? 0.3 : 1)

                if isLoading {
                    iWrestleProgressView()
                }
            }
        }
        .canvas()
        .toolbar(.hidden, for: .navigationBar)
        .enableSwipeBack()
        .hideKeyboardOnTap()
        .task {
            location = CLLocationCoordinate2D(latitude: event.location.coordinate.latitude,
                                              longitude: event.location.coordinate.longitude)
        }
    }

    // MARK: - Chrome

    private var topBar: some View {
        HStack(spacing: 12) {
            BackButton()
            VStack(alignment: .leading, spacing: 2) {
                Eyebrow("Organizer", size: 10)
                Text(isEditing ? "Edit event" : "Your event")
                    .font(.pushedTitle)
                    .tracked(-0.02, 20)
                    .foregroundStyle(Theme.textPrimary)
            }
            Spacer()
            if isEditing {
                Button("Cancel") {
                    event = ogEvent
                    newLogo = nil
                    newFlyer = nil
                    saveError = nil
                    withAnimation(Motion.fast) { isEditing = false }
                }
                .font(.body13)
                .foregroundStyle(Theme.textTertiary)
                .buttonStyle(.plain)
            }
            Button(isEditing ? "Save" : "Edit") {
                if isEditing {
                    saveEvent()
                } else {
                    withAnimation(Motion.fast) { isEditing = true }
                }
            }
            .font(.body13_5Medium)
            .foregroundStyle(Theme.gold)
            .buttonStyle(.plain)
        }
        .padding(.horizontal, Theme.gutter)
        .padding(.top, 6)
        .padding(.bottom, 10)
    }

    // MARK: - Sections

    private var eventInformation: some View {
        VStack(alignment: .leading, spacing: 12) {
            Eyebrow("01 — Event information", size: 10, tracking: 0.18)
            FormTextField(placeholder: "Event name", text: $event.name,
                          capitalization: .words, focused: focusedField == .name)
                .focused($focusedField, equals: .name)

            if !cantChangeDate {
                FormRowButton(icon: .calendar, text: event.date.shortDayLabel) {
                    withAnimation(Motion.normal) { isShowingDatePicker.toggle() }
                }
                if isShowingDatePicker {
                    EventDateCalendar(date: $event.date)
                        .onChange(of: event.date) {
                            withAnimation(Motion.normal) { isShowingDatePicker = false }
                        }
                }
            }

            MapView(selectedLocation: $location, address: $event.address)
            AgeGroupPickerString(selectedAgeGroups: $event.ageGroups, ageGroups: ageGroups, title: "Age groups")
            FormTextField(placeholder: "Registration link (optional)",
                          text: Binding(
                            get: { event.registration ?? "" },
                            set: { event.registration = $0.isEmpty ? nil : $0 }
                          ),
                          keyboard: .URL, capitalization: .never,
                          focused: focusedField == .registration)
                .focused($focusedField, equals: .registration)
        }
        .disabled(!isEditing)
    }

    private var contact: some View {
        VStack(alignment: .leading, spacing: 12) {
            Eyebrow("02 — Contact", size: 10, tracking: 0.18)
            HStack(spacing: 10) {
                FormTextField(placeholder: "First name", text: $event.eventContactFirstName,
                              contentType: .givenName, capitalization: .words,
                              focused: focusedField == .firstName)
                    .focused($focusedField, equals: .firstName)
                    .accessibilityLabel("First name")
                FormTextField(placeholder: "Last name", text: $event.eventContactLastName,
                              contentType: .familyName, capitalization: .words,
                              focused: focusedField == .lastName)
                    .focused($focusedField, equals: .lastName)
                    .accessibilityLabel("Last name")
            }
            FormTextField(placeholder: "Email", text: $event.eventContactEmail,
                          keyboard: .emailAddress, contentType: .emailAddress, capitalization: .never,
                          focused: focusedField == .email)
                .focused($focusedField, equals: .email)
            FormTextField(placeholder: "Phone (optional)", text: $event.eventContactPhone,
                          keyboard: .phonePad, contentType: .telephoneNumber,
                          focused: focusedField == .phone)
                .focused($focusedField, equals: .phone)
        }
        .disabled(!isEditing)
    }

    private var files: some View {
        VStack(alignment: .leading, spacing: 12) {
            Eyebrow("03 — Files", size: 10, tracking: 0.18)
            iWrestlePDFPicker(title: "Replace event flyer (PDF)", importedURL: $newFlyer)
            iWrestlePhotoPicker(image: $newLogo, title: "Replace event logo", existingLogoURL: event.logo)
        }
        .disabled(!isEditing)
    }

    // MARK: - Save

    func saveEvent() {
        Task {
            isLoading = true
            saveError = nil
            defer { isLoading = false }

            if event.address != ogEvent.address {
                guard let location else {
                    saveError = "Pick the event location again before saving."
                    return
                }
                event.location = CLLocation(latitude: location.latitude, longitude: location.longitude)
            }

            var logo: URL? = nil
            if let newLogo {
                guard let photoUrl = ck.getPhotoURL(image: newLogo) else {
                    saveError = "We couldn't prepare the new logo. Try choosing it again."
                    return
                }
                logo = photoUrl
                event.logo = photoUrl
            }
            if let newFlyer {
                event.flyer = newFlyer
            }

            do {
                try await ck.updateEvent(event, newFlyer: newFlyer, newLogo: logo)
                ogEvent = event
                isEditing = false
                dismiss()
            } catch {
                saveError = "We couldn't save your changes. \(error.localizedDescription)"
            }
        }
    }
}
