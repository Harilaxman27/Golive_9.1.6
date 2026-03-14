#!/usr/bin/env python3
"""
Enhanced Streaming Module with Global FPS Control
Integrates with fps_controller for precise timing
"""

import subprocess
import threading
import time
import queue
import numpy as np
from typing import Optional, Dict, Any
from PyQt6.QtCore import QObject, pyqtSignal
from fps_controller import get_fps_controller, FrameTimestamp
import cv2


class StreamFrameQueue:
    """
    Fix 8B: Bounded frame queue for streaming output with rate limiting.
    Drops oldest frames when full (never blocks the render thread).
    Rate-limited writer ensures FFmpeg pipe never gets flooded.
    Uses absolute nanosecond deadline timing (OBS-style precision).
    """
    def __init__(self, target_fps, max_queue_size=3):
        self._queue = queue.Queue(maxsize=max_queue_size)
        self._target_fps = target_fps
        self._frame_interval_ns = int(1_000_000_000 / target_fps)
        self._running = False
        self._pipe = None
        self._writer_thread = None
        self._last_frame = None
    
    def start(self, pipe, target_fps):
        """Start the rate-limited writer thread."""
        self._pipe = pipe
        self._target_fps = target_fps
        self._frame_interval_ns = int(1_000_000_000 / target_fps)
        self._running = True
        self._writer_thread = threading.Thread(
            target=self._write_loop, daemon=True, name="StreamPipeWriter"
        )
        self._writer_thread.start()
    
    def put_frame(self, frame_bytes):
        """Non-blocking — drops oldest frame if queue is full (Fix 8B)."""
        try:
            self._queue.put_nowait(frame_bytes)
        except queue.Full:
            # Drop oldest frame to make room (like OBS frame drop under load)
            try:
                self._queue.get_nowait()
                self._queue.put_nowait(frame_bytes)
                print("[STREAM] Queue full, dropped oldest frame to prevent backpressure")
            except queue.Empty:
                pass
    
    def _write_loop(self):
        """
        Writes frames to FFmpeg pipe at EXACTLY target_fps using absolute deadline timing.
        Same OBS-style nanosecond precision as RenderThread (Fix 8B).
        """
        frame_interval_ns = self._frame_interval_ns
        next_frame_ns = time.perf_counter_ns()
        last_frame = None
        
        while self._running:
            # Step 1: Advance absolute deadline
            next_frame_ns += frame_interval_ns
            
            # Step 2: Get next frame (or reuse last if none available)
            try:
                frame_bytes = self._queue.get_nowait()
                last_frame = frame_bytes
            except queue.Empty:
                frame_bytes = last_frame  # Frame duplication — keeps CFR intact
            
            # Step 3: Write to pipe if we have a frame
            if frame_bytes is not None and self._pipe is not None:
                try:
                    self._pipe.stdin.write(frame_bytes)
                    self._pipe.stdin.flush()
                except (BrokenPipeError, OSError) as e:
                    print(f"[STREAM] Pipe error, stopping write loop: {e}")
                    self._running = False
                    break
            
            # Step 4: Precision sleep to absolute deadline
            sleep_ns = next_frame_ns - time.perf_counter_ns()
            if sleep_ns > 1_000_000:
                # Coarse sleep for efficiency, minus 1ms
                time.sleep((sleep_ns - 1_000_000) / 1_000_000_000)
                # Busy-wait final 1ms for nanosecond precision
                while time.perf_counter_ns() < next_frame_ns:
                    pass
            elif sleep_ns > 0:
                # Less than 1ms remaining — just busy-wait
                while time.perf_counter_ns() < next_frame_ns:
                    pass
            elif sleep_ns < -frame_interval_ns:
                # Fell more than 1 full frame behind — resync to now
                next_frame_ns = time.perf_counter_ns()
    
    def stop(self):
        """Stop the writer thread."""
        self._running = False
        if self._writer_thread:
            self._writer_thread.join(timeout=2.0)


