//
//  DatePickeriWrestle.swift
//  iWrestle
//
//  Created by Brock Zacherl on 12/13/25.
//

import SwiftUI

/// Graphical calendar in a dark card, gold tint.
struct EventDateCalendar: View {
    @Binding var date: Date

    var body: some View {
        DatePicker("Event date", selection: $date, displayedComponents: .date)
            .datePickerStyle(.graphical)
            .tint(Theme.gold)
            .padding(8)
            .background(RoundedRectangle(cornerRadius: Theme.Radius.input, style: .continuous).fill(Theme.slate950))
            .overlay(
                RoundedRectangle(cornerRadius: Theme.Radius.input, style: .continuous)
                    .strokeBorder(Theme.borderDefault, lineWidth: 1)
            )
    }
}

/// Date row that expands into the calendar below it.
struct DatePickeriWrestle: View {
    @Binding var eventDate: Date
    @State private var isShowingDatePicker: Bool = false

    var body: some View {
        VStack(spacing: 10) {
            FormRowButton(icon: .calendar, text: eventDate.shortDayLabel) {
                withAnimation(Motion.normal) { isShowingDatePicker.toggle() }
            }
            if isShowingDatePicker {
                EventDateCalendar(date: $eventDate)
                    .onChange(of: eventDate) {
                        withAnimation(Motion.normal) { isShowingDatePicker = false }
                    }
            }
        }
    }
}
