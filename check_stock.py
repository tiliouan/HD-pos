#!/usr/bin/env python3
"""
Check current product stock levels and add stock if needed.
"""

from core.database import DatabaseManager
from core.inventory import InventoryManager

def main():    # Initialize database
    db = DatabaseManager()
    db.initialize()

    # Get inventory manager
    inventory = InventoryManager(db)

    # Check existing products
    products = inventory.get_all_products()
    print(f'Found {len(products)} products:')
    
    for p in products:
        print(f'  - {p.name} (SKU: {p.sku}) - Stock: {p.quantity_in_stock}')
        
        # Add stock if product has 0 stock
        if p.quantity_in_stock == 0:
            print(f'    Adding 50 units of stock to {p.name}...')
            success = inventory.adjust_stock(p.id, 50, "Initial stock setup", user_id=1)
            if success:
                print(f'    ✓ Stock added successfully')
            else:
                print(f'    ✗ Failed to add stock')

if __name__ == "__main__":
    main()
