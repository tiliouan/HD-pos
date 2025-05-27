"""
Client Models

Client and transaction data classes.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from decimal import Decimal


@dataclass
class Client:
    """Client data class."""
    id: Optional[int]
    customer_code: str
    first_name: str
    last_name: str
    email: Optional[str]
    phone: Optional[str]
    address: Optional[str]
    city: Optional[str]
    postal_code: Optional[str]
    credit_limit: Decimal
    current_balance: Decimal
    is_active: bool
    created_at: datetime

    @property
    def full_name(self) -> str:
        """Get full name."""
        return f"{self.first_name} {self.last_name}"

    @property
    def available_credit(self) -> Decimal:
        """Get available credit."""
        return self.credit_limit - self.current_balance

    @property
    def credit_utilization(self) -> float:
        """Get credit utilization percentage."""
        if self.credit_limit == 0:
            return 0.0
        return float(self.current_balance / self.credit_limit * 100)


@dataclass
class ClientTransaction:
    """Client transaction data class."""
    id: int
    client_id: int
    transaction_type: str  # 'sale', 'payment', 'credit_adjustment'
    amount: Decimal
    reference_id: Optional[int]
    reference_number: Optional[str]
    description: str
    created_at: datetime
