"""
Stock Management Dialog

Provides comprehensive stock management functionality including:
- Inventory overview and search
- Stock adjustments and corrections
- Stock movement history
- Low stock alerts
- Stock audit functionality
"""

import sys
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Optional, Dict, Any

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget,
    QTableWidget, QTableWidgetItem, QHeaderView, QPushButton,
    QLineEdit, QLabel, QComboBox, QSpinBox, QTextEdit,
    QDateEdit, QGroupBox, QGridLayout, QFormLayout,
    QMessageBox, QProgressBar, QFrame, QSplitter,
    QCheckBox, QDoubleSpinBox
)
from PyQt5.QtCore import Qt, QDate, QTimer, pyqtSignal
from PyQt5.QtGui import QFont, QIcon, QPixmap, QPalette, QColor

from core.inventory import InventoryManager
from core.auth import AuthenticationManager
from models import Product, StockMovement


class StockManagerDialog(QDialog):
    """Stock management dialog with multiple tabs for different functions."""
    
    def __init__(self, inventory_manager: InventoryManager, auth_manager: AuthenticationManager, parent=None):
        super().__init__(parent)
        self.inventory_manager = inventory_manager
        self.auth_manager = auth_manager
        self.current_user = auth_manager.get_current_user()
        
        self.setWindowTitle("Stock Manager - Hardware POS")
        self.setGeometry(100, 100, 1200, 800)
        self.setModal(True)
        
        self.setup_ui()
        self.load_data()
        
        # Auto-refresh timer
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.refresh_current_tab)
        self.refresh_timer.start(30000)  # Refresh every 30 seconds

    def setup_ui(self):
        """Set up the user interface."""
        layout = QVBoxLayout(self)
        
        # Header
        header_frame = self.create_header()
        layout.addWidget(header_frame)
        
        # Main tab widget
        self.tab_widget = QTabWidget()
        
        # Create tabs
        self.inventory_tab = self.create_inventory_tab()
        self.adjustments_tab = self.create_adjustments_tab()
        self.movements_tab = self.create_movements_tab()
        self.alerts_tab = self.create_alerts_tab()
        
        self.tab_widget.addTab(self.inventory_tab, "📦 Inventory Overview")
        self.tab_widget.addTab(self.adjustments_tab, "⚖️ Stock Adjustments")
        self.tab_widget.addTab(self.movements_tab, "📋 Movement History")
        self.tab_widget.addTab(self.alerts_tab, "⚠️ Stock Alerts")
        
        layout.addWidget(self.tab_widget)
        
        # Footer buttons
        footer_layout = QHBoxLayout()
        footer_layout.addStretch()
        
        self.refresh_btn = QPushButton("🔄 Refresh")
        self.refresh_btn.clicked.connect(self.refresh_current_tab)
        footer_layout.addWidget(self.refresh_btn)
        
        self.export_btn = QPushButton("📊 Export Report")
        self.export_btn.clicked.connect(self.export_stock_report)
        footer_layout.addWidget(self.export_btn)
        
        self.close_btn = QPushButton("✖️ Close")
        self.close_btn.clicked.connect(self.close)
        footer_layout.addWidget(self.close_btn)
        
        layout.addLayout(footer_layout)
        
        # Connect tab change event
        self.tab_widget.currentChanged.connect(self.on_tab_changed)

    def create_header(self) -> QFrame:
        """Create header section."""
        header_frame = QFrame()
        header_frame.setFrameStyle(QFrame.StyledPanel)
        header_frame.setStyleSheet("QFrame { background-color: #f0f0f0; border: 1px solid #ccc; }")
        
        layout = QGridLayout(header_frame)
        
        # Title
        title_label = QLabel("Stock Management System")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        layout.addWidget(title_label, 0, 0, 1, 2)
        
        # User info
        user_label = QLabel(f"User: {self.current_user.username if self.current_user else 'Unknown'}")
        layout.addWidget(user_label, 0, 2)
        
        # Last update time
        self.last_update_label = QLabel("Last Updated: Loading...")
        layout.addWidget(self.last_update_label, 1, 0)
        
        # Quick stats
        self.total_products_label = QLabel("Products: -")
        layout.addWidget(self.total_products_label, 1, 1)
        
        self.low_stock_label = QLabel("Low Stock: -")
        self.low_stock_label.setStyleSheet("QLabel { color: red; font-weight: bold; }")
        layout.addWidget(self.low_stock_label, 1, 2)
        
        return header_frame

    def create_inventory_tab(self) -> QWidget:
        """Create inventory overview tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Search and filter section
        search_layout = QHBoxLayout()
        
        self.inventory_search = QLineEdit()
        self.inventory_search.setPlaceholderText("Search products by name, SKU, or barcode...")
        self.inventory_search.textChanged.connect(self.filter_inventory)
        search_layout.addWidget(QLabel("Search:"))
        search_layout.addWidget(self.inventory_search)
        
        self.category_filter = QComboBox()
        self.category_filter.addItem("All Categories", None)
        self.category_filter.currentTextChanged.connect(self.filter_inventory)
        search_layout.addWidget(QLabel("Category:"))
        search_layout.addWidget(self.category_filter)
        
        self.stock_filter = QComboBox()
        self.stock_filter.addItems(["All Products", "In Stock", "Low Stock", "Out of Stock"])
        self.stock_filter.currentTextChanged.connect(self.filter_inventory)
        search_layout.addWidget(QLabel("Stock Status:"))
        search_layout.addWidget(self.stock_filter)
        
        layout.addLayout(search_layout)
        
        # Inventory table
        self.inventory_table = QTableWidget()
        self.inventory_table.setColumnCount(9)
        self.inventory_table.setHorizontalHeaderLabels([
            "SKU", "Product Name", "Category", "Current Stock", 
            "Min Level", "Status", "Cost Price", "Selling Price", "Location"
        ])
        
        # Configure table
        header = self.inventory_table.horizontalHeader()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(QHeaderView.Interactive)
        
        self.inventory_table.setAlternatingRowColors(True)
        self.inventory_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.inventory_table.setSortingEnabled(True)
        
        layout.addWidget(self.inventory_table)
        
        # Quick action buttons
        action_layout = QHBoxLayout()
        
        self.quick_adjust_btn = QPushButton("Quick Adjust")
        self.quick_adjust_btn.clicked.connect(self.quick_stock_adjust)
        action_layout.addWidget(self.quick_adjust_btn)
        
        self.view_movements_btn = QPushButton("View Movements")
        self.view_movements_btn.clicked.connect(self.view_product_movements)
        action_layout.addWidget(self.view_movements_btn)
        
        action_layout.addStretch()
        layout.addLayout(action_layout)
        
        return widget

    def create_adjustments_tab(self) -> QWidget:
        """Create stock adjustments tab."""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        
        # Left panel - Product selection and adjustment form
        left_panel = QGroupBox("Stock Adjustment")
        left_layout = QVBoxLayout(left_panel)
        
        # Product search
        product_search_layout = QHBoxLayout()
        self.adj_product_search = QLineEdit()
        self.adj_product_search.setPlaceholderText("Search product by name, SKU, or barcode...")
        self.adj_product_search.textChanged.connect(self.search_products_for_adjustment)
        
        product_search_layout.addWidget(QLabel("Product:"))
        product_search_layout.addWidget(self.adj_product_search)
        left_layout.addLayout(product_search_layout)
        
        # Product list for selection
        self.adj_product_list = QTableWidget()
        self.adj_product_list.setColumnCount(4)
        self.adj_product_list.setHorizontalHeaderLabels(["SKU", "Name", "Current Stock", "Location"])
        self.adj_product_list.setMaximumHeight(200)
        self.adj_product_list.itemSelectionChanged.connect(self.on_adjustment_product_selected)
        left_layout.addWidget(self.adj_product_list)
        
        # Selected product info
        self.selected_product_frame = QFrame()
        self.selected_product_frame.setFrameStyle(QFrame.StyledPanel)
        selected_layout = QFormLayout(self.selected_product_frame)
        
        self.selected_product_label = QLabel("No product selected")
        self.selected_product_label.setStyleSheet("font-weight: bold;")
        selected_layout.addRow("Selected Product:", self.selected_product_label)
        
        self.current_stock_label = QLabel("-")
        selected_layout.addRow("Current Stock:", self.current_stock_label)
        
        self.min_level_label = QLabel("-")
        selected_layout.addRow("Minimum Level:", self.min_level_label)
        
        left_layout.addWidget(self.selected_product_frame)
        
        # Adjustment form
        adj_form = QGroupBox("Adjustment Details")
        form_layout = QFormLayout(adj_form)
        
        self.adjustment_type = QComboBox()
        self.adjustment_type.addItems(["Set Quantity", "Add Quantity", "Remove Quantity"])
        self.adjustment_type.currentTextChanged.connect(self.on_adjustment_type_changed)
        form_layout.addRow("Adjustment Type:", self.adjustment_type)
        
        self.adjustment_quantity = QSpinBox()
        self.adjustment_quantity.setRange(-9999, 9999)
        self.adjustment_quantity.valueChanged.connect(self.calculate_new_stock)
        form_layout.addRow("Quantity:", self.adjustment_quantity)
        
        self.new_stock_label = QLabel("-")
        self.new_stock_label.setStyleSheet("font-weight: bold; color: blue;")
        form_layout.addRow("New Stock Level:", self.new_stock_label)
        
        self.adjustment_reason = QComboBox()
        self.adjustment_reason.setEditable(True)
        self.adjustment_reason.addItems([
            "Physical count adjustment",
            "Damage/Loss",
            "Found inventory",
            "System correction",
            "Supplier return",
            "Customer return",
            "Transfer between locations"
        ])
        form_layout.addRow("Reason:", self.adjustment_reason)
        
        self.adjustment_notes = QTextEdit()
        self.adjustment_notes.setMaximumHeight(80)
        form_layout.addRow("Notes:", self.adjustment_notes)
        
        left_layout.addWidget(adj_form)
        
        # Adjustment buttons
        adj_btn_layout = QHBoxLayout()
        
        self.preview_adjustment_btn = QPushButton("Preview")
        self.preview_adjustment_btn.clicked.connect(self.preview_adjustment)
        adj_btn_layout.addWidget(self.preview_adjustment_btn)
        
        self.apply_adjustment_btn = QPushButton("Apply Adjustment")
        self.apply_adjustment_btn.clicked.connect(self.apply_stock_adjustment)
        self.apply_adjustment_btn.setStyleSheet("QPushButton { background-color: #4CAF50; color: white; font-weight: bold; }")
        adj_btn_layout.addWidget(self.apply_adjustment_btn)
        
        left_layout.addLayout(adj_btn_layout)
        
        layout.addWidget(left_panel, 1)
        
        # Right panel - Recent adjustments
        right_panel = QGroupBox("Recent Adjustments")
        right_layout = QVBoxLayout(right_panel)
        
        self.recent_adjustments_table = QTableWidget()
        self.recent_adjustments_table.setColumnCount(6)
        self.recent_adjustments_table.setHorizontalHeaderLabels([
            "Date/Time", "Product", "Type", "Quantity", "Reason", "User"
        ])
        
        header = self.recent_adjustments_table.horizontalHeader()
        header.setStretchLastSection(True)
        
        right_layout.addWidget(self.recent_adjustments_table)
        
        layout.addWidget(right_panel, 1)
        
        # Initialize state
        self.selected_product = None
        self.enable_adjustment_controls(False)
        
        return widget

    def create_movements_tab(self) -> QWidget:
        """Create stock movements history tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Filter section
        filter_layout = QHBoxLayout()
        
        self.movement_date_from = QDateEdit()
        self.movement_date_from.setDate(QDate.currentDate().addDays(-30))
        filter_layout.addWidget(QLabel("From:"))
        filter_layout.addWidget(self.movement_date_from)
        
        self.movement_date_to = QDateEdit()
        self.movement_date_to.setDate(QDate.currentDate())
        filter_layout.addWidget(QLabel("To:"))
        filter_layout.addWidget(self.movement_date_to)
        
        self.movement_type_filter = QComboBox()
        self.movement_type_filter.addItems(["All Types", "Stock In", "Stock Out", "Adjustment"])
        filter_layout.addWidget(QLabel("Type:"))
        filter_layout.addWidget(self.movement_type_filter)
        
        self.movement_product_search = QLineEdit()
        self.movement_product_search.setPlaceholderText("Search by product name or SKU...")
        filter_layout.addWidget(QLabel("Product:"))
        filter_layout.addWidget(self.movement_product_search)
        
        self.filter_movements_btn = QPushButton("Filter")
        self.filter_movements_btn.clicked.connect(self.filter_movements)
        filter_layout.addWidget(self.filter_movements_btn)
        
        filter_layout.addStretch()
        layout.addLayout(filter_layout)
        
        # Movements table
        self.movements_table = QTableWidget()
        self.movements_table.setColumnCount(8)
        self.movements_table.setHorizontalHeaderLabels([
            "Date/Time", "Product", "Type", "Quantity", "Reference", "Notes", "User", "Running Stock"
        ])
        
        header = self.movements_table.horizontalHeader()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(QHeaderView.Interactive)
        
        self.movements_table.setAlternatingRowColors(True)
        self.movements_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.movements_table.setSortingEnabled(True)
        
        layout.addWidget(self.movements_table)
        
        return widget

    def create_alerts_tab(self) -> QWidget:
        """Create stock alerts tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Alert summary
        summary_layout = QHBoxLayout()
        
        self.low_stock_count = QLabel("0")
        self.low_stock_count.setStyleSheet("font-size: 24px; font-weight: bold; color: red;")
        
        self.out_of_stock_count = QLabel("0")
        self.out_of_stock_count.setStyleSheet("font-size: 24px; font-weight: bold; color: darkred;")
        
        self.overstock_count = QLabel("0")
        self.overstock_count.setStyleSheet("font-size: 24px; font-weight: bold; color: orange;")
        
        low_box = QGroupBox("Low Stock")
        low_layout = QVBoxLayout(low_box)
        low_layout.addWidget(self.low_stock_count, alignment=Qt.AlignCenter)
        summary_layout.addWidget(low_box)
        
        out_box = QGroupBox("Out of Stock")
        out_layout = QVBoxLayout(out_box)
        out_layout.addWidget(self.out_of_stock_count, alignment=Qt.AlignCenter)
        summary_layout.addWidget(out_box)
        
        over_box = QGroupBox("Overstock (>3x Min)")
        over_layout = QVBoxLayout(over_box)
        over_layout.addWidget(self.overstock_count, alignment=Qt.AlignCenter)
        summary_layout.addWidget(over_box)
        
        layout.addLayout(summary_layout)
        
        # Alert details table
        self.alerts_table = QTableWidget()
        self.alerts_table.setColumnCount(7)
        self.alerts_table.setHorizontalHeaderLabels([
            "Alert Type", "SKU", "Product Name", "Current Stock", 
            "Min Level", "Recommended Action", "Priority"
        ])
        
        header = self.alerts_table.horizontalHeader()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(QHeaderView.Interactive)
        
        self.alerts_table.setAlternatingRowColors(True)
        self.alerts_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.alerts_table.setSortingEnabled(True)
        
        layout.addWidget(self.alerts_table)
        
        # Alert actions
        alert_actions_layout = QHBoxLayout()
        
        self.create_purchase_order_btn = QPushButton("Create Purchase Order")
        self.create_purchase_order_btn.clicked.connect(self.create_purchase_order)
        alert_actions_layout.addWidget(self.create_purchase_order_btn)
        
        self.mark_resolved_btn = QPushButton("Mark as Resolved")
        self.mark_resolved_btn.clicked.connect(self.mark_alert_resolved)
        alert_actions_layout.addWidget(self.mark_resolved_btn)
        
        alert_actions_layout.addStretch()
        layout.addLayout(alert_actions_layout)
        
        return widget

    def load_data(self):
        """Load initial data for all tabs."""
        self.load_categories()
        self.load_inventory()
        self.load_recent_adjustments()
        self.load_stock_alerts()
        self.update_header_stats()

    def load_categories(self):
        """Load categories for filtering."""
        try:
            categories = self.inventory_manager.get_all_categories()
            self.category_filter.clear()
            self.category_filter.addItem("All Categories", None)
            
            for category in categories:
                self.category_filter.addItem(category.name, category.id)
                
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to load categories: {str(e)}")

    def load_inventory(self):
        """Load inventory data."""
        try:
            products = self.inventory_manager.get_all_products()
            self.populate_inventory_table(products)
            
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to load inventory: {str(e)}")

    def populate_inventory_table(self, products: List[Product]):
        """Populate inventory table with products."""
        self.inventory_table.setRowCount(len(products))
        
        for row, product in enumerate(products):
            # SKU
            self.inventory_table.setItem(row, 0, QTableWidgetItem(product.sku))
            
            # Product Name
            self.inventory_table.setItem(row, 1, QTableWidgetItem(product.name))
            
            # Category
            category_name = product.category_name or "No Category"
            self.inventory_table.setItem(row, 2, QTableWidgetItem(category_name))
            
            # Current Stock
            stock_item = QTableWidgetItem(str(product.quantity_in_stock))
            if product.is_low_stock:
                stock_item.setBackground(QColor(255, 200, 200))  # Light red for low stock
            self.inventory_table.setItem(row, 3, stock_item)
            
            # Min Level
            self.inventory_table.setItem(row, 4, QTableWidgetItem(str(product.min_stock_level)))
            
            # Status
            if product.quantity_in_stock == 0:
                status = "Out of Stock"
                status_color = QColor(255, 150, 150)  # Red
            elif product.is_low_stock:
                status = "Low Stock"
                status_color = QColor(255, 220, 150)  # Orange
            elif product.quantity_in_stock > product.min_stock_level * 3:
                status = "Overstock"
                status_color = QColor(200, 200, 255)  # Light blue
            else:
                status = "Normal"
                status_color = QColor(200, 255, 200)  # Light green
            
            status_item = QTableWidgetItem(status)
            status_item.setBackground(status_color)
            self.inventory_table.setItem(row, 5, status_item)
            
            # Cost Price
            self.inventory_table.setItem(row, 6, QTableWidgetItem(f"${product.cost_price:.2f}"))
            
            # Selling Price
            self.inventory_table.setItem(row, 7, QTableWidgetItem(f"${product.selling_price:.2f}"))
            
            # Location
            location = product.location or "Not specified"
            self.inventory_table.setItem(row, 8, QTableWidgetItem(location))

    def filter_inventory(self):
        """Filter inventory based on search criteria."""
        search_text = self.inventory_search.text().lower()
        category_id = self.category_filter.currentData()
        stock_status = self.stock_filter.currentText()
        
        try:
            # Get filtered products
            if search_text:
                products = self.inventory_manager.search_products(search_text, category_id)
            else:
                products = self.inventory_manager.get_all_products()
                if category_id:
                    products = [p for p in products if p.category_id == category_id]
            
            # Apply stock status filter
            if stock_status == "In Stock":
                products = [p for p in products if p.quantity_in_stock > 0]
            elif stock_status == "Low Stock":
                products = [p for p in products if p.is_low_stock and p.quantity_in_stock > 0]
            elif stock_status == "Out of Stock":
                products = [p for p in products if p.quantity_in_stock == 0]
            
            self.populate_inventory_table(products)
            
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to filter inventory: {str(e)}")

    def search_products_for_adjustment(self):
        """Search products for adjustment tab."""
        search_text = self.adj_product_search.text()
        
        if len(search_text) < 2:
            self.adj_product_list.setRowCount(0)
            return
        
        try:
            products = self.inventory_manager.search_products(search_text)
            self.populate_adjustment_product_list(products[:20])  # Limit to 20 results
            
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to search products: {str(e)}")

    def populate_adjustment_product_list(self, products: List[Product]):
        """Populate product list for adjustment selection."""
        self.adj_product_list.setRowCount(len(products))
        
        for row, product in enumerate(products):
            self.adj_product_list.setItem(row, 0, QTableWidgetItem(product.sku))
            self.adj_product_list.setItem(row, 1, QTableWidgetItem(product.name))
            self.adj_product_list.setItem(row, 2, QTableWidgetItem(str(product.quantity_in_stock)))
            
            location = product.location or "Not specified"
            self.adj_product_list.setItem(row, 3, QTableWidgetItem(location))
            
            # Store product data
            self.adj_product_list.item(row, 0).setData(Qt.UserRole, product)

    def on_adjustment_product_selected(self):
        """Handle product selection in adjustment tab."""
        current_row = self.adj_product_list.currentRow()
        if current_row >= 0:
            product_item = self.adj_product_list.item(current_row, 0)
            if product_item:
                self.selected_product = product_item.data(Qt.UserRole)
                self.update_selected_product_info()
                self.enable_adjustment_controls(True)
        else:
            self.selected_product = None
            self.enable_adjustment_controls(False)

    def update_selected_product_info(self):
        """Update selected product information display."""
        if self.selected_product:
            self.selected_product_label.setText(f"{self.selected_product.name} ({self.selected_product.sku})")
            self.current_stock_label.setText(str(self.selected_product.quantity_in_stock))
            self.min_level_label.setText(str(self.selected_product.min_stock_level))
            self.calculate_new_stock()
        else:
            self.selected_product_label.setText("No product selected")
            self.current_stock_label.setText("-")
            self.min_level_label.setText("-")
            self.new_stock_label.setText("-")

    def enable_adjustment_controls(self, enabled: bool):
        """Enable or disable adjustment controls."""
        self.adjustment_type.setEnabled(enabled)
        self.adjustment_quantity.setEnabled(enabled)
        self.adjustment_reason.setEnabled(enabled)
        self.adjustment_notes.setEnabled(enabled)
        self.preview_adjustment_btn.setEnabled(enabled)
        self.apply_adjustment_btn.setEnabled(enabled)

    def on_adjustment_type_changed(self):
        """Handle adjustment type change."""
        adj_type = self.adjustment_type.currentText()
        
        if adj_type == "Set Quantity":
            self.adjustment_quantity.setMinimum(0)
            self.adjustment_quantity.setValue(self.selected_product.quantity_in_stock if self.selected_product else 0)
        elif adj_type == "Add Quantity":
            self.adjustment_quantity.setMinimum(1)
            self.adjustment_quantity.setValue(1)
        else:  # Remove Quantity
            max_remove = self.selected_product.quantity_in_stock if self.selected_product else 0
            self.adjustment_quantity.setMinimum(1)
            self.adjustment_quantity.setMaximum(max_remove)
            self.adjustment_quantity.setValue(min(1, max_remove))
        
        self.calculate_new_stock()

    def calculate_new_stock(self):
        """Calculate and display new stock level."""
        if not self.selected_product:
            self.new_stock_label.setText("-")
            return
        
        current_stock = self.selected_product.quantity_in_stock
        adj_type = self.adjustment_type.currentText()
        quantity = self.adjustment_quantity.value()
        
        if adj_type == "Set Quantity":
            new_stock = quantity
        elif adj_type == "Add Quantity":
            new_stock = current_stock + quantity
        else:  # Remove Quantity
            new_stock = current_stock - quantity
        
        self.new_stock_label.setText(str(new_stock))
        
        # Color coding
        if new_stock < 0:
            self.new_stock_label.setStyleSheet("font-weight: bold; color: red;")
        elif new_stock <= self.selected_product.min_stock_level:
            self.new_stock_label.setStyleSheet("font-weight: bold; color: orange;")
        else:
            self.new_stock_label.setStyleSheet("font-weight: bold; color: blue;")

    def preview_adjustment(self):
        """Preview the stock adjustment."""
        if not self.selected_product:
            return
        
        current_stock = self.selected_product.quantity_in_stock
        adj_type = self.adjustment_type.currentText()
        quantity = self.adjustment_quantity.value()
        reason = self.adjustment_reason.currentText()
        
        if adj_type == "Set Quantity":
            new_stock = quantity
            change = new_stock - current_stock
        elif adj_type == "Add Quantity":
            new_stock = current_stock + quantity
            change = quantity
        else:  # Remove Quantity
            new_stock = current_stock - quantity
            change = -quantity
        
        message = f"""
