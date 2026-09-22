//
//  LocationManager.swift
//  iWrestle
//
//  Created by Brock Zacherl on 12/4/25.
//

import Foundation
import SwiftUI
import CoreLocation
import MapKit
import Observation

@Observable
class LocationManager: NSObject, CLLocationManagerDelegate {
    var isPermissionDenied: Bool?
    // map properties
    var currentRegion: MKCoordinateRegion?
    var position: MapCameraPosition = .automatic
    var userCoordinates: CLLocationCoordinate2D?
    var userLocation: CLLocation?
    /// "Clarion, PA" — reverse-geocoded once per location fix for the home
    /// header. Nil until the lookup completes or when it fails.
    var userCity: String?
    
    // search properties
    var searchText: String = ""
    
    var searchResults: [MKMapItem] = []
    var selectedResult: MKMapItem?  
    var showSearchResults: Bool = false
    var isSeaching: Bool = false
    
    private var manager: CLLocationManager = .init()
    override init() {
        super.init()
        manager.delegate = self
    }
    
    func locationManagerDidChangeAuthorization(_ manager: CLLocationManager) {
        let status = manager.authorizationStatus
        guard status != .notDetermined else { return }
        
        isPermissionDenied = status == .denied
        if status != .denied {
            // fetch location
            manager.startUpdatingLocation()
        }
    }
    func locationManager(_ manager: CLLocationManager, didUpdateLocations locations: [CLLocation]) {
        guard let coordinates = locations.first?.coordinate else { return }
        
        //updating user cordinates
        userCoordinates = coordinates
        userLocation = locations.first
        if let location = locations.first { Self.store(lastKnown: location) }
        let region = MKCoordinateRegion(center: coordinates, latitudinalMeters: 1000, longitudinalMeters: 1000)
        position = .region(region)
        
        // stopping updates
        manager.stopUpdatingLocation()
        Task { await reverseGeocodeCity(locations.first) }
    }

    // MARK: - Last known location

    private static let lastLatitudeKey = "lastKnownLocation.latitude"
    private static let lastLongitudeKey = "lastKnownLocation.longitude"

    /// Saved so background work (the weekly digest refresh) has a location
    /// without waiting on CoreLocation, which it cannot do in the background.
    static func store(lastKnown location: CLLocation) {
        let defaults = UserDefaults.standard
        defaults.set(location.coordinate.latitude, forKey: lastLatitudeKey)
        defaults.set(location.coordinate.longitude, forKey: lastLongitudeKey)
    }

    /// The most recent fix from any earlier session, or nil if none was saved.
    static var lastKnownLocation: CLLocation? {
        let defaults = UserDefaults.standard
        guard
            let latitude = defaults.object(forKey: lastLatitudeKey) as? Double,
            let longitude = defaults.object(forKey: lastLongitudeKey) as? Double
        else { return nil }
        return CLLocation(latitude: latitude, longitude: longitude)
    }

    /// Resolves the user's city for the "Events near {city}." title.
    func reverseGeocodeCity(_ location: CLLocation?) async {
        guard let location, let request = MKReverseGeocodingRequest(location: location) else { return }
        guard let item = try? await request.mapItems.first else { return }
        let representations = item.addressRepresentations
        let city = representations?.cityWithContext ?? item.address?.shortAddress
        await MainActor.run { userCity = city }
    }
    func locationManager(_ manager: CLLocationManager, didFailWithError error: any Error) {
        /// handle errors
    }
    
    
    /// Additional Helper methods
    func requestUserLocaiton(){
        manager.requestWhenInUseAuthorization()
    }
    func searchForPlaces() {
        guard let currentRegion else { return }
        Task { @MainActor in
            isSeaching = true
            
            let request = MKLocalSearch.Request()
            request.region = currentRegion
            request.naturalLanguageQuery = searchText
            let search = MKLocalSearch(request: request)
            guard let response = try? await search.start() else {
                isSeaching = false
                return
            }
            
            searchResults = response.mapItems
            isSeaching = false
        }
    }
    func clearSearch() {
        searchText = ""
        searchResults = []
        
    }
    
    func updateMapPosition(_ mapItem: MKMapItem) {
        let coordinates = mapItem.location.coordinate
        let region = MKCoordinateRegion(center: coordinates, latitudinalMeters: 1000, longitudinalMeters: 1000)
        position = .region(region)
        selectedResult = mapItem
        showSearchResults = false
    }
    
    func loadPOIs() async {
        
        guard let currentRegion = currentRegion else { return }
//        guard let coordinates = userCoordinates else { return }
        let request = MKLocalPointsOfInterestRequest(coordinateRegion: currentRegion)
//        let reqestTwo = MKLocalPointsOfInterestRequest(center: coordinates, radius: 800)
        
        let search = MKLocalSearch(request: request)
        if let response = try? await search.start() {
            // A newer camera change already superseded this load; dropping the
            // response keeps a slow earlier search from overwriting a newer one.
            if Task.isCancelled { return }
            await MainActor.run {

                // clear all other results
                searchResults = response.mapItems
            }
        }
    }
}
