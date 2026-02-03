//
//  DatePickeriWrestle.swift
//  iWrestle
//
//  Created by Brock Zacherl on 12/13/25.
//

import SwiftUI

struct DatePickeriWrestle: View {
    @Binding var eventDate: Date
    @State private var isShowingDatePicker: Bool = false
    var body: some View {
        Group{
            Button {
                withAnimation {
                    isShowingDatePicker.toggle()
                }
            } label: {
                HStack {
                    Text("Event Date")
                    Spacer()
                    Text(eventDate.formatted(date: .abbreviated, time: .omitted))
                        .foregroundStyle(.secondary)
                }
            }
            .buttonStyle(BorderlessButtonStyle())

            if isShowingDatePicker {
                DatePicker("Event Date", selection: $eventDate,displayedComponents: .date)
                    .datePickerStyle(.graphical)
                    .onChange(of: eventDate) {
                        withAnimation {
                            isShowingDatePicker = false
                        }
                    }
                    .onTapGesture(count: 99) {} // for some reason cant pick without this 😅
            }
        }
    }
}

//#Preview {
//    DatePickeriWrestle()
//}
