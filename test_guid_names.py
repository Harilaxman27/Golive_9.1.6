#!/usr/bin/env python3
"""Test using @device_cm_{GUID} format with FFmpeg"""

import subprocess
import sys
import re

# Get FFmpeg
ffmpeg_path = None
for attempt in ["ffmpeg", "C:\\ffmpeg\\bin\\ffmpeg.exe"]:
    try:
        result = subprocess.run([attempt, "-version"], capture_output=True, timeout=5)
        if result.returncode == 0:
            ffmpeg_path = attempt
            break
    except:
        pass

if not ffmpeg_path:
    print("❌ FFmpeg not found")
    sys.exit(1)

print(f"Using FFmpeg: {ffmpeg_path}\n")

# Get device list and extract GUIDs
print("[Step 1] Listing devices and extracting GUIDs...")
result = subprocess.run(
    [ffmpeg_path, "-f", "dshow", "-list_devices", "true", "-i", "dummy"],
    capture_output=True,
    text=True,
    errors="replace"
)

output = result.stdout + result.stderr
lines = output.split('\n')

devices = {}  # Friendly name -> GUID
guids = []

# Find devices
device_pattern = r'\[in#\d+[^\]]*\]\s+"([^"]+)"\s*\(audio\)'
for match in re.finditer(device_pattern, output, re.DOTALL):
    friendly = ' '.join(match.group(1).split())
    devices[friendly] = ''
    guids.append(friendly)

print(f"Found {len(devices)} device(s):\n")

# Find corresponding GUIDs
for i, line in enumerate(lines):
    if '(audio)' in line:
        if i + 1 < len(lines):
            next_line = lines[i + 1]
            guid_match = re.search(r'@device_cm_\{([^}]+)\}', next_line)
            if guid_match:
                guid = guid_match.group(1)
                # Find which device this is
                name_match = re.search(r'"([^"]+)"\s*\(audio\)', line)
                if name_match:
                    friendly = ' '.join(name_match.group(1).split())
                    if friendly in devices:
                        devices[friendly] = guid
                        print(f"✓ {friendly[:50]}")
                        print(f"  → GUID: {guid}")
                        print(f"  → Alt name: @device_cm_{{{guid}}}\n")

# Test each device with FFmpeg
print("[Step 2] Testing device access with FFmpeg...\n")
for friendly, guid in devices.items():
    if guid:
        alt_name = f"@device_cm_{{{guid}}}"
        print(f"Testing: {friendly[:50]}")
        print(f"  GUID {alt_name}...")
        
        try:
            # Test with alt name (GUID-based)
            cmd = [
                ffmpeg_path,
                "-f", "dshow",
                "-i", f"audio={alt_name}",
                "-f", "null",
                "-t", "0.1",
                "NUL"
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, errors="replace", timeout=5)
            
            if "Could not find" in result.stderr:
                print(f"  ❌ GUID-based access failed")
                # Show error
                error_lines = [l for l in result.stderr.split('\n') if 'Could not find' in l]
                if error_lines:
                    print(f"     {error_lines[0][:70]}")
            elif result.returncode == 0 or "frame=" in result.stderr:
                print(f"  ✅ GUID-based access WORKS!")
            else:
                print(f"  ⚠️  Unclear result (returncode {result.returncode})")
                # Check for actual FFmpeg errors
                error_lines = [l for l in result.stderr.split('\n') if 'error' in l.lower() and 'audio' in l.lower()]
                if error_lines:
                    print(f"     {error_lines[0][:70]}")
        except Exception as e:
            print(f"  ❌ Exception: {str(e)[:60]}")

print("\n[Done]")
