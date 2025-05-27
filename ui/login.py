"""
Login Dialog for Hardware POS System

Provides user authentication interface.
"""

import logging
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
                             QLineEdit, QPushButton, QLabel, QMessageBox,
                             QFrame, QCheckBox, QSpacerItem, QSizePolicy)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QPixmap, QIcon, QFont

from core.database import DatabaseManager
from core.auth import AuthenticationManager, AuthenticationError
from utils.logger import get_logger


class LoginDialog(QDialog):
    """Login dialog for user authentication."""
      # Signal emitted when user logs in successfully
    login_successful = pyqtSignal(object)  # Emits user object
    
    def __init__(self, db_manager: DatabaseManager = None, auth_manager: AuthenticationManager = None, parent=None):
        """Initialize login dialog.
        
        Args:
            db_manager: Database manager instance (optional)
            auth_manager: Authentication manager instance (optional)
            parent: Parent widget
        """
        super().__init__(parent)
        self.logger = get_logger(__name__)
        
        # Initialize managers
        if db_manager and auth_manager:
            self.db_manager = db_manager
            self.auth_manager = auth_manager
        else:
            self.db_manager = DatabaseManager()
            self.auth_manager = AuthenticationManager(self.db_manager)
        
        self.current_user = None
        
        self.setup_ui()
        self.setup_connections()
        
        # Set focus to username field
        self.username_edit.setFocus()
    
    def setup_ui(self):
        """Setup the user interface."""
        self.setWindowTitle("Hardware POS - Login")
        self.setFixedSize(400, 350)
        self.setWindowFlags(Qt.Dialog | Qt.WindowCloseButtonHint)
        
        # Main layout
        main_layout = QVBoxLayout()
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(30, 30, 30, 30)
        
        # Logo/Title section
        title_layout = QVBoxLayout()
        title_layout.setAlignment(Qt.AlignCenter)
        
        # Title
        title_label = QLabel("Hardware POS System")
        title_font = QFont()
        title_font.setPointSize(18)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("color: #4a90e2; margin-bottom: 10px;")
        
        subtitle_label = QLabel("Point of Sale Management")
        subtitle_label.setAlignment(Qt.AlignCenter)
        subtitle_label.setStyleSheet("color: #666666; font-size: 12px;")
        
        title_layout.addWidget(title_label)
        title_layout.addWidget(subtitle_label)
        
        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        separator.setStyleSheet("border: 1px solid #cccccc;")
        
        # Login form
        form_layout = QFormLayout()
        form_layout.setSpacing(15)
        
        # Username field
        self.username_edit = QLineEdit()
        self.username_edit.setPlaceholderText("Enter your username")
        self.username_edit.setMinimumHeight(35)
        
        # Password field
        self.password_edit = QLineEdit()
        self.password_edit.setPlaceholderText("Enter your password")
        self.password_edit.setEchoMode(QLineEdit.Password)
        self.password_edit.setMinimumHeight(35)
        
        # Remember me checkbox
        self.remember_checkbox = QCheckBox("Remember username")
        
        form_layout.addRow("Username:", self.username_edit)
        form_layout.addRow("Password:", self.password_edit)
        form_layout.addRow("", self.remember_checkbox)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        
        # Spacer
        button_layout.addItem(QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))
        
        # Cancel button
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setMinimumSize(80, 35)
        
        # Login button
        self.login_button = QPushButton("Login")
        self.login_button.setMinimumSize(80, 35)
        self.login_button.setDefault(True)
        self.login_button.setProperty("class", "primary")
        
        button_layout.addWidget(self.cancel_button)
        button_layout.addWidget(self.login_button)
        
        # Status label
        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("color: #e74c3c; font-size: 11px;")
        self.status_label.hide()
        
        # Add to main layout
        main_layout.addLayout(title_layout)
        main_layout.addWidget(separator)
        main_layout.addLayout(form_layout)
        main_layout.addLayout(button_layout)
        main_layout.addWidget(self.status_label)
        
        # Add spacer at bottom
        main_layout.addItem(QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding))
        
        self.setLayout(main_layout)
        
        # Load saved username if enabled
        self.load_saved_credentials()
    
    def setup_connections(self):
        """Setup signal connections."""
        self.login_button.clicked.connect(self.handle_login)
        self.cancel_button.clicked.connect(self.reject)
        
        # Enter key handling
        self.username_edit.returnPressed.connect(self.password_edit.setFocus)
        self.password_edit.returnPressed.connect(self.handle_login)
    
    def handle_login(self):
        """Handle login button click."""
        username = self.username_edit.text().strip()
        password = self.password_edit.text()
        
        # Validate input
        if not username:
            self.show_status("Please enter your username.", error=True)
            self.username_edit.setFocus()
            return
        
        if not password:
            self.show_status("Please enter your password.", error=True)
            self.password_edit.setFocus()
            return
        
        # Disable buttons during login
        self.login_button.setEnabled(False)
        self.cancel_button.setEnabled(False)
        self.show_status("Authenticating...", error=False)
        
        try:
            # Attempt authentication
            if self.auth_manager.authenticate(username, password):
                # Save username if remember me is checked
                if self.remember_checkbox.isChecked():
                    self.save_credentials(username)
                else:
                    self.clear_saved_credentials()
                  # Emit success signal
                self.current_user = self.auth_manager.get_current_user()
                self.login_successful.emit(self.current_user)
                
                self.logger.info(f"User '{username}' logged in successfully")
                self.accept()
            else:
                self.show_status("Invalid username or password.", error=True)
                
        except AuthenticationError as e:
            self.show_status(str(e), error=True)
            self.logger.warning(f"Login failed for user '{username}': {e}")
            
        except Exception as e:
            self.show_status("Login system error. Please try again.", error=True)
            self.logger.error(f"Login error: {e}")
        
        finally:
            # Re-enable buttons
            self.login_button.setEnabled(True)
            self.cancel_button.setEnabled(True)
            
            # Clear password field on failure
            if not self.auth_manager.is_authenticated():
                self.password_edit.clear()
                self.password_edit.setFocus()
    
    def show_status(self, message: str, error: bool = False):
        """Show status message.
        
        Args:
            message: Status message
            error: Whether this is an error message
        """
        self.status_label.setText(message)
        
        if error:
            self.status_label.setStyleSheet("color: #e74c3c; font-size: 11px;")
        else:
            self.status_label.setStyleSheet("color: #27ae60; font-size: 11px;")
        
        self.status_label.show()
    
    def load_saved_credentials(self):
        """Load saved credentials from settings."""
        try:
            from config.settings import settings
            saved_username = settings.get('ui.saved_username', '')
            
            if saved_username:
                self.username_edit.setText(saved_username)
                self.remember_checkbox.setChecked(True)
                self.password_edit.setFocus()
            
        except Exception as e:
            self.logger.debug(f"Could not load saved credentials: {e}")
    
    def save_credentials(self, username: str):
        """Save username to settings.
        
        Args:
            username: Username to save
        """
        try:
            from config.settings import settings
            settings.set('ui.saved_username', username)
            settings.save()
            
        except Exception as e:
            self.logger.debug(f"Could not save credentials: {e}")
    
    def clear_saved_credentials(self):
        """Clear saved credentials."""
        try:
            from config.settings import settings
            settings.set('ui.saved_username', '')
            settings.save()
            
        except Exception as e:
            self.logger.debug(f"Could not clear saved credentials: {e}")
    
    def get_auth_manager(self) -> AuthenticationManager:
        """Get the authentication manager.
        
        Returns:
            Authentication manager instance
        """
        return self.auth_manager
    
    def closeEvent(self, event):
        """Handle dialog close event."""
        # If user closes dialog without logging in, reject it
        if not self.auth_manager.is_authenticated():
            self.reject()
        event.accept()


