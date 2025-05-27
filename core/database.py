"""
Database Manager for Hardware POS System

Handles SQLite database operations, schema creation, and data management.
"""

import sqlite3
import logging
import os
from pathlib import Path
from contextlib import contextmanager
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

from config.settings import settings


class DatabaseManager:
    """Manages SQLite database operations for the POS system."""
    
    def __init__(self):
        """Initialize the database manager."""
        self.db_path = settings.get_database_path()
        self.logger = logging.getLogger(__name__)
        self._ensure_database_directory()
    
    def _ensure_database_directory(self) -> None:
        """Ensure the database directory exists."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
    
    def initialize(self) -> bool:
        """Initialize the database with schema.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            with self.get_connection() as conn:
                self._create_schema(conn)
                self._create_default_data(conn)
            self.logger.info("Database initialized successfully")
            return True
        except Exception as e:
            self.logger.error(f"Failed to initialize database: {e}")
            return False
    
    @contextmanager
    def get_connection(self):
        """Get a database connection with automatic cleanup.
        
        Yields:
            sqlite3.Connection: Database connection
        """
        conn = None
        try:
            conn = sqlite3.connect(str(self.db_path))
            conn.row_factory = sqlite3.Row  # Enable column access by name
            conn.execute("PRAGMA foreign_keys = ON")  # Enable foreign key constraints
            yield conn
        except Exception as e:
            if conn:
                conn.rollback()
            raise e
        finally:
            if conn:
                conn.close()
    
    def get_simple_connection(self):
        """Get a simple database connection without context management."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn
    
    def _create_schema(self, conn: sqlite3.Connection) -> None:
        """Create database schema.
        
        Args:
            conn: Database connection
        """
        schema_sql = """
        -- Users table
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            full_name TEXT NOT NULL,
            email TEXT,
            role TEXT NOT NULL DEFAULT 'cashier',
            is_active BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP
        );
        
        -- Categories table
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            description TEXT,
            parent_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (parent_id) REFERENCES categories (id)
        );
        
        -- Suppliers table
        CREATE TABLE IF NOT EXISTS suppliers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            contact_person TEXT,
            email TEXT,
            phone TEXT,
            address TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        -- Products table
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sku TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            description TEXT,
            category_id INTEGER,
            supplier_id INTEGER,
            cost_price DECIMAL(10,2) NOT NULL,
            selling_price DECIMAL(10,2) NOT NULL,
            quantity_in_stock INTEGER DEFAULT 0,
            min_stock_level INTEGER DEFAULT 0,
            barcode TEXT,
            location TEXT,
            is_active BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (category_id) REFERENCES categories (id),
            FOREIGN KEY (supplier_id) REFERENCES suppliers (id)
        );
        
        -- Clients table
        CREATE TABLE IF NOT EXISTS clients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_code TEXT UNIQUE,
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL,
            email TEXT,
            phone TEXT,
            address TEXT,
            city TEXT,
            postal_code TEXT,
            credit_limit DECIMAL(10,2) DEFAULT 0,
            current_balance DECIMAL(10,2) DEFAULT 0,
            is_active BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        -- Sales table
        CREATE TABLE IF NOT EXISTS sales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sale_number TEXT UNIQUE NOT NULL,
            client_id INTEGER,
            user_id INTEGER NOT NULL,
            subtotal DECIMAL(10,2) NOT NULL,
            tax_amount DECIMAL(10,2) NOT NULL,
            discount_amount DECIMAL(10,2) DEFAULT 0,
            total_amount DECIMAL(10,2) NOT NULL,
            payment_method TEXT NOT NULL,
            payment_status TEXT DEFAULT 'completed',
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (client_id) REFERENCES clients (id),
            FOREIGN KEY (user_id) REFERENCES users (id)
        );
        
        -- Sale items table
        CREATE TABLE IF NOT EXISTS sale_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sale_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL,
            unit_price DECIMAL(10,2) NOT NULL,
            total_price DECIMAL(10,2) NOT NULL,
            discount DECIMAL(10,2) DEFAULT 0,
            FOREIGN KEY (sale_id) REFERENCES sales (id) ON DELETE CASCADE,
            FOREIGN KEY (product_id) REFERENCES products (id)
        );
        
        -- Stock movements table
        CREATE TABLE IF NOT EXISTS stock_movements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL,
            movement_type TEXT NOT NULL, -- 'in', 'out', 'adjustment'
            quantity INTEGER NOT NULL,
            reference_type TEXT, -- 'sale', 'purchase', 'adjustment'
            reference_id INTEGER,
            notes TEXT,
            user_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (product_id) REFERENCES products (id),
            FOREIGN KEY (user_id) REFERENCES users (id)
        );
        
        -- Payments table
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sale_id INTEGER NOT NULL,
            amount DECIMAL(10,2) NOT NULL,
            payment_method TEXT NOT NULL,
            transaction_reference TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (sale_id) REFERENCES sales (id)
        );
        
        -- Create indexes for better performance
        CREATE INDEX IF NOT EXISTS idx_products_sku ON products(sku);
        CREATE INDEX IF NOT EXISTS idx_products_barcode ON products(barcode);
        CREATE INDEX IF NOT EXISTS idx_sales_number ON sales(sale_number);
        CREATE INDEX IF NOT EXISTS idx_sales_date ON sales(created_at);
        CREATE INDEX IF NOT EXISTS idx_clients_code ON clients(customer_code);
        """
        
        conn.executescript(schema_sql)
        conn.commit()
    
    def _create_default_data(self, conn: sqlite3.Connection) -> None:
        """Create default data for the system.
        
        Args:
            conn: Database connection
        """
        # Check if default user exists
        cursor = conn.execute("SELECT COUNT(*) FROM users WHERE username = 'admin'")
        if cursor.fetchone()[0] == 0:
            # Create default admin user (password: admin123)
            import hashlib
            password_hash = hashlib.sha256("admin123".encode()).hexdigest()
            
            conn.execute("""
                INSERT INTO users (username, password_hash, full_name, role)
                VALUES ('admin', ?, 'System Administrator', 'admin')
            """, (password_hash,))
        
        # Create default categories
        default_categories = [
            ("Tools", "Hand and power tools"),
            ("Hardware", "Nuts, bolts, screws, and fasteners"),
            ("Electrical", "Electrical supplies and components"),
            ("Plumbing", "Plumbing supplies and fixtures"),
            ("Paint", "Paint and painting supplies"),
            ("Garden", "Garden and outdoor supplies")
        ]
        
        for name, description in default_categories:
            conn.execute("""
                INSERT OR IGNORE INTO categories (name, description)
                VALUES (?, ?)
            """, (name, description))
        
        conn.commit()
    
    def execute_query(self, query: str, params: Tuple = ()) -> List[sqlite3.Row]:
        """Execute a SELECT query and return results.
        
        Args:
            query: SQL query string
            params: Query parameters
            
        Returns:
            List of result rows
        """
        conn = None
        try:
            conn = self.get_simple_connection()
            cursor = conn.execute(query, params)
            return cursor.fetchall()
        finally:
            if conn:
                conn.close()
    
    def execute_update(self, query: str, params: Tuple = ()) -> int:
        """Execute an INSERT, UPDATE, or DELETE query.
        
        Args:
            query: SQL query string
            params: Query parameters
            
        Returns:
            Number of affected rows
        """
        conn = None
        try:
            conn = self.get_simple_connection()
            cursor = conn.execute(query, params)
            conn.commit()
            return cursor.rowcount
        finally:
            if conn:
                conn.close()
    
    def execute_insert(self, query: str, params: Tuple = ()) -> int:
        """Execute an INSERT query and return the new row ID.
        
        Args:
            query: SQL query string
            params: Query parameters
            
        Returns:
            ID of the newly inserted row
        """
        conn = None
        try:
            conn = self.get_simple_connection()
            cursor = conn.execute(query, params)
            conn.commit()
            return cursor.lastrowid
        finally:
            if conn:
                conn.close()
    
    def backup_database(self, backup_path: Optional[Path] = None) -> bool:
        """Create a backup of the database.
        
        Args:
            backup_path: Path for backup file. If None, uses default location.
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if backup_path is None:
                backup_dir = settings.get_backup_path()
                backup_dir.mkdir(parents=True, exist_ok=True)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_path = backup_dir / f"hardware_pos_backup_{timestamp}.db"
            
            # Copy database file
            import shutil
            shutil.copy2(self.db_path, backup_path)
            
            self.logger.info(f"Database backed up to: {backup_path}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to backup database: {e}")
            return False
    
    def get_table_info(self, table_name: str) -> List[Dict[str, Any]]:
        """Get information about a table's columns.
        
        Args:
            table_name: Name of the table
            
        Returns:
            List of column information dictionaries
        """
        query = f"PRAGMA table_info({table_name})"
        rows = self.execute_query(query)
        return [dict(row) for row in rows]
    
    def vacuum_database(self) -> bool:
        """Optimize the database by running VACUUM.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            with self.get_connection() as conn:
                conn.execute("VACUUM")
            self.logger.info("Database vacuumed successfully")
            return True
        except Exception as e:
            self.logger.error(f"Failed to vacuum database: {e}")
            return False
