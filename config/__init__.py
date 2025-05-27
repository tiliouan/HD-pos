"""
Settings Manager for Hardware POS System

Handles loading, saving, and managing application settings.
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional


class Settings:
    """Manages application settings with JSON configuration file."""
    
    def __init__(self, config_file: Optional[str] = None):
        """Initialize settings manager.
        
        Args:
            config_file: Path to configuration file. If None, uses default location.
        """
        if config_file is None:
            self.config_path = Path(__file__).parent / "settings.json"
        else:
            self.config_path = Path(config_file)
        
        self._settings = {}
        self._load_settings()
    
    def _load_settings(self) -> None:
        """Load settings from configuration file."""
        try:
            if self.config_path.exists():
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    self._settings = json.load(f)
            else:
                self._create_default_settings()
        except Exception as e:
            print(f"Error loading settings: {e}")
            self._create_default_settings()
    
    def _create_default_settings(self) -> None:
        """Create default settings if config file doesn't exist."""
        self._settings = {
            "database": {
                "type": "sqlite",
                "filename": "hardware_pos.db",
                "backup_interval": 24
            },
            "ui": {
                "theme": "modern",
                "language": "en",
                "window_size": [1200, 800],
                "maximize_on_startup": False
            },
            "pos": {
                "tax_rate": 0.13,
                "currency": "CAD",
                "currency_symbol": "$",
                "receipt_template": "default",
                "auto_backup": True
            },
            "printing": {
                "receipt_printer": "",
                "barcode_printer": "",
                "receipt_width": 80,
                "auto_print_receipt": False
            },
            "inventory": {
                "low_stock_threshold": 10,
                "auto_reorder": False,
                "track_serial_numbers": True
            },
            "network": {
                "sync_enabled": False,
                "sync_interval": 300,
                "server_url": "",
                "api_key": ""
            },
            "security": {
                "session_timeout": 3600,
                "password_policy": {
                    "min_length": 8,
                    "require_special_chars": True,
                    "require_numbers": True
                }
            }
        }
        self.save()
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a setting value using dot notation.
        
        Args:
            key: Setting key (e.g., 'database.type' or 'ui.theme')
            default: Default value if key not found
            
        Returns:
            Setting value or default
        """
        keys = key.split('.')
        value = self._settings
        
        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default
    
    def set(self, key: str, value: Any) -> None:
        """Set a setting value using dot notation.
        
        Args:
            key: Setting key (e.g., 'database.type' or 'ui.theme')
            value: Value to set
        """
        keys = key.split('.')
        setting = self._settings
        
        # Navigate to the parent dictionary
        for k in keys[:-1]:
            if k not in setting:
                setting[k] = {}
            setting = setting[k]
        
        # Set the value
        setting[keys[-1]] = value
    
    def save(self) -> bool:
        """Save settings to configuration file.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Ensure directory exists
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self._settings, f, indent=4, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Error saving settings: {e}")
            return False
    
    def get_all(self) -> Dict[str, Any]:
        """Get all settings as a dictionary.
        
        Returns:
            Complete settings dictionary
        """
        return self._settings.copy()
    
    def reset_to_defaults(self) -> None:
        """Reset all settings to default values."""
        self._create_default_settings()
    
    def get_database_path(self) -> Path:
        """Get the full path to the database file.
        
        Returns:
            Path to database file
        """
        db_filename = self.get('database.filename', 'hardware_pos.db')
        return Path(__file__).parent.parent / db_filename
    
    def get_backup_path(self) -> Path:
        """Get the path to the backup directory.
        
        Returns:
            Path to backup directory
        """
        return Path(__file__).parent.parent / "backups"
    
    def get_assets_path(self) -> Path:
        """Get the path to the assets directory.
        
        Returns:
            Path to assets directory
        """
        return Path(__file__).parent.parent / "assets"


# Global settings instance
settings = Settings()
