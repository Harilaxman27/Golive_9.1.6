#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OBS-Style Camera Rendering Pipeline - Implementation Guide
============================================================

This document describes the complete refactoring of the camera rendering pipeline
to achieve stable, locked FPS (exactly 30fps = 30fps, 60fps = 60fps) like OBS Studio.

ARCHITECTURE OVERVIEW
=====================

The new pipeline implements the OBS libobs architecture with three independent components:

1. CAMERA CAPTURE THREAD (CameraWorker)
   - Dedicated QThread that reads frames from OpenCV VideoCapture
   - Runs in tight loop at camera's native speed (unrestricted)
   - Pushes frames into thread-safe FrameBuffer
   - Uses optimal camera settings:
     * CAP_DSHOW on Windows, CAP_V4L2 on Linux (for low-latency capture)
     * BUFFERSIZE=1 (prevents stale frame buffering)
     * MJPEG codec (lower latency on supported cameras)
   - Signals FPS stats back to main thread
   - Never touches Qt or rendering code

2. FRAME BUFFER (FrameBuffer)
   - Thread-safe circular buffer with max 3 frames (like OBS NUM_TEXTURES)
   - Holds latest frames, automatically discards oldest on new frame arrival
   - Synchronized via threading.Lock + threading.Event
   - get_latest() returns newest frame without blocking
   - Used by render thread to fetch the freshest available frame

3. RENDER THREAD (RenderThread)
   - Dedicated QThread running at target FPS (30, 60, etc.)
   - **MOST CRITICAL**: Uses OBS-style nanosecond-precision timing
   - Implements absolute deadline scheduling (NOT relative/reset)
   - Frame deadline advances by exactly frame_interval_ns each cycle
   - Hybrid sleep strategy:
     * Coarse OS sleep for all but last 1ms (CPU/kernel efficient)
     * Busy-wait for final 1ms (nanosecond precision required by OBS)
   - Always emits a frame (reuses last if none available = frame duplication)
   - Only resets deadline if >1 frame behind (prevents cascading lag)
   - Emits Qt signal on main thread for display

TIMING PRECISION (The Core Innovation)
======================================

Unlike traditional QTimer or time.sleep() which have millisecond jitter,
the OBS-style render thread achieves nanosecond-level precision:

    Traditional Approach (DRIFT ACCUMULATES):
    ┌─────┐     ┌─────┐     ┌─────┐
    Frame 1    Frame 2     Frame 3
    Deadline 1 -> Sleep(~33ms) -> Deadline 2 -> Sleep(~33ms) -> Deadline 3
    (drift accumulates from timer inaccuracy)

    OBS Approach (ABSOLUTE DEADLINES):
    Deadline 1 ──────── Deadline 2 ──────── Deadline 3 ────── ...
    (exact 16.67ms intervals, never reset)
       ↓ Frame 1          ↓ Frame 2           ↓ Frame 3
    
