#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GoLive Studio - Main Application
A cross-platform PyQt6 application for live streaming and recording
"""

import sys
import os
import time
import json
import traceback
import threading
import platform

from PyQt6.QtWidgets import QVBoxLayout

# Ensure stdout/stderr can encode Unicode on Windows consoles
try:
    if sys.platform.startswith('win'):
        try:
            sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        except Exception:
            pass
        try:
            sys.stderr.reconfigure(encoding='utf-8', errors='replace')
        except Exception:
            pass
except Exception:
    pass

print("\n[IMPORT] Starting GoLive Studio imports...", flush=True, file=sys.stderr)
sys.stderr.flush()

try:
    # Auto-restart with Python 3.12 if running with Python 3.13
    if sys.version_info.major == 3 and sys.version_info.minor == 13:
        import subprocess
        script_dir = os.path.dirname(os.path.abspath(__file__))
        # Prefer platform-appropriate venv layout. On Windows look for Scripts\python.exe,
        # on Unix-like systems look for bin/python. Also allow either form if present.
        candidates = [
            os.path.join(script_dir, "venv_py312", "Scripts", "python.exe"),
            os.path.join(script_dir, "venv_py312", "Scripts", "python"),
            os.path.join(script_dir, "venv_py312", "bin", "python"),
        ]
        venv_python = None
        for c in candidates:
            if os.path.exists(c):
                venv_python = c
                break
        if venv_python:
            print("Detected Python 3.13. Restarting with Python 3.12...")
            try:
                subprocess.run([venv_python] + sys.argv)
            except OSError as e:
                print(f"Failed to execute restart interpreter {venv_python}: {e}")
            sys.exit(0)
    
    print("[IMPORT] Loading PyQt6...", flush=True, file=sys.stderr)
    sys.stderr.flush()
    from PyQt6.QtWidgets import QApplication, QMainWindow, QFrame, QWidget, QSplitter, QMessageBox, QHBoxLayout, QVBoxLayout, QLabel, QGridLayout, QPushButton, QSizePolicy, QSpacerItem, QSlider, QGraphicsDropShadowEffect, QStackedWidget, QButtonGroup, QScrollArea, QTextEdit
    from PyQt6.QtCore import Qt, QSize, qInstallMessageHandler, QtMsgType, QUrl, QTimer, QObject, QEvent
    from PyQt6.QtGui import QIcon, QPixmap, QImage, QFont, QPalette, QColor
    from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput, QAudioSource, QAudioSink, QMediaDevices, QVideoSink, QCamera, QMediaCaptureSession, QAudioFormat
    # Defer PyAV import to runtime; some systems may not have FFmpeg headers/libs available.
    _HAS_AVF_PYAV = False
    # Thread pool for offloading blocking work
    try:
        from thread_pool_manager import thread_pool, TaskPriority
    except Exception:
        thread_pool = None
        TaskPriority = None
    
    print("[IMPORT] Loading project modules...", flush=True, file=sys.stderr)
    sys.stderr.flush()
    from PyQt6 import uic
    from transitions import TransitionManager, TRANSITIONS_CATALOG
    from overlay_manager import EffectManager
    from premiere_effects_panel_final import FinalEffectsPanel as PremiereEffectsPanel

    try:
        from project_manager import ProjectManager
    except Exception:
        ProjectManager = None
    
    # macOS Native Features (AVFoundation Camera, VideoToolbox Encoder)
    try:
        from macos_native_helper import get_macos_helper, MacOSNativeHelper
        MACOS_NATIVE_AVAILABLE = True
    except Exception as e:
        MACOS_NATIVE_AVAILABLE = False
        print(f"[IMPORT] macOS native features not available: {e}")
    
    print("[IMPORT] All critical imports successful!", flush=True, file=sys.stderr)
    sys.stderr.flush()

except Exception as e:
    print(f"\n[IMPORT ERROR] Failed during initialization: {e}", flush=True, file=sys.stderr)
    print(traceback.format_exc(), flush=True, file=sys.stderr)
    sys.stderr.flush()
    sys.exit(1)

print("[IMPORT] Loading performance and utility modules...", flush=True, file=sys.stderr)
sys.stderr.flush()

# DISABLED: Try-except that was exiting on error
# Now we'll try to import but continue even if modules fail
try:
    # Import FPS controller for global timing control
    try:
        from fps_controller import get_fps_controller, set_global_fps, get_global_fps
        from enhanced_streaming import get_streaming_manager
        FPS_CONTROLLER_AVAILABLE = True
    except ImportError:
        FPS_CONTROLLER_AVAILABLE = False
        print("FPS Controller not available, using legacy timing")
    
    print("[IMPORT-SUB-1] Importing fps_stabilizer...", flush=True, file=sys.stderr)
    sys.stderr.flush()
    from fps_stabilizer import fps_manager
    
    print("[IMPORT-SUB-2] Importing unified_timer...", flush=True, file=sys.stderr)
    sys.stderr.flush()
    from unified_timer import timer_manager
    
    print("[IMPORT-SUB-3] Importing event_coalescer...", flush=True, file=sys.stderr)
    sys.stderr.flush()
    try:
        from event_coalescer import event_coalescer, ui_coalescer
    except Exception as e:
        print(f"[IMPORT-SKIP] event_coalescer failed: {e}", flush=True, file=sys.stderr)
        event_coalescer = None
        ui_coalescer = None
    
    print("[IMPORT-SUB-4] Skipping gl_context_manager (compatibility mode)...", flush=True, file=sys.stderr)
    sys.stderr.flush()
    # DISABLED: gl_context_manager causes app to crash
    # from gl_context_manager import gl_context_manager
    gl_context_manager = None

    print("[IMPORT-SUB-5] Importing texture_pool...", flush=True, file=sys.stderr)
    sys.stderr.flush()
    try:
        from texture_pool import texture_pool
    except Exception as e:
        print(f"[IMPORT-SKIP] texture_pool failed: {e}", flush=True, file=sys.stderr)
        texture_pool = None
    
    print("[IMPORT-SUB-6] Importing smart_cache...", flush=True, file=sys.stderr)
    sys.stderr.flush()
    try:
        from smart_cache import smart_cache
    except Exception as e:
        print(f"[IMPORT-SKIP] smart_cache failed: {e}", flush=True, file=sys.stderr)
        smart_cache = None
    
    print("[IMPORT-SUB-7] Importing thread_pool_manager...", flush=True, file=sys.stderr)
    sys.stderr.flush()
    try:
        from thread_pool_manager import thread_pool, TaskPriority
    except Exception as e:
        print(f"[IMPORT-SKIP] thread_pool_manager failed: {e}", flush=True, file=sys.stderr)
        thread_pool = None
        TaskPriority = None
    
    print("[IMPORT-SUB-8] Importing adaptive_quality...", flush=True, file=sys.stderr)
    sys.stderr.flush()
    try:
        from adaptive_quality import quality_manager
    except Exception as e:
        print(f"[IMPORT-SKIP] adaptive_quality failed: {e}", flush=True, file=sys.stderr)
        quality_manager = None
    
    print("[IMPORT-SUB-9] Importing memory_pool...", flush=True, file=sys.stderr)
    sys.stderr.flush()
    try:
        from memory_pool import general_memory_pool, image_memory_pool
    except Exception as e:
        print(f"[IMPORT-SKIP] memory_pool failed: {e}", flush=True, file=sys.stderr)
        general_memory_pool = None
        image_memory_pool = None
    
    print("[IMPORT-SUB-10] Importing performance_monitor...", flush=True, file=sys.stderr)
    sys.stderr.flush()
    try:
        from performance_monitor import performance_monitor
    except Exception as e:
        print(f"[IMPORT-SKIP] performance_monitor failed: {e}", flush=True, file=sys.stderr)
        performance_monitor = None
    
    print("[IMPORT] All utility modules loaded!", flush=True, file=sys.stderr)
    sys.stderr.flush()
    
except Exception as e:
    print(f"\n[IMPORT WARNING] Failed loading some utility modules (continuing anyway): {e}", flush=True, file=sys.stderr)
    import traceback
    print(traceback.format_exc(), file=sys.stderr)
    sys.stderr.flush()
    # DON'T exit - allow app to continue with reduced functionality

print("[TRACE-1] About to import performance optimizers", flush=True, file=sys.stderr)
sys.stderr.flush()

# Import performance optimizer for memory and FPS optimization
try:
    from performance_optimizer import get_performance_optimizer, optimize_performance_now
    PERFORMANCE_OPTIMIZER_AVAILABLE = True
except ImportError:
    PERFORMANCE_OPTIMIZER_AVAILABLE = False
    print("Performance Optimizer not available")

print("[TRACE-2] About to import aggressive memory optimizer", flush=True, file=sys.stderr)
sys.stderr.flush()

# Import aggressive memory optimizer for ultra-low memory usage
try:
    from aggressive_memory_optimizer import force_memory_under_target, continuous_memory_management
    AGGRESSIVE_MEMORY_OPTIMIZER_AVAILABLE = True
except ImportError:
    AGGRESSIVE_MEMORY_OPTIMIZER_AVAILABLE = False
    print("Aggressive Memory Optimizer not available")

print("[TRACE-3] About to import renderer", flush=True, file=sys.stderr)
sys.stderr.flush()

# Import optimized renderer with single path
try:
    from renderer.migration_helper import create_graphics_output_widget, check_gpu_support
    
    print("[TRACE-3a] check_gpu_support() starting", flush=True, file=sys.stderr)
    sys.stderr.flush()
    
    gpu_info = check_gpu_support()
    
    print(f"[TRACE-3b] GPU info: {gpu_info}", flush=True, file=sys.stderr)
    sys.stderr.flush()
    
    _USE_NEW_RENDERER = bool(gpu_info.get('opengl_available') or gpu_info.get('d3d_available'))
    
    # OPTIMIZATION: Use single renderer path to avoid duplication
    if _USE_NEW_RENDERER:
        print(f"Using GPU renderer (OpenGL: {gpu_info.get('opengl_available')})")
        # Import enhanced version for GPU
        from enhanced_graphics_output import EnhancedGraphicsOutputWidget as GraphicsOutputWidget
    else:
        print("Using CPU renderer (fallback mode)")
        # Try to use enhanced graphics output as fallback
        from enhanced_graphics_output import EnhancedGraphicsOutputWidget as GraphicsOutputWidget
    
    print("[TRACE-3c] Renderer loaded successfully", flush=True, file=sys.stderr)
    sys.stderr.flush()
    
except ImportError as e:
    print(f"Renderer import error, using fallback: {e}")
    # Create a fallback minimal graphics output widget
    from PyQt6.QtWidgets import QLabel
    from PyQt6.QtGui import QImage, QPixmap
    from PyQt6.QtCore import QSize, Qt
    
    class GraphicsOutputWidget(QLabel):
        def __init__(self, parent=None):
            super().__init__(parent)
            self.setStyleSheet("background-color: black; color: white;")
            self.setText("Graphics Output")
            self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        def render_to_image(self, size):
            img = QImage(size, QImage.Format.Format_RGBA8888)
            img.fill(0)  # Black
            return img
        
        def set_preview_render_size(self, size):
            pass
        
        def get_current_source(self):
            return None
        
        def render_source_only(self, size):
            return self.render_to_image(size)
    
    _USE_NEW_RENDERER = False
from text_overlay import TextOverlayControls, TextOverlayMiniBar
from config import app_config
from streaming import StreamController
# Import enhanced display controller that fixes pixelation
try:
    from enhanced_external_display import EnhancedDisplayMirrorController
    _USE_ENHANCED_MIRROR = True
    print("Using enhanced display mirror controller (pixelation fixes)")
except ImportError as e:
    print(f"Enhanced mirror not available, using fallback: {e}")
    from external_display import DisplayMirrorController
    _USE_ENHANCED_MIRROR = False

print("[TRACE-4] About to import recording modules", flush=True, file=sys.stderr)
sys.stderr.flush()

from recording import RecorderController
from recording_settings_dialog import RecordingSettingsDialog

print("[TRACE-4.5] About to import OBS-style camera pipeline", flush=True, file=sys.stderr)
sys.stderr.flush()

# Import OBS-style camera pipeline modules (for stable, locked FPS)
try:
    from obs_pipeline import FrameBuffer, CameraWorker, RenderThread
    from camera_manager_obs import SignaledCameraManager
    OBS_CAMERA_PIPELINE_AVAILABLE = True
    print("OBS-style camera pipeline loaded successfully")
except ImportError as e:
    OBS_CAMERA_PIPELINE_AVAILABLE = False
    print(f"OBS-style camera pipeline not available, will use fallback: {e}")

print("[TRACE-5] About to import FFmpeg utils", flush=True, file=sys.stderr)
sys.stderr.flush()

# Enhanced bundled FFmpeg support - ensures internal FFmpeg is always used
from ffmpeg_utils import setup_ffmpeg_environment, get_ffmpeg_path

print("[TRACE-6] About to import GPU acceleration", flush=True, file=sys.stderr)
sys.stderr.flush()

# Import GPU acceleration module for texture upload and YUV conversion
try:
    from gpu_acceleration import (
        initialize_gpu_acceleration, 
        shutdown_gpu_acceleration,
        get_gpu_texture_manager,
        get_gpu_frame_converter
    )
    GPU_ACCELERATION_AVAILABLE = True
    print("GPU acceleration module loaded successfully")
except ImportError as e:
    GPU_ACCELERATION_AVAILABLE = False
    print(f"GPU acceleration not available: {e}")

# Import Phase 3: Full GPU Pipeline with zero-copy
try:
    from gpu_pipeline import (
        initialize_gpu_pipeline,
        shutdown_gpu_pipeline,
        get_gpu_pipeline
    )
    GPU_PIPELINE_AVAILABLE = True
    print("Phase 3 GPU Pipeline loaded successfully")
except ImportError as e:
    GPU_PIPELINE_AVAILABLE = False
    print(f"Phase 3 GPU Pipeline not available: {e}")

print("[TRACE-6] About to call setup_ffmpeg_environment()", flush=True, file=sys.stderr)
sys.stderr.flush()

# Initialize FFmpeg environment
_bundled_ffmpeg_path = setup_ffmpeg_environment()

print(f"[TRACE-7] FFmpeg setup complete. Path: {_bundled_ffmpeg_path}", flush=True, file=sys.stderr)
sys.stderr.flush()

if _bundled_ffmpeg_path:
    print(f"✓ Using bundled FFmpeg: {_bundled_ffmpeg_path}")
else:
    print("⚠ Bundled FFmpeg not found, will try system FFmpeg")

print("[TRACE-8] About to define _get_data_path function", flush=True, file=sys.stderr)
sys.stderr.flush()

# Resolve bundled data files (effects, icons, ui) across dev, PyInstaller onedir, and macOS .app Resources
def _get_data_path(*parts: str) -> str:
    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        candidates = []
        # 1) Next to executable (PyInstaller onedir typically puts datas in MacOS for some layouts)
        candidates.append(os.path.join(base_dir, *parts))
        # 2) macOS .app Resources
        candidates.append(os.path.join(base_dir, '..', 'Resources', *parts))
        # 3) PyInstaller onefile temporary extraction dir
        meipass = getattr(sys, '_MEIPASS', None)
        if meipass:
            candidates.append(os.path.join(meipass, *parts))
        for p in candidates:
            if os.path.exists(p):
                return os.path.normpath(p)
        # fallback to dev root (source layout)
        return os.path.normpath(os.path.join(base_dir, *parts))
    except Exception:
        return os.path.join(*parts)

def _get_writable_cache_dir(app_name: str, subdir: str = '') -> str:
    try:
        if sys.platform == 'darwin':
            root = os.path.join(os.path.expanduser('~'), 'Library', 'Application Support', app_name)
        elif sys.platform.startswith('win'):
            root = os.path.join(os.environ.get('APPDATA', os.path.expanduser('~')), app_name)
        else:
            root = os.path.join(os.environ.get('XDG_CACHE_HOME', os.path.join(os.path.expanduser('~'), '.cache')), app_name)
        if subdir:
            root = os.path.join(root, subdir)
        os.makedirs(root, exist_ok=True)
        return root
    except Exception:
        # very last resort: current working directory subdir
        root = os.path.join(os.getcwd(), subdir or 'cache')
        os.makedirs(root, exist_ok=True)
        return root

def qt_message_handler(mode, context, message):
    """Custom Qt message handler to suppress known noisy warnings"""
    if "libpng warning" in message and "iCCP" in message:
        return  # Suppress libpng iCCP warnings
    if "JPEG datastream contains no image" in message:
        return  # Suppress Qt camera MJPEG decode errors (corrupt frames from some USB cameras)
    # Allow other messages to pass through
    if mode == QtMsgType.QtDebugMsg:
        print(f"Qt Debug: {message}")
    elif mode == QtMsgType.QtWarningMsg:
        print(f"Qt Warning: {message}")
    elif mode == QtMsgType.QtCriticalMsg:
        print(f"Qt Critical: {message}")
    elif mode == QtMsgType.QtFatalMsg:
        print(f"Qt Fatal: {message}")

# Install the custom message handler
qInstallMessageHandler(qt_message_handler)

print("[STARTUP] Startup health check disabled temporarily for debugging", flush=True, file=sys.stderr)

# ---------- Startup health check: memory & low-memory mode ----------
# DISABLED TEMPORARILY FOR DEBUGGING - ENTIRE BLOCK COMMENTED OUT
# (Original 100+ lines of memory optimization code removed for testing)


class AspectRatioFrame(QFrame):
    """Custom QFrame that maintains 16:9 aspect ratio with clipping for Windows overlay safety"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.aspect_ratio = 16.0 / 9.0
        # Make sure this widget prefers width-driven sizing with proper height-for-width support
        from PyQt6.QtWidgets import QSizePolicy
        sp = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        sp.setHeightForWidth(True)
        self.setSizePolicy(sp)
        # ENABLE CLIPPING: Prevent overlays from painting outside frame bounds (Windows fix)
        # These attributes ensure that any child widget or painted content is clipped to this frame
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, True)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        self.setLineWidth(0)
        self.setMidLineWidth(0)
    
    def sizeHint(self):
        """Return preferred size maintaining 16:9 aspect ratio"""
        return QSize(320, 180)  # 16:9 ratio
    
    def minimumSizeHint(self):
        """Return minimum size maintaining 16:9 aspect ratio"""
        return QSize(160, 90)   # 16:9 ratio
    
    def hasHeightForWidth(self):
        """Enable height-for-width layout"""
        return True
    
    def heightForWidth(self, width):
        """Calculate height based on width to maintain 16:9 aspect ratio"""
        # Pure 16:9 calculation - no reductions
        # Qt's layout engine and container spacing handle all boundary safety
        return int(width / self.aspect_ratio)

    
    def resizeEvent(self, event):
        """Maintain aspect ratio during resize"""
        super().resizeEvent(event)
        # Note: Do NOT set fixed min/max height here - it breaks layout on Windows
        # The heightForWidth layout policy handles aspect ratio automatically
        # Ensure any child label will scale inside
        if hasattr(self, '_video_label'):
            self._video_label.setMinimumSize(1, 1)
    
    def paintEvent(self, event):
        """Paint event with explicit clip region to prevent overlays from escaping bounds"""
        # Set up a clip region to the widget's bounds before painting children
        # This is the ultimate safety measure for Windows overlay containment
        from PyQt6.QtGui import QPainter
        painter = QPainter(self)
        # Ensure clip region is set to widget rectangle (bounds)
        painter.setClipRect(self.rect())
        super().paintEvent(event)

class ResponsiveEffectsWidget(QWidget):
    """Responsive widget that automatically adjusts effect thumbnails based on available width"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        from PyQt6.QtWidgets import QGridLayout
        self.grid_layout = QGridLayout(self)
        self.grid_layout.setSpacing(8)  # Increased spacing to prevent overlapping
        self.grid_layout.setContentsMargins(8, 8, 8, 8)  # Increased margins for better spacing
        self.effects_buttons = []
        self.columns = 4  # Fixed 4 columns
        self.aspect_ratio = 16.0 / 9.0
        self.cache_dir = None
        self._pending_icons = []
        self._batch_timer = None
        self._selected_path = None
        self._click_cb = None
        self._dblclick_cb = None
        
    def set_cache_dir(self, cache_dir):
        self.cache_dir = cache_dir

    def add_effects(self, png_files, click_callback, dblclick_callback=None):
        """Add effect buttons lazily. click_callback(path) single-click; dblclick_callback(path) optional."""
        from PyQt6.QtWidgets import QPushButton
        import os
        self._click_cb = click_callback
        self._dblclick_cb = dblclick_callback
        
        for png_file in png_files:
            try:
                # Create clickable button for each image
                image_button = QPushButton()
                image_button.setStyleSheet("""
                    QPushButton {
                        border: 2px solid #555;
                        border-radius: 4px;
                        background-color: #2b2b2b;
                    }
                    QPushButton:hover {
                        border: 2px solid #0078d4;
                        background-color: #333;
                    }
                    QPushButton:pressed {
                        background-color: #0078d4;
                    }
                """)
                # Store file path and pixmap for later use
                image_button.effect_file_path = png_file
                image_button.effect_name = os.path.basename(png_file)
                image_button._has_icon = False
                
                # Connect click event
                image_button.clicked.connect(lambda checked, path=png_file: self._handle_click(path))
                # Double-click support
                def _dbl(ev, path=png_file, btn=image_button):
                    if self._dblclick_cb:
                        self._dblclick_cb(path)
                    ev.accept()
                image_button.mouseDoubleClickEvent = _dbl
                
                # Add tooltip with filename
                image_button.setToolTip(os.path.basename(png_file))
                
                self.effects_buttons.append(image_button)
                
            except Exception as e:
                print(f"Error loading image {png_file}: {e}")
                continue
        
        # Defer initial layout until widget is properly sized
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(100, self.update_layout)

    def _handle_click(self, path):
        if self._click_cb:
            self._click_cb(path)
        self.update_selection(path)
    
    def _thumb_path(self, src_path, w, h):
        import hashlib, os
        try:
            st = os.stat(src_path)
            key = f"{src_path}|{int(st.st_mtime)}|{st.st_size}|{w}x{h}".encode('utf-8')
        except Exception:
            key = f"{src_path}|{w}x{h}".encode('utf-8')
        name = hashlib.md5(key).hexdigest() + ".jpg"
        if not self.cache_dir:
            return None
        os.makedirs(self.cache_dir, exist_ok=True)
        return os.path.join(self.cache_dir, name)

    def _ensure_button_icon(self, button, button_width):
        """Ensure the button has its icon set, using cached thumbnail if possible."""
        from PyQt6.QtGui import QIcon, QImageReader, QPixmap
        from PyQt6.QtCore import QSize
        if getattr(button, '_has_icon', False):
            return
        bw = max(32, button_width - 4)
        bh = int(bw / self.aspect_ratio)
        button.setFixedSize(bw + 4, bh + 4)
        thumb_path = self._thumb_path(button.effect_file_path, bw, bh)
        pix = QPixmap()
        loaded = False
        if thumb_path and os.path.exists(thumb_path):
            loaded = pix.load(thumb_path)
        if not loaded:
            # Decode at target size (fast and memory-efficient)
            reader = QImageReader(button.effect_file_path)
            reader.setAutoTransform(True)
            reader.setScaledSize(QSize(bw, bh))
            img = reader.read()
            if not img.isNull():
                pix = QPixmap.fromImage(img)
                if thumb_path:
                    try:
                        img.save(thumb_path, 'JPG', quality=80)
                    except Exception:
                        pass
        if not pix.isNull():
            button.setIcon(QIcon(pix))
            button.setIconSize(pix.size())
            button._has_icon = True

    def update_layout(self):
        """Update the grid layout with fixed 4 columns and responsive button sizing"""
        if not self.effects_buttons:
            return
            
        # Get parent widget dimensions for better width calculation
        parent_widget = self.parent()
        while parent_widget and not hasattr(parent_widget, 'width'):
            parent_widget = parent_widget.parent()
            
        # Calculate available width more accurately
        if parent_widget and hasattr(parent_widget, 'width'):
            available_width = max(parent_widget.width() - 20, 400)  # Account for margins and padding
        else:
            available_width = max(self.width() - 16, 400) if self.width() > 0 else 600
        
        # Clear existing layout
        for i in reversed(range(self.grid_layout.count())):
            item = self.grid_layout.itemAt(i)
            if item and item.widget():
                item.widget().setParent(None)
        
        # Fixed 4 columns - calculate button width to fill available space
        spacing = self.grid_layout.spacing()
        margins = self.grid_layout.contentsMargins()
        total_spacing = (self.columns - 1) * spacing + margins.left() + margins.right()
        button_width = max(120, (available_width - total_spacing) // self.columns)
        
        # Update all buttons and add to grid; defer heavy icon work to batches
        row = 0
        col = 0
        self._pending_icons = []
        for button in self.effects_buttons:
            # Size the button; icon will be applied in batches
            btn_h = int(button_width / self.aspect_ratio)
            button.setFixedSize(button_width, btn_h)
            button.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)  # Ensure fixed size
            self._pending_icons.append((button, button_width))
            
            # Add to grid
            self.grid_layout.addWidget(button, row, col, Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
            
            col += 1
            if col >= self.columns:
                col = 0
                row += 1

        # Process icons in small batches to keep UI responsive
        self._start_icon_batch()

    def resizeEvent(self, event):
        """Handle resize events to update layout"""
        super().resizeEvent(event)
        # Add a small delay to prevent excessive updates during resize
        from PyQt6.QtCore import QTimer
        if hasattr(self, '_resize_timer'):
            self._resize_timer.stop()
        self._resize_timer = QTimer()
        self._resize_timer.setSingleShot(True)
        self._resize_timer.timeout.connect(self.update_layout)
        self._resize_timer.start(50)

    def _start_icon_batch(self):
        from PyQt6.QtCore import QTimer
        if self._batch_timer:
            self._batch_timer.stop()
        self._batch_timer = QTimer(self)
        self._batch_timer.timeout.connect(self._process_icon_batch)
        self._batch_timer.start(10)

    def _process_icon_batch(self):
        if not self._pending_icons:
            if self._batch_timer:
                self._batch_timer.stop()
            return
        # Process up to N icons per tick
        batch = 24
        for _ in range(min(batch, len(self._pending_icons))):
            button, bw = self._pending_icons.pop(0)
            try:
                self._ensure_button_icon(button, bw)
            except Exception:
                pass

    def update_selection(self, selected_path: str | None):
        """Visually highlight the selected button by path."""
        self._selected_path = selected_path
        # Styles
        base_style = """
            QPushButton { border: 2px solid #555; border-radius: 4px; background-color: #2b2b2b; }
            QPushButton:hover { border: 2px solid #0078d4; background-color: #333; }
            QPushButton:pressed { background-color: #0078d4; }
        """
        sel_style = """
            QPushButton { border: 3px solid #00aaff; border-radius: 4px; background-color: #2f2f2f; }
        """
        for b in self.effects_buttons:
            try:
                if getattr(b, 'effect_file_path', None) == selected_path and selected_path:
                    b.setStyleSheet(sel_style)
                else:
                    b.setStyleSheet(base_style)
            except Exception:
                pass

print("[STARTUP] About to define GoLiveStudio class...", flush=True, file=sys.stderr)
sys.stderr.flush()

from PyQt6.QtCore import pyqtSignal, QThread, QMetaObject, Q_ARG, pyqtSlot
from PyQt6.QtMultimedia import QVideoFrame
import queue

# ============================================================================
# MJPEG FORMAT SELECTOR - Prefers compressed over raw USB formats  
# ============================================================================
def _select_best_camera_format(camera_device, target_w, target_h, target_fps):
    """
    Select camera format with explicit pixel-format fallback order.
    
    Desired preference (user-requested):
      NV12 -> YUY2 -> MJPEG -> RGB
    
    Windows lists each resolution twice:
    - MJPEG (compressed, low bandwidth)
    - YUY2/NV12 (raw uncompressed, high bandwidth)
    
    Previous code just picked the first match — unreliable. This function
    explicitly prefers MJPEG.
    """
    from PyQt6.QtMultimedia import QVideoFrameFormat
    
    all_formats = camera_device.videoFormats()

    def _pf_name(pf):
        try:
            if pf == QVideoFrameFormat.PixelFormat.Format_Jpeg:
                return "MJPEG"
        except Exception:
            pass
        try:
            return str(pf).split('.')[-1]
        except Exception:
            return str(pf)

    def _pf_rank(pf):
        """Lower is better."""
        PF = QVideoFrameFormat.PixelFormat
        # Order requested by user:
        # NV12 -> YUY2 -> MJPEG -> RGB
        try:
            if pf == PF.Format_NV12:
                return 0
        except Exception:
            pass
        # Qt names vary across platforms/drivers; treat common packed YUV as 'YUY2 bucket'
        try:
            if pf in (getattr(PF, 'Format_YUYV', None), getattr(PF, 'Format_UYVY', None), getattr(PF, 'Format_YUV422P', None)):
                return 1
        except Exception:
            pass
        try:
            if pf == PF.Format_Jpeg:
                return 2
        except Exception:
            pass
        # RGB / RGBA / BGRA etc.
        try:
            if pf in (
                getattr(PF, 'Format_RGBX8888', None),
                getattr(PF, 'Format_RGBA8888', None),
                getattr(PF, 'Format_BGRX8888', None),
                getattr(PF, 'Format_BGRA8888', None),
                getattr(PF, 'Format_RGB888', None),
                getattr(PF, 'Format_BGR888', None),
            ):
                return 3
        except Exception:
            pass
        # Anything else, last
        return 4

    def _fmt_score(fmt):
        res = fmt.resolution()
        w = int(res.width())
        h = int(res.height())
        fps_max = float(fmt.maxFrameRate())
        pf = fmt.pixelFormat()

        # Prefer exact resolution; then higher fps; then pixel format rank.
        # Use negative values for preferred properties in tuple sort.
        exact_res = 0 if (w == target_w and h == target_h) else 1
        fps_ok = 0 if fps_max >= float(target_fps) else 1
        pf_rank = _pf_rank(pf)
        # Prefer higher fps_max within the same bucket
        return (exact_res, fps_ok, pf_rank, -fps_max)
    
    # Print format list with pixel format info
    print("Qt camera supported formats (with pixel format):")
    format_list = []
    for fmt in all_formats:
        res = fmt.resolution()
        w = int(res.width())
        h = int(res.height())
        fps_max = float(fmt.maxFrameRate())
        pf = fmt.pixelFormat()
        pf_name = _pf_name(pf)
        format_list.append((w, h, fps_max, pf_name, fmt))
        print(f"  - {w}x{h} @ up to {fps_max:.0f}fps [{pf_name}]")

    if not all_formats:
        print(f"[CAMERA] ❌ No formats reported by device")
        return None, target_fps

    best = min(all_formats, key=_fmt_score)
    try:
        res = best.resolution()
        w = int(res.width())
        h = int(res.height())
        fps_max = float(best.maxFrameRate())
        pf = best.pixelFormat()
        pf_name = _pf_name(pf)
        print(f"[CAMERA] ✅ Selected format: {w}x{h} @ {fps_max:.0f}fps [{pf_name}]")
        return best, int(fps_max) if fps_max > 0 else int(target_fps)
    except Exception:
        return best, target_fps


print("[STARTUP] About to define GoLiveStudio class...", flush=True, file=sys.stderr)
sys.stderr.flush()

from PyQt6.QtCore import pyqtSignal, QThread, QMetaObject, Q_ARG, pyqtSlot
from PyQt6.QtMultimedia import QVideoFrame
import queue

# ============================================================================
# FRAME PROCESSING WORKER - Moves expensive frame processing off GUI thread
# ============================================================================
class FrameProcessingWorker:
    """
    Per-input worker thread that processes camera frames off the GUI thread.
    Receives QImage from GUI thread, converts + processes, stores result.
    Uses bounded queue (maxsize=2) — drops old frames if processing is slow.
    
    FIX FOR WINDOWS: GUI thread can't keep up with 60fps frame influx on Windows
    (expensive toImage() + scaling + cache updates). This worker moves that work
    to a background thread, keeping GUI thread responsive.
    """
    def __init__(self, input_number, on_frame_ready_callback):
        self._input_number = input_number
        self._on_frame_ready = on_frame_ready_callback
        self._queue = queue.Queue(maxsize=2)
        self._running = True
        self._thread = threading.Thread(
            target=self._run, daemon=True,
            name=f"FrameWorker-Input{input_number}"
        )
        self._thread.start()
        
        # FPS tracking
        self._fps_count = 0
        self._fps_clock = time.perf_counter()
        self._frame_count = 0

    def process_frame(self, qimage, input_number):
        """Non-blocking. Drops oldest frames when processing can't keep up (OBS-style)."""
        try:
            self._queue.put_nowait((qimage, input_number))
        except queue.Full:
            try:
                _ = self._queue.get_nowait()
            except Exception:
                return
            try:
                self._queue.put_nowait((qimage, input_number))
            except Exception:
                pass
    
    def process_video_frame(self, video_frame, input_number):
        """Process QVideoFrame directly (moves expensive toImage() to worker thread)."""
        try:
            # Convert QVideoFrame to QImage on worker thread (NOT GUI thread!)
            # This avoids blocking GUI with JPEG decode for MJPEG frames
            img = video_frame.toImage()
            if img is None or img.isNull():
                return
            # Queue the converted image
            self._queue.put_nowait((img, input_number))
        except queue.Full:
            try:
                _ = self._queue.get_nowait()
            except Exception:
                return
            try:
                self._queue.put_nowait((img, input_number))
            except Exception:
                pass
        except Exception:
            pass

    def _run(self):
        """Worker thread main loop."""
        while self._running:
            try:
                qimage, input_number = self._queue.get(timeout=0.1)
                self._process(qimage, input_number)
            except queue.Empty:
                continue
            except Exception:
                pass

    def _process(self, qimage, input_number):
        """Convert QVideoFrame/QImage to a safe QImage copy and forward to GUI thread."""
        try:
            # IMPORTANT:
            # Converting to numpy and then back to QImage on the GUI thread is costly and
            # commonly caps effective FPS (~30fps). For display + caching we only need QImage.
            # Make a defensive copy because Qt may reuse internal buffers.
            img = qimage.copy()
            width = img.width()
            height = img.height()
            
            # FPS tracking
            self._frame_count += 1
            self._fps_count += 1
            now = time.perf_counter()
            if now - self._fps_clock >= 1.0:
                actual_fps = self._fps_count / (now - self._fps_clock)
                self._fps_clock = now
                self._fps_count = 0
                print(f"Input-{self._input_number} actual FPS: {actual_fps:.1f}")
                if self._frame_count % 60 == 0:
                    print(f"Input-{self._input_number} Frame #{self._frame_count}: {width}x{height}")
            
            # Call back to main thread with processed QImage
            self._on_frame_ready(self._input_number, img)
            
        except Exception as e:
            pass

    def stop(self):
        """Stop the worker thread cleanly."""
        self._running = False
        self._thread.join(timeout=1.0)


# ============================================================================
# QIMAGE RING BUFFER - Thread-safe circular buffer for QImage frames (OBS-style)
# ============================================================================
from typing import Optional

class QImageRingBuffer:
    """
    Thread-safe ring buffer for QImage frames (like OBS NUM_TEXTURES).
    Stores limited frames; new frames overwrite oldest.
    Render thread reads latest frame at fixed FPS.
    """
    
    def __init__(self, maxlen: int = 3):
        self._buf = []
        self._maxlen = maxlen
        self._lock = threading.Lock()
        self._write_idx = 0
        # Pre-allocate slots
        for _ in range(maxlen):
            self._buf.append(None)
    
    def put(self, frame: QImage):
        """Add frame to buffer. Thread-safe."""
        with self._lock:
            # Store copy to prevent reference issues
            if frame is not None and not frame.isNull():
                self._buf[self._write_idx] = frame.copy()
            else:
                self._buf[self._write_idx] = None
            self._write_idx = (self._write_idx + 1) % self._maxlen
    
    def get_latest(self) -> Optional[QImage]:
        """Get most recent frame without removing. Thread-safe."""
        with self._lock:
            # Read from write_idx - 1 (most recent)
            read_idx = (self._write_idx - 1) % self._maxlen
            frame = self._buf[read_idx]
            if frame is not None and not frame.isNull():
                return frame.copy()
            return None
    
    def clear(self):
        """Clear all frames."""
        with self._lock:
            for i in range(len(self._buf)):
                self._buf[i] = None


# ============================================================================
# FRAME CONVERTER WORKER - Moves expensive QVideoFrame.toImage() off main thread
# ============================================================================
class FrameConverterWorker(QObject):
    """
    Worker that converts QVideoFrame to QImage on a background thread.
    Also pre-scales to 720p to prevent main thread blocking during scaling.
    """
    # Signal: emitted with both full-res and pre-scaled QImage back to main thread
    frame_converted = pyqtSignal(int, QImage, QImage)  # (input_number, full_res, scaled_720p)
    
    def __init__(self):
        super().__init__()
        self._throttle = {}  # FPS throttle per input
    
    @pyqtSlot(int, QVideoFrame)
    def convert_frame(self, input_number: int, video_frame: QVideoFrame):
        """
        Convert QVideoFrame to QImage on background thread.
        Also pre-scale to 720p (this is expensive, so do it here not on main thread).
        
        Args:
            input_number: Camera input number
            video_frame: Qt QVideoFrame from camera
        """
        try:
            # FIXED: Remove throttling - convert EVERY frame without dropping
            # Frame deduplication happens in frame provider via frame_id check
            import time
            from collections import deque
            now = time.perf_counter()
            
            # Track raw delivery rate for diagnostics
            if not hasattr(self, '_converter_frame_times'):
                self._converter_frame_times = {}
            if input_number not in self._converter_frame_times:
                self._converter_frame_times[input_number] = deque(maxlen=120)
            self._converter_frame_times[input_number].append(now)
            
            # Report every 5 seconds
            if not hasattr(self, '_converter_fps_report'):
                self._converter_fps_report = {}
            last_report = self._converter_fps_report.get(input_number, 0.0)
            if now - last_report >= 5.0:
                times = self._converter_frame_times[input_number]
                if len(times) > 1:
                    span = times[-1] - times[0]
                    raw_rate = (len(times) - 1) / span if span > 0 else 0
                    print(f"[CONVERTER-DELIVERY] Input-{input_number}: camera delivering {raw_rate:.1f}fps")
                    self._converter_fps_report[input_number] = now
            
            # Convert to QImage (this is expensive, but now on background thread)
            img = video_frame.toImage()
            if img is None or img.isNull():
                return
            
            # Copy the image (video_frame may be reused by Qt)
            img = img.copy()
            
            # PRE-SCALE to common output sizes on background thread
            # This prevents expensive scaling on the main thread
            pre_scaled_sizes = [
                (1280, 720),   # 720p for thumbnails
                (1920, 1080),  # 1080p full-res
                (1710, 1073),  # Mirror size (Retina MacBook Pro scaled)
                (1710, 1107),  # Mirror size alternative
            ]
            
            scaled_images = {}
            for target_w, target_h in pre_scaled_sizes:
                # Skip if same as original
                if img.width() == target_w and img.height() == target_h:
                    continue
                scaled = img.scaled(
                    target_w, target_h,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.FastTransformation
                )
                scaled_images[(target_w, target_h)] = scaled
            
            # Use 1280x720 as the default scaled version for UI
            scaled_720p = scaled_images.get((1280, 720), img)
            
            # Emit full-res and 720p back to main thread
            self.frame_converted.emit(input_number, img, scaled_720p)
            
            # ALSO emit other pre-scaled sizes as separate signals so they get cached
            # This prevents cache misses for mirror sizes
            for size_key, scaled_img in scaled_images.items():
                if size_key != (1280, 720):  # 720p already emitted
                    # Emit as additional frame with that specific size
                    # This will be cached in last_input_image_scaled
                    self.frame_converted.emit(input_number, img, scaled_img)
            
        except Exception as e:
            import time as time_module
            if not hasattr(self, '_last_error_time'):
                self._last_error_time = 0.0
            now = time_module.time()
            if now - self._last_error_time > 1.0:
                print(f"FrameConverterWorker error: {e}")
                self._last_error_time = now


def _diag_error(context: str, error: Exception, extra: str = ""):
    """Pinpoints exactly where an error occurred with full context."""
    tb = traceback.extract_tb(error.__traceback__)
    if tb:
        last = tb[-1]
        file_short = os.path.basename(last.filename)
        line = last.lineno
        func = last.name
        print(f"\n{'='*60}")
        print(f"[ERROR] ❌ {context}")
        print(f"[ERROR]    File    : {file_short} (full: {last.filename})")
        print(f"[ERROR]    Line    : {line}")
        print(f"[ERROR]    Function: {func}")
        print(f"[ERROR]    Type    : {type(error).__name__}")
        print(f"[ERROR]    Message : {error}")
        if extra:
            print(f"[ERROR]    Context : {extra}")
        print(f"[ERROR]    Stack trace:")
        for frame in tb:
            print(f"[ERROR]      → {os.path.basename(frame.filename)}:"
                  f"{frame.lineno} in {frame.name}")
        print(f"{'='*60}\n")
    else:
        print(f"[ERROR] ❌ {context}: {type(error).__name__}: {error}")


class GoLiveStudio(QMainWindow):
    camera_frame_ready = pyqtSignal(int, object)
    def __init__(self):
        super().__init__()
        # Initialize all optimization systems first
        self._init_optimization_systems()
        # Initialize unified timer system
        timer_manager.initialize(self)
        # Initialize transition attributes early (before load_ui) to prevent AttributeError
        self.transition_manager = TransitionManager(self)
        self.selected_transition = 'None'
        self.transition_duration_ms = 700
        self.transition_easing = 'ease_in_out'
        self._transition_running = False
        
        # Initialize graphics output widget (will be created in _ensure_output_preview_label)
        self._graphics_output = None
        
        # Initialize OBS-style camera pipeline managers (per-input camera control)
        self.camera_managers = {}  # dict of {input_number: SignaledCameraManager}
        self.obs_camera_pipeline_enabled = OBS_CAMERA_PIPELINE_AVAILABLE
        
        # Initialize macOS native helper (AVFoundation camera, VideoToolbox encoder)
        self._macos_native = None
        if MACOS_NATIVE_AVAILABLE and platform.system() == "Darwin":
            try:
                self._macos_native = get_macos_helper(self)
                self._macos_native.print_status()
            except Exception as e:
                print(f"[INIT] macOS native helper initialization failed: {e}")
        
        # Initialize per-input frame processing workers (moves frame processing off GUI thread)
        self._frame_workers = {}  # input_number -> FrameProcessingWorker
        
        # Initialize frame converter worker (moves QVideoFrame.toImage() to background thread)
        self._converter_thread = QThread()
        self._converter_worker = FrameConverterWorker()
        self._converter_worker.moveToThread(self._converter_thread)
        # Connect frame_converted signal to main thread for UI updates (QueuedConnection is thread-safe)
        self._converter_worker.frame_converted.connect(
            self._on_frame_converted_from_worker,
            Qt.ConnectionType.QueuedConnection
        )
        self._converter_thread.start()
        
        # Initialize deferred frame processing flags (prevents event queue flooding)
        # Maps input_number -> bool, where True means a timer event is pending
        self._qt_frame_deferred_pending = {}
        # Tracks which inputs have pending deferred frame processing timers
        self._qt_frame_timer_pending = set()
        
        # OBS-STYLE: Initialize ring buffers for each input (like OBS NUM_TEXTURES)
        # This decouples capture thread from render thread for smooth playback
        self._input_frame_buffers = {}  # input_number -> QImageRingBuffer
        
        # Initialize scaled frame cache (prevents expensive scaling on streaming background thread)
        # Maps (input_number, width, height) -> pre-scaled QImage
        self.last_input_image_scaled = {}
        
        self.load_ui()
        # Connect UI signals to their slots
        self.connect_signals()
        # Initialize application state
        self.init_app_state()
        # Set performance mode based on system capabilities
        self._set_performance_mode()
        # Connect quality manager signals
        self._connect_quality_signals()
        # Connect camera frame ready signal to UI update slot
        # CRITICAL: Use QueuedConnection to ensure text rendering happens on main thread
        # This prevents Qt crashes when QImage/QPainter operations occur on camera thread
        from PyQt6.QtCore import Qt as QtCore
        self.camera_frame_ready.connect(self._on_camera_frame_ready, QtCore.ConnectionType.QueuedConnection)
        
        # Initialize global FPS controller
        if FPS_CONTROLLER_AVAILABLE:
            try:
                self.fps_controller = get_fps_controller()
                self.streaming_manager = get_streaming_manager()
                
                # Set initial FPS from configuration
                initial_fps = int(app_config.get('ui.preview_fps', 30))
                self.fps_controller.set_target_fps(initial_fps)
                self.fps_controller.start()
                
                print(f"Global FPS Controller initialized at {initial_fps} FPS")
            except Exception as e:
                print(f"FPS Controller initialization error: {e}")
        
        # Start deferred systems that use QTimer (must be after QObject/QApplication ready)
        try:
            event_coalescer.start()
            ui_coalescer.start()
        except Exception as _e:
            print(f"Deferred coalescers start warning: {_e}")
        try:
            performance_monitor.start_monitoring()
        except Exception as _e:
            print(f"Performance monitor start warning: {_e}")
        
        # Force layout after app fully loads (1 second delay allows Qt to fully render)
        QTimer.singleShot(1000, self.apply_forced_layout)

    def showEvent(self, event):
        """Override showEvent to force layout when window first appears."""
        super().showEvent(event)
        # Call forced layout immediately after window is shown
        self.apply_forced_layout()
        # Ensure stream controllers initialize (resizeEvent may not fire on first show)
        QTimer.singleShot(150, self._on_deferred_resize)

    def changeEvent(self, event):
        try:
            super().changeEvent(event)
        except Exception:
            pass
        try:
            if event is not None and event.type() == QEvent.Type.WindowStateChange:
                # When window state changes (maximize, restore, minimize), refresh layout and styles
                window_state = self.windowState()
                # Refresh layout for both maximize and restore states
                if not (window_state & Qt.WindowState.WindowMinimized):
                    # Window is now visible/normal - refresh layout
                    if hasattr(self, '_apply_monitor_area_height_policy'):
                        try:
                            QTimer.singleShot(0, self._apply_monitor_area_height_policy)
                        except Exception:
                            self._apply_monitor_area_height_policy()
                    # Also refresh the main layout to restore styles/borders
                    if hasattr(self, 'apply_forced_layout'):
                        try:
                            QTimer.singleShot(50, self.apply_forced_layout)
                        except Exception:
                            pass
        except Exception:
            pass
    
    def _init_optimization_systems(self):
        """Initialize all optimization systems."""
        # Initialize GL context manager (only if available)
        try:
            if gl_context_manager:
                gl_context_manager.initialize()
        except Exception as e:
            print(f"[WARNING] Could not initialize gl_context_manager: {e}")
        
        # Initialize GPU acceleration (Phase 2)
        if GPU_ACCELERATION_AVAILABLE:
            try:
                initialize_gpu_acceleration()
                print("[GPU] GPU acceleration initialized successfully")
            except Exception as e:
                print(f"[GPU] Failed to initialize GPU acceleration: {e}")
        
        # Initialize Phase 3: Full GPU Pipeline with zero-copy
        if GPU_PIPELINE_AVAILABLE:
            try:
                initialize_gpu_pipeline()
                print("[GPU] Phase 3 GPU Pipeline initialized successfully")
            except Exception as e:
                print(f"[GPU] Failed to initialize Phase 3 GPU Pipeline: {e}")
        
        # Set up memory pools
        try:
            if general_memory_pool:
                general_memory_pool.optimize()
        except Exception:
            pass
        
        try:
            if image_memory_pool:
                image_memory_pool.optimize()
        except Exception:
            pass
        
        # Configure smart cache
        try:
            if smart_cache:
                smart_cache.clear()  # Start fresh
        except Exception:
            pass
        
        # Set up event coalescers
        event_coalescer.register_handler('ui_update', self._handle_coalesced_ui_update)
        event_coalescer.register_handler('fps_update', self._handle_coalesced_fps_update)
        
        # Initialize optimization systems
        print("Optimization systems initialized")
        
        # Initialize performance optimizer for better memory and FPS management
        if PERFORMANCE_OPTIMIZER_AVAILABLE:
            self.performance_optimizer = get_performance_optimizer()
            # Force initial memory optimization
            optimize_performance_now()
            print("Performance optimizer initialized with aggressive memory management")
        else:
            self.performance_optimizer = None
        
        # Apply ultra-aggressive memory optimization to meet 250MB target
        if AGGRESSIVE_MEMORY_OPTIMIZER_AVAILABLE:
            success = force_memory_under_target(250)
            if success:
                print("✅ Memory successfully optimized to under 250MB target")
            else:
                print("⚠️ Memory optimization applied, but target not fully met")
            
            # Enable continuous memory management
            continuous_memory_management()
            print("Continuous memory management enabled")
    
    def _connect_quality_signals(self):
        """Connect adaptive quality manager signals."""
        quality_manager.quality_changed.connect(self._on_quality_changed)
        quality_manager.settings_updated.connect(self._on_quality_settings_updated)
    
    def _on_quality_changed(self, level: str):
        """Handle quality level change."""
        print(f"Adaptive quality changed to: {level}")
        # Update UI to reflect quality change
        if hasattr(self, 'statusBar'):
            self.statusBar().showMessage(f"Quality: {level}", 2000)
    
    def _on_quality_settings_updated(self, settings: dict):
        """Apply new quality settings."""
        try:
            # Update FPS
            if 'fps' in settings and hasattr(self, '_graphics_output'):
                self._graphics_output.set_target_fps(settings['fps'])
            
            # Update resolution
            if 'resolution' in settings:
                width, height = settings['resolution']
                # Update output resolution
                app_config.set('recording.width', width)
                app_config.set('recording.height', height)
            
            # Update effects
            if 'effects_enabled' in settings:
                # Enable/disable effects based on quality
                pass  # Implement as needed
            
            # Update cache sizes
            if 'cache_size' in settings:
                from premiere_effects_panel_final import ThumbnailCache
                cache = ThumbnailCache()
                cache._max_cache_size = settings['cache_size']
        except Exception as e:
            print(f"Error applying quality settings: {e}")
    
    def _handle_coalesced_ui_update(self, data):
        """Handle coalesced UI updates."""
        # Process batched UI updates
        if data and isinstance(data, set):
            for widget in data:
                try:
                    widget.update()
                except:
                    pass
    
    def _handle_coalesced_fps_update(self, data):
        """Handle coalesced FPS updates."""
        # Process batched FPS updates
        pass
    
    def _set_performance_mode(self):
        """Set performance mode based on system capabilities."""
        try:
            import psutil
            cpu_count = psutil.cpu_count(logical=False) or 4
            memory_gb = psutil.virtual_memory().total / (1024**3)
            
            if cpu_count >= 8 and memory_gb >= 16:
                fps_manager.set_performance_mode('quality')
                print("Performance mode: Quality (High-end system detected)")
            elif cpu_count >= 4 and memory_gb >= 8:
                fps_manager.set_performance_mode('balanced')
                print("Performance mode: Balanced (Mid-range system detected)")
            else:
                fps_manager.set_performance_mode('performance')
        except Exception as e:
            print(f"Error setting performance mode: {e}")

    def resizeEvent(self, event):
        try:
            super().resizeEvent(event)
        except Exception:
            pass
        # Debounce expensive rescale operations during interactive resize
        try:
            if not hasattr(self, '_resize_timer'):
                self._resize_timer = QTimer(self)
                self._resize_timer.setSingleShot(True)
                self._resize_timer.timeout.connect(self._on_deferred_resize)
            # Restart debounce timer (100ms)
            self._resize_timer.start(100)
        except Exception:
            # Fallback: call directly (best-effort)
            try:
                self._on_deferred_resize()
            except Exception:
                pass

    def _on_deferred_resize(self):
        """Deferred resize handler: rescale cached preview images to current widget sizes.

        Uses already-cached full-resolution QImages in `self.last_input_image` to create
        scaled pixmaps quickly without re-reading camera frames.
        """
        try:
            from PyQt6.QtGui import QPixmap
            from PyQt6.QtCore import Qt, QSize
            if hasattr(self, 'last_input_image'):
                for input_number, q_image in list(self.last_input_image.items()):
                    try:
                        if q_image is None:
                            continue
                        try:
                            video_widget = getattr(self, f'inputVideoFrame{input_number}')
                        except Exception:
                            video_widget = None
                        pixmap = QPixmap.fromImage(q_image)
                        if video_widget is not None:
                            widget_size = video_widget.size()
                            if widget_size.width() <= 1 or widget_size.height() <= 1:
                                min_size = video_widget.minimumSize()
                                widget_size = min_size if min_size.isValid() else QSize(320, 180)
                            if widget_size.width() > 0 and widget_size.height() > 0:
                                scaled = pixmap.scaled(
                                    widget_size,
                                    Qt.AspectRatioMode.KeepAspectRatio,
                                    Qt.TransformationMode.SmoothTransformation
                                )
                                if hasattr(video_widget, 'label'):
                                    video_widget.label.setPixmap(scaled)
                                elif hasattr(video_widget, '_video_label'):
                                    video_widget._video_label.setPixmap(scaled)
                                else:
                                    # create a lightweight QLabel if needed
                                    try:
                                        from PyQt6.QtWidgets import QLabel, QVBoxLayout, QSizePolicy
                                        video_widget._video_label = QLabel(video_widget)
                                        if not video_widget.layout():
                                            layout = QVBoxLayout(video_widget)
                                            layout.setContentsMargins(0, 0, 0, 0)
                                            video_widget.setLayout(layout)
                                        video_widget._video_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
                                        video_widget.layout().addWidget(video_widget._video_label)
                                        video_widget._video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                                        video_widget._video_label.setScaledContents(True)
                                        video_widget._video_label.setPixmap(scaled)
                                    except Exception:
                                        pass
                                try:
                                    self.last_input_pixmap[input_number] = scaled
                                except Exception:
                                    pass
                    except Exception:
                        continue
        except Exception as e:
            print(f"Error during deferred resize: {e}")
        try:
            overscan = app_config.get('ui.overscan', 1.00)
            fps = app_config.get('ui.preview_fps', 60)
            if self._graphics_output is not None:
                self._graphics_output.set_overscan(overscan)
                self._graphics_output.set_target_fps(fps)
            # Do NOT auto-apply any effect at startup (as per required workflow)
        except Exception as e:
            print(f"Error restoring settings: {e}")

        # Transitions (transition_manager already initialized in __init__)
        # Load transition settings from config
        self.selected_transition = app_config.get('ui.transition.type', self.selected_transition)
        self.transition_duration_ms = int(app_config.get('ui.transition.duration_ms', self.transition_duration_ms))
        self.transition_easing = app_config.get('ui.transition.easing', self.transition_easing)
        try:
            self.setup_transitions_panel()
        except Exception as e:
            print(f"Error setting up transitions panel: {e}")

        # Streaming controller (one-time init; skip if already done)
        if not hasattr(self, 'stream_controller') or self.stream_controller is None:
            self.stream_controller = StreamController(self)
            self.stream_controller.set_frame_provider(self._provide_stream_frame)
            try:
                self.stream_controller.statusChanged.connect(self._on_stream_status_changed)
            except Exception:
                pass

        # External Display Mirror controller - Enhanced version fixes pixelation
        if not hasattr(self, 'mirror_controller') or self.mirror_controller is None:
            try:
                if _USE_ENHANCED_MIRROR:
                    self.mirror_controller = EnhancedDisplayMirrorController(self)
                    print("Enhanced Display Mirror Controller initialized with pixelation fixes")
                else:
                    self.mirror_controller = DisplayMirrorController(self)
                    print("Standard Display Mirror Controller initialized")
                self.mirror_controller.set_frame_provider(self._provide_stream_frame)
            except Exception as e:
                print(f"Error initializing DisplayMirrorController: {e}")

        # Independent RTMP stream controllers (Stream 1 and Stream 2) - one-time init
        if not hasattr(self, 'stream_controllers') or not isinstance(self.stream_controllers, dict):
            try:
                print("🎬 Initializing stream controllers...")
                self.stream_controllers = {
                    1: StreamController(self),
                    2: StreamController(self),
                }
                for stream_id, sc in self.stream_controllers.items():
                    sc.set_frame_provider(self._provide_stream_frame)
                    sc.on_log(self._on_stream_log)
                    try:
                        sc.statusChanged.connect(lambda st, sid=int(stream_id): self._on_stream_status_changed(st, sid))
                    except Exception:
                        sc.statusChanged.connect(self._on_stream_status_changed)
                    print(f"✅ Stream {stream_id} controller initialized")
                self.stream1_active = False
                self.stream2_active = False
                print("✅ Stream controllers initialized successfully")
            except Exception as e:
                print(f"❌ Error initializing StreamControllers: {e}")
                import traceback
                traceback.print_exc()

        # Enhanced Recording controller - one-time init
        if not hasattr(self, 'recorder_controller') or self.recorder_controller is None:
            try:
                print("🎥 Initializing recording controller...")
                self.recorder_controller = RecorderController(self)
                self.recorder_controller.set_frame_provider(self._provide_stream_frame)
                self.recorder_controller.on_log(self._on_record_log)
                self.recorder_controller.statusChanged.connect(self._on_record_status_changed)
                self.recording = False
                print("✅ Recording controller initialized successfully")
                self.show_recording_health_info()
            except Exception as e:
                print(f"❌ Error initializing RecorderController: {e}")
                import traceback
                traceback.print_exc()

        # Install graphics output view if not present yet
        try:
            self._ensure_output_preview_label()
        except Exception:
            pass

        # Add compact Text Overlay mini bar beside Switching Controls (without altering other UI)
        # (Removed as we are moving it to the main layout in apply_modern_redesign)
        pass

    def apply_modern_redesign(self):
        print("🎨 Applying Premium Production Redesign...")
        
        # --- Wrap preview and program monitors in AspectRatioFrame for 16:9 ratio ---
        from PyQt6.QtWidgets import QVBoxLayout
        if hasattr(self, 'preview_container'):
            ar_preview = AspectRatioFrame()
            ar_preview.setObjectName('arPreview')
            ar_preview.setMinimumSize(320, 180)
            ar_preview.setSizePolicy(self.preview_container.sizePolicy())
            layout = QVBoxLayout(ar_preview)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.addWidget(self.preview_container)
            self.preview_container.setParent(ar_preview)
            self.preview_container = ar_preview
        if hasattr(self, 'program_container'):
            ar_program = AspectRatioFrame()
            ar_program.setObjectName('arProgram')
            ar_program.setMinimumSize(320, 180)
            ar_program.setSizePolicy(self.program_container.sizePolicy())
            layout = QVBoxLayout(ar_program)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.addWidget(self.program_container)
            self.program_container.setParent(ar_program)
            self.program_container = ar_program

        # Force a wider window size for desktop-app feel
        self.resize(1600, 950)
        
        # --- Premium Production Stylesheet ---
        self.setStyleSheet("""
            /* Global Reset & Typography */
            QMainWindow { background-color: #1C1C1C; color: #E0E0E0; }
            QWidget { font-family: 'Inter', 'SF Pro Display', 'Segoe UI', sans-serif; font-size: 13px; color: #E0E0E0; }
            
            /* Panels & Containers */
            QFrame { border: none; }
            
            /* Left Sidebar (Nav Rail) */
            QFrame#modernSidebar { 
                background-color: #222222; 
                border-right: 1px solid #333; 
            }
            
            /* Monitor Frames */
            QFrame#previewMonitor { 
                background-color: #000; 
                border: 2px solid #007AFF; 
                border-radius: 6px; 
            }
            QFrame#programMonitor { 
                background-color: #000; 
                border: 2px solid #FF3B30; 
                border-radius: 6px; 
            }
            
            /* Deck Panels (Inputs, Media, Effects) */
            QFrame#deckPanel {
                background-color: #252525;
                border: 1px solid #333;
                border-radius: 8px;
            }
            
            /* Status Bar */
            QFrame#statusBar {
                background-color: #181818;
                border-top: 1px solid #333;
            }
            
            /* Buttons - General Premium Style */
            QPushButton { 
                background-color: #333; 
                border: 1px solid #444; 
                border-radius: 4px; 
                padding: 6px 12px; 
                color: #EEE;
                font-weight: 500;
            }
            QPushButton:hover { background-color: #404040; border-color: #555; }
            QPushButton:pressed { background-color: #007AFF; border-color: #007AFF; color: white; }
            QPushButton:checked { background-color: #005BB5; border-color: #005BB5; color: white; }
            
            /* Sidebar Buttons (Nav Rail Icons) */
            QPushButton#sidebarBtn {
                background-color: transparent;
                border: none;
                border-radius: 8px;
                padding: 12px;
                text-align: center;
                color: #888;
            }
            QPushButton#sidebarBtn:hover { 
                background-color: #333; 
                color: #FFF;
            }
            QPushButton#sidebarBtn:checked { 
                background-color: #333; 
                color: #007AFF;
                border-left: 3px solid #007AFF;
            }
            
            /* Record Button Special State */
            QPushButton#recordBtn {
                color: #FF3B30;
            }
            QPushButton#recordBtn:checked {
                background-color: rgba(255, 59, 48, 0.1);
                color: #FF3B30;
                border: 1px solid #FF3B30;
            }
            
            /* Labels */
            QLabel#monitorLabel { 
                font-weight: 700; 
                font-size: 11px; 
                letter-spacing: 1px; 
                padding: 4px 8px;
                background: rgba(0,0,0,0.6);
                border-radius: 4px;
            }
            QLabel#sectionHeader { 
                font-weight: 600; 
                font-size: 11px; 
                color: #888; 
                text-transform: uppercase; 
                letter-spacing: 0.5px;
            }
            
            /* Status Bar Text */
            QLabel#statusLabel { font-family: 'Menlo', monospace; font-size: 11px; color: #888; }
            QLabel#statusValue { font-family: 'Menlo', monospace; font-size: 11px; color: #EEE; font-weight: bold; }
            
            /* Sliders */
            QSlider::groove:horizontal { background: #333; height: 4px; border-radius: 2px; }
            QSlider::sub-page:horizontal { background: #007AFF; border-radius: 2px; }
            QSlider::handle:horizontal { 
                background: #E0E0E0; 
                width: 14px; height: 14px; 
                margin: -5px 0; 
                border-radius: 7px; 
                border: 1px solid #000;
            }
            
            /* Scrollbars */
            QScrollBar:vertical { background: #1C1C1C; width: 10px; margin: 0; }
            QScrollBar::handle:vertical { background: #444; min-height: 20px; border-radius: 5px; margin: 2px; }
            QScrollBar::handle:vertical:hover { background: #555; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
        """)

        # 1. Setup Main Layout Structure
        new_root_widget = QWidget()
        new_root_layout = QVBoxLayout(new_root_widget)
        new_root_layout.setContentsMargins(0, 0, 0, 0)
        new_root_layout.setSpacing(0)
        
        # Upper Area (Sidebar + Content)
        upper_area = QWidget()
        upper_layout = QHBoxLayout(upper_area)
        upper_layout.setContentsMargins(0, 0, 0, 0)
        upper_layout.setSpacing(0)
        
        # --- Left Sidebar (Nav Rail) ---
        sidebar_frame = QFrame()
        sidebar_frame.setObjectName("modernSidebar")
        sidebar_frame.setFixedWidth(80) 
        sidebar_layout = QVBoxLayout(sidebar_frame)
        sidebar_layout.setContentsMargins(0, 20, 0, 20)
        sidebar_layout.setSpacing(16)
        
        self.workspace_btns = []
        self.workspace_stack = QStackedWidget() # Pre-declare
        
        def create_ws_btn(name, icon_text, index, tooltip):
            btn = QPushButton()
            btn.setObjectName("sidebarBtn")
            btn.setCheckable(True)
            btn.setFixedSize(60, 60)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setToolTip(tooltip)
            
            # Layout for icon + text
            lay = QVBoxLayout(btn)
            lay.setContentsMargins(0,0,0,0)
            lay.setSpacing(4)
            lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
            # Using Emoji/Text for now as we want clean "Proper" icons
            # Ideally these would be SVG icons
            icn = QLabel(icon_text)
            icn.setStyleSheet("font-size: 24px; color: #888; background: transparent;")
            icn.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
            txt = QLabel(name)
            txt.setStyleSheet("font-size: 10px; font-weight: 600; color: #888; background: transparent;")
            txt.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
            lay.addWidget(icn)
            lay.addWidget(txt)
            
            # Connect
            btn.clicked.connect(lambda: self.set_active_workspace(index))
            
            sidebar_layout.addWidget(btn)
            self.workspace_btns.append((btn, icn, txt))
            return btn

        # Workspace Buttons
        create_ws_btn("GENERAL", "🏠", 0, "General Switching & Effects")
        create_ws_btn("STREAM", "📡", 1, "Streaming Controls")
        create_ws_btn("RECORD", "🔴", 2, "Recording Controls")
        
        sidebar_layout.addStretch()
        
        # Settings Button at bottom
        # create_ws_btn("SETTINGS", "⚙️", 3, "Application Settings") # Optional
        
        # Define Workspace Switcher
        def set_active_workspace(index):
            if hasattr(self, 'workspace_stack'):
                self.workspace_stack.setCurrentIndex(index)

            # Keep monitor area height consistent across all workspaces (baseline from General)
            try:
                if hasattr(self, '_apply_monitor_area_height_policy'):
                    self._apply_monitor_area_height_policy()
            except Exception:
                pass
            
            # Update Styles
            for i, (btn, icn, txt) in enumerate(self.workspace_btns):
                if i == index:
                    btn.setChecked(True)
                    btn.setStyleSheet("background-color: #252525; border-left: 3px solid #007AFF;")
                    icn.setStyleSheet("font-size: 24px; color: #EEE; background: transparent;")
                    txt.setStyleSheet("font-size: 10px; font-weight: 600; color: #EEE; background: transparent;")
                else:
                    btn.setChecked(False)
                    btn.setStyleSheet("background-color: transparent; border: none;")
                    icn.setStyleSheet("font-size: 24px; color: #888; background: transparent;")
                    txt.setStyleSheet("font-size: 10px; font-weight: 600; color: #888; background: transparent;")
                    
        self.set_active_workspace = set_active_workspace

        # --- Main Content Area ---
        # Create vertical layout for content without scrolling Preview/Program
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(12, 12, 12, 12)
        content_layout.setSpacing(12)
        
        # 1. Monitors Section (Preview | Program)
        # Wrap monitors + switcher into a single widget so we can lock its height.
        self.monitor_area = QWidget()
        monitor_area_layout = QVBoxLayout(self.monitor_area)
        monitor_area_layout.setContentsMargins(0, 0, 0, 0)
        monitor_area_layout.setSpacing(8)
        
        # MAKE VIDEO HEIGHT RESPONSIVE (35% of window height, with min/max constraints)
        self._monitor_height_percentage = 0.35  # 35% of window height for videos
        self._monitor_min_height = 200
        self._monitor_max_height = 400
        
        def _update_monitor_height():
            try:
                # Do NOT set fixed height - use soft constraints instead
                # Allow the layout to handle sizing with aspect ratio policy
                pass
            except Exception:
                pass
        
        self._update_monitor_height = _update_monitor_height

        def _apply_monitor_area_height_policy():
            try:
                if not hasattr(self, 'monitor_area') or self.monitor_area is None:
                    return
                # Monitor area uses heightForWidth layout policy for responsive sizing
            except Exception:
                pass

        self._apply_monitor_area_height_policy = _apply_monitor_area_height_policy
        self._apply_monitor_area_height_policy()

        # --- FIXED MONITOR LAYOUT ---
        # Create Preview Monitor with title
        preview_container_frame = QFrame()
        preview_container_frame.setObjectName("previewContainer")
        preview_container_frame.setStyleSheet("QFrame#previewContainer { background-color: #1a1a1a; border: none; }")
        preview_container_frame.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        preview_container_layout = QVBoxLayout(preview_container_frame)
        preview_container_layout.setContentsMargins(0, 0, 0, 4)  # Add 4px bottom margin for safety
        preview_container_layout.setSpacing(6)
        
        preview_title = QLabel("Preview")
        preview_title.setStyleSheet("color: #0078d4; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px;")
        preview_container_layout.addWidget(preview_title)
        
        preview_aspect = AspectRatioFrame()
        preview_aspect.setObjectName("previewMonitor")
        preview_aspect.setMinimumSize(320, 180)  # Only set minimum, let heightForWidth handle resizing
        # DO NOT set MaximumSize - it prevents free window resizing
        preview_aspect.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        # ENABLE CLIPPING: Prevent overlays from painting outside preview frame bounds (Windows fix)
        preview_aspect.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, True)
        preview_aspect.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        preview_aspect.setStyleSheet("QFrame#previewMonitor { overflow: hidden; border: 2px solid #0078d4; border-radius: 4px; background-color: black; }")
        preview_layout = QVBoxLayout(preview_aspect)
        preview_layout.setContentsMargins(2, 2, 2, 2)
        preview_layout.setSpacing(0)
        self.preview_video_label = QLabel("Select a source to preview")
        self.preview_video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_video_label.setStyleSheet("background-color: black; color: rgba(255, 255, 255, 0.4); font-size: 13px; font-weight: 500;")
        preview_layout.addWidget(self.preview_video_label, 1)
        
        preview_container_layout.addWidget(preview_aspect, 1)

        # Create Program Monitor with title
        program_container_frame = QFrame()
        program_container_frame.setObjectName("programContainer")
        program_container_frame.setStyleSheet("QFrame#programContainer { background-color: #1a1a1a; border: none; }")
        program_container_frame.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        program_container_layout = QVBoxLayout(program_container_frame)
        program_container_layout.setContentsMargins(0, 0, 0, 4)  # Add 4px bottom margin for safety
        program_container_layout.setSpacing(6)
        
        program_title = QLabel("Program Live")
        program_title.setStyleSheet("color: #d13438; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px;")
        program_container_layout.addWidget(program_title)
        
        program_aspect = AspectRatioFrame()
        program_aspect.setObjectName("programMonitor")
        program_aspect.setMinimumSize(320, 180)  # Only set minimum, let heightForWidth handle resizing
        # DO NOT set MaximumSize - it prevents free window resizing
        program_aspect.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        # ENABLE CLIPPING: Prevent overlays from painting outside program frame bounds (Windows fix)
        program_aspect.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, True)
        program_aspect.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        program_aspect.setStyleSheet("QFrame#programMonitor { overflow: hidden; border: 2px solid #d13438; border-radius: 4px; background-color: black; }")
        program_layout = QVBoxLayout(program_aspect)
        program_layout.setContentsMargins(2, 2, 2, 2)
        program_layout.setSpacing(0)
        if hasattr(self, 'outputPreview'):
            self.outputPreview.setParent(None)
            # Ensure outputPreview respects the AspectRatioFrame's sizing
            self.outputPreview.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            self.outputPreview.setMinimumSize(320, 180)  # Match container minimum
            program_layout.addWidget(self.outputPreview, 1)
            self.outputPreview.setStyleSheet("background-color: black; border: none; border-radius: 6px;")
            self.outputPreview.show()
        
        program_container_layout.addWidget(program_aspect, 1)

        # --- FIXED UI LAYOUT ---
        # Group monitors and transition bar vertically
        # --- Create transition bar widgets first ---
        self.lbl_switch_transition = QLabel("Transition: None")
        self.lbl_switch_transition.setStyleSheet("color:#cfcfcf;font-weight:600;")

        self.slider_switch_dur = QSlider(Qt.Orientation.Horizontal)
        self.slider_switch_dur.setRange(100, 2000)
        self.slider_switch_dur.setSingleStep(50)
        self.slider_switch_dur.setPageStep(100)
        try:
            self.slider_switch_dur.setValue(int(getattr(self, 'transition_duration_ms', 700) or 700))
        except Exception:
            self.slider_switch_dur.setValue(700)
        self.slider_switch_dur.setFixedWidth(180)

        # --- Now build the monitor and transition bar layout ---
        monitor_group_layout = QVBoxLayout()
        monitor_group_layout.setContentsMargins(8, 8, 8, 0)
        monitor_group_layout.setSpacing(8)
        
        monitors_layout = QHBoxLayout()
        monitors_layout.setContentsMargins(0, 0, 0, 0)
        monitors_layout.setSpacing(12)
        monitors_layout.addWidget(preview_container_frame, 1)
        monitors_layout.addWidget(program_container_frame, 1)
        monitor_group_layout.addLayout(monitors_layout, 1)

        switcher_bar = QFrame()
        switcher_bar.setFixedHeight(54)
        switcher_bar.setObjectName("switcherBar")
        switcher_bar.setStyleSheet("QFrame#switcherBar{background-color:#1a1a1a;border:1px solid #2c2c2c;border-radius:10px;}")
        sw_layout = QHBoxLayout(switcher_bar)
        sw_layout.setContentsMargins(16, 8, 16, 8)
        sw_layout.setSpacing(12)
        monitor_group_layout.addWidget(switcher_bar, 0, Qt.AlignmentFlag.AlignHCenter)

        # Responsive: monitor group gets moderate stretch (2), lower content gets stretch (1)
        # This creates a 2:1 ratio where monitors take 2/3 of space, workspace takes 1/3
        content_layout.addLayout(monitor_group_layout, 2)
        # NOTE: Do NOT add workspace_stack here - it's added later at full configuration
        self.slider_switch_dur.setToolTip("Transition Duration (ms)")
        self.slider_switch_dur.setStyleSheet("""
            QSlider::groove:horizontal { height: 4px; background: #333; border-radius: 2px; }
            QSlider::handle:horizontal { width: 14px; height: 14px; margin: -5px 0; background: #FF9500; border-radius: 7px; }
            QSlider::sub-page:horizontal { background: #FF9500; border-radius: 2px; }
        """)

        self.lbl_switch_dur = QLabel(f"{self.slider_switch_dur.value()} ms")
        self.lbl_switch_dur.setStyleSheet("color:#9f9f9f;")

        def _on_dur_changed(v: int):
            try:
                self.transition_duration_ms = int(v)
                app_config.set('ui.transition.duration_ms', int(v))
                app_config.save_settings()
            except Exception:
                pass
            try:
                self.lbl_switch_dur.setText(f"{int(v)} ms")
            except Exception:
                pass
        self.slider_switch_dur.valueChanged.connect(_on_dur_changed)

        # Buttons
        self.btn_cut = QPushButton("CUT")
        self.btn_cut.setFixedSize(110, 36)
        self.btn_cut.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_cut.setStyleSheet("QPushButton{background:#2b2b2b;color:#fff;border:1px solid #3a3a3a;border-radius:8px;font-weight:800;} QPushButton:hover{background:#353535;} QPushButton:pressed{background:#1f1f1f;}")
        self.btn_cut.clicked.connect(self.cut_transition)

        self.btn_auto = QPushButton("AUTO")
        self.btn_auto.setFixedSize(110, 36)
        self.btn_auto.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_auto.setStyleSheet("QPushButton{background:#007AFF;color:#fff;border:none;border-radius:8px;font-weight:900;} QPushButton:hover{background:#1f8bff;} QPushButton:pressed{background:#0b5ec2;}")
        self.btn_auto.clicked.connect(self.auto_transition)

        sw_layout.addWidget(self.lbl_switch_transition)
        sw_layout.addSpacing(6)
        sw_layout.addWidget(self.slider_switch_dur)
        sw_layout.addWidget(self.lbl_switch_dur)
        sw_layout.addStretch(1)
        sw_layout.addWidget(self.btn_cut)
        sw_layout.addWidget(self.btn_auto)

        _ = None

        # Add monitors directly to monitor_group_layout (not monitor_area_layout which is now unused)
        # Note: monitor_area and monitor_area_layout are leftover from older code structure
        # 2. Lower Control Deck using Workspace Stack
        self.workspace_stack = QStackedWidget()
        self.workspace_stack.setContentsMargins(0,0,0,0)
        try:
            # Prevent non-General pages from forcing a larger minimum height (which would shrink monitors)
            # Allow the workspace to expand normally; monitor_area height is controlled separately.
            self.workspace_stack.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            self.workspace_stack.setMinimumHeight(200)  # Soft minimum for controls section
        except Exception:
            pass
        
        # Add workspace stack to content with LOW stretch factor (1) so it takes remaining space
        content_layout.addWidget(self.workspace_stack, 1)
        
        # --- WORKSPACE 1: GENERAL (Standard Inputs & Effects) ---
        general_page = QWidget()
        general_deck = QHBoxLayout(general_page)
        general_deck.setSpacing(8)
        general_deck.setContentsMargins(0, 0, 0, 0)
        
        # [Moved Existing Logic Here]
        
        # --- Left Column: Inputs & Media ---
        left_deck = QVBoxLayout()
        left_deck.setSpacing(8)
        
        # Inputs Section
        inputs_container = QFrame()
        inputs_container.setObjectName("deckPanel")
        inputs_layout = QVBoxLayout(inputs_container)
        inputs_layout.setContentsMargins(8, 8, 8, 8)
        inputs_layout.setSpacing(8)
        
        in_lbl = QLabel("INPUTS")
        in_lbl.setObjectName("sectionHeader")
        inputs_layout.addWidget(in_lbl)
        
        if not hasattr(self, '_visible_input_slots'):
            try:
                # OBS-style: start small and let user add slots via '+'
                self._visible_input_slots = int(app_config.get('ui.inputs.visible_slots', 1) or 1)
            except Exception:
                self._visible_input_slots = 1

        def _make_add_tile(kind: str):
            btn = QPushButton("+")
            btn.setFixedHeight(96)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(
                "QPushButton{background:#151515;color:#9a9a9a;border:1px dashed #3a3a3a;border-radius:10px;font-size:28px;font-weight:700;}"
                "QPushButton:hover{background:#1b1b1b;border-color:#5a5a5a;color:#d0d0d0;}"
                "QPushButton:pressed{background:#101010;}"
            )
            btn.setToolTip(f"Add {kind}")
            return btn

        inputs_grid = QGridLayout()
        inputs_grid.setHorizontalSpacing(8)
        inputs_grid.setVerticalSpacing(8)
        inputs_grid.setContentsMargins(0, 0, 0, 0)
        inputs_cols = 3

        def _refresh_inputs_grid():
            while inputs_grid.count():
                item = inputs_grid.takeAt(0)
                if item and item.widget():
                    item.widget().setParent(None)

            visible = max(1, min(3, int(getattr(self, '_visible_input_slots', 1) or 1)))
            for i in range(1, 4):
                w = getattr(self, f'inputDisplay{i}', None)
                if not w:
                    continue
                w.setParent(inputs_container)
                w.setStyleSheet(
                    "QFrame{background-color:#1a1a1a;border-radius:10px;border:1px solid #333;}"
                    "QFrame:hover{background-color:#252525;border:1px solid #555;}"
                    "QLabel{background-color:transparent;color:#ddd;font-weight:500;}"
                )
                try:
                    w.setMinimumHeight(150)
                    w.setMaximumWidth(320)  # Constrain card width to prevent horizontal stretching
                except Exception:
                    pass

                # Add a compact footer strip to reduce empty space (visual parity with Media tiles)
                try:
                    existing_footer = w.findChild(QFrame, f"inputTileFooter{i}")
                    if existing_footer is not None:
                        existing_footer.setParent(None)
                        existing_footer.deleteLater()
                except Exception:
                    pass
                try:
                    if w.layout() is not None:
                        footer = QFrame(w)
                        footer.setObjectName(f"inputTileFooter{i}")
                        footer.setFixedHeight(24)
                        footer.setStyleSheet("QFrame{background:#151515;border:1px solid #2f2f2f;border-radius:8px;}")
                        fl = QHBoxLayout(footer)
                        fl.setContentsMargins(8, 2, 8, 2)
                        fl.setSpacing(8)

                        dot = QFrame(footer)
                        dot.setFixedSize(8, 8)
                        dot.setStyleSheet("background:#3a3a3a;border-radius:4px;")

                        txt = QLabel("No camera")
                        txt.setStyleSheet("color:#9f9f9f;font-size:11px;")

                        fl.addWidget(dot)
                        fl.addWidget(txt)
                        fl.addStretch(1)

                        w.layout().addWidget(footer)

                        if not hasattr(self, '_input_footer_widgets'):
                            self._input_footer_widgets = {}
                        self._input_footer_widgets[int(i)] = {'dot': dot, 'label': txt}
                        try:
                            if hasattr(self, '_update_input_footer'):
                                self._update_input_footer(int(i))
                        except Exception:
                            pass
                except Exception:
                    pass
                if i <= visible:
                    r = (i - 1) // inputs_cols
                    c = (i - 1) % inputs_cols
                    inputs_grid.addWidget(w, r, c)
                    w.show()
                else:
                    w.hide()

            if visible < 3:
                add_btn = _make_add_tile('Input')
                next_slot = visible + 1
                add_btn.clicked.connect(lambda _=False, n=next_slot: self._add_input_slot(n))
                r = visible // inputs_cols
                c = visible % inputs_cols
                inputs_grid.addWidget(add_btn, r, c)

            # Set column stretches to 0 to prevent horizontal stretching, then add right spacer
            for col in range(inputs_cols):
                inputs_grid.setColumnStretch(col, 0)
            # Add stretch at the end to push cards left
            inputs_grid.addItem(QSpacerItem(0, 0, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum), 2, inputs_cols)
            inputs_grid.setColumnStretch(inputs_cols, 1)  # Make spacer column expand
            # Set row stretches to prevent card overlapping when window is resized/maximized
            for row in range(3):
                inputs_grid.setRowStretch(row, 0)  # Cards maintain their natural height

        def _add_input_slot(self_ref, slot: int):
            try:
                self_ref._visible_input_slots = max(int(getattr(self_ref, '_visible_input_slots', 0) or 0), int(slot))
                app_config.set('ui.inputs.visible_slots', int(self_ref._visible_input_slots))
                app_config.save_settings()
            except Exception:
                pass
            try:
                _refresh_inputs_grid()
            except Exception:
                pass
            try:
                self_ref.show_camera_selection_dialog(int(slot))
            except Exception:
                pass

        self._add_input_slot = lambda slot: _add_input_slot(self, slot)

        _refresh_inputs_grid()
        inputs_layout.addLayout(inputs_grid)
        left_deck.addWidget(inputs_container)
        
        # Media Section
        media_container = QFrame()
        media_container.setObjectName("deckPanel")
        media_layout = QVBoxLayout(media_container)
        media_layout.setContentsMargins(8, 8, 8, 8)
        media_layout.setSpacing(8)
        
        med_lbl = QLabel("MEDIA PLAYERS")
        med_lbl.setObjectName("sectionHeader")
        media_layout.addWidget(med_lbl)
        
        if not hasattr(self, '_visible_media_slots'):
            try:
                # OBS-style: start small and let user add slots via '+'
                self._visible_media_slots = int(app_config.get('ui.media.visible_slots', 1) or 1)
            except Exception:
                self._visible_media_slots = 1

        media_grid = QGridLayout()
        media_grid.setHorizontalSpacing(8)
        media_grid.setVerticalSpacing(8)
        media_grid.setContentsMargins(0, 0, 0, 0)
        media_cols = 3

        def _refresh_media_grid():
            while media_grid.count():
                item = media_grid.takeAt(0)
                if item and item.widget():
                    item.widget().setParent(None)

            visible = max(1, min(3, int(getattr(self, '_visible_media_slots', 1) or 1)))
            for i in range(1, 4):
                w = getattr(self, f'mediaDisplay{i}', None)
                if not w:
                    continue
                w.setParent(media_container)
                w.setStyleSheet(
                    "QFrame{background-color:#1a1a1a;border-radius:10px;border:1px solid #333;}"
                    "QFrame:hover{background-color:#252525;border:1px solid #555;}"
                    "QLabel{background-color:transparent;color:#ddd;font-weight:500;}"
                )
                try:
                    w.setMinimumHeight(150)
                    w.setMaximumWidth(320)  # Constrain card width to prevent horizontal stretching
                except Exception:
                    pass
                if i <= visible:
                    r = (i - 1) // media_cols
                    c = (i - 1) % media_cols
                    media_grid.addWidget(w, r, c)
                    w.show()
                else:
                    w.hide()

            if visible < 3:
                add_btn = _make_add_tile('Media')
                next_slot = visible + 1
                add_btn.clicked.connect(lambda _=False, n=next_slot: self._add_media_slot(n))
                r = visible // media_cols
                c = visible % media_cols
                media_grid.addWidget(add_btn, r, c)

            # Set column stretches to 0 to prevent horizontal stretching, then add right spacer
            for col in range(media_cols):
                media_grid.setColumnStretch(col, 0)
            # Add stretch at the end to push cards left
            media_grid.addItem(QSpacerItem(0, 0, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum), 2, media_cols)
            media_grid.setColumnStretch(media_cols, 1)  # Make spacer column expand
            # Set row stretches to prevent card overlapping when window is resized/maximized
            for row in range(3):
                media_grid.setRowStretch(row, 0)  # Cards maintain their natural height

        def _add_media_slot(self_ref, slot: int):
            try:
                self_ref._visible_media_slots = max(int(getattr(self_ref, '_visible_media_slots', 0) or 0), int(slot))
                app_config.set('ui.media.visible_slots', int(self_ref._visible_media_slots))
                app_config.save_settings()
            except Exception:
                pass
            try:
                _refresh_media_grid()
            except Exception:
                pass
            try:
                self_ref.show_media_selection_dialog(int(slot))
            except Exception:
                pass

        self._add_media_slot = lambda slot: _add_media_slot(self, slot)

        _refresh_media_grid()
        media_layout.addLayout(media_grid)
        left_deck.addWidget(media_container)

        # Move media playback controls into each Media tile (play/pause + seek)
        # This reuses existing UI widgets to avoid breaking playback/seek logic.
        try:
            pb_map = {1: 'pushButton_19', 2: 'pushButton_20', 3: 'pushButton_21'}
            sl_map = {1: 'horizontalSlider', 2: 'horizontalSlider_2', 3: 'horizontalSlider_3'}

            for i in (1, 2, 3):
                tile = getattr(self, f'mediaDisplay{i}', None)
                if tile is None:
                    continue

                # If redesign runs multiple times, remove previously injected control strip
                try:
                    existing = tile.findChild(QFrame, f"mediaTileControls{i}")
                    if existing is not None:
                        existing.setParent(None)
                        existing.deleteLater()
                except Exception:
                    pass

                play_btn = getattr(self, pb_map.get(i, ''), None)
                seek_sl = getattr(self, sl_map.get(i, ''), None)
                if play_btn is None and seek_sl is None:
                    continue

                # Ensure tile has a layout
                if tile.layout() is None:
                    lay = QVBoxLayout(tile)
                    lay.setContentsMargins(4, 2, 4, 2)
                    lay.setSpacing(6)
                    tile.setLayout(lay)

                ctrl = QFrame(tile)
                ctrl.setObjectName(f"mediaTileControls{i}")
                ctrl.setFixedHeight(24)
                ctrl.setStyleSheet(
                    "QFrame{background:#151515;border:1px solid #2f2f2f;border-radius:8px;}"
                )
                h = QHBoxLayout(ctrl)
                h.setContentsMargins(8, 2, 8, 2)
                h.setSpacing(8)

                if play_btn is not None:
                    play_btn.setParent(ctrl)
                    try:
                        play_btn.setMinimumSize(22, 22)
                        play_btn.setMaximumSize(22, 22)
                        play_btn.setStyleSheet("QPushButton{background:transparent;border:none;} QPushButton:hover{background:#2a2a2a;border-radius:6px;}")
                    except Exception:
                        pass
                    h.addWidget(play_btn)

                if seek_sl is not None:
                    seek_sl.setParent(ctrl)
                    try:
                        # match seek_media() contract (0-100)
                        seek_sl.setRange(0, 100)
                        seek_sl.setFixedHeight(16)
                        seek_sl.setStyleSheet(
                            "QSlider::groove:horizontal{height:4px;background:#333;border-radius:2px;}"
                            "QSlider::handle:horizontal{width:12px;height:12px;margin:-4px 0;background:#007AFF;border-radius:6px;}"
                            "QSlider::sub-page:horizontal{background:#007AFF;border-radius:2px;}"
                        )
                    except Exception:
                        pass
                    h.addWidget(seek_sl, 1)

                # Append controls to bottom of the tile
                try:
                    tile.layout().addWidget(ctrl)
                except Exception:
                    pass
        except Exception:
            pass
        
        general_deck.addLayout(left_deck, 40)
        
        # --- Middle Column: Effects ---
        middle_deck = QVBoxLayout()
        effects_container = QFrame()
        effects_container.setObjectName("deckPanel")
        effects_layout = QVBoxLayout(effects_container)
        effects_layout.setContentsMargins(8, 8, 8, 8)
        effects_layout.setSpacing(8)
        
        eff_lbl = QLabel("EFFECTS & GRAPHICS")
        eff_lbl.setObjectName("sectionHeader")
        effects_layout.addWidget(eff_lbl)
        
        if hasattr(self, 'premiere_effects_panel'):
            self.premiere_effects_panel.setParent(effects_container)
            effects_layout.addWidget(self.premiere_effects_panel)
            self.premiere_effects_panel.show()
            if hasattr(self, 'tabWidget_effects'):
                self.tabWidget_effects.hide()
        elif hasattr(self, 'tabWidget_effects'):
            self.tabWidget_effects.setParent(effects_container)
            effects_layout.addWidget(self.tabWidget_effects)
            self.tabWidget_effects.show()
            
        middle_deck.addWidget(effects_container)
        general_deck.addLayout(middle_deck, 35)
        
        # --- Right Column: Transitions & Switching ---
        right_deck = QVBoxLayout()
        right_deck.setSpacing(8)
        
        # Text Overlay Settings
        overlay_container = QFrame()
        overlay_container.setObjectName("deckPanel")
        overlay_layout = QVBoxLayout(overlay_container)
        overlay_layout.setContentsMargins(8, 8, 8, 8)
        overlay_layout.setSpacing(8)
        
        ov_lbl = QLabel("OVERLAY SETTINGS")
        ov_lbl.setObjectName("sectionHeader")
        overlay_layout.addWidget(ov_lbl)
        
        self.textOverlayMini = TextOverlayMiniBar(self)
        overlay_layout.addWidget(self.textOverlayMini)
        
        # Wire to graphics output
        def _on_overlay_changed(d: dict):
            # Adapt mini overlay props to the global text overlay renderer settings
            try:
                from PyQt6.QtGui import QColor
                # We keep preview/program text settings separate; do not touch Program here

                def _to_qcolor_from_rgba(v):
                    c = QColor()
                    try:
                        c.setRgba(int(v))
                    except Exception:
                        # Fallback to white/black
                        c = QColor(255, 255, 255) if 'color' in d else QColor(0, 0, 0)
                    return c

                # Map properties
                vis = bool(d.get('visible', True))
                txt = str(d.get('text', '')) if vis else ''
                font_family = str(d.get('font_family', ''))
                try:
                    font_size = int(d.get('font_size', 36))
                except Exception:
                    font_size = 36

                c_text = _to_qcolor_from_rgba(d.get('color', 0xFFFFFFFF))
                c_stroke = _to_qcolor_from_rgba(d.get('stroke_color', 0xFF000000))
                c_bg = _to_qcolor_from_rgba(d.get('bg_color', 0x00000000))

                try:
                    stroke_w = int(d.get('stroke_width', 0))
                except Exception:
                    stroke_w = 0

                try:
                    pos_x = int(d.get('pos_x', 50))
                    pos_y = int(d.get('pos_y', 90))
                except Exception:
                    pos_x, pos_y = 50, 90

                align = str(d.get('anchor', 'center'))

                bg_enabled = bool(d.get('bg_enabled', False))
                bg_opacity = float(c_bg.alpha() / 255.0)

                settings = {
                    'text': txt,
                    'font_family': font_family,
                    'font_size': font_size,
                    'text_color': c_text.name(),
                    'stroke_color': c_stroke.name(),
                    'stroke_width': stroke_w,
                    'outline_enabled': stroke_w > 0,
                    'position_x': pos_x,
                    'position_y': pos_y,
                    'alignment': align,
                    'bg_enabled': bg_enabled,
                    'bg_color': c_bg.name(),
                    'bg_opacity': bg_opacity,
                }

                # Store for PREVIEW - position_y/alignment come from user settings, not forced
                # Both preview and program use the same position so they match visually
                enforced_settings = dict(settings)
                # Do NOT force position_y or alignment - use what user configured
                # This ensures preview and program text appear at identical positions
                
                # Store for preview right now
                try:
                    self.preview_text_settings = enforced_settings
                    # DO NOT touch program_text_settings here
                    # Program settings only update when CUT or AUTO is clicked
                except Exception:
                    pass
                # Refresh Preview monitor immediately
                try:
                    pv = getattr(self, 'active_preview_source', None)
                    if pv and isinstance(pv, tuple) and len(pv) == 2:
                        st, idx = pv[0], int(pv[1])
                        frame = None
                        if st == 'input':
                            frame = self.last_input_image.get(idx) if hasattr(self, 'last_input_image') else None
                        elif st == 'media':
                            frame = self.last_media_image.get(idx) if hasattr(self, 'last_media_image') else None
                        self._update_preview_monitor(frame, st, idx)
                except Exception:
                    pass
            except Exception as e:
                print(f"Overlay mapping error: {e}")
        self.textOverlayMini.overlayChanged.connect(_on_overlay_changed)
        
        # Apply defaults once UI is ready
        def _emit_defaults():
            try:
                p = self.textOverlayMini.props_ref.props
                init = {
                    **p,
                    'color': p['color'].rgba(),
                    'stroke_color': p['stroke_color'].rgba(),
                    'bg_color': p['bg_color'].rgba(),
                }
                _on_overlay_changed(init)
            except Exception:
                pass
        QTimer.singleShot(0, _emit_defaults)

        right_deck.addWidget(overlay_container, 0)

        # Transitions
        trans_container = QFrame()
        trans_container.setObjectName("deckPanel")
        trans_layout = QVBoxLayout(trans_container)
        trans_layout.setContentsMargins(8, 8, 8, 8)
        trans_layout.setSpacing(8)
        
        tr_lbl = QLabel("TRANSITIONS")
        tr_lbl.setObjectName("sectionHeader")
        trans_layout.addWidget(tr_lbl)
        
        if hasattr(self, 'tabWidget_transitions'):
            self.tabWidget_transitions.setParent(trans_container)
            trans_layout.addWidget(self.tabWidget_transitions)
            self.tabWidget_transitions.show()
            
        right_deck.addWidget(trans_container, 1)
        
        general_deck.addLayout(right_deck, 25)
        
        # Wrap general_page in a scroll area for vertical scrolling of controls
        general_scroll = QScrollArea()
        general_scroll.setWidgetResizable(True)
        general_scroll.setFrameShape(QFrame.Shape.NoFrame)
        general_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        general_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        general_scroll.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        general_scroll.setWidget(general_page)
        
        self.workspace_stack.addWidget(general_scroll)
        # --- Ensure transitions panel and overlay preview are always initialized ---
        try:
            self.setup_transitions_panel()
        except Exception as e:
            print(f"[FIX] Error forcing transitions panel: {e}")
        try:
            self._ensure_output_preview_label()
        except Exception as e:
            print(f"[FIX] Error forcing overlay preview: {e}")
        
        # --- WORKSPACE 2: STREAMING ---
        streaming_page = QWidget()
        try:
            streaming_page.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            streaming_page.setMinimumHeight(0)
        except Exception:
            pass
        streaming_page_layout = QVBoxLayout(streaming_page)
        streaming_page_layout.setContentsMargins(0, 0, 0, 0)
        streaming_page_layout.setSpacing(0)

        streaming_scroll = QScrollArea()
        streaming_scroll.setWidgetResizable(True)
        streaming_scroll.setFrameShape(QFrame.Shape.NoFrame)
        streaming_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        try:
            streaming_scroll.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            streaming_scroll.setMinimumHeight(0)
        except Exception:
            pass
        try:
            streaming_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        except Exception:
            pass

        streaming_inner = QWidget()
        try:
            streaming_inner.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            streaming_inner.setMinimumHeight(0)
        except Exception:
            pass
        streaming_layout = QHBoxLayout(streaming_inner)
        streaming_layout.setSpacing(8)
        streaming_layout.setContentsMargins(8, 8, 8, 8)
        
        # We need to import the panels here or at top
        try:
            from streaming_settings_dialog_improved import StreamingSettingsPanel
            
            # Stream 1 Panel
            s1_container = QFrame()
            s1_container.setObjectName("deckPanel")
            s1_layout = QVBoxLayout(s1_container)
            s1_layout.setContentsMargins(0,0,0,0)
            
            # Header 1
            h1 = QLabel("STREAM 1 (Primary)")
            try:
                h1.setFont(QFont('', 14, QFont.Weight.Bold))
            except Exception:
                pass
            h1.setStyleSheet("color: white; padding: 8px; background-color: #333; border-top-left-radius: 8px; border-top-right-radius: 8px;")
            h1.setAlignment(Qt.AlignmentFlag.AlignCenter)
            s1_layout.addWidget(h1)
            
            self.stream1_panel = StreamingSettingsPanel(self, 1, app_config)
            s1_layout.addWidget(self.stream1_panel)

            # Bottom status + log
            s1_footer = QFrame()
            s1_footer.setObjectName("streamFooter")
            s1_footer.setStyleSheet("QFrame#streamFooter{background:#121212;border:1px solid #2a2a2a;border-radius:10px;}")
            s1_footer_l = QVBoxLayout(s1_footer)
            s1_footer_l.setContentsMargins(10, 8, 10, 8)
            s1_footer_l.setSpacing(8)

            s1_row = QHBoxLayout()
            s1_row.setContentsMargins(0, 0, 0, 0)
            s1_row.setSpacing(10)

            pill_base = "QLabel{background:#1a1a1a;border:1px solid #2f2f2f;border-radius:8px;padding:4px 8px;font-size:11px;font-weight:700;color:#cfcfcf;}"
            s1_dot = QFrame()
            s1_dot.setFixedSize(10, 10)
            s1_dot.setStyleSheet("background:#3a3a3a;border-radius:5px;")
            s1_status = QLabel("READY")
            s1_status.setStyleSheet(pill_base)
            s1_uptime = QLabel("Uptime 00:00:00")
            s1_uptime.setStyleSheet(pill_base)
            s1_bitrate = QLabel("Bitrate — kbps")
            s1_bitrate.setStyleSheet(pill_base)

            s1_row.addWidget(s1_dot)
            s1_row.addWidget(s1_status)
            s1_row.addStretch(1)
            s1_row.addWidget(s1_uptime)
            s1_row.addWidget(s1_bitrate)

            s1_log = QTextEdit()
            s1_log.setReadOnly(True)
            s1_log.setFixedHeight(58)
            s1_log.setStyleSheet("QTextEdit{background:#0b0b0b;border:1px solid #232323;border-radius:8px;color:#cfcfcf;padding:6px;font-size:11px;}")

            s1_footer_l.addLayout(s1_row)
            s1_footer_l.addWidget(s1_log)
            s1_layout.addWidget(s1_footer)

            streaming_layout.addWidget(s1_container)
            
            # Stream 2 Panel
            s2_container = QFrame()
            s2_container.setObjectName("deckPanel")
            s2_layout = QVBoxLayout(s2_container)
            s2_layout.setContentsMargins(0,0,0,0)
            
            # Header 2
            h2 = QLabel("STREAM 2 (Secondary / Backup)")
            try:
                h2.setFont(QFont('', 14, QFont.Weight.Bold))
            except Exception:
                pass
            h2.setStyleSheet("color: white; padding: 8px; background-color: #333; border-top-left-radius: 8px; border-top-right-radius: 8px;")
            h2.setAlignment(Qt.AlignmentFlag.AlignCenter)
            s2_layout.addWidget(h2)
            
            self.stream2_panel = StreamingSettingsPanel(self, 2, app_config)
            s2_layout.addWidget(self.stream2_panel)

            # Bottom status + log
            s2_footer = QFrame()
            s2_footer.setObjectName("streamFooter")
            s2_footer.setStyleSheet("QFrame#streamFooter{background:#121212;border:1px solid #2a2a2a;border-radius:10px;}")
            s2_footer_l = QVBoxLayout(s2_footer)
            s2_footer_l.setContentsMargins(10, 8, 10, 8)
            s2_footer_l.setSpacing(8)

            s2_row = QHBoxLayout()
            s2_row.setContentsMargins(0, 0, 0, 0)
            s2_row.setSpacing(10)

            pill_base = "QLabel{background:#1a1a1a;border:1px solid #2f2f2f;border-radius:8px;padding:4px 8px;font-size:11px;font-weight:700;color:#cfcfcf;}"
            s2_dot = QFrame()
            s2_dot.setFixedSize(10, 10)
            s2_dot.setStyleSheet("background:#3a3a3a;border-radius:5px;")
            s2_status = QLabel("READY")
            s2_status.setStyleSheet(pill_base)
            s2_uptime = QLabel("Uptime 00:00:00")
            s2_uptime.setStyleSheet(pill_base)
            s2_bitrate = QLabel("Bitrate — kbps")
            s2_bitrate.setStyleSheet(pill_base)

            s2_row.addWidget(s2_dot)
            s2_row.addWidget(s2_status)
            s2_row.addStretch(1)
            s2_row.addWidget(s2_uptime)
            s2_row.addWidget(s2_bitrate)

            s2_log = QTextEdit()
            s2_log.setReadOnly(True)
            s2_log.setFixedHeight(58)
            s2_log.setStyleSheet("QTextEdit{background:#0b0b0b;border:1px solid #232323;border-radius:8px;color:#cfcfcf;padding:6px;font-size:11px;}")

            s2_footer_l.addLayout(s2_row)
            s2_footer_l.addWidget(s2_log)
            s2_layout.addWidget(s2_footer)

            streaming_layout.addWidget(s2_container)

            # Keep refs for updates
            if not hasattr(self, '_stream_ui'):
                self._stream_ui = {}
            self._stream_ui[1] = {'dot': s1_dot, 'status': s1_status, 'uptime': s1_uptime, 'bitrate': s1_bitrate, 'log': s1_log}
            self._stream_ui[2] = {'dot': s2_dot, 'status': s2_status, 'uptime': s2_uptime, 'bitrate': s2_bitrate, 'log': s2_log}

            if not hasattr(self, '_stream_started_at'):
                self._stream_started_at = {}
            if not hasattr(self, '_stream_last_status'):
                self._stream_last_status = {}

            def _update_stream_footer(stream_id: int, status_text: str):
                try:
                    ui = getattr(self, '_stream_ui', {}).get(int(stream_id))
                    if not isinstance(ui, dict):
                        return
                    stl = (status_text or '').lower()

                    dot = ui.get('dot')
                    lbl = ui.get('status')
                    log = ui.get('log')

                    if 'started' in stl or 'streaming' in stl:
                        if dot is not None:
                            dot.setStyleSheet("background:#35C759;border-radius:5px;")
                        if lbl is not None:
                            lbl.setText("LIVE")
                            lbl.setStyleSheet("QLabel{background:rgba(53,199,89,0.10);border:1px solid rgba(53,199,89,0.35);border-radius:8px;padding:4px 8px;font-size:11px;font-weight:900;color:#35C759;}")
                        if int(stream_id) not in self._stream_started_at:
                            import time
                            self._stream_started_at[int(stream_id)] = float(time.time())
                    elif 'reconnecting' in stl:
                        if dot is not None:
                            dot.setStyleSheet("background:#FF9500;border-radius:5px;")
                        if lbl is not None:
                            lbl.setText("RECONNECT")
                            lbl.setStyleSheet("QLabel{background:rgba(255,149,0,0.10);border:1px solid rgba(255,149,0,0.35);border-radius:8px;padding:4px 8px;font-size:11px;font-weight:900;color:#FF9500;}")
                    elif 'error' in stl:
                        if dot is not None:
                            dot.setStyleSheet("background:#FF3B30;border-radius:5px;")
                        if lbl is not None:
                            lbl.setText("ERROR")
                            lbl.setStyleSheet("QLabel{background:rgba(255,59,48,0.10);border:1px solid rgba(255,59,48,0.35);border-radius:8px;padding:4px 8px;font-size:11px;font-weight:900;color:#FF3B30;}")
                        try:
                            self._stream_started_at.pop(int(stream_id), None)
                        except Exception:
                            pass
                    else:
                        if dot is not None:
                            dot.setStyleSheet("background:#3a3a3a;border-radius:5px;")
                        if lbl is not None:
                            lbl.setText("READY")
                            lbl.setStyleSheet("QLabel{background:#1a1a1a;border:1px solid #2f2f2f;border-radius:8px;padding:4px 8px;font-size:11px;font-weight:700;color:#cfcfcf;}")
                        try:
                            self._stream_started_at.pop(int(stream_id), None)
                        except Exception:
                            pass

                    try:
                        self._stream_last_status[int(stream_id)] = str(status_text or '')
                    except Exception:
                        pass

                    if log is not None and status_text:
                        try:
                            log.append(status_text)
                        except Exception:
                            pass
                except Exception:
                    pass
                    pass
            self._update_stream_footer = _update_stream_footer

            def _tick_stream_uptime():
                try:
                    import time
                    now = float(time.time())
                    for sid, ui in getattr(self, '_stream_ui', {}).items():
                        up_lbl = ui.get('uptime') if isinstance(ui, dict) else None
                        started = getattr(self, '_stream_started_at', {}).get(int(sid))
                        if up_lbl is None:
                            continue
                        if not started:
                            up_lbl.setText("Uptime 00:00:00")
                            continue
                        secs = max(0, int(now - float(started)))
                        hh = secs // 3600
                        mm = (secs % 3600) // 60
                        ss = secs % 60
                        up_lbl.setText(f"Uptime {hh:02d}:{mm:02d}:{ss:02d}")
                except Exception:
                    pass

            if not hasattr(self, '_stream_uptime_timer'):
                self._stream_uptime_timer = QTimer(self)
                self._stream_uptime_timer.setInterval(1000)
                self._stream_uptime_timer.timeout.connect(_tick_stream_uptime)
                self._stream_uptime_timer.start()
            
        except Exception as e:
            print(f"Error loading streaming panels: {e}")
            lbl = QLabel(f"Error loading streaming interface: {e}")
            streaming_layout.addWidget(lbl)
        
        streaming_scroll.setWidget(streaming_inner)
        streaming_page_layout.addWidget(streaming_scroll)
        self.workspace_stack.addWidget(streaming_page)
        
        # --- WORKSPACE 3: RECORDING ---
        recording_page = QWidget()
        try:
            recording_page.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            recording_page.setMinimumHeight(0)
        except Exception:
            pass
        recording_page_layout = QVBoxLayout(recording_page)
        recording_page_layout.setContentsMargins(0, 0, 0, 0)
        recording_page_layout.setSpacing(0)

        recording_scroll = QScrollArea()
        recording_scroll.setWidgetResizable(True)
        recording_scroll.setFrameShape(QFrame.Shape.NoFrame)
        recording_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        try:
            recording_scroll.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            recording_scroll.setMinimumHeight(0)
        except Exception:
            pass
        try:
            recording_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        except Exception:
            pass

        recording_inner = QWidget()
        try:
            recording_inner.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            recording_inner.setMinimumHeight(0)
        except Exception:
            pass
        recording_layout = QVBoxLayout(recording_inner)
        recording_layout.setContentsMargins(8, 8, 8, 8)
        recording_layout.setSpacing(8)
        
        rec_panel_frame = QFrame()
        rec_panel_frame.setObjectName("deckPanel")
        rec_lay = QVBoxLayout(rec_panel_frame)
        rec_lay.setContentsMargins(0,0,0,0)
        
        rec_head = QLabel("RECORDING MASTER CONTROL")
        try:
            rec_head.setFont(QFont('', 16, QFont.Weight.Bold))
        except Exception:
            pass
        rec_head.setStyleSheet("color: white; padding: 10px; background-color: #333; border-top-left-radius: 8px; border-top-right-radius: 8px;")
        rec_head.setAlignment(Qt.AlignmentFlag.AlignCenter)
        rec_lay.addWidget(rec_head)
        
        try:
            from recording_settings_dialog import RecordingSettingsPanel
            
            # Get initial values
            initial_path = app_config.get('recording.output_path', '') or ''
            include_audio = bool(app_config.get('recording.audio_enabled', True))
            initial_audio_device = app_config.get('recording.audio_device', '') or ''
            
            self.recording_panel = RecordingSettingsPanel(self, initial_path=initial_path, include_audio=include_audio, initial_audio_device=initial_audio_device)
            
            # Add a customized "Start Recording" button inside the workspace since the panel is just settings
            # We can overlay it or add it to the layout.
            # Actually, let's keep the panel for settings and add a big Record button below it.
            
            rec_content = QVBoxLayout()
            rec_content.setContentsMargins(12, 12, 12, 12)
            rec_content.addWidget(self.recording_panel)
            
            # Big Record Button
            self.record_action_btn = QPushButton("START RECORDING")
            self.record_action_btn.setMinimumHeight(60)
            self.record_action_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            self.record_action_btn.setStyleSheet("""
                QPushButton {
                    background-color: #ff3b30;
                    color: white;
                    font-size: 18px;
                    font-weight: bold;
                    border-radius: 8px;
                    border: 2px solid #ff5b50;
                }
                QPushButton:hover {
                    background-color: #ff5b50;
                }
                QPushButton:checked {
                    background-color: #d32f2f;
                    border-color: #b71c1c;
                }
            """)
            self.record_action_btn.setCheckable(True)
            self.record_action_btn.toggled.connect(self._on_record_toggled_workspace)
            
            rec_content.addSpacing(20)
            rec_content.addWidget(self.record_action_btn)
            rec_content.addStretch()
            
            rec_lay.addLayout(rec_content)
            
        except Exception as e:
            print(f"Error loading recording panel: {e}")
            rec_lay.addWidget(QLabel(f"Error: {e}"))
            
        recording_layout.addWidget(rec_panel_frame)
        recording_scroll.setWidget(recording_inner)
        recording_page_layout.addWidget(recording_scroll)
        self.workspace_stack.addWidget(recording_page)

        # Initialize
        self.set_active_workspace(0)

        # Capture baseline monitor area height from General after first layout pass
        def _capture_monitor_area_baseline():
            try:
                if hasattr(self, 'monitor_area') and self.monitor_area is not None:
                    h = int(self.monitor_area.sizeHint().height() or self.monitor_area.height() or 0)
                    if h > 0:
                        self._monitor_area_baseline_h = int(h)
                        self._apply_monitor_area_height_policy()
            except Exception:
                pass
        QTimer.singleShot(0, _capture_monitor_area_baseline)
        
        lower_deck = self.workspace_stack # For compatibility
        # workspace_stack already added to content_layout above with proper stretch factor
        
        # --- Tally Light Styling ---
        self.setStyleSheet(self.styleSheet() + """
            QFrame[tally="program"] {
                border: 2px solid #FF3B30 !important;
                background-color: #2A1A1A;
            }
            QFrame[tally="preview"] {
                border: 2px solid #007AFF !important;
                background-color: #1A202A;
            }
            /* Input / Media Cards */
            QFrame#deckPanel {
                background-color: #1e1e1e;
                border: 1px solid #333;
                border-radius: 8px;
            }
            /* Hide Redundant Tab Bar ONLY in Transitions (don't affect Stream/Recording tabs) */
            QTabWidget#tabWidget_transitions::pane { border: none; }
            QTabWidget#tabWidget_transitions QTabBar::tab { height: 0px; margin: 0; padding: 0; border: none; }
        """)

        # Assemble Final Layout
        # content_widget contains monitors_layout and workspace_stack
        
        upper_layout.addWidget(sidebar_frame)
        upper_layout.addWidget(content_widget)  # Add content directly without scrolling
        
        new_root_layout.addWidget(upper_area)
        
        # --- Status Bar ---
        status_bar = QFrame()
        status_bar.setObjectName("statusBar")
        status_bar.setFixedHeight(24)
        status_layout = QHBoxLayout(status_bar)
        status_layout.setContentsMargins(10, 0, 10, 0)
        status_layout.setSpacing(20)
        
        def add_status_item(label, value_id):
            container = QWidget()
            hbox = QHBoxLayout(container)
            hbox.setContentsMargins(0,0,0,0)
            hbox.setSpacing(6)
            
            lbl = QLabel(label)
            lbl.setObjectName("statusLabel")
            val = QLabel("---")
            val.setObjectName("statusValue")
            setattr(self, value_id, val)
            
            hbox.addWidget(lbl)
            hbox.addWidget(val)
            status_layout.addWidget(container)
            
        add_status_item("CPU:", "status_cpu")
        add_status_item("RAM:", "status_ram")
        add_status_item("FPS:", "status_fps")
        add_status_item("REC:", "status_rec")
        add_status_item("STREAM:", "status_stream")
        
        status_layout.addStretch()
        
        self.clock_label = QLabel("00:00:00")
        self.clock_label.setObjectName("statusValue")
        status_layout.addWidget(self.clock_label)
        
        new_root_layout.addWidget(status_bar)
        
        # Set Central Widget
        self.setCentralWidget(new_root_widget)
        
        # Start Status Timer
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self._update_status_bar)
        self.status_timer.start(1000)
        
        # --- Initialize State for Switching ---
        # Preview-first workflow: Program stays empty until user presses CUT/AUTO
        if not hasattr(self, 'active_program_source'):
            self.active_program_source = None  # No source on Program until CUT
        if not hasattr(self, 'active_preview_source'):
            self.active_preview_source = ('input', 1)  # Default Preview to Input 1
        # Keep current_output in sync (Program = what's live; None = black until CUT)
        if not hasattr(self, 'current_output') or getattr(self, '_preview_first_init', True):
            self.current_output = None
            self._preview_first_init = False
            
        # Make Inputs Clickable
        for i in range(1, 4):
            w = getattr(self, f'inputDisplay{i}', None)
            if w:
                # We need to capture 'i' in the lambda
                # Use a transparent button overlay or event filter. 
                # Simplest: override mousePressEvent dynamically
                def make_callback(idx):
                    return lambda event: self.set_preview_source('input', idx)
                w.mousePressEvent = make_callback(i)
                w.setCursor(Qt.CursorShape.PointingHandCursor)

        # Make Media Clickable
        for i in range(1, 4):
            w = getattr(self, f'mediaDisplay{i}', None)
            if w:
                def make_callback(idx):
                    return lambda event: self.set_preview_source('media', idx)
                w.mousePressEvent = make_callback(i)
                w.setCursor(Qt.CursorShape.PointingHandCursor)

        # Initial Tally Update
        self.update_tally_lights()
        
        print("✅ Premium Redesign Applied Successfully")

    def _unlock_video_dominance(self):
        """
        Override minimum height constraints to allow video section to dominate.
        This is called after apply_modern_redesign() to forcefully unlock the bottom section.
        """
        try:
            # 1. UNLOCK BOTTOM SECTION: Remove minimumHeight from workspace_stack and its children
            if hasattr(self, 'workspace_stack'):
                self.workspace_stack.setMinimumHeight(0)
                print("[VIDEO DOMINANCE] workspace_stack minimumHeight unlocked → 0")
                
                # Recursively unlock all child widgets in workspace_stack
                def unlock_children(widget):
                    try:
                        widget.setMinimumHeight(0)
                        for child in widget.findChildren(QWidget):
                            try:
                                child.setMinimumHeight(0)
                            except Exception:
                                pass
                    except Exception:
                        pass
                
                unlock_children(self.workspace_stack)
            
            # 2. UNLOCK SPECIFIC FRAMES: Remove constraints from Inputs, Effects, Media, etc.
            for widget_name in ['inputsFrame', 'effectsFrame', 'mediaFrame', 'deckPanel', 'generalPage', 'streamPage', 'recordPage']:
                try:
                    w = getattr(self, widget_name, None)
                    if w is not None:
                        w.setMinimumHeight(0)
                        print(f"[VIDEO DOMINANCE] {widget_name} minimumHeight unlocked → 0")
                except Exception:
                    pass
            
            # 3. FORCE TOP EXPANSION: Set monitor_area to expand in both directions
            if hasattr(self, 'monitor_area'):
                # Set size policy to Expanding/Expanding so it grows to fill available space
                size_policy = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
                self.monitor_area.setSizePolicy(size_policy)
                print("[VIDEO DOMINANCE] monitor_area size policy set to Expanding/Expanding")
                
                # Ensure no maximum height constraint
                self.monitor_area.setMaximumHeight(16777215)  # Qt's max value
            
            # 4. RE-APPLY STRETCH: Get parent layout and re-enforce stretch factors
            if hasattr(self, 'monitor_area') and self.monitor_area.parent() is not None:
                parent_layout = self.monitor_area.parent().layout()
                if parent_layout is not None:
                    # Find indices of monitor_area and workspace_stack in the layout
                    monitor_idx = None
                    workspace_idx = None
                    
                    for i in range(parent_layout.count()):
                        item = parent_layout.itemAt(i)
                        if item and item.widget() == self.monitor_area:
                            monitor_idx = i
                        elif item and item.widget() == getattr(self, 'workspace_stack', None):
                            workspace_idx = i
                    
                    # Re-apply stretch: 3:1 ratio (video:controls)
                    if monitor_idx is not None:
                        parent_layout.setStretch(monitor_idx, 3)
                        print(f"[VIDEO DOMINANCE] monitor_area stretch factor set to 3 at index {monitor_idx}")
                    
                    if workspace_idx is not None:
                        parent_layout.setStretch(workspace_idx, 1)
                        print(f"[VIDEO DOMINANCE] workspace_stack stretch factor set to 1 at index {workspace_idx}")
            
            # 5. FORCE LAYOUT UPDATE
            self.update()
            self.repaint()
            print("[VIDEO DOMINANCE] Layout forcefully updated and repainted")
            
        except Exception as e:
            print(f"[VIDEO DOMINANCE ERROR] Failed to unlock video dominance: {e}")
            import traceback
            traceback.print_exc()

    def set_preview_source(self, source_type, index):
        """Set the preview source and update UI."""
        self.active_preview_source = (source_type, index)
        self.update_tally_lights()
        
        try:
            img = None
            if source_type == 'input':
                img = self.last_input_image.get(index) if hasattr(self, 'last_input_image') else None
            elif source_type == 'media':
                img = self.last_media_image.get(index) if hasattr(self, 'last_media_image') else None
            self._update_preview_monitor(img, source_type, index)
        except Exception:
            pass

    def _detect_overlay_opening(self, effect_path: str, overlay_img: QImage):
        """Detect opening area in overlay using the same methods as enhanced_graphics_output.py"""
        import json
        try:
            # Method 1: Try JSON sidecar file
            base, _ = os.path.splitext(effect_path)
            json_path = base + '.json'
            if os.path.exists(json_path):
                try:
                    with open(json_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    opening = data.get('opening') if isinstance(data, dict) else None
                    if isinstance(opening, (list, tuple)) and len(opening) == 4:
                        nx, ny, nw, nh = [float(v) for v in opening]
                        return (
                            max(0.0, min(1.0, nx)),
                            max(0.0, min(1.0, ny)),
                            max(0.01, min(1.0, nw)),
                            max(0.01, min(1.0, nh))
                        )
                except Exception:
                    pass
            
            # Method 2: Try mask file
            mask_path = base + '_mask.png'
            if os.path.exists(mask_path):
                try:
                    mask_img = QImage(mask_path)
                    if not mask_img.isNull():
                        w, h = mask_img.width(), mask_img.height()
                        min_x = min_y = float('inf')
                        max_x = max_y = -1
                        
                        for y in range(h):
                            for x in range(w):
                                c = mask_img.pixelColor(x, y)
                                if c.red() > 200 and c.green() > 200 and c.blue() > 200 and c.alpha() > 200:
                                    min_x = min(min_x, x)
                                    min_y = min(min_y, y)
                                    max_x = max(max_x, x)
                                    max_y = max(max_y, y)
                        
                        if max_x > min_x and max_y > min_y:
                            return (min_x / w, min_y / h, (max_x - min_x + 1) / w, (max_y - min_y + 1) / h)
                except Exception:
                    pass
            
            # Method 3: Auto-detect from transparency
            if overlay_img and not overlay_img.isNull():
                try:
                    w, h = overlay_img.width(), overlay_img.height()
                    if w > 10 and h > 10:
                        min_x = min_y = float('inf')
                        max_x = max_y = -1
                        
                        for y in range(h):
                            for x in range(w):
                                # Be more tolerant: consider semi-transparent pixels as opening too
                                # This helps effects whose window uses soft edges or partial transparency
                                if overlay_img.pixelColor(x, y).alpha() <= 64:
                                    min_x = min(min_x, x)
                                    min_y = min(min_y, y)
                                    max_x = max(max_x, x)
                                    max_y = max(max_y, y)
                        
                        if max_x > min_x and max_y > min_y:
                            return (min_x / w, min_y / h, (max_x - min_x + 1) / w, (max_y - min_y + 1) / h)
                except Exception:
                    pass
            
            return None
        except Exception:
            return None

    def _update_preview_monitor(self, img: QImage | None, source_type: str, index: int):
        try:
            # Debug logging removed for performance - was running on every frame
            # Uncomment below for debugging if needed
            # img_status = "None" if img is None else ("Null" if (hasattr(img, 'isNull') and img.isNull()) else f"{img.width()}x{img.height()}")
            # overlay_status = "Yes" if getattr(self, 'preview_overlay_path', None) else "No"
            # if not hasattr(self, '_preview_update_count'):
            #     self._preview_update_count = 0
            # self._preview_update_count += 1
            # if self._preview_update_count % 30 == 1:
            #     print(f"📺 Preview update #{self._preview_update_count}: {source_type}-{index}, img={img_status}, overlay={overlay_status}")
            
            if not hasattr(self, 'preview_video_label') or self.preview_video_label is None:
                return
            if img is None or (hasattr(img, 'isNull') and img.isNull()):
                self.preview_video_label.setPixmap(QPixmap())
                if source_type == 'input':
                    self.preview_video_label.setText(f"Input {index}")
                elif source_type == 'media':
                    self.preview_video_label.setText(f"Media {index}")
                else:
                    self.preview_video_label.setText("Select a source to preview")
                return
            preview_size = self.preview_video_label.size()
            if preview_size.width() <= 1 or preview_size.height() <= 1:
                ms = self.preview_video_label.minimumSize()
                preview_size = ms if ms.isValid() else QSize(640, 360)
            # Apply preview-only effect (does not affect LIVE/stream/record)
            # Use the EXACT same logic as enhanced_graphics_output.py for consistent rendering
            # OPTIMIZED: Cache scaled overlays, masks, and geometry to reduce CPU usage
            # ULTRA-OPTIMIZED: Frame skipping and quality reduction for low-end systems (i3 laptops)
            try:
                from PyQt6.QtGui import QPainter
                from PyQt6.QtCore import QRectF
                import json
                
                pfx = getattr(self, 'preview_overlay_path', None)
                if pfx and os.path.exists(str(pfx)):
                    # OPTIMIZATION: Frame skipping for low-end systems
                    # Only process overlay every Nth frame to reduce CPU load
                    if not hasattr(self, '_preview_frame_skip_counter'):
                        self._preview_frame_skip_counter = 0
                        self._preview_last_composed = None
                    
                    self._preview_frame_skip_counter += 1
                    
                    # Skip every other frame when overlay is active (50% reduction)
                    # On i3 laptops, this makes a huge difference
                    # But if a new effect was just selected, force compose for a couple frames
                    if hasattr(self, '_preview_compose_force') and isinstance(self._preview_compose_force, int) and self._preview_compose_force > 0:
                        self._preview_compose_force -= 1
                    elif self._preview_frame_skip_counter % 2 != 0 and self._preview_last_composed is not None:
                        # Reuse last composed frame
                        img = self._preview_last_composed
                    else:
                        # Load and cache the overlay image (only when it changes)
                        if not hasattr(self, '_preview_overlay_cache_path') or self._preview_overlay_cache_path != pfx:
                            self._preview_overlay_image = QImage(str(pfx))
                            self._preview_overlay_cache_path = pfx
                            # Detect opening area using the same methods as enhanced_graphics_output.py
                            self._preview_opening_norm = self._detect_overlay_opening(str(pfx), self._preview_overlay_image)
                            # Clear cached scaled overlays and masks when overlay changes
                            self._preview_scaled_overlay_cache = {}
                            self._preview_mask_cache = {}
                            self._preview_geom_cache = {}
                        
                        overlay_img = self._preview_overlay_image
                        opening_norm = self._preview_opening_norm
                        
                        if overlay_img and not overlay_img.isNull():
                            # Calculate overlay geometry (aspect-fit into preview_size)
                            # OPTIMIZATION: Cache geometry calculation
                            cache_key = (preview_size.width(), preview_size.height())
                            
                            if not hasattr(self, '_preview_geom_cache'):
                                self._preview_geom_cache = {}
                            
                            geom = self._preview_geom_cache.get(cache_key)
                            if geom is None:
                                src_w = overlay_img.width()
                                src_h = overlay_img.height()
                                dst_w = preview_size.width()
                                dst_h = preview_size.height()
                                scale = min(dst_w / src_w, dst_h / src_h)
                                scaled_w = int(src_w * scale)
                                scaled_h = int(src_h * scale)
                                off_x = (dst_w - scaled_w) // 2
                                off_y = (dst_h - scaled_h) // 2
                                geom = (scaled_w, scaled_h, off_x, off_y)
                                self._preview_geom_cache[cache_key] = geom
                            
                            scaled_w, scaled_h, off_x, off_y = geom
                            
                            # OPTIMIZATION: Cache scaled overlay
                            if not hasattr(self, '_preview_scaled_overlay_cache'):
                                self._preview_scaled_overlay_cache = {}
                            
                            scaled_overlay = self._preview_scaled_overlay_cache.get(cache_key)
                            if scaled_overlay is None:
                                # OPTIMIZATION: Use FastTransformation for i3 laptops (much faster than SmoothTransformation)
                                scaled_overlay = overlay_img.scaled(
                                    QSize(scaled_w, scaled_h),
                                    Qt.AspectRatioMode.IgnoreAspectRatio,
                                    Qt.TransformationMode.FastTransformation  # Changed from SmoothTransformation
                                )
                                self._preview_scaled_overlay_cache[cache_key] = scaled_overlay
                            
                            # Create canvas
                            canvas = QImage(preview_size, QImage.Format.Format_ARGB32)
                            canvas.fill(QColor(0, 0, 0, 255))
                            
                            painter = QPainter(canvas)
                            try:
                                # OPTIMIZATION: Disable antialiasing for i3 laptops (faster rendering)
                                painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, False)
                                painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
                                
                                # 1. Draw video in the opening area (or full-screen if no opening detected)
                                if img and not img.isNull():
                                    if opening_norm:
                                        # Draw video inside the detected opening
                                        nx, ny, nw, nh = opening_norm
                                        video_rect = QRectF(
                                            off_x + (nx * scaled_w),
                                            off_y + (ny * scaled_h),
                                            max(1.0, nw * scaled_w),
                                            max(1.0, nh * scaled_h)
                                        )
                                    else:
                                        # No opening detected, draw full-screen
                                        video_rect = QRectF(0, 0, preview_size.width(), preview_size.height())
                                    
                                    # Draw video scaled to fit the target rect
                                    painter.drawImage(video_rect, img, QRectF(img.rect()))
                                    
                                    # Apply mask if opening is detected
                                    if opening_norm:
                                        # OPTIMIZATION: Cache mask
                                        if not hasattr(self, '_preview_mask_cache'):
                                            self._preview_mask_cache = {}
                                        
                                        mask = self._preview_mask_cache.get(cache_key)
                                        if mask is None:
                                            # Create mask for the opening area
                                            mask = QImage(preview_size, QImage.Format.Format_ARGB32)
                                            mask.fill(QColor(0, 0, 0, 0))
                                            mask_painter = QPainter(mask)
                                            mask_painter.fillRect(
                                                int(video_rect.x()),
                                                int(video_rect.y()),
                                                int(video_rect.width()),
                                                int(video_rect.height()),
                                                QColor(255, 255, 255, 255)
                                            )
                                            mask_painter.end()
                                            self._preview_mask_cache[cache_key] = mask
                                        
                                        # Apply mask to clip video to opening
                                        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_DestinationIn)
                                        painter.drawImage(0, 0, mask)
                                        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
                                
                                # 2. Draw cached scaled overlay on top
                                painter.drawImage(off_x, off_y, scaled_overlay)
                                
                            finally:
                                painter.end()
                            
                            # Cache the composed result for frame skipping
                            self._preview_last_composed = canvas.copy()
                            img = canvas
            except Exception as e:
                print(f"❌ Preview overlay error: {e}")
                import traceback
                traceback.print_exc()

            # Apply Preview-only text overlay to the preview image before displaying
            # Use ENFORCED position settings (already set to bottom in _on_overlay_changed)
            try:
                if hasattr(self, 'preview_text_settings') and isinstance(self.preview_text_settings, dict):
                    s = dict(self.preview_text_settings)  # Use enforced settings
                    if s.get('text', '').strip():
                        from text_overlay_renderer import TextOverlayRenderer
                        if not hasattr(self, '_preview_text_renderer') or self._preview_text_renderer is None:
                            self._preview_text_renderer = TextOverlayRenderer()
                        # Position is already enforced in preview_text_settings, just use it
                        self._preview_text_renderer.update_settings(s)
                        img = self._preview_text_renderer.render_overlay(img)
            except Exception as e:
                print(f"[Preview Text] Error: {e}")

            pix = QPixmap.fromImage(img)
            # Avoid double scaling: if we already composed at preview_size, use it directly.
            try:
                if img.size() == preview_size:
                    preview_pix = pix
                else:
                    try:
                        preview_pix = pix.scaled(preview_size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                    except:
                        # Fallback to fast transformation if smooth fails
                        preview_pix = pix.scaled(preview_size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.FastTransformation)
            except Exception as e:
                # If scaling fails, show original
                preview_pix = pix
            self.preview_video_label.setPixmap(preview_pix)
            self.preview_video_label.setText("")

            # Ensure preview audio is never output: mute preview media players
            try:
                if source_type == 'media' and hasattr(self, 'media_players'):
                    player = self.media_players.get(int(index))
                    if player is not None:
                        # Keep preview muted at all times
                        try:
                            if hasattr(player, 'audioOutput') and player.audioOutput():
                                player.audioOutput().setVolume(0.0)
                        except Exception:
                            pass
            except Exception:
                pass
        except Exception:
            pass
            
    def set_program_source(self, source_type, index):
        print(f"[DEBUG] set_program_source called with source_type={source_type}, index={index}", flush=True)
        """Set the program source (Live) and update UI."""
        # Auto-play local media when previewed (if not live)
        if source_type == 'media':
            try:
                player = self.media_players.get(index)
                if player and player.playbackState() != QMediaPlayer.PlaybackState.PlayingState:
                    # Only auto-play if not the current Program source (to avoid restart overlaps)
                    if self.active_program_source != ('media', index):
                        print(f"Auto-playing Media {index} for Preview")
                        player.play()
                        if hasattr(self, 'btn_prev_play'):
                            self.btn_prev_play.setIcon(self.get_icon("Pause.png"))
            except Exception:
                pass

        # Authoritative program switch: route through existing output switching pipeline
        # so that GraphicsOutputWidget, streaming/recording, and external display stay consistent.
        self.active_program_source = (source_type, index)
        try:
            self.set_output_source(source_type, index)
        except Exception:
            # Fallback to immediate program switch if transition pipeline is unavailable
            try:
                self._set_output_source_immediate(source_type, index)
            except Exception:
                pass
        # Keep legacy state in sync (many frame handlers still reference current_output)
        self.current_output = (source_type, index)
        self.update_tally_lights()

    def cut_transition(self):
        """Immediate cut between Preview and Program (NO transition animation)."""
        # This is for instant cuts - do NOT call auto_transition
        # Swap sources and perform an immediate program cut
        try:
            # Promote preview text overlay settings to Program when cutting
            # This ensures text overlay appears on program with same settings as preview
            if hasattr(self, 'preview_text_settings') and isinstance(self.preview_text_settings, dict):
                self.program_text_settings = dict(self.preview_text_settings)
        except Exception:
            pass
        prev = getattr(self, 'active_preview_source', ('input', 1))
        prog = getattr(self, 'active_program_source', None)
        if prog is None:
            prog = ('input', 1)  # Fallback when Program was empty (preview-first workflow)
        # Commit preview -> program immediately
        try:
            self._pending_program_swap = None
        except Exception:
            pass

        # Effect workflow: commit preview effect to LIVE on CUT
        try:
            self.program_overlay_path = getattr(self, 'preview_overlay_path', None)
            if hasattr(self, '_graphics_output') and self._graphics_output is not None:
                if self.program_overlay_path:
                    self._graphics_output.set_overlay_from_path(str(self.program_overlay_path), use_transition=False)
                else:
                    self._graphics_output.clear_overlay(use_transition=False)
            # Do NOT clear preview effect: user wants to keep seeing the effect in Preview
            # so they can continue tweaking without affecting Program
        except Exception:
            pass
        # Promote preview text overlay settings to Program (Live) when transitioning
        try:
            # When cut_transition or auto_transition is called, sync the settings
            # This is already done in auto_transition and cut_transition methods
            pass
        except Exception:
            pass
        try:
            self._set_output_source_immediate(prev[0], int(prev[1]))
        except Exception:
            # Fallback
            self.set_program_source(prev[0], int(prev[1]))
        # Update buses
        self.active_program_source = (prev[0], int(prev[1]))
        self.current_output = self.active_program_source
        self.active_preview_source = (prog[0], int(prog[1]))
        self.update_tally_lights()
        # Refresh preview monitor to show the newly assigned preview source
        try:
            if prog[0] == 'input':
                self._update_preview_monitor(self.last_input_image.get(int(prog[1])), 'input', int(prog[1]))
            elif prog[0] == 'media':
                self._update_preview_monitor(self.last_media_image.get(int(prog[1])), 'media', int(prog[1]))
        except Exception:
            pass
        print(f"CUT: Program={self.active_program_source}, Preview={self.active_preview_source}")

    def auto_transition(self):
        """Auto transition ONLY when AUTO button is clicked."""
        # Perform a real transition from current program -> preview, then swap buses.
        try:
            prev = getattr(self, 'active_preview_source', None)
            prog = getattr(self, 'active_program_source', None)
            if not prev or not prog:
                self.cut_transition()
                return
            # Ensure transition_duration_ms and selected_transition are set
            if not hasattr(self, 'transition_duration_ms'):
                self.transition_duration_ms = 700
            if not hasattr(self, 'selected_transition'):
                self.selected_transition = 'Fade'
            # Use the selected transition (set only by button click)
            transition_name = self.selected_transition or 'Fade'
            # Promote preview text overlay to program BEFORE transition
            if hasattr(self, 'preview_text_settings') and isinstance(self.preview_text_settings, dict):
                self.program_text_settings = dict(self.preview_text_settings)
            # Store pending swap so _on_transition_done can update buses consistently
            self._pending_program_swap = {
                'from': (prog[0], int(prog[1])),
                'to': (prev[0], int(prev[1])),
            }
            # Route through output switcher which invokes TransitionManager when enabled
            self.set_output_source(prev[0], int(prev[1]))
            print(f"AUTO: transitioning Program {prog} -> {prev} with {transition_name} ({self.transition_duration_ms}ms)")
        except Exception as e:
            # Safe fallback
            print(f"AUTO transition error: {e}")
            self.cut_transition()

    def update_tally_lights(self):
        """Update the visual tally state of all inputs and media."""
        # Common Tally Style Helpers
        def set_tally(widget, status):
            if not widget: return
            widget.setProperty("tally", status)
            widget.style().unpolish(widget)
            widget.style().polish(widget)

        # Update Input Tallies
        for i in range(1, 4):
            # Inputs
            w = getattr(self, f'inputDisplay{i}', None)
            set_tally(w, "")
            
            # Media
            m = getattr(self, f'mediaDisplay{i}', None)
            set_tally(m, "")

        # Set Program Tally (Red) - may be None until CUT is pressed
        prog = getattr(self, 'active_program_source', None)
        if prog is not None:
            p_type, p_idx = prog
            if p_type == 'input':
                set_tally(getattr(self, f'inputDisplay{p_idx}', None), "program")
            elif p_type == 'media':
                set_tally(getattr(self, f'mediaDisplay{p_idx}', None), "program")

        # Set Preview Tally (Blue)
        pv = getattr(self, 'active_preview_source', None)
        if pv is None:
            pv = ('input', 1)
        pv_type, pv_idx = pv
        if pv_type == 'input':
            set_tally(getattr(self, f'inputDisplay{pv_idx}', None), "preview")
        elif pv_type == 'media':
             set_tally(getattr(self, f'mediaDisplay{pv_idx}', None), "preview")
            
    # --- New Playback Control Methods ---
    def _toggle_preview_playback(self):
        """Toggle playback for the active preview media."""
        try:
            st, idx = self.active_preview_source
            if st != 'media': return
            
            player = self.media_players.get(idx)
            if not player: return
            
            if player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
                player.pause()
                if hasattr(self, 'btn_prev_play'):
                    self.btn_prev_play.setIcon(self.get_icon("Play.png"))
            else:
                player.play()
                if hasattr(self, 'btn_prev_play'):
                    self.btn_prev_play.setIcon(self.get_icon("Pause.png"))
        except Exception as e:
            print(f"Preview playback error: {e}")

    def _seek_preview_media(self, val):
        """Seek preview media based on slider (0-1000)."""
        try:
            st, idx = self.active_preview_source
            if st != 'media': return
            
            player = self.media_players.get(idx)
            if not player: return
            
            dur = player.duration()
            if dur > 0:
                pos = int(dur * (val / 1000.0))
                player.setPosition(pos)
        except Exception:
            pass

    def _update_status_bar(self):
        """Update status bar metrics"""
        try:
            import psutil
            import time
            
            # CPU/RAM
            cpu = psutil.cpu_percent()
            mem = psutil.Process().memory_info().rss / 1024 / 1024
            if hasattr(self, 'status_cpu'): self.status_cpu.setText(f"{cpu:.1f}%")
            if hasattr(self, 'status_ram'): self.status_ram.setText(f"{mem:.0f}MB")
            
            # Clock
            self.status_clock.setText(time.strftime("%H:%M:%S"))
            
            # FPS (Mock for now, or hook into real FPS controller)
            if hasattr(self, 'status_fps'): self.status_fps.setText("60")
            
        except Exception:
            pass

    def load_ui(self):
        """Load UI from .ui file directly"""
        try:
            # Get the absolute path to the .ui file
            ui_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mainwindow.ui")
            
            # Load the .ui file directly
            uic.loadUi(ui_file_path, self)
            # print("UI loaded successfully from mainwindow.ui")
            
            # Set icons programmatically after UI is loaded
            self.set_ui_icons()
            
            # Apply 16:9 aspect ratio to video widgets
            self.apply_aspect_ratio_constraints()

            # Enforce 50/50 split between left and right main panels
            self.apply_main_panel_stretch()

            # Load effects from folder into tabs
            self.load_effects_into_tabs()

            # Master-clock-driven Preview refresh (independent from Program pipeline)
            try:
                from fps_controller import get_fps_controller
                self._preview_clock = get_fps_controller()
                # Connect once
                if not hasattr(self, '_preview_clock_connected') or not self._preview_clock_connected:
                    self._preview_clock.frame_ready.connect(self._on_master_frame_tick)
                    self._preview_clock_connected = True
                # Ensure the master clock is running
                if not getattr(self._preview_clock, 'is_running', False):
                    self._preview_clock.start()
            except Exception:
                pass

            # Make transitions panel grow to fill extra space on the right
            self.apply_right_panel_stretch()

            # Make effects tabs grow to fill extra space on the left
            self.apply_left_panel_stretch()

            # Apply Modern Redesign
            self.apply_modern_redesign()

            # Force unlock bottom section size constraints and prioritize video area
            self._unlock_video_dominance()

            # Install output aspect guard to enforce 16:9 based on actual width
            QTimer.singleShot(0, self._install_output_aspect_guard)
            # Install calibration shortcut (Ctrl+Shift+C)
            try:
                from PyQt6.QtGui import QShortcut, QKeySequence
                self._calib_shortcut = QShortcut(QKeySequence("Ctrl+Shift+C"), self)
                self._calib_shortcut.activated.connect(self.open_calibration_tool)
            except Exception:
                pass
            # Audio delay correction will be applied automatically when needed
            # Populate audio outputs if the combo exists
            try:
                self._populate_audio_outputs_combo()
            except Exception:
                pass
            
        except Exception as e:
            print(f"Failed to load UI file: {e}")
            sys.exit(-1)
    
    def get_icon(self, icon_name):
        """Get icon from icons folder with cross-platform path handling"""
        try:
            # Get the directory where this script is located
            if getattr(sys, 'frozen', False):
                # If running as compiled executable
                base_path = sys._MEIPASS
            else:
                # If running as script
                base_path = os.path.dirname(os.path.abspath(__file__))
            
            icon_path = os.path.join(base_path, "icons", icon_name)
            
            if os.path.exists(icon_path):
                return QIcon(icon_path)
            else:
                # Fallback to a default icon or empty icon
                print(f"Warning: Icon not found: {icon_path}")
                return QIcon()  # Empty icon
        except Exception as e:
            print(f"Error loading icon {icon_name}: {e}")
            return QIcon()  # Empty icon
    
    def connect_signals(self):
        """Connect UI signals to their respective slots"""
        try:
            # Record buttons
            if hasattr(self, 'recordRedCircle'):
                self.recordRedCircle.clicked.connect(self.toggle_recording)
            if hasattr(self, 'playButton'):
                self.playButton.clicked.connect(self.toggle_playback)
            if hasattr(self, 'captureButton'):
                self.captureButton.clicked.connect(self.capture_screenshot)
            if hasattr(self, 'settingsRecordButton'):
                # Simple direct connection to recording settings
                self.settingsRecordButton.clicked.connect(self.open_record_settings)
                self.settingsRecordButton.setToolTip("Recording Settings")
                print("✅ Connected recording settings button")
            
            # Check for text overlay button
            if hasattr(self, 'textOverlayButton'):
                self.textOverlayButton.clicked.connect(self.show_text_overlay_settings)
                self.textOverlayButton.setToolTip("Text Overlay Settings")
                print("✅ Connected text overlay settings button")
            elif hasattr(self, 'overlayButton'):
                self.overlayButton.clicked.connect(self.show_text_overlay_settings)
                self.overlayButton.setToolTip("Text Overlay Settings")
                print("✅ Connected overlay settings button")
            
            # Stream buttons - Settings buttons open settings dialog, separate toggle mechanism
            if hasattr(self, 'stream1SettingsBtn'):
                # Left-click opens settings dialog
                self.stream1SettingsBtn.clicked.connect(lambda: self.open_stream_settings_dialog(1))
                self.stream1SettingsBtn.setToolTip("Stream 1 Settings")
                print("✅ Connected Stream 1 settings button")
            else:
                print("❌ Stream 1 settings button not found")
            
            if hasattr(self, 'stream2SettingsBtn'):
                # Left-click opens settings dialog
                self.stream2SettingsBtn.clicked.connect(lambda: self.open_stream_settings_dialog(2))
                self.stream2SettingsBtn.setToolTip("Stream 2 Settings")
                print("✅ Connected Stream 2 settings button")
            else:
                print("❌ Stream 2 settings button not found")
            
            # Connect stream labels for toggling streams
            if hasattr(self, 'stream1Label'):
                # Make stream label clickable to toggle streaming
                self.stream1Label.mousePressEvent = lambda event: self.handle_stream_button_click(1)
                self.stream1Label.setToolTip("Click to toggle Stream 1")
                self.stream1Label.setStyleSheet("QLabel:hover { background-color: #3a3a3a; border-radius: 4px; }")
                print("✅ Connected Stream 1 label for toggling")
            
            if hasattr(self, 'stream2Label'):
                # Make stream label clickable to toggle streaming
                self.stream2Label.mousePressEvent = lambda event: self.handle_stream_button_click(2)
                self.stream2Label.setToolTip("Click to toggle Stream 2")
                self.stream2Label.setStyleSheet("QLabel:hover { background-color: #3a3a3a; border-radius: 4px; }")
                print("✅ Connected Stream 2 label for toggling")
            
            # Audio buttons in Additional section
            # Top button is Global Mute toggle for the entire app (inputs + media)
            if hasattr(self, 'audioTopButton'):
                self.audioTopButton.clicked.connect(self.toggle_global_mute)
                try:
                    self.audioTopButton.setToolTip("Global Mute (mute all inputs and media)")
                except Exception:
                    pass
            # Second button: Clear Visuals (restored to original functionality)
            if hasattr(self, 'bottomButton2'):
                try:
                    # Ensure no menu is attached
                    try:
                        self.bottomButton2.setMenu(None)
                    except Exception:
                        pass
                    # Click to clear visuals
                    self.bottomButton2.clicked.connect(self.action_clear_visuals)
                    self.bottomButton2.setToolTip("Clear Visuals (remove overlay and hide text)")
                except Exception:
                    pass
            
            # Combo boxes
            if hasattr(self, 'outputSizeComboBox'):
                # Populate Output Size profiles and set initial selection
                try:
                    self._populate_output_size_combo()
                except Exception:
                    pass
                self.outputSizeComboBox.currentTextChanged.connect(self.on_output_size_changed)
            if hasattr(self, 'fpsComboBox'):
                # Set default FPS selection
                try:
                    current_fps = int(app_config.get('ui.preview_fps', 60))
                    if current_fps == 30:
                        self.fpsComboBox.setCurrentText("30 FPS")
                    else:
                        self.fpsComboBox.setCurrentText("60 FPS")
                except Exception:
                    self.fpsComboBox.setCurrentText("60 FPS")
                self.fpsComboBox.currentTextChanged.connect(self.on_fps_changed)
            if hasattr(self, 'audioOutputComboBox'):
                self.audioOutputComboBox.currentTextChanged.connect(self.on_audio_output_changed)
            
            # Connect input settings buttons to camera selection dialogs
            if hasattr(self, 'input1SettingsButton'):
                self.input1SettingsButton.clicked.connect(lambda: self.show_camera_selection_dialog(1))
                print("✅ Connected Input 1 settings button")
            else:
                print("❌ Input 1 settings button not found")
            
            if hasattr(self, 'input2SettingsButton'):
                self.input2SettingsButton.clicked.connect(lambda: self.show_camera_selection_dialog(2))
                print("✅ Connected Input 2 settings button")
            else:
                print("❌ Input 2 settings button not found")
                
            if hasattr(self, 'input3SettingsButton'):
                self.input3SettingsButton.clicked.connect(lambda: self.show_camera_selection_dialog(3))
                print("✅ Connected Input 3 settings button")
            else:
                print("❌ Input 3 settings button not found")
            
            # Connect media settings buttons to media file selection dialogs
            if hasattr(self, 'media1SettingsButton'):
                self.media1SettingsButton.clicked.connect(lambda: self.show_media_selection_dialog(1))
                print("✅ Connected Media 1 settings button")
            else:
                print("❌ Media 1 settings button not found")
                
            if hasattr(self, 'media2SettingsButton'):
                self.media2SettingsButton.clicked.connect(lambda: self.show_media_selection_dialog(2))
                print("✅ Connected Media 2 settings button")
            else:
                print("❌ Media 2 settings button not found")
                
            if hasattr(self, 'media3SettingsButton'):
                self.media3SettingsButton.clicked.connect(lambda: self.show_media_selection_dialog(3))
                print("✅ Connected Media 3 settings button")
            else:
                print("❌ Media 3 settings button not found")
        
            # Connect media control buttons (play/pause) mapped to UI names pushButton_19/20/21
            if hasattr(self, 'pushButton_19'):
                self.pushButton_19.clicked.connect(lambda: self.toggle_media_playback(1))
            if hasattr(self, 'pushButton_20'):
                self.pushButton_20.clicked.connect(lambda: self.toggle_media_playback(2))
            if hasattr(self, 'pushButton_21'):
                self.pushButton_21.clicked.connect(lambda: self.toggle_media_playback(3))
        
            # Connect audio toggle buttons for inputs
            if hasattr(self, 'input1AudioButton'):
                self.input1AudioButton.clicked.connect(lambda: self.toggle_input_audio(1))
            if hasattr(self, 'input2AudioButton'):
                self.input2AudioButton.clicked.connect(lambda: self.toggle_input_audio(2))
            if hasattr(self, 'input3AudioButton'):
                self.input3AudioButton.clicked.connect(lambda: self.toggle_input_audio(3))

            # Connect audio toggle buttons for media
            if hasattr(self, 'media1AudioButton'):
                self.media1AudioButton.clicked.connect(lambda: self.toggle_media_audio(1))
            if hasattr(self, 'media2AudioButton'):
                self.media2AudioButton.clicked.connect(lambda: self.toggle_media_audio(2))
            if hasattr(self, 'media3AudioButton'):
                self.media3AudioButton.clicked.connect(lambda: self.toggle_media_audio(3))
        
            # Connect progress sliders for media seeking (0-100 percent)
            if hasattr(self, 'horizontalSlider'):
                self.horizontalSlider.valueChanged.connect(lambda value: self.seek_media(1, value))
            if hasattr(self, 'horizontalSlider_2'):
                self.horizontalSlider_2.valueChanged.connect(lambda value: self.seek_media(2, value))
            if hasattr(self, 'horizontalSlider_3'):
                self.horizontalSlider_3.valueChanged.connect(lambda value: self.seek_media(3, value))

            # print("UI signals connected successfully")
        except Exception as e:
            print(f"Error connecting UI signals: {e}")

        # Connect switching controls
        # ISSUE 2 & 3 FIX: Changed to set_preview_source so transitions apply to preview FIRST,
        # then click AUTO to transition preview -> program. This matches professional broadcast workflow.
        try:
            if hasattr(self, 'switchInput1Btn'):
                self.switchInput1Btn.clicked.connect(lambda: self.set_preview_source('input', 1))
            if hasattr(self, 'switchInput2Btn'):
                self.switchInput2Btn.clicked.connect(lambda: self.set_preview_source('input', 2))
            if hasattr(self, 'switchInput3Btn'):
                self.switchInput3Btn.clicked.connect(lambda: self.set_preview_source('input', 3))
            if hasattr(self, 'switchMedia1Btn'):
                self.switchMedia1Btn.clicked.connect(lambda: self.set_preview_source('media', 1))
            if hasattr(self, 'switchMedia2Btn'):
                self.switchMedia2Btn.clicked.connect(lambda: self.set_preview_source('media', 2))
            if hasattr(self, 'switchMedia3Btn'):
                self.switchMedia3Btn.clicked.connect(lambda: self.set_preview_source('media', 3))
        except Exception as e:
            print(f"Error connecting switching controls: {e}")
    def toggle_media_playback(self, media_index):
        """Toggle playback for the specified media (Qt Multimedia)"""
        player = self.media_players[media_index]
        if player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            player.pause()
        else:
            # Ensure only one media plays at a time
            self._pause_all_media_except(media_index)
            player.play()
            # If this media is currently on program output, apply audio delay correction
            if getattr(self, 'current_output', None) == ('media', media_index):
                print(f"Media {media_index} started playing on program output - applying audio delay correction...")
                self._auto_apply_audio_delay_correction()
        self.update_media_controls(media_index)

    def toggle_media_audio(self, media_index):
        """Toggle audio mute for the specified media (Qt Multimedia)"""
        # Only allow unmuting if this media is the current output; otherwise enforce mute
        is_current_output = getattr(self, 'current_output', None) == ('media', media_index)
        audio_output = self.media_audio_outputs[media_index]
        if is_current_output:
            # Respect Global Mute: if enabled, force muted
            if getattr(self, 'global_audio_muted', False):
                print("Global mute is enabled; media will remain muted until global mute is disabled.")
                audio_output.setMuted(True)
            else:
                audio_output.setMuted(not audio_output.isMuted())
        else:
            # Enforce muted when not on program output
            audio_output.setMuted(True)
            print(f"Media {media_index} audio can only be unmuted when routed to output.")
        # Persist and reflect state
        setattr(self, f"media{media_index}_audio_muted", audio_output.isMuted())
        btn_attr = f"media{media_index}AudioButton"
        if hasattr(self, btn_attr):
            btn = getattr(self, btn_attr)
            # If global mute is on, always show Mute icon
            force_muted = audio_output.isMuted() or getattr(self, 'global_audio_muted', False)
            btn.setIcon(self.get_icon("Mute.png" if force_muted else "Volume.png"))

    def seek_media(self, media_index, position_percent):
        """Seek in media based on percent (0-100)"""
        player = self.media_players[media_index]
        dur = max(1, player.duration())
        target_ms = int(dur * (position_percent / 100.0))
        player.setPosition(target_ms)
        # If this media is on Program and streaming is active, resync stream to this new position
        try:
            if getattr(self, 'current_output', None) == ('media', media_index) and hasattr(self, 'stream_controller'):
                sc = self.stream_controller
                if hasattr(sc, 'is_running') and sc.is_running():
                    media_path = self.get_current_program_media_audio_path()
                    if media_path:
                        sc.resync_to_media(media_path, target_ms)
                        # Apply audio delay correction after seeking
                        print(f"Media {media_index} seeked - reapplying audio delay correction...")
                        self._auto_apply_audio_delay_correction()
        except Exception as e:
            print(f"Error resyncing stream on seek: {e}")

    def load_media(self, media_index, file_path):
        """Load the specified media file (Qt Multimedia)"""
        try:
            # Check if file exists
            if not os.path.exists(file_path):
                print(f"Error: Media file does not exist: {file_path}")
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.warning(self, "File Not Found", 
                                   f"The selected file does not exist:\n{file_path}")
                return
            
            # Get file info
            file_size = os.path.getsize(file_path)
            file_ext = os.path.splitext(file_path)[1].lower()
            print(f"Loading Media {media_index}: {file_path}")
            print(f"  File size: {file_size:,} bytes")
            print(f"  File extension: {file_ext}")
            
            player = self.media_players[media_index]
            
            # Stop any current playback
            if player.playbackState() != QMediaPlayer.PlaybackState.StoppedState:
                player.stop()
            
            # Clear current source
            player.setSource(QUrl())
            
            # Set new source
            url = QUrl.fromLocalFile(file_path)
            print(f"  Setting source URL: {url.toString()}")
            player.setSource(url)
            
            # Wait a moment for media to load
            QApplication.processEvents()
            
            # Media should be paused by default when loaded
            player.pause()
            self.update_media_controls(media_index)
            
            print(f"  Media {media_index} loaded successfully (paused by default)")
            print(f"  Audio delay correction will be applied automatically when streaming (configurable)")
            
            # If this media becomes active and there's a 5-second delay issue, 
            # automatically apply a negative offset to compensate
            if hasattr(self, '_auto_sync_correction') and self._auto_sync_correction:
                print(f"  Auto-sync correction enabled for Media {media_index}")

            # Remember media file path for streaming audio mapping
            if not hasattr(self, 'media_paths'):
                self.media_paths = {}
            self.media_paths[media_index] = file_path

            # Immediately set output if this media is selected (use original image if available)
            if not getattr(self, '_transition_running', False) and self.current_output == ('media', media_index):
                if media_index in self.last_media_image:
                    self._set_output_image(self.last_media_image[media_index])
                elif media_index in self.last_media_pixmap:
                    self._set_output_pixmap(self.last_media_pixmap[media_index])
                    
        except Exception as e:
            print(f"Error loading media {media_index}: {e}")
            import traceback
            traceback.print_exc()
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Media Load Error", 
                               f"Failed to load media file:\n{str(e)}")

    def _on_media_position_changed(self, media_index, pos_ms):
        """Update UI when media position changes"""
        try:
            # Update slider
            slider_attr = {1: 'horizontalSlider', 2: 'horizontalSlider_2', 3: 'horizontalSlider_3'}.get(media_index)
            if slider_attr and hasattr(self, slider_attr):
                slider = getattr(self, slider_attr)
                if slider:
                    dur = max(1, self.media_players[media_index].duration())
                    percent = int((pos_ms / dur) * 100)
                    slider.blockSignals(True)
                    slider.setValue(percent)
                    slider.blockSignals(False)
        except RuntimeError:
            # Ignore "wrapped C/C++ object has been deleted"
            pass
        except Exception as e:
            # print(f"Slider update error: {e}")
            pass

        # Update controls (icon)
        self.update_media_controls(media_index)

    def _on_media_duration_changed(self, media_index, dur_ms):
        """Handle duration updates if needed (placeholder for future)"""
        pass
    
    def _on_media_error(self, media_index, error):
        """Handle media player errors"""
        error_string = {
            QMediaPlayer.Error.NoError: "No error",
            QMediaPlayer.Error.ResourceError: "Resource/file error",
            QMediaPlayer.Error.FormatError: "Format not supported",
            QMediaPlayer.Error.NetworkError: "Network error",
            QMediaPlayer.Error.AccessDeniedError: "Access denied"
        }.get(error, f"Unknown error: {error}")
        
        print(f"Media {media_index} error: {error_string}")
        
        # Show error message to user
        if error != QMediaPlayer.Error.NoError:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self, f"Media {media_index} Error", 
                               f"Failed to load media: {error_string}\n\n"
                               f"Please check that the file exists and is in a supported format.")
    
    def _on_media_status_changed(self, media_index, status):
        """Handle media status changes for debugging"""
        status_string = {
            QMediaPlayer.MediaStatus.NoMedia: "No media",
            QMediaPlayer.MediaStatus.LoadingMedia: "Loading media",
            QMediaPlayer.MediaStatus.LoadedMedia: "Media loaded",
            QMediaPlayer.MediaStatus.StalledMedia: "Media stalled",
            QMediaPlayer.MediaStatus.BufferingMedia: "Buffering media",
            QMediaPlayer.MediaStatus.BufferedMedia: "Media buffered",
            QMediaPlayer.MediaStatus.EndOfMedia: "End of media",
            QMediaPlayer.MediaStatus.InvalidMedia: "Invalid media"
        }.get(status, f"Unknown status: {status}")
        
        print(f"Media {media_index} status: {status_string}")
        
        # If media is invalid, show error
        if status == QMediaPlayer.MediaStatus.InvalidMedia:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self, f"Media {media_index} Invalid", 
                               f"The selected media file is invalid or corrupted.\n"
                               f"Please select a different file.")
    
    def _on_playback_state_changed(self, media_index, state):
        """Handle playback state changes"""
        state_string = {
            QMediaPlayer.PlaybackState.StoppedState: "Stopped",
            QMediaPlayer.PlaybackState.PlayingState: "Playing",
            QMediaPlayer.PlaybackState.PausedState: "Paused"
        }.get(state, f"Unknown state: {state}")
        
        print(f"Media {media_index} playback state: {state_string}")

    def _on_media_frame(self, media_index, video_frame):
        """Handle incoming media frames from QVideoSink and render to the media frame and output preview if selected"""
        try:
            image = video_frame.toImage()
            if image is not None and not image.isNull():
                # Debug: Only log first few frames to avoid spam
                if not hasattr(self, '_media_frame_count'):
                    self._media_frame_count = {}
                if media_index not in self._media_frame_count:
                    self._media_frame_count[media_index] = 0
                self._media_frame_count[media_index] += 1
                if self._media_frame_count[media_index] <= 3:
                    print(f"🎬 Media-{media_index}: Received frame {image.width()}x{image.height()}")
            
            # Update the current source in graphics output if this media is on program
            if hasattr(self, '_graphics_output') and hasattr(self, 'outputSource') and \
               self.outputSource == 'media' and self.outputSourceIndex == media_index:
                self._graphics_output._current_source = {'type': 'media', 'index': media_index}
                self._graphics_output._last_frame = image
            if image.isNull():
                return
            # ✅ APPLY MEDIA PROCESSING (speed, scaling, effects, etc.)
            processed_image = image
            try:
                from media_processor import media_processors
                # Only process if settings are actually applied (not default values)
                if media_processors[media_index].is_enabled():
                    processed_result = media_processors[media_index].process_frame(image)
                    if processed_result is not None:
                        processed_image = processed_result
                        print(f"✅ Applied media processing to Media-{media_index}")
            except Exception as e:
                print(f"Media processing error for Media-{media_index}: {e}")
            
            # Cache processed image for high-quality output scaling
            self.last_media_image[media_index] = processed_image.copy()
            pix = QPixmap.fromImage(processed_image)
            # Ensure media label exists
            self._ensure_media_label(media_index)
            frame_attr = f"mediaVideoFrame{media_index}"
            if hasattr(self, frame_attr):
                frame = getattr(self, frame_attr)
                target_size = frame.size()
                if target_size.width() <= 1 or target_size.height() <= 1:
                    ms = frame.minimumSize()
                    target_size = ms if ms.isValid() else QSize(320, 180)
                scaled = pix.scaled(target_size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                if hasattr(frame, '_video_label'):
                    frame._video_label.setPixmap(scaled)
                # Store last and update output if selected
                self.last_media_pixmap[media_index] = scaled
                if not getattr(self, '_transition_running', False) and self.current_output == ('media', media_index):
                    # Use original for output to avoid scaling artifacts
                    self._set_output_image(self.last_media_image[media_index])

            # 4. Update Preview Monitor (Fix for Media Preview Playback)
            if hasattr(self, 'active_preview_source') and self.active_preview_source == ('media', media_index):
                 if hasattr(self, 'preview_video_label'):
                    # Calculate size once
                    preview_size = self.preview_video_label.size()
                    if preview_size.width() > 1 and preview_size.height() > 1:
                        # Use cached processed image if available, else raw
                        src_img = self.last_media_image.get(media_index, image)
                        preview_pix = QPixmap.fromImage(src_img).scaled(
                            preview_size,
                            Qt.AspectRatioMode.KeepAspectRatio,
                            Qt.TransformationMode.SmoothTransformation,
                        )
                        self.preview_video_label.setPixmap(preview_pix)
                        self.preview_video_label.setText("")

            # 5. Loop Logic (if enabled)
            # Handled via QMediaPlayer loops usually, but if manual loop needed:
            # if self.media_loops[media_index] and player.mediaStatus() == QMediaPlayer.MediaStatus.EndOfMedia:
            #     player.play()

        except Exception as e:
            print(f"Error rendering media frame for Media-{media_index}: {e}")

    def _ensure_media_label(self, media_index):
        """Ensure a QLabel exists inside media frame to render pixmap"""
        frame_attr = f"mediaVideoFrame{media_index}"
        if hasattr(self, frame_attr):
            frame = getattr(self, frame_attr)
            if not hasattr(frame, '_video_label'):
                from PyQt6.QtWidgets import QLabel, QVBoxLayout, QSizePolicy
                label = QLabel(frame)
                label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
                if not frame.layout():
                    layout = QVBoxLayout(frame)
                    layout.setContentsMargins(0, 0, 0, 0)
                    frame.setLayout(layout)
                frame.layout().addWidget(label)
                frame._video_label = label

    # Phase 2: Input audio monitoring helpers
    # Phase 2: Input audio monitoring helpers
    def _ensure_input_audio(self, input_number):
        """Create QAudioSource and QAudioSink to monitor input audio (PyQt6)."""
        if not hasattr(self, 'input_audio_sources'):
            self.input_audio_sources = {}
        if not hasattr(self, 'input_audio_sinks'):
            self.input_audio_sinks = {}
        if not hasattr(self, 'input_audio_timers'):
            self.input_audio_timers = {}

        if input_number in self.input_audio_sources:
            return
        
        # Use default input/output devices for now
        input_dev = QMediaDevices.defaultAudioInput()
        output_dev = QMediaDevices.defaultAudioOutput()
        
        if input_dev.isNull() or output_dev.isNull():
             # print(f"Input audio warning: Default audio devices not found for input {input_number}")
             return

        # Try to find a common format
        from PyQt6.QtMultimedia import QAudioFormat
        
        # Start with input device's preferred format
        format = input_dev.preferredFormat()
        
        # If invalid, try standard defaults
        if not format.isValid():
            format = QAudioFormat()
            format.setSampleRate(48000)
            format.setChannelCount(2)
            format.setSampleFormat(QAudioFormat.SampleFormat.Int16)
        
        # Check if output supports it
        if not output_dev.isFormatSupported(format):
            # Try output preferred
            format = output_dev.preferredFormat()
        
        # If still issue, try standard
        if not output_dev.isFormatSupported(format):
             format = QAudioFormat()
             format.setSampleRate(48000)
             format.setChannelCount(2)
             format.setSampleFormat(QAudioFormat.SampleFormat.Int16)

        try:
            source = QAudioSource(input_dev, format)
            sink = QAudioSink(output_dev, format)
            self.input_audio_sources[input_number] = source
            self.input_audio_sinks[input_number] = sink

            # Start monitoring immediately unless muted: shuttle bytes from mic to speaker
            if not getattr(self, f"input{input_number}_audio_muted", True):
                out_dev = sink.start()
                in_dev = source.start()
                
                # Check for errors
                # if source.error() != QAudioSource.Error.NoError:
                #      print(f"Audio Source Error: {source.error()}")
                # if sink.error() != QAudioSink.Error.NoError:
                #      print(f"Audio Sink Error: {sink.error()}")

                from PyQt6.QtCore import QTimer
                t = QTimer(self)
                t.setInterval(10)
                def pump():
                    try:
                        # Read available bytes
                        bytes_available = source.bytesAvailable()
                        if bytes_available > 0:
                            data = in_dev.read(bytes_available)
                            if data:
                                out_dev.write(data)
                    except Exception:
                        pass
                t.timeout.connect(pump)
                t.start()
                self.input_audio_timers[input_number] = t
        except Exception as e:
            print(f"Error initializing audio for input {input_number}: {e}")

    def _stop_input_audio(self, input_number):
        if hasattr(self, 'input_audio_timers') and input_number in self.input_audio_timers:
            try:
                self.input_audio_timers[input_number].stop()
            except Exception:
                pass
            del self.input_audio_timers[input_number]
        if hasattr(self, 'input_audio_sources') and input_number in self.input_audio_sources:
            try:
                self.input_audio_sources[input_number].stop()
            except Exception:
                pass
            del self.input_audio_sources[input_number]
        if input_number in self.input_audio_sinks:
            try:
                self.input_audio_sinks[input_number].stop()
            except Exception:
                pass
            del self.input_audio_sinks[input_number]

    def apply_main_panel_stretch(self):
        """Set 50/50 stretch for left and right panels at the top level layout."""
        try:
            cw = self.centralWidget()
            if not cw:
                return
            top_layout = cw.layout()
            if not top_layout or not hasattr(top_layout, 'setStretch'):
                return
            # Find indices of items that contain the left and right panel layouts
            left_idx = right_idx = None
            for i in range(top_layout.count()):
                item = top_layout.itemAt(i)
                lay = item.layout() if item is not None else None
                if lay and lay.objectName() == 'verticalLayout_leftPanel':
                    left_idx = i
                if lay and lay.objectName() == 'verticalLayout_rightPanel':
                    right_idx = i
            # If not found as direct children, try to inspect child widgets' layouts
            if left_idx is None or right_idx is None:
                for i in range(top_layout.count()):
                    item = top_layout.itemAt(i)
                    w = item.widget() if item is not None else None
                    if w and hasattr(w, 'layout') and w.layout():
                        lay = w.layout()
                        # Check children of this layout
                        for j in range(lay.count()):
                            sub_item = lay.itemAt(j)
                            sub_lay = sub_item.layout() if sub_item else None
                            if sub_lay:
                                if sub_lay.objectName() == 'verticalLayout_leftPanel':
                                    left_idx = i
                                if sub_lay.objectName() == 'verticalLayout_rightPanel':
                                    right_idx = i
            if left_idx is not None and right_idx is not None:
                top_layout.setStretch(left_idx, 1)
                top_layout.setStretch(right_idx, 1)
        except Exception as e:
            print(f"Error applying main panel stretch: {e}")

    def apply_right_panel_stretch(self):
        """Ensure the transitions panel grows to absorb extra vertical space on the right panel.
        This prevents large empty gaps below 16:9 video boxes when the window is tall.
        """
        try:
            if not hasattr(self, 'tabWidget_transitions'):
                return
            # Ensure transitions widget is willing to expand
            from PyQt6.QtWidgets import QSizePolicy
            self.tabWidget_transitions.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            # Find its immediate parent layout and set stretch
            parent = self.tabWidget_transitions.parent()
            while parent and (not hasattr(parent, 'layout') or parent.layout() is None):
                parent = parent.parent()
            if not parent:
                return
            lay = parent.layout()
            if not lay or not hasattr(lay, 'setStretch'):
                return
            trans_index = None
            for i in range(lay.count()):
                item = lay.itemAt(i)
                if item and item.widget() is self.tabWidget_transitions:
                    trans_index = i
                    break
            if trans_index is None:
                return
            # Minimize stretch for other rows, maximize for transitions row
            for i in range(lay.count()):
                lay.setStretch(i, 0)
            lay.setStretch(trans_index, 1)
        except Exception as e:
            print(f"Error applying right panel stretch: {e}")

    def apply_left_panel_stretch(self):
        """Prioritize outputPreview height in the left panel. Ensure output grows more than
        the effects area when the window is tall, keeping output 16:9 and avoiding width-only stretching.
        """
        try:
            from PyQt6.QtWidgets import QSizePolicy
            # Determine which effects UI is present
            has_tabs = hasattr(self, 'tabWidget_effects') and self.tabWidget_effects is not None
            has_pep = hasattr(self, 'premiere_effects_panel') and self.premiere_effects_panel is not None
            if not (has_tabs or has_pep):
                return
            # Effects can expand but shouldn't steal priority from output
            if has_tabs:
                self.tabWidget_effects.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            if has_pep:
                self.premiere_effects_panel.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

            cw = self.centralWidget()
            if not cw or not cw.layout():
                return
            # Find left panel vertical layout
            left_layout = None
            tl = cw.layout()
            for i in range(tl.count()):
                item = tl.itemAt(i)
                lay = item.layout() if item else None
                if lay and lay.objectName() == 'verticalLayout_leftPanel':
                    left_layout = lay
                    break
                w = item.widget() if item else None
                if w and hasattr(w, 'layout') and w.layout() and w.layout().objectName() == 'verticalLayout_leftPanel':
                    left_layout = w.layout()
                    break
            if not left_layout or not hasattr(left_layout, 'setStretch'):
                return

            # Locate container indexes
            output_idx = None
            effects_idx = None
            for i in range(left_layout.count()):
                item = left_layout.itemAt(i)
                w = item.widget() if item else None
                if w and getattr(w, 'objectName', lambda: '')() == 'outputPreview':
                    output_idx = i
                if w and hasattr(w, 'findChild'):
                    # Old tabs container
                    if has_tabs:
                        tw = w.findChild(type(self.tabWidget_effects), 'tabWidget_effects')
                        if tw is not None:
                            effects_idx = i
                    # New Premiere panel container
                    try:
                        from premiere_effects_panel_final import FinalEffectsPanel as _PEP
                        if has_pep and w.findChild(_PEP) is not None:
                            effects_idx = i
                    except Exception:
                        pass

            # Default: last item is effects
            if effects_idx is None and left_layout.count() > 0:
                effects_idx = left_layout.count() - 1

            # Apply stretches: output gets higher priority
            for i in range(left_layout.count()):
                left_layout.setStretch(i, 0)
            if output_idx is not None:
                left_layout.setStretch(output_idx, 3)
            if effects_idx is not None:
                left_layout.setStretch(effects_idx, 1)
        except Exception as e:
            print(f"Error applying left panel stretch: {e}")

    def apply_left_splitter(self):
        """Replace the left panel stack with a QSplitter so Output keeps priority height
        and the user gets a robust, resizable layout. Output stays 16:9 via AspectRatioFrame.
        """
        try:
            cw = self.centralWidget()
            if not cw or not cw.layout():
                return
            # Find the left panel vertical layout
            left_layout = None
            tl = cw.layout()
            for i in range(tl.count()):
                item = tl.itemAt(i)
                lay = item.layout() if item else None
                if lay and lay.objectName() == 'verticalLayout_leftPanel':
                    left_layout = lay
                    break
                w = item.widget() if item else None
                if w and hasattr(w, 'layout') and w.layout() and w.layout().objectName() == 'verticalLayout_leftPanel':
                    left_layout = w.layout()
                    break
            if not left_layout:
                return

            # Identify direct child widgets: output container and effects container
            output_widget = None
            effects_container = None
            for i in range(left_layout.count()):
                item = left_layout.itemAt(i)
                w = item.widget() if item else None
                if not w:
                    continue
                if getattr(w, 'objectName', lambda: '')() == 'outputPreview':
                    output_widget = w
                # Check if this widget contains tabWidget_effects
                if hasattr(self, 'tabWidget_effects') and hasattr(w, 'findChild'):
                    found = w.findChild(type(self.tabWidget_effects), 'tabWidget_effects')
                    if found is not None:
                        effects_container = w
                # Also support the new PremiereEffectsPanel as the marker for the effects area
                # Use FinalEffectsPanel as the marker for the effects area (v2 not found)
                try:
                    from premiere_effects_panel_final import FinalEffectsPanel as _PEP
                    if isinstance(w, _PEP) or (hasattr(w, 'findChild') and w.findChild(_PEP) is not None):
                        effects_container = w
                except Exception:
                    pass

            # If effects container not detected, fall back to last widget in layout
            if effects_container is None:
                # Try to find an existing PremiereEffectsPanel anywhere and move it under left panel
                try:
                    from premiere_effects_panel_final import FinalEffectsPanel as _PEP
                    found_panel = None
                    for child in self.findChildren(_PEP):
                        found_panel = child
                        break
                    if found_panel is not None:
                        try:
                            par = found_panel.parent()
                            if par and hasattr(par, 'layout') and par.layout():
                                par.layout().removeWidget(found_panel)
                        except Exception:
                            pass
                        # Insert as a new widget at the bottom of the left layout
                        left_layout.addWidget(found_panel)
                        effects_container = found_panel
                except Exception:
                    pass
                # Final fallback to last item
                if effects_container is None and left_layout.count() > 0:
                    last_item = left_layout.itemAt(left_layout.count() - 1)
                    effects_container = last_item.widget() if last_item else None

            if not output_widget or not effects_container:
                return

            # Remove both from layout without deleting
            for target in (output_widget, effects_container):
                for i in range(left_layout.count() - 1, -1, -1):
                    if left_layout.itemAt(i) and left_layout.itemAt(i).widget() is target:
                        left_layout.takeAt(i)
                        break

            # Create splitter
            splitter = QSplitter(Qt.Orientation.Vertical, cw)
            splitter.setChildrenCollapsible(False)
            splitter.setHandleWidth(6)
            splitter.addWidget(output_widget)
            splitter.addWidget(effects_container)
            splitter.setStretchFactor(0, 3)  # Output priority
            splitter.setStretchFactor(1, 1)  # Effects grows but less

            # Insert splitter back into left layout
            left_layout.addWidget(splitter)
            # Keep a handle to tune sizes later
            self._left_splitter = splitter
        except Exception as e:
            print(f"Error applying left splitter: {e}")

    def apply_right_splitter(self):
        """Replace the right panel stack with a QSplitter so Transitions can absorb extra height
        while keeping the sources grid compact. This avoids large blank gaps under 16:9 tiles.
        """
        try:
            cw = self.centralWidget()
            if not cw or not cw.layout():
                return
            # Find the right panel vertical layout
            right_layout = None
            tl = cw.layout()
            for i in range(tl.count()):
                item = tl.itemAt(i)
                lay = item.layout() if item else None
                if lay and lay.objectName() == 'verticalLayout_rightPanel':
                    right_layout = lay
                    break
                w = item.widget() if item else None
                if w and hasattr(w, 'layout') and w.layout() and w.layout().objectName() == 'verticalLayout_rightPanel':
                    right_layout = w.layout()
                    break
            if not right_layout:
                return

            # Identify transitions and the block above it (sources cluster)
            transitions_widget = getattr(self, 'tabWidget_transitions', None)
            sources_container = None
            trans_idx = None
            for i in range(right_layout.count()):
                it = right_layout.itemAt(i)
                w = it.widget() if it else None
                if w is transitions_widget:
                    trans_idx = i
                    # Previous visible widget is considered sources container
                    # Look upward for the nearest widget item
                    for j in range(i - 1, -1, -1):
                        prev = right_layout.itemAt(j)
                        if prev and prev.widget():
                            sources_container = prev.widget()
                            break
                    break
            if not transitions_widget or not sources_container:
                return

            # Take both out of layout (without deleting)
            for target in (sources_container, transitions_widget):
                for i in range(right_layout.count() - 1, -1, -1):
                    if right_layout.itemAt(i) and right_layout.itemAt(i).widget() is target:
                        right_layout.takeAt(i)
                        break

            # Create splitter and set factors
            splitter = QSplitter(Qt.Orientation.Vertical, cw)
            splitter.setChildrenCollapsible(False)
            splitter.setHandleWidth(6)
            splitter.addWidget(sources_container)
            splitter.addWidget(transitions_widget)
            splitter.setStretchFactor(0, 2)  # Sources
            splitter.setStretchFactor(1, 3)  # Transitions grows more

            right_layout.addWidget(splitter)
            # Keep a handle to tune sizes later
            self._right_splitter = splitter
        except Exception as e:
            print(f"Error applying right splitter: {e}")

    def _init_splitter_sizes(self):
        """Initialize splitter sizes based on current window height for a good default layout."""
        try:
            h = max(1, self.height())
            # Left: Output ~65%, Effects ~35%
            if hasattr(self, '_left_splitter') and self._left_splitter:
                self._left_splitter.setSizes([int(h * 0.65), int(h * 0.35)])
            # Right: Sources ~40%, Transitions ~60%
            if hasattr(self, '_right_splitter') and self._right_splitter:
                self._right_splitter.setSizes([int(h * 0.40), int(h * 0.60)])
            # One more pass to align left with actual width/aspect once laid out
            QTimer.singleShot(0, self._adjust_splitters_for_aspect)
        except Exception as e:
            print(f"Error initializing splitter sizes: {e}")

    def resizeEvent(self, event):
        """Allow responsive sizing of video/monitor area with 16:9 aspect ratio."""
        super().resizeEvent(event)
        
        # Ignore minimized windows to avoid errors
        if self.height() <= 0 or self.width() <= 0:
            return
        
        try:
            # Allow monitor_area to size responsively (do NOT force fixed heights)
            # The AspectRatioFrame and heightForWidth policy handle 16:9 automatically
            if hasattr(self, 'monitor_area') and self.monitor_area:
                # Only set minimum, allow maximum to be unlimited for responsiveness
                self.monitor_area.setMinimumHeight(360)
                # Do NOT set maximum height - this prevents proper scaling
                
                # Schedule layout update to take effect
                QTimer.singleShot(0, self.update)
        except Exception as e:
            print(f"[VIDEO HEIGHT] Error: {e}")

    def apply_forced_layout(self):
        """Apply responsive layout when window appears. Called from showEvent."""
        try:
            # Allow monitor_area to size responsively with minimum height constraint
            if hasattr(self, 'monitor_area') and self.monitor_area:
                self.monitor_area.setMinimumHeight(360)
                # Do NOT set maximum height - allows responsive scaling
            
            # Set workspace (controls) to expand but not force minimum
            if hasattr(self, 'workspace_stack') and self.workspace_stack:
                self.workspace_stack.setMinimumHeight(200)
                self.workspace_stack.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            
            # Refresh monitor styles to handle Windows minimize/restore bug
            self._refresh_monitor_styles()
            
            # Force immediate layout update
            if self.centralWidget() and self.centralWidget().layout():
                self.centralWidget().layout().activate()
        except Exception as e:
            print(f"[LAYOUT] Error: {e}")

    def _refresh_monitor_styles(self):
        """Refresh monitor styles to ensure they persist after minimize/restore on Windows."""
        try:
            # Reapply styling to preview monitor
            if hasattr(self, 'preview_video_label'):
                self.preview_video_label.setStyleSheet("background-color: black; color: rgba(255, 255, 255, 0.4); font-size: 13px; font-weight: 500;")
            
            # Find and reapply Preview frame styles with correct size policies
            for widget in self.findChildren(QFrame, "previewMonitor"):
                widget.setStyleSheet("QFrame#previewMonitor { overflow: hidden; border: 2px solid #0078d4; border-radius: 4px; background-color: black; }")
                widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            
            # Find and reapply Program frame styles with correct size policies
            for widget in self.findChildren(QFrame, "programMonitor"):
                widget.setStyleSheet("QFrame#programMonitor { overflow: hidden; border: 2px solid #d13438; border-radius: 4px; background-color: black; }")
                widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            
            # Reapply container styles and size policies
            for widget in self.findChildren(QFrame, "previewContainer"):
                widget.setStyleSheet("QFrame#previewContainer { background-color: #1a1a1a; border: none; }")
                widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            
            for widget in self.findChildren(QFrame, "programContainer"):
                widget.setStyleSheet("QFrame#programContainer { background-color: #1a1a1a; border: none; }")
                widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            
            # Ensure titles are visible and properly styled with correct colors
            for label in self.findChildren(QLabel):
                if label.text() in ["Preview", "PREVIEW"]:
                    label.setStyleSheet("color: #0078d4; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px;")
                elif label.text() in ["Program Live", "PROGRAM LIVE"]:
                    label.setStyleSheet("color: #d13438; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px;")
        except Exception as e:
            print(f"[STYLE_REFRESH] Error: {e}")

    def _adjust_splitters_for_aspect(self):
        try:
            if hasattr(self, '_left_splitter') and self._left_splitter and hasattr(self, 'outputPreview'):
                splitter = self._left_splitter
                # Available panel height
                avail_h = max(1, splitter.height())
                # Allocate heights proportionally: video gets 75%, effects get 25%
                min_effects = 100
                out_h = max(300, int(avail_h * 0.75))
                eff_h = max(min_effects, avail_h - out_h)
                splitter.setSizes([out_h, eff_h])
                # Do NOT set fixed heights on frame - allows responsive sizing
                self.refresh_output_preview()
        except Exception as e:
            print(f"Error adjusting splitters: {e}")

    def _ensure_output_preview_label(self):
        """Install the GraphicsOutputWidget into outputPreview container."""
        if hasattr(self, 'outputPreview'):
            # FORCE Overlay to sit ON TOP of the video and match size
            if hasattr(self, 'graphics_widget') and hasattr(self, 'program_frame'):
                self.graphics_widget.setParent(self.program_frame)
                self.graphics_widget.raise_()
                self.graphics_widget.show()
                self.program_frame.resizeEvent = lambda e: self.graphics_widget.resize(e.size())
                self.graphics_widget.resize(self.program_frame.size())
            from PyQt6.QtWidgets import QVBoxLayout, QSizePolicy
            frame = self.outputPreview
            if self._graphics_output is None:
                # FIX 3: Cleanup old instance if it somehow still exists (in case method is called twice)
                pre_existing = getattr(self, '_graphics_output_temp', None)
                if pre_existing is not None:
                    try:
                        pre_existing._cleanup_render_thread()
                    except Exception:
                        pass
                # Try enhanced graphics output first (fixes pixelation)
                try:
                    from enhanced_graphics_output import EnhancedGraphicsOutputWidget
                    view = EnhancedGraphicsOutputWidget(frame)
                    print("Created Enhanced Graphics Output Widget (pixelation fixes enabled)")
                except ImportError:
                    if _USE_NEW_RENDERER:
                        # Prefer GPU only when supported; factory will still fall back to CPU safely
                        view = create_graphics_output_widget(frame, prefer_gpu=True)
                        renderer_type = "GPU" if hasattr(view, 'renderer') and getattr(view, 'renderer') else "CPU"
                        print(f"Created graphics output: {renderer_type}")
                    else:
                        # Force legacy CPU path to guarantee full feature parity
                        # No graphics_output.py available, fallback to EnhancedGraphicsOutputWidget
                        # Fix 2: Cleanup old instance if it exists before creating new one
                        if hasattr(self, '_graphics_output') and self._graphics_output is not None:
                            self._graphics_output._cleanup_render_thread()
                            self._graphics_output = None
                        from enhanced_graphics_output import EnhancedGraphicsOutputWidget as _LegacyGOW
                        view = _LegacyGOW(frame)
                view.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
                if not frame.layout():
                    layout = QVBoxLayout(frame)
                    layout.setContentsMargins(0, 0, 0, 0)
                    frame.setLayout(layout)
                else:
                    # Clear existing children (e.g., old QLabel)
                    while frame.layout().count():
                        item = frame.layout().takeAt(0)
                        w = item.widget()
                        if w:
                            w.setParent(None)
                frame.layout().addWidget(view)
                self._graphics_output = view

                # Effects workflow: ensure no overlay is applied at startup
                try:
                    self._graphics_output.clear_overlay(use_transition=False)
                except Exception:
                    try:
                        self._graphics_output.clear_overlay()
                    except Exception:
                        pass
                try:
                    self.program_overlay_path = None
                    self.preview_overlay_path = None
                except Exception:
                    pass

    def _install_output_aspect_guard(self):
        try:
            if not hasattr(self, 'outputPreview') or self.outputPreview is None:
                return
            if hasattr(self, '_output_aspect_guard') and self._output_aspect_guard:
                return
            class _Guard(QObject):
                def __init__(self, outer):
                    super().__init__(outer)
                    self.outer = outer
                def eventFilter(self, obj, event):
                    if event.type() == QEvent.Type.Resize and hasattr(self.outer, 'outputPreview'):
                        # Do NOT force fixed heights - allow responsive sizing
                        # The AspectRatioFrame and heightForWidth policy handle 16:9
                        pass
                    return QObject.eventFilter(self, obj, event)
            self._output_aspect_guard = _Guard(self)
            # Monitor both the output frame and its parent container for resizes
            self.outputPreview.installEventFilter(self._output_aspect_guard)
            if self.outputPreview.parent():
                self.outputPreview.parent().installEventFilter(self._output_aspect_guard)
        except Exception as e:
            print(f"Error installing output aspect guard: {e}")

    def _set_output_pixmap(self, pixmap):
        """Backward-compatible: convert to QImage and pass to graphics output."""
        if pixmap is None or pixmap.isNull():
            self._set_output_image(None)
            return
        self._set_output_image(pixmap.toImage())

    def _set_output_image(self, image: QImage):
        """Send frame to graphics output widget; falls back to black if None."""
        final_image = image
        if image is not None:
            try:
                text_settings = None
                if hasattr(self, 'program_text_settings') and isinstance(self.program_text_settings, dict):
                    if self.program_text_settings.get('text', '').strip():
                        # Use program text but always apply preview's CURRENT position settings
                        text_settings = dict(self.program_text_settings)
                        if hasattr(self, 'preview_text_settings') and isinstance(self.preview_text_settings, dict):
                            text_settings['position_x'] = self.preview_text_settings.get('position_x', 50)
                            text_settings['position_y'] = self.preview_text_settings.get('position_y', 90)
                            text_settings['alignment'] = self.preview_text_settings.get('alignment', 'center')

                if text_settings:
                    from text_overlay_renderer import TextOverlayRenderer
                    if not hasattr(self, '_program_text_renderer'):
                        self._program_text_renderer = TextOverlayRenderer()
                    self._program_text_renderer.update_settings(text_settings)
                    final_image = self._program_text_renderer.render_overlay(image)
            except Exception as e:
                print(f"[Program Text] Error: {e}")
                final_image = image

        if self._graphics_output is not None:
            self._graphics_output.set_frame(final_image)

    def set_output_source(self, source_type, index):
        """Switch the main output to the selected source.
        If a transition is selected, perform animated switch; otherwise immediate.
        """
        # If we're already in a transition, ignore new requests
        if getattr(self, '_transition_running', False):
            return
        # Notify streaming backends to clear old audio and add a small safety delay
        try:
            self._notify_stream_source_switch(delay_ms=150)
        except Exception:
            pass
            
        # Update the current source in graphics output
        if hasattr(self, '_graphics_output'):
            if source_type == 'input':
                self._graphics_output._current_source = {'type': 'input', 'index': index}
            elif source_type == 'media':
                self._graphics_output._current_source = {'type': 'media', 'index': index}
            else:
                self._graphics_output._current_source = {'type': None, 'index': -1}
        try:
            sel = (self.selected_transition or 'None').strip()
            if sel.lower() not in ('none', ''):
                self.begin_transition_to(source_type, index)
                return
        except Exception:
            pass
        self._set_output_source_immediate(source_type, index)

    def _pause_all_media_except(self, active_media_index=None):
        """Pause all media players except the specified one"""
        paused_media = []
        for media_idx in [1, 2, 3]:
            if media_idx != active_media_index:
                player = self.media_players[media_idx]
                if player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
                    player.pause()
                    self.update_media_controls(media_idx)
                    paused_media.append(media_idx)
        if paused_media:
            print(f"Paused media: {paused_media} (ensuring only one media plays at a time)")

    def _set_output_source_immediate(self, source_type, index):
        """Existing immediate switch behavior (extracted from original)."""
        # Handle media playback logic: pause all media, then start selected media if it's a media source
        if source_type == 'media':
            # Pause all media first
            self._pause_all_media_except()
            # Start the selected media
            selected_player = self.media_players[index]
            if selected_player.playbackState() != QMediaPlayer.PlaybackState.PlayingState:
                selected_player.play()
                self.update_media_controls(index)
                print(f"Started playback for Media {index} (switched to program output)")
            else:
                print(f"Media {index} already playing (switched to program output)")
            
            # Automatically apply audio delay correction for streaming
            self._auto_apply_audio_delay_correction()
        else:
            # If switching to input source, pause all media
            self._pause_all_media_except()
            print(f"Switched to Input {index} (paused all media)")
        
        self.current_output = (source_type, index)
        
        # Clear pending frame queues to discard backlog from previous input
        # Prevents FPS drops when switching inputs due to queued deferred tasks
        if hasattr(self, '_qt_frame_deferred_pending'):
            self._qt_frame_deferred_pending.clear()
        if hasattr(self, '_qt_pending_frames'):
            self._qt_pending_frames.clear()
        
        # Attempt to immediately update output with last known frame
        if getattr(self, '_transition_running', False):
            return
        if source_type == 'input':
            if index in self.last_input_image:
                self._set_output_image(self.last_input_image[index])
            elif index in self.last_input_pixmap:
                self._set_output_pixmap(self.last_input_pixmap[index])
        elif source_type == 'media':
            if index in self.last_media_image:
                self._set_output_image(self.last_media_image[index])
            elif index in self.last_media_pixmap:
                self._set_output_pixmap(self.last_media_pixmap[index])

        # Enforce media audio policy: only unmute the media routed to output; mute all others.
        # Respect Global Mute: if enabled, force all media muted regardless of program source.
        try:
            for i in (1, 2, 3):
                if getattr(self, 'global_audio_muted', False):
                    should_mute = True
                else:
                    should_mute = not (source_type == 'media' and index == i)
                # Persist state flag
                setattr(self, f"media{i}_audio_muted", should_mute)
                # Apply to actual audio output if available
                if hasattr(self, 'media_audio_outputs') and i in self.media_audio_outputs:
                    self.media_audio_outputs[i].setMuted(should_mute)
                # Reflect on UI button icon if present
                btn_attr = f"media{i}AudioButton"
                if hasattr(self, btn_attr):
                    btn = getattr(self, btn_attr)
                    btn.setIcon(self.get_icon("Mute.png" if should_mute else "Volume.png"))
        except Exception as e:
            print(f"Error enforcing media audio policy: {e}")

        # Auto-manage input audio monitoring so the selected input is heard
        try:
            for i in (1, 2, 3):
                if source_type == 'input' and index == i and not getattr(self, f"input{i}_audio_muted", True):
                    self._ensure_input_audio(i)
                else:
                    self._stop_input_audio(i)
        except Exception as e:
            print(f"Error managing input audio monitoring: {e}")

        # If streaming and the new program is a media, resync streaming audio to the current position
        try:
            if source_type == 'media' and hasattr(self, 'stream_controller'):
                sc = self.stream_controller
                if hasattr(sc, 'is_running') and sc.is_running():
                    media_path = self.get_current_program_media_audio_path()
                    pos_ms = self.get_current_program_media_position_ms() or 0
                    if media_path:
                        sc.resync_to_media(media_path, pos_ms)
        except Exception as e:
            print(f"Error resyncing stream on source switch: {e}")

        # Keep external display mirror in perfect sync: match FPS and maximize resolution
        try:
            if hasattr(self, 'mirror_controller') and self.mirror_controller and self.mirror_controller.is_running():
                from config import app_config as _cfg
                cur_fps = int(_cfg.get('ui.preview_fps', 60))
                self.mirror_controller.update({'fps': cur_fps, 'maximize': True})
        except Exception:
            pass

    def _notify_stream_source_switch(self, delay_ms: int = 150):
        """Inform all running streaming controllers that program source switched.
        This lets the PyAV master-clock backend discard buffered audio and apply
        a tiny delay so the new source's audio does not lead video.
        """
        try:
            # New multi-stream controllers
            if hasattr(self, 'stream_controllers') and isinstance(self.stream_controllers, dict):
                for sc in self.stream_controllers.values():
                    try:
                        if hasattr(sc, 'is_running') and sc.is_running():
                            if hasattr(sc, 'on_source_switch'):
                                sc.on_source_switch(int(max(0, delay_ms)))
                    except Exception:
                        pass
            # Legacy single controller
            elif hasattr(self, 'stream_controller') and self.stream_controller is not None:
                sc = self.stream_controller
                if hasattr(sc, 'is_running') and sc.is_running():
                    if hasattr(sc, 'on_source_switch'):
                        sc.on_source_switch(int(max(0, delay_ms)))
        except Exception:
            pass

    def begin_transition_to(self, source_type: str, index: int):
        """Run a non-blocking transition from the current program frame to the target source.
        
        ISSUE 3 FIX: Apply preview overlay immediately so it renders during the transition.
        This ensures the program shows the preview's complete appearance (source + overlay).
        """
        try:
            if not self._graphics_output:
                self._set_output_source_immediate(source_type, index)
                return
            
            # ISSUE 3 FIX: Switch to preview's overlay IMMEDIATELY for transition rendering
            # This ensures the overlay is visible during the transition animation
            try:
                preview_overlay = getattr(self, 'preview_overlay_path', None)
                if preview_overlay and os.path.exists(str(preview_overlay)):
                    # Use transition=True to smoothly fade overlay during effect change
                    self._graphics_output.set_overlay_from_path(str(preview_overlay), use_transition=True)
            except Exception as e:
                pass
            
            # Capture current composited frame from preview
            size = self._graphics_output._scene_size() if hasattr(self._graphics_output, '_scene_size') else self._graphics_output.size()
            if hasattr(size, 'width') and hasattr(size, 'height'):
                target_size = QSize(max(1, size.width()), max(1, size.height()))
            else:
                target_size = QSize(1280, 720)
            # Build base frames WITHOUT overlay for both current and target
            cur_src = getattr(self, 'current_output', None)
            if not cur_src or not isinstance(cur_src, tuple) or len(cur_src) != 2:
                # If we don't know current, fall back to immediate
                self._set_output_source_immediate(source_type, index)
                return
            a_base = self._get_base_frame_for_source(cur_src[0], int(cur_src[1]), target_size)
            b_base = self._get_base_frame_for_source(source_type, index, target_size)
            if a_base is None or a_base.isNull() or b_base is None or b_base.isNull():
                self._set_output_source_immediate(source_type, index)
                return
            tname = (self.selected_transition or 'Fade')
            dur = int(self.transition_duration_ms or 400)
            easing = (self.transition_easing or 'ease_in_out')
            # Start animated transition (pause normal updates until done)
            self._transition_running = True
            self.transition_manager.start_transition(
                a_base,
                b_base,
                transition_type=tname,
                duration_ms=dur,
                easing=easing,
                # IMPORTANT: send the raw transitioned video frame; the overlay is drawn by GraphicsOutputWidget.
                on_frame=lambda img: self._set_output_image(img),
                on_done=lambda st=source_type, idx=index: self._on_transition_done(st, idx)
            )
        except Exception as e:
            print(f"Transition error: {e}")
            self._set_output_source_immediate(source_type, index)

    def _finalize_switch_to(self, source_type: str, index: int):
        """After transition completes, set the new source for normal updates."""
        self._set_output_source_immediate(source_type, index)

    def _on_transition_done(self, source_type: str, index: int):
        """Clear transition lock and finalize switch safely.
        
        ISSUE 3 FIX: After transition completes, ensure program overlay is finalized.
        """
        try:
            self._transition_running = False
        except Exception:
            pass
        # If AUTO transition is running, swap Preview/Program buses consistently
        try:
            pending = getattr(self, '_pending_program_swap', None)
        except Exception:
            pending = None
        if isinstance(pending, dict) and pending.get('to'):
            try:
                to_src = pending.get('to')
                from_src = pending.get('from')
                if isinstance(to_src, tuple) and len(to_src) == 2:
                    self.active_program_source = (to_src[0], int(to_src[1]))
                    self.current_output = self.active_program_source
                if isinstance(from_src, tuple) and len(from_src) == 2:
                    # The old program becomes the new preview
                    self.active_preview_source = (from_src[0], int(from_src[1]))
                # Clear pending state
                try:
                    self._pending_program_swap = None
                except Exception:
                    pass
                # Update UI tallies and preview monitor
                try:
                    self.update_tally_lights()
                except Exception:
                    pass
                try:
                    pv = getattr(self, 'active_preview_source', None)
                    if pv and isinstance(pv, tuple) and len(pv) == 2:
                        if pv[0] == 'input':
                            self._update_preview_monitor(self.last_input_image.get(int(pv[1])), 'input', int(pv[1]))
                        elif pv[0] == 'media':
                            self._update_preview_monitor(self.last_media_image.get(int(pv[1])), 'media', int(pv[1]))
                except Exception:
                    pass

                # Effect workflow: commit preview effect to LIVE at end of AUTO
                # ISSUE 3 FIX: Ensure the overlay persists correctly after transition
                try:
                    self.program_overlay_path = getattr(self, 'preview_overlay_path', None)
                    if hasattr(self, '_graphics_output') and self._graphics_output is not None:
                        if self.program_overlay_path:
                            # Overlay should already be set (done in begin_transition_to)
                            # Just make sure it's finalized without transition
                            self._graphics_output.set_overlay_from_path(str(self.program_overlay_path), use_transition=False)
                        else:
                            self._graphics_output.clear_overlay(use_transition=False)
                    # Do NOT clear preview effect here; keep it on Preview for continued auditioning
                except Exception as e:
                    pass
                    
                # Promote preview text overlay settings to Program (Live) at end of AUTO
                try:
                    if hasattr(self, 'preview_text_settings') and isinstance(self.preview_text_settings, dict):
                        self.program_text_settings = dict(self.preview_text_settings)
                except Exception:
                    pass
            except Exception as e:
                pass
        # Finalize the program output switch
        self._finalize_switch_to(source_type, index)

    def _compose_frame_for_source(self, source_type: str, index: int, target_size: QSize) -> QImage | None:
        """Compose the target source frame with current overlay, off-screen."""
        try:
            # Base image from caches
            base: QImage | None = None
            if source_type == 'input':
                base = self.last_input_image.get(index) if hasattr(self, 'last_input_image') else None
                if base is None and hasattr(self, 'last_input_pixmap') and index in self.last_input_pixmap:
                    base = self.last_input_pixmap[index].toImage()
            elif source_type == 'media':
                base = self.last_media_image.get(index) if hasattr(self, 'last_media_image') else None
                if base is None and hasattr(self, 'last_media_pixmap') and index in self.last_media_pixmap:
                    base = self.last_media_pixmap[index].toImage()
            if base is None or base.isNull():
                return None
            # Ensure format
            if base.format() != QImage.Format.Format_ARGB32 and base.format() != QImage.Format.Format_RGBA8888:
                try:
                    base = base.convertToFormat(QImage.Format.Format_ARGB32)
                except Exception:
                    pass
            # Overlay composition using current overlay path (if any)
            eff = EffectManager()
            overlay_path = self._graphics_output.get_overlay_path() if hasattr(self._graphics_output, 'get_overlay_path') else None
            if overlay_path:
                eff.set_effect(overlay_path)
                composed = eff.compose(base, target_size)
            else:
                # Scale base to target, preserving aspect
                composed = base.scaled(target_size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                # Center on canvas
                canvas = QImage(target_size, QImage.Format.Format_ARGB32)
                from PyQt6.QtGui import QColor, QPainter
                canvas.fill(QColor(0, 0, 0, 255))
                p = QPainter(canvas)
                x = (target_size.width() - composed.width()) // 2
                y = (target_size.height() - composed.height()) // 2
                p.drawImage(x, y, composed)
                p.end()
                composed = canvas
            return composed
        except Exception:
            return None

    def _get_base_frame_for_source(self, source_type: str, index: int, target_size: QSize) -> QImage | None:
        """Return a base frame (no overlay applied), scaled and centered on a canvas of target_size."""
        try:
            # Fetch from last caches
            base: QImage | None = None
            if source_type == 'input':
                base = self.last_input_image.get(index) if hasattr(self, 'last_input_image') else None
                if base is None and hasattr(self, 'last_input_pixmap') and index in self.last_input_pixmap:
                    base = self.last_input_pixmap[index].toImage()
            elif source_type == 'media':
                base = self.last_media_image.get(index) if hasattr(self, 'last_media_image') else None
                if base is None and hasattr(self, 'last_media_pixmap') and index in self.last_media_pixmap:
                    base = self.last_media_pixmap[index].toImage()
            if base is None or base.isNull():
                return None
            # Scale with aspect and center on black canvas
            scaled = base.scaled(target_size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            canvas = QImage(target_size, QImage.Format.Format_ARGB32)
            from PyQt6.QtGui import QColor, QPainter
            canvas.fill(QColor(0, 0, 0, 255))
            p = QPainter(canvas)
            try:
                x = (target_size.width() - scaled.width()) // 2
                y = (target_size.height() - scaled.height()) // 2
                p.drawImage(x, y, scaled)
            finally:
                p.end()
            return canvas
        except Exception:
            return None

    def _apply_overlay_once(self, frame: QImage, target_size: QSize, eff: EffectManager | None) -> QImage:
        """Apply the current overlay exactly once over the provided frame."""
        try:
            if eff is None:
                return frame
            # EffectManager.compose clips to opening and draws overlay; it expects base content
            composed = eff.compose(frame, target_size)
            return composed if composed and not composed.isNull() else frame
        except Exception:
            return frame

    def setup_transitions_panel(self):
        """Dynamically create and populate the transitions grid from the catalog."""
        try:
            from PyQt6.QtWidgets import QPushButton, QGridLayout
            grid: QGridLayout = self.gridLayout_trans1
            if not grid:
                return

            # Clear any placeholder widgets from the UI file
            while grid.count():
                item = grid.takeAt(0)
                widget = item.widget()
                if widget is not None:
                    widget.deleteLater()

            # Store dynamically created buttons here
            self.transition_buttons = []
            entries = [('None', 'No transition (instant switch)')] + TRANSITIONS_CATALOG
            cols = 2 # Changed to 2 columns to fit better
            row, col = 0, 0

            for name, desc in entries:
                btn = QPushButton(name)
                btn.setToolTip(desc)
                btn.setCheckable(True)
                btn.setProperty("transition_name", name)
                # Improved stylesheet for text wrapping and visibility
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: #404040;
                        border: 2px solid #404040;
                        border-radius: 4px;
                        color: #ffffff;
                        font-size: 9px;
                        font-weight: bold;
                        padding: 2px;
                        text-align: center;
                        min-height: 30px;
                        max-height: 30px;
                        margin: 0px;
                        max-width: 90px;
                    }
                    QPushButton:hover {
                        background-color: #505050;
                        border-color: #555;
                    }
                    QPushButton:checked {
                        border-color: #00aaff;
                        background-color: #4a4a4a;
                    }
                """)
                btn.clicked.connect(self._on_transition_selected)
                grid.addWidget(btn, row, col)
                self.transition_buttons.append(btn)
                col += 1
                if col >= cols:
                    col = 0
                    row += 1
            
            # Restore selection
            self._update_transition_selection_ui()

        except Exception as e:
            print(f"Error dynamically populating transitions panel: {e}")

    def _on_transition_selected(self):
        """Handle click on any transition button (ONLY store, no-op until AUTO clicked)."""
        sender = self.sender()
        if not sender:
            return
        name = sender.property("transition_name")
        # ONLY store the selected transition - DO NOT apply it
        self.selected_transition = name
        self.pending_transition = name
        app_config.set('ui.transition.type', name)
        app_config.save_settings()
        try:
            if hasattr(self, 'lbl_switch_transition') and self.lbl_switch_transition is not None:
                self.lbl_switch_transition.setText(f"Transition: {name}")
        except Exception:
            pass
        # ⚠️ CRITICAL: Do NOT call auto_transition() here
        # Transitions only execute when user explicitly clicks the AUTO button
        print(f"[TRANSITION] Selected: {name} (will apply when AUTO is clicked)")
        # Show visual demo of selected transition in Preview monitor only (Program untouched)
        try:
            sel = (self.selected_transition or 'None').strip()
            if sel.lower() not in ('none', ''):
                self._preview_transition_demo()
        except Exception:
            pass
        self._update_transition_selection_ui()

    def _preview_transition_demo(self):
        """Show a visual demo of the selected transition in the Preview monitor only.
        Program Live is NOT affected. After demo ends, Preview restores to live source.
        """
        try:
            from PyQt6.QtCore import QSize
            from PyQt6.QtGui import QPixmap

            if not hasattr(self, 'preview_video_label') or self.preview_video_label is None:
                return

            pv = getattr(self, 'active_preview_source', None)
            pg = getattr(self, 'active_program_source', None)
            if not pv or not pg:
                return

            preview_size = self.preview_video_label.size()
            if preview_size.width() <= 1 or preview_size.height() <= 1:
                preview_size = QSize(566, 286)

            # A = current Program frame, B = current Preview frame
            a_frame = self._get_base_frame_for_source(pg[0], int(pg[1]), preview_size)
            b_frame = self._get_base_frame_for_source(pv[0], int(pv[1]), preview_size)

            if a_frame is None or a_frame.isNull() or b_frame is None or b_frame.isNull():
                return

            tname = self.selected_transition or 'Fade'
            dur = int(self.transition_duration_ms or 700)

            # Use a dedicated manager so Program's transition state is never touched
            if not hasattr(self, '_preview_demo_manager') or self._preview_demo_manager is None:
                from transitions import TransitionManager
                self._preview_demo_manager = TransitionManager(self)

            def _on_demo_frame(img):
                try:
                    lbl = getattr(self, 'preview_video_label', None)
                    if lbl is None:
                        return
                    # Composite the preview overlay on top of the transition frame
                    # so the filter stays visible during the animation (matches Program behavior)
                    pfx = getattr(self, 'preview_overlay_path', None)
                    if pfx and os.path.exists(str(pfx)):
                        try:
                            from PyQt6.QtGui import QPainter, QColor
                            from PyQt6.QtCore import QRectF
                            preview_size = img.size()
                            # Load/use cached overlay image
                            if not hasattr(self, '_preview_overlay_image') or \
                               getattr(self, '_preview_overlay_cache_path', None) != pfx:
                                self._preview_overlay_image = QImage(str(pfx))
                                self._preview_overlay_cache_path = pfx
                                self._preview_opening_norm = self._detect_overlay_opening(
                                    str(pfx), self._preview_overlay_image)
                                self._preview_scaled_overlay_cache = {}
                                self._preview_geom_cache = {}
                            overlay_img = self._preview_overlay_image
                            opening_norm = self._preview_opening_norm
                            if overlay_img and not overlay_img.isNull():
                                cache_key = (preview_size.width(), preview_size.height())
                                if not hasattr(self, '_preview_geom_cache'):
                                    self._preview_geom_cache = {}
                                geom = self._preview_geom_cache.get(cache_key)
                                if geom is None:
                                    src_w, src_h = overlay_img.width(), overlay_img.height()
                                    dst_w, dst_h = preview_size.width(), preview_size.height()
                                    scale = min(dst_w / src_w, dst_h / src_h)
                                    scaled_w = int(src_w * scale)
                                    scaled_h = int(src_h * scale)
                                    off_x = (dst_w - scaled_w) // 2
                                    off_y = (dst_h - scaled_h) // 2
                                    geom = (scaled_w, scaled_h, off_x, off_y)
                                    self._preview_geom_cache[cache_key] = geom
                                scaled_w, scaled_h, off_x, off_y = geom
                                if not hasattr(self, '_preview_scaled_overlay_cache'):
                                    self._preview_scaled_overlay_cache = {}
                                scaled_overlay = self._preview_scaled_overlay_cache.get(cache_key)
                                if scaled_overlay is None:
                                    scaled_overlay = overlay_img.scaled(
                                        QSize(scaled_w, scaled_h),
                                        Qt.AspectRatioMode.IgnoreAspectRatio,
                                        Qt.TransformationMode.FastTransformation)
                                    self._preview_scaled_overlay_cache[cache_key] = scaled_overlay
                                # Build canvas: transition frame as background, overlay on top
                                canvas = QImage(preview_size, QImage.Format.Format_ARGB32)
                                canvas.fill(QColor(0, 0, 0, 255))
                                painter = QPainter(canvas)
                                try:
                                    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, False)
                                    # Draw transition frame in opening area if detected
                                    if opening_norm:
                                        nx, ny, nw, nh = opening_norm
                                        video_rect = QRectF(
                                            off_x + nx * scaled_w, off_y + ny * scaled_h,
                                            max(1.0, nw * scaled_w), max(1.0, nh * scaled_h))
                                        painter.drawImage(video_rect, img, QRectF(img.rect()))
                                    else:
                                        painter.drawImage(QRectF(img.rect()), img, QRectF(img.rect()))
                                    # Draw overlay on top — filter stays visible
                                    painter.drawImage(off_x, off_y, scaled_overlay)
                                finally:
                                    painter.end()
                                img = canvas
                        except Exception:
                            pass  # Fall through to display unmodified transition frame
                    pix = QPixmap.fromImage(img)
                    lbl.setPixmap(pix)
                    lbl.setText("")
                except Exception:
                    pass

            def _on_demo_done():
                # Restore live preview source after demo finishes
                try:
                    self._force_preview_refresh()
                except Exception:
                    pass

            self._preview_demo_manager.start_transition(
                a_frame,
                b_frame,
                transition_type=tname,
                duration_ms=dur,
                easing='ease_in_out',
                on_frame=_on_demo_frame,
                on_done=_on_demo_done,
            )
        except Exception as e:
            print(f"Preview transition demo error: {e}")

    def _update_transition_selection_ui(self):
        """Update the visual state of all transition buttons based on current selection."""
        try:
            sel = self.selected_transition or 'None'
            if hasattr(self, 'transition_buttons'):
                for btn in self.transition_buttons:
                    is_checked = (btn.property("transition_name") == sel)
                    btn.setChecked(is_checked)
        except Exception as e:
            print(f"Error updating transition UI selection: {e}")

    def get_current_program_media_audio_path(self) -> str | None:
        """Return the file path of the media currently on program, if any."""
        try:
            if getattr(self, 'current_output', None) and self.current_output[0] == 'media':
                idx = self.current_output[1]
                if hasattr(self, 'media_paths'):
                    return self.media_paths.get(idx)
        except Exception:
            pass
        return None

    def get_current_program_media_position_ms(self) -> int | None:
        """Return current playback position (ms) of the media on program, if any."""
        try:
            if getattr(self, 'current_output', None) and self.current_output[0] == 'media':
                idx = self.current_output[1]
                player = self.media_players.get(idx)
                if player:
                    return int(player.position())
        except Exception:
            pass
        return None

    def get_active_media_info(self) -> dict | None:
        """Return information about the currently active (playing) media for streaming."""
        try:
            # Check if current output is media and it's playing
            if getattr(self, 'current_output', None) and self.current_output[0] == 'media':
                idx = self.current_output[1]
                player = self.media_players.get(idx)
                if player and player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
                    media_path = self.media_paths.get(idx) if hasattr(self, 'media_paths') else None
                    if media_path:
                        return {
                            'index': idx,
                            'path': media_path,
                            'position_ms': int(player.position()),
                            'duration_ms': int(player.duration())
                        }
        except Exception:
            pass
        return None

    def adjust_audio_sync_delay(self, delay_ms: int):
        """Dynamically adjust audio sync delay for active streams."""
        try:
            # Update primary stream controller
            if hasattr(self, 'stream_controller') and self.stream_controller.is_running():
                active_media = self.get_active_media_info()
                if active_media:
                    self.stream_controller.update_av_delay_and_resync(
                        delay_ms, 
                        active_media['path'], 
                        active_media['position_ms']
                    )
                    print(f"Updated audio sync delay to {delay_ms}ms for active stream")
                else:
                    self.stream_controller.update_av_delay_and_resync(delay_ms)
                    print(f"Updated audio sync delay to {delay_ms}ms")
            
            # Update independent stream controllers
            if hasattr(self, 'stream_controllers'):
                for stream_id, sc in self.stream_controllers.items():
                    if sc.is_running():
                        active_media = self.get_active_media_info()
                        if active_media:
                            sc.update_av_delay_and_resync(
                                delay_ms, 
                                active_media['path'], 
                                active_media['position_ms']
                            )
                        else:
                            sc.update_av_delay_and_resync(delay_ms)
                        print(f"Updated audio sync delay to {delay_ms}ms for stream {stream_id}")
                        
        except Exception as e:
            print(f"Error adjusting audio sync delay: {e}")
    
    def fix_audio_delay_issue(self):
        """Quick fix for 5-second audio delay issue."""
        print("\n=== AUDIO SYNC DELAY FIX ===")
        print("Applying audio delay correction for 5-second delay issue...")
        
        # Check if streaming is active
        streaming_active = False
        if hasattr(self, 'stream_controller') and self.stream_controller.is_running():
            streaming_active = True
        if hasattr(self, 'stream_controllers'):
            for sc in self.stream_controllers.values():
                if sc.is_running():
                    streaming_active = True
                    break
        
        if not streaming_active:
            print("WARNING: No active streams detected. Start streaming first, then apply this fix.")
            print("The fix will be applied when you start streaming.")
            # Set flag for auto-correction when streaming starts
            self._needs_delay_correction = True
            return
        
        # Apply a negative delay to compensate for the 5-second delay
        # This effectively moves audio earlier relative to video
        corrected_delay = -4800  # Negative 4.8 seconds to compensate for 5s delay
        self.adjust_audio_sync_delay(corrected_delay)
        print(f"✓ Applied {corrected_delay}ms audio offset to correct sync issue")
        print("\nIf audio is still not in sync:")
        print("1. Use Ctrl+Shift+A to re-apply this fix")
        print("2. Manually adjust in Stream Settings > A/V Sync Offset")
        print("3. Try values between -5000ms to -4000ms for fine-tuning")
        print("===============================\n")

    def _auto_apply_audio_delay_correction(self):
        """Automatically apply audio delay correction when media is selected for streaming."""
        try:
            # Check if any streaming is active
            streaming_active = False
            if hasattr(self, 'stream_controller') and self.stream_controller.is_running():
                streaming_active = True
            if hasattr(self, 'stream_controllers'):
                for sc in self.stream_controllers.values():
                    if sc.is_running():
                        streaming_active = True
                        break
            
            if streaming_active:
                print("Auto-applying audio delay correction for streaming...")
                # Pull correction from config; default to -1500 ms to address ~0.5s residual delay
                try:
                    corrected_delay = int(app_config.get('streaming.av_sync_correction_ms', -1500))
                except Exception:
                    corrected_delay = -1500
                self.adjust_audio_sync_delay(corrected_delay)
                print(f"✓ Automatically applied {corrected_delay} ms audio offset for sync correction")
            else:
                print("No active streams - audio correction will be applied when streaming starts")
                
        except Exception as e:
            print(f"Error in auto audio delay correction: {e}")

    def update_media_controls(self, media_number):
        """Update media control buttons (play/pause icon) for the given media slot"""
        try:
            button_map = {1: 'pushButton_19', 2: 'pushButton_20', 3: 'pushButton_21'}
            button_name = button_map.get(media_number)
            if not button_name:
                return
            if hasattr(self, button_name):
                button = getattr(self, button_name)
                # In redesigned UI, some legacy widgets may be deleted; avoid RuntimeError spam
                try:
                    if button is None or getattr(button, 'isVisible', None) is None:
                        return
                except RuntimeError:
                    return
                player = self.media_players.get(media_number)
                if player:
                    playing = player.playbackState() == QMediaPlayer.PlaybackState.PlayingState
                    button.setIcon(self.get_icon("Pause.png" if playing else "Play.png"))
                    button.setToolTip(("Pause" if playing else "Play") + f" Media {media_number}")
                    button.setMinimumSize(22, 22)
                    button.setMaximumSize(22, 22)
        except RuntimeError:
            # Ignore "wrapped C/C++ object has been deleted"
            return
        except Exception as e:
            print(f"Error updating media controls: {e}")

    def toggle_input_audio(self, input_number):
        """Toggle input audio monitor (default device) and update button icon"""
        try:
            # Track mute flags per input
            flag_attr = f"input{input_number}_audio_muted"
            current = getattr(self, flag_attr, True)
            new_state = not current
            setattr(self, flag_attr, new_state)

            # Start/stop monitoring
            if new_state:  # muted
                self._stop_input_audio(input_number)
            else:
                # Respect Global Mute: do not actually start audio while master mute is on
                if getattr(self, 'global_audio_muted', False):
                    print("Global mute is enabled; input will remain silenced until global mute is disabled.")
                    # Keep monitor stopped despite desired unmute
                    self._stop_input_audio(input_number)
                else:
                    self._ensure_input_audio(input_number)

            # Update icon on the dedicated input audio button
            btn_attr = f"input{input_number}AudioButton"
            if hasattr(self, btn_attr):
                btn = getattr(self, btn_attr)
                # If global mute is on, always show Mute icon
                force_muted = new_state or getattr(self, 'global_audio_muted', False)
                btn.setIcon(self.get_icon("Mute.png" if force_muted else "Volume.png"))

            print(f"Input {input_number} audio {'muted' if new_state else 'unmuted'}")
        except Exception as e:
            print(f"Error toggling input audio: {e}")
    def set_ui_icons(self):
        """Set icons for UI elements programmatically"""
        try:
            # Main control buttons
            if hasattr(self, 'settingsRecordButton'):
                self.settingsRecordButton.setIcon(self.get_icon("Settings.png"))
            if hasattr(self, 'recordRedCircle'):
                self.recordRedCircle.setIcon(self.get_icon("Record.png"))
            if hasattr(self, 'playButton'):
                self.playButton.setIcon(self.get_icon("Play.png"))
            if hasattr(self, 'captureButton'):
                self.captureButton.setIcon(self.get_icon("capture.png"))
            
            # Stream buttons
            if hasattr(self, 'stream1SettingsBtn'):
                self.stream1SettingsBtn.setIcon(self.get_icon("Settings.png"))
            if hasattr(self, 'stream1AudioBtn'):
                self.stream1AudioBtn.setIcon(self.get_icon("Stream.png"))
            if hasattr(self, 'stream2SettingsBtn'):
                self.stream2SettingsBtn.setIcon(self.get_icon("Settings.png"))
            if hasattr(self, 'stream2AudioBtn'):
                self.stream2AudioBtn.setIcon(self.get_icon("Stream.png"))
            
            # Additional section buttons initial icons
            # Global mute button reflects master state
            if hasattr(self, 'audioTopButton'):
                self.audioTopButton.setIcon(self.get_icon("Mute.png" if getattr(self, 'global_audio_muted', False) else "Volume.png"))
            # bottomButton2 is Clear Visuals button – set clear icon
            if hasattr(self, 'bottomButton2'):
                try:
                    self.bottomButton2.setIcon(self.get_icon("Clear.png"))
                except Exception:
                    pass
            
            # Input audio buttons (reflect muted state)
            if hasattr(self, 'input1AudioButton'):
                self.input1AudioButton.setIcon(self.get_icon("Mute.png" if getattr(self, 'input1_audio_muted', True) else "Volume.png"))
            if hasattr(self, 'input2AudioButton'):
                self.input2AudioButton.setIcon(self.get_icon("Mute.png" if getattr(self, 'input2_audio_muted', True) else "Volume.png"))
            if hasattr(self, 'input3AudioButton'):
                self.input3AudioButton.setIcon(self.get_icon("Mute.png" if getattr(self, 'input3_audio_muted', True) else "Volume.png"))
            
            # Input settings buttons
            if hasattr(self, 'input1SettingsButton'):
                self.input1SettingsButton.setIcon(self.get_icon("Settings.png"))
            if hasattr(self, 'input2SettingsButton'):
                self.input2SettingsButton.setIcon(self.get_icon("Settings.png"))
            if hasattr(self, 'input3SettingsButton'):
                self.input3SettingsButton.setIcon(self.get_icon("Settings.png"))
            
            # Media audio buttons (reflect muted state)
            if hasattr(self, 'media1AudioButton'):
                self.media1AudioButton.setIcon(self.get_icon("Mute.png" if getattr(self, 'media1_audio_muted', False) else "Volume.png"))
            if hasattr(self, 'media2AudioButton'):
                self.media2AudioButton.setIcon(self.get_icon("Mute.png" if getattr(self, 'media2_audio_muted', False) else "Volume.png"))
            if hasattr(self, 'media3AudioButton'):
                self.media3AudioButton.setIcon(self.get_icon("Mute.png" if getattr(self, 'media3_audio_muted', False) else "Volume.png"))
            
            # Media settings buttons & play buttons default icons
            if hasattr(self, 'media1SettingsButton'):
                self.media1SettingsButton.setIcon(self.get_icon("Settings.png"))
            if hasattr(self, 'media2SettingsButton'):
                self.media2SettingsButton.setIcon(self.get_icon("Settings.png"))
            if hasattr(self, 'media3SettingsButton'):
                self.media3SettingsButton.setIcon(self.get_icon("Settings.png"))
            # Set default play icons for media control buttons
            if hasattr(self, 'pushButton_19'):
                self.pushButton_19.setIcon(self.get_icon("Play.png"))
            if hasattr(self, 'pushButton_20'):
                self.pushButton_20.setIcon(self.get_icon("Play.png"))
            if hasattr(self, 'pushButton_21'):
                self.pushButton_21.setIcon(self.get_icon("Play.png"))
            
            # print("UI icons set successfully")
        except Exception as e:
            print(f"Error setting UI icons: {e}")
    
    def apply_aspect_ratio_constraints(self):
        """Apply 16:9 aspect ratio constraints to all video widgets"""
        try:
            from PyQt6.QtWidgets import QSizePolicy
            from PyQt6.QtCore import QSize
            
            # List of video widget names that should maintain 16:9 aspect ratio
            video_widgets = [
                'outputPreview',
                'inputVideoFrame1', 'inputVideoFrame2', 'inputVideoFrame3',
                'mediaVideoFrame1', 'mediaVideoFrame2', 'mediaVideoFrame3'
            ]
            
            for widget_name in video_widgets:
                if hasattr(self, widget_name):
                    widget = getattr(self, widget_name)
                    if widget:
                        # Replace the widget with AspectRatioFrame if it's not already one
                        if not isinstance(widget, AspectRatioFrame):
                            parent = widget.parent()
                            if parent:
                                # Get the current layout position
                                layout = parent.layout()
                                if layout:
                                    # Find the widget's position in the layout
                                    for i in range(layout.count()):
                                        item = layout.itemAt(i)
                                        if item and item.widget() == widget:
                                            # Remove the old widget
                                            layout.removeWidget(widget)
                                            widget.setParent(None)
                                            
                                            # Create new AspectRatioFrame
                                            new_frame = AspectRatioFrame(parent)
                                            # Ensure it expands properly in layouts
                                            from PyQt6.QtWidgets import QSizePolicy
                                            new_frame.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
                                            new_frame.setObjectName(widget_name)
                                            
                                            # Copy original widget properties
                                            new_frame.setFrameStyle(widget.frameStyle())
                                            original_style = widget.styleSheet()
                                            
                                            # Set minimum size based on widget type
                                            if widget_name == 'outputPreview':
                                                new_frame.setMinimumSize(320, 180)
                                            else:
                                                new_frame.setMinimumSize(160, 90)
                                            
                                            # Ensure the frame is visible with proper styling
                                            if 'media' in widget_name.lower():
                                                media_style = """
                                                    QFrame {
                                                        background-color: #2a2a2a;
                                                        border: 1px solid #555;
                                                        border-radius: 4px;
                                                    }
                                                """
                                                new_frame.setStyleSheet(original_style + media_style)
                                            else:
                                                new_frame.setStyleSheet(original_style)
                                            
                                            # Add to layout at the same position
                                            layout.insertWidget(i, new_frame)
                                            
                                            # Update the reference
                                            setattr(self, widget_name, new_frame)
                                            
                                           # print(f"Replaced {widget_name} with AspectRatioFrame")
                                            break
                        else:
                            print(f"{widget_name} is already an AspectRatioFrame")
            
            # print("16:9 aspect ratio constraints applied to all video widgets")
            
        except Exception as e:
            print(f"Error applying aspect ratio constraints: {e}")
    
    def detect_camera_sources(self):
        """Detect available camera sources with platform-specific handling"""
        import cv2
        import platform
        from PyQt6.QtMultimedia import QMediaDevices
        
        camera_sources = []
        try:
            system = platform.system()
            
            # On macOS, try native AVFoundation cameras first (NV12 hardware capture)
            if system == "Darwin" and hasattr(self, '_macos_native') and self._macos_native:
                try:
                    native_cams = self._macos_native.get_native_cameras()
                    for cam in native_cams:
                        camera_sources.append({
                            'index': cam['index'],
                            'name': cam['name'] + ' (Native)',
                            'resolution': '1920x1080',
                            'fps': 60,
                            'backend': 'avfoundation_native',
                            'native_device': cam  # Store native device info
                        })
                    if native_cams:
                        print(f"Detected {len(native_cams)} native AVFoundation camera(s)")
                except Exception as e:
                    print(f"[Camera] Native camera detection error: {e}")
            
            if system == "Darwin":
                # On macOS, enumerate with Qt; optionally probe with PyAV if available.
                try:
                    qt_devices = list(QMediaDevices.videoInputs())
                except Exception:
                    qt_devices = []
                if qt_devices:
                    # Check if PyAV is importable for probing
                    _can_probe = False
                    try:
                        import av_capture as _avc  # lazy av import happens inside
                        _ = getattr(_avc, 'probe_device', None)
                        if _:
                            _can_probe = True
                    except Exception:
                        _can_probe = False
                    for d in qt_devices:
                        name = ''
                        try:
                            name = d.description()
                            width = height = 0
                            fps_val = 0
                            if _can_probe:
                                try:
                                    info = _avc.probe_device(name, sample_seconds=0.8)
                                except Exception:
                                    info = {'ok': False}
                                if info.get('ok'):
                                    width = int(info.get('width') or 0)
                                    height = int(info.get('height') or 0)
                                    fps_val = int(round(float(info.get('fps') or 0.0)))
                                else:
                                    # Fall back to max format hints if probe fails
                                    best_key = (-1.0, 0, 0)
                                    for fmt in d.videoFormats():
                                        try:
                                            fps_max = float(fmt.maxFrameRate())
                                        except Exception:
                                            fps_max = 0.0
                                        size = fmt.resolution()
                                        w = int(size.width()) if hasattr(size, 'width') else int(getattr(size, 'width', 0))
                                        h = int(size.height()) if hasattr(size, 'height') else int(getattr(size, 'height', 0))
                                        key = (fps_max, w, h)
                                        if (key > best_key) or (abs(fps_max - best_key[0]) < 0.1 and (w, h) == (1920, 1080)):
                                            best_key = key
                                    width = best_key[1]
                                    height = best_key[2]
                                    fps_val = int(best_key[0]) if best_key[0] > 0 else 0
                            else:
                                # No probe available; at least report name
                                pass
                            camera_sources.append({
                                'index': -1,
                                'name': name or 'Camera',
                                'resolution': f"{width}x{height}" if width and height else "Unknown",
                                'fps': fps_val if fps_val > 0 else 30,
                                'backend': 'avf_pyav' if _can_probe else 'qt'
                            })
                        except Exception:
                            # Never drop device; add minimal record
                            if name:
                                camera_sources.append({
                                    'index': -1,
                                    'name': name,
                                    'resolution': "Unknown",
                                    'fps': 30,
                                    'backend': 'qt'
                                })
                    print(f"Detected {len(camera_sources)} camera sources (Qt enumeration with optional PyAV probe)")
                    self._last_camera_sources = camera_sources
                    return camera_sources
                # Fallback to OpenCV probing if Qt enumeration failed
                indices = list(range(0, 10))
                backends_to_try = [cv2.CAP_AVFOUNDATION, 0]
            else:
                indices = list(range(0, 10))
                backends_to_try = [0]
            
            # Try to get device names from Qt (more reliable than OpenCV)
            qt_devices = []
            try:
                qt_devices = list(QMediaDevices.videoInputs())
            except Exception:
                qt_devices = []
            qt_names = [d.description() for d in qt_devices] if qt_devices else []
            if qt_names:
                try:
                    print("Qt Video Inputs:")
                    for n in qt_names:
                        print(f"  - {n}")
                except Exception:
                    pass
            
            for i in indices:
                opened = False
                used_backend = None
                width = height = fps = 0
                for be in backends_to_try:
                    cap = cv2.VideoCapture(i, be) if be != 0 else cv2.VideoCapture(i)
                    if cap.isOpened():
                        opened = True
                        used_backend = be
                        
                        # First, try to detect camera's current/native settings without changing anything
                        print(f"Testing camera {i} capabilities...")
                        
                        # Get camera's current native settings - don't change anything, just read
                        native_width = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
                        native_height = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
                        native_fps = cap.get(cv2.CAP_PROP_FPS)
                        
                        print(f"  Camera's native settings: {native_width}x{native_height} @ {native_fps}fps")
                        
                        # Use the camera's actual configured settings without modification
                        width = native_width
                        height = native_height
                        fps = native_fps
                        
                        # Apply minimal optimizations without changing FPS/resolution
                        try:
                            # Set buffer size to 1 to reduce latency
                            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                            # Use MJPEG codec for better performance if supported
                            cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc('M','J','P','G'))
                        except Exception as e:
                            print(f"    Warning: Could not set camera optimizations: {e}")
                        
                        print(f"Using camera {i} native configuration: {width}x{height} @ {fps}fps")
                        
                        cap.release()
                        break
                    cap.release()
                if opened:
                    # Best-effort: map OpenCV index to a Qt device name by order if available
                    name = None
                    if qt_names and i < len(qt_names):
                        name = qt_names[i]
                    if not name:
                        name = f"Camera {i} ({'macOS' if system == 'Darwin' else system})"
                    camera_info = {
                        'index': i,
                        'name': name,
                        'resolution': f"{int(width)}x{int(height)}" if width and height else "Unknown",
                        'fps': int(fps) if fps and fps > 0 else 30,
                        'backend': int(used_backend) if used_backend is not None else 0,
                    }
                    camera_sources.append(camera_info)
            print(f"Detected {len(camera_sources)} camera sources")
            # Store for later reference
            self._last_camera_sources = camera_sources
        except Exception as e:
            print(f"Error detecting cameras: {e}")
        return camera_sources
    
    def force_external_camera_detection(self, camera_index, is_external=True):
        """Force a camera to be treated as external (HDMI/USB) or built-in
        
        Args:
            camera_index (int): Camera index (0, 1, 2, etc.)
            is_external (bool): True to treat as external camera, False as built-in
        """
        key = f'camera.force_external.{camera_index}'
        if is_external:
            app_config.set(key, True)
            print(f"Camera {camera_index} will be treated as external camera")
        else:
            app_config.remove(key)
            print(f"Camera {camera_index} will use automatic detection")
        app_config.save_settings()
        print("Call refresh_camera_capabilities() to re-detect with new settings")

    def set_camera_priority(self, prioritize_resolution=True):
        """Set whether to prioritize resolution or FPS when detecting cameras
        
        Args:
            prioritize_resolution (bool): If True, prefer higher resolution over FPS.
                                        If False, prefer higher FPS over resolution.
        """
        app_config.set('camera.prioritize_resolution', prioritize_resolution)
        app_config.save_settings()
        priority_type = "resolution" if prioritize_resolution else "FPS"
        print(f"Camera priority set to: {priority_type} first")
        print("Call refresh_camera_capabilities() to re-detect with new priority")

    def refresh_camera_capabilities(self):
        """Force refresh of camera capabilities detection"""
        try:
            print("Refreshing camera capabilities...")
            self._last_camera_sources = self.detect_camera_sources()
            print(f"Refreshed: Found {len(self._last_camera_sources)} cameras")
            for cam in self._last_camera_sources:
                print(f"  - {cam['name']}: {cam['resolution']} @ {cam['fps']}fps")
        except Exception as e:
            print(f"Error refreshing camera capabilities: {e}")

    def set_camera_fps_override(self, input_number, fps):
        """Allow user to override camera FPS for performance tuning"""
        try:
            if fps <= 0:
                # Remove override, use camera's native FPS
                app_config.remove(f'camera.input{input_number}.fps_override')
                print(f"Removed FPS override for Input-{input_number}, using camera native FPS")
            else:
                app_config.set(f'camera.input{input_number}.fps_override', int(fps))
                print(f"Set FPS override for Input-{input_number}: {fps}fps")
            app_config.save_settings()
            
            # If camera is currently active, restart it with new settings
            if hasattr(self, 'camera_captures') and input_number in self.camera_captures:
                print(f"Restarting Input-{input_number} with new FPS settings...")
                # Get current camera info
                current_camera = None
                for camera_info in getattr(self, '_last_camera_sources', []):
                    if camera_info.get('index') == self.input_camera_indices.get(input_number):
                        current_camera = camera_info
                        break
                if current_camera:
                    self.start_camera_capture(current_camera, input_number)
        except Exception as e:
            print(f"Error setting camera FPS override: {e}")

    def show_camera_selection_dialog(self, input_number):
        """Show enhanced camera selection dialog for the specified input"""
        from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QListWidget, 
                                   QPushButton, QLabel, QListWidgetItem, QMessageBox, QProgressBar)
        from PyQt6.QtCore import Qt, QThread, pyqtSignal
        from PyQt6.QtGui import QFont, QIcon
        
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Camera Source - Input {input_number}")
        dialog.setModal(True)
        dialog.resize(500, 400)
        dialog.setStyleSheet("""
            QDialog {
                background-color: #2b2b2b;
                color: #ffffff;
            }
            QLabel {
                color: #ffffff;
                font-size: 12px;
            }
            QListWidget {
                background-color: #3c3c3c;
                border: 1px solid #555555;
                border-radius: 4px;
                color: #ffffff;
                selection-background-color: #0078d4;
            }
            QPushButton {
                background-color: #0078d4;
                border: none;
                border-radius: 4px;
                color: white;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #106ebe;
            }
            QPushButton:pressed {
                background-color: #005a9e;
            }
            QPushButton#cancelButton {
                background-color: #666666;
            }
            QPushButton#cancelButton:hover {
                background-color: #777777;
            }
        """)
        
        layout = QVBoxLayout(dialog)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Title with icon
        title_layout = QHBoxLayout()
        title_label = QLabel(f"Select Camera Source for Input-{input_number}")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_layout.addWidget(title_label)
        title_layout.addStretch()
        layout.addLayout(title_layout)
        
        # Status label
        status_label = QLabel("Scanning for available cameras...")
        status_label.setStyleSheet("color: #cccccc; font-size: 10px;")
        layout.addWidget(status_label)
        
        # Progress bar
        progress_bar = QProgressBar()
        progress_bar.setRange(0, 0)  # Indeterminate progress
        progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #555555;
                border-radius: 4px;
                background-color: #3c3c3c;
                height: 6px;
            }
            QProgressBar::chunk {
                background-color: #0078d4;
                border-radius: 3px;
            }
        """)
        layout.addWidget(progress_bar)
        
        # Camera list
        camera_list = QListWidget()
        camera_list.setMinimumHeight(200)
        layout.addWidget(camera_list)
        
        # Info label
        info_label = QLabel("Select a camera from the list above and click OK to connect.")
        info_label.setStyleSheet("color: #cccccc; font-size: 10px; margin-top: 10px;")
        layout.addWidget(info_label)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        refresh_button = QPushButton("🔄 Refresh")
        refresh_button.setObjectName("refreshButton")
        cancel_button = QPushButton("Cancel")
        cancel_button.setObjectName("cancelButton")
        ok_button = QPushButton("Connect")
        
        button_layout.addWidget(refresh_button)
        button_layout.addWidget(cancel_button)
        button_layout.addWidget(ok_button)
        layout.addLayout(button_layout)
        
        # Load cameras
        def load_cameras():
            progress_bar.hide()
            status_label.setText("Ready")
            camera_sources = self.detect_camera_sources()
            
            camera_list.clear()
            if not camera_sources:
                no_camera_item = QListWidgetItem("❌ No cameras detected")
                no_camera_item.setFlags(Qt.ItemFlag.NoItemFlags)
                camera_list.addItem(no_camera_item)
                ok_button.setEnabled(False)
                info_label.setText("No cameras found. Please check your camera connections and try refreshing.")
            else:
                ok_button.setEnabled(False)  # Don't enable until user selects
                for i, camera in enumerate(camera_sources):
                    item_text = f"📹 {camera['name']} - {camera['resolution']} @ {camera['fps']}fps"
                    item = QListWidgetItem(item_text)
                    item.setData(Qt.ItemDataRole.UserRole, camera)
                    camera_list.addItem(item)
                    # Don't auto-select any camera
                
                info_label.setText(f"Found {len(camera_sources)} camera(s). Select one and click Connect.")
        
        # Enable OK button when user selects a camera
        def on_camera_selection_changed():
            current_item = camera_list.currentItem()
            if current_item and current_item.data(Qt.ItemDataRole.UserRole):
                ok_button.setEnabled(True)
            else:
                ok_button.setEnabled(False)
        
        # Connect signals
        ok_button.clicked.connect(lambda: self.on_camera_selected(dialog, camera_list, input_number))
        cancel_button.clicked.connect(dialog.reject)
        refresh_button.clicked.connect(load_cameras)
        camera_list.itemSelectionChanged.connect(on_camera_selection_changed)
        
        # Initial load
        load_cameras()
        
        dialog.exec()
    
    def on_camera_selected(self, dialog, camera_list, input_number):
        """Handle camera selection and start video capture"""
        current_item = camera_list.currentItem()
        if current_item and current_item.data(Qt.ItemDataRole.UserRole):
            camera_info = current_item.data(Qt.ItemDataRole.UserRole)
            self.start_camera_capture(camera_info, input_number)
            dialog.accept()
        else:
            dialog.reject()
    
    def start_camera_capture(self, camera_info, input_number):
        """Start capturing video from selected camera"""
        import cv2
        import platform
        from PyQt6.QtCore import QTimer
        from PyQt6.QtGui import QImage, QPixmap
        
        try:
            # Stop any existing capture for this input
            self.stop_camera_capture(input_number)

            try:
                if not hasattr(self, '_last_camera_info'):
                    self._last_camera_info = {}
                if isinstance(camera_info, dict):
                    self._last_camera_info[int(input_number)] = dict(camera_info)
                else:
                    self._last_camera_info[int(input_number)] = camera_info
            except Exception:
                pass
            
            # Prevent multiple inputs from sharing the same camera index
            if not hasattr(self, 'input_camera_indices'):
                self.input_camera_indices = {}
            # Stop any other input using the same camera index
            for other_input, idx in getattr(self, 'input_camera_indices', {}).items():
                try:
                    if other_input != input_number and idx == camera_info['index']:
                        self.stop_camera_capture(other_input)
                except Exception:
                    pass
            # Ensure containers
            if not hasattr(self, 'camera_captures'):
                self.camera_captures = {}
            if not hasattr(self, 'camera_timers'):
                self.camera_timers = {}
            if not hasattr(self, 'last_input_image'):
                self.last_input_image = {}
            if not hasattr(self, 'last_input_pixmap'):
                self.last_input_pixmap = {}
            
            # Check if this is a native AVFoundation camera
            native_device = camera_info.get('native_device') if isinstance(camera_info, dict) else None
            backend = camera_info.get('backend', '') if isinstance(camera_info, dict) else ''
            
            if backend == 'avfoundation_native' and native_device and hasattr(self, '_macos_native') and self._macos_native:
                # Use native AVFoundation camera capture
                try:
                    print(f"[CAMERA] Starting native AVFoundation capture for Input-{input_number}")
                    success = self._macos_native.start_native_camera_capture(
                        device_index=native_device['index'],
                        width=1920,
                        height=1080,
                        fps=30,
                        frame_callback=lambda frame, ts, idx=input_number: self._on_native_camera_frame(idx, frame)
                    )
                    if success:
                        print(f"[CAMERA] Native AVFoundation camera started for Input-{input_number}")
                        # Store native camera info for cleanup
                        if not hasattr(self, '_native_camera_inputs'):
                            self._native_camera_inputs = set()
                        self._native_camera_inputs.add(input_number)
                        return True
                    else:
                        print(f"[CAMERA] Native capture failed, falling back to Qt/OpenCV")
                except Exception as e:
                    print(f"[CAMERA] Native capture error: {e}")
            
            # Prefer Qt Camera when we have a QCameraDevice (reliable device selection on Windows/macOS)
            system = platform.system()
            used_qt_camera = False
            used_obs_pipeline = False
            timer = None
            dev = camera_info.get('device')  # QCameraDevice from InputSettingsDialog
            if dev is None:
                target_name = str(camera_info.get('name', '') or '')
                try:
                    from PyQt6.QtMultimedia import QMediaDevices
                    for d in QMediaDevices.videoInputs():
                        if d.description() == target_name or (target_name and target_name.strip('📹 ') in d.description()):
                            dev = d
                            break
                except Exception:
                    dev = None
            if dev is not None:
                try:
                    target_name = str(camera_info.get('name', '') or (dev.description() if hasattr(dev, 'description') else '') or '')
                    if not hasattr(self, 'qt_cameras'):
                        self.qt_cameras = {}
                    if not hasattr(self, 'qt_sessions'):
                        self.qt_sessions = {}
                    if not hasattr(self, 'qt_sinks'):
                        self.qt_sinks = {}
                    if not hasattr(self, '_fps_measure'):
                        self._fps_measure = {}
                    from collections import deque
                    self._fps_measure[input_number] = {
                        'times': deque(maxlen=120),  # ~2s at 60fps
                        'last_report': 0.0,
                        'measured_fps': None,
                    }
                    cam = QCamera(dev)
                    # Choose format matching user's resolution and FPS; PREFER MJPEG over raw
                    user_fps = int(camera_info.get('fps') or 60)
                    user_res = camera_info.get('resolution')
                    if isinstance(user_res, (tuple, list)) and len(user_res) >= 2:
                        target_w, target_h = int(user_res[0]), int(user_res[1])
                    else:
                        target_w, target_h = 1920, 1080
                    
                    # Use new MJPEG-preferring format selection
                    try:
                        best_fmt, qt_selected_fps = _select_best_camera_format(dev, target_w, target_h, user_fps)
                        if best_fmt is not None:
                            cam.setCameraFormat(best_fmt)
                            try:
                                print(f"Selected Qt camera format: {target_w}x{target_h} @ {qt_selected_fps}fps")
                            except Exception:
                                pass
                        else:
                            print(f"Warning: no camera format found for {target_w}x{target_h} @ {user_fps}fps")
                            qt_selected_fps = user_fps
                    except Exception as e:
                        print(f"Warning: could not set Qt camera format: {e}")
                        qt_selected_fps = user_fps

                    try:
                        if not hasattr(self, '_qt_camera_target_fps'):
                            self._qt_camera_target_fps = {}
                        if not hasattr(self, '_qt_camera_target_res'):
                            self._qt_camera_target_res = {}
                        self._qt_camera_target_fps[int(input_number)] = int(qt_selected_fps)
                        self._qt_camera_target_res[int(input_number)] = (int(target_w), int(target_h))
                    except Exception:
                        pass
                    sink = QVideoSink()
                    sess = QMediaCaptureSession()
                    sess.setCamera(cam)
                    sess.setVideoSink(sink)
                    # Connect camera sink to frame converter worker (off-main-thread)
                    # Also track raw delivery rate directly on the GUI thread for diagnostics.
                    sink.videoFrameChanged.connect(lambda vf, idx=input_number: self._on_qt_sink_frame(idx, vf))
                    cam.start()
                    self.qt_cameras[input_number] = cam
                    self.qt_sessions[input_number] = sess
                    self.qt_sinks[input_number] = sink
                    used_qt_camera = True
                    print(f"Started Qt camera for Input-{input_number}: {target_name}")
                except Exception as e:
                    print(f"Qt camera start failed, falling back to OpenCV: {e}")

            if not used_qt_camera:
                # TRY OBS-STYLE PIPELINE FIRST (if available)
                if self.obs_camera_pipeline_enabled:
                    try:
                        # Extract camera parameters
                        index = int(camera_info.get('index', 0))
                        user_res = camera_info.get('resolution')
                        if isinstance(user_res, (tuple, list)) and len(user_res) >= 2:
                            width, height = int(user_res[0]), int(user_res[1])
                        else:
                            width, height = 1920, 1080
                        
                        user_fps = int(camera_info.get('fps', 60))
                        user_fps_override = app_config.get(f'camera.input{input_number}.fps_override', None)
                        if user_fps_override and user_fps_override > 0:
                            user_fps = int(user_fps_override)
                        
                        # Create OBS-style camera manager (CameraWorker + RenderThread + FrameBuffer)
                        camera_mgr = SignaledCameraManager(
                            input_number=input_number,
                            parent=self,
                            device=index,
                            width=width,
                            height=height,
                            fps=user_fps
                        )
                        
                        # Connect manager's frame_ready signal to our frame handler
                        # The render thread emits BGR frames (from OpenCV)
                        camera_mgr.signals.frame_ready.connect(
                            lambda in_num, frame, mgr_ref=camera_mgr: self._on_obs_camera_frame(in_num, frame),
                            type=Qt.ConnectionType.QueuedConnection
                        )
                        
                        # Connect error signal
                        camera_mgr.signals.camera_error.connect(
                            lambda in_num, msg: print(f"[Camera-{in_num}] Error: {msg}"),
                            type=Qt.ConnectionType.QueuedConnection
                        )
                        
                        # Connect FPS update signal
                        camera_mgr.signals.fps_updated.connect(
                            lambda in_num, fps: self._on_obs_camera_fps_updated(in_num, fps),
                            type=Qt.ConnectionType.QueuedConnection
                        )
                        
                        # Start the pipeline threads
                        camera_mgr.start()
                        
                        # Set OS-level thread priorities (prevent preemption)
                        # This eliminates FPS spikes from UI repaints and other system tasks
                        try:
                            from PyQt6.QtCore import QThread
                            camera_mgr.camera_worker.setPriority(QThread.Priority.HighPriority)
                            camera_mgr.render_thread.setPriority(QThread.Priority.TimeCriticalPriority)
                        except Exception as e:
                            print(f"[WARNING] Could not set thread priorities: {e}")
                        
                        # Store manager
                        self.camera_managers[input_number] = camera_mgr
                        used_obs_pipeline = True
                        
                        print(f"Started OBS-style camera pipeline for Input-{input_number}")
                        print(f"  Device: {index}, Resolution: {width}x{height}, FPS: {user_fps}")
                        print(f"  Using dedicated CameraWorker + RenderThread with nanosecond-precision timing")
                        
                    except Exception as e:
                        print(f"[OBS Camera Pipeline] Failed to initialize: {e}")
                        print(f"  Falling back to legacy OpenCV timer-based capture")
                        # Fall through to legacy OpenCV path
                        self.obs_camera_pipeline_enabled = False
                
                # FALLBACK: Legacy OpenCV timer-based capture (if OBS pipeline failed/disabled)
                if not self.obs_camera_pipeline_enabled or input_number not in self.camera_managers:
                    # Create capture using the backend that worked during detection; try fallbacks
                    be_pref = int(camera_info.get('backend', 0)) if isinstance(camera_info, dict) else 0
                    index = int(camera_info.get('index', 0))
                    tried = []
                    def try_open(backend):
                        cap_local = cv2.VideoCapture(index, backend) if backend != 0 else cv2.VideoCapture(index)
                        tried.append(backend)
                        return cap_local if cap_local.isOpened() else None
                    cap = None
                    if be_pref:
                        cap = try_open(be_pref)
                    if cap is None and system == "Darwin":
                        cap = try_open(cv2.CAP_AVFOUNDATION)
                    if cap is None and system == "Windows":
                        cap = try_open(cv2.CAP_DSHOW)  # DirectShow often works better for USB cameras
                    if cap is None:
                        cap = try_open(0)
                    if cap is None:
                        raise RuntimeError(f"Failed to open camera index {index} with backends {tried}")
                    
                    # Configure camera resolution only if explicitly provided; do NOT force FPS
                    if isinstance(camera_info, dict):
                        # Extract requested settings
                        res = camera_info.get('resolution')
                        if res:
                            if isinstance(res, (tuple, list)) and len(res) >= 2:
                                requested_w, requested_h = int(res[0]), int(res[1])
                            elif isinstance(res, str) and 'x' in res:
                                requested_w, requested_h = map(int, res.split('x'))
                            else:
                                requested_w = requested_h = 0
                        else:
                            requested_w = requested_h = 0
                        
                        requested_fps = camera_info.get('fps', 60)
                        user_fps_override = app_config.get(f'camera.input{input_number}.fps_override', None)
                        if user_fps_override and user_fps_override > 0:
                            requested_fps = int(user_fps_override)
                        else:
                            requested_fps = int(requested_fps)
                        
                        # **CRITICAL ORDER on Windows DSHOW**: Codec FIRST, then resolution, then FPS, then buffer
                        # Without this order, cameras silently cap at 30fps even if they support 120fps
                        try:
                            # 1. Set MJPEG codec FIRST (enables 60fps+ on most cameras)
                            cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
                            print(f"[CAMERA] Set codec: MJPG")
                        except Exception as e:
                            print(f"[CAMERA] Warning: Could not set MJPG codec: {e}")
                        
                        try:
                            # 2. Then set resolution
                            if requested_w > 0 and requested_h > 0:
                                cap.set(cv2.CAP_PROP_FRAME_WIDTH, requested_w)
                                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, requested_h)
                                print(f"[CAMERA] Set resolution: {requested_w}x{requested_h}")
                        except Exception as e:
                            print(f"[CAMERA] Warning: Could not set resolution: {e}")
                        
                        try:
                            # 3. Then set FPS
                            cap.set(cv2.CAP_PROP_FPS, requested_fps)
                            print(f"[CAMERA] Set FPS: {requested_fps}")
                        except Exception as e:
                            print(f"[CAMERA] Warning: Could not set FPS: {e}")
                        
                        try:
                            # 4. Critical: buffer size 1 to prevent stale frame queue at high fps
                            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                            print(f"[CAMERA] Set buffer size: 1")
                        except Exception as e:
                            print(f"[CAMERA] Warning: Could not set buffer size: {e}")
                        
                        try:
                            # Verify what the camera actually accepted
                            actual_fps = cap.get(cv2.CAP_PROP_FPS)
                            actual_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                            actual_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                            print(f"[CAMERA] Requested: {requested_w}x{requested_h} @ {requested_fps}fps")
                            print(f"[CAMERA] Actual    : {actual_w}x{actual_h} @ {actual_fps}fps")
                            if actual_fps < requested_fps:
                                print(f"[CAMERA] ⚠ Hardware limit detected: camera delivers {actual_fps}fps, "
                                      f"render thread will duplicate frames to output {requested_fps}fps")
                        except Exception as e:
                            print(f"[CAMERA] Warning: Could not verify camera properties: {e}")
                    
                    self.camera_captures[input_number] = cap
                    self.input_camera_indices[input_number] = int(camera_info.get('index', 0))
                    
                    # Create timer for frame updates (legacy path only)
                    timer = QTimer()
                    timer.timeout.connect(lambda: self.update_camera_frame(input_number))
                    if isinstance(camera_info, dict):
                        detected_fps = camera_info.get('fps', 60)
                        user_fps_override = app_config.get(f'camera.input{input_number}.fps_override', None)
                        if user_fps_override and user_fps_override > 0:
                            camera_fps = min(user_fps_override, detected_fps)
                        else:
                            camera_fps = detected_fps
                    else:
                        camera_fps = 60
                    
                    interval_ms = max(4, int(1000 / camera_fps))
                    timer.start(interval_ms)
                    print(f"Camera timer set to {interval_ms}ms intervals ({camera_fps}fps)")
                    self.camera_timers[input_number] = timer
                    # Update graphics and preview config to match this non-Qt camera rate
                    if hasattr(self, '_graphics_output'):
                        self._graphics_output.set_target_fps(int(camera_fps))
                    app_config.set('ui.preview_fps', int(camera_fps))
                    app_config.save_settings()
            
            # Qt camera path continues here
            if used_qt_camera:
                # Create idle timer for Qt camera (signal-driven, but keep timer for lifecycle)
                timer = QTimer()  # Initialize timer (was scoped bug if not done here)
                timer.timeout.connect(lambda: None)  # No-op, frames arrive via signal
                timer.start(1000)  # 1s no-op
                print("Qt camera uses signal-driven frames; timer is idle.")
                self.camera_timers[input_number] = timer
                # Apply FPS to output pipeline - use format's actual fps to avoid throttling (e.g. 60 not 30)
                camera_fps = int(qt_selected_fps)
                
                if hasattr(self, '_graphics_output') and self._graphics_output is not None:
                    self._graphics_output.set_target_fps(camera_fps)
                app_config.set('ui.preview_fps', camera_fps)
                app_config.save_settings()
                try:
                    if FPS_CONTROLLER_AVAILABLE:
                        from fps_controller import set_global_fps
                        set_global_fps(camera_fps)
                except Exception:
                    pass
                QTimer.singleShot(100, lambda f=camera_fps: self._safe_set_fps_combo(f))
                print(f"Applied {camera_fps}fps to output pipeline (from camera selection)")
            else:
                if isinstance(camera_info, dict):
                    detected_fps = camera_info.get('fps', 60)
                    user_fps_override = app_config.get(f'camera.input{input_number}.fps_override', None)
                    if user_fps_override and user_fps_override > 0:
                        camera_fps = min(user_fps_override, detected_fps)
                    else:
                        camera_fps = detected_fps
                else:
                    camera_fps = 60

                if timer is not None:
                    interval_ms = max(4, int(1000 / camera_fps))
                    timer.start(interval_ms)
                    print(f"Camera timer set to {interval_ms}ms intervals ({camera_fps}fps)")
                    self.camera_timers[input_number] = timer

                # Update graphics and preview config to match this non-Qt camera rate
                if hasattr(self, '_graphics_output'):
                    self._graphics_output.set_target_fps(int(camera_fps))
                app_config.set('ui.preview_fps', int(camera_fps))
                app_config.save_settings()
            
            try:
                if not hasattr(self, '_input_camera_name'):
                    self._input_camera_name = {}
                self._input_camera_name[int(input_number)] = str(camera_info.get('name', '') or '')
            except Exception:
                pass
            try:
                if hasattr(self, '_update_input_footer'):
                    self._update_input_footer(int(input_number))
            except Exception:
                pass

            print(f"Started camera capture for Input-{input_number}: {camera_info['name']}")
            
        except Exception as e:
            print(f"Error starting camera capture: {e}")
    
    def update_camera_frame(self, input_number):
        """Offload camera frame capture to thread pool and update UI via signal."""
        import cv2
        if not hasattr(self, 'camera_captures') or input_number not in self.camera_captures:
            return

        # OBS-style: never allow capture ticks to backlog.
        # If a previous read is still in-flight, drop this tick.
        try:
            if not hasattr(self, '_opencv_read_pending'):
                self._opencv_read_pending = {}
            if self._opencv_read_pending.get(int(input_number), False):
                return
            self._opencv_read_pending[int(input_number)] = True
        except Exception:
            pass

        cap = self.camera_captures[input_number]
        # Use thread pool for capture
        def capture_task():
            try:
                ret, frame = cap.read()
                if not ret or frame is None:
                    return (False, None)
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                return (True, rgb_frame)
            except Exception as e:
                print(f"Camera read failed for input {input_number}: {e}")
                return (False, None)
        def on_done(fut):
            try:
                ret, rgb_frame = fut.result()
            except Exception:
                ret, rgb_frame = False, None

            try:
                if hasattr(self, '_opencv_read_pending'):
                    self._opencv_read_pending[int(input_number)] = False
            except Exception:
                pass

            if ret:
                self.camera_frame_ready.emit(input_number, rgb_frame)
        # Submit to thread pool
        if thread_pool:
            fut = thread_pool.submit_task(capture_task)
            if fut:
                fut.add_done_callback(on_done)
            else:
                try:
                    if hasattr(self, '_opencv_read_pending'):
                        self._opencv_read_pending[int(input_number)] = False
                except Exception:
                    pass
        else:
            # Fallback: run synchronously (should not happen)
            ret, rgb_frame = capture_task()
            try:
                if hasattr(self, '_opencv_read_pending'):
                    self._opencv_read_pending[int(input_number)] = False
            except Exception:
                pass
            self.camera_frame_ready.emit(input_number, rgb_frame)

    def _on_obs_camera_frame(self, input_number, bgr_frame):
        """
        Handle frames from OBS-style camera pipeline.
        Frames come from render thread (BGR format from OpenCV).
        Converts BGR to RGB and processes them like regular capture frames.
        """
        try:
            if bgr_frame is None:
                return
            
            import cv2
            # Convert BGR (from OpenCV) to RGB (for Qt display)
            rgb_frame = cv2.cvtColor(bgr_frame, cv2.COLOR_BGR2RGB)
            
            # Process frame through the standard camera frame handler
            self._on_camera_frame_ready(input_number, rgb_frame)
        except Exception as e:
            print(f"[OBS Camera] Frame processing error for input {input_number}: {e}")
    
    def _on_obs_camera_fps_updated(self, input_number, fps):
        """Handle FPS updates from OBS camera pipeline (useful for adaptive quality)."""
        try:
            # Could adapt quality or update UI based on measured FPS
            if hasattr(self, 'quality_manager'):
                # Optionally: adjust quality based on camera FPS
                pass
        except Exception:
            pass

    def _on_camera_frame_ready(self, input_number, rgb_frame):
        """Update the UI with the captured frame (runs on main thread)."""
        try:
            from PyQt6.QtGui import QImage, QPixmap
            from PyQt6.QtCore import QSize, Qt
            if rgb_frame is None:
                return
            height, width, channel = rgb_frame.shape
            bytes_per_line = 3 * width
            q_image = QImage(rgb_frame.data, width, height, bytes_per_line, QImage.Format.Format_RGB888).copy()
            
            # Cache original raw frame (without effects) for scaling and use by graphics output
            # Effects will be applied by graphics output widget during rendering AND by streaming
            try:
                self.last_input_image[input_number] = q_image
            except Exception:
                pass
            # Convert to QPixmap and scale to widget
            pixmap = QPixmap.fromImage(q_image)
            try:
                video_widget = getattr(self, f'inputVideoFrame{input_number}')
            except Exception:
                video_widget = None
            if video_widget is not None:
                widget_size = video_widget.size()
                if widget_size.width() <= 1 or widget_size.height() <= 1:
                    min_size = video_widget.minimumSize()
                    widget_size = min_size if min_size.isValid() else QSize(320, 180)
                if widget_size.width() > 0 and widget_size.height() > 0:
                    scaled_pixmap = pixmap.scaled(
                        widget_size,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation
                    )
                else:
                    scaled_pixmap = pixmap
                if hasattr(video_widget, 'label'):
                    video_widget.label.setPixmap(scaled_pixmap)
                else:
                    if hasattr(video_widget, '_video_label'):
                        video_widget._video_label.setPixmap(scaled_pixmap)
                    else:
                        try:
                            from PyQt6.QtWidgets import QLabel, QVBoxLayout, QSizePolicy
                            video_widget._video_label = QLabel(video_widget)
                            if not video_widget.layout():
                                layout = QVBoxLayout(video_widget)
                                layout.setContentsMargins(0, 0, 0, 0)
                                video_widget.setLayout(layout)
                            video_widget._video_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
                            video_widget.layout().addWidget(video_widget._video_label)
                            video_widget._video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                            video_widget._video_label.setScaledContents(True)
                        except Exception:
                            pass
                        video_widget._video_label.setPixmap(scaled_pixmap)
                try:
                    self.last_input_pixmap[input_number] = scaled_pixmap
                except Exception:
                    pass
        except Exception:
            pass
        # If currently selected as output, update main output image
        try:
            if not getattr(self, '_transition_running', False) and self.current_output == ('input', input_number):
                self._set_output_image(self.last_input_image.get(input_number))
        except Exception:
            pass
        # Update live preview monitor if active
        try:
            if hasattr(self, 'active_preview_source') and self.active_preview_source == ('input', input_number):
                self._update_preview_monitor(self.last_input_image.get(input_number), 'input', int(input_number))
        except Exception:
            pass

    def _apply_read_result(self, input_number):
        """Apply the result of a background camera read to the UI."""
        try:
            fut = None
            if hasattr(self, '_camera_read_futures'):
                fut = self._camera_read_futures.pop(input_number, None)

            ret = False
            frame = None

            # If fallback stored a tuple (ret, frame)
            if isinstance(fut, tuple) and len(fut) == 2:
                ret, frame = fut
            else:
                # If it's a Future-like object, attempt to get result
                try:
                    if fut is not None and hasattr(fut, 'result'):
                        res = fut.result(timeout=0)
                        if isinstance(res, tuple) and len(res) == 2:
                            ret, frame = res
                except Exception:
                    ret, frame = False, None

            if not ret or frame is None:
                return

            import cv2
            from PyQt6.QtGui import QImage, QPixmap
            from PyQt6.QtCore import QSize, Qt

            # Convert BGR to RGB and create an owned QImage copy
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            height, width, channel = rgb_frame.shape
            bytes_per_line = 3 * width
            q_image = QImage(rgb_frame.data, width, height, bytes_per_line, QImage.Format.Format_RGB888).copy()

            # Cache original image for high-quality output scaling
            try:
                self.last_input_image[input_number] = q_image
            except Exception:
                pass

            # Convert to QPixmap and scale to widget
            pixmap = QPixmap.fromImage(q_image)
            try:
                video_widget = getattr(self, f'inputVideoFrame{input_number}')
            except Exception:
                video_widget = None

            if video_widget is not None:
                widget_size = video_widget.size()
                if widget_size.width() <= 1 or widget_size.height() <= 1:
                    min_size = video_widget.minimumSize()
                    widget_size = min_size if min_size.isValid() else QSize(320, 180)
                if widget_size.width() > 0 and widget_size.height() > 0:
                    scaled_pixmap = pixmap.scaled(
                        widget_size,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation
                    )
                    if hasattr(video_widget, 'label'):
                        video_widget.label.setPixmap(scaled_pixmap)
                    else:
                        if hasattr(video_widget, '_video_label'):
                            video_widget._video_label.setPixmap(scaled_pixmap)
                        else:
                            try:
                                from PyQt6.QtWidgets import QLabel, QVBoxLayout, QSizePolicy
                                video_widget._video_label = QLabel(video_widget)
                                if not video_widget.layout():
                                    layout = QVBoxLayout(video_widget)
                                    layout.setContentsMargins(0, 0, 0, 0)
                                    video_widget.setLayout(layout)
                                video_widget._video_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
                                video_widget.layout().addWidget(video_widget._video_label)
                                video_widget._video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                                video_widget._video_label.setScaledContents(True)
                                video_widget._video_label.setPixmap(scaled_pixmap)
                            except Exception:
                                pass

                    try:
                        self.last_input_pixmap[input_number] = scaled_pixmap
                    except Exception:
                        pass

            # If currently selected as output, update main output image
            try:
                if not getattr(self, '_transition_running', False) and self.current_output == ('input', input_number):
                    self._set_output_image(self.last_input_image.get(input_number))
            except Exception:
                pass

            # Update live preview monitor if active
            try:
                if hasattr(self, 'active_preview_source') and self.active_preview_source == ('input', input_number):
                    self._update_preview_monitor(self.last_input_image.get(input_number), 'input', int(input_number))
            except Exception:
                pass

        except Exception as e:
            print(f"Error applying camera read result for input {input_number}: {e}")
    
    def _on_avf_frame(self, input_number: int, qimg: QImage, measured_fps: float):
        """Handle frames from AVFoundation (PyAV) capture."""
        try:
            if qimg is None or qimg.isNull():
                return
            # Cache originals
            if not hasattr(self, 'last_input_image'):
                self.last_input_image = {}
            if not hasattr(self, 'last_input_pixmap'):
                self.last_input_pixmap = {}
        
            # ✅ CAMERA PROCESSING IS NOW DONE ON BACKGROUND THREAD (av_capture.py)
            # We just use the frame as-is, which is already processed.
            processed_img = qimg
            
            self.last_input_image[input_number] = processed_img.copy()
            pixmap = QPixmap.fromImage(processed_img)
            video_widget = getattr(self, f'inputVideoFrame{input_number}', None)
            if not video_widget:
                return
            widget_size = video_widget.size()
            if widget_size.width() <= 1 or widget_size.height() <= 1:
                ms = video_widget.minimumSize()
                widget_size = ms if ms.isValid() else QSize(320, 180)
            scaled_pixmap = pixmap.scaled(
                widget_size,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            if hasattr(video_widget, 'label'):
                video_widget.label.setPixmap(scaled_pixmap)
            else:
                if not hasattr(video_widget, '_video_label'):
                    from PyQt6.QtWidgets import QLabel, QVBoxLayout, QSizePolicy
                    video_widget._video_label = QLabel(video_widget)
                    if not video_widget.layout():
                        layout = QVBoxLayout(video_widget)
                        layout.setContentsMargins(0, 0, 0, 0)
                        video_widget.setLayout(layout)
                    video_widget._video_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
                    video_widget.layout().addWidget(video_widget._video_label)
                    video_widget._video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    video_widget._video_label.setScaledContents(True)
                video_widget._video_label.setPixmap(scaled_pixmap)

            self.last_input_pixmap[input_number] = scaled_pixmap
            # If on program, send original image to output
            if not getattr(self, '_transition_running', False) and self.current_output == ('input', input_number):
                self._set_output_image(self.last_input_image[input_number])

            # Live preview monitor update (use full-res cached image)
            try:
                if hasattr(self, 'active_preview_source') and self.active_preview_source == ('input', int(input_number)):
                    self._update_preview_monitor(self.last_input_image.get(int(input_number)), 'input', int(input_number))
            except Exception:
                pass

            # Runtime FPS adaptation (same policy as Qt path)
            try:
                measured = float(measured_fps or 0.0)
                if measured > 1.0:
                    new_fps = int(round(min(240, measured)))
                    app_config.set('ui.preview_fps', new_fps)
                    app_config.save_settings()
                    # Log measured FPS
                    # Use FPS stabilizer to prevent excessive updates
                    should_update, stable_fps = fps_manager.update_component_fps(f'input_{input_number}', measured)
                    if should_update:
                        stable_fps = max(24, stable_fps)  # Minimum 24 FPS to prevent lag
                        print(f"Input-{input_number} FPS stabilized at {stable_fps}fps (was {measured:.1f}fps)")
                        if getattr(self, 'current_output', (None, None)) == ('input', input_number):
                            if hasattr(self, '_graphics_output'):
                                self._graphics_output.set_target_fps(stable_fps)
                                print(f"Graphics output FPS updated to {stable_fps}fps")
                        if hasattr(self, 'mirror_controller') and self.mirror_controller and self.mirror_controller.is_running():
                            self.mirror_controller.update({'fps': new_fps})
                        if hasattr(self, 'stream_controllers'):
                            for sc in self.stream_controllers.values():
                                try:
                                    if sc.is_running():
                                        sc.set_fps(new_fps)
                                except Exception:
                                    pass
            except Exception:
                pass
        except Exception as e:
            print(f"AVF camera frame error (Input-{input_number}): {e}")

    def _on_qt_camera_frame(self, input_number, video_frame):
        """
        GUI thread handler for camera frames.
        DIAGNOSTIC: Measure raw frame delivery rate from Qt/camera layer.
        """
        try:
            if not video_frame.isValid():
                return
            
            # MEASUREMENT: Track raw frame delivery (NOT processing time)
            if not hasattr(self, '_raw_frame_count'):
                self._raw_frame_count = {}
                self._raw_fps_clock = {}
            
            if input_number not in self._raw_frame_count:
                self._raw_frame_count[input_number] = 0
                self._raw_fps_clock[input_number] = time.perf_counter()
            
            self._raw_frame_count[input_number] += 1
            now = time.perf_counter()
            elapsed = now - self._raw_fps_clock[input_number]
            
            if elapsed >= 1.0:
                raw_fps = self._raw_frame_count[input_number] / elapsed
                print(f"[RAW-CAMERA-SIGNAL] Input-{input_number} Qt signal delivery rate: {raw_fps:.1f}fps")
                self._raw_frame_count[input_number] = 0
                self._raw_fps_clock[input_number] = now
            
            # Hand off to worker for processing
            worker = self._get_or_create_frame_worker(input_number)
            worker.process_video_frame(video_frame, input_number)
            
        except Exception as e:
            pass  # Never let camera errors crash the GUI thread

    def _on_qt_sink_frame(self, input_number: int, video_frame: 'QVideoFrame'):
        try:
            if video_frame is None or not video_frame.isValid():
                return

            if not hasattr(self, '_qt_sink_fps'):
                self._qt_sink_fps = {}
            st = self._qt_sink_fps.get(int(input_number))
            if st is None:
                st = {'count': 0, 'clock': time.perf_counter()}
                self._qt_sink_fps[int(input_number)] = st
            st['count'] += 1
            now = time.perf_counter()
            elapsed = now - st['clock']
            if elapsed >= 1.0:
                fps = st['count'] / elapsed
                st['count'] = 0
                st['clock'] = now
                print(f"[QT-SINK] Input-{input_number} delivery rate: {fps:.1f}fps")

            # OBS-style: never let the capture callback flood the event queue.
            # Keep only the latest frame per input and schedule at most one dispatch at a time.
            if not hasattr(self, '_qt_latest_vf'):
                self._qt_latest_vf = {}
            if not hasattr(self, '_qt_vf_dispatch_pending'):
                self._qt_vf_dispatch_pending = set()

            try:
                self._qt_latest_vf[int(input_number)] = QVideoFrame(video_frame)
            except Exception:
                self._qt_latest_vf[int(input_number)] = video_frame

            if int(input_number) not in self._qt_vf_dispatch_pending:
                self._qt_vf_dispatch_pending.add(int(input_number))
                QTimer.singleShot(0, lambda idx=int(input_number): self._dispatch_latest_qt_video_frame(idx))
        except Exception:
            try:
                QMetaObject.invokeMethod(
                    self._converter_worker,
                    'convert_frame',
                    Qt.ConnectionType.QueuedConnection,
                    Q_ARG(int, int(input_number)),
                    Q_ARG(QVideoFrame, video_frame)
                )
            except Exception:
                pass

    def _dispatch_latest_qt_video_frame(self, input_number: int):
        try:
            if hasattr(self, '_qt_vf_dispatch_pending'):
                self._qt_vf_dispatch_pending.discard(int(input_number))

            if not hasattr(self, '_qt_latest_vf'):
                return

            vf = self._qt_latest_vf.pop(int(input_number), None)
            if vf is None or not vf.isValid():
                return

            QMetaObject.invokeMethod(
                self._converter_worker,
                'convert_frame',
                Qt.ConnectionType.QueuedConnection,
                Q_ARG(int, int(input_number)),
                Q_ARG(QVideoFrame, vf)
            )

            # If another frame arrived while we were dispatching, schedule again.
            if int(input_number) in getattr(self, '_qt_latest_vf', {}):
                if int(input_number) not in getattr(self, '_qt_vf_dispatch_pending', set()):
                    self._qt_vf_dispatch_pending.add(int(input_number))
                    QTimer.singleShot(0, lambda idx=int(input_number): self._dispatch_latest_qt_video_frame(idx))
        except Exception:
            pass
    
    def _get_or_create_frame_worker(self, input_number):
        """Get or create a frame processing worker for the given input."""
        if input_number not in self._frame_workers:
            self._frame_workers[input_number] = FrameProcessingWorker(
                input_number,
                on_frame_ready_callback=self._on_camera_frame_processed
            )
        return self._frame_workers[input_number]
    
    def _on_camera_frame_processed(self, input_number, frame_numpy):
        """
        Called from FrameProcessingWorker thread with processed numpy frame.
        This does what _process_qt_camera_frame_deferred used to do — 
        frame cache, display update, etc.
        """
        try:
            # Schedule the heavy UI work back on GUI thread via deferred processing
            if not hasattr(self, '_qt_pending_frames'):
                self._qt_pending_frames = {}
            self._qt_pending_frames[input_number] = frame_numpy
            
            if not hasattr(self, '_qt_frame_timer_pending'):
                self._qt_frame_timer_pending = set()
            if input_number not in self._qt_frame_timer_pending:
                self._qt_frame_timer_pending.add(input_number)
                QTimer.singleShot(0, lambda idx=input_number: self._process_frame_on_gui_thread(idx))
        except Exception:
            pass
    
    def _process_frame_on_gui_thread(self, input_number):
        """
        Process frame on GUI thread — this is what _process_qt_camera_frame_deferred did.
        Now called from _on_camera_frame_processed after worker finishes conversion.
        """
        try:
            self._qt_frame_timer_pending.discard(input_number)
            frame = self._qt_pending_frames.get(input_number)
            if frame is None:
                return
            
            # Convert numpy frame to QImage for display
            import numpy as np
            if isinstance(frame, np.ndarray):
                from PyQt6.QtGui import QImage
                h, w = frame.shape[:2]
                if len(frame.shape) == 3 and frame.shape[2] == 3:
                    # RGB numpy → QImage
                    bytes_per_line = 3 * w
                    qimg = QImage(frame.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
                    qimg = qimg.copy()  # Make a copy so frame_numpy can be freed
                else:
                    return
            else:
                qimg = frame
            
            # PRIORITY 1: Update graphics output FIRST (before any other UI work)
            try:
                if hasattr(self, '_graphics_output') and self._graphics_output:
                    self._graphics_output.set_input_frame(input_number, qimg)
            except Exception:
                pass
            
            # OPTIMIZATION: Skip heavy processing if this input isn't currently displayed
            active = getattr(self, 'current_output', None)
            prev_src = getattr(self, 'active_preview_source', None)
            is_active = (active and active[0] == 'input' and active[1] == input_number) or \
                        (prev_src and prev_src[0] == 'input' and prev_src[1] == input_number)
            
            # Debug: Log frame info (only for active inputs to reduce spam)
            if is_active:
                if not hasattr(self, '_frame_debug_counts'): 
                    self._frame_debug_counts = {}
                if input_number not in self._frame_debug_counts: 
                    self._frame_debug_counts[input_number] = 0
                self._frame_debug_counts[input_number] += 1
                
                if self._frame_debug_counts[input_number] == 1 or self._frame_debug_counts[input_number] % 60 == 0:
                    print(f"Input-{input_number} Frame #{self._frame_debug_counts[input_number]}: {qimg.width()}x{qimg.height()}")
            
            # Evict stale scaled cache entries (prevent memory accumulation)
            if hasattr(self, 'last_input_image_scaled'):
                primary_key = None
                for k in self.last_input_image_scaled:
                    if k[0] == input_number:
                        primary_key = k
                        break
                keys_to_delete = [k for k in self.last_input_image_scaled 
                                  if k[0] == input_number and (primary_key is None or k != primary_key)]
                for k in keys_to_delete:
                    del self.last_input_image_scaled[k]
            
            # Update UI widgets only if input is active
            if is_active:
                # Update Input Card Thumbnail
                video_widget = getattr(self, f"inputVideoFrame{input_number}", None)
                if video_widget:
                    try:
                        if not hasattr(video_widget, '_video_label'):
                            from PyQt6.QtWidgets import QLabel, QVBoxLayout
                            video_widget._video_label = QLabel(video_widget)
                            video_widget._video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                            video_widget._video_label.setStyleSheet("background-color: black;")
                            if not video_widget.layout():
                                layout = QVBoxLayout(video_widget)
                                layout.setContentsMargins(0,0,0,0)
                                video_widget.setLayout(layout)
                            video_widget.layout().addWidget(video_widget._video_label)
                        
                        thumb_size = video_widget.size()
                        if thumb_size.width() < 10: 
                            thumb_size = QSize(320, 180)
                        
                        scaled_cache = getattr(self, 'last_input_image_scaled', {})
                        cached_720p = None
                        for k in scaled_cache:
                            if k[0] == input_number:
                                cached_720p = scaled_cache[k]
                                break
                        
                        if cached_720p is not None and not cached_720p.isNull():
                            source_for_thumb = cached_720p
                        else:
                            source_for_thumb = qimg
                        
                        thumb_img = source_for_thumb.scaled(
                            thumb_size,
                            Qt.AspectRatioMode.KeepAspectRatio,
                            Qt.TransformationMode.FastTransformation
                        )
                        thumb_pix = QPixmap.fromImage(thumb_img)
                        del thumb_img
                        video_widget._video_label.setPixmap(thumb_pix)
                    except Exception:
                        pass
        except Exception:
            pass

    def _process_qt_camera_frame_deferred(self, input_number):
        """Process the latest pending frame (coalesced) - prevents buffering by showing only newest.
        
        NOTE: Scaling is already done in FrameConverterWorker on background thread.
        This method just updates UI and evicts stale cache entries.
        """
        import time
        try:
            self._qt_frame_timer_pending.discard(input_number)
            img = self._qt_pending_frames.get(input_number)
            if img is None or img.isNull():
                return
            
            # PRIORITY 1: Update graphics output FIRST (before any other UI work)
            # Every millisecond of delay here adds to the latency chain
            try:
                if hasattr(self, '_graphics_output') and self._graphics_output:
                    self._graphics_output.set_input_frame(input_number, img)
            except Exception:
                pass
            
            # OPTIMIZATION: Skip heavy processing if this input isn't currently displayed
            active = getattr(self, 'current_output', None)
            prev_src = getattr(self, 'active_preview_source', None)
            is_active = (active and active[0] == 'input' and active[1] == input_number) or \
                        (prev_src and prev_src[0] == 'input' and prev_src[1] == input_number)
            
            # Debug: Log frame info (only for active inputs to reduce spam)
            if is_active:
                if not hasattr(self, '_frame_debug_counts'): 
                    self._frame_debug_counts = {}
                if input_number not in self._frame_debug_counts: 
                    self._frame_debug_counts[input_number] = 0
                self._frame_debug_counts[input_number] += 1
                
                if self._frame_debug_counts[input_number] == 1 or self._frame_debug_counts[input_number] % 60 == 0:
                    print(f"Input-{input_number} Frame #{self._frame_debug_counts[input_number]}: {img.width()}x{img.height()}")
            
            # FIXED: Cache updates on EVERY FRAME (no gating to every 60)
            if is_active:
                # Store actual resolution for tracking resolution changes
                if not hasattr(self, '_prev_input_resolution'):
                    self._prev_input_resolution = {}
                # Log diagnosis only once per second to reduce spam
                if not hasattr(self, '_frame_cache_log_throttle'):
                    self._frame_cache_log_throttle = {}
                import time as _cache_time
                now_cache = _cache_time.monotonic()
                last_log = self._frame_cache_log_throttle.get(input_number, 0.0)
                if now_cache - last_log >= 1.0:
                    print(f"[FRAME_CACHE] Input {input_number}: cached {img.width()}x{img.height()} for streaming (every frame updated)")
                    self._frame_cache_log_throttle[input_number] = now_cache
            
            # Evict stale scaled cache entries (prevent memory accumulation)
            # Keep only the primary scaled entry for this input (most recent)
            if hasattr(self, 'last_input_image_scaled'):
                primary_key = None
                # Find the most recently updated key for this input
                for k in self.last_input_image_scaled:
                    if k[0] == input_number:
                        primary_key = k
                        break
                # Delete all other keys for this input
                keys_to_delete = [k for k in self.last_input_image_scaled 
                                  if k[0] == input_number and (primary_key is None or k != primary_key)]
                for k in keys_to_delete:
                    del self.last_input_image_scaled[k]
            
            # ✅ SLOW PATH: Update UI widgets only if input is active (skip otherwise to save CPU)
            if not is_active:
                # Just evict cache, skip widget/display updates for inactive inputs
                pass
            else:
                # 1. Update Input Card Thumbnail (if input is visible in sidebar)
                video_widget = getattr(self, f"inputVideoFrame{input_number}", None)
                if video_widget:
                    try:
                        if not hasattr(video_widget, '_video_label'):
                            from PyQt6.QtWidgets import QLabel, QVBoxLayout
                            video_widget._video_label = QLabel(video_widget)
                            video_widget._video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                            video_widget._video_label.setStyleSheet("background-color: black;")
                            if not video_widget.layout():
                                layout = QVBoxLayout(video_widget)
                                layout.setContentsMargins(0,0,0,0)
                                video_widget.setLayout(layout)
                            video_widget.layout().addWidget(video_widget._video_label)
                        
                        # Use pre-scaled cache for thumbnail (avoid scaling on main thread)
                        thumb_size = video_widget.size()
                        if thumb_size.width() < 10: 
                            thumb_size = QSize(320, 180)
                        
                        # Find the cached scaled version for this input (any scale size)
                        scaled_cache = getattr(self, 'last_input_image_scaled', {})
                        cached_720p = None
                        for k in scaled_cache:
                            if k[0] == input_number:
                                cached_720p = scaled_cache[k]
                                break
                        
                        if cached_720p is not None and not cached_720p.isNull():
                            source_for_thumb = cached_720p
                        else:
                            source_for_thumb = img
                        
                        thumb_img = source_for_thumb.scaled(
                            thumb_size,
                            Qt.AspectRatioMode.KeepAspectRatio,
                            Qt.TransformationMode.FastTransformation
                        )
                        thumb_pix = QPixmap.fromImage(thumb_img)
                        del thumb_img  # Explicit cleanup
                        video_widget._video_label.setPixmap(thumb_pix)
                    except Exception:
                        pass
                
                # 2. Update Program Monitor (if this input is on air)
                prog_src = getattr(self, 'active_program_source', None)
                if prog_src == ('input', input_number) and not getattr(self, '_transition_running', False):
                    try:
                        self._set_output_image(img)
                    except Exception:
                        pass
                
                # 3. Update Preview Monitor (if selected in preview)
                if prev_src and prev_src == ('input', input_number):
                    try:
                        self._update_preview_monitor(img, 'input', input_number)
                    except Exception:
                        pass
            
            # Explicit cleanup to prevent Qt object accumulation between GC cycles
            if input_number in self._qt_pending_frames:
                del self._qt_pending_frames[input_number]
            thumb_pix = None  # Release pixmap ref
                        
        except Exception as e:
            if not hasattr(self, '_last_input_error_time'): 
                self._last_input_error_time = 0
            if time.time() - self._last_input_error_time > 1.0:
                print(f"Input frame error (Input-{input_number}): {e}")
                self._last_input_error_time = time.time()

    def _run_deferred_frame_task(self, input_number):
        """
        Helper to run deferred frame processing and clear the pending flag.
        Called via QTimer.singleShot(1) to prevent event queue flooding.
        
        This ensures at most ONE timer event per input is pending at any time.
        New frames arriving during processing just update the stored frame;
        they don't schedule additional timer events.
        """
        # Clear the pending flag FIRST so new frames can schedule again
        if hasattr(self, '_qt_frame_deferred_pending'):
            self._qt_frame_deferred_pending[input_number] = False
        # Now process the latest frame for this input
        self._process_qt_camera_frame_deferred(input_number)

    @pyqtSlot(int, QImage, QImage)
    def _on_frame_converted_from_worker(self, input_number, img, scaled_720p):
        """
        Receive converted QImage from FrameConverterWorker (executes on main thread).
        Receives both full-res and pre-scaled versions.
        Both scaling and image conversion already happened on background thread.
        
        OBS-STYLE: Writes to ring buffer for decoupled render thread access.
        """
        try:
            if img is None or img.isNull():
                return
            
            # OBS-STYLE: Initialize ring buffer for this input if not exists
            if not hasattr(self, '_input_frame_buffers'):
                self._input_frame_buffers = {}
            if input_number not in self._input_frame_buffers:
                self._input_frame_buffers[input_number] = QImageRingBuffer(maxlen=3)
            
            # OBS-STYLE: Write full-res frame to ring buffer
            # This decouples capture thread from render thread
            self._input_frame_buffers[input_number].put(img)
            
            # Store scaled version for UI thumbnails (fast access)
            if not hasattr(self, 'last_input_image_scaled'):
                self.last_input_image_scaled = {}
            cache_key = (input_number, scaled_720p.width(), scaled_720p.height())
            self.last_input_image_scaled[cache_key] = scaled_720p
            
            # Also store in legacy cache for compatibility
            if not hasattr(self, 'last_input_image'):
                self.last_input_image = {}
            self.last_input_image[input_number] = img
            
            # === DIAGNOSTIC: Track actual camera input FPS ===
            if not hasattr(self, '_input_fps_counters'):
                self._input_fps_counters = {}
            if input_number not in self._input_fps_counters:
                import time as _t
                self._input_fps_counters[input_number] = {
                    'count': 0,
                    'start': _t.monotonic(),
                    'last_report': _t.monotonic(),
                    'last_fps': 0.0
                }
            
            import time as _fps_t
            _fps_now = _fps_t.monotonic()
            _fps_data = self._input_fps_counters[input_number]
            _fps_data['count'] += 1
            
            # Report every 1 second
            _fps_elapsed = _fps_now - _fps_data['last_report']
            if _fps_elapsed >= 1.0:
                _actual_fps = _fps_data['count'] / _fps_elapsed
                _fps_data['last_fps'] = _actual_fps
                _fps_data['count'] = 0
                _fps_data['last_report'] = _fps_now
                print(f"Input-{input_number} actual FPS: {_actual_fps:.1f}")
            
            # Schedule deferred UI update (coalesced)
            if not hasattr(self, '_qt_pending_frames'):
                self._qt_pending_frames = {}
            self._qt_pending_frames[input_number] = img
            
            # Only schedule for active input to prevent flooding
            active = getattr(self, 'current_output', None)
            if active and active[0] == 'input' and active[1] != input_number:
                return
            
            # Prevent event queue flooding
            if not hasattr(self, '_qt_frame_deferred_pending'):
                self._qt_frame_deferred_pending = {}
            
            was_pending = self._qt_frame_deferred_pending.get(input_number, False)
            if not was_pending:
                self._qt_frame_deferred_pending[input_number] = True
                QTimer.singleShot(0, lambda idx=input_number: self._run_deferred_frame_task(idx))
                
        except Exception as e:
            import time
            if not hasattr(self, '_last_converter_error_time'):
                self._last_converter_error_time = 0
            now = time.time()
            if now - self._last_converter_error_time > 1.0:
                print(f"Frame converter callback error (Input-{input_number}): {e}")
                self._last_converter_error_time = now

    def _on_native_camera_frame(self, input_number, frame):
        """Handle frame from native AVFoundation camera."""
        try:
            # Convert numpy RGB to QImage
            height, width, channels = frame.shape
            bytes_per_line = channels * width
            q_image = QImage(frame.data, width, height, bytes_per_line, QImage.Format.Format_RGB888)
            
            # Store frame
            self.last_input_image[input_number] = q_image
            self.camera_frame_ready.emit(input_number, q_image)
            
            # Update preview if this is the active input
            if hasattr(self, 'current_output') and self.current_output == ('input', input_number):
                self._set_output_image(q_image)
        except Exception as e:
            print(f"[CAMERA] Native frame handler error: {e}")
            
    def stop_camera_capture(self, input_number):
        """Stop camera capture for specified input"""
        try:
            # Stop native AVFoundation camera if running
            if hasattr(self, '_native_camera_inputs') and input_number in self._native_camera_inputs:
                try:
                    if hasattr(self, '_macos_native') and self._macos_native:
                        self._macos_native.stop_native_camera_capture()
                        print(f"[CAMERA] Stopped native AVFoundation capture for Input-{input_number}")
                except Exception as e:
                    print(f"[CAMERA] Error stopping native capture: {e}")
                self._native_camera_inputs.discard(input_number)
            
            # Stop OBS-style camera pipeline if running
            if input_number in self.camera_managers:
                try:
                    mgr = self.camera_managers.pop(input_number)
                    mgr.stop()
                    print(f"Stopped OBS-style camera pipeline for Input-{input_number}")
                except Exception as e:
                    print(f"Error stopping OBS camera manager: {e}")
            
            # Stop legacy QTimer-based camera
            if hasattr(self, 'camera_timers') and input_number in self.camera_timers:
                self.camera_timers[input_number].stop()
                del self.camera_timers[input_number]
            
            if hasattr(self, 'camera_captures') and input_number in self.camera_captures:
                self.camera_captures[input_number].release()
                del self.camera_captures[input_number]
            # Stop Qt camera pipeline if present
            if hasattr(self, 'qt_cameras') and input_number in self.qt_cameras:
                try:
                    cam = self.qt_cameras.pop(input_number)
                    cam.stop()
                except Exception:
                    pass
            if hasattr(self, 'qt_sessions') and input_number in self.qt_sessions:
                try:
                    self.qt_sessions.pop(input_number)
                except Exception:
                    pass
            if hasattr(self, 'qt_sinks') and input_number in self.qt_sinks:
                try:
                    sink = self.qt_sinks.pop(input_number)
                    sink.videoFrameChanged.disconnect()
                except Exception:
                    pass
            # Clear pending frames to avoid processing stale data
            if hasattr(self, '_qt_pending_frames') and input_number in self._qt_pending_frames:
                self._qt_pending_frames.pop(input_number, None)
            if hasattr(self, '_qt_frame_timer_pending'):
                self._qt_frame_timer_pending.discard(input_number)
            
            print(f"Stopped camera capture for Input-{input_number}")
            try:
                if hasattr(self, '_input_camera_name') and input_number in self._input_camera_name:
                    self._input_camera_name.pop(input_number, None)
            except Exception:
                pass
            try:
                if hasattr(self, '_update_input_footer'):
                    self._update_input_footer(int(input_number))
            except Exception:
                pass
        except Exception as e:
            print(f"Error stopping camera capture for Input-{input_number}: {e}")

    def _update_input_footer(self, input_number: int):
        try:
            if not hasattr(self, '_input_footer_widgets'):
                return
            w = self._input_footer_widgets.get(int(input_number))
            if not isinstance(w, dict):
                return
            dot = w.get('dot')
            lbl = w.get('label')
            if dot is None or lbl is None:
                return

            name = None
            try:
                if hasattr(self, '_input_camera_name'):
                    name = self._input_camera_name.get(int(input_number))
            except Exception:
                name = None

            active = False
            try:
                if hasattr(self, 'qt_cameras') and int(input_number) in getattr(self, 'qt_cameras', {}):
                    active = True
                elif hasattr(self, 'camera_captures') and int(input_number) in getattr(self, 'camera_captures', {}):
                    active = True
            except Exception:
                active = False

            if name:
                try:
                    lbl.setText(str(name))
                except Exception:
                    pass
            else:
                try:
                    lbl.setText("No camera")
                except Exception:
                    pass

            try:
                if active and name:
                    dot.setStyleSheet("background:#35C759;border-radius:4px;")
                else:
                    dot.setStyleSheet("background:#3a3a3a;border-radius:4px;")
            except Exception:
                pass
        except RuntimeError:
            pass
        except Exception:
            pass
    
    def show_media_selection_dialog(self, media_number):
        """Show enhanced media file selection dialog for the specified media slot"""
        from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton, 
                                   QLabel, QFileDialog, QListWidget, QListWidgetItem,
                                   QSplitter, QTextEdit, QProgressBar)
        from PyQt6.QtCore import Qt, QFileInfo, QThread, pyqtSignal
        from PyQt6.QtGui import QFont, QPixmap
        import os
        
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Media Selection - Media {media_number}")
        dialog.setModal(True)
        dialog.resize(700, 500)
        dialog.setStyleSheet("""
            QDialog {
                background-color: #2b2b2b;
                color: #ffffff;
            }
            QLabel {
                color: #ffffff;
                font-size: 12px;
            }
            QListWidget {
                background-color: #3c3c3c;
                border: 1px solid #555555;
                border-radius: 4px;
                color: #ffffff;
                selection-background-color: #0078d4;
            }
            QTextEdit {
                background-color: #3c3c3c;
                border: 1px solid #555555;
                border-radius: 4px;
                color: #ffffff;
                font-family: 'Menlo', 'Monaco', 'Courier New', monospace;
                font-size: 10px;
            }
            QPushButton {
                background-color: #0078d4;
                border: none;
                border-radius: 4px;
                color: white;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #106ebe;
            }
            QPushButton:pressed {
                background-color: #005a9e;
            }
            QPushButton#cancelButton {
                background-color: #666666;
            }
            QPushButton#cancelButton:hover {
                background-color: #777777;
            }
            QPushButton#browseButton {
                background-color: #28a745;
            }
            QPushButton#browseButton:hover {
                background-color: #218838;
            }
        """)
        
        layout = QVBoxLayout(dialog)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Title
        title_label = QLabel(f"Select Media File for Media-{media_number}")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title_label.setFont(title_font)
        layout.addWidget(title_label)
        
        # Simple file selection approach
        info_label = QLabel("Click 'Browse Files' to select a media file (video or audio)")
        info_label.setStyleSheet("color: #cccccc; margin: 10px 0;")
        layout.addWidget(info_label)
        
        # File info display
        file_info = QTextEdit()
        file_info.setMaximumHeight(100)
        file_info.setReadOnly(True)
        file_info.setText("No file selected")
        layout.addWidget(file_info)
        
        # Status label
        status_label = QLabel("Ready to select media file")
        status_label.setStyleSheet("color: #cccccc; font-size: 10px;")
        layout.addWidget(status_label)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        browse_button = QPushButton("📁 Browse Files")
        browse_button.setObjectName("browseButton")
        cancel_button = QPushButton("Cancel")
        cancel_button.setObjectName("cancelButton")
        load_button = QPushButton("Load Media")
        load_button.setEnabled(False)
        
        button_layout.addWidget(browse_button)
        button_layout.addStretch()
        button_layout.addWidget(cancel_button)
        button_layout.addWidget(load_button)
        layout.addLayout(button_layout)
        
        # Variables to store selected file
        selected_file_path = None
        
        def browse_files():
            nonlocal selected_file_path
            file_path, _ = QFileDialog.getOpenFileName(
                dialog,
                f"Select Media File for Media-{media_number}",
                "",
                "Video Files (*.mp4 *.avi *.mov *.mkv *.wmv *.flv *.webm *.m4v *.3gp);;Audio Files (*.mp3 *.wav *.aac *.flac *.ogg *.m4a);;All Files (*)"
            )
            
            if file_path:
                selected_file_path = file_path
                update_file_info(file_path)
                status_label.setText(f"Selected: {os.path.basename(file_path)}")
                load_button.setEnabled(True)
        
        def update_file_info(file_path):
            if not file_path or not os.path.exists(file_path):
                return
                
            file_info_obj = QFileInfo(file_path)
            file_size = file_info_obj.size()
            file_name = file_info_obj.fileName()
            file_dir = file_info_obj.absolutePath()
            
            # Format file size
            if file_size < 1024:
                size_str = f"{file_size} B"
            elif file_size < 1024 * 1024:
                size_str = f"{file_size / 1024:.1f} KB"
            elif file_size < 1024 * 1024 * 1024:
                size_str = f"{file_size / (1024 * 1024):.1f} MB"
            else:
                size_str = f"{file_size / (1024 * 1024 * 1024):.1f} GB"
            
            info_text = f"""File Name: {file_name}
Location: {file_dir}
Size: {size_str}
Type: {file_info_obj.suffix().upper() if file_info_obj.suffix() else 'Unknown'}

Ready to load this media file."""
            
            file_info.setText(info_text)
        
        def load_selected_media():
            if selected_file_path:
                # Use Qt Multimedia pipeline
                self.load_media(media_number, selected_file_path)
                dialog.accept()
        
        # Connect signals
        browse_button.clicked.connect(browse_files)
        cancel_button.clicked.connect(dialog.reject)
        load_button.clicked.connect(load_selected_media)
        
        dialog.exec()
    
    
    def load_effects_into_tabs(self):
        """Set up new Premiere Pro-style effects panel."""
        try:
            # Import the final panel class
            from premiere_effects_panel_final import FinalEffectsPanel
            
            # Get effects folder path (support dev, PyInstaller onedir, and macOS .app Resources)
            effects_path = _get_data_path("effects")
            
            if not os.path.exists(effects_path):
                print(f"Effects folder not found: {effects_path}")
                return
            
            # Get the effects tab widget container
            if not hasattr(self, 'tabWidget_effects'):
                print("Effects tab widget not found")
                return
            
            # Replace the tab widget with our new Premiere Pro-style panel
            tab_widget = self.tabWidget_effects
            # Find left panel layout to ensure placement under output
            left_layout = None
            cw = self.centralWidget()
            if cw and cw.layout():
                tl = cw.layout()
                for i in range(tl.count()):
                    it = tl.itemAt(i)
                    lay = it.layout() if it else None
                    if lay and lay.objectName() == 'verticalLayout_leftPanel':
                        left_layout = lay
                        break
                    w = it.widget() if it else None
                    if w and hasattr(w, 'layout') and w.layout() and w.layout().objectName() == 'verticalLayout_leftPanel':
                        left_layout = w.layout()
                        break

            inserted = False
            if left_layout is not None:
                # Find index of the existing tab widget in left layout
                idx_in_left = None
                for i in range(left_layout.count()):
                    it = left_layout.itemAt(i)
                    if it and it.widget() is tab_widget:
                        idx_in_left = i
                        break
                if idx_in_left is None:
                    # Fallback: remove from its parent layout and append to left layout
                    idx_in_left = left_layout.count()
                # Remove tab widget from its layout (wherever it is)
                try:
                    if tab_widget.parent() and hasattr(tab_widget.parent(), 'layout') and tab_widget.parent().layout():
                        tab_widget.parent().layout().removeWidget(tab_widget)
                except Exception:
                    pass
                tab_widget.hide()

                # Create new panel and insert at same index
                self.premiere_effects_panel = FinalEffectsPanel(effects_path, left_layout.parentWidget())
                self.premiere_effects_panel.effect_selected.connect(self.on_effect_clicked)
                self.premiere_effects_panel.effect_cleared.connect(self.on_effect_cleared)
                left_layout.insertWidget(idx_in_left, self.premiere_effects_panel)
                inserted = True

            if not inserted:
                # Fallback: replace within the original parent layout
                parent_widget = tab_widget.parent()
                if parent_widget and hasattr(parent_widget, 'layout') and parent_widget.layout():
                    layout = parent_widget.layout()
                    layout.removeWidget(tab_widget)
                    tab_widget.hide()
                    self.premiere_effects_panel = FinalEffectsPanel(effects_path, parent_widget)
                    self.premiere_effects_panel.effect_selected.connect(self.on_effect_clicked)
                    self.premiere_effects_panel.effect_cleared.connect(self.on_effect_cleared)
                    layout.addWidget(self.premiere_effects_panel)
                    inserted = True

            if inserted:
                # Re-apply splitter and stretch to enforce placement and sizing
                try:
                    self.apply_left_splitter()
                    self.apply_left_panel_stretch()
                except Exception:
                    pass
                print("Successfully placed Premiere Effects panel under output (left panel)")
            else:
                print("Could not place Premiere Effects panel; left panel layout not found")
             
        except Exception as e:
            print(f"Error loading Premiere Pro effects panel: {e}")
            import traceback
            traceback.print_exc()
    
    def on_effect_clicked(self, effect_path):
        """Handle effect image click"""
        try:
            effect_name = os.path.basename(effect_path)

            # Apply effect to PREVIEW ONLY for auditioning
            self.preview_overlay_path = effect_path
            
            # Reset debug flag for new overlay
            if hasattr(self, '_preview_overlay_composed_logged'):
                delattr(self, '_preview_overlay_composed_logged')
            print(f"Selected effect: {effect_name} (Preview only)")

            # Auto-create sidecar JSON with opening rect if missing, so all effects work in Preview
            try:
                self._ensure_effect_sidecar(effect_path)
            except Exception as _e:
                print(f"[Effect] Sidecar generation skipped: {_e}")
            # Ensure next preview frames compose overlay immediately (no frame-skipping)
            try:
                self._preview_compose_force = 2  # force compose for next 2 frames
            except Exception:
                pass

            # Force an immediate preview refresh so the user sees the effect instantly
            try:
                self._force_preview_refresh()
            except Exception:
                pass
            
            # Legacy support
            if hasattr(self, '_effects_tabs') and hasattr(self, 'tabWidget_effects'):
                idx = self.tabWidget_effects.currentIndex()
                data = self._effects_tabs.get(idx)
                if data and 'widget' in data and data['widget']:
                    data['widget'].update_selection(effect_path)
            
            # Trigger an immediate update of the preview if possible
            if hasattr(self, 'active_preview_source'):
                st, idx = self.active_preview_source
                # If it's an input, we wait for next frame. If media/static, we could force update.
                
        except Exception as e:
            print(f"Error handling effect click: {e}")

    def on_effect_cleared(self):
        """Clear the current effect."""
        try:
            # Clear PREVIEW selection only (effect is preview-only)
            self.preview_overlay_path = None
            
            try:
                if hasattr(self, '_preview_effect_manager') and self._preview_effect_manager is not None:
                    self._preview_effect_manager.clear_effect()
            except Exception:
                pass

            # Clear selection highlight in UI panel if present
            try:
                if hasattr(self, 'premiere_effects_panel'):
                    self.premiere_effects_panel.clear_selection()
            except Exception:
                pass

            # Refresh preview (remove effect)
            try:
                self._force_preview_refresh()
            except Exception:
                pass
                
        except Exception as e:
            print(f"Error clearing effect: {e}")


    def _ensure_effect_sidecar(self, effect_path: str):
        """Create a JSON sidecar with 'opening' if it doesn't exist and we can auto-detect it.
        This makes effects reliable in Preview regardless of click order (effect-first or media-first).
        """
        try:
            import json, os
            base, _ = os.path.splitext(effect_path)
            json_path = base + '.json'
            if os.path.exists(json_path):
                return  # nothing to do
            from PyQt6.QtGui import QImage
            overlay_img = QImage(str(effect_path))
            if overlay_img.isNull():
                return
            opening = self._detect_overlay_opening(effect_path, overlay_img)
            if not opening or not isinstance(opening, tuple) or len(opening) != 4:
                return
            nx, ny, nw, nh = opening
            data = {"opening": [round(float(nx), 4), round(float(ny), 4), round(float(nw), 4), round(float(nh), 4)]}
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(data, f)
            print(f"[Effect] Wrote sidecar: {json_path} opening={data['opening']}")
        except Exception as e:
            print(f"[Effect] Failed to write sidecar for {effect_path}: {e}")

    def _force_preview_refresh(self):
        """Re-render the preview panel immediately using the latest available frame for the
        current preview source. This helps when selecting an effect while a media source
        hasn't yet populated last_media_image.
        """
        try:
            pv = getattr(self, 'active_preview_source', None)
            if not pv or not isinstance(pv, tuple) or len(pv) != 2:
                return
            st, idx = pv[0], int(pv[1])
            img = None
            if st == 'input':
                if hasattr(self, 'last_input_image'):
                    img = self.last_input_image.get(idx)
            elif st == 'media':
                # Prefer cached full-res image
                if hasattr(self, 'last_media_image'):
                    img = self.last_media_image.get(idx)
                # Fallback: pull a frame directly from the video sink
                if (img is None or (hasattr(img, 'isNull') and img.isNull())):
                    try:
                        if hasattr(self, 'media_sinks') and isinstance(self.media_sinks, dict):
                            sink = self.media_sinks.get(idx)
                            if sink and hasattr(sink, 'videoFrame'):
                                vf = sink.videoFrame()
                                if vf and vf.isValid():
                                    img = vf.toImage()
                    except Exception:
                        pass
                # Fallback: use pixmap cache
                if (img is None or (hasattr(img, 'isNull') and img.isNull())) and hasattr(self, 'last_media_pixmap'):
                    pm = self.last_media_pixmap.get(idx)
                    if pm is not None and hasattr(pm, 'toImage'):
                        try:
                            img = pm.toImage()
                        except Exception:
                            img = None
            # Trigger preview update
            self._update_preview_monitor(img, st, idx)
        except Exception:
            pass

    def open_calibration_tool(self):
        """Calibration tool is unavailable (missing calibration_tool.py)."""
        print("Calibration tool is not available in this build.")

    def refresh_output_preview(self):
        """Re-render the output preview with current effect and last frame (or black)."""
        try:
            if getattr(self, '_transition_running', False):
                # During transitions, frames are driven by the transition engine.
                return
            if not hasattr(self, 'current_output') or self.current_output is None:
                # No source selected; render effect over black
                self._set_output_image(None)
                return
            st, idx = self.current_output
            if st == 'input':
                img = self.last_input_image.get(idx)
                if img is not None:
                    self._set_output_image(img)
                else:
                    self._set_output_image(None)
            elif st == 'media':
                img = self.last_media_image.get(idx)
                if img is not None:
                    self._set_output_image(img)
                else:
                    self._set_output_image(None)
            else:
                self._set_output_image(None)
        except Exception as e:
            print(f"Error refreshing output preview: {e}")

    def _on_master_frame_tick(self, ts):
        """Master clock tick: refresh the Preview monitor independently at global FPS.
        Does not affect Program output, audio, or encoders.
        """
        try:
            pv = getattr(self, 'active_preview_source', None)
            if not pv or not isinstance(pv, tuple) or len(pv) != 2:
                return
            st, idx = pv[0], int(pv[1])
            frame = None
            if st == 'input':
                frame = self.last_input_image.get(idx) if hasattr(self, 'last_input_image') else None
            elif st == 'media':
                frame = self.last_media_image.get(idx) if hasattr(self, 'last_media_image') else None
            self._update_preview_monitor(frame, st, idx)
        except Exception:
            pass
    
    def init_app_state(self):
        """Initialize the application state"""
        self.recording = False
        self.playing = False

        # Effects workflow state
        self.preview_overlay_path = None
        self.program_overlay_path = None

        # Backend project model (Scenes/Sources persistence) - headless for now (no UI changes)
        try:
            if ProjectManager is not None and not hasattr(self, 'project_manager'):
                self.project_manager = ProjectManager()
                self.project = self.project_manager.load()
        except Exception:
            pass

        self.stream1_active = False
        self.stream2_active = False
        self.audio_monitor_muted = False
        # Global audio mute state (master mute)
        self.global_audio_muted = False
        # Tools button states
        self.passthrough_enabled = False
        self.controls_locked = False
        
        # Renderer performance tracking
        self.renderer_mode = "Quality"
        self.renderer_fps = 60

        self._renderer_stats = {
            'frame_count': 0,
            'last_fps_check': 0,
            'current_fps': 0
        }
        # Previous per-channel states to restore after global unmute
        self._prev_audio_states = {
            'inputs': {1: True, 2: True, 3: True},
            'media': {1: True, 2: True, 3: True},
        }

        self.input1_audio_muted = False
        self.input2_audio_muted = False
        self.input3_audio_muted = False
        # Media audio should be muted by default; only the selected output media gets unmuted
        self.media1_audio_muted = True
        self.media2_audio_muted = True
        self.media3_audio_muted = True
        self.media_playing = False
        self.current_1A_source = None
        self.current_2B_source = None

        # Graphics output scene-based preview
        self._graphics_output: GraphicsOutputWidget | None = None

        # Output selection state (for switching controls)
        self.current_output = None  # no auto program selection at startup
        # Previews (downscaled for right panel)
        self.last_input_pixmap = {}
        self.last_media_pixmap = {}
        # Originals (full-res) for high-quality output screen scaling
        self.last_input_image = {}
        self.last_media_image = {}

        # Ensure output preview label exists
        self._ensure_output_preview_label()

        # Initialize Qt Multimedia media players and outputs (Phase 1)
        self.media_players = {
            1: QMediaPlayer(self),
            2: QMediaPlayer(self),
            3: QMediaPlayer(self),
        }
        self.media_audio_outputs = {
            1: QAudioOutput(self),
            2: QAudioOutput(self),
            3: QAudioOutput(self),
        }
        # Attach audio outputs and set default mute state (muted by default)
        for i in (1, 2, 3):
            self.media_players[i].setAudioOutput(self.media_audio_outputs[i])
            self.media_audio_outputs[i].setMuted(getattr(self, f"media{i}_audio_muted", True))

        # Use QVideoSink to receive frames for media and render to frames and output
        self.media_sinks = {}
        for i in (1, 2, 3):
            sink = QVideoSink(self)
            sink.videoFrameChanged.connect(lambda frame, idx=i: self._on_media_frame(idx, frame))
            self.media_sinks[i] = sink
            self.media_players[i].setVideoOutput(sink)
            # Position/duration signals for slider
            self.media_players[i].positionChanged.connect(lambda pos, idx=i: self._on_media_position_changed(idx, pos))
            self.media_players[i].durationChanged.connect(lambda dur, idx=i: self._on_media_duration_changed(idx, dur))
            # Add error handling and media status monitoring
            self.media_players[i].errorOccurred.connect(lambda error, idx=i: self._on_media_error(idx, error))
            self.media_players[i].mediaStatusChanged.connect(lambda status, idx=i: self._on_media_status_changed(idx, status))
            self.media_players[i].playbackStateChanged.connect(lambda state, idx=i: self._on_playback_state_changed(idx, state))

        # Initialize input audio monitors (Phase 2) containers
        self.input_audio_inputs = {}
        self.input_audio_sinks = {}

        # Clear effects and ensure text overlay is disabled by default
        if self._graphics_output is not None:
            self._graphics_output.clear_overlay()
            # Ensure text overlay is disabled
            default_text_props = {
                'visible': False,
                'text': '',
                'font_size': 36,
                'font_family': '',
                'color': 0xFFFFFFFF,
                'stroke_color': 0xFF000000,
                'stroke_width': 3,
                'bg_enabled': False,
                'bg_color': 0xA0000000,
                'pos_x': 50,
                'pos_y': 90,
                'anchor': 'center',
                'scroll': False,
                'scroll_speed': 50,
            }
            self._graphics_output.set_text_overlay(default_text_props)

        # Update status
        self.update_record_status("Ready", "#777777")

    def closeEvent(self, event):
        """Ensure clean shutdown of background processes and persist settings."""
        # Print performance report
        print("\nGenerating final performance report...")
        try:
            performance_monitor.print_performance_summary()
        except:
            pass
        
        try:
            # Stop frame processing workers (WINDOWS FPS FIX)
            try:
                if hasattr(self, '_frame_workers') and isinstance(self._frame_workers, dict):
                    for worker in list(self._frame_workers.values()):
                        try:
                            worker.stop()
                        except Exception:
                            pass
                    self._frame_workers.clear()
            except Exception:
                pass
            # Stop streaming controllers (primary)
            try:
                if hasattr(self, 'stream_controller') and self.stream_controller:
                    self.stream_controller.stop()
            except Exception:
                pass
            # Stop independent stream controllers (Stream 1 & 2)
            try:
                if hasattr(self, 'stream_controllers') and isinstance(self.stream_controllers, dict):
                    for _sc in self.stream_controllers.values():
                        try:
                            _sc.stop()
                        except Exception:
                            pass
            except Exception:
                pass
            # Stop recorder
            try:
                if hasattr(self, 'recorder_controller') and self.recorder_controller:
                    self.recorder_controller.stop()
            except Exception:
                pass
            # Stop mirror controller
            try:
                if hasattr(self, 'mirror_controller') and self.mirror_controller:
                    self.mirror_controller.stop()
            except Exception:
                pass
            # Stop OBS-style camera pipelines
            try:
                if hasattr(self, 'camera_managers') and isinstance(self.camera_managers, dict):
                    for input_num in list(self.camera_managers.keys()):
                        try:
                            self.stop_camera_capture(input_num)
                        except Exception:
                            pass
            except Exception:
                pass
            # Save UI/session settings
            try:
                if self._graphics_output is not None:
                    # Keep existing config values (overscan/fps tracked elsewhere)
                    pass
                try:
                    if hasattr(self, 'project_manager') and getattr(self, 'project_manager', None) is not None:
                        self.project_manager.save()
                except Exception:
                    pass
                app_config.save_settings()
            except Exception:
                pass
            
            # Cleanup optimization systems
            print("Cleaning up optimization systems...")
            try:
                if timer_manager.get_system():
                    timer_manager.get_system().cleanup()
            except:
                pass
            try:
                thread_pool.shutdown(wait=False)
            except:
                pass
            try:
                event_coalescer.stop()
            except:
                pass
            try:
                gl_context_manager.cleanup()
            except:
                pass
            try:
                smart_cache.clear()
                texture_pool.clear()
                general_memory_pool.clear()
                image_memory_pool.clear()
            except:
                pass
            
            # Shutdown GPU acceleration
            try:
                if GPU_ACCELERATION_AVAILABLE:
                    shutdown_gpu_acceleration()
            except:
                pass
            
            # Shutdown GPU pipeline (Phase 3)
            try:
                if GPU_PIPELINE_AVAILABLE:
                    shutdown_gpu_pipeline()
            except:
                pass
            
        except Exception:
            pass
        super().closeEvent(event)

    def cleanup_on_exit(self):
        """Called from QApplication.aboutToQuit to ensure all processes are stopped before teardown."""
        try:
            try:
                if hasattr(self, 'stream_controller') and self.stream_controller:
                    self.stream_controller.stop()
            except Exception:
                pass
            try:
                if hasattr(self, 'mirror_controller') and self.mirror_controller:
                    self.mirror_controller.stop()
            except Exception:
                pass
        except Exception:
            pass
    
    def toggle_recording(self):
        """Enhanced toggle recording with better error handling and user feedback"""
        try:
            current_state = getattr(self, 'recording', False)
            
            if not current_state:
                # Start recording
                # === DIAGNOSTIC: Recording start ===
                print(f"\n[REC] 🔴 Recording starting — main.py")
                print(f"[REC]    Time: {time.strftime('%H:%M:%S')}\n")
                print("🎥 Starting recording...")
                success = self.start_recording()
                if success:
                    self.recording = True
                    try:
                        self.update_record_status("Recording", "#ff0000")
                    except Exception:
                        pass
                    print("✅ Recording started successfully")
                else:
                    self.recording = False
                    try:
                        self.update_record_status("Ready", "#777777")
                    except Exception:
                        pass
                    print("❌ Failed to start recording")
            else:
                # Stop recording
                # === DIAGNOSTIC: Recording stop ===
                print(f"\n[REC] ⬜ Recording stopping — main.py")
                print(f"[REC]    Time: {time.strftime('%H:%M:%S')}\n")
                print("🛑 Stopping recording...")
                self.stop_recording()
                self.recording = False
                try:
                    self.update_record_status("Ready", "#777777")
                except Exception:
                    pass
                print("✅ Recording stopped")
                
        except Exception as e:
            # === DIAGNOSTIC: Recording error ===
            _diag_error("Recording toggle failed",
                       e,
                       f"File: main.py | "
                       f"Current state: {getattr(self, 'recording', False)}")
            print(f"❌ Error toggling recording: {e}")
            self.recording = False
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Recording Error", f"Failed to toggle recording:\n{str(e)}")

    def toggle_global_mute(self):
        """Toggle master mute for all inputs and media. Restores previous states on unmute."""
        try:
            new_state = not getattr(self, 'global_audio_muted', False)
            if new_state:
                # Save current per-channel states
                self._prev_audio_states = {
                    'inputs': {
                        1: getattr(self, 'input1_audio_muted', True),
                        2: getattr(self, 'input2_audio_muted', True),
                        3: getattr(self, 'input3_audio_muted', True),
                    },
                    'media': {
                        1: getattr(self, 'media1_audio_muted', True),
                        2: getattr(self, 'media2_audio_muted', True),
                        3: getattr(self, 'media3_audio_muted', True),
                    }
                }
                # Mute all inputs (stop monitors) and set icons
                self.input1_audio_muted = True
                self.input2_audio_muted = True
                self.input3_audio_muted = True
                for i in (1, 2, 3):
                    try:
                        self._stop_input_audio(i)
                    except Exception:
                        pass
                if hasattr(self, 'input1AudioButton'):
                    self.input1AudioButton.setIcon(self.get_icon("Mute.png"))
                if hasattr(self, 'input2AudioButton'):
                    self.input2AudioButton.setIcon(self.get_icon("Mute.png"))
                if hasattr(self, 'input3AudioButton'):
                    self.input3AudioButton.setIcon(self.get_icon("Mute.png"))

                # Mute all media and set icons
                for i in (1, 2, 3):
                    setattr(self, f"media{i}_audio_muted", True)
                    if hasattr(self, 'media_audio_outputs') and i in self.media_audio_outputs:
                        try:
                            self.media_audio_outputs[i].setMuted(True)
                        except Exception:
                            pass
                    btn_attr = f"media{i}AudioButton"
                    if hasattr(self, btn_attr):
                        getattr(self, btn_attr).setIcon(self.get_icon("Mute.png"))

                print("Global audio muted")
            else:
                # Restore previous states for inputs
                for i in (1, 2, 3):
                    prev = self._prev_audio_states.get('inputs', {}).get(i, True)
                    setattr(self, f"input{i}_audio_muted", prev)
                    # If input should be active (unmuted) and currently on program, ensure monitor
                    try:
                        if not prev and getattr(self, 'current_output', (None, -1))[0] == 'input' and getattr(self, 'current_output', (None, -1))[1] == i:
                            self._ensure_input_audio(i)
                        else:
                            self._stop_input_audio(i)
                    except Exception:
                        pass
                    btn_attr = f"input{i}AudioButton"
                    if hasattr(self, btn_attr):
                        getattr(self, btn_attr).setIcon(self.get_icon("Mute.png" if prev else "Volume.png"))

                # Restore previous states for media and apply
                for i in (1, 2, 3):
                    prev = self._prev_audio_states.get('media', {}).get(i, True)
                    setattr(self, f"media{i}_audio_muted", prev)
                    if hasattr(self, 'media_audio_outputs') and i in self.media_audio_outputs:
                        try:
                            # Also respect current media policy (it may immediately re-mute others on next switch)
                            self.media_audio_outputs[i].setMuted(prev)
                        except Exception:
                            pass
                    btn_attr = f"media{i}AudioButton"
                    if hasattr(self, btn_attr):
                        getattr(self, btn_attr).setIcon(self.get_icon("Mute.png" if prev else "Volume.png"))

                print("Global audio unmuted (previous states restored)")

            # Update master icon and state
            self.global_audio_muted = new_state
            if hasattr(self, 'audioTopButton'):
                self.audioTopButton.setIcon(self.get_icon("Mute.png" if self.global_audio_muted else "Volume.png"))
        except Exception as e:
            print(f"Error toggling global mute: {e}")
    
    def start_recording(self) -> bool:
        """Enhanced start recording with better validation and error handling."""
        try:
            print("🎬 Initializing recording...")

            # Ensure recorder controller is initialized (lazy init in case startup init failed)
            try:
                self._ensure_recorder_controller()
            except Exception as _e:
                print(f"❌ Recorder controller init failed: {_e}")
                import traceback
                traceback.print_exc()
            
            # Check if recorder controller exists
            if not hasattr(self, 'recorder_controller') or not self.recorder_controller:
                print("❌ Recorder controller not available")
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.critical(self, "Recording Error", "Recording system not initialized properly.")
                return False
            
            # Check if already recording
            if self.recorder_controller.is_running():
                print("⚠️ Recording already in progress")
                return False
            
            # Ensure we have a save path
            out_path = app_config.get('recording.output_path', '') or ''
            include_audio = bool(app_config.get('recording.audio_enabled', True))
            
            print(f"📁 Output path: {out_path}")
            print(f"🎧 Include audio: {include_audio}")
            
            if not out_path:
                print("⚠️ No output path configured, opening settings...")
                # Prompt settings dialog if no path saved yet
                self.open_record_settings()
                out_path = app_config.get('recording.output_path', '') or ''
                include_audio = bool(app_config.get('recording.audio_enabled', True))
                if not out_path:
                    print("❌ User cancelled or no path provided")
                    return False

            # Determine output size and fps (follow Output Size selection), then clamp for recording
            fps = int(app_config.get('ui.preview_fps', 60) or 60)
            width = int(app_config.get('ui.output_width', 1920))
            height = int(app_config.get('ui.output_height', 1080))

            # Clamp recording FPS to 24 to further prevent pipe backpressure
            rec_fps = min(24, max(10, fps))

            # Downscale large resolutions for recording to 960x540 to reduce raw pipe bandwidth
            rec_width, rec_height = width, height
            if width * height > 960 * 540:
                aspect = width / max(1, height)
                rec_width = 960
                rec_height = int(round(rec_width / aspect))
                # Ensure multiple of 2 for encoders
                if rec_height % 2:
                    rec_height += 1

            print(f"🎯 Effective recording resolution: {rec_width}x{rec_height} @ {rec_fps}fps (source: {width}x{height} @ {fps}fps)")

            # Audio strategy: if a media is on program, mux its original audio; otherwise optionally capture system
            program_media_audio_path = self.get_current_program_media_audio_path() or ''
            # Determine media start position so recorded audio aligns with current playback
            program_media_audio_start_ms = 0
            try:
                if getattr(self, 'current_output', (None, None))[0] == 'media':
                    m_idx = getattr(self, 'current_output', (None, None))[1]
                    player = self.media_players.get(m_idx)
                    if player is not None:
                        program_media_audio_start_ms = int(getattr(player, 'position')() or 0)
            except Exception:
                program_media_audio_start_ms = 0

            audio_device = ''
            # Validate output directory
            import os
            output_dir = os.path.dirname(out_path)
            if not os.path.exists(output_dir):
                try:
                    os.makedirs(output_dir, exist_ok=True)
                    print(f"📁 Created output directory: {output_dir}")
                except Exception as e:
                    print(f"❌ Cannot create output directory: {e}")
                    from PyQt6.QtWidgets import QMessageBox
                    QMessageBox.critical(self, "Recording Error", f"Cannot create output directory:\n{output_dir}\n\nError: {e}")
                    return False
            
            # Check disk space (warn if less than 1GB)
            try:
                import shutil
                free_space = shutil.disk_usage(output_dir).free
                free_gb = free_space / (1024**3)
                print(f"💾 Available disk space: {free_gb:.1f} GB")
                if free_gb < 1.0:
                    from PyQt6.QtWidgets import QMessageBox
                    reply = QMessageBox.warning(
                        self, "Low Disk Space", 
                        f"Warning: Only {free_gb:.1f} GB of disk space available.\n\nContinue recording anyway?",
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                        QMessageBox.StandardButton.No
                    )
                    if reply == QMessageBox.StandardButton.No:
                        return False
            except Exception:
                pass
            
            # Audio configuration
            if include_audio and not program_media_audio_path:
                # First, try to use the audio device stored in config (from recording settings dialog)
                audio_device = app_config.get('recording.audio_device', '') or ''
                if audio_device:
                    print(f"🎤 ✅ Using audio device from settings: {audio_device}")
                else:
                    print(f"🎤 ⚠️ No audio device in config, attempting auto-detection...")
                    # Fallback: Reuse streaming's auto device detection for convenience
                    try:
                        sc = None
                        if hasattr(self, 'stream_controllers') and isinstance(self.stream_controllers, dict):
                            sc = self.stream_controllers.get(1) or self.stream_controllers.get(2)
                        if sc is not None and hasattr(sc, '_auto_select_audio_device'):
                            audio_device = sc._auto_select_audio_device() or ''
                            if audio_device:
                                print(f"🎤 ✅ Auto-selected audio device: {audio_device}")
                            else:
                                print(f"🎤 ⚠️ Streaming controller did not return device")
                    except Exception as e:
                        print(f"🎤 ⚠️ Streaming controller fallback failed: {e}")
                        audio_device = ''

            # Windows fallback: if no device was selected, try to pick the first available dshow audio device
            if include_audio and not program_media_audio_path and not audio_device:
                print(f"🎤 ⚠️ Attempting Windows DirectShow device fallback...")
                try:
                    import sys as _sys
                    if _sys.platform.startswith('win'):
                        from ffmpeg_utils import get_ffmpeg_path
                        import subprocess
                        ffmpeg_path = get_ffmpeg_path()
                        print(f"🎤 Querying FFmpeg for audio devices...")
                        res = subprocess.run(
                            [ffmpeg_path, '-hide_banner', '-list_devices', 'true', '-f', 'dshow', '-i', 'dummy'],
                            capture_output=True, text=True, timeout=3
                        )
                        text = (res.stdout or '') + '\n' + (res.stderr or '')
                        for line in text.splitlines():
                            l = (line or '').strip()
                            if '(audio)' in l and '"' in l:
                                try:
                                    audio_device = l.split('"')[1]
                                    break
                                except Exception:
                                    continue
                        if audio_device:
                            print(f"🎤 ✅ Windows fallback audio device found: {audio_device}")
                        else:
                            print(f"🎤 ❌ Windows fallback: No audio devices found")
                except Exception as e:
                    print(f"🎤 ❌ Windows fallback failed: {e}")
            
            # Get advanced settings from recording settings dialog
            advanced_settings = self._get_recording_advanced_settings()
            # Adjust bitrate for reduced resolution to avoid encoder backpressure
            eff_bitrate = int(advanced_settings.get('bitrate_kbps', 12000))
            if rec_width * rec_height <= 960 * 540 and eff_bitrate > 6000:
                eff_bitrate = 6000
            
            print(f"📺 Recording settings:")
            print(f"  Resolution: {width}x{height}")
            print(f"  FPS: {fps}")
            print(f"  Bitrate: {eff_bitrate} kbps")
            print(f"  Format: {advanced_settings.get('format', 'MP4')}")
            print(f"  🎤 Audio capture: {include_audio and not program_media_audio_path}")
            print(f"  🎤 Audio device: {audio_device if audio_device else '(None - will use fallback)'}")
            # Respect user include_audio setting when not muxing media audio
            
            settings = {
                'file_path': out_path,
                'width': rec_width,
                'height': rec_height,
                'fps': rec_fps,
                'bitrate_kbps': eff_bitrate,
                'video_preset': advanced_settings.get('video_preset', 'veryfast'),
                'capture_audio': include_audio and not program_media_audio_path,
                'audio_device': audio_device,
                'program_media_audio_path': program_media_audio_path,
                # Align media audio to current playback position
                'program_media_audio_start_ms': program_media_audio_start_ms,
                # Keep A/V delay at 0 when using direct media audio; recorder can add minimal if needed
                'av_sync_delay_ms': 0,
            }
            
            try:
                print("🚀 Starting recorder controller...")
                self.recorder_controller.start(settings)
                
                # Update UI
                self.update_record_status("Recording", "#ff0000")
                
                # Update record button icon to show recording state (guard widget lifetime)
                try:
                    btn = getattr(self, 'recordRedCircle', None)
                    if btn is not None:
                        btn.setStyleSheet("background-color: #ff0000; border-radius: 15px;")
                except Exception:
                    pass
                
                # Show Pause icon on play button (guard widget lifetime)
                try:
                    pb = getattr(self, 'playButton', None)
                    if pb is not None:
                        pb.setIcon(self.get_icon("Pause.png"))
                except Exception:
                    pass
                
                print("✅ Recording started successfully")
                return True
                
            except Exception as e:
                print(f"❌ Failed to start recording: {e}")
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.critical(self, "Recording Error", f"Failed to start recording:\n{str(e)}")
                return False
                
        except Exception as e:
            print(f"❌ Error starting recording: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _ensure_recorder_controller(self):
        try:
            if hasattr(self, 'recorder_controller') and self.recorder_controller:
                return
        except Exception:
            # If PyQt object has been deleted, accessing it may raise; recreate
            pass

        print("🎥 Initializing recording controller (lazy)...")
        self.recorder_controller = RecorderController(self)
        self.recorder_controller.set_frame_provider(self._provide_stream_frame)
        self.recorder_controller.on_log(self._on_record_log)
        self.recorder_controller.statusChanged.connect(self._on_record_status_changed)
        if not hasattr(self, 'recording'):
            self.recording = False
        print("✅ Recording controller initialized successfully (lazy)")
    
    def check_recording_health(self) -> dict:
        """Check recording system health and return diagnostic information."""
        health = {
            'status': 'unknown',
            'issues': [],
            'recommendations': [],
            'system_info': {}
        }
        
        try:
            # Check recorder controller
            if not hasattr(self, 'recorder_controller') or not self.recorder_controller:
                health['status'] = 'error'
                health['issues'].append("Recording controller not initialized")
                health['recommendations'].append("Restart the application")
                return health
            
            # Check if recording is active
            is_running = self.recorder_controller.is_running()
            is_paused = self.recorder_controller.is_paused() if is_running else False
            
            if is_running:
                if is_paused:
                    health['status'] = 'paused'
                else:
                    health['status'] = 'recording'
            else:
                health['status'] = 'ready'
            
            # Check output path configuration
            out_path = app_config.get('recording.output_path', '') or ''
            if not out_path:
                health['issues'].append("No output path configured")
                health['recommendations'].append("Configure recording output path in settings")
            else:
                # Check if output directory exists and is writable
                import os
                output_dir = os.path.dirname(out_path)
                if not os.path.exists(output_dir):
                    health['issues'].append(f"Output directory does not exist: {output_dir}")
                    health['recommendations'].append("Create output directory or choose different path")
                elif not os.access(output_dir, os.W_OK):
                    health['issues'].append(f"Output directory not writable: {output_dir}")
                    health['recommendations'].append("Check directory permissions")
                
                # Check disk space
                try:
                    import shutil
                    free_space = shutil.disk_usage(output_dir).free
                    free_gb = free_space / (1024**3)
                    health['system_info']['free_space_gb'] = round(free_gb, 1)
                    
                    if free_gb < 0.5:
                        health['issues'].append(f"Very low disk space: {free_gb:.1f} GB")
                        health['recommendations'].append("Free up disk space or choose different location")
                    elif free_gb < 2.0:
                        health['issues'].append(f"Low disk space: {free_gb:.1f} GB")
                        health['recommendations'].append("Consider freeing up disk space")
                except Exception:
                    pass
            
            # Check FFmpeg availability
            try:
                from ffmpeg_utils import get_ffmpeg_path
                import subprocess
                ffmpeg_path = get_ffmpeg_path()
                result = subprocess.run([ffmpeg_path, '-version'], 
                                      capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    health['system_info']['ffmpeg_available'] = True
                    # Extract version info
                    for line in result.stdout.split('\n'):
                        if 'ffmpeg version' in line.lower():
                            health['system_info']['ffmpeg_version'] = line.strip()
                            break
                else:
                    health['issues'].append("FFmpeg not working properly")
                    health['recommendations'].append("Reinstall FFmpeg")
            except Exception as e:
                health['issues'].append(f"FFmpeg not available: {str(e)}")
                health['recommendations'].append("Install FFmpeg")
            
            # Overall health assessment
            if not health['issues']:
                health['status'] = 'healthy' if health['status'] == 'ready' else health['status']
            elif len(health['issues']) > 2:
                health['status'] = 'critical'
            else:
                health['status'] = 'warning'
                
        except Exception as e:
            health['status'] = 'error'
            health['issues'].append(f"Health check failed: {str(e)}")
            
        return health
    
    def show_recording_health_info(self):
        """Display recording health information to user."""
        health = self.check_recording_health()
        
        print(f"\n🎥 Recording System Health Check:")
        print("=" * 50)
        print(f"Status: {health['status'].upper()}")
        
        if health['system_info']:
            print("\n📊 System Info:")
            for key, value in health['system_info'].items():
                print(f"  • {key}: {value}")
        
        if health['issues']:
            print(f"\n⚠️ Issues Found ({len(health['issues'])}):")
            for issue in health['issues']:
                print(f"  • {issue}")
        
        if health['recommendations']:
            print(f"\n💡 Recommendations:")
            for rec in health['recommendations']:
                print(f"  • {rec}")
        
        print("=" * 50)
    
    def _get_recording_advanced_settings(self) -> dict:
        """Get advanced recording settings from config."""
        return {
            'bitrate_kbps': int(app_config.get('recording.bitrate_kbps', 12000)),
            'video_preset': app_config.get('recording.video_preset', 'veryfast'),
            'format': app_config.get('recording.format', 'MP4'),
            'crf': int(app_config.get('recording.crf', 18)),
            'hardware_acceleration': bool(app_config.get('recording.hardware_acceleration', True)),
        }
    
    def stop_recording(self):
        """Enhanced stop recording with better feedback."""
        try:
            print("🛑 Stopping recording...")
            
            if hasattr(self, 'recorder_controller') and self.recorder_controller:
                if self.recorder_controller.is_running():
                    self.recorder_controller.stop()
                    print("✅ Recorder controller stopped")
                else:
                    print("⚠️ Recorder was not running")
            else:
                print("❌ Recorder controller not available")
            
            # Update UI
            self.update_record_status("Ready", "#777777")
            
            # Reset record button appearance
            try:
                btn = getattr(self, 'recordRedCircle', None)
                if btn is not None:
                    btn.setStyleSheet("background-color: #404040; border-radius: 15px;")
            except Exception:
                pass
            
            # Reset play button to Play icon
            try:
                pb = getattr(self, 'playButton', None)
                if pb is not None:
                    pb.setIcon(self.get_icon("Play.png"))
            except Exception:
                pass
            
            print("✅ Recording stopped successfully")
            
        except Exception as e:
            print(f"❌ Error stopping recording: {e}")
            import traceback
            traceback.print_exc()
    
    def toggle_playback(self):
        """Enhanced play/pause button: pauses/resumes the recorder if running."""
        try:
            rc = getattr(self, 'recorder_controller', None)
            if rc and rc.is_running():
                if rc.is_paused():
                    print("▶️ Resuming recording...")
                    rc.resume()
                    if hasattr(self, 'playButton'):
                        self.playButton.setIcon(self.get_icon("Pause.png"))
                    self.update_record_status("Recording", "#ff0000")
                    print("✅ Recording resumed")
                else:
                    print("⏸️ Pausing recording...")
                    rc.pause()
                    if hasattr(self, 'playButton'):
                        self.playButton.setIcon(self.get_icon("Play.png"))
                    self.update_record_status("Paused", "#ffaa00")
                    print("✅ Recording paused")
                return
            else:
                print("⚠️ No active recording to pause/resume")
                
        except Exception as e:
            print(f"❌ Error toggling record pause: {e}")
            
        # Fallback: toggle local state and icon if recorder not present
        self.playing = not getattr(self, 'playing', False)
        if self.playing:
            if hasattr(self, 'playButton'):
                self.playButton.setIcon(self.get_icon("Pause.png"))
        else:
            if hasattr(self, 'playButton'):
                self.playButton.setIcon(self.get_icon("Play.png"))
    
    def capture_screenshot(self):
        """Capture a screenshot of the output panel and save next to the recording output path."""
        try:
            # Determine output directory from recording settings
            out_path = app_config.get('recording.output_path', '') or ''
            if not out_path:
                QMessageBox.information(self, "Screenshot", "Please set a recording path first in Recording Settings.")
                return
            out_dir = os.path.dirname(out_path)
            if not out_dir:
                out_dir = os.path.expanduser('~')
            # Render current output using selected Output Size
            ow = int(app_config.get('ui.output_width', 1920))
            oh = int(app_config.get('ui.output_height', 1080))
            target_size = QSize(ow, oh)
            if hasattr(self, '_graphics_output') and self._graphics_output is not None:
                img = self._graphics_output.render_to_image(target_size)
            else:
                img = QImage(target_size, QImage.Format.Format_ARGB32)
                img.fill(0)
            # Filename with timestamp
            from PyQt6.QtCore import QDateTime
            ts = QDateTime.currentDateTime().toString('yyyyMMdd_HHmmss')
            base = os.path.splitext(os.path.basename(out_path))[0] or 'recording'
            fname = f"{base}_{ts}.png"
            fpath = os.path.join(out_dir, fname)
            ok = img.save(fpath)
            if ok:
                print(f"Screenshot saved: {fpath}")
            else:
                QMessageBox.warning(self, "Screenshot", "Failed to save screenshot.")
        except Exception as e:
            print(f"Screenshot error: {e}")
    
    def open_record_settings(self):
        """Open recording settings dialog to choose file path and audio option."""
        try:
            print("🎥 Opening recording settings dialog...")
            initial = app_config.get('recording.output_path', '') or ''
            include_audio = bool(app_config.get('recording.audio_enabled', True))
            initial_audio_device = app_config.get('recording.audio_device', '') or ''
            print(f"📁 Initial path: {initial}")
            print(f"🎧 Include audio: {include_audio}")
            print(f"🎤 Initial audio device: {initial_audio_device if initial_audio_device else '(Default/Auto-detect)'}")
            
            dlg = RecordingSettingsDialog(self, initial_path=initial, include_audio=include_audio, initial_audio_device=initial_audio_device)
            print("✅ Recording settings dialog created successfully")
            
            if dlg.exec():
                values = dlg.get_values() or {}
                advanced = dlg.get_advanced_settings() or {}
                path = (values.get('output_path') or '').strip() if isinstance(values, dict) else ''
                audio = bool(values.get('audio_enabled', True)) if isinstance(values, dict) else True
                audio_device = (values.get('audio_device') or '').strip() if isinstance(values, dict) else ''
                print(f"💾 User saved settings:")
                print(f"  📁 Path: {path}")
                print(f"  🎧 Audio: {audio}")
                print(f"  🎤 Audio Device: {audio_device if audio_device else '(Default/Auto-detect)'}")
                try:
                    if isinstance(values, dict):
                        print(f"  🎬 Format: {values.get('format', 'Unknown')}")
                        print(f"  ⭐ Quality: CRF {values.get('crf', 'Unknown')}")
                except Exception:
                    pass
                
                if path:
                    app_config.set('recording.output_path', path)
                    app_config.set('recording.audio_enabled', bool(audio))
                    app_config.set('recording.audio_device', audio_device)
                    app_config.save_settings()
                    print("✅ Recording settings saved to config")
                else:
                    print("⚠️ No path specified, settings not saved")
            else:
                print("❌ User cancelled recording settings")
                
        except Exception as e:
            print(f"❌ Recording settings error: {e}")
            import traceback
            traceback.print_exc()
    
    def _debug_open_record_settings(self):
        """Debug wrapper for recording settings."""
        print("🎥 DEBUG: Recording Settings menu item clicked")
        self.open_record_settings()
    
    def _debug_show_text_overlay_settings(self):
        """Debug wrapper for text overlay settings."""
        print("✍️ DEBUG: Text Overlay Settings menu item clicked")
        self.show_text_overlay_settings()

    def _on_record_status_changed(self, status: str):
        try:
            st = (status or '').lower()
            if 'started' in st:
                self.update_record_status("Recording", "#ff0000")
            elif 'paused' in st:
                self.update_record_status("Paused", "#ffaa00")
            elif 'error' in st:
                self.update_record_status("Record Error", "#ff4444")
            else:
                # Stopped or unknown
                self.update_record_status("Ready", "#777777")
        except Exception as e:
            print(f"Record status UI error: {e}")

    def _on_record_log(self, text: str):
        try:
            if text:
                print(text, end='' if text.endswith('\n') else '\n')
        except Exception:
            pass

    def _on_stream_log(self, text: str):
        """Stream controller FFmpeg/log output - always print to terminal for debugging."""
        try:
            if text:
                print(text, end='' if text.endswith('\n') else '\n')
        except Exception:
            pass

    def get_stream_controller(self, stream_id: int) -> StreamController:
        """Get the StreamController for the given stream_id. Falls back to legacy controller for stream 1 if needed."""
        try:
            if hasattr(self, 'stream_controllers') and isinstance(self.stream_controllers, dict):
                ctrl = self.stream_controllers.get(stream_id)
                if ctrl is not None:
                    return ctrl
            # Fallback: use legacy stream_controller for stream 1 (in case stream_controllers init failed)
            if stream_id == 1 and hasattr(self, 'stream_controller') and self.stream_controller is not None:
                return self.stream_controller
            if not hasattr(self, 'stream_controllers'):
                print(f"[STREAM] get_stream_controller: stream_controllers not initialized")
            elif stream_id not in (getattr(self, 'stream_controllers', None) or {}):
                print(f"[STREAM] get_stream_controller: no controller for stream {stream_id}")
            return None
        except Exception as e:
            print(f"[STREAM] get_stream_controller error: {e}")
            return None

    def handle_stream_button_click(self, stream_id: int):
        """Handle stream button click - toggles stream on/off."""
        print(f"🎬 Stream {stream_id} button clicked - toggling stream...")
        self.toggle_stream(stream_id)
    
    def toggle_stream(self, stream_id: int):
        """Toggle stream on/off using independent StreamController and saved settings."""
        key_prefix = f'streaming.stream{stream_id}'
        active_attr = f'stream{stream_id}_active'
        current = getattr(self, active_attr, False)
        controller = self.get_stream_controller(stream_id)
        if controller is None:
            print(f"❌ Stream controller for stream {stream_id} not available (see logs above)")
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(self, f"Stream {stream_id} Error",
                "Streaming controller not available. The stream controllers may not have initialized correctly. Try restarting the application.")
            return
        
        if not current:
            # Start streaming
            settings = self._load_stream_settings(stream_id)
            print(f"🚀 Starting Stream {stream_id} with settings: {settings}")
            
            # Check if settings are configured
            if not settings.get('url') and settings.get('platform') != 'External Display (Mirror)':
                print(f"⚠️ Stream {stream_id} not configured - opening settings dialog")
                self.open_stream_settings_dialog(stream_id)
                return
            
            try:
                if settings.get('platform') == 'YouTube Live':
                    self._apply_youtube_optimizations(settings)
            except Exception:
                pass
            
            def _do_start():
                try:
                    controller.start(settings)
                except Exception as e:
                    # Marshal error back to main thread
                    from PyQt6.QtCore import QMetaObject, Qt
                    QMetaObject.invokeMethod(
                        self, "_on_stream_start_error",
                        Qt.ConnectionType.QueuedConnection,
                        Q_ARG(int, stream_id),
                        Q_ARG(str, str(e))
                    )
                    return
                # Marshal success back to main thread
                from PyQt6.QtCore import QMetaObject, Qt
                QMetaObject.invokeMethod(
                    self, "_on_stream_start_success",
                    Qt.ConnectionType.QueuedConnection,
                    Q_ARG(int, stream_id)
                )
            
            import threading
            t = threading.Thread(target=_do_start, daemon=True, name=f"StreamStart-{stream_id}")
            t.start()
        else:
            # Stop streaming
            print(f"🛑 Stopping Stream {stream_id}...")
            controller.stop()
            setattr(self, active_attr, False)
            
            # Update button appearance
            btn = getattr(self, f'stream{stream_id}SettingsBtn', None)
            if btn:
                btn.setIcon(self.get_icon("Settings.png"))
                btn.setStyleSheet("border-radius: 5px; background-color: #404040;")  # Gray when stopped
            
            self.update_record_status("Ready", "#777777")
            print(f"✅ Stream {stream_id} stopped")
    
    @pyqtSlot(int)
    def _on_stream_start_success(self, stream_id: int):
        """Called on main thread after stream starts successfully."""
        # === DIAGNOSTIC: Stream started success ===
        print(f"\n[STREAM] 🔴 STREAM {stream_id} STARTED — main.py")
        print(f"[STREAM]    Platform  : {getattr(self, '_current_platform', 'External Mirror') or 'External Mirror'}")
        print(f"[STREAM]    Target FPS: {getattr(self, '_current_fps', 30)}")
        print(f"[STREAM]    Resolution: {getattr(self, '_output_width', '?')}x{getattr(self, '_output_height', '?')}")
        print(f"[STREAM]    Thread    : {threading.current_thread().name}")
        print(f"[STREAM]    Time      : {time.strftime('%H:%M:%S')}\n")
        active_attr = f'stream{stream_id}_active'
        setattr(self, active_attr, True)
        
        btn = getattr(self, f'stream{stream_id}SettingsBtn', None)
        if btn:
            btn.setIcon(self.get_icon("Settings.png"))
            btn.setStyleSheet("border-radius: 5px; background-color: #ff4444;")
        
        self.update_record_status(f"Streaming {stream_id}", "#00aa00")
        print(f"✅ Stream {stream_id} started successfully")
        
        try:
            self._show_streaming_health_info(stream_id, {})
        except Exception:
            pass
        try:
            self._auto_apply_audio_delay_correction()
        except Exception:
            pass
    
    @pyqtSlot(int, str)
    def _on_stream_start_error(self, stream_id: int, error_msg: str):
        """Called on main thread when stream fails to start."""
        # === DIAGNOSTIC: Stream start error ===
        print(f"\n[STREAM] ❌ STREAM {stream_id} FAILED TO START — main.py")
        print(f"[STREAM]    Error: {error_msg}")
        print(f"[STREAM]    Time : {time.strftime('%H:%M:%S')}\n")
        # Try to create an exception-like object for _diag_error
        try:
            raise RuntimeError(f"Stream {stream_id} startup failed: {error_msg}")
        except Exception as e:
            _diag_error(f"Stream {stream_id} failed to start",
                       e,
                       f"File: main.py → _on_stream_start_error | "
                       f"Error message: {error_msg}")
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.critical(self, f"Stream {stream_id} Error",
                             f"Failed to start stream:\n{error_msg}\n\nCheck your stream settings.")
    
    def open_stream_settings_dialog(self, stream_id: int):
        try:
            print(f"🎬 Opening Stream {stream_id} settings dialog...")
            from streaming_settings_dialog_improved import StreamingSettingsDialog
            dlg = StreamingSettingsDialog(self, stream_id, app_config)
            print(f"✅ Stream {stream_id} settings dialog created successfully")
            
            result = dlg.exec()
            print(f"📝 Stream {stream_id} settings dialog closed with result: {result}")
            
            # If user saved settings, ask if they want to start streaming
            if result == dlg.DialogCode.Accepted:
                from PyQt6.QtWidgets import QMessageBox
                reply = QMessageBox.question(
                    self, 
                    f"Stream {stream_id} Settings Saved", 
                    f"Stream {stream_id} settings have been saved.\n\nWould you like to start streaming now?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No
                )
                
                if reply == QMessageBox.StandardButton.Yes:
                    print(f"🚀 User chose to start Stream {stream_id}")
                    self.toggle_stream(stream_id)
                    
        except Exception as e:
            print(f"❌ Error opening Stream {stream_id} settings dialog: {e}")
            import traceback
            traceback.print_exc()
    
    def toggle_stream2(self):
        """Toggle Stream2 state"""
        self.stream2_active = not self.stream2_active
        if self.stream2_active:
            print("Starting Stream2...")
            if hasattr(self, 'stream2AudioBtn'):
                self.stream2AudioBtn.setIcon(self.get_icon("Stop.png"))
        else:
            print("Stopping Stream2...")
            if hasattr(self, 'stream2AudioBtn'):
                self.stream2AudioBtn.setIcon(self.get_icon("Stream.png"))
        # Add your stream2 logic here
    
    def _save_stream_settings(self, stream_id: int, settings: dict):
        prefix = f'streaming.stream{stream_id}'
        for k, v in settings.items():
            app_config.set(f'{prefix}.{k}', v)
        app_config.save_settings()

    def _load_stream_settings(self, stream_id: int) -> dict:
        prefix = f'streaming.stream{stream_id}'
        
        # Get current settings
        settings = {
            'platform': app_config.get(f'{prefix}.platform', 'custom'),
            'url': app_config.get(f'{prefix}.url', ''),
            'key': app_config.get(f'{prefix}.key', ''),
            'width': app_config.get(f'{prefix}.width', 1920),
            'height': app_config.get(f'{prefix}.height', 1080),
            'fps': app_config.get(f'{prefix}.fps', 60),
            # Audio capture settings (default True so stream has mic by default)
            'capture_audio': app_config.get(f'{prefix}.capture_audio', True),
            'audio_device': app_config.get(f'{prefix}.audio_device', ''),
            # Advanced encoding and sync
            'video_preset': app_config.get(f'{prefix}.video_preset', 'veryfast'),
            'crf': app_config.get(f'{prefix}.crf', 20),
            'av_sync_delay_ms': int(app_config.get(f'{prefix}.av_sync_delay_ms', 0)),
            'bitrate_kbps': int(app_config.get(f'{prefix}.bitrate_kbps', 0) or 0),
            'use_av_master_clock': bool(app_config.get(f'{prefix}.use_av_master_clock', True)),
            # Background Music (BGM)
            'bgm_enabled': bool(app_config.get(f'{prefix}.bgm_enabled', False)),
            'bgm_path': app_config.get(f'{prefix}.bgm_path', ''),
            'bgm_playlist': app_config.get(f'{prefix}.bgm_playlist', []) or [],
            'bgm_loop': bool(app_config.get(f'{prefix}.bgm_loop', True)),
            'bgm_volume': int(app_config.get(f'{prefix}.bgm_volume', 50)),
        }
        
        # AUTO-FIX: Ensure adequate bitrate for YouTube streaming
        if settings['platform'] == 'YouTube Live':
            min_bitrate = self._get_recommended_bitrate(settings['width'], settings['height'], settings['fps'])
            if settings['bitrate_kbps'] < min_bitrate:
                print(f"⚠️ Stream {stream_id}: Bitrate too low ({settings['bitrate_kbps']} kbps)")
                print(f"🔧 Auto-adjusting to recommended bitrate: {min_bitrate} kbps")
                settings['bitrate_kbps'] = min_bitrate
                # Save the corrected bitrate
                app_config.set(f'{prefix}.bitrate_kbps', min_bitrate)
                app_config.save_settings()
        
        return settings
    
    def _get_recommended_bitrate(self, width: int, height: int, fps: int) -> int:
        """Get recommended bitrate for YouTube streaming based on resolution and FPS."""
        # YouTube recommended bitrates (kbps)
        if height >= 2160:  # 4K
            return 35000 if fps > 30 else 20000
        elif height >= 1440:  # 1440p
            return 16000 if fps > 30 else 9000
        elif height >= 1080:  # 1080p
            return 8000 if fps > 30 else 5000
        elif height >= 720:   # 720p
            return 5000 if fps > 30 else 3000
        else:  # 480p and below
            return 2500 if fps > 30 else 1500
    
    def _apply_youtube_optimizations(self, settings: dict):
        """Apply YouTube-specific streaming optimizations to prevent buffering."""
        print("🎬 Applying YouTube streaming optimizations...")
        
        # Ensure keyframe interval is set correctly (2 seconds for YouTube)
        target_fps = settings.get('fps', 30)
        keyframe_interval = target_fps * 2  # 2 seconds
        settings['keyframe_interval'] = keyframe_interval
        
        # Use CBR (Constant Bitrate) for more stable streaming
        settings['rate_control'] = 'cbr'
        
        # Set buffer size to 2x bitrate for stable upload
        bitrate = settings.get('bitrate_kbps', 5000)
        settings['buffer_size'] = bitrate * 2
        
        # Use faster preset for real-time encoding
        if settings.get('video_preset') in ['slow', 'slower', 'veryslow']:
            settings['video_preset'] = 'fast'
            print("🔧 Changed encoding preset to 'fast' for better real-time performance")
        
        # Enable low-latency optimizations
        settings['tune'] = 'zerolatency'
        settings['threads'] = 0  # Auto-detect CPU cores
        
        print(f"✅ YouTube optimizations applied:")
        print(f"  📊 Bitrate: {bitrate} kbps")
        print(f"  🎯 Keyframe interval: {keyframe_interval} frames ({keyframe_interval/target_fps:.1f}s)")
        print(f"  ⚡ Preset: {settings.get('video_preset')}")
        print(f"  📦 Buffer size: {settings.get('buffer_size')} kb")
    
    def _show_streaming_health_info(self, stream_id: int, settings: dict):
        """Display streaming health information to help diagnose issues."""
        print(f"\n📊 Stream {stream_id} Health Check:")
        print("=" * 50)
        
        # Resolution and quality info
        width = settings.get('width', 1920)
        height = settings.get('height', 1080)
        fps = settings.get('fps', 30)
        bitrate = settings.get('bitrate_kbps', 5000)
        
        print(f"📺 Resolution: {width}x{height} @ {fps}fps")
        print(f"📊 Bitrate: {bitrate} kbps")
        
        # Check if bitrate is adequate
        recommended = self._get_recommended_bitrate(width, height, fps)
        if bitrate >= recommended:
            print(f"✅ Bitrate is adequate (recommended: {recommended} kbps)")
        else:
            print(f"⚠️ Bitrate may be too low (recommended: {recommended} kbps)")
            print(f"💡 Consider increasing bitrate in stream settings")
        
        # Platform-specific tips
        platform = settings.get('platform', 'Custom')
        print(f"🎬 Platform: {platform}")
        
        if platform == 'YouTube Live':
            print("💡 YouTube Tips:")
            print("   • Use CBR (Constant Bitrate) for stable streaming")
            print("   • Keyframe interval should be 2 seconds")
            print("   • Upload speed should be 1.5x your bitrate")
            print(f"   • Recommended upload speed: {int(bitrate * 1.5 / 1000)} Mbps")
        
        print("=" * 50)

    def _apply_frame_effects(self, frame: QImage) -> QImage:
        """Apply overlay effects to a frame for streaming output using graphics output widget's system.
        
        Uses the same overlay masking as the graphics output widget to ensure
        the camera frame appears properly positioned inside the overlay frame,
        just like it displays in PROGRAM LIVE.
        
        Args:
            frame: Input QImage frame
            
        Returns:
            QImage with overlay effects properly applied with masking
        """
        try:
            if frame is None or frame.isNull():
                return frame
            
            # Use graphics output widget's overlay system for proper masking
            if not hasattr(self, '_graphics_output') or self._graphics_output is None:
                return frame
            
            graphics_output = self._graphics_output
            
            # Check if graphics output has an active overlay with opening
            overlay_image = getattr(graphics_output, '_overlay_image', None)
            opening_norm = getattr(graphics_output, '_opening_norm', None)
            
            # No overlay active - return frame as-is
            if overlay_image is None or overlay_image.isNull() or opening_norm is None:
                return frame
            
            try:
                from PyQt6.QtGui import QPainter, QImage
                from PyQt6.QtCore import Qt, QRectF
                
                # Create output image at frame size
                output = QImage(frame.size(), QImage.Format.Format_ARGB32_Premultiplied)
                output.fill(0)  # Transparent background
                
                painter = QPainter(output)
                try:
                    size = frame.size()
                    W_w = size.width()
                    H_w = size.height()
                    
                    # Get overlay geometry (how the overlay sits on the frame)
                    geom = graphics_output._get_overlay_geom(size, overlay_image)
                    if geom is not None:
                        scaled_w, scaled_h, off_x, off_y = geom
                        nx, ny, nw, nh = opening_norm
                        
                        # Calculate opening area in output coordinates
                        video_rect = QRectF(
                            off_x + (nx * scaled_w),
                            off_y + (ny * scaled_h),
                            max(1.0, nw * scaled_w),
                            max(1.0, nh * scaled_h)
                        )
                        
                        # Draw frame to fill the opening area (like graphics output does)
                        painter.drawImage(video_rect, frame, QRectF(frame.rect()))
                        
                        # Build and apply mask to clip frame to opening area only
                        try:
                            mask = graphics_output._build_opening_mask_for_opening(size, opening_norm, overlay_image)
                            if mask and not mask.isNull():
                                painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_DestinationIn)
                                painter.drawImage(0, 0, mask)
                                painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
                        except Exception:
                            pass  # Mask application optional
                        
                        # Draw overlay frame on top
                        scaled_overlay = overlay_image.scaled(
                            size,
                            Qt.AspectRatioMode.KeepAspectRatio,
                            Qt.TransformationMode.SmoothTransformation
                        )
                        x = (W_w - scaled_overlay.width()) // 2
                        y = (H_w - scaled_overlay.height()) // 2
                        painter.drawImage(x, y, scaled_overlay)
                        
                        return output
                
                finally:
                    painter.end()
                
                return frame
            except Exception as e:
                # Error using graphics output methods - fallback to simple overlay
                if not getattr(self, '_effect_error_logged', False):
                    print(f"[Stream Effects] Graphic overlay error: {e}")
                    self._effect_error_logged = True
                return frame
        except Exception:
            return frame

    def _provide_stream_frame(self, size: QSize, direct_passthrough: bool = False) -> QImage:
        """Provide frame for streaming output using pre-scaled cache.
        
        OPTIMIZATION: Check pre-scaled cache first (fast path on background thread).
        Only scale if cache miss. Pre-scaling happens on main thread when frames arrive.
        
        Args:
            size: Requested output size
            direct_passthrough: If True, bypass effects and return raw camera frame
        """
        # Track FPS throttling per resolution
        if not hasattr(self, '_frame_provider_throttle'):
            self._frame_provider_throttle = {}
        
        import time as _throttle_time
        _now = _throttle_time.perf_counter()
        _size_key = (size.width(), size.height())
        _last_time = self._frame_provider_throttle.get(_size_key, 0.0)
        
        # Throttle by resolution (camera hardware limits)
        # FIXED: Don't gate frame delivery by resolution - render threads pace themselves
        # Use measured input FPS for diagnostics only
        active_input = None
        if hasattr(self, 'current_output') and self.current_output:
            source_type, source_id = self.current_output
            if source_type == 'input':
                active_input = source_id
        
        if active_input is not None and hasattr(self, '_input_fps_counters'):
            measured_fps = self._input_fps_counters.get(active_input, {}).get('last_fps', 0.0)
            if measured_fps > 0:
                _diagnostic_fps = int(measured_fps)
            else:
                _diagnostic_fps = 30 if (size.width() >= 1920 and size.height() >= 1080) else 60
        else:
            _diagnostic_fps = 30 if (size.width() >= 1920 and size.height() >= 1080) else 60
        
        # DEBUG: Log occasionally
        if not hasattr(self, '_fp_call_count'):
            self._fp_call_count = 0
        self._fp_call_count += 1
        if self._fp_call_count <= 5 or self._fp_call_count % 60 == 0:
            print(f"🎬 Frame provider: call #{self._fp_call_count}, active_input={active_input}, size={size.width()}x{size.height()}")
        
        try:
            def _ensure_exact_size(img: QImage) -> QImage:
                """Ensure image is exactly the requested size, with fast path for exact match."""
                try:
                    if img is None or img.isNull():
                        out = QImage(size, QImage.Format.Format_RGBA8888)
                        out.fill(0)
                        return out
                    # FAST PATH: If already exact size, return as-is
                    if img.size() == size and img.format() == QImage.Format.Format_RGBA8888:
                        return img
                    # Size mismatch - need to create exact size
                    from PyQt6.QtGui import QPainter
                    out = QImage(size, QImage.Format.Format_RGBA8888)
                    out.fill(0)
                    painter = QPainter(out)
                    try:
                        # If image is close to target, center it without scaling
                        if img.width() > size.width() * 0.9 and img.height() > size.height() * 0.9:
                            x = (size.width() - img.width()) // 2
                            y = (size.height() - img.height()) // 2
                            painter.drawImage(x, y, img)
                        else:
                            # Image is significantly different size - scale it
                            scaled = img.scaled(
                                size,
                                Qt.AspectRatioMode.KeepAspectRatio,
                                Qt.TransformationMode.FastTransformation
                            )
                            x = (size.width() - scaled.width()) // 2
                            y = (size.height() - scaled.height()) // 2
                            painter.drawImage(x, y, scaled)
                    finally:
                        painter.end()
                    return out
                except Exception:
                    out = QImage(size, QImage.Format.Format_RGBA8888)
                    out.fill(0)
                    return out

            # STEP 1: Determine active input (the one being displayed/streamed)
            active_input = None
            if hasattr(self, 'current_output') and self.current_output:
                source_type, source_id = self.current_output
                if source_type == 'input':
                    active_input = source_id
            
            # Default to input 1 if no input is selected
            if active_input is None:
                active_input = 1
                if self._fp_call_count <= 10:
                    print(f"  -> No input selected, defaulting to Input-1")
            
            if active_input is None:
                if self._fp_call_count <= 10:
                    print(f"  -> No active input (current_output={getattr(self, 'current_output', None)})")
                black = QImage(size, QImage.Format.Format_RGBA8888)
                black.fill(0)
                return black
            
            # STEP 2: OBS-STYLE — Read from ring buffer first (decoupled capture/render)
            if hasattr(self, '_input_frame_buffers') and active_input in self._input_frame_buffers:
                ring_buffer = self._input_frame_buffers[active_input]
                img = ring_buffer.get_latest()
                if img is not None and not img.isNull():
                    # Fast path: return cached scaled version if available
                    cache_key = (active_input, size.width(), size.height())
                    scaled_cache = getattr(self, 'last_input_image_scaled', {})
                    cached_scaled = scaled_cache.get(cache_key)
                    if cached_scaled is not None and not cached_scaled.isNull():
                        if self._fp_call_count <= 10:
                            print(f"  -> RING BUFFER + CACHE HIT for {size.width()}x{size.height()}")
                        return cached_scaled.copy()
                    
                    # Scale if needed
                    if img.size() != size:
                        if self._fp_call_count <= 3:
                            print(f"  -> Ring buffer hit, scaling from {img.width()}x{img.height()} to {size.width()}x{size.height()}")
                        img = img.scaled(
                            size,
                            Qt.AspectRatioMode.KeepAspectRatio,
                            Qt.TransformationMode.FastTransformation
                        )
                        # Cache for future calls
                        if not hasattr(self, 'last_input_image_scaled'):
                            self.last_input_image_scaled = {}
                        self.last_input_image_scaled[cache_key] = img.copy()
                    if self._fp_call_count <= 10:
                        print(f"  -> RING BUFFER HIT for Input-{active_input}")
                    return img.copy()
            
            # STEP 3: FALLBACK — Check legacy scaled cache
            cache_key = (active_input, size.width(), size.height())
            scaled_cache = getattr(self, 'last_input_image_scaled', {})
            cached_scaled = scaled_cache.get(cache_key)
            if cached_scaled is not None and not cached_scaled.isNull():
                if self._fp_call_count <= 10:
                    print(f"  -> LEGACY CACHE HIT for {size.width()}x{size.height()}")
                return cached_scaled.copy()
            
            if self._fp_call_count <= 10:
                print(f"  -> CACHE MISS for {size.width()}x{size.height()}, cache has: {list(scaled_cache.keys())}")
            
            # STEP 4: FALLBACK — Get from legacy full-res cache and scale
            full_res_cache = getattr(self, 'last_input_image', {})
            img = full_res_cache.get(active_input)
            if img is not None and not img.isNull():
                # Fast scale if needed
                if img.size() != size:
                    if self._fp_call_count <= 3:
                        print(f"  -> Legacy cache miss, scaled from {img.width()}x{img.height()} to {size.width()}x{size.height()}")
                    img = img.scaled(
                        size,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.FastTransformation
                    )
                # Cache and return
                if not hasattr(self, 'last_input_image_scaled'):
                    self.last_input_image_scaled = {}
                self.last_input_image_scaled[cache_key] = img.copy()
                return img.copy()
            
            # STEP 4: Fallback — try getting last frame from graphics output
            if hasattr(self, '_graphics_output') and self._graphics_output is not None:
                last_frame = getattr(self._graphics_output, '_last_frame', None)
                if last_frame is not None and not last_frame.isNull():
                    if last_frame.size() != size:
                        last_frame = last_frame.scaled(
                            size,
                            Qt.AspectRatioMode.KeepAspectRatio,
                            Qt.TransformationMode.FastTransformation
                        )
                    if self._fp_call_count <= 3:
                        print(f"  -> Used fallback _last_frame from graphics output")
                    # ✅ Apply overlay effects for streaming before returning
                    last_frame = self._apply_frame_effects(last_frame)
                    last_frame = _ensure_exact_size(last_frame)
                    return last_frame
            
            # STEP 5: Return black frame if nothing available
            if self._fp_call_count <= 3:
                print(f"  -> No active frame, returning black")
            black = QImage(size, QImage.Format.Format_RGBA8888)
            black.fill(0)
            return black
            
        except Exception as e:
            # === DIAGNOSTIC: Frame provider error ===
            _diag_error("Frame provider failed — stream will drop this frame",
                       e,
                       f"File: main.py → _provide_stream_frame() | "
                       f"Active input: {active_input if 'active_input' in locals() else 'unknown'} | "
                       f"Requested size: {size.width()}x{size.height()} | "
                       f"Frame #{self._fp_call_count}")
            # Return black frame on error
            black = QImage(size, QImage.Format.Format_RGBA8888)
            black.fill(0)
            return black
    
    def toggle_audio_monitor(self):
        """Toggle audio monitor mute"""
        self.audio_monitor_muted = not self.audio_monitor_muted
        if self.audio_monitor_muted:
            print("Muting audio monitor...")
        else:
            print("Unmuting audio monitor...")
        # Add your audio monitor logic here

    def action_clear_visuals(self):
        """Clear overlay/effects and hide any text overlay (non-destructive to state)."""
        try:
            if hasattr(self, '_graphics_output') and self._graphics_output is not None:
                self._graphics_output.clear_overlay()
                # Hide text overlay immediately
                self._graphics_output.set_text_overlay({'visible': False, 'text': ''})
            # Sync mini UI if present
            try:
                if hasattr(self, 'textOverlayMini') and self.textOverlayMini:
                    self.textOverlayMini.props_ref.apply_props({'visible': False, 'text': ''}, emit=True)
                    if hasattr(self.textOverlayMini, 'chk_visible'):
                        self.textOverlayMini.chk_visible.setChecked(False)
            except Exception:
                pass
            print("Visuals cleared (overlay and text hidden)")
        except Exception as e:
            print(f"Error clearing visuals: {e}")

    def action_toggle_passthrough(self, enabled: bool):
        """Toggle direct passthrough mode (bypass effects/overlays in rendering path)."""
        try:
            self.passthrough_enabled = bool(enabled)
            # Update menu check if exists
            try:
                if hasattr(self, '_tools_menu_act_pass'):
                    self._tools_menu_act_pass.setChecked(self.passthrough_enabled)
            except Exception:
                pass
            # Force preview refresh to reflect change immediately
            try:
                self.refresh_output_preview()
            except Exception:
                pass
            print(f"Direct Passthrough {'enabled' if self.passthrough_enabled else 'disabled'}")
        except Exception as e:
            print(f"Error toggling passthrough: {e}")

    def _apply_controls_lock_state(self):
        """Enable/disable key interactive controls based on controls_locked."""
        try:
            lock = bool(getattr(self, 'controls_locked', False))
            widgets = []
            # Recording controls
            for n in ('settingsRecordButton','recordRedCircle','playButton','captureButton'):
                if hasattr(self, n): widgets.append(getattr(self, n))
            # Stream controls
            for n in ('stream1SettingsBtn','stream1AudioBtn','stream2SettingsBtn','stream2AudioBtn'):
                if hasattr(self, n): widgets.append(getattr(self, n))
            # Input audio and settings
            for n in ('input1AudioButton','input2AudioButton','input3AudioButton','input1SettingsButton','input2SettingsButton','input3SettingsButton'):
                if hasattr(self, n): widgets.append(getattr(self, n))
            # Media audio/settings/play
            for n in ('media1AudioButton','media2AudioButton','media3AudioButton','media1SettingsButton','media2SettingsButton','media3SettingsButton','pushButton_19','pushButton_20','pushButton_21'):
                if hasattr(self, n): widgets.append(getattr(self, n))
            # Global audio mute button
            if hasattr(self, 'audioTopButton'): widgets.append(self.audioTopButton)
            # Tools button itself remains enabled to unlock
            for w in widgets:
                try:
                    w.setEnabled(not lock)
                except Exception:
                    pass
        except Exception:
            pass

    def action_toggle_controls_lock(self, enabled: bool):
        """Toggle UI lock to prevent accidental clicks on critical controls."""
        try:
            self.controls_locked = bool(enabled)
            # Update menu check if exists
            try:
                if hasattr(self, '_tools_menu_act_lock'):
                    self._tools_menu_act_lock.setChecked(self.controls_locked)
            except Exception:
                pass
            self._apply_controls_lock_state()
            print(f"Controls {'locked' if self.controls_locked else 'unlocked'}")
        except Exception as e:
            print(f"Error toggling controls lock: {e}")
    
    def get_renderer_info(self) -> dict:
        """Get information about the current renderer"""
        info = {
            'using_new_renderer': _USE_NEW_RENDERER,
            'renderer_type': 'Unknown',
            'gpu_accelerated': False,
            'performance': self._renderer_stats.copy()
        }
        
        if hasattr(self, '_graphics_output') and self._graphics_output:
            if _USE_NEW_RENDERER and hasattr(self._graphics_output, 'get_performance_info'):
                info.update(self._graphics_output.get_performance_info())
            else:
                info['renderer_type'] = 'CPU (Legacy)'
        
        return info
    
    def on_output_size_changed(self, text):
        """Handle output size change"""
        print(f"Output size changed to: {text}")
        try:
            if not hasattr(self, 'outputSizeComboBox'):
                return
            idx = self.outputSizeComboBox.currentIndex()
            if idx < 0:
                return
            data = self.outputSizeComboBox.itemData(idx)
            if not isinstance(data, dict):
                return
            w = int(data.get('width', 1920))
            h = int(data.get('height', 1080))
            fps = int(data.get('fps', 60))
            label = data.get('label', text)
            
            # Update FPS combo box to match the profile's FPS
            if hasattr(self, 'fpsComboBox'):
                self.fpsComboBox.blockSignals(True)
                if fps == 30:
                    self.fpsComboBox.setCurrentText("30 FPS")
                else:
                    self.fpsComboBox.setCurrentText("60 FPS")
                self.fpsComboBox.blockSignals(False)
            
            self._apply_output_profile(w, h, fps, label)
        except Exception as e:
            print(f"Output size apply error: {e}")

    def _apply_output_profile(self, width: int, height: int, fps: int, label: str):
        """Apply output profile to preview and running mirror; persist to config."""
        try:
            # Persist selection
            app_config.set('ui.output_width', int(width))
            app_config.set('ui.output_height', int(height))
            app_config.set('ui.preview_fps', int(fps))
            app_config.set('ui.output_profile_label', str(label or ''))
            app_config.save_settings()
        except Exception:
            pass
        # Update preview timer FPS
        try:
            if hasattr(self, '_graphics_output') and self._graphics_output is not None:
                self._graphics_output.set_target_fps(int(fps))
                # Compose preview at selected resolution for fidelity
                from PyQt6.QtCore import QSize as _QSize
                self._graphics_output.set_preview_render_size(_QSize(int(width), int(height)))
                # Force an immediate refresh so both video and text update right away
                try:
                    self.refresh_output_preview()
                except Exception:
                    pass
        except Exception:
            pass
        # Live-update external display mirror if running
        try:
            if hasattr(self, 'mirror_controller') and self.mirror_controller and self.mirror_controller.is_running():
                # For mirror, prefer full-screen maximize and matching FPS to avoid pixelation
                self.mirror_controller.update({'width': int(width), 'height': int(height), 'fps': int(fps), 'maximize': True})
        except Exception:
            pass
        print(f"Applied output profile: {label} -> {width}x{height} @ {fps}fps")

    def _populate_output_size_combo(self):
        """Populate Output Size combo with video standard, resolution, and fps options."""
        if not hasattr(self, 'outputSizeComboBox'):
            return
        cb = self.outputSizeComboBox
        cb.blockSignals(True)
        try:
            cb.clear()
            # Only quality presets
            profiles = [
                { 'label': '144p',  'width': 256, 'height': 144,  'fps': 60 },
                { 'label': '240p',  'width': 426, 'height': 240,  'fps': 60 },
                { 'label': '360p',  'width': 640, 'height': 360,  'fps': 60 },
                { 'label': '480p',  'width': 854, 'height': 480,  'fps': 60 },
                { 'label': '720p',  'width': 1280,'height': 720,  'fps': 60 },
                { 'label': '1080p', 'width': 1920,'height': 1080, 'fps': 60 },
            ]
            # Restore last selection if available
            last_label = app_config.get('ui.output_profile_label', '') or ''
            last_w = int(app_config.get('ui.output_width', 1920))
            last_h = int(app_config.get('ui.output_height', 1080))
            last_fps = int(app_config.get('ui.preview_fps', 60))
            select_index = -1
            for i, p in enumerate(profiles):
                label = p['label']
                cb.addItem(label, { **p, 'label': label })
                if select_index == -1:
                    if last_label and label == last_label:
                        select_index = i
                    elif (p['width'], p['height'], p['fps']) == (last_w, last_h, last_fps):
                        select_index = i
            if select_index >= 0:
                cb.setCurrentIndex(select_index)
                data = cb.itemData(select_index)
                self._apply_output_profile(int(data['width']), int(data['height']), int(data['fps']), data['label'])
            else:
                # Default to 1080p
                idx = next((i for i,p in enumerate(profiles) if p['label'] == '1080p'), len(profiles) - 1)
                cb.setCurrentIndex(idx)
                data = cb.itemData(idx)
                self._apply_output_profile(int(data['width']), int(data['height']), int(data['fps']), data['label'])
        finally:
            cb.blockSignals(False)
    
    def _safe_set_fps_combo(self, fps_value: int):
        """Safely update FPS combo box (avoids 'deleted' errors when dialog closes)."""
        try:
            if hasattr(self, 'fpsComboBox') and self.fpsComboBox is not None:
                try:
                    self.fpsComboBox.blockSignals(True)
                    self.fpsComboBox.setCurrentText(f"{int(fps_value)} FPS")
                finally:
                    try:
                        self.fpsComboBox.blockSignals(False)
                    except Exception:
                        pass
        except Exception:
            pass
    
    def on_fps_changed(self, text):
        """Handle FPS change with global FPS controller integration"""
        print(f"FPS changed to: {text}")
        try:
            # Extract FPS value from text (e.g., "30 FPS" -> 30)
            fps_value = 60  # default
            if "30" in text:
                fps_value = 30
            elif "60" in text:
                fps_value = 60
            
            # Update global FPS controller if available
            if FPS_CONTROLLER_AVAILABLE:
                set_global_fps(fps_value)
                print(f"Global FPS controller updated to {fps_value} FPS")
            
            # Update configuration
            app_config.set('ui.preview_fps', fps_value)
            app_config.save_settings()
            
            # Update current output profile if one is selected
            if hasattr(self, 'outputSizeComboBox'):
                idx = self.outputSizeComboBox.currentIndex()
                if idx >= 0:
                    data = self.outputSizeComboBox.itemData(idx)
                    if isinstance(data, dict):
                        width = int(data.get('width', 1920))
                        height = int(data.get('height', 1080))
                        label = data.get('label', 'Custom')
                        self._apply_output_profile(width, height, fps_value, label)
            
            # Update streaming manager if available
            if FPS_CONTROLLER_AVAILABLE:
                streaming_manager = get_streaming_manager()
                # Restart any active streams with new FPS
                active_streams = streaming_manager.get_active_streams()
                for stream_url in active_streams:
                    print(f"Restarting stream {stream_url} with new FPS: {fps_value}")
            
            print(f"FPS updated to: {fps_value}")
        except Exception as e:
            print(f"FPS change error: {e}")

    def on_audio_output_changed(self, text):
        """Handle audio output change"""
        print(f"Audio output changed to: {text}")
        try:
            from PyQt6.QtMultimedia import QMediaDevices
            # Find matching output device by description
            target = None
            for dev in QMediaDevices.audioOutputs():
                if dev.description() == text:
                    target = dev
                    break
            if target is None:
                print("Selected audio output device not found; keeping current devices.")
                return
            # Apply to media audio outputs
            if hasattr(self, 'media_audio_outputs'):
                for i in (1, 2, 3):
                    ao = self.media_audio_outputs.get(i)
                    if ao:
                        try:
                            ao.setDevice(target)
                        except Exception:
                            pass
            # Recreate input audio sinks with the new device for monitoring
            if hasattr(self, 'input_audio_sinks') and hasattr(self, 'input_audio_sources'):
                active_inputs = []
                for i, sink in list(self.input_audio_sinks.items()):
                    # Determine if this input should remain active
                    is_active = getattr(self, f"input{i}_audio_muted", True) is False and getattr(self, 'current_output', (None,None)) == ('input', i)
                    # Stop existing
                    try:
                        self._stop_input_audio(i)
                    except Exception:
                        pass
                    if is_active:
                        # Recreate with new sink device
                        try:
                            # Ensure structures exist
                            from PyQt6.QtMultimedia import QAudioSource, QAudioSink, QMediaDevices
                            input_dev = QMediaDevices.defaultAudioInput()
                            source = QAudioSource(input_dev)
                            sink = QAudioSink(target)
                            self.input_audio_sources[i] = source
                            self.input_audio_sinks[i] = sink
                            out_dev = sink.start()
                            in_dev = source.start()
                            from PyQt6.QtCore import QTimer
                            t = QTimer(self)
                            t.setInterval(10)
                            def pump():
                                try:
                                    data = in_dev.read(4096)
                                    if data:
                                        out_dev.write(data)
                                except Exception:
                                    pass
                            t.timeout.connect(pump)
                            t.start()
                            if not hasattr(self, 'input_audio_timers'):
                                self.input_audio_timers = {}
                            self.input_audio_timers[i] = t
                        except Exception:
                            pass
        except Exception as e:
            print(f"Error applying audio output device: {e}")

    def _populate_audio_outputs_combo(self):
        """Populate the audioOutputComboBox with system output devices, selecting default."""
        if not hasattr(self, 'audioOutputComboBox'):
            return
        try:
            from PyQt6.QtMultimedia import QMediaDevices
            combo = self.audioOutputComboBox
            combo.blockSignals(True)
            combo.clear()
            default_desc = QMediaDevices.defaultAudioOutput().description() if QMediaDevices.defaultAudioOutput() else ''
            for dev in QMediaDevices.audioOutputs():
                combo.addItem(dev.description())
            # Select default device if present
            if default_desc:
                idx = combo.findText(default_desc)
                if idx >= 0:
                    combo.setCurrentIndex(idx)
            combo.blockSignals(False)
        except Exception as e:
            print(f"Error populating audio outputs: {e}")
    
    def update_record_status(self, status_text, color):
        """Update the record status text and color"""
        try:
            # Helper to check if a Qt widget is still alive
            def _alive(w):
                try:
                    if w is None:
                        return False
                    # Accessing property safely will throw if deleted
                    _ = w.objectName()
                    return True
                except Exception:
                    return False

            lbl = getattr(self, 'recordStatusText', None)
            if _alive(lbl):
                lbl.setText(status_text)
                lbl.setStyleSheet(f"color: {color};")
            
            # Sync workspace record button
            btn = getattr(self, 'record_action_btn', None)
            if _alive(btn):
                is_recording = False
                try:
                    rc = getattr(self, 'recorder_controller', None)
                    if rc is not None and hasattr(rc, 'is_running'):
                        is_recording = bool(rc.is_running())
                    else:
                        is_recording = bool(getattr(self, 'recording', False))
                except Exception:
                    is_recording = bool(getattr(self, 'recording', False))
                btn.blockSignals(True)
                btn.setChecked(is_recording)
                if is_recording:
                    btn.setText("STOP RECORDING")
                    btn.setStyleSheet("""
                        QPushButton {
                            background-color: transparent;
                            color: #ff4444;
                            font-size: 18px;
                            font-weight: bold;
                            border-radius: 8px;
                            border: 2px solid #ff4444;
                        }
                        QPushButton:hover { background-color: rgba(255, 68, 68, 0.1); }
                    """)
                else:
                    btn.setText("START RECORDING")
                    btn.setStyleSheet("""
                        QPushButton {
                            background-color: #ff3b30;
                            color: white;
                            font-size: 18px;
                            font-weight: bold;
                            border-radius: 8px;
                            border: 2px solid #ff5b50;
                        }
                        QPushButton:hover { background-color: #ff5b50; }
                    """)
                btn.blockSignals(False)

            # Sync main round record button icon/style
            main_btn = getattr(self, 'recordRedCircle', None)
            if _alive(main_btn):
                try:
                    rc = getattr(self, 'recorder_controller', None)
                    is_recording = bool(rc.is_running()) if rc is not None and hasattr(rc, 'is_running') else bool(getattr(self, 'recording', False))
                except Exception:
                    is_recording = bool(getattr(self, 'recording', False))
                try:
                    if is_recording:
                        main_btn.setIcon(self.get_icon("Stop.png"))
                        main_btn.setStyleSheet("background-color: #ff0000; border-radius: 15px;")
                    else:
                        main_btn.setIcon(self.get_icon("Record.png"))
                        main_btn.setStyleSheet("background-color: #404040; border-radius: 15px;")
                except Exception:
                    pass
                
             # Also update Status Bar
            status_lbl = getattr(self, 'status_rec', None)
            if _alive(status_lbl):
                status_lbl.setText(status_text)
                status_lbl.setStyleSheet(f"color: {color}; font-weight: bold;")
                 
        except AttributeError:
            print(f"Record status update: {status_text}")
    
    def _on_record_toggled_workspace(self, checked):
        """Handle toggle from workspace button"""
        # We just trigger the main toggle logic
        # The button visual state will be fixed by update_record_status if the action succeeds or fails
        self.toggle_recording()

    def _on_stream_status_changed(self, status: str, stream_id: int | None = None):
        """Handle StreamController status updates and reflect them in the UI."""
        try:
            st = (status or '').lower()
            if 'started' in st:
                self.update_record_status("Streaming", "#00aa00")
            elif 'reconnecting' in st:
                self.update_record_status("Reconnecting...", "#ffaa00")
            elif 'error' in st:
                self.update_record_status("Stream Error", "#ff4444")
            else:
                # Stopped or unknown
                self.update_record_status("Ready", "#777777")
        except Exception as e:
            print(f"Status UI error: {e}")

        # Stream workspace footer + log
        try:
            sid = int(stream_id) if stream_id is not None else None
        except Exception:
            sid = None
        try:
            if sid is not None and hasattr(self, '_update_stream_footer'):
                self._update_stream_footer(sid, str(status or ''))
        except Exception:
            pass
    
    # Input panel methods
    def open_input1_settings(self):
        """Open Input-1 settings dialog"""
        print("Opening Input-1 settings...")
        # Add your input1 settings dialog here
    
    def toggle_input1_audio(self):
        """Toggle Input-1 audio mute"""
        self.input1_audio_muted = not self.input1_audio_muted
        if self.input1_audio_muted:
            print("Muting Input-1 audio...")
            if hasattr(self, 'input1AudioButton'):
                self.input1AudioButton.setIcon(self.get_icon("Mute.png"))
        else:
            print("Unmuting Input-1 audio...")
            if hasattr(self, 'input1AudioButton'):
                self.input1AudioButton.setIcon(self.get_icon("Volume.png"))
        # Add your input1 audio logic here
    
    def open_input2_settings(self):
        """Open Input-2 settings dialog"""
        print("Opening Input-2 settings...")
        # Add your input2 settings dialog here
    
    def toggle_input2_audio(self):
        """Toggle Input-2 audio mute"""
        self.input2_audio_muted = not self.input2_audio_muted
        if self.input2_audio_muted:
            print("Muting Input-2 audio...")
            if hasattr(self, 'input2AudioButton'):
                self.input2AudioButton.setIcon(self.get_icon("Mute.png"))
        else:
            print("Unmuting Input-2 audio...")
            if hasattr(self, 'input2AudioButton'):
                self.input2AudioButton.setIcon(self.get_icon("Volume.png"))
        # Add your input2 audio logic here
    
    def open_input3_settings(self):
        """Open Input 3 settings dialog"""
        print("Opening Input 3 settings...")
        # TODO: Implement input settings dialog
    
    def toggle_input3_audio(self):
        """Toggle input 3 audio mute state"""
        self.input3_audio_muted = not self.input3_audio_muted
        icon_name = "Mute.png" if self.input3_audio_muted else "Volume.png"
        if hasattr(self, 'input3AudioButton'):
            self.input3AudioButton.setIcon(self.get_icon(icon_name))
        print(f"Input 3 audio {'muted' if self.input3_audio_muted else 'unmuted'}")
    
    def open_media1_settings(self):
        """Open Media 1 settings dialog"""
        print("Opening Media 1 settings...")
        # TODO: Implement media settings dialog
    
    def toggle_media1_audio(self):
        """Toggle media 1 audio mute state"""
        self.media1_audio_muted = not self.media1_audio_muted
        icon_name = "Mute.png" if self.media1_audio_muted else "Volume.png"
        if hasattr(self, 'media1AudioButton'):
            self.media1AudioButton.setIcon(self.get_icon(icon_name))
        print(f"Media 1 audio {'muted' if self.media1_audio_muted else 'unmuted'}")
    
    def open_media2_settings(self):
        """Open Media 2 settings dialog"""
        print("Opening Media 2 settings...")
        # TODO: Implement media settings dialog
    
    def toggle_media2_audio(self):
        """Toggle media 2 audio mute state"""
        self.media2_audio_muted = not self.media2_audio_muted
        icon_name = "Mute.png" if self.media2_audio_muted else "Volume.png"
        if hasattr(self, 'media2AudioButton'):
            self.media2AudioButton.setIcon(self.get_icon(icon_name))
        print(f"Media 2 audio {'muted' if self.media2_audio_muted else 'unmuted'}")
    
    def open_media3_settings(self):
        """Open Media 3 settings dialog"""
        print("Opening Media 3 settings...")
        # TODO: Implement media settings dialog
    
    def toggle_media3_audio(self):
        """Toggle media 3 audio mute state"""
        self.media3_audio_muted = not self.media3_audio_muted
        icon_name = "Mute.png" if self.media3_audio_muted else "Volume.png"
        if hasattr(self, 'media3AudioButton'):
            self.media3AudioButton.setIcon(self.get_icon(icon_name))
        print(f"Media 3 audio {'muted' if self.media3_audio_muted else 'unmuted'}")

    def set_source_1A(self, source_name):
        """Set source for 1A output"""
        self.current_1A_source = source_name
        print(f"1A source set to: {source_name}")
        # TODO: Implement actual source switching logic
    
    def set_source_2B(self, source_name):
        """Set source for 2B output"""
        self.current_2B_source = source_name
        print(f"2B source set to: {source_name}")
        # TODO: Implement actual source switching logic
    
    def apply_transition(self, transition_id):
        """Apply transition effect"""
        print(f"Applying transition {transition_id}")
        # TODO: Implement transition effects
        
    # ===== Enhanced Dialog Methods =====
    
    def show_camera_selection_dialog(self, input_number: int):
        """Show enhanced camera settings dialog with real-time updates."""
        try:
            print(f"📹 Opening Input {input_number} settings dialog...")
            from input_settings_dialog import InputSettingsDialog
            from camera_processor import camera_processors
            
            dialog = InputSettingsDialog(self, input_number)
            print(f"✅ Input {input_number} settings dialog created successfully")
            
            # Load existing settings if any
            current_settings = camera_processors[input_number].get_current_settings()
            if current_settings:
                dialog.load_current_settings(current_settings)
                print(f"📝 Loaded existing settings for Input {input_number}")
            
            # Connect real-time updates and camera selection
            dialog.settingsChanged.connect(lambda settings: self._on_camera_settings_changed(input_number, settings))
            dialog.camera_combo.currentIndexChanged.connect(lambda: self._on_camera_selected_in_dialog(input_number, dialog))
            
            # Show dialog (no need to check result since updates are real-time)
            result = dialog.exec()
            print(f"📝 Input {input_number} settings dialog closed with result: {result}")
            
        except Exception as e:
            print(f"❌ Error opening Input {input_number} settings dialog: {e}")
            import traceback
            traceback.print_exc()
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Error", f"Failed to open camera settings: {str(e)}")
    
    def _on_camera_settings_changed(self, input_number: int, settings: dict):
        """Handle real-time camera settings changes."""
        try:
            if not isinstance(settings, dict):
                return
            from camera_processor import camera_processors
            
            # Apply settings to processor
            camera_processors[input_number].update_settings(settings)
            
            # Check if resolution changed (requires camera restart with new format)
            try:
                new_res = settings.get('resolution')
                if new_res and isinstance(new_res, (tuple, list)) and len(new_res) >= 2:
                    new_res = (int(new_res[0]), int(new_res[1]))
                    prev_res_dict = getattr(self, '_prev_input_resolution', {})
                    prev_res = prev_res_dict.get(input_number)
                    
                    if prev_res != new_res:
                        print(f"[CAMERA] Resolution changed from {prev_res} to {new_res} for Input {input_number}")
                        prev_res_dict[input_number] = new_res
                        
                        # Restart camera with new format
                        if hasattr(self, 'qt_cameras') and input_number in self.qt_cameras:
                            cam_obj = self.qt_cameras[input_number]
                            if cam_obj and hasattr(cam_obj, 'cameraDevice'):
                                dev = cam_obj.cameraDevice()
                                # Reconstruct camera_info with new resolution and current settings
                                fps_val = settings.get('fps', 60)
                                try:
                                    fps_val = int(float(fps_val))
                                except (TypeError, ValueError):
                                    fps_val = 60
                                camera_info = {
                                    'name': str(cam_obj.cameraDevice().description() if hasattr(dev, 'description') else ''),
                                    'index': self.input_camera_indices.get(input_number, 0),
                                    'device': dev,
                                    'fps': fps_val,
                                    'resolution': new_res,
                                }
                                print(f"[CAMERA] Restarting camera for Input {input_number} with resolution {new_res[0]}x{new_res[1]}")
                                self.start_camera_capture(camera_info, input_number)
            except Exception as e:
                print(f"[CAMERA] Warning: Could not restart camera on resolution change: {e}")
            
            # Force refresh of current frame if this input is active
            if hasattr(self, 'current_output') and self.current_output == ('input', input_number):
                if input_number in getattr(self, 'last_input_image', {}):
                    # Re-process and display the last frame with new settings
                    original_img = self.last_input_image[input_number]
                    if camera_processors[input_number].is_enabled():
                        processed_img = camera_processors[input_number].process_frame(original_img)
                        if processed_img:
                            self._set_output_image(processed_img)

            # Always apply FPS from dialog to output pipeline (honor user selection: 30, 60, etc.)
            try:
                fps_val = settings.get('fps')
                if fps_val is not None:
                    fps_value = int(float(fps_val))
                    if fps_value > 0:
                        app_config.set('ui.preview_fps', fps_value)
                        if hasattr(self, '_graphics_output') and self._graphics_output is not None:
                            self._graphics_output.set_target_fps(fps_value)
                        if FPS_CONTROLLER_AVAILABLE:
                            from fps_controller import set_global_fps
                            set_global_fps(fps_value)
                        # Defer fpsComboBox update to avoid "deleted" errors when dialog is closing
                        QTimer.singleShot(50, lambda f=fps_value: self._safe_set_fps_combo(f))
            except (TypeError, ValueError, Exception):
                pass

            # If dialog requested auto output profile, apply detected resolution/FPS and set dropdown to 'Auto'
            if settings.get('output_profile_auto'):
                try:
                    res = settings.get('resolution') or (1920, 1080)
                    w, h = int(res[0]), int(res[1])
                    fps_value = int(settings.get('fps') or 60)
                    # Ensure output size combo exists
                    if hasattr(self, 'outputSizeComboBox'):
                        cb = self.outputSizeComboBox
                        # Insert or update an 'Auto' item at index 0
                        auto_payload = { 'label': 'Auto', 'width': w, 'height': h, 'fps': fps_value }
                        found_auto = False
                        for i in range(cb.count()):
                            data = cb.itemData(i)
                            if isinstance(data, dict) and data.get('label') == 'Auto':
                                cb.setItemData(i, auto_payload)
                                cb.setCurrentIndex(i)
                                found_auto = True
                                break
                        if not found_auto:
                            cb.insertItem(0, 'Auto', auto_payload)
                            cb.setCurrentIndex(0)
                        # Reflect FPS in fpsComboBox if present
                        if hasattr(self, 'fpsComboBox'):
                            try:
                                self.fpsComboBox.blockSignals(True)
                                self.fpsComboBox.setCurrentText(f"{fps_value} FPS")
                            finally:
                                self.fpsComboBox.blockSignals(False)
                        # Sync global FPS controller as well so frame pacing matches camera
                        try:
                            if FPS_CONTROLLER_AVAILABLE:
                                set_global_fps(int(fps_value))
                        except Exception:
                            pass
                        # Apply profile to preview and mirror
                        self._apply_output_profile(w, h, fps_value, 'Auto')
                except Exception:
                    pass
            
            print(f"🎨 Real-time camera settings applied to Input {input_number}")
            
        except Exception as e:
            print(f"Error applying camera settings: {e}")
    
    def _on_camera_selected_in_dialog(self, input_number: int, dialog):
        """Handle camera selection in dialog."""
        try:
            if not dialog:
                return
            camera_device = dialog.camera_combo.currentData()
            if not camera_device:  # "Select Camera..." selected
                return
            # Map combo index to device index
            combo_index = dialog.camera_combo.currentIndex()
            device_index = max(0, combo_index - 1)
            # Safely get FPS/resolution from dialog (may fail if widgets destroyed)
            fps_val, res_val = 60, (1920, 1080)
            try:
                settings = dialog.get_settings() if hasattr(dialog, 'get_settings') else {}
                if isinstance(settings, dict):
                    f = settings.get('fps')
                    fps_val = int(float(f)) if f is not None else 60
                    r = settings.get('resolution')
                    res_val = r if isinstance(r, (tuple, list)) and len(r) >= 2 else (1920, 1080)
            except Exception:
                pass
            camera_info = {
                'name': str(getattr(dialog.camera_combo, 'currentText', lambda: '')() or ''),
                'index': device_index,
                'device': camera_device,
                'fps': fps_val,
                'resolution': res_val,
            }
            self.start_camera_capture(camera_info, input_number)
            print(f"✅ Started camera capture for input {input_number}: {camera_info['name']} @ {camera_info['fps']}fps")
        except Exception as e:
            print(f"❌ Failed to start camera capture: {e}")
    
    def show_media_selection_dialog(self, media_number: int):
        """Show enhanced media file selection and settings dialog."""
        try:
            from media_settings_dialog import MediaSettingsDialog
            from media_processor import media_processors
            
            # Get current media path if any
            current_path = ""  # TODO: Get current media path from media player
            
            dialog = MediaSettingsDialog(self, media_number, current_path)
            if dialog.exec() == dialog.DialogCode.Accepted:
                settings = dialog.get_settings()
                
                # ✅ ACTUALLY APPLY THE MEDIA SETTINGS
                media_processors[media_number].update_settings(settings, current_path)
                
                # ✅ LOAD THE MEDIA FILE
                file_path = settings.get('file_path')
                if file_path:
                    try:
                        self.load_media(media_number, file_path)
                        print(f"✅ Loaded media file for media {media_number}: {file_path}")
                    except Exception as e:
                        print(f"❌ Failed to load media file: {e}")
                
                print(f"✅ Applied media settings for media {media_number}:", settings)
                
                # Show confirmation
                from PyQt6.QtWidgets import QMessageBox
                effects_list = []
                if settings.get('file_path'):
                    effects_list.append(f"File: {settings['file_path'].split('/')[-1]}")
                if settings.get('speed', 1.0) != 1.0:
                    effects_list.append(f"Speed: {settings['speed']}x")
                if settings.get('scale_mode', 'Fit (Maintain Aspect)') != 'Fit (Maintain Aspect)':
                    effects_list.append(f"Scale: {settings['scale_mode']}")
                if settings.get('brightness', 0) != 0:
                    effects_list.append(f"Brightness: {settings['brightness']:+d}")
                if settings.get('contrast', 0) != 0:
                    effects_list.append(f"Contrast: {settings['contrast']:+d}")
                if settings.get('flip_horizontal', False):
                    effects_list.append("Horizontal Flip")
                
                # Removed confirmation dialog - settings applied silently
        except Exception as e:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Error", f"Failed to open media settings: {str(e)}")
    
    def show_text_overlay_settings(self):
        """Show enhanced text overlay settings dialog."""
        try:
            from text_overlay_settings_dialog import TextOverlaySettingsDialog
            
            dialog = TextOverlaySettingsDialog(self)
            if dialog.exec() == dialog.DialogCode.Accepted:
                settings = dialog.get_settings()
                print("Applied text overlay settings:", settings)
                # Store to Preview-only settings; do not affect Program until CUT/AUTO
                try:
                    self.preview_text_settings = dict(settings)
                except Exception:
                    pass
                # Refresh Preview panel
                try:
                    pv = getattr(self, 'active_preview_source', None)
                    if pv and isinstance(pv, tuple) and len(pv) == 2:
                        st, idx = pv[0], int(pv[1])
                        frame = None
                        if st == 'input':
                            frame = self.last_input_image.get(idx) if hasattr(self, 'last_input_image') else None
                        elif st == 'media':
                            frame = self.last_media_image.get(idx) if hasattr(self, 'last_media_image') else None
                        self._update_preview_monitor(frame, st, idx)
                except Exception:
                    pass
                
                # Show confirmation
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.information(self, "Text Overlay", 
                    f"✅ Text overlay applied!\n\nText: '{settings.get('text', '')[:50]}{'...' if len(settings.get('text', '')) > 50 else ''}'")
        except Exception as e:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Error", f"Failed to open text overlay settings: {str(e)}")

def main():
    """Main application entry point"""
    # Enable high DPI scaling; on Qt6 AA_UseHighDpiPixmaps may not exist, so guard it
    from PyQt6.QtGui import QGuiApplication
    # Also import QSurfaceFormat for forcing default GL format on Windows
    try:
        from PyQt6.QtGui import QSurfaceFormat
    except Exception:
        QSurfaceFormat = None
    import os
    try:
        # Enable high DPI scaling before QApplication is created
        enable_attr = getattr(Qt.ApplicationAttribute, 'AA_EnableHighDpiScaling', None)
        if enable_attr is not None:
            QGuiApplication.setAttribute(enable_attr, True)
        attr = getattr(Qt.ApplicationAttribute, 'AA_UseHighDpiPixmaps', None)
        if attr is not None:
            QGuiApplication.setAttribute(attr, True)
    except Exception:
        pass
    # Prefer desktop GL on Windows to avoid software GL fallbacks (ANGLE) when possible
    try:
        if sys.platform.startswith('win'):
            os.environ.setdefault('QT_OPENGL', 'desktop')
    except Exception:
        pass

    # Set a default QSurfaceFormat requesting a modern core profile before creating QApplication
    try:
        if QSurfaceFormat is not None:
            fmt = QSurfaceFormat()
            try:
                fmt.setVersion(3, 3)
                fmt.setProfile(QSurfaceFormat.OpenGLContextProfile.CoreProfile)
            except Exception:
                try:
                    fmt.setVersion(3, 0)
                except Exception:
                    pass
            try:
                fmt.setSwapBehavior(QSurfaceFormat.SwapBehavior.DoubleBuffer)
            except Exception:
                pass
            QSurfaceFormat.setDefaultFormat(fmt)
    except Exception:
        pass

    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)

    app = QApplication(sys.argv)
    # Provide a safe substitution for missing Monospace fonts to silence alias warning
    try:
        QFont.insertSubstitution("Monospace", "Menlo")
    except Exception:
        pass
    app.setApplicationName("GoLive Studio")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("GoLive Studio")
    
    # Set application style for better cross-platform appearance
    app.setStyle('Fusion')
    
    # Create and show main window
    window = GoLiveStudio()
    window.show()

    # --- Ensure all QTimers are started after QApplication is running ---
    try:
        # Start adaptive quality monitoring QTimer
        if hasattr(quality_manager, 'start_monitoring'):
            quality_manager.start_monitoring()
        else:
            print("[WARN] quality_manager has no start_monitoring() method; ensure QTimer is started if needed.")
    except Exception as e:
        print(f"[WARN] Could not start quality_manager monitoring: {e}")

    # NOTE: If you use EnhancedCameraInput, call .start_stats_timer() on each instance after creation.

    # Ensure background processes are stopped before app quits
    try:
        app.aboutToQuit.connect(window.cleanup_on_exit)
    except Exception:
        pass

    # Start event loop
    sys.exit(app.exec())

if __name__ == "__main__":
    import traceback
    print("\n" + "="*70, flush=True)
    print(">>> GoLive Studio Launcher <<<", flush=True)
    print("="*70, flush=True)
    print(f"Python: {sys.version}", flush=True)
    print(f"Working Dir: {os.getcwd()}", flush=True)
    print("="*70 + "\n", flush=True)
    sys.stdout.flush()
    
    try:
        print("[STARTUP] Initializing main()...", flush=True)
        sys.stdout.flush()
        sys.stderr.flush()
        main()
        print("[STARTUP] main() completed successfully", flush=True)
    except SystemExit as se:
        print(f"[STARTUP] SystemExit({se.code})", flush=True)
        sys.exit(se.code if se.code else 0)
    except Exception as e:
        error_msg = f"FATAL ERROR: {type(e).__name__}: {e}\n\n{traceback.format_exc()}"
        print("\n" + error_msg + "\n", flush=True)
        sys.stderr.write(error_msg + "\n")
        sys.stderr.flush()
        sys.stdout.flush()
        
        # Try to show error dialog
        try:
            from PyQt6.QtWidgets import QApplication, QMessageBox
            if not QApplication.instance():
                app = QApplication(sys.argv)
            else:
                app = QApplication.instance()
            QMessageBox.critical(None, "GoLive Studio - Startup Error", error_msg)
        except Exception as gui_err:
            print(f"[GUI ERROR] Could not show error dialog: {gui_err}", flush=True)
        sys.exit(1)
