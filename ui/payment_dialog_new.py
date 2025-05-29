"""
Payment Processing Dialog for Hardware POS System

Handles payment collection, change calculation, and receipt generation.
"""

import logging
from decimal import Decimal
from typing import Optional, Dict, Any
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, 
    QPushButton, QLineEdit, QComboBox, QTextEdit, QGroupBox,
    QMessageBox, QCheckBox, QSpinBox, QDoubleSpinBox
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont, QPixmap

from models import Sale
from utils.logger import get_logger


class PaymentDialog(QDialog):
    """Payment processing dialog."""
    
    payment_completed = pyqtSignal(dict)  # Emits payment details
    
    def __init__(self, sale: Sale, parent=None):
        super().__init__(parent)
        self.sale = sale
        self.logger = get_logger(__name__)
        self.payment_details = {}
        
        self.setup_ui()
        self.setup_connections()
        
    def setup_ui(self):
        """Setup the UI components."""
        self.setWindowTitle("Process Payment")
        self.setModal(True)
        self.setFixedSize(500, 600)
        
        layout = QVBoxLayout(self)
        
        # Sale summary
        self.create_sale_summary(layout)
        
        # Payment method selection
        self.create_payment_method_section(layout)
        
        # Payment amount section
        self.create_payment_amount_section(layout)
        
        # Change calculation
        self.create_change_section(layout)
        
        # Buttons
        self.create_buttons(layout)
        
        # Apply styles
        self.apply_styles()
        
    def create_sale_summary(self, layout):
        """Create sale summary section."""
        summary_group = QGroupBox("Sale Summary")
        summary_layout = QGridLayout(summary_group)
        
        # Sale details
        self.sale_number_label = QLabel(f"Sale #: {self.sale.sale_number}")
        self.sale_number_label.setFont(QFont("Arial", 12, QFont.Bold))
        
        self.items_count_label = QLabel(f"Items: {len(self.sale.items)}")
        self.subtotal_label = QLabel(f"Subtotal: ${self.sale.subtotal:.2f}")
        self.tax_label = QLabel(f"Tax: ${self.sale.tax_amount:.2f}")
        self.discount_label = QLabel(f"Discount: ${self.sale.discount_amount:.2f}")
        
        # Total amount (large and bold)
        self.total_label = QLabel(f"TOTAL: ${self.sale.total_amount:.2f}")
        self.total_label.setFont(QFont("Arial", 16, QFont.Bold))
        self.total_label.setStyleSheet("color: #2E7D32; background-color: #E8F5E8; padding: 10px; border-radius: 5px;")
        
        # Add to layout
        summary_layout.addWidget(self.sale_number_label, 0, 0, 1, 2)
        summary_layout.addWidget(self.items_count_label, 1, 0)
        summary_layout.addWidget(self.subtotal_label, 2, 0)
        summary_layout.addWidget(self.tax_label, 2, 1)
        summary_layout.addWidget(self.discount_label, 3, 0)
        summary_layout.addWidget(self.total_label, 4, 0, 1, 2)
        
        layout.addWidget(summary_group)
        
    def create_payment_method_section(self, layout):
        """Create payment method selection section."""
        payment_group = QGroupBox("Payment Method")
        payment_layout = QVBoxLayout(payment_group)
        
        # Payment method combo
        method_layout = QHBoxLayout()
        method_layout.addWidget(QLabel("Method:"))
        
        self.payment_method_combo = QComboBox()
        self.payment_method_combo.addItems([
            "Cash",
            "Credit Card", 
            "Debit Card",
            "Customer Credit",
            "Split Payment"
        ])
        method_layout.addWidget(self.payment_method_combo)
        payment_layout.addLayout(method_layout)
        
        # Card details (for card payments)
        self.card_details_widget = QGroupBox("Card Details")
        card_layout = QGridLayout(self.card_details_widget)
        
        card_layout.addWidget(QLabel("Card Number:"), 0, 0)
        self.card_number_input = QLineEdit()
        self.card_number_input.setPlaceholderText("**** **** **** ****")
        card_layout.addWidget(self.card_number_input, 0, 1)
        
        card_layout.addWidget(QLabel("Authorization:"), 1, 0)
        self.auth_code_input = QLineEdit()
        self.auth_code_input.setPlaceholderText("Auth code")
        card_layout.addWidget(self.auth_code_input, 1, 1)
        
        self.card_details_widget.hide()  # Hidden by default
        payment_layout.addWidget(self.card_details_widget)
        
        layout.addWidget(payment_group)
        
    def create_payment_amount_section(self, layout):
        """Create payment amount section."""
        amount_group = QGroupBox("Payment Amount")
        amount_layout = QGridLayout(amount_group)
        
        # Amount received
        amount_layout.addWidget(QLabel("Amount Received:"), 0, 0)
        self.amount_received_input = QDoubleSpinBox()
        self.amount_received_input.setRange(0.00, 99999.99)
        self.amount_received_input.setDecimals(2)
        self.amount_received_input.setValue(float(self.sale.total_amount))
        self.amount_received_input.setPrefix("$")
        amount_layout.addWidget(self.amount_received_input, 0, 1)
        
        # Quick amount buttons for cash
        self.quick_buttons_widget = QGroupBox("Quick Amounts")
        quick_layout = QGridLayout(self.quick_buttons_widget)
        
        # Common bill denominations
        amounts = [20, 50, 100, 200]
        for i, amount in enumerate(amounts):
            btn = QPushButton(f"${amount}")
            btn.clicked.connect(lambda checked, amt=amount: self.set_quick_amount(amt))
            quick_layout.addWidget(btn, i // 2, i % 2)
        
        # Exact amount button
        exact_btn = QPushButton("Exact Amount")
        exact_btn.clicked.connect(self.set_exact_amount)
        quick_layout.addWidget(exact_btn, 2, 0, 1, 2)
        
        amount_layout.addWidget(self.quick_buttons_widget, 1, 0, 1, 2)
        layout.addWidget(amount_group)
        
    def create_change_section(self, layout):
        """Create change calculation section."""
        change_group = QGroupBox("Change")
        change_layout = QVBoxLayout(change_group)
        
        # Change amount (large and visible)
        self.change_label = QLabel("$0.00")
        self.change_label.setFont(QFont("Arial", 20, QFont.Bold))
        self.change_label.setAlignment(Qt.AlignCenter)
        self.change_label.setStyleSheet("color: #1976D2; background-color: #E3F2FD; padding: 15px; border-radius: 8px;")
        
        change_layout.addWidget(QLabel("Change Due:"))
        change_layout.addWidget(self.change_label)
        
        layout.addWidget(change_group)
        
    def create_buttons(self, layout):
        """Create action buttons."""
        # Receipt options
        receipt_group = QGroupBox("Receipt Options")
        receipt_layout = QVBoxLayout(receipt_group)
        
        self.thermal_receipt_check = QCheckBox("Print Thermal Receipt (80mm)")
        self.thermal_receipt_check.setChecked(True)
        self.pdf_invoice_check = QCheckBox("Generate PDF Invoice")
        self.pdf_invoice_check.setChecked(False)
        self.auto_print_check = QCheckBox("Auto-print thermal receipt")
        self.auto_print_check.setChecked(False)
        
        receipt_layout.addWidget(self.thermal_receipt_check)
        receipt_layout.addWidget(self.pdf_invoice_check)
        receipt_layout.addWidget(self.auto_print_check)
        
        layout.addWidget(receipt_group)
        
        # Action buttons
        button_layout = QHBoxLayout()
        
        # Cancel button
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setMinimumHeight(40)
        
        # Process payment button
        self.process_button = QPushButton("Process Payment")
        self.process_button.setMinimumHeight(40)
        self.process_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #45A049;
            }
        """)
        
        button_layout.addWidget(self.cancel_button)
        button_layout.addWidget(self.process_button)
        
        layout.addLayout(button_layout)
        
    def setup_connections(self):
        """Setup signal connections."""
        self.payment_method_combo.currentTextChanged.connect(self.on_payment_method_changed)
        self.amount_received_input.valueChanged.connect(self.calculate_change)
        self.cancel_button.clicked.connect(self.reject)
        self.process_button.clicked.connect(self.process_payment)
        
        # Initial calculation
        self.calculate_change()
        
    def on_payment_method_changed(self, method: str):
        """Handle payment method change."""
        # Show/hide card details
        if "Card" in method:
            self.card_details_widget.show()
        else:
            self.card_details_widget.hide()
            
        # Show/hide quick buttons for cash
        if method == "Cash":
            self.quick_buttons_widget.show()
        else:
            self.quick_buttons_widget.hide()
            
        # Recalculate change
        self.calculate_change()
        
    def set_quick_amount(self, amount: float):
        """Set quick amount."""
        self.amount_received_input.setValue(amount)
        
    def set_exact_amount(self):
        """Set exact amount."""
        self.amount_received_input.setValue(float(self.sale.total_amount))
        
    def calculate_change(self):
        """Calculate and display change."""
        amount_received = Decimal(str(self.amount_received_input.value()))
        change = amount_received - self.sale.total_amount
        
        if change >= 0:
            self.change_label.setText(f"${change:.2f}")
            self.change_label.setStyleSheet("color: #1976D2; background-color: #E3F2FD; padding: 15px; border-radius: 8px;")
            self.process_button.setEnabled(True)
        else:
            self.change_label.setText(f"-${abs(change):.2f}")
            self.change_label.setStyleSheet("color: #D32F2F; background-color: #FFEBEE; padding: 15px; border-radius: 8px;")
            self.process_button.setEnabled(False)
            
    def process_payment(self):
        """Process the payment."""
        try:
            method = self.payment_method_combo.currentText()
            amount_received = Decimal(str(self.amount_received_input.value()))
            change = amount_received - self.sale.total_amount
            
            # Validate payment
            if amount_received < self.sale.total_amount:
                QMessageBox.warning(self, "Insufficient Payment", 
                                  "Payment amount is less than the total due.")
                return
                
            # Prepare payment details
            self.payment_details = {
                'method': method.lower().replace(' ', '_'),
                'amount_received': amount_received,
                'change_due': change,
                'total_amount': self.sale.total_amount
            }
            
            # Add card details if applicable
            if "Card" in method:
                self.payment_details['card_number'] = self.card_number_input.text()[-4:]  # Last 4 digits only
                self.payment_details['auth_code'] = self.auth_code_input.text()
                
            # Confirm payment
            reply = QMessageBox.question(self, "Confirm Payment",
                                       f"Process payment of ${amount_received:.2f} via {method}?\n"
                                       f"Change due: ${change:.2f}",
                                       QMessageBox.Yes | QMessageBox.No)
            
            if reply == QMessageBox.Yes:
                self.payment_completed.emit(self.payment_details)
                self.accept()
                
        except Exception as e:
            self.logger.error(f"Error processing payment: {e}")
            QMessageBox.critical(self, "Payment Error", f"Failed to process payment: {e}")
            
    def apply_styles(self):
        """Apply custom styles."""
        self.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #cccccc;
                border-radius: 5px;
                margin: 5px 0px;
                padding-top: 15px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
            QLineEdit, QDoubleSpinBox, QComboBox {
                padding: 5px;
                border: 1px solid #ccc;
                border-radius: 3px;
            }
            QPushButton {
                padding: 8px;
                border-radius: 4px;
                border: 1px solid #ccc;
            }
            QPushButton:hover {
                background-color: #f0f0f0;
            }
        """)
