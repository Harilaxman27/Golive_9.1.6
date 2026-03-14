from __future__ import annotations
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QPushButton,
    QGroupBox, QTabWidget, QWidget, QSlider, QCheckBox, QSpinBox, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtMultimedia import QMediaDevices, QCamera, QVideoFrame

RESOLUTION_PRESETS = [
    (3840, 2160, "4K UHD (2160p)"),
    (2560, 1440, "QHD (1440p)"),
    (1920, 1080, "1080p (Full HD)"),
    (1280, 720, "720p (HD)"),
    (640, 480, "480p (SD)"),
]

FPS_PRESETS = [15, 24, 30, 60, 120]

class InputSettingsDialog(QDialog):
    settingsChanged = pyqtSignal(dict)
    
    def __init__(self, parent=None, input_number: int = 1):
        super().__init__(parent)
        self.setWindowTitle(f"📹 Input {input_number} Camera Settings")
        self.setModal(True)
        self.setMinimumSize(650, 550)
        self.input_number = input_number
        
        # Premium Dark Theme Styling
        self.setStyleSheet("""
            QDialog {
                background-color: #121212;
                color: #ffffff;
            }
            QGroupBox {
                border: 1px solid #333333;
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 16px;
                font-weight: 600;
                color: #e0e0e0;
                background-color: #1e1e1e;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 5px;
                color: #64b5f6;
            }
            QComboBox {
                background-color: #2c2c2c;
                border: 1px solid #424242;
                border-radius: 6px;
                padding: 8px;
                color: #ffffff;
                min-height: 20px;
            }
            QComboBox:hover {
                border: 1px solid #64b5f6;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            QPushButton {
                background-color: #1976d2;
                color: #ffffff;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                font-weight: 600;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #2196f3;
            }
            QPushButton:pressed {
                background-color: #0d47a1;
            }
            QPushButton#refreshBtn {
                background-color: #424242;
            }
            QPushButton#refreshBtn:hover {
                background-color: #616161;
            }
            QLabel {
                color: #b0bec5;
                font-size: 13px;
            }
            QLabel#headerLabel {
                color: #ffffff;
                font-size: 14px;
                font-weight: bold;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(24, 24, 24, 24)
        
        # Header
        header_layout = QHBoxLayout()
        icon_label = QLabel("📹")
        icon_label.setStyleSheet("font-size: 24px;")
        header_layout.addWidget(icon_label)
        
        title_layout = QVBoxLayout()
        title_layout.setSpacing(4)
        title_label = QLabel(f"Input {input_number} Settings")
        title_label.setObjectName("headerLabel")
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; color: white;")
        subtitle_label = QLabel("Configure camera source and resolution")
        subtitle_label.setStyleSheet("color: #757575; font-size: 12px;")
        title_layout.addWidget(title_label)
        title_layout.addWidget(subtitle_label)
        header_layout.addLayout(title_layout)
        header_layout.addStretch()
        layout.addLayout(header_layout)

        # Camera Selection Group
        camera_group = QGroupBox("Device Configuration")
        camera_layout = QVBoxLayout(camera_group)
        camera_layout.setSpacing(16)
        camera_layout.setContentsMargins(16, 24, 16, 16)
        
        # Camera Dropdown
        cam_row = QVBoxLayout()
        cam_row.setSpacing(6)
        cam_label = QLabel("Camera Source")
        cam_label.setStyleSheet("color: #e0e0e0; font-weight: 500;")
        cam_row.addWidget(cam_label)
        
        cam_input_row = QHBoxLayout()
        self.camera_combo = QComboBox()
        self.camera_combo.currentIndexChanged.connect(self._on_camera_changed)
        cam_input_row.addWidget(self.camera_combo, 1)
        
        refresh_btn = QPushButton("⟳")
        refresh_btn.setObjectName("refreshBtn")
        refresh_btn.setFixedSize(36, 36)
        refresh_btn.setToolTip("Refresh Camera List")
        refresh_btn.clicked.connect(self._populate_cameras)
        cam_input_row.addWidget(refresh_btn)
        cam_row.addLayout(cam_input_row)
        camera_layout.addLayout(cam_row)
        
        # Resolution & FPS Row
        res_fps_layout = QHBoxLayout()
        res_fps_layout.setSpacing(16)
        
        # Resolution
        res_col = QVBoxLayout()
        res_col.setSpacing(6)
        res_label = QLabel("Resolution")
        res_label.setStyleSheet("color: #e0e0e0; font-weight: 500;")
        res_col.addWidget(res_label)
        self.resolution_combo = QComboBox()
        for w, h, desc in RESOLUTION_PRESETS:
            self.resolution_combo.addItem(f"{desc} ({w}×{h})", (w, h))
        self.resolution_combo.setCurrentIndex(2)  # Default 1080p
        res_col.addWidget(self.resolution_combo)
        res_fps_layout.addLayout(res_col)
        
        # FPS
        fps_col = QVBoxLayout()
        fps_col.setSpacing(6)
        fps_label = QLabel("Framerate")
        fps_label.setStyleSheet("color: #e0e0e0; font-weight: 500;")
        fps_col.addWidget(fps_label)
        self.fps_combo = QComboBox()
        for fps in FPS_PRESETS:
            self.fps_combo.addItem(f"{fps} FPS", fps)
        self.fps_combo.setCurrentIndex(3)  # Default 60 FPS for high-end cameras
        fps_col.addWidget(self.fps_combo)
        res_fps_layout.addLayout(fps_col)
        
        camera_layout.addLayout(res_fps_layout)
        
        # Auto Detect Button
        auto_btn = QPushButton("✨ Auto-Detect Best Settings")
        auto_btn.setStyleSheet("""
            QPushButton {
                background-color: #2e7d32;
                margin-top: 8px;
            }
            QPushButton:hover {
                background-color: #388e3c;
            }
        """)
        auto_btn.clicked.connect(self._auto_detect_settings)
        camera_layout.addWidget(auto_btn)
        
        layout.addWidget(camera_group)
        
        # Status
        self.status_label = QLabel("Ready")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet("color: #757575; margin-top: 10px;")
        layout.addWidget(self.status_label)
        
        layout.addStretch()
        
        # Footer Buttons
        btns = QHBoxLayout()
        btns.addStretch()
        
        close_btn = QPushButton("Done")
        close_btn.setFixedWidth(120)
        close_btn.clicked.connect(self.accept)
        btns.addWidget(close_btn)
        
        layout.addLayout(btns)
        
        # Initialize
        self._populate_cameras()
        
        # Connect real-time updates
        self._connect_real_time_updates()
    
    def _populate_cameras(self):
        """Populate camera dropdown with available cameras."""
        try:
            self.camera_combo.clear()
            
            # Add default "Select Camera" option
            self.camera_combo.addItem("📹 Select Camera...", None)
            
            cameras = QMediaDevices.videoInputs()
            
            if not cameras:
                self.camera_combo.addItem("No cameras detected", None)
                self.status_label.setText("⚠️ No cameras found. Please connect a camera.")
                return
            
            for camera in cameras:
                try:
                    desc = camera.description()
                    self.camera_combo.addItem(f"📹 {desc}", camera)
                except Exception:
                    self.camera_combo.addItem("📹 Camera", camera)
            
            # Keep "Select Camera..." as default selection
            self.camera_combo.setCurrentIndex(0)
            self.status_label.setText(f"✅ Found {len(cameras)} camera(s) - Select one to configure")
        except Exception as e:
            print(f"Error populating cameras: {e}")
            self.camera_combo.addItem("Error detecting cameras", None)
    
    def _on_camera_changed(self, index):
        """Handle camera selection change."""
        camera_device = self.camera_combo.currentData()
        if camera_device:
            self.status_label.setText(f"📹 Selected: {self.camera_combo.currentText()}")
            # Auto-detect and set best resolution/FPS when camera is selected
            if self._auto_detect_from_qt_device(camera_device):
                try:
                    self.settingsChanged.emit(self.get_settings())
                except Exception:
                    pass
    
    def _auto_detect_from_qt_device(self, camera_device) -> bool:
        """Auto-detect best resolution and FPS from Qt camera device (works on Windows, macOS, Linux)."""
        try:
            if not hasattr(camera_device, 'videoFormats'):
                return False
            formats = camera_device.videoFormats()
            if not formats:
                return False
            best_w = best_h = 0
            best_fps = 30.0
            best_score = (-1, -1, -1.0)  # (res_pixels, prefer_1080p, fps)
            for fmt in formats:
                try:
                    size = fmt.resolution()
                    w = int(size.width()) if hasattr(size, 'width') else int(getattr(size, 'width', 0))
                    h = int(size.height()) if hasattr(size, 'height') else int(getattr(size, 'height', 0))
                    fps_max = float(fmt.maxFrameRate()) if hasattr(fmt, 'maxFrameRate') else 30.0
                    if fps_max <= 0:
                        fps_max = 30.0
                    res_pixels = w * h
                    prefer_1080p = 1 if (w == 1920 and h == 1080) else 0
                    score = (res_pixels, prefer_1080p, fps_max)
                    if score > best_score:
                        best_score = score
                        best_w, best_h, best_fps = w, h, fps_max
                except Exception:
                    continue
            if best_w <= 0 or best_h <= 0:
                best_w, best_h = 1920, 1080
            if best_fps <= 0:
                best_fps = 60.0
            self._apply_detected_settings(best_w, best_h, best_fps)
            return True
        except Exception as e:
            print(f"Qt auto-detect error: {e}")
            return False

    def _apply_detected_settings(self, detected_w: int, detected_h: int, detected_fps: float):
        """Apply detected resolution and FPS to combo boxes."""
        def _nearest_resolution_index(w: int, h: int) -> int:
            best_i = 0
            best_diff = 10**9
            for i in range(self.resolution_combo.count()):
                data = self.resolution_combo.itemData(i)
                if not data:
                    continue
                rw, rh = data
                diff = abs(rw - w) + abs(rh - h)
                if diff < best_diff:
                    best_diff = diff
                    best_i = i
            return best_i

        def _select_fps(fps_value: float) -> None:
            best_i = -1
            best_diff = 10**9
            for i in range(self.fps_combo.count()):
                val = self.fps_combo.itemData(i)
                if val is None:
                    continue
                diff = abs(int(val) - int(round(fps_value)))
                if diff < best_diff:
                    best_diff = diff
                    best_i = i
            if best_i >= 0:
                self.fps_combo.setCurrentIndex(best_i)
            else:
                self.fps_combo.insertItem(0, f"{int(round(fps_value))} FPS", int(round(fps_value)))
                self.fps_combo.setCurrentIndex(0)

        res_i = _nearest_resolution_index(detected_w, detected_h)
        self.resolution_combo.setCurrentIndex(res_i)
        _select_fps(detected_fps)
        self.status_label.setText(f"✅ Auto-detected: {detected_w}×{detected_h} @ {int(round(detected_fps))} FPS")

    def _auto_detect_settings(self):
        """Auto-detect best resolution and FPS for selected camera."""
        try:
            cam_data = self.camera_combo.currentData()
            if cam_data is None:
                self.status_label.setText("⚠️ Please select a camera before auto-detecting")
                return
            # Prefer Qt-based detection (works on Windows, macOS, Linux)
            if self._auto_detect_from_qt_device(cam_data):
                try:
                    current = self.get_settings()
                    current['output_profile_auto'] = True
                    self.settingsChanged.emit(current)
                except Exception:
                    pass
                return
            # Fallback: av_capture probe (macOS only)
            try:
                from av_capture import probe_device
            except Exception:
                probe_device = None
            detected_w, detected_h, detected_fps = 1920, 1080, 60.0
            if probe_device is not None:
                try:
                    cam_index = self.camera_combo.currentIndex()
                    device_id = max(0, cam_index - 1)
                    info = probe_device(device_id, sample_seconds=0.8)
                    if info and info.get('ok'):
                        detected_w = int(info.get('width') or 1920)
                        detected_h = int(info.get('height') or 1080)
                        detected_fps = float(info.get('fps') or 60.0)
                except Exception:
                    pass
            self._apply_detected_settings(detected_w, detected_h, detected_fps)
            try:
                current = self.get_settings()
                current['output_profile_auto'] = True
                self.settingsChanged.emit(current)
            except Exception:
                pass
        except Exception as e:
            print(f"Error auto-detecting: {e}")
    
    def get_settings(self) -> dict:
        """Return all camera settings."""
        camera_info = self.camera_combo.currentData()
        resolution = self.resolution_combo.currentData()
        fps = self.fps_combo.currentData()
        
        return {
            'camera': camera_info,
            'camera_name': self.camera_combo.currentText(),
            'resolution': resolution,
            'fps': fps,
            # Default values for removed settings to maintain compatibility
            'brightness': 0,
            'contrast': 0,
            'saturation': 0,
            'flip_horizontal': False,
            'flip_vertical': False,
            'rotation': 0,
            'low_light_boost': False,
            'noise_reduction': False,
            'auto_focus': True,
            'chroma_key_enabled': False,
            'chroma_color': 'Green',
            'chroma_threshold': 30,
        }
    
    def _connect_real_time_updates(self):
        """Connect all controls to real-time updates."""
        # Only connect what exists
        try:
            self.camera_combo.currentIndexChanged.connect(self._on_setting_changed)
            self.resolution_combo.currentIndexChanged.connect(self._on_setting_changed)
            self.fps_combo.currentIndexChanged.connect(self._on_setting_changed)
        except Exception:
            pass
    
    def _on_setting_changed(self):
        """Handle real-time setting changes."""
        try:
            # Get current settings
            settings = self.get_settings()
            
            # Apply to camera processor immediately
            from camera_processor import camera_processors
            if self.input_number in camera_processors:
                camera_processors[self.input_number].update_settings(settings)
            
            # Emit signal for parent to handle
            self.settingsChanged.emit(settings)
            
        except Exception as e:
            print(f"Real-time update error: {e}")
    
    def load_current_settings(self, settings: dict):
        """Load existing settings into the dialog."""
        if not settings:
            return
        
        try:
            # Camera selection
            camera_name = settings.get('camera_name', '')
            if camera_name:
                # Find and select the camera in dropdown
                for i in range(self.camera_combo.count()):
                    if camera_name in self.camera_combo.itemText(i):
                        self.camera_combo.setCurrentIndex(i)
                        break
            
            # Resolution
            res = settings.get('resolution')
            if res:
                for i in range(self.resolution_combo.count()):
                    if self.resolution_combo.itemData(i) == res:
                        self.resolution_combo.setCurrentIndex(i)
                        break
            
            # FPS
            fps = settings.get('fps')
            if fps:
                for i in range(self.fps_combo.count()):
                    if self.fps_combo.itemData(i) == fps:
                        self.fps_combo.setCurrentIndex(i)
                        break
            
        except Exception as e:
            print(f"Error loading settings: {e}")
