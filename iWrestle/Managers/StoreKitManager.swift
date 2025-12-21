//
//  StoreKitManager.swift
//  iWrestle
//
//  Created by Brock Zacherl on 12/20/25.
//

import Foundation
import StoreKit
import Observation

@Observable @MainActor
class StoreKitManager {
    var products: [Product] = []
    var isPurchasing = false
    
    let productIDs = ["event_purchase","event_with_logo_gen"]
    
    
    func loadProducts() async throws {
        products = try await Product.products(for: productIDs)
        product = products.first(where: { $0.id == productIDs[0] })
    }

    var product: Product?

    enum PurchaseResult {
        case success(transaction: Transaction)
        case cancelled
        case pending
    }

    func purchaseListing(logoGen: Bool) async throws -> PurchaseResult {
        if logoGen {
            product = products.first(where: { $0.id == productIDs[1] })
            
        }
        
        guard let product else {
            throw NSError(domain: "StoreKitManager", code: 1, userInfo: [NSLocalizedDescriptionKey: "Product not loaded"])
        }

        isPurchasing = true
        

        let result = try await product.purchase()

        switch result {
        case .success(let verification):
            let transaction = try checkVerified(verification)
            await transaction.finish()
            return .success(transaction: transaction)

        case .userCancelled:
            return .cancelled

        case .pending:
            return .pending

        @unknown default:
            return .cancelled
        }
    }

    private func checkVerified<T>(_ result: VerificationResult<T>) throws -> T {
        switch result {
        case .unverified(_, let error): throw error
        case .verified(let safe): return safe
        }
    }
}


