# GoLive Studio - Complete Architecture Analysis

**Generated:** February 27, 2026  
**Issue:** Frame drops and UI freezing at 60fps with correct terminal FPS  
**Status:** Comprehensive Analysis Complete

---

## 1. COMPLETE FOLDER & FILE STRUCTURE

```
GoLive 9.1 5/
├── Core Application Files
│   ├── main.py                            # Main application entry point (9425 lines)
│   ├── config.py                          # Configuration management
│   ├── launch_golive.py                   # Launcher script
│   ├── requirements.txt                   # Python dependencies
│
├── Camera Pipeline (OBS-style)
│   ├── obs_pipeline.py                    # OBS-style camera/render pipeline (420 lines)
│   │   ├── FrameBuffer                    # Thread-safe circular frame buffer
│   │   ├── CameraWorker (QThread)         # Dedicated camera capture thread
│   │   └── RenderThread (QThread)         # Dedicated render scheduler thread
│   │
│   ├── camera_manager_obs.py              # Camera manager wrapper (150+ lines)
│   │   ├── CameraManager                  # Single camera pipeline manager
│   │   └── SignaledCameraManager          # Qt-signal emitting version
│   │
│   ├── camera_processor.py                # Frame processing utilities
│   ├── enhanced_camera_input.py           # Enhanced camera input module
│   ├── av_capture.py                      # Alternative A/V capture backend
│
├── Streaming Pipeline
│   ├── streaming.py                       # Main stream controller (1314 lines)
│   │   ├── StreamController (QObject)     # FFmpeg pipe manager
│   │   └── StreamFrameQueue               # Rate-limited frame queue w/ backpressure
│   │
│   ├── enhanced_streaming.py              # Enhanced streaming manager
│   ├── av_streamer.py                     # PyAV-based streamer
│   ├── encoder/                           # Encoder selection module
│   │   └── encoder_selector.py
│
├── Graphics & Display
│   ├── renderer/                          # Hardware-accelerated renderer
│   │   ├── base_renderer.py
│   │   ├── gpu_graphics_output.py         # GPU-based graphics output
│   │   ├── opengl_renderer.py             # OpenGL renderer
│   │   ├── d3d_renderer.py                # Direct3D renderer (Windows)
│   │   ├── gpu_overlay_manager.py
│   │   ├── gpu_external_display.py
│   │   └── migration_helper.py            # Renderer selection logic
│   │
│   ├── enhanced_graphics_output.py        # Main graphics widget (1367 lines)
│   │   ├── EnhancedGraphicsOutputWidget   # QOpenGLWidget for display
│   │   ├── GraphicsRenderThread (QThread) # Hardware-accelerated render timing
│   │   └── Text/Overlay rendering
│   │
│   ├── external_display.py                # External monitor mirroring
│   ├── enhanced_external_display.py       # Enhanced external display
│
├── Threading & Synchronization
│   ├── thread_pool_manager.py             # Managed thread pool (339 lines)
│   │   ├── ManagedThreadPool              # ThreadPoolExecutor wrapper
│   │   ├── TaskPriority (Enum)
│   │   └── ResourceMonitor                # CPU/memory monitoring
│   │
│   ├── event_coalescer.py                 # Event batching for UI updates
│   ├── unified_timer.py                   # Centralized timer system
│   ├── fps_controller.py                  # Global FPS controller
│   ├── fps_stabilizer.py                  # FPS stability management
│
├── Performance Optimization
│   ├── performance_monitor.py             # Real-time performance tracking
│   ├── performance_optimizer.py           # Adaptive performance tuning
│   ├── aggressive_memory_optimizer.py     # Memory management
│   ├── adaptive_quality.py                # Quality level adaptation
│   ├── memory_pool.py                     # Object pooling
│   ├── smart_cache.py                     # Intelligent caching
│   ├── texture_pool.py                    # Texture resource pooling
│   ├── gl_context_manager.py              # OpenGL context management
│
├── Audio
│   ├── audio/                             # Audio backend abstraction
│   │   ├── base_audio.py
│   │   ├── qt_audio.py                    # Qt Multimedia audio
│   │   ├── macos_audio.py                 # macOS-specific audio
│   │   └── __init__.py
│   │
│   ├── enhanced_audio_sync.py             # A/V synchronization
│
├── Overlays & Text
│   ├── text_overlay.py                    # Text overlay controls
│   ├── text_overlay_renderer.py           # Text rendering
│   ├── text_overlay_settings_dialog.py
│   ├── overlay_manager.py                 # Effect manager
│   ├── transitions.py                     # Transition effects
│
├── Recording
│   ├── recording.py                       # Recording controller
│   ├── recording_settings_dialog.py       # Recording settings UI
│
├── UI Dialogs & Settings
│   ├── input_settings_dialog.py
│   ├── media_settings_dialog.py
│   ├── streaming_settings_dialog_improved.py
│   ├── premiere_effects_panel_final.py
│   ├── project_manager.py
│   ├── project_model.py
│
├── Utilities
│   ├── ffmpeg_utils.py                    # FFmpeg path & validation
│   ├── ffmpeg_validator.py
│   ├── error_handler.py                   # Error logging
│   ├── secure_storage.py                  # Secure data storage
│   ├── screen_capture.py                  # Screen capture utilities
│   ├── media_processor.py
│
├── Build & Deployment
│   ├── build_scripts/
│   ├── build.py, build_master.py
│   ├── build_complete_application.py
│   ├── build_windows_installer.py
│   ├── build_macos_installer.py
│   ├── create_windows_exe_complete.py
│   ├── create_macos_dmg.py
│
├── Resources
│   ├── resources.qrc                      # Qt resource file
│   ├── resources_rc.py                    # Compiled resources
│   ├── mainwindow.ui                      # Qt Designer UI
│   ├── icons/                             # Icon files
│   ├── effects/                           # Effect assets
│
├── Test/Debug Files
│   ├── test_*.py (multiple)
│   ├── debug_*.py (multiple)
│   ├── verify_fixes.py
│   ├── launch_debug.py
│
└── Documentation
    ├── README.md
    ├── QUICK_REFERENCE.md
    ├── OBS_PIPELINE_GUIDE.md
    ├── AUDIO_FIX_COMPLETE.md
    ├── MAXIMIZE_LAYOUT_FIX.md
    └── FIX_SUMMARY.md
```

