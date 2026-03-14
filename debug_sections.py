#!/usr/bin/env python3
"""
Debug: Find where the audio section markers are
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

print("=" * 80)
print("LOOKING FOR SECTION MARKERS")
print("=" * 80)

# Look for any lines with "devices" in them
for i, line in enumerate(output.split('\n')):
    if 'device' in line.lower():
        print(f"Line {i}: {repr(line[:100])}")

print("\n" + "=" * 80)
print("LOOKING FOR AUDIO-RELATED LINES")
print("=" * 80)

for i, line in enumerate(output.split('\n')):
    if 'audio' in line.lower() or '(audio)' in line.lower():
        print(f"Line {i}: {repr(line[:100])}")
