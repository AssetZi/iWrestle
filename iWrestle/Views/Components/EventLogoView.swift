//
//  EventLogoView.swift
//  iWrestle
//
//  Created by Brock Zacherl on 12/12/25.
//

import SwiftUI

struct EventLogoView: View {
    let url: URL

    var body: some View {
        // If event.logo is a remote URL (http/https), use AsyncImage
        // If it's a file URL, you can still use AsyncImage in iOS 17+, or load via a task below.
        AsyncImage(url: url) { phase in
            switch phase {
            case .empty:
                placeholder
            case .success(let image):
                image
                    .resizable()
                    .scaledToFit()
                    
                    
            case .failure:
                placeholder
            @unknown default:
                placeholder
            }
        }
        .cornerRadius(10)
        .frame(width: 100,height: 100)
        
    }

    private var placeholder: some View {
        RoundedRectangle(cornerRadius: 10, style: .continuous)
            .fill(.secondary.opacity(0.2))
            .overlay {
                Image(systemName: "photo")
                    .foregroundStyle(.secondary)
            }
    }
}


#Preview {
    EventLogoView(url: URL(string: "https://dxbhsrqyrr690.cloudfront.net/sidearm.nextgen.sites/clariongoldeneagles.com/images/2025/10/23/_Zacherl_Brock.jpg?width=300")!)
}
