#!/usr/bin/env python3
"""
GoLive Studio - Simple Launcher
Bypasses complex initialization to test core functionality.
"""
import sys
import os

# Change to project root
script_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(script_dir)
sys.path.insert(0, script_dir)

print("\n" + "="*70)
print("GoLive Studio - Minimal Launcher")
print("="*70)
print(f"Python: {sys.version}")
print(f"CWD: {os.getcwd()}\n")

try:
    print("[STEP 1] Importing PyQt6...")
    from PyQt6.QtWidgets import QApplication, QMainWindow, QPushButton, QVBoxLayout, QWidget
    from PyQt6.QtCore import Qt
    print("[STEP 1] ✓ PyQt6 imported\n")
    
    print("[STEP 2] Creating QApplication...")
    app = QApplication(sys.argv)
    print("[STEP 2] ✓ QApplication created\n")
    
    print("[STEP 3] Creating main window...")
    
    class SimpleWindow(QMainWindow):
        def __init__(self):
            super().__init__()
            self.setWindowTitle("GoLive Studio - Test Window")
            self.setGeometry(100, 100, 600, 400)
            
            # Central widget
            central = QWidget()
            layout = QVBoxLayout(central)
            
            # Test button
            btn = QPushButton("GoLive Studio is Running!")
            btn.clicked.connect(self.test_click)
            layout.addWidget(btn)
            
            self.setCentralWidget(central)
        
        def test_click(self):
            print("[APP] Button clicked - app is responsive!")
    
    window = SimpleWindow()
    print("[STEP 3] ✓ Main window created\n")
    
    print("[STEP 4] Showing window...")
    window.show()
    print("[STEP 4] ✓ Window shown\n")
    
    print("="*70)
    print("GoLive Studio Launcher Ready!")
    print("Window should be visible. Click the button to test responsiveness.")
    print("="*70 + "\n")
    
    # Start event loop
    sys.exit(app.exec())

except Exception as e:
    print(f"\n[ERROR] {type(e).__name__}: {e}\n")
    import traceback
    traceback.print_exc()
    sys.exit(1)
