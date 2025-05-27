"""
Sales Processing System for Hardware POS

Handles sales transactions, payments, and order management.
"""

import logging
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum

from .database import DatabaseManager
from .inventory import InventoryManager
from config.settings import settings


class PaymentMethod(Enum):
    """Payment method enumeration."""
    CASH = "cash"
    CARD = "card"
    CREDIT = "credit"
    PARTIAL = "partial"


class PaymentStatus(Enum):
    """Payment status enumeration."""
    COMPLETED = "completed"
    PENDING = "pending"
    PARTIAL = "partial"
    REFUNDED = "refunded"


@dataclass
class SaleItem:
    """Sale item data class."""
    product_id: int
    sku: str
    name: str
    quantity: int
    unit_price: Decimal
    discount: Decimal
    total_price: Decimal
    tax_rate: Decimal


@dataclass
class Sale:
    """Sale data class."""
    id: Optional[int]
    sale_number: str
    client_id: Optional[int]
    client_name: Optional[str]
    user_id: int
    user_name: str
    items: List[SaleItem]
    subtotal: Decimal
    tax_amount: Decimal
    discount_amount: Decimal
    total_amount: Decimal
    payment_method: str
    payment_status: str
    amount_paid: Decimal
    amount_due: Decimal
    notes: Optional[str]
    created_at: datetime


@dataclass
class Payment:
    """Payment data class."""
    id: Optional[int]
    sale_id: int
    amount: Decimal
    payment_method: str
    reference: Optional[str]
    created_at: datetime


