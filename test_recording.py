#!/usr/bin/env python3
"""
Test script to verify recording frame capture
"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QSize, QTimer
from PyQt6.QtGui import QImage
from recording import RecorderController

class TestFrameProvider:
    def __init__(self):
        self.frame_count = 0
        
    def __call__(self, size: QSize) -> QImage:
        """Generate a test frame with frame number"""
        self.frame_count += 1
        
        # Create a simple test image with frame number
        img = QImage(size, QImage.Format.Format_RGBA8888)
        
        # Fill with different colors based on frame number
        colors = [
            (255, 0, 0, 255),    # Red
            (0, 255, 0, 255),    # Green  
            (0, 0, 255, 255),    # Blue
            (255, 255, 0, 255),  # Yellow
            (255, 0, 255, 255),  # Magenta
        ]
        
        color = colors[self.frame_count % len(colors)]
        img.fill(color[0] << 24 | color[1] << 16 | color[2] << 8 | color[3])
        
        print(f"Generated test frame #{self.frame_count} - Color: {color}")
        return img

def test_recording():
    app = QApplication(sys.argv)
    
    print("🎬 Testing Recording System")
    print("=" * 40)
    
    # Create recorder
    recorder = RecorderController()
    
    # Set up frame provider
    frame_provider = TestFrameProvider()
    recorder.set_frame_provider(frame_provider)
    
    # Set up logging
    def log_callback(message):
        print(f"[RECORDER] {message.strip()}")
    recorder.on_log(log_callback)
    
    # Test settings
    settings = {
        'file_path': '/Users/rohithpavan/Desktop/test_recording.mp4',
        'width': 640,
        'height': 480,
        'fps': 10,  # Lower FPS for testing
        'bitrate_kbps': 1000,
        'video_preset': 'ultrafast',
        'capture_audio': False,
        'audio_device': '',
        'program_media_audio_path': '',
    }
    
    try:
        print("🚀 Starting test recording...")
        recorder.start(settings)
        
        # Record for 5 seconds
        def stop_recording():
            print("🛑 Stopping test recording...")
            recorder.stop()
            app.quit()
        
        QTimer.singleShot(5000, stop_recording)  # Stop after 5 seconds
        
        print("⏰ Recording for 5 seconds...")
        app.exec()
        
        print("✅ Test completed")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_recording()
