# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for GoLive Studio
Comprehensive build configuration for Windows EXE and macOS DMG
"""

import sys
import os
from pathlib import Path

# Get the project root directory
import os
project_root = Path(os.getcwd())

# Platform detection
IS_WINDOWS = sys.platform.startswith('win')
IS_MACOS = sys.platform == 'darwin'
IS_LINUX = sys.platform.startswith('linux')

# Platform-specific settings
if IS_MACOS:
    ffmpeg_binary = project_root / 'ffmpeg' / 'ffmpeg'
    icon_file = project_root / 'EditLive.icns'
    target_arch = 'universal2'  # Universal binary for both Intel and Apple Silicon
elif IS_WINDOWS:
    ffmpeg_binary = project_root / 'ffmpeg' / 'ffmpeg.exe'
    icon_file = project_root / 'EditLive.ico'
    target_arch = None
else:  # Linux
    ffmpeg_binary = project_root / 'ffmpeg' / 'ffmpeg'
    icon_file = None
    target_arch = None

# Data files to include - comprehensive list
datas = [
    # UI and resources
    (str(project_root / 'mainwindow.ui'), '.'),
    (str(project_root / 'resources_rc.py'), '.'),
    
    # Icons and effects
    (str(project_root / 'icons'), 'icons'),
    (str(project_root / 'effects'), 'effects'),
    
    # Module directories
    (str(project_root / 'renderer'), 'renderer'),
    (str(project_root / 'encoder'), 'encoder'),
    (str(project_root / 'audio'), 'audio'),
]

# Add resources.qrc if it exists
if (project_root / 'resources.qrc').exists():
    datas.append((str(project_root / 'resources.qrc'), '.'))

# Binary files to include
binaries = []

# Add FFmpeg binary if it exists
if ffmpeg_binary.exists():
    if IS_WINDOWS:
        binaries.append((str(ffmpeg_binary), 'ffmpeg'))
    else:
        binaries.append((str(ffmpeg_binary), 'ffmpeg'))

# Comprehensive hidden imports - all modules that PyInstaller might miss
hiddenimports = [
    # Standard library modules
    'json',
    'pickle',
    'hashlib',
    'threading',
    'queue',
    'subprocess',
    'platform',
    'tempfile',
    'shutil',
    'weakref',
    'gc',
    'math',
    'logging',
    'fractions',
    'collections',
    'collections.deque',
    'collections.OrderedDict',
    'concurrent.futures',
    'concurrent.futures.ThreadPoolExecutor',
    'dataclasses',
    'enum',
    'abc',
    
    # PyQt6 core modules
    'PyQt6',
    'PyQt6.QtCore',
    'PyQt6.QtGui',
    'PyQt6.QtWidgets',
    'PyQt6.QtMultimedia',
    'PyQt6.QtOpenGL',
    'PyQt6.QtOpenGLWidgets',
    'PyQt6.uic',
    
    # PyQt6 specific classes
    'PyQt6.QtCore.QObject',
    'PyQt6.QtCore.QTimer',
    'PyQt6.QtCore.QSize',
    'PyQt6.QtCore.QProcess',
    'PyQt6.QtCore.pyqtSignal',
    'PyQt6.QtCore.Qt',
    'PyQt6.QtCore.QRect',
    'PyQt6.QtCore.QRectF',
    'PyQt6.QtCore.QEasingCurve',
    'PyQt6.QtCore.QElapsedTimer',
    'PyQt6.QtCore.QEvent',
    'PyQt6.QtCore.QThread',
    'PyQt6.QtCore.pyqtSlot',
    'PyQt6.QtCore.QUrl',
    'PyQt6.QtCore.qInstallMessageHandler',
    'PyQt6.QtCore.QtMsgType',
    
    'PyQt6.QtGui.QImage',
    'PyQt6.QtGui.QPixmap',
    'PyQt6.QtGui.QPainter',
    'PyQt6.QtGui.QColor',
    'PyQt6.QtGui.QIcon',
    'PyQt6.QtGui.QFont',
    'PyQt6.QtGui.QImageReader',
    'PyQt6.QtGui.QPainterPath',
    'PyQt6.QtGui.QPen',
    'PyQt6.QtGui.QMouseEvent',
    'PyQt6.QtGui.QOpenGLContext',
    'PyQt6.QtGui.QSurfaceFormat',
    'PyQt6.QtGui.QOffscreenSurface',
    'PyQt6.QtGui.QGuiApplication',
    'PyQt6.QtGui.QScreen',
    
    'PyQt6.QtWidgets.QApplication',
    'PyQt6.QtWidgets.QMainWindow',
    'PyQt6.QtWidgets.QWidget',
    'PyQt6.QtWidgets.QFrame',
    'PyQt6.QtWidgets.QLabel',
    'PyQt6.QtWidgets.QVBoxLayout',
    'PyQt6.QtWidgets.QHBoxLayout',
    'PyQt6.QtWidgets.QGridLayout',
    'PyQt6.QtWidgets.QSplitter',
    'PyQt6.QtWidgets.QMessageBox',
    'PyQt6.QtWidgets.QLineEdit',
    'PyQt6.QtWidgets.QSlider',
    'PyQt6.QtWidgets.QPushButton',
    'PyQt6.QtWidgets.QColorDialog',
    'PyQt6.QtWidgets.QSpinBox',
    'PyQt6.QtWidgets.QCheckBox',
    'PyQt6.QtWidgets.QGroupBox',
    'PyQt6.QtWidgets.QComboBox',
    'PyQt6.QtWidgets.QDialog',
    'PyQt6.QtWidgets.QDialogButtonBox',
    'PyQt6.QtWidgets.QFontComboBox',
    'PyQt6.QtWidgets.QGraphicsView',
    'PyQt6.QtWidgets.QGraphicsScene',
    'PyQt6.QtWidgets.QGraphicsPixmapItem',
    'PyQt6.QtWidgets.QLayout',
    
    'PyQt6.QtMultimedia.QMediaPlayer',
    'PyQt6.QtMultimedia.QAudioOutput',
    'PyQt6.QtMultimedia.QAudioSource',
    'PyQt6.QtMultimedia.QAudioSink',
    'PyQt6.QtMultimedia.QMediaDevices',
    'PyQt6.QtMultimedia.QVideoSink',
    'PyQt6.QtMultimedia.QCamera',
    'PyQt6.QtMultimedia.QMediaCaptureSession',
    'PyQt6.QtMultimedia.QAudioFormat',
    'PyQt6.QtMultimedia.QAudioDevice',
    
    'PyQt6.QtOpenGL.QOpenGLFramebufferObject',
    'PyQt6.QtOpenGL.QOpenGLShaderProgram',
    'PyQt6.QtOpenGL.QOpenGLTexture',
    'PyQt6.QtOpenGLWidgets.QOpenGLWidget',
    
    # Third-party core libraries
    'numpy',
    'numpy.core',
    'numpy.core.multiarray',
    'numpy.core.numeric',
    'numpy.core.umath',
    'numpy.linalg',
    'numpy.random',
    'cv2',
    'cv2.gapi',
    'cv2.mat_wrapper',
    'cv2.misc',
    'cv2.typing',
    'cv2.utils',
    'cv2.data',
    'cv2.config',
    'cv2.version',
    'cv2.load_config_py3',
    'cv2.config-3',
    
    # OpenGL
    'OpenGL',
    'OpenGL.GL',
    'OpenGL.arrays',
    'OpenGL.GL.shaders',
    'OpenGL.arrays.vbo',
    
    # Audio/Video processing
    'av',
    'av.audio',
    'av.video',
    'av.codec',
    'av.container',
    'av.stream',
    'av.format',
    'av.packet',
    'av.frame',
    
    # PIL/Pillow
    'PIL',
    'PIL.Image',
    'PIL.ImageDraw',
    'PIL.ImageFont',
    'PIL.ImageFilter',
    'PIL.ImageEnhance',
    
    # Project modules - core
    'config',
    'ffmpeg_utils',
    'streaming',
    'recording',
    'text_overlay',
    'transitions',
    'overlay_manager',
    'external_display',
    'enhanced_external_display',
    'graphics_output',
    'enhanced_graphics_output',
    'recording_settings_dialog',
    'streaming_settings_dialog_improved',
    'gpu_streaming',
    'av_streamer',
    'av_capture',
    'enhanced_audio_sync',
    'enhanced_camera_input',
    'enhanced_streaming',
    'premiere_effects_panel_final',
    'premiere_effects_panel_v2',
    
    # Project modules - optimization
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
    
    # Renderer modules
    'renderer',
    'renderer.base_renderer',
    'renderer.opengl_renderer',
    'renderer.d3d_renderer',
    'renderer.gpu_graphics_output',
    'renderer.gpu_external_display',
    'renderer.gpu_overlay_manager',
    'renderer.migration_helper',
    
    # Encoder modules
    'encoder',
    'encoder.base_encoder',
    'encoder.x264_encoder',
    'encoder.nvenc_encoder',
    'encoder.vt_encoder',
    
    # Audio modules
    'audio',
    'audio.base_audio',
    'audio.qt_audio',
    'audio.macos_audio',
    
    # Resources
    'resources_rc',
]

# Platform-specific hidden imports
if IS_MACOS:
    hiddenimports.extend([
        'objc',
        'Foundation',
        'AVFoundation',
        'CoreMedia',
        'CoreVideo',
        'Quartz',
        'CoreGraphics',
        'AppKit',
        'Cocoa',
        'CoreAudio',
        'AudioToolbox',
        'VideoToolbox',
        'Metal',
        'MetalKit',
    ])
elif IS_WINDOWS:
    hiddenimports.extend([
        'win32api',
        'win32con',
        'win32gui',
        'win32process',
        'win32file',
        'win32pipe',
        'pywintypes',
        'winsound',
        'ctypes.wintypes',
        'msvcrt',
    ])
elif IS_LINUX:
    hiddenimports.extend([
        'gi',
        'gi.repository',
        'gi.repository.Gtk',
        'gi.repository.GLib',
        'gi.repository.Gst',
    ])

# Add psutil if available
try:
    import psutil
    hiddenimports.append('psutil')
except ImportError:
    pass

# Add requests if available
try:
    import requests
    hiddenimports.extend(['requests', 'urllib3', 'certifi'])
except ImportError:
    pass

# Modules to exclude (reduce bundle size)
excludes = [
    # Unused PyQt6 modules
    'PyQt6.QtBluetooth',
    'PyQt6.QtWebEngineCore',
    'PyQt6.QtWebEngineWidgets',
    'PyQt6.QtWebEngineQuick',
    'PyQt6.Qt3DCore',
    'PyQt6.Qt3DRender',
    'PyQt6.Qt3DInput',
    'PyQt6.Qt3DAnimation',
    'PyQt6.QtQml',
    'PyQt6.QtQuick',
    'PyQt6.QtQuickWidgets',
    'PyQt6.QtSql',
    'PyQt6.QtTest',
    'PyQt6.QtXml',
    'PyQt6.QtSvg',
    'PyQt6.QtSvgWidgets',
    'PyQt6.QtDesigner',
    'PyQt6.QtHelp',
    'PyQt6.QtLocation',
    'PyQt6.QtPositioning',
    'PyQt6.QtSensors',
    'PyQt6.QtSerialPort',
    'PyQt6.QtWebChannel',
    'PyQt6.QtWebSockets',
    'PyQt6.QtRemoteObjects',
    'PyQt6.QtScxml',
    'PyQt6.QtStateMachine',
    'PyQt6.QtCharts',
    'PyQt6.QtDataVisualization',
    'PyQt6.QtNetworkAuth',
    'PyQt6.QtPdf',
    'PyQt6.QtPdfWidgets',
    
    # Unused scientific libraries
    'matplotlib',
    'scipy',
    'pandas',
    'sklearn',
    'tensorflow',
    'torch',
    'keras',
    
    # Unused GUI toolkits
    'tkinter',
    'wx',
    'kivy',
    
    # Development tools
    'pytest',
    'unittest',
    'doctest',
    'pdb',
    'cProfile',
    'profile',
    
    # Documentation tools
    'sphinx',
    'docutils',
    
    # Jupyter/IPython
    'IPython',
    'jupyter',
    'notebook',
    
    # Other unused modules
    'email',
    'html',
    'http',
    'urllib',
    'xml',
    'xmlrpc',
    'distutils',
    'setuptools',
    'pip',
]

# Analysis configuration
a = Analysis(
    ['main.py'],
    pathex=[str(project_root)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
    optimize=0,
)

# Remove duplicate files and optimize
pyz = PYZ(a.pure, a.zipped_data, cipher=None)

# Executable configuration
exe_kwargs = {
    'pyz': pyz,
    'a.scripts': a.scripts,
    'a.binaries': a.binaries,
    'a.zipfiles': a.zipfiles,
    'a.datas': a.datas,
    'name': 'GoLive Studio',
    'debug': False,
    'bootloader_ignore_signals': False,
    'strip': False,
    'upx': True,
    'upx_exclude': [],
    'runtime_tmpdir': None,
    'console': False,
    'disable_windowed_traceback': False,
}

# Add icon if it exists
if icon_file and icon_file.exists():
    exe_kwargs['icon'] = str(icon_file)

# Add target architecture for macOS
if target_arch and IS_MACOS:
    exe_kwargs['target_arch'] = target_arch

# Create executable
exe = EXE(**exe_kwargs)

# Platform-specific bundle creation
if IS_MACOS:
    # macOS app bundle
    app = BUNDLE(
        exe,
        name='GoLive Studio.app',
        icon=str(icon_file) if icon_file and icon_file.exists() else None,
        bundle_identifier='com.golivestudio.app',
        version='1.0.0',
        info_plist={
            'CFBundleName': 'GoLive Studio',
            'CFBundleDisplayName': 'GoLive Studio',
            'CFBundleVersion': '1.0.0',
            'CFBundleShortVersionString': '1.0.0',
            'CFBundleIdentifier': 'com.golivestudio.app',
            'CFBundleExecutable': 'GoLive Studio',
            'CFBundlePackageType': 'APPL',
            'CFBundleSignature': 'GLVS',
            'NSCameraUsageDescription': 'GoLive Studio needs camera access to capture video from your inputs.',
            'NSMicrophoneUsageDescription': 'GoLive Studio needs microphone access to capture audio from your inputs.',
            'NSDesktopFolderUsageDescription': 'GoLive Studio needs access to save recordings and screenshots.',
            'NSDocumentsFolderUsageDescription': 'GoLive Studio needs access to save recordings and screenshots.',
            'NSDownloadsFolderUsageDescription': 'GoLive Studio needs access to save recordings and screenshots.',
            'NSHighResolutionCapable': True,
            'LSMinimumSystemVersion': '10.15.0',
            'LSApplicationCategoryType': 'public.app-category.video',
            'NSRequiresAquaSystemAppearance': False,
            'NSSupportsAutomaticGraphicsSwitching': True,
            'NSHumanReadableCopyright': 'Copyright © 2024 GoLive Studio. All rights reserved.',
        },
    )
elif IS_WINDOWS:
    # Windows doesn't need additional bundle configuration
    # The exe is sufficient for Windows distribution
    pass