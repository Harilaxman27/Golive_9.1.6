#!/usr/bin/env python3
"""Test script to verify audio device detection and selection."""

import subprocess
import re
import sys

def get_ffmpeg_path():
    """Get FFmpeg path."""
    try:
        from ffmpeg_utils import get_ffmpeg_path
        return get_ffmpeg_path()
    except ImportError:
        return 'ffmpeg'

def list_windows_audio_devices():
    """List available Windows audio input devices using FFmpeg DirectShow.
    
    Returns: [(friendly_name, alternative_name_or_empty), ...]
    """
    try:
        ffmpeg_path = get_ffmpeg_path()
        result = subprocess.run(
            [ffmpeg_path, '-hide_banner', '-f', 'dshow', '-list_devices', 'true', '-i', 'dummy'],
            capture_output=True,
            text=True,
            timeout=5,
            encoding='utf-8',
            errors='replace',
        )
        output = (result.stdout or '') + '\n' + (result.stderr or '')
        
        devices = []
        in_audio_section = False
        last_friendly = None
        
        for line in output.splitlines():
            line = line.strip()
            if 'DirectShow audio devices' in line:
                in_audio_section = True
                continue
            if 'DirectShow video devices' in line:
                in_audio_section = False
                continue
            if not in_audio_section:
                continue
            
            # Match: "device name" (audio)
            match = re.search(r'"([^"]+)"\s*\(audio\)', line)
            if match:
                name = match.group(1).strip()
                if name and not any(d[0] == name for d in devices):
                    devices.append((name, ''))
                    last_friendly = name
                continue
            
            # Match alternative name
            if 'Alternative name' in line and last_friendly:
                match = re.search(r'"([^"]+)"', line)
                if match:
                    alt = match.group(1).strip()
                    for i, (fname, a) in enumerate(devices):
                        if fname == last_friendly:
                            devices[i] = (fname, alt)
                            break
        
        return devices
    except Exception as e:
        print(f"Error listing audio devices: {e}")
        return []

def test_audio_devices():
    """Test audio device detection."""
    print("=" * 70)
    print("Audio Device Detection Test")
    print("=" * 70)
    
    devices = list_windows_audio_devices()
    
    if not devices:
        print("❌ No audio devices found!")
        return False
    
    print(f"\n✅ Found {len(devices)} audio device(s):\n")
    for i, (friendly, alt) in enumerate(devices, 1):
        print(f"  {i}. Friendly Name: {friendly}")
        if alt:
            print(f"     Alternative: {alt}")
    
    # Verify microphone detection
    print("\n" + "-" * 70)
    print("Microphone Detection:")
    for friendly, alt in devices:
        if 'microphone' in friendly.lower() or 'mic' in friendly.lower():
            print(f"  ✅ Found microphone: {friendly}")
            print(f"     Use device ID: {alt or friendly}")
            
            # Test with FFmpeg
            print("\n  Testing with FFmpeg...")
            try:
                ffmpeg_path = get_ffmpeg_path()
                device_id = alt or friendly
                
                # Try to capture 2 seconds of audio
                result = subprocess.run(
                    [ffmpeg_path, '-y', '-f', 'dshow', '-i', f'audio="{device_id}"', 
                     '-t', '2', '-acodec', 'pcm_s16le', 'test_audio.wav'],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                # Check if output file was created
                import os
                if os.path.exists('test_audio.wav'):
                    size_kb = os.path.getsize('test_audio.wav') / 1024
                    print(f"  ✅ Audio capture successful! File size: {size_kb:.1f} KB")
                    os.remove('test_audio.wav')
                else:
                    print(f"  ⚠️ Capture command executed but no file created")
                    if result.stderr:
                        print(f"     FFmpeg output: {result.stderr[:200]}")
            except Exception as e:
                print(f"  ❌ FFmpeg test failed: {e}")
    
    print("\n" + "=" * 70)
    print("Test Complete!")
    print("=" * 70)
    return True

if __name__ == '__main__':
    if 'win' not in sys.platform.lower():
        print("❌ This test is for Windows only")
        sys.exit(1)
    
    success = test_audio_devices()
    sys.exit(0 if success else 1)
