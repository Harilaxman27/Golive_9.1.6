#!/usr/bin/env python3
"""
Debug the actual bytes in the device name after parsing
"""

import subprocess
import re 

ffmpeg_path = r"C:\ffmpeg\bin\ffmpeg.exe"

result = subprocess.run(
    [ffmpeg_path, '-hide_banner', '-f', 'dshow', '-list_devices', 'true', '-i', 'dummy'],
    capture_output=True,
    text=True,
    timeout=5,
    encoding='utf-8',
    errors='replace',
)
output = result.stdout + '\n' + result.stderr

# Find the microphone device name
device_pattern = r'\[in#\d+[^\]]*\]\s+"([^"]+)"\s*\(audio\)'

for match in re.finditer(device_pattern, output, re.DOTALL):
    name = match.group(1)
    # Clean up whitespace from line wrapping
    name = ' '.join(name.split())
    
    print(f"\n{'='*80}")
    print("RAW EXTRACTED NAME:")
    print(f"  String repr: {repr(name)}")
    print(f"  Length: {len(name)} chars")
    print(f"  Bytes (UTF-8): {name.encode('utf-8').hex()}")
    print(f"  Bytes (Latin-1): {name.encode('latin-1', errors='replace').hex()}")
    
    # Apply our cleanup
    name_cleaned = name.replace('Â®', '®').replace('Â', '')
    print(f"\nAFTER CLEANUP:")
    print(f"  String repr: {repr(name_cleaned)}")
    print(f"  Length: {len(name_cleaned)} chars")
    print(f"  Bytes (UTF-8): {name_cleaned.encode('utf-8').hex()}")
    print(f"  Display: {name_cleaned}")
    
    # Test passing to subprocess
    print(f"\n{'='*80}")
    print("TESTING WITH SUBPROCESS:")
    
    #  Let's see what bytes actually get sent to FFmpeg
    test_arg = f'audio="{name_cleaned}"'
    print(f"  Argument to pass: {repr(test_arg)}")
    print(f"  Arg bytes (UTF-8): {test_arg.encode('utf-8').hex()}")
    
    # Try with explicit UTF-8 encoding
    result2 = subprocess.run(
        [ffmpeg_path, '-f', 'dshow', '-i', test_arg, '-t', '0.1', '-f', 'null', 'NUL'],
        capture_output=True,
        text=True,
        timeout=5,
        encoding='utf-8',
    )
    
    # Check for errors
    for line in result2.stderr.split('\n'):
        if 'Could not find' in line or 'could not' in line.lower():
            print(f"\n  FFmpeg error: {line.strip()}")
            # Extract what FFmpeg thinks the name is
            if '[' in line and ']' in line:
                bracket_content = line[line.find('[')+1:line.find(']')]
                print(f"  FFmpeg sees: {repr(bracket_content)}")
            break
    
    break
