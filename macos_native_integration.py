"""
macOS Native Integration for GoLive Studio
Integrates AVFoundation camera, VideoToolbox encoder, and CoreAudio
into the existing application.

Usage:
    from macos_native_integration import MacOSNativeIntegration
    
    # Initialize
    native = MacOSNativeIntegration(main_window)
    native.initialize()
    
    # Use native camera
    native.start_camera_capture(device_index=0, width=1920, height=1080, fps=30)
    
    # Use hardware streaming
    native.start_stream(url, key, width=1920, height=1080, fps=30)
"""

import platform
import time
from typing import Optional, Callable, Dict, Any
import numpy as np

# Import native modules
from macos_camera_capture import (
    MacOSCameraCapture, create_macos_camera_capture, nv12_to_rgb,
    AVFOUNDATION_AVAILABLE
)
from macos_videotoolbox import (
    VideoToolboxEncoder, FFmpegVideoToolboxStreamer,
    create_hardware_streamer, check_videotoolbox_support
)
from macos_coreaudio import (
    CoreAudioCapture, CoreAudioEncoder,
    create_coreaudio_capture, check_coreaudio_support,
    get_audio_devices
)


class MacOSNativeIntegration:
    """
    Integration layer for macOS native features.
    Provides a unified interface for camera, encoding, and audio.
    """
    
    def __init__(self, parent=None):
        self.parent = parent
        self._camera: Optional[MacOSCameraCapture] = None
        self._streamer: Optional[FFmpegVideoToolboxStreamer] = None
        self._audio_capture: Optional[CoreAudioCapture] = None
        
        self._is_macos = platform.system() == "Darwin"
        self._support_status: Dict[str, Any] = {}
        
        # Frame callback from camera
        self._camera_frame_callback: Optional[Callable] = None
        self._last_camera_frame: Optional[np.ndarray] = None
        
    def initialize(self) -> bool:
        """
        Initialize macOS native integration.
        Check all available features and print status.
        """
        if not self._is_macos:
            print("[macOS Native] Not macOS - native features disabled")
            return False
            
        print("\n" + "="*60)
        print("macOS NATIVE FEATURES INITIALIZATION")
        print("="*60)
        
        # Check AVFoundation camera
        if AVFOUNDATION_AVAILABLE:
            print("✅ AVFoundation Camera: Available")
            self._camera = create_macos_camera_capture()
        else:
            print("❌ AVFoundation Camera: Not available (PyObjC missing)")
            
        # Check VideoToolbox
        self._support_status['videotoolbox'] = check_videotoolbox_support()
        vt_status = self._support_status['videotoolbox']
        
        if vt_status.get('available', False):
            h264 = vt_status.get('h264_hardware', False)
            hevc = vt_status.get('hevc_hardware', False)
            apple_silicon = vt_status.get('apple_silicon', False)
            
            print(f"✅ VideoToolbox: Available")
            print(f"   - H264 Hardware: {'✅' if h264 else '❌'}")
            print(f"   - HEVC Hardware: {'✅' if hevc else '❌'}")
            print(f"   - Apple Silicon: {'✅' if apple_silicon else '❌ (Intel)'}")
        else:
            print(f"❌ VideoToolbox: {vt_status.get('reason', 'Not available')}")
            
        # Check CoreAudio
        self._support_status['coreaudio'] = check_coreaudio_support()
        ca_status = self._support_status['coreaudio']
        
        if ca_status.get('available', False):
            print(f"✅ CoreAudio: Available ({ca_status.get('device_count', 0)} devices)")
        else:
            print(f"❌ CoreAudio: {ca_status.get('reason', 'Not available')}")
            
        print("="*60 + "\n")
        
        return True
        
    def start_camera_capture(
        self,
        device_index: int = 0,
        width: int = 1920,
        height: int = 1080,
        fps: int = 30,
        frame_callback: Optional[Callable[[np.ndarray], None]] = None
    ) -> bool:
        """
        Start native macOS camera capture.
        Falls back to Qt/OpenCV if native capture is not available.
        """
        if not self._camera:
            print("[macOS Native] Camera not available, using fallback")
            return False
            
        # Wrap callback to convert NV12 to RGB
        def native_callback(nv12_data, timestamp):
            try:
                # Convert NV12 to RGB
                rgb_frame = nv12_to_rgb(nv12_data)
                if rgb_frame is not None and frame_callback:
                    frame_callback(rgb_frame)
            except Exception as e:
                print(f"[macOS Native] Frame conversion error: {e}")
                
        try:
            success = self._camera.start_capture(
                device_index=device_index,
                width=width,
                height=height,
                fps=fps,
                frame_callback=native_callback
            )
            
            if success:
                print(f"[macOS Native] Camera capture started: {width}x{height} @ {fps}fps (NV12)")
                
            return success
            
        except Exception as e:
            print(f"[macOS Native] Camera start error: {e}")
            return False
            
    def stop_camera_capture(self):
        """Stop native camera capture."""
        if self._camera:
            self._camera.stop_capture()
            
    def is_camera_running(self) -> bool:
        """Check if native camera is running."""
        return self._camera.is_running() if self._camera else False
        
    def start_stream(
        self,
        url: str,
        key: str,
        width: int = 1920,
        height: int = 1080,
        fps: int = 30,
        bitrate_kbps: int = 6000
    ) -> bool:
        """
        Start streaming with VideoToolbox hardware encoding.
        Falls back to software encoding if hardware is not available.
        """
        # Check if VideoToolbox is available
        vt_status = self._support_status.get('videotoolbox', {})
        if not vt_status.get('available', False):
            print("[macOS Native] VideoToolbox not available, using software encoding")
            return False
            
        # Create hardware streamer
        self._streamer = create_hardware_streamer()
        if not self._streamer:
            print("[macOS Native] Failed to create hardware streamer")
            return False
            
        try:
            success = self._streamer.start_stream(
                url=url,
                key=key,
                width=width,
                height=height,
                fps=fps,
                bitrate_kbps=bitrate_kbps
            )
            
            if success:
                print(f"[macOS Native] Hardware streaming started: {width}x{height} @ {fps}fps")
                print(f"[macOS Native] Using VideoToolbox H264 hardware encoder")
                
            return success
            
        except Exception as e:
            print(f"[macOS Native] Stream start error: {e}")
            return False
            
    def send_stream_frame(self, frame: np.ndarray) -> bool:
        """Send a frame to the hardware encoder."""
        if self._streamer and self._streamer.is_streaming():
            return self._streamer.send_frame(frame)
        return False
        
    def stop_stream(self):
        """Stop hardware streaming."""
        if self._streamer:
            self._streamer.stop_stream()
            
    def is_streaming(self) -> bool:
        """Check if currently streaming."""
        return self._streamer.is_streaming() if self._streamer else False
        
    def get_recommended_stream_settings(
        self,
        resolution: str = '1080p',
        fps: int = 30
    ) -> Dict[str, Any]:
        """
        Get recommended streaming settings for this Mac.
        Based on hardware capabilities.
        """
        settings = {
            'width': 1920,
            'height': 1080,
            'fps': fps,
            'bitrate_kbps': 6000,
            'codec': 'h264',
            'pix_fmt': 'yuv420p',  # Default software
            'hardware': False
        }
        
        vt_status = self._support_status.get('videotoolbox', {})
        
        if vt_status.get('available', False):
            settings['hardware'] = True
            
            if resolution == '1080p':
                settings['width'] = 1920
                settings['height'] = 1080
                if fps >= 60:
                    settings['bitrate_kbps'] = 9000
                else:
                    settings['bitrate_kbps'] = 6000
                    
            elif resolution == '720p':
                settings['width'] = 1280
                settings['height'] = 720
                if fps >= 60:
                    settings['bitrate_kbps'] = 6000
                else:
                    settings['bitrate_kbps'] = 4500
                    
            elif resolution in ('4k', '2160p'):
                settings['width'] = 3840
                settings['height'] = 2160
                settings['bitrate_kbps'] = 45000
                
                # Use HEVC for 4K if available (Apple Silicon)
                if vt_status.get('hevc_hardware', False):
                    settings['codec'] = 'hevc'
                    
            # Use NV12 pixel format for hardware encoding
            settings['pix_fmt'] = 'nv12'
            
        return settings
        
    def get_audio_devices(self) -> list:
        """Get list of available audio devices."""
        return get_audio_devices()
        
    def start_audio_capture(self, device_id: Optional[int] = None) -> bool:
        """Start CoreAudio capture."""
        if not self._audio_capture:
            self._audio_capture = create_coreaudio_capture()
            
        if self._audio_capture:
            return self._audio_capture.start_capture(device_id=device_id)
        return False
        
    def stop_audio_capture(self):
        """Stop CoreAudio capture."""
        if self._audio_capture:
            self._audio_capture.stop_capture()
            
    def shutdown(self):
        """Clean up all native resources."""
        print("[macOS Native] Shutting down...")
        self.stop_camera_capture()
        self.stop_stream()
        self.stop_audio_capture()
        print("[macOS Native] Shutdown complete")

# Convenience function for quick initialization
def setup_macos_native(parent=None) -> Optional[MacOSNativeIntegration]:
    """
    Quick setup function for macOS native features.
    Returns initialized MacOSNativeIntegration or None if not on macOS.
    """
    if platform.system() != "Darwin":
        return None
        
    native = MacOSNativeIntegration(parent)
    native.initialize()
    return native
