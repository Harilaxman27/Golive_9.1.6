from __future__ import annotations
import os
import subprocess
import threading
import time
from typing import Optional, Callable, Dict
from PyQt6.QtCore import QObject, QTimer, QSize, QProcess, pyqtSignal, QBuffer, QByteArray
from PyQt6.QtGui import QImage, QPainter

# Import FFmpeg path resolver
try:
    from ffmpeg_utils import get_ffmpeg_path
except ImportError:
    def get_ffmpeg_path():
        env_path = os.environ.get('GOLIVE_FFMPEG_PATH')
        if env_path and os.path.exists(env_path):
            return env_path
        return 'ffmpeg'


class SubprocessWrapper(QObject):
    """Wraps subprocess.Popen to provide a QProcess-like interface.

    Used when we need shell=True for proper UTF-8 encoding of FFmpeg device names.
    Mimics QProcess API: start(), write(), closeWriteChannel(), waitForFinished(), etc.
    """
    stateChanged = pyqtSignal(int)
    readyReadStandardError = pyqtSignal()
    finished = pyqtSignal(int, int)
    errorOccurred = pyqtSignal(int)

    class ProcessState:
        NotRunning = 0
        Running = 1

    class ProcessChannelMode:
        SeparateChannels = 0
        MergedChannels = 1

    def __init__(self, parent=None):
        super().__init__(parent)
        self._proc: Optional[subprocess.Popen] = None
        self._state = self.ProcessState.NotRunning
        self._stderr_reader_thread: Optional[threading.Thread] = None
        self._stderr_buffer = b''
        self._stderr_lock = threading.Lock()
        self._pending_bytes = 0
        self._cmd_str = ''

    def setProcessChannelMode(self, mode):
        pass

    def start(self, program: str, args: list = None):
        pass

    def _start_shell(self, cmd_string: str):
        self._cmd_str = cmd_string
        try:
            self._proc = subprocess.Popen(
                cmd_string,
                shell=True,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=False,
                encoding=None,
                errors=None,
                creationflags=0x08000000 if os.name == 'nt' else 0
            )
            self._state = self.ProcessState.Running
            self.stateChanged.emit(self._state)
            self._stderr_reader_thread = threading.Thread(target=self._read_stderr, daemon=True)
            self._stderr_reader_thread.start()
            threading.Thread(target=self._monitor_process, daemon=True).start()
        except Exception:
            self._state = self.ProcessState.NotRunning
            self.errorOccurred.emit(1)
            raise

    def _read_stderr(self):
        if not self._proc:
            return
        try:
            while self._proc.poll() is None or self._proc.stderr:
                data = self._proc.stderr.read(4096)
                if not data:
                    time.sleep(0.01)
                    continue
                with self._stderr_lock:
                    self._stderr_buffer += data
                self.readyReadStandardError.emit()
        except Exception:
            pass

    def _monitor_process(self):
        if not self._proc:
            return
        try:
            code = self._proc.wait()
            self._state = self.ProcessState.NotRunning
            self.stateChanged.emit(self._state)
            time.sleep(0.1)
            self.finished.emit(code, 0)
        except Exception:
            pass

    def write(self, data: QByteArray) -> int:
        if not self._proc or not self._proc.stdin:
            return 0
        try:
            if isinstance(data, QByteArray):
                data_bytes = bytes(data)
            else:
                data_bytes = data if isinstance(data, bytes) else data.encode() if isinstance(data, str) else bytes(data)
            self._proc.stdin.write(data_bytes)
            self._proc.stdin.flush()
            self._pending_bytes += len(data_bytes)
            return len(data_bytes)
        except Exception:
            return 0

    def bytesToWrite(self) -> int:
        return max(0, self._pending_bytes)

    def waitForBytesWritten(self, timeout_ms=5000) -> bool:
        if self._proc and self._proc.stdin:
            try:
                self._proc.stdin.flush()
                self._pending_bytes = 0
                return True
            except Exception:
                return False
        return False

    def closeWriteChannel(self):
        if self._proc and self._proc.stdin:
            try:
                self._proc.stdin.close()
            except Exception:
                pass

    def state(self):
        if self._proc:
            if self._proc.poll() is None:
                return self.ProcessState.Running
        return self.ProcessState.NotRunning

    def waitForFinished(self, timeout_ms=30000) -> bool:
        if not self._proc:
            return True
        try:
            timeout_sec = timeout_ms / 1000.0 if timeout_ms > 0 else None
            self._proc.wait(timeout=timeout_sec)
            return True
        except subprocess.TimeoutExpired:
            return False
        except Exception:
            return False

    def terminate(self):
        if self._proc:
            try:
                self._proc.terminate()
            except Exception:
                pass

    def kill(self):
        if self._proc:
            try:
                self._proc.kill()
            except Exception:
                pass

    def readAllStandardError(self) -> QByteArray:
        with self._stderr_lock:
            data = self._stderr_buffer
            self._stderr_buffer = b''
        result = QByteArray()
        for byte_val in data:
            result.append(byte_val)
        return result


