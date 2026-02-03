//
//  FilterDatePickeriWrestle.swift
//  iWrestle
//
//  Created by Brock Zacherl on 12/17/25.
//

import SwiftUI

struct FilterDatePickeriWrestle: View {
    @Binding var selection: DateOptionsIWrestle
    @Binding var customDate: Date
    
    var body: some View {
        Section(header: Text("Filter by Date")) {
            VStack(spacing: 16) {
                Picker("Date Filter", selection: $selection) {
                    ForEach(DateOptionsIWrestle.allCases) { option in
                        Text(option.rawValue).tag(option)
                    }
                }
                .pickerStyle(.segmented)
                
                if selection == .select {
                    DatePicker(
                        "Select Date",
                        selection: $customDate,
                        displayedComponents: [.date]
                    )
                    .datePickerStyle(.graphical)
                }
                
                if let interval = selection.dateInterval(customDate: customDate) {
                    Text("\(interval.start.formatted(date: .abbreviated, time: .omitted)) – \(interval.end.formatted(date: .abbreviated, time: .omitted))")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                } else {
                    Text("No date interval")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
            }
        }
        
        
    }
    

    
}
//
//#Preview {
//    @Previewable @State var selection: DateOptionsIWrestle = .thisWeek
//    NavigationStack {
//        FilterDatePickeriWrestle(selection: $selection)
//    }
//}




enum DateOptionsIWrestle: String, CaseIterable, Identifiable {
    case thisWeek = "This Week"
    case nextWeek = "Next Week"
    case thisMonth = "This Month"
    case select = "Select Date"
    
    var id: String { rawValue }
    
    func dateInterval(customDate: Date = Date()) -> DateInterval? {
        let calendar = Calendar.current
        
        switch self {
        case .thisWeek:
            guard
                let thisWeek = calendar.dateInterval(of: .weekOfYear, for: Date()),
                let endInclusive = calendar.date(byAdding: .day, value: 1, to: thisWeek.end)
            else { return nil }
//            return calendar.dateInterval(of: .weekOfYear, for: Date())
            return DateInterval(start: thisWeek.start, end: endInclusive)
            
        case .nextWeek:
            guard
                let thisWeek = calendar.dateInterval(of: .weekOfYear, for: Date()),
                let nextWeekStart = calendar.date(byAdding: .weekOfYear, value: 1, to: thisWeek.start),
                let nextWeek = calendar.dateInterval(of: .weekOfYear, for: nextWeekStart),
                let nextWeekEndInclusive = calendar.date(byAdding: .day, value: 1, to: nextWeek.end)
            else { return nil }
            
            return DateInterval(start: nextWeekStart, end: nextWeekEndInclusive)
            
        case .thisMonth:
            let start = Date()
            guard let end = calendar.date(byAdding: .month, value: 1, to: start) else { return nil }
            return DateInterval(start: start, end: end)
            
        case .select:
            let startOfDay = calendar.startOfDay(for: customDate)
            guard let endOfDay = calendar.date(byAdding: .day, value: 1, to: startOfDay) else { return nil }
            return DateInterval(start: startOfDay, end: endOfDay)
        
        }
    }
}