class TimedFFmpegEncoder(QObject):
    """
    FFmpeg encoder with rate-limited streaming (Fix 8B) and A/V sync fixes.
    Uses StreamFrameQueue to prevent pipe backpressure.
    Implements fixes 8A (BGR24), 8C (A/V sync), 8E (audio buffer).
    """
    
    # Signals
    encoding_started = pyqtSignal()
    encoding_stopped = pyqtSignal()
    frame_encoded = pyqtSignal(int)  # frame number
    error_occurred = pyqtSignal(str)
    
    def __init__(self, output_url: str, width: int = 1920, height: int = 1080):
        super().__init__()
        
        self.output_url = output_url
        self.width = width
        self.height = height
        
        # FPS controller integration
        self.fps_controller = get_fps_controller()
        self.target_fps = self.fps_controller.get_target_fps()
        
        # FFmpeg process
        self.ffmpeg_process: Optional[subprocess.Popen] = None
        self.encoding_thread: Optional[threading.Thread] = None
        
        # Use StreamFrameQueue instead of raw queue (Fix 8B)
        self.frame_queue = StreamFrameQueue(self.target_fps, max_queue_size=3)
        
        # Timing control
        self.pts_counter = 0
        self.time_base = 1.0 / self.target_fps
        self.start_time = 0.0
        
        # State
        self.is_encoding = False
        self.should_stop = False
        
        # Connect to FPS controller
        self.fps_controller.fps_changed.connect(self._on_fps_changed)
        self.fps_controller.frame_ready.connect(self._on_frame_ready)
    
    def _build_ffmpeg_command(self) -> list:
        """
        Build FFmpeg command with fixes 8A, 8C, 8E.
        8A: BGR24 instead of RGBA (reduces data by 25%)
        8C: Fix A/V sync with proper flags
        8E: Increase audio buffer from 500K to 100M
        """
        cmd = [
            'ffmpeg',
            '-y',  # Overwrite output
            
            # Input video (Fix 8A: BGR24)
            '-f', 'rawvideo',
            '-vcodec', 'rawvideo',
            '-pix_fmt', 'bgr24',  # Fix 8A: 3 bytes/pixel instead of RGBA 4 bytes
            '-s', f'{self.width}x{self.height}',
            '-r', str(self.target_fps),
            '-i', '-',
        ]
        
        # Audio input if specified (Fix 8E: Large buffer 100M)
        if self.audio_device:
            cmd.extend([
                '-f', 'dshow',
                '-rtbufsize', '100M',  # Fix 8E: Was 500K, now 100M for streaming
                '-thread_queue_size', '1024',  # Extra: Ensure audio queue doesn't fill
                '-i', f'audio="{self.audio_device}"',
            ])
        
        # Video codec settings
        cmd.extend([
            '-c:v', 'libx264',
            '-preset', 'ultrafast',
            '-tune', 'zerolatency',
            '-crf', '23',
            '-maxrate', '6000k',
            '-bufsize', '12000k',
            '-g', str(self.target_fps * 2),
            '-keyint_min', str(self.target_fps),
            '-sc_threshold', '0',
            
            # Fix 8C: A/V sync flags
            # Changed from '-vsync cfr' to '-vsync vfr' to avoid frame duplication
            '-vsync', 'vfr',  # Variable frame rate (don't duplicate on slow input)
            '-async', '1',  # Sync audio to video
            '-time_base', f'1/{self.target_fps}',
            '-fflags', '+genpts',
        ])
        
        # Audio codec and sync filters (Fix 8C)
        if self.audio_device:
            cmd.extend([
                '-c:a', 'aac',
                '-b:a', '128k',
                '-af', 'aresample=async=1000:min_hard_comp=0.100:first_pts=0',  # Fix 8C
            ])
        
        # Output format
        cmd.extend([
            '-f', 'flv' if 'rtmp' in self.output_url else 'mp4',
            self.output_url
        ])
        
        return cmd
    
    def start_encoding(self):
        """Start the FFmpeg encoding process with StreamFrameQueue (Fix 8B)"""
        if self.is_encoding:
            return
        
        try:
            # Reset timing
            self.pts_counter = 0
            self.start_time = self.fps_controller.get_current_time()
            self.should_stop = False
            
            # Build command
            cmd = self._build_ffmpeg_command()
            print(f"[STREAM] Starting FFmpeg: {' '.join(cmd[:10])}... (Fix 8A/8C/8E)")
            
            # Start FFmpeg process
            self.ffmpeg_process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                bufsize=0
            )
            
            # Start StreamFrameQueue writer (Fix 8B)
            self.frame_queue.start(self.ffmpeg_process, self.target_fps)
            
            # Start encoding thread
            self.encoding_thread = threading.Thread(target=self._encoding_loop, daemon=True)
            self.encoding_thread.start()
            
            self.is_encoding = True
            self.encoding_started.emit()
            print(f"[STREAM] Encoder started at {self.target_fps} FPS with rate-limited queue")
            
        except Exception as e:
            self.error_occurred.emit(f"Failed to start encoding: {e}")
    
    def stop_encoding(self):
        """Stop the FFmpeg encoding process"""
        if not self.is_encoding:
            return
        
        self.should_stop = True
        
        # Stop StreamFrameQueue (Fix 8B)
        if self.frame_queue:
            self.frame_queue.stop()
        
        # Close FFmpeg stdin
        if self.ffmpeg_process and self.ffmpeg_process.stdin:
            try:
                self.ffmpeg_process.stdin.close()
            except:
                pass
        
        # Wait for encoding thread
        if self.encoding_thread:
            self.encoding_thread.join(timeout=5.0)
        
        # Terminate FFmpeg process
        if self.ffmpeg_process:
            try:
                self.ffmpeg_process.terminate()
                self.ffmpeg_process.wait(timeout=5.0)
            except:
                try:
                    self.ffmpeg_process.kill()
                except:
                    pass
            self.ffmpeg_process = None
        
        self.is_encoding = False
        self.encoding_stopped.emit()
        print("[STREAM] Encoder stopped")
    
    def _encoding_loop(self):
        """Main encoding loop with precise timing and StreamFrameQueue (Fix 8B)"""
        frame_interval = 1.0 / self.target_fps
        next_frame_time = self.start_time
        
        while not self.should_stop and self.ffmpeg_process:
            try:
                current_time = self.fps_controller.get_current_time()
                
                # Wait for next frame time
                if current_time < next_frame_time:
                    sleep_time = next_frame_time - current_time
                    if sleep_time > 0.001:
                        time.sleep(sleep_time)
                
                # Get frame from queue or use last frame
                frame_data = None
                try:
                    # Try to get the most recent frame
                    while not self.frame_queue._queue.empty():
                        frame_data = self.frame_queue._queue.get_nowait()
                except queue.Empty:
                    pass
                
                if frame_data is not None:
                    # Encode frame with precise PTS (StreamFrameQueue handles rate limiting)
                    self._encode_frame(frame_data)
                    self.frame_encoded.emit(self.pts_counter)
                
                # Update timing
                next_frame_time += frame_interval
                self.pts_counter += 1
                
                # Prevent timing drift
                if next_frame_time < current_time - frame_interval:
                    next_frame_time = current_time
                
            except Exception as e:
                if not self.should_stop:
                    self.error_occurred.emit(f"Encoding error: {e}")
                break
    
    def _encode_frame(self, frame_data: np.ndarray):
        """Encode a single frame (Fix 8B: uses StreamFrameQueue)"""
        if not self.ffmpeg_process:
            return
        
        try:
            # Ensure frame is correct size and format
            if frame_data.shape[:2] != (self.height, self.width):
                frame_data = cv2.resize(frame_data, (self.width, self.height))
            
            # Non-blocking put via StreamFrameQueue (Fix 8B)
            frame_bytes = frame_data.tobytes()
            self.frame_queue.put_frame(frame_bytes)
            
        except Exception as e:
            if not self.should_stop:
                print(f"[STREAM] Frame encoding error: {e}")
    
    def add_frame(self, frame: np.ndarray):
        """Add frame to StreamFrameQueue (Fix 8B: non-blocking)"""
        if not self.is_encoding:
            return
        
        try:
            # Ensure frame is correct format (Fix 8A: BGR24)
            if frame.shape[2] == 4:
                frame = cv2.cvtColor(frame, cv2.COLOR_RGBA2BGR)
            
            # Non-blocking queue put (Fix 8B)
            frame_bytes = frame.tobytes()
            self.frame_queue.put_frame(frame_bytes)
        except Exception as e:
            print(f"[STREAM] Error adding frame: {e}")
    
    def _on_fps_changed(self, new_fps: int):
        """Handle FPS change from controller"""
        if self.target_fps != new_fps:
            print(f"[STREAM] Encoder FPS changing: {self.target_fps} -> {new_fps}")
            
            was_encoding = self.is_encoding
            
            # Stop current encoding
            if was_encoding:
                self.stop_encoding()
            
            # Update settings
            self.target_fps = new_fps
            self.time_base = 1.0 / new_fps
            
            # Restart encoding if it was running
            if was_encoding:
                self.start_encoding()
    
    def _on_frame_ready(self, timestamped_frame: FrameTimestamp):
        """Handle frame ready from FPS controller"""
        if self.is_encoding and hasattr(timestamped_frame, 'frame_data'):
            self.add_frame(timestamped_frame.frame_data)

