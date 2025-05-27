"""
Category Manager Dialog

Dialog for managing product categories in the Hardware POS system.
Provides CRUD operations for category management.
"""

import logging
from typing import Optional, List
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QTableWidget, QTableWidgetItem, QLineEdit, QPushButton, QLabel,
    QGroupBox, QSplitter, QMessageBox, QHeaderView, QTextEdit,
    QCheckBox, QFrame, QAbstractItemView
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont

from core.database import DatabaseManager
from core.inventory import InventoryManager
from models import User
from utils.logger import get_logger


class CategoryManagerDialog(QDialog):
    """Dialog for managing product categories."""
    
    categories_updated = pyqtSignal()
    
    def __init__(self, db_manager: DatabaseManager, inventory_manager: InventoryManager, 
                 current_user: User, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.inventory_manager = inventory_manager
        self.current_user = current_user
        self.logger = get_logger(__name__)
        
        self.setWindowTitle("Category Manager")
        self.setGeometry(100, 100, 800, 600)
        self.setModal(True)
        
        self.selected_category = None
        
        self.setup_ui()
        self.load_categories()
    
    def setup_ui(self):
        """Setup the user interface."""
        layout = QVBoxLayout(self)
        
        # Title
        title_label = QLabel("Category Management")
        title_label.setFont(QFont("Arial", 16, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        # Main splitter
        splitter = QSplitter(Qt.Horizontal)
        layout.addWidget(splitter)
        
        # Left side - Category list
        left_widget = QGroupBox("Categories")
        left_layout = QVBoxLayout(left_widget)
        
        # Search controls
        search_layout = QHBoxLayout()
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search categories...")
        self.search_input.textChanged.connect(self.search_categories)
        search_layout.addWidget(QLabel("Search:"))
        search_layout.addWidget(self.search_input)
        
        left_layout.addLayout(search_layout)
        
        # Category table
        self.category_table = QTableWidget()
        self.category_table.setColumnCount(3)
        self.category_table.setHorizontalHeaderLabels([
            "Name", "Description", "Product Count"
        ])
        
        # Configure table
        header = self.category_table.horizontalHeader()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(QHeaderView.Interactive)
        
        self.category_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.category_table.setAlternatingRowColors(True)
        self.category_table.itemSelectionChanged.connect(self.on_category_selected)
        self.category_table.itemDoubleClicked.connect(self.edit_category)
        
        left_layout.addWidget(self.category_table)
        
        # Table buttons
        table_buttons = QHBoxLayout()
        
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self.load_categories)
        table_buttons.addWidget(self.refresh_btn)
        
        table_buttons.addStretch()
        
        self.delete_btn = QPushButton("Delete")
        self.delete_btn.clicked.connect(self.delete_category)
        self.delete_btn.setEnabled(False)
        table_buttons.addWidget(self.delete_btn)
        
        left_layout.addLayout(table_buttons)
        
        splitter.addWidget(left_widget)
        
        # Right side - Category form
        right_widget = QGroupBox("Category Details")
        right_layout = QVBoxLayout(right_widget)
        
        # Category form
        form_layout = QFormLayout()
        
        self.name_input = QLineEdit()
        self.name_input.setMaxLength(50)
        form_layout.addRow("Name:", self.name_input)
        
        self.description_input = QTextEdit()
        self.description_input.setMaximumHeight(100)
        form_layout.addRow("Description:", self.description_input)
        
        right_layout.addLayout(form_layout)
        
        # Form buttons
        form_buttons = QHBoxLayout()
        
        self.new_btn = QPushButton("New")
        self.new_btn.clicked.connect(self.new_category)
        form_buttons.addWidget(self.new_btn)
        
        self.save_btn = QPushButton("Save")
        self.save_btn.clicked.connect(self.save_category)
        form_buttons.addWidget(self.save_btn)
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.cancel_edit)
        form_buttons.addWidget(self.cancel_btn)
        
        form_buttons.addStretch()
        
        right_layout.addLayout(form_buttons)
        
        splitter.addWidget(right_widget)
        
        # Set splitter proportions
        splitter.setSizes([500, 300])
        
        # Dialog buttons
        dialog_buttons = QHBoxLayout()
        
        self.close_btn = QPushButton("Close")
        self.close_btn.clicked.connect(self.accept)
        dialog_buttons.addStretch()
        dialog_buttons.addWidget(self.close_btn)
        
        layout.addLayout(dialog_buttons)
        
        # Clear form initially
        self.clear_form()
    
    def load_categories(self):
        """Load all categories into the table."""
        try:
            categories = self.inventory_manager.get_all_categories()
            
            self.category_table.setRowCount(len(categories))
            
            for row, category in enumerate(categories):
                # Name
                self.category_table.setItem(row, 0, QTableWidgetItem(category.name or ""))
                
                # Description
                description = category.description or ""
                if len(description) > 50:
                    description = description[:47] + "..."
                self.category_table.setItem(row, 1, QTableWidgetItem(description))
                
                # Product Count (placeholder)
                self.category_table.setItem(row, 2, QTableWidgetItem("0"))
                
                # Store category object in first column
                self.category_table.item(row, 0).setData(Qt.UserRole, category)
            
            # Resize columns to content
            self.category_table.resizeColumnsToContents()
            
        except Exception as e:
            self.logger.error(f"Error loading categories: {e}")
            QMessageBox.critical(self, "Error", f"Failed to load categories: {e}")
    
    def search_categories(self):
        """Search categories based on search input."""
        search_term = self.search_input.text().lower()
        
        for row in range(self.category_table.rowCount()):
            show_row = False
            
            # Search in name and description columns
            for col in [0, 1]:
                item = self.category_table.item(row, col)
                if item and search_term in item.text().lower():
                    show_row = True
                    break
            
            self.category_table.setRowHidden(row, not show_row)
    
    def on_category_selected(self):
        """Handle category selection."""
        selected_rows = self.category_table.selectionModel().selectedRows()
        
        if selected_rows:
            row = selected_rows[0].row()
            item = self.category_table.item(row, 0)
            
            if item:
                self.selected_category = item.data(Qt.UserRole)
                self.load_category_details(self.selected_category)
                self.delete_btn.setEnabled(True)
            else:
                self.selected_category = None
                self.clear_form()
                self.delete_btn.setEnabled(False)
        else:
            self.selected_category = None
            self.clear_form()
            self.delete_btn.setEnabled(False)
    
    def load_category_details(self, category):
        """Load category details into the form."""
        self.name_input.setText(category.name or "")
        self.description_input.setPlainText(category.description or "")
    
    def clear_form(self):
        """Clear the category form."""
        self.name_input.clear()
        self.description_input.clear()
    
    def new_category(self):
        """Start creating a new category."""
        self.selected_category = None
        self.category_table.clearSelection()
        self.clear_form()
        self.name_input.setFocus()
    
    def save_category(self):
        """Save the category."""
        try:
            # Validate required fields
            if not self.name_input.text().strip():
                QMessageBox.warning(self, "Validation Error", "Category name is required.")
                self.name_input.setFocus()
                return
            
            # Create category data
            category_data = {
                'name': self.name_input.text().strip(),
                'description': self.description_input.toPlainText().strip() or None
            }
            
            if self.selected_category:
                # Update existing category
                category_data['id'] = self.selected_category.id
                self.inventory_manager.update_category(category_data)
                QMessageBox.information(self, "Success", "Category updated successfully.")
            else:
                # Create new category
                category_id = self.inventory_manager.add_category(category_data)
                QMessageBox.information(self, "Success", f"Category created successfully with ID: {category_id}")
            
            # Reload the categories list
            self.load_categories()
            self.clear_form()
            self.selected_category = None
            
            # Emit signal to update parent window
            self.categories_updated.emit()
            
        except Exception as e:
            self.logger.error(f"Error saving category: {e}")
            QMessageBox.critical(self, "Error", f"Failed to save category: {e}")
    
    def edit_category(self):
        """Edit the selected category."""
        if self.selected_category:
            self.load_category_details(self.selected_category)
    
    def delete_category(self):
        """Delete the selected category."""
        if not self.selected_category:
            return
        
        reply = QMessageBox.question(
            self, "Confirm Delete", 
            f"Are you sure you want to delete category '{self.selected_category.name}'?\n"
            "This will also affect all products in this category.",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                self.inventory_manager.delete_category(self.selected_category.id)
                QMessageBox.information(self, "Success", "Category deleted successfully.")
                
                # Reload the categories list
                self.load_categories()
                self.clear_form()
                self.selected_category = None
                
                # Emit signal to update parent window
                self.categories_updated.emit()
                
            except Exception as e:
                self.logger.error(f"Error deleting category: {e}")
                QMessageBox.critical(self, "Error", f"Failed to delete category: {e}")
    
    def cancel_edit(self):
        """Cancel current edit operation."""
        self.selected_category = None
        self.category_table.clearSelection()
        self.clear_form()