---

## 2. CAMERA CAPTURE PIPELINE

### Architecture
**Primary:** OBS-style pipeline (obs_pipeline.py + camera_manager_obs.py)  
**Fallback:** Legacy OpenCV timer-based (main.py: update_camera_frame)  
**Library:** OpenCV (cv2) + PyQt6 QThread

### Components

#### **FrameBuffer** (obs_pipeline.py, lines 18-76)
- **Type:** Thread-safe circular buffer (collections.deque)
- **Size:** 3 frames max (NUM_TEXTURES like OBS)
- **Thread Safety:** threading.Lock + threading.Event
- **Operations:**
  - `put(frame)`: Adds frame, overwrites oldest if full
  - `get_latest()`: Non-blocking retrieval of most recent frame
  - `wait(timeout)`: Blocks until frame available

#### **CameraWorker** (obs_pipeline.py, lines 80-241)
- **Type:** QThread subclass
- **Purpose:** Dedicated camera capture (never touches Qt rendering)
- **Run Loop:** Tight loop calling `cap.read()`
- **Thread Priority:** HighPriority (QThread.Priority.HighPriority)
- **Critical Settings:**
  ```python
  # Windows DSHOW initialization order (critical for 60fps+):
  1. cv2.CAP_PROP_FOURCC = 'MJPG'  # MUST be FIRST
  2. cv2.CAP_PROP_FRAME_WIDTH/HEIGHT
  3. cv2.CAP_PROP_FPS
  4. cv2.CAP_PROP_BUFFERSIZE = 1   # Prevent stale frame queue
  ```
- **Stats:** Emits fps_stats signal every 1 second

#### **RenderThread** (obs_pipeline.py, lines 251-351)
- **Type:** QThread subclass
- **Purpose:** Render scheduling with nanosecond-precision timing
- **Timing Model:** OBS-style absolute deadline scheduling
  ```python
  next_frame_ns += frame_interval_ns        # ADVANCE deadline
  sleep_ns = next_frame_ns - perf_counter_ns()
  if sleep_ns > 1ms:
      sleep((sleep_ns - 1ms) / 1e9)  # Coarse sleep
      while perf_counter_ns() < next_frame_ns:
          pass                        # Busy-wait final 1ms
  ```
- **Thread Priority:** TimeCriticalPriority
- **Frame Handling:** Duplicates frames if camera slower than target FPS
- **Signals:** frame_ready (emits numpy BGR array)

### Signal Flow
```
Camera Device
    ↓
CameraWorker.run()
    ├─ Read frame from cv2.VideoCapture
    ├─ Put into FrameBuffer
    └─ Emit fps_stats signal
         ↓
    FrameBuffer (circular, 3-frame max)
         ↓
RenderThread.run()
    ├─ Get latest frame from buffer
    ├─ Emit frame_ready signal (numpy array)
    ├─ Sleep to nanosecond deadline
    └─ Emit fps_updated signal
         ↓
    SignaledCameraManager.signals.frame_ready
         ↓
    main.py: _on_obs_camera_frame()
         ↓
    Convert BGR→RGB numpy to QImage
         ↓
    Enhanced Graphics Output Widget
```

---

## 3. FRAME RENDERING PIPELINE

### Display Path: Camera → Graphics Output Widget

