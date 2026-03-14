# Audio Recording Fix Summary

## Problem
When pressing the "Start Recording" button, the video was being saved without audio. FFmpeg was falling back to silent audio (`anullsrc`) with the message:
```
Recording audio: requested Windows audio device not found; using silent audio.
```

## Root Causes Identified
1. **No Audio Device Selector in UI**: The recording settings dialog didn't have a control to select which audio input device to use
2. **Audio Device Detection Failing**: The device name matching logic couldn't properly handle device names with special characters (like the ® symbol in "Microphone Array (Intel® Smart Sound Technology...)")
3. **Empty Audio Device Parameter**: Without a selected device, the system couldn't capture audio and fell back to silent

## Solutions Implemented

### 1. **Added Audio Device Selector to Recording Settings UI**

Modified `recording_settings_dialog.py`:
- Added a new **Audio Device** dropdown in the Audio tab
- Users can now select from available audio input devices before recording
- Added a refresh button (🔄) to rescan for available devices
- Selected audio device is saved to config and reused for next recording

**New UI Controls:**
```
Audio Configuration
  ✅ Include audio in recording
  
Audio Device:    [🎤 Default (Auto-detect) ▼]  [🔄]
  
Audio Codec:     [AAC (Best compatibility) ▼]
Audio Bitrate:   [192 kbps (Recommended) ▼]
```

### 2. **Improved Audio Device Detection**

Modified `recording_settings_dialog.py` - Added `_list_windows_audio_devices()` function:
- Uses FFmpeg DirectShow to enumerate available audio input devices
- Properly parses device names and alternative names with special character handling
- Runs at startup and allows manual refresh

### 3. **Enhanced Device Name Matching**

Modified `recording.py`:
- Improved `_normalize_windows_device_name()` to handle Unicode characters properly
- Now properly handles special characters like ®, é, ü, etc.
- Added multiple matching strategies:
  - Exact name matching
  - Normalized string comparison
  - Substring matching for partial device names
  - Case-insensitive comparison

**Updated matching logic:**
```python
def _select_windows_dshow_audio_device(self, requested: str) -> str:
    # 1. Try exact match (friendly or alternative name)
    # 2. Try normalized comparison (handles special characters)
    # 3. Try substring matching (handles partial device names)
    # 4. Auto-select microphone devices if no match
    # 5. Fallback to first available device
```

### 4. **Config Integration**

Modified `main.py` and `recording_settings_dialog.py`:
- Audio device selection is saved to config file
- When opening recording settings, previously selected device is restored
- Audio device is passed to recorder when starting recording

**Config Keys Added:**
- `recording.audio_device` - Stores the selected audio device ID

## How to Use

1. **Open Recording Settings**
   - Click "Recording" button → "Settings" (gear icon)

2. **Select Audio Device** (NEW!)
   - Check "✅ Include audio in recording"
   - Select your microphone from the "Audio Device" dropdown
   - Click the refresh button (🔄) if your device isn't listed
   - Your device will be highlighted as "🎤 Microphone Array (Intel® Smart Sound...)"

3. **Start Recording**
   - Click "START RECORDING" button
   - Audio will now be captured using the selected device
   - All subsequent recordings will default to your selected device

## Technical Details

### Device Detection Process (Windows DirectShow)
```
FFmpeg query → Parse output → Extract friendly names + alternative names
→ Populate dropdown with available devices
```

### Device Name Normalization
```
Input: "Microphone Array (Intel® Smart Sound Technology...)"
↓
Normalize Unicode: Remove accents, special chars, convert to lowercase
↓
Compare with selected device: Match using multiple strategies
↓
Pass device ID to FFmpeg: audio="[device name or alternative]"
```

### Audio Recording Command
**Before (No Audio):**
```bash
ffmpeg ... -f lavfi -i anullsrc=cl=stereo:r=48000 ...
```

**After (With Audio):**
```bash
ffmpeg ... -thread_queue_size 1024 -rtbufsize 100M -f dshow \
  -i "audio=Microphone Array (Intel® ...)" ...
```

## Testing

Run the test script to verify audio device detection:
```bash
python test_audio_devices.py
```

Expected output:
```
Found 1 audio device(s):
  1. Friendly Name: Microphone Array (Intel® Smart Sound Technology...)
     Alternative: @device_cm_...

✅ Found microphone: Microphone Array (Intel® Smart Sound Technology...)
✅ Audio capture successful! File size: ~100 KB
```

## Files Modified

1. **recording_settings_dialog.py**
   - Added `_list_windows_audio_devices()` function
   - Added audio device selector dropdown
   - Added refresh button
   - Updated `get_values()` to include audio_device
   - Added audio device handling methods

2. **recording.py**
   - Improved `_normalize_windows_device_name()` for better unicode handling
   - Enhanced `_select_windows_dshow_audio_device()` with better matching logic
   - Better fallback behavior for device selection

3. **main.py**
   - Updated to pass audio_device from settings dialog to recorder
   - Added config storage and retrieval for audio device
   - Pass initial_audio_device to recording panels

## Known Limitations

- Device detection requires FFmpeg to be in PATH
- Works specifically with Windows DirectShow audio devices
- Special characters in device names are handled via normalization but best results with simple names
- If multiple devices have similar names, the first match is used

## Future Improvements

- Add audio device testing button to verify before recording
- Show audio levels/monitoring in real-time
- Support for multiple audio inputs (mix audio from several sources)
- macOS and Linux audio device selectors
