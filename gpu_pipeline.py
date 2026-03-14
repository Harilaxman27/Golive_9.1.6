"""
Phase 3: Full GPU Pipeline with Zero-Copy
Implements complete GPU-accelerated video pipeline for GoLive Studio
"""

import numpy as np
from PyQt6.QtCore import QObject, pyqtSignal, QThread, QTimer
from PyQt6.QtGui import QImage, QOpenGLContext, QOffscreenSurface, QSurfaceFormat
from PyQt6.QtOpenGL import QOpenGLFramebufferObject, QOpenGLTexture, QOpenGLBuffer
from PyQt6.QtOpenGLWidgets import QOpenGLWidget
from OpenGL import GL as gl
from OpenGL.GL import shaders
import threading
import time
from typing import Optional, Tuple, Dict, List
import ctypes
import weakref


# ============================================================================
# ZERO-COPY GPU PIPELINE
# ============================================================================

class ZeroCopyGPUContext(QObject):
    """
    Manages a shared OpenGL context for zero-copy GPU operations.
    All GPU operations happen on this context to avoid CPU→GPU transfers.
    """
    
    def __init__(self):
        super().__init__()
        self._context: Optional[QOpenGLContext] = None
        self._surface: Optional[QOffscreenSurface] = None
        self._initialized = False
        self._lock = threading.Lock()
        
    def initialize(self):
        """Initialize shared OpenGL context."""
        if self._initialized:
            return True
            
        try:
            # Create format with high performance settings
            format = QSurfaceFormat()
            format.setRenderableType(QSurfaceFormat.RenderableType.OpenGL)
            format.setProfile(QSurfaceFormat.OpenGLContextProfile.CoreProfile)
            format.setVersion(3, 3)
            format.setSwapBehavior(QSurfaceFormat.SwapBehavior.DoubleBuffer)
            format.setDepthBufferSize(0)  # No depth needed for video
            
            # Create context
            self._context = QOpenGLContext()
            self._context.setFormat(format)
            
            if not self._context.create():
                print("[GPU-PIPELINE] Failed to create OpenGL context")
                return False
                
            # Create offscreen surface
            self._surface = QOffscreenSurface()
            self._surface.setFormat(format)
            self._surface.create()
            
            # Make current and verify
            self._context.makeCurrent(self._surface)
            
            # Print OpenGL info
            vendor = gl.glGetString(gl.GL_VENDOR).decode('utf-8')
            renderer = gl.glGetString(gl.GL_RENDERER).decode('utf-8')
            version = gl.glGetString(gl.GL_VERSION).decode('utf-8')
            print(f"[GPU-PIPELINE] OpenGL initialized: {vendor} - {renderer} - {version}")
            
            self._context.doneCurrent()
            self._initialized = True
            return True
            
        except Exception as e:
            print(f"[GPU-PIPELINE] Failed to initialize: {e}")
            return False
            
    def make_current(self):
        """Make this context current for rendering."""
        if self._initialized and self._context and self._surface:
            self._context.makeCurrent(self._surface)
            return True
        return False
        
    def done_current(self):
        """Release this context."""
        if self._initialized and self._context:
            self._context.doneCurrent()
            
    def get_context(self) -> Optional[QOpenGLContext]:
        """Get the OpenGL context for sharing."""
        return self._context
        
    def shutdown(self):
        """Clean up GPU resources."""
        if self._initialized:
            if self._context:
                self._context.makeCurrent(self._surface)
            self._initialized = False
            if self._surface:
                self._surface.destroy()
            if self._context:
                self._context.destroy()


# Global GPU context instance
_gpu_context: Optional[ZeroCopyGPUContext] = None

def get_gpu_context() -> ZeroCopyGPUContext:
    """Get or create global GPU context."""
    global _gpu_context
    if _gpu_context is None:
        _gpu_context = ZeroCopyGPUContext()
    return _gpu_context


# ============================================================================
# GPU VIDEO TEXTURE - Zero-copy video frame storage
# ============================================================================

