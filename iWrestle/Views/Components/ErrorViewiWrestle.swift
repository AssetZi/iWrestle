//
//  ErrorViewiWrestle.swift
//  iWrestle
//
//  Created by Brock Zacherl on 12/11/25.
//

import SwiftUI

struct ErrorViewiWrestle: View {
    let error: iWrestleError
    var body: some View {
        ContentUnavailableView(error.title, systemImage: error.image, description: Text(error.description))
    }
}

#Preview {
    ErrorViewiWrestle(error: .noData)
}