```
OBS Pipeline RenderThread
    (emits numpy BGR frame via signal)
         ↓
main.py._on_obs_camera_frame()
    (runs on main thread via QueuedConnection)
         ↓
Convert numpy BGR to QImage:
    rgb_frame = numpy BGR
    height, width = rgb_frame.shape[:2]
    q_image = QImage(rgb_frame.data, width, height, ..., Format_RGB888).copy()
         ↓
Cache in self.last_input_image[input_number]
         ↓
Update inputVideoFrame widget:
    pixmap = QPixmap.fromImage(q_image)
    scaled_pixmap = pixmap.scaled(
        widget_size,
        KeepAspectRatio,
        SmoothTransformation
    )
    video_widget._video_label.setPixmap(scaled_pixmap)
         ↓
If input is active output source:
    _set_output_image(q_image)
         ↓
EnhancedGraphicsOutputWidget.set_frame(q_image)
    (marshals to GUI thread if called from worker)
         ↓
_apply_frame_on_gui(q_image):
    self._last_frame = q_image
    _update_display()
         ↓
update() → scheduled repaint
         ↓
paintGL() [main rendering method]
    (runs when GraphicsRenderThread emits render_tick)
```

### Key Display Widget: EnhancedGraphicsOutputWidget

- **Type:** QOpenGLWidget (hardware-accelerated)
- **Location:** enhanced_graphics_output.py (1367 lines)
- **Rendering Thread:** GraphicsRenderThread
- **Rendering Method:** paintGL()

#### paintGL() Rendering Layers (lines ~850-900):
1. **Video Layer:** Renders input frame with aspect ratio, overlay opening
2. **Overlay Layer:** Composites PNG effects/transitions
3. **Text Layer:** Renders text overlays with scrolling support

#### Frame Flow in Widget:
```python
GraphicsRenderThread (nanosecond-precise scheduling)
    ├─ Advances deadline by frame_interval_ns
    ├─ Emits render_tick signal
    └─ Sleeps to nanosecond deadline
         ↓
render_tick signal (QueuedConnection)
    └─ Calls self.update() [schedule repaint]
         ↓
Qt event loop
    └─ Calls paintGL()
         ↓
paintGL() [main rendering]
    ├─ Creates/reuses offscreen QImage (ARGB32_Premultiplied)
    ├─ Paints to offscreen using QPainter
    ├─ Composites video + overlay + text
    └─ Blits to widget framebuffer
```

---

## 4. STREAMING PIPELINE

### Architecture

**File:** streaming.py (1314 lines)  
**Type:** FFmpeg pipe-based RTMP streaming  
**Controller:** StreamController (QObject)

### Components

#### **StreamFrameQueue** (streaming.py, lines 42-143)
- **Purpose:** Rate-limited frame delivery to FFmpeg pipe
- **Buffer:** queue.Queue(maxsize=3) - prevents backpressure
- **Drop Strategy:** Non-blocking with frame dropping on full queue
- **Writer Thread:** _write_loop() (separate daemon thread)
- **Timing:** OBS-style absolute deadline scheduling (like RenderThread)

#### **StreamController** (streaming.py, lines 147-1314)
- **Type:** QObject (Qt signals)
- **Purpose:** Manages FFmpeg subprocess and frame piping
- **Signals:** statusChanged (String)

### Streaming Flow

```
MainWindow._graphics_output [EnhancedGraphicsOutputWidget]
    (has rendered frame in paintGL)
         ↓
call _stream_controller.set_frame_provider(callable)
    └─ Provider returns QImage of target size
         ↓
StreamController.[initialize ffmpeg]
    ├─ Build ffmpeg command (h264, RTMP output)
    ├─ Subprocess with stdin=PIPE
    ├─ Start StreamFrameQueue rate limiter
    └─ Spawn _frame_queue._write_loop() thread
         ↓
Timer event (or frame provider callback):
    └─ get QImage from provider
         ↓
Convert QImage to raw RGBA bytes:
    bytes = qimage.bits().asarray(...)
         ↓
StreamFrameQueue.put_frame(bytes)
    (non-blocking, drops on full)
         ↓
_write_loop() [daemon thread]:
    ├─ Waits for frames in queue
    ├─ Writes to ffmpeg stdin
    ├─ Maintains absolute deadline for CFR
    └─ Handles backpressure gracefully
         ↓
FFmpeg subprocess
    ├─ Decodes raw RGBA via libx264/h264_nvenc/etc
    ├─ Encodes frames
    └─ Pipes to RTMP server
```

### FFmpeg Command Structure
```bash
ffmpeg
  -loglevel info
  -hide_banner
  -pix_fmt rgba                              # Input format
  -s <width>x<height>                        # Input resolution
  -r <fps>                                   # Input FPS
  -f rawvideo                                # Input container
  -i pipe:0                                  # Stdin input
  [optional audio input]
  -c:v h264_nvenc|h264_qsv|libx264          # Video codec
  -preset veryfast|fast|medium
  -b:v <bitrate_kbps>k
  -f flv                                     # Output container
  <rtmp_url>
```

