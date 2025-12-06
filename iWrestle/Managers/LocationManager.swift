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
        let region = MKCoordinateRegion(center: coordinates, latitudinalMeters: 1000, longitudinalMeters: 1000)
        position = .region(region)
        
        // stopping updates
        manager.stopUpdatingLocation()
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
            await MainActor.run {
                
                // clear all other results 
                searchResults = response.mapItems
            }
        }
    }
}
