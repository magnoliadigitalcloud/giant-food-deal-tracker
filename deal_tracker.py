#!/usr/bin/env python3
"""
Giant Food Deal Tracker
Tracks items that have both digital coupons AND sales for maximum savings
"""

import json
import os
from datetime import datetime
from typing import List, Dict, Optional

class DealTracker:
    def __init__(self, data_file: str = "deals_database.json"):
        self.data_file = data_file
        self.deals = self.load_deals()
        
    def load_deals(self) -> List[Dict]:
        """Load existing deals from JSON file"""
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                print(f"⚠️  Could not load {self.data_file}, starting fresh")
                return []
        return []
    
    def save_deals(self):
        """Save deals to JSON file"""
        with open(self.data_file, 'w') as f:
            json.dump(self.deals, f, indent=2)
        print(f"💾 Saved {len(self.deals)} deals to {self.data_file}")
    
    def add_deal(self, product_name: str, original_price: float, 
                 sale_price: float, coupon_discount: float, 
                 store_location: str = "", notes: str = "") -> Dict:
        """Add a new double-savings deal"""
        
        final_price = max(0, sale_price - coupon_discount)
        total_savings = original_price - final_price
        savings_percent = (total_savings / original_price) * 100 if original_price > 0 else 0
        
        deal = {
            'id': len(self.deals) + 1,
            'product': product_name,
            'original_price': round(original_price, 2),
            'sale_price': round(sale_price, 2),
            'coupon_discount': round(coupon_discount, 2),
            'final_price': round(final_price, 2),
            'total_savings': round(total_savings, 2),
            'savings_percent': round(savings_percent, 1),
            'date_found': datetime.now().isoformat(),
            'store_location': store_location,
            'notes': notes,
            'purchased': False
        }
        
        self.deals.append(deal)
        self.save_deals()
        
        print(f"✅ Added: {product_name}")
        print(f"   💰 You save: ${total_savings:.2f} ({savings_percent:.1f}%)")
        print(f"   🏷️  Final price: ${final_price:.2f}")
        
        return deal
    
    def mark_purchased(self, deal_id: int):
        """Mark a deal as purchased"""
        for deal in self.deals:
            if deal['id'] == deal_id:
                deal['purchased'] = True
                deal['purchase_date'] = datetime.now().isoformat()
                self.save_deals()
                print(f"✅ Marked '{deal['product']}' as purchased!")
                return
        print(f"❌ Deal #{deal_id} not found")
    
    def show_active_deals(self):
        """Show all unpurchased deals"""
        active_deals = [deal for deal in self.deals if not deal['purchased']]
        
        if not active_deals:
            print("📭 No active deals found. Add some deals first!")
            return
        
        # Sort by savings amount (highest first)
        active_deals.sort(key=lambda x: x['total_savings'], reverse=True)
        
        total_potential_savings = sum(deal['total_savings'] for deal in active_deals)
        
        print(f"\n🛍️  Active Giant Food Double-Savings Deals")
        print(f"📊 {len(active_deals)} deals • ${total_potential_savings:.2f} potential savings")
        print("=" * 70)
        
        for deal in active_deals:
            self._print_deal(deal)
    
    def show_all_deals(self):
        """Show all deals (purchased and unpurchased)"""
        if not self.deals:
            print("📭 No deals found. Add some deals first!")
            return
        
        # Sort by date found (newest first)
        sorted_deals = sorted(self.deals, key=lambda x: x['date_found'], reverse=True)
        
        purchased_deals = [d for d in self.deals if d['purchased']]
        active_deals = [d for d in self.deals if not d['purchased']]
        
        total_saved = sum(deal['total_savings'] for deal in purchased_deals)
        potential_savings = sum(deal['total_savings'] for deal in active_deals)
        
        print(f"\n🛍️  All Giant Food Double-Savings Deals")
        print(f"📊 {len(self.deals)} total deals")
        print(f"💰 ${total_saved:.2f} already saved • ${potential_savings:.2f} potential savings")
        print("=" * 70)
        
        for deal in sorted_deals:
            self._print_deal(deal)
    
    def _print_deal(self, deal: Dict):
        """Helper method to print a single deal"""
        status = "✅ PURCHASED" if deal['purchased'] else "🛒 Available"
        
        print(f"#{deal['id']} {deal['product']} ({status})")
        print(f"    Original: ${deal['original_price']:.2f} → Sale: ${deal['sale_price']:.2f} → Final: ${deal['final_price']:.2f}")
        print(f"    💰 Savings: ${deal['total_savings']:.2f} ({deal['savings_percent']}%) | Coupon: -${deal['coupon_discount']:.2f}")
        print(f"    📅 Found: {deal['date_found'][:10]}")
        
        if deal['store_location']:
            print(f"    🏪 Store: {deal['store_location']}")
        if deal['notes']:
            print(f"    📝 Notes: {deal['notes']}")
        if deal['purchased'] and 'purchase_date' in deal:
            print(f"    🛍️  Purchased: {deal['purchase_date'][:10]}")
        
        print("-" * 50)
    
    def get_shopping_list(self):
        """Generate a shopping list of active deals"""
        active_deals = [deal for deal in self.deals if not deal['purchased']]
        
        if not active_deals:
            print("📝 No active deals for shopping list")
            return
        
        # Sort by store location, then by savings
        active_deals.sort(key=lambda x: (x['store_location'], -x['total_savings']))
        
        print(f"\n📝 Shopping List - {len(active_deals)} Double-Savings Deals")
        print("=" * 50)
        
        current_store = ""
        for deal in active_deals:
            if deal['store_location'] != current_store:
                current_store = deal['store_location']
                print(f"\n🏪 {current_store or 'Giant Food'}")
                print("-" * 30)
            
            print(f"☐ {deal['product']} - ${deal['final_price']:.2f}")
            print(f"   (Save ${deal['total_savings']:.2f} with sale + coupon)")
    
    def get_stats(self):
        """Show statistics about deals"""
        if not self.deals:
            print("📊 No deals to analyze yet")
            return
        
        purchased_deals = [d for d in self.deals if d['purchased']]
        active_deals = [d for d in self.deals if not d['purchased']]
        
        total_saved = sum(deal['total_savings'] for deal in purchased_deals)
        potential_savings = sum(deal['total_savings'] for deal in active_deals)
        avg_savings = sum(deal['total_savings'] for deal in self.deals) / len(self.deals)
        
        best_deal = max(self.deals, key=lambda x: x['total_savings'])
        best_percent = max(self.deals, key=lambda x: x['savings_percent'])
        
        print(f"\n📊 Deal Statistics")
        print("=" * 40)
        print(f"Total deals found: {len(self.deals)}")
        print(f"Deals purchased: {len(purchased_deals)}")
        print(f"Active deals: {len(active_deals)}")
        print(f"Money already saved: ${total_saved:.2f}")
        print(f"Potential savings: ${potential_savings:.2f}")
        print(f"Average savings per deal: ${avg_savings:.2f}")
        print(f"\n🏆 Best dollar savings: {best_deal['product']} (${best_deal['total_savings']:.2f})")
        print(f"🏆 Best percentage savings: {best_percent['product']} ({best_percent['savings_percent']}%)")