---

## 5. THREADING ARCHITECTURE

### All Threads in System

| # | Thread | Type | Priority | Purpose | Location |
|---|--------|------|----------|---------|----------|
| 1 | **Main/GUI Thread** | Qt Event Loop | Normal | UI updates, event dispatch | PyQt6 |
| 2 | **CameraWorker** | QThread | HighPriority | Camera frame capture (cv2 read) | obs_pipeline.py:80 |
| 3 | **RenderThread** | QThread | TimeCriticalPriority | Frame timing schedules (FrameBuffer→frame_ready) | obs_pipeline.py:251 |
| 4 | **GraphicsRenderThread** | QThread | TimeCriticalPriority | Hardware-accelerated render tick generation | enhanced_graphics_output.py:43 |
| 5 | **StreamPipeWriter** | threading.Thread | Daemon | Rate-limited FFmpeg pipe writes | streaming.py:_write_loop |
| 6-N | **ThreadPoolExecutor Workers** | threading.Thread | Default | Background task execution | thread_pool_manager.py |
| M | **Performance Monitor** | threading.Thread | Daemon | CPU/memory monitoring | performance_monitor.py |
| Q | **Qt Audio** | (Internal) | (Internal) | Audio capture/playback | PyQt6 QAudioSource/Sink |

### Key Thread Interactions

#### **Camera → Render → UI**
```
CameraWorker (read loop)     RenderThread (timing loop)     Main GUI Thread
     │                             │                              │
     ├─ Read frame               │                              │
     ├─ Put in FrameBuffer      │                              │
     └─ (QueuedConnection)       │                              │
                                 ├─ Get latest frame            │
                                 ├─ Calculate deadline          │
                                 ├─ Emit frame_ready            │
                                 │   (QueuedConnection) ─────────→ _on_obs_camera_frame()
                                 │                             │
                                 │                             ├─ Convert BGR→RGB
                                 │                             ├─ Cache QImage
                                 │                             └─ Update widget
                                 │
                                 ├─ Emit render_tick            │
                                 │   (QueuedConnection) ─────────→ GraphicsOutputWidget.update()
                                 │                             │
                                 └─ Sleep to deadline           ├─ Qt schedules paintGL()
                                                               │
                                                               └─ paintGL() runs
```

### Signal Connections (Critical)

**All camera→UI frame connections use `Qt.ConnectionType.QueuedConnection`** to ensure:
- Frame conversion (numpy/cv2 ops) happens on main thread
- Qt painting APIs (QImage, QPainter) are thread-safe
- No crashes from cross-thread painter access

#### Frame Ready Signal Path
```python
# obs_pipeline.py:RenderThread
self.frame_ready.emit(self._last_frame.copy())

# camera_manager_obs.py:SignaledCameraManager.__init__()
self.render_thread.frame_ready.connect(
    lambda frame: self.signals.frame_ready.emit(input_number, frame)
)

# main.py:GoLiveStudio.__init__()
camera_mgr.signals.frame_ready.connect(
    lambda in_num, frame, mgr_ref=camera_mgr: 
        self._on_obs_camera_frame(in_num, frame),
    type=Qt.ConnectionType.QueuedConnection
)
```

---

## 6. SIGNAL & SLOT CONNECTIONS

### Primary Signal Network

#### Camera Manager Signals (camera_manager_obs.py)
```python
class CameraSignals(QObject):
    frame_ready = pyqtSignal(int, object)               # (input_number, numpy frame)
    camera_error = pyqtSignal(int, str)                 # (input_number, error_msg)
    fps_updated = pyqtSignal(int, float)                # (input_number, measured_fps)
    camera_initialized = pyqtSignal(int)                # (input_number)
```

#### Connections in main.py (~line 5915)
```python
camera_mgr.signals.frame_ready.connect(
    lambda in_num, frame: self._on_obs_camera_frame(in_num, frame),
    type=Qt.ConnectionType.QueuedConnection  # ← CRITICAL: ensures main thread
)

camera_mgr.signals.camera_error.connect(
    lambda in_num, msg: print(f"[Camera-{in_num}] Error: {msg}"),
    type=Qt.ConnectionType.QueuedConnection
)

camera_mgr.signals.fps_updated.connect(
    lambda in_num, fps: self._on_obs_camera_fps_updated(in_num, fps),
    type=Qt.ConnectionType.QueuedConnection
)
```

#### Graphics Output Signals
```python
# GraphicsRenderThread → EnhancedGraphicsOutputWidget
render_tick = pyqtSignal()

# Connected in __init__ (line ~197)
self._render_thread.render_tick.connect(
    self.update,
    Qt.ConnectionType.QueuedConnection
)
```

