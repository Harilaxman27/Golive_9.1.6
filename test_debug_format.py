#!/usr/bin/env python3
"""Debug the exact FFmpeg DirectShow device output format"""

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

# Get device list
result = subprocess.run(
    [ffmpeg_path, "-f", "dshow", "-list_devices", "true", "-i", "dummy"],
    capture_output=True,
    text=True,
    errors="replace"
)

output = result.stdout + result.stderr
lines = output.split('\n')

print("Raw FFmpeg output around audio devices:")
print("=" * 80)
for i, line in enumerate(lines):
    # Print context around (audio) markers
    if '(audio)' in line or (i > 0 and '(audio)' in lines[i-1]) or (i < len(lines)-1 and '(audio)' in lines[i+1]):
        print(f"[{i:3d}] {repr(line)}")
print("=" * 80)

print("\nSearching for alternative names format...")
in_audio_section = False
for i, line in enumerate(lines):
    if '(audio)' in line:
        print(f"\nFound (audio) at line {i}:")
        print(f"  Current:  {repr(line)}")
        # Print next few lines
        for j in range(1, 4):
            if i+j < len(lines):
                print(f"  Next[+{j}]: {repr(lines[i+j])}")
        
        # Try different extraction patterns
        # Pattern 1: Direct curly braces on same line
        m = re.search(r'"([^"]+)"\s*\(\s*audio\s*\)\s*\{\s*([^}]+)\s*\}', line)
        if m:
            print(f"  ✅ Pattern 1 (same line): friendly='{m.group(1)}' alt='{m.group(2)}'")
        
        # Pattern 2: Curly braces on next line
        if i+1 < len(lines):
            m = re.search(r'\{\s*([^}]+)\s*\}', lines[i+1])
            if m:
                print(f"  Pattern 2 (next line): alt='{m.group(1)}'")
            
            # Also check if next line has different format
            print(f"  Next line content: {repr(lines[i+1])[0:100]}")

print("\n\nDirect device name extraction with DOTALL:")
devices = re.findall(r'\[in#\d+[^\]]*\]\s+"([^"]+)"\s*\(audio\)', output, re.DOTALL)
for dev in devices:
    print(f"  Device: {repr(dev)}")
    print(f"  Bytes:  {dev.encode('utf-8')}")
    print(f"  Repr in terminal: {dev}")
