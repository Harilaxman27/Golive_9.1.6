#!/usr/bin/env python3
"""
Debug: Show full AUDIO lines
"""

import subprocess

ffmpeg_path = r"C:\ffmpeg\bin\ffmpeg.exe"

result = subprocess.run(
    [ffmpeg_path, '-hide_banner', '-f', 'dshow', '-list_devices', 'true', '-i', 'dummy'],
    capture_output=True,
    text=True,
    timeout=5,
    encoding='utf-8',
    errors='replace',
)

output = (result.stdout or '') + '\n' + (result.stderr or '')

print("="*80)
print("FULL AUDIO DEVICE LINES")
print("="*80)
for i, line in enumerate(output.split('\n')):
    if 'Microphone' in line or '(audio)' in line:
        print(f"Line {i}: {repr(line)}")

print("\n" + "="*80)
print("CHECKING FOR (audio) TAG")
print("="*80)
if '(audio)' in output:
    print("✓ Found '(audio)' in output")
else:
    print("✗ NOT FOUND '(audio)' in output")

print("\n" + "="*80)
print("ALL LINES WITH [...devices]")
print("="*80)
for i, line in enumerate(output.split('\n')):
    if 'in#' in line and 'devices' not in line:
        print(f"Line {i}: {repr(line)}")