class EnhancedStreamingManager(QObject):
    """Enhanced streaming manager with global FPS control"""
    
    # Signals
    stream_started = pyqtSignal(str)  # stream URL
    stream_stopped = pyqtSignal()
    stream_error = pyqtSignal(str)
    stats_updated = pyqtSignal(dict)
    
    def __init__(self):
        super().__init__()
        
        # FPS controller
        self.fps_controller = get_fps_controller()
        
        # Encoders
        self.encoders: Dict[str, TimedFFmpegEncoder] = {}
        
        # Statistics
        self.stats = {
            'active_streams': 0,
            'total_frames_encoded': 0,
            'encoding_fps': 0.0,
            'last_frame_time': 0.0
        }
        
        # Connect to FPS controller
        self.fps_controller.timing_stats.connect(self._update_stats)
    
    def start_stream(self, stream_url: str, width: int = 1920, height: int = 1080) -> bool:
        """Start streaming to URL"""
        try:
            if stream_url in self.encoders:
                print(f"Stream already active: {stream_url}")
                return True
            
            # Create encoder
            encoder = TimedFFmpegEncoder(stream_url, width, height)
            encoder.encoding_started.connect(lambda: self.stream_started.emit(stream_url))
            encoder.encoding_stopped.connect(self.stream_stopped.emit)
            encoder.error_occurred.connect(self.stream_error.emit)
            
            # Start encoding
            encoder.start_encoding()
            
            self.encoders[stream_url] = encoder
            self.stats['active_streams'] = len(self.encoders)
            
            print(f"Started stream: {stream_url}")
            return True
            
        except Exception as e:
            self.stream_error.emit(f"Failed to start stream: {e}")
            return False
    
    def stop_stream(self, stream_url: str):
        """Stop streaming to URL"""
        if stream_url in self.encoders:
            encoder = self.encoders[stream_url]
            encoder.stop_encoding()
            del self.encoders[stream_url]
            
            self.stats['active_streams'] = len(self.encoders)
            print(f"Stopped stream: {stream_url}")
    
    def stop_all_streams(self):
        """Stop all active streams"""
        for stream_url in list(self.encoders.keys()):
            self.stop_stream(stream_url)
    
    def add_frame_to_all_streams(self, frame: np.ndarray):
        """Add frame to all active streams"""
        for encoder in self.encoders.values():
            encoder.add_frame(frame)
    
    def _update_stats(self, timing_stats: dict):
        """Update streaming statistics"""
        self.stats.update({
            'encoding_fps': self.fps_controller.get_target_fps(),
            'last_frame_time': timing_stats.get('last_frame_time', 0.0)
        })
        
        # Count total encoded frames
        total_frames = sum(
            encoder.pts_counter for encoder in self.encoders.values()
        )
        self.stats['total_frames_encoded'] = total_frames
        
        self.stats_updated.emit(self.stats.copy())
    
    def get_active_streams(self) -> list:
        """Get list of active stream URLs"""
        return list(self.encoders.keys())
    
    def is_streaming(self) -> bool:
        """Check if any streams are active"""
        return len(self.encoders) > 0

# Global streaming manager instance
enhanced_streaming_manager = EnhancedStreamingManager()

def get_streaming_manager() -> EnhancedStreamingManager:
    """Get the global streaming manager"""
    return enhanced_streaming_manager
