from __future__ import annotations
from typing import Dict, Optional
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QComboBox, QLineEdit,
    QSpinBox, QCheckBox, QPushButton, QTextEdit, QMessageBox, QGroupBox, QFrame, QFileDialog,
    QSizePolicy, QSpacerItem, QListWidget, QListWidgetItem, QTabWidget, QWidget, QSlider, QProgressBar
)
from PyQt6.QtGui import QGuiApplication, QFont, QDragEnterEvent, QDropEvent, QColor, QPalette
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QLayout
from PyQt6.QtMultimedia import QMediaDevices

PLATFORMS = {
    # Use RTMPS by default for YouTube to avoid RTMP port blocks
    "YouTube Live": {"url": "rtmps://a.rtmps.youtube.com/live2", "needs_key": True},
    "Twitch": {"url": "rtmp://live.twitch.tv/app", "needs_key": True},
    "Facebook Live": {"url": "rtmps://live-api-s.facebook.com:443/rtmp", "needs_key": True},
    "Custom RTMP": {"url": "", "needs_key": True},
    # Special local platform: mirrors composed output to an external display via a fullscreen window
    "External Display (Mirror)": {"url": "", "needs_key": False},
}

RESOLUTIONS = [
    (3840, 2160, "4K UHD (2160p)"),
    (2560, 1440, "QHD (1440p)"),
    (1920, 1080, "1080p (Full HD)"),
    (1600, 900,  "900p"),
    (1280, 720,  "720p (HD)"),
    (1024, 576,  "576p"),
    (960, 540,   "540p"),
    (854, 480,   "480p"),
    (640, 360,   "360p"),
]

FRAMERATES = [15, 25, 30, 50, 60]
PRESETS = ["ultrafast", "superfast", "veryfast", "faster", "fast", "medium", "slow"]

