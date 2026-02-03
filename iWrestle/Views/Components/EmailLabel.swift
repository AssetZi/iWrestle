//
//  EmailLabel.swift
//  iWrestle
//
//  Created by Brock Zacherl on 12/12/25.
//

import SwiftUI

struct EmailLabel: View {
    let email: String
    var body: some View {
        if let mailURL = URL(string: "mailto:\(email)") {
            Link(destination: mailURL) {
                Label(email, systemImage: "envelope")
            }
        } else {
            Label(email, systemImage: "envelope")
        }
    }
}

//#Preview {
//    EmailLabel()
//}
