from __future__ import annotations
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QFileDialog, QCheckBox, QComboBox, QGroupBox, QTabWidget, QWidget,
    QSpinBox, QSlider, QTextEdit, QSizePolicy, QFrame
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont
import os

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

class RecordingSettingsDialog(QDialog):
    def __init__(self, parent=None, *, initial_path: str = '', include_audio: bool = True):
        super().__init__(parent)
        self.setWindowTitle("🎥 Recording Settings")
        self.setModal(True)
        self.setMinimumSize(600, 500)
        
        # Modern dark theme styling (matching stream settings)
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
        """)

        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(12, 12, 12, 12)
        
        # Create tabs
        tabs = QTabWidget()
        
        # ===== OUTPUT TAB =====
        output_tab = QWidget()
        output_layout = QVBoxLayout(output_tab)
        output_layout.setSpacing(12)
        
        # Output file group
        output_group = QGroupBox("📁 Output File")
        output_group_layout = QVBoxLayout(output_group)
        output_group_layout.setSpacing(10)
        
        # File path row
        path_row = QHBoxLayout()
        path_label = QLabel("Save to:")
        path_label.setStyleSheet("font-weight: 600; color: #ffffff;")
        path_row.addWidget(path_label)
        
        self.path_edit = QLineEdit(self)
        self.path_edit.setPlaceholderText("/path/to/output.mp4")
        self.path_edit.setMinimumHeight(32)
        if initial_path:
            self.path_edit.setText(initial_path)
        path_row.addWidget(self.path_edit, 1)
        
        browse_btn = QPushButton("📂 Browse", self)
        browse_btn.setMinimumHeight(32)
        browse_btn.clicked.connect(self._on_browse)
        path_row.addWidget(browse_btn)
        output_group_layout.addLayout(path_row)
        
        # Format preset
        format_row = QHBoxLayout()
        format_label = QLabel("Format:")
        format_label.setStyleSheet("font-weight: 600; color: #ffffff;")
        format_row.addWidget(format_label)
        
        self.format_combo = QComboBox()
        self.format_combo.setMinimumHeight(32)
        for name, info in FORMAT_PRESETS.items():
            self.format_combo.addItem(f"{name} - {info['desc']}", name)
        self.format_combo.currentTextChanged.connect(self._on_format_changed)
        format_row.addWidget(self.format_combo, 1)
        output_group_layout.addLayout(format_row)
        
        # Format description
        self.format_desc = QLabel()
        self.format_desc.setStyleSheet("color: #b0b0b0; font-size: 11px; font-style: italic;")
        self.format_desc.setWordWrap(True)
        output_group_layout.addWidget(self.format_desc)
        
        output_layout.addWidget(output_group)
        
        # File info group
        info_group = QGroupBox("ℹ️ File Information")
        info_layout = QVBoxLayout(info_group)
        
        self.file_info_label = QLabel("Estimated file size will be calculated based on settings")
        self.file_info_label.setStyleSheet("color: #b0b0b0; font-size: 11px;")
        self.file_info_label.setWordWrap(True)
        info_layout.addWidget(self.file_info_label)
        
        output_layout.addWidget(info_group)
        output_layout.addStretch()
        
        tabs.addTab(output_tab, "Output")
        
        # ===== QUALITY TAB =====
        quality_tab = QWidget()
        quality_layout = QVBoxLayout(quality_tab)
        quality_layout.setSpacing(12)
        
        # Quality preset group
        quality_group = QGroupBox("⭐ Quality Settings")
        quality_group_layout = QVBoxLayout(quality_group)
        quality_group_layout.setSpacing(10)
        
        # Quality preset selector
        preset_row = QHBoxLayout()
        preset_label = QLabel("Preset:")
        preset_label.setStyleSheet("font-weight: 600; color: #ffffff;")
        preset_row.addWidget(preset_label)
        
        self.quality_combo = QComboBox()
        self.quality_combo.setMinimumHeight(32)
        for name, info in QUALITY_PRESETS.items():
            self.quality_combo.addItem(f"{name} - {info['desc']}", name)
        self.quality_combo.setCurrentIndex(2)  # Default to Medium
        self.quality_combo.currentTextChanged.connect(self._on_quality_changed)
        preset_row.addWidget(self.quality_combo, 1)
        quality_group_layout.addLayout(preset_row)
        
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
        quality_group_layout.addLayout(crf_row)
        
        crf_hint = QLabel("Lower = better quality, larger file | Higher = smaller file, lower quality")
        crf_hint.setStyleSheet("color: #b0b0b0; font-size: 10px; font-style: italic;")
        quality_group_layout.addWidget(crf_hint)
        
        # Bitrate option
        bitrate_row = QHBoxLayout()
        self.use_bitrate_check = QCheckBox("Use fixed bitrate instead of CRF")
        self.use_bitrate_check.toggled.connect(self._on_bitrate_mode_toggled)
        bitrate_row.addWidget(self.use_bitrate_check)
        quality_group_layout.addLayout(bitrate_row)
        
        bitrate_control_row = QHBoxLayout()
        bitrate_control_label = QLabel("Bitrate:")
        bitrate_control_label.setStyleSheet("font-weight: 600; color: #ffffff;")
        bitrate_control_row.addWidget(bitrate_control_label)
        
        self.bitrate_spin = QSpinBox()
        self.bitrate_spin.setRange(1000, 100000)
        self.bitrate_spin.setValue(10000)
        self.bitrate_spin.setSingleStep(1000)
        self.bitrate_spin.setSuffix(" kbps")
        self.bitrate_spin.setMinimumHeight(32)
        self.bitrate_spin.setEnabled(False)
        bitrate_control_row.addWidget(self.bitrate_spin, 1)
        quality_group_layout.addLayout(bitrate_control_row)
        
        quality_layout.addWidget(quality_group)
        quality_layout.addStretch()
        
        tabs.addTab(quality_tab, "Quality")
        
        # ===== AUDIO TAB =====
        audio_tab = QWidget()
        audio_layout = QVBoxLayout(audio_tab)
        audio_layout.setSpacing(12)
        
        # Audio settings group
        audio_group = QGroupBox("🎧 Audio Settings")
        audio_group_layout = QVBoxLayout(audio_group)
        audio_group_layout.setSpacing(10)
        
        self.audio_cb = QCheckBox("✅ Include audio in recording")
        self.audio_cb.setChecked(include_audio)
        self.audio_cb.setMinimumHeight(32)
        self.audio_cb.setStyleSheet("font-size: 13px; font-weight: 600; color: #4fc3f7;")
        audio_group_layout.addWidget(self.audio_cb)
        
        # Audio codec
        codec_row = QHBoxLayout()
        codec_label = QLabel("Audio Codec:")
        codec_label.setStyleSheet("font-weight: 600; color: #ffffff;")
        codec_row.addWidget(codec_label)
        
        self.audio_codec_combo = QComboBox()
        self.audio_codec_combo.setMinimumHeight(32)
        self.audio_codec_combo.addItems(["AAC (Best compatibility)", "MP3 (Universal)", "FLAC (Lossless)", "Opus (High quality)"])
        codec_row.addWidget(self.audio_codec_combo, 1)
        audio_group_layout.addLayout(codec_row)
        
        # Audio bitrate
        audio_bitrate_row = QHBoxLayout()
        audio_bitrate_label = QLabel("Audio Bitrate:")
        audio_bitrate_label.setStyleSheet("font-weight: 600; color: #ffffff;")
        audio_bitrate_row.addWidget(audio_bitrate_label)
        
        self.audio_bitrate_combo = QComboBox()
        self.audio_bitrate_combo.setMinimumHeight(32)
        self.audio_bitrate_combo.addItems(["128 kbps", "192 kbps (Recommended)", "256 kbps", "320 kbps (High quality)"])
        self.audio_bitrate_combo.setCurrentIndex(1)
        audio_bitrate_row.addWidget(self.audio_bitrate_combo, 1)
        audio_group_layout.addLayout(audio_bitrate_row)
        
        audio_layout.addWidget(audio_group)
        audio_layout.addStretch()
        
        tabs.addTab(audio_tab, "Audio")
        
        # ===== ADVANCED TAB =====
        advanced_tab = QWidget()
        advanced_layout = QVBoxLayout(advanced_tab)
        advanced_layout.setSpacing(12)
        
        # Advanced options group
        advanced_group = QGroupBox("⚙️ Advanced Options")
        advanced_group_layout = QVBoxLayout(advanced_group)
        advanced_group_layout.setSpacing(10)
        
        # Hardware acceleration
        self.hw_accel_check = QCheckBox("🚀 Use hardware acceleration (if available)")
        self.hw_accel_check.setChecked(True)
        self.hw_accel_check.setStyleSheet("font-weight: 500;")
        advanced_group_layout.addWidget(self.hw_accel_check)
        
        # Fast start
        self.fast_start_check = QCheckBox("⚡ Enable fast start (web streaming)")
        self.fast_start_check.setChecked(True)
        self.fast_start_check.setStyleSheet("font-weight: 500;")
        advanced_group_layout.addWidget(self.fast_start_check)
        
        # Two-pass encoding
        self.two_pass_check = QCheckBox("🎯 Two-pass encoding (better quality, slower)")
        self.two_pass_check.setChecked(False)
        self.two_pass_check.setStyleSheet("font-weight: 500;")
        advanced_group_layout.addWidget(self.two_pass_check)
        
        # Encoder preset
        encoder_row = QHBoxLayout()
        encoder_label = QLabel("Encoder Speed:")
        encoder_label.setStyleSheet("font-weight: 600; color: #ffffff;")
        encoder_row.addWidget(encoder_label)
        
        self.encoder_preset_combo = QComboBox()
        self.encoder_preset_combo.setMinimumHeight(32)
        self.encoder_preset_combo.addItems(["ultrafast", "superfast", "veryfast", "faster", "fast", "medium (Recommended)", "slow", "slower", "veryslow"])
        self.encoder_preset_combo.setCurrentIndex(5)
        encoder_row.addWidget(self.encoder_preset_combo, 1)
        advanced_group_layout.addLayout(encoder_row)
        
        encoder_hint = QLabel("Faster = quicker encoding, larger files | Slower = better compression")
        encoder_hint.setStyleSheet("color: #b0b0b0; font-size: 10px; font-style: italic;")
        advanced_group_layout.addWidget(encoder_hint)
        
        advanced_layout.addWidget(advanced_group)
        advanced_layout.addStretch()
        
        tabs.addTab(advanced_tab, "Advanced")
        
        # Add tabs to main layout
        layout.addWidget(tabs)
        
        # Action buttons
        btns = QHBoxLayout()
        btns.addStretch(1)
        
        save_btn = QPushButton("💾 Save & Close", self)
        save_btn.setMinimumHeight(36)
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #2e7d32, stop:1 #1b5e20);
                font-size: 13px;
                padding: 10px 24px;
            }
            QPushButton:hover {
                background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #388e3c, stop:1 #2e7d32);
            }
        """)
        save_btn.clicked.connect(self.accept)
        
        cancel_btn = QPushButton("❌ Cancel", self)
        cancel_btn.setMinimumHeight(36)
        cancel_btn.clicked.connect(self.reject)
        
        btns.addWidget(save_btn)
        btns.addWidget(cancel_btn)
        layout.addLayout(btns)
        
        # Initialize
        self._on_format_changed()
        self._update_file_info()

    def _on_browse(self):
        path, _ = QFileDialog.getSaveFileName(self, "Choose output file", self.path_edit.text() or "", "Video (*.mp4 *.mov *.mkv)")
        if path:
            self.path_edit.setText(path)

    def _on_format_changed(self):
        """Update file extension when format changes."""
        try:
            current_format = self.format_combo.currentData()
            if current_format and current_format in FORMAT_PRESETS:
                preset = FORMAT_PRESETS[current_format]
                self.format_desc.setText(f"Codec: {preset['codec']} | {preset['desc']}")
                
                # Update file extension in path
                current_path = self.path_edit.text()
                if current_path:
                    base = os.path.splitext(current_path)[0]
                    new_path = base + preset['ext']
                    self.path_edit.setText(new_path)
            
            self._update_file_info()
        except Exception as e:
            print(f"Error updating format: {e}")
    
    def _on_quality_changed(self):
        """Update CRF/bitrate when quality preset changes."""
        try:
            current_quality = self.quality_combo.currentData()
            if current_quality and current_quality in QUALITY_PRESETS:
                preset = QUALITY_PRESETS[current_quality]
                self.crf_slider.setValue(preset['crf'])
                self.bitrate_spin.setValue(preset['bitrate'])
            
            self._update_file_info()
        except Exception as e:
            print(f"Error updating quality: {e}")
    
    def _on_crf_changed(self, value: int):
        """Update CRF value label."""
        try:
            self.crf_value_label.setText(str(value))
            
            # Color code based on quality
            if value <= 18:
                color = "#4fc3f7"  # Cyan - high quality
            elif value <= 28:
                color = "#4caf50"  # Green - good quality
            else:
                color = "#ff9800"  # Orange - lower quality
            
            self.crf_value_label.setStyleSheet(f"font-weight: bold; color: {color}; min-width: 30px;")
            self._update_file_info()
        except Exception as e:
            print(f"Error updating CRF: {e}")
    
    def _on_bitrate_mode_toggled(self, checked: bool):
        """Toggle between CRF and bitrate mode."""
        try:
            self.crf_slider.setEnabled(not checked)
            self.bitrate_spin.setEnabled(checked)
            self._update_file_info()
        except Exception as e:
            print(f"Error toggling bitrate mode: {e}")
    
    def _update_file_info(self):
        """Update estimated file size information."""
        try:
            # Get current settings
            use_bitrate = self.use_bitrate_check.isChecked()
            bitrate = self.bitrate_spin.value() if use_bitrate else self._estimate_bitrate_from_crf()
            
            # Estimate for 1 minute of video
            video_size_mb = (bitrate * 60) / (8 * 1024)  # Convert kbps to MB
            
            # Add audio if enabled
            if self.audio_cb.isChecked():
                audio_bitrate_text = self.audio_bitrate_combo.currentText()
                audio_bitrate = int(audio_bitrate_text.split()[0])  # Extract number
                audio_size_mb = (audio_bitrate * 60) / (8 * 1024)
                total_size_mb = video_size_mb + audio_size_mb
            else:
                total_size_mb = video_size_mb
            
            # Format info text
            info_text = f"📊 Estimated size: ~{total_size_mb:.1f} MB per minute\n"
            info_text += f"📹 Video: {bitrate} kbps"
            
            if self.audio_cb.isChecked():
                info_text += f" | 🎧 Audio: {audio_bitrate_text}"
            
            self.file_info_label.setText(info_text)
        except Exception as e:
            print(f"Error updating file info: {e}")
            self.file_info_label.setText("Unable to estimate file size")
    
    def _estimate_bitrate_from_crf(self) -> int:
        """Estimate bitrate from CRF value (rough approximation)."""
        crf = self.crf_slider.value()
        
        # Rough estimates for 1080p video
        if crf <= 18:
            return 20000
        elif crf <= 23:
            return 10000
        elif crf <= 28:
            return 5000
        else:
            return 2500

    def get_values(self) -> tuple[str, bool]:
        """Return basic values for backward compatibility."""
        return self.path_edit.text().strip(), bool(self.audio_cb.isChecked())
    
    def get_advanced_settings(self) -> dict:
        """Return all advanced settings."""
        current_format = self.format_combo.currentData()
        format_preset = FORMAT_PRESETS.get(current_format, FORMAT_PRESETS["MP4 (H.264)"])
        
        encoder_preset = self.encoder_preset_combo.currentText().split()[0]  # Remove "(Recommended)"
        
        audio_codec_map = {
            "AAC (Best compatibility)": "aac",
            "MP3 (Universal)": "libmp3lame",
            "FLAC (Lossless)": "flac",
            "Opus (High quality)": "libopus",
        }
        
        audio_codec = audio_codec_map.get(
            self.audio_codec_combo.currentText(),
            "aac"
        )
        
        audio_bitrate_text = self.audio_bitrate_combo.currentText()
        audio_bitrate = int(audio_bitrate_text.split()[0])  # Extract number
        
        return {
            'output_path': self.path_edit.text().strip(),
            'include_audio': bool(self.audio_cb.isChecked()),
            'format': current_format,
            'video_codec': format_preset['codec'],
            'use_crf': not self.use_bitrate_check.isChecked(),
            'crf': self.crf_slider.value(),
            'bitrate': self.bitrate_spin.value(),
            'audio_codec': audio_codec,
            'audio_bitrate': audio_bitrate,
            'encoder_preset': encoder_preset,
            'hardware_accel': self.hw_accel_check.isChecked(),
            'fast_start': self.fast_start_check.isChecked(),
            'two_pass': self.two_pass_check.isChecked(),
        }
