import SwiftUI
import UniformTypeIdentifiers

struct iWrestlePDFPicker: View {
    let title: String
    @Binding var importedURL: URL?
    
    @State private var showImporter = false
    @State private var fileUploadSuccessful: Bool = false
    
    var body: some View {
        Button { showImporter = true } label: {
            HStack{
                Label(title, systemImage: "doc.text")
                Spacer()
                Text(importedURL != nil ? "✓" :"＋")
            }
            
        }
        .fileImporter(
            isPresented: $showImporter,
            allowedContentTypes: [.pdf],
            allowsMultipleSelection: false
        ) { result in
            do {
                guard let picked = try result.get().first else { return }
                // Access sandboxed file and copy into your app’s Documents
                let saved = try persistToDocuments(picked)
                DispatchQueue.main.async {
                    importedURL = saved
                }
            } catch {
                print("Import failed:", error.localizedDescription)
            }
        }

    }
}


/// Copies a security-scoped file URL into your app's Documents directory.
/// Returns the new URL inside your container.
private func persistToDocuments(_ sourceURL: URL) throws -> URL {
    let fm = FileManager.default
    let docs = fm.urls(for: .documentDirectory, in: .userDomainMask).first!
    let destination = docs.appendingPathComponent(sourceURL.lastPathComponent)

    var didStart = false
    if sourceURL.startAccessingSecurityScopedResource() { didStart = true }
    defer { if didStart { sourceURL.stopAccessingSecurityScopedResource() } }

    // If a file with same name exists, add a suffix.
    let finalURL = uniqueURL(for: destination)
    try fm.copyItem(at: sourceURL, to: finalURL)
    return finalURL
}

private func uniqueURL(for url: URL) -> URL {
    let fm = FileManager.default
    if !fm.fileExists(atPath: url.path) { return url }

    let baseName = url.deletingPathExtension().lastPathComponent
    let fileExtension = url.pathExtension
    let directory = url.deletingLastPathComponent()

    var i = 2
    while true {
        let candidateName = "\(baseName) \(i)"
        var candidate = directory.appendingPathComponent(candidateName)
        if !fileExtension.isEmpty {
            candidate = candidate.appendingPathExtension(fileExtension)
        }
        if !fm.fileExists(atPath: candidate.path) { return candidate }
        i += 1
    }
}
