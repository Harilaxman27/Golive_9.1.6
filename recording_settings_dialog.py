from __future__ import annotations
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QFileDialog, QCheckBox, QComboBox, QGroupBox, QTabWidget, QWidget,
    QSpinBox, QSlider, QTextEdit, QSizePolicy, QFrame
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont
import os
import subprocess
import re
import sys as _sys

def _list_windows_audio_devices() -> list[tuple[str, str]]:
    """List available Windows audio input devices using FFmpeg DirectShow.
    
    Returns: [(friendly_name, alternative_name_or_empty), ...]
    
    IMPORTANT: Device names are returned EXACTLY AS FFmpeg lists them,
    including any encoding artifacts like Â® for ® - these must be 
    passed back to FFmpeg unchanged for matching to work.
    """
    try:
        # Try to find ffmpeg
        ffmpeg_path = None
        try:
            from ffmpeg_utils import get_ffmpeg_path
            ffmpeg_path = get_ffmpeg_path()
        except ImportError:
            ffmpeg_path = 'ffmpeg'
        
        print("[AUDIO] 🔍 Scanning for Windows DirectShow audio devices...")
        result = subprocess.run(
            [ffmpeg_path, '-hide_banner', '-f', 'dshow', '-list_devices', 'true', '-i', 'dummy'],
            capture_output=True,
            text=True,
            timeout=20,
            encoding='utf-8',
            errors='replace',
        )
        output = (result.stdout or '') + '\n' + (result.stderr or '')
        print(f"[AUDIO] FFmpeg returned {len(output)} characters")
        
        devices: dict[str, tuple[str, str]] = {}  # name -> (name, alt)
        device_index: list[str] = []  # Track insertion order
        
        # Find all device entries that have "(audio)" marker
        # Pattern: [in#N....] "Device Name" (audio)
        # Note: Device names can span multiple lines in terminal output
        device_pattern = r'\[in#\d+[^\]]*\]\s+"([^"]+)"\s*\(audio\)'
        
        print("[AUDIO] 📡 Parsing device entries...")
        for match in re.finditer(device_pattern, output, re.DOTALL):
            name = match.group(1)
            # Clean up whitespace from line wrapping, but PRESERVE all characters including encoding artifacts
            name = ' '.join(name.split())
            # DO NOT clean up Â® or other encoding artifacts - they must match what FFmpeg expects!
            
            if name and name not in devices:
                devices[name] = (name, '')
                device_index.append(name)
                # Display with Unicode normalization for readability only
                display_name = name.replace('Â®', '®').replace('Â', '')
                print(f"[AUDIO] 🎤 Device found: '{display_name}'")
        
        # Now track alternative names by looking for them right after audio device lines
        lines = output.split('\n')
        for i, line in enumerate(lines):
            # Check if this is a device line with (audio)
            if '(audio)' in line and i + 1 < len(lines):
                # The next line should be the alternative name
                next_line = lines[i + 1]
                if 'Alternative name' in next_line:
                    match = re.search(r'"([^"]+)"', next_line)
                    if match and device_index:
                        alt = match.group(1).strip()
                        # Assign to the last device we added (which should be from this line)
                        last_device_name = device_index[-1]
                        old_name, _ = devices[last_device_name]
                        devices[last_device_name] = (old_name, alt)
                        print(f"[AUDIO] 🔗 Alternative name: {alt[:60]}...")
        
        # Convert back to list
        result_devices = [devices[name] for name in device_index]
        
        print(f"[AUDIO] ✅ TOTAL DEVICES FOUND: {len(result_devices)}")
        for i, (fname, alt) in enumerate(result_devices, 1):
            # Display with cleaned encoding for readability
            display = fname.replace('Â®', '®').replace('Â', '')
            print(f"[AUDIO]   {i}. {display}")
            if alt:
                print(f"[AUDIO]      ↳ {alt[:80]}...")
        return result_devices
    except Exception as e:
        print(f"[AUDIO] ❌ Error listing audio devices: {e}")
        import traceback
        traceback.print_exc()
        return []

