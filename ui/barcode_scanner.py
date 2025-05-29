"""
Barcode Scanner Integration for Hardware POS System

Provides barcode scanning functionality using USB barcode scanners.
"""

import logging
import threading
import time
from typing import Callable, Optional, Dict, Any
from PyQt5.QtCore import QObject, pyqtSignal, QTimer, QThread
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit, QMessageBox

from utils.logger import get_logger


class BarcodeScannerWorker(QThread):
    """Worker thread for barcode scanning."""
    
    barcode_scanned = pyqtSignal(str)
    error_occurred = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.logger = get_logger(__name__)
        self.running = False
        self.scan_buffer = ""
        self.last_scan_time = 0
        self.scan_timeout = 100  # 100ms timeout between characters
        
    def start_scanning(self):
        """Start the barcode scanning process."""
        self.running = True
        self.start()
        
    def stop_scanning(self):
        """Stop the barcode scanning process."""
        self.running = False
        self.quit()
        self.wait()
        
    def run(self):
        """Main scanning loop."""
        self.logger.info("Barcode scanner worker started")
        
        while self.running:
            try:
                # In a real implementation, this would interface with actual scanner hardware
                # For now, we'll simulate by monitoring keyboard input patterns
                self.msleep(10)  # Small delay to prevent high CPU usage
                
            except Exception as e:
                self.error_occurred.emit(f"Scanner error: {str(e)}")
                self.logger.error(f"Barcode scanner error: {e}")
                
        self.logger.info("Barcode scanner worker stopped")
        
    def process_character(self, char: str):
        """Process a character from input stream."""
        current_time = time.time() * 1000  # Convert to milliseconds
        
        # If too much time has passed, reset buffer
        if current_time - self.last_scan_time > self.scan_timeout:
            self.scan_buffer = ""
            
        self.scan_buffer += char
        self.last_scan_time = current_time
        
        # Check if this looks like a complete barcode (ends with Enter/Return)
        if char in ['\r', '\n'] and len(self.scan_buffer) > 1:
            barcode = self.scan_buffer.rstrip('\r\n')
            if len(barcode) >= 4:  # Minimum barcode length
                self.barcode_scanned.emit(barcode)
                self.logger.info(f"Barcode scanned: {barcode}")
            self.scan_buffer = ""


class BarcodeInputWidget(QWidget):
    """Widget for barcode input with scanning support."""
    
    barcode_entered = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.logger = get_logger(__name__)
        self.scanner_worker = None
        self.setup_ui()
        self.setup_scanner()
        
    def setup_ui(self):
        """Setup the UI components."""
        layout = QVBoxLayout(self)
        
        # Title
        title_label = QLabel("Barcode Scanner")
        title_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(title_label)
        
        # Input section
        input_layout = QHBoxLayout()
        
        self.barcode_input = QLineEdit()
        self.barcode_input.setPlaceholderText("Scan barcode or enter manually...")
        self.barcode_input.returnPressed.connect(self.process_manual_input)
        input_layout.addWidget(self.barcode_input)
        
        self.scan_button = QPushButton("Manual Entry")
        self.scan_button.clicked.connect(self.process_manual_input)
        input_layout.addWidget(self.scan_button)
        
        layout.addLayout(input_layout)
        
        # Status section
        status_layout = QHBoxLayout()
        
        self.status_label = QLabel("Ready for scanning")
        self.status_label.setStyleSheet("color: green;")
        status_layout.addWidget(self.status_label)
        
        self.scanner_toggle = QPushButton("Start Scanner")
        self.scanner_toggle.clicked.connect(self.toggle_scanner)
        status_layout.addWidget(self.scanner_toggle)
        
        layout.addLayout(status_layout)
        
        # Recent scans
        self.recent_label = QLabel("Last scan: None")
        self.recent_label.setStyleSheet("color: gray; font-size: 12px;")
        layout.addWidget(self.recent_label)
        
    def setup_scanner(self):
        """Setup the barcode scanner worker."""
        self.scanner_worker = BarcodeScannerWorker()
        self.scanner_worker.barcode_scanned.connect(self.on_barcode_scanned)
        self.scanner_worker.error_occurred.connect(self.on_scanner_error)
        
    def toggle_scanner(self):
        """Toggle scanner on/off."""
        if not self.scanner_worker:
            return
            
        if self.scanner_worker.running:
            self.stop_scanner()
        else:
            self.start_scanner()
            
    def start_scanner(self):
        """Start the barcode scanner."""
        try:
            if self.scanner_worker and not self.scanner_worker.running:
                self.scanner_worker.start_scanning()
                self.status_label.setText("Scanner active - Ready to scan")
                self.status_label.setStyleSheet("color: green;")
                self.scanner_toggle.setText("Stop Scanner")
                self.logger.info("Barcode scanner started")
                
        except Exception as e:
            self.logger.error(f"Failed to start scanner: {e}")
            self.status_label.setText(f"Scanner error: {str(e)}")
            self.status_label.setStyleSheet("color: red;")
            
    def stop_scanner(self):
        """Stop the barcode scanner."""
        try:
            if self.scanner_worker and self.scanner_worker.running:
                self.scanner_worker.stop_scanning()
                self.status_label.setText("Scanner stopped")
                self.status_label.setStyleSheet("color: orange;")
                self.scanner_toggle.setText("Start Scanner")
                self.logger.info("Barcode scanner stopped")
                
        except Exception as e:
            self.logger.error(f"Failed to stop scanner: {e}")
            
    def process_manual_input(self):
        """Process manually entered barcode."""
        barcode = self.barcode_input.text().strip()
        if barcode:
            self.on_barcode_scanned(barcode)
            self.barcode_input.clear()
            
    def on_barcode_scanned(self, barcode: str):
        """Handle scanned barcode."""
        self.logger.info(f"Barcode received: {barcode}")
        self.recent_label.setText(f"Last scan: {barcode}")
        self.barcode_entered.emit(barcode)
        
        # Visual feedback
        self.barcode_input.setText(barcode)
        QTimer.singleShot(1000, self.barcode_input.clear)  # Clear after 1 second
        
    def on_scanner_error(self, error_message: str):
        """Handle scanner errors."""
        self.logger.error(f"Scanner error: {error_message}")
        self.status_label.setText(f"Error: {error_message}")
        self.status_label.setStyleSheet("color: red;")
        
    def closeEvent(self, event):
        """Handle widget close event."""
        if self.scanner_worker:
            self.stop_scanner()
        event.accept()


