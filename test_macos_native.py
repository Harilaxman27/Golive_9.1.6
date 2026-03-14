#!/usr/bin/env python3
"""
Test script for macOS native features
Verifies AVFoundation camera, VideoToolbox encoder, and CoreAudio are working.
"""

import sys
import platform

def test_macos_native():
    """Test all macOS native modules."""
    print("="*60)
    print("macOS NATIVE FEATURES TEST")
    print("="*60)
    print(f"Platform: {platform.system()}")
    print(f"Machine: {platform.machine()}")
    print(f"Python: {sys.version}")
    print()
    
    if platform.system() != "Darwin":
        print("❌ Not macOS - native features not available")
        return False
        
    success = True
    
    # Test 1: macOS Camera Capture
    print("[TEST 1] AVFoundation Camera Capture")
    print("-" * 40)
    try:
        from macos_camera_capture import (
            create_macos_camera_capture, 
            AVFOUNDATION_AVAILABLE
        )
        
        if AVFOUNDATION_AVAILABLE:
            camera = create_macos_camera_capture()
            if camera:
                devices = camera.enumerate_devices()
                print(f"✅ AVFoundation available")
                print(f"   Found {len(devices)} camera(s)")
                for d in devices:
                    print(f"   - {d['name']}")
            else:
                print("⚠️ AVFoundation available but camera creation failed")
        else:
            print("❌ AVFoundation not available (PyObjC not installed)")
            success = False
            
    except Exception as e:
        print(f"❌ Camera test failed: {e}")
        success = False
        
    print()
    
    # Test 2: VideoToolbox Encoder
    print("[TEST 2] VideoToolbox Hardware Encoder")
    print("-" * 40)
    try:
        from macos_videotoolbox import (
            check_videotoolbox_support,
            create_hardware_streamer
        )
        
        support = check_videotoolbox_support()
        if support.get('available', False):
            print(f"✅ VideoToolbox available")
            print(f"   H264 Hardware: {'Yes' if support.get('h264_hardware') else 'No'}")
            print(f"   HEVC Hardware: {'Yes' if support.get('hevc_hardware') else 'No'}")
            print(f"   Apple Silicon: {'Yes' if support.get('apple_silicon') else 'No'}")
            
            # Try creating streamer
            streamer = create_hardware_streamer()
            if streamer:
                print("✅ Hardware streamer created successfully")
            else:
                print("⚠️ Hardware streamer not available (may need hardware support)")
        else:
            print(f"❌ VideoToolbox not available: {support.get('reason', 'Unknown')}")
            success = False
            
    except Exception as e:
        print(f"❌ VideoToolbox test failed: {e}")
        import traceback
        traceback.print_exc()
        success = False
        
    print()
    
    # Test 3: CoreAudio
    print("[TEST 3] CoreAudio Audio Capture")
    print("-" * 40)
    try:
        from macos_coreaudio import (
            check_coreaudio_support,
            get_audio_devices
        )
        
        support = check_coreaudio_support()
        if support.get('available', False):
            print(f"✅ CoreAudio available")
            print(f"   Devices: {support.get('device_count', 0)} total")
            print(f"   Input: {support.get('input_devices', 0)}")
            print(f"   Output: {support.get('output_devices', 0)}")
            
            devices = get_audio_devices()
            for d in devices[:3]:  # Show first 3
                io_type = "Input" if d['is_input'] else ""
                io_type += "/Output" if d['is_output'] else ""
                print(f"   - {d['name']} ({io_type})")
        else:
            print(f"❌ CoreAudio not available: {support.get('reason', 'Unknown')}")
            success = False
            
    except Exception as e:
        print(f"❌ CoreAudio test failed: {e}")
        import traceback
        traceback.print_exc()
        success = False
        
    print()
    
    # Test 4: Integration Module
    print("[TEST 4] Integration Module")
    print("-" * 40)
    try:
        from macos_native_integration import setup_macos_native
        
        native = setup_macos_native()
        if native:
            print("✅ Integration module initialized")
            
            # Get recommended settings
            settings = native.get_recommended_stream_settings('1080p', 30)
            print(f"   Recommended: {settings['width']}x{settings['height']} @ {settings['fps']}fps")
            print(f"   Codec: {settings['codec']} ({'Hardware' if settings['hardware'] else 'Software'})")
            print(f"   Bitrate: {settings['bitrate_kbps']} kbps")
        else:
            print("⚠️ Integration module not available (may not be macOS)")
            
    except Exception as e:
        print(f"❌ Integration test failed: {e}")
        import traceback
        traceback.print_exc()
        success = False
        
    print()
    print("="*60)
    if success:
        print("✅ ALL TESTS PASSED - macOS native features ready")
    else:
        print("⚠️ SOME TESTS FAILED - Check output above")
    print("="*60)
    
    return success


if __name__ == "__main__":
    test_macos_native()
