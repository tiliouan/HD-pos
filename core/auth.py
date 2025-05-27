"""
Authentication System for Hardware POS System

Handles user authentication, session management, and password security.
"""

import hashlib
import secrets
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from dataclasses import dataclass

from .database import DatabaseManager


@dataclass
class User:
    """User data class."""
    id: int
    username: str
    full_name: str
    email: Optional[str]
    role: str
    is_active: bool
    created_at: datetime
    last_login: Optional[datetime]


class AuthenticationError(Exception):
    """Custom exception for authentication errors."""
    pass


class AuthenticationManager:
    """Manages user authentication and sessions."""
    
    def __init__(self, db_manager: DatabaseManager):
        """Initialize authentication manager.
        
        Args:
            db_manager: Database manager instance
        """
        self.db = db_manager
        self.logger = logging.getLogger(__name__)
        self.current_user: Optional[User] = None
        self.session_start_time: Optional[datetime] = None
    
    def hash_password(self, password: str, salt: Optional[str] = None) -> tuple[str, str]:
        """Hash a password with salt.
        
        Args:
            password: Plain text password
            salt: Optional salt (generated if not provided)
            
        Returns:
            Tuple of (hashed_password, salt)
        """
        if salt is None:
            salt = secrets.token_hex(32)
        
        # Combine password and salt
        password_salt = f"{password}{salt}"
        
        # Hash using SHA-256
        hashed = hashlib.sha256(password_salt.encode('utf-8')).hexdigest()
        
        return hashed, salt
    
    def verify_password(self, password: str, stored_hash: str, salt: str) -> bool:
        """Verify a password against stored hash.
        
        Args:
            password: Plain text password to verify
            stored_hash: Stored password hash
            salt: Password salt
            
        Returns:
            True if password matches, False otherwise
        """
        hashed, _ = self.hash_password(password, salt)
        return hashed == stored_hash
    
    def authenticate(self, username: str, password: str) -> bool:
        """Authenticate a user with username and password.
        
        Args:
            username: Username
            password: Plain text password
            
        Returns:
            True if authentication successful, False otherwise
            
        Raises:
            AuthenticationError: If authentication fails
        """
        try:
            # Get user from database
            query = """
                SELECT id, username, password_hash, full_name, email, role, is_active,
                       created_at, last_login
                FROM users 
                WHERE username = ? AND is_active = 1
            """
            results = self.db.execute_query(query, (username,))
            
            if not results:
                self.logger.warning(f"Authentication failed: User '{username}' not found")
                raise AuthenticationError("Invalid username or password")
            
            user_data = results[0]
            stored_hash = user_data['password_hash']
            
            # For backward compatibility, check if it's an old hash (without salt)
            if len(stored_hash) == 64:  # Old SHA-256 hash without salt
                password_hash = hashlib.sha256(password.encode()).hexdigest()
                if password_hash != stored_hash:
                    self.logger.warning(f"Authentication failed: Invalid password for user '{username}'")
                    raise AuthenticationError("Invalid username or password")
            else:
                # New format with salt (implement when migrating passwords)
                password_hash = hashlib.sha256(password.encode()).hexdigest()
                if password_hash != stored_hash:
                    self.logger.warning(f"Authentication failed: Invalid password for user '{username}'")
                    raise AuthenticationError("Invalid username or password")
            
            # Create user object
            self.current_user = User(
                id=user_data['id'],
                username=user_data['username'],
                full_name=user_data['full_name'],
                email=user_data['email'],
                role=user_data['role'],
                is_active=bool(user_data['is_active']),
                created_at=datetime.fromisoformat(user_data['created_at']),
                last_login=datetime.fromisoformat(user_data['last_login']) if user_data['last_login'] else None
            )
            
            # Update last login time
            self.db.execute_update(
                "UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?",
                (self.current_user.id,)
            )
            
            self.session_start_time = datetime.now()
            
            self.logger.info(f"User '{username}' authenticated successfully")
            return True
            
        except AuthenticationError:
            raise
        except Exception as e:
            self.logger.error(f"Authentication error: {e}")
            raise AuthenticationError("Authentication system error")
    
    def logout(self) -> None:
        """Logout the current user."""
        if self.current_user:
            self.logger.info(f"User '{self.current_user.username}' logged out")
        
        self.current_user = None
        self.session_start_time = None
    
    def is_authenticated(self) -> bool:
        """Check if a user is currently authenticated.
        
        Returns:
            True if user is authenticated, False otherwise
        """
        return self.current_user is not None
    
    def get_current_user(self) -> Optional[User]:
        """Get the currently authenticated user.
        
        Returns:
            Current user object or None if not authenticated
        """
        return self.current_user
    
    def has_permission(self, permission: str) -> bool:
        """Check if the current user has a specific permission.
        
        Args:
            permission: Permission to check
            
        Returns:
            True if user has permission, False otherwise
        """
        if not self.current_user:
            return False
        
        # Define role-based permissions
        permissions = {
            'admin': ['*'],  # Admin has all permissions
            'manager': [
                'sales.create', 'sales.view', 'sales.modify',
                'inventory.create', 'inventory.view', 'inventory.modify',
                'clients.create', 'clients.view', 'clients.modify',
                'reports.view', 'settings.view'
            ],
            'cashier': [
                'sales.create', 'sales.view',
                'inventory.view',
                'clients.view', 'clients.create'
            ]
        }
        
        user_permissions = permissions.get(self.current_user.role, [])
        
        # Admin has all permissions
        if '*' in user_permissions:
            return True
        
        return permission in user_permissions
    
    def require_permission(self, permission: str) -> None:
        """Require a specific permission or raise an exception.
        
        Args:
            permission: Required permission
            
        Raises:
            AuthenticationError: If user doesn't have permission
        """
        if not self.has_permission(permission):
            raise AuthenticationError(f"Access denied: '{permission}' permission required")
    
    def is_session_valid(self) -> bool:
        """Check if the current session is still valid.
        
        Returns:
            True if session is valid, False otherwise
        """
        if not self.is_authenticated() or not self.session_start_time:
            return False
        
        # Check session timeout (from settings)
        from config.settings import settings
        timeout_minutes = settings.get('security.session_timeout', 60)
        
        session_duration = datetime.now() - self.session_start_time
        return session_duration.total_seconds() < (timeout_minutes * 60)
    
    def create_user(self, username: str, password: str, full_name: str, 
                   email: Optional[str] = None, role: str = 'cashier') -> int:
        """Create a new user.
        
        Args:
            username: Unique username
            password: Plain text password
            full_name: User's full name
            email: Email address (optional)
            role: User role (admin, manager, cashier)
            
        Returns:
            ID of the newly created user
            
        Raises:
            AuthenticationError: If user creation fails
        """
        try:
            # Check if username already exists
            existing = self.db.execute_query(
                "SELECT id FROM users WHERE username = ?", (username,)
            )
            
            if existing:
                raise AuthenticationError(f"Username '{username}' already exists")
            
            # Hash password
            password_hash = hashlib.sha256(password.encode()).hexdigest()
            
            # Insert new user
            user_id = self.db.execute_insert("""
                INSERT INTO users (username, password_hash, full_name, email, role)
                VALUES (?, ?, ?, ?, ?)
            """, (username, password_hash, full_name, email, role))
            
            self.logger.info(f"User '{username}' created successfully")
            return user_id
            
        except Exception as e:
            self.logger.error(f"Error creating user: {e}")
            raise AuthenticationError("Failed to create user")
    
    def change_password(self, user_id: int, old_password: str, new_password: str) -> bool:
        """Change a user's password.
        
        Args:
            user_id: User ID
            old_password: Current password
            new_password: New password
            
        Returns:
            True if password changed successfully, False otherwise
            
        Raises:
            AuthenticationError: If password change fails
        """
        try:
            # Get current password hash
            query = "SELECT password_hash FROM users WHERE id = ?"
            results = self.db.execute_query(query, (user_id,))
            
            if not results:
                raise AuthenticationError("User not found")
            
            stored_hash = results[0]['password_hash']
            
            # Verify old password
            old_hash = hashlib.sha256(old_password.encode()).hexdigest()
            if old_hash != stored_hash:
                raise AuthenticationError("Current password is incorrect")
            
            # Hash new password
            new_hash = hashlib.sha256(new_password.encode()).hexdigest()
            
            # Update password
            rows_affected = self.db.execute_update(
                "UPDATE users SET password_hash = ? WHERE id = ?",
                (new_hash, user_id)
            )
            
            if rows_affected > 0:
                self.logger.info(f"Password changed for user ID {user_id}")
                return True
            else:
                return False
                
        except AuthenticationError:
            raise
        except Exception as e:
            self.logger.error(f"Error changing password: {e}")
            raise AuthenticationError("Failed to change password")
    
    def get_all_users(self) -> list[Dict[str, Any]]:
        """Get all users (excluding password hashes).
        
        Returns:
            List of user dictionaries
        """
        query = """
            SELECT id, username, full_name, email, role, is_active, 
                   created_at, last_login
            FROM users
            ORDER BY username
        """
        
        results = self.db.execute_query(query)
        return [dict(row) for row in results]
    
    def deactivate_user(self, user_id: int) -> bool:
        """Deactivate a user account.
        
        Args:
            user_id: User ID to deactivate
            
        Returns:
            True if successful, False otherwise
        """
        try:
            rows_affected = self.db.execute_update(
                "UPDATE users SET is_active = 0 WHERE id = ?",
                (user_id,)
            )
            
            if rows_affected > 0:
                self.logger.info(f"User ID {user_id} deactivated")
                return True
            else:
                return False
                
        except Exception as e:
            self.logger.error(f"Error deactivating user: {e}")
            return False
