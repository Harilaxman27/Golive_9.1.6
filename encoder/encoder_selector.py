#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GoLive Studio - Shared Encoder Selection Logic
Centralized encoder detection and selection for streaming and recording
"""

import sys
import subprocess
from typing import Set, Optional, Dict, Any
from enum import Enum


class EncoderType(Enum):
    """Available encoder types"""
    H264_VIDEOTOOLBOX = "h264_videotoolbox"  # Apple VideoToolbox (macOS)
    H264_NVENC = "h264_nvenc"                # NVIDIA NVENC
    H264_QSV = "h264_qsv"                    # Intel QuickSync
    H264_AMF = "h264_amf"                    # AMD AMF
    LIBX264 = "libx264"                      # Software fallback
    HEVC_VIDEOTOOLBOX = "hevc_videotoolbox"  # Apple HEVC
    HEVC_NVENC = "hevc_nvenc"                # NVIDIA HEVC


class EncoderSelector:
    """Detects and selects the best available encoder"""
    
    def __init__(self, ffmpeg_path: str = 'ffmpeg'):
        """
        Initialize encoder selector
        
        Args:
            ffmpeg_path: Path to FFmpeg binary
        """
        self.ffmpeg_path = ffmpeg_path
        self._available_encoders: Optional[Set[str]] = None
        self._encoder_cache: Dict[str, Any] = {}
    
    def detect_available_encoders(self, force_refresh: bool = False) -> Set[str]:
        """
        Detect all available encoders by querying FFmpeg
        
        Args:
            force_refresh: Force re-detection even if cached
            
        Returns:
            Set of available encoder names
        """
        if self._available_encoders is not None and not force_refresh:
            return self._available_encoders
        
        encoders: Set[str] = set()
        
        try:
            result = subprocess.run(
                [self.ffmpeg_path, '-hide_banner', '-v', 'quiet', '-encoders'],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            output = (result.stdout or '') + '\n' + (result.stderr or '')
            
            for line in output.splitlines():
                # Lines look like: " V....D h264_videotoolbox ..."
                parts = line.strip().split()
                if len(parts) >= 2 and parts[0].startswith(('V', 'A', '.')):
                    encoder_name = parts[1]
                    encoders.add(encoder_name)
            
            self._available_encoders = encoders
            return encoders
            
        except Exception as e:
            print(f"Error detecting encoders: {e}")
            # Return empty set on error; libx264 will be used as fallback
            self._available_encoders = set()
            return self._available_encoders
    
    def select_best_h264_encoder(self, prefer_hardware: bool = True) -> str:
        """
        Select the best available H.264 encoder for the current platform
        
        Args:
            prefer_hardware: Prefer hardware encoders over software
            
        Returns:
            Encoder name (e.g., 'h264_videotoolbox', 'libx264')
        """
        available = self.detect_available_encoders()
        
        if not prefer_hardware:
            return EncoderType.LIBX264.value
        
        # Platform-specific preferences
        if sys.platform == 'darwin':
            # macOS: Prefer VideoToolbox (native, reliable, efficient)
            if EncoderType.H264_VIDEOTOOLBOX.value in available:
                return EncoderType.H264_VIDEOTOOLBOX.value
        
        elif sys.platform.startswith('win'):
            # Windows: Prefer QSV (Intel) > NVENC (NVIDIA) > AMF (AMD)
            # Many laptops (Intel Iris Xe, etc.) have no NVIDIA - QSV works on Intel 11th Gen+
            if EncoderType.H264_QSV.value in available:
                return EncoderType.H264_QSV.value
            if EncoderType.H264_NVENC.value in available:
                return EncoderType.H264_NVENC.value
            if EncoderType.H264_AMF.value in available:
                return EncoderType.H264_AMF.value
        
        else:
            # Linux: Prefer NVENC > QSV > AMF
            if EncoderType.H264_NVENC.value in available:
                return EncoderType.H264_NVENC.value
            if EncoderType.H264_QSV.value in available:
                return EncoderType.H264_QSV.value
            if EncoderType.H264_AMF.value in available:
                return EncoderType.H264_AMF.value
        
        # Universal fallback: software encoder
        return EncoderType.LIBX264.value
    
    def select_best_hevc_encoder(self) -> str:
        """
        Select the best available HEVC/H.265 encoder
        
        Returns:
            Encoder name
        """
        available = self.detect_available_encoders()
        
        if sys.platform == 'darwin':
            if EncoderType.HEVC_VIDEOTOOLBOX.value in available:
                return EncoderType.HEVC_VIDEOTOOLBOX.value
        
        if EncoderType.HEVC_NVENC.value in available:
            return EncoderType.HEVC_NVENC.value
        
        # Fallback to H.264 if no HEVC support
        return self.select_best_h264_encoder()
    
    def get_encoder_capabilities(self, encoder_name: str) -> Dict[str, Any]:
        """
        Get capabilities and recommended settings for an encoder
        
        Args:
            encoder_name: Name of the encoder
            
        Returns:
            Dictionary with encoder capabilities
        """
        if encoder_name in self._encoder_cache:
            return self._encoder_cache[encoder_name]
        
        capabilities = {
            'name': encoder_name,
            'hardware': encoder_name != EncoderType.LIBX264.value,
            'supports_cbr': True,
            'supports_vbr': True,
            'supports_crf': encoder_name == EncoderType.LIBX264.value,
            'max_resolution': (3840, 2160),  # 4K
            'recommended_preset': self._get_recommended_preset(encoder_name),
            'recommended_bitrate_multiplier': self._get_bitrate_multiplier(encoder_name)
        }
        
        self._encoder_cache[encoder_name] = capabilities
        return capabilities
    
    def _get_recommended_preset(self, encoder_name: str) -> str:
        """Get recommended preset for encoder"""
        if encoder_name == EncoderType.LIBX264.value:
            return 'veryfast'
        elif encoder_name == EncoderType.H264_NVENC.value:
            return 'p4'  # Performance preset 4
        elif encoder_name == EncoderType.H264_VIDEOTOOLBOX.value:
            return 'medium'
        elif encoder_name == EncoderType.H264_QSV.value:
            return 'medium'
        elif encoder_name == EncoderType.H264_AMF.value:
            return 'balanced'
        else:
            return 'medium'
    
    def _get_bitrate_multiplier(self, encoder_name: str) -> float:
        """
        Get bitrate multiplier for encoder quality
        Hardware encoders typically need higher bitrate for same quality
        """
        if encoder_name == EncoderType.LIBX264.value:
            return 1.0  # Reference
        elif encoder_name in [EncoderType.H264_VIDEOTOOLBOX.value]:
            return 1.2  # VideoToolbox needs slightly higher bitrate
        elif encoder_name in [EncoderType.H264_NVENC.value, EncoderType.H264_QSV.value]:
            return 1.3  # Hardware encoders need more bitrate
        else:
            return 1.2
    
    def recommend_bitrate(self, width: int, height: int, fps: int, 
                         encoder_name: Optional[str] = None) -> int:
        """
        Recommend bitrate in kbps for given resolution/fps
        
        Args:
            width: Video width
            height: Video height
            fps: Frame rate
            encoder_name: Specific encoder (uses best if None)
            
        Returns:
            Recommended bitrate in kbps
        """
        if encoder_name is None:
            encoder_name = self.select_best_h264_encoder()
        
        # Base bitrates for common resolutions (30fps reference)
        pixels = width * height
        
        # YouTube recommended bitrates as baseline
        if pixels >= 3840 * 2160:  # 4K
            base_bitrate = 35000 if fps > 30 else 20000
        elif pixels >= 2560 * 1440:  # 1440p
            base_bitrate = 16000 if fps > 30 else 10000
        elif pixels >= 1920 * 1080:  # 1080p
            base_bitrate = 8000 if fps > 30 else 5000
        elif pixels >= 1280 * 720:   # 720p
            base_bitrate = 5000 if fps > 30 else 3000
        else:  # Lower resolutions
            base_bitrate = 2500
        
        # Apply encoder multiplier
        capabilities = self.get_encoder_capabilities(encoder_name)
        multiplier = capabilities.get('recommended_bitrate_multiplier', 1.0)
        
        return int(base_bitrate * multiplier)
    
    def is_encoder_available(self, encoder_name: str) -> bool:
        """
        Check if a specific encoder is available
        
        Args:
            encoder_name: Encoder to check
            
        Returns:
            True if available
        """
        available = self.detect_available_encoders()
        return encoder_name in available
    
    def get_encoder_info(self) -> Dict[str, Any]:
        """
        Get comprehensive encoder information for debugging
        
        Returns:
            Dictionary with encoder info
        """
        return {
            'platform': sys.platform,
            'ffmpeg_path': self.ffmpeg_path,
            'available_encoders': list(self.detect_available_encoders()),
            'recommended_h264': self.select_best_h264_encoder(),
            'recommended_hevc': self.select_best_hevc_encoder()
        }


# Global encoder selector instance
_encoder_selector: Optional[EncoderSelector] = None


def get_encoder_selector(ffmpeg_path: str = 'ffmpeg') -> EncoderSelector:
    """Get or create global encoder selector"""
    global _encoder_selector
    if _encoder_selector is None:
        _encoder_selector = EncoderSelector(ffmpeg_path)
    return _encoder_selector
