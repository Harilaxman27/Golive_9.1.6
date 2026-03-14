#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OBS-Style Camera Rendering Pipeline
Implements OBS libobs architecture: dedicated capture thread, frame buffer, and precise render thread
with nanosecond-level timing (like obs_graphics_thread and os_sleepto_ns)
"""

import cv2
import threading
import time
import numpy as np
from collections import deque
from typing import Optional, Tuple
from PyQt6.QtCore import QThread, pyqtSignal, Qt
from PyQt6.QtGui import QImage


class FrameBuffer:
    """
    Thread-safe circular frame buffer (like OBS NUM_TEXTURES).
    Stores a limited number of frames; new frames overwrite oldest.
    """
    
    def __init__(self, maxlen: int = 3):
        """
        Initialize frame buffer.
        
        Args:
            maxlen: Maximum number of frames to keep (default 3, like OBS video textures)
        """
        self._buf = deque(maxlen=maxlen)
        self._lock = threading.Lock()
        self._event = threading.Event()
    
    def put(self, frame: np.ndarray):
        """
        Add a frame to the buffer. If buffer is full, oldest frame is discarded.
        
        Args:
            frame: numpy array (BGR or RGB)
        """
        with self._lock:
            self._buf.append(frame)
        self._event.set()
    
    def get_latest(self) -> Optional[np.ndarray]:
        """
        Get the most recent frame without blocking.
        
        Returns:
            Latest frame (numpy array) or None if buffer is empty
        """
        with self._lock:
            if self._buf:
                return self._buf[-1]
        return None
    
    def wait(self, timeout: float = 0.1):
        """
        Wait for a new frame (blocks until frame is available or timeout).
        
        Args:
            timeout: Timeout in seconds
        """
        self._event.wait(timeout)
        self._event.clear()
    
    def is_empty(self) -> bool:
        """Check if buffer is empty."""
        with self._lock:
            return len(self._buf) == 0
    
    def clear(self):
        """Clear all frames from buffer."""
        with self._lock:
            self._buf.clear()


class CameraWorker(QThread):
    """
    Dedicated camera capture thread (like OBS camera source thread).
    Runs in a tight loop reading from OpenCV VideoCapture into a thread-safe frame buffer.
    This thread NEVER touches Qt rendering.
    """
    
    # Signal: camera initialized with (device_id, width, height, fps)
    camera_initialized = pyqtSignal(int, int, int, float)
    # Signal: error occurred with message
    error_occurred = pyqtSignal(str)
    # Signal: FPS stats (measured_fps)
    fps_stats = pyqtSignal(float)
    
    def __init__(self, frame_buffer: FrameBuffer, device: int = 0, width: int = 1920,
                 height: int = 1080, fps: float = 60.0, use_mjpeg: bool = True):
        """
        Initialize camera worker.
        
        Args:
            frame_buffer: Shared FrameBuffer instance
            device: Camera device index
            width: Desired frame width
            height: Desired frame height
            fps: Desired FPS
            use_mjpeg: Use MJPEG codec for lower latency on supported cameras
        """
        super().__init__()
        self.frame_buffer = frame_buffer
        self.device = device
        self.width = width
        self.height = height
        self.fps = fps
        self.use_mjpeg = use_mjpeg
        
        self._running = False
        self._cap: Optional[cv2.VideoCapture] = None
        
        # Stats
        self._frame_count = 0
        self._last_stats_time = 0.0
    
    def set_fps(self, fps: float):
        """Change camera FPS (will restart capture)."""
        self.fps = fps
    
    def run(self):
        """Main capture loop."""
        try:
            self._running = True
            
            # Initialize camera with OBS-style settings
            if not self._init_camera():
                self._running = False
                return
            
            # Emit initialization signal
            self.camera_initialized.emit(self.device, self.width, self.height, self.fps)
            
            # Main capture loop
            self._capture_loop()
            
        except Exception as e:
            self.error_occurred.emit(f"Camera thread error: {e}")
        finally:
            if self._cap:
                self._cap.release()
            self._running = False
    
    def _init_camera(self) -> bool:
        """
        Initialize camera with optimal settings for low latency.
        Returns True if successful, False otherwise.
        
        CRITICAL: Settings order on Windows DSHOW is important:
        1. Open camera
        2. Set codec (MJPEG) FIRST - without this, cameras cap at 30fps
        3. Set resolution
        4. Set FPS
        5. Set buffer size
        """
        try:
            # Windows uses CAP_DSHOW, Linux uses CAP_V4L2
            import sys
            if sys.platform.startswith('win'):
                backend = cv2.CAP_DSHOW
            else:
                backend = cv2.CAP_V4L2
            
            self._cap = cv2.VideoCapture(self.device, backend)
            if not self._cap.isOpened():
                self.error_occurred.emit(f"Failed to open camera {self.device}")
                return False
            
            # **CRITICAL: Set codec FIRST** (before resolution/fps)
            # Without this order, cameras silently cap at 30fps even if they support 120fps
            if self.use_mjpeg:
                try:
                    self._cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
                except Exception as e:
                    # Log but continue - some cameras may not support explicit codec setting
                    pass
            
            # Then set resolution
            try:
                self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
                self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
            except Exception:
                pass
            
            # Then set FPS
            try:
                self._cap.set(cv2.CAP_PROP_FPS, self.fps)
            except Exception:
                pass
            
            # CRITICAL: Set buffer size to 1 to get latest frame, not buffered/stale frames
            # At high FPS (120+), buffer buildup causes 100+ms latency spikes
            try:
                self._cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            except Exception:
                pass
            
            # Disable any auto-exposure/white-balance feedback loops
            try:
                self._cap.set(cv2.CAP_PROP_AUTOFOCUS, 0)
            except:
                pass
            
            return True
        except Exception as e:
            self.error_occurred.emit(f"Camera initialization failed: {e}")
            return False
    
    def _capture_loop(self):
        """Tight loop reading frames and pushing to buffer."""
        self._frame_count = 0
        self._last_stats_time = time.monotonic()
        
        while self._running:
            try:
                ret, frame = self._cap.read()
                if not ret:
                    # Try to reinitialize on frame read failure
                    if not self._init_camera():
                        break
                    continue
                
                # Push frame to buffer (will overwrite oldest if full)
                self.frame_buffer.put(frame)
                
                # Update stats every second
                self._frame_count += 1
                now = time.monotonic()
                elapsed = now - self._last_stats_time
                if elapsed >= 1.0:
                    measured_fps = self._frame_count / elapsed
                    self.fps_stats.emit(measured_fps)
                    self._frame_count = 0
                    self._last_stats_time = now
                
            except Exception as e:
                print(f"[CameraWorker] Capture error: {e}")
                continue
    
    def stop(self):
        """Stop the capture thread."""
        self._running = False
        self.wait()


class RenderThread(QThread):
    """
    Dedicated render thread with OBS-style nanosecond-precision timing.
    This thread reads from the frame buffer at a fixed, locked FPS rate using
    absolute deadline scheduling (like OBS os_sleepto_ns).
    
    Frame deadlines are ABSOLUTE, never reset (except if >1 frame behind).
    Uses hybrid sleep: coarse OS sleep + busy-wait for the final 1ms.
    """
    
    # Signal: new frame ready for display (emits numpy BGR frame)
    frame_ready = pyqtSignal(object)
    # Signal: actual measured FPS
    fps_updated = pyqtSignal(float)
    
    def __init__(self, frame_buffer: FrameBuffer, target_fps: float = 60.0):
        """
        Initialize render thread.
        
        Args:
            frame_buffer: Shared FrameBuffer instance
            target_fps: Target rendering FPS (e.g., 30.0, 60.0)
        """
        super().__init__()
        self.frame_buffer = frame_buffer
        self.target_fps = target_fps
        
        self._running = False
        self._fps_changed = False  # Flag for dynamic FPS changes
        self._last_frame: Optional[np.ndarray] = None
    
    def set_fps(self, fps: float):
        """Change target FPS (takes effect immediately on next frame)."""
        self.target_fps = max(1.0, min(240.0, fps))  # Clamp 1-240 FPS
        self._fps_changed = True  # Signal run() loop to recalculate interval
    
    def run(self):
        """Main render loop with OBS-style absolute deadline timing."""
        self._running = True
        self._fps_changed = False
        
        # Calculate frame interval in nanoseconds
        frame_interval_ns = int(1_000_000_000 / self.target_fps)
        
        # FPS counter state
        fps_count = 0
        fps_clock = time.perf_counter_ns()
        
        # ABSOLUTE deadline (key: advances by interval, never reset unless way behind)
        next_frame_ns = time.perf_counter_ns()
        
        while self._running:
            # Step 1: ADVANCE deadline by exactly one frame interval (always first)
            # This is the KEY to preventing drift — absolute scheduling, not relative
            next_frame_ns += frame_interval_ns
            
            # Step 2: Respond to dynamic FPS changes (mid-run)
            if self._fps_changed:
                frame_interval_ns = int(1_000_000_000 / self.target_fps)
                self._fps_changed = False
                # Note: Do NOT reset next_frame_ns — stay on timeline, just change interval
            
            # Step 3: Get latest frame or reuse last (frame duplication like OBS)
            frame = self.frame_buffer.get_latest()
            if frame is not None:
                self._last_frame = frame
            
            # Emit frame for display (always emit, even if duplicate)
            if self._last_frame is not None:
                self.frame_ready.emit(self._last_frame.copy())
            
            # Step 4: Update FPS counter
            fps_count += 1
            now = time.perf_counter_ns()
            elapsed = now - fps_clock
            if elapsed >= 1_000_000_000:  # 1 second
                measured_fps = fps_count / (elapsed / 1_000_000_000)
                self.fps_updated.emit(measured_fps)
                fps_count = 0
                fps_clock = now
            
            # Step 5: PRECISION SLEEP to absolute deadline (OBS-style os_sleepto_ns)
            # This is the most critical part for stable, locked FPS
            sleep_ns = next_frame_ns - time.perf_counter_ns()
            
            if sleep_ns > 1_000_000:
                # Coarse sleep for most of the frame (efficient)
                time.sleep((sleep_ns - 1_000_000) / 1_000_000_000)
                # Busy-wait the final 1ms for nanosecond precision
                while time.perf_counter_ns() < next_frame_ns:
                    pass
            elif sleep_ns > 0:
                # Small positive sleep: just busy-wait all of it
                while time.perf_counter_ns() < next_frame_ns:
                    pass
            elif sleep_ns < -frame_interval_ns:
                # More than 1 frame behind: resync deadline to now
                # This prevents cascading frame skips (like OBS)
                next_frame_ns = time.perf_counter_ns()
    
    def stop(self):
        """Stop the render thread."""
        self._running = False
        self.wait()


class CameraDisplayWidget:
    """
    Simple display widget that receives frames from the render thread.
    Must be mixed in with a QWidget subclass.
    Handles frame updates via signal connection in main thread.
    """
    
    def __init__(self):
        """Initialize display widget."""
        self._pixmap = None
        self._frame = None
    
    def update_frame(self, frame: np.ndarray):
        """
        Update display with new frame (called from render thread via signal).
        Convert numpy BGR frame to QPixmap and schedule repaint.
        
        Args:
            frame: numpy array in BGR format
        """
        try:
            if frame is None:
                return
            
            from PyQt6.QtGui import QImage, QPixmap
            
            # Convert BGR to RGB for Qt display
            h, w = frame.shape[:2]
            
            # Handle both 3-channel (BGR) and 4-channel (BGRA) frames
            if len(frame.shape) == 3:
                if frame.shape[2] == 3:
                    # BGR -> RGB
                    rgb_frame = frame[:, :, ::-1].copy()
                    format_type = QImage.Format.Format_RGB888
                elif frame.shape[2] == 4:
                    # BGRA -> RGBA
                    rgb_frame = frame[:, :, [2, 1, 0, 3]].copy()
                    format_type = QImage.Format.Format_RGBA8888
                else:
                    return
            else:
                return
            
            # Create QImage from numpy array
            bytes_per_line = 3 * w if format_type == QImage.Format.Format_RGB888 else 4 * w
            q_image = QImage(rgb_frame.data, w, h, bytes_per_line, format_type)
            
            # Convert to QPixmap
            self._pixmap = QPixmap.fromImage(q_image)
            
            # Schedule repaint (non-blocking, posts to Qt event queue)
            self.update()
        
        except Exception as e:
            print(f"[CameraDisplayWidget] Frame update error: {e}")
    
    def paintEvent(self, event):
        """Paint the latest frame."""
        if self._pixmap:
            from PyQt6.QtGui import QPainter
            painter = QPainter(self)
            painter.drawPixmap(self.rect(), self._pixmap)