class GPUVideoTexture(QObject):
    """
    Represents a video frame stored as GPU texture (zero-copy).
    Uses PBO (Pixel Buffer Object) for efficient CPU→GPU transfer.
    """
    
    frame_uploaded = pyqtSignal(int, int)  # (input_number, texture_id)
    
    def __init__(self, width: int, height: int, pixel_format: int = gl.GL_RGBA8):
        super().__init__()
        self._width = width
        self._height = height
        self._pixel_format = pixel_format
        self._texture_id: Optional[int] = None
        self._pbo_id: Optional[int] = None
        self._initialized = False
        
    def initialize(self):
        """Create GPU texture and PBO."""
        if self._initialized:
            return True
            
        context = get_gpu_context()
        if not context.make_current():
            return False
            
        try:
            # Create texture
            self._texture_id = gl.glGenTextures(1)
            gl.glBindTexture(gl.GL_TEXTURE_2D, self._texture_id)
            
            # Set texture parameters
            gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MIN_FILTER, gl.GL_LINEAR)
            gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MAG_FILTER, gl.GL_LINEAR)
            gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_S, gl.GL_CLAMP_TO_EDGE)
            gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_T, gl.GL_CLAMP_TO_EDGE)
            
            # Allocate texture storage
            gl.glTexImage2D(
                gl.GL_TEXTURE_2D, 0, self._pixel_format,
                self._width, self._height, 0,
                gl.GL_RGBA, gl.GL_UNSIGNED_BYTE, None
            )
            
            # Create PBO for fast upload
            self._pbo_id = gl.glGenBuffers(1)
            gl.glBindBuffer(gl.GL_PIXEL_UNPACK_BUFFER, self._pbo_id)
            gl.glBufferData(gl.GL_PIXEL_UNPACK_BUFFER, 
                           self._width * self._height * 4, 
                           None, gl.GL_STREAM_DRAW)
            
            gl.glBindBuffer(gl.GL_PIXEL_UNPACK_BUFFER, 0)
            gl.glBindTexture(gl.GL_TEXTURE_2D, 0)
            
            self._initialized = True
            return True
            
        except Exception as e:
            print(f"[GPU-PIPELINE] Failed to create video texture: {e}")
            return False
        finally:
            context.done_current()
            
    def upload_frame(self, frame_data: bytes) -> bool:
        """
        Upload frame data to GPU texture using PBO (zero-copy path).
        
        Args:
            frame_data: Raw pixel data (RGBA)
            
        Returns:
            True if upload successful
        """
        if not self._initialized:
            if not self.initialize():
                return False
                
        context = get_gpu_context()
        if not context.make_current():
            return False
            
        try:
            # Bind PBO and copy data (CPU → GPU staging)
            gl.glBindBuffer(gl.GL_PIXEL_UNPACK_BUFFER, self._pbo_id)
            gl.glBufferSubData(gl.GL_PIXEL_UNPACK_BUFFER, 0, len(frame_data), frame_data)
            
            # Bind texture and copy from PBO (GPU → GPU, zero-copy)
            gl.glBindTexture(gl.GL_TEXTURE_2D, self._texture_id)
            gl.glTexSubImage2D(
                gl.GL_TEXTURE_2D, 0, 0, 0,
                self._width, self._height,
                gl.GL_RGBA, gl.GL_UNSIGNED_BYTE, ctypes.c_void_p(0)  # From PBO
            )
            
            # Unbind
            gl.glBindTexture(gl.GL_TEXTURE_2D, 0)
            gl.glBindBuffer(gl.GL_PIXEL_UNPACK_BUFFER, 0)
            
            return True
            
        except Exception as e:
            print(f"[GPU-PIPELINE] Frame upload failed: {e}")
            return False
        finally:
            context.done_current()
            
    def get_texture_id(self) -> Optional[int]:
        """Get OpenGL texture ID."""
        return self._texture_id if self._initialized else None
        
    def bind(self, texture_unit: int = 0):
        """Bind texture to specified texture unit."""
        if self._initialized and self._texture_id:
            gl.glActiveTexture(gl.GL_TEXTURE0 + texture_unit)
            gl.glBindTexture(gl.GL_TEXTURE_2D, self._texture_id)
            
    def unbind(self):
        """Unbind texture."""
        gl.glBindTexture(gl.GL_TEXTURE_2D, 0)
        
    def delete(self):
        """Clean up GPU resources."""
        if not self._initialized:
            return
            
        context = get_gpu_context()
        if context.make_current():
            if self._texture_id:
                gl.glDeleteTextures(1, [self._texture_id])
            if self._pbo_id:
                gl.glDeleteBuffers(1, [self._pbo_id])
            context.done_current()
            
        self._initialized = False


# ============================================================================
# GPU SCALER - Hardware-accelerated scaling
# ============================================================================

