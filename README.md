# GoLive Studio

**Professional Live Streaming & Recording Application**

GoLive Studio is a cross-platform application for live streaming and recording with professional-grade features, hardware acceleration, and an intuitive interface.

---

## Features

### Core Capabilities
- 🎥 **Multi-Platform Streaming** - Stream to YouTube, Twitch, Facebook, and custom RTMP servers
- 🎬 **Dual-Stream Support** - Stream to two platforms simultaneously
- 💾 **Local Recording** - Record high-quality video locally while streaming
- 🖥️ **External Display Mirroring** - Preview your program output on external displays
- 🎨 **Real-Time Effects** - Apply video effects and transitions in real-time
- 🎭 **Text Overlays** - Add customizable text overlays to your stream

### Advanced Features
- ⚡ **Hardware Acceleration** - Support for NVENC, VideoToolbox, QuickSync, and AMF encoders
- 🎵 **Audio Mixing** - Professional audio capture and mixing
- 🔄 **Scene Management** - Organize your sources with scenes (coming soon)
- 📹 **Multiple Sources** - Media files, cameras, screen capture (in development)
- 🎯 **Adaptive Quality** - Automatic quality adjustment based on system performance
- 🔐 **Secure Settings** - Stream keys stored securely

---

## System Requirements

### Minimum Requirements
- **OS**: macOS 10.15+, Windows 10+, or Linux (Ubuntu 20.04+)
- **CPU**: Intel Core i5 or equivalent
- **RAM**: 4GB (8GB recommended)
- **GPU**: Any GPU with OpenGL 3.3+ support
- **Disk**: 500MB for application + space for recordings

### Recommended Requirements
- **CPU**: Intel Core i7 or equivalent (for 1080p60)
- **RAM**: 8GB+
- **GPU**: NVIDIA GPU (NVENC), AMD GPU (AMF), or Apple Silicon (VideoToolbox)
- **Network**: 10Mbps upload for 1080p streaming

---

## Installation

### macOS

1. **Install FFmpeg** (required):
   ```bash
   brew install ffmpeg
   ```

2. **Download GoLive Studio** from the releases page

3. **Move to Applications folder** and launch

### Windows

