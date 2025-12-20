//
//  PhoneLabel.swift
//  iWrestle
//
//  Created by Brock Zacherl on 12/12/25.
//

import SwiftUI

struct PhoneLabel: View {
    let number: String
    var body: some View {
        let phoneDigits = number.filter { $0.isNumber || $0 == "+" }
        if let telURL = URL(string: "tel:\(phoneDigits)") {
            Link(destination: telURL) {
                Label(number, systemImage: "phone")
            }
        } else {
            Label(number, systemImage: "phone")
        }
    }
}


