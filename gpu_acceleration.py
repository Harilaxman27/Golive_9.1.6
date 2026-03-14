"""
GPU Acceleration Module for GoLive Studio
Handles GPU texture upload, YUV→RGB conversion, and GPU-based compositing
"""

import numpy as np
from PyQt6.QtCore import QObject, pyqtSignal, QThread
from PyQt6.QtGui import QImage, QOpenGLContext, QOffscreenSurface
from PyQt6.QtOpenGL import QOpenGLFramebufferObject, QOpenGLTexture
from PyQt6.QtOpenGLWidgets import QOpenGLWidget
from OpenGL import GL as gl
from OpenGL.GL import shaders
import threading
import time
from typing import Optional, Tuple, Dict
import weakref


# YUV to RGB conversion shader (NV12 format - most common for cameras)
YUV_TO_RGB_VERTEX_SHADER = """
#version 330 core
layout(location = 0) in vec2 position;
layout(location = 1) in vec2 texCoord;
out vec2 vTexCoord;

void main() {
    gl_Position = vec4(position, 0.0, 1.0);
    vTexCoord = texCoord;
}
"""

YUV_TO_RGB_FRAGMENT_SHADER = """
#version 330 core
in vec2 vTexCoord;
out vec4 fragColor;

uniform sampler2D yTexture;
uniform sampler2D uvTexture;

// BT.601 conversion matrix (standard for SD video)
const mat3 yuvToRgb = mat3(
    1.0,    1.0,    1.0,
    0.0,   -0.39465, 2.03211,
    1.13983,-0.58060, 0.0
);

void main() {
    float y = texture(yTexture, vTexCoord).r;
    vec2 uv = texture(uvTexture, vTexCoord).rg - 0.5;
    
    vec3 yuv = vec3(y, uv.x, uv.y);
    vec3 rgb = yuvToRgb * yuv;
    
    fragColor = vec4(rgb, 1.0);
}
"""

# Simple pass-through shader for RGB frames
RGB_VERTEX_SHADER = """
#version 330 core
layout(location = 0) in vec2 position;
layout(location = 1) in vec2 texCoord;
out vec2 vTexCoord;

void main() {
    gl_Position = vec4(position, 0.0, 1.0);
    vTexCoord = texCoord;
}
"""

RGB_FRAGMENT_SHADER = """
#version 330 core
in vec2 vTexCoord;
out vec4 fragColor;

uniform sampler2D rgbTexture;

void main() {
    fragColor = texture(rgbTexture, vTexCoord);
}
"""


