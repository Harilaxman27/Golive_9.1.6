"""
macOS Native Integration Wrapper
Simple wrapper to integrate AVFoundation camera and VideoToolbox encoder into main.py
"""

import platform
from typing import Optional, Dict, Any

# Import native modules (will gracefully fail if not on macOS or PyObjC not installed)
from macos_camera_capture import (
    MacOSCameraCapture, create_macos_camera_capture, nv12_to_rgb,
    AVFOUNDATION_AVAILABLE
)
from macos_videotoolbox import (
    VideoToolboxEncoder, FFmpegVideoToolboxStreamer,
    create_hardware_streamer, check_videotoolbox_support,
    VIDEOTOOLBOX_AVAILABLE
)

class MacOSNativeHelper:
    """
    Helper class to integrate macOS native features into GoLive Studio.
    
    This provides a simple interface to:
    1. Use AVFoundation native camera capture (hardware NV12)
    2. Use VideoToolbox hardware encoding for streaming
    """
    
    def __init__(self, parent=None):
        self.parent = parent
        self._native_camera: Optional[MacOSCameraCapture] = None
        self._hardware_streamer: Optional[FFmpegVideoToolboxStreamer] = None
        self._is_macos = platform.system() == "Darwin"
        
        # Cache for camera devices
        self._cached_cameras = []
        
    @property
    def avfoundation_available(self) -> bool:
        """Check if AVFoundation camera is available."""
        return self._is_macos and AVFOUNDATION_AVAILABLE
        
    @property
    def videotoolbox_available(self) -> bool:
        """Check if VideoToolbox hardware encoding is available."""
        return self._is_macos and VIDEOTOOLBOX_AVAILABLE
        
    def get_native_cameras(self) -> list:
        """
        Get list of native AVFoundation cameras.
        Returns list of dicts with camera info.
        """
        if not self.avfoundation_available:
            return []
            
        if not self._native_camera:
            self._native_camera = create_macos_camera_capture()
            
        if self._native_camera:
            try:
                devices = self._native_camera.enumerate_devices()
                self._cached_cameras = [
                    {
                        'index': d['index'],
                        'name': d['name'],
                        'id': d['id'],
                        'is_builtin': d.get('is_builtin', False),
                        'backend': 'avfoundation_native'
                    }
                    for d in devices
                ]
                return self._cached_cameras
            except Exception as e:
                print(f"[MacOSNativeHelper] Camera enumeration error: {e}")
                
        return []
        
    def start_native_camera_capture(
        self,
        device_index: int = 0,
        width: int = 1920,
        height: int = 1080,
        fps: int = 30,
        frame_callback = None
    ) -> bool:
        """
        Start native AVFoundation camera capture.
        
        Args:
            device_index: Index of camera device to use
            width: Target capture width
            height: Target capture height
            fps: Target FPS
            frame_callback: Callback function(frame_rgb, timestamp)
            
        Returns:
            True if capture started successfully
        """
        if not self.avfoundation_available:
            print("[MacOSNativeHelper] AVFoundation not available")
            return False
            
        if not self._native_camera:
            self._native_camera = create_macos_camera_capture()
            
        if not self._native_camera:
            return False
            
        def _native_callback(nv12_data, timestamp):
            """Convert NV12 to RGB and call user's callback."""
            try:
                rgb_frame = nv12_to_rgb(nv12_data)
                if rgb_frame is not None and frame_callback:
                    frame_callback(rgb_frame, timestamp)
            except Exception as e:
                print(f"[MacOSNativeHelper] Frame conversion error: {e}")
                
        try:
            return self._native_camera.start_capture(
                device_index=device_index,
                width=width,
                height=height,
                fps=fps,
                frame_callback=_native_callback
            )
        except Exception as e:
            print(f"[MacOSNativeHelper] Start capture error: {e}")
            return False
            
    def stop_native_camera_capture(self):
        """Stop native camera capture."""
        if self._native_camera:
            self._native_camera.stop_capture()
            
    def get_recommended_stream_settings(
        self,
        resolution: str = '1080p',
        fps: int = 30
    ) -> Dict[str, Any]:
        """
        Get recommended streaming settings for this Mac.
        
        Returns settings optimized for hardware encoding if available,
        otherwise returns software encoding settings.
        """
        settings = {
            'width': 1920,
            'height': 1080,
            'fps': fps,
            'bitrate_kbps': 6000,
            'codec': 'h264',
            'pix_fmt': 'yuv420p',
            'hardware': False,
            'encoder_name': 'libx264'
        }
        
        if not self.videotoolbox_available:
            return settings
            
        # Get hardware support info
        support = check_videotoolbox_support()
        
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
            # Use HEVC for 4K on Apple Silicon
            if support.get('hevc_hardware', False):
                settings['codec'] = 'hevc'
                settings['encoder_name'] = 'hevc_videotoolbox'
            else:
                settings['encoder_name'] = 'h264_videotoolbox'
        else:
            settings['bitrate_kbps'] = 3000
            
        # Use hardware encoding
        settings['hardware'] = True
        settings['pix_fmt'] = 'nv12'
        settings['encoder_name'] = 'h264_videotoolbox'
        
        return settings
        
    def get_ffmpeg_encoder_args(
        self,
        width: int = 1920,
        height: int = 1080,
        fps: int = 30,
        bitrate_kbps: int = 6000,
        use_hardware: bool = True
    ) -> list:
        """
        Get FFmpeg encoder arguments optimized for this Mac.
        
        Returns hardware encoder args if available and requested,
        otherwise returns software encoder args.
        """
        if not use_hardware or not self.videotoolbox_available:
            # Software encoding fallback
            return [
                '-c:v', 'libx264',
                '-preset', 'veryfast',
                '-tune', 'zerolatency',
                '-profile:v', 'high',
                '-b:v', f'{bitrate_kbps}k',
                '-maxrate:v', f'{bitrate_kbps}k',
                '-bufsize:v', f'{bitrate_kbps * 2}k',
                '-pix_fmt', 'yuv420p',
                '-g', str(fps * 2),
                '-keyint_min', str(fps),
                '-sc_threshold', '0',
            ]
            
        # Hardware encoding with VideoToolbox
        encoder = VideoToolboxEncoder()
        encoder.initialize(
            width=width,
            height=height,
            fps=fps,
            bitrate_kbps=bitrate_kbps,
            codec='h264',
            profile='high'
        )
        
        return encoder.get_ffmpeg_encoder_args()
        
    def print_status(self):
        """Print status of macOS native features."""
        print("\n" + "="*60)
        print("macOS NATIVE FEATURES STATUS")
        print("="*60)
        
        if not self._is_macos:
            print("Not running on macOS - native features disabled")
            print("="*60)
            return
            
        # Camera status
        if self.avfoundation_available:
            cameras = self.get_native_cameras()
            print(f"✅ AVFoundation Camera: {len(cameras)} device(s) available")
            for cam in cameras:
                builtin = "(Built-in)" if cam['is_builtin'] else "(External)"
                print(f"   - {cam['name']} {builtin}")
        else:
            print("❌ AVFoundation Camera: Not available")
            
        # Encoder status
        if self.videotoolbox_available:
            support = check_videotoolbox_support()
            h264 = support.get('h264_hardware', False)
            hevc = support.get('hevc_hardware', False)
            print(f"✅ VideoToolbox Hardware Encoding:")
            print(f"   - H264: {'✅' if h264 else '❌'}")
            print(f"   - HEVC: {'✅' if hevc else '❌'}")
            print(f"   - Apple Silicon: {'✅' if support.get('apple_silicon') else '❌'}")
        else:
            print("❌ VideoToolbox Hardware Encoding: Not available")
            
        print("="*60 + "\n")


# Global helper instance (lazy initialization)
_macos_helper: Optional[MacOSNativeHelper] = None

def get_macos_helper(parent=None) -> Optional[MacOSNativeHelper]:
    """Get or create the macOS native helper instance."""
    global _macos_helper
    if _macos_helper is None:
        _macos_helper = MacOSNativeHelper(parent)
    return _macos_helper
