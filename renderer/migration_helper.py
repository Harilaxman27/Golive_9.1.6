"""
GoLive Studio - Migration Helper
Helps transition from CPU-based graphics_output.py to GPU-based renderer
"""

from typing import Optional, Union
from PyQt6.QtCore import QSize
from PyQt6.QtGui import QImage

# Import both old and new implementations
try:
    from .gpu_graphics_output import GPUGraphicsOutputWidget
    _HAS_GPU = True
except ImportError as e:
    print(f"GPU renderer not available: {e}")
    _HAS_GPU = False
    GPUGraphicsOutputWidget = None

try:
    from graphics_output import GraphicsOutputWidget as CPUGraphicsOutputWidget
    _HAS_CPU = True
except ImportError:
    _HAS_CPU = False
    CPUGraphicsOutputWidget = None


def GraphicsOutputWidget(parent=None, use_gpu=True, renderer_backend='auto'):
    """
    Factory function that returns either GPU or CPU graphics output widget
    Provides seamless migration path from old to new renderer
    """
    # Check platform GPU support first to avoid creating a GPU widget that cannot init
    gpu_supported = False
    try:
        from . import check_gpu_support as _check_gpu_support
        info = _check_gpu_support()
        gpu_supported = bool(info.get('opengl_available') or info.get('d3d_available'))
    except Exception:
        gpu_supported = False

    # Try GPU renderer first only if requested and supported
    if use_gpu and _HAS_GPU and gpu_supported:
        try:
            widget = GPUGraphicsOutputWidget(parent, renderer_backend)
            print("Using GPU-accelerated renderer")
            return widget
        except Exception as e:
            print(f"GPU renderer failed, falling back to CPU: {e}")
            # fall through to CPU

    # Fallback to CPU renderer
    if _HAS_CPU:
        widget = CPUGraphicsOutputWidget(parent)
        print("Using CPU renderer")
        return widget
    else:
        raise RuntimeError("No renderer available")


def create_graphics_output_widget(parent=None, prefer_gpu=True, renderer_backend='auto'):
    """
    Factory function to create graphics output widget
    
    Args:
        parent: Parent widget
        prefer_gpu: Whether to prefer GPU rendering
        renderer_backend: 'auto', 'opengl', 'd3d'
    
    Returns:
        GraphicsOutputWidget: Configured widget
    """
    try:
        return GraphicsOutputWidget(parent, prefer_gpu, renderer_backend)
    except Exception as e:
        print(f"Failed to create graphics output widget: {e}")
        # Force CPU fallback
        if _HAS_CPU:
            return CPUGraphicsOutputWidget(parent)
        else:
            raise RuntimeError("No graphics output widget available")


def check_gpu_support() -> dict:
    """
    Check GPU rendering support on current system
    
    Returns:
        dict: Support information
    """
    support_info = {
        'gpu_available': _HAS_GPU,
        'cpu_available': _HAS_CPU,
        'opengl_available': False,
        'd3d_available': False,
        'recommended_backend': 'cpu'
    }
    
    if _HAS_GPU:
        try:
            from . import create_renderer
            
            # Test OpenGL
            try:
                renderer = create_renderer('opengl')
                support_info['opengl_available'] = True
                support_info['recommended_backend'] = 'opengl'
                renderer.cleanup()
            except Exception:
                pass
            
            # Test D3D (Windows only)
            try:
                renderer = create_renderer('d3d')
                support_info['d3d_available'] = True
                support_info['recommended_backend'] = 'd3d'
                renderer.cleanup()
            except Exception:
                pass
                
        except Exception:
            pass
    
    return support_info
