"""
GoLive Studio - Base Renderer Abstract Interface
Defines the abstract interface for GPU-based rendering backends
"""

from abc import ABC, abstractmethod
from typing import Optional, Tuple, List, Dict, Any
from dataclasses import dataclass
from enum import Enum
from PyQt6.QtCore import QSize, QRectF
from PyQt6.QtGui import QImage, QColor


class BlendMode(Enum):
    """Blending modes for layer composition"""
    NORMAL = "normal"
    MULTIPLY = "multiply"
    SCREEN = "screen"
    OVERLAY = "overlay"
    ADDITIVE = "additive"
    ALPHA_BLEND = "alpha_blend"


class FilterType(Enum):
    """Texture filtering types"""
    NEAREST = "nearest"
    LINEAR = "linear"
    BILINEAR = "bilinear"
    TRILINEAR = "trilinear"


@dataclass
class RenderTexture:
    """Represents a GPU texture resource"""
    texture_id: int
    width: int
    height: int
    format: str = "RGBA8"
    filter_type: FilterType = FilterType.LINEAR
    
    def size(self) -> QSize:
        return QSize(self.width, self.height)


@dataclass
class RenderLayer:
    """Represents a compositing layer"""
    texture: Optional[RenderTexture]
    transform: QRectF  # Source and destination rectangles
    opacity: float = 1.0
    blend_mode: BlendMode = BlendMode.ALPHA_BLEND
    visible: bool = True
    z_order: int = 0
    
    # Effect parameters
    color_tint: Optional[QColor] = None
    rotation: float = 0.0
    scale_x: float = 1.0
    scale_y: float = 1.0
    
    # Shader parameters
    shader_params: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.shader_params is None:
            self.shader_params = {}
        if self.color_tint is None:
            self.color_tint = QColor(255, 255, 255, 255)


class BaseRenderer(ABC):
    """
    Abstract base class for GPU-based renderers
    
    Provides interface for:
    - Texture management
    - Layer composition
    - Frame rendering
    - Effect application
    """
    
    def __init__(self, width: int = 1920, height: int = 1080):
        self.width = width
        self.height = height
        self._initialized = False
        self._layers: List[RenderLayer] = []
        self._textures: Dict[str, RenderTexture] = {}
        
    @abstractmethod
    def initialize(self) -> bool:
        """Initialize the renderer backend"""
        pass
    
    @abstractmethod
    def cleanup(self):
        """Clean up renderer resources"""
        pass
    
    @abstractmethod
    def resize(self, width: int, height: int):
        """Resize the render target"""
        pass
    
    @abstractmethod
    def create_texture(self, width: int, height: int, 
                      format: str = "RGBA8", 
                      filter_type: FilterType = FilterType.LINEAR) -> RenderTexture:
        """Create a new texture resource"""
        pass
    
    @abstractmethod
    def upload_texture(self, texture: RenderTexture, image: QImage) -> bool:
        """Upload image data to texture"""
        pass
    
    @abstractmethod
    def delete_texture(self, texture: RenderTexture):
        """Delete a texture resource"""
        pass
    
    @abstractmethod
    def create_framebuffer(self, width: int, height: int) -> int:
        """Create a framebuffer object"""
        pass
    
    @abstractmethod
    def bind_framebuffer(self, fbo_id: int):
        """Bind framebuffer for rendering"""
        pass
    
    @abstractmethod
    def clear_framebuffer(self, color: QColor = QColor(0, 0, 0, 0)):
        """Clear the current framebuffer"""
        pass
    
    @abstractmethod
    def draw_layer(self, layer: RenderLayer):
        """Draw a single layer to the current framebuffer"""
        pass
    
    @abstractmethod
    def present_frame(self) -> QImage:
        """Present the rendered frame and return as QImage"""
        pass
    
    @abstractmethod
    def read_framebuffer(self, fbo_id: int) -> QImage:
        """Read framebuffer contents as QImage"""
        pass
    
    # High-level composition methods
    def add_layer(self, layer: RenderLayer):
        """Add a layer to the composition"""
        self._layers.append(layer)
        self._layers.sort(key=lambda l: l.z_order)
    
    def remove_layer(self, layer: RenderLayer):
        """Remove a layer from composition"""
        if layer in self._layers:
            self._layers.remove(layer)
    
    def clear_layers(self):
        """Clear all layers"""
        self._layers.clear()
    
    def render_frame(self, target_fbo: Optional[int] = None) -> QImage:
        """
        Render all layers to target framebuffer
        
        Args:
            target_fbo: Target framebuffer ID, None for default
            
        Returns:
            QImage: Rendered frame
        """
        if target_fbo is not None:
            self.bind_framebuffer(target_fbo)
        
        self.clear_framebuffer()
        
        # Render layers in z-order
        for layer in self._layers:
            if layer.visible and layer.texture:
                self.draw_layer(layer)
        
        if target_fbo is not None:
            return self.read_framebuffer(target_fbo)
        else:
            return self.present_frame()
    
    def get_texture(self, name: str) -> Optional[RenderTexture]:
        """Get named texture"""
        return self._textures.get(name)
    
    def store_texture(self, name: str, texture: RenderTexture):
        """Store texture with name"""
        self._textures[name] = texture
    
    def remove_texture(self, name: str):
        """Remove named texture"""
        if name in self._textures:
            texture = self._textures[name]
            self.delete_texture(texture)
            del self._textures[name]
    
    @property
    def size(self) -> QSize:
        """Get renderer size"""
        return QSize(self.width, self.height)
    
    @property
    def is_initialized(self) -> bool:
        """Check if renderer is initialized"""
        return self._initialized
    
    @property
    def layers(self) -> List[RenderLayer]:
        """Get current layers"""
        return self._layers.copy()
