from __future__ import annotations
import subprocess
import threading
import sys as _sys
import os
import time as _time
import traceback
import shutil
import tempfile
import queue
from typing import Dict, Optional, Callable, List
from PyQt6.QtCore import QObject, pyqtSignal, QTimer, QProcess, QSize
from PyQt6.QtGui import QImage, QPainter

# Import error handler
try:
    from error_handler import get_error_handler, ErrorSeverity
except ImportError:
    # Fallback if error_handler not available
    def get_error_handler():
        return None
    class ErrorSeverity:
        ERROR = "ERROR"
        WARNING = "WARNING"

# Import encoder selector
try:
    from encoder.encoder_selector import get_encoder_selector
except ImportError:
    get_encoder_selector = None

# Import FFmpeg path resolver
try:
    from ffmpeg_utils import get_ffmpeg_path, verify_ffmpeg
except ImportError:
    # Fallback if ffmpeg_utils is not available
    def get_ffmpeg_path():
        env_path = os.environ.get('GOLIVE_FFMPEG_PATH')
        if env_path and os.path.exists(env_path):
            return env_path
        return 'ffmpeg'
    def verify_ffmpeg(path: str) -> bool:
        try:
            import subprocess as _sub
            p = _sub.run([path, '-version'], capture_output=True, text=True, timeout=5)
            return p.returncode == 0
        except Exception:
            return False


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
        # === DIAGNOSTIC COUNTERS ===
        _stream_frame_count = 0
        _stream_period_count = 0
        _stream_start_time = _time.monotonic()
        _stream_last_report_time = _time.monotonic()
        _stream_last_frame_time = _time.monotonic()
        _stream_dropped_frames = 0
        _stream_consecutive_errors = 0
        _stream_max_frame_interval_ms = 0.0
        
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
                    
                    # === DIAGNOSTIC ONLY ===
                    _stream_frame_count += 1
                    _stream_period_count += 1
                    now = _time.monotonic()
                    frame_interval_ms = (now - _stream_last_frame_time) * 1000
                    _stream_last_frame_time = now
                    _stream_consecutive_errors = 0  # reset on success
                    
                    # Track worst-case jitter
                    if frame_interval_ms > _stream_max_frame_interval_ms:
                        _stream_max_frame_interval_ms = frame_interval_ms
                    
                    # Warn if single frame took too long (jitter spike)
                    if frame_interval_ms > 100:  # >100ms between frames = visible stutter
                        print(f"[STREAM] ⚠ JITTER SPIKE: frame took {frame_interval_ms:.1f}ms "
                              f"(frame #{_stream_frame_count}) "
                              f"| streaming.py → writer loop")
                    
                    # Report every 5 seconds
                    if now - _stream_last_report_time >= 5.0:
                        elapsed = now - _stream_start_time
                        avg_fps = _stream_frame_count / elapsed if elapsed > 0 else 0
                        period_fps = _stream_period_count / 5.0
                        fps_status = "✅" if period_fps >= 28 else "⚠" if period_fps >= 20 else "❌"
                        print(f"[STREAM] {fps_status} Delivering: {avg_fps:.2f}fps avg | "
                              f"Last 5s: {period_fps:.1f}fps | "
                              f"Total: {_stream_frame_count} frames | "
                              f"Dropped: {_stream_dropped_frames} | "
                              f"Worst jitter: {_stream_max_frame_interval_ms:.1f}ms")
                        _stream_last_report_time = now
                        _stream_period_count = 0
                        _stream_max_frame_interval_ms = 0.0  # reset jitter tracker
                    
                except BrokenPipeError as e:
                    _stream_consecutive_errors += 1
                    _diag_error("FFmpeg pipe broke — FFmpeg may have crashed or stream disconnected",
                                e, 
                                f"Frame #{_stream_frame_count} | "
                                f"File: streaming.py | "
                                f"Consecutive errors: {_stream_consecutive_errors}")
                    if _stream_consecutive_errors >= 3:
                        print(f"[STREAM] ❌ FATAL: {_stream_consecutive_errors} consecutive pipe errors "
                              f"— stream is dead | streaming.py")
                        self._running = False
                        break
                    
                except OSError as e:
                    _stream_consecutive_errors += 1
                    _diag_error("OS error writing to FFmpeg pipe",
                                e,
                                f"Frame #{_stream_frame_count} | "
                                f"File: streaming.py | "
                                f"errno: {e.errno}")
                    
                except Exception as e:
                    _stream_consecutive_errors += 1
                    _diag_error("Unexpected error in stream writer loop",
                                e,
                                f"Frame #{_stream_frame_count} | File: streaming.py")
            elif frame_bytes is None:
                # === DROPPED FRAME COUNTER ===
                _stream_dropped_frames += 1
                now_drop = _time.monotonic()
                if _stream_dropped_frames % 10 == 0:
                    print(f"[STREAM] ⚠ {_stream_dropped_frames} frames dropped | "
                          f"streaming.py → frame provider returned None | "
                          f"Elapsed: {now_drop - _stream_start_time:.1f}s")
                if _stream_dropped_frames % 100 == 0:
                    print(f"[STREAM] ❌ HIGH DROP COUNT: {_stream_dropped_frames} total drops — "
                          f"check _provide_stream_frame() in main.py")

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