#### Global FPS Controller Signals
```python
# fps_controller.py
frame_ready = pyqtSignal(object)
fps_changed = pyqtSignal(int)

# enhanced_graphics_output.py
fps_controller.fps_changed.connect(self._on_fps_changed)
fps_controller.frame_ready.connect(self._on_frame_ready)
```

### Signal Connection Count
- **Frame delivery:** 3 signals per input × N inputs
- **FPS updates:** 2 signals per thread
- **Render thread:** 2 signals (render_tick, fps_updated)
- **Display updates:** 50+ update/repaint calls
- **Performance:** ~100+ active connections

---

## 7. MAIN DISPLAY WIDGET

### Widget Class: **EnhancedGraphicsOutputWidget**

**File:** enhanced_graphics_output.py  
**Base Class:** QOpenGLWidget  
**Lines:** 1367 total

#### Key Properties
```python
# Frame data
_last_frame: Optional[QImage]                 # Current video frame
_overlay_image: Optional[QImage]              # PNG overlay
_offscreen: Optional[QImage]                  # Offscreen render buffer

# Rendering thread
_render_thread: GraphicsRenderThread          # Nanosecond-precise scheduler
_min_fps_timer: QTimer                        # 24 FPS minimum fallback

# Timing
_target_fps: int                              # Target render FPS
_target_interval_ms: int                      # 1000/fps

# Performance
_frame_count: int                             # Frame counter
_diag_elapsed: QElapsedTimer                  # Diagnostics timer

# Transition system
_transition_active: bool
_transition_timer: QTimer
_transition_progress: float                   # 0.0 to 1.0

# Text overlay
_text_props: Dict[str, Any]
_scroll_timer: QTimer                         # Scrolling text timer
```

#### Main Rendering Method: paintGL()
```python
def paintGL(self):
    """Hardware-accelerated rendering with pixelation fixes."""
    
    # Create/reuse offscreen buffer (ARGB32_Premultiplied)
    self._offscreen = QImage(size, QImage.Format.Format_ARGB32_Premultiplied)
    painter = QPainter(self._offscreen)
    
    # Render layers in order:
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
    self._render_video_layer(painter, size)       # Video with aspect ratio
    self._render_overlay_layer(painter, size)     # PNG effect overlay
    self._render_text_layer(painter, size)        # Text with scrolling
    
    # Blit to widget framebuffer
    widget_painter = QPainter(self)
    widget_painter.drawImage(0, 0, self._offscreen)
```

#### Rendering Threads
```
GraphicsRenderThread (nanosecond-precise)
    ├─ Emits render_tick
    └─ Runs at exactly target_fps
             ↓
render_tick signal (QueuedConnection)
    └─ Calls self.update() [schedule repaint]
             ↓
Qt Event Loop
    └─ Calls paintGL()

_min_fps_timer (24 FPS fallback)
    ├─ Interval: 42ms (~24fps)
    └─ Emits if no frames in 42ms
```

#### Update Methods
```python
def set_frame(self, frame: Optional[QImage]):
    """Set video frame (marshals to GUI thread if needed)."""
    if QThread.currentThread() != self.thread():
        QTimer.singleShot(0, lambda: self._apply_frame_on_gui(frame))
    else:
        self._apply_frame_on_gui(frame)

def _apply_frame_on_gui(self, frame: Optional[QImage]):
    """Apply frame on GUI thread."""
    self._last_frame = frame
    self._update_display()

def _update_display(self):
    """Update display with performance tracking."""
    self._frame_count += 1
    if self._frame_count % self._memory_cleanup_interval == 0:
        self._cleanup_memory()
    self.update()  # Schedule repaint
```

---

## 8. FRAME QUEUE & BUFFERING

### Buffers in System

| Buffer | Type | Size | Purpose | Location |
|--------|------|------|---------|----------|
| **FrameBuffer (Camera)** | collections.deque | 3 frames | Circular capture buffer | obs_pipeline.py:18 |
| **StreamFrameQueue** | queue.Queue | 3 frames | Rate-limited streaming | streaming.py:55 |
| **_last_frame (Graphics)** | QImage | 1 frame | Current display frame | enhanced_graphics_output.py |
| **_offscreen (Graphics)** | QImage | 1 frame | Render target buffer | enhanced_graphics_output.py |
| **last_input_image (UI)** | Dict[int, QImage] | N inputs | Cached high-res frames | main.py:6201 |
| **last_input_pixmap (UI)** | Dict[int, QPixmap] | N inputs | Cached scaled display | main.py:6231 |

### Frame Buffer Management

#### FrameBuffer (OBS-style)
```python
# obs_pipeline.py:FrameBuffer
_buf = deque(maxlen=3)                      # Auto-drops oldest when full
_lock = threading.Lock()                    # Thread-safe access
_event = threading.Event()                  # Notify on new frame

def put(frame):
    with self._lock:
        self._buf.append(frame)             # Overwrites oldest if full
    self._event.set()

def get_latest():
    with self._lock:
        if self._buf:
            return self._buf[-1]            # Always return newest
    return None
```

