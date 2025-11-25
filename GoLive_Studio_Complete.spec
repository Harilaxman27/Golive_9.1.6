# -*- mode: python ; coding: utf-8 -*-
"""
Complete PyInstaller Spec for GoLive Studio
Comprehensive packaging with all dependencies and modules
"""

import sys
import os
from pathlib import Path

# Get project root
project_root = Path(__file__).parent
print(f"Building from: {project_root}")

# Define all Python modules in the project
project_modules = [
    'main',
    'config',
    'launch',
    
    # Core modules
    'fps_controller',
    'fps_stabilizer',
    'unified_timer',
    'event_coalescer',
    'gl_context_manager',
    'texture_pool',
    'smart_cache',
    'thread_pool_manager',
    'adaptive_quality',
    'memory_pool',
    'performance_monitor',
    'performance_optimizer',
    'aggressive_memory_optimizer',
    
    # Graphics and rendering
    'enhanced_graphics_output',
    'external_display',
    'enhanced_external_display',
    'text_overlay',
    'overlay_manager',
    'transitions',
    
    # Audio/Video
    'av_capture',
    'av_streamer',
    'streaming',
    'enhanced_streaming',
    'recording',
    'recording_settings_dialog',
    'enhanced_audio_sync',
    'enhanced_camera_input',
    'ffmpeg_utils',
    
    # Effects and UI
    'premiere_effects_panel_final',
    'streaming_settings_dialog_improved',
    
    # Resources
    'resources_rc',
]

# All hidden imports needed
hidden_imports = [
    # PyQt6 modules
    'PyQt6.QtCore',
    'PyQt6.QtGui',
    'PyQt6.QtWidgets',
    'PyQt6.QtOpenGL',
    'PyQt6.QtOpenGLWidgets',
    'PyQt6.QtMultimedia',
    'PyQt6.QtMultimediaWidgets',
    'PyQt6.sip',
    
    # Audio/Video processing
    'av',
    'av.audio',
    'av.video',
    'av.container',
    'av.codec',
    'cv2',
    'numpy',
    'PIL',
    'PIL.Image',
    'PIL.ImageTk',
    
    # OpenGL
    'OpenGL',
    'OpenGL.GL',
    'OpenGL.arrays',
    'OpenGL.platform',
    
    # System modules
    'psutil',
    'threading',
    'multiprocessing',
    'queue',
    'subprocess',
    'platform',
    'ctypes',
    'ctypes.util',
    
    # Data processing
    'json',
    'pickle',
    'hashlib',
    'weakref',
    'collections',
    'dataclasses',
    'enum',
    'statistics',
    'math',
    'time',
    'datetime',
    
    # File operations
    'pathlib',
    'shutil',
    'tempfile',
    'zipfile',
    'tarfile',
    
    # Network
    'requests',
    'urllib',
    'urllib.request',
    'urllib.parse',
    
    # macOS specific
    'objc',
    'Foundation',
    'AppKit',
    'AVFoundation',
    'CoreMedia',
    'Quartz',
    
    # Project modules and packages
    'audio',
    'audio.base_audio',
    'audio.macos_audio',
    'audio.qt_audio',
    'encoder',
    'encoder.base_encoder',
    'encoder.nvenc_encoder',
    'encoder.vt_encoder',
    'encoder.x264_encoder',
    'renderer',
    'renderer.base_renderer',
    'renderer.d3d_renderer',
    'renderer.gpu_external_display',
    'renderer.gpu_graphics_output',
    'renderer.gpu_overlay_manager',
    'renderer.migration_helper',
    'renderer.opengl_renderer',
]

# Data files to include
datas = [
    # UI files
    ('mainwindow.ui', '.'),
    ('resources.qrc', '.'),
    
    # Icons and assets
    ('EditLive.icns', '.'),
    ('EditLive.ico', '.'),
    ('icons', 'icons'),
    ('effects', 'effects'),
    
    # Configuration files
    ('requirements.txt', '.'),
    ('version_info.txt', '.'),
    ('LICENSE.txt', '.'),
    
    # FFmpeg binaries (if present)
    ('ffmpeg', 'ffmpeg'),
    
    # Documentation
    ('README.md', '.'),
]

