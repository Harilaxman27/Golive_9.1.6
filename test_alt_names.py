#!/usr/bin/env python3
"""
Test using alternative device names with FFmpeg
"""

import subprocess
import re

ffmpeg_path = r"C:\ffmpeg\bin\ffmpeg.exe"

print("="*80)
print("Testing Alternative Device Names")
print("="*80)

result = subprocess.run(
    [ffmpeg_path, '-hide_banner', '-f', 'dshow', '-list_devices', 'true', '-i', 'dummy'],
    capture_output=True,
    text=True,
    timeout=5,
)
output = result.stdout + '\n' + result.stderr

# Extract both friendly name and alternative name
device_pattern = r'\[in#\d+[^\]]*\]\s+"([^"]+)"\s*\(audio\)'
alt_pattern = r'Alternative name\s+"([^"]+)"'

lines = output.split('\n')
for i, line in enumerate(lines):
    if 'Microphone' in line and '(audio)' in line:
        # This is a device line - extract friendly name
        match = re.search(device_pattern, line, re.DOTALL)
        if match:
            friendly = ' '.join(match.group(1).split())
            print(f"\nFriendly name: {repr(friendly)}")
            print(f"Display: {friendly.replace('Â®', '®').replace('Â', '')}")
            
            # Look for alternative name in next lines
            for j in range(i+1, min(i+3, len(lines))):
                if 'Alternative name' in lines[j]:
                    alt_match = re.search(r'"([^"]+)"', lines[j])
                    if alt_match:
                        alt_name = alt_match.group(1)
                        print(f"Alternative name: {repr(alt_name)}")
                        
                        # Test with alternative name
                        print(f"\nTesting FFmpeg with alternative name...")
                        test_input = f'audio="{alt_name}"'
                        result = subprocess.run(
                            [ffmpeg_path, '-f', 'dshow', '-i', test_input, '-t', '0.1', '-f', 'null', 'NUL'],
                            capture_output=True,
                            text=True,
                            timeout=5,
                        )
                        
                        if result.returncode == 0:
                            print(f"✅ Alternative name works with FFmpeg!")
                        else:
                            print(f"❌ Alternative name also failed")
                            for line in result.stderr.split('\n'):
                                if 'Could not find' in line or 'error' in line.lower():
                                    print(f"   {line.strip()}")
                        break
            break