The algorithm:
    1. Calculate frame_interval_ns = 1_000_000_000 / target_fps
    2. Set next_frame_ns = NOW
    3. Loop:
       - next_frame_ns += frame_interval_ns  (ADVANCE LINE, don't reset)
       - Get frame from buffer (may reuse last)
       - Emit frame signal
       - Sleep until next_frame_ns nanosecond deadline
       - Repeat

This means:
    ✓ 30fps stays 30fps (no drift)
    ✓ 60fps stays 60fps (no drift)
    ✓ No frame drops from timing issues
    ✓ Consistent frame delivery even if camera lags

HOW IT ALL CONNECTS
===================

Per-Camera Manager (SignaledCameraManager):
    ├─ FrameBuffer (circular, thread-safe)
    │  ├─ CameraWorker (reads from OpenCV in tight loop)
    │  └─ RenderThread (outputs at fixed FPS with OBS timing)
    └─ Signals (frame_ready, fps_updated, error_occurred)

Main Thread Integration:
    1. start_camera_capture() creates SignaledCameraManager for each input
    2. Manager's frame_ready signal connects to _on_obs_camera_frame()
    3. Signals use Qt.QueuedConnection (ensures main thread safety)
    4. _on_obs_camera_frame() converts BGR→RGB and updates UI
    5. stop_camera_capture() stops manager threads gracefully

USAGE FROM MAIN APPLICATION
============================

Starting a camera (from start_camera_capture):
    >>> camera_mgr = SignaledCameraManager(
    ...     input_number=1,
    ...     parent=self,
    ...     device=0,  # /dev/video0 or COM port
    ...     width=1920,
    ...     height=1080,
    ...     fps=60.0
    ... )
    >>> camera_mgr.signals.frame_ready.connect(self._on_obs_camera_frame)
    >>> camera_mgr.start()
    >>> self.camera_managers[1] = camera_mgr

Changing FPS at runtime:
    >>> self.camera_managers[1].set_fps(30.0)

Stopping a camera:
    >>> mgr = self.camera_managers.pop(1)
    >>> mgr.stop()

FALLBACK COMPATIBILITY
======================

If OBS pipeline is unavailable or fails:
    1. Automatically falls back to legacy OpenCV timer-based capture
    2. Uses QTimer with calculated interval (1000ms / fps)
    3. Polls frames via update_camera_frame()
    4. Maintains backward compatibility
    5. Graceful degradation (less precise, but still works)

Qt Camera Path (Untouched):
    - Qt multimedia cameras use signal-driven frame delivery
    - Separate code path, bypasses OBS pipeline entirely
    - Used when QCameraDevice is available
    - Maintains all existing Qt camera functionality

THREAD SAFETY
=============

Frame Buffer Access:
    ✓ threading.Lock protects deque from concurrent access
    ✓ get_latest() doesn't block capture or render
    ✓ put() overwrites oldest, never blocks

Signal Flow:
    ✓ CameraWorker → Buffer → RenderThread → Qt Signal (queued)
    ✓ Qt.QueuedConnection ensures main thread processes all UI updates
    ✓ No cross-thread Qt painting or memory access

PERFORMANCE CHARACTERISTICS
===========================

Latency:
    - Camera read to display: ~3-4 frames (~50-66ms @ 60fps)
    - 1 frame in capture buffer + 1 in render queue + 1 display
    - Compare to OBS: 2-3 frames same reason

CPU Usage:
    - Capture thread: Minimal (just cv2.read() in loop)
    - Render thread: Nanosecond precision with hybrid sleep
      * OS sleep most of frame interval (efficient)
      * 1ms busy-wait (trades CPU for precision, like OBS)
    - Main thread: Only UI updates, no polling

Memory:
    - FrameBuffer(maxlen=3): Stores 3 frames max
    - Example: 1920x1080 BGR = 6.3MB per frame × 3 = 19MB per camera
    - 4 inputs = ~76MB total frame storage

GPU Support:
    - Pure CPU-based (uses OpenCV, no GPU acceleration)
    - Lower power consumption suitable for laptops
    - Easily extended to CUDA/OpenCL if needed

TESTING CHECKLIST
=================

1. FPS Stability:
   □ Start camera at 30fps, verify exactly 30fps output
   □ Start camera at 60fps, verify exactly 60fps output
   □ Change FPS on-the-fly, verify immediate lock to new FPS
   □ Run for 30 seconds, check FPS never drifts >1%

2. Frame Delivery:
   □ No blank/black frames (last frame reused correctly)
   □ No skipped frames (each render outputs)
   □ No dropped frames visible (smooth playback)

3. Latency:
   □ Point camera at clock, measure display lag
   □ Should be consistent, no sudden jumps
   □ Compare Qt camera vs OpenCV paths

4. Multi-Camera:
   □ Start 2+ cameras simultaneously
   □ Each at different FPS (30+60), verify independence
   □ Verify no crosstalk between camera threads

5. Error Handling:
   □ Unplug camera during capture
   □ Verify error signal fires
   □ Verify graceful fallback to last frame
   □ Verify no crashes or hangs

6. Clean Shutdown:
   □ Stop camera while running
   □ Verify threads exit within 1 second
   □ Verify no zombie threads
   □ Verify no resource leaks

DEBUGGING
=========

Enable frame-by-frame tracing (add to RenderThread.run()):
    print(f"[Render] Frame {fps_frame_count} at {time.perf_counter_ns()}")

Check camera stats:
    >>> mgr = self.camera_managers[1]
    >>> print(f"Capture FPS: {mgr.camera_worker._frame_count}")
    >>> print(f"Buffer empty: {mgr.frame_buffer.is_empty()}")

Monitor thread states:
    >>> print(mgr.camera_worker.isRunning())
    >>> print(mgr.render_thread.isRunning())

LIMITATIONS & FUTURE WORK
=========================

Current Limitations:
    - Pure CPU (no GPU acceleration)
    - Nanosecond precision limited by time.perf_counter_ns() resolution
    - 1ms busy-wait only on systems with sleep granularity >1ms
    - No frame skipping on overload (always outputs)

Future Enhancements:
    - GPU frame buffering (faster, lower latency)
    - Adaptive frame skipping (if capture can't keep up)
    - A/V sync with audio timestamps
    - Jitter buffer (absorb network delays)
    - Interpolation (frame blending for smooth motion)

REFERENCES
==========

- libobs source: https://github.com/obsproject/obs-studio/blob/master/libobs/obs-video.c
- OBS architecture: https://github.com/obsproject/obs-studio/wiki/Source-Implementation-Guide
- Qt threading: https://doc.qt.io/qt-6/qthread.html
- Python perf_counter_ns: https://docs.python.org/3/library/time.html#time.perf_counter_ns

==============================================================================
"""
