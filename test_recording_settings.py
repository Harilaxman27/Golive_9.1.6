#!/usr/bin/env python3
"""
Test script for Recording Settings Dialog
"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

from PyQt6.QtWidgets import QApplication, QPushButton, QVBoxLayout, QWidget, QLabel
from PyQt6.QtCore import Qt
from recording_settings_dialog import RecordingSettingsDialog

class TestWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("🎥 Test Recording Settings")
        self.setGeometry(100, 100, 400, 200)
        
        layout = QVBoxLayout()
        
        label = QLabel("Click the button to test Recording Settings Dialog:")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(label)
        
        test_btn = QPushButton("🎥 Open Recording Settings")
        test_btn.clicked.connect(self.test_recording_settings)
        layout.addWidget(test_btn)
        
        self.result_label = QLabel("No settings tested yet")
        self.result_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.result_label.setStyleSheet("color: gray; font-style: italic;")
        layout.addWidget(self.result_label)
        
        self.setLayout(layout)
    
    def test_recording_settings(self):
        try:
            # Test the recording settings dialog
            dialog = RecordingSettingsDialog(self, initial_path="/tmp/test_recording.mp4", include_audio=True)
            
            if dialog.exec():
                # User clicked Save & Close
                path, audio = dialog.get_values()
                advanced = dialog.get_advanced_settings()
                
                result_text = f"✅ Settings saved!\n"
                result_text += f"📁 Path: {path}\n"
                result_text += f"🎧 Audio: {'Yes' if audio else 'No'}\n"
                result_text += f"🎬 Format: {advanced.get('format', 'Unknown')}\n"
                result_text += f"⭐ Quality: CRF {advanced.get('crf', 'Unknown')}"
                
                self.result_label.setText(result_text)
                self.result_label.setStyleSheet("color: green;")
            else:
                # User clicked Cancel
                self.result_label.setText("❌ Settings cancelled")
                self.result_label.setStyleSheet("color: orange;")
                
        except Exception as e:
            self.result_label.setText(f"❌ Error: {str(e)}")
            self.result_label.setStyleSheet("color: red;")
            print(f"Recording settings test error: {e}")
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
    
    window = TestWindow()
    window.show()
    
    print("✅ Recording Settings Test Window opened")
    print("Click the button to test the Recording Settings Dialog")
    
    sys.exit(app.exec())