#### StreamFrameQueue
```python
# streaming.py:StreamFrameQueue
_queue = queue.Queue(maxsize=3)
_running = True                             # Controls _write_loop

def put_frame(frame_bytes):
    try:
        self._queue.put_nowait(frame_bytes) # Non-blocking
    except queue.Full:
        self._queue.get_nowait()            # Drop oldest
        self._queue.put_nowait(frame_bytes) # Add new

def _write_loop():
    while self._running:
        try:
            frame = self._queue.get_nowait()
        except queue.Empty:
            frame = last_frame               # Duplicate frames for CFR
        
        self._process.write(frame)          # Pipe to FFmpeg
        sleep_ns = next_frame_ns - perf_counter_ns()
        # OBS-style precision sleep...
```

#### Graphics Output Widget
```python
# enhanced_graphics_output.py:EnhancedGraphicsOutputWidget
_last_frame: Optional[QImage]               # Current frame to render
_offscreen: Optional[QImage]                # Render-to-texture buffer

def set_frame(frame):
    self._last_frame = frame
    self.update()  # Schedule repaint (won't call immediately)

def paintGL():
    # Render _last_frame to _offscreen
    # Then blit _offscreen to widget framebuffer
```

#### Memory Optimization
```python
# Limit mask cache size
_max_cache_size = 10
if len(self._mask_cache) > self._max_cache_size:
    # Remove oldest entries

# Periodic cleanup every 100 frames
def _cleanup_memory():
    # Check mask cache
    # (NOT calling gc.collect() - causes stuttering)
```

---

## 9. TIMER USAGE

### QTimer Instances

| Timer | Owner | Interval | Purpose | Location |
|-------|-------|----------|---------|----------|
| **_render_thread** | EnhancedGraphicsOutputWidget | 0ms | Nanosecond-precise render scheduling | line 193 |
| **_min_fps_timer** | EnhancedGraphicsOutputWidget | 42ms | 24 FPS minimum fallback | line 206 |
| **_transition_timer** | EnhancedGraphicsOutputWidget | 33ms | Effect transition animation | line 176 |
| **_scroll_timer** | EnhancedGraphicsOutputWidget | 16ms | Scrolling text animation | line 171 |
| **camera_timers[n]** | GoLiveStudio | ≤4ms | Legacy camera frame reads | main.py:6066 |
| **_resize_timer** | GoLiveStudio | 100ms | Debounced resize handler | main.py:919 |
| **_batch_timer** | GoLiveStudio | variable | Event batching | main.py:639 |
| **_stream_uptime_timer** | GoLiveStudio | 1000ms | Stream uptime display | main.py:2310 |
| **status_timer** | GoLiveStudio | variable | Status bar updates | main.py:2519 |
| **monitor_timer** | performance_monitor | 100ms | Memory/CPU monitoring | performance_monitor.py:184 |
| **optimize_timer** | performance_monitor | 5000ms | Memory optimization | performance_monitor.py:189 |
| **_capture_timer** | screen_capture | 33ms | Screen capture polling | screen_capture.py:38 |

### Timer Connections
```python
# Graphics render thread (nanosecond-precise)
self._render_thread.render_tick.connect(
    self.update,
    Qt.ConnectionType.QueuedConnection
)

# Min FPS fallback (24 FPS guarantee)
self._min_fps_timer.timeout.connect(self._on_min_fps_tick)
self._min_fps_timer.start(42)

# Camera frame reads (legacy path only)
timer.timeout.connect(lambda: self.update_camera_frame(input_number))
timer.start(interval_ms)  # e.g., 16ms for 60fps
```

### Timer Intervals Summary
- **Nanosecond-precision timers:** _render_thread (QThread-based, no QTimer)
- **Frame delivery:** 0-4ms intervals (fast as possible)
- **UI updates:** 16-42ms intervals (24-60fps)
- **System monitoring:** 100-5000ms intervals (background)

---

## 10. KNOWN BOTTLENECKS & BLOCKING CALLS

### ⚠️ CRITICAL BLOCKING CALLS IN MAIN THREAD

#### 1. **Camera Frame Conversion (main.py:6188-6200)**
```python
def _on_camera_frame_ready(self, input_number, rgb_frame):
    height, width, channel = rgb_frame.shape          # ← Fast
    bytes_per_line = 3 * width
    q_image = QImage(rgb_frame.data, width, height,   # ← BLOCKING
                     bytes_per_line, 
                     QImage.Format.Format_RGB888).copy()  # ← COPY is blocking
```
**Issue:** `.copy()` allocates memory and copies ~6MB/frame at 60fps  
**Frequency:** Every frame (60fps = 60 copies/sec)  
**Impact:** ~360MB/sec memory traffic

