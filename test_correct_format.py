#!/usr/bin/env python3
"""
Test FFmpeg DirectShow with the correct syntax (no extra quotes)
"""

import subprocess

ffmpeg_path = r"C:\ffmpeg\bin\ffmpeg.exe"

result = subprocess.run(
    [ffmpeg_path, '-f', 'dshow', '-list_devices', 'true', '-i', 'dummy'],
    capture_output=True,
    text=True,
    timeout=5,
)
output = result.stdout + '\n' + result.stderr

# Extract device name
for line in output.split('\n'):
    if 'Microphone' in line and '(audio)' in line:
        parts = line.split('"')
        if len(parts) >= 2:
            device_name = parts[1]
            device_name = ' '.join(device_name.split())  # Clean whitespace
            
            print(f"Device: {repr(device_name)}")
            print(f"Display: {device_name.replace('Â®', '®').replace('Â', '')}")
            
            # Test WITHOUT extra quotes
            test_input = f'audio={device_name}'
            print(f"\nTesting: ffmpeg -f dshow -i '{test_input}'...")
            
            result = subprocess.run(
                [ffmpeg_path, '-f', 'dshow', '-i', test_input, '-t', '0.001', '-f', 'null', 'NUL'],
                capture_output=True,
                text=True,
                timeout=5,
            )
            
            if result.returncode == 0 or 'Past duration'  in result.stderr or 'frame=' in result.stderr:
                print("✅ SUCCESS - Device works with FFmpeg!")
            else:
                print("❌ Failed")
                for line in result.stderr.split('\n')[-10:]:
                    if line.strip():
                        print(f"  {line.strip()}")
            break
