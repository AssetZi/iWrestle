//
//  HomeView.swift
//  iWrestle
//
//  Created by Brock Zacherl on 11/26/25.
//

import SwiftUI

struct HomeView: View {
//    @State private var events: [Event] = []
    @Environment(CloudKitManager.self) var ck
    @State private var viewState: ViewState = .loading
    var body: some View {
        NavigationStack {
            Group{
                switch viewState {
                case .loading:
                    iWrestleProgressView()
                case .loaded(let events):
                    ScrollView {
                        ForEach(events) { event in
                            NavigationLink{
                                EventDetailView(event: event)
                            } label:{
                                EventCell(event: event)
                            }
                        }
                    }
                case .error(let error):
                    ErrorViewiWrestle(error: error)
                    
                }
            }
            .navigationTitle(Text("iWrestle"))
            .task {
                loadEvents()
            }
        }
    }
    
    func loadEvents() {
        Task {
            let events = try await ck.fetchEvents()
            if !events.isEmpty {
                viewState = .loaded(events)
            } else {viewState = .error(.noData)}
        }
    }
    enum ViewState {
        case loading
        case loaded([Event])
        case error(iWrestleError)
    }
}

//#Preview {
//    HomeView()
//}
