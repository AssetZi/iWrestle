//
//  EventsFilterView.swift
//  iWrestle
//
//  Bottom sheet that edits a draft copy of the home filters. The Apply
//  button carries a live count. Counting asks CloudKit for record IDs only,
//  and each answer is cached per filter combination, so opening the sheet
//  or switching back to a combination already seen costs nothing. Apply
//  hands the filters back and HomeView loads the events itself.
//

import SwiftUI
import CoreLocation

struct EventsFilterView: View {
    @Environment(CloudKitManager.self) var ck
    @Environment(LocationManager.self) var lm
    @Environment(\.dismiss) var dismiss

    /// The filters HomeView is showing now.
    let filters: EventFilters
    /// Whether HomeView has a list on screen for `filters`. If it does not
    /// (still loading, or failed), Apply reloads even without changes.
    let homeIsLoaded: Bool
    let onApply: (EventFilters) -> Void

    @State private var draft: EventFilters
    /// Known counts by filter combination, seeded with what HomeView shows.
    @State private var counts: [EventFilters: Int]
    @State private var status: Status = .idle
    /// Bumped by Retry so the count task runs again for the same draft.
    @State private var attempt = 0
    @State private var sheetHeight: CGFloat = 600

    enum Status { case idle, counting, needsLocation, failed }

    private struct CountKey: Equatable {
        let draft: EventFilters
        let attempt: Int
    }

    /// - Parameter currentCount: how many events HomeView is showing for
    ///   `filters`, or nil when it has no list on screen.
    init(filters: EventFilters, currentCount: Int?, onApply: @escaping (EventFilters) -> Void) {
        self.filters = filters
        self.homeIsLoaded = currentCount != nil
        self.onApply = onApply
        _draft = State(initialValue: filters)
        _counts = State(initialValue: currentCount.map { [filters: $0] } ?? [:])
    }

    var body: some View {
        VStack(spacing: 16) {
            DragHandle()

            HStack(alignment: .firstTextBaseline) {
                Text("Filter events")
                    .font(.sheetTitle)
                    .tracked(-0.01, 17)
                    .foregroundStyle(Theme.textPrimary)
                Spacer()
                Button("Clear") {
                    withAnimation(Motion.fast) { draft = .default }
                }
                .font(.body12)
                .foregroundStyle(Theme.textTertiary)
                .buttonStyle(.plain)
            }

            chipGroup("Event type", EventTypeFilter.allCases, selection: $draft.eventType) { $0.title }
            chipGroup("Age group", AgeGroupFilter.allCases, selection: $draft.ageGroup) { $0.title }
            chipGroup("Distance", DistanceOption.allCases, selection: $draft.distance) { $0.title }
            chipGroup("Date", DateOptionsIWrestle.allCases, selection: $draft.date) { $0.rawValue }

            switch status {
            case .needsLocation:
                Text("Enable location to filter by distance.")
                    .font(.caption11_5)
                    .foregroundStyle(Theme.danger)
                    .frame(maxWidth: .infinity, alignment: .leading)
            case .failed:
                HStack {
                    Text("Couldn't load the count.")
                        .font(.caption11_5)
                        .foregroundStyle(Theme.textTertiary)
                    Spacer()
                    Button("Retry") { attempt += 1 }
                        .font(.caption11_5)
                        .foregroundStyle(Theme.gold)
                        .buttonStyle(.plain)
                }
            case .idle, .counting:
                EmptyView()
            }

            PrimaryGoldButton(title: applyTitle) { apply() }
                .disabled(status == .needsLocation)
                .padding(.top, 4)
        }
        .padding(.horizontal, Theme.gutter)
        .padding(.bottom, 6)
        // The sheet sizes itself to the content; the device's bottom safe area
        // supplies the rest of the mock's 34pt bottom padding.
        .onGeometryChange(for: CGFloat.self) { $0.size.height } action: { sheetHeight = $0 }
        .frame(maxHeight: .infinity, alignment: .top)
        .background(Theme.slate900)
        .presentationDetents([.height(sheetHeight)])
        .presentationDragIndicator(.hidden)
        .presentationBackground(Theme.slate900)
        .presentationCornerRadius(Theme.Radius.sheet)
        .task(id: CountKey(draft: draft, attempt: attempt)) { await refreshCount() }
    }

    private func chipGroup<T: Hashable & Identifiable>(_ label: String,
                                                        _ options: [T],
                                                        selection: Binding<T>,
                                                        title: @escaping (T) -> String) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            Eyebrow(label, color: Theme.textTertiary, size: 10)
            ChipFlow {
                ForEach(options) { option in
                    SelectChip(label: title(option), selected: option == selection.wrappedValue) {
                        selection.wrappedValue = option
                    }
                }
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }

    private var applyTitle: String {
        if let count = counts[draft] {
            if count >= FetchLimits.filtered { return "Show \(FetchLimits.filtered)+ events" }
            return count == 1 ? "Show 1 event" : "Show \(count) events"
        }
        switch status {
        case .needsLocation, .failed: return "Show events"
        case .idle, .counting: return "Show … events"
        }
    }

    // MARK: - Counting

    private func refreshCount() async {
        if counts[draft] != nil {
            status = .idle
            return
        }
        guard let predicates = draft.predicates(userLocation: lm.userLocation) else {
            status = .needsLocation
            return
        }
        status = .counting
        let snapshot = draft
        do {
            // Debounce so tapping through chips doesn't fire a query per tap.
            try await Task.sleep(for: .milliseconds(300))
            #if DEBUG
            if MockEvents.isEnabled {
                let local = NSCompoundPredicate(andPredicateWithSubpredicates: predicates.filter { !$0.predicateFormat.contains("distanceToLocation") })
                counts[snapshot] = MockEvents.nearby.filter { local.evaluate(with: MockEvents.predicateObject($0)) }.count
                status = .idle
                return
            }
            #endif
            let ck = self.ck
            let count = try await withTimeout(.seconds(15)) {
                try await ck.countEvents(predicates: predicates)
            }
            // Keep the answer even if the draft has moved on; it is still
            // right for `snapshot` if the user comes back to it.
            counts[snapshot] = count
            if !Task.isCancelled { status = .idle }
        } catch {
            // Cancellation means the draft changed, not that anything failed.
            guard !Task.isCancelled else { return }
            status = .failed
        }
    }

    private func apply() {
        if draft != filters || !homeIsLoaded {
            onApply(draft)
        }
        dismiss()
    }
}
