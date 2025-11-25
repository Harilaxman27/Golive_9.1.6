"""
GoLive Studio - GPU External Display Controller
GPU-accelerated external monitor/projector output using renderer abstraction
"""

from typing import Optional, Callable, List, Dict
from dataclasses import dataclass
from PyQt6.QtCore import QObject, QTimer, QSize, Qt, QRect, QRectF
from PyQt6.QtGui import QImage, QScreen
from PyQt6.QtWidgets import QWidget, QApplication
from PyQt6.QtOpenGLWidgets import QOpenGLWidget

from .base_renderer import BaseRenderer, RenderLayer, RenderTexture, BlendMode
from . import create_renderer


class GPUExternalDisplayWindow(QOpenGLWidget):
    """
    GPU-accelerated external display window
    Renders frames using GPU directly to external monitor
    """
    
    def __init__(self, screen_geometry: QRect, renderer_backend='auto', parent=None):
        super().__init__(parent)
        
        # Window setup for external display
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)
        self.setWindowFlag(Qt.WindowType.Tool, True)
        
        # Position on target screen
        self.setGeometry(screen_geometry)
        
        # GPU renderer
        self.renderer: Optional[BaseRenderer] = None
        self.renderer_backend = renderer_backend
        # Mirror mode: 'program' (match program buffer) or 'display' (match external display native resolution)
        self._mode: str = 'program'
        
        # Frame data
        self._current_frame: Optional[QImage] = None
        self._frame_texture: Optional[RenderTexture] = None
        self._frame_layer: Optional[RenderLayer] = None
        # Layer provider (preferred) and GPU texture cache
        self._layer_provider: Optional[Callable[[QSize], List[QImage]]] = None
        self._texture_cache: Dict[str, RenderTexture] = {}
        
        # Performance optimization
        self.setUpdateBehavior(QOpenGLWidget.UpdateBehavior.NoPartialUpdate)
        
        # Show fullscreen on target display
        self.showFullScreen()
    
    def initializeGL(self):
        """Initialize GPU renderer for external display"""
        try:
            self.renderer = create_renderer(self.renderer_backend, widget=self)
            
            if not self.renderer.initialize():
                raise RuntimeError("Failed to initialize external display renderer")
            
            # Create frame layer
            self._setup_frame_layer()
            
            print(f"External display GPU renderer initialized: {type(self.renderer).__name__}")
            
        except Exception as e:
            print(f"Failed to initialize external display GPU renderer: {e}")
    
    def resizeGL(self, width: int, height: int):
        """Handle resize"""
        if self.renderer:
            self.renderer.resize(width, height)
            self._setup_frame_layer()
    
    def paintGL(self):
        """Render frame to external display"""
        if not self.renderer or not self.renderer.is_initialized:
            return
        
        try:
            if self._layer_provider:
                self._render_layers_native()
            else:
                self._update_frame_layer()
                self.renderer.render_frame()
        except Exception as e:
            print(f"External display render error: {str(e)}")
    
    def _setup_frame_layer(self):
        """Setup frame rendering layer"""
        if not self.renderer:
            return

        native_size = self.native_pixel_size()
        self._frame_layer = RenderLayer(
            texture=None,
            transform=QRectF(0, 0, native_size.width(), native_size.height()),
            z_order=0,
            visible=True
        )
        
        self.renderer.clear_layers()
        self.renderer.add_layer(self._frame_layer)

    def _render_layers_native(self):
        """Request separate layers (source/overlays/text) at native resolution and compose on GPU."""
        if not self.renderer:
            return
        target_size = self.native_pixel_size()
        # The layer provider returns a list of QImages in z-order already sized for target
        # Contract for now: index 0 = source frame (background), others = overlays/text
        images: List[QImage] = self._layer_provider(target_size) if self._layer_provider else []
        if not images:
            return
        # Build layers with per-image textures, cache by key (size + index) to minimize reallocation
        self.renderer.clear_layers()
        for idx, img in enumerate(images):
            if not img or img.isNull():
                continue
            key = f"layer_{idx}_{target_size.width()}x{target_size.height()}"
            tex = self._texture_cache.get(key)
            if (tex is None) or (tex.width != img.width()) or (tex.height != img.height()):
                # Dispose old texture if any
                if tex is not None:
                    try:
                        self.renderer.delete_texture(tex)
                    except Exception:
                        pass
                tex = self.renderer.create_texture(img.width(), img.height())
                self._texture_cache[key] = tex
            # Upload image data
            self.renderer.upload_texture(tex, img)
            # Fullscreen transform (1:1 sampling at native pixels)
            layer = RenderLayer(
                texture=tex,
                transform=QRectF(0, 0, target_size.width(), target_size.height()),
                z_order=idx,
                visible=True,
                blend_mode=BlendMode.ALPHA_BLEND,
                opacity=1.0
            )
            self.renderer.add_layer(layer)
        # Render all layers into the default framebuffer
        self.renderer.render_frame()
    
    def _update_frame_layer(self):
        """Update frame layer with current frame"""
        if not self.renderer or not self._frame_layer:
            return
        
        if self._current_frame and not self._current_frame.isNull():
            # Create or update texture
            if not self._frame_texture or \
               self._frame_texture.width != self._current_frame.width() or \
               self._frame_texture.height != self._current_frame.height():
                
                if self._frame_texture:
                    self.renderer.delete_texture(self._frame_texture)
                
                self._frame_texture = self.renderer.create_texture(
                    self._current_frame.width(),
                    self._current_frame.height()
                )
            
            # Upload frame data
            self.renderer.upload_texture(self._frame_texture, self._current_frame)
            self._frame_layer.texture = self._frame_texture
            self._frame_layer.visible = True
        else:
            self._frame_layer.visible = False
    
    def set_frame(self, img: QImage):
        """Set frame to display"""
        if img is None or img.isNull():
            self._current_frame = None
        else:
            if self._mode == 'display':
                # In display mode, assume provider already delivered native-pixel buffer; avoid CPU scaling
                self._current_frame = img
            else:
                # In program mode, scale to window size (logical) as a compatibility path
                target_size = self.size()
                if img.size() != target_size:
                    self._current_frame = img.scaled(
                        target_size,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation
                    )
                else:
                    self._current_frame = img
        
        self.update()

    def set_mode(self, mode: str):
        """Set mirror mode: 'program' or 'display'"""
        mode = (mode or 'program').lower()
        if mode not in ('program', 'display'):
            mode = 'program'
        if self._mode != mode:
            self._mode = mode
            # Recreate frame layer on mode change
            self._setup_frame_layer()

    def native_pixel_size(self) -> QSize:
        """Return the native pixel size of this window's framebuffer (accounts for devicePixelRatio)."""
        dpr = 1.0
        try:
            dpr = float(self.devicePixelRatioF())
        except Exception:
            pass
        w = int(max(1, round(self.width() * dpr)))
        h = int(max(1, round(self.height() * dpr)))
        return QSize(w, h)
    
    def set_layer_provider(self, provider: Optional[Callable[[QSize], List[QImage]]]):
        """Set a provider that returns separate layer images sized to target (source, overlays, text).
        When provided, this path takes precedence over the legacy frame provider for sharp native rendering."""
        self._layer_provider = provider
    
    def cleanup(self):
        """Clean up GPU resources"""
        if self.renderer:
            if self._frame_texture:
                self.renderer.delete_texture(self._frame_texture)
            self.renderer.cleanup()
            self.renderer = None


