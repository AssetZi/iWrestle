//
//  iWrestlePhotoPicker.swift
//  iWrestle
//
//  Created by Brock Zacherl on 12/10/25.
//

import SwiftUI
import PhotosUI

/// Dashed upload row backed by PhotosPicker. Shows a thumbnail of the chosen
/// image, or of `existingLogoURL` on the edit screen until one is chosen.
struct iWrestlePhotoPicker: View {
    @State private var selectedItem: PhotosPickerItem?
    @Binding var image: UIImage?
    var title: String = "Upload event logo (required)"
    var isInvalid = false
    var existingLogoURL: URL? = nil

    var body: some View {
        PhotosPicker(selection: $selectedItem, matching: .images) {
            UploadRowLabel(icon: .image,
                           label: image == nil ? title : "Logo added",
                           filled: image != nil,
                           isInvalid: isInvalid) {
                if let image {
                    Image(uiImage: image)
                        .resizable()
                        .scaledToFill()
                        .frame(width: 28, height: 28)
                        .clipShape(RoundedRectangle(cornerRadius: 7, style: .continuous))
                } else if let existingLogoURL {
                    EventLogoView(url: existingLogoURL, name: "", size: 28, radius: 7, font: .monoIndex)
                }
            }
        }
        .buttonStyle(PressableButtonStyle())
        .onChange(of: selectedItem) { _, newItem in
            guard let newItem else { return }
            Task {
                if let data = try? await newItem.loadTransferable(type: Data.self) {
                    image = UIImage(data: data)
                }
            }
        }
    }
}
