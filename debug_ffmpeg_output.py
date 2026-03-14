#!/usr/bin/env python3
"""
Debug script to see exact FFmpeg DirectShow device output
"""

import subprocess
import sys

try:
    # Try to find FFmpeg
    ffmpeg_path = r"C:\ffmpeg\bin\ffmpeg.exe"
    
    print("=" * 80)
    print("DEBUGGING FFmpeg DirectShow Audio Device Detection")
    print("=" * 80)
    print(f"Using FFmpeg: {ffmpeg_path}")
    print()
    
    # Run FFmpeg to list DirectShow devices
    result = subprocess.run(
        [ffmpeg_path, '-list_devices', 'true', '-f', 'dshow', '-i', 'dummy'],
        capture_output=True,
        text=True,
        timeout=10
    )
    
    print("STDOUT:")
    print("-" * 80)
    print(result.stdout)
    print("-" * 80)
    
    print("\nSTDERR:")
    print("-" * 80)
    print(result.stderr)
    print("-" * 80)
    
    # Also try to show character codes
    print("\nDETAILED CHARACTER ANALYSIS OF STDERR:")
    print("-" * 80)
    
    for i, line in enumerate(result.stderr.split('\n')):
        if 'Microphone' in line or 'Audio' in line or 'audio' in line:
            print(f"Line {i}: {repr(line)}")
            print(f"  Bytes: {[f'{ord(c):02x}' for c in line[:100]]}")
    
    print("\n" + "=" * 80)
    print("TOTAL STDERR LENGTH:", len(result.stderr), "characters")
    print("=" * 80)
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
