#!/usr/bin/env python3
"""
Test script for Text Overlay functionality
"""

import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QLabel
from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtCore import Qt

# Test the text overlay renderer
def test_text_overlay():
    app = QApplication(sys.argv)
    
    # Create test window
    window = QMainWindow()
    window.setWindowTitle("Text Overlay Test")
    window.setGeometry(100, 100, 800, 600)
    
    central_widget = QWidget()
    window.setCentralWidget(central_widget)
    layout = QVBoxLayout(central_widget)
    
    # Create preview label
    preview_label = QLabel()
    preview_label.setMinimumSize(400, 300)
    preview_label.setStyleSheet("border: 1px solid gray;")
    layout.addWidget(preview_label)
    
    # Test button
    test_btn = QPushButton("Test Text Overlay")
    layout.addWidget(test_btn)
    
    def test_overlay():
        try:
            from text_overlay_renderer import text_overlay_renderer
            
            # Set up test settings
            test_settings = {
                'text': 'Hello, GoLive Studio!',
                'font_family': 'Arial',
                'font_size': 48,
                'bold': True,
                'italic': False,
                'underline': False,
                'text_color': '#ffffff',
                'position_x': 50,
                'position_y': 20,
                'alignment': 'center',
                'bg_enabled': True,
                'bg_color': '#000080',
                'bg_opacity': 0.7,
                'outline_enabled': True,
                'outline_width': 2,
                'shadow_enabled': True,
            }
            
            # Apply settings
            text_overlay_renderer.update_settings(test_settings)
            
            # Generate preview
            preview_image = text_overlay_renderer.get_preview_image(400, 300)
            
            # Display in label
            pixmap = QPixmap.fromImage(preview_image)
            preview_label.setPixmap(pixmap)
            
            print("✅ Text overlay test successful!")
            
        except Exception as e:
            print(f"❌ Text overlay test failed: {e}")
            import traceback
            traceback.print_exc()
    
    test_btn.clicked.connect(test_overlay)
    
    window.show()
    
    # Run initial test
    test_overlay()
    
    return app.exec()

if __name__ == "__main__":
    sys.exit(test_text_overlay())
