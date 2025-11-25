#!/usr/bin/env python3
"""
Test script for all Settings Dialogs
"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

from PyQt6.QtWidgets import QApplication, QPushButton, QVBoxLayout, QWidget, QLabel
from PyQt6.QtCore import Qt

class TestSettingsWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("🔧 Test Settings Dialogs")
        self.setGeometry(100, 100, 400, 300)
        
        layout = QVBoxLayout()
        
        label = QLabel("Click buttons to test each settings dialog:")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(label)
        
        # Input Settings Test
        input_btn = QPushButton("📹 Test Input Settings Dialog")
        input_btn.clicked.connect(self.test_input_settings)
        layout.addWidget(input_btn)
        
        # Recording Settings Test
        record_btn = QPushButton("🎥 Test Recording Settings Dialog")
        record_btn.clicked.connect(self.test_recording_settings)
        layout.addWidget(record_btn)
        
        # Stream Settings Test
        stream_btn = QPushButton("🎬 Test Stream Settings Dialog")
        stream_btn.clicked.connect(self.test_stream_settings)
        layout.addWidget(stream_btn)
        
        # Media Settings Test
        media_btn = QPushButton("🎞️ Test Media Settings Dialog")
        media_btn.clicked.connect(self.test_media_settings)
        layout.addWidget(media_btn)
        
        self.result_label = QLabel("No dialogs tested yet")
        self.result_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.result_label.setStyleSheet("color: gray; font-style: italic;")
        layout.addWidget(self.result_label)
        
        self.setLayout(layout)
    
    def test_input_settings(self):
        try:
            print("Testing Input Settings Dialog...")
            from input_settings_dialog import InputSettingsDialog
            dialog = InputSettingsDialog(self, 1)
            
            if dialog.exec():
                self.result_label.setText("✅ Input Settings Dialog - OK")
                self.result_label.setStyleSheet("color: green;")
            else:
                self.result_label.setText("❌ Input Settings Dialog - Cancelled")
                self.result_label.setStyleSheet("color: orange;")
                
        except Exception as e:
            self.result_label.setText(f"❌ Input Settings Error: {str(e)}")
            self.result_label.setStyleSheet("color: red;")
            print(f"Input settings error: {e}")
            import traceback
            traceback.print_exc()
    
    def test_recording_settings(self):
        try:
            print("Testing Recording Settings Dialog...")
            from recording_settings_dialog import RecordingSettingsDialog
            dialog = RecordingSettingsDialog(self, initial_path="/tmp/test.mp4", include_audio=True)
            
            if dialog.exec():
                self.result_label.setText("✅ Recording Settings Dialog - OK")
                self.result_label.setStyleSheet("color: green;")
            else:
                self.result_label.setText("❌ Recording Settings Dialog - Cancelled")
                self.result_label.setStyleSheet("color: orange;")
                
        except Exception as e:
            self.result_label.setText(f"❌ Recording Settings Error: {str(e)}")
            self.result_label.setStyleSheet("color: red;")
            print(f"Recording settings error: {e}")
            import traceback
            traceback.print_exc()
    
    def test_stream_settings(self):
        try:
            print("Testing Stream Settings Dialog...")
            from streaming_settings_dialog_improved import StreamingSettingsDialog
            from config import app_config
            dialog = StreamingSettingsDialog(self, 1, app_config)
            
            if dialog.exec():
                self.result_label.setText("✅ Stream Settings Dialog - OK")
                self.result_label.setStyleSheet("color: green;")
            else:
                self.result_label.setText("❌ Stream Settings Dialog - Cancelled")
                self.result_label.setStyleSheet("color: orange;")
                
        except Exception as e:
            self.result_label.setText(f"❌ Stream Settings Error: {str(e)}")
            self.result_label.setStyleSheet("color: red;")
            print(f"Stream settings error: {e}")
            import traceback
            traceback.print_exc()
    
    def test_media_settings(self):
        try:
            print("Testing Media Settings Dialog...")
            from media_settings_dialog import MediaSettingsDialog
            dialog = MediaSettingsDialog(self, 1, "/tmp/test.mp4")
            
            if dialog.exec():
                self.result_label.setText("✅ Media Settings Dialog - OK")
                self.result_label.setStyleSheet("color: green;")
            else:
                self.result_label.setText("❌ Media Settings Dialog - Cancelled")
                self.result_label.setStyleSheet("color: orange;")
                
        except Exception as e:
            self.result_label.setText(f"❌ Media Settings Error: {str(e)}")
            self.result_label.setStyleSheet("color: red;")
            print(f"Media settings error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Set dark theme
    app.setStyleSheet("""
        QWidget {
            background-color: #2d2d2d;
            color: #e0e0e0;
        }
        QPushButton {
            background-color: #3a7ca5;
            color: white;
            border: none;
            border-radius: 6px;
            padding: 10px;
            font-weight: bold;
        }
        QPushButton:hover {
            background-color: #4a8cb5;
        }
    """)
    
    window = TestSettingsWindow()
    window.show()
    
    print("✅ Settings Dialog Test Window opened")
    print("Click buttons to test each settings dialog")
    
    sys.exit(app.exec())
