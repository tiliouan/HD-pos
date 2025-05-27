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
