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
            
            allowed_fields = ['sku', 'name', 'description', 'category_id', 'supplier_id',
                            'cost_price', 'selling_price', 'barcode', 'location', 
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
    
    def _row_to_product(self, row: tuple) -> Product:
        """Convert database row to Product object.
        
        Args:
            row: Database row tuple
            
        Returns:
            Product object
        """
        return Product(
            id=row[0],
            sku=row[1],
            name=row[2],
            description=row[3],
            category_id=row[4],
            supplier_id=row[5],
            cost_price=Decimal(str(row[6])) if row[6] is not None else Decimal('0'),
            selling_price=Decimal(str(row[7])) if row[7] is not None else Decimal('0'),
            barcode=row[8],
            location=row[9],
            stock_quantity=row[10] if row[10] is not None else 0,
            min_stock_level=row[11] if row[11] is not None else 0,
            is_active=bool(row[12]) if row[12] is not None else True,
            created_at=row[13],
            updated_at=row[14],
            category_name=row[15] if len(row) > 15 else None,
            supplier_name=row[16] if len(row) > 16 else None
        )
    
    # Category Management
    def get_all_categories(self) -> List[Category]:
        """Get all categories.
        
        Returns:
            List of all categories
        """
        query = "SELECT * FROM categories ORDER BY name"
        results = self.db.execute_query(query)
        return [self._row_to_category(row) for row in results]
    
    def get_category(self, category_id: int) -> Optional[Category]:
        """Get a category by ID.
        
        Args:
            category_id: Category ID
            
        Returns:
            Category object or None if not found
        """
        query = "SELECT * FROM categories WHERE id = ?"
        results = self.db.execute_query(query, (category_id,))
        if results:
            return self._row_to_category(results[0])
        return None
    
    def create_category(self, name: str, description: Optional[str] = None) -> int:
        """Create a new category.
        
        Args:
            name: Category name
            description: Category description
            
        Returns:
            ID of the newly created category
        """
        try:
            category_id = self.db.execute_insert(
                "INSERT INTO categories (name, description) VALUES (?, ?)",
                (name, description)
            )
            self.logger.info(f"Category '{name}' created successfully")
            return category_id
        except Exception as e:
            self.logger.error(f"Error creating category: {e}")
            raise
    
    def update_category(self, category_id: int, name: str, description: Optional[str] = None) -> bool:
        """Update a category.
        
        Args:
            category_id: Category ID
            name: Category name
            description: Category description
            
        Returns:
            True if successful, False otherwise
        """
        try:
            rows_affected = self.db.execute_update(
                "UPDATE categories SET name = ?, description = ? WHERE id = ?",
                (name, description, category_id)
            )
            if rows_affected > 0:
                self.logger.info(f"Category ID {category_id} updated successfully")
                return True
            return False
        except Exception as e:
            self.logger.error(f"Error updating category: {e}")
            return False
    
    def delete_category(self, category_id: int) -> bool:
        """Delete a category.
        
        Args:
            category_id: Category ID
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Check if category has products
            products = self.db.execute_query(
                "SELECT COUNT(*) FROM products WHERE category_id = ? AND is_active = 1",
                (category_id,)
            )
            if products and products[0][0] > 0:
                raise ValueError("Cannot delete category with associated products")
            
            rows_affected = self.db.execute_update(
                "DELETE FROM categories WHERE id = ?",
                (category_id,)
            )
            if rows_affected > 0:
                self.logger.info(f"Category ID {category_id} deleted successfully")
                return True
            return False
        except Exception as e:
            self.logger.error(f"Error deleting category: {e}")
            raise
    
    def _row_to_category(self, row: tuple) -> Category:
        """Convert database row to Category object.
        
        Args:
            row: Database row tuple
            
        Returns:
            Category object
        """
        return Category(
            id=row[0],
            name=row[1],
            description=row[2],
            created_at=row[3],
            updated_at=row[4]
        )
    
    # Stock Management
    def get_current_stock(self, product_id: int) -> int:
        """Get current stock level for a product.
        
        Args:
            product_id: Product ID
            
        Returns:
            Current stock quantity
        """
        query = "SELECT stock_quantity FROM products WHERE id = ?"
        results = self.db.execute_query(query, (product_id,))
        if results:
            return results[0][0] or 0
        return 0
    
    def update_stock(self, product_id: int, quantity: int, movement_type: str, 
                    notes: Optional[str] = None, user_id: Optional[int] = None) -> bool:
        """Update stock level for a product.
        
        Args:
            product_id: Product ID
            quantity: Quantity change (positive or negative)
            movement_type: Type of movement (sale, purchase, adjustment, etc.)
            notes: Optional notes
            user_id: User ID who made the change
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get current stock
            current_stock = self.get_current_stock(product_id)
            new_stock = current_stock + quantity
            
            if new_stock < 0:
                raise ValueError("Insufficient stock")
            
            # Update product stock
            self.db.execute_update(
                "UPDATE products SET stock_quantity = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (new_stock, product_id)
            )
            
            # Record stock movement
            self.db.execute_insert("""
                INSERT INTO stock_movements (product_id, movement_type, quantity, 
                                           previous_stock, new_stock, notes, user_id)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (product_id, movement_type, quantity, current_stock, new_stock, notes, user_id))
            
            self.logger.info(f"Stock updated for product ID {product_id}: {current_stock} -> {new_stock}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error updating stock: {e}")
            raise
    
    def get_low_stock_products(self) -> List[Product]:
        """Get products with low stock levels.
        
        Returns:
            List of products with stock below minimum level
        """
        query = """
            SELECT p.*, c.name as category_name, s.name as supplier_name
            FROM products p
            LEFT JOIN categories c ON p.category_id = c.id
            LEFT JOIN suppliers s ON p.supplier_id = s.id
            WHERE p.stock_quantity <= p.min_stock_level AND p.is_active = 1
            ORDER BY p.stock_quantity ASC
        """
        
        results = self.db.execute_query(query)
        return [self._row_to_product(row) for row in results]
    
    def get_stock_movements(self, product_id: Optional[int] = None, 
                          limit: Optional[int] = None) -> List[StockMovement]:
        """Get stock movements.
        
        Args:
            product_id: Filter by product ID (optional)
            limit: Limit number of results (optional)
            
        Returns:
            List of stock movements
        """
        query = """
            SELECT sm.*, p.name as product_name, p.sku as product_sku
            FROM stock_movements sm
            JOIN products p ON sm.product_id = p.id
        """
        
        params = []
        if product_id:
            query += " WHERE sm.product_id = ?"
            params.append(product_id)
        
        query += " ORDER BY sm.created_at DESC"
        
        if limit:
            query += " LIMIT ?"
            params.append(limit)
        
        results = self.db.execute_query(query, tuple(params))
        return [self._row_to_stock_movement(row) for row in results]
    
    def _row_to_stock_movement(self, row: tuple) -> StockMovement:
        """Convert database row to StockMovement object.
        
        Args:
            row: Database row tuple
            
        Returns:
            StockMovement object
        """
        return StockMovement(
            id=row[0],
            product_id=row[1],
            movement_type=row[2],
            quantity=row[3],
            previous_stock=row[4],
            new_stock=row[5],
            notes=row[6],
            user_id=row[7],
            created_at=row[8],
            product_name=row[9] if len(row) > 9 else None,
            product_sku=row[10] if len(row) > 10 else None
        )
