"""
Product and Inventory Models

Product, category, supplier and stock movement data classes.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from decimal import Decimal


@dataclass
class Product:
    """Product data class."""
    id: int
    sku: str
    name: str
    description: Optional[str]
    category_id: Optional[int]
    category_name: Optional[str]
    supplier_id: Optional[int]
    supplier_name: Optional[str]
    cost_price: Decimal
    selling_price: Decimal
    quantity_in_stock: int
    min_stock_level: int
    barcode: Optional[str]
    location: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime

    @property
    def profit_margin(self) -> Decimal:
        """Calculate profit margin percentage."""
        if self.cost_price == 0:
            return Decimal('0')
        return ((self.selling_price - self.cost_price) / self.cost_price) * 100

    @property
    def is_low_stock(self) -> bool:
        """Check if product is low on stock."""
        return self.quantity_in_stock <= self.min_stock_level


@dataclass
class Category:
    """Category data class."""
    id: int
    name: str
    description: Optional[str]
    parent_id: Optional[int]
    created_at: datetime


@dataclass
class Supplier:
    """Supplier data class."""
    id: int
    name: str
    contact_person: Optional[str]
    email: Optional[str]
    phone: Optional[str]
    address: Optional[str]
    created_at: datetime


@dataclass
class StockMovement:
    """Stock movement data class."""
    id: int
    product_id: int
    product_name: str
    movement_type: str  # 'in', 'out', 'adjustment'
    quantity: int
    reference_type: Optional[str]  # 'sale', 'purchase', 'adjustment'
    reference_id: Optional[int]
    notes: Optional[str]
    user_id: Optional[int]
    created_at: datetime
