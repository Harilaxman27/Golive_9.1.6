#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GoLive Studio - Centralized Error Handler
Provides consistent error handling, logging, and user notifications
"""

import sys
import traceback
import logging
from typing import Optional, Callable
from datetime import datetime
from pathlib import Path
from PyQt6.QtWidgets import QMessageBox, QWidget
from PyQt6.QtCore import QObject, pyqtSignal


class ErrorSeverity:
    """Error severity levels"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class ErrorHandler(QObject):
    """Centralized error handling and logging system"""
    
    error_occurred = pyqtSignal(str, str)  # severity, message
    
    def __init__(self, parent=None, log_dir: Optional[Path] = None):
        super().__init__(parent)
        
        # Setup logging directory
        if log_dir is None:
            if sys.platform == 'darwin':
                log_dir = Path.home() / 'Library' / 'Logs' / 'GoLive Studio'
            elif sys.platform.startswith('win'):
                import os
                log_dir = Path(os.environ.get('APPDATA', Path.home())) / 'GoLive Studio' / 'logs'
            else:
                log_dir = Path.home() / '.local' / 'share' / 'golive-studio' / 'logs'
        
        log_dir.mkdir(parents=True, exist_ok=True)
        
        # Setup file logging
        log_file = log_dir / f"golive_studio_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        
        # Configure logger
        self.logger = logging.getLogger('GoLiveStudio')
        self.logger.setLevel(logging.DEBUG)
        
        # File handler
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
        )
        file_handler.setFormatter(file_formatter)
        self.logger.addHandler(file_handler)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter('%(levelname)s: %(message)s')
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)
        
        self.log_file_path = log_file
        self.show_dialogs = True  # Can be disabled for testing
        
        self.logger.info(f"Error handler initialized. Log file: {log_file}")
    
    def handle_exception(self, 
                        exception: Exception,
                        severity: str = ErrorSeverity.ERROR,
                        context: str = "",
                        show_dialog: bool = True,
                        parent: Optional[QWidget] = None) -> None:
        """
        Handle an exception with logging and optional user notification
        
        Args:
            exception: The exception to handle
            severity: Error severity level
            context: Additional context about where the error occurred
            show_dialog: Whether to show a dialog to the user
            parent: Parent widget for the dialog
        """
        # Format error message
        error_msg = str(exception)
        full_context = f"{context}: {error_msg}" if context else error_msg
        
        # Log the error
        if severity == ErrorSeverity.CRITICAL:
            self.logger.critical(full_context, exc_info=True)
        elif severity == ErrorSeverity.ERROR:
            self.logger.error(full_context, exc_info=True)
        elif severity == ErrorSeverity.WARNING:
            self.logger.warning(full_context, exc_info=True)
        else:
            self.logger.info(full_context, exc_info=True)
        
        # Emit signal
        self.error_occurred.emit(severity, full_context)
        
        # Show dialog if requested
        if show_dialog and self.show_dialogs:
            self._show_error_dialog(severity, error_msg, context, parent)
    
    def log_error(self, message: str, severity: str = ErrorSeverity.ERROR, 
                  show_dialog: bool = False, parent: Optional[QWidget] = None) -> None:
        """
        Log an error message
        
        Args:
            message: Error message
            severity: Error severity level
            show_dialog: Whether to show a dialog to the user
            parent: Parent widget for the dialog
        """
        # Log based on severity
        if severity == ErrorSeverity.CRITICAL:
            self.logger.critical(message)
        elif severity == ErrorSeverity.ERROR:
            self.logger.error(message)
        elif severity == ErrorSeverity.WARNING:
            self.logger.warning(message)
        elif severity == ErrorSeverity.INFO:
            self.logger.info(message)
        else:
            self.logger.debug(message)
        
        # Emit signal
        self.error_occurred.emit(severity, message)
        
        # Show dialog if requested
        if show_dialog and self.show_dialogs:
            self._show_error_dialog(severity, message, "", parent)
    
    def _show_error_dialog(self, severity: str, message: str, 
                          context: str, parent: Optional[QWidget]) -> None:
        """Show error dialog to user"""
        try:
            # Determine dialog type
            if severity == ErrorSeverity.CRITICAL:
                icon = QMessageBox.Icon.Critical
                title = "Critical Error"
            elif severity == ErrorSeverity.ERROR:
                icon = QMessageBox.Icon.Critical
                title = "Error"
            elif severity == ErrorSeverity.WARNING:
                icon = QMessageBox.Icon.Warning
                title = "Warning"
            else:
                icon = QMessageBox.Icon.Information
                title = "Information"
            
            # Format message
            if context:
                full_message = f"{context}\n\n{message}"
            else:
                full_message = message
            
            # Show dialog
            msg_box = QMessageBox(parent)
            msg_box.setIcon(icon)
            msg_box.setWindowTitle(title)
            msg_box.setText(full_message)
            msg_box.setInformativeText(f"Check log file for details:\n{self.log_file_path}")
            msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
            msg_box.exec()
        except Exception as e:
            # Don't let dialog errors crash the app
            self.logger.error(f"Failed to show error dialog: {e}")
    
    def wrap_function(self, func: Callable, context: str = "", 
                     severity: str = ErrorSeverity.ERROR,
                     show_dialog: bool = True,
                     parent: Optional[QWidget] = None) -> Callable:
        """
        Wrap a function with error handling
        
        Args:
            func: Function to wrap
            context: Context description
            severity: Error severity for exceptions
            show_dialog: Whether to show dialogs on error
            parent: Parent widget for dialogs
            
        Returns:
            Wrapped function
        """
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                self.handle_exception(
                    e, 
                    severity=severity,
                    context=context or f"Error in {func.__name__}",
                    show_dialog=show_dialog,
                    parent=parent
                )
                return None
        
        wrapper.__name__ = func.__name__
        wrapper.__doc__ = func.__doc__
        return wrapper
    
    def get_log_file_path(self) -> Path:
        """Get the current log file path"""
        return self.log_file_path


# Global error handler instance
_error_handler: Optional[ErrorHandler] = None


def get_error_handler(parent=None) -> ErrorHandler:
    """Get or create the global error handler"""
    global _error_handler
    if _error_handler is None:
        _error_handler = ErrorHandler(parent)
    return _error_handler


def handle_exception(exception: Exception, context: str = "", 
                    severity: str = ErrorSeverity.ERROR,
                    show_dialog: bool = True,
                    parent: Optional[QWidget] = None) -> None:
    """Convenience function to handle exceptions"""
    handler = get_error_handler(parent)
    handler.handle_exception(exception, severity, context, show_dialog, parent)


def log_error(message: str, severity: str = ErrorSeverity.ERROR,
             show_dialog: bool = False, parent: Optional[QWidget] = None) -> None:
    """Convenience function to log errors"""
    handler = get_error_handler(parent)
    handler.log_error(message, severity, show_dialog, parent)
