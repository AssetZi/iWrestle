//
//  NotificationManager.swift
//  iWrestle
//
//  Created by Brock Zacherl on 12/18/25.
//

import Foundation
import Observation
import UserNotifications
import UIKit
import CoreLocation
import MapKit

@Observable
class NotificationManager {
    var ck = CloudKitManager()
    var numLocalEvents: Int = 0
    var permissionGranted: Bool = false
    init() {
        refreshAuthorizationStatus()
    }
    
    func requestPermission() {
        UNUserNotificationCenter.current().requestAuthorization(options: [.alert,.badge]) { success, error in
            if success {
                self.permissionGranted = true
                print("All Set")
            } else if let error {
                print(error.localizedDescription)
            }
        }
    }
    func refreshAuthorizationStatus() {
        UNUserNotificationCenter.current().getNotificationSettings { settings in
            DispatchQueue.main.async {
                self.permissionGranted = (settings.authorizationStatus == .authorized || settings.authorizationStatus == .provisional)
            }
        }
    }
    func scheduleNotification(userLocation: CLLocation) {
        Task {
            clearNotifications()
            let predicates = establishPredicates(userLocation: userLocation)
            let ok = await doPreWorkAsyncAwait(predicates: predicates)
            guard ok else {return}
            let content = UNMutableNotificationContent()
            content.title = "\(numLocalEvents) Events in your area this Week"
            content.body = "Check them out today!"
            
            let trigger = UNTimeIntervalNotificationTrigger(timeInterval: 60, repeats: true)
            
            let request = UNNotificationRequest(identifier: UUID().uuidString, content: content, trigger: trigger)
            
            UNUserNotificationCenter.current().add(request) { error in
                if let error {
                    print(error.localizedDescription)
                }
            }
        }
        
    }
    func scheduleWeeklyNotification(userLocation: CLLocation) { // 2 = Monday
        Task {
            // monday
            let weekday = 2
            let hour = 9
            let min = 0
            // 1) Compute right now (when scheduling)
            clearNotifications()
            let predicates = establishPredicates(userLocation: userLocation)
            let ok = await doPreWorkAsyncAwait(predicates: predicates)
            
            guard ok else { return }

            let content = UNMutableNotificationContent()
            content.title = "\(numLocalEvents) Events in your area this Week!"
            content.body = "Check them out today!"
            content.sound = .default

            var date = DateComponents()
            date.weekday = weekday
            date.hour = hour
            date.minute = min

            let trigger = UNCalendarNotificationTrigger(dateMatching: date, repeats: true)

            let request = UNNotificationRequest(
                identifier: "weekly-events-update", // stable id so you can replace it
                content: content,
                trigger: trigger
            )

            UNUserNotificationCenter.current().add(request) { error in
                if let error { print("Notification add error:", error) }
            }
        }
    }
    func doPreWorkAsyncAwait(predicates: [NSPredicate]) async -> Bool {
        // Perform async work here
        do {
            let events = try await ck.fetchEvents(predicates: predicates)
            numLocalEvents = events.count
            return true
        } catch {
            return false
        }
    }
    func clearNotifications() {
        UNUserNotificationCenter.current().removeAllPendingNotificationRequests()
    }
    func openAppSettings() {
        guard let url = URL(string: UIApplication.openSettingsURLString) else { return }
        if UIApplication.shared.canOpenURL(url) {
            UIApplication.shared.open(url, options: [:], completionHandler: nil)
        }
    }
    
    
    func establishPredicates(userLocation: CLLocation) -> [NSPredicate] {
        var predicates: [NSPredicate] = []
        let radiusInMeters = 200.milesToMeters
        let distancePredicate = NSPredicate(
            format: "distanceToLocation:fromLocation:(location, %@) < %f",
            userLocation,
            radiusInMeters
        )
        predicates.append(distancePredicate)
        
        
        guard
            let thisWeek = Calendar.current.dateInterval(of: .weekOfYear, for: Date()),
            let nextWeekStart = Calendar.current.date(
                byAdding: .weekOfYear,
                value: 1,
                to: thisWeek.start
            ),
            let nextWeekEndInclusive = Calendar.current.date(
                byAdding: .day,
                value: 1,
                to: thisWeek.end
            )
//            let interval = Calendar.current.dateInterval(of: .weekOfYear, for: nextWeekStart)
        else { return predicates }
        
        let datePredicate = NSPredicate(format: "date >= %@ AND date < %@", nextWeekStart as CVarArg, nextWeekEndInclusive as CVarArg)
        predicates.append(datePredicate)
        
        
        return predicates
    }
    
}