class BarcodeValidator:
    """Validates and formats barcodes."""
    
    @staticmethod
    def validate_barcode(barcode: str) -> Dict[str, Any]:
        """Validate a barcode and return information about it.
        
        Args:
            barcode: The barcode string to validate
            
        Returns:
            Dictionary with validation results
        """
        result = {
            'valid': False,
            'barcode': barcode,
            'type': 'unknown',
            'length': len(barcode),
            'errors': []
        }
        
        # Remove any whitespace
        barcode = barcode.strip()
        result['barcode'] = barcode
        result['length'] = len(barcode)
        
        if not barcode:
            result['errors'].append("Barcode is empty")
            return result
            
        # Check for valid characters (digits only for most barcode types)
        if not barcode.isdigit():
            result['errors'].append("Barcode contains non-digit characters")
            
        # Determine barcode type based on length
        length = len(barcode)
        if length == 8:
            result['type'] = 'EAN-8'
        elif length == 13:
            result['type'] = 'EAN-13'
        elif length == 12:
            result['type'] = 'UPC-A'
        elif length in [6, 7, 8]:
            result['type'] = 'UPC-E'
        elif length in range(4, 25):  # Code 128 can vary
            result['type'] = 'Code 128'
        else:
            result['type'] = f'Custom ({length} digits)'
            
        # Basic validation passed if no errors and reasonable length
        if not result['errors'] and 4 <= length <= 30:
            result['valid'] = True
            
        return result
    
    @staticmethod
    def format_barcode(barcode: str, barcode_type: str = None) -> str:
        """Format barcode for display.
        
        Args:
            barcode: The barcode string
            barcode_type: Optional barcode type
            
        Returns:
            Formatted barcode string
        """
        barcode = barcode.strip()
        
        # Add formatting based on type
        if barcode_type == 'EAN-13' and len(barcode) == 13:
            # Format as 1 234567 890123
            return f"{barcode[0]} {barcode[1:7]} {barcode[7:]}"
        elif barcode_type == 'EAN-8' and len(barcode) == 8:
            # Format as 1234 5678
            return f"{barcode[:4]} {barcode[4:]}"
        elif barcode_type == 'UPC-A' and len(barcode) == 12:
            # Format as 1 23456 78901 2
            return f"{barcode[0]} {barcode[1:6]} {barcode[6:11]} {barcode[11]}"
            
        return barcode


# Example usage and testing
if __name__ == "__main__":
    import sys
    from PyQt5.QtWidgets import QApplication, QMainWindow
    
    class TestWindow(QMainWindow):
        def __init__(self):
            super().__init__()
            self.setWindowTitle("Barcode Scanner Test")
            self.setGeometry(100, 100, 400, 300)
            
            self.scanner_widget = BarcodeInputWidget()
            self.scanner_widget.barcode_entered.connect(self.on_barcode_received)
            self.setCentralWidget(self.scanner_widget)
            
        def on_barcode_received(self, barcode):
            validation = BarcodeValidator.validate_barcode(barcode)
            formatted = BarcodeValidator.format_barcode(barcode, validation['type'])
            
            print(f"Barcode received: {barcode}")
            print(f"Validation: {validation}")
            print(f"Formatted: {formatted}")
            
    app = QApplication(sys.argv)
    window = TestWindow()
    window.show()
    sys.exit(app.exec_())
