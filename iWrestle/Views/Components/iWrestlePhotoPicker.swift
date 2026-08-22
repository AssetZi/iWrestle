//
//  iWrestlePhotoPicker.swift
//  iWrestle
//
//  Created by Brock Zacherl on 12/10/25.
//

import SwiftUI
import PhotosUI

struct iWrestlePhotoPicker: View {
    @State private var selectedItem: PhotosPickerItem?
    @State private var imageData: Data?
    @Binding var image: UIImage?
    /// Defaulted so the edit screen keeps its existing wording; the add screens
    /// pass a title marked "(Required)".
    var title: String = "Upload Event Logo"
    var body: some View {
        PhotosPicker(selection: $selectedItem,matching: .images) {
            myview()
        }
        .onChange(of: selectedItem) { _, newItem in
            guard let newItem else { return }
            Task {
                if let data = try? await newItem.loadTransferable(type: Data.self) {
                    imageData = data
                    image = UIImage(data: data)
                }
            }
        }
    }
    
    
    func myview() -> some View {
        HStack {
            Label(title, systemImage: "photo")
            Spacer()
            if let uiImage = image {
                Image(uiImage: uiImage)
                    .resizable()
                    .scaledToFit()
                    .frame(height: 50)
                    .clipShape(RoundedRectangle(cornerRadius: 12))
            } else {
                Text("＋")
            }
        }
    }
}

//#Preview {
//    iWrestlePhotoPicker(image: )
//}


