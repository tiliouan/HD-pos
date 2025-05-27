"""
Inventory Management System for Hardware POS

Handles product management, stock tracking, and inventory operations.
"""

import logging
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from decimal import Decimal

from .database import DatabaseManager
from models import Product, Category, Supplier, StockMovement


class InventoryManager:
    """Manages inventory operations."""
    
    def __init__(self, db_manager: DatabaseManager):
        """Initialize inventory manager.
        
        Args:
            db_manager: Database manager instance
        """
        self.db = db_manager
        self.logger = logging.getLogger(__name__)
    
    # Product Management
    def create_product(self, sku: str, name: str, cost_price: Decimal, 
                      selling_price: Decimal, description: Optional[str] = None,
                      category_id: Optional[int] = None, supplier_id: Optional[int] = None,
                      barcode: Optional[str] = None, location: Optional[str] = None,
                      min_stock_level: int = 0) -> int:
        """Create a new product.
        
        Args:
            sku: Product SKU (unique identifier)
            name: Product name
            cost_price: Cost price
            selling_price: Selling price
            description: Product description
            category_id: Category ID
            supplier_id: Supplier ID
            barcode: Product barcode
            location: Storage location
            min_stock_level: Minimum stock level
              Returns:
            ID of the newly created product
        """
        try:
            # Check if SKU already exists
            existing = self.db.execute_query("SELECT id FROM products WHERE sku = ?", (sku,))
            if existing:
                raise ValueError(f"Product with SKU '{sku}' already exists")
            
            product_id = self.db.execute_insert("""
                INSERT INTO products (sku, name, description, category_id, supplier_id,
                                    cost_price, selling_price, barcode, location, min_stock_level)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (sku, name, description, category_id, supplier_id, 
                  float(cost_price), float(selling_price), barcode, location, min_stock_level))
            
            self.logger.info(f"Product '{name}' (SKU: {sku}) created successfully")
            return product_id
            
        except Exception as e:
            self.logger.error(f"Error creating product: {e}")
            raise
    
    def update_product(self, product_id: int, **kwargs) -> bool:
        """Update a product.
        
        Args:
            product_id: Product ID
            **kwargs: Fields to update
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Build update query dynamically
            update_fields = []
            params = []
            
            allowed_fields = ['sku', 'name', 'description', 'category_id', 'supplier_id',                            'cost_price', 'selling_price', 'barcode', 'location', 
                            'min_stock_level', 'is_active']
            
            for field, value in kwargs.items():
                if field in allowed_fields:
                    update_fields.append(f"{field} = ?")
                    # Convert Decimal to float for SQLite compatibility
                    if isinstance(value, Decimal):
                        value = float(value)
                    params.append(value)
            
            if not update_fields:
                return False
            
            # Add updated_at timestamp
            update_fields.append("updated_at = CURRENT_TIMESTAMP")
            params.append(product_id)
            
            query = f"UPDATE products SET {', '.join(update_fields)} WHERE id = ?"
            rows_affected = self.db.execute_update(query, tuple(params))
            
            if rows_affected > 0:
                self.logger.info(f"Product ID {product_id} updated successfully")
                return True
            return False
            
        except Exception as e:
            self.logger.error(f"Error updating product: {e}")
            return False
    
    def add_product(self, product_data: Dict[str, Any]) -> int:
        """Add a new product (wrapper for create_product that accepts dict).
        
        Args:
            product_data: Dictionary containing product data
            
        Returns:
            ID of the newly created product
        """
        return self.create_product(
            sku=product_data['sku'],
            name=product_data['name'],
            cost_price=Decimal(str(product_data['cost_price'])),
            selling_price=Decimal(str(product_data['selling_price'])),
            description=product_data.get('description'),
            category_id=product_data.get('category_id'),
            supplier_id=product_data.get('supplier_id'),
            barcode=product_data.get('barcode'),
            location=product_data.get('location'),
            min_stock_level=product_data.get('min_stock_level', 0)
        )
    
    def update_product_dict(self, product_id: int, product_data: Dict[str, Any]) -> bool:
        """Update a product using dictionary data.
        
        Args:
            product_id: Product ID
            product_data: Dictionary containing product data
            
        Returns:
            True if successful, False otherwise
        """
        # Convert numeric fields to proper types
        if 'cost_price' in product_data:
            product_data['cost_price'] = Decimal(str(product_data['cost_price']))
        if 'selling_price' in product_data:
            product_data['selling_price'] = Decimal(str(product_data['selling_price']))
        
        return self.update_product(product_id, **product_data)
    
    def delete_product(self, product_id: int) -> bool:
        """Delete a product (soft delete by setting is_active = 0).
        
        Args:
            product_id: Product ID
            
        Returns:
            True if successful, False otherwise
        """
        try:
            rows_affected = self.db.execute_update(
                "UPDATE products SET is_active = 0, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (product_id,)
            )
            
            if rows_affected > 0:
                self.logger.info(f"Product ID {product_id} deleted successfully")
                return True
            return False
            
        except Exception as e:
            self.logger.error(f"Error deleting product: {e}")
            return False
    
    def get_product(self, product_id: int) -> Optional[Product]:
        """Get a product by ID.
        
        Args:
            product_id: Product ID
            
        Returns:
            Product object or None if not found
        """
        query = """
            SELECT p.*, c.name as category_name, s.name as supplier_name
            FROM products p
            LEFT JOIN categories c ON p.category_id = c.id
            LEFT JOIN suppliers s ON p.supplier_id = s.id
            WHERE p.id = ?
        """
        
        results = self.db.execute_query(query, (product_id,))
        if results:
            return self._row_to_product(results[0])
        return None
    
    def get_product_by_sku(self, sku: str) -> Optional[Product]:
        """Get a product by SKU.
        
        Args:
            sku: Product SKU
            
        Returns:
            Product object or None if not found
        """
        query = """
            SELECT p.*, c.name as category_name, s.name as supplier_name
            FROM products p
            LEFT JOIN categories c ON p.category_id = c.id
            LEFT JOIN suppliers s ON p.supplier_id = s.id
            WHERE p.sku = ? AND p.is_active = 1
        """
        
        results = self.db.execute_query(query, (sku,))
        if results:
            return self._row_to_product(results[0])
        return None
    
    def get_product_by_barcode(self, barcode: str) -> Optional[Product]:
        """Get a product by barcode.
        
        Args:
            barcode: Product barcode
            
        Returns:
            Product object or None if not found
        """
        query = """
            SELECT p.*, c.name as category_name, s.name as supplier_name
            FROM products p
            LEFT JOIN categories c ON p.category_id = c.id
            LEFT JOIN suppliers s ON p.supplier_id = s.id
            WHERE p.barcode = ? AND p.is_active = 1
        """
        
        results = self.db.execute_query(query, (barcode,))
        if results:
            return self._row_to_product(results[0])
        return None
    
    def search_products(self, search_term: str, category_id: Optional[int] = None,
                       active_only: bool = True) -> List[Product]:
        """Search products by name, SKU, or barcode.
        
        Args:
            search_term: Search term
            category_id: Filter by category (optional)
            active_only: Only return active products
            
        Returns:
            List of matching products
        """
        query = """
            SELECT p.*, c.name as category_name, s.name as supplier_name
            FROM products p
            LEFT JOIN categories c ON p.category_id = c.id
            LEFT JOIN suppliers s ON p.supplier_id = s.id
            WHERE (p.name LIKE ? OR p.sku LIKE ? OR p.barcode LIKE ?)
        """
        
        params = [f"%{search_term}%", f"%{search_term}%", f"%{search_term}%"]
        
        if category_id:
            query += " AND p.category_id = ?"
            params.append(category_id)
        
        if active_only:
            query += " AND p.is_active = 1"
        
        query += " ORDER BY p.name"
        
        results = self.db.execute_query(query, tuple(params))
        return [self._row_to_product(row) for row in results]
    
    def get_all_products(self, active_only: bool = True) -> List[Product]:
        """Get all products.
        
        Args:
            active_only: Only return active products
            
        Returns:
            List of all products
        """
        query = """
            SELECT p.*, c.name as category_name, s.name as supplier_name
            FROM products p
            LEFT JOIN categories c ON p.category_id = c.id
            LEFT JOIN suppliers s ON p.supplier_id = s.id
        """
        
        if active_only:
            query += " WHERE p.is_active = 1"
        
        query += " ORDER BY p.name"
        
        results = self.db.execute_query(query)
        return [self._row_to_product(row) for row in results]
    
    def get_low_stock_products(self) -> List[Product]:
        """Get products with stock below minimum level.
        
        Returns:
            List of low stock products
        """
        query = """
            SELECT p.*, c.name as category_name, s.name as supplier_name
            FROM products p
            LEFT JOIN categories c ON p.category_id = c.id
            LEFT JOIN suppliers s ON p.supplier_id = s.id
            WHERE p.quantity_in_stock <= p.min_stock_level 
            AND p.is_active = 1
            ORDER BY (p.min_stock_level - p.quantity_in_stock) DESC
        """
        
        results = self.db.execute_query(query)
        return [self._row_to_product(row) for row in results]
    
    # Stock Management
    def update_stock(self, product_id: int, quantity_change: int, 
                    movement_type: str, reference_type: Optional[str] = None,
                    reference_id: Optional[int] = None, notes: Optional[str] = None,
                    user_id: Optional[int] = None) -> bool:
        """Update product stock and record movement.
        
        Args:
            product_id: Product ID
            quantity_change: Quantity to add (positive) or remove (negative)
            movement_type: 'in', 'out', or 'adjustment'
            reference_type: Type of reference ('sale', 'purchase', 'adjustment')
            reference_id: ID of reference record
            notes: Optional notes
            user_id: User performing the action
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with self.db.get_connection() as conn:
                # Get current stock
                cursor = conn.execute("SELECT quantity_in_stock FROM products WHERE id = ?", (product_id,))
                result = cursor.fetchone()
                
                if not result:
                    raise ValueError(f"Product with ID {product_id} not found")
                
                current_stock = result['quantity_in_stock']
                new_stock = current_stock + quantity_change
                
                # Prevent negative stock (unless it's an adjustment)
                if new_stock < 0 and movement_type != 'adjustment':
                    raise ValueError("Insufficient stock")
                
                # Update product stock
                conn.execute(
                    "UPDATE products SET quantity_in_stock = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (new_stock, product_id)
                )
                
                # Record stock movement
                conn.execute("""
                    INSERT INTO stock_movements (product_id, movement_type, quantity, 
                                               reference_type, reference_id, notes, user_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (product_id, movement_type, quantity_change, reference_type, 
                      reference_id, notes, user_id))
                
                conn.commit()
                
                self.logger.info(f"Stock updated for product ID {product_id}: {quantity_change}")
                return True
                
        except Exception as e:
            self.logger.error(f"Error updating stock: {e}")
            return False
    
    def adjust_stock(self, product_id: int, new_quantity: int, 
                    notes: Optional[str] = None, user_id: Optional[int] = None) -> bool:
        """Adjust stock to a specific quantity.
        
        Args:
            product_id: Product ID
            new_quantity: New stock quantity
            notes: Adjustment notes
            user_id: User performing the adjustment
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get current stock
            product = self.get_product(product_id)
            if not product:
                return False
            
            quantity_change = new_quantity - product.quantity_in_stock
            
            return self.update_stock(
                product_id, quantity_change, 'adjustment', 
                reference_type='adjustment', notes=notes, user_id=user_id
            )
            
        except Exception as e:
            self.logger.error(f"Error adjusting stock: {e}")
            return False
    
    def get_stock_movements(self, product_id: Optional[int] = None, 
                          days: int = 30) -> List[StockMovement]:
        """Get stock movements.
        
        Args:
            product_id: Filter by product ID (optional)
            days: Number of days to look back
            
        Returns:
            List of stock movements
        """
        query = """
            SELECT sm.*, p.name as product_name
            FROM stock_movements sm
            JOIN products p ON sm.product_id = p.id
            WHERE sm.created_at >= datetime('now', '-{} days')
        """.format(days)
        
        params = []
        
        if product_id:
            query += " AND sm.product_id = ?"
            params.append(product_id)
        
        query += " ORDER BY sm.created_at DESC"
        
        results = self.db.execute_query(query, tuple(params))
        return [self._row_to_stock_movement(row) for row in results]
    
    # Category Management
    def create_category(self, name: str, description: Optional[str] = None,
                       parent_id: Optional[int] = None) -> int:
        """Create a new category.
        
        Args:
            name: Category name
            description: Category description
            parent_id: Parent category ID
            
        Returns:
            ID of the newly created category
        """
        try:
            category_id = self.db.execute_insert("""
                INSERT INTO categories (name, description, parent_id)
                VALUES (?, ?, ?)
            """, (name, description, parent_id))
            
            self.logger.info(f"Category '{name}' created successfully")
            return category_id
            
        except Exception as e:
            self.logger.error(f"Error creating category: {e}")
            raise
    
    def get_all_categories(self) -> List[Category]:
        """Get all categories.
        
        Returns:
            List of all categories
        """
        query = "SELECT * FROM categories ORDER BY name"
        results = self.db.execute_query(query)
        return [self._row_to_category(row) for row in results]
    
    def add_category(self, category_data: dict) -> int:
        """Add a new category.
        
        Args:
            category_data: Dictionary containing category information
            
        Returns:
            ID of the newly created category
        """
        try:
            category_id = self.db.execute_insert("""
                INSERT INTO categories (name, description)
                VALUES (?, ?)
            """, (category_data['name'], category_data.get('description')))
            
            self.logger.info(f"Category '{category_data['name']}' created successfully")
            return category_id
            
        except Exception as e:
            self.logger.error(f"Error creating category: {e}")
            raise
    
    def update_category(self, category_data: dict) -> bool:
        """Update an existing category.
        
        Args:
            category_data: Dictionary containing category information with 'id'
            
        Returns:
            True if successful, False otherwise
        """
        try:
            rows_affected = self.db.execute_update("""
                UPDATE categories SET name = ?, description = ?
                WHERE id = ?
            """, (category_data['name'], category_data.get('description'), category_data['id']))
            
            if rows_affected > 0:
                self.logger.info(f"Category ID {category_data['id']} updated successfully")
                return True
            return False
            
        except Exception as e:
            self.logger.error(f"Error updating category: {e}")
            return False
    
    def delete_category(self, category_id: int) -> bool:
        """Delete a category.
        
        Args:
            category_id: ID of the category to delete
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Check if category has products
            result = self.db.execute_query("SELECT COUNT(*) as count FROM products WHERE category_id = ?", (category_id,))
            if result and result[0]['count'] > 0:
                raise ValueError("Cannot delete category with existing products")
            
            rows_affected = self.db.execute_update("DELETE FROM categories WHERE id = ?", (category_id,))
            
            if rows_affected > 0:
                self.logger.info(f"Category ID {category_id} deleted successfully")
                return True
            return False
            
        except Exception as e:
            self.logger.error(f"Error deleting category: {e}")
            raise
    
    # Supplier Management
    def create_supplier(self, name: str, contact_person: Optional[str] = None,
                       email: Optional[str] = None, phone: Optional[str] = None,
                       address: Optional[str] = None) -> int:
        """Create a new supplier.
        
        Args:
            name: Supplier name
            contact_person: Contact person
            email: Email address
            phone: Phone number
            address: Address
            
        Returns:
            ID of the newly created supplier
        """
        try:
            supplier_id = self.db.execute_insert("""
                INSERT INTO suppliers (name, contact_person, email, phone, address)
                VALUES (?, ?, ?, ?, ?)
            """, (name, contact_person, email, phone, address))
            
            self.logger.info(f"Supplier '{name}' created successfully")
            return supplier_id
            
        except Exception as e:
            self.logger.error(f"Error creating supplier: {e}")
            raise
    
    def get_all_suppliers(self) -> List[Supplier]:
        """Get all suppliers.
        
        Returns:
            List of all suppliers
        """
        query = "SELECT * FROM suppliers ORDER BY name"
        results = self.db.execute_query(query)
        return [self._row_to_supplier(row) for row in results]
    
    # Helper methods    def _row_to_product(self, row) -> Product:
        """Convert database row to Product object.
        
        Args:
            row: Database row (sqlite3.Row object)
            
        Returns:
            Product object
        """
        return Product(
            id=row['id'],
            sku=row['sku'],
            name=row['name'],
            description=row['description'],
            category_id=row['category_id'],
            category_name=row['category_name'] if 'category_name' in row.keys() else None,
            supplier_id=row['supplier_id'],
            supplier_name=row['supplier_name'] if 'supplier_name' in row.keys() else None,
            cost_price=Decimal(str(row['cost_price'])) if row['cost_price'] is not None else Decimal('0'),
            selling_price=Decimal(str(row['selling_price'])) if row['selling_price'] is not None else Decimal('0'),
            quantity_in_stock=row['quantity_in_stock'] if row['quantity_in_stock'] is not None else 0,
            min_stock_level=row['min_stock_level'] if row['min_stock_level'] is not None else 0,
            barcode=row['barcode'],
            location=row['location'],
            is_active=bool(row['is_active']) if row['is_active'] is not None else True,            created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else datetime.now(),
            updated_at=datetime.fromisoformat(row['updated_at']) if row['updated_at'] else datetime.now()
        )
    
    def _row_to_category(self, row) -> Category:
        """Convert database row to Category object.
        
        Args:
            row: Database row (sqlite3.Row object)
            
        Returns:
            Category object
        """
        return Category(
            id=row['id'],
            name=row['name'],
            description=row['description'],
            parent_id=row['parent_id'],
            created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else datetime.now()
        )
    
    def _row_to_supplier(self, row) -> Supplier:
        """Convert database row to Supplier object."""
        return Supplier(
            id=row['id'],
            name=row['name'],
            contact_person=row['contact_person'],
            email=row['email'],
            phone=row['phone'],
            address=row['address'],
            created_at=datetime.fromisoformat(row['created_at'])
        )
    
    def _row_to_stock_movement(self, row) -> StockMovement:
        """Convert database row to StockMovement object."""
        return StockMovement(
            id=row['id'],
            product_id=row['product_id'],
            product_name=row['product_name'],
            movement_type=row['movement_type'],
            quantity=row['quantity'],
            reference_type=row['reference_type'],
            reference_id=row['reference_id'],
            notes=row['notes'],
            user_id=row['user_id'],
            created_at=datetime.fromisoformat(row['created_at'])
        )
