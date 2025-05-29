"""
Receipt Generator for Hardware POS System

Handles both thermal printer receipts and PDF invoice generation.
"""

import os
import logging
from datetime import datetime
from decimal import Decimal
from typing import List, Dict, Any, Optional
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.pdfgen import canvas
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

from models import Sale
from utils.logger import get_logger


class ReceiptGenerator:
    """Generates receipts and invoices for completed sales."""
    
    def __init__(self):
        self.logger = get_logger(__name__)
        self.company_info = {
            'name': 'Hardware Store',
            'address': '123 Main Street',
            'city': 'Your City, Province',
            'postal_code': 'X1X 1X1',
            'phone': '(555) 123-4567',
            'email': 'info@hardwarestore.com',
            'tax_number': 'GST/HST: 123456789RT0001'
        }
        
    def generate_thermal_receipt(self, sale: 'Sale', payment_details: Dict[str, Any]) -> str:
        """
        Generate a thermal printer receipt (plain text format).
        
        Args:
            sale: The completed sale
            payment_details: Payment information
            
        Returns:
            String containing formatted receipt text
        """
        try:
            receipt_lines = []
            
            # Header
            receipt_lines.append("=" * 40)
            receipt_lines.append(f"{self.company_info['name']:^40}")
            receipt_lines.append(f"{self.company_info['address']:^40}")
            receipt_lines.append(f"{self.company_info['city']:^40}")
            receipt_lines.append(f"Phone: {self.company_info['phone']:^32}")
            receipt_lines.append("=" * 40)
            receipt_lines.append("")
            
            # Sale info
            receipt_lines.append(f"Receipt #: {sale.sale_id}")
            receipt_lines.append(f"Date: {sale.date.strftime('%Y-%m-%d %H:%M:%S')}")
            if sale.client:
                receipt_lines.append(f"Customer: {sale.client.name}")
            receipt_lines.append("-" * 40)
            
            # Items
            receipt_lines.append("ITEMS:")
            receipt_lines.append(f"{'Item':<20} {'Qty':>4} {'Price':>8} {'Total':>8}")
            receipt_lines.append("-" * 40)
            
            for item in sale.items:
                item_name = item['name'][:20]  # Truncate if too long
                qty = item['quantity']
                price = f"${item['price']:.2f}"
                total = f"${item['total']:.2f}"
                receipt_lines.append(f"{item_name:<20} {qty:>4} {price:>8} {total:>8}")
            
            receipt_lines.append("-" * 40)
            
            # Totals
            receipt_lines.append(f"{'Subtotal:':<32} ${sale.subtotal:.2f}")
            receipt_lines.append(f"{'Tax:':<32} ${sale.tax:.2f}")
            receipt_lines.append(f"{'TOTAL:':<32} ${sale.total:.2f}")
            receipt_lines.append("")
            
            # Payment info
            receipt_lines.append("PAYMENT:")
            receipt_lines.append(f"Method: {payment_details.get('method', 'Cash')}")
            receipt_lines.append(f"Amount Paid: ${payment_details.get('amount_paid', sale.total):.2f}")
            if payment_details.get('change', 0) > 0:
                receipt_lines.append(f"Change: ${payment_details['change']:.2f}")
            receipt_lines.append("")
            
            # Footer
            receipt_lines.append(f"{self.company_info['tax_number']:^40}")
            receipt_lines.append("")
            receipt_lines.append("Thank you for your business!")
            receipt_lines.append("=" * 40)
            
            return "\n".join(receipt_lines)
            
        except Exception as e:
            self.logger.error(f"Error generating thermal receipt: {e}")
            return "Error generating receipt"
    
    def generate_pdf_invoice(self, sale: 'Sale', payment_details: Dict[str, Any], 
                           save_path: Optional[str] = None) -> str:
        """
        Generate a PDF invoice for the sale.
        
        Args:
            sale: The completed sale
            payment_details: Payment information
            save_path: Optional path to save the PDF. If None, saves to receipts folder.
            
        Returns:
            Path to the generated PDF file
        """
        try:
            if save_path is None:
                # Create receipts directory if it doesn't exist
                receipts_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'receipts')
                os.makedirs(receipts_dir, exist_ok=True)
                filename = f"invoice_{sale.sale_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
                save_path = os.path.join(receipts_dir, filename)
            
            # Create PDF document
            doc = SimpleDocTemplate(save_path, pagesize=letter)
            story = []
            styles = getSampleStyleSheet()
            
            # Custom styles
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=20,
                spaceAfter=30,
                alignment=TA_CENTER
            )
            
            header_style = ParagraphStyle(
                'CustomHeader',
                parent=styles['Normal'],
                fontSize=12,
                alignment=TA_CENTER,
                spaceAfter=20
            )
            
            # Company header
            story.append(Paragraph(self.company_info['name'], title_style))
            story.append(Paragraph(f"{self.company_info['address']}<br/>{self.company_info['city']}<br/>Phone: {self.company_info['phone']}<br/>Email: {self.company_info['email']}", header_style))
            
            story.append(Spacer(1, 20))
            
            # Invoice info
            invoice_data = [
                ['Invoice #:', sale.sale_id, 'Date:', sale.date.strftime('%Y-%m-%d %H:%M:%S')],
            ]
            
            if sale.client:
                invoice_data.append(['Customer:', sale.client.name, 'Phone:', getattr(sale.client, 'phone', 'N/A')])
                invoice_data.append(['Address:', getattr(sale.client, 'address', 'N/A'), '', ''])
            
            invoice_table = Table(invoice_data, colWidths=[1.5*inch, 2.5*inch, 1*inch, 2*inch])
            invoice_table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ]))
            story.append(invoice_table)
            story.append(Spacer(1, 20))
            
            # Items table
            items_data = [['Item', 'Quantity', 'Unit Price', 'Total']]
            
            for item in sale.items:
                items_data.append([
                    item['name'],
                    str(item['quantity']),
                    f"${item['price']:.2f}",
                    f"${item['total']:.2f}"
                ])
            
            items_table = Table(items_data, colWidths=[3*inch, 1*inch, 1.5*inch, 1.5*inch])
            items_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 10),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            story.append(items_table)
            story.append(Spacer(1, 20))
            
            # Totals
            totals_data = [
                ['', '', 'Subtotal:', f"${sale.subtotal:.2f}"],
                ['', '', 'Tax:', f"${sale.tax:.2f}"],
                ['', '', 'TOTAL:', f"${sale.total:.2f}"],
            ]
            
            totals_table = Table(totals_data, colWidths=[3*inch, 1*inch, 1.5*inch, 1.5*inch])
            totals_table.setStyle(TableStyle([
                ('ALIGN', (2, 0), (-1, -1), 'RIGHT'),
                ('FONTNAME', (2, 0), (-1, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (2, 0), (-1, -1), 12),
                ('LINEBELOW', (2, -1), (-1, -1), 2, colors.black),
            ]))
            story.append(totals_table)
            story.append(Spacer(1, 20))
            
            # Payment info
            payment_data = [
                ['Payment Method:', payment_details.get('method', 'Cash')],
                ['Amount Paid:', f"${payment_details.get('amount_paid', sale.total):.2f}"],
            ]
            
            if payment_details.get('change', 0) > 0:
                payment_data.append(['Change:', f"${payment_details['change']:.2f}"])
            
            payment_table = Table(payment_data, colWidths=[2*inch, 2*inch])
            payment_table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
            ]))
            story.append(payment_table)
            story.append(Spacer(1, 30))
            
            # Footer
            footer_style = ParagraphStyle(
                'Footer',
                parent=styles['Normal'],
                fontSize=10,
                alignment=TA_CENTER
            )
            
            story.append(Paragraph(f"{self.company_info['tax_number']}", footer_style))
            story.append(Paragraph("Thank you for your business!", footer_style))
            
            # Build PDF
            doc.build(story)
            
            self.logger.info(f"PDF invoice generated: {save_path}")
            return save_path
            
        except Exception as e:
            self.logger.error(f"Error generating PDF invoice: {e}")
            raise
    
    def print_thermal_receipt(self, receipt_text: str, printer_name: Optional[str] = None) -> bool:
        """
        Send receipt to thermal printer.
        
        Args:
            receipt_text: The formatted receipt text
            printer_name: Optional printer name. If None, uses default printer.
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # This is a basic implementation
            # In a real system, you'd use specific thermal printer libraries
            # like python-escpos or win32print for Windows
            
            if os.name == 'nt':  # Windows
                import win32print
                import win32api
                
                if printer_name is None:
                    printer_name = win32print.GetDefaultPrinter()
                
                # Open printer
                hPrinter = win32print.OpenPrinter(printer_name)
                
                try:
                    # Start print job
                    hJob = win32print.StartDocPrinter(hPrinter, 1, ("Receipt", None, "RAW"))
                    win32print.StartPagePrinter(hPrinter)
                    
                    # Send data
                    win32print.WritePrinter(hPrinter, receipt_text.encode('utf-8'))
                    
                    # End print job
                    win32print.EndPagePrinter(hPrinter)
                    win32print.EndDocPrinter(hPrinter)
                    
                    self.logger.info(f"Receipt printed to {printer_name}")
                    return True
                    
                finally:
                    win32print.ClosePrinter(hPrinter)
                    
            else:
                # Linux/Unix - use lpr command
                import subprocess
                cmd = ['lpr']
                if printer_name:
                    cmd.extend(['-P', printer_name])
                
                process = subprocess.Popen(cmd, stdin=subprocess.PIPE)
                process.communicate(input=receipt_text.encode('utf-8'))
                
                if process.returncode == 0:
                    self.logger.info("Receipt printed successfully")
                    return True
                else:
                    self.logger.error("Failed to print receipt")
                    return False
                    
        except Exception as e:
            self.logger.error(f"Error printing receipt: {e}")
            return False
    
    def save_receipt_text(self, receipt_text: str, sale_id: str) -> str:
        """
        Save receipt text to file.
        
        Args:
            receipt_text: The receipt text to save
            sale_id: The sale ID for filename
            
        Returns:
            Path to saved file
        """
        try:
            receipts_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'receipts')
            os.makedirs(receipts_dir, exist_ok=True)
            
            filename = f"receipt_{sale_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            filepath = os.path.join(receipts_dir, filename)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(receipt_text)
            
            self.logger.info(f"Receipt saved: {filepath}")
            return filepath
            
        except Exception as e:
            self.logger.error(f"Error saving receipt: {e}")
            raise