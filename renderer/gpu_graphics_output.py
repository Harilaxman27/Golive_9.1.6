"""
GoLive Studio - GPU Graphics Output Widget
GPU-accelerated replacement for graphics_output.py using renderer abstraction
"""

from typing import Optional, Dict, Tuple
import os

from PyQt6.QtCore import QTimer, QSize, QElapsedTimer, Qt, QRectF
from PyQt6.QtGui import QImage, QColor, QPainter, QPixmap
from PyQt6.QtOpenGLWidgets import QOpenGLWidget

from .base_renderer import BaseRenderer, RenderLayer, RenderTexture, BlendMode
from . import create_renderer


class GPUGraphicsOutputWidget(QOpenGLWidget):
    """
    GPU-accelerated graphics output widget
    Replaces the original GraphicsOutputWidget with GPU-based rendering
    """
    
    def __init__(self, parent=None, renderer_backend='auto'):
        super().__init__(parent)
        
        # Renderer
        self.renderer: Optional[BaseRenderer] = None
        self.renderer_backend = renderer_backend
        
        # Current source frame
        self._last_frame: Optional[QImage] = None
        self._current_source: Optional[dict] = None
        
        # Textures
        self._source_texture: Optional[RenderTexture] = None
        self._overlay_texture: Optional[RenderTexture] = None
        self._text_texture: Optional[RenderTexture] = None
        
        # Layers
        self._background_layer: Optional[RenderLayer] = None
        self._source_layer: Optional[RenderLayer] = None
        self._overlay_layer: Optional[RenderLayer] = None
        self._text_layer: Optional[RenderLayer] = None
        
        # Overlay state
        self._overlay_image: Optional[QImage] = None
        self._overlay_path: Optional[str] = None
        self._opening_norm: Optional[Tuple[float, float, float, float]] = None
        
        # Text overlay properties
        self._text_props = {
            'visible': False,
            'text': '',
            'font_size': 36,
            'font_family': '',
            'color': QColor(255, 255, 255, 255),
            'stroke_color': QColor(0, 0, 0, 255),
            'stroke_width': 3,
            'bg_enabled': False,
            'bg_color': QColor(0, 0, 0, 160),
            'pos_x': 50,
            'pos_y': 90,
            'anchor': 'center',
            'scroll': False,
            'scroll_speed': 50,
        }
        
        # Rendering settings
        self._overscan = 1.03
        self._render_output_size: Optional[QSize] = None
        
        # Update timer
        self._update_timer = QTimer(self)
        self._update_timer.timeout.connect(self.update)
        self._target_interval_ms = 33  # ~30 FPS
        
        # Scrolling text
        self._scroll_timer = QTimer(self)
        self._scroll_timer.timeout.connect(self._on_scroll_tick)
        self._scroll_px = 0.0
        self._elapsed = QElapsedTimer()
        
        # Performance optimization
        self.setUpdateBehavior(QOpenGLWidget.UpdateBehavior.NoPartialUpdate)
    
    def initializeGL(self):
        """Initialize OpenGL context and renderer"""
        try:
            # Check if any GPU renderer is available first
            from . import check_gpu_support
            gpu_support = check_gpu_support()
            
            if not gpu_support.get('opengl_available') and not gpu_support.get('d3d_available'):
                print("No GPU renderer available, skipping GPU initialization")
                self.renderer = None
                return
            
            # Create renderer with this widget's context
            self.renderer = create_renderer(self.renderer_backend, widget=self)
            
            if not self.renderer or not self.renderer.initialize():
                raise RuntimeError("Failed to initialize renderer")
            
            # Create initial layers
            self._setup_layers()
            
            print(f"GPU renderer initialized: {type(self.renderer).__name__}")
            
        except Exception as e:
            print(f"Failed to initialize GPU renderer: {e}")
            self.renderer = None
            # Don't raise exception - just continue without GPU rendering
    
    def resizeGL(self, width: int, height: int):
        """Handle OpenGL resize"""
        if self.renderer:
            self.renderer.resize(width, height)
    
    def paintGL(self):
        """Render frame using GPU"""
        if not self.renderer or not self.renderer.is_initialized:
            return
        
        try:
            # Update layers
            self._update_layers()
            
            # Render frame
            rendered_image = self.renderer.render_frame()
            
            # The rendered image is automatically displayed by OpenGL
            
        except Exception as e:
            print(f"GPU render error: {e}")
    
    def _setup_layers(self):
        """Setup initial render layers"""
        if not self.renderer:
            return
        
        size = self.size()
        if not size.isValid():
            size = QSize(1920, 1080)
        
        # Background layer (black)
        self._background_layer = RenderLayer(
            texture=None,
            transform=QRectF(0, 0, size.width(), size.height()),
            z_order=0,
            visible=True
        )
        
        # Source video layer
        self._source_layer = RenderLayer(
            texture=None,
            transform=QRectF(0, 0, size.width(), size.height()),
            z_order=10,
            visible=True
        )
        
        # Overlay layer
        self._overlay_layer = RenderLayer(
            texture=None,
            transform=QRectF(0, 0, size.width(), size.height()),
            z_order=20,
            visible=False
        )
        
        # Text layer
        self._text_layer = RenderLayer(
            texture=None,
            transform=QRectF(0, 0, size.width(), size.height()),
            z_order=30,
            visible=False
        )
        
        # Add layers to renderer
        self.renderer.add_layer(self._background_layer)
        self.renderer.add_layer(self._source_layer)
        self.renderer.add_layer(self._overlay_layer)
        self.renderer.add_layer(self._text_layer)
    
    def _update_layers(self):
        """Update layer textures and properties"""
        if not self.renderer:
            return
        
        # Update source layer
        if self._last_frame and not self._last_frame.isNull():
            if not self._source_texture:
                self._source_texture = self.renderer.create_texture(
                    self._last_frame.width(),
                    self._last_frame.height()
                )
            
            self.renderer.upload_texture(self._source_texture, self._last_frame)
            self._source_layer.texture = self._source_texture
            self._source_layer.visible = True
        else:
            self._source_layer.visible = False
        
        # Update overlay layer
        if self._overlay_image and not self._overlay_image.isNull():
            if not self._overlay_texture:
                self._overlay_texture = self.renderer.create_texture(
                    self._overlay_image.width(),
                    self._overlay_image.height()
                )
            
            self.renderer.upload_texture(self._overlay_texture, self._overlay_image)
            self._overlay_layer.texture = self._overlay_texture
            self._overlay_layer.visible = True
        else:
            self._overlay_layer.visible = False
        
        # Update text layer
        if self._text_props.get('visible') and self._text_props.get('text'):
            text_image = self._render_text_image(self.size())
            if not text_image.isNull():
                if not self._text_texture:
                    self._text_texture = self.renderer.create_texture(
                        text_image.width(),
                        text_image.height()
                    )
                
                self.renderer.upload_texture(self._text_texture, text_image)
                self._text_layer.texture = self._text_texture
                self._text_layer.visible = True
            else:
                self._text_layer.visible = False
        else:
            self._text_layer.visible = False
    
    def _render_text_image(self, size: QSize) -> QImage:
        """Render text overlay to image (CPU fallback for now)"""
        # This is a simplified version - the full text rendering logic
        # from the original graphics_output.py should be ported here
        
        if not self._text_props.get('visible') or not self._text_props.get('text'):
            return QImage()
        
        canvas = QImage(size, QImage.Format.Format_ARGB32)
        canvas.fill(QColor(0, 0, 0, 0))
        
        painter = QPainter(canvas)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
        
        # Basic text rendering
        color = self._text_props.get('color', QColor(255, 255, 255))
        painter.setPen(color)
        
        font_size = self._text_props.get('font_size', 36)
        font = painter.font()
        font.setPointSize(font_size)
        painter.setFont(font)
        
        text = self._text_props.get('text', '')
        pos_x = self._text_props.get('pos_x', 50) * size.width() / 100
        pos_y = self._text_props.get('pos_y', 90) * size.height() / 100
        
        painter.drawText(int(pos_x), int(pos_y), text)
        painter.end()
        
        return canvas
    
    # Public API methods (compatible with original GraphicsOutputWidget)
    
    def get_current_source(self) -> dict:
        """Get current source information"""
        return self._current_source
    
    def set_frame(self, frame: Optional[QImage]):
        """Set current source frame"""
        self._last_frame = frame
        
        # Throttle updates
        if not self._update_timer.isActive():
            self._update_timer.start(self._target_interval_ms)
    
    def set_overlay_from_path(self, path: Optional[str]):
        """Set overlay from image path"""
        if not path:
            self._overlay_image = None
            self._overlay_path = None
            self._overlay_texture = None
            if self._overlay_layer:
                self._overlay_layer.visible = False
            self.update()
            return
        
        img = QImage(path)
        if img.isNull():
            return
        
        self._overlay_image = img
        self._overlay_path = path
        
        # Clear existing texture to force recreation
        if self._overlay_texture:
            self.renderer.delete_texture(self._overlay_texture)
            self._overlay_texture = None
        
        self.update()
    
    def clear_overlay(self):
        """Clear current overlay"""
        self.set_overlay_from_path(None)
    
    def set_text_overlay(self, props: dict):
        """Set text overlay properties"""
        if not isinstance(props, dict):
            return
        
        self._text_props.update(props)
        
        # Clear existing texture to force recreation
        if self._text_texture:
            self.renderer.delete_texture(self._text_texture)
            self._text_texture = None
        
        # Manage scrolling timer
        if props.get('scroll') and props.get('visible') and props.get('text'):
            if not self._scroll_timer.isActive():
                self._elapsed.restart()
                self._scroll_timer.start(16)  # ~60 FPS for smooth scrolling
        else:
            self._scroll_timer.stop()
            self._scroll_px = 0.0
        
        self.update()
    
    def set_overscan(self, value: float):
        """Set overscan value"""
        self._overscan = max(1.0, float(value))
        self.update()
    
    def set_target_fps(self, fps: int):
        """Set target FPS"""
        self._target_interval_ms = max(5, int(1000 / max(5, min(120, fps))))
    
    def set_preview_render_size(self, size: Optional[QSize]):
        """Set fixed render size for preview"""
        self._render_output_size = size
        self.update()
    
    def render_to_image(self, size: QSize) -> QImage:
        """Render current composition to image"""
        if not self.renderer or not self.renderer.is_initialized:
            # Fallback to black image
            img = QImage(size, QImage.Format.Format_RGBA8888)
            img.fill(0)
            return img
        
        try:
            # Create temporary framebuffer for export
            export_fbo = self.renderer.create_framebuffer(size.width(), size.height())
            if export_fbo == 0:
                # Fallback
                img = QImage(size, QImage.Format.Format_RGBA8888)
                img.fill(0)
                return img
            
            # Render to export framebuffer
            return self.renderer.render_frame(export_fbo)
            
        except Exception as e:
            print(f"Export render error: {e}")
            img = QImage(size, QImage.Format.Format_RGBA8888)
            img.fill(0)
            return img
    
    def render_source_only(self, size: QSize) -> QImage:
        """Render just the source without overlays"""
        if not self._last_frame or self._last_frame.isNull():
            return QImage(size, QImage.Format.Format_RGBA8888)
        
        # Scale source frame to target size
        scaled = self._last_frame.scaled(
            size,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        
        # Center on target canvas
        result = QImage(size, QImage.Format.Format_RGBA8888)
        result.fill(Qt.GlobalColor.black)
        
        x = (size.width() - scaled.width()) // 2
        y = (size.height() - scaled.height()) // 2
        
        painter = QPainter(result)
        painter.drawImage(x, y, scaled)
        painter.end()
        
        return result
    
    def _on_scroll_tick(self):
        """Update scrolling text"""
        try:
            ms = self._elapsed.restart()
            speed = float(self._text_props.get('scroll_speed', 50))
            self._scroll_px -= (speed * (ms / 1000.0))
            
            # Update text properties with new scroll position
            # This would need to be integrated with the text rendering
            self.update()
            
        except Exception:
            pass
    
    def cleanup(self):
        """Clean up GPU resources"""
        if self.renderer:
            # Clean up textures
            if self._source_texture:
                self.renderer.delete_texture(self._source_texture)
            if self._overlay_texture:
                self.renderer.delete_texture(self._overlay_texture)
            if self._text_texture:
                self.renderer.delete_texture(self._text_texture)
            
            self.renderer.cleanup()
            self.renderer = None
