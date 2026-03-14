#!/usr/bin/env python3
"""
Test the fixed audio device detection parsing
"""

import subprocess
import re


def _list_windows_audio_devices_fixed() -> list[tuple[str, str]]:
    """List available Windows audio input devices using FFmpeg DirectShow.
    
    Returns: [(friendly_name, alternative_name_or_empty), ...]
    """
    try:
        ffmpeg_path = r"C:\ffmpeg\bin\ffmpeg.exe"
        
        print("[AUDIO] 🔍 Scanning for Windows DirectShow audio devices...")
        result = subprocess.run(
            [ffmpeg_path, '-hide_banner', '-f', 'dshow', '-list_devices', 'true', '-i', 'dummy'],
            capture_output=True,
            text=True,
            timeout=5,
            encoding='utf-8',
            errors='replace',
        )
        output = (result.stdout or '') + '\n' + (result.stderr or '')
        print(f"[AUDIO] FFmpeg returned {len(output)} characters")
        
        devices: list[tuple[str, str]] = []
        
        # Find all device entries that have "(audio)" marker
        # Pattern: [in#N....] "Device Name" (audio)
        # Note: Device names can span multiple lines in terminal output
        device_pattern = r'\[in#\d+[^\]]*\]\s+"([^"]+)"\s*\(audio\)'
        
        print("[AUDIO] 📡 Parsing device entries...")
        for match in re.finditer(device_pattern, output, re.DOTALL):
            name = match.group(1)
            # Clean up whitespace from line wrapping
            name = ' '.join(name.split())
            # Clean up encoding artifacts (Â character that appears before ®)
            name = name.replace('Â®', '®').replace('Â', '')
            
            if name and not any(d[0] == name for d in devices):
                devices.append((name, ''))
                print(f"[AUDIO] 🎤 Device found: '{name}'")
        
        # Find alternative names - these are labeled "Alternative name" on the next line
        lines = output.split('\n')
        for i, line in enumerate(lines):
            if 'Alternative name' in line and devices:
                match = re.search(r'"([^"]+)"', line)
                if match:
                    alt = match.group(1).strip()
                    # Assign to last device
                    fname, _ = devices[-1]
                    devices[-1] = (fname, alt)
                    print(f"[AUDIO] 🔗 Alternative name: {alt[:60]}...")
        
        print(f"\n[AUDIO] ✅ TOTAL DEVICES FOUND: {len(devices)}")
        for i, (fname, alt) in enumerate(devices, 1):
            print(f"[AUDIO]   {i}. {fname}")
            if alt:
                print(f"[AUDIO]      ↳ {alt[:80]}...")
        return devices
    except Exception as e:
        print(f"[AUDIO] ❌ Error listing audio devices: {e}")
        import traceback
        traceback.print_exc()
        return []


if __name__ == '__main__':
    devices = _list_windows_audio_devices_fixed()
    print("\n" + "="*80)
    print(f"RESULT: Found {len(devices)} audio devices")
    for name, alt in devices:
        print(f"  - {name}")

