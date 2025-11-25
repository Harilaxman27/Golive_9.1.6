"""
GoLive Studio - Renderer Module
Cross-platform GPU rendering abstraction
"""

from .base_renderer import BaseRenderer, RenderLayer, RenderTexture

try:
    from .opengl_renderer import OpenGLRenderer
    _HAS_OPENGL = True
except ImportError:
    _HAS_OPENGL = False
    OpenGLRenderer = None

# Platform-specific renderer imports
try:
    from .d3d_renderer import D3DRenderer
    _HAS_D3D = True
except ImportError:
    _HAS_D3D = False
    D3DRenderer = None

def create_renderer(renderer_type='auto', **kwargs) -> BaseRenderer:
    """
    Factory function to create appropriate renderer
    
    Args:
        renderer_type: 'auto', 'opengl', 'd3d'
        **kwargs: Additional renderer arguments
    
    Returns:
        BaseRenderer: Configured renderer instance
    """
    if renderer_type == 'auto':
        # Auto-select best available renderer
        if _HAS_OPENGL:
            try:
                renderer = OpenGLRenderer(**kwargs)
                return renderer
            except Exception as e:
                print(f"OpenGL renderer failed: {e}")
        
        if _HAS_D3D:
            try:
                renderer = D3DRenderer(**kwargs)
                return renderer
            except Exception as e:
                print(f"D3D renderer failed: {e}")
        
        raise RuntimeError("No GPU renderer available")
    
    if renderer_type == 'opengl' and _HAS_OPENGL:
        return OpenGLRenderer(**kwargs)
    elif renderer_type == 'd3d' and _HAS_D3D:
        return D3DRenderer(**kwargs)
    else:
        raise RuntimeError(f"Renderer '{renderer_type}' not available")

def check_gpu_support() -> dict:
    """Check GPU rendering support on current system"""
    return {
        'opengl_available': _HAS_OPENGL,
        'd3d_available': _HAS_D3D,
        'gpu_available': _HAS_OPENGL or _HAS_D3D,
        'recommended_backend': 'opengl' if _HAS_OPENGL else ('d3d' if _HAS_D3D else 'cpu')
    }


__all__ = [
    'BaseRenderer', 'RenderLayer', 'RenderTexture',
    'OpenGLRenderer', 'D3DRenderer', 'create_renderer', 'check_gpu_support'
]