class GPUScaler(QObject):
    """
    Scales video frames on GPU using bilinear filtering.
    Much faster than CPU QImage.scaled().
    """
    
    def __init__(self, input_width: int, input_height: int, 
                 output_width: int, output_height: int):
        super().__init__()
        self._input_width = input_width
        self._input_height = input_height
        self._output_width = output_width
        self._output_height = output_height
        self._fbo: Optional[QOpenGLFramebufferObject] = None
        self._shader: Optional[int] = None
        self._vao: Optional[int] = None
        self._vbo: Optional[int] = None
        self._initialized = False
        
    def initialize(self):
        """Initialize FBO and shader."""
        if self._initialized:
            return True
            
        context = get_gpu_context()
        if not context.make_current():
            return False
            
        try:
            # Create FBO for output
            self._fbo = QOpenGLFramebufferObject(self._output_width, self._output_height)
            
            # Create simple pass-through shader
            vertex_shader = shaders.compileShader("""
                #version 330 core
                layout(location = 0) in vec2 position;
                layout(location = 1) in vec2 texCoord;
                out vec2 vTexCoord;
                void main() {
                    gl_Position = vec4(position, 0.0, 1.0);
                    vTexCoord = texCoord;
                }
            """, gl.GL_VERTEX_SHADER)
            
            fragment_shader = shaders.compileShader("""
                #version 330 core
                in vec2 vTexCoord;
                out vec4 fragColor;
                uniform sampler2D inputTexture;
                void main() {
                    fragColor = texture(inputTexture, vTexCoord);
                }
            """, gl.GL_FRAGMENT_SHADER)
            
            self._shader = shaders.compileProgram(vertex_shader, fragment_shader)
            
            # Create VAO/VBO for fullscreen quad
            vertices = np.array([
                -1.0, -1.0, 0.0, 0.0,
                 1.0, -1.0, 1.0, 0.0,
                 1.0,  1.0, 1.0, 1.0,
                -1.0,  1.0, 0.0, 1.0,
            ], dtype=np.float32)
            
            self._vao = gl.glGenVertexArrays(1)
            self._vbo = gl.glGenBuffers(1)
            
            gl.glBindVertexArray(self._vao)
            gl.glBindBuffer(gl.GL_ARRAY_BUFFER, self._vbo)
            gl.glBufferData(gl.GL_ARRAY_BUFFER, vertices.nbytes, vertices, gl.GL_STATIC_DRAW)
            
            gl.glVertexAttribPointer(0, 2, gl.GL_FLOAT, False, 16, None)
            gl.glEnableVertexAttribArray(0)
            gl.glVertexAttribPointer(1, 2, gl.GL_FLOAT, False, 16, ctypes.c_void_p(8))
            gl.glEnableVertexAttribArray(1)
            
            gl.glBindVertexArray(0)
            
            self._initialized = True
            return True
            
        except Exception as e:
            print(f"[GPU-PIPELINE] Failed to initialize scaler: {e}")
            return False
        finally:
            context.done_current()
            
    def scale(self, input_texture_id: int) -> Optional[int]:
        """
        Scale input texture to output size.
        
        Args:
            input_texture_id: Source texture ID
            
        Returns:
            Output texture ID or None if failed
        """
        if not self._initialized:
            if not self.initialize():
                return None
                
        context = get_gpu_context()
        if not context.make_current():
            return None
            
        try:
            # Bind FBO
            self._fbo.bind()
            
            # Set viewport
            gl.glViewport(0, 0, self._output_width, self._output_height)
            gl.glClear(gl.GL_COLOR_BUFFER_BIT)
            
            # Use shader
            gl.glUseProgram(self._shader)
            
            # Bind input texture
            gl.glActiveTexture(gl.GL_TEXTURE0)
            gl.glBindTexture(gl.GL_TEXTURE_2D, input_texture_id)
            gl.glUniform1i(gl.glGetUniformLocation(self._shader, "inputTexture"), 0)
            
            # Draw quad
            gl.glBindVertexArray(self._vao)
            gl.glDrawArrays(gl.GL_TRIANGLE_FAN, 0, 4)
            
            # Cleanup
            gl.glBindVertexArray(0)
            gl.glBindTexture(gl.GL_TEXTURE_2D, 0)
            gl.glUseProgram(0)
            self._fbo.release()
            
            return self._fbo.texture()
            
        except Exception as e:
            print(f"[GPU-PIPELINE] Scaling failed: {e}")
            return None
        finally:
            context.done_current()
            
    def delete(self):
        """Clean up GPU resources."""
        if not self._initialized:
            return
            
        context = get_gpu_context()
        if context.make_current():
            if self._fbo:
                self._fbo.destroy()
            if self._shader:
                gl.glDeleteProgram(self._shader)
            if self._vao:
                gl.glDeleteVertexArrays(1, [self._vao])
            if self._vbo:
                gl.glDeleteBuffers(1, [self._vbo])
            context.done_current()
            
        self._initialized = False


# ============================================================================
# GPU PIPELINE MANAGER - High-level interface
# ============================================================================

