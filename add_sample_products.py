#!/usr/bin/env python3
"""
Add sample hardware products for testing the POS system.
"""

from decimal import Decimal
from core.database import DatabaseManager
from core.inventory import InventoryManager

def main():
    # Initialize database
    db = DatabaseManager()
    db.initialize()

    # Get inventory manager
    inventory = InventoryManager(db)

    # Sample hardware products to add
    sample_products = [
        {
            'sku': 'HAM001',
            'name': 'Claw Hammer 16oz',
            'description': 'Professional claw hammer with ergonomic handle',
            'cost_price': Decimal('12.50'),
            'selling_price': Decimal('24.99'),
            'barcode': '123456789012',
            'min_stock_level': 10
        },
        {
            'sku': 'SCR002',
            'name': 'Phillips Head Screwdriver Set',
            'description': 'Set of 4 Phillips head screwdrivers',
            'cost_price': Decimal('8.75'),
            'selling_price': Decimal('16.99'),
            'barcode': '123456789013',
            'min_stock_level': 5
        },
        {
            'sku': 'NUT003',
            'name': 'Hex Nuts M8 (Pack of 20)',
            'description': 'Stainless steel hex nuts M8 size',
            'cost_price': Decimal('3.25'),
            'selling_price': Decimal('6.99'),
            'barcode': '123456789014',
            'min_stock_level': 50
        },
        {
            'sku': 'DRL004',
            'name': 'Drill Bits Set HSS',
            'description': 'High speed steel drill bits set 1-10mm',
            'cost_price': Decimal('15.80'),
            'selling_price': Decimal('29.99'),
            'barcode': '123456789015',
            'min_stock_level': 8
        },
        {
            'sku': 'TAP005',
            'name': 'Duct Tape Silver 50mm',
            'description': 'Heavy duty silver duct tape 50mm x 25m',
            'cost_price': Decimal('4.20'),
            'selling_price': Decimal('8.99'),
            'barcode': '123456789016',
            'min_stock_level': 20
        }
    ]

    print("Adding sample hardware products...")
    
    for product_data in sample_products:
        try:
            # Check if product already exists
            existing = inventory.get_product_by_sku(product_data['sku'])
            if existing:
                print(f"  - {product_data['name']} already exists, skipping...")
                continue
                
            # Create product
            product_id = inventory.create_product(**product_data)
            
            # Add initial stock (30 units for each product)
            inventory.adjust_stock(product_id, 30, "Initial stock setup", user_id=1)
            
            print(f"  ✓ Added {product_data['name']} (SKU: {product_data['sku']}) with 30 units")
            
        except Exception as e:
            print(f"  ✗ Failed to add {product_data['name']}: {e}")

    print("\nStock setup completed!")

if __name__ == "__main__":
    main()