class GPUDisplayMirrorController(QObject):
    """
    GPU-accelerated display mirror controller
    Manages external display output using GPU rendering
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self._window: Optional[GPUExternalDisplayWindow] = None
        self._frame_provider: Optional[Callable[[QSize], QImage]] = None
        self._layer_provider: Optional[Callable[[QSize], List[QImage]]] = None
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._update_frame)
        
        self._running = False
        self._target_screen: Optional[QScreen] = None
        self._settings = {}
        self._mode: str = 'program'  # 'program' or 'display'
        
        # Performance settings
        self._fps = 30
        self._maximize = True
        
    def set_frame_provider(self, provider: Callable[[QSize], QImage]):
        """Set frame provider function"""
        self._frame_provider = provider
    
    def set_layer_provider(self, provider: Callable[[QSize], List[QImage]]):
        """Set layer provider function (preferred for high-quality native rendering)."""
        self._layer_provider = provider
    
    def start(self, settings: dict) -> bool:
        """
        Start external display mirroring
        
        Args:
            settings: Display settings dict with keys:
                - screen_index: Target screen index
                - fps: Target FPS
                - maximize: Whether to maximize window
                - renderer_backend: 'auto', 'opengl', 'd3d'
        
        Returns:
            bool: Success status
        """
        try:
            if self._running:
                self.stop()
            
            self._settings = settings.copy()
            self._mode = (self._settings.get('mode', 'program') or 'program').lower()
            
            # Get target screen
            screen_index = settings.get('screen_index', 1)
            screens = QApplication.screens()
            
            if screen_index >= len(screens):
                print(f"Screen index {screen_index} not available, using primary screen")
                screen_index = 0
            
            self._target_screen = screens[screen_index]
            screen_geometry = self._target_screen.geometry()
            
            # Create external display window
            renderer_backend = settings.get('renderer_backend', 'auto')
            self._window = GPUExternalDisplayWindow(screen_geometry, renderer_backend)
            # Apply mode to the window
            self._window.set_mode(self._mode)
            # Pass layer provider to window if present
            if self._layer_provider:
                self._window.set_layer_provider(self._layer_provider)
            
            # Configure FPS
            self._fps = max(1, min(120, settings.get('fps', 30)))
            interval_ms = int(1000 / self._fps)
            
            # Start update timer
            self._timer.start(interval_ms)
            self._running = True
            
            print(f"GPU external display started on screen {screen_index} at {self._fps} FPS, mode={self._mode}")
            return True
            
        except Exception as e:
            print(f"Failed to start GPU external display: {e}")
            return False
    
    def stop(self):
        """Stop external display mirroring"""
        try:
            self._running = False
            self._timer.stop()
            
            if self._window:
                self._window.cleanup()
                self._window.close()
                self._window = None
            
            print("GPU external display stopped")
            
        except Exception as e:
            print(f"Error stopping GPU external display: {e}")
    
    def update(self, settings: dict):
        """Update display settings"""
        try:
            self._settings.update(settings)
            if 'mode' in settings:
                self._mode = (settings.get('mode', self._mode) or 'program').lower()
                if self._window:
                    self._window.set_mode(self._mode)
            
            # Update FPS if changed
            new_fps = settings.get('fps', self._fps)
            if new_fps != self._fps:
                self._fps = max(1, min(120, new_fps))
                if self._running:
                    interval_ms = int(1000 / self._fps)
                    self._timer.start(interval_ms)
            
            print(f"GPU external display settings updated: FPS={self._fps}, mode={self._mode}")
            
        except Exception as e:
            print(f"Error updating GPU external display: {e}")
    
    def is_running(self) -> bool:
        """Check if mirroring is active"""
        return self._running and self._window is not None
    
    def get_target_size(self) -> QSize:
        """Get target display size"""
        # In display mode, ask the window for native-pixel framebuffer size (accounts for HiDPI)
        if self._mode == 'display' and self._window:
            return self._window.native_pixel_size()
        # Otherwise, use logical size of target screen or fallback
        if self._target_screen:
            try:
                geo = self._target_screen.geometry()
                return geo.size()
            except Exception:
                pass
        return QSize(1920, 1080)
    
    def _update_frame(self):
        """Update frame on external display"""
        if not self._running or not self._window or not self._frame_provider:
            return
        
        try:
            # Get frame from provider at appropriate resolution
            target_size = self.get_target_size()
            frame = self._frame_provider(target_size)
            
            if frame and not frame.isNull():
                self._window.set_frame(frame)
                
        except Exception as e:
            print(f"External display frame update error: {e}")
    
    def get_performance_info(self) -> dict:
        """Get performance information"""
        info = {
            'running': self._running,
            'fps': self._fps,
            'target_screen': self._target_screen.name() if self._target_screen else None,
            'renderer_type': 'Unknown'
        }
        
        if self._window and self._window.renderer:
            info['renderer_type'] = type(self._window.renderer).__name__
        
        return info
