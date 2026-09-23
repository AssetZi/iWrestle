//
//  HideKeyboard.swift
//  iWrestle
//
//  Created by Brock Zacherl on 12/10/25.
//

import Foundation
import SwiftUI

extension View {
    /// Dismisses the keyboard when the user taps empty space behind this view's
    /// content.
    ///
    /// Implemented as a background layer rather than a gesture on the view
    /// itself: an ancestor `onTapGesture` steals single taps from UIKit-backed
    /// children (notably the graphical `DatePicker`), so a day cell only
    /// registers on a second simultaneous touch.
    ///
    /// Apply this to scroll *content*, never to a `ScrollView`. `UIScrollView`
    /// claims every hit inside its bounds, so a layer behind it never fires.
    func hideKeyboardOnTap() -> some View {
        background {
            Color.clear
                .contentShape(Rectangle())
                .onTapGesture {
                    UIApplication.shared.sendAction(#selector(UIResponder.resignFirstResponder),
                                                    to: nil, from: nil, for: nil)
                }
        }
    }
}