def main():
    """Main interactive menu"""
    tracker = DealTracker()
    
    # Show welcome message for first-time users
    if len(tracker.deals) == 0:
        print("🎉 Welcome to Giant Food Deal Tracker!")
        print("💡 This tool helps you track items that have BOTH sales AND digital coupons")
        print("📱 Start by browsing Giant Food's app/website for double-savings deals")
        print("✨ Use option 1 below to add deals as you find them\n")
    
    while True:
        print(f"\n🛍️  Giant Food Deal Tracker")
        print("=" * 40)
        print("1. 📱 Add new deal")
        print("2. 👀 Show active deals")
        print("3. 📋 Show all deals")
        print("4. ✅ Mark deal as purchased")
        print("5. 📝 Generate shopping list")
        print("6. 📊 Show statistics")
        print("7. 🚪 Exit")
        
        choice = input("\nWhat would you like to do? (1-7): ").strip()
        
        if choice == '1':
            print("\n📱 Add New Deal")
            print("-" * 20)
            try:
                product = input("Product name: ").strip()
                original = float(input("Original price ($): "))
                sale = float(input("Sale price ($): "))
                coupon = float(input("Digital coupon discount ($): "))
                store = input("Store location (optional): ").strip()
                notes = input("Notes (optional): ").strip()
                
                tracker.add_deal(product, original, sale, coupon, store, notes)
            except ValueError:
                print("❌ Please enter valid numbers for prices")
        
        elif choice == '2':
            tracker.show_active_deals()
        
        elif choice == '3':
            tracker.show_all_deals()
        
        elif choice == '4':
            tracker.show_active_deals()
            try:
                deal_id = int(input("\nEnter deal # to mark as purchased: "))
                tracker.mark_purchased(deal_id)
            except ValueError:
                print("❌ Please enter a valid deal number")
        
        elif choice == '5':
            tracker.get_shopping_list()
        
        elif choice == '6':
            tracker.get_stats()
        
        elif choice == '7':
            print("👋 Happy savings!")
            break
        
        else:
            print("❌ Please choose 1-7")

if __name__ == "__main__":
    main()