class GPUTextureManager(QObject):
    """
    Manages GPU textures for efficient frame upload and reuse.
    Uploads QImage frames as GPU textures to avoid CPU→GPU copy every frame.
    """
    
    frame_uploaded = pyqtSignal(int, int)  # (input_number, texture_id)
    
    def __init__(self, max_textures: int = 10):
        super().__init__()
        self._textures: Dict[int, Dict] = {}  # input_number -> texture data
        self._max_textures = max_textures
        self._lock = threading.Lock()
        self._initialized = False
        self._context: Optional[QOpenGLContext] = None
        self._surface: Optional[QOffscreenSurface] = None
        
    def initialize(self):
        """Initialize OpenGL context for offscreen rendering."""
        if self._initialized:
            return
            
        try:
            # Create OpenGL context
            self._context = QOpenGLContext()
            format = QOpenGLContext.globalShareContext().format() if QOpenGLContext.globalShareContext() else None
            if format:
                self._context.setFormat(format)
            self._context.create()
            
            # Create offscreen surface
            self._surface = QOffscreenSurface()
            if format:
                self._surface.setFormat(format)
            self._surface.create()
            
            self._initialized = True
            print("[GPU] Texture manager initialized successfully")
        except Exception as e:
            print(f"[GPU] Failed to initialize texture manager: {e}")
            
    def upload_frame(self, input_number: int, frame: QImage) -> Optional[int]:
        """
        Upload QImage frame as GPU texture.
        
        Args:
            input_number: Camera input number
            frame: QImage frame to upload
            
        Returns:
            OpenGL texture ID or None if upload failed
        """
        if not self._initialized or frame is None or frame.isNull():
            return None
            
        try:
            with self._lock:
                # Make context current
                self._context.makeCurrent(self._surface)
                
                # Check if we have existing texture for this input
                if input_number in self._textures:
                    tex_data = self._textures[input_number]
                    # Check if size changed
                    if tex_data['width'] != frame.width() or tex_data['height'] != frame.height():
                        # Delete old texture
                        gl.glDeleteTextures(1, [tex_data['id']])
                        del self._textures[input_number]
                
                # Create new texture if needed
                if input_number not in self._textures:
                    texture_id = gl.glGenTextures(1)
                    gl.glBindTexture(gl.GL_TEXTURE_2D, texture_id)
                    
                    # Set texture parameters
                    gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MIN_FILTER, gl.GL_LINEAR)
                    gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MAG_FILTER, gl.GL_LINEAR)
                    gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_S, gl.GL_CLAMP_TO_EDGE)
                    gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_T, gl.GL_CLAMP_TO_EDGE)
                    
                    # Allocate texture storage
                    gl.glTexImage2D(
                        gl.GL_TEXTURE_2D, 0, gl.GL_RGBA8,
                        frame.width(), frame.height(), 0,
                        gl.GL_RGBA, gl.GL_UNSIGNED_BYTE, None
                    )
                    
                    self._textures[input_number] = {
                        'id': texture_id,
                        'width': frame.width(),
                        'height': frame.height(),
                        'last_used': time.time()
                    }
                else:
                    texture_id = self._textures[input_number]['id']
                    gl.glBindTexture(gl.GL_TEXTURE_2D, texture_id)
                
                # Upload pixel data
                # Convert QImage to format suitable for OpenGL
                if frame.format() != QImage.Format.Format_RGBA8888:
                    frame = frame.convertToFormat(QImage.Format.Format_RGBA8888)
                
                # Get raw pointer to pixel data
                bits = frame.bits()
                if bits:
                    gl.glTexSubImage2D(
                        gl.GL_TEXTURE_2D, 0, 0, 0,
                        frame.width(), frame.height(),
                        gl.GL_RGBA, gl.GL_UNSIGNED_BYTE, bits
                    )
                
                # Update last used time
                self._textures[input_number]['last_used'] = time.time()
                
                # Unbind texture
                gl.glBindTexture(gl.GL_TEXTURE_2D, 0)
                
                # Done with context
                self._context.doneCurrent()
                
                self.frame_uploaded.emit(input_number, texture_id)
                return texture_id
                
        except Exception as e:
            print(f"[GPU] Failed to upload frame for Input-{input_number}: {e}")
            return None
            
    def get_texture(self, input_number: int) -> Optional[int]:
        """Get texture ID for input if available."""
        with self._lock:
            if input_number in self._textures:
                return self._textures[input_number]['id']
        return None
        
    def cleanup_old_textures(self, max_age_seconds: float = 5.0):
        """Remove textures not used for specified time."""
        with self._lock:
            now = time.time()
            to_delete = []
            for input_number, tex_data in self._textures.items():
                if now - tex_data['last_used'] > max_age_seconds:
                    to_delete.append(input_number)
                    
            for input_number in to_delete:
                tex_data = self._textures[input_number]
                self._context.makeCurrent(self._surface)
                gl.glDeleteTextures(1, [tex_data['id']])
                self._context.doneCurrent()
                del self._textures[input_number]
                
    def shutdown(self):
        """Clean up all GPU resources."""
        with self._lock:
            if self._context and self._surface:
                self._context.makeCurrent(self._surface)
                for tex_data in self._textures.values():
                    gl.glDeleteTextures(1, [tex_data['id']])
                self._context.doneCurrent()
                
            self._textures.clear()
            self._initialized = False
            
            if self._surface:
                self._surface.destroy()
                self._surface = None
            if self._context:
                self._context.destroy()
                self._context = None


