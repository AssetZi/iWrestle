//
//  CloudKitManager.swift
//  iWrestle
//
//  Created by Brock Zacherl on 12/9/25.
//

// ck assest tutorial https://www.youtube.com/watch?v=AtFMqG-zziA
// chat tutorial //  https://chatgpt.com/share/69383df1-a088-800a-9824-030b3b5b545a

import Foundation
import CloudKit
import Observation

@Observable
class CloudKitManager {
    var isSignedIn: Bool = false
    var permissionStatus: Bool = false
    var isAdmin: Bool = false 
    var error: String = ""
    var userRef: CKRecord.Reference?
    
    
    init () {
        getiCloudStatus()
//        requestPermission()
        fetchUserRecordId()
    }
    
    func getiCloudStatus() {
        CKContainer.default().accountStatus { [weak self] returnStatus, returnedError in
            DispatchQueue.main.async {
                switch returnStatus {
                case .couldNotDetermine:
                    self?.error = CloudkitError.notDetermined.localizedDescription
                    print("could not determine")
                case .available:
                    self?.isSignedIn = true
                case .restricted:
                    self?.error = CloudkitError.restricted.localizedDescription
                    print("restricted")
                case .noAccount:
                    self?.error = CloudkitError.accountNotFound.localizedDescription
                    print("account not found")
                case .temporarilyUnavailable:
                    self?.error = CloudkitError.tempUnavailable.localizedDescription
                    print("temp unavailable")
                default :
                    self?.error = CloudkitError.unknown.localizedDescription
                    print("default error")
                }
            }
        }
    }
    func fetchUserRecordId() {
        CKContainer.default().fetchUserRecordID { [weak self] returnRecord, returnedError in
            if let id = returnRecord {
                self?.userRef = CKRecord.Reference(recordID: id, action: .deleteSelf)
                self?.isAdmin = id.recordName == admin
//                self?.discoveriCloudUser(id)
            }
        }
    }
    func saveCkRecord(_ record: CKRecord) async -> Bool {
        do {
           try await CKContainer.default().publicCloudDatabase.save(record)
            return true
        } catch {
            print("Error saving record: \(error)")
            return false
        }
    }
    func getUserReference() async -> CKRecord.Reference? {
        do {
            let container = CKContainer.default()
            let userRecordID = try await container.userRecordID()
            // Create a reference to the user's record with no delete action
            let reference = CKRecord.Reference(recordID: userRecordID, action: .none)
            return reference
        } catch {
            print("Error getting user reference: \(error.localizedDescription)")
            return nil
        }
    }
//    func requestPermission() {
//        // read a doc that makes it seem like i can delete this???
//        CKContainer.default().requestApplicationPermission(.userDiscoverability) {[weak self] returnedStatus, returnedError in
//            DispatchQueue.main.async {
//                if returnedStatus == .granted {
//                    self?.permissionStatus = true
//                }
//            }
//        }
//    }
    
    
    enum CloudkitError: LocalizedError {
        case accountNotFound,notDetermined,restricted,tempUnavailable, unknown
    }
}
