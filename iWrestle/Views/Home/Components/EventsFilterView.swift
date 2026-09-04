//
//  EventsFilterView.swift
//  iWrestle
//
//  Bottom sheet that edits a draft copy of the home filters. The Apply
//  button carries a live count, fetched (debounced) as the draft changes;
//  Apply hands the already-fetched events back so nothing is queried twice.
//

import SwiftUI
import CoreLocation

struct EventsFilterView: View {
    @Environment(CloudKitManager.self) var ck
    @Environment(LocationManager.self) var lm
    @Environment(\.dismiss) var dismiss

    let onApply: (EventFilters, [Event]) -> Void
    @State private var draft: EventFilters
    @State private var count: CountState = .idle
    @State private var isApplying = false
    @State private var sheetHeight: CGFloat = 600

    enum CountState: Equatable {
        case idle, counting, needsLocation
        case counted(EventFilters, [Event])

        static func == (lhs: CountState, rhs: CountState) -> Bool {
            switch (lhs, rhs) {
            case (.idle, .idle), (.counting, .counting), (.needsLocation, .needsLocation): return true
            case (.counted(let a, let x), .counted(let b, let y)): return a == b && x.map(\.id) == y.map(\.id)
            default: return false
            }
        }
    }

    init(filters: EventFilters, onApply: @escaping (EventFilters, [Event]) -> Void) {
        self.onApply = onApply
        _draft = State(initialValue: filters)
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

            if count == .needsLocation {
                Text("Enable location to filter by distance.")
                    .font(.caption11_5)
                    .foregroundStyle(Theme.danger)
                    .frame(maxWidth: .infinity, alignment: .leading)
            }

            PrimaryGoldButton(title: applyTitle, isBusy: isApplying) { apply() }
                .disabled(count == .needsLocation)
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
        .interactiveDismissDisabled(isApplying)
        .task(id: draft) { await refreshCount() }
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
        switch count {
        case .counted(let filters, let events) where filters == draft:
            return events.count == 1 ? "Show 1 event" : "Show \(events.count) events"
        case .needsLocation:
            return "Show events"
        default:
            return "Show … events"
        }
    }

    // MARK: - Fetching

    private func refreshCount() async {
        guard let predicates = draft.predicates(userLocation: lm.userLocation) else {
            count = .needsLocation
            return
        }
        count = .counting
        // Debounce so tapping through chips doesn't fire a query per tap.
        try? await Task.sleep(for: .milliseconds(300))
        guard !Task.isCancelled else { return }
        let snapshot = draft
        #if DEBUG
        if MockEvents.isEnabled {
            let filtered = MockEvents.nearby.filter { NSCompoundPredicate(andPredicateWithSubpredicates: predicates.filter { !$0.predicateFormat.contains("distanceToLocation") }).evaluate(with: MockEvents.predicateObject($0)) }
            count = .counted(snapshot, filtered)
            return
        }
        #endif
        if let events = try? await ck.fetchEvents(predicates: predicates), !Task.isCancelled {
            count = .counted(snapshot, events)
        } else if !Task.isCancelled {
            count = .idle
        }
    }

    private func apply() {
        if case .counted(let filters, let events) = count, filters == draft {
            onApply(draft, events)
            dismiss()
            return
        }
        guard let predicates = draft.predicates(userLocation: lm.userLocation) else {
            count = .needsLocation
            return
        }
        isApplying = true
        Task {
            let events = (try? await ck.fetchEvents(predicates: predicates)) ?? []
            isApplying = false
            onApply(draft, events)
            dismiss()
        }
    }
}
