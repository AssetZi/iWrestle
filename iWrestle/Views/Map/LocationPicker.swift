//
//  LocationPicker.swift
//  iWrestle
//
//  Created by Brock Zacherl on 11/30/25.
//
//https://www.youtube.com/watch?v=U2kBmasBSTA how to video. 7:33

import SwiftUI
import CoreLocation
import MapKit

extension View {
    func locationPicker(isPresented: Binding<Bool>, mapItem: @escaping (MKMapItem?) -> ()) -> some View {
        self
            .fullScreenCover(isPresented: isPresented) {
                LocationPickerView(isPresented: isPresented, mapItem: mapItem)
            }
    }
}

fileprivate struct LocationPickerView: View {
    @Binding var isPresented: Bool
    var mapItem: (MKMapItem?) -> ()
    @Namespace private var mapSpace
    @FocusState private var isKeyboardActive: Bool
    @State private var manager: LocationManager = .init()
    
    @State private var selectedMapItem: MKMapItem?
    
    @Environment(\.openURL) private var openURL
    var body: some View {
        ZStack{
            if let isPermissionDenied = manager.isPermissionDenied {
                if isPermissionDenied{
                    UserPermissionDeniedView()
                } else {
                    ZStack{
                        SearchResultView()
                        MapDisplayView()
                            .safeAreaInset(edge: .bottom,spacing: 0) {
                                SelectLocationButton()
                            }
                            .opacity(manager.showSearchResults ? 0:1)
                            .ignoresSafeArea(.keyboard,edges: .all)
                    }
                    .safeAreaInset(edge: .top,spacing: 0) {
                        MapSearchBar()
                    }
                    
                    
                }
            } else {
                Rectangle()
                    .fill(.ultraThinMaterial)
                    .ignoresSafeArea()
                ProgressView()
            }
        }
        .onAppear(perform: manager.requestUserLocaiton)
        .animation(.easeInOut(duration: 0.25), value: manager.showSearchResults)
    }
    
    
    @ViewBuilder
    func UserPermissionDeniedView() -> some View {
        ZStack(alignment: .bottom) {
            Rectangle().fill(.ultraThinMaterial).ignoresSafeArea()
            Text("Please allow location permission\nin the app settings.")
                .fontWeight(.semibold).multilineTextAlignment(.center)
                .frame(maxWidth: .infinity, maxHeight: .infinity)
            
            Button {
                isPresented = false
            } label: {
                Image(systemName: "xmark")
                    .font(.title3)
                    .fontWeight(.semibold)
                    .foregroundStyle(Color.primary)
                    .padding(15)
                    .contentShape(.rect)
            }
            .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading)
            
            VStack(spacing: 12){
                Button("Try Again", action: manager.requestUserLocaiton)
                    .fontWeight(.semibold)
                    .foregroundStyle(.primary)
                Button {
                    if let settingsURL = URL(string: UIApplication.openSettingsURLString){
                        openURL(settingsURL)
                    }
                } label: {
                    Text("Go to Settings")
                        .fontWeight(.semibold)
                        .frame(maxWidth: .infinity)
                        .padding(.vertical,12)
                        .foregroundStyle(.background)
                        .background(Color.primary, in: .rect(cornerRadius: 12))
                }
                .padding(.horizontal, 30)
                .padding(.bottom,10)

            }

        }
    }
    
    @ViewBuilder
    func MapDisplayView() -> some View {
        Map(position: $manager.position, selection: $selectedMapItem){
            UserAnnotation()
            ForEach(manager.searchResults, id: \.self) { item in
                let coord = item.location.coordinate
                Marker(item.name ?? "Place", coordinate: coord)
                    .tag(item)
                    .tint(item == selectedMapItem ? .green : .red)
                    
            }
        }
        .mapControls {
            MapUserLocationButton(scope: mapSpace)
            MapCompass(scope: mapSpace)
            MapPitchToggle(scope: mapSpace)
        }
        .mapScope(mapSpace)
        .onMapCameraChange { ctx in
            manager.currentRegion = ctx.region
            Task{
                await manager.loadPOIs()
            }
//            selecedCoordinates = ctx.region.center
        }
    }
    
    @ViewBuilder
    func MapSearchBar() -> some View {
        VStack(spacing: 15) {
            Text("Select Location")
                .fontWeight(.semibold)
                .frame(maxWidth: .infinity)
                .overlay(alignment: .leading) {
                    Button {
                        if manager.showSearchResults {
                            isKeyboardActive = false
                            manager.clearSearch()
                            manager.showSearchResults = false
                        } else {
                            isPresented = false
                        }
                        
                        
                    } label: {
                        Image(systemName: "chevron.left")
                            .font(.title3)
                            .fontWeight(.semibold)
                            .foregroundStyle(Color.primary)
                            .contentShape(.rect)
                    }

                }
            
            HStack(spacing: 12) {
                Image(systemName: "magnifyingglass")
                    .foregroundStyle(.gray)
                TextField("Search", text: $manager.searchText)
                    .padding(.vertical,10)
                    .focused($isKeyboardActive)
                    .submitLabel(.search)
                    .onSubmit {
                        if manager.searchText.isEmpty {
                            manager.clearSearch()
                        } else {
                            manager.searchForPlaces()
                        }
                    }
                    .onChange(of: isKeyboardActive, { oldValue, newValue in
                        if newValue {
                            manager.showSearchResults = true
                        }
                    })
                    .contentShape(.rect)
                
                if manager.showSearchResults {
                    Button {
                        manager.clearSearch()
                    } label: {
                        Image(systemName: "xmark.circle.fill")
                            .font(.title3).foregroundStyle(.gray)
                    }
                    .opacity(manager.isSeaching ? 0 : 1)
                    .overlay{
                        ProgressView()
                            .opacity(manager.isSeaching ? 1 : 0)
                    }

                }
            }
            .padding(.horizontal,15)
            .background(.ultraThinMaterial, in: .rect(cornerRadius: 10))
        }
        .padding(15)
        .background(.background)
    }
    
    @ViewBuilder
    func SelectLocationButton() -> some View {
        Button {
            guard let item = selectedMapItem else { return }
            isPresented = false
            
            mapItem(item)
            
            
        } label: {
            Text("Select Location")
                .fontWeight(.semibold)
                .foregroundStyle(.primary)
                .frame(maxWidth: .infinity)
                .padding(.vertical,12)
                .background(.ultraThinMaterial, in: .rect(cornerRadius: 10))
        }
        .padding(15)
        .background(.background)

    }
    
    @ViewBuilder
    func SearchResultView() -> some View {
        ScrollView(.vertical) {
            LazyVStack(spacing: 15){
                ForEach(manager.searchResults, id: \.self){ mapItem in
                    SearchResultCard(mapItem).padding()
                }
            }
        }
        .frame(maxWidth: .infinity)
        .background(.background)
    }
    
    @ViewBuilder
    func SearchResultCard(_ mapItem: MKMapItem) -> some View {
        VStack(spacing: 10){
            HStack(spacing: 10){
                VStack(alignment: .leading,spacing: 8) {
                    Text(mapItem.name ?? "")
                    Text(mapItem.address?.fullAddress ?? "")
                        .font(.caption).foregroundStyle(.gray)
                    
                    
                }
                Spacer(minLength: 0)
                Image(systemName: "checkmark")
                    .font(.callout).foregroundStyle(.gray)
                    .opacity(manager.selectedResult == mapItem ? 1 : 0)
            }
            Divider()
        }
        .contentShape(.rect)
        .onTapGesture {
            isKeyboardActive = false
            // updating map position
            selectedMapItem = mapItem
            manager.updateMapPosition(mapItem)
        }
    }
}