class PasswordChangeDialog(QDialog):
    """Dialog for changing user password."""
    
    def __init__(self, auth_manager: AuthenticationManager, parent=None):
        """Initialize password change dialog.
        
        Args:
            auth_manager: Authentication manager
            parent: Parent widget
        """
        super().__init__(parent)
        self.auth_manager = auth_manager
        self.logger = get_logger(__name__)
        
        self.setup_ui()
        self.setup_connections()
    
    def setup_ui(self):
        """Setup the user interface."""
        self.setWindowTitle("Change Password")
        self.setFixedSize(350, 250)
        self.setModal(True)
        
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Form
        form_layout = QFormLayout()
        
        self.current_password_edit = QLineEdit()
        self.current_password_edit.setEchoMode(QLineEdit.Password)
        self.current_password_edit.setMinimumHeight(30)
        
        self.new_password_edit = QLineEdit()
        self.new_password_edit.setEchoMode(QLineEdit.Password)
        self.new_password_edit.setMinimumHeight(30)
        
        self.confirm_password_edit = QLineEdit()
        self.confirm_password_edit.setEchoMode(QLineEdit.Password)
        self.confirm_password_edit.setMinimumHeight(30)
        
        form_layout.addRow("Current Password:", self.current_password_edit)
        form_layout.addRow("New Password:", self.new_password_edit)
        form_layout.addRow("Confirm Password:", self.confirm_password_edit)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.cancel_button = QPushButton("Cancel")
        self.change_button = QPushButton("Change Password")
        self.change_button.setDefault(True)
        
        button_layout.addWidget(self.cancel_button)
        button_layout.addWidget(self.change_button)
        
        # Status
        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.hide()
        
        layout.addLayout(form_layout)
        layout.addLayout(button_layout)
        layout.addWidget(self.status_label)
        
        self.setLayout(layout)
    
    def setup_connections(self):
        """Setup signal connections."""
        self.change_button.clicked.connect(self.handle_change_password)
        self.cancel_button.clicked.connect(self.reject)
        
        # Enter key handling
        self.current_password_edit.returnPressed.connect(self.new_password_edit.setFocus)
        self.new_password_edit.returnPressed.connect(self.confirm_password_edit.setFocus)
        self.confirm_password_edit.returnPressed.connect(self.handle_change_password)
    
    def handle_change_password(self):
        """Handle password change."""
        current_password = self.current_password_edit.text()
        new_password = self.new_password_edit.text()
        confirm_password = self.confirm_password_edit.text()
        
        # Validate input
        if not current_password:
            self.show_status("Please enter your current password.", error=True)
            return
        
        if not new_password:
            self.show_status("Please enter a new password.", error=True)
            return
        
        if new_password != confirm_password:
            self.show_status("New passwords do not match.", error=True)
            return
        
        if len(new_password) < 6:
            self.show_status("Password must be at least 6 characters long.", error=True)
            return
        
        try:
            user = self.auth_manager.get_current_user()
            if user and self.auth_manager.change_password(user.id, current_password, new_password):
                QMessageBox.information(self, "Success", "Password changed successfully.")
                self.accept()
            else:
                self.show_status("Failed to change password.", error=True)
                
        except AuthenticationError as e:
            self.show_status(str(e), error=True)
            
        except Exception as e:
            self.show_status("Error changing password.", error=True)
            self.logger.error(f"Password change error: {e}")
    
    def show_status(self, message: str, error: bool = False):
        """Show status message."""
        self.status_label.setText(message)
        
        if error:
            self.status_label.setStyleSheet("color: #e74c3c; font-size: 11px;")
        else:
            self.status_label.setStyleSheet("color: #27ae60; font-size: 11px;")
        
        self.status_label.show()
