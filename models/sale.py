"""
Sales and Payment Models

Sale, sale item, and payment data classes.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional
from decimal import Decimal
from enum import Enum


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

    @property
    def subtotal(self) -> Decimal:
        """Calculate subtotal before discount and tax."""
        return self.unit_price * self.quantity

    @property
    def discount_amount(self) -> Decimal:
        """Calculate total discount amount."""
        return self.discount * self.quantity

    @property
    def tax_amount(self) -> Decimal:
        """Calculate tax amount."""
        return self.total_price * self.tax_rate


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

    @property
    def item_count(self) -> int:
        """Get total number of items in sale."""
        return sum(item.quantity for item in self.items)

    @property
    def is_paid(self) -> bool:
        """Check if sale is fully paid."""
        return self.amount_due <= Decimal('0')


@dataclass
class Payment:
    """Payment data class."""
    id: Optional[int]
    sale_id: int
    amount: Decimal
    payment_method: str
    reference: Optional[str]
    created_at: datetime