class StreamController(QObject):
    """Streams program output by rendering frames and piping to FFmpeg via stdin.

    A/V sync (from recording.py):
      - probesize 32, analyzeduration 0: reduce startup analysis delay
      - fflags +genpts+discardcorrupt+nobuffer: reduce pipe buffering
      - thread_queue_size 512: smaller queue for video pipe and dshow audio
      - setpts=PTS-STARTPTS on video: reset video PTS to align with audio
      - asetpts=PTS-STARTPTS, aresample=async on audio
      - -bf 0 -rc-lookahead 0 (libx264) / -bf 0 (NVENC/QSV): no B-frame buffer delay
      - -fps_mode cfr: stable mux timestamps

    Usage:
      - set_frame_provider(callable returning QImage of target size)
      - start(settings_dict)
      - stop()
      - on_log(callback) to receive ffmpeg logs
    """

    # Signals for UI status updates
    statusChanged = pyqtSignal(str)  # "Started", "Stopped", "Error: ...", "Reconnecting..."

    def __init__(self, parent=None):
        super().__init__(parent)
        self._proc: Optional[QProcess] = None
        self._timer = QTimer(self)
        try:
            # Use precise timer to minimize drift between frames
            from PyQt6.QtCore import Qt as _Qt
            self._timer.setTimerType(_Qt.TimerType.PreciseTimer)
        except Exception:
            pass
        self._timer.timeout.connect(self._send_frame)
        self._fps = 60
        self._size = QSize(1920, 1080)
        self._frame_provider: Optional[Callable[[QSize], QImage]] = None
        self._log_cb: Optional[Callable[[str], None]] = None
        self._running = False
        self._stderr_thread: Optional[threading.Thread] = None  # unused with QProcess; kept for backward compat
        self._auto_reconnect = True
        self._reconnect_delay_ms = 2000
        self._bitrate_kbps = 6000  # Default within YouTube 4500–9000kbps for 1080p
        self._use_nvenc = None  # legacy flag; kept for backward compat
        self._available_encoders: Optional[set[str]] = None
        self._forced_encoder: Optional[str] = None  # override encoder choice if set
        self._stopping = False
        # Optional PyAV backend for master-clock A/V sync
        self._av_backend = None
        # Reusable buffers
        self._frame_bytes: int = self._size.width() * self._size.height() * 4
        self._resize_canvas: Optional[QImage] = None
        # A/V sync debug: throttle output-time logging
        self._last_av_log_time: float = 0
        # Fix 8B: Rate-limited frame queue
        self._frame_queue: Optional[StreamFrameQueue] = None

    def set_frame_provider(self, provider: Callable[[QSize], QImage]):
        self._frame_provider = provider

    def on_log(self, cb: Callable[[str], None]):
        self._log_cb = cb

    def is_running(self) -> bool:
        # Running if either PyAV backend is active or the QProcess is running
        if not self._running:
            return False
        if self._av_backend is not None:
            return True
        return self._proc is not None and self._proc.state() != QProcess.ProcessState.NotRunning

    def start(self, settings: Dict):
        """Start FFmpeg with given settings.
        settings keys: url, fps, width, height, video_preset, crf, bitrate_kbps, capture_audio, audio_device
        """
        if self.is_running():
            return
        # Cache settings for reconnects
        try:
            self._last_start_settings = dict(settings)
        except Exception:
            self._last_start_settings = settings
        self._fps = int(settings.get('fps', 60))
        self._size = QSize(int(settings.get('width', 1920)), int(settings.get('height', 1080)))
        # Cache frame byte size for raw RGBA
        try:
            self._frame_bytes = int(self._size.width() * self._size.height() * 4)
        except Exception:
            self._frame_bytes = 0
        url = settings.get('url')
        if not url:
            raise ValueError('Streaming URL is required')
        # Respect user-provided scheme (RTMP or RTMPS) without auto-modification
        preset = settings.get('video_preset', 'veryfast')
        crf = str(settings.get('crf', 20))
        # Determine bitrate: if not provided or <=0, compute recommended for resolution/fps
        req_bitrate = int(settings.get('bitrate_kbps', 0) or 0)
        if req_bitrate <= 0:
            req_bitrate = self._recommended_bitrate_kbps(self._size.width(), self._size.height(), self._fps)
        self._bitrate_kbps = int(max(500, req_bitrate))
        # Force H.264 path; hardware-accelerated when available
        forced_codec = (settings.get('codec') or '').strip().lower()
        capture_audio = bool(settings.get('capture_audio', False))
        audio_device = settings.get('audio_device', '') or ''
        program_media_audio_path = settings.get('program_media_audio_path', '') or ''
        av_sync_delay_ms = int(settings.get('av_sync_delay_ms', 0) or 0)
        program_media_audio_start_ms = int(settings.get('program_media_audio_start_ms', 0) or 0)
        # Background music (BGM) settings
        bgm_enabled = bool(settings.get('bgm_enabled', False))
        bgm_playlist: List[str] = settings.get('bgm_playlist', []) or []
        bgm_loop = bool(settings.get('bgm_loop', True))
        try:
            bgm_volume = max(0, min(100, int(settings.get('bgm_volume', 50))))
        except Exception:
            bgm_volume = 50
        # If user enabled audio but didn't choose a device, try to auto-detect a sensible system mix
        if capture_audio and not audio_device:
            try:
                audio_device = self._auto_select_audio_device() or ''
                if audio_device and self._log_cb:
                    self._log_cb(f"Auto-selected audio device: {audio_device}\n")
            except Exception:
                audio_device = ''

        # Determine encoder (prefer platform HW H.264 if available; fallback to libx264)
        if forced_codec:
            encoder = forced_codec
        else:
            encoder = self._forced_encoder or self._get_best_video_encoder()

        # Optional: use PyAV-based master clock backend for precise A/V sync
        use_av_master = bool(settings.get('use_av_master_clock', False))
        if use_av_master:
            try:
                from av_streamer import AVMasterClockRTMPStreamer
            except Exception as e:
                if self._log_cb:
                    self._log_cb(f"PyAV backend unavailable, falling back to pipe: {e}\n")
                use_av_master = False

        # Direct passthrough (bypass compositing) takes precedence over PyAV backend
        direct_passthrough = bool(settings.get('direct_passthrough', False))
        media_path = (settings.get('program_media_audio_path') or '').strip()

        if direct_passthrough and media_path:
            # Build a pass-through command that sends the selected media directly to RTMP
            # without piping raw frames from the app. Audio can be copied when compatible.
            from pathlib import Path as _Path
            ext = _Path(media_path).suffix.lower()
            is_audio_only = ext in ['.mp3', '.wav', '.aac', '.m4a', '.flac']

            cmd = ['-loglevel', 'info', '-hide_banner']

            if is_audio_only:
                # Input 0: audio file at native rate; Input 1: synthetic black video
                if program_media_audio_start_ms > 0:
                    ss_seconds = max(0.0, program_media_audio_start_ms / 1000.0)
                    cmd += ['-ss', f'{ss_seconds:.3f}']
                cmd += ['-re', '-thread_queue_size', '1024', '-i', media_path]
                # Synthetic video matching target resolution/FPS
                cmd += ['-f', 'lavfi', '-r', str(self._fps), '-i', f"color=size={self._size.width()}x{self._size.height()}:color=black"]

                # Map: 1:v:0 (color video), 0:a:0 (audio file)
                # Video must be H.264 yuv420p for YouTube RTMP
                # For direct passthrough (FFmpeg-generated synthetic video), prefer CPU OR stable GPU encoders
                direct_encoder = encoder if encoder in ['h264_qsv', 'h264_amf', 'h264_videotoolbox', 'libx264'] else 'libx264'
                vopts = ['-map', '1:v:0', '-c:v', direct_encoder,
                         '-g', str(max(2, int(self._fps) * 2)), '-pix_fmt', 'yuv420p',
                         '-preset', preset, '-profile:v', 'high', '-level', '4.2',
                         '-b:v', f"{max(500, self._bitrate_kbps)}k", '-maxrate', f"{max(500, self._bitrate_kbps)}k",
                         '-bufsize', f"{2*max(500,self._bitrate_kbps)}k"]
                # Audio: copy MP3/AAC when possible, else transcode to AAC
                aopts = ['-map', '0:a:0']
                if ext in ['.mp3', '.aac', '.m4a']:
                    aopts += ['-c:a', 'copy']
                else:
                    aopts += ['-c:a', 'aac', '-b:a', '192k', '-ar', '48000', '-ac', '2']
                tail = ['-flvflags', 'no_duration_filesize', '-vsync', 'vfr', '-f', 'flv', '-rtmp_live', 'live', '-rw_timeout', '15000000', url]  # Fix 8C
                cmd = cmd + vopts + aopts + tail
            else:
                # Video file. Attempt stream copy where compatible (common: H.264/AAC in MP4/MOV)
                if program_media_audio_start_ms > 0:
                    ss_seconds = max(0.0, program_media_audio_start_ms / 1000.0)
                    cmd += ['-ss', f'{ss_seconds:.3f}']
                cmd += ['-re', '-thread_queue_size', '1024', '-i', media_path]
                # Try to copy both streams; many MP4s are already H.264/AAC
                # If ingest rejects, user can disable passthrough.
                # Use optional audio map so files without audio don't error (-map 0:a:0?)
                cmd += ['-map', '0:v:0', '-map', '0:a:0?', '-c:v', 'copy', '-c:a', 'copy',
                        '-shortest', '-flvflags', 'no_duration_filesize', '-vsync', 'vfr', '-f', 'flv', '-rtmp_live', 'live', '-rw_timeout', '15000000', url]  # Fix 8C

            # Launch QProcess using the same start logic as below
            try:
                cmd_str = ' '.join(f'"{arg}"' if ' ' in arg else arg for arg in ['ffmpeg'] + cmd)
                if self._log_cb:
                    self._log_cb(f"Starting FFmpeg (pass-through): {cmd_str}\n")
                proc = QProcess(self)
                proc.setProcessChannelMode(QProcess.ProcessChannelMode.SeparateChannels)
                proc.readyReadStandardError.connect(self._on_ffmpeg_stderr)
                proc.errorOccurred.connect(self._on_ffmpeg_error)
                proc.finished.connect(self._on_ffmpeg_finished)
                ffmpeg_path = get_ffmpeg_path()
                if self._log_cb:
                    self._log_cb(f"Using FFmpeg binary: {ffmpeg_path}\n")
                try:
                    ok = verify_ffmpeg(ffmpeg_path)
                except Exception:
                    ok = False
                if not ok:
                    raise RuntimeError(f"FFmpeg binary not executable or not working: {ffmpeg_path}")
                proc.start(ffmpeg_path, cmd)
                if not proc.waitForStarted(8000):
                    raise RuntimeError('Failed to start FFmpeg process (timeout).')
                self._proc = proc
                self._running = True
                # Do NOT start frame timer in pass-through mode
                if self._log_cb:
                    self._log_cb(f"FFmpeg pass-through started (PID: {self._proc.processId()})\n")
                self.statusChanged.emit("Started")
                return
            except Exception as e:
                raise RuntimeError(f'Failed to start FFmpeg process (pass-through): {e}') from e

        if use_av_master:
            # Start AV backend; no QProcess or timer used in this mode
            self._bitrate_kbps = int(max(500, self._bitrate_kbps))
            self._running = True
            try:
                self._av_backend = AVMasterClockRTMPStreamer(
                    frame_provider=self._frame_provider,
                    width=self._size.width(),
                    height=self._size.height(),
                    fps=self._fps,
                    url=url,
                    audio_device=audio_device if capture_audio else None,
                    encoder=encoder,
                    video_bitrate_kbps=self._bitrate_kbps,
                    log_cb=self._log_cb,
                    resolve_avf_index=self._resolve_avfoundation_audio_index,
                )
                self._av_backend.start()
                if self._log_cb:
                    self._log_cb("Started PyAV master-clock backend.\n")
                self.statusChanged.emit("Started")
                return
            except Exception as e:
                if self._log_cb:
                    self._log_cb(f"Failed to start PyAV backend, falling back to FFmpeg pipe: {e}\n")
                # fall through to pipe mode

        # Build ffmpeg command: read raw BGR24 frames from stdin and push to RTMP
        # Fix 8A: Use BGR24 instead of RGBA (3 bytes/pixel vs 4 = 25% less bandwidth)
        # A/V sync (from recording.py): probesize/analyzeduration reduce startup delay;
        # fflags genpts+discardcorrupt+nobuffer reduce pipe buffering; thread_queue_size 512 = less buffer
        cmd = [
            '-loglevel', 'info', '-hide_banner',
            '-probesize', '32',
            '-analyzeduration', '0',
            '-fflags', '+genpts+discardcorrupt+nobuffer',
        ]
        # Video from stdin (program output) - smaller queue = less latency, better sync
        # Fix 8A: Changed from 'rgba' to 'bgr24' to reduce pipe bandwidth
        cmd += ['-f', 'rawvideo', '-pix_fmt', 'bgr24',
                '-thread_queue_size', '1024',
                '-s', f'{self._size.width()}x{self._size.height()}',
                '-r', str(self._fps), '-i', 'pipe:0']
        # Optional audio input (or generate silent audio if disabled)
        have_audio = False
        # Compute A/V delay: positive -> delay audio, negative -> delay video.
        # For MIC: audio is often behind (dshow buffer). Default 0 - do NOT delay audio further.
        try:
            audio_delay_ms = int(av_sync_delay_ms) if int(av_sync_delay_ms) > 0 else 0
        except Exception:
            audio_delay_ms = 0
        try:
            video_delay_ms = abs(int(av_sync_delay_ms)) if int(av_sync_delay_ms) < 0 else 0
        except Exception:
            video_delay_ms = 0
        # A/V sync (from recording.py): Always reset video PTS to 0 to align with audio asetpts=PTS-STARTPTS.
        # When video needs delay, add it on top of the reset.
        vfilter_str = 'setpts=PTS-STARTPTS'
        if video_delay_ms > 0:
            vfilter_str = f"setpts=PTS-STARTPTS+{video_delay_ms/1000.0:.3f}/TB"
        # If BGM is enabled, we will mute program audio entirely (exclusive BGM)
        # Determine this BEFORE adding any audio inputs so we can skip non-BGM inputs.
        use_bgm = bool(bgm_enabled and len(bgm_playlist) > 0)

        # Prefer direct media-file audio when available (safest and in-sync with media file),
        # but only if BGM is NOT enabled. When BGM is enabled, skip adding any other audio input
        # so that BGM becomes the first and only audio input (index 1).
        if (not use_bgm) and program_media_audio_path:
            # If user hasn't set a delay yet, apply minimal default to prevent delay buildup
            # Further reduced to prevent audio delay accumulation
            if av_sync_delay_ms == 0:
                av_sync_delay_ms = 50  # Minimal default delay to prevent buildup
                if self._log_cb:
                    self._log_cb("A/V delay not set; applying minimal 50 ms for media audio.\n")
            # Seek audio to current playback pos; buffer input to tolerate jitter
            if program_media_audio_start_ms > 0:
                ss_seconds = max(0.0, program_media_audio_start_ms / 1000.0)
                cmd += ['-ss', f'{ss_seconds:.3f}']
            cmd += ['-thread_queue_size', '1024', '-i', program_media_audio_path]
            have_audio = True
        elif (not use_bgm) and capture_audio and audio_device:
            import sys as _sys
            if _sys.platform == 'darwin':
                # avfoundation audio only input: ":<index>". Resolve name -> index for reliability.
                idx = self._resolve_avfoundation_audio_index(audio_device) or audio_device
                # If resolution failed, ffmpeg may still accept a direct name; prefer index if available
                cmd += ['-f', 'avfoundation', '-i', f':{idx}']
                have_audio = True
            elif _sys.platform.startswith('win'):
                # Use dshow audio with large buffer
                # Fix 8E: Increased from 500K to 100M to prevent audio overflow under load
                cmd += [
                    '-thread_queue_size', '1024',
                    '-rtbufsize', '100M',   # Fix 8E: Large buffer for streaming stability (was 500K)
                    '-f', 'dshow',
                    '-i', f'audio={audio_device}',
                ]
                have_audio = True
            else:
                # On Linux, user can specify ALSA/Pulse inputs; allow raw string pass-through
                cmd += ['-f', 'pulse', '-i', audio_device]
                have_audio = True
        else:
            if not use_bgm:
                # Provide a silent stereo 48kHz audio source to satisfy ingest requirements
                cmd += ['-f', 'lavfi', '-i', 'anullsrc=cl=stereo:r=48000']
                have_audio = True
        # Log audio/video connection status and sync delays for terminal visibility
        if self._log_cb:
            audio_src = "BGM" if use_bgm else ("media file" if program_media_audio_path else ("microphone" if (capture_audio and audio_device) else "silent (anullsrc)"))
            self._log_cb(f"[STREAM] Video: {self._size.width()}x{self._size.height()} @ {self._fps}fps, encoder: {encoder}\n")
            self._log_cb(f"[STREAM] Audio: {audio_src}\n")
            self._log_cb(f"[STREAM] A/V sync: video_delay_ms={video_delay_ms}, audio_delay_ms={audio_delay_ms}\n")
            if capture_audio and audio_device:
                self._log_cb(f"[STREAM] Audio device: {audio_device}\n")
        # Encoding and output
        # Map streams: 0 = video from pipe, 1 = audio if present
        # Use 2-second keyframe interval as recommended by YouTube: g = 2 * fps
        gop = str(max(2, int(self._fps) * 2))
        # YouTube CBR: set b:v, maxrate, bufsize
        bv = f"{max(500, self._bitrate_kbps)}k"
        # YouTube requires yuv420p for RTMP ingest
        pix_fmt = 'yuv420p'
        common_video_opts = ['-c:v', encoder,
                             '-g', gop, '-keyint_min', gop, '-sc_threshold', '0',
                             '-pix_fmt', pix_fmt]
        if encoder == 'libx264':
            # x264 tuned for low-latency live; -bf 0 -rc-lookahead 0 = no buffer delay (A/V sync)
            common_video_opts += ['-preset', preset, '-tune', 'zerolatency', '-profile:v', 'high', '-level', '4.2']
            common_video_opts += ['-g', gop, '-keyint_min', gop, '-sc_threshold', '0']
            common_video_opts += ['-bf', '0', '-rc-lookahead', '0']
            common_video_opts += ['-b:v', bv, '-maxrate', bv, '-bufsize', f"{2*max(500,self._bitrate_kbps)}k"]
        elif encoder == 'h264_nvenc':
            # NVENC: GPU-accelerated H.264 with low-latency real-time preset
            common_video_opts += ['-preset', 'p4', '-tune', 'll', '-rc', 'cbr', '-profile:v', 'high', '-rc-lookahead', '0', '-bf', '0']
            common_video_opts += ['-b:v', bv, '-maxrate', bv, '-bufsize', f"{2*max(500,self._bitrate_kbps)}k"]
        elif encoder == 'h264_videotoolbox':
            # VideoToolbox real-time CBR
            common_video_opts += ['-profile:v', 'high', '-realtime', '1']
            common_video_opts += ['-b:v', bv, '-maxrate', bv, '-bufsize', f"{2*max(500,self._bitrate_kbps)}k"]
        elif encoder == 'h264_qsv':
            # Intel QuickSync: GPU-accelerated H.264 with low-latency preset
            common_video_opts += ['-preset', 'medium', '-profile:v', 'high', '-look_ahead', '0', '-bf', '0']
            common_video_opts += ['-b:v', bv, '-maxrate', bv, '-bufsize', f"{2*max(500,self._bitrate_kbps)}k"]
        elif encoder == 'h264_amf':
            # AMD AMF: GPU-accelerated H.264 with low-latency quality
            common_video_opts += ['-quality', 'speed', '-rc', 'cbr', '-profile:v', 'high']
            common_video_opts += ['-b:v', bv, '-maxrate', bv, '-bufsize', f"{2*max(500,self._bitrate_kbps)}k"]
        else:
            # Generic fallback H.264-compatible options
            common_video_opts += ['-profile:v', 'high']
            common_video_opts += ['-b:v', bv, '-maxrate', bv, '-bufsize', f"{2*max(500,self._bitrate_kbps)}k"]
        # Suppress duration/filesize warnings on live FLV
        flv_opts = ['-flvflags', 'no_duration_filesize']
        # rtmp live mode and IO timeout to avoid indefinite hangs
        rtmp_opts = ['-rtmp_live', 'live', '-rw_timeout', '15000000']  # 15s timeout

        # If BGM is enabled, add it as the sole audio source (mute program audio)
        bgm_input_added = False
        if use_bgm:
            # Build BGM input. For multiple files, use concat demuxer file list.
            if len(bgm_playlist) == 1:
                if bgm_loop:
                    cmd += ['-stream_loop', '-1']
                # Read input at native rate to ensure real-time playback
                cmd += ['-re', '-thread_queue_size', '1024', '-i', bgm_playlist[0]]
                bgm_input_added = True
            elif len(bgm_playlist) > 1:
                # Create a temporary concat list file
                try:
                    list_fd, list_path = tempfile.mkstemp(prefix='bgm_', suffix='.txt')
                    with os.fdopen(list_fd, 'w', encoding='utf-8') as f:
                        for p in bgm_playlist:
                            escaped_p = p.replace("\\", "\\\\").replace("'", "\\'")
                            f.write(f"file '{escaped_p}'\n")
                    # Note: -stream_loop typically not supported with concat demuxer; ignoring loop for multi-file
                    cmd += ['-re', '-thread_queue_size', '1024', '-f', 'concat', '-safe', '0', '-i', list_path]
                    bgm_input_added = True
                    # Keep path to remove later if needed
                    self._bgm_concat_list_path = list_path
                except Exception as e:
                    if self._log_cb:
                        self._log_cb(f"Failed to build BGM playlist: {e}\n")
                    use_bgm = False
        # Build filters
        vfilter_opts = ['-vf', vfilter_str] if vfilter_str else []

        if use_bgm and bgm_input_added:
            # Sole audio path: BGM only at index 1
            afilters = ['asetpts=PTS-STARTPTS', f"volume={bgm_volume/100.0:.2f}"]
            if audio_delay_ms > 0:
                afilters.append(f"adelay={audio_delay_ms}|{audio_delay_ms}")
            afilters.append('aresample=async=1000:min_hard_comp=0.100:first_pts=0')
            audio_sync_opts = ['-af', ','.join(afilters)]
            cmd += (
                ['-map', '0:v:0', '-map', '1:a:0']
                + vfilter_opts
                + common_video_opts
                + ['-c:a', 'aac', '-b:a', '192k', '-ar', '48000', '-ac', '2']
                + audio_sync_opts
                + flv_opts
                + ['-vsync', 'vfr', '-async', '1', '-f', 'flv']
                + rtmp_opts
                + [url]
            )
        elif have_audio:
            # We have program audio (index 1). Optionally add BGM as additional input (index 2)
            # Single input audio path
            afilters = ['asetpts=PTS-STARTPTS']
            if audio_delay_ms > 0:
                afilters.append(f"adelay={audio_delay_ms}|{audio_delay_ms}")
            afilters.append('aresample=async=1000:min_hard_comp=0.100:first_pts=0')
            audio_sync_opts = ['-af', ','.join(afilters)]
            cmd += (
                ['-map', '0:v:0', '-map', '1:a:0']
                + vfilter_opts
                + common_video_opts
                + ['-c:a', 'aac', '-b:a', '192k', '-ar', '48000', '-ac', '2']
                + audio_sync_opts
                + flv_opts
                + ['-vsync', 'vfr', '-async', '1', '-f', 'flv']
                + rtmp_opts
                + [url]
            )
        else:
            # No program audio. If BGM is enabled and added, use it as the sole audio input.
            if use_bgm and bgm_input_added:
                afilters = ['asetpts=PTS-STARTPTS', f"volume={bgm_volume/100.0:.2f}"]
                if audio_delay_ms > 0:
                    afilters.append(f"adelay={audio_delay_ms}|{audio_delay_ms}")
                afilters.append('aresample=async=1000:min_hard_comp=0.100:first_pts=0')
                audio_sync_opts = ['-af', ','.join(afilters)]
                cmd += (
                    ['-map', '0:v:0', '-map', '1:a:0']
                    + vfilter_opts
                    + common_video_opts
                    + ['-c:a', 'aac', '-b:a', '192k', '-ar', '48000', '-ac', '2']
                    + audio_sync_opts
                    + flv_opts
                    + ['-vsync', 'vfr', '-async', '1', '-f', 'flv']  # Fix 8C: vfr instead of cfr, async for A/V sync
                    + rtmp_opts
                    + [url]
                )
            else:
                # Video-only; still allow video delay if requested
                cmd += ['-map', '0:v:0'] + vfilter_opts + common_video_opts + flv_opts + ['-vsync', 'vfr', '-async', '1', '-f', 'flv'] + rtmp_opts + [url]

        try:
            # Debug: log the exact FFmpeg command
            cmd_str = ' '.join(f'"{arg}"' if ' ' in arg else arg for arg in ['ffmpeg'] + cmd)
            if self._log_cb:
                self._log_cb(f"Starting FFmpeg: {cmd_str}\n")
                self._log_cb(f"Encoder: {encoder}, pix_fmt: {pix_fmt}, bitrate: {bv}\n")
            # Start QProcess
            proc = QProcess(self)
            proc.setProcessChannelMode(QProcess.ProcessChannelMode.SeparateChannels)
            # Connect signals directly to instance methods so Qt auto-disconnects if `self` is deleted
            proc.readyReadStandardError.connect(self._on_ffmpeg_stderr)
            proc.errorOccurred.connect(self._on_ffmpeg_error)
            proc.finished.connect(self._on_ffmpeg_finished)
            # Launch using resolved FFmpeg path
            ffmpeg_path = get_ffmpeg_path()
            if self._log_cb:
                self._log_cb(f"Using FFmpeg binary: {ffmpeg_path}\n")
            # Verify FFmpeg works before starting QProcess (prevents false timeouts on bad paths)
            try:
                ok = verify_ffmpeg(ffmpeg_path)
            except Exception:
                ok = False
            if not ok:
                # Try alternates (system/Homebrew) when bundled or env path fails
                if self._log_cb:
                    self._log_cb(f"Primary FFmpeg failed verification: {ffmpeg_path}. Trying alternates...\n")
                alternates = []
                try:
                    found = shutil.which('ffmpeg')
                    if found:
                        alternates.append(found)
                except Exception:
                    pass
                alternates.extend(['/opt/homebrew/bin/ffmpeg', '/usr/local/bin/ffmpeg', '/usr/bin/ffmpeg'])
                selected = None
                for alt in alternates:
                    if alt and os.path.exists(alt) and os.access(alt, os.X_OK):
                        try:
                            if verify_ffmpeg(alt):
                                selected = alt
                                break
                        except Exception:
                            continue
                if selected:
                    if self._log_cb:
                        self._log_cb(f"Falling back to FFmpeg: {selected}\n")
                    ffmpeg_path = selected
                else:
                    # Provide quarantine hint if path looks like bundled
                    if 'ffmpeg/ffmpeg' in (ffmpeg_path or '') and self._log_cb:
                        self._log_cb("Hint: On macOS, a quarantined bundled FFmpeg may fail to run. You can remove quarantine with: xattr -d com.apple.quarantine '<path-to-ffmpeg>'\n")
                    raise RuntimeError(f"FFmpeg binary not executable or not working: {ffmpeg_path}")
            try:
                # === DIAGNOSTIC: FFmpeg startup ===
                print(f"\n[STREAM] ╭──────────────────────────────────────────")
                print(f"[STREAM] 🔴 FFmpeg process starting")
                print(f"[STREAM]    FFmpeg path: {ffmpeg_path}")
                print(f"[STREAM]    File: streaming.py")
                print(f"[STREAM]    Time: {_time.strftime('%H:%M:%S')}")
                print(f"[STREAM] ╪─────────────────────────────────────────\n")
                proc.start(ffmpeg_path, cmd)
            except FileNotFoundError as e:
                _diag_error("FFmpeg executable not found — check FFmpeg installation",
                            e,
                            f"File: streaming.py | "
                            f"Expected path: {ffmpeg_path}")
                raise
            except Exception as e:
                _diag_error("Failed to start FFmpeg process",
                            e, 
                            f"File: streaming.py | Command args: {cmd[:4]}")
                raise
            
            # === DIAGNOSTIC: Verify process started ===
            if not proc.waitForStarted(8000):
                raise RuntimeError('Failed to start FFmpeg process (timeout).')
            self._proc = proc
        except FileNotFoundError as e:
            raise RuntimeError('FFmpeg not found. Please install ffmpeg and ensure it is in PATH.') from e
        except Exception as e:
            raise RuntimeError(f'Failed to start FFmpeg process: {e}') from e

        self._running = True

        # Fix 8B: Start the rate-limited frame queue
        self._frame_queue = StreamFrameQueue(target_fps=self._fps, max_queue_size=3)
        self._frame_queue.start(self._proc, target_fps=self._fps, log_cb=self._log_cb)

        # Start frame timer - use precise timing for streaming
        interval = max(4, int(1000 / max(1, self._fps)))  # Allow >60fps
        self._timer.start(interval)
        
        # === DIAGNOSTIC: Confirm startup success ===
        print(f"[STREAM] ✅ FFmpeg started successfully (PID: {self._proc.processId()})")
        print(f"[STREAM]    Target FPS: {self._fps}")
        print(f"[STREAM]    Resolution: {self._size.width()}x{self._size.height()}")
        print(f"[STREAM]    File: streaming.py\n")
        
        # Log startup success
        if self._log_cb:
            self._log_cb(f"FFmpeg process started (PID: {self._proc.processId()})\n")
        self.statusChanged.emit("Started")

    def stop(self):
        # === DIAGNOSTIC: Stream stop ===
        print(f"\n[STREAM] 🛑 Stopping stream controller")
        print(f"[STREAM]    File: streaming.py")
        try:
            import time as _stop_time
            print(f"[STREAM]    Time: {_stop_time.strftime('%H:%M:%S')}")
        except Exception:
            pass
        print(f"[STREAM]\n")
        if not self.is_running():
            return
        try:
            self._stopping = True
            # Stop PyAV backend if running
            if self._av_backend is not None:
                try:
                    self._av_backend.stop()
                except Exception:
                    pass
                self._av_backend = None
            # Stop frame queue (Fix 8B)
            if self._frame_queue:
                self._frame_queue.stop()
                self._frame_queue = None
            # Stop pipe-based process
            self._timer.stop()
            if self._proc:
                try:
                    # Close stdin (signals EOF) and terminate
                    self._proc.closeWriteChannel()
                except Exception:
                    pass
                try:
                    self._proc.terminate()
                    self._proc.waitForFinished(3000)
                except Exception:
                    try:
                        self._proc.kill()
                    except Exception:
                        pass
        finally:
            self._running = False
            self._proc = None
            self.statusChanged.emit("Stopped")
            # Clear stopping flag after we've transitioned to stopped
            self._stopping = False
            # Cleanup temp concat list if created
            try:
                if hasattr(self, '_bgm_concat_list_path') and self._bgm_concat_list_path:
                    import os as _os
                    try:
                        _os.remove(self._bgm_concat_list_path)
                    except Exception:
                        pass
                    self._bgm_concat_list_path = None
            except Exception:
                pass

    def _send_frame(self):
        """Send a frame to FFmpeg stdin using the rate-limited queue (Fix 8B)"""
        if not self.is_running() or not self._frame_provider:
            return
        
        try:
            # Get frame from provider
            img = self._frame_provider(self._size)
            if img is None or img.isNull():
                if self._log_cb:
                    self._log_cb("Warning: Received null frame from provider\n")
                return
            
            # Ensure correct size
            if img.size() != self._size:
                if (self._resize_canvas is None or
                        self._resize_canvas.size() != self._size or
                        self._resize_canvas.format() != QImage.Format.Format_RGBA8888):
                    self._resize_canvas = QImage(self._size, QImage.Format.Format_RGBA8888)
                self._resize_canvas.fill(0)
                painter = QPainter(self._resize_canvas)
                painter.drawImage(0, 0, img)
                painter.end()
                img = self._resize_canvas
            
            # Ensure RGBA8888 format
            if img.format() != QImage.Format.Format_RGBA8888:
                img = img.convertToFormat(QImage.Format.Format_RGBA8888)
            
            # Fix 8A: Convert RGBA to BGR24 (3 bytes/pixel instead of 4)
            # Get raw RGBA bytes first
            frame_len = self._size.width() * self._size.height() * 4  # RGBA
            rgba_data = img.bits().asstring(frame_len)
            
            # Convert RGBA to BGR24 using numpy (100x faster than Python loop)
            try:
                import numpy as np
                
                # Convert RGBA bytes to numpy array and reshape to pixels
                arr = np.frombuffer(rgba_data, dtype=np.uint8).reshape(-1, 4)
                bgr24 = arr[:, [2, 1, 0]]  # Take B, G, R channels (drop A)
                frame_bytes = bgr24.tobytes()
            except Exception:
                # Fallback: use RGBA directly if conversion fails
                if self._log_cb:
                    self._log_cb("Warning: RGBA->BGR24 conversion failed, using RGBA\n")
                frame_bytes = rgba_data
            
            # Fix 8B: Use non-blocking queue instead of direct pipe write
            if self._frame_queue:
                self._frame_queue.put_frame(frame_bytes)
            elif self._proc and self._proc.state() == QProcess.ProcessState.Running:
                # Fallback: if queue not available, write directly (for compatibility)
                try:
                    self._proc.write(frame_bytes)
                except Exception as e:
                    if self._log_cb:
                        self._log_cb(f"FFmpeg write error: {e}\n")
                    self._handle_broken_pipe()

        except BrokenPipeError:
            if self._log_cb:
                self._log_cb("FFmpeg stdin closed - attempting reconnect...\n")
            self._handle_broken_pipe()
        except Exception as e:
            if self._log_cb:
                self._log_cb(f"Frame send error: {e}\n")
            self._handle_broken_pipe()

    def set_fps(self, fps: int):
        """Dynamically update the target FPS for streaming without restarting.
        Adjusts the frame timer interval accordingly.
        """
        try:
            new_fps = int(max(1, min(240, fps)))
            if new_fps == getattr(self, '_fps', None):
                return
            self._fps = new_fps
            interval = max(4, int(1000 / self._fps))
            if self._timer is not None:
                self._timer.setInterval(interval)
            if self._log_cb:
                self._log_cb(f"Streaming FPS updated to {self._fps} (interval={interval}ms)\n")
        except Exception:
            pass

    # --- QProcess handlers and reconnect logic ---
    def _on_ffmpeg_stderr(self):
        try:
            if not self._proc:
                return
            data = bytes(self._proc.readAllStandardError()).decode('utf-8', errors='ignore')
            for line in data.splitlines():
                if line and self._log_cb:
                    self._log_cb(f"FFmpeg: {line}\n")
                # Log when audio+video are connected to output
                low = (line or '').lower()
                if 'stream #0:0' in low and '-> #0:0' in low:
                    if self._log_cb:
                        self._log_cb("[STREAM] Video connected to output\n")
                if ('-> #0:1' in low or 'stream #1:0 -> #0:1' in low) and ('audio' in low or 'aac' in low or 'pcm' in low):
                    if self._log_cb:
                        self._log_cb("[STREAM] Audio connected to output\n")
                # Parse progress "time=HH:MM:SS.ms" for A/V sync debug (throttle to ~every 5s)
                if 'time=' in line and 'bitrate=' in line and self._log_cb:
                    import re as _re
                    m = _re.search(r'time=(\d{2}):(\d{2}):(\d{2}\.\d+)', line)
                    if m:
                        try:
                            h, mi, s = int(m.group(1)), int(m.group(2)), float(m.group(3))
                            out_sec = h * 3600 + mi * 60 + s
                            now = _time.time()
                            if now - getattr(self, '_last_av_log_time', 0) >= 5.0:
                                self._last_av_log_time = now
                                self._log_cb(f"[STREAM] A/V output_time={out_sec:.1f}s (video+audio muxed)\n")
                        except Exception:
                            pass
                # Runtime fallback: NVENC/CUDA unavailable or unknown encoder -> force libx264
                low = (line or '').lower()
                nvenc_fail = 'cannot load nvcuda' in low or 'nvcuda.dll' in low
                encoder_fail = 'unknown encoder' in low or 'error selecting an encoder' in low
                if nvenc_fail or encoder_fail:
                    if self._forced_encoder != 'libx264':
                        self._forced_encoder = 'libx264'
                        if self._log_cb:
                            self._log_cb("NVENC/CUDA unavailable - falling back to libx264 (software) encoder...\n")
                        self._immediate_restart()
                        return
        except Exception:
            pass

    def _on_ffmpeg_error(self, err):
        # === DIAGNOSTIC: Error occurred ===
        _diag_error(f"FFmpeg process error occurred",
                    err,
                    f"File: streaming.py → _on_ffmpeg_error | "
                    f"Error code: {err}")
        if self._log_cb:
            self._log_cb(f"FFmpeg process error: {err}\n")
        # Guard against emitting after deletion during teardown
        try:
            self.statusChanged.emit("Error")
        except RuntimeError:
            return
        self._schedule_reconnect()

    def _on_ffmpeg_finished(self, code: int, status):
        # === DIAGNOSTIC: Process finished ===
        print(f"\n[STREAM] ⬛ FFmpeg exited")
        print(f"[STREAM]    Exit code: {code}")
        print(f"[STREAM]    Status: {status}")
        print(f"[STREAM]    File: streaming.py")
        print(f"[STREAM]    Time: {_time.strftime('%H:%M:%S')}\n")
        if self._log_cb:
            self._log_cb(f"FFmpeg exited with code {code}, status {status}\n")
        if self._running and not self._stopping:
            # Unexpected exit while streaming
            self._schedule_reconnect()

    def _handle_broken_pipe(self):
        # Stop current process and schedule reconnection if enabled
        try:
            if self._proc:
                try:
                    self._proc.closeWriteChannel()
                except Exception:
                    pass
                try:
                    self._proc.kill()
                except Exception:
                    pass
        finally:
            self._proc = None
            if self._running:
                self._schedule_reconnect()

    def _schedule_reconnect(self):
        if not self._auto_reconnect:
            self.stop()
            return
        if self._log_cb:
            self._log_cb("Attempting to reconnect in 2s...\n")
        self.statusChanged.emit("Reconnecting...")
        # Restart ffmpeg with last settings; to do so we need to keep last settings
        # For simplicity, we stop and expect caller to call start() again via dialog; or cache settings
        # We'll cache minimal settings necessary to restart
        try:
            # Cache restart via a timer callback capturing current parameters
            last = {
                'width': self._size.width(),
                'height': self._size.height(),
                'fps': self._fps,
                'bitrate_kbps': self._bitrate_kbps,
            }
            # We cannot recover URL/audio here without stored settings; so store them on start
        except Exception:
            last = None
        if hasattr(self, '_last_start_settings') and self._last_start_settings:
            settings = dict(self._last_start_settings)
        else:
            settings = None

        def do_restart():
            if not self._running:
                return
            if settings:
                try:
                    self._start_with_cached_settings(settings)
                except Exception as e:
                    if self._log_cb:
                        self._log_cb(f"Reconnect failed: {e}\n")
                    # Try again later
                    QTimer.singleShot(self._reconnect_delay_ms, do_restart)

        QTimer.singleShot(self._reconnect_delay_ms, do_restart)

    def _start_with_cached_settings(self, settings: Dict):
        # Re-run start without resetting _running
        try:
            # Start a new FFmpeg and keep timer running; writes will resume when proc is up
            # Build URL etc. by delegating to start(), but preserve _running flag
            self._running = True
            self.start(settings)
        except Exception as e:
            raise e

    def _immediate_restart(self):
        """Stop current process and restart quickly with cached settings (no 2s delay)."""
        try:
            if self._proc:
                try:
                    self._proc.closeWriteChannel()
                except Exception:
                    pass
                try:
                    self._proc.kill()
                except Exception:
                    pass
        finally:
            self._proc = None
            settings = getattr(self, '_last_start_settings', None)
            if settings:
                self._start_with_cached_settings(settings)

    # --- Source switch notification ---
    def on_source_switch(self, delay_ms: int = 150):
        """Notify backend that program source has switched.
        In PyAV master-clock mode, clears buffered audio and applies a small delay so new
        source audio does not lead video. In pipe/FFmpeg mode, no-op (FFmpeg filter graph
        would be required to emulate adelay dynamically).
        """
        try:
            if self._av_backend is not None:
                self._av_backend.source_switched(int(max(0, delay_ms)))
                if self._log_cb:
                    self._log_cb(f"Applied source switch with audio delay {int(max(0, delay_ms))} ms (PyAV)\n")
        except Exception as e:
            # Log error for debugging
            error_handler = get_error_handler()
            if error_handler:
                error_handler.log_error(f"Error in source switch: {e}", ErrorSeverity.WARNING)

    # --- Public API for A/V resync when media scrubs while live ---
    def resync_to_media(self, media_path: str, start_ms: int):
        """Re-align streaming to the given media path and position while keeping video from the app.
        Updates cached settings and performs a quick restart so audio and video remain in sync.
        """
        try:
            if not self.is_running():
                return
            if not hasattr(self, '_last_start_settings') or not self._last_start_settings:
                return
            # If no media available (switched to overlays/camera), disable passthrough and restart pipeline mode
            if not media_path:
                if bool(self._last_start_settings.get('direct_passthrough', False)):
                    self._last_start_settings['direct_passthrough'] = False
                    # Also clear media-specific fields
                    self._last_start_settings['program_media_audio_path'] = ''
                    self._last_start_settings['program_media_audio_start_ms'] = 0
                    if self._log_cb:
                        self._log_cb("Source switched to non-media: disabling direct passthrough and restarting pipeline mode.\n")
                    self._immediate_restart()
                return
            # Media available: keep passthrough if enabled and update offsets
            self._last_start_settings['program_media_audio_path'] = media_path
            self._last_start_settings['program_media_audio_start_ms'] = int(max(0, start_ms or 0))
            # Disable device capture when using direct media audio
            self._last_start_settings['capture_audio'] = False
            self._last_start_settings['audio_device'] = ''
            # Fast restart to apply new media/position
            self._immediate_restart()
        except Exception as e:
            if self._log_cb:
                self._log_cb(f"Resync error: {e}\n")

    def update_av_delay_and_resync(self, delay_ms: int, media_path: Optional[str] = None, start_ms: Optional[int] = None):
        """Apply a new A/V delay (ms) and restart quickly to take effect. If media_path/start_ms
        are provided (for Option A), also align audio to the current media position.
        """
        try:
            if not hasattr(self, '_last_start_settings') or not self._last_start_settings:
                return
            self._last_start_settings['av_sync_delay_ms'] = int(max(0, delay_ms or 0))
            if media_path is not None:
                self._last_start_settings['program_media_audio_path'] = media_path
            if start_ms is not None:
                self._last_start_settings['program_media_audio_start_ms'] = int(max(0, start_ms or 0))
            if self.is_running():
                self._immediate_restart()
        except Exception as e:
            if self._log_cb:
                self._log_cb(f"Update A/V delay error: {e}\n")

    def _select_best_encoder(self) -> str:
        """Detect available encoders and choose the best one for this platform."""
        try:
            encs = self._detect_available_encoders()
            import sys as _sys
            if _sys.platform == 'darwin' and 'h264_videotoolbox' in encs:
                return 'h264_videotoolbox'
            if _sys.platform.startswith('win') and 'h264_qsv' in encs:
                return 'h264_qsv'
            if 'h264_nvenc' in encs:
                return 'h264_nvenc'
            if _sys.platform.startswith('win') and 'h264_amf' in encs:
                return 'h264_amf'
            if 'h264_qsv' in encs:
                return 'h264_qsv'
        except Exception:
            pass
        return 'libx264'

    def _get_best_video_encoder(self) -> str:
        """Intelligently select GPU video encoder with automatic fallback.
        Tests for NVIDIA NVENC → Intel QuickSync → AMD AMF → libx264."""
        try:
            encs = self._detect_available_encoders()
            
            # Prioritize by platform and GPU availability
            import sys as _sys
            
            # Test encoders in priority order
            gpu_encoders = [
                ('h264_nvenc', 'NVIDIA NVENC'),
                ('h264_qsv', 'Intel QuickSync'),
                ('h264_amf', 'AMD AMF'),
            ]
            
            # Platform-specific adjustments
            if _sys.platform == 'darwin':
                # macOS: VideoToolbox is preferred
                if 'h264_videotoolbox' in encs:
                    if self._log_cb:
                        self._log_cb("[ENCODE] ✅ Using Apple VideoToolbox (GPU encoding)\n")
                    return 'h264_videotoolbox'
            elif _sys.platform.startswith('win'):
                # Windows: Try GPU encoders, prioritize QSV for Intel systems
                if 'h264_qsv' in encs:
                    if self._log_cb:
                        self._log_cb("[ENCODE] ✅ Using Intel QuickSync (GPU encoding)\n")
                    return 'h264_qsv'
            
            # Try remaining GPU encoders
            for encoder_name, encoder_label in gpu_encoders:
                if encoder_name in encs:
                    if self._log_cb:
                        self._log_cb(f"[ENCODE] ✅ Using {encoder_label} (GPU encoding)\n")
                    return encoder_name
            
            # No GPU encoder found; fallback to software
            if self._log_cb:
                self._log_cb("[ENCODE] ⚠ Using libx264 (CPU encoding) — no GPU encoder found\n")
            return 'libx264'
            
        except Exception as e:
            error_handler = get_error_handler()
            if error_handler:
                error_handler.log_error(f"Error selecting encoder: {e}", ErrorSeverity.WARNING)
            if self._log_cb:
                self._log_cb(f"[ENCODE] ⚠ Using libx264 (CPU encoding) — selection error: {e}\n")
            return 'libx264'

    def _select_best_h264_encoder(self) -> str:
        """Prefer hardware H.264 encoders per platform; fallback to libx264."""
        try:
            # Use centralized encoder selector if available
            if get_encoder_selector:
                selector = get_encoder_selector(get_ffmpeg_path())
                return selector.select_best_h264_encoder()
            
            # Fallback to old logic (Windows: QSV before NVENC for Intel Iris Xe laptops)
            encs = self._detect_available_encoders()
            import sys as _sys
            if _sys.platform == 'darwin' and 'h264_videotoolbox' in encs:
                return 'h264_videotoolbox'
            if _sys.platform.startswith('win') and 'h264_qsv' in encs:
                return 'h264_qsv'
            if 'h264_nvenc' in encs:
                return 'h264_nvenc'
            if _sys.platform.startswith('win') and 'h264_amf' in encs:
                return 'h264_amf'
            if 'h264_qsv' in encs:
                return 'h264_qsv'
        except Exception as e:
            error_handler = get_error_handler()
            if error_handler:
                error_handler.log_error(f"Error selecting encoder: {e}", ErrorSeverity.WARNING)
        return 'libx264'

    def _recommended_bitrate_kbps(self, w: int, h: int, fps: int) -> int:
        """Return a recommended CBR bitrate for YouTube Live for given resolution/fps."""
        # Conservative high-quality ranges; pick the upper end for maximum allowed within typical limits
        try:
            pixels = max(1, int(w) * int(h))
            f = int(max(1, fps))
            if pixels >= 3840*2160:  # 4K
                return 51000 if f > 30 else 45000
            if pixels >= 2560*1440:  # 1440p
                return 24000 if f > 30 else 16000
            if pixels >= 1920*1080:  # 1080p
                return 9000 if f > 30 else 6000
            if pixels >= 1280*720:   # 720p
                return 6000 if f > 30 else 4500
            # lower resolutions
            return 3000
        except Exception:
            return 6000

    # --- macOS device helpers ---
    def _resolve_avfoundation_audio_index(self, target_name: str) -> Optional[str]:
        """Return the AVFoundation audio device index (as string) matching the given name.
        Uses `ffmpeg -f avfoundation -list_devices true -i ""` and performs fuzzy matching.
        """
        try:
            import sys as _sys
            if _sys.platform != 'darwin':
                return None
            ffmpeg_path = get_ffmpeg_path()
            res = subprocess.run(
                [ffmpeg_path, '-f', 'avfoundation', '-list_devices', 'true', '-i', ''],
                capture_output=True, text=True, timeout=3
            )
            text = (res.stdout or '') + '\n' + (res.stderr or '')
            # Parse lines like: "[AVFoundation input device @ ...] [0] Built-in Microphone"
            import re
            candidates: list[tuple[str, str]] = []  # (index_str, name)
            pattern = re.compile(r"AVFoundation input device.*?\[(\d+)\]\s*(.*)$")
            for raw in text.splitlines():
                l = raw.strip()
                if 'AVFoundation input device' not in l:
                    continue
                m = pattern.search(l)
                if m:
                    idx = m.group(1).strip()
                    name = m.group(2).strip()
                    if idx and name:
                        candidates.append((idx, name))
            # Fuzzy match by containment (case-insensitive)
            tn = (target_name or '').lower()
            best = None
            for idx, name in candidates:
                n = (name or '').lower()
                if tn == n:
                    best = idx; break
                if tn and tn in n:
                    best = idx
            if best:
                if self._log_cb:
                    self._log_cb(f"Mapped audio device '{target_name}' to AVFoundation index {best}\n")
                return best
            # Fallback: return None to allow name-based invocation
            if self._log_cb:
                self._log_cb(f"Could not map audio device '{target_name}' to index; using name.\n")
            return None
        except Exception:
            return None

    def _detect_available_encoders(self) -> set[str]:
        if self._available_encoders is not None:
            return self._available_encoders
        encs: set[str] = set()
        try:
            ffmpeg_path = get_ffmpeg_path()
            res = subprocess.run([ffmpeg_path, '-hide_banner', '-v', 'quiet', '-encoders'], capture_output=True, text=True)
            text = (res.stdout or '') + '\n' + (res.stderr or '')
            for line in text.splitlines():
                # lines look like: " V....D h264_videotoolbox ..."
                parts = line.strip().split()
                if len(parts) >= 2 and parts[0].startswith(('V', 'A', '.')):
                    encs.add(parts[1])
        except Exception:
            pass
        self._available_encoders = encs
        return encs

    # --- Audio auto-detection helpers ---
    def _auto_select_audio_device(self) -> Optional[str]:
        """Try to find a loopback/system-mix device automatically.
        Returns a device identifier to be passed as `audio_device` in start().
        macOS (avfoundation): returns a device name or index string usable after ':'
        Windows (dshow): returns the friendly name as used by "audio=<name>"
        Linux: returns None (no auto)
        """
        import sys as _sys
        if _sys.platform == 'darwin':
            return self._auto_select_audio_device_macos()
        if _sys.platform.startswith('win'):
            return self._auto_select_audio_device_windows()
        return None

    def _auto_select_audio_device_macos(self) -> Optional[str]:
        """Parse avfoundation device list and pick BlackHole/Loopback/Soundflower if available; else Built-in Microphone."""
        try:
            ffmpeg_path = get_ffmpeg_path()
            res = subprocess.run(
                [ffmpeg_path, '-f', 'avfoundation', '-list_devices', 'true', '-i', ''],
                capture_output=True, text=True, timeout=3
            )
            text = (res.stdout or '') + '\n' + (res.stderr or '')
            candidates = []
            for line in text.splitlines():
                l = line.strip()
                # Typical format: [AVFoundation input device @ 0x...] [0] Built-in Microphone
                if 'AVFoundation input device' in l and ']' in l:
                    try:
                        parts = l.split(']')
                        name = parts[-1].strip()
                        if name:
                            candidates.append(name)
                    except Exception:
                        pass
            priority = (
                'BlackHole', 'Loopback', 'Soundflower', 'VB-Audio', 'Stereo Mix', 'Built-in Microphone'
            )
            for p in priority:
                for c in candidates:
                    if p.lower() in c.lower():
                        return c
            # fallback first candidate
            return candidates[0] if candidates else None
        except Exception:
            return None

    def _auto_select_audio_device_windows(self) -> Optional[str]:
        """Parse dshow device list and pick Stereo Mix/VB-Audio Cable if available; else default microphone."""
        try:
            ffmpeg_path = get_ffmpeg_path()
            res = subprocess.run(
                [ffmpeg_path, '-list_devices', 'true', '-f', 'dshow', '-i', 'dummy'],
                capture_output=True, text=True, timeout=3
            )
            text = (res.stdout or '') + '\n' + (res.stderr or '')
            in_audio = False
            names = []
            for line in text.splitlines():
                l = line.strip()
                if 'DirectShow audio devices' in l:
                    in_audio = True
                    continue
                if in_audio and 'DirectShow video devices' in l:
                    break

                # Header-based parsing: lines like: "Stereo Mix (Realtek(R) Audio)"
                if in_audio and '"' in l:
                    try:
                        name = l.split('"')[1]
                        if name:
                            names.append(name)
                    except Exception:
                        pass

                # Fallback parsing for some FFmpeg builds/log formats (no section headers), e.g.:
                # [in#0 @ ...] "Microphone Array (...)" (audio)
                if (not in_audio) and '(audio)' in l and '"' in l:
                    try:
                        name = l.split('"')[1]
                        if name:
                            names.append(name)
                    except Exception:
                        pass
            priority = (
                'Stereo Mix', 'CABLE Output', 'VB-Audio', 'What U Hear', 'Wave Out Mix', 'Mix', 'Microphone'
            )
            for p in priority:
                for n in names:
                    if p.lower() in n.lower():
                        return n
            return names[0] if names else None
        except Exception:
            return None