class StreamingSettingsDialog(QDialog):
    def __init__(self, parent, stream_id: int, app_config):
        super().__init__(parent)
        self.setWindowTitle(f"🎬 Stream {stream_id} Settings")
        self.setModal(True)
        self.setMinimumSize(600, 560)
        
        # Modern dark theme styling
        self.setStyleSheet("""
            QDialog {
                background-color: #1e1e1e;
                color: #e0e0e0;
            }
            QGroupBox {
                border: 2px solid #3a3a3a;
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 8px;
                font-weight: bold;
                color: #ffffff;
                background-color: #252525;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 8px;
                color: #4fc3f7;
            }
            QTabWidget::pane {
                border: 1px solid #3a3a3a;
                border-radius: 6px;
                background-color: #252525;
            }
            QTabBar::tab {
                background-color: #2d2d2d;
                color: #b0b0b0;
                padding: 10px 20px;
                margin-right: 2px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                font-weight: 500;
            }
            QTabBar::tab:selected {
                background-color: #3a7ca5;
                color: #ffffff;
                font-weight: bold;
            }
            QTabBar::tab:hover:!selected {
                background-color: #3a3a3a;
                color: #ffffff;
            }
            QLineEdit, QSpinBox, QComboBox {
                background-color: #2d2d2d;
                border: 1px solid #4a4a4a;
                border-radius: 5px;
                padding: 6px;
                color: #e0e0e0;
                selection-background-color: #3a7ca5;
            }
            QLineEdit:focus, QSpinBox:focus, QComboBox:focus {
                border: 2px solid #4fc3f7;
            }
            QPushButton {
                background-color: #3a7ca5;
                color: #ffffff;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #4a8cb5;
            }
            QPushButton:pressed {
                background-color: #2a6c95;
            }
            QPushButton:disabled {
                background-color: #3a3a3a;
                color: #707070;
            }
            QCheckBox {
                color: #e0e0e0;
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border: 2px solid #4a4a4a;
                border-radius: 4px;
                background-color: #2d2d2d;
            }
            QCheckBox::indicator:checked {
                background-color: #4fc3f7;
                border-color: #4fc3f7;
                image: url(data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTIiIGhlaWdodD0iMTIiIHZpZXdCb3g9IjAgMCAxMiAxMiIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cGF0aCBkPSJNMTAgMkw0LjUgOC41TDIgNiIgc3Ryb2tlPSJ3aGl0ZSIgc3Ryb2tlLXdpZHRoPSIyIiBmaWxsPSJub25lIi8+PC9zdmc+);
            }
            QListWidget {
                background-color: #2d2d2d;
                border: 1px solid #4a4a4a;
                border-radius: 6px;
                color: #e0e0e0;
                padding: 4px;
            }
            QListWidget::item {
                padding: 8px;
                border-radius: 4px;
                margin: 2px;
            }
            QListWidget::item:selected {
                background-color: #3a7ca5;
                color: #ffffff;
            }
            QListWidget::item:hover {
                background-color: #3a3a3a;
            }
            QTextEdit {
                background-color: #1a1a1a;
                border: 1px solid #4a4a4a;
                border-radius: 6px;
                color: #e0e0e0;
                padding: 8px;
            }
            QSlider::groove:horizontal {
                border: 1px solid #4a4a4a;
                height: 6px;
                background-color: #2d2d2d;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background-color: #4fc3f7;
                border: 2px solid #3a7ca5;
                width: 16px;
                height: 16px;
                margin: -6px 0;
                border-radius: 8px;
            }
            QSlider::handle:horizontal:hover {
                background-color: #6dd5ff;
            }
            QProgressBar {
                border: 1px solid #4a4a4a;
                border-radius: 4px;
                background-color: #2d2d2d;
                text-align: center;
                color: #e0e0e0;
            }
            QProgressBar::chunk {
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #4fc3f7, stop:1 #3a7ca5);
                border-radius: 3px;
            }
        """)
        self._parent = parent
        self._stream_id = stream_id
        self._config = app_config

        # Create main layout
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        try:
            layout.setContentsMargins(12, 12, 12, 12)
        except Exception:
            pass
        try:
            layout.setSizeConstraint(QLayout.SizeConstraint.SetMinimumSize)
        except Exception:
            pass

        # Platform & Connection Group
        conn_group = QGroupBox("Platform & Connection")
        conn_layout = QGridLayout(conn_group)
        self.conn_group = conn_group
        self.conn_layout = conn_layout
        
        self.platform = QComboBox()
        self.platform.addItems(PLATFORMS.keys())
        self.platform.setMinimumHeight(28)
        
        self.url_edit = QLineEdit()
        self.url_edit.setMinimumHeight(28)
        self.url_edit.setPlaceholderText("RTMP URL (auto-filled for known platforms)")
        
        self.key_edit = QLineEdit()
        self.key_edit.setMinimumHeight(28)
        self.key_edit.setPlaceholderText("Enter your stream key here")
        self.key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        
        show_key_btn = QPushButton("Show")
        show_key_btn.setMaximumWidth(60)
        show_key_btn.clicked.connect(self._toggle_key_visibility)
        self.show_key_btn = show_key_btn
        
        self.platform_label = QLabel("Platform:")
        conn_layout.addWidget(self.platform_label, 0, 0)
        conn_layout.addWidget(self.platform, 0, 1, 1, 2)
        self.url_label = QLabel("Stream URL:")
        conn_layout.addWidget(self.url_label, 1, 0)
        conn_layout.addWidget(self.url_edit, 1, 1, 1, 2)
        self.key_label = QLabel("Stream Key:")
        conn_layout.addWidget(self.key_label, 2, 0)
        conn_layout.addWidget(self.key_edit, 2, 1)
        conn_layout.addWidget(show_key_btn, 2, 2)

        # Mirror mode helper info (shown only when External Display is selected)
        self.mirror_info = QLabel("Mirror your composed output to a selected external display.\nSelect the display below and click Start.")
        self.mirror_info.setWordWrap(True)
        conn_layout.addWidget(self.mirror_info, 3, 0, 1, 3)
        
        # Direct Passthrough option (also used for RTMP to bypass compositing and stream media file directly)
        self.passthrough_check = QCheckBox("Direct Passthrough")
        self.passthrough_check.setToolTip("When enabled: \n- Mirror: send raw input/media to display.\n- RTMP: stream the current media file directly via FFmpeg (bypasses app compositing).")
        self.passthrough_check.setStyleSheet("QCheckBox { color: #bbbbbb; }")
        conn_layout.addWidget(self.passthrough_check, 4, 0, 1, 3)
        
        # Style the mirror info and passthrough check
        for widget in [self.mirror_info, self.passthrough_check]:
            widget.setStyleSheet("color: #bbbbbb;")
        
        self.mirror_info.setVisible(False)
        # Keep passthrough visible for all platforms (mirror and RTMP)
        self.passthrough_check.setVisible(True)

        # Video Settings Group
        video_group = QGroupBox("Video Settings")
        video_layout = QGridLayout(video_group)
        self.video_group = video_group
        
        self.display_combo = QComboBox()
        self.display_combo.setMinimumHeight(28)
        # Add a manual refresh button for displays
        self.refresh_displays_btn = QPushButton("Refresh")
        self.refresh_displays_btn.setToolTip("Re-detect connected displays")
        self.refresh_displays_btn.setMinimumHeight(28)
        self.refresh_displays_btn.clicked.connect(self._populate_displays)
        
        self.res_combo = QComboBox()
        self.res_combo.setMinimumHeight(28)
        for w, h, desc in RESOLUTIONS:
            self.res_combo.addItem(f"{desc} ({w}×{h})", (w, h))
        
        self.fps_combo = QComboBox()
        self.fps_combo.setMinimumHeight(28)
        for f in FRAMERATES:
            self.fps_combo.addItem(f"{f} FPS", f)

        # Bitrate controls: auto (recommended for YouTube) with manual override
        self.auto_bitrate_check = QCheckBox("Auto bitrate (YouTube recommended)")
        self.auto_bitrate_check.setChecked(True)
        self.bitrate_spin = QSpinBox()
        self.bitrate_spin.setRange(500, 60000)
        self.bitrate_spin.setSingleStep(500)
        self.bitrate_spin.setSuffix(" kbps")
        self.bitrate_spin.setEnabled(False)
        
        # Store Display label and row so we can toggle visibility per platform
        self.display_label = QLabel("Display:")
        video_layout.addWidget(self.display_label, 0, 0)
        # Place combo and refresh button in a small row
        self.display_row = QHBoxLayout()
        self.display_row.setSpacing(6)
        self.display_row.addWidget(self.display_combo)
        self.display_row.addWidget(self.refresh_displays_btn)
        video_layout.addLayout(self.display_row, 0, 1)
        self.res_label = QLabel("Resolution:")
        video_layout.addWidget(self.res_label, 1, 0)
        video_layout.addWidget(self.res_combo, 1, 1)
        self.fps_label = QLabel("Framerate:")
        video_layout.addWidget(self.fps_label, 2, 0)
        video_layout.addWidget(self.fps_combo, 2, 1)
        video_layout.addWidget(self.auto_bitrate_check, 3, 0, 1, 1)
        video_layout.addWidget(self.bitrate_spin, 3, 1)

        # Audio Settings Group (BGM only)
        audio_group = QGroupBox("Audio Settings")
        audio_layout = QVBoxLayout(audio_group)
        try:
            audio_layout.setContentsMargins(12, 10, 12, 10)
            audio_layout.setSpacing(12)
        except Exception:
            pass
        self.audio_group = audio_group
        try:
            self.audio_group.setMinimumHeight(160)
            self.audio_group.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        except Exception:
            pass

        # Background Music (BGM) Group - Enhanced Playlist Audio Section
        bgm_group = QGroupBox("🎵 Background Music Player")
        bgm_layout = QVBoxLayout(bgm_group)
        bgm_layout.setSpacing(12)
        bgm_layout.setContentsMargins(16, 16, 16, 16)
        
        try:
            bgm_group.setMinimumHeight(180)
            bgm_group.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        except Exception:
            pass
        
        # Enable BGM with modern toggle
        self.bgm_enable_check = QCheckBox("🎧 Enable Background Music (replaces program audio)")
        self.bgm_enable_check.setChecked(False)
        self.bgm_enable_check.setMinimumHeight(32)
        self.bgm_enable_check.setStyleSheet("""
            QCheckBox {
                font-size: 13px;
                font-weight: 600;
                color: #4fc3f7;
            }
        """)
        self.bgm_enable_check.toggled.connect(self._on_bgm_toggled)
        bgm_layout.addWidget(self.bgm_enable_check)
        
        # Internal playlist storage
        self._bgm_playlist = []  # list[str]
        self._current_playing_index = -1  # Track currently playing song
        
        # Playlist header with info
        playlist_header = QHBoxLayout()
        playlist_label = QLabel("📋 Playlist")
        playlist_label.setStyleSheet("font-weight: bold; color: #ffffff; font-size: 12px;")
        self.playlist_count_label = QLabel("0 tracks")
        self.playlist_count_label.setStyleSheet("color: #b0b0b0; font-size: 11px;")
        playlist_header.addWidget(playlist_label)
        playlist_header.addWidget(self.playlist_count_label)
        playlist_header.addStretch()
        bgm_layout.addLayout(playlist_header)
        
        # Enhanced playlist with drag-drop support
        self.bgm_list = QListWidget()
        self.bgm_list.setDragDropMode(QListWidget.DragDropMode.InternalMove)
        self.bgm_list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        self.bgm_list.setAlternatingRowColors(True)
        self.bgm_list.setMinimumHeight(150)
        self.bgm_list.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.bgm_list.setStyleSheet("""
            QListWidget {
                font-size: 12px;
            }
            QListWidget::item {
                padding: 10px;
                border-left: 3px solid transparent;
            }
            QListWidget::item:selected {
                border-left: 3px solid #4fc3f7;
            }
        """)
        self.bgm_list.model().rowsMoved.connect(self._on_playlist_reordered)
        bgm_layout.addWidget(self.bgm_list)
        
        # Control buttons row
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        
        self.bgm_add_btn = QPushButton("➕ Add Files")
        self.bgm_add_btn.setMinimumHeight(32)
        self.bgm_add_btn.setStyleSheet("""
            QPushButton {
                background-color: #2e7d32;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #388e3c;
            }
        """)
        self.bgm_add_btn.clicked.connect(self._add_bgm_files)
        
        self.bgm_remove_btn = QPushButton("🗑️ Remove")
        self.bgm_remove_btn.setMinimumHeight(32)
        self.bgm_remove_btn.setStyleSheet("""
            QPushButton {
                background-color: #c62828;
            }
            QPushButton:hover {
                background-color: #d32f2f;
            }
        """)
        self.bgm_remove_btn.clicked.connect(self._remove_bgm_files)
        
        self.bgm_shuffle_btn = QPushButton("🔀 Shuffle")
        self.bgm_shuffle_btn.setMinimumHeight(32)
        self.bgm_shuffle_btn.clicked.connect(self._shuffle_bgm_playlist)
        
        self.bgm_clear_btn = QPushButton("🧹 Clear All")
        self.bgm_clear_btn.setMinimumHeight(32)
        self.bgm_clear_btn.setStyleSheet("""
            QPushButton {
                background-color: #f57c00;
            }
            QPushButton:hover {
                background-color: #fb8c00;
            }
        """)
        self.bgm_clear_btn.clicked.connect(self._clear_bgm_files)
        
        btn_row.addWidget(self.bgm_add_btn)
        btn_row.addWidget(self.bgm_remove_btn)
        btn_row.addWidget(self.bgm_shuffle_btn)
        btn_row.addWidget(self.bgm_clear_btn)
        bgm_layout.addLayout(btn_row)
        
        # Playback controls
        playback_group = QFrame()
        playback_group.setStyleSheet("""
            QFrame {
                background-color: #1e1e1e;
                border-radius: 8px;
                padding: 12px;
            }
        """)
        playback_layout = QVBoxLayout(playback_group)
        playback_layout.setSpacing(10)
        
        # Loop and shuffle options
        options_row = QHBoxLayout()
        self.bgm_loop_check = QCheckBox("🔁 Loop Playlist")
        self.bgm_loop_check.setChecked(True)
        self.bgm_loop_check.setStyleSheet("font-weight: 500;")
        
        self.bgm_shuffle_mode_check = QCheckBox("🔀 Shuffle Mode")
        self.bgm_shuffle_mode_check.setChecked(False)
        self.bgm_shuffle_mode_check.setStyleSheet("font-weight: 500;")
        
        options_row.addWidget(self.bgm_loop_check)
        options_row.addWidget(self.bgm_shuffle_mode_check)
        options_row.addStretch()
        playback_layout.addLayout(options_row)
        
        # Volume control with slider
        vol_row = QHBoxLayout()
        vol_label = QLabel("🔊 Volume:")
        vol_label.setStyleSheet("font-weight: 600; color: #ffffff;")
        
        self.bgm_vol_slider = QSlider(Qt.Orientation.Horizontal)
        self.bgm_vol_slider.setRange(0, 100)
        self.bgm_vol_slider.setValue(50)
        self.bgm_vol_slider.setMinimumWidth(150)
        self.bgm_vol_slider.valueChanged.connect(self._on_volume_changed)
        
        self.bgm_vol_label = QLabel("50%")
        self.bgm_vol_label.setStyleSheet("""
            QLabel {
                font-weight: bold;
                color: #4fc3f7;
                min-width: 40px;
                font-size: 13px;
            }
        """)
        
        # Keep spinbox for compatibility but hide it
        self.bgm_vol_spin = QSpinBox()
        self.bgm_vol_spin.setRange(0, 100)
        self.bgm_vol_spin.setValue(50)
        self.bgm_vol_spin.setVisible(False)
        
        vol_row.addWidget(vol_label)
        vol_row.addWidget(self.bgm_vol_slider)
        vol_row.addWidget(self.bgm_vol_label)
        playback_layout.addLayout(vol_row)
        
        # Now playing indicator
        self.now_playing_label = QLabel("⏸️ No track playing")
        self.now_playing_label.setStyleSheet("""
            QLabel {
                color: #b0b0b0;
                font-style: italic;
                font-size: 11px;
                padding: 4px;
            }
        """)
        playback_layout.addWidget(self.now_playing_label)
        
        bgm_layout.addWidget(playback_group)

        audio_layout.addWidget(bgm_group)
        # Add stretch to ensure sufficient space below BGM group
        try:
            audio_layout.addStretch(1)
        except Exception:
            pass

        # Add visual separation before Advanced Settings (removed for tabbed UI)
        try:
            pass
        except Exception:
            pass
        # Advanced Settings Group
        advanced_group = QGroupBox("Advanced Settings")
        advanced_layout = QGridLayout(advanced_group)
        self.advanced_group = advanced_group
        try:
            advanced_layout.setContentsMargins(10, 8, 10, 10)
            advanced_layout.setHorizontalSpacing(8)
            advanced_layout.setVerticalSpacing(8)
        except Exception:
            pass
        
        self.preset_combo = QComboBox()
        self.preset_combo.addItems(PRESETS)
        self.preset_combo.setCurrentText("veryfast")
        self.preset_combo.setMinimumHeight(28)
        
        self.crf_spin = QSpinBox()
        self.crf_spin.setRange(10, 40)
        self.crf_spin.setValue(20)
        self.crf_spin.setMinimumHeight(28)
        self.crf_spin.setSuffix(" (lower = better quality)")

        # A/V sync offset (ms): delays audio to match video path latency
        self.avsync_spin = QSpinBox()
        self.avsync_spin.setRange(0, 3000)
        self.avsync_spin.setSingleStep(50)
        self.avsync_spin.setValue(500)
        self.avsync_spin.setMinimumHeight(28)
        # Nudge buttons
        self.avsync_plus_btn = QPushButton("+50 ms")
        self.avsync_minus_btn = QPushButton("-50 ms")
        self.avsync_plus_btn.setMinimumHeight(26)
        self.avsync_minus_btn.setMinimumHeight(26)

        # Use Master Clock (PyAV) backend for precise A/V sync
        self.use_av_master_check = QCheckBox("Use Master Clock (PyAV A/V Sync)")
        self.use_av_master_check.setToolTip("Timestamp audio and video against a single time.monotonic() master clock and resample audio to correct drift. Requires PyAV.")
        self.use_av_master_check.setChecked(True)
        
        advanced_layout.addWidget(QLabel("A/V Sync Offset (ms):"), 2, 0)
        # A small layout row for spin + buttons
        av_row = QHBoxLayout()
        av_row.addWidget(self.avsync_spin)
        av_row.addWidget(self.avsync_minus_btn)
        av_row.addWidget(self.avsync_plus_btn)
        advanced_layout.addLayout(av_row, 2, 1)
        # Master clock toggle row
        advanced_layout.addWidget(self.use_av_master_check, 3, 0, 1, 2)
        
        advanced_layout.addWidget(QLabel("Encoder Preset:"), 0, 0)
        advanced_layout.addWidget(self.preset_combo, 0, 1)
        advanced_layout.addWidget(QLabel("Quality (CRF):"), 1, 0)
        advanced_layout.addWidget(self.crf_spin, 1, 1)

        # Control Buttons
        button_layout = QHBoxLayout()
        self.test_btn = QPushButton("Test Connection")
        self.start_btn = QPushButton("Start Streaming")
        self.stop_btn = QPushButton("Stop Streaming")
        
        self.test_btn.setMinimumHeight(30)
        self.start_btn.setMinimumHeight(30)
        self.stop_btn.setMinimumHeight(30)
        
        self.start_btn.setStyleSheet("""
            QPushButton {
                background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #2e7d32, stop:1 #1b5e20);
                color: white;
                font-weight: bold;
                font-size: 13px;
                padding: 10px 24px;
            }
            QPushButton:hover {
                background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #388e3c, stop:1 #2e7d32);
            }
        """)
        self.stop_btn.setStyleSheet("""
            QPushButton {
                background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #c62828, stop:1 #b71c1c);
                color: white;
                font-weight: bold;
                font-size: 13px;
                padding: 10px 24px;
            }
            QPushButton:hover {
                background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #d32f2f, stop:1 #c62828);
            }
        """)
        self.stop_btn.setEnabled(False)
        
        button_layout.addWidget(self.test_btn)
        button_layout.addStretch()
        button_layout.addWidget(self.start_btn)
        button_layout.addWidget(self.stop_btn)

        # Connection/Log Output
        self.conn_status = QLabel("Not connected")
        self.conn_status.setStyleSheet("QLabel { color: #cccccc; }")
        
        log_label = QLabel("FFmpeg Output:")
        log_label.setFont(QFont("", 10, QFont.Weight.Bold))
        
        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setMaximumHeight(100)
        self.log_view.setStyleSheet("QTextEdit { background-color: #2b2b2b; color: #ffffff; font-family: monospace; }")

        # Add groups into tabs for a more compact UI
        tabs = QTabWidget()

        # Connection tab
        conn_tab = QWidget()
        conn_tab_layout = QVBoxLayout(conn_tab)
        conn_tab_layout.addWidget(conn_group)
        try:
            conn_tab_layout.addStretch(1)
        except Exception:
            pass
        tabs.addTab(conn_tab, "Connection")

        # Video tab
        video_tab = QWidget()
        video_tab_layout = QVBoxLayout(video_tab)
        video_tab_layout.addWidget(video_group)
        try:
            video_tab_layout.addStretch(1)
        except Exception:
            pass
        tabs.addTab(video_tab, "Video")

        # Audio tab
        audio_tab = QWidget()
        audio_tab_layout = QVBoxLayout(audio_tab)
        audio_tab_layout.addWidget(audio_group)
        try:
            audio_tab_layout.addStretch(1)
        except Exception:
            pass
        tabs.addTab(audio_tab, "Audio")

        # Advanced tab
        adv_tab = QWidget()
        adv_tab_layout = QVBoxLayout(adv_tab)
        adv_tab_layout.addWidget(advanced_group)
        try:
            adv_tab_layout.addStretch(1)
        except Exception:
            pass
        tabs.addTab(adv_tab, "Advanced")

        # Logs tab
        logs_tab = QWidget()
        logs_tab_layout = QVBoxLayout(logs_tab)
        logs_tab_layout.addWidget(self.conn_status)
        logs_tab_layout.addWidget(log_label)
        logs_tab_layout.addWidget(self.log_view)
        try:
            logs_tab_layout.addStretch(1)
        except Exception:
            pass
        tabs.addTab(logs_tab, "Logs")

        layout.addWidget(tabs)
        layout.addLayout(button_layout)

        # Wire events
        self.platform.currentTextChanged.connect(self._on_platform_changed)
        self.start_btn.clicked.connect(self._on_start)
        self.stop_btn.clicked.connect(self._on_stop)
        self.test_btn.clicked.connect(self._on_test)
        # No device capture controls; audio is BGM-only here
        self.res_combo.currentIndexChanged.connect(self._update_recommended_bitrate)
        self.fps_combo.currentIndexChanged.connect(self._update_recommended_bitrate)
        self.auto_bitrate_check.toggled.connect(self._on_auto_bitrate_toggled)

        # Initialize
        self._populate_displays()
        # Auto-refresh displays when screens change (e.g., external monitor connected)
        try:
            app = QGuiApplication.instance()
            if app is not None:
                # Signals provide a QScreen* argument; use a wrapper to ignore it
                app.screenAdded.connect(lambda _s: self._populate_displays())
                app.screenRemoved.connect(lambda _s: self._populate_displays())
        except Exception:
            pass
        # No audio devices to populate in BGM-only mode
        self._load_from_config()
        self._on_platform_changed(self.platform.currentText())
        # Initialize bitrate recommendation after controls are populated
        self._update_recommended_bitrate()

        # No audio device sync in BGM-only mode

        # Subscribe to stream logs
        if hasattr(parent, 'stream_controller'):
            parent.stream_controller.on_log(self._append_log)

        # Also subscribe to this stream's independent controller for logs and status
        try:
            if hasattr(parent, 'get_stream_controller'):
                _sc = parent.get_stream_controller(self._stream_id)
                if _sc is not None:
                    try:
                        _sc.on_log(self._append_log)
                    except Exception:
                        pass
                    try:
                        _sc.statusChanged.connect(self._on_controller_status)
                    except Exception:
                        pass
        except Exception:
            pass

        # Ensure buttons reflect current running state when dialog opens
        try:
            self._sync_ui_with_state()
        except Exception:
            pass

    def showEvent(self, event):
        try:
            super().showEvent(event)
        except Exception:
            pass
        # Refresh UI state each time dialog is shown
        try:
            self._sync_ui_with_state()
        except Exception:
            pass

    def _on_controller_status(self, status: str):
        """Update UI controls based on controller status callbacks."""
        try:
            if status and isinstance(status, str):
                self.log_view.append(f"Status: {status}")
        except Exception:
            pass
        try:
            self._sync_ui_with_state()
        except Exception:
            pass

    def _sync_ui_with_state(self):
        """Sync Start/Stop/Test button states with actual streaming/mirror status."""
        # Default states
        start_enabled = True
        stop_enabled = False
        test_enabled = True

        # Check mirror controller running state (only if this stream owns it)
        try:
            if hasattr(self._parent, 'mirror_controller'):
                owner = getattr(self._parent, '_mirror_owner_stream', None)
                mc = self._parent.mirror_controller
                if owner == self._stream_id and hasattr(mc, 'is_running') and mc.is_running():
                    start_enabled = False
                    stop_enabled = True
                    test_enabled = False
        except Exception:
            pass

        # Check RTMP controller running state
        try:
            if hasattr(self._parent, 'get_stream_controller'):
                sc = self._parent.get_stream_controller(self._stream_id)
                if sc is not None and hasattr(sc, 'is_running') and sc.is_running():
                    start_enabled = False
                    stop_enabled = True
                    test_enabled = False
        except Exception:
            pass

        # Apply to buttons
        try:
            self.start_btn.setEnabled(start_enabled)
            self.stop_btn.setEnabled(stop_enabled)
            self.test_btn.setEnabled(test_enabled)
        except Exception:
            pass

    def _toggle_key_visibility(self):
        if self.key_edit.echoMode() == QLineEdit.EchoMode.Password:
            self.key_edit.setEchoMode(QLineEdit.EchoMode.Normal)
            self.sender().setText("Hide")
        else:
            self.key_edit.setEchoMode(QLineEdit.EchoMode.Password)
            self.sender().setText("Show")

    def _append_log(self, text: str):
        self.log_view.append(text.rstrip())
        self.log_view.ensureCursorVisible()
        t = text.lower()
        # Detect when output starts (connected to RTMP)
        if "output #0, flv, to" in t or "writing header" in t:
            self.conn_status.setText("Connected: sending frames. Open YouTube Live Control Room and click 'Go Live'.")
            self.conn_status.setStyleSheet("QLabel { color: #00d084; font-weight: bold; }")

    def _populate_displays(self):
        # Preserve current selection if possible
        prev_idx = self.display_combo.currentIndex()
        self.display_combo.blockSignals(True)
        try:
            self.display_combo.clear()
            screens = QGuiApplication.screens()
            try:
                print(f"[Stream Settings] Qt detected {len(screens) if screens else 0} screens")
            except Exception:
                pass
            
            # Try macOS-native NSScreen fallback if Qt only sees one screen
            nsscreens = []
            if len(screens) <= 1:
                try:
                    from AppKit import NSScreen
                    nsscreens = NSScreen.screens()
                    print(f"[Stream Settings] NSScreen fallback detected {len(nsscreens)} screens")
                except ImportError:
                    print("[Stream Settings] pyobjc not available, install with: pip install pyobjc-framework-Cocoa")
                except Exception as e:
                    print(f"[Stream Settings] NSScreen fallback failed: {e}")
            
            # Use NSScreen data if we have more screens there than Qt
            if len(nsscreens) > len(screens):
                print("[Stream Settings] Using NSScreen data (more screens detected)")
                self._display_index_map = []
                self._nsscreen_rects = []  # Store NSScreen rects for positioning
                
                for i, ns in enumerate(nsscreens):
                    try:
                        # NSScreen coordinates are flipped (origin at bottom-left)
                        frame = ns.frame()
                        x, y, w, h = int(frame.origin.x), int(frame.origin.y), int(frame.size.width), int(frame.size.height)
                        
                        # Get display name if available
                        try:
                            device_desc = ns.deviceDescription()
                            disp_name = device_desc.get('NSDeviceDisplayName', f'Display {i+1}')
                        except Exception:
                            disp_name = f'Display {i+1}'
                        
                        label = f"{disp_name} - {w}×{h}"
                        self.display_combo.addItem(label, (w, h))
                        self._display_index_map.append(i)
                        self._nsscreen_rects.append((x, y, w, h))
                        
                        print(f"  - NSScreen #{i}: {disp_name} {w}x{h} @({x},{y})")
                    except Exception as e:
                        print(f"  - NSScreen #{i}: Error parsing - {e}")
                        
            else:
                # Use Qt screens as before
                if not screens:
                    self.display_combo.addItem("No displays detected", None)
                    self.start_btn.setEnabled(False)
                    return
                    
                self._display_index_map = []
                self._nsscreen_rects = []  # Clear NSScreen data
                
                for i, s in enumerate(screens, start=1):
                    geo = s.geometry()
                    name = getattr(s, 'name', None)
                    try:
                        # PyQt6 QScreen has name() method
                        disp_name = s.name() if callable(getattr(s, 'name', None)) else (name() if name else f"Display {i}")
                    except Exception:
                        disp_name = f"Display {i}"
                    label = f"{disp_name} - {geo.width()}×{geo.height()}"
                    self.display_combo.addItem(label, (geo.width(), geo.height()))
                    self._display_index_map.append(i - 1)
                
                try:
                    print("[Stream Settings] Qt Screens:")
                    for idx, s in enumerate(screens):
                        g = s.geometry()
                        nm = ''
                        try:
                            nm = s.name() if callable(getattr(s, 'name', None)) else ''
                        except Exception:
                            nm = ''
                        print(f"  - #{idx}: {nm} {g.width()}x{g.height()} @({g.x()},{g.y()})")
                except Exception:
                    pass
            
            # Restore previous selection when available
            if 0 <= prev_idx < self.display_combo.count():
                self.display_combo.setCurrentIndex(prev_idx)
            self.start_btn.setEnabled(True)
        finally:
            self.display_combo.blockSignals(False)

    def _populate_audio_devices(self):
        pass  # Removed: BGM-only mode

    def _on_platform_changed(self, name: str):
        tmpl = PLATFORMS.get(name, {})
        is_mirror = (name == "External Display (Mirror)")
        # Toggle connection fields
        self.url_edit.setVisible(not is_mirror)
        self.key_edit.setVisible(not is_mirror)
        self.show_key_btn.setVisible(not is_mirror)
        self.url_label.setVisible(not is_mirror)
        self.key_label.setVisible(not is_mirror)
        self.mirror_info.setVisible(is_mirror)
        # Passthrough applies to all platforms; adjust tooltip text
        try:
            if is_mirror:
                self.passthrough_check.setToolTip("When enabled, sends raw input/media directly to display without processing")
            else:
                self.passthrough_check.setToolTip("When enabled, streams the current media file directly via FFmpeg (bypasses app compositing). Audio may be copied when compatible.")
        except Exception:
            pass
        # Display selection only for mirror mode
        try:
            self.display_label.setVisible(is_mirror)
            self.display_combo.setVisible(is_mirror)
            self.refresh_displays_btn.setVisible(is_mirror)
        except Exception:
            pass
        # Hide Resolution/FPS pickers for mirror mode (mirror auto-maximizes and matches fps)
        try:
            self.res_label.setVisible(not is_mirror)
            self.res_combo.setVisible(not is_mirror)
            self.fps_label.setVisible(not is_mirror)
            self.fps_combo.setVisible(not is_mirror)
            self.auto_bitrate_check.setVisible(not is_mirror)
            self.bitrate_spin.setVisible(not is_mirror)
        except Exception:
            pass
        # In mirror mode, allow selecting an audio OUTPUT device to route audio to HDMI
        self.audio_group.setEnabled(True)
        # For non-custom RTMP platforms, prefill URL
        if name not in ("Custom RTMP", "External Display (Mirror)"):
            self.url_edit.setText(tmpl.get("url", ""))
        elif name == "Custom RTMP":
            self.url_edit.setText("")
        # Refresh recommended bitrate when platform changes back to RTMP mode
        self._update_recommended_bitrate()

    def _on_audio_toggled(self, checked: bool):
        try:
            if hasattr(self, 'audio_dev_combo'):
                self.audio_dev_combo.setEnabled(checked)
        except Exception:
            pass

    def _on_auto_bitrate_toggled(self, checked: bool):
        self.bitrate_spin.setEnabled(not checked)
        if checked:
            self._update_recommended_bitrate()

    def _recommended_bitrate_kbps(self, w: int, h: int, fps: int) -> int:
        """Return a recommended CBR bitrate for YouTube Live for given resolution/fps."""
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
            return 3000
        except Exception:
            return 6000

    def _update_recommended_bitrate(self):
        """Update bitrate spin to show the current recommended value when Auto is enabled."""
        try:
            (w, h) = self.res_combo.currentData()
            fps = int(self.fps_combo.currentData())
            rec = self._recommended_bitrate_kbps(w, h, fps)
            if self.auto_bitrate_check.isChecked():
                # Display recommendation; keep disabled spin visually synced
                self.bitrate_spin.blockSignals(True)
                self.bitrate_spin.setValue(rec)
                self.bitrate_spin.blockSignals(False)
        except Exception:
            pass

    def _resolve_url(self) -> str:
        url = (self.url_edit.text() or "").strip()
        key = (self.key_edit.text() or "").strip()
        if not url or not key:
            return ""
        if key and not url.endswith(key):
            joiner = '' if url.endswith('/') else '/'
            return f"{url}{joiner}{key}"
        return url

    def get_settings(self) -> Dict:
        (w, h) = self.res_combo.currentData()
        fps = int(self.fps_combo.currentData())
        url = self._resolve_url()
        # Determine selected screen index (default 0)
        try:
            idx_in_combo = max(0, int(self.display_combo.currentIndex()))
            screen_index = self._display_index_map[idx_in_combo] if hasattr(self, '_display_index_map') and idx_in_combo < len(self._display_index_map) else 0
        except Exception:
            screen_index = 0
        return {
            'platform': self.platform.currentText(),
            'url': url,
            'key': self.key_edit.text().strip(),
            'width': w,
            'height': h,
            'fps': fps,
            'screen_index': int(screen_index),
            'direct_passthrough': self.passthrough_check.isChecked(),
            'mirror_mode': self.platform.currentText() == "External Display (Mirror)",
            # Device capture disabled in BGM-only mode
            'capture_audio': False,
            'audio_device': '',
            'video_preset': self.preset_combo.currentText(),
            'crf': int(self.crf_spin.value()),
            'av_sync_delay_ms': int(self.avsync_spin.value()),
            'bitrate_kbps': 0 if self.auto_bitrate_check.isChecked() else int(self.bitrate_spin.value()),
            'use_av_master_clock': bool(self.use_av_master_check.isChecked()),
            # BGM settings
            'bgm_enabled': bool(self.bgm_enable_check.isChecked()),
            'bgm_playlist': list(self._bgm_playlist),
            'bgm_loop': bool(self.bgm_loop_check.isChecked()),
            'bgm_volume': int(self.bgm_vol_spin.value()),
        }

    def _load_from_config(self):
        prefix = f'streaming.stream{self._stream_id}'
        
        # Platform
        plat = self._config.get(f'{prefix}.platform', 'YouTube Live')
        pidx = self.platform.findText(plat)
        self.platform.setCurrentIndex(pidx if pidx >= 0 else 0)
        
        # URL and Key
        self.url_edit.setText(self._config.get(f'{prefix}.url', ''))
        self.key_edit.setText(self._config.get(f'{prefix}.key', ''))
        
        # Resolution
        w = self._config.get(f'{prefix}.width', 1920)
        h = self._config.get(f'{prefix}.height', 1080)
        for i in range(self.res_combo.count()):
            rw, rh = self.res_combo.itemData(i)
            if rw == w and rh == h:
                self.res_combo.setCurrentIndex(i)
                break
        
        # FPS
        fps = self._config.get(f'{prefix}.fps', 30)
        for i in range(self.fps_combo.count()):
            if int(self.fps_combo.itemData(i)) == int(fps):
                self.fps_combo.setCurrentIndex(i)
                break
        
        # No capture audio settings in BGM-only mode
        
        # Advanced
        preset = self._config.get(f'{prefix}.video_preset', 'veryfast')
        pvidx = self.preset_combo.findText(preset)
        self.preset_combo.setCurrentIndex(pvidx if pvidx >= 0 else 2)
        self.crf_spin.setValue(int(self._config.get(f'{prefix}.crf', 20)))
        # Default av sync delay minimized to prevent delay buildup
        self.avsync_spin.setValue(int(self._config.get(f'{prefix}.av_sync_delay_ms', 50)))
        # Master clock backend default: True
        try:
            use_av_master = bool(self._config.get(f'{prefix}.use_av_master_clock', True))
        except Exception:
            use_av_master = True
        self.use_av_master_check.setChecked(use_av_master)
        # Bitrate: if <=0 use auto; else set manual
        try:
            br = int(self._config.get(f'{prefix}.bitrate_kbps', 0) or 0)
        except Exception:
            br = 0
        if br <= 0:
            self.auto_bitrate_check.setChecked(True)
            self.bitrate_spin.setEnabled(False)
        else:
            self.auto_bitrate_check.setChecked(False)
            self.bitrate_spin.setEnabled(True)
            self.bitrate_spin.setValue(max(500, br))

        # BGM: load persisted settings (playlist)
        try:
            bgm_enabled = bool(self._config.get(f'{prefix}.bgm_enabled', False))
            bgm_list = self._config.get(f'{prefix}.bgm_playlist', []) or []
            bgm_loop = bool(self._config.get(f'{prefix}.bgm_loop', True))
            bgm_volume = int(self._config.get(f'{prefix}.bgm_volume', 50))
            self.bgm_enable_check.setChecked(bgm_enabled)
            # Restore playlist UI
            if isinstance(bgm_list, list):
                self._bgm_playlist = [str(x) for x in bgm_list]
            else:
                self._bgm_playlist = []
            self._refresh_bgm_list_widget()
            self.bgm_loop_check.setChecked(bgm_loop)
            self.bgm_vol_spin.setValue(max(0, min(100, bgm_volume)))
            # Sync slider with loaded volume
            self.bgm_vol_slider.setValue(max(0, min(100, bgm_volume)))
        except Exception:
            pass

    def _add_bgm_files(self):
        try:
            files, _ = QFileDialog.getOpenFileNames(self, "Select Background Music Files", "", "Audio Files (*.mp3 *.wav *.m4a *.aac *.flac);;All Files (*)")
            if files:
                # Keep order; append
                self._bgm_playlist.extend([f for f in files if f])
                self.bgm_enable_check.setChecked(True)
                self._refresh_bgm_list_widget()
        except Exception:
            pass

    def _clear_bgm_files(self):
        try:
            self._bgm_playlist = []
            self._refresh_bgm_list_widget()
        except Exception:
            pass

    def _refresh_bgm_list_widget(self):
        """Refresh the playlist UI with current tracks and visual indicators."""
        try:
            self.bgm_list.clear()
            if not self._bgm_playlist:
                it = QListWidgetItem("🎵 No tracks added yet")
                it.setFlags(it.flags() & ~Qt.ItemFlag.ItemIsEnabled)  # non-selectable
                it.setForeground(QColor("#707070"))
                self.bgm_list.addItem(it)
                self.playlist_count_label.setText("0 tracks")
            else:
                for idx, p in enumerate(self._bgm_playlist):
                    name = p.split('/')[-1]
                    # Add visual indicator for currently playing track
                    if idx == self._current_playing_index:
                        display_name = f"▶️ {name}"
                        item = QListWidgetItem(display_name)
                        item.setForeground(QColor("#4fc3f7"))
                    else:
                        display_name = f"🎵 {name}"
                        item = QListWidgetItem(display_name)
                    self.bgm_list.addItem(item)
                
                # Update track count
                count = len(self._bgm_playlist)
                self.playlist_count_label.setText(f"{count} track{'s' if count != 1 else ''}")
        except Exception as e:
            print(f"Error refreshing BGM list: {e}")
            pass
    
    def _remove_bgm_files(self):
        """Remove selected tracks from the playlist."""
        try:
            selected_items = self.bgm_list.selectedItems()
            if not selected_items:
                QMessageBox.information(self, "No Selection", "Please select tracks to remove.")
                return
            
            # Get indices to remove (in reverse order to avoid index shifting)
            indices_to_remove = []
            for item in selected_items:
                row = self.bgm_list.row(item)
                if 0 <= row < len(self._bgm_playlist):
                    indices_to_remove.append(row)
            
            # Remove in reverse order
            for idx in sorted(indices_to_remove, reverse=True):
                del self._bgm_playlist[idx]
            
            self._refresh_bgm_list_widget()
            
            # Show confirmation
            removed_count = len(indices_to_remove)
            if removed_count > 0:
                self.now_playing_label.setText(f"🗑️ Removed {removed_count} track{'s' if removed_count != 1 else ''}")
        except Exception as e:
            print(f"Error removing BGM files: {e}")
            QMessageBox.warning(self, "Error", f"Failed to remove tracks: {str(e)}")
    
    def _shuffle_bgm_playlist(self):
        """Shuffle the current playlist order."""
        try:
            if not self._bgm_playlist:
                QMessageBox.information(self, "Empty Playlist", "Add some tracks first!")
                return
            
            import random
            random.shuffle(self._bgm_playlist)
            self._refresh_bgm_list_widget()
            self.now_playing_label.setText("🔀 Playlist shuffled!")
        except Exception as e:
            print(f"Error shuffling playlist: {e}")
            QMessageBox.warning(self, "Error", f"Failed to shuffle: {str(e)}")
    
    def _on_playlist_reordered(self, parent, start, end, destination, row):
        """Handle drag-drop reordering of playlist items."""
        try:
            # Rebuild playlist from current UI order
            new_playlist = []
            for i in range(self.bgm_list.count()):
                item_text = self.bgm_list.item(i).text()
                # Remove emoji prefixes to get original filename
                clean_name = item_text.replace("▶️ ", "").replace("🎵 ", "")
                # Find matching path in original playlist
                for path in self._bgm_playlist:
                    if path.split('/')[-1] == clean_name:
                        new_playlist.append(path)
                        break
            
            if len(new_playlist) == len(self._bgm_playlist):
                self._bgm_playlist = new_playlist
                self.now_playing_label.setText("↕️ Playlist reordered")
        except Exception as e:
            print(f"Error handling playlist reorder: {e}")
    
    def _on_volume_changed(self, value: int):
        """Sync volume slider with spinbox and update display."""
        try:
            self.bgm_vol_spin.setValue(value)
            self.bgm_vol_label.setText(f"{value}%")
            
            # Visual feedback on volume label
            if value == 0:
                self.bgm_vol_label.setStyleSheet("""
                    QLabel {
                        font-weight: bold;
                        color: #f44336;
                        min-width: 40px;
                        font-size: 13px;
                    }
                """)
            elif value < 30:
                self.bgm_vol_label.setStyleSheet("""
                    QLabel {
                        font-weight: bold;
                        color: #ff9800;
                        min-width: 40px;
                        font-size: 13px;
                    }
                """)
            else:
                self.bgm_vol_label.setStyleSheet("""
                    QLabel {
                        font-weight: bold;
                        color: #4fc3f7;
                        min-width: 40px;
                        font-size: 13px;
                    }
                """)
        except Exception as e:
            print(f"Error updating volume: {e}")
    
    def update_now_playing(self, track_index: int, track_name: str = ""):
        """Update the now playing indicator (can be called from parent/controller)."""
        try:
            self._current_playing_index = track_index
            if track_index >= 0 and track_index < len(self._bgm_playlist):
                if not track_name:
                    track_name = self._bgm_playlist[track_index].split('/')[-1]
                self.now_playing_label.setText(f"▶️ Now playing: {track_name}")
                self.now_playing_label.setStyleSheet("""
                    QLabel {
                        color: #4fc3f7;
                        font-style: normal;
                        font-weight: 600;
                        font-size: 11px;
                        padding: 4px;
                    }
                """)
            else:
                self.now_playing_label.setText("⏸️ No track playing")
                self.now_playing_label.setStyleSheet("""
                    QLabel {
                        color: #b0b0b0;
                        font-style: italic;
                        font-size: 11px;
                        padding: 4px;
                    }
                """)
            self._refresh_bgm_list_widget()
        except Exception as e:
            print(f"Error updating now playing: {e}")

    def _on_bgm_toggled(self, checked: bool):
        # When turning on BGM, auto-mute all sources via main window's global audio button if available
        if checked:
            try:
                parent = self.parent()
                if parent is not None and hasattr(parent, 'audioTopButton') and parent.audioTopButton:
                    # Simulate user clicking the global mute button
                    parent.audioTopButton.click()
            except Exception:
                pass

    def _validate(self) -> bool:
        # Mirror mode: require a valid display only in this mode
        if self.platform.currentText() == "External Display (Mirror)":
            if self.display_combo.currentData() is None:
                QMessageBox.warning(self, "Validation Error", "No display detected.")
                return False
            return True
        # RTMP modes require URL/Key
        url = self.url_edit.text().strip()
        key = self.key_edit.text().strip()
        if not url:
            QMessageBox.warning(self, "Validation Error", "Please enter a Stream URL.")
            return False
        if not key:
            QMessageBox.warning(self, "Validation Error", "Please enter a Stream Key.")
            return False
        return True

    def _save_settings(self):
        settings = self.get_settings()
        prefix = f'streaming.stream{self._stream_id}'
        for k, v in settings.items():
            self._config.set(f'{prefix}.{k}', v)
        self._config.save_settings()

    def _on_test(self):
        if not self._validate():
            return
        
        self.log_view.clear()
        self.log_view.append("Testing connection...")
        
        # Simple connection test - try to resolve URL
        url = self._resolve_url()
        self.log_view.append(f"Final RTMP URL: {url}")
        
        QMessageBox.information(self, "Connection Test", 
                              f"URL constructed successfully:\n{url}\n\nNote: Actual connection test requires FFmpeg to attempt streaming.")

    def _on_start(self):
        if not self._validate():
            return
        
        self._save_settings()
        settings = self.get_settings()
        # If mirror mode, start the external display mirror instead of RTMP
        if settings.get('mirror_mode'):
            try:
                self.log_view.clear()
                self.log_view.append("Starting external display mirror...")
                # Route audio to selected output device if requested
                try:
                    if (
                        hasattr(self, 'audio_check') and getattr(self.audio_check, 'isChecked', lambda: False)() and
                        hasattr(self, 'audio_dev_combo') and hasattr(self._parent, 'on_audio_output_changed')
                    ):
                        sel = self.audio_dev_combo.currentText().strip()
                        if sel:
                            self._parent.on_audio_output_changed(sel)
                except Exception:
                    pass
                
                # Pass NSScreen rect data if we used the fallback
                if hasattr(self, '_nsscreen_rects') and self._nsscreen_rects:
                    settings['nsscreen_rects'] = self._nsscreen_rects
                # Mirror should auto-maximize and use parent's current preview fps
                settings['maximize'] = True
                try:
                    # Prefer parent's graphics output target fps stored in config
                    from config import app_config as _cfg
                    settings['fps'] = int(_cfg.get('ui.preview_fps', 30))
                except Exception:
                    pass
                if hasattr(self._parent, 'mirror_controller'):
                    # If mirror already running, update resolution/fps instead of restarting
                    mc = self._parent.mirror_controller
                    try:
                        # Assign ownership to this stream regardless (user choice)
                        self._parent._mirror_owner_stream = self._stream_id
                    except Exception:
                        pass
                    if getattr(mc, 'is_running') and mc.is_running():
                        try:
                            mc.update(settings)
                            self.log_view.append("Applied mirror settings (resolution/framerate) to running mirror.")
                        except Exception as e:
                            self.log_view.append(f"Failed to apply mirror settings: {e}")
                    else:
                        mc.start(settings)
                    self.start_btn.setEnabled(False)
                    self.stop_btn.setEnabled(True)
                    self.test_btn.setEnabled(False)
                    if hasattr(self._parent, 'update_record_status'):
                        self._parent.update_record_status(f"Mirroring (Stream {self._stream_id})", "#00aa00")
                else:
                    QMessageBox.critical(self, "Error", "Mirror controller not available.")
            except Exception as e:
                QMessageBox.critical(self, "Mirror Error", f"Failed to start mirroring:\n{str(e)}")
                self.log_view.append(f"ERROR: {str(e)}")
            return
        
        # RTMP streaming path
        # If a media is currently on program, pass its file path and current position so FFmpeg can capture audio from it directly and aligned
        try:
            if hasattr(self._parent, 'get_current_program_media_audio_path'):
                media_path = self._parent.get_current_program_media_audio_path()
                if media_path:
                    settings['program_media_audio_path'] = media_path
                    if hasattr(self._parent, 'get_current_program_media_position_ms'):
                        pos_ms = self._parent.get_current_program_media_position_ms() or 0
                        settings['program_media_audio_start_ms'] = int(pos_ms)
                    # Disable device capture when direct media audio is available
                    settings['capture_audio'] = False
                    settings['audio_device'] = ''
        except Exception:
            pass
        
        try:
            self.log_view.clear()
            self.log_view.append("Starting stream...")
            # Use independent controller for this stream
            controller = None
            if hasattr(self._parent, 'get_stream_controller'):
                controller = self._parent.get_stream_controller(self._stream_id)
            if controller is not None:
                controller.start(settings)
                self.start_btn.setEnabled(False)
                self.stop_btn.setEnabled(True)
                self.test_btn.setEnabled(False)
                
                # Update main window status
                if hasattr(self._parent, 'update_record_status'):
                    self._parent.update_record_status(f"Streaming {self._stream_id}", "#00aa00")
            else:
                QMessageBox.critical(self, "Error", f"Streaming controller for Stream {self._stream_id} not available.")
        except Exception as e:
            QMessageBox.critical(self, "Streaming Error", f"Failed to start streaming:\n{str(e)}")
            self.log_view.append(f"ERROR: {str(e)}")

    def _on_stop(self):
        try:
            # Stop mirror only if this stream owns it
            if hasattr(self._parent, 'mirror_controller'):
                try:
                    owner = getattr(self._parent, '_mirror_owner_stream', None)
                    if owner == self._stream_id:
                        self._parent.mirror_controller.stop()
                        try:
                            self._parent._mirror_owner_stream = None
                        except Exception:
                            pass
                except Exception:
                    pass
            # Stop RTMP only for this stream id
            controller = None
            if hasattr(self._parent, 'get_stream_controller'):
                controller = self._parent.get_stream_controller(self._stream_id)
            if controller is not None:
                try:
                    controller.stop()
                except Exception:
                    pass
            # After stopping, resync UI state rather than forcing a specific state
            self._sync_ui_with_state()
            self.log_view.append("Stopped.")
            # Update main window status
            if hasattr(self._parent, 'update_record_status'):
                self._parent.update_record_status("Ready", "#777777")
        except Exception as e:
            QMessageBox.warning(self, "Stop Error", f"Failed to stop cleanly: {str(e)}")
