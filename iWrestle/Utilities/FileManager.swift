//
//  FileManager.swift
//  iWrestle
//
//  Created by Brock Zacherl on 11/26/25.
//

import Foundation

extension FileManager {
    func createTempFile(with data: Data, suggestedFilename: String) throws -> URL {
        let tempDir = temporaryDirectory
        let ext = (suggestedFilename as NSString).pathExtension
        let filename = UUID().uuidString + (ext.isEmpty ? "" : ".\(ext)")
        let url = tempDir.appendingPathComponent(filename)
        try data.write(to: url, options: [.atomic])
        return url
    }
}