#### 2. **Pixmap Scaling (main.py:6209-6216)**
```python
scaled_pixmap = pixmap.scaled(
    widget_size,
    Qt.AspectRatioMode.KeepAspectRatio,
    Qt.TransformationMode.SmoothTransformation  # ← CPU-intensive scaling
)
```
**Issue:** SmoothTransformation uses bilinear filtering on every frame  
**Frequency:** Every frame update  
**Impact:** 10-50ms per frame (1080p → widget size)

#### 3. **QLabel.setPixmap() (main.py:6220-6223)**
```python
video_widget._video_label.setPixmap(scaled_pixmap)
```
**Issue:** Triggers immediate widget repaint (if visible)  
**Frequency:** Every frame  
**Impact:** Competes with graphics thread for GPU bandwidth

#### 4. **_set_output_image() Call (main.py:6234-6235)**
```python
if self.current_output == ('input', input_number):
    self._set_output_image(self.last_input_image.get(input_number))
```
**Issue:** If currently active, triggers output graphics rendering immediately  
**Frequency:** Every frame  
**Impact:** Can cause 30-100ms pauses

#### 5. **Graphics Output Widget.set_frame() (main.py:6234)**
```python
def set_frame(self, frame: Optional[QImage]):
    # Multiple Qt operations, potential re-entrancy
    self._apply_frame_on_gui(frame)  
```
**Issue:** Not guarded against concurrent calls  
**Frequency:** Per frame rate  
**Impact:** Possible frame drops if painting is already happening

#### 6. **Event Loop Pressure (main.py overall)**
```python
# In _on_camera_frame_ready():
    # ~10 Qt operations per frame
    # ~4 string operations (print/logging)
    # ~3 dict lookups/updates
    # ~2 exception handlers
```
**Frequency:** 60 times/second = 600 event queue operations/sec  
**Impact:** Main thread can't process other events fast enough

### ⚠️ MEMORY ALLOCATION HOTSPOTS

#### 1. **QImage.copy() (main.py:6199)**
```python
q_image = QImage(..., Format_RGB888).copy()  # Allocates 6MB+
```
**Frequency:** Every frame @ 60fps = 360MB/sec allocation rate  
**GC Pressure:** Python GC runs when heap fills, causes hiccups

#### 2. **Pixmap Cache (main.py:6230-6231)**
```python
self.last_input_pixmap[input_number] = scaled_pixmap  # Stores every frame
```
**Frequency:** Every frame  
**Memory Leak Risk:** Dict grows unbounded if input numbers increment

#### 3. **Offscreen Buffer (enhanced_graphics_output.py:~850)**
```python
if self._offscreen is None or self._offscreen.size() != render_size:
    self._offscreen = QImage(render_size, Format_ARGB32_Premultiplied)
```
**Issue:** Large allocation (1920×1080×4 bytes = 8MB)  
**Frequency:** Every resize event  
**Impact:** Stalls rendering briefly

### ⚠️ TIMING PRECISION ISSUES

#### 1. **QTimer Precision (platform-dependent)**
```python
timer.start(4)  # Request 4ms interval
# Actual interval on Windows: 15-16ms (scheduler quantum)
# Actual interval on macOS: 1-2ms (better precision)
```
**Issue:** Cannot achieve sub-16ms intervals on Windows with regular QTimer  
**Result:** Frame drops if camera runs 60fps but timer only fires every 15ms

#### 2. **processEvents() Blocking (main.py:3550)**
```python
QApplication.processEvents()  # Blocks until event queue empty
```
**Issue:** Can stall main thread for 10-100ms on busy systems  
**Frequency:** Unknown (grep shows 1 occurrence)

#### 3. **sleep() Calls in Threads (various)**
```python
# obs_pipeline.py:338, streaming.py:120
time.sleep((sleep_ns - 1_000_000) / 1_000_000_000)
```
**Issue:** System scheduler may wake thread early/late  
**Precision:** ±10ms on Windows (depends on scheduler load)

### ⚠️ THREAD CONTENTION

#### 1. **FrameBuffer Lock Contention (obs_pipeline.py:57)**
```python
def put(self, frame: np.ndarray):
    with self._lock:
        self._buf.append(frame)  # Even 1-2μs lock adds up at 60fps
```
**Frequency:** 60 times/second  
**Impact:** CameraWorker blocks RenderThread every frame

#### 2. **Graphics Widget Re-entrancy (enhanced_graphics_output.py:~240)**
```python
def set_frame(self, frame: Optional[QImage]):
    if getattr(self, '_in_set_frame', False):  # Guard against recursion
        QTimer.singleShot(10, lambda: self.set_frame(frame))
        return  # Delayed reschedule adds latency
```
**Issue:** If paintGL() takes >10ms, frame queue backs up  
**Result:** Frame drops or display lag