FORMAT_PRESETS = {
    "MP4 (H.264)": {"ext": ".mp4", "codec": "libx264", "desc": "Most compatible, good quality"},
    "MP4 (H.265/HEVC)": {"ext": ".mp4", "codec": "libx265", "desc": "Better compression, smaller files"},
    "MKV (H.264)": {"ext": ".mkv", "codec": "libx264", "desc": "Open format, supports all codecs"},
    "MOV (ProRes)": {"ext": ".mov", "codec": "prores_ks", "desc": "Professional editing, large files"},
    "WebM (VP9)": {"ext": ".webm", "codec": "libvpx-vp9", "desc": "Web-optimized, good quality"},
}

QUALITY_PRESETS = {
    "Ultra (Lossless)": {"crf": 0, "bitrate": 0, "desc": "Lossless quality, huge files"},
    "High (Visually Lossless)": {"crf": 18, "bitrate": 20000, "desc": "Near-perfect quality"},
    "Medium (Balanced)": {"crf": 23, "bitrate": 10000, "desc": "Good quality, reasonable size"},
    "Low (Streaming)": {"crf": 28, "bitrate": 5000, "desc": "Smaller files, visible compression"},
}

class RecordingSettingsPanel(QWidget):
    def __init__(self, parent=None, *, initial_path: str = '', include_audio: bool = True, initial_audio_device: str = ''):
        super().__init__(parent)
        self.initial_audio_device = initial_audio_device
        
        # Premium Dark Theme Styling
        self.setStyleSheet("""
            QWidget {
                background-color: transparent;
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
            QTabWidget::pane {
                border: 1px solid #333333;
                border-radius: 6px;
                background-color: #1e1e1e;
            }
            QTabBar{ background-color: transparent; }
            QTabBar::tab {
                background-color: #2c2c2c;
                color: #b0bec5;
                padding: 10px 20px;
                margin-right: 2px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                font-weight: 500;
            }
            QTabBar::tab:selected {
                background-color: #1976d2;
                color: #ffffff;
                font-weight: bold;
            }
            QTabBar::tab:hover:!selected {
                background-color: #424242;
                color: #ffffff;
            }
            QLineEdit, QSpinBox, QComboBox {
                background-color: #2c2c2c;
                border: 1px solid #424242;
                border-radius: 6px;
                padding: 8px;
                color: #ffffff;
                min-height: 20px;
            }
            QLineEdit:focus, QSpinBox:focus, QComboBox:focus {
                border: 1px solid #64b5f6;
            }
            QPushButton {
                 background-color: #1976d2;
                 color: #ffffff;
                 border: none;
                 border-radius: 6px;
                 padding: 8px 16px;
                 font-weight: 600;
                 font-size: 13px;
             }
             QPushButton:hover {
                 background-color: #2196f3;
             }
             QPushButton:pressed {
                 background-color: #0d47a1;
             }
            QCheckBox {
                color: #e0e0e0;
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border: 2px solid #757575;
                border-radius: 4px;
                background-color: #2c2c2c;
            }
            QCheckBox::indicator:checked {
                background-color: #1976d2;
                border-color: #1976d2;
            }
            QTextEdit {
                background-color: #2c2c2c;
                border: 1px solid #424242;
                border-radius: 6px;
                color: #ffffff;
                padding: 8px;
            }
            QSlider::groove:horizontal {
                border: 1px solid #424242;
                height: 6px;
                background-color: #2c2c2c;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background-color: #64b5f6;
                border: 2px solid #1976d2;
                width: 16px;
                height: 16px;
                margin: -6px 0;
                border-radius: 8px;
            }
            QSlider::handle:horizontal:hover {
                background-color: #90caf9;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(12, 12, 12, 12)
        
        # Create tabs
        tabs = QTabWidget()
        
        # ===== OUTPUT TAB =====
        output_tab = QWidget()
        output_layout = QVBoxLayout(output_tab)
        output_layout.setSpacing(20)
        output_layout.setContentsMargins(20, 20, 20, 20)
        
        # Header
        out_header = QLabel("Output Destination")
        out_header.setFont(QFont("Inter", 12, QFont.Weight.Bold))
        out_header.setStyleSheet("color: #64b5f6;")
        output_layout.addWidget(out_header)
        
        # File path row
        path_row = QHBoxLayout()
        path_label = QLabel("Save to:")
        path_label.setMinimumWidth(60)
        path_label.setStyleSheet("font-weight: 600; color: #ffffff;")
        path_row.addWidget(path_label)
        
        self.path_edit = QLineEdit(self)
        self.path_edit.setPlaceholderText("/path/to/output.mp4")
        self.path_edit.setMinimumHeight(40)
        if initial_path:
            self.path_edit.setText(initial_path)
        path_row.addWidget(self.path_edit, 1)
        
        browse_btn = QPushButton("📂 Browse", self)
        browse_btn.setMinimumHeight(40)
        browse_btn.clicked.connect(self._on_browse)
        path_row.addWidget(browse_btn)
        output_layout.addLayout(path_row)
        
        # Format preset
        format_row = QHBoxLayout()
        format_label = QLabel("Format:")
        format_label.setMinimumWidth(60)
        format_label.setStyleSheet("font-weight: 600; color: #ffffff;")
        format_row.addWidget(format_label)
        
        self.format_combo = QComboBox()
        self.format_combo.setMinimumHeight(40)
        for name, info in FORMAT_PRESETS.items():
            self.format_combo.addItem(f"{name} - {info['desc']}", name)
        self.format_combo.currentTextChanged.connect(self._on_format_changed)
        format_row.addWidget(self.format_combo, 1)
        output_layout.addLayout(format_row)
        
        # Format description
        self.format_desc = QLabel()
        self.format_desc.setStyleSheet("color: #b0b0b0; font-size: 11px; font-style: italic;")
        self.format_desc.setWordWrap(True)
        output_layout.addWidget(self.format_desc)
        
        # File info group
        # File info
        info_frame = QFrame()
        info_frame.setStyleSheet("background-color: #252525; border-radius: 6px; padding: 10px;")
        info_layout = QVBoxLayout(info_frame)
        
        self.file_info_label = QLabel("Estimated file size will be calculated based on settings")
        self.file_info_label.setStyleSheet("color: #b0b0b0; font-size: 11px;")
        self.file_info_label.setWordWrap(True)
        info_layout.addWidget(self.file_info_label)
        
        output_layout.addWidget(info_frame)
        output_layout.addStretch()
        
        tabs.addTab(output_tab, "Output")
        
        # ===== QUALITY TAB =====
        quality_tab = QWidget()
        quality_layout = QVBoxLayout(quality_tab)
        quality_layout.setSpacing(20)
        quality_layout.setContentsMargins(20, 20, 20, 20)
        
        q_header = QLabel("Video Quality")
        q_header.setFont(QFont("Inter", 12, QFont.Weight.Bold))
        q_header.setStyleSheet("color: #64b5f6;")
        quality_layout.addWidget(q_header)
        
        # Quality preset selector
        preset_row = QHBoxLayout()
        preset_label = QLabel("Preset:")
        preset_label.setStyleSheet("font-weight: 600; color: #ffffff;")
        preset_row.addWidget(preset_label)
        
        self.quality_combo = QComboBox()
        self.quality_combo.setMinimumHeight(40)
        for name, info in QUALITY_PRESETS.items():
            self.quality_combo.addItem(f"{name} - {info['desc']}", name)
        self.quality_combo.setCurrentIndex(2)  # Default to Medium
        self.quality_combo.currentTextChanged.connect(self._on_quality_changed)
        preset_row.addWidget(self.quality_combo, 1)
        quality_layout.addLayout(preset_row)
        
        # CRF slider
        crf_row = QHBoxLayout()
        crf_label = QLabel("Quality (CRF):")
        crf_label.setStyleSheet("font-weight: 600; color: #ffffff;")
        crf_row.addWidget(crf_label)
        
        self.crf_slider = QSlider(Qt.Orientation.Horizontal)
        self.crf_slider.setRange(0, 51)
        self.crf_slider.setValue(23)
        self.crf_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.crf_slider.setTickInterval(5)
        self.crf_slider.valueChanged.connect(self._on_crf_changed)
        crf_row.addWidget(self.crf_slider, 1)
        
        self.crf_value_label = QLabel("23")
        self.crf_value_label.setStyleSheet("font-weight: bold; color: #4fc3f7; min-width: 30px;")
        crf_row.addWidget(self.crf_value_label)
        quality_layout.addLayout(crf_row)
        
        crf_hint = QLabel("Lower = better quality, larger file | Higher = smaller file, lower quality")
        crf_hint.setStyleSheet("color: #b8b8b8; font-size: 11px;")
        quality_layout.addWidget(crf_hint)
        
        quality_layout.addSpacing(10)
        
        # Bitrate option
        bitrate_row = QHBoxLayout()
        self.use_bitrate_check = QCheckBox("Use fixed bitrate instead of CRF (Advanced)")
        self.use_bitrate_check.toggled.connect(self._on_bitrate_mode_toggled)
        bitrate_row.addWidget(self.use_bitrate_check)
        quality_layout.addLayout(bitrate_row)
        
        bitrate_control_row = QHBoxLayout()
        bitrate_control_label = QLabel("Bitrate:")
        bitrate_control_label.setStyleSheet("font-weight: 600; color: #ffffff;")
        bitrate_control_row.addWidget(bitrate_control_label)
        
        self.bitrate_spin = QSpinBox()
        self.bitrate_spin.setRange(1000, 100000)
        self.bitrate_spin.setValue(10000)
        self.bitrate_spin.setSingleStep(1000)
        self.bitrate_spin.setSuffix(" kbps")
        self.bitrate_spin.setMinimumHeight(40)
        self.bitrate_spin.setEnabled(False)
        bitrate_control_row.addWidget(self.bitrate_spin, 1)
        quality_layout.addLayout(bitrate_control_row)
        quality_layout.addStretch()
        
        tabs.addTab(quality_tab, "Quality")
        
        # ===== AUDIO TAB =====
        audio_tab = QWidget()
        audio_layout = QVBoxLayout(audio_tab)
        audio_layout.setSpacing(20)
        audio_layout.setContentsMargins(20, 20, 20, 20)
        
        a_header = QLabel("Audio Configuration")
        a_header.setFont(QFont("Inter", 12, QFont.Weight.Bold))
        a_header.setStyleSheet("color: #64b5f6;")
        audio_layout.addWidget(a_header)
        
        self.audio_cb = QCheckBox("✅ Include audio in recording")
        self.audio_cb.setChecked(include_audio)
        self.audio_cb.setMinimumHeight(32)
        self.audio_cb.setStyleSheet("font-size: 13px; font-weight: 600; color: #4fc3f7;")
        self.audio_cb.stateChanged.connect(self._on_audio_toggled)
        audio_layout.addWidget(self.audio_cb)
        
        # Audio device selection
        device_row = QHBoxLayout()
        device_label = QLabel("Audio Device:")
        device_label.setMinimumWidth(90)
        device_label.setStyleSheet("font-weight: 600; color: #ffffff;")
        device_row.addWidget(device_label)
        
        self.audio_device_combo = QComboBox()
        self.audio_device_combo.setMinimumHeight(40)
        self.audio_device_combo.addItem("🎤 Default", "")
        device_row.addWidget(self.audio_device_combo, 1)
        
        # Refresh button
        refresh_btn = QPushButton("🔄", self)
        refresh_btn.setMaximumWidth(45)
        refresh_btn.setMinimumHeight(40)
        refresh_btn.setToolTip("Refresh audio devices list")
        refresh_btn.clicked.connect(self._on_refresh_audio_devices)
        device_row.addWidget(refresh_btn)
        audio_layout.addLayout(device_row)
        
        # Load available audio devices
        QTimer.singleShot(500, self._on_refresh_audio_devices)
        
        # Audio codec
        codec_row = QHBoxLayout()
        codec_label = QLabel("Audio Codec:")
        codec_label.setStyleSheet("font-weight: 600; color: #ffffff;")
        codec_row.addWidget(codec_label)
        
        self.audio_codec_combo = QComboBox()
        self.audio_codec_combo.setMinimumHeight(40)
        self.audio_codec_combo.addItems(["AAC (Best compatibility)", "MP3 (Universal)", "FLAC (Lossless)", "Opus (High quality)"])
        codec_row.addWidget(self.audio_codec_combo, 1)
        audio_layout.addLayout(codec_row)
        
        # Audio bitrate
        audio_bitrate_row = QHBoxLayout()
        audio_bitrate_label = QLabel("Audio Bitrate:")
        audio_bitrate_label.setStyleSheet("font-weight: 600; color: #ffffff;")
        audio_bitrate_row.addWidget(audio_bitrate_label)
        
        self.audio_bitrate_combo = QComboBox()
        self.audio_bitrate_combo.setMinimumHeight(40)
        self.audio_bitrate_combo.addItems(["128 kbps", "192 kbps (Recommended)", "256 kbps", "320 kbps (High quality)"])
        self.audio_bitrate_combo.setCurrentIndex(1)
        audio_bitrate_row.addWidget(self.audio_bitrate_combo, 1)
        audio_layout.addLayout(audio_bitrate_row)
        audio_layout.addStretch()
        
        tabs.addTab(audio_tab, "Audio")
        
        # ===== ADVANCED TAB =====
        advanced_tab = QWidget()
        advanced_layout = QVBoxLayout(advanced_tab)
        advanced_layout.setSpacing(20)
        advanced_layout.setContentsMargins(20, 20, 20, 20)
        
        adv_header = QLabel("Performance & Encoding")
        adv_header.setFont(QFont("Inter", 12, QFont.Weight.Bold))
        adv_header.setStyleSheet("color: #64b5f6;")
        advanced_layout.addWidget(adv_header)
        
        # Hardware acceleration
        self.hw_accel_check = QCheckBox("🚀 Use hardware acceleration (if available)")
        self.hw_accel_check.setChecked(True)
        self.hw_accel_check.setStyleSheet("font-weight: 500;")
        advanced_layout.addWidget(self.hw_accel_check)
        
        # Fast start
        self.fast_start_check = QCheckBox("⚡ Enable fast start (optimize for web)")
        self.fast_start_check.setChecked(True)
        self.fast_start_check.setStyleSheet("font-weight: 500;")
        advanced_layout.addWidget(self.fast_start_check)
        
        # Two-pass encoding
        self.two_pass_check = QCheckBox("🎯 Two-pass encoding (better quality, slower)")
        self.two_pass_check.setChecked(False)
        self.two_pass_check.setStyleSheet("font-weight: 500;")
        advanced_layout.addWidget(self.two_pass_check)
        
        advanced_layout.addSpacing(10)
        
        # Encoder preset
        encoder_row = QHBoxLayout()
        encoder_label = QLabel("Encoder Speed:")
        encoder_label.setStyleSheet("font-weight: 600; color: #ffffff;")
        encoder_row.addWidget(encoder_label)
        
        self.encoder_preset_combo = QComboBox()
        self.encoder_preset_combo.setMinimumHeight(40)
        self.encoder_preset_combo.addItems(["ultrafast", "superfast", "veryfast", "faster", "fast", "medium (Recommended)", "slow", "slower", "veryslow"])
        self.encoder_preset_combo.setCurrentIndex(5)
        encoder_row.addWidget(self.encoder_preset_combo, 1)
        advanced_layout.addLayout(encoder_row)
        
        encoder_hint = QLabel("Faster = quicker encoding, larger files | Slower = better compression")
        encoder_hint.setStyleSheet("color: #b0b0b0; font-size: 11px;")
        advanced_layout.addWidget(encoder_hint)
        advanced_layout.addStretch()
        
        tabs.addTab(advanced_tab, "Advanced")
        
        # Add tabs to main layout
        layout.addWidget(tabs)
        
        # Initialize
        self._on_format_changed()
        self._update_file_info()

    def _on_browse(self):
        filename, _ = QFileDialog.getSaveFileName(
            self, "Save Recording As", 
            self.path_edit.text() if self.path_edit.text() else "recording",
            "MP4 Files (*.mp4);;MKV Files (*.mkv);;MOV Files (*.mov);;WebM Files (*.webm)"
        )
        if filename:
            self.path_edit.setText(filename)
            self._update_file_info()

    def _on_format_changed(self):
        desc = self.format_combo.currentText()
        name = desc.split(" - ")[0]
        info = FORMAT_PRESETS.get(name, {})
        self.format_desc.setText(f"🎥 {info.get('desc', '')} | Codec: {info.get('codec', '')}")
        self._update_file_info()

    def _on_quality_changed(self, desc):
        name = desc.split(" - ")[0]
        info = QUALITY_PRESETS.get(name, {})
        self.crf_slider.blockSignals(True)
        self.crf_slider.setValue(info.get("crf", 23))
        self.crf_slider.blockSignals(False)
        self.crf_value_label.setText(str(info.get("crf", 23)))
        
        # If preset is selected, update bitrate if in bitrate mode
        if self.use_bitrate_check.isChecked():
            self.bitrate_spin.setValue(info.get("bitrate", 10000))
        
        self._update_file_info()

    def _on_crf_changed(self, val):
        self.crf_value_label.setText(str(val))
        self._update_file_info()

    def _on_bitrate_mode_toggled(self, checked):
        self.bitrate_spin.setEnabled(checked)
        self.crf_slider.setEnabled(not checked)
        self._update_file_info()

    def _update_file_info(self):
        try:
            # Estimate file size
            # Base logic: assume 1 hour of recording
            duration_sec = 3600
            
            video_bitrate = 0
            if self.use_bitrate_check.isChecked():
                video_bitrate = self.bitrate_spin.value()
            else:
                crf = self.crf_slider.value()
                video_bitrate = self._estimate_bitrate_from_crf(crf)
            
            # Audio bitrate
            ab_text = self.audio_codec_combo.currentText()
            # Simple fallback default
            audio_bitrate = 192 
            try:
                # Try to parse from second combo? Oops that's codec, bitrate is in audio_bitrate_combo
                if hasattr(self, 'audio_bitrate_combo'):
                    ab_txt = self.audio_bitrate_combo.currentText()
                    audio_bitrate = int(ab_txt.split(" ")[0])
            except:
                pass

            total_bitrate = video_bitrate + audio_bitrate
            size_mb = (total_bitrate * duration_sec) / 8 / 1024
            
            self.file_info_label.setText(
                f"📊 Estimated Bitrate: ~{total_bitrate} kbps\n"
                f"💾 Approx. File Size (1 hour): ~{size_mb/1024:.2f} GB\n"
                f"ℹ️ Actual size depends on content complexity."
            )
        except Exception as e:
            print(f"Error updating estimation: {e}")

    def _estimate_bitrate_from_crf(self, crf):
        # Very rough estimation for 1080p60
        # CRF 0 -> Lossless (huge)
        # CRF 18 ~ 15-20 Mbps
        # CRF 23 ~ 8-10 Mbps
        # CRF 28 ~ 4-5 Mbps
        if crf == 0: return 50000 # Cap estimation
        # Rough exponential fit
        # 18 -> 20000, 28 -> 4000
        # This is just for UI feedback
        val = 60000 * (0.85 ** crf)
        return int(max(1000, val))

    def get_values(self):
        """Return the core recording configuration."""
        fmt_text = self.format_combo.currentText().split(" - ")[0]
        preset = FORMAT_PRESETS.get(fmt_text, {})
        
        return {
            "output_path": self.path_edit.text(),
            "format": preset.get("ext", ".mp4"),
            "video_codec": preset.get("codec", "libx264"),
            "audio_enabled": self.audio_cb.isChecked(),
            "audio_device": self.audio_device_combo.currentData() or "",
            "audio_codec": self.audio_codec_combo.currentText().split(" ")[0].lower(),
            "audio_bitrate": self.audio_bitrate_combo.currentText().split(" ")[0],
            # Quality
            "crf": self.crf_slider.value(),
            "use_fixed_bitrate": self.use_bitrate_check.isChecked(),
            "video_bitrate": self.bitrate_spin.value()
        }

    def _on_audio_toggled(self, state):
        """Enable/disable audio device selection based on checkbox."""
        enabled = state > 0
        self.audio_device_combo.setEnabled(enabled)
        print(f"[AUDIO] Audio recording toggled: {enabled}")

    def _on_refresh_audio_devices(self):
        """Refresh the audio device list."""
        print("[AUDIO] 🔄 Refreshing audio device list...")
        current_selection = self.audio_device_combo.currentData() if self.audio_device_combo.count() > 0 else None
        self.audio_device_combo.clear()
        self.audio_device_combo.addItem("🎤 Default (Auto-detect)", "")
        print("[AUDIO] Added Default option")
        
        # Only on Windows
        if _sys.platform.startswith('win'):
            try:
                devices = _list_windows_audio_devices()
                if devices:
                    print(f"[AUDIO] Adding {len(devices)} device(s) to dropdown...")
                    for i, (friendly_name, alt_name) in enumerate(devices):
                        # Use alternative name if available, otherwise friendly name
                        device_id = alt_name or friendly_name
                        display_name = f"🎤 {friendly_name}"
                        self.audio_device_combo.addItem(display_name, device_id)
                        print(f"[AUDIO] ✅ Added to dropdown: {display_name}")
                else:
                    print("[AUDIO] ⚠️ No audio devices returned from detection")
            except Exception as e:
                print(f"[AUDIO] ❌ Failed to load audio devices: {e}")
                import traceback
                traceback.print_exc()
        else:
            print(f"[AUDIO] ⚠️ Not on Windows, skipping device scan")
        
        # Restore previous selection or initial selection
        selection_to_restore = current_selection or self.initial_audio_device
        if selection_to_restore:
            idx = self.audio_device_combo.findData(selection_to_restore)
            if idx >= 0:
                self.audio_device_combo.setCurrentIndex(idx)
                print(f"[AUDIO] ✅ Restored previous device selection")
            else:
                # Try to find by friendly name match if alt name doesn't match
                for i in range(self.audio_device_combo.count()):
                    item_data = self.audio_device_combo.itemData(i)
                    item_text = self.audio_device_combo.itemText(i)
                    if item_data == selection_to_restore or selection_to_restore in item_text:
                        self.audio_device_combo.setCurrentIndex(i)
                        print(f"[AUDIO] ✅ Found device by text match")
                        break
        
        print(f"[AUDIO] 📊 Dropdown now has {self.audio_device_combo.count()} items")

    def get_advanced_settings(self):
        """Return advanced configuration."""
        return {
            "hw_accel": self.hw_accel_check.isChecked(),
            "fast_start": self.fast_start_check.isChecked(),
            "two_pass": self.two_pass_check.isChecked(),
            "preset": self.encoder_preset_combo.currentText().split(" (")[0]
        }

class RecordingSettingsDialog(QDialog):
    def __init__(self, parent=None, *, initial_path: str = '', include_audio: bool = True, initial_audio_device: str = ''):
        super().__init__(parent)
        self.setWindowTitle("🎥 Recording Settings")
        self.setModal(True)
        self.setMinimumSize(600, 500)
        self.setStyleSheet("QDialog { background-color: #121212; color: #ffffff; }")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0,0,0,0)
        
        self.panel = RecordingSettingsPanel(self, initial_path=initial_path, include_audio=include_audio, initial_audio_device=initial_audio_device)
        layout.addWidget(self.panel)
        
        # Action buttons
        btns = QHBoxLayout()
        btns.setContentsMargins(12, 12, 12, 12)
        btns.addStretch(1)
        
        save_btn = QPushButton("💾 Save & Close", self)
        save_btn.setMinimumHeight(36)
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #2e7d32, stop:1 #1b5e20);
                font-size: 13px;
                padding: 10px 24px;
                color: white; border: none; border-radius: 6px; font-weight: 600;
            }
            QPushButton:hover {
                background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #388e3c, stop:1 #2e7d32);
            }
        """)
        save_btn.clicked.connect(self.accept)
        
        cancel_btn = QPushButton("❌ Cancel", self)
        cancel_btn.setMinimumHeight(36)
        cancel_btn.setStyleSheet("QPushButton { color: white; background-color: #c62828; border-radius: 6px; padding: 10px 24px; font-weight: 600; }")
        cancel_btn.clicked.connect(self.reject)
        
        btns.addWidget(save_btn)
        btns.addWidget(cancel_btn)
        layout.addLayout(btns)
    
    # Delegated methods for compatibility
    def get_values(self): return self.panel.get_values()
    def get_advanced_settings(self): return self.panel.get_advanced_settings()




