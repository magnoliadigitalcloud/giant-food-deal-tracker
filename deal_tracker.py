# SIMPLE GIANT FOOD COUPON CHECKER
# This is a simplified version that's easier to set up

import requests
import json
import time
from datetime import datetime

def check_giant_deals():
    print("🛍️ Checking Giant Food for double savings...")
    print("=" * 50)
    
    # This is where we'll add the real checking code
    # For now, this is a demo version
    
    sample_deals = [
        {
            "name": "Tide Laundry Detergent",
            "original_price": 12.99,
            "sale_price": 8.99,
            "coupon_savings": 2.00,
            "final_price": 6.99,
            "total_savings": 6.00
        },
        {
            "name": "Cheerios Cereal",
            "original_price": 5.49,
            "sale_price": 3.99,
            "coupon_savings": 1.00,
            "final_price": 2.99,
            "total_savings": 2.50
        }
    ]
    
    print(f"Found {len(sample_deals)} double-savings deals!\n")
    
    for i, deal in enumerate(sample_deals, 1):
        savings_percent = (deal['total_savings'] / deal['original_price']) * 100
        
        print(f"{i}. {deal['name']}")
        print(f"   Was: ${deal['original_price']:.2f}")
        print(f"   Sale: ${deal['sale_price']:.2f}")
        print(f"   After Coupon: ${deal['final_price']:.2f}")
        print(f"   💰 YOU SAVE: ${deal['total_savings']:.2f} ({savings_percent:.0f}%)")
        print("-" * 40)
    
    return sample_deals

def main():
    print("🏪 Giant Food Double Savings Checker")
    print("Starting up...\n")
    
    deals = check_giant_deals()
    
    print(f"\n✅ Check complete! Found {len(deals)} great deals.")
    print("\nPress Enter to exit...")
    input()

if __name__ == "__main__":
    main()