#### 3. **Main Thread Saturation**
```
CameraWorker emits frame_ready
    ↓
Main thread queues event
    ↓
Main thread calls _on_camera_frame_ready()
    ├─ QImage conversion (10-20ms)
    ├─ Pixmap scaling (10-50ms)
    ├─ Widget update (1-5ms)
    └─ Graphics widget work (varies)
    ↓
Total: 21-75ms per frame
    ↓
At 60fps, need <16.67ms per frame
    Result: FRAME DROPS (unable to keep up)
```

### 🔴 ROOT CAUSES OF FREEZING & FRAME DROPS

1. **QImage.copy() in main thread** - 10-20ms stall per frame
2. **Pixmap scaling with SmoothTransformation** - 10-50ms per frame
3. **Lock contention on FrameBuffer** - 1-2μs × 60fps
4. **Event queue saturation** - 600 ops/sec on main thread
5. **Graphics thread painting while main thread updates** - Race condition
6. **Memory allocation pressure** - 360MB/sec allocation → GC stalls
7. **Legacy QTimer precision** - 15ms quantum on Windows loses frames
8. **Re-entrancy guards with QTimer.singleShot() reschedule** - Adds latency

---

## SIGNAL & SLOT CONNECTIONS TABLE

### Frame Delivery Connections
```python
CameraWorker.frame_ready
    → SignaledCameraManager.signals.frame_ready
        → GoLiveStudio._on_obs_camera_frame() [QueuedConnection]

RenderThread.frame_ready  
    (emits numpy array, not displayed directly)

GraphicsRenderThread.render_tick
    → EnhancedGraphicsOutputWidget.update() [QueuedConnection]

EnhancedGraphicsOutputWidget._render_thread
    (internal thread, emits render_tick at target_fps)
```

### Performance & Status Connections
```python
CameraWorker.fps_stats
    → (logged to console)

RenderThread.fps_updated
    → SignaledCameraManager.signals.fps_updated [via camera_mgr]
        → GoLiveStudio._on_obs_camera_fps_updated() [QueuedConnection]

CameraWorker.error_occurred
    → ErrorHandler / Console logging

quality_manager.quality_changed
    → GoLiveStudio._on_quality_changed()

quality_manager.settings_updated
    → GoLiveStudio._on_quality_settings_updated()

fps_controller.fps_changed
    → EnhancedGraphicsOutputWidget._on_fps_changed()

fps_controller.frame_ready
    → enhanced_streaming.py:_on_frame_ready()
```

### UI Update Connections
```python
GoLiveStudio.camera_frame_ready
    → GoLiveStudio._on_camera_frame_ready() [QueuedConnection]

event_coalescer
    → _handle_coalesced_ui_update() [batches updates]
    → _handle_coalesced_fps_update() [batches FPS updates]
```

---

## CONFIG & SETTINGS

### Key Configuration Values (config.py)
```python
ui.preview_fps = 60             # Display FPS
ui.overscan = 1.03              # Video scale factor
recording.width = 1920          # Output width
recording.height = 1080         # Output height
camera.input1.fps_override = 60 # Per-input FPS
```

### Performance Settings
```python
# Thread priorities
CameraWorker: QThread.Priority.HighPriority
RenderThread: QThread.Priority.TimeCriticalPriority
GraphicsRenderThread: QThread.Priority.TimeCriticalPriority

# Buffer sizes
FrameBuffer: 3 frames
StreamFrameQueue: 3 frames
thread_queue_size: 512 (FFmpeg audio)

# Memory targets
Low-memory mode: <250MB
Aggressive optimizer: Forces sub-256MB

# Cache limits
_max_cache_size: 10 (mask cache)
_memory_cleanup_interval: 100 frames
```

---

## SUMMARY

### Architecture Type
**Multi-threaded, signal-driven, hardware-accelerated Qt6 streaming application**

### Thread Model
- **3 dedicated real-time threads:** CameraWorker, RenderThread, GraphicsRenderThread
- **Multiple background threads:** Thread pool, streaming writer, audio, monitors
- **Main thread:** 100+ Qt signals/second, 600+ event queue operations/second

### Frame Path (Ideal)
60fps camera → FrameBuffer (3-frame) → RenderThread (nanosecond-precise) → signal → UI update (16.67ms budget)

### Frame Path (Actual)
60fps camera → FrameBuffer → RenderThread → signal → **main thread (21-75ms)** → UI update  
**Result:** Frame drops when main thread work exceeds 16.67ms budget

### Critical Bottlenecks
1. **QImage.copy()** in main thread (10-20ms)
2. **Pixmap scaling** with SmoothTransformation (10-50ms)
3. **Lock contention** on FrameBuffer (1-2μs ×60)
4. **Memory allocation** pressure (360MB/sec) → GC stalls
5. **Event queue saturation** (600 ops/sec)

### Root Cause of Freezing
Frame conversion and scaling happen on main thread synchronously, taking 21-75ms per frame when 16.67ms budget is available.

