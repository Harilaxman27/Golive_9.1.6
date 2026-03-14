#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GoLive Studio - Screen Capture Module
Cross-platform screen and window capture functionality
"""

import sys
from typing import List, Optional, Tuple
from dataclasses import dataclass
from PyQt6.QtCore import QObject, pyqtSignal, QTimer, QRect
from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtWidgets import QApplication


@dataclass
class CaptureSource:
    """Represents a capture source (screen or window)"""
    id: str
    name: str
    source_type: str  # 'screen' or 'window'
    geometry: QRect = None  # Screen/window geometry
    
    def __str__(self) -> str:
        return f"{self.name} ({self.source_type})"


class ScreenCapture(QObject):
    """Cross-platform screen and window capture"""
    
    frame_captured = pyqtSignal(QImage)  # Emitted when frame is captured
    error_occurred = pyqtSignal(str)     # Emitted on error
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self._capturing = False
        self._capture_timer = QTimer(self)
        self._capture_timer.timeout.connect(self._capture_frame)
        
        self._current_source: Optional[CaptureSource] = None
        self._fps = 30
        self._capture_cursor = True
        
        # Platform-specific backend
        self._backend = self._init_backend()
    
    def _init_backend(self) -> str:
        """Determine capture backend based on platform"""
        if sys.platform == 'darwin':
            return 'quartz'  # macOS Quartz/CoreGraphics
        elif sys.platform.startswith('win'):
            return 'win32'  # Windows GDI/DXGI
        else:
            return 'x11'  # Linux X11
    
    def get_available_screens(self) -> List[CaptureSource]:
        """
        Get list of available screens
        
        Returns:
            List of screen capture sources
        """
        screens = []
        app = QApplication.instance()
        
        if app:
            for i, screen in enumerate(app.screens()):
                geometry = screen.geometry()
                source = CaptureSource(
                    id=f"screen_{i}",
                    name=f"Screen {i + 1} ({screen.name()})",
                    source_type='screen',
                    geometry=geometry
                )
                screens.append(source)
        
        return screens
    
    def get_available_windows(self) -> List[CaptureSource]:
        """
        Get list of available windows
        
        Returns:
            List of window capture sources
        """
        if sys.platform == 'darwin':
            return self._get_windows_macos()
        elif sys.platform.startswith('win'):
            return self._get_windows_windows()
        else:
            return self._get_windows_linux()
    
    def _get_windows_macos(self) -> List[CaptureSource]:
        """Get windows on macOS using CoreGraphics"""
        windows = []
        
        try:
            from Quartz import CGWindowListCopyWindowInfo, kCGWindowListOptionOnScreenOnly, kCGNullWindowID
            
            window_list = CGWindowListCopyWindowInfo(
                kCGWindowListOptionOnScreenOnly,
                kCGNullWindowID
            )
            
            for i, window in enumerate(window_list):
                # Get window info
                window_name = window.get('kCGWindowName', '')
                owner_name = window.get('kCGWindowOwnerName', '')
                window_id = window.get('kCGWindowNumber', 0)
                
                # Skip windows without names
                if not window_name and not owner_name:
                    continue
                
                # Get geometry
                bounds = window.get('kCGWindowBounds', {})
                geometry = QRect(
                    int(bounds.get('X', 0)),
                    int(bounds.get('Y', 0)),
                    int(bounds.get('Width', 0)),
                    int(bounds.get('Height', 0))
                )
                
                display_name = f"{owner_name}: {window_name}" if window_name else owner_name
                
                source = CaptureSource(
                    id=f"window_{window_id}",
                    name=display_name,
                    source_type='window',
                    geometry=geometry
                )
                windows.append(source)
        
        except ImportError:
            self.error_occurred.emit("pyobjc-framework-Quartz not installed")
        except Exception as e:
            self.error_occurred.emit(f"Error listing windows: {e}")
        
        return windows
    
    def _get_windows_windows(self) -> List[CaptureSource]:
        """Get windows on Windows using win32gui"""
        windows = []
        
        try:
            import win32gui
            import win32con
            
            def enum_callback(hwnd, results):
                if win32gui.IsWindowVisible(hwnd):
                    title = win32gui.GetWindowText(hwnd)
                    if title:  # Only include windows with titles
                        rect = win32gui.GetWindowRect(hwnd)
                        geometry = QRect(rect[0], rect[1], rect[2] - rect[0], rect[3] - rect[1])
                        
                        source = CaptureSource(
                            id=f"window_{hwnd}",
                            name=title,
                            source_type='window',
                            geometry=geometry
                        )
                        results.append(source)
            
            win32gui.EnumWindows(enum_callback, windows)
        
        except ImportError:
            self.error_occurred.emit("pywin32 not installed")
        except Exception as e:
            self.error_occurred.emit(f"Error listing windows: {e}")
        
        return windows
    
    def _get_windows_linux(self) -> List[CaptureSource]:
        """Get windows on Linux using X11"""
        windows = []
        
        try:
            from Xlib import X, display
            
            d = display.Display()
            root = d.screen().root
            
            # Get window tree
            window_ids = root.get_full_property(
                d.intern_atom('_NET_CLIENT_LIST'),
                X.AnyPropertyType
            )
            
            if window_ids:
                for window_id in window_ids.value:
                    try:
                        window = d.create_resource_object('window', window_id)
                        
                        # Get window name
                        name_atom = d.intern_atom('_NET_WM_NAME')
                        name_prop = window.get_full_property(name_atom, 0)
                        
                        if name_prop:
                            name = name_prop.value.decode('utf-8', errors='ignore')
                            
                            # Get geometry
                            geom = window.get_geometry()
                            geometry = QRect(geom.x, geom.y, geom.width, geom.height)
                            
                            source = CaptureSource(
                                id=f"window_{window_id}",
                                name=name,
                                source_type='window',
                                geometry=geometry
                            )
                            windows.append(source)
                    except Exception:
                        continue
        
        except ImportError:
            self.error_occurred.emit("python-xlib not installed")
        except Exception as e:
            self.error_occurred.emit(f"Error listing windows: {e}")
        
        return windows
    
    def start_capture(self, source: CaptureSource, fps: int = 30) -> bool:
        """
        Start capturing from source
        
        Args:
            source: Capture source (screen or window)
            fps: Capture frame rate
            
        Returns:
            True if capture started successfully
        """
        try:
            self._current_source = source
            self._fps = fps
            
            # Start capture timer
            interval = int(1000 / fps)
            self._capture_timer.start(interval)
            self._capturing = True
            
            return True
        except Exception as e:
            self.error_occurred.emit(f"Failed to start capture: {e}")
            return False
    
    def stop_capture(self):
        """Stop capturing"""
        self._capture_timer.stop()
        self._capturing = False
        self._current_source = None
    
    def is_capturing(self) -> bool:
        """Check if currently capturing"""
        return self._capturing
    
    def set_capture_cursor(self, enabled: bool):
        """Enable/disable cursor capture"""
        self._capture_cursor = enabled
    
    def _capture_frame(self):
        """Capture a single frame"""
        if not self._current_source:
            return
        
        try:
            if self._current_source.source_type == 'screen':
                image = self._capture_screen(self._current_source)
            else:  # window
                image = self._capture_window(self._current_source)
            
            if image and not image.isNull():
                self.frame_captured.emit(image)
        except Exception as e:
            self.error_occurred.emit(f"Capture error: {e}")
    
    def _capture_screen(self, source: CaptureSource) -> Optional[QImage]:
        """Capture entire screen"""
        try:
            app = QApplication.instance()
            if not app:
                return None
            
            # Get screen by index
            screen_index = int(source.id.split('_')[1])
            if screen_index < len(app.screens()):
                screen = app.screens()[screen_index]
                pixmap = screen.grabWindow(0)  # 0 = desktop window
                return pixmap.toImage()
        except Exception as e:
            self.error_occurred.emit(f"Screen capture error: {e}")
        
        return None
    
    def _capture_window(self, source: CaptureSource) -> Optional[QImage]:
        """Capture specific window"""
        if sys.platform == 'darwin':
            return self._capture_window_macos(source)
        elif sys.platform.startswith('win'):
            return self._capture_window_windows(source)
        else:
            return self._capture_window_linux(source)
    
    def _capture_window_macos(self, source: CaptureSource) -> Optional[QImage]:
        """Capture window on macOS"""
        try:
            from Quartz import CGWindowListCreateImage, kCGWindowListOptionIncludingWindow, kCGWindowImageDefault, CGRectNull
            from CoreFoundation import CFDataGetBytePtr, CFDataGetLength
            
            # Extract window ID
            window_id = int(source.id.split('_')[1])
            
            # Capture window
            image_ref = CGWindowListCreateImage(
                CGRectNull,
                kCGWindowListOptionIncludingWindow,
                window_id,
                kCGWindowImageDefault
            )
            
            if image_ref:
                # Convert to QImage
                # (Simplified - full implementation would handle pixel format conversion)
                return QImage()  # Placeholder
        except Exception as e:
            self.error_occurred.emit(f"macOS window capture error: {e}")
        
        return None
    
    def _capture_window_windows(self, source: CaptureSource) -> Optional[QImage]:
        """Capture window on Windows"""
        try:
            import win32gui
            import win32ui
            import win32con
            from PIL import Image
            
            # Extract window handle
            hwnd = int(source.id.split('_')[1])
            
            # Get window DC
            hwndDC = win32gui.GetWindowDC(hwnd)
            mfcDC = win32ui.CreateDCFromHandle(hwndDC)
            saveDC = mfcDC.CreateCompatibleDC()
            
            # Get window size
            left, top, right, bottom = win32gui.GetWindowRect(hwnd)
            width = right - left
            height = bottom - top
            
            # Create bitmap
            saveBitMap = win32ui.CreateBitmap()
            saveBitMap.CreateCompatibleBitmap(mfcDC, width, height)
            saveDC.SelectObject(saveBitMap)
            
            # Copy window content
            saveDC.BitBlt((0, 0), (width, height), mfcDC, (0, 0), win32con.SRCCOPY)
            
            # Convert to QImage
            bmpinfo = saveBitMap.GetInfo()
            bmpstr = saveBitMap.GetBitmapBits(True)
            
            img = Image.frombuffer(
                'RGB',
                (bmpinfo['bmWidth'], bmpinfo['bmHeight']),
                bmpstr,
                'raw',
                'BGRX',
                0,
                1
            )
            
            # Convert PIL Image to QImage
            # (Simplified - full implementation needed)
            return QImage()  # Placeholder
        
        except Exception as e:
            self.error_occurred.emit(f"Windows window capture error: {e}")
        
        return None
    
    def _capture_window_linux(self, source: CaptureSource) -> Optional[QImage]:
        """Capture window on Linux"""
        try:
            from Xlib import X, display
            from PIL import Image
            
            d = display.Display()
            window_id = int(source.id.split('_')[1])
            window = d.create_resource_object('window', window_id)
            
            # Get window geometry
            geom = window.get_geometry()
            
            # Capture window
            raw = window.get_image(0, 0, geom.width, geom.height, X.ZPixmap, 0xffffffff)
            
            # Convert to QImage
            # (Simplified - full implementation needed)
            return QImage()  # Placeholder
        
        except Exception as e:
            self.error_occurred.emit(f"Linux window capture error: {e}")
        
        return None


# Global screen capture instance
_screen_capture: Optional[ScreenCapture] = None


def get_screen_capture() -> ScreenCapture:
    """Get or create global screen capture instance"""
    global _screen_capture
    if _screen_capture is None:
        _screen_capture = ScreenCapture()
    return _screen_capture