# --- Module-level convenience API ---
_global_controller: Optional[StreamController] = None

def _get_controller() -> StreamController:
    global _global_controller
    if _global_controller is None:
        _global_controller = StreamController()
    return _global_controller

def setFrameProvider(provider: Callable[[QSize], QImage]):
    """Set the frame provider used by the module-level controller."""
    _get_controller().set_frame_provider(provider)

def onStreamLog(cb: Callable[[str], None]):
    """Subscribe to FFmpeg log lines for the module-level controller."""
    _get_controller().on_log(cb)

def startStreaming(streamUrl: str, streamKey: str, *,
                   width: int = 1920, height: int = 1080, fps: int = 60,
                   video_preset: str = 'veryfast', crf: int = 20,
                   bitrate_kbps: int = 6000,
                   capture_audio: bool = False, audio_device: str = '') -> None:
    """Start YouTube/RTMP streaming using the module-level controller.
    Joins URL + Key, configures 1080p60 H.264 CBR and AAC per YouTube guidance.
    """
    url = (streamUrl or '').strip()
    key = (streamKey or '').strip()
    if not url or not key:
        raise ValueError('Both streamUrl and streamKey are required')
    if not url.endswith(key):
        joiner = '' if url.endswith('/') else '/'
        url = f"{url}{joiner}{key}"
    settings = {
        'url': url,
        'width': int(width),
        'height': int(height),
        'fps': int(fps),
        'video_preset': str(video_preset),
        'crf': int(crf),
        'bitrate_kbps': int(bitrate_kbps),
        'capture_audio': bool(capture_audio),
        'audio_device': audio_device or '',
    }
    _get_controller().start(settings)

def stopStreaming() -> None:
    """Stop streaming using the module-level controller."""
    _get_controller().stop()
