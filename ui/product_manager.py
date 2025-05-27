"""
Product Management Dialog for Hardware POS System.
"""

from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, 
                           QTableWidgetItem, QPushButton, QLineEdit, QLabel, 
                           QComboBox, QSpinBox, QDoubleSpinBox, QTextEdit,
                           QGroupBox, QFormLayout, QMessageBox, QHeaderView,
                           QAbstractItemView, QSplitter, QFrame)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont

from core.database import DatabaseManager
from core.inventory import InventoryManager
from models.product import Product, Category, Supplier
from utils.logger import get_logger
from typing import Optional, List


class ProductManagerDialog(QDialog):
    """Dialog for managing products, categories, and suppliers."""
    
    product_updated = pyqtSignal()
    
    def __init__(self, db_manager: DatabaseManager, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.inventory_manager = InventoryManager(db_manager)
        self.logger = get_logger(__name__)
        
        self.current_product: Optional[Product] = None
        self.products: List[Product] = []
        self.categories: List[Category] = []
        self.suppliers: List[Supplier] = []
        
        self.setup_ui()
        self.setup_connections()
        self.load_data()
    
    def setup_ui(self):
        """Setup the user interface."""
        self.setWindowTitle("Product Management")
        self.setGeometry(100, 100, 1200, 800)
        
        # Main layout
        main_layout = QHBoxLayout(self)
        
        # Create splitter
        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)
        
        # Left panel - Product list
        left_panel = self.create_product_list_panel()
        splitter.addWidget(left_panel)
        
        # Right panel - Product details
        right_panel = self.create_product_details_panel()
        splitter.addWidget(right_panel)
        
        # Set splitter proportions
        splitter.setSizes([600, 600])
    
    def create_product_list_panel(self) -> QFrame:
        """Create the product list panel."""
        frame = QFrame()
        layout = QVBoxLayout(frame)
        
        # Search and filter section
        search_group = QGroupBox("Search & Filter")
        search_layout = QVBoxLayout(search_group)
        
        # Search input
        search_row = QHBoxLayout()
        search_row.addWidget(QLabel("Search:"))
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search by name, SKU, or barcode...")
        self.search_button = QPushButton("Search")
        search_row.addWidget(self.search_input)
        search_row.addWidget(self.search_button)
        search_layout.addLayout(search_row)
        
        # Category filter
        filter_row = QHBoxLayout()
        filter_row.addWidget(QLabel("Category:"))
        self.category_filter = QComboBox()
        self.category_filter.addItem("All Categories", None)
        filter_row.addWidget(self.category_filter)
        
        # Status filter
        filter_row.addWidget(QLabel("Status:"))
        self.status_filter = QComboBox()
        self.status_filter.addItems(["All", "Active", "Inactive"])
        filter_row.addWidget(self.status_filter)
        
        search_layout.addLayout(filter_row)
        layout.addWidget(search_group)
        
        # Products table
        products_group = QGroupBox("Products")
        products_layout = QVBoxLayout(products_group)
        
        self.products_table = QTableWidget()
        self.products_table.setColumnCount(6)
        self.products_table.setHorizontalHeaderLabels([
            "SKU", "Name", "Category", "Price", "Stock", "Status"
        ])
        
        # Configure table
        header = self.products_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch)
        self.products_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.products_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.products_table.setAlternatingRowColors(True)
        
        products_layout.addWidget(self.products_table)
        
        # Action buttons
        button_row = QHBoxLayout()
        self.new_product_button = QPushButton("New Product")
        self.edit_product_button = QPushButton("Edit Product")
        self.delete_product_button = QPushButton("Delete Product")
        self.refresh_button = QPushButton("Refresh")
        
        button_row.addWidget(self.new_product_button)
        button_row.addWidget(self.edit_product_button)
        button_row.addWidget(self.delete_product_button)
        button_row.addStretch()
        button_row.addWidget(self.refresh_button)
        
        products_layout.addLayout(button_row)
        layout.addWidget(products_group)
        
        return frame
    
    def create_product_details_panel(self) -> QFrame:
        """Create the product details panel."""
        frame = QFrame()
        layout = QVBoxLayout(frame)
        
        # Product details form
        details_group = QGroupBox("Product Details")
        form_layout = QFormLayout(details_group)
        
        # Basic information
        self.sku_input = QLineEdit()
        self.name_input = QLineEdit()
        self.barcode_input = QLineEdit()
        self.description_input = QTextEdit()
        self.description_input.setMaximumHeight(80)
        
        form_layout.addRow("SKU:", self.sku_input)
        form_layout.addRow("Name:", self.name_input)
        form_layout.addRow("Barcode:", self.barcode_input)
        form_layout.addRow("Description:", self.description_input)
        
        # Category and supplier
        self.category_combo = QComboBox()
        self.supplier_combo = QComboBox()
        
        form_layout.addRow("Category:", self.category_combo)
        form_layout.addRow("Supplier:", self.supplier_combo)
        
        # Pricing
        self.cost_price_input = QDoubleSpinBox()
        self.cost_price_input.setRange(0, 99999.99)
        self.cost_price_input.setDecimals(2)
        self.cost_price_input.setPrefix("$")
        
        self.selling_price_input = QDoubleSpinBox()
        self.selling_price_input.setRange(0, 99999.99)
        self.selling_price_input.setDecimals(2)
        self.selling_price_input.setPrefix("$")
        
        form_layout.addRow("Cost Price:", self.cost_price_input)
        form_layout.addRow("Selling Price:", self.selling_price_input)
        
        # Stock
        self.stock_quantity_input = QSpinBox()
        self.stock_quantity_input.setRange(0, 999999)
        self.min_stock_input = QSpinBox()
        self.min_stock_input.setRange(0, 999999)
        
        form_layout.addRow("Stock Quantity:", self.stock_quantity_input)
        form_layout.addRow("Minimum Stock:", self.min_stock_input)
        
        # Status
        self.active_combo = QComboBox()
        self.active_combo.addItems(["Active", "Inactive"])
        form_layout.addRow("Status:", self.active_combo)
        
        layout.addWidget(details_group)
        
        # Action buttons
        button_group = QGroupBox("Actions")
        button_layout = QHBoxLayout(button_group)
        
        self.save_button = QPushButton("Save Product")
        self.cancel_button = QPushButton("Cancel")
        self.clear_button = QPushButton("Clear Form")
        
        self.save_button.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
        self.cancel_button.setStyleSheet("background-color: #f44336; color: white;")
        
        button_layout.addWidget(self.save_button)
        button_layout.addWidget(self.cancel_button)
        button_layout.addWidget(self.clear_button)
        button_layout.addStretch()
        
        layout.addWidget(button_group)
        
        # Quick actions
        quick_group = QGroupBox("Quick Actions")
        quick_layout = QVBoxLayout(quick_group)
        
        self.manage_categories_button = QPushButton("Manage Categories")
        self.manage_suppliers_button = QPushButton("Manage Suppliers")
        self.import_products_button = QPushButton("Import Products")
        self.export_products_button = QPushButton("Export Products")
        
        quick_layout.addWidget(self.manage_categories_button)
        quick_layout.addWidget(self.manage_suppliers_button)
        quick_layout.addWidget(self.import_products_button)
        quick_layout.addWidget(self.export_products_button)
        
        layout.addWidget(quick_group)
        layout.addStretch()
        
        return frame
    
    def setup_connections(self):
        """Setup signal connections."""
        # Search and filter
        self.search_button.clicked.connect(self.search_products)
        self.search_input.returnPressed.connect(self.search_products)
        self.category_filter.currentTextChanged.connect(self.filter_products)
        self.status_filter.currentTextChanged.connect(self.filter_products)
        
        # Table selection
        self.products_table.itemSelectionChanged.connect(self.on_product_selected)
        
        # Product actions
        self.new_product_button.clicked.connect(self.new_product)
        self.edit_product_button.clicked.connect(self.edit_product)
        self.delete_product_button.clicked.connect(self.delete_product)
        self.refresh_button.clicked.connect(self.load_data)
        
        # Form actions
        self.save_button.clicked.connect(self.save_product)
        self.cancel_button.clicked.connect(self.cancel_edit)
        self.clear_button.clicked.connect(self.clear_form)
        
        # Quick actions
        self.manage_categories_button.clicked.connect(self.manage_categories)
        self.manage_suppliers_button.clicked.connect(self.manage_suppliers)
        self.import_products_button.clicked.connect(self.import_products)
        self.export_products_button.clicked.connect(self.export_products)
    
    def load_data(self):
        """Load all data."""
        try:
            self.load_categories()
            self.load_suppliers()
            self.load_products()
        except Exception as e:
            self.logger.error(f"Error loading data: {e}")
            QMessageBox.critical(self, "Error", f"Failed to load data: {e}")
    
    def load_categories(self):
        """Load categories."""
        try:
            self.categories = self.inventory_manager.get_all_categories()
            
            # Update category filter
            self.category_filter.clear()
            self.category_filter.addItem("All Categories", None)
            
            # Update category combo
            self.category_combo.clear()
            self.category_combo.addItem("Select Category", None)
            
            for category in self.categories:
                self.category_filter.addItem(category.name, category.id)
                self.category_combo.addItem(category.name, category.id)
                
        except Exception as e:
            self.logger.error(f"Error loading categories: {e}")
    
    def load_suppliers(self):
        """Load suppliers."""
        try:
            self.suppliers = self.inventory_manager.get_all_suppliers()
            
            self.supplier_combo.clear()
            self.supplier_combo.addItem("Select Supplier", None)
            
            for supplier in self.suppliers:
                self.supplier_combo.addItem(supplier.name, supplier.id)
                
        except Exception as e:
            self.logger.error(f"Error loading suppliers: {e}")
    
    def load_products(self):
        """Load products into the table."""
        try:
            self.products = self.inventory_manager.get_all_products()
            self.update_products_table()
            
        except Exception as e:
            self.logger.error(f"Error loading products: {e}")
            QMessageBox.critical(self, "Error", f"Failed to load products: {e}")
    
    def update_products_table(self):
        """Update the products table."""
        self.products_table.setRowCount(len(self.products))
        
        for row, product in enumerate(self.products):
            # Get category name
            category_name = "N/A"
            if product.category_id:
                category = next((c for c in self.categories if c.id == product.category_id), None)
                if category:
                    category_name = category.name
            
            # Set table items
            self.products_table.setItem(row, 0, QTableWidgetItem(product.sku))
            self.products_table.setItem(row, 1, QTableWidgetItem(product.name))
            self.products_table.setItem(row, 2, QTableWidgetItem(category_name))
            self.products_table.setItem(row, 3, QTableWidgetItem(f"${product.selling_price:.2f}"))
            self.products_table.setItem(row, 4, QTableWidgetItem(str(product.stock_quantity)))
            self.products_table.setItem(row, 5, QTableWidgetItem("Active" if product.is_active else "Inactive"))
            
            # Store product ID in first column
            self.products_table.item(row, 0).setData(Qt.UserRole, product.id)
    
    def search_products(self):
        """Search products."""
        search_term = self.search_input.text().strip()
        category_id = self.category_filter.currentData()
        status = self.status_filter.currentText()
        
        try:
            if search_term:
                self.products = self.inventory_manager.search_products(
                    search_term, category_id=category_id
                )
            else:
                self.products = self.inventory_manager.get_all_products()
            
            # Filter by status
            if status == "Active":
                self.products = [p for p in self.products if p.is_active]
            elif status == "Inactive":
                self.products = [p for p in self.products if not p.is_active]
            
            self.update_products_table()
            
        except Exception as e:
            self.logger.error(f"Error searching products: {e}")
            QMessageBox.critical(self, "Error", f"Search failed: {e}")
    
    def filter_products(self):
        """Filter products by category and status."""
        self.search_products()
    
    def on_product_selected(self):
        """Handle product selection."""
        selected_rows = self.products_table.selectionModel().selectedRows()
        if not selected_rows:
            self.current_product = None
            self.clear_form()
            return
        
        row = selected_rows[0].row()
        product_id = self.products_table.item(row, 0).data(Qt.UserRole)
        
        # Find the product
        self.current_product = next((p for p in self.products if p.id == product_id), None)
        if self.current_product:
            self.populate_form(self.current_product)
    
    def populate_form(self, product: Product):
        """Populate the form with product data."""
        self.sku_input.setText(product.sku)
        self.name_input.setText(product.name)
        self.barcode_input.setText(product.barcode or "")
        self.description_input.setText(product.description or "")
        
        # Set category
        if product.category_id:
            index = self.category_combo.findData(product.category_id)
            if index >= 0:
                self.category_combo.setCurrentIndex(index)
        
        # Set supplier
        if product.supplier_id:
            index = self.supplier_combo.findData(product.supplier_id)
            if index >= 0:
                self.supplier_combo.setCurrentIndex(index)
        
        self.cost_price_input.setValue(product.cost_price)
        self.selling_price_input.setValue(product.selling_price)
        self.stock_quantity_input.setValue(product.stock_quantity)
        self.min_stock_input.setValue(product.min_stock_level)
        
        self.active_combo.setCurrentText("Active" if product.is_active else "Inactive")
    
    def clear_form(self):
        """Clear the form."""
        self.sku_input.clear()
        self.name_input.clear()
        self.barcode_input.clear()
        self.description_input.clear()
        self.category_combo.setCurrentIndex(0)
        self.supplier_combo.setCurrentIndex(0)
        self.cost_price_input.setValue(0.0)
        self.selling_price_input.setValue(0.0)
        self.stock_quantity_input.setValue(0)
        self.min_stock_input.setValue(0)
        self.active_combo.setCurrentIndex(0)
        
        self.current_product = None
    
    def new_product(self):
        """Create a new product."""
        self.clear_form()
        self.products_table.clearSelection()
    
    def edit_product(self):
        """Edit the selected product."""
        if not self.current_product:
            QMessageBox.warning(self, "No Selection", "Please select a product to edit.")
            return
    
    def delete_product(self):
        """Delete the selected product."""
        if not self.current_product:
            QMessageBox.warning(self, "No Selection", "Please select a product to delete.")
            return
        
        reply = QMessageBox.question(
            self, "Delete Product",
            f"Are you sure you want to delete '{self.current_product.name}'?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                self.inventory_manager.delete_product(self.current_product.id)
                self.load_products()
                self.clear_form()
                QMessageBox.information(self, "Success", "Product deleted successfully!")
                self.product_updated.emit()
                
            except Exception as e:
                self.logger.error(f"Error deleting product: {e}")
                QMessageBox.critical(self, "Error", f"Failed to delete product: {e}")
    
    def save_product(self):
        """Save the product."""
        # Validate form
        if not self.name_input.text().strip():
            QMessageBox.warning(self, "Validation Error", "Product name is required.")
            return
        
        if not self.sku_input.text().strip():
            QMessageBox.warning(self, "Validation Error", "SKU is required.")
            return
        
        try:
            # Create product data
            product_data = {
                'sku': self.sku_input.text().strip(),
                'name': self.name_input.text().strip(),
                'barcode': self.barcode_input.text().strip() or None,
                'description': self.description_input.toPlainText().strip() or None,
                'category_id': self.category_combo.currentData(),
                'supplier_id': self.supplier_combo.currentData(),
                'cost_price': self.cost_price_input.value(),
                'selling_price': self.selling_price_input.value(),
                'stock_quantity': self.stock_quantity_input.value(),
                'min_stock_level': self.min_stock_input.value(),
                'is_active': self.active_combo.currentText() == "Active"            }
            
            if self.current_product:
                # Update existing product
                self.inventory_manager.update_product_dict(self.current_product.id, product_data)
                message = "Product updated successfully!"
            else:
                # Create new product
                self.inventory_manager.add_product(product_data)
                message = "Product created successfully!"
            
            self.load_products()
            QMessageBox.information(self, "Success", message)
            self.product_updated.emit()
            
        except Exception as e:
            self.logger.error(f"Error saving product: {e}")
            QMessageBox.critical(self, "Error", f"Failed to save product: {e}")
    
    def cancel_edit(self):
        """Cancel editing."""
        if self.current_product:
            self.populate_form(self.current_product)
        else:
            self.clear_form()
    
    def manage_categories(self):
        """Open category management dialog."""
        QMessageBox.information(self, "Feature", "Category management will be implemented.")
    
    def manage_suppliers(self):
        """Open supplier management dialog."""
        QMessageBox.information(self, "Feature", "Supplier management will be implemented.")
    
    def import_products(self):
        """Import products from file."""
        QMessageBox.information(self, "Feature", "Product import will be implemented.")
    
    def export_products(self):
        """Export products to file."""
        QMessageBox.information(self, "Feature", "Product export will be implemented.")