class GPUShaderProgram:
    """
    Compiled OpenGL shader program for YUV→RGB or RGB rendering.
    """
    
    def __init__(self, vertex_source: str, fragment_source: str):
        self._program = None
        self._vertex_source = vertex_source
        self._fragment_source = fragment_source
        self._compiled = False
        
    def compile(self):
        """Compile shader program."""
        try:
            vertex_shader = shaders.compileShader(self._vertex_source, gl.GL_VERTEX_SHADER)
            fragment_shader = shaders.compileShader(self._fragment_source, gl.GL_FRAGMENT_SHADER)
            
            self._program = shaders.compileProgram(vertex_shader, fragment_shader)
            self._compiled = True
            
            # Clean up individual shaders
            gl.glDeleteShader(vertex_shader)
            gl.glDeleteShader(fragment_shader)
            
            return True
        except Exception as e:
            print(f"[GPU] Shader compilation failed: {e}")
            return False
            
    def use(self):
        """Activate shader program."""
        if self._compiled and self._program:
            gl.glUseProgram(self._program)
            
    def get_uniform_location(self, name: str) -> int:
        """Get uniform variable location."""
        if self._compiled and self._program:
            return gl.glGetUniformLocation(self._program, name)
        return -1
        
    def set_int(self, name: str, value: int):
        """Set integer uniform."""
        loc = self.get_uniform_location(name)
        if loc >= 0:
            gl.glUniform1i(loc, value)
            
    def delete(self):
        """Delete shader program."""
        if self._program:
            gl.glDeleteProgram(self._program)
            self._program = None
            self._compiled = False


class GPUFrameConverter:
    """
    Converts camera frames (YUV/NV12) to RGB on GPU using shaders.
    Much faster than CPU conversion.
    """
    
    def __init__(self):
        self._yuv_shader: Optional[GPUShaderProgram] = None
        self._rgb_shader: Optional[GPUShaderProgram] = None
        self._initialized = False
        self._fbo: Optional[QOpenGLFramebufferObject] = None
        
    def initialize(self):
        """Initialize shader programs."""
        if self._initialized:
            return
            
        try:
            # Compile YUV conversion shader
            self._yuv_shader = GPUShaderProgram(YUV_TO_RGB_VERTEX_SHADER, YUV_TO_RGB_FRAGMENT_SHADER)
            if not self._yuv_shader.compile():
                print("[GPU] Failed to compile YUV shader")
                return
                
            # Compile RGB pass-through shader
            self._rgb_shader = GPUShaderProgram(RGB_VERTEX_SHADER, RGB_FRAGMENT_SHADER)
            if not self._rgb_shader.compile():
                print("[GPU] Failed to compile RGB shader")
                return
                
            self._initialized = True
            print("[GPU] Frame converter initialized successfully")
        except Exception as e:
            print(f"[GPU] Failed to initialize frame converter: {e}")
            
    def convert_yuv_to_rgb(self, y_texture: int, uv_texture: int, width: int, height: int) -> Optional[int]:
        """
        Convert YUV textures to RGB using GPU shader.
        
        Args:
            y_texture: OpenGL texture ID for Y plane
            uv_texture: OpenGL texture ID for UV plane
            width: Output width
            height: Output height
            
        Returns:
            FBO texture ID containing RGB result
        """
        if not self._initialized:
            return None
            
        try:
            # Ensure FBO is created with correct size
            if self._fbo is None or self._fbo.width() != width or self._fbo.height() != height:
                if self._fbo:
                    self._fbo.destroy()
                self._fbo = QOpenGLFramebufferObject(width, height)
                
            # Bind FBO for rendering
            self._fbo.bind()
            
            # Set viewport
            gl.glViewport(0, 0, width, height)
            
            # Clear
            gl.glClear(gl.GL_COLOR_BUFFER_BIT)
            
            # Use YUV shader
            self._yuv_shader.use()
            
            # Bind Y texture to unit 0
            gl.glActiveTexture(gl.GL_TEXTURE0)
            gl.glBindTexture(gl.GL_TEXTURE_2D, y_texture)
            self._yuv_shader.set_int("yTexture", 0)
            
            # Bind UV texture to unit 1
            gl.glActiveTexture(gl.GL_TEXTURE1)
            gl.glBindTexture(gl.GL_TEXTURE_2D, uv_texture)
            self._yuv_shader.set_int("uvTexture", 1)
            
            # Draw fullscreen quad
            self._draw_quad()
            
            # Unbind
            gl.glBindTexture(gl.GL_TEXTURE_2D, 0)
            self._fbo.release()
            
            # Return FBO texture ID
            return self._fbo.texture()
            
        except Exception as e:
            print(f"[GPU] YUV conversion failed: {e}")
            return None
            
    def _draw_quad(self):
        """Draw fullscreen quad for shader processing."""
        # Simple quad vertices (position + texCoord)
        vertices = np.array([
            -1.0, -1.0, 0.0, 0.0,  # Bottom-left
             1.0, -1.0, 1.0, 0.0,  # Bottom-right
             1.0,  1.0, 1.0, 1.0,  # Top-right
            -1.0,  1.0, 0.0, 1.0,  # Top-left
        ], dtype=np.float32)
        
        # Create and bind VAO/VBO
        vao = gl.glGenVertexArrays(1)
        vbo = gl.glGenBuffers(1)
        
        gl.glBindVertexArray(vao)
        gl.glBindBuffer(gl.GL_ARRAY_BUFFER, vbo)
        gl.glBufferData(gl.GL_ARRAY_BUFFER, vertices.nbytes, vertices, gl.GL_STATIC_DRAW)
        
        # Position attribute (location 0)
        gl.glVertexAttribPointer(0, 2, gl.GL_FLOAT, False, 4 * 4, None)
        gl.glEnableVertexAttribArray(0)
        
        # TexCoord attribute (location 1)
        gl.glVertexAttribPointer(1, 2, gl.GL_FLOAT, False, 4 * 4, ctypes.c_void_p(2 * 4))
        gl.glEnableVertexAttribArray(1)
        
        # Draw
        gl.glDrawArrays(gl.GL_TRIANGLE_FAN, 0, 4)
        
        # Cleanup
        gl.glDisableVertexAttribArray(0)
        gl.glDisableVertexAttribArray(1)
        gl.glBindBuffer(gl.GL_ARRAY_BUFFER, 0)
        gl.glBindVertexArray(0)
        gl.glDeleteBuffers(1, [vbo])
        gl.glDeleteVertexArrays(1, [vao])
        
    def shutdown(self):
        """Clean up GPU resources."""
        if self._yuv_shader:
            self._yuv_shader.delete()
            self._yuv_shader = None
        if self._rgb_shader:
            self._rgb_shader.delete()
            self._rgb_shader = None
        if self._fbo:
            self._fbo.destroy()
            self._fbo = None
        self._initialized = False


