#!/usr/bin/env python3
"""
Test different FFmpeg DirectShow audio input formats
"""

import subprocess
import sys

ffmpeg_path = r"C:\ffmpeg\bin\ffmpeg.exe"

# Get the device list first
print("=" * 80)
print("GETTING DEVICE LIST FROM FFmpeg")
print("=" * 80)
result = subprocess.run(
    [ffmpeg_path, '-hide_banner', '-f', 'dshow', '-list_devices', 'true', '-i', 'dummy'],
    capture_output=True,
    text=True,
    timeout=5,
)
output = result.stdout + '\n' + result.stderr

# Find the microphone device name
for line in output.split('\n'):
    if 'Microphone' in line and '(audio)' in line:
        # Extract just the friendly name between quotes
        parts = line.split('"')
        if len(parts) >= 2:
            device_name = parts[1]
            print(f"Found device: {repr(device_name)}")
            
            # Now test different formats with ffmpeg
            formats_to_test = [
                f'audio="{device_name}"',  # With quotes
                f"audio='{device_name}'",  # With single quotes
                f"audio={device_name}",    # Without quotes
            ]
            
            for fmt in formats_to_test:
                print(f"\n{'='*80}")
                print(f"Testing format: {repr(fmt)}")
                print(f"{'='*80}")
                
                # Try a very simple test - just try to get info without recording
                try:
                    result = subprocess.run(
                        [ffmpeg_path, '-f', 'dshow', '-i', fmt, '-t', '0.1', '-f', 'null', 'NUL'],
                        capture_output=True,
                        text=True,
                        timeout=5,
                    )
                    
                    if result.returncode == 0:
                        print(f"✅ SUCCESS with format: {repr(fmt)}")
                    else:
                        stderr_lines = result.stderr.split('\n')
                        for line in stderr_lines[-10:]:
                            if 'error' in line.lower() or 'could not' in line.lower():
                                print(f"❌ ERROR: {line.strip()}")
                except Exception as e:
                    print(f"❌ Exception: {e}")
            
            break
