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
