#!/usr/bin/env python3
"""
Test different FFmpeg DirectShow input formats
"""

import subprocess

ffmpeg_path = r"C:\ffmpeg\bin\ffmpeg.exe"

# Get device name
result = subprocess.run(
    [ffmpeg_path, '-f', 'dshow', '-list_devices', 'true', '-i', 'dummy'],
    capture_output=True,
    text=True,
    timeout=5,
)
output = result.stdout + '\n' + result.stderr

#Extract the microphone name
for line in output.split('\n'):
    if 'Microphone' in line and '(audio)' in line:
        # Get just the device name between quotes
        parts = line.split('"')
        if len(parts) >= 2:
            device_name = parts[1]
            print(f"Device found: {repr(device_name[:50])}")
            
            # Test multiple formats
            formats = [
               f'audio="{device_name}"',
                f'audio={repr(device_name)}',  # Python repr
                f'"{device_name}"',            # Just device name in quotes
                f'{device_name}',                # No quotes
                f'dshow:audio="{device_name}"', # With dshow: prefix
            ]
            
            for fmt in formats:
                print(f"\n{'='*60}")
                print(f"Format: {fmt[:50]}...")
                try:
                    result = subprocess.run(
                        [ffmpeg_path, '-f', 'dshow', '-i', fmt, '-t', '0.001', '-f', 'null', 'NUL'],
                        capture_output=True,
                        text=True,
                        timeout=3,
                    )
                    if result.returncode == 0 or 'Past duration' in result.stderr:
                        print("✅ WORKED!")
                        break
                    else:
                        for line in result.stderr.split('\n'):
                            if 'error' in line.lower():
                                print(f"❌ {line.strip()[:60]}")
                                break
                except Exception as e:
                    print(f"❌ Exception: {str(e)[:50]}")
            break
