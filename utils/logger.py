"""
Logging utilities for Hardware POS System

Provides centralized logging configuration and setup.
"""

import logging
import logging.handlers
import os
from pathlib import Path
from datetime import datetime


def setup_logger(log_level: str = "INFO", log_to_file: bool = True, 
                log_to_console: bool = True) -> None:
    """Setup the application logger.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_to_file: Whether to log to file
        log_to_console: Whether to log to console
    """
    # Create logs directory
    log_dir = Path(__file__).parent.parent / "logs"
    log_dir.mkdir(exist_ok=True)
    
    # Configure root logger
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, log_level.upper()))
    
    # Clear any existing handlers
    logger.handlers.clear()
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Console handler
    if log_to_console:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    
    # File handler with rotation
    if log_to_file:
        log_file = log_dir / "hardware_pos.log"
        file_handler = logging.handlers.RotatingFileHandler(
            log_file, maxBytes=10*1024*1024, backupCount=5  # 10MB max, 5 backups
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        
        # Error file handler
        error_log_file = log_dir / "errors.log"
        error_handler = logging.handlers.RotatingFileHandler(
            error_log_file, maxBytes=5*1024*1024, backupCount=3  # 5MB max, 3 backups
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(formatter)
        logger.addHandler(error_handler)


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance.
    
    Args:
        name: Logger name (usually __name__)
        
    Returns:
        Logger instance
    """
    return logging.getLogger(name)


class ContextLogger:
    """Logger with context information."""
    
    def __init__(self, logger_name: str, context: dict = None):
        """Initialize context logger.
        
        Args:
            logger_name: Logger name
            context: Context information to include in logs
        """
        self.logger = logging.getLogger(logger_name)
        self.context = context or {}
    
    def _format_message(self, message: str) -> str:
        """Format message with context.
        
        Args:
            message: Log message
            
        Returns:
            Formatted message with context
        """
        if self.context:
            context_str = " | ".join([f"{k}={v}" for k, v in self.context.items()])
            return f"[{context_str}] {message}"
        return message
    
    def debug(self, message: str, *args, **kwargs):
        """Log debug message."""
        self.logger.debug(self._format_message(message), *args, **kwargs)
    
    def info(self, message: str, *args, **kwargs):
        """Log info message."""
        self.logger.info(self._format_message(message), *args, **kwargs)
    
    def warning(self, message: str, *args, **kwargs):
        """Log warning message."""
        self.logger.warning(self._format_message(message), *args, **kwargs)
    
    def error(self, message: str, *args, **kwargs):
        """Log error message."""
        self.logger.error(self._format_message(message), *args, **kwargs)
    
    def critical(self, message: str, *args, **kwargs):
        """Log critical message."""
        self.logger.critical(self._format_message(message), *args, **kwargs)
    
    def exception(self, message: str, *args, **kwargs):
        """Log exception with traceback."""
        self.logger.exception(self._format_message(message), *args, **kwargs)


def audit_log(action: str, user_id: int = None, details: dict = None) -> None:
    """Log audit events.
    
    Args:
        action: Action performed
        user_id: User ID performing the action
        details: Additional details
    """
    audit_logger = logging.getLogger("audit")
    
    audit_info = {
        "action": action,
        "user_id": user_id,
        "timestamp": datetime.now().isoformat(),
        "details": details or {}
    }
    
    audit_logger.info(f"AUDIT: {audit_info}")


def performance_log(operation: str, duration: float, details: dict = None) -> None:
    """Log performance metrics.
    
    Args:
        operation: Operation name
        duration: Duration in seconds
        details: Additional details
    """
    perf_logger = logging.getLogger("performance")
    
    perf_info = {
        "operation": operation,
        "duration": round(duration, 4),
        "timestamp": datetime.now().isoformat(),
        "details": details or {}
    }
    
    perf_logger.info(f"PERFORMANCE: {perf_info}")


def security_log(event: str, user_id: int = None, ip_address: str = None, 
                details: dict = None) -> None:
    """Log security events.
    
    Args:
        event: Security event
        user_id: User ID involved
        ip_address: IP address
        details: Additional details
    """
    security_logger = logging.getLogger("security")
    
    security_info = {
        "event": event,
        "user_id": user_id,
        "ip_address": ip_address,
        "timestamp": datetime.now().isoformat(),
        "details": details or {}
    }
    
    security_logger.warning(f"SECURITY: {security_info}")
