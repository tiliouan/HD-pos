"""
Printer utilities for Hardware POS System

Handles receipt printing, barcode printing, and label generation.
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from decimal import Decimal
import tempfile
import os

# Import for different printing methods
try:
    import win32print
    import win32api
    HAS_WIN32_PRINT = True
except ImportError:
    HAS_WIN32_PRINT = False

from config.settings import settings


class PrinterManager:
    """Manages printing operations."""
    
    def __init__(self):
        """Initialize printer manager."""
        self.logger = logging.getLogger(__name__)
        
    def get_available_printers(self) -> List[str]:
        """Get list of available printers.
        
        Returns:
            List of printer names
        """
        printers = []
        
        if HAS_WIN32_PRINT:
            try:
                # Get default printer
                default_printer = win32print.GetDefaultPrinter()
                
                # Get all printers
                printer_list = win32print.EnumPrinters(win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS)
                
                for printer in printer_list:
                    printers.append(printer[2])  # Printer name
                    
            except Exception as e:
                self.logger.error(f"Error getting printers: {e}")
        
        return printers
    
    def print_receipt(self, sale_data: Dict[str, Any]) -> bool:
        """Print a sales receipt.
        
        Args:
            sale_data: Sale information dictionary
            
        Returns:
            True if successful, False otherwise
        """
        try:
            receipt_content = self._generate_receipt_content(sale_data)
            
            # Get receipt printer from settings
            printer_name = settings.get('printing.receipt_printer', '')
            
            if not printer_name:
                # Use default printer
                if HAS_WIN32_PRINT:
                    printer_name = win32print.GetDefaultPrinter()
                else:
                    self.logger.warning("No printer configured and win32print not available")
                    return False
            
            return self._print_text(receipt_content, printer_name)
            
        except Exception as e:
            self.logger.error(f"Error printing receipt: {e}")
            return False
    
    def _generate_receipt_content(self, sale_data: Dict[str, Any]) -> str:
        """Generate receipt content.
        
        Args:
            sale_data: Sale information
            
        Returns:
            Formatted receipt content
        """
        width = settings.get('printing.receipt_width', 80)
        currency_symbol = settings.get('pos.currency_symbol', '$')
        
        # Header
        content = []
        content.append("="*width)
        content.append("HARDWARE STORE POS SYSTEM".center(width))
        content.append("="*width)
        content.append("")
        
        # Sale info
        content.append(f"Receipt #: {sale_data.get('sale_number', 'N/A')}")
        content.append(f"Date: {sale_data.get('date', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))}")
        content.append(f"Cashier: {sale_data.get('cashier_name', 'N/A')}")
        
        if sale_data.get('client_name'):
            content.append(f"Customer: {sale_data['client_name']}")
        
        content.append("")
        content.append("-"*width)
        
        # Items
        content.append(f"{'Item':<30} {'Qty':>6} {'Price':>10} {'Total':>10}")
        content.append("-"*width)
        
        for item in sale_data.get('items', []):
            name = item['name'][:29] if len(item['name']) > 29 else item['name']
            qty = str(item['quantity'])
            price = f"{currency_symbol}{item['unit_price']:.2f}"
            total = f"{currency_symbol}{item['total_price']:.2f}"
            
            content.append(f"{name:<30} {qty:>6} {price:>10} {total:>10}")
        
        content.append("-"*width)
        
        # Totals
        subtotal = sale_data.get('subtotal', 0)
        tax_amount = sale_data.get('tax_amount', 0)
        discount = sale_data.get('discount_amount', 0)
        total = sale_data.get('total_amount', 0)
        
        content.append(f"{'Subtotal:':<50} {currency_symbol}{subtotal:.2f}".rjust(width))
        
        if discount > 0:
            content.append(f"{'Discount:':<50} -{currency_symbol}{discount:.2f}".rjust(width))
        
        content.append(f"{'Tax:':<50} {currency_symbol}{tax_amount:.2f}".rjust(width))
        content.append(f"{'TOTAL:':<50} {currency_symbol}{total:.2f}".rjust(width))
        
        # Payment info
        content.append("")
        content.append(f"Payment Method: {sale_data.get('payment_method', 'Cash')}")
        
        # Footer
        content.append("")
        content.append("="*width)
        content.append("Thank you for your business!".center(width))
        content.append("="*width)
        content.append("")
        content.append("")  # Extra space for cutting
        
        return "\n".join(content)
    
    def _print_text(self, content: str, printer_name: str) -> bool:
        """Print text content to printer.
        
        Args:
            content: Text content to print
            printer_name: Name of the printer
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if HAS_WIN32_PRINT:
                # Create a temporary file
                with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                    f.write(content)
                    temp_file = f.name
                
                try:
                    # Print the file
                    win32api.ShellExecute(
                        0,
                        "print",
                        temp_file,
                        f'/d:"{printer_name}"',
                        ".",
                        0
                    )
                    return True
                finally:
                    # Clean up temporary file
                    try:
                        os.unlink(temp_file)
                    except:
                        pass
            else:
                # Fallback: save to file for manual printing
                receipt_file = f"receipt_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
                with open(receipt_file, 'w') as f:
                    f.write(content)
                
                self.logger.info(f"Receipt saved to {receipt_file} (no printer available)")
                return True
                
        except Exception as e:
            self.logger.error(f"Error printing: {e}")
            return False
    
    def print_barcode_label(self, product_data: Dict[str, Any]) -> bool:
        """Print a barcode label.
        
        Args:
            product_data: Product information
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Generate barcode label content
            label_content = self._generate_barcode_label(product_data)
            
            # Get barcode printer from settings
            printer_name = settings.get('printing.barcode_printer', '')
            
            if not printer_name:
                printer_name = settings.get('printing.receipt_printer', '')
            
            if not printer_name and HAS_WIN32_PRINT:
                printer_name = win32print.GetDefaultPrinter()
            
            return self._print_text(label_content, printer_name)
            
        except Exception as e:
            self.logger.error(f"Error printing barcode label: {e}")
            return False
    
    def _generate_barcode_label(self, product_data: Dict[str, Any]) -> str:
        """Generate barcode label content.
        
        Args:
            product_data: Product information
            
        Returns:
            Formatted label content
        """
        content = []
        
        # Product name (truncated if too long)
        name = product_data.get('name', 'Unknown Product')
        if len(name) > 40:
            name = name[:37] + "..."
        content.append(name)
        
        # SKU
        content.append(f"SKU: {product_data.get('sku', 'N/A')}")
        
        # Price
        currency_symbol = settings.get('pos.currency_symbol', '$')
        price = product_data.get('selling_price', 0)
        content.append(f"Price: {currency_symbol}{price:.2f}")
        
        # Barcode (simple text representation)
        barcode = product_data.get('barcode', '')
        if barcode:
            content.append(f"Barcode: {barcode}")
            # Simple ASCII barcode representation
            content.append("|||| | || ||| | | |||| |||")
        
        content.append("")  # Space for cutting
        
        return "\n".join(content)
    
    def test_printer(self, printer_name: str = None) -> bool:
        """Test printer connection.
        
        Args:
            printer_name: Printer name to test (default: configured printer)
            
        Returns:
            True if printer is working, False otherwise
        """
        try:
            if not printer_name:
                printer_name = settings.get('printing.receipt_printer', '')
            
            if not printer_name and HAS_WIN32_PRINT:
                printer_name = win32print.GetDefaultPrinter()
            
            test_content = f"""
TEST PRINT
==========

Printer: {printer_name}
Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

This is a test print from Hardware POS System.

If you can read this, the printer is working correctly.

==========
"""
            
            return self._print_text(test_content, printer_name)
            
        except Exception as e:
            self.logger.error(f"Error testing printer: {e}")
            return False


# Global printer manager instance
printer_manager = PrinterManager()
