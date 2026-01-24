//
//  UserEvents.swift
//  iWrestle
//
//  Created by Brock Zacherl on 12/11/25.
//

import SwiftUI

struct UserEventsView: View {
    @Environment(CloudKitManager.self) var ck
    @Binding var userEvents: [Event]
    @State private var viewState: ViewState = .loading
    
    enum ViewState {
        case loading
        case loaded
        case error(iWrestleError)
    }
    var body: some View {
        Group {
            switch viewState {
            case .loading:
                iWrestleProgressView()
            case .loaded:
                eventList()
            case .error(let iWrestleError):
                ErrorViewiWrestle(error: iWrestleError, action: {})
            }
        }
        .task {
            loadUserEvents()
        }
        .navigationTitle(Text("Events Dashboard"))
    }
    
    @ViewBuilder
    func eventRow(_ event: Event) -> some View {
        HStack {
            if let data = try? Data(contentsOf: event.logo), let image = UIImage(data: data) {
                Image(uiImage: image)
                    .resizable()
                    .scaledToFill()
                    .frame(width: 44, height: 44)
                    .clipShape(RoundedRectangle(cornerRadius: 8, style: .continuous))
            }
            Text(event.name)
            Spacer()
            Text("\(event.date, format: .dateTime)")
        }
    }
    func eventList() -> some View {
        ScrollView {
            ForEach($userEvents) { $event in
                NavigationLink {
                    UserEventDetailView(ogEvent: $event, event: event)
                } label: {
                    EventCell(event: event, userLocation: nil)
                }

            }
        }
        .refreshable {
            loadUserEvents()
        }
    }
    
    func loadUserEvents() {
        Task {
            do {
                if userEvents.isEmpty {
                    userEvents = try await ck.fetchUserEvents()
                    if !userEvents.isEmpty {
                        viewState = .loaded
                    } else {
                        viewState = .error(.noUserEvents)
                    }
                }
                else {viewState = .loaded}
            } catch {
                viewState = .error(.noUserEvents)
            }
        }
    }
}

//#Preview {
//    UserEventsView(userEvents: )
//}
