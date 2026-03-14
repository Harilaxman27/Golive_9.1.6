#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GoLive Studio - FFmpeg Validator
Validates FFmpeg installation on startup and provides helpful error messages
"""

import os
import sys
import subprocess
import shutil
from typing import Optional, Dict, Any, Tuple
from pathlib import Path
from PyQt6.QtWidgets import QMessageBox, QWidget


class FFmpegValidator:
    """Validates FFmpeg installation and provides troubleshooting"""
    
    def __init__(self):
        self.ffmpeg_path: Optional[str] = None
        self.ffprobe_path: Optional[str] = None
        self.validation_result: Dict[str, Any] = {}
    
    def validate_on_startup(self, parent: Optional[QWidget] = None) -> Tuple[bool, str]:
        """
        Validate FFmpeg installation on application startup
        
        Args:
            parent: Parent widget for dialogs
            
        Returns:
            Tuple of (success, error_message)
        """
        # Try to find FFmpeg
        ffmpeg_path = self._find_ffmpeg()
        
        if not ffmpeg_path:
            return self._handle_ffmpeg_not_found(parent)
        
        # Validate FFmpeg works
        if not self._test_ffmpeg(ffmpeg_path):
            return self._handle_ffmpeg_not_working(ffmpeg_path, parent)
        
        # Store paths
        self.ffmpeg_path = ffmpeg_path
        self.ffprobe_path = self._find_ffprobe()
        
        # Validate encoders
        encoder_check = self._check_required_encoders(ffmpeg_path)
        if not encoder_check['has_minimum']:
            self._warn_missing_encoders(encoder_check, parent)
            # Continue anyway - libx264 fallback exists
        
        return True, ""
    
    def _find_ffmpeg(self) -> Optional[str]:
        """Find FFmpeg binary in various locations"""
        
        # 1. Check environment variable
        env_path = os.environ.get('GOLIVE_FFMPEG_PATH') or os.environ.get('FFMPEG_PATH')
        if env_path and os.path.exists(env_path):
            return env_path
        
        # 2. Check bundled FFmpeg (for packaged apps)
        try:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            
            # Common bundled paths
            bundled_paths = [
                os.path.join(base_dir, 'ffmpeg', 'ffmpeg'),
                os.path.join(base_dir, '..', 'Resources', 'ffmpeg', 'ffmpeg'),
                os.path.join(base_dir, 'bin', 'ffmpeg'),
            ]
            
            # Add .exe extension on Windows
            if sys.platform.startswith('win'):
                bundled_paths = [p + '.exe' for p in bundled_paths]
            
            for path in bundled_paths:
                if os.path.exists(path) and os.access(path, os.X_OK):
                    return path
        except Exception:
            pass
        
        # 3. Check system PATH
        ffmpeg_name = 'ffmpeg.exe' if sys.platform.startswith('win') else 'ffmpeg'
        system_ffmpeg = shutil.which(ffmpeg_name) or shutil.which('ffmpeg')
        if system_ffmpeg:
            return system_ffmpeg
        
        # 4. Check common install locations
        common_paths = []
        
        if sys.platform == 'darwin':
            common_paths = [
                '/opt/homebrew/bin/ffmpeg',
                '/usr/local/bin/ffmpeg',
                '/opt/local/bin/ffmpeg',
            ]
        elif sys.platform.startswith('win'):
            common_paths = [
                r'C:\Program Files\ffmpeg\bin\ffmpeg.exe',
                r'C:\ffmpeg\bin\ffmpeg.exe',
            ]
        else:  # Linux
            common_paths = [
                '/usr/bin/ffmpeg',
                '/usr/local/bin/ffmpeg',
                '/snap/bin/ffmpeg',
            ]
        
        for path in common_paths:
            if os.path.exists(path) and os.access(path, os.X_OK):
                return path
        
        return None
    
    def _find_ffprobe(self) -> Optional[str]:
        """Find FFprobe binary (usually alongside FFmpeg)"""
        if not self.ffmpeg_path:
            return None
        
        # Replace 'ffmpeg' with 'ffprobe' in path
        probe_path = self.ffmpeg_path.replace('ffmpeg', 'ffprobe')
        if os.path.exists(probe_path):
            return probe_path
        
        # Try system PATH
        probe_name = 'ffprobe.exe' if sys.platform.startswith('win') else 'ffprobe'
        return shutil.which(probe_name)
    
    def _test_ffmpeg(self, ffmpeg_path: str) -> bool:
        """Test if FFmpeg binary works"""
        try:
            result = subprocess.run(
                [ffmpeg_path, '-version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except Exception:
            return False
    
    def _check_required_encoders(self, ffmpeg_path: str) -> Dict[str, Any]:
        """Check if required encoders are available"""
        try:
            result = subprocess.run(
                [ffmpeg_path, '-hide_banner', '-v', 'quiet', '-encoders'],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            output = (result.stdout or '') + '\n' + (result.stderr or '')
            encoders = set()
            
            for line in output.splitlines():
                parts = line.strip().split()
                if len(parts) >= 2 and parts[0].startswith(('V', 'A', '.')):
                    encoders.add(parts[1])
            
            # Check for essential encoders
            has_libx264 = 'libx264' in encoders
            has_aac = 'aac' in encoders or 'libfdk_aac' in encoders
            has_hardware = any(hw in encoders for hw in [
                'h264_videotoolbox', 'h264_nvenc', 'h264_qsv', 'h264_amf'
            ])
            
            return {
                'has_minimum': has_libx264 and has_aac,
                'has_libx264': has_libx264,
                'has_aac': has_aac,
                'has_hardware': has_hardware,
                'available_encoders': list(encoders)
            }
            
        except Exception:
            return {
                'has_minimum': False,
                'has_libx264': False,
                'has_aac': False,
                'has_hardware': False,
                'available_encoders': []
            }
    
    def _handle_ffmpeg_not_found(self, parent: Optional[QWidget]) -> Tuple[bool, str]:
        """Handle case where FFmpeg is not found"""
        error_msg = "FFmpeg Not Found"
        
        # Build helpful message based on platform
        if sys.platform == 'darwin':
            instructions = (
                "FFmpeg is required for GoLive Studio to function.\n\n"
                "To install FFmpeg on macOS:\n\n"
                "1. Using Homebrew (recommended):\n"
                "   brew install ffmpeg\n\n"
                "2. Using MacPorts:\n"
                "   sudo port install ffmpeg\n\n"
                "3. Download from https://ffmpeg.org/download.html\n\n"
                "After installation, restart GoLive Studio."
            )
        elif sys.platform.startswith('win'):
            instructions = (
                "FFmpeg is required for GoLive Studio to function.\n\n"
                "To install FFmpeg on Windows:\n\n"
                "1. Download from https://ffmpeg.org/download.html\n"
                "2. Extract the archive\n"
                "3. Add the 'bin' folder to your PATH\n"
                "   OR\n"
                "4. Set GOLIVE_FFMPEG_PATH environment variable\n\n"
                "After installation, restart GoLive Studio."
            )
        else:  # Linux
            instructions = (
                "FFmpeg is required for GoLive Studio to function.\n\n"
                "To install FFmpeg on Linux:\n\n"
                "Ubuntu/Debian: sudo apt install ffmpeg\n"
                "Fedora: sudo dnf install ffmpeg\n"
                "Arch: sudo pacman -S ffmpeg\n\n"
                "After installation, restart GoLive Studio."
            )
        
        # Show dialog
        if parent is not None:
            msg_box = QMessageBox(parent)
            msg_box.setIcon(QMessageBox.Icon.Critical)
            msg_box.setWindowTitle("FFmpeg Not Found")
            msg_box.setText(error_msg)
            msg_box.setInformativeText(instructions)
            msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
            msg_box.exec()
        
        return False, instructions
    
    def _handle_ffmpeg_not_working(self, ffmpeg_path: str, 
                                   parent: Optional[QWidget]) -> Tuple[bool, str]:
        """Handle case where FFmpeg exists but doesn't work"""
        error_msg = f"FFmpeg found at {ffmpeg_path} but is not executable."
        
        # Check for macOS quarantine
        if sys.platform == 'darwin' and 'ffmpeg/ffmpeg' in ffmpeg_path:
            instructions = (
                "The bundled FFmpeg may be quarantined by macOS.\n\n"
                "To fix this, run the following command in Terminal:\n\n"
                f"xattr -d com.apple.quarantine '{ffmpeg_path}'\n\n"
                "Then restart GoLive Studio."
            )
        else:
            instructions = (
                "FFmpeg was found but cannot be executed.\n\n"
                "Possible causes:\n"
                "1. File permissions - try making it executable\n"
                "2. Corrupted binary - try reinstalling FFmpeg\n"
                "3. Missing dependencies - install FFmpeg from your package manager\n\n"
                "After fixing, restart GoLive Studio."
            )
        
        # Show dialog
        if parent is not None:
            msg_box = QMessageBox(parent)
            msg_box.setIcon(QMessageBox.Icon.Critical)
            msg_box.setWindowTitle("FFmpeg Not Working")
            msg_box.setText(error_msg)
            msg_box.setInformativeText(instructions)
            msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
            msg_box.exec()
        
        return False, instructions
    
    def _warn_missing_encoders(self, check_result: Dict[str, Any], 
                               parent: Optional[QWidget]) -> None:
        """Warn about missing encoders (non-blocking)"""
        warnings = []
        
        if not check_result['has_libx264']:
            warnings.append("• libx264 encoder not found (software encoding)")
        
        if not check_result['has_aac']:
            warnings.append("• AAC audio encoder not found")
        
        if not check_result['has_hardware']:
            warnings.append("• No hardware encoders found (may affect performance)")
        
        if warnings and parent is not None:
            msg_box = QMessageBox(parent)
            msg_box.setIcon(QMessageBox.Icon.Warning)
            msg_box.setWindowTitle("Encoder Warning")
            msg_box.setText("Some encoders are missing:")
            msg_box.setInformativeText(
                "\n".join(warnings) + "\n\n"
                "GoLive Studio will work with limited functionality.\n"
                "Consider installing a full FFmpeg build."
            )
            msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
            msg_box.exec()
    
    def get_ffmpeg_path(self) -> Optional[str]:
        """Get validated FFmpeg path"""
        return self.ffmpeg_path
    
    def get_ffprobe_path(self) -> Optional[str]:
        """Get validated FFprobe path"""
        return self.ffprobe_path


# Global validator instance
_ffmpeg_validator: Optional[FFmpegValidator] = None


def get_ffmpeg_validator() -> FFmpegValidator:
    """Get or create global FFmpeg validator"""
    global _ffmpeg_validator
    if _ffmpeg_validator is None:
        _ffmpeg_validator = FFmpegValidator()
    return _ffmpeg_validator


def validate_ffmpeg_on_startup(parent: Optional[QWidget] = None) -> Tuple[bool, str]:
    """Convenience function to validate FFmpeg on startup"""
    validator = get_ffmpeg_validator()
    return validator.validate_on_startup(parent)
