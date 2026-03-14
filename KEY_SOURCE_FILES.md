# KEY SOURCE FILE CONTENTS

## FILE 1: obs_pipeline.py (Complete OBS-Style Camera Pipeline)

**Location:** GoLive 9.1 5/obs_pipeline.py  
**Size:** 420 lines  
**Purpose:** Dedicated camera capture and render threads with nanosecond-precision timing

```python
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
            
            bytes_per_line = rgb_frame.nbytes // h
            q_image = QImage(rgb_frame.data, w, h, bytes_per_line, format_type)
            self._pixmap = QPixmap.fromImage(q_image)
            self.update()
            
        except Exception as e:
            print(f"Error updating frame: {e}")
```

---

## FILE 2: camera_manager_obs.py (Complete Camera Manager)

**Location:** GoLive 9.1 5/camera_manager_obs.py  
**Size:** 150+ lines

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Camera Manager - Manages OBS-style pipeline for each camera input
Handles initialization, frame delivery, and cleanup for per-camera OBS pipelines
"""

from PyQt6.QtCore import QThread, pyqtSignal, Qt
from obs_pipeline import FrameBuffer, CameraWorker, RenderThread


class CameraManager:
    """
    Manages a single camera's OBS-style pipeline.
    - Owns a FrameBuffer, CameraWorker, and RenderThread
    - Handles inter-thread communication
    - Emits signals for frame updates and stats
    """
    
    def __init__(self, input_number: int, device: int = 0, width: int = 1920,
                 height: int = 1080, fps: float = 60.0):
        """
        Initialize camera manager for a single input.
        
        Args:
            input_number: UI input number (1, 2, 3, etc)
            device: Camera device index
            width: Desired frame width
            height: Desired frame height
            fps: Desired FPS
        """
        self.input_number = input_number
        self.device = device
        self.width = width
        self.height = height
        self.fps = fps
        
        # Create frame buffer (circular buffer with room for 3 frames)
        self.frame_buffer = FrameBuffer(maxlen=3)
        
        # Create camera capture worker thread
        self.camera_worker = CameraWorker(
            frame_buffer=self.frame_buffer,
            device=device,
            width=width,
            height=height,
            fps=fps,
            use_mjpeg=True  # Enable MJPEG for lower latency
        )
        
        # Create render thread (with OBS-style timing)
        self.render_thread = RenderThread(
            frame_buffer=self.frame_buffer,
            target_fps=fps
        )
        
        # Set thread priorities (like OBS)
        # Note: On some systems, these may not have effect if running as non-admin
        self.camera_worker.setPriority(QThread.Priority.HighPriority)
        self.render_thread.setPriority(QThread.Priority.TimeCriticalPriority)
        
        # State
        self._running = False
        self._last_frame = None
    
    def start(self):
        """Start both camera and render threads."""
        if self._running:
            return
        
        self._running = True
        self.camera_worker.start()
        self.render_thread.start()
    
    def stop(self):
        """Stop both camera and render threads."""
        if not self._running:
            return
        
        self._running = False
        self.render_thread.stop()
        self.camera_worker.stop()
    
    def set_fps(self, fps: float):
        """Update target FPS (affects render thread)."""
        self.fps = fps
        self.render_thread.set_fps(fps)
        # Camera worker can adapt based on actual camera capabilities
        self.camera_worker.set_fps(fps)
    
    def is_running(self) -> bool:
        """Check if manager is running."""
        return self._running


class SignaledCameraManager(CameraManager):
    """
    CameraManager subclass that can be used directly with Qt signals.
    Creates actual Qt signals that can be connected to slots.
    """
    
    def __init__(self, input_number: int, parent=None, device: int = 0, 
                 width: int = 1920, height: int = 1080, fps: float = 60.0):
        """Initialize with parent for signal ownership."""
        super().__init__(input_number, device, width, height, fps)
        self.parent = parent
        
        # Import here to avoid circular deps
        from PyQt6.QtCore import QObject
        
        # Create a signal emitter (QObject) for this camera
        class CameraSignals(QObject):
            frame_ready = pyqtSignal(int, object)  # (input_number, frame)
            camera_error = pyqtSignal(int, str)  # (input_number, error_msg)
            fps_updated = pyqtSignal(int, float)  # (input_number, measured_fps)
            camera_initialized = pyqtSignal(int)  # (input_number)
        
        self.signals = CameraSignals()
        
        # Connect worker signals to our signals
        self.camera_worker.camera_initialized.connect(
            lambda d, w, h, f: self.signals.camera_initialized.emit(input_number)
        )
        self.camera_worker.error_occurred.connect(
            lambda msg: self.signals.camera_error.emit(input_number, msg)
        )
        self.camera_worker.fps_stats.connect(
            lambda fps: self.signals.fps_updated.emit(input_number, fps)
        )
        
        # Connect render thread signals to our signals
        self.render_thread.frame_ready.connect(
            lambda frame: self.signals.frame_ready.emit(input_number, frame)
        )
        self.render_thread.fps_updated.connect(
            lambda fps: self.signals.fps_updated.emit(input_number, fps)
        )
```

---

## FILE 3: streaming.py - StreamFrameQueue (Key Streaming Section)

**Location:** GoLive 9.1 5/streaming.py, lines 42-143

```python
class StreamFrameQueue:
    """
    Fix 8B: Bounded frame queue for streaming output with rate limiting.
    Decouples render thread from FFmpeg pipe to prevent backpressure.
    Uses absolute nanosecond deadline timing (OBS-style precision).
    """
    def __init__(self, target_fps, max_queue_size=3):
        self._queue = queue.Queue(maxsize=max_queue_size)
        self._target_fps = target_fps
        self._frame_interval_ns = int(1_000_000_000 / target_fps)
        self._running = False
        self._process = None
        self._writer_thread = None
        self._last_frame = None

    def start(self, process, target_fps, log_cb=None):
        """Start the rate-limited writer thread."""
        self._process = process
        self._target_fps = target_fps
        self._frame_interval_ns = int(1_000_000_000 / target_fps)
        self._running = True
        self._log_cb = log_cb
        self._writer_thread = threading.Thread(
            target=self._write_loop, daemon=True, name="StreamPipeWriter"
        )
        self._writer_thread.start()
        if log_cb:
            log_cb(f"[STREAM] Frame queue started at {target_fps}fps\n")

    def put_frame(self, frame_bytes):
        """Non-blocking — drops oldest frame if queue is full (Fix 8B)."""
        try:
            self._queue.put_nowait(frame_bytes)
        except queue.Full:
            try:
                self._queue.get_nowait()
                self._queue.put_nowait(frame_bytes)
                if hasattr(self, '_log_cb') and self._log_cb:
                    self._log_cb("[STREAM] Queue full, dropped oldest frame to prevent backpressure\n")
            except queue.Empty:
                pass

    def _write_loop(self):
        """Writes frames to FFmpeg pipe at EXACTLY target_fps using absolute deadline timing."""
        frame_interval_ns = self._frame_interval_ns
        next_frame_ns = _time.perf_counter_ns()
        last_frame = None

        while self._running:
            # Step 1: Advance absolute deadline
            next_frame_ns += frame_interval_ns

            # Step 2: Get next frame (or reuse last if none available)
            try:
                frame_bytes = self._queue.get_nowait()
                last_frame = frame_bytes
            except queue.Empty:
                frame_bytes = last_frame  # Frame duplication for CFR

            # Step 3: Write to pipe if we have a frame
            if frame_bytes is not None and self._process is not None:
                try:
                    self._process.write(frame_bytes)
                except (BrokenPipeError, OSError, Exception):
                    self._running = False
                    break

            # Step 4: Precision sleep to absolute deadline
            sleep_ns = next_frame_ns - _time.perf_counter_ns()
            if sleep_ns > 1_000_000:
                _time.sleep((sleep_ns - 1_000_000) / 1_000_000_000)
                while _time.perf_counter_ns() < next_frame_ns:
                    pass
            elif sleep_ns > 0:
                while _time.perf_counter_ns() < next_frame_ns:
                    pass
            elif sleep_ns < -frame_interval_ns:
                next_frame_ns = _time.perf_counter_ns()

    def stop(self):
        """Stop the writer thread."""
        self._running = False
        if self._writer_thread and self._writer_thread.is_alive():
            self._writer_thread.join(timeout=2.0)
        if hasattr(self, '_log_cb') and self._log_cb:
            self._log_cb("[STREAM] Frame queue stopped\n")
```

---

## FILE 4: enhanced_graphics_output.py - Display Widget (Key Sections)

**Location:** GoLive 9.1 5/enhanced_graphics_output.py

### GraphicsRenderThread (lines 43-130)

```python
class GraphicsRenderThread(QThread):
    """
    Dedicated render timing thread for graphics output widget.
    Uses absolute nanosecond deadline timing — same as OBS obs_graphics_thread.
    Emits render_tick at exactly the target FPS with nanosecond precision.
    """
    render_tick = pyqtSignal()  # Emitted when it's time to repaint

    def __init__(self, target_fps=60, parent=None):
        super().__init__(parent)
        self.target_fps = target_fps
        self._running = False
        self._fps_changed = False

    def set_fps(self, fps):
        """Change target FPS (takes effect immediately on next frame)."""
        if fps > 0:
            self.target_fps = max(24, fps)
            self._fps_changed = True

    def run(self):
        """Main render timing loop with OBS-style absolute deadline scheduling."""
        self._running = True
        self._fps_changed = False
        
        frame_interval_ns = int(1_000_000_000 / self.target_fps)
        frame_count = 0
        fps_clock_ns = time.perf_counter_ns()
        next_frame_ns = time.perf_counter_ns()
        
        while self._running:
            # Step 1: ADVANCE deadline by exactly one frame interval
            next_frame_ns += frame_interval_ns
            
            # Step 2: Respond to dynamic FPS changes
            if self._fps_changed:
                frame_interval_ns = int(1_000_000_000 / self.target_fps)
                self._fps_changed = False
            
            # Step 3: Signal the widget to repaint
            self.render_tick.emit()
            
            # Step 4: Update FPS counter
            frame_count += 1
            now_ns = time.perf_counter_ns()
            elapsed_ns = now_ns - fps_clock_ns
            if elapsed_ns >= 1_000_000_000:
                measured_fps = frame_count
                print(f"Render FPS: {measured_fps}")
                frame_count = 0
                fps_clock_ns = now_ns
            
            # Step 5: PRECISION SLEEP to absolute deadline
            sleep_ns = next_frame_ns - time.perf_counter_ns()
            
            if sleep_ns > 1_000_000:
                time.sleep((sleep_ns - 1_000_000) / 1_000_000_000)
                while time.perf_counter_ns() < next_frame_ns:
                    pass
            elif sleep_ns > 0:
                while time.perf_counter_ns() < next_frame_ns:
                    pass
            elif sleep_ns < -frame_interval_ns:
                next_frame_ns = time.perf_counter_ns()

    def stop(self):
        """Stop the render thread cleanly."""
        self._running = False
        self.wait(2000)
```

### EnhancedGraphicsOutputWidget.__init__() (lines 156-207)

```python
def __init__(self, parent=None):
    super().__init__(parent)
    
    # Frame data
    self._last_frame: Optional[QImage] = None
    self._overlay_image: Optional[QImage] = None
    self._offscreen: Optional[QImage] = None
    
    # Rendering settings
    self._overscan = 1.03
    self._target_fps = 60
    self._target_interval_ms = int(1000.0 / self._target_fps)
    
    # Graphics render thread with nanosecond-precision timing
    self._render_thread = GraphicsRenderThread(target_fps=self._target_fps, parent=None)
    self._render_thread.render_tick.connect(
        self.update,
        Qt.ConnectionType.QueuedConnection
    )
    self._render_thread.setPriority(QThread.Priority.TimeCriticalPriority)
    self._render_thread.start()
    
    # Minimum 24 FPS refresh timer
    self._min_fps_timer = QTimer(self)
    self._min_fps_timer.setInterval(42)  # ~24 FPS minimum
    self._min_fps_timer.timeout.connect(self._on_min_fps_tick)
    self._min_fps_timer.start()
    
    # Cleanup signal
    self.destroyed.connect(self._cleanup_render_thread)
```

### paintGL() - Main Rendering Method (lines ~850-900)

```python
def paintGL(self):
    """Hardware-accelerated rendering with pixelation fixes."""
    
    if getattr(self, '_painting', False):
        return
    self._painting = True
    
    try:
        render_size = self._get_effective_render_size()
        
        # Create or reuse offscreen buffer
        if (self._offscreen is None or 
            self._offscreen.size() != render_size):
            self._offscreen = QImage(render_size, 
                                    QImage.Format.Format_ARGB32_Premultiplied)
        
        output = self._offscreen
        output.fill(QColor(0, 0, 0, 255))
        
        painter = QPainter(output)
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
            
            # Render layers
            self._render_video_layer(painter, render_size)
            self._render_overlay_layer(painter, render_size)
            self._render_text_layer(painter, render_size)
            
        finally:
            painter.end()
        
        # Display the rendered frame
        widget_painter = QPainter(self)
        try:
            widget_painter.setRenderHint(
                QPainter.RenderHint.SmoothPixmapTransform, True
            )
            widget_painter.drawImage(0, 0, output)
        finally:
            widget_painter.end()
    
    finally:
        self._painting = False
```

---

## FILE 5: main.py - Frame Handler (_on_camera_frame_ready)

**Location:** GoLive 9.1 5/main.py, lines 6188-6241

```python
def _on_camera_frame_ready(self, input_number, rgb_frame):
    """Update the UI with the captured frame (runs on main thread)."""
    try:
        from PyQt6.QtGui import QImage, QPixmap
        from PyQt6.QtCore import QSize, Qt
        if rgb_frame is None:
            return
        height, width, channel = rgb_frame.shape
        bytes_per_line = 3 * width
        
        # ⚠️ CRITICAL: This .copy() is the main bottleneck (10-20ms)
        q_image = QImage(rgb_frame.data, width, height, bytes_per_line, 
                        QImage.Format.Format_RGB888).copy()
        
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
                # ⚠️ CRITICAL: SmoothTransformation is CPU-intensive (10-50ms)
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
        
        try:
            self.last_input_pixmap[input_number] = scaled_pixmap
        except Exception:
            pass
    
    except Exception:
        pass
    
    # If currently selected as output, update main output image
    try:
        if not getattr(self, '_transition_running', False) and \
           self.current_output == ('input', input_number):
            self._set_output_image(self.last_input_image.get(input_number))
    except Exception:
        pass
    
    # Update live preview monitor if active
    try:
        if hasattr(self, 'active_preview_source') and \
           self.active_preview_source == ('input', input_number):
            self._update_preview_monitor(self.last_input_image.get(input_number), 
                                        'input', int(input_number))
    except Exception:
        pass
```

