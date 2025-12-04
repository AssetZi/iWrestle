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
}