class GPUPipelineManager(QObject):
    """
    Manages the complete GPU video pipeline.
    Handles texture upload, scaling, and compositing on GPU.
    """
    
    frame_processed = pyqtSignal(int, int)  # (input_number, output_texture_id)
    
    def __init__(self):
        super().__init__()
        self._input_textures: Dict[int, GPUVideoTexture] = {}
        self._scalers: Dict[Tuple[int, int, int, int], GPUScaler] = {}
        self._lock = threading.Lock()
        self._initialized = False
        
    def initialize(self):
        """Initialize GPU pipeline."""
        if self._initialized:
            return True
            
        context = get_gpu_context()
        if not context.initialize():
            print("[GPU-PIPELINE] Failed to initialize GPU context")
            return False
            
        self._initialized = True
        print("[GPU-PIPELINE] Pipeline manager initialized")
        return True
        
    def upload_frame(self, input_number: int, frame: QImage) -> bool:
        """
        Upload QImage frame to GPU texture.
        
        Args:
            input_number: Camera input number
            frame: QImage frame to upload
            
        Returns:
            True if successful
        """
        if not self._initialized or frame is None or frame.isNull():
            return False
            
        try:
            with self._lock:
                # Get or create texture for this input
                key = input_number
                if key not in self._input_textures:
                    self._input_textures[key] = GPUVideoTexture(
                        frame.width(), frame.height()
                    )
                
                texture = self._input_textures[key]
                
                # Check if size changed
                if texture._width != frame.width() or texture._height != frame.height():
                    texture.delete()
                    self._input_textures[key] = GPUVideoTexture(
                        frame.width(), frame.height()
                    )
                    texture = self._input_textures[key]
                
                # Convert to RGBA if needed
                if frame.format() != QImage.Format.Format_RGBA8888:
                    frame = frame.convertToFormat(QImage.Format.Format_RGBA8888)
                
                # Upload frame data
                bits = frame.bits()
                if bits:
                    success = texture.upload_frame(bits)
                    if success:
                        self.frame_processed.emit(input_number, texture.get_texture_id())
                    return success
                    
            return False
            
        except Exception as e:
            print(f"[GPU-PIPELINE] Upload failed: {e}")
            return False
            
    def scale_frame(self, input_number: int, target_width: int, target_height: int) -> Optional[int]:
        """
        Scale frame to target resolution on GPU.
        
        Args:
            input_number: Input number
            target_width: Output width
            target_height: Output height
            
        Returns:
            Output texture ID or None
        """
        if not self._initialized:
            return None
            
        try:
            with self._lock:
                # Get input texture
                if input_number not in self._input_textures:
                    return None
                    
                input_texture = self._input_textures[input_number]
                input_tex_id = input_texture.get_texture_id()
                if input_tex_id is None:
                    return None
                
                # Get or create scaler
                scaler_key = (input_number, target_width, target_height)
                if scaler_key not in self._scalers:
                    self._scalers[scaler_key] = GPUScaler(
                        input_texture._width, input_texture._height,
                        target_width, target_height
                    )
                
                scaler = self._scalers[scaler_key]
                return scaler.scale(input_tex_id)
                
        except Exception as e:
            print(f"[GPU-PIPELINE] Scale failed: {e}")
            return None
            
    def get_texture_id(self, input_number: int) -> Optional[int]:
        """Get texture ID for input."""
        with self._lock:
            if input_number in self._input_textures:
                return self._input_textures[input_number].get_texture_id()
        return None
        
    def cleanup(self):
        """Clean up old resources."""
        # Could add LRU eviction here
        pass
        
    def shutdown(self):
        """Shut down pipeline and clean up all resources."""
        if not self._initialized:
            return
            
        with self._lock:
            for texture in self._input_textures.values():
                texture.delete()
            self._input_textures.clear()
            
            for scaler in self._scalers.values():
                scaler.delete()
            self._scalers.clear()
            
        self._initialized = False
        print("[GPU-PIPELINE] Pipeline shut down")


# Global pipeline manager instance
_gpu_pipeline: Optional[GPUPipelineManager] = None

def get_gpu_pipeline() -> GPUPipelineManager:
    """Get or create global GPU pipeline."""
    global _gpu_pipeline
    if _gpu_pipeline is None:
        _gpu_pipeline = GPUPipelineManager()
    return _gpu_pipeline

def initialize_gpu_pipeline():
    """Initialize full GPU pipeline."""
    print("[GPU-PIPELINE] Initializing Phase 3: Full GPU Pipeline...")
    
    pipeline = get_gpu_pipeline()
    if pipeline.initialize():
        print("[GPU-PIPELINE] ✅ Phase 3 GPU Pipeline ready")
    else:
        print("[GPU-PIPELINE] ⚠️ GPU Pipeline unavailable, falling back to CPU")
        
def shutdown_gpu_pipeline():
    """Shut down GPU pipeline."""
    global _gpu_pipeline
    if _gpu_pipeline:
        _gpu_pipeline.shutdown()
        _gpu_pipeline = None
        
    # Also shut down GPU context
    global _gpu_context
    if _gpu_context:
        _gpu_context.shutdown()
        _gpu_context = None
