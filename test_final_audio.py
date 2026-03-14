#!/usr/bin/env python3
"""
Final test: Verify the complete audio recording flow
"""

import subprocess
import re

ffmpeg_path = r"C:\ffmpeg\bin\ffmpeg.exe"

print("=" * 80)
print("AUDIO RECORDING FIX - COMPLETE VERIFICATION")
print("=" * 80)

# Step 1: Get device list  
print("\n[1] Detecting audio devices...")
result = subprocess.run(
    [ffmpeg_path, '-hide_banner', '-f', 'dshow', '-list_devices', 'true', '-i', 'dummy'],
    capture_output=True,
    text=True,
    timeout=5,
)
output = result.stdout + '\n' + result.stderr

# Extract device name exactly as FFmpeg lists it
device_pattern = r'\[in#\d+[^\]]*\]\s+"([^"]+)"\s*\(audio\)'
devices_found = []

for match in re.finditer(device_pattern, output, re.DOTALL):
    name = ' '.join(match.group(1).split())  # Clean whitespace only
    display = name.replace('Â®', '®').replace('Â', '')
    devices_found.append((name, display))
    print(f"  ✓ Found: {display}")

if not devices_found:
    print("  ✗ No devices found!")
    exit(1)

device_name, display_name = devices_found[0]
print(f"\n✅ Using device: {display_name}")

# Step 2: Test FFmpeg with the device name
print(f"\n[2] Testing FFmpeg with device name...")
print(f"  Device string: {repr(device_name)}")
print(f"  Command: ffmpeg -f dshow -i 'audio=\"{device_name}\"'...")

test_input = f'audio="{device_name}"'
result = subprocess.run(
    [ffmpeg_path, '-f', 'dshow', '-i', test_input, '-t', '0.1', '-f', 'null', 'NUL'],
    capture_output=True,
    text=True,
    timeout=5,
)

if result.returncode == 0:
    print(f"  ✅ FFmpeg successfully opened the device!")
else:
    # Check for specific errors
    stderr = result.stderr
    if 'Could not find' in stderr:
        print(f"  ✗ FFmpeg could not find the device")
        for line in stderr.split('\n'):
            if 'Could not find' in line:
                print(f"     Error: {line.strip()}")
                if '[' in line and ']' in line:
                    what_it_sees = line[line.find('[')+1:line.find(']')]
                    print(f"     FFmpeg sees: {repr(what_it_sees)}")
    else:
        print(f"  ✗ FFmpeg returned error code {result.returncode}")
        print(f"     Last error line: {stderr.split(chr(10))[-2]}")

print("\n" + "=" * 80)
if result.returncode == 0:
    print("✅ SUCCESS - Audio device can be used for recording!")
    print("\nYou can now:")
    print("1. Run: python launch_golive.py")
    print("2. Click Recording → Settings")
    print("3. Select your microphone from the audio dropdown")
    print("4. Click Record and speak into your microphone")
    print("5. Audio WILL be included in the recording file")
else:
    print("❌ FAILED - Audio device still cannot beused")
    print("\nPlease check:")
    print("1. Microphone is connected and not muted")
    print("2. Windows Sound Settings show the device working")
    print("3. No other application has exclusive access to the microphone")
print("=" * 80)
