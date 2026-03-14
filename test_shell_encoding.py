#!/usr/bin/env python3
"""
Final working test - build FFmpeg command as shell command string to preserve encoding
"""

import subprocess

ffmpeg_path = r"C:\ffmpeg\bin\ffmpeg.exe"

# Get raw output including bytes
result = subprocess.run(
    [ffmpeg_path, '-f', 'dshow', '-list_devices', 'true', '-i', 'dummy'],
    capture_output=True,
    text=False,  # Get bytes, not text
    timeout=5,
)

# Decode with error handling
output = result.stdout.decode('utf-8', errors='replace') + '\n' + result.stderr.decode('utf-8', errors='replace')

for line in output.split('\n'):
    if 'Microphone' in line and '(audio)' in line:
        print(f"Raw line bytes: {repr(line)}")
        
        # Extract using bytes handling
        parts = line.split('"')
        if len(parts) >= 2:
            device_name = parts[1]
            print(f"Device name: {repr(device_name)}")
            print(f"Display: {device_name.replace('Â®', '®').replace('Â', '')}")
            
            # Build command with shell escaping
            cmd_str = f'{ffmpeg_path} -f dshow -i "audio={device_name}" -t 0.001 -f null NUL'
            print(f"\nTesting via shell command string...")
            print(f"Command: {cmd_str[:100]}...")
            
            # Use shell=True to preserve the encoding when interpreting the command
            result = subprocess.run(
                cmd_str,
                shell=True,
                capture_output=True,
                text=True,
                timeout=5,
            )
            
            if 'Could not find' in result.stderr or 'Error opening' in result.stderr:
                print("❌ Still failed with shell=True")
            elif result.returncode == 0 or 'frame=' in result.stderr:
                print("✅ SUCCESS with shell=True!")
            else:
                print(f"Status: {result.returncode}")
            
            for line in result.stderr.split('\n'):
                if 'Could not find' in line:
                    print(f"  FFmpeg error: {line.strip()[:80]}")
            break
