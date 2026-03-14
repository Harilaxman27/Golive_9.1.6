# Quick Start: Fix Audio in Recording

## What Was Fixed?
Your recording was saving without audio because GoLive wasn't selecting an audio input device. This has been fixed with a new audio device selector.

## How to Use (3 Steps)

### Step 1: Open Recording Settings
1. Press the **Recording** button
2. Click the ⚙️ **Settings** button

### Step 2: Select Your Microphone ✨ NEW!
1. Check the box: **✅ Include audio in recording**
2. Select your microphone from the **Audio Device** dropdown
   - Look for: `🎤 Microphone Array (Intel® Smart Sound Technology...)`
   - If you don't see it, click the 🔄 **Refresh** button
3. You can also adjust audio codec and bitrate if needed

### Step 3: Start Recording
1. Click **💾 Save & Close** to save your audio device selection
2. Click **START RECORDING** button
3. ✅ Audio will now be captured!

## Tips

- **Your device selection is saved** - Next time you record, your selected device will be remembered
- **Click 🔄 to refresh** - If you connected a new microphone, click refresh to see it in the list
- **Default option** - If you select "🎤 Default (Auto-detect)", the system will automatically pick available audio

## Troubleshooting

| Problem | Solution |
|---------|----------|
| No audio devices in dropdown | Click 🔄 Refresh button to rescan connected devices |
| Still no audio after selecting device | Verify microphone is working in Windows Sound Settings (Settings → Sound → Volume and device preferences) |
| Audio recorded but very quiet | Adjust microphone volume in Windows Sound Settings or use GoLive's audio level controls if available |
| "Include audio" checkbox is greyed out | Check your recording settings - audio should be enabled by default |

## What Changed Behind the Scenes

✅ Added Audio Device Selector dropdown in Recording Settings  
✅ Implemented Windows audio device detection via FFmpeg  
✅ Improved device name matching to handle special characters (like ®)  
✅ Audio device preferences are now saved and restored  
✅ Better fallback logic when device isn't found  

## Need Help?

Check the logs for messages like:
- `🎤 Using audio device from settings: [device name]` - Audio device is selected correctly
- `🎤 Audio device: [device name]` - Auto-detected audio device
- `⚠️ Using silent audio` - No audio device found (run refreshing or check Windows sound settings)

Run the test to verify audio device detection:
```bash
python test_audio_devices.py
```

For detailed technical information, see: `AUDIO_FIX_SUMMARY.md`
