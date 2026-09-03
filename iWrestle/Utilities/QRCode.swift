//
//  QRCode.swift
//  iWrestle
//
//  QR generation for the shared event PDF.
//

import CoreImage
import CoreImage.CIFilterBuiltins
import UIKit

enum QRCode {
    /// A QR code for `string` at `scale` pixels per module. Nil for empty input.
    /// Draw it with `.interpolation(.none)` so the modules stay crisp when zoomed.
    static func image(for string: String, scale: CGFloat = 12) -> UIImage? {
        let trimmed = string.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { return nil }

        let filter = CIFilter.qrCodeGenerator()
        filter.message = Data(trimmed.utf8)
        filter.correctionLevel = "M"

        guard let output = filter.outputImage?
            .transformed(by: CGAffineTransform(scaleX: scale, y: scale)),
              let cgImage = CIContext().createCGImage(output, from: output.extent)
        else { return nil }

        return UIImage(cgImage: cgImage)
    }
}
