#!/usr/bin/env python3
"""Test if alternate device names work with FFmpeg"""

import subprocess
import sys
import os

# Try to get FFmpeg from path or hardcoded locations
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

print(f"Using FFmpeg: {ffmpeg_path}")

# First, get the list of devices and parse out alternative names
print("\n[Step 1] Listing audio devices...")
result = subprocess.run(
    [ffmpeg_path, "-f", "dshow", "-list_devices", "true", "-i", "dummy"],
    capture_output=True,
    text=True,
    errors="replace"
)

output = result.stdout + result.stderr
import re
devices = re.findall(r'\[in#\d+[^\]]*\]\s+"([^"]+)"\s*\(audio\)', output, re.DOTALL)

if not devices:
    print("No audio devices found")
    sys.exit(1)

print(f"Found {len(devices)} device(s):")
for i, dev in enumerate(devices):
    print(f"  {i+1}. {dev}")

if not devices:
    sys.exit(1)

# Now try to list devices with alternative names (the DirectShow device identifier)
print("\n[Step 2] Extracting alternative device names...")
alt_names = {}
lines = output.split('\n')
for i, line in enumerate(lines):
    if '(audio)' in line:
        # Try to find the friendly name in quotes
        m = re.search(r'"([^"]+)"\s*\(audio\)', line)
        if m:
            friendly = m.group(1)
            # Look for alternative name on next line
            if i + 1 < len(lines):
                alt_match = re.search(r'\{\s*([^}]+)\s*\}', lines[i+1])
                if alt_match:
                    alt = alt_match.group(1)
                    alt_names[friendly] = alt
                    print(f"  {friendly} -> {alt}")

if not alt_names:
    print("No alternative names found in output")
    print("Raw output around (audio) markers:")
    for i, line in enumerate(lines):
        if '(audio)' in line:
            print(f"  Line {i}: {line}")
            if i+1 < len(lines):
                print(f"  Line {i+1}: {lines[i+1]}")
    sys.exit(1)

# Try using each device with FFmpeg
print("\n[Step 3] Testing each device with FFmpeg...")
for device in devices:
    alt = alt_names.get(device, "")
    
    # Test 1: Try friendly name without shell
    print(f"\n  Testing friendly name (no shell): '{device[:40]}...'")
    try:
        cmd = [
            ffmpeg_path,
            "-f", "dshow",
            "-i", f"audio={device}",
            "-f", "null",
            "-t", "0.1",
            "NUL"
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, errors="replace", timeout=5)
        if "Could not find" not in result.stderr and result.returncode != 1:
            print(f"    ✅ Friendly name works!")
        else:
            print(f"    ❌ Friendly name failed")
            error_line = [l for l in result.stderr.split('\n') if 'Could not find' in l or 'error' in l.lower()]
            if error_line:
                print(f"       Error: {error_line[0][:80]}")
    except Exception as e:
        print(f"    ❌ Exception: {str(e)[:60]}")
    
    # Test 2: Try alternative name without shell
    if alt:
        print(f"  Testing alternative name (no shell): '{alt[:40]}...'")
        try:
            cmd = [
                ffmpeg_path,
                "-f", "dshow",
                "-i", f"audio={alt}",
                "-f", "null",
                "-t", "0.1",
                "NUL"
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, errors="replace", timeout=5)
            if "Could not find" not in result.stderr and result.returncode != 1:
                print(f"    ✅ Alternative name works!")
            else:
                print(f"    ❌ Alternative name failed")
                error_line = [l for l in result.stderr.split('\n') if 'Could not find' in l or 'error' in l.lower()]
                if error_line:
                    print(f"       Error: {error_line[0][:80]}")
        except Exception as e:
            print(f"    ❌ Exception: {str(e)[:60]}")
    
    # Test 3: Try friendly name WITH shell=True
    print(f"  Testing friendly name (with shell=True): '{device[:40]}...'")
    try:
        cmd_str = f'{ffmpeg_path} -f dshow -i "audio={device}" -f null -t 0.1 NUL'
        result = subprocess.run(cmd_str, shell=True, capture_output=True, text=True, errors="replace", timeout=5)
        if "Could not find" not in result.stderr and result.returncode != 1:
            print(f"    ✅ Friendly name (shell) works!")
        else:
            print(f"    ❌ Friendly name (shell) failed")
            error_line = [l for l in result.stderr.split('\n') if 'Could not find' in l or 'error' in l.lower()]
            if error_line:
                print(f"       Error: {error_line[0][:80]}")
    except Exception as e:
        print(f"    ❌ Exception: {str(e)[:60]}")

print("\n[Done]")
