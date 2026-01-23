//
//  ErrorViewiWrestle.swift
//  iWrestle
//
//  Created by Brock Zacherl on 12/11/25.
//

import SwiftUI

struct ErrorViewiWrestle: View {
    let error: iWrestleError
    let action: () -> Void
    @State private var manager: LocationManager = .init()
    @State private var isLoading: Bool = false
    @Environment(\.openURL) private var openURL
    var body: some View {
        Group{
            ContentUnavailableView(error.title, systemImage: error.image, description: Text(error.description))
            if error == .locationError{
                locationErrorButton()
            }
        }
    }
    
    func locationErrorButton() -> some View{
        VStack(spacing: 12){
            Button {
                isLoading = true
                action()
            } label: {
                if isLoading{ProgressView()} else {
                    Text("Continue Without Location")
                        .fontWeight(.semibold)
                }
            }
            .disabled(isLoading)
            Button {
                if let settingsURL = URL(string: UIApplication.openSettingsURLString){
                    openURL(settingsURL)
                }
            } label: {
                Text("Go to Settings")
                    .fontWeight(.semibold)
                    .frame(maxWidth: .infinity)
                    .padding(.vertical,12)
                    .foregroundStyle(.background)
                    .background(Color.primary, in: .rect(cornerRadius: 12))
            }
            .padding(.horizontal, 30)
            .padding(.bottom,10)

        }
    }
}

//#Preview {
//    ErrorViewiWrestle(error: .noData)
//}
