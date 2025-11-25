from __future__ import annotations
import os
from typing import Optional, Callable, Dict
from PyQt6.QtCore import QObject, QTimer, QSize, QProcess, pyqtSignal, QBuffer, QByteArray
from PyQt6.QtGui import QImage, QPainter

# Import FFmpeg path resolver
try:
    from ffmpeg_utils import get_ffmpeg_path
except ImportError:
    # Fallback if ffmpeg_utils is not available
    def get_ffmpeg_path():
        env_path = os.environ.get('GOLIVE_FFMPEG_PATH')
        if env_path and os.path.exists(env_path):
            return env_path
        return 'ffmpeg'

class RecorderController(QObject):
    """Records program output frames (and optional audio) to a local file using FFmpeg via QProcess.

    Usage:
      - set_frame_provider(callable returning QImage of target size)
      - start(settings_dict)
      - stop()
    settings keys:
      - file_path (str, required)
      - width, height (int)
      - fps (int)
      - video_preset (str) [for libx264], bitrate_kbps (int)
      - capture_audio (bool), audio_device (str)
      - program_media_audio_path (str, optional) to mux direct audio from media file
      - av_sync_delay_ms (int), program_media_audio_start_ms (int)
    """

    statusChanged = pyqtSignal(str)  # "Started", "Stopped", "Error: ..."

    def __init__(self, parent=None):
        super().__init__(parent)
        self._proc: Optional[QProcess] = None
        self._timer = QTimer(self)
        try:
            from PyQt6.QtCore import Qt as _Qt
            self._timer.setTimerType(_Qt.TimerType.PreciseTimer)
            self._timer.setSingleShot(False)  # Ensure repeating timer
        except Exception:
            pass
        self._timer.timeout.connect(self._send_frame)
        self._fps = 30
        self._size = QSize(1920, 1080)
        self._frame_provider: Optional[Callable[[QSize], QImage]] = None
        self._log_cb: Optional[Callable[[str], None]] = None
        self._running = False
        self._bitrate_kbps = 12000  # higher default for local recording
        self._forced_encoder: Optional[str] = None
        self._last_start_settings: Optional[Dict] = None
        self._paused: bool = False
        self._frame_count: int = 0
        self._dropped_frames: int = 0
        self._last_frame_time: float = 0

    def set_frame_provider(self, provider: Callable[[QSize], QImage]):
        self._frame_provider = provider

    def on_log(self, cb: Callable[[str], None]):
        self._log_cb = cb

    def is_running(self) -> bool:
        return self._running and self._proc is not None and self._proc.state() != QProcess.ProcessState.NotRunning

    def is_paused(self) -> bool:
        return bool(self._paused)

    def start(self, settings: Dict):
        if self.is_running():
            return
        self._last_start_settings = dict(settings)
        self._fps = int(settings.get('fps', 30))
        self._size = QSize(int(settings.get('width', 1920)), int(settings.get('height', 1080)))
        file_path = (settings.get('file_path') or '').strip()
        if not file_path:
            raise ValueError('Recording file path is required')
        # Ensure destination directory exists
        try:
            import os as _os
            out_dir = _os.path.dirname(file_path) or _os.path.expanduser('~')
            _os.makedirs(out_dir, exist_ok=True)
        except Exception:
            pass
        # Ensure we have a sane extension (default mp4)
        try:
            import os as _os
            if '.' not in _os.path.basename(file_path):
                file_path = file_path + '.mp4'
        except Exception:
            pass
        preset = settings.get('video_preset', 'veryfast')
        self._bitrate_kbps = int(settings.get('bitrate_kbps', self._bitrate_kbps))
        capture_audio = bool(settings.get('capture_audio', False))
        audio_device = settings.get('audio_device', '') or ''
        program_media_audio_path = settings.get('program_media_audio_path', '') or ''
        av_sync_delay_ms = int(settings.get('av_sync_delay_ms', 0) or 0)
        program_media_audio_start_ms = int(settings.get('program_media_audio_start_ms', 0) or 0)

        # Choose encoder (prefer macOS videotoolbox if available)
        encoder = self._select_best_encoder()

        # Build ffmpeg command
        cmd = ['-y', '-loglevel', 'info', '-hide_banner', '-fflags', '+genpts']
        # Video from stdin as MJPEG via image2pipe to reduce pipe bandwidth and ensure robust muxing
        cmd += ['-f', 'image2pipe', '-vcodec', 'mjpeg',
                '-thread_queue_size', '8192',
                '-framerate', str(self._fps), '-i', 'pipe:0']

        # Audio input
        have_audio = False
        if program_media_audio_path:
            if program_media_audio_start_ms > 0:
                ss_seconds = max(0.0, program_media_audio_start_ms / 1000.0)
                cmd += ['-ss', f'{ss_seconds:.3f}']
            cmd += ['-thread_queue_size', '1024', '-i', program_media_audio_path]
            have_audio = True
        elif capture_audio and audio_device:
            import sys as _sys
            if _sys.platform == 'darwin':
                # Allow special 'auto' to probe loopback devices
                if str(audio_device).strip().lower() == 'auto':
                    sel = self._select_mac_loopback_device('')
                else:
                    sel = f":{audio_device}"
                cmd += ['-f', 'avfoundation', '-thread_queue_size', '1024', '-i', sel]
                have_audio = True
            elif _sys.platform.startswith('win'):
                cmd += ['-f', 'dshow', '-i', f'audio={audio_device}']
                have_audio = True
            else:
                cmd += ['-f', 'pulse', '-i', audio_device]
                have_audio = True
        elif capture_audio:
            # Capture default system input if no device specified
            import sys as _sys
            if _sys.platform == 'darwin':
                # Auto-select a likely loopback device (BlackHole/Soundflower/etc.), fallback :0
                sel = self._select_mac_loopback_device('')
                cmd += ['-f', 'avfoundation', '-thread_queue_size', '1024', '-i', sel]
                have_audio = True
                if self._log_cb:
                    self._log_cb(f"Recording audio: using avfoundation device {sel} (auto)\n")
            elif _sys.platform.startswith('win'):
                cmd += ['-f', 'dshow', '-i', 'audio=default']
                have_audio = True
            else:
                cmd += ['-f', 'pulse', '-i', 'default']
                have_audio = True
        else:
            # silent stereo to keep container happy
            cmd += ['-f', 'lavfi', '-i', 'anullsrc=cl=stereo:r=48000']
            have_audio = True

        # Video encoding opts
        gop = str(max(2, int(self._fps) * 2))
        bv = f"{max(1500, self._bitrate_kbps)}k"
        vopts = ['-c:v', encoder, '-g', gop, '-keyint_min', gop, '-sc_threshold', '0', '-pix_fmt', 'yuv420p']
        if encoder == 'libx264':
            vopts += ['-preset', preset, '-profile:v', 'high', '-level', '4.2',
                      '-b:v', bv, '-maxrate', bv, '-bufsize', f"{2*max(1500,self._bitrate_kbps)}k"]
        elif encoder == 'h264_videotoolbox':
            vopts += ['-profile:v', 'high', '-b:v', bv, '-maxrate', bv, '-bufsize', f"{2*max(1500,self._bitrate_kbps)}k"]
        elif encoder == 'h264_nvenc':
            vopts += ['-preset', 'p4', '-rc', 'vbr', '-profile:v', 'high', '-b:v', bv, '-maxrate', bv, '-bufsize', f"{2*max(1500,self._bitrate_kbps)}k"]
        else:
            vopts += ['-b:v', bv]

        # Container based on extension
        ext = file_path.split('.')[-1].lower() if '.' in file_path else 'mp4'
        fmt = 'mp4'
        if ext in ('mov',):
            fmt = 'mov'
        elif ext in ('mkv',):
            fmt = 'matroska'

        if have_audio:
            audio_sync_opts = []
            if program_media_audio_path:
                afilters = ['asetpts=PTS-STARTPTS']
                if av_sync_delay_ms > 0:
                    afilters.append(f"adelay={av_sync_delay_ms}|{av_sync_delay_ms}")
                afilters.append('aresample=async=1000:min_hard_comp=0.100:first_pts=0')
                audio_sync_opts = ['-af', ','.join(afilters)]
            cmd += (
                ['-map', '0:v:0', '-map', '1:a:0']
                + vopts + ['-fps_mode', 'cfr', '-r', str(self._fps)]
                + ['-c:a', 'aac', '-b:a', '192k', '-ar', '48000', '-ac', '2']
                + audio_sync_opts
                + ['-movflags', '+faststart']
                + ['-shortest']
                + ['-f', fmt, file_path]
            )
        else:
            cmd += ['-map', '0:v:0'] + vopts + ['-fps_mode', 'cfr', '-r', str(self._fps), '-movflags', '+faststart', '-shortest', '-f', fmt, file_path]

        # Launch ffmpeg
        try:
            cmd_str = ' '.join(f'"{arg}"' if ' ' in arg else arg for arg in ['ffmpeg'] + cmd)
            if self._log_cb:
                self._log_cb(f"Starting FFmpeg (record): {cmd_str}\n")
            proc = QProcess(self)
            proc.setProcessChannelMode(QProcess.ProcessChannelMode.SeparateChannels)
            proc.readyReadStandardError.connect(self._on_ffmpeg_stderr)
            proc.errorOccurred.connect(self._on_ffmpeg_error)
            proc.finished.connect(self._on_ffmpeg_finished)
            ffmpeg_path = get_ffmpeg_path()
            proc.start(ffmpeg_path, cmd)
            if not proc.waitForStarted(3000):
                raise RuntimeError('Failed to start FFmpeg for recording (timeout).')
            self._proc = proc
        except FileNotFoundError as e:
            raise RuntimeError('FFmpeg not found. Please install ffmpeg and ensure it is in PATH.') from e
        except Exception as e:
            raise RuntimeError(f'Failed to start FFmpeg for recording: {e}') from e

        self._running = True
        self._paused = False
        self._frame_count = 0
        self._dropped_frames = 0
        
        import time
        self._last_frame_time = time.time()
        
        interval = max(16, int(1000 / self._fps))
        if self._log_cb:
            self._log_cb(f"Recording timer starting with {interval}ms interval ({self._fps} fps)\n")
        
        self._timer.start(interval)
        
        # Verify timer is actually running
        if self._timer.isActive():
            if self._log_cb:
                self._log_cb(f"✅ Recording timer is active with {self._timer.interval()}ms interval\n")
        else:
            if self._log_cb:
                self._log_cb(f"❌ Recording timer failed to start!\n")
            raise RuntimeError("Failed to start recording timer")
        
        self.statusChanged.emit('Started')

    def stop(self):
        if not self.is_running():
            return
        try:
            self._timer.stop()
            if self._proc:
                try:
                    # Close stdin to signal EOF and allow ffmpeg to finalize
                    self._proc.closeWriteChannel()
                except Exception:
                    pass
                try:
                    # Give ffmpeg ample time to mux/flush frames on normal EOF
                    if not self._proc.waitForFinished(7000):
                        # Try gentle terminate and wait more
                        self._proc.terminate()
                        if not self._proc.waitForFinished(3000):
                            # As a last resort, kill
                            self._proc.kill()
                except Exception:
                    pass
        finally:
            # Report final statistics
            if self._log_cb:
                self._log_cb(f"Recording stopped. Total frames: {self._frame_count}, Dropped: {self._dropped_frames}\n")
            
            self._running = False
            self._proc = None
            self._paused = False
            self.statusChanged.emit('Stopped')

    def _send_frame(self):
        if not self.is_running() or not self._frame_provider:
            return
        
        import time
        current_time = time.time()
        
        try:
            # Get frame from provider
            img = self._frame_provider(self._size)
            if img is None or img.isNull():
                if self._log_cb and self._frame_count < 10:  # Only log first few null frames
                    self._log_cb(f"Frame provider returned null/empty image (frame {self._frame_count})\n")
                return
            
            # Resize if needed
            if img.size() != self._size:
                canvas = QImage(self._size, QImage.Format.Format_RGBA8888)
                canvas.fill(0)
                p = QPainter(canvas)
                p.drawImage(0, 0, img)
                p.end()
                img = canvas
                
            # Convert to a format suitable for JPEG encode (let Qt handle conversion)
            if img.format() not in (QImage.Format.Format_RGB888, QImage.Format.Format_RGBA8888, QImage.Format.Format_ARGB32):
                img = img.convertToFormat(QImage.Format.Format_RGB888)
            
            # Check if FFmpeg process is still running
            if self._proc and self._proc.state() == QProcess.ProcessState.Running:
                # Backpressure guard: drop frame if too much pending in pipe
                try:
                    pending = int(self._proc.bytesToWrite())
                except Exception:
                    pending = 0
                    
                # Allow up to ~8MB pending in pipe for MJPEG stream
                max_pending = 8 * 1024 * 1024
                if pending > max_pending:
                    self._dropped_frames += 1
                    if self._log_cb:
                        self._log_cb(f"Dropping frame {self._frame_count} due to backpressure (pending={pending})\n")
                    return
                
                # Encode frame to JPEG in-memory and write to FFmpeg stdin
                buf = QBuffer()
                buf.open(QBuffer.OpenModeFlag.WriteOnly)
                img.save(buf, b"JPEG", 85)
                frame_bytes: QByteArray = buf.data()
                buf.close()
                bytes_written = self._proc.write(frame_bytes)
                try:
                    # Encourage the OS to flush data to ffmpeg promptly
                    self._proc.waitForBytesWritten(5)
                except Exception:
                    pass
                
                if bytes_written != len(frame_bytes):
                    if self._log_cb:
                        self._log_cb(f"Warning: Only wrote {bytes_written}/{len(frame_bytes)} bytes for frame {self._frame_count}\n")
                
                self._frame_count += 1
                
                # Log progress every 30 frames (every ~1 second at 30fps)
                if self._frame_count % 30 == 0:
                    elapsed = current_time - self._last_frame_time
                    actual_fps = 30 / elapsed if elapsed > 0 else 0
                    if self._log_cb:
                        self._log_cb(f"Recording: {self._frame_count} frames, {actual_fps:.1f} fps, {self._dropped_frames} dropped\n")
                    self._last_frame_time = current_time
                    
            else:
                if self._log_cb:
                    self._log_cb(f"FFmpeg process not running, stopping recording\n")
                self.stop()
                
        except Exception as e:
            if self._log_cb:
                self._log_cb(f"Frame capture error: {e}\n")
            # Stop on persistent errors
            self.stop()

    # --- Pause/Resume ---
    def pause(self):
        """Pause recording in a cross-platform way by stopping the frame timer and flagging paused.
        Note: When capturing system audio directly via FFmpeg, audio input may continue during pause.
        """
        if not self.is_running() or self._paused:
            return
        self._timer.stop()
        self._paused = True
        self.statusChanged.emit('Paused')

    def resume(self):
        """Resume recording in a cross-platform way by restarting the frame timer."""
        if not self.is_running() or not self._paused:
            return
        interval = max(16, int(1000 / self._fps))
        self._timer.start(interval)
        self._paused = False
        self.statusChanged.emit('Started')

    def _on_ffmpeg_stderr(self):
        try:
            if not self._proc:
                return
            data = bytes(self._proc.readAllStandardError()).decode('utf-8', errors='ignore')
            if self._log_cb:
                for line in data.splitlines():
                    if line:
                        self._log_cb(f"FFmpeg(rec): {line}\n")
        except Exception:
            pass

    def _on_ffmpeg_error(self, err):
        self.statusChanged.emit('Error')

    def _on_ffmpeg_finished(self, code: int, status):
        # Mark stopped if process exits
        self._running = False
        self.statusChanged.emit('Stopped')

    def _select_best_encoder(self) -> str:
        # Prefer platform hardware if present; otherwise libx264
        try:
            import subprocess, sys as _sys
            ffmpeg_path = get_ffmpeg_path()
            res = subprocess.run([ffmpeg_path, '-hide_banner', '-v', 'quiet', '-encoders'], capture_output=True, text=True)
            text = (res.stdout or '') + '\n' + (res.stderr or '')
            encs = set()
            for line in text.splitlines():
                parts = line.strip().split()
                if len(parts) >= 2 and parts[0].startswith(('V', 'A', '.')):
                    encs.add(parts[1])
            if _sys.platform == 'darwin' and 'h264_videotoolbox' in encs:
                return 'h264_videotoolbox'
            if 'h264_nvenc' in encs:
                return 'h264_nvenc'
        except Exception:
            pass
        return 'libx264'

    def _select_mac_loopback_device(self, requested: str = '') -> str:
        """Probe avfoundation devices and return an input index/name for system/loopback audio.
        Priority order: explicit requested, then common loopback device names, then default :0.
        Returns a string suitable for avfoundation like ':<index>' or a device name.
        """
        try:
            import subprocess
            ffmpeg_path = get_ffmpeg_path()
            res = subprocess.run([ffmpeg_path, '-hide_banner', '-f', 'avfoundation', '-list_devices', 'true', '-i', ''], capture_output=True, text=True)
            out = (res.stdout or '') + '\n' + (res.stderr or '')
            candidates = []
            for line in out.splitlines():
                ls = line.strip()
                # Example: [AVFoundation input device @ 0x...] [0] Built-in Microphone
                if ls.startswith('[') and ']' in ls and '[' in ls and ']' in ls:
                    try:
                        if '] [' in ls:
                            idx_part = ls.split('] [', 1)[1]
                        else:
                            continue
                        idx_str, rest = idx_part.split(']', 1)
                        idx = idx_str.strip()
                        name = rest.strip().lstrip(' ').lstrip(':').strip()
                        candidates.append((idx, name))
                    except Exception:
                        continue
            # If explicit requested provided, prefer exact index/name match
            if requested:
                for idx, name in candidates:
                    if requested == idx or requested.lower() in name.lower():
                        if self._log_cb:
                            self._log_cb(f"Recording audio: using requested avfoundation device :{idx} ({name})\n")
                        return f":{idx}"
            # Common loopback names
            preferred = ['blackhole', 'soundflower', 'loopback', 'ishowu', 'vb-cable', 'vb cable', 'cable input']
            for p in preferred:
                for idx, name in candidates:
                    if p in name.lower():
                        if self._log_cb:
                            self._log_cb(f"Recording audio: auto-selected avfoundation device :{idx} ({name})\n")
                        return f":{idx}"
            # Fallback to first audio device index 0
            if self._log_cb:
                self._log_cb("Recording audio: falling back to avfoundation device :0 (no loopback found)\n")
            return ':0'
        except Exception:
            # Final fallback
            if self._log_cb:
                self._log_cb("Recording audio: device probe failed, using :0\n")
            return ':0'