1. **Install FFmpeg**:
   - Download from [ffmpeg.org](https://ffmpeg.org/download.html)
   - Add to PATH or set `GOLIVE_FFMPEG_PATH` environment variable

2. **Download GoLive Studio** installer from releases

3. **Run installer** and follow prompts

### Linux

1. **Install FFmpeg**:
   ```bash
   # Ubuntu/Debian
   sudo apt install ffmpeg
   
   # Fedora
   sudo dnf install ffmpeg
   
   # Arch
   sudo pacman -S ffmpeg
   ```

2. **Install dependencies**:
   ```bash
   sudo apt install python3-pyqt6 python3-pip
   ```

3. **Install GoLive Studio** or run from source

---

## Quick Start Guide

### First Launch

1. **FFmpeg Validation** - The application will check for FFmpeg on startup
2. **Configure Settings** - Set your streaming and recording preferences
3. **Add Stream Keys** - Configure your streaming platforms

### Streaming Setup

1. Click **Stream 1 Settings** ⚙️
2. Enter your **RTMP URL** (e.g., `rtmp://a.rtmp.youtube.com/live2`)
3. Enter your **Stream Key**
4. Choose video quality and encoder
5. Click **OK** to save

### Start Streaming

1. Select your video source or effect
2. Click the **Stream button** 🔴
3. Monitor status in the UI
4. Click again to stop

### Recording Setup

1. Click **Recording Settings** ⚙️
2. Choose output folder and format
3. Set video quality and bitrate
4. Click **OK** to save

### Start Recording

1. Select your content
2. Click **Record button** ⏺
3. Recording indicator will turn red
4. Click **Stop** when finished

---

## Configuration

### Settings Location

- **macOS**: `~/Library/Application Support/GoLive Studio/config.json`
- **Windows**: `%APPDATA%\GoLive Studio\config.json`
- **Linux**: `~/.config/golive_studio/config.json`

### Log Files

- **macOS**: `~/Library/Logs/GoLive Studio/`
- **Windows**: `%APPDATA%\GoLive Studio\logs\`
- **Linux**: `~/.local/share/golive-studio/logs/`

### Stream Keys Security

Stream keys are stored in plaintext in the configuration file. Keep this file secure:

```bash
# macOS/Linux - restrict permissions
chmod 600 ~/.config/golive_studio/config.json
```

**Note**: Future versions will use system keychain for secure storage.

---

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Space` | Start/Stop streaming |
| `R` | Start/Stop recording |
| `P` | Pause/Resume recording |
| `Cmd/Ctrl + ,` | Open settings |
| `Cmd/Ctrl + Q` | Quit application |

---

## Troubleshooting

### FFmpeg Not Found

**Error**: "FFmpeg is required for GoLive Studio to function"

**Solution**:
1. Install FFmpeg using your package manager (see Installation section)
2. Restart GoLive Studio
3. If still not working, set `GOLIVE_FFMPEG_PATH` environment variable

### macOS Quarantine Issues

**Error**: "FFmpeg found but is not executable"

**Solution**:
```bash
# Remove quarantine attribute
xattr -d com.apple.quarantine /path/to/GoLive\ Studio.app
```

### Streaming Connection Failures

**Symptoms**: Stream disconnects frequently

**Solutions**:
1. Check your internet connection (run speed test)
2. Lower bitrate in Stream Settings
3. Check firewall settings
4. Verify RTMP URL and stream key are correct
5. Check streaming platform status

### High CPU Usage

**Solutions**:
1. Switch to hardware encoder (NVENC, VideoToolbox, etc.)
2. Lower resolution or frame rate
3. Disable unnecessary effects
4. Enable adaptive quality in settings

### Recording Sync Issues

**Symptoms**: Audio/video out of sync

**Solutions**:
1. Use media file's native audio track (not device capture)
2. Adjust A/V delay in settings
3. Ensure sufficient disk write speed
4. Close other resource-intensive applications

### Memory Issues

**Symptoms**: Application uses excessive memory

**Solutions**:
1. Clear effect thumbnail cache
2. Reduce preview quality
3. Disable unnecessary features
4. Restart application periodically

---

## Development

### Running from Source

1. **Clone repository**:
   ```bash
   git clone https://github.com/yourusername/golive-studio.git
   cd golive-studio
   ```

2. **Create virtual environment**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Run application**:
   ```bash
   python main.py
   ```

### Building

#### macOS
```bash
./build_macos.sh
```

#### Windows
```cmd
build_windows.bat
```

#### Linux
```bash
./build_scripts/build_linux.sh
```

### Project Structure

```
golive-studio/
├── main.py                 # Main application entry point
├── config.py               # Configuration management
├── error_handler.py        # Centralized error handling
├── ffmpeg_validator.py     # FFmpeg validation on startup
├── streaming.py            # RTMP streaming controller
├── recording.py            # Local recording controller
├── av_streamer.py          # PyAV-based A/V sync
├── audio/                  # Audio capture modules
│   ├── base_audio.py
│   ├── macos_audio.py
│   └── qt_audio.py
├── encoder/                # Video encoder modules
│   ├── base_encoder.py
│   ├── encoder_selector.py # Shared encoder selection
│   ├── nvenc_encoder.py
│   ├── vt_encoder.py
│   └── x264_encoder.py
├── renderer/               # GPU rendering modules
│   ├── base_renderer.py
│   ├── opengl_renderer.py
│   └── d3d_renderer.py
├── build_scripts/          # Platform-specific build scripts
└── effects/                # Video effect resources
```

### Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

---

## Known Issues

### Current Limitations

- ❌ Screen capture not yet implemented
- ❌ Scene management in development
- ❌ Audio mixer UI incomplete
- ❌ Camera preview needs improvement
- ⚠️ Stream key storage not encrypted (planned for future)

### Reported Bugs

See [Issues](https://github.com/yourusername/golive-studio/issues) on GitHub

---

## Roadmap

### Version 1.1 (Next Release)
- [ ] Screen/window capture
- [ ] Scene management system
- [ ] Visual audio mixer
- [ ] Encrypted settings storage
- [ ] Improved error messages

### Version 1.2 (Future)
- [ ] NDI/RTSP source support
- [ ] Plugin system for custom effects
- [ ] Cloud integration
- [ ] Multi-language support
- [ ] Advanced audio processing (VST)

---

## License

GoLive Studio is licensed under the MIT License. See [LICENSE.txt](LICENSE.txt) for details.

---

## Support

- **Documentation**: See this README
- **Bug Reports**: [GitHub Issues](https://github.com/yourusername/golive-studio/issues)
- **Feature Requests**: [GitHub Discussions](https://github.com/yourusername/golive-studio/discussions)
- **Email**: support@golivestudio.com

---

## Credits

### Third-Party Libraries

- **PyQt6** - GUI framework
- **FFmpeg** - Video/audio processing
- **PyAV** - Python bindings for FFmpeg libraries
- **NumPy** - Numerical processing
- **Pillow** - Image processing
- **psutil** - System monitoring

### Contributors

See [CONTRIBUTORS.md](CONTRIBUTORS.md) for the full list.

---

## Acknowledgments

Special thanks to the open-source community and all contributors who have helped make GoLive Studio possible.

---

**GoLive Studio** - Professional streaming made simple.

*Version 1.0 - December 2025*
