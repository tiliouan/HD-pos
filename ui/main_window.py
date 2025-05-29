"""
Main POS Interface

The main window for the Hardware POS system with sales interface, product grid, and navigation.
"""

import logging
from decimal import Decimal
from typing import Optional, List
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QLineEdit, QPushButton, QTableWidget, QTableWidgetItem,
    QGroupBox, QSpinBox, QComboBox, QTextEdit, QMenuBar, QStatusBar,
    QAction, QSplitter, QFrame, QMessageBox, QDialog, QHeaderView,
    QScrollArea, QButtonGroup, QCheckBox
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QThread, pyqtSlot
from PyQt5.QtGui import QFont, QPixmap, QIcon, QPalette, QColor

from core.database import DatabaseManager
from core.auth import AuthenticationManager
from core.inventory import InventoryManager
from core.sales import SalesManager
from core.clients import ClientManager
from models import User, Product, Sale, SaleItem, Client
from config.settings import settings
from utils.logger import get_logger
from ui.product_manager import ProductManagerDialog
from ui.client_manager import ClientManagerDialog
from ui.category_manager import CategoryManagerDialog
from ui.stock_manager import StockManagerDialog
from ui.barcode_scanner import BarcodeInputWidget
from ui.payment_dialog import PaymentDialog


class ProductButton(QPushButton):
    """Custom product button for quick selection."""
    
    def __init__(self, product: Product, parent=None):
        super().__init__(parent)
        self.product = product
        self.setup_ui()
    
    def setup_ui(self):
        """Setup button UI."""
        self.setText(f"{self.product.name}\n${self.product.selling_price}")
        self.setMinimumHeight(80)
        self.setMaximumWidth(150)
        self.setStyleSheet("""
            QPushButton {
                background-color: #f0f0f0;
                border: 2px solid #ccc;
                border-radius: 8px;
                font-weight: bold;
                text-align: center;
            }
            QPushButton:hover {
                background-color: #e0e0e0;
                border-color: #007ACC;
            }
            QPushButton:pressed {
                background-color: #d0d0d0;
            }
        """)


class SaleItemsTable(QTableWidget):
    """Custom table for sale items."""
    
    item_removed = pyqtSignal(int)  # product_id
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
    
    def setup_ui(self):
        """Setup table UI."""
        self.setColumnCount(6)
        self.setHorizontalHeaderLabels([
            "Product", "SKU", "Qty", "Price", "Discount", "Total"
        ])
        
        # Set column widths
        header = self.horizontalHeader()
        header.setStretchLastSection(True)
        header.resizeSection(0, 200)  # Product name
        header.resizeSection(1, 100)  # SKU
        header.resizeSection(2, 60)   # Quantity
        header.resizeSection(3, 80)   # Price
        header.resizeSection(4, 80)   # Discount
        header.resizeSection(5, 100)  # Total
        
        self.setAlternatingRowColors(True)
        self.setSelectionBehavior(QTableWidget.SelectRows)
        
    def add_sale_item(self, item: SaleItem):
        """Add a sale item to the table."""
        row = self.rowCount()
        self.insertRow(row)
        
        self.setItem(row, 0, QTableWidgetItem(item.name))
        self.setItem(row, 1, QTableWidgetItem(item.sku))
        self.setItem(row, 2, QTableWidgetItem(str(item.quantity)))
        self.setItem(row, 3, QTableWidgetItem(f"${item.unit_price:.2f}"))
        self.setItem(row, 4, QTableWidgetItem(f"${item.discount:.2f}"))
        self.setItem(row, 5, QTableWidgetItem(f"${item.total_price:.2f}"))
        
        # Store product ID in the first item
        self.item(row, 0).setData(Qt.UserRole, item.product_id)
    
    def clear_items(self):
        """Clear all items from the table."""
        self.setRowCount(0)
    
    def keyPressEvent(self, event):
        """Handle key press events."""
        if event.key() == Qt.Key_Delete:
            current_row = self.currentRow()
            if current_row >= 0:
                product_id = self.item(current_row, 0).data(Qt.UserRole)
                self.item_removed.emit(product_id)
        super().keyPressEvent(event)