# Binary files to include
binaries = []

# Add FFmpeg binaries if they exist
ffmpeg_paths = [
    '/usr/local/bin/ffmpeg',
    '/opt/homebrew/bin/ffmpeg',
    project_root / 'ffmpeg' / 'ffmpeg',
]

for ffmpeg_path in ffmpeg_paths:
    if os.path.exists(ffmpeg_path):
        binaries.append((str(ffmpeg_path), 'ffmpeg'))
        print(f"Including FFmpeg from: {ffmpeg_path}")
        break

# Exclude unnecessary modules to reduce size
excludes = [
    'tkinter',
    'turtle',
    'test',
    'unittest',
    'pydoc',
    'doctest',
    'argparse',
    'difflib',
    'inspect',
    'pdb',
    'profile',
    'pstats',
    'timeit',
    'trace',
    'matplotlib',
    'scipy',
    'pandas',
    'jupyter',
    'IPython',
]

# Analysis configuration
a = Analysis(
    ['main.py'],
    pathex=[str(project_root)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

# Remove duplicate files
pyz = PYZ(a.pure, a.zipped_data, cipher=None)

# Platform-specific executable configuration
if sys.platform == 'darwin':  # macOS
    exe = EXE(
        pyz,
        a.scripts,
        [],
        exclude_binaries=True,
        name='GoLive Studio',
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=True,
        console=False,
        disable_windowed_traceback=False,
        argv_emulation=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
        icon='EditLive.icns',
    )
    
    coll = COLLECT(
        exe,
        a.binaries,
        a.zipfiles,
        a.datas,
        strip=False,
        upx=True,
        upx_exclude=[],
        name='GoLive Studio',
    )
    
    app = BUNDLE(
        coll,
        name='GoLive Studio.app',
        icon='EditLive.icns',
        bundle_identifier='com.golive.studio',
        version='9.1.3',
        info_plist={
            'CFBundleName': 'GoLive Studio',
            'CFBundleDisplayName': 'GoLive Studio',
            'CFBundleIdentifier': 'com.golive.studio',
            'CFBundleVersion': '9.1.3',
            'CFBundleShortVersionString': '9.1.3',
            'CFBundleInfoDictionaryVersion': '6.0',
            'CFBundleExecutable': 'GoLive Studio',
            'CFBundlePackageType': 'APPL',
            'CFBundleSignature': 'GLVS',
            'NSHighResolutionCapable': True,
            'NSRequiresAquaSystemAppearance': False,
            'LSMinimumSystemVersion': '10.15.0',
            'NSCameraUsageDescription': 'GoLive Studio needs camera access for video capture.',
            'NSMicrophoneUsageDescription': 'GoLive Studio needs microphone access for audio capture.',
            'NSDesktopFolderUsageDescription': 'GoLive Studio needs desktop access for screen capture.',
            'NSDocumentsFolderUsageDescription': 'GoLive Studio needs documents access for saving recordings.',
        },
    )

elif sys.platform == 'win32':  # Windows
    exe = EXE(
        pyz,
        a.scripts,
        a.binaries,
        a.zipfiles,
        a.datas,
        [],
        name='GoLive Studio',
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=True,
        upx_exclude=[],
        runtime_tmpdir=None,
        console=False,
        disable_windowed_traceback=False,
        argv_emulation=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
        icon='EditLive.ico',
        version_file=None,
    )

else:  # Linux
    exe = EXE(
        pyz,
        a.scripts,
        a.binaries,
        a.zipfiles,
        a.datas,
        [],
        name='GoLive Studio',
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=True,
        upx_exclude=[],
        runtime_tmpdir=None,
        console=False,
        disable_windowed_traceback=False,
        argv_emulation=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
    )
