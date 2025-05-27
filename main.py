#!/usr/bin/env python3
"""
Hardware POS System - Main Entry Point

A comprehensive Point of Sale system for hardware stores with inventory management,
client management, sales processing, and reporting capabilities.
"""

import sys
import os
import logging
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from PyQt5.QtWidgets import QApplication, QMessageBox
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon

from core.database import DatabaseManager
from core.auth import AuthenticationManager
from ui.main_window import MainWindow
from ui.login import LoginDialog
from utils.logger import setup_logger
from config.settings import Settings


def setup_application():
    """Setup the application environment and dependencies."""
    # Setup logging
    setup_logger()
    logger = logging.getLogger(__name__)
    
    # Load settings
    settings = Settings()
    
    # Initialize database
    db_manager = DatabaseManager()
    if not db_manager.initialize():
        logger.error("Failed to initialize database")
        return False
    
    logger.info("Application setup completed successfully")
    return True


def main():
    """Main application entry point."""
    app = QApplication(sys.argv)
    app.setApplicationName("Hardware POS System")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("Hardware Store Solutions")
    
    # Set application icon
    icon_path = project_root / "assets" / "icons" / "app_icon.png"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))
    
    # Load stylesheet
    styles_path = project_root / "config" / "styles.qss"
    if styles_path.exists():
        with open(styles_path, 'r') as f:
            app.setStyleSheet(f.read())
    
    # Setup application
    if not setup_application():
        QMessageBox.critical(None, "Error", "Failed to initialize the application. Please check the logs.")
        return 1
    
    # Initialize database and authentication managers
    db_manager = DatabaseManager()
    auth_manager = AuthenticationManager(db_manager)
    
    # Show login dialog
    login_dialog = LoginDialog(db_manager, auth_manager)
    if login_dialog.exec_() == login_dialog.Accepted:
        # Login successful, get the authenticated user
        current_user = auth_manager.get_current_user()
        if current_user:
            # Show main window
            main_window = MainWindow(db_manager, auth_manager, current_user)
            main_window.show()
            
            return app.exec_()
        else:
            QMessageBox.critical(None, "Error", "Authentication failed. Please try again.")
            return 1
    else:
        # Login cancelled or failed
        return 0


if __name__ == "__main__":
    sys.exit(main())
