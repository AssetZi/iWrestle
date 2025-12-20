//
//  GetPhotoURL.swift
//  iWrestle
//
//  Created by Brock Zacherl on 12/10/25.
//

import Foundation
import SwiftUI
import CloudKit

extension CloudKitManager {
    func getPhotoURL(image: UIImage) -> URL? {
        guard let url = FileManager.default.urls(for: .cachesDirectory, in: .userDomainMask).first?.appendingPathComponent("buybitcoin.jpg") else {print("no url");return nil}
        guard let data = image.jpegData(compressionQuality: 1.0) else {print("no data");return nil}
        
        do {
            try data.write(to: url)
            return url
        } catch {
            print("ERROR writing to file: \(error.localizedDescription)")
            return nil
        }
    }
}
