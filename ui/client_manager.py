"""
Client Manager Dialog

Dialog for managing clients in the Hardware POS system.
Provides CRUD operations for client management.
"""

import logging
from typing import Optional, List
from decimal import Decimal
from datetime import datetime
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QFormLayout,
    QTableWidget, QTableWidgetItem, QLineEdit, QPushButton, QLabel,
    QGroupBox, QSplitter, QMessageBox, QHeaderView, QComboBox,
    QTextEdit, QSpinBox, QDoubleSpinBox, QCheckBox, QDateEdit,
    QFrame, QAbstractItemView
)
from PyQt5.QtCore import Qt, pyqtSignal, QDate
from PyQt5.QtGui import QFont, QIcon

from core.database import DatabaseManager
from core.clients import ClientManager
from models import User, Client
from utils.logger import get_logger


class ClientManagerDialog(QDialog):
    """Dialog for managing clients."""
    
    clients_updated = pyqtSignal()
    
    def __init__(self, db_manager: DatabaseManager, client_manager: ClientManager, 
                 current_user: User, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.client_manager = client_manager
        self.current_user = current_user
        self.logger = get_logger(__name__)
        
        self.setWindowTitle("Client Manager")
        self.setGeometry(100, 100, 1200, 800)
        self.setModal(True)
        
        self.selected_client = None
        
        self.setup_ui()
        self.load_clients()
    
    def setup_ui(self):
        """Setup the user interface."""
        layout = QVBoxLayout(self)
        
        # Title
        title_label = QLabel("Client Management")
        title_label.setFont(QFont("Arial", 16, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        # Main splitter
        splitter = QSplitter(Qt.Horizontal)
        layout.addWidget(splitter)
        
        # Left side - Client list
        left_widget = QGroupBox("Clients")
        left_layout = QVBoxLayout(left_widget)
        
        # Search and filter controls
        search_layout = QHBoxLayout()
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search clients...")
        self.search_input.textChanged.connect(self.search_clients)
        search_layout.addWidget(QLabel("Search:"))
        search_layout.addWidget(self.search_input)
        
        self.status_filter = QComboBox()
        self.status_filter.addItems(["All", "Active", "Inactive"])
        self.status_filter.currentTextChanged.connect(self.filter_clients)
        search_layout.addWidget(QLabel("Status:"))
        search_layout.addWidget(self.status_filter)
        
        left_layout.addLayout(search_layout)
        
        # Client table
        self.client_table = QTableWidget()
        self.client_table.setColumnCount(6)
        self.client_table.setHorizontalHeaderLabels([
            "Code", "Name", "Phone", "Email", "Credit Limit", "Status"
        ])
        
        # Configure table
        header = self.client_table.horizontalHeader()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(QHeaderView.Interactive)
        
        self.client_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.client_table.setAlternatingRowColors(True)
        self.client_table.itemSelectionChanged.connect(self.on_client_selected)
        self.client_table.itemDoubleClicked.connect(self.edit_client)
        
        left_layout.addWidget(self.client_table)
        
        # Table buttons
        table_buttons = QHBoxLayout()
        
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self.load_clients)
        table_buttons.addWidget(self.refresh_btn)
        
        table_buttons.addStretch()
        
        self.delete_btn = QPushButton("Delete")
        self.delete_btn.clicked.connect(self.delete_client)
        self.delete_btn.setEnabled(False)
        table_buttons.addWidget(self.delete_btn)
        
        left_layout.addLayout(table_buttons)
        
        splitter.addWidget(left_widget)
        
        # Right side - Client form
        right_widget = QGroupBox("Client Details")
        right_layout = QVBoxLayout(right_widget)
        
        # Client form
        form_layout = QFormLayout()
        
        self.customer_code_input = QLineEdit()
        self.customer_code_input.setMaxLength(20)
        form_layout.addRow("Customer Code:", self.customer_code_input)
        
        self.first_name_input = QLineEdit()
        self.first_name_input.setMaxLength(50)
        form_layout.addRow("First Name:", self.first_name_input)
        
        self.last_name_input = QLineEdit()
        self.last_name_input.setMaxLength(50)
        form_layout.addRow("Last Name:", self.last_name_input)
        
        self.phone_input = QLineEdit()
        self.phone_input.setMaxLength(20)
        form_layout.addRow("Phone:", self.phone_input)
        
        self.email_input = QLineEdit()
        self.email_input.setMaxLength(100)
        form_layout.addRow("Email:", self.email_input)
        
        self.address_input = QTextEdit()
        self.address_input.setMaximumHeight(80)
        form_layout.addRow("Address:", self.address_input)
        
        self.credit_limit_input = QDoubleSpinBox()
        self.credit_limit_input.setRange(0, 999999.99)
        self.credit_limit_input.setDecimals(2)
        self.credit_limit_input.setSuffix(" $")
        form_layout.addRow("Credit Limit:", self.credit_limit_input)
        
        self.is_active_checkbox = QCheckBox("Active")
        self.is_active_checkbox.setChecked(True)
        form_layout.addRow("Status:", self.is_active_checkbox)
        
        self.notes_input = QTextEdit()
        self.notes_input.setMaximumHeight(80)
        form_layout.addRow("Notes:", self.notes_input)
        
        right_layout.addLayout(form_layout)
        
        # Form buttons
        form_buttons = QHBoxLayout()
        
        self.new_btn = QPushButton("New")
        self.new_btn.clicked.connect(self.new_client)
        form_buttons.addWidget(self.new_btn)
        
        self.save_btn = QPushButton("Save")
        self.save_btn.clicked.connect(self.save_client)
        form_buttons.addWidget(self.save_btn)
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.cancel_edit)
        form_buttons.addWidget(self.cancel_btn)
        
        form_buttons.addStretch()
        
        right_layout.addLayout(form_buttons)
        
        # Client statistics
        stats_group = QGroupBox("Client Statistics")
        stats_layout = QFormLayout(stats_group)
        
        self.total_purchases_label = QLabel("$0.00")
        stats_layout.addRow("Total Purchases:", self.total_purchases_label)
        
        self.current_balance_label = QLabel("$0.00")
        stats_layout.addRow("Current Balance:", self.current_balance_label)
        
        self.last_purchase_label = QLabel("Never")
        stats_layout.addRow("Last Purchase:", self.last_purchase_label)
        
        right_layout.addWidget(stats_group)
        
        splitter.addWidget(right_widget)
        
        # Set splitter proportions
        splitter.setSizes([600, 600])
        
        # Dialog buttons
        dialog_buttons = QHBoxLayout()
        
        self.close_btn = QPushButton("Close")
        self.close_btn.clicked.connect(self.accept)
        dialog_buttons.addStretch()
        dialog_buttons.addWidget(self.close_btn)
        
        layout.addLayout(dialog_buttons)
        
        # Clear form initially
        self.clear_form()
    
    def load_clients(self):
        """Load all clients into the table."""
        try:
            clients = self.client_manager.get_all_clients()
            
            self.client_table.setRowCount(len(clients))
            
            for row, client in enumerate(clients):
                # Customer Code
                self.client_table.setItem(row, 0, QTableWidgetItem(client.customer_code or ""))
                
                # Full Name
                self.client_table.setItem(row, 1, QTableWidgetItem(client.full_name or ""))
                
                # Phone
                self.client_table.setItem(row, 2, QTableWidgetItem(client.phone or ""))
                
                # Email
                self.client_table.setItem(row, 3, QTableWidgetItem(client.email or ""))
                
                # Credit Limit
                credit_limit = f"${client.credit_limit:.2f}" if client.credit_limit else "$0.00"
                self.client_table.setItem(row, 4, QTableWidgetItem(credit_limit))
                
                # Status
                status = "Active" if client.is_active else "Inactive"
                self.client_table.setItem(row, 5, QTableWidgetItem(status))
                
                # Store client object in first column
                self.client_table.item(row, 0).setData(Qt.UserRole, client)
            
            # Resize columns to content
            self.client_table.resizeColumnsToContents()
            
        except Exception as e:
            self.logger.error(f"Error loading clients: {e}")
            QMessageBox.critical(self, "Error", f"Failed to load clients: {e}")
    
    def search_clients(self):
        """Search clients based on search input."""
        search_term = self.search_input.text().lower()
        
        for row in range(self.client_table.rowCount()):
            show_row = False
            
            # Search in all visible columns
            for col in range(self.client_table.columnCount()):
                item = self.client_table.item(row, col)
                if item and search_term in item.text().lower():
                    show_row = True
                    break
            
            self.client_table.setRowHidden(row, not show_row)
    
    def filter_clients(self):
        """Filter clients by status."""
        status_filter = self.status_filter.currentText()
        
        for row in range(self.client_table.rowCount()):
            show_row = True
            
            if status_filter != "All":
                status_item = self.client_table.item(row, 5)
                if status_item:
                    client_status = status_item.text()
                    show_row = (status_filter == client_status)
            
            # Apply search filter as well
            if show_row:
                search_term = self.search_input.text().lower()
                if search_term:
                    show_row = False
                    for col in range(self.client_table.columnCount()):
                        item = self.client_table.item(row, col)
                        if item and search_term in item.text().lower():
                            show_row = True
                            break
            
            self.client_table.setRowHidden(row, not show_row)
    
    def on_client_selected(self):
        """Handle client selection."""
        selected_rows = self.client_table.selectionModel().selectedRows()
        
        if selected_rows:
            row = selected_rows[0].row()
            item = self.client_table.item(row, 0)
            
            if item:
                self.selected_client = item.data(Qt.UserRole)
                self.load_client_details(self.selected_client)
                self.delete_btn.setEnabled(True)
            else:
                self.selected_client = None
                self.clear_form()
                self.delete_btn.setEnabled(False)
        else:
            self.selected_client = None
            self.clear_form()
            self.delete_btn.setEnabled(False)
    
    def load_client_details(self, client: Client):
        """Load client details into the form."""
        self.customer_code_input.setText(client.customer_code or "")
        self.first_name_input.setText(client.first_name or "")
        self.last_name_input.setText(client.last_name or "")
        self.phone_input.setText(client.phone or "")
        self.email_input.setText(client.email or "")
        self.address_input.setPlainText(client.address or "")
        self.credit_limit_input.setValue(float(client.credit_limit or 0))
        self.is_active_checkbox.setChecked(client.is_active)
        self.notes_input.setPlainText("")  # Notes field not in Client model yet
        
        # Load client statistics
        self.load_client_statistics(client.id)
    
    def clear_form(self):
        """Clear the client form."""
        self.customer_code_input.clear()
        self.first_name_input.clear()
        self.last_name_input.clear()
        self.phone_input.clear()
        self.email_input.clear()
        self.address_input.clear()
        self.credit_limit_input.setValue(0)
        self.is_active_checkbox.setChecked(True)
        self.notes_input.clear()
        
        self.total_purchases_label.setText("$0.00")
        self.current_balance_label.setText("$0.00")
        self.last_purchase_label.setText("Never")
    
    def new_client(self):
        """Start creating a new client."""
        self.selected_client = None
        self.client_table.clearSelection()
        self.clear_form()
        self.first_name_input.setFocus()
    
    def save_client(self):
        """Save the client."""
        try:
            # Validate required fields
            if not self.first_name_input.text().strip():
                QMessageBox.warning(self, "Validation Error", "First name is required.")
                self.first_name_input.setFocus()
                return
            
            if not self.last_name_input.text().strip():
                QMessageBox.warning(self, "Validation Error", "Last name is required.")
                self.last_name_input.setFocus()
                return
            
            # Create client data
            if self.selected_client:
                # Update existing client
                client_data = Client(
                    id=self.selected_client.id,
                    customer_code=self.customer_code_input.text().strip() or self.selected_client.customer_code,
                    first_name=self.first_name_input.text().strip(),
                    last_name=self.last_name_input.text().strip(),
                    phone=self.phone_input.text().strip() or None,
                    email=self.email_input.text().strip() or None,
                    address=self.address_input.toPlainText().strip() or None,
                    city=self.selected_client.city,  # Keep existing city for now
                    postal_code=self.selected_client.postal_code,  # Keep existing postal_code for now
                    credit_limit=Decimal(str(self.credit_limit_input.value())),
                    current_balance=self.selected_client.current_balance,  # Keep existing balance
                    is_active=self.is_active_checkbox.isChecked(),
                    created_at=self.selected_client.created_at
                )
                self.client_manager.update_client(client_data)
                QMessageBox.information(self, "Success", "Client updated successfully.")
            else:
                # Create new client
                client_data = Client(
                    id=None,
                    customer_code=self.customer_code_input.text().strip() or None,
                    first_name=self.first_name_input.text().strip(),
                    last_name=self.last_name_input.text().strip(),
                    phone=self.phone_input.text().strip() or None,
                    email=self.email_input.text().strip() or None,
                    address=self.address_input.toPlainText().strip() or None,
                    city=None,
                    postal_code=None,
                    credit_limit=Decimal(str(self.credit_limit_input.value())),
                    current_balance=Decimal('0'),
                    is_active=self.is_active_checkbox.isChecked(),
                    created_at=datetime.now()
                )
                client_id = self.client_manager.add_client(client_data)
                QMessageBox.information(self, "Success", f"Client created successfully with ID: {client_id}")
            
            # Reload the clients list
            self.load_clients()
            self.clear_form()
            self.selected_client = None
            
            # Emit signal to update parent window
            self.clients_updated.emit()
            
        except Exception as e:
            self.logger.error(f"Error saving client: {e}")
            QMessageBox.critical(self, "Error", f"Failed to save client: {e}")
    
    def edit_client(self):
        """Edit the selected client."""
        if self.selected_client:
            self.load_client_details(self.selected_client)
    
    def delete_client(self):
        """Delete the selected client."""
        if not self.selected_client:
            return
        
        reply = QMessageBox.question(
            self, "Confirm Delete", 
            f"Are you sure you want to delete client '{self.selected_client.full_name}'?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                self.client_manager.delete_client(self.selected_client.id)
                QMessageBox.information(self, "Success", "Client deleted successfully.")
                
                # Reload the clients list
                self.load_clients()
                self.clear_form()
                self.selected_client = None
                
                # Emit signal to update parent window
                self.clients_updated.emit()
                
            except Exception as e:
                self.logger.error(f"Error deleting client: {e}")
                QMessageBox.critical(self, "Error", f"Failed to delete client: {e}")
    
    def cancel_edit(self):
        """Cancel current edit operation."""
        self.selected_client = None
        self.client_table.clearSelection()
        self.clear_form()
    
    def load_client_statistics(self, client_id: int):
        """Load client statistics."""
        try:
            stats = self.client_manager.calculate_client_stats(client_id)
            if stats:
                self.total_purchases_label.setText(f"${stats.get('total_spent', 0):.2f}")
                client_data = stats.get('client')
                if client_data:
                    self.current_balance_label.setText(f"${client_data.current_balance:.2f}")
                else:
                    self.current_balance_label.setText("$0.00")
                
                last_purchase = stats.get('last_purchase_date')
                if last_purchase:
                    self.last_purchase_label.setText(last_purchase[:10])  # Just the date part
                else:
                    self.last_purchase_label.setText("Never")
            else:
                self.total_purchases_label.setText("$0.00")
                self.current_balance_label.setText("$0.00")
                self.last_purchase_label.setText("Never")
        except Exception as e:
            self.logger.error(f"Error loading client statistics: {e}")
            self.total_purchases_label.setText("Error")
            self.current_balance_label.setText("Error")
            self.last_purchase_label.setText("Error")
