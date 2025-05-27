"""
User Model

User authentication and role-based access control.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class User:
    """User data class for authentication and permissions."""
    id: Optional[int]
    username: str
    password_hash: str
    email: str
    full_name: str
    role: str  # 'admin', 'manager', 'seller'
    is_active: bool
    last_login: Optional[datetime]
    created_at: datetime
    
    def has_permission(self, permission: str) -> bool:
        """Check if user has a specific permission based on role.
        
        Args:
            permission: Permission to check
            
        Returns:
            True if user has permission, False otherwise
        """
        # Define role-based permissions
        permissions = {
            'admin': [
                'manage_users', 'manage_settings', 'view_reports', 'manage_inventory',
                'process_sales', 'manage_clients', 'backup_restore', 'void_sales'
            ],
            'manager': [
                'view_reports', 'manage_inventory', 'process_sales', 'manage_clients',
                'void_sales'
            ],
            'seller': [
                'process_sales', 'view_basic_inventory', 'add_clients'
            ]
        }
        
        role_permissions = permissions.get(self.role, [])
        return permission in role_permissions
