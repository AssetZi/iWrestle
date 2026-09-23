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

    /// The user's actual choice, owned here rather than by the Map.
    ///
    /// `Map(selection:)` clears itself whenever the tapped item's `.tag()` leaves
    /// the rendered content, and `loadPOIs()` replaces `searchResults` wholesale on
    /// every camera settle. Since `MKMapItem` compares by pointer identity, a
    /// refetched place is a different object, so relying on `selectedMapItem` alone
    /// loses the choice as soon as the map recenters — which is exactly what
    /// tapping a search result does.
    @State private var chosenMapItem: MKMapItem?
    @State private var poiTask: Task<Void, Never>?

    @Environment(\.openURL) private var openURL

    private var chosenAddress: String? { chosenMapItem?.address?.fullAddress }
    private var canSelect: Bool { chosenAddress != nil }
    private var selectButtonTitle: String {
        if chosenMapItem == nil { return "Tap a place to select it" }
        if chosenAddress == nil { return "That place has no address — pick another" }
        return "Select Location"
    }

    var body: some View {
        ZStack{
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

            if manager.isPermissionDenied == true {
                UserPermissionDeniedView()
            }
        }
        .background(Theme.ink.ignoresSafeArea())
        .preferredColorScheme(.dark)
        .onAppear(perform: manager.requestUserLocaiton)
        .onDisappear { poiTask?.cancel() }
        .onChange(of: selectedMapItem) { _, newValue in
            // Only ever promote a real selection; ignore the nil the Map writes
            // back when a refetch drops the tag out from under us.
            if let newValue { chosenMapItem = newValue }
        }
        .animation(.easeInOut(duration: 0.25), value: manager.showSearchResults)
    }
    
    
    @ViewBuilder
    func UserPermissionDeniedView() -> some View {
        ZStack(alignment: .bottom) {
            Rectangle().fill(Theme.scrim).ignoresSafeArea()
            Text("Please allow location permission\nin the app settings.")
                .font(.body14Medium)
                .foregroundStyle(Theme.textPrimary)
                .multilineTextAlignment(.center)
                .frame(maxWidth: .infinity, maxHeight: .infinity)
            
            Button {
                isPresented = false
            } label: {
                IconButtonLabel(icon: .x, size: 34, radius: 10, iconSize: 15, strokeWidth: 2)
                    .padding(15)
            }
            .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading)
            
            VStack(spacing: 12){
                Button("Try again", action: manager.requestUserLocaiton)
                    .font(.body13)
                    .foregroundStyle(Theme.textTertiary)
                    .buttonStyle(.plain)
                PrimaryGoldButton(title: "Go to Settings", icon: .arrowUpRight) {
                    if let settingsURL = URL(string: UIApplication.openSettingsURLString){
                        openURL(settingsURL)
                    }
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
                    .tint(item == chosenMapItem ? Theme.gold : Theme.slate400)

            }
        }
        .mapControls {
            MapUserLocationButton(scope: mapSpace)
            MapCompass(scope: mapSpace)
            MapPitchToggle(scope: mapSpace)
        }
        .mapScope(mapSpace)
        .mapStyle(.standard(elevation: .flat, emphasis: .muted, showsTraffic: false))
        .onMapCameraChange { ctx in
            manager.currentRegion = ctx.region
            // Cancel the in-flight load so a slow earlier response can't land
            // after a newer one and clobber the marker list.
            poiTask?.cancel()
            poiTask = Task{
                await manager.loadPOIs()
            }
//            selecedCoordinates = ctx.region.center
        }
    }
    
    @ViewBuilder
    func MapSearchBar() -> some View {
        VStack(spacing: 15) {
            Text("Select location")
                .font(.cardTitle)
                .foregroundStyle(Theme.textPrimary)
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
                        IconButtonLabel(icon: .chevronLeft, size: 34, radius: 10, iconSize: 16, strokeWidth: 2)
                    }
                    .buttonStyle(PressableButtonStyle())

                }
            
            HStack(spacing: 12) {
                LucideIcon(.search, size: 15)
                    .foregroundStyle(Theme.textTertiary)
                TextField("", text: $manager.searchText, prompt: Text("Search places").foregroundColor(Theme.slate500))
                    .font(.body14)
                    .foregroundStyle(Theme.textPrimary)
                    .tint(Theme.gold)
                    .padding(.vertical,12)
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
                        LucideIcon(.x, size: 15, strokeWidth: 2)
                            .foregroundStyle(Theme.textTertiary)
                    }
                    .opacity(manager.isSeaching ? 0 : 1)
                    .overlay{
                        GoldSpinner(size: 16)
                            .opacity(manager.isSeaching ? 1 : 0)
                    }

                }
            }
            .padding(.horizontal,14)
            .background(RoundedRectangle(cornerRadius: Theme.Radius.input, style: .continuous).fill(Theme.slate950))
            .overlay(RoundedRectangle(cornerRadius: Theme.Radius.input, style: .continuous).strokeBorder(Theme.borderDefault, lineWidth: 1))
        }
        .padding(15)
        .background(Theme.ink)
    }
    
    @ViewBuilder
    func SelectLocationButton() -> some View {
        Button {
            guard let item = chosenMapItem, chosenAddress != nil else { return }
            isPresented = false

            mapItem(item)


        } label: {
            Text(selectButtonTitle)
                .font(.buttonLabel)
                // .disabled() alone won't dim a label whose colour is pinned, so
                // the disabled state sets its own colour and opacity.
                .foregroundStyle(canSelect ? Theme.onAccent : Theme.textSecondary)
                .frame(maxWidth: .infinity)
                .padding(.vertical,14)
                .background(RoundedRectangle(cornerRadius: Theme.Radius.button, style: .continuous)
                    .fill(canSelect ? Theme.gold : Theme.slate900))
                .overlay(RoundedRectangle(cornerRadius: Theme.Radius.button, style: .continuous)
                    .strokeBorder(canSelect ? .clear : Theme.borderDefault, lineWidth: 1))
        }
        .buttonStyle(PressableButtonStyle(scale: 0.99))
        .disabled(!canSelect)
        .padding(15)
        .background(Theme.ink)

    }
    
    @ViewBuilder
    func SearchResultView() -> some View {
        ScrollView(.vertical) {
            LazyVStack(spacing: 4){
                ForEach(manager.searchResults, id: \.self){ mapItem in
                    SearchResultCard(mapItem)
                        .padding(.horizontal, Theme.gutter)
                        .padding(.vertical, 8)
                }
            }
        }
        .frame(maxWidth: .infinity)
        .background(Theme.ink)
    }
    
    @ViewBuilder
    func SearchResultCard(_ mapItem: MKMapItem) -> some View {
        VStack(spacing: 10){
            HStack(spacing: 10){
                VStack(alignment: .leading,spacing: 4) {
                    Text(mapItem.name ?? "")
                        .font(.rowTitle)
                        .foregroundStyle(Theme.textPrimary)
                    Text(mapItem.address?.fullAddress ?? "")
                        .font(.body12).foregroundStyle(Theme.textTertiary)
                }
                Spacer(minLength: 0)
                LucideIcon(.check, size: 16, strokeWidth: 2)
                    .foregroundStyle(Theme.gold)
                    .opacity(manager.selectedResult == mapItem ? 1 : 0)
            }
            HairlineDivider()
        }
        .contentShape(.rect)
        .onTapGesture {
            isKeyboardActive = false
            // updating map position
            selectedMapItem = mapItem
            // Set the choice directly: updateMapPosition moves the camera, which
            // refetches POIs and drops this item's tag, clearing selectedMapItem.
            chosenMapItem = mapItem
            manager.updateMapPosition(mapItem)
        }
    }
}