class MainWindow(QMainWindow):
    """Main POS interface window."""
    
    def __init__(self, db_manager: DatabaseManager, auth_manager: AuthenticationManager,
                 current_user: User):
        super().__init__()
        self.db_manager = db_manager
        self.auth_manager = auth_manager
        self.current_user = current_user
        self.logger = get_logger(__name__)
        
        # Initialize managers
        self.inventory_manager = InventoryManager(db_manager)
        self.sales_manager = SalesManager(db_manager, self.inventory_manager)
        self.client_manager = ClientManager(db_manager)
        
        # UI components
        self.product_buttons = []
        self.current_sale: Optional[Sale] = None
        
        self.setup_ui()
        self.setup_connections()
        self.load_products()
        
        # Start new sale automatically
        self.start_new_sale()
        
        self.logger.info(f"Main window initialized for user: {current_user.username}")
    
    def setup_ui(self):
        """Setup the main UI."""
        self.setWindowTitle(f"Hardware POS - {self.current_user.full_name}")
        self.setGeometry(100, 100, 1400, 800)
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QHBoxLayout(central_widget)
        
        # Create splitter
        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)
        
        # Left panel - Products and search
        left_panel = self.create_left_panel()
        splitter.addWidget(left_panel)
        
        # Right panel - Sale details and controls
        right_panel = self.create_right_panel()
        splitter.addWidget(right_panel)
        
        # Set splitter proportions
        splitter.setSizes([800, 600])
        
        # Menu bar
        self.create_menu_bar()
        
        # Status bar
        self.create_status_bar()
          # Apply stylesheet
        self.apply_styles()
    
    def create_left_panel(self) -> QWidget:
        """Create the left panel with products and search."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Barcode scanner section
        self.barcode_scanner = BarcodeInputWidget()
        layout.addWidget(self.barcode_scanner)
        
        # Search section
        search_group = QGroupBox("Product Search")
        search_layout = QVBoxLayout(search_group)
        
        # Search input
        search_row = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search products by name, SKU, or barcode...")
        self.search_button = QPushButton("Search")
        search_row.addWidget(self.search_input)
        search_row.addWidget(self.search_button)
        search_layout.addLayout(search_row)
        
        # Category filter
        category_row = QHBoxLayout()
        category_row.addWidget(QLabel("Category:"))
        self.category_combo = QComboBox()
        self.category_combo.addItem("All Categories", None)
        category_row.addWidget(self.category_combo)
        search_layout.addLayout(category_row)
        
        layout.addWidget(search_group)
        
        # Products grid
        products_group = QGroupBox("Quick Select Products")
        products_layout = QVBoxLayout(products_group)
        
        # Scroll area for products
        self.products_scroll = QScrollArea()
        self.products_widget = QWidget()
        self.products_grid = QGridLayout(self.products_widget)
        self.products_scroll.setWidget(self.products_widget)
        self.products_scroll.setWidgetResizable(True)
        
        products_layout.addWidget(self.products_scroll)
        layout.addWidget(products_group)
        
        return widget
    
    def create_right_panel(self) -> QWidget:
        """Create the right panel with sale details."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Sale info section
        sale_info_group = QGroupBox("Current Sale")
        sale_info_layout = QVBoxLayout(sale_info_group)
        
        # Sale number and client
        info_row = QHBoxLayout()
        self.sale_number_label = QLabel("Sale #: --")
        self.sale_number_label.setFont(QFont("Arial", 12, QFont.Bold))
        info_row.addWidget(self.sale_number_label)
        info_row.addStretch()
        
        # Client selection
        client_row = QHBoxLayout()
        client_row.addWidget(QLabel("Client:"))
        self.client_combo = QComboBox()
        self.client_combo.setEditable(True)
        self.client_combo.addItem("Walk-in Customer", None)
        client_row.addWidget(self.client_combo)
        self.new_client_button = QPushButton("New Client")
        client_row.addWidget(self.new_client_button)
        
        sale_info_layout.addLayout(info_row)
        sale_info_layout.addLayout(client_row)
        layout.addWidget(sale_info_group)
        
        # Items table
        items_group = QGroupBox("Sale Items")
        items_layout = QVBoxLayout(items_group)
        
        self.items_table = SaleItemsTable()
        items_layout.addWidget(self.items_table)
        
        # Add item manually
        add_item_row = QHBoxLayout()
        add_item_row.addWidget(QLabel("Add Item:"))
        self.item_search = QLineEdit()
        self.item_search.setPlaceholderText("Scan barcode or enter SKU...")
        self.qty_spinbox = QSpinBox()
        self.qty_spinbox.setMinimum(1)
        self.qty_spinbox.setMaximum(999)
        self.qty_spinbox.setValue(1)
        self.add_item_button = QPushButton("Add")
        
        add_item_row.addWidget(self.item_search)
        add_item_row.addWidget(QLabel("Qty:"))
        add_item_row.addWidget(self.qty_spinbox)
        add_item_row.addWidget(self.add_item_button)
        
        items_layout.addLayout(add_item_row)
        layout.addWidget(items_group)
        
        # Totals section
        totals_group = QGroupBox("Sale Totals")
        totals_layout = QGridLayout(totals_group)
        
        self.subtotal_label = QLabel("$0.00")
        self.tax_label = QLabel("$0.00")
        self.discount_label = QLabel("$0.00")
        self.total_label = QLabel("$0.00")
        
        self.subtotal_label.setAlignment(Qt.AlignRight)
        self.tax_label.setAlignment(Qt.AlignRight)
        self.discount_label.setAlignment(Qt.AlignRight)
        self.total_label.setAlignment(Qt.AlignRight)
        
        # Make total label bold and larger
        font = QFont("Arial", 14, QFont.Bold)
        self.total_label.setFont(font)
        
        totals_layout.addWidget(QLabel("Subtotal:"), 0, 0)
        totals_layout.addWidget(self.subtotal_label, 0, 1)
        totals_layout.addWidget(QLabel("Tax:"), 1, 0)
        totals_layout.addWidget(self.tax_label, 1, 1)
        totals_layout.addWidget(QLabel("Discount:"), 2, 0)
        totals_layout.addWidget(self.discount_label, 2, 1)
        totals_layout.addWidget(QLabel("TOTAL:"), 3, 0)
        totals_layout.addWidget(self.total_label, 3, 1)
        
        layout.addWidget(totals_group)
        
        # Action buttons
        actions_group = QGroupBox("Actions")
        actions_layout = QVBoxLayout(actions_group)
        
        # Payment buttons
        payment_row = QHBoxLayout()
        self.cash_button = QPushButton("Cash Payment")
        self.card_button = QPushButton("Card Payment")
        self.credit_button = QPushButton("Credit Sale")
        
        self.cash_button.setMinimumHeight(50)
        self.card_button.setMinimumHeight(50)
        self.credit_button.setMinimumHeight(50)
        
        payment_row.addWidget(self.cash_button)
        payment_row.addWidget(self.card_button)
        payment_row.addWidget(self.credit_button)
        
        # Control buttons
        control_row = QHBoxLayout()
        self.discount_button = QPushButton("Apply Discount")
        self.void_button = QPushButton("Void Sale")
        self.new_sale_button = QPushButton("New Sale")
        
        control_row.addWidget(self.discount_button)
        control_row.addWidget(self.void_button)
        control_row.addWidget(self.new_sale_button)
        
        actions_layout.addLayout(payment_row)
        actions_layout.addLayout(control_row)
        layout.addWidget(actions_group)
        
        return widget
    
    def create_menu_bar(self):
        """Create the menu bar."""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu('File')
        
        new_sale_action = QAction('New Sale', self)
        new_sale_action.setShortcut('Ctrl+N')
        new_sale_action.triggered.connect(self.start_new_sale)
        file_menu.addAction(new_sale_action)
        
        file_menu.addSeparator()
        
        logout_action = QAction('Logout', self)
        logout_action.triggered.connect(self.logout)
        file_menu.addAction(logout_action)
        
        exit_action = QAction('Exit', self)
        exit_action.setShortcut('Ctrl+Q')
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Inventory menu
        inventory_menu = menubar.addMenu('Inventory')
        
        products_action = QAction('Manage Products', self)
        products_action.triggered.connect(self.open_products_manager)
        inventory_menu.addAction(products_action)
        
        categories_action = QAction('Manage Categories', self)
        categories_action.triggered.connect(self.open_categories_manager)
        inventory_menu.addAction(categories_action)
        
        stock_action = QAction('Stock Movements', self)
        stock_action.triggered.connect(self.open_stock_manager)
        inventory_menu.addAction(stock_action)
        
        # Clients menu
        clients_menu = menubar.addMenu('Clients')
        
        manage_clients_action = QAction('Manage Clients', self)
        manage_clients_action.triggered.connect(self.open_clients_manager)
        clients_menu.addAction(manage_clients_action)
        
        # Reports menu
        reports_menu = menubar.addMenu('Reports')
        
        sales_report_action = QAction('Sales Report', self)
        sales_report_action.triggered.connect(self.open_sales_report)
        reports_menu.addAction(sales_report_action)
        
        inventory_report_action = QAction('Inventory Report', self)
        inventory_report_action.triggered.connect(self.open_inventory_report)
        reports_menu.addAction(inventory_report_action)
        
        # Settings menu (admin only)
        if self.current_user.role in ['admin', 'manager']:
            settings_menu = menubar.addMenu('Settings')
            
            system_settings_action = QAction('System Settings', self)
            system_settings_action.triggered.connect(self.open_settings)
            settings_menu.addAction(system_settings_action)
            
            users_action = QAction('Manage Users', self)
            users_action.triggered.connect(self.open_users_manager)
            settings_menu.addAction(users_action)
    
    def create_status_bar(self):
        """Create the status bar."""
        self.status_bar = self.statusBar()
        
        # User info
        user_label = QLabel(f"User: {self.current_user.full_name} ({self.current_user.role})")
        self.status_bar.addPermanentWidget(user_label)
        
        # Time
        self.time_label = QLabel()
        self.status_bar.addPermanentWidget(self.time_label)
        
        # Update time every second
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_time)
        self.timer.start(1000)
        self.update_time()
    
    def apply_styles(self):
        """Apply custom styles."""
        # Load and apply QSS stylesheet
        try:
            from config.settings import settings
            style_file = settings.get('ui.style_file', 'config/styles.qss')
            
            with open(style_file, 'r') as f:
                self.setStyleSheet(f.read())
        except Exception as e:            self.logger.warning(f"Could not load stylesheet: {e}")
    
    def setup_connections(self):
        """Setup signal connections."""
        # Barcode scanner
        self.barcode_scanner.barcode_entered.connect(self.on_barcode_scanned)
        
        # Search
        self.search_button.clicked.connect(self.search_products)
        self.search_input.returnPressed.connect(self.search_products)
        self.category_combo.currentTextChanged.connect(self.filter_products)
        
        # Add item
        self.add_item_button.clicked.connect(self.add_item_manual)
        self.item_search.returnPressed.connect(self.add_item_manual)
        
        # Sale actions
        self.cash_button.clicked.connect(lambda: self.process_payment('cash'))
        self.card_button.clicked.connect(lambda: self.process_payment('card'))
        self.credit_button.clicked.connect(lambda: self.process_payment('credit'))
        
        self.discount_button.clicked.connect(self.apply_discount)
        self.void_button.clicked.connect(self.void_sale)
        self.new_sale_button.clicked.connect(self.start_new_sale)
        
        # Table
        self.items_table.item_removed.connect(self.remove_item)
        
        # Client
        self.new_client_button.clicked.connect(self.add_new_client)
    
    def load_products(self):
        """Load products for quick selection."""
        try:
            # Temporarily disconnect signal to prevent recursion
            self.category_combo.currentTextChanged.disconnect()
            
            # Load categories first
            categories = self.inventory_manager.get_all_categories()
            self.category_combo.clear()
            self.category_combo.addItem("All Categories", None)
            
            for category in categories:
                self.category_combo.addItem(category.name, category.id)
            
            # Reconnect signal
            self.category_combo.currentTextChanged.connect(self.filter_products)
            
            # Load popular/featured products for quick access
            products = self.inventory_manager.get_all_products(active_only=True)
            
            # Clear existing buttons
            for button in self.product_buttons:
                button.deleteLater()
            self.product_buttons.clear()
            
            # Create product buttons (limit to first 20 for quick access)
            row, col = 0, 0
            max_cols = 4
            
            for i, product in enumerate(products[:20]):
                button = ProductButton(product)
                button.clicked.connect(lambda checked, p=product: self.add_product_to_sale(p))
                
                self.products_grid.addWidget(button, row, col)
                self.product_buttons.append(button)
                
                col += 1
                if col >= max_cols:
                    col = 0
                    row += 1
            
            # Load clients
            clients = self.client_manager.get_all_clients()
            self.client_combo.clear()
            self.client_combo.addItem("Walk-in Customer", None)
            
            for client in clients:
                self.client_combo.addItem(f"{client.full_name} ({client.customer_code})", client.id)
            
        except Exception as e:
            # Make sure to reconnect signal even if there's an error
            try:
                self.category_combo.currentTextChanged.connect(self.filter_products)
            except:
                pass
            self.logger.error(f"Error loading products: {e}")
            QMessageBox.critical(self, "Error", f"Failed to load products: {e}")
    
    def search_products(self):
        """Search for products."""
        search_term = self.search_input.text().strip()
        if not search_term:
            self.load_products()
            return
        
        try:
            category_id = self.category_combo.currentData()
            products = self.inventory_manager.search_products(
                search_term, category_id=category_id, active_only=True
            )
            
            # Update product buttons with search results
            for button in self.product_buttons:
                button.deleteLater()
            self.product_buttons.clear()
            
            row, col = 0, 0
            max_cols = 4
            
            for product in products[:20]:  # Limit results
                button = ProductButton(product)
                button.clicked.connect(lambda checked, p=product: self.add_product_to_sale(p))
                
                self.products_grid.addWidget(button, row, col)
                self.product_buttons.append(button)
                
                col += 1
                if col >= max_cols:
                    col = 0
                    row += 1
            
        except Exception as e:
            self.logger.error(f"Error searching products: {e}")
            QMessageBox.critical(self, "Error", f"Search failed: {e}")
    
    def filter_products(self):
        """Filter products by category."""
        self.search_products()  # Reuse search logic with category filter
    
    def start_new_sale(self):
        """Start a new sale."""
        try:
            sale_number = self.sales_manager.start_new_sale(self.current_user.id)
            self.current_sale = self.sales_manager.get_current_sale()
            
            # Update UI
            self.sale_number_label.setText(f"Sale #: {sale_number}")
            self.items_table.clear_items()
            self.update_totals()
            
            # Reset client selection
            self.client_combo.setCurrentIndex(0)
            
            self.status_bar.showMessage(f"New sale started: {sale_number}", 3000)
            
        except Exception as e:
            self.logger.error(f"Error starting new sale: {e}")
            QMessageBox.critical(self, "Error", f"Failed to start new sale: {e}")
    
    def add_product_to_sale(self, product: Product):
        """Add a product to the current sale."""
        try:
            quantity = 1  # Default quantity
            self.sales_manager.add_item(product.id, quantity)
            
            # Update UI
            self.refresh_sale_display()
            
        except Exception as e:
            self.logger.error(f"Error adding product to sale: {e}")
            QMessageBox.warning(self, "Error", str(e))
    
    def add_item_manual(self):
        """Add item manually by SKU or barcode."""
        search_text = self.item_search.text().strip()
        if not search_text:
            return
        
        try:
            # Try to find product by SKU or barcode
            product = self.inventory_manager.get_product_by_sku(search_text)
            if not product:
                product = self.inventory_manager.get_product_by_barcode(search_text)
            
            if not product:
                QMessageBox.warning(self, "Product Not Found", 
                                  f"No product found with SKU/barcode: {search_text}")
                return
            
            quantity = self.qty_spinbox.value()
            self.sales_manager.add_item(product.id, quantity)
            
            # Update UI
            self.refresh_sale_display()
            
            # Clear input
            self.item_search.clear()
            self.qty_spinbox.setValue(1)
            
        except Exception as e:
            self.logger.error(f"Error adding item manually: {e}")
            QMessageBox.warning(self, "Error", str(e))
    
    def on_barcode_scanned(self, barcode: str):
        """Handle barcode scanned from the barcode scanner widget."""
        try:
            # Set the barcode in the item search field
            self.item_search.setText(barcode)
            
            # Try to find product by barcode
            product = self.inventory_manager.get_product_by_barcode(barcode)
            if not product:
                # Try by SKU as fallback
                product = self.inventory_manager.get_product_by_sku(barcode)
            
            if product:
                # Automatically add the product with default quantity
                quantity = self.qty_spinbox.value()
                self.sales_manager.add_item(product.id, quantity)
                
                # Update UI
                self.refresh_sale_display()
                
                # Clear input after short delay for visual feedback
                QTimer.singleShot(1500, self.item_search.clear)
                
                self.logger.info(f"Product added via barcode scan: {product.name} (Barcode: {barcode})")
            else:
                # Product not found - leave barcode in field for manual verification
                QMessageBox.warning(self, "Product Not Found", 
                                  f"No product found with barcode: {barcode}\n"
                                  f"Please verify the barcode or add the product manually.")
                self.logger.warning(f"Barcode scan failed - product not found: {barcode}")
                
        except Exception as e:
            self.logger.error(f"Error processing scanned barcode {barcode}: {e}")
            QMessageBox.warning(self, "Barcode Error", 
                              f"Error processing barcode: {str(e)}")
    
    def remove_item(self, product_id: int):
        """Remove an item from the sale."""
        try:
            self.sales_manager.remove_item(product_id)
            self.refresh_sale_display()
            
        except Exception as e:
            self.logger.error(f"Error removing item: {e}")
            QMessageBox.warning(self, "Error", str(e))
    
    def refresh_sale_display(self):
        """Refresh the sale display."""
        self.current_sale = self.sales_manager.get_current_sale()
        if not self.current_sale:
            return
        
        # Update items table
        self.items_table.clear_items()
        for item in self.current_sale.items:
            self.items_table.add_sale_item(item)
          # Update totals
        self.update_totals()
    
    def update_totals(self):
        """Update the totals display."""
        if not self.current_sale:
            self.subtotal_label.setText("$0.00")
            self.tax_label.setText("$0.00")
            self.discount_label.setText("$0.00")
            self.total_label.setText("$0.00")
            return
        
        self.subtotal_label.setText(f"${self.current_sale.subtotal:.2f}")
        self.tax_label.setText(f"${self.current_sale.tax_amount:.2f}")
        self.discount_label.setText(f"${self.current_sale.discount_amount:.2f}")
        self.total_label.setText(f"${self.current_sale.total_amount:.2f}")
    
    def process_payment(self, payment_method: str):
        """Process payment for the current sale."""
        if not self.current_sale or not self.current_sale.items:
            QMessageBox.warning(self, "No Sale", "No items in current sale.")
            return
        
        try:
            # Get client ID if selected
            client_id = self.client_combo.currentData()
            if client_id:
                # Update sale with client
                self.current_sale.client_id = client_id
            
            # Open payment dialog
            payment_dialog = PaymentDialog(self.current_sale, self)
            payment_dialog.payment_completed.connect(self.on_payment_completed)
            
            # Show the dialog
            if payment_dialog.exec_() == QDialog.Accepted:
                pass  # Payment completed signal will handle the completion
                
        except Exception as e:
            self.logger.error(f"Error opening payment dialog: {e}")
            QMessageBox.critical(self, "Payment Error", f"Failed to open payment dialog: {e}")
    
    def on_payment_completed(self, payment_details: dict):
        """Handle completed payment from payment dialog."""
        try:
            # Extract payment details
            payment_method = payment_details.get('method', 'cash')
            amount_paid = payment_details.get('amount_received', self.current_sale.total_amount)
            
            # Complete the sale
            sale_id = self.sales_manager.complete_sale(payment_method, amount_paid)
            
            # Show success message with payment details
            change_due = payment_details.get('change_due', 0)
            if change_due > 0:
                message = (f"Sale {self.current_sale.sale_number} completed successfully!\n"
                          f"Payment: ${amount_paid:.2f}\n"
                          f"Change due: ${change_due:.2f}")
            else:
                message = f"Sale {self.current_sale.sale_number} completed successfully!"
            
            QMessageBox.information(self, "Sale Completed", message)
            
            # Start new sale
            self.start_new_sale()
            
        except Exception as e:
            self.logger.error(f"Error completing payment: {e}")
            QMessageBox.critical(self, "Payment Error", f"Failed to complete payment: {e}")
    
    def apply_discount(self):
        """Apply a discount to the sale."""
        if not self.current_sale:
            QMessageBox.warning(self, "No Sale", "No active sale to apply discount.")
            return
        # TODO: Implement discount dialog
        QMessageBox.information(self, "Feature", "Discount feature will be implemented.")
    
    def void_sale(self):
        """Void the current sale."""
        if not self.current_sale:
            QMessageBox.warning(self, "No Sale", "No active sale to void.")
            return
        
        reply = QMessageBox.question(self, "Void Sale", 
                                   "Are you sure you want to void this sale?",
                                   QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            try:
                self.sales_manager.void_sale("Voided by user")
                self.start_new_sale()
                
            except Exception as e:
                self.logger.error(f"Error voiding sale: {e}")
                QMessageBox.critical(self, "Error", f"Failed to void sale: {e}")
    
    def add_new_client(self):
        """Add a new client."""
        # TODO: Implement new client dialog
        QMessageBox.information(self, "Feature", "New client feature will be implemented.")
    
    def update_time(self):
        """Update the time display."""
        from datetime import datetime
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.time_label.setText(current_time)
    
    # Menu actions
    def open_products_manager(self):
        """Open the Product Manager dialog."""
        try:
            product_dialog = ProductManagerDialog(
                self.db_manager,
                self
            )
            product_dialog.product_updated.connect(self.load_products)
            product_dialog.exec_()
        except Exception as e:
            self.logger.error(f"Error opening product manager: {e}")
            QMessageBox.critical(self, "Error", f"Failed to open product manager: {e}")
    
    def open_categories_manager(self):
        """Open the Category Manager dialog."""
        try:
            category_dialog = CategoryManagerDialog(
                self.db_manager,
                self.inventory_manager,
                self.current_user,
                self
            )
            category_dialog.categories_updated.connect(self.load_products)  # Reload categories in combo
            category_dialog.exec_()
        except Exception as e:
            self.logger.error(f"Error opening category manager: {e}")
            QMessageBox.critical(self, "Error", f"Failed to open category manager: {e}")
    
    def open_stock_manager(self):
        """Open the Stock Manager dialog."""
        try:
            stock_dialog = StockManagerDialog(
                self.inventory_manager,
                self.auth_manager,
                self
            )
            stock_dialog.exec_()
        except Exception as e:
            self.logger.error(f"Error opening stock manager: {e}")
            QMessageBox.critical(self, "Error", f"Failed to open stock manager: {e}")
    
    def open_clients_manager(self):
        """Open the Client Manager dialog."""
        try:
            client_dialog = ClientManagerDialog(
                self.db_manager,
                self.client_manager,
                self.current_user,
                self
            )
            client_dialog.clients_updated.connect(self.load_products)  # Reload clients in combo
            client_dialog.exec_()
        except Exception as e:
            self.logger.error(f"Error opening client manager: {e}")
            QMessageBox.critical(self, "Error", f"Failed to open client manager: {e}")
    
    def open_sales_report(self):
        """Open the Sales Report dialog."""
        QMessageBox.information(self, "Feature", "Sales reports will be implemented soon.")
    
    def open_inventory_report(self):
        """Open the Inventory Report dialog."""
        QMessageBox.information(self, "Feature", "Inventory reports will be implemented soon.")
    
    def open_settings(self):
        """Open the System Settings dialog."""
        QMessageBox.information(self, "Feature", "System settings will be implemented soon.")
    
    def open_users_manager(self):
        """Open the User Manager dialog."""
        QMessageBox.information(self, "Feature", "User management will be implemented soon.")
    
    def logout(self):
        """Logout current user."""
        reply = QMessageBox.question(self, "Logout", "Are you sure you want to logout?",
                                   QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            self.auth_manager.logout()
            self.close()
            
            # Re-import and show login dialog
            from ui.login import LoginDialog
            login_dialog = LoginDialog(self.db_manager, self.auth_manager)
            if login_dialog.exec_() == QDialog.Accepted:
                # Start new main window with new user
                new_main_window = MainWindow(
                    self.db_manager, 
                    self.auth_manager, 
                    login_dialog.current_user
                )
                new_main_window.show()
    
    def closeEvent(self, event):
        """Handle close event."""
        reply = QMessageBox.question(self, "Exit", "Are you sure you want to exit?",
                                   QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            # Clean up any pending sales
            if self.current_sale and self.current_sale.items:
                save_reply = QMessageBox.question(self, "Pending Sale", 
                                               "You have items in the current sale. Save as pending?",
                                               QMessageBox.Yes | QMessageBox.No)
                if save_reply == QMessageBox.Yes:
                    # TODO: Implement save pending sale
                    pass
            
            event.accept()
        else:
            event.ignore()