class RecorderController(QObject):
    """Records program output frames (and optional audio) to a local file using FFmpeg via QProcess.

    KEY FIX (A/V sync):
      - Added -bf 0 / -rc_lookahead 0 to eliminate x264 frame buffering delay
      - Added -probesize 32 -analyzeduration 0 to reduce FFmpeg startup latency
      - Added setpts=PTS-STARTPTS video filter to align video PTS with audio PTS
      - Added -fflags +discardcorrupt+nobuffer to reduce pipe buffering
      - Changed fps_mode to cfr for stable mux timing

    Usage:
      - set_frame_provider(callable returning QImage of target size)
      - start(settings_dict)
      - stop()
    """

    statusChanged = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._proc: Optional[QProcess] = None
        self._timer = QTimer(self)
        try:
            from PyQt6.QtCore import Qt as _Qt
            self._timer.setTimerType(_Qt.TimerType.PreciseTimer)
            self._timer.setSingleShot(False)
        except Exception:
            pass
        self._timer.timeout.connect(self._send_frame)
        self._fps = 30
        self._size = QSize(1920, 1080)
        self._frame_provider: Optional[Callable[[QSize], QImage]] = None
        self._log_cb: Optional[Callable[[str], None]] = None
        self._running = False
        self._bitrate_kbps = 12000
        self._forced_encoder: Optional[str] = None
        self._last_start_settings: Optional[Dict] = None
        self._paused: bool = False
        self._frame_count: int = 0
        self._dropped_frames: int = 0
        self._last_frame_time: float = 0
        self._audio_retry_done: bool = False

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
        self._audio_retry_done = bool(settings.get('audio_retry_done', False))
        self._fps = int(settings.get('fps', 30))
        self._size = QSize(int(settings.get('width', 1920)), int(settings.get('height', 1080)))
        file_path = (settings.get('file_path') or '').strip()
        if not file_path:
            raise ValueError('Recording file path is required')
        try:
            import os as _os
            out_dir = _os.path.dirname(file_path) or _os.path.expanduser('~')
            _os.makedirs(out_dir, exist_ok=True)
        except Exception:
            pass
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
        force_silent_audio = bool(settings.get('force_silent_audio', False))
        program_media_audio_path = settings.get('program_media_audio_path', '') or ''
        av_sync_delay_ms = int(settings.get('av_sync_delay_ms', 0) or 0)
        program_media_audio_start_ms = int(settings.get('program_media_audio_start_ms', 0) or 0)

        encoder = self._select_best_encoder()

        # ---------------------------------------------------------------
        # Build FFmpeg command
        # KEY SYNC FIXES applied here:
        #   1. -probesize 32 -analyzeduration 0  → no startup analysis delay
        #   2. -fflags +genpts+discardcorrupt+nobuffer → reduce pipe buffering
        #   3. -bf 0 -rc_lookahead 0             → no B-frame buffer delay
        #   4. setpts=PTS-STARTPTS video filter  → reset video PTS to 0
        #   5. asetpts=PTS-STARTPTS audio filter → reset audio PTS to 0
        #   6. -vsync cfr (was passthrough)      → stable mux timestamps
        # ---------------------------------------------------------------
        cmd = [
            '-y',
            '-loglevel', 'info',
            '-hide_banner',
            # Reduce startup analysis delay (crucial for sync)
            '-probesize', '32',
            '-analyzeduration', '0',
            # genpts + nobuffer to reduce latency on pipe
            '-fflags', '+genpts+discardcorrupt+nobuffer',
        ]

        # Video input from stdin (MJPEG via image2pipe)
        cmd += [
            '-f', 'image2pipe',
            '-vcodec', 'mjpeg',
            '-thread_queue_size', '512',   # smaller = less buffering = better sync
            '-framerate', str(self._fps),
            '-i', 'pipe:0',
        ]

        # Audio input
        have_audio = False
        if program_media_audio_path:
            if program_media_audio_start_ms > 0:
                ss_seconds = max(0.0, program_media_audio_start_ms / 1000.0)
                cmd += ['-ss', f'{ss_seconds:.3f}']
            cmd += ['-thread_queue_size', '1024', '-i', program_media_audio_path]
            have_audio = True
        elif force_silent_audio:
            cmd += ['-f', 'lavfi', '-i', 'anullsrc=cl=stereo:r=48000']
            have_audio = True
        elif capture_audio and audio_device:
            import sys as _sys
            if _sys.platform == 'darwin':
                if str(audio_device).strip().lower() == 'auto':
                    sel = self._select_mac_loopback_device('')
                else:
                    sel = f":{audio_device}"
                cmd += ['-f', 'avfoundation', '-thread_queue_size', '1024', '-i', sel]
                have_audio = True
            elif _sys.platform.startswith('win'):
                selected = self._select_windows_dshow_audio_device(str(audio_device))
                if selected:
                    if self._log_cb:
                        self._log_cb(f"Recording audio: using Windows DirectShow device: {selected}\n")
                    cmd += [
                        '-thread_queue_size', '512',
                        '-rtbufsize', '50M',
                        '-f', 'dshow',
                        '-i', f'audio={selected}',
                    ]
                    have_audio = True
                else:
                    if self._log_cb:
                        self._log_cb("Recording audio: requested Windows audio device not found; using silent audio.\n")
                    cmd += ['-f', 'lavfi', '-i', 'anullsrc=cl=stereo:r=48000']
                    have_audio = True
            else:
                cmd += ['-f', 'pulse', '-i', audio_device]
                have_audio = True
        elif capture_audio:
            import sys as _sys
            if _sys.platform == 'darwin':
                sel = self._select_mac_loopback_device('')
                cmd += ['-f', 'avfoundation', '-thread_queue_size', '1024', '-i', sel]
                have_audio = True
                if self._log_cb:
                    self._log_cb(f"Recording audio: using avfoundation device {sel} (auto)\n")
            elif _sys.platform.startswith('win'):
                selected = self._select_windows_dshow_audio_device('')
                if selected:
                    if self._log_cb:
                        self._log_cb(f"Recording audio: auto-selected Windows DirectShow device: {selected}\n")
                    cmd += [
                        '-thread_queue_size', '512',
                        '-rtbufsize', '50M',
                        '-f', 'dshow',
                        '-i', f'audio={selected}',
                    ]
                    have_audio = True
                else:
                    if self._log_cb:
                        self._log_cb("Recording audio: no Windows audio capture devices found; using silent audio.\n")
                    cmd += ['-f', 'lavfi', '-i', 'anullsrc=cl=stereo:r=48000']
                    have_audio = True
            else:
                cmd += ['-f', 'pulse', '-i', 'default']
                have_audio = True
        else:
            cmd += ['-f', 'lavfi', '-i', 'anullsrc=cl=stereo:r=48000']
            have_audio = True

        # Video encoding options
        # SYNC FIX: -bf 0 eliminates B-frame lookahead buffering (was causing 3s video delay)
        # SYNC FIX: -rc_lookahead 0 eliminates rate-control lookahead buffering
        gop = str(max(2, int(self._fps) * 2))
        bv = f"{max(1500, self._bitrate_kbps)}k"
        vopts = [
            '-c:v', encoder,
            '-g', gop,
            '-keyint_min', str(max(1, int(self._fps) // 2)),
            '-sc_threshold', '0',
            '-pix_fmt', 'yuv420p',
        ]
        if encoder == 'libx264':
            vopts += [
                '-preset', preset,
                '-profile:v', 'high',
                '-level', '4.2',
                '-bf', '0',             # ← NO B-frames (eliminates buffer delay)
                '-rc-lookahead', '0',   # ← NO lookahead (eliminates buffer delay)
                '-b:v', bv,
                '-maxrate', bv,
                '-bufsize', f"{2 * max(1500, self._bitrate_kbps)}k",
            ]
        elif encoder == 'h264_videotoolbox':
            vopts += [
                '-profile:v', 'high',
                '-b:v', bv,
                '-maxrate', bv,
                '-bufsize', f"{2 * max(1500, self._bitrate_kbps)}k",
            ]
        elif encoder == 'h264_nvenc':
            vopts += [
                '-preset', 'p4',
                '-rc', 'vbr',
                '-profile:v', 'high',
                '-bf', '0',             # ← NO B-frames on NVENC too
                '-b:v', bv,
                '-maxrate', bv,
                '-bufsize', f"{2 * max(1500, self._bitrate_kbps)}k",
            ]
        else:
            vopts += ['-b:v', bv]

        # Container
        ext = file_path.split('.')[-1].lower() if '.' in file_path else 'mp4'
        fmt = 'mp4'
        if ext == 'mov':
            fmt = 'mov'
        elif ext == 'mkv':
            fmt = 'matroska'

        if have_audio:
            if program_media_audio_path:
                # Media file audio: trim and resample
                afilters = [
                    'asetpts=PTS-STARTPTS',
                ]
                if av_sync_delay_ms > 0:
                    afilters.append(f"adelay={av_sync_delay_ms}|{av_sync_delay_ms}")
                afilters.append('aresample=async=1000:min_hard_comp=0.100:first_pts=0')
                audio_filter_str = ','.join(afilters)
            else:
                # Live audio capture (DirectShow/AVFoundation):
                # SYNC FIX: asetpts=PTS-STARTPTS resets audio clock to 0
                # This matches the video which also starts at PTS=0 from pipe
                # aresample handles any remaining drift
                audio_filter_str = 'asetpts=PTS-STARTPTS,aresample=async=1000:min_hard_comp=0.100:first_pts=0'

            # SYNC FIX: setpts=PTS-STARTPTS resets video PTS to 0 to match audio reset above
            video_filter_str = 'setpts=PTS-STARTPTS'

            cmd += (
                ['-map', '0:v:0', '-map', '1:a:0']
                + vopts
                + ['-vf', video_filter_str]
                # SYNC FIX: vsync cfr gives the muxer stable timestamps (was passthrough)
                + ['-vsync', 'cfr']
                + ['-c:a', 'aac', '-b:a', '192k', '-ar', '48000', '-ac', '2']
                + ['-af', audio_filter_str]
                + ['-movflags', '+faststart+frag_keyframe+empty_moov']
                + ['-shortest']
                + ['-f', fmt, file_path]
            )
        else:
            cmd += (
                ['-map', '0:v:0']
                + vopts
                + ['-vf', 'setpts=PTS-STARTPTS']
                + ['-vsync', 'cfr']
                + ['-movflags', '+faststart+frag_keyframe+empty_moov']
                + ['-shortest']
                + ['-f', fmt, file_path]
            )

        # Launch FFmpeg
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
        self._last_frame_time = time.time()

        interval = max(16, int(1000 / self._fps))
        if self._log_cb:
            self._log_cb(f"Recording timer starting with {interval}ms interval ({self._fps} fps)\n")

        self._timer.start(interval)

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
                    self._proc.closeWriteChannel()
                except Exception:
                    pass
                try:
                    if not self._proc.waitForFinished(7000):
                        self._proc.terminate()
                        if not self._proc.waitForFinished(3000):
                            self._proc.kill()
                except Exception:
                    pass
        finally:
            if self._log_cb:
                self._log_cb(f"Recording stopped. Total frames: {self._frame_count}, Dropped: {self._dropped_frames}\n")
            self._running = False
            self._proc = None
            self._paused = False
            self.statusChanged.emit('Stopped')

    def _send_frame(self):
        if not self.is_running() or not self._frame_provider:
            return

        current_time = time.time()

        try:
            img = self._frame_provider(self._size)
            if img is None or img.isNull():
                if self._log_cb and self._frame_count < 10:
                    self._log_cb(f"Frame provider returned null/empty image (frame {self._frame_count})\n")
                return

            if img.size() != self._size:
                canvas = QImage(self._size, QImage.Format.Format_RGBA8888)
                canvas.fill(0)
                p = QPainter(canvas)
                p.drawImage(0, 0, img)
                p.end()
                img = canvas

            if img.format() not in (QImage.Format.Format_RGB888, QImage.Format.Format_RGBA8888, QImage.Format.Format_ARGB32):
                img = img.convertToFormat(QImage.Format.Format_RGB888)

            if self._proc and self._proc.state() == QProcess.ProcessState.Running:
                try:
                    pending = int(self._proc.bytesToWrite())
                except Exception:
                    pending = 0

                max_pending = 4 * 1024 * 1024  # 4MB (tighter than before to reduce latency)
                if pending > max_pending:
                    self._dropped_frames += 1
                    if self._log_cb:
                        self._log_cb(f"Dropping frame {self._frame_count} due to backpressure (pending={pending})\n")
                    return

                buf = QBuffer()
                buf.open(QBuffer.OpenModeFlag.WriteOnly)
                img.save(buf, b"JPEG", 85)
                frame_bytes: QByteArray = buf.data()
                buf.close()
                bytes_written = self._proc.write(frame_bytes)
                try:
                    self._proc.waitForBytesWritten(5)
                except Exception:
                    pass

                if bytes_written != len(frame_bytes):
                    if self._log_cb:
                        self._log_cb(f"Warning: Only wrote {bytes_written}/{len(frame_bytes)} bytes for frame {self._frame_count}\n")

                self._frame_count += 1

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
            self.stop()

    # --- Pause/Resume ---
    def pause(self):
        if not self.is_running() or self._paused:
            return
        self._timer.stop()
        self._paused = True
        self.statusChanged.emit('Paused')

    def resume(self):
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
        self._running = False
        do_retry = False
        retry_settings: Optional[Dict] = None
        try:
            import sys as _sys
            if (
                _sys.platform.startswith('win')
                and code != 0
                and not self._audio_retry_done
                and isinstance(self._last_start_settings, dict)
                and bool(self._last_start_settings.get('capture_audio', False))
                and not self._last_start_settings.get('program_media_audio_path')
            ):
                do_retry = True
                retry_settings = dict(self._last_start_settings)
                retry_settings['force_silent_audio'] = True
                retry_settings['audio_retry_done'] = True
        except Exception:
            do_retry = False

        if do_retry and retry_settings:
            try:
                if self._timer.isActive():
                    self._timer.stop()
            except Exception:
                pass
            self._proc = None
            self._paused = False
            if self._log_cb:
                self._log_cb("Recording audio failed on Windows; retrying recording with silent audio.\n")
            QTimer.singleShot(0, lambda: self.start(retry_settings))
            return

        self.statusChanged.emit('Stopped')

    def _select_best_encoder(self) -> str:
        try:
            import subprocess, sys as _sys
            ffmpeg_path = get_ffmpeg_path()
            res = subprocess.run([ffmpeg_path, '-hide_banner', '-v', 'quiet', '-encoders'],
                                 capture_output=True, text=True)
            text = (res.stdout or '') + '\n' + (res.stderr or '')
            encs = set()
            for line in text.splitlines():
                parts = line.strip().split()
                if len(parts) >= 2 and parts[0].startswith(('V', 'A', '.')):
                    encs.add(parts[1])
            if _sys.platform == 'darwin' and 'h264_videotoolbox' in encs:
                return 'h264_videotoolbox'
            if 'h264_nvenc' in encs:
                if _sys.platform.startswith('win'):
                    try:
                        import ctypes
                        ctypes.WinDLL('nvcuda.dll')
                        return 'h264_nvenc'
                    except Exception:
                        return 'libx264'
                return 'h264_nvenc'
        except Exception:
            pass
        return 'libx264'

    def _list_windows_dshow_audio_devices(self) -> list[tuple[str, str]]:
        """Return a list of DirectShow audio devices available to FFmpeg on Windows.

        Returns a list of (friendly_name, alternative_name).
        Device names are returned EXACTLY AS FFmpeg lists them.
        """
        try:
            import subprocess
            import re
            ffmpeg_path = get_ffmpeg_path()
            res = subprocess.run(
                [ffmpeg_path, '-hide_banner', '-f', 'dshow', '-list_devices', 'true', '-i', 'dummy'],
                capture_output=True,
                text=True,
                timeout=8,
                encoding='utf-8',
                errors='replace',
            )
            out = (res.stdout or '') + '\n' + (res.stderr or '')
            print(f"[AUDIO] Querying FFmpeg for audio devices...")

            devices: dict[str, tuple[str, str]] = {}
            device_index: list[str] = []

            device_pattern = r'\[in#\d+[^\]]*\]\s+"([^"]+)"\s*\(audio\)'
            for match in re.finditer(device_pattern, out, re.DOTALL):
                name = match.group(1)
                name = ' '.join(name.split())
                if name and name not in devices:
                    devices[name] = (name, '')
                    device_index.append(name)

            lines = out.split('\n')
            for i, line in enumerate(lines):
                if '(audio)' in line:
                    if i + 1 < len(lines):
                        next_line = lines[i + 1]
                        guid_match = re.search(r'@device_cm_\{([^}]+)\}', next_line)
                        if guid_match:
                            guid = guid_match.group(1)
                            alt_name = f"@device_cm_{{{guid}}}"
                            name_match = re.search(r'"([^"]+)"\s*\(audio\)', line)
                            if name_match:
                                dev_name = ' '.join(name_match.group(1).split())
                                if dev_name in devices:
                                    old_name, _ = devices[dev_name]
                                    devices[dev_name] = (old_name, alt_name)

            result = [devices[name] for name in device_index]
            print(f"[AUDIO] Available devices: {len(result)}")
            for fname, alt in result:
                display = fname.replace('Â®', '®').replace('Â', '')
                print(f"[AUDIO]   - {display}")
                if alt:
                    print(f"[AUDIO]     alt: {alt[:60]}...")
            return result
        except Exception as e:
            print(f"[AUDIO] ❌ Error listing devices: {e}")
            return []

    def _normalize_windows_device_name(self, s: str) -> str:
        try:
            import re
            ns = (s or '').lower()
            ns = re.sub(r'\s+', ' ', ns).strip()
            ns = ns.replace(' ', '')
            return ns
        except Exception:
            return (s or '').lower()

    def _select_windows_dshow_audio_device(self, requested: str) -> str:
        """Pick a valid DirectShow audio device for FFmpeg."""
        devices = self._list_windows_dshow_audio_devices()
        if self._log_cb:
            self._log_cb(f"[AUDIO] Available devices: {len(devices)}\n")
            for fname, alt in devices:
                self._log_cb(f"[AUDIO]   - {fname}\n")

        if not devices:
            if self._log_cb:
                self._log_cb("[AUDIO] ❌ No DirectShow audio devices found\n")
            return ''

        req = (requested or '').strip()
        if self._log_cb:
            self._log_cb(f"[AUDIO] Requested device: '{req}'\n")

        if req:
            for friendly, alt in devices:
                if friendly == req or alt == req:
                    if self._log_cb:
                        self._log_cb(f"[AUDIO] ✅ Exact match found: {friendly}\n")
                    return friendly

            nreq = self._normalize_windows_device_name(req)
            if nreq:
                for friendly, alt in devices:
                    if (self._normalize_windows_device_name(friendly) == nreq
                            or self._normalize_windows_device_name(alt) == nreq):
                        if self._log_cb:
                            self._log_cb(f"[AUDIO] ✅ Normalized match found: {friendly}\n")
                        return friendly
                    for name_to_check in [friendly, alt]:
                        norm = self._normalize_windows_device_name(name_to_check)
                        if norm.find(nreq) != -1 or nreq.find(norm) != -1:
                            if self._log_cb:
                                self._log_cb(f"[AUDIO] ✅ Substring match found: {friendly}\n")
                            return friendly

        for friendly, alt in devices:
            dl = friendly.lower()
            if 'microphone' in dl or 'mic' in dl or 'mic array' in dl:
                if self._log_cb:
                    self._log_cb(f"[AUDIO] ✅ Auto-selected microphone: {friendly}\n")
                return friendly

        if self._log_cb:
            self._log_cb(f"[AUDIO] Using first available device: {devices[0][0]}\n")
        return devices[0][0]

    def _select_mac_loopback_device(self, requested: str = '') -> str:
        """Probe avfoundation devices and return an input index for system/loopback audio."""
        try:
            import subprocess
            ffmpeg_path = get_ffmpeg_path()
            res = subprocess.run(
                [ffmpeg_path, '-hide_banner', '-f', 'avfoundation', '-list_devices', 'true', '-i', ''],
                capture_output=True, text=True
            )
            out = (res.stdout or '') + '\n' + (res.stderr or '')
            candidates = []
            for line in out.splitlines():
                ls = line.strip()
                if ls.startswith('[') and '] [' in ls:
                    try:
                        idx_part = ls.split('] [', 1)[1]
                        idx_str, rest = idx_part.split(']', 1)
                        idx = idx_str.strip()
                        name = rest.strip().lstrip(' ').lstrip(':').strip()
                        candidates.append((idx, name))
                    except Exception:
                        continue
            if requested:
                for idx, name in candidates:
                    if requested == idx or requested.lower() in name.lower():
                        if self._log_cb:
                            self._log_cb(f"Recording audio: using requested avfoundation device :{idx} ({name})\n")
                        return f":{idx}"
            preferred = ['blackhole', 'soundflower', 'loopback', 'ishowu', 'vb-cable', 'vb cable', 'cable input']
            for p in preferred:
                for idx, name in candidates:
                    if p in name.lower():
                        if self._log_cb:
                            self._log_cb(f"Recording audio: auto-selected avfoundation device :{idx} ({name})\n")
                        return f":{idx}"
            if self._log_cb:
                self._log_cb("Recording audio: falling back to avfoundation device :0 (no loopback found)\n")
            return ':0'
        except Exception:
            if self._log_cb:
                self._log_cb("Recording audio: device probe failed, using :0\n")
            return ':0'