class SalesManager:
    """Manages sales operations."""
    
    def __init__(self, db_manager: DatabaseManager, inventory_manager: InventoryManager):
        """Initialize sales manager.
        
        Args:
            db_manager: Database manager instance
            inventory_manager: Inventory manager instance
        """
        self.db = db_manager
        self.inventory = inventory_manager
        self.logger = logging.getLogger(__name__)
        
        # Current sale being processed
        self.current_sale: Optional[Sale] = None
        self.sale_items: List[SaleItem] = []
    
    def start_new_sale(self, user_id: int, client_id: Optional[int] = None) -> str:
        """Start a new sale transaction.
        
        Args:
            user_id: ID of the user making the sale
            client_id: ID of the client (optional)
            
        Returns:
            Sale number
        """
        # Generate sale number
        sale_number = self._generate_sale_number()
        
        # Initialize current sale
        self.current_sale = Sale(
            id=None,
            sale_number=sale_number,
            client_id=client_id,
            client_name=None,
            user_id=user_id,
            user_name="",
            items=[],
            subtotal=Decimal('0'),
            tax_amount=Decimal('0'),
            discount_amount=Decimal('0'),
            total_amount=Decimal('0'),
            payment_method="",
            payment_status="pending",
            amount_paid=Decimal('0'),
            amount_due=Decimal('0'),
            notes=None,
            created_at=datetime.now()
        )
        
        # Clear sale items
        self.sale_items = []
        
        self.logger.info(f"Started new sale: {sale_number}")
        return sale_number
    
    def add_item(self, product_id: int, quantity: int, 
                 unit_price: Optional[Decimal] = None,
                 discount: Decimal = Decimal('0')) -> bool:
        """Add an item to the current sale.
        
        Args:
            product_id: Product ID
            quantity: Quantity to add
            unit_price: Override unit price (optional)
            discount: Discount amount per item
            
        Returns:
            True if successful, False otherwise
        """
        if not self.current_sale:
            raise ValueError("No active sale. Start a new sale first.")
        
        try:
            # Get product details
            product = self.inventory.get_product(product_id)
            if not product:
                raise ValueError(f"Product with ID {product_id} not found")
            
            if not product.is_active:
                raise ValueError("Product is not active")
            
            # Check stock availability
            if product.quantity_in_stock < quantity:
                raise ValueError(f"Insufficient stock. Available: {product.quantity_in_stock}")
            
            # Use provided unit price or default to product selling price
            if unit_price is None:
                unit_price = product.selling_price
            
            # Calculate total price
            total_price = (unit_price * quantity) - (discount * quantity)
            
            # Check if item already exists in sale
            existing_item = None
            for item in self.sale_items:
                if item.product_id == product_id and item.unit_price == unit_price:
                    existing_item = item
                    break
            
            if existing_item:
                # Update existing item
                existing_item.quantity += quantity
                existing_item.total_price = (existing_item.unit_price * existing_item.quantity) - (existing_item.discount * existing_item.quantity)
            else:
                # Add new item
                tax_rate = settings.get('pos.tax_rate', 0.13)
                sale_item = SaleItem(
                    product_id=product_id,
                    sku=product.sku,
                    name=product.name,
                    quantity=quantity,
                    unit_price=unit_price,
                    discount=discount,
                    total_price=total_price,
                    tax_rate=Decimal(str(tax_rate))
                )
                self.sale_items.append(sale_item)
            
            # Recalculate totals
            self._calculate_totals()
            
            self.logger.info(f"Added item to sale: {product.name} x {quantity}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error adding item to sale: {e}")
            raise
    
    def remove_item(self, product_id: int, quantity: Optional[int] = None) -> bool:
        """Remove an item from the current sale.
        
        Args:
            product_id: Product ID
            quantity: Quantity to remove (if None, removes all)
            
        Returns:
            True if successful, False otherwise
        """
        if not self.current_sale:
            return False
        
        try:
            for i, item in enumerate(self.sale_items):
                if item.product_id == product_id:
                    if quantity is None or quantity >= item.quantity:
                        # Remove entire item
                        self.sale_items.pop(i)
                    else:
                        # Reduce quantity
                        item.quantity -= quantity
                        item.total_price = (item.unit_price * item.quantity) - (item.discount * item.quantity)
                    
                    # Recalculate totals
                    self._calculate_totals()
                    return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error removing item from sale: {e}")
            return False
    
    def apply_discount(self, discount_amount: Decimal) -> None:
        """Apply a global discount to the sale.
        
        Args:
            discount_amount: Discount amount to apply
        """
        if not self.current_sale:
            raise ValueError("No active sale")
        
        self.current_sale.discount_amount = discount_amount
        self._calculate_totals()
    
    def complete_sale(self, payment_method: str, amount_paid: Decimal,
                     notes: Optional[str] = None) -> int:
        """Complete the current sale.
        
        Args:
            payment_method: Payment method used
            amount_paid: Amount paid by customer
            notes: Optional sale notes
            
        Returns:
            Sale ID
        """
        if not self.current_sale:
            raise ValueError("No active sale")
        
        if not self.sale_items:
            raise ValueError("No items in sale")
        
        try:
            with self.db.get_connection() as conn:
                # Determine payment status
                if amount_paid >= self.current_sale.total_amount:
                    payment_status = PaymentStatus.COMPLETED.value
                    amount_due = Decimal('0')
                elif amount_paid > 0:
                    payment_status = PaymentStatus.PARTIAL.value
                    amount_due = self.current_sale.total_amount - amount_paid
                else:
                    payment_status = PaymentStatus.PENDING.value
                    amount_due = self.current_sale.total_amount
                
                # Insert sale record
                sale_id = self.db.execute_insert("""
                    INSERT INTO sales (sale_number, client_id, user_id, subtotal, tax_amount,
                                     discount_amount, total_amount, payment_method, payment_status, notes)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    self.current_sale.sale_number,
                    self.current_sale.client_id,
                    self.current_sale.user_id,
                    self.current_sale.subtotal,
                    self.current_sale.tax_amount,
                    self.current_sale.discount_amount,
                    self.current_sale.total_amount,
                    payment_method,
                    payment_status,
                    notes
                ))
                
                # Insert sale items
                for item in self.sale_items:
                    conn.execute("""
                        INSERT INTO sale_items (sale_id, product_id, quantity, unit_price, total_price, discount)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (sale_id, item.product_id, item.quantity, item.unit_price, item.total_price, item.discount))
                    
                    # Update stock
                    self.inventory.update_stock(
                        item.product_id, -item.quantity, 'out',
                        reference_type='sale', reference_id=sale_id,
                        user_id=self.current_sale.user_id
                    )
                
                # Record payment if amount was paid
                if amount_paid > 0:
                    conn.execute("""
                        INSERT INTO payments (sale_id, amount, payment_method, reference)
                        VALUES (?, ?, ?, ?)
                    """, (sale_id, amount_paid, payment_method, None))
                
                conn.commit()
                
                # Update current sale with ID
                self.current_sale.id = sale_id
                self.current_sale.payment_method = payment_method
                self.current_sale.payment_status = payment_status
                self.current_sale.amount_paid = amount_paid
                self.current_sale.amount_due = amount_due
                self.current_sale.notes = notes
                
                self.logger.info(f"Sale completed: {self.current_sale.sale_number}")
                return sale_id
                
        except Exception as e:
            self.logger.error(f"Error completing sale: {e}")
            raise
    
    def void_sale(self, reason: str) -> bool:
        """Void the current sale.
        
        Args:
            reason: Reason for voiding the sale
            
        Returns:
            True if successful, False otherwise
        """
        if not self.current_sale:
            return False
        
        try:
            # Clear current sale and items
            self.current_sale = None
            self.sale_items = []
            
            self.logger.info(f"Sale voided: {reason}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error voiding sale: {e}")
            return False
    
    def get_current_sale(self) -> Optional[Sale]:
        """Get the current sale.
        
        Returns:
            Current sale or None
        """
        if self.current_sale:
            self.current_sale.items = self.sale_items.copy()
        return self.current_sale
    
    def get_sale(self, sale_id: int) -> Optional[Sale]:
        """Get a sale by ID.
        
        Args:
            sale_id: Sale ID
            
        Returns:
            Sale object or None if not found
        """
        try:
            # Get sale data
            query = """
                SELECT s.*, u.full_name as user_name, c.first_name || ' ' || c.last_name as client_name
                FROM sales s
                JOIN users u ON s.user_id = u.id
                LEFT JOIN clients c ON s.client_id = c.id
                WHERE s.id = ?
            """
            
            results = self.db.execute_query(query, (sale_id,))
            if not results:
                return None
            
            sale_data = results[0]
            
            # Get sale items
            items_query = """
                SELECT si.*, p.sku, p.name
                FROM sale_items si
                JOIN products p ON si.product_id = p.id
                WHERE si.sale_id = ?
            """
            
            item_results = self.db.execute_query(items_query, (sale_id,))
            items = []
            
            for item_row in item_results:
                item = SaleItem(
                    product_id=item_row['product_id'],
                    sku=item_row['sku'],
                    name=item_row['name'],
                    quantity=item_row['quantity'],
                    unit_price=Decimal(str(item_row['unit_price'])),
                    discount=Decimal(str(item_row['discount'])),
                    total_price=Decimal(str(item_row['total_price'])),
                    tax_rate=Decimal('0.13')  # Default tax rate
                )
                items.append(item)
            
            # Create sale object
            sale = Sale(
                id=sale_data['id'],
                sale_number=sale_data['sale_number'],
                client_id=sale_data['client_id'],
                client_name=sale_data['client_name'],
                user_id=sale_data['user_id'],
                user_name=sale_data['user_name'],
                items=items,
                subtotal=Decimal(str(sale_data['subtotal'])),
                tax_amount=Decimal(str(sale_data['tax_amount'])),
                discount_amount=Decimal(str(sale_data['discount_amount'])),
                total_amount=Decimal(str(sale_data['total_amount'])),
                payment_method=sale_data['payment_method'],
                payment_status=sale_data['payment_status'],
                amount_paid=Decimal('0'),  # Calculate from payments
                amount_due=Decimal('0'),   # Calculate from payments
                notes=sale_data['notes'],
                created_at=datetime.fromisoformat(sale_data['created_at'])
            )
            
            # Calculate payment amounts
            payment_query = "SELECT SUM(amount) as total_paid FROM payments WHERE sale_id = ?"
            payment_results = self.db.execute_query(payment_query, (sale_id,))
            
            if payment_results and payment_results[0]['total_paid']:
                sale.amount_paid = Decimal(str(payment_results[0]['total_paid']))
            
            sale.amount_due = sale.total_amount - sale.amount_paid
            
            return sale
            
        except Exception as e:
            self.logger.error(f"Error getting sale: {e}")
            return None
    
    def search_sales(self, start_date: Optional[datetime] = None,
                    end_date: Optional[datetime] = None,
                    client_id: Optional[int] = None,
                    user_id: Optional[int] = None,
                    payment_status: Optional[str] = None) -> List[Sale]:
        """Search sales with filters.
        
        Args:
            start_date: Start date filter
            end_date: End date filter
            client_id: Client ID filter
            user_id: User ID filter
            payment_status: Payment status filter
            
        Returns:
            List of matching sales
        """
        try:
            query = """
                SELECT s.*, u.full_name as user_name, c.first_name || ' ' || c.last_name as client_name
                FROM sales s
                JOIN users u ON s.user_id = u.id
                LEFT JOIN clients c ON s.client_id = c.id
                WHERE 1=1
            """
            
            params = []
            
            if start_date:
                query += " AND s.created_at >= ?"
                params.append(start_date.isoformat())
            
            if end_date:
                query += " AND s.created_at <= ?"
                params.append(end_date.isoformat())
            
            if client_id:
                query += " AND s.client_id = ?"
                params.append(client_id)
            
            if user_id:
                query += " AND s.user_id = ?"
                params.append(user_id)
            
            if payment_status:
                query += " AND s.payment_status = ?"
                params.append(payment_status)
            
            query += " ORDER BY s.created_at DESC"
            
            results = self.db.execute_query(query, tuple(params))
            sales = []
            
            for row in results:
                # Get basic sale info (items loaded separately if needed)
                sale = Sale(
                    id=row['id'],
                    sale_number=row['sale_number'],
                    client_id=row['client_id'],
                    client_name=row['client_name'],
                    user_id=row['user_id'],
                    user_name=row['user_name'],
                    items=[],  # Load separately if needed
                    subtotal=Decimal(str(row['subtotal'])),
                    tax_amount=Decimal(str(row['tax_amount'])),
                    discount_amount=Decimal(str(row['discount_amount'])),
                    total_amount=Decimal(str(row['total_amount'])),
                    payment_method=row['payment_method'],
                    payment_status=row['payment_status'],
                    amount_paid=Decimal('0'),
                    amount_due=Decimal('0'),
                    notes=row['notes'],
                    created_at=datetime.fromisoformat(row['created_at'])
                )
                sales.append(sale)
            
            return sales
            
        except Exception as e:
            self.logger.error(f"Error searching sales: {e}")
            return []
    
    def process_refund(self, sale_id: int, items_to_refund: List[Dict[str, Any]],
                      refund_reason: str, user_id: int) -> bool:
        """Process a refund for sale items.
        
        Args:
            sale_id: Original sale ID
            items_to_refund: List of items to refund with quantities
            refund_reason: Reason for refund
            user_id: User processing the refund
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with self.db.get_connection() as conn:
                # Get original sale
                original_sale = self.get_sale(sale_id)
                if not original_sale:
                    raise ValueError("Original sale not found")
                
                # Create refund sale (negative amounts)
                refund_sale_number = f"RF-{original_sale.sale_number}"
                
                refund_total = Decimal('0')
                
                # Process each refund item
                for refund_item in items_to_refund:
                    product_id = refund_item['product_id']
                    refund_quantity = refund_item['quantity']
                    
                    # Find original item
                    original_item = None
                    for item in original_sale.items:
                        if item.product_id == product_id:
                            original_item = item
                            break
                    
                    if not original_item:
                        raise ValueError(f"Product {product_id} not found in original sale")
                    
                    if refund_quantity > original_item.quantity:
                        raise ValueError(f"Refund quantity exceeds original quantity")
                    
                    # Calculate refund amount
                    refund_amount = (original_item.unit_price * refund_quantity) - (original_item.discount * refund_quantity)
                    refund_total += refund_amount
                    
                    # Return stock
                    self.inventory.update_stock(
                        product_id, refund_quantity, 'in',
                        reference_type='refund', reference_id=sale_id,
                        notes=f"Refund from sale {original_sale.sale_number}",
                        user_id=user_id
                    )
                
                # Record refund transaction
                refund_id = conn.execute("""
                    INSERT INTO sales (sale_number, client_id, user_id, subtotal, tax_amount,
                                     discount_amount, total_amount, payment_method, payment_status, notes)
                    VALUES (?, ?, ?, ?, ?, ?, ?, 'refund', 'completed', ?)
                """, (
                    refund_sale_number,
                    original_sale.client_id,
                    user_id,
                    -refund_total,
                    Decimal('0'),
                    Decimal('0'),
                    -refund_total,
                    f"Refund for sale {original_sale.sale_number}: {refund_reason}"
                )).lastrowid
                
                conn.commit()
                
                self.logger.info(f"Refund processed for sale {original_sale.sale_number}")
                return True
                
        except Exception as e:
            self.logger.error(f"Error processing refund: {e}")
            return False
    
    def _calculate_totals(self) -> None:
        """Calculate sale totals."""
        if not self.current_sale:
            return
        
        subtotal = Decimal('0')
        tax_amount = Decimal('0')
        
        for item in self.sale_items:
            item_total = item.total_price
            subtotal += item_total
            
            # Calculate tax on item
            tax_on_item = item_total * item.tax_rate
            tax_amount += tax_on_item
        
        # Apply global discount
        subtotal_after_discount = subtotal - self.current_sale.discount_amount
        
        # Recalculate tax on discounted amount
        if self.current_sale.discount_amount > 0:
            tax_rate = Decimal(str(settings.get('pos.tax_rate', 0.13)))
            tax_amount = subtotal_after_discount * tax_rate
        
        total_amount = subtotal_after_discount + tax_amount
        
        # Round to 2 decimal places
        self.current_sale.subtotal = subtotal.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        self.current_sale.tax_amount = tax_amount.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        self.current_sale.total_amount = total_amount.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        
        # Calculate amount due
        self.current_sale.amount_due = self.current_sale.total_amount - self.current_sale.amount_paid
    
    def _generate_sale_number(self) -> str:
        """Generate a unique sale number.
        
        Returns:
            Unique sale number
        """
        # Get current date
        today = datetime.now()
        date_prefix = today.strftime("%Y%m%d")
        
        # Get last sale number for today
        query = """
            SELECT sale_number FROM sales 
            WHERE sale_number LIKE ? 
            ORDER BY created_at DESC 
            LIMIT 1
        """
        
        results = self.db.execute_query(query, (f"{date_prefix}-%",))
        
        if results:
            last_number = results[0]['sale_number']
            # Extract sequence number
            try:
                sequence = int(last_number.split('-')[1]) + 1
            except (IndexError, ValueError):
                sequence = 1
        else:
            sequence = 1
        
        return f"{date_prefix}-{sequence:04d}"
