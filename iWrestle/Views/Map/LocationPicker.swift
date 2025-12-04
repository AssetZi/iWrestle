//
//  LocationPicker.swift
//  iWrestle
//
//  Created by Brock Zacherl on 11/30/25.
//
//https://www.youtube.com/watch?v=U2kBmasBSTA how to video. 7:33

import SwiftUI
import CoreLocation
import MapKit

extension View {
    func locationPicker(isPresented: Binding<Bool>, coordinates: @escaping (CLLocationCoordinate2D?) -> ()) -> some View {
        self
            .fullScreenCover(isPresented: isPresented) {
                LocationPickerView(isPresented: isPresented, coordinates: coordinates)
            }
    }
}

fileprivate struct LocationPickerView: View {
    @Binding var isPresented: Bool
    var coordinates: (CLLocationCoordinate2D?) -> ()
    
    @State private var manager: LocationManager = .init()
    var body: some View {
        ZStack{
            if let isPermissionDenied = manager.isPermissionDenied {
                if isPermissionDenied{
                    
                } else {
                    
                }
            } else {
                Rectangle()
                    .fill(.ultraThinMaterial)
                    .ignoresSafeArea()
                ProgressView()
            }
        }.onAppear(perform: manager.requestUserLocaiton)
    }
    
    
    @ViewBuilder
    func UserPermissionDeniedView() -> some View {
        ZStack(alignment: .bottom) {
            Rectangle().fill(.ultraThinMaterial).ignoresSafeArea()
            Text("Please allow location permission\nin the app settings.")
                .fontWeight(.semibold).multilineTextAlignment(.center)
            
            Button {
                isPresented = false
            } label: {
                Image(systemName: "xmark")
                    .font(.title3)
                    .fontWeight(.semibold)
                    .foregroundStyle(Color.gray)
                    .contentShape(.rect)
            }
            
            VStack(spacing: 12){
                
            }

        }
    }
}