Stock Adjustment Preview

Product: {self.selected_product.name} ({self.selected_product.sku})
Current Stock: {current_stock}
Adjustment: {'+' if change >= 0 else ''}{change}
New Stock: {new_stock}
Reason: {reason}

Do you want to proceed with this adjustment?
        """
        
        reply = QMessageBox.question(self, "Confirm Adjustment", message.strip(),
                                   QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            self.apply_stock_adjustment()

    def apply_stock_adjustment(self):
        """Apply the stock adjustment."""
        if not self.selected_product:
            QMessageBox.warning(self, "Error", "No product selected.")
            return
        
        try:
            adj_type = self.adjustment_type.currentText()
            quantity = self.adjustment_quantity.value()
            reason = self.adjustment_reason.currentText()
            notes = self.adjustment_notes.toPlainText()
            
            current_stock = self.selected_product.quantity_in_stock
            
            if adj_type == "Set Quantity":
                new_stock = quantity
                success = self.inventory_manager.adjust_stock(
                    self.selected_product.id, new_stock, 
                    f"{reason}: {notes}", self.current_user.id if self.current_user else None
                )
            else:
                if adj_type == "Add Quantity":
                    change = quantity
                else:  # Remove Quantity
                    change = -quantity
                
                success = self.inventory_manager.update_stock(
                    self.selected_product.id, change, 'adjustment',
                    reference_type='manual_adjustment',
                    notes=f"{reason}: {notes}",
                    user_id=self.current_user.id if self.current_user else None
                )
            
            if success:
                QMessageBox.information(self, "Success", "Stock adjustment applied successfully.")
                
                # Refresh data
                self.load_inventory()
                self.load_recent_adjustments()
                self.load_stock_alerts()
                self.update_header_stats()
                
                # Clear adjustment form
                self.adj_product_search.clear()
                self.adj_product_list.setRowCount(0)
                self.selected_product = None
                self.enable_adjustment_controls(False)
                self.update_selected_product_info()
                self.adjustment_quantity.setValue(0)
                self.adjustment_notes.clear()
                
            else:
                QMessageBox.warning(self, "Error", "Failed to apply stock adjustment.")
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error applying adjustment: {str(e)}")

    def load_recent_adjustments(self):
        """Load recent stock adjustments."""
        try:
            # Get stock movements for adjustments in the last 7 days
            movements = self.inventory_manager.get_stock_movements(days=7)
            adjustment_movements = [m for m in movements if m.movement_type == 'adjustment']
            
            self.recent_adjustments_table.setRowCount(len(adjustment_movements))
            
            for row, movement in enumerate(adjustment_movements):
                # Date/Time
                date_str = movement.created_at.strftime("%Y-%m-%d %H:%M")
                self.recent_adjustments_table.setItem(row, 0, QTableWidgetItem(date_str))
                
                # Product
                self.recent_adjustments_table.setItem(row, 1, QTableWidgetItem(movement.product_name))
                
                # Type
                adj_type = "Set" if movement.reference_type == 'adjustment' else "Manual"
                self.recent_adjustments_table.setItem(row, 2, QTableWidgetItem(adj_type))
                
                # Quantity
                qty_text = f"{'+' if movement.quantity >= 0 else ''}{movement.quantity}"
                qty_item = QTableWidgetItem(qty_text)
                if movement.quantity < 0:
                    qty_item.setBackground(QColor(255, 200, 200))  # Light red
                else:
                    qty_item.setBackground(QColor(200, 255, 200))  # Light green
                self.recent_adjustments_table.setItem(row, 3, qty_item)
                
                # Reason
                notes = movement.notes or "No reason specified"
                self.recent_adjustments_table.setItem(row, 4, QTableWidgetItem(notes))
                
                # User
                user_name = "System" if not movement.user_id else f"User {movement.user_id}"
                self.recent_adjustments_table.setItem(row, 5, QTableWidgetItem(user_name))
            
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to load recent adjustments: {str(e)}")

    def filter_movements(self):
        """Filter stock movements based on criteria."""
        try:
            # Get date range
            from_date = self.movement_date_from.date().toPyDate()
            to_date = self.movement_date_to.date().toPyDate()
            days_diff = (to_date - from_date).days + 1
            
            # Get movements
            movements = self.inventory_manager.get_stock_movements(days=days_diff)
            
            # Apply filters
            type_filter = self.movement_type_filter.currentText()
            if type_filter != "All Types":
                type_map = {
                    "Stock In": "in",
                    "Stock Out": "out", 
                    "Adjustment": "adjustment"
                }
                movements = [m for m in movements if m.movement_type == type_map[type_filter]]
            
            # Product search filter
            product_search = self.movement_product_search.text().lower()
            if product_search:
                movements = [m for m in movements if product_search in m.product_name.lower()]
            
            self.populate_movements_table(movements)
            
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to filter movements: {str(e)}")

    def populate_movements_table(self, movements: List[StockMovement]):
        """Populate movements table."""
        self.movements_table.setRowCount(len(movements))
        
        for row, movement in enumerate(movements):
            # Date/Time
            date_str = movement.created_at.strftime("%Y-%m-%d %H:%M:%S")
            self.movements_table.setItem(row, 0, QTableWidgetItem(date_str))
            
            # Product
            self.movements_table.setItem(row, 1, QTableWidgetItem(movement.product_name))
            
            # Type
            type_map = {"in": "Stock In", "out": "Stock Out", "adjustment": "Adjustment"}
            movement_type = type_map.get(movement.movement_type, movement.movement_type)
            self.movements_table.setItem(row, 2, QTableWidgetItem(movement_type))
            
            # Quantity
            qty_text = f"{'+' if movement.quantity >= 0 else ''}{movement.quantity}"
            qty_item = QTableWidgetItem(qty_text)
            if movement.quantity < 0:
                qty_item.setBackground(QColor(255, 200, 200))  # Light red
            else:
                qty_item.setBackground(QColor(200, 255, 200))  # Light green
            self.movements_table.setItem(row, 3, qty_item)
            
            # Reference
            ref_text = ""
            if movement.reference_type and movement.reference_id:
                ref_text = f"{movement.reference_type} #{movement.reference_id}"
            elif movement.reference_type:
                ref_text = movement.reference_type
            self.movements_table.setItem(row, 4, QTableWidgetItem(ref_text))
            
            # Notes
            notes = movement.notes or ""
            self.movements_table.setItem(row, 5, QTableWidgetItem(notes))
            
            # User
            user_name = "System" if not movement.user_id else f"User {movement.user_id}"
            self.movements_table.setItem(row, 6, QTableWidgetItem(user_name))
            
            # Running Stock (placeholder - would need to calculate)
            self.movements_table.setItem(row, 7, QTableWidgetItem("-"))

    def load_stock_alerts(self):
        """Load stock alerts."""
        try:
            products = self.inventory_manager.get_all_products()
            
            low_stock_products = []
            out_of_stock_products = []
            overstock_products = []
            
            for product in products:
                if product.quantity_in_stock == 0:
                    out_of_stock_products.append(product)
                elif product.is_low_stock:
                    low_stock_products.append(product)
                elif product.quantity_in_stock > product.min_stock_level * 3 and product.min_stock_level > 0:
                    overstock_products.append(product)
            
            # Update counts
            self.low_stock_count.setText(str(len(low_stock_products)))
            self.out_of_stock_count.setText(str(len(out_of_stock_products)))
            self.overstock_count.setText(str(len(overstock_products)))
            
            # Populate alerts table
            all_alerts = []
            
            for product in out_of_stock_products:
                all_alerts.append({
                    'type': 'Out of Stock',
                    'product': product,
                    'priority': 'Critical',
                    'action': 'Immediate reorder required'
                })
            
            for product in low_stock_products:
                all_alerts.append({
                    'type': 'Low Stock',
                    'product': product,
                    'priority': 'High',
                    'action': 'Reorder soon'
                })
            
            for product in overstock_products:
                all_alerts.append({
                    'type': 'Overstock',
                    'product': product,
                    'priority': 'Low',
                    'action': 'Consider promotion or return'
                })
            
            self.populate_alerts_table(all_alerts)
            
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to load stock alerts: {str(e)}")

    def populate_alerts_table(self, alerts: List[Dict[str, Any]]):
        """Populate alerts table."""
        self.alerts_table.setRowCount(len(alerts))
        
        for row, alert in enumerate(alerts):
            product = alert['product']
            
            # Alert Type
            alert_item = QTableWidgetItem(alert['type'])
            if alert['priority'] == 'Critical':
                alert_item.setBackground(QColor(255, 150, 150))  # Red
            elif alert['priority'] == 'High':
                alert_item.setBackground(QColor(255, 220, 150))  # Orange
            else:
                alert_item.setBackground(QColor(200, 200, 255))  # Light blue
            self.alerts_table.setItem(row, 0, alert_item)
            
            # SKU
            self.alerts_table.setItem(row, 1, QTableWidgetItem(product.sku))
            
            # Product Name
            self.alerts_table.setItem(row, 2, QTableWidgetItem(product.name))
            
            # Current Stock
            self.alerts_table.setItem(row, 3, QTableWidgetItem(str(product.quantity_in_stock)))
            
            # Min Level
            self.alerts_table.setItem(row, 4, QTableWidgetItem(str(product.min_stock_level)))
            
            # Recommended Action
            self.alerts_table.setItem(row, 5, QTableWidgetItem(alert['action']))
            
            # Priority
            priority_item = QTableWidgetItem(alert['priority'])
            priority_item.setBackground(alert_item.background())
            self.alerts_table.setItem(row, 6, priority_item)

    def update_header_stats(self):
        """Update header statistics."""
        try:
            products = self.inventory_manager.get_all_products()
            low_stock_products = self.inventory_manager.get_low_stock_products()
            
            self.total_products_label.setText(f"Products: {len(products)}")
            self.low_stock_label.setText(f"Low Stock: {len(low_stock_products)}")
            self.last_update_label.setText(f"Last Updated: {datetime.now().strftime('%H:%M:%S')}")
            
        except Exception as e:
            self.last_update_label.setText("Last Updated: Error")

    def on_tab_changed(self, index):
        """Handle tab change event."""
        tab_names = ["Inventory", "Adjustments", "Movements", "Alerts"]
        if index < len(tab_names):
            tab_name = tab_names[index]
            if tab_name == "Movements":
                self.filter_movements()  # Auto-load movements when tab is opened

    def refresh_current_tab(self):
        """Refresh current tab data."""
        current_index = self.tab_widget.currentIndex()
        
        if current_index == 0:  # Inventory
            self.load_inventory()
            self.update_header_stats()
        elif current_index == 1:  # Adjustments
            self.load_recent_adjustments()
        elif current_index == 2:  # Movements
            self.filter_movements()
        elif current_index == 3:  # Alerts
            self.load_stock_alerts()

    def quick_stock_adjust(self):
        """Quick stock adjustment from inventory tab."""
        current_row = self.inventory_table.currentRow()
        if current_row < 0:
            QMessageBox.information(self, "Info", "Please select a product from the inventory table.")
            return
        
        # Switch to adjustments tab and pre-fill product
        sku_item = self.inventory_table.item(current_row, 0)
        product_name_item = self.inventory_table.item(current_row, 1)
        
        if sku_item and product_name_item:
            self.tab_widget.setCurrentIndex(1)  # Switch to adjustments tab
            self.adj_product_search.setText(sku_item.text())
            self.search_products_for_adjustment()

    def view_product_movements(self):
        """View movements for selected product."""
        current_row = self.inventory_table.currentRow()
        if current_row < 0:
            QMessageBox.information(self, "Info", "Please select a product from the inventory table.")
            return
        
        # Switch to movements tab and filter by product
        product_name_item = self.inventory_table.item(current_row, 1)
        
        if product_name_item:
            self.tab_widget.setCurrentIndex(2)  # Switch to movements tab
            self.movement_product_search.setText(product_name_item.text())
            self.filter_movements()

    def create_purchase_order(self):
        """Create purchase order for selected low stock items."""
        selected_rows = set()
        for item in self.alerts_table.selectedItems():
            selected_rows.add(item.row())
        
        if not selected_rows:
            QMessageBox.information(self, "Info", "Please select items to create a purchase order.")
            return
        
        # For now, just show a message
        QMessageBox.information(self, "Purchase Order", 
                              f"Purchase order creation feature would generate an order for {len(selected_rows)} selected items.")

    def mark_alert_resolved(self):
        """Mark selected alerts as resolved."""
        selected_rows = set()
        for item in self.alerts_table.selectedItems():
            selected_rows.add(item.row())
        
        if not selected_rows:
            QMessageBox.information(self, "Info", "Please select alerts to mark as resolved.")
            return
        
        # For now, just refresh the alerts
        self.load_stock_alerts()
        QMessageBox.information(self, "Info", f"{len(selected_rows)} alerts marked as resolved.")

    def export_stock_report(self):
        """Export stock report."""
        current_index = self.tab_widget.currentIndex()
        tab_names = ["Inventory", "Adjustments", "Movements", "Alerts"]
        
        if current_index < len(tab_names):
            tab_name = tab_names[current_index]
            QMessageBox.information(self, "Export", 
                                  f"Export functionality for {tab_name} report would be implemented here.")

    def closeEvent(self, event):
        """Handle dialog close event."""
        self.refresh_timer.stop()
        event.accept()


if __name__ == "__main__":
    # This would be used for testing the dialog standalone
    pass
