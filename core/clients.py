"""
Client Management System for Hardware POS

Handles client operations, credit tracking, and purchase history.
"""

import logging
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from decimal import Decimal

from .database import DatabaseManager


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


class ClientManager:
    """Manages client operations."""
    
    def __init__(self, db_manager: DatabaseManager):
        """Initialize client manager.
        
        Args:
            db_manager: Database manager instance
        """
        self.db = db_manager
        self.logger = logging.getLogger(__name__)

    def create_client(self, first_name: str, last_name: str,
                     email: Optional[str] = None, phone: Optional[str] = None,
                     address: Optional[str] = None, city: Optional[str] = None,
                     postal_code: Optional[str] = None,
                     credit_limit: Decimal = Decimal('0')) -> int:
        """Create a new client.
        
        Args:
            first_name: Client first name
            last_name: Client last name
            email: Email address
            phone: Phone number
            address: Address
            city: City
            postal_code: Postal code
            credit_limit: Credit limit
            
        Returns:
            ID of the newly created client
        """
        try:
            # Generate customer code
            customer_code = self._generate_customer_code()
            
            client_id = self.db.execute_insert("""
                INSERT INTO clients (customer_code, first_name, last_name, email, phone,
                                   address, city, postal_code, credit_limit)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (customer_code, first_name, last_name, email, phone,
                  address, city, postal_code, credit_limit))
            
            self.logger.info(f"Client '{first_name} {last_name}' created successfully")
            return client_id
            
        except Exception as e:
            self.logger.error(f"Error creating client: {e}")
            raise

    def add_client(self, client: Client) -> int:
        """Add a new client.
        
        Args:
            client: Client object to add
            
        Returns:
            ID of the newly created client
        """
        try:
            # Generate customer code if not provided
            customer_code = client.customer_code or self._generate_customer_code()
            
            client_id = self.db.execute_insert("""
                INSERT INTO clients (customer_code, first_name, last_name, email, phone,
                                   address, city, postal_code, credit_limit, current_balance, is_active)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (customer_code, client.first_name, client.last_name, client.email, client.phone,
                  client.address, client.city, client.postal_code, client.credit_limit, 
                  client.current_balance, client.is_active))
            
            self.logger.info(f"Client '{client.full_name}' created successfully")
            return client_id
            
        except Exception as e:
            self.logger.error(f"Error adding client: {e}")
            raise e

    def update_client(self, client: Client) -> bool:
        """Update a client.
        
        Args:
            client: Client object with updated data
            
        Returns:
            True if successful, False otherwise
        """
        try:
            query = """
                UPDATE clients SET 
                    customer_code = ?, first_name = ?, last_name = ?, email = ?, phone = ?,
                    address = ?, city = ?, postal_code = ?, credit_limit = ?, 
                    current_balance = ?, is_active = ?
                WHERE id = ?
            """
            
            rows_affected = self.db.execute_update(query, (
                client.customer_code, client.first_name, client.last_name, client.email, 
                client.phone, client.address, client.city, client.postal_code, 
                client.credit_limit, client.current_balance, client.is_active, client.id
            ))
            
            if rows_affected > 0:
                self.logger.info(f"Client '{client.full_name}' updated successfully")
                return True
            return False
            
        except Exception as e:
            self.logger.error(f"Error updating client: {e}")
            return False

    def update_client_fields(self, client_id: int, **kwargs) -> bool:
        """Update specific client fields.
        
        Args:
            client_id: Client ID
            **kwargs: Fields to update
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Build update query dynamically
            update_fields = []
            params = []
            
            allowed_fields = ['first_name', 'last_name', 'email', 'phone', 'address',
                            'city', 'postal_code', 'credit_limit', 'is_active']
            
            for field, value in kwargs.items():
                if field in allowed_fields:
                    update_fields.append(f"{field} = ?")
                    params.append(value)
            
            if not update_fields:
                return False
            
            params.append(client_id)
            query = f"UPDATE clients SET {', '.join(update_fields)} WHERE id = ?"
            
            rows_affected = self.db.execute_update(query, tuple(params))
            
            if rows_affected > 0:
                self.logger.info(f"Client ID {client_id} updated successfully")
                return True
            return False
            
        except Exception as e:
            self.logger.error(f"Error updating client: {e}")
            return False

    def delete_client(self, client_id: int) -> bool:
        """Delete a client.
        
        Args:
            client_id: Client ID to delete
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Check if client has any sales or outstanding balance
            client = self.get_client(client_id)
            if not client:
                raise ValueError(f"Client with ID {client_id} not found")
            
            if client.current_balance > 0:
                raise ValueError("Cannot delete client with outstanding balance")
            
            # Check for existing sales
            sales_query = "SELECT COUNT(*) as count FROM sales WHERE client_id = ?"
            sales_results = self.db.execute_query(sales_query, (client_id,))
            
            if sales_results and sales_results[0]['count'] > 0:
                # Instead of deleting, mark as inactive
                rows_affected = self.db.execute_update(
                    "UPDATE clients SET is_active = 0 WHERE id = ?", 
                    (client_id,)
                )
            else:
                # Safe to delete
                rows_affected = self.db.execute_update(
                    "DELETE FROM clients WHERE id = ?", 
                    (client_id,)
                )
            
            if rows_affected > 0:
                self.logger.info(f"Client ID {client_id} deleted successfully")
                return True
            return False
            
        except Exception as e:
            self.logger.error(f"Error deleting client: {e}")
            raise e

    def get_client(self, client_id: int) -> Optional[Client]:
        """Get a client by ID.
        
        Args:
            client_id: Client ID
            
        Returns:
            Client object or None if not found
        """
        query = "SELECT * FROM clients WHERE id = ?"
        results = self.db.execute_query(query, (client_id,))
        
        if results:
            return self._row_to_client(results[0])
        return None

    def get_client_by_code(self, customer_code: str) -> Optional[Client]:
        """Get a client by customer code.
        
        Args:
            customer_code: Customer code
            
        Returns:
            Client object or None if not found
        """
        query = "SELECT * FROM clients WHERE customer_code = ?"
        results = self.db.execute_query(query, (customer_code,))
        
        if results:
            return self._row_to_client(results[0])
        return None

    def search_clients(self, search_term: str, active_only: bool = True) -> List[Client]:
        """Search clients by name, email, phone, or customer code.
        
        Args:
            search_term: Search term
            active_only: Only return active clients
            
        Returns:
            List of matching clients
        """
        query = """
            SELECT * FROM clients 
            WHERE (first_name LIKE ? OR last_name LIKE ? OR email LIKE ? 
                   OR phone LIKE ? OR customer_code LIKE ?)
        """
        
        search_pattern = f"%{search_term}%"
        params = [search_pattern] * 5
        
        if active_only:
            query += " AND is_active = 1"
        
        query += " ORDER BY first_name, last_name"
        
        results = self.db.execute_query(query, tuple(params))
        return [self._row_to_client(row) for row in results]

    def get_all_clients(self, active_only: bool = True) -> List[Client]:
        """Get all clients.
        
        Args:
            active_only: Only return active clients
            
        Returns:
            List of all clients
        """
        query = "SELECT * FROM clients"
        
        if active_only:
            query += " WHERE is_active = 1"
        
        query += " ORDER BY first_name, last_name"
        
        results = self.db.execute_query(query)
        return [self._row_to_client(row) for row in results]

    def update_client_balance(self, client_id: int, amount: Decimal,
                            transaction_type: str, reference_id: Optional[int] = None,
                            reference_number: Optional[str] = None,
                            description: str = "") -> bool:
        """Update client balance and record transaction.
        
        Args:
            client_id: Client ID
            amount: Amount to add (positive) or subtract (negative)
            transaction_type: Type of transaction
            reference_id: Reference ID (sale ID, payment ID, etc.)
            reference_number: Reference number
            description: Transaction description
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with self.db.get_connection() as conn:
                # Get current balance
                cursor = conn.execute("SELECT current_balance FROM clients WHERE id = ?", (client_id,))
                result = cursor.fetchone()
                
                if not result:
                    raise ValueError(f"Client with ID {client_id} not found")
                
                current_balance = Decimal(str(result['current_balance']))
                new_balance = current_balance + amount
                
                # Update client balance
                conn.execute(
                    "UPDATE clients SET current_balance = ? WHERE id = ?",
                    (new_balance, client_id)
                )
                
                # Record transaction (if we had a client_transactions table)
                # For now, we'll just log it
                
                conn.commit()
                
                self.logger.info(f"Client balance updated: ID {client_id}, Amount: {amount}")
                return True
                
        except Exception as e:
            self.logger.error(f"Error updating client balance: {e}")
            return False

    def get_client_purchase_history(self, client_id: int, days: int = 30) -> List[Dict[str, Any]]:
        """Get client purchase history.
        
        Args:
            client_id: Client ID
            days: Number of days to look back
            
        Returns:
            List of purchase history records
        """
        query = """
            SELECT s.*, COUNT(si.id) as item_count
            FROM sales s
            LEFT JOIN sale_items si ON s.id = si.sale_id
            WHERE s.client_id = ? 
            AND s.created_at >= datetime('now', '-{} days')
            GROUP BY s.id
            ORDER BY s.created_at DESC
        """.format(days)
        
        results = self.db.execute_query(query, (client_id,))
        return [dict(row) for row in results]

    def get_clients_with_outstanding_balance(self) -> List[Client]:
        """Get clients with outstanding balances.
        
        Returns:
            List of clients with positive balances
        """
        query = """
            SELECT * FROM clients 
            WHERE current_balance > 0 AND is_active = 1
            ORDER BY current_balance DESC
        """
        
        results = self.db.execute_query(query)
        return [self._row_to_client(row) for row in results]

    def get_clients_near_credit_limit(self, threshold: float = 0.8) -> List[Client]:
        """Get clients near their credit limit.
        
        Args:
            threshold: Percentage of credit limit (0.8 = 80%)
            
        Returns:
            List of clients near their credit limit
        """
        query = """
            SELECT * FROM clients 
            WHERE credit_limit > 0 
            AND current_balance >= (credit_limit * ?)
            AND is_active = 1
            ORDER BY (current_balance / credit_limit) DESC
        """
        
        results = self.db.execute_query(query, (threshold,))
        return [self._row_to_client(row) for row in results]

    def calculate_client_stats(self, client_id: int) -> Dict[str, Any]:
        """Calculate client statistics.
        
        Args:
            client_id: Client ID
            
        Returns:
            Dictionary with client statistics
        """
        try:
            # Get basic client info
            client = self.get_client(client_id)
            if not client:
                return {}
            
            # Total purchases
            total_query = """
                SELECT COUNT(*) as total_orders, 
                       COALESCE(SUM(total_amount), 0) as total_spent,
                       COALESCE(AVG(total_amount), 0) as avg_order_value
                FROM sales 
                WHERE client_id = ?
            """
            total_results = self.db.execute_query(total_query, (client_id,))
            total_data = total_results[0] if total_results else {}
            
            # Recent purchases (last 30 days)
            recent_query = """
                SELECT COUNT(*) as recent_orders,
                       COALESCE(SUM(total_amount), 0) as recent_spent
                FROM sales 
                WHERE client_id = ? 
                AND created_at >= datetime('now', '-30 days')
            """
            recent_results = self.db.execute_query(recent_query, (client_id,))
            recent_data = recent_results[0] if recent_results else {}
            
            # Last purchase date
            last_purchase_query = """
                SELECT MAX(created_at) as last_purchase_date
                FROM sales 
                WHERE client_id = ?
            """
            last_purchase_results = self.db.execute_query(last_purchase_query, (client_id,))
            last_purchase_data = last_purchase_results[0] if last_purchase_results else {}
            
            return {
                'client': client,
                'total_orders': total_data.get('total_orders', 0),
                'total_spent': Decimal(str(total_data.get('total_spent', 0))),
                'avg_order_value': Decimal(str(total_data.get('avg_order_value', 0))),
                'recent_orders': recent_data.get('recent_orders', 0),
                'recent_spent': Decimal(str(recent_data.get('recent_spent', 0))),
                'last_purchase_date': last_purchase_data.get('last_purchase_date'),
                'available_credit': client.available_credit,
                'credit_utilization': (client.current_balance / client.credit_limit * 100) if client.credit_limit > 0 else 0
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating client stats: {e}")
            return {}

    def _generate_customer_code(self) -> str:
        """Generate a unique customer code.
        
        Returns:
            Unique customer code
        """
        # Get current date
        today = datetime.now()
        date_prefix = today.strftime("%Y%m")
        
        # Get last customer code for this month
        query = """
            SELECT customer_code FROM clients 
            WHERE customer_code LIKE ? 
            ORDER BY created_at DESC 
            LIMIT 1
        """
        
        results = self.db.execute_query(query, (f"C{date_prefix}%",))
        
        if results:
            last_code = results[0]['customer_code']
            # Extract sequence number
            try:
                sequence = int(last_code[7:]) + 1  # Skip "C" + YYYYMM
            except (IndexError, ValueError):
                sequence = 1
        else:
            sequence = 1
        
        return f"C{date_prefix}{sequence:04d}"

    def _row_to_client(self, row) -> Client:
        """Convert database row to Client object.
        
        Args:
            row: Database row
            
        Returns:
            Client object
        """
        return Client(
            id=row['id'],
            customer_code=row['customer_code'],
            first_name=row['first_name'],
            last_name=row['last_name'],
            email=row['email'],
            phone=row['phone'],
            address=row['address'],
            city=row['city'],
            postal_code=row['postal_code'],
            credit_limit=Decimal(str(row['credit_limit'])),
            current_balance=Decimal(str(row['current_balance'])),
            is_active=bool(row['is_active']),
            created_at=datetime.fromisoformat(row['created_at'])
        )