# Global GPU manager instance
_gpu_texture_manager: Optional[GPUTextureManager] = None
_gpu_frame_converter: Optional[GPUFrameConverter] = None

def get_gpu_texture_manager() -> GPUTextureManager:
    """Get or create global GPU texture manager."""
    global _gpu_texture_manager
    if _gpu_texture_manager is None:
        _gpu_texture_manager = GPUTextureManager()
    return _gpu_texture_manager

def get_gpu_frame_converter() -> GPUFrameConverter:
    """Get or create global GPU frame converter."""
    global _gpu_frame_converter
    if _gpu_frame_converter is None:
        _gpu_frame_converter = GPUFrameConverter()
    return _gpu_frame_converter

def initialize_gpu_acceleration():
    """Initialize all GPU acceleration systems."""
    print("[GPU] Initializing GPU acceleration...")
    
    tex_manager = get_gpu_texture_manager()
    tex_manager.initialize()
    
    frame_converter = get_gpu_frame_converter()
    frame_converter.initialize()
    
    print("[GPU] GPU acceleration initialized")
    
def shutdown_gpu_acceleration():
    """Shutdown all GPU acceleration systems."""
    global _gpu_texture_manager, _gpu_frame_converter
    
    print("[GPU] Shutting down GPU acceleration...")
    
    if _gpu_texture_manager:
        _gpu_texture_manager.shutdown()
        _gpu_texture_manager = None
        
    if _gpu_frame_converter:
        _gpu_frame_converter.shutdown()
        _gpu_frame_converter = None
        
    print("[GPU] GPU acceleration shut down")
