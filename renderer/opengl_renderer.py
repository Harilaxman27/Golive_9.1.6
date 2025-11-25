"""
GoLive Studio - OpenGL Renderer Implementation
Cross-platform GPU rendering using OpenGL
"""

import sys
from typing import Optional, Dict, Tuple
import numpy as np

from PyQt6.QtCore import QSize, QRectF
from PyQt6.QtGui import QImage, QColor, QOpenGLContext, QSurfaceFormat
from PyQt6.QtOpenGL import QOpenGLFramebufferObject, QOpenGLShaderProgram, QOpenGLTexture
from PyQt6.QtOpenGLWidgets import QOpenGLWidget

try:
    from OpenGL import GL as gl
    from OpenGL.GL import shaders
    _HAS_OPENGL = True
except ImportError:
    _HAS_OPENGL = False
    gl = None

from .base_renderer import BaseRenderer, RenderLayer, RenderTexture, BlendMode, FilterType


class OpenGLRenderer(BaseRenderer):
    """
    OpenGL-based renderer implementation
    Provides GPU-accelerated compositing using OpenGL
    """
    
    # Vertex shader for basic texture rendering
    VERTEX_SHADER = """
    #version 330 core
    layout (location = 0) in vec3 aPos;
    layout (location = 1) in vec2 aTexCoord;
    
    out vec2 TexCoord;
    
    uniform mat4 transform;
    uniform mat4 projection;
    
    void main() {
        gl_Position = projection * transform * vec4(aPos, 1.0);
        TexCoord = aTexCoord;
    }
    """
    
    # Fragment shader for basic texture rendering
    FRAGMENT_SHADER = """
    #version 330 core
    out vec4 FragColor;
    
    in vec2 TexCoord;
    
    uniform sampler2D ourTexture;
    uniform float opacity;
    uniform vec4 colorTint;
    uniform int blendMode;
    
    void main() {
        vec4 texColor = texture(ourTexture, TexCoord);
        texColor *= colorTint;
        texColor.a *= opacity;
        
        // Apply blend mode (simplified)
        FragColor = texColor;
    }
    """
    
    def __init__(self, width: int = 1920, height: int = 1080, widget: Optional[QOpenGLWidget] = None):
        super().__init__(width, height)
        
        if not _HAS_OPENGL:
            raise RuntimeError("OpenGL not available. Install PyOpenGL: pip install PyOpenGL PyOpenGL_accelerate")
        
        self.widget = widget
        self.context: Optional[QOpenGLContext] = None
        self.shader_program: Optional[QOpenGLShaderProgram] = None
        self.main_fbo: Optional[QOpenGLFramebufferObject] = None
        
        # OpenGL resources
        self.vao = None
        self.vbo = None
        self.ebo = None
        
        # Texture cache
        self._gl_textures: Dict[int, QOpenGLTexture] = {}
        
    def initialize(self) -> bool:
        """Initialize OpenGL renderer"""
        try:
            # Check if OpenGL is available
            if not _HAS_OPENGL:
                print("OpenGL not available - PyOpenGL not installed")
                return False
            
            if self.widget:
                try:
                    self.widget.makeCurrent()
                    self.context = self.widget.context()
                    if not self.context or not self.context.isValid():
                        print("Invalid OpenGL context from widget")
                        return False
                except Exception as e:
                    print(f"Failed to get OpenGL context from widget: {e}")
                    return False
            else:
                # Create offscreen context
                try:
                    self.context = QOpenGLContext()
                    format = QSurfaceFormat()
                    format.setVersion(3, 3)
                    format.setProfile(QSurfaceFormat.OpenGLContextProfile.CoreProfile)
                    self.context.setFormat(format)
                    if not self.context.create():
                        print("Failed to create OpenGL context")
                        return False
                except Exception as e:
                    print(f"Failed to create offscreen OpenGL context: {e}")
                    return False
            
            # Try to initialize OpenGL state
            try:
                self._init_opengl()
                self._init_shaders()
                self._init_geometry()
                self._init_framebuffer()
            except Exception as e:
                print(f"OpenGL state initialization failed: {e}")
                return False
            
            self._initialized = True
            return True
            
        except Exception as e:
            print(f"OpenGL initialization failed: {e}")
            return False
    
    def _init_opengl(self):
        """Initialize OpenGL state"""
        gl.glEnable(gl.GL_BLEND)
        gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)
        gl.glEnable(gl.GL_DEPTH_TEST)
        gl.glDepthFunc(gl.GL_LEQUAL)
        
        # Set viewport
        gl.glViewport(0, 0, self.width, self.height)
        
    def _init_shaders(self):
        """Initialize shader programs"""
        self.shader_program = QOpenGLShaderProgram()
        
        if not self.shader_program.addShaderFromSourceCode(
            QOpenGLShaderProgram.ShaderType.Vertex, self.VERTEX_SHADER):
            raise RuntimeError("Failed to compile vertex shader")
            
        if not self.shader_program.addShaderFromSourceCode(
            QOpenGLShaderProgram.ShaderType.Fragment, self.FRAGMENT_SHADER):
            raise RuntimeError("Failed to compile fragment shader")
            
        if not self.shader_program.link():
            raise RuntimeError("Failed to link shader program")
    
    def _init_geometry(self):
        """Initialize geometry buffers"""
        # Quad vertices (position + texture coordinates)
        vertices = np.array([
            # positions     # texture coords
            -1.0, -1.0, 0.0,  0.0, 0.0,  # bottom left
             1.0, -1.0, 0.0,  1.0, 0.0,  # bottom right
             1.0,  1.0, 0.0,  1.0, 1.0,  # top right
            -1.0,  1.0, 0.0,  0.0, 1.0   # top left
        ], dtype=np.float32)
        
        indices = np.array([
            0, 1, 2,  # first triangle
            2, 3, 0   # second triangle
        ], dtype=np.uint32)
        
        # Generate and bind VAO
        self.vao = gl.glGenVertexArrays(1)
        gl.glBindVertexArray(self.vao)
        
        # Generate and bind VBO
        self.vbo = gl.glGenBuffers(1)
        gl.glBindBuffer(gl.GL_ARRAY_BUFFER, self.vbo)
        gl.glBufferData(gl.GL_ARRAY_BUFFER, vertices.nbytes, vertices, gl.GL_STATIC_DRAW)
        
        # Generate and bind EBO
        self.ebo = gl.glGenBuffers(1)
        gl.glBindBuffer(gl.GL_ELEMENT_ARRAY_BUFFER, self.ebo)
        gl.glBufferData(gl.GL_ELEMENT_ARRAY_BUFFER, indices.nbytes, indices, gl.GL_STATIC_DRAW)
        
        # Position attribute
        gl.glVertexAttribPointer(0, 3, gl.GL_FLOAT, gl.GL_FALSE, 5 * 4, None)
        gl.glEnableVertexAttribArray(0)
        
        # Texture coordinate attribute
        gl.glVertexAttribPointer(1, 2, gl.GL_FLOAT, gl.GL_FALSE, 5 * 4, gl.ctypes.c_void_p(3 * 4))
        gl.glEnableVertexAttribArray(1)
        
        gl.glBindVertexArray(0)
    
    def _init_framebuffer(self):
        """Initialize main framebuffer"""
        self.main_fbo = QOpenGLFramebufferObject(self.width, self.height)
        if not self.main_fbo.isValid():
            raise RuntimeError("Failed to create main framebuffer")
    
    def cleanup(self):
        """Clean up OpenGL resources"""
        if self.vao:
            gl.glDeleteVertexArrays(1, [self.vao])
        if self.vbo:
            gl.glDeleteBuffers(1, [self.vbo])
        if self.ebo:
            gl.glDeleteBuffers(1, [self.ebo])
        
        # Clean up textures
        for texture in self._gl_textures.values():
            texture.destroy()
        self._gl_textures.clear()
        
        if self.main_fbo:
            self.main_fbo = None
        
        if self.shader_program:
            self.shader_program = None
        
        self._initialized = False
    
    def resize(self, width: int, height: int):
        """Resize render target"""
        self.width = width
        self.height = height
        
        if self._initialized:
            gl.glViewport(0, 0, width, height)
            
            # Recreate main framebuffer
            if self.main_fbo:
                self.main_fbo = None
            self.main_fbo = QOpenGLFramebufferObject(width, height)
    
    def create_texture(self, width: int, height: int, 
                      format: str = "RGBA8", 
                      filter_type: FilterType = FilterType.LINEAR) -> RenderTexture:
        """Create OpenGL texture"""
        texture = QOpenGLTexture(QOpenGLTexture.Target.Target2D)
        texture.setSize(width, height)
        
        # Set format
        if format == "RGBA8":
            texture.setFormat(QOpenGLTexture.TextureFormat.RGBA8_UNorm)
        elif format == "RGB8":
            texture.setFormat(QOpenGLTexture.TextureFormat.RGB8_UNorm)
        else:
            texture.setFormat(QOpenGLTexture.TextureFormat.RGBA8_UNorm)
        
        # Set filtering
        if filter_type == FilterType.NEAREST:
            texture.setMinificationFilter(QOpenGLTexture.Filter.Nearest)
            texture.setMagnificationFilter(QOpenGLTexture.Filter.Nearest)
        else:
            texture.setMinificationFilter(QOpenGLTexture.Filter.Linear)
            texture.setMagnificationFilter(QOpenGLTexture.Filter.Linear)
        
        texture.setWrapMode(QOpenGLTexture.WrapMode.ClampToEdge)
        texture.allocateStorage()
        
        texture_id = texture.textureId()
        self._gl_textures[texture_id] = texture
        
        return RenderTexture(
            texture_id=texture_id,
            width=width,
            height=height,
            format=format,
            filter_type=filter_type
        )
    
    def upload_texture(self, texture: RenderTexture, image: QImage) -> bool:
        """Upload image data to texture"""
        try:
            gl_texture = self._gl_textures.get(texture.texture_id)
            if not gl_texture:
                return False
            
            # Convert QImage to OpenGL format
            gl_image = image.convertToFormat(QImage.Format.Format_RGBA8888)
            gl_texture.setData(gl_image)
            
            return True
            
        except Exception as e:
            print(f"Failed to upload texture: {e}")
            return False
    
    def delete_texture(self, texture: RenderTexture):
        """Delete OpenGL texture"""
        if texture.texture_id in self._gl_textures:
            gl_texture = self._gl_textures[texture.texture_id]
            gl_texture.destroy()
            del self._gl_textures[texture.texture_id]
    
    def create_framebuffer(self, width: int, height: int) -> int:
        """Create framebuffer object"""
        fbo = QOpenGLFramebufferObject(width, height)
        if fbo.isValid():
            return fbo.handle()
        return 0
    
    def bind_framebuffer(self, fbo_id: int):
        """Bind framebuffer for rendering"""
        gl.glBindFramebuffer(gl.GL_FRAMEBUFFER, fbo_id)
    
    def clear_framebuffer(self, color: QColor = QColor(0, 0, 0, 0)):
        """Clear framebuffer"""
        gl.glClearColor(
            color.redF(),
            color.greenF(), 
            color.blueF(),
            color.alphaF()
        )
        gl.glClear(gl.GL_COLOR_BUFFER_BIT | gl.GL_DEPTH_BUFFER_BIT)
    
    def draw_layer(self, layer: RenderLayer):
        """Draw layer using OpenGL"""
        if not layer.texture or not layer.visible:
            return
        
        gl_texture = self._gl_textures.get(layer.texture.texture_id)
        if not gl_texture:
            return
        
        # Bind shader program
        self.shader_program.bind()
        
        # Set uniforms
        self.shader_program.setUniformValue("opacity", layer.opacity)
        self.shader_program.setUniformValue("colorTint", 
            layer.color_tint.redF(),
            layer.color_tint.greenF(),
            layer.color_tint.blueF(),
            layer.color_tint.alphaF()
        )
        
        # Bind texture
        gl_texture.bind()
        self.shader_program.setUniformValue("ourTexture", 0)
        
        # Set transform matrices (simplified)
        # TODO: Implement proper transform matrix calculation
        
        # Draw quad
        gl.glBindVertexArray(self.vao)
        gl.glDrawElements(gl.GL_TRIANGLES, 6, gl.GL_UNSIGNED_INT, None)
        gl.glBindVertexArray(0)
        
        gl_texture.release()
        self.shader_program.release()
    
    def present_frame(self) -> QImage:
        """Present frame and return as QImage"""
        if not self.main_fbo:
            return QImage()
        
        return self.main_fbo.toImage()
    
    def read_framebuffer(self, fbo_id: int) -> QImage:
        """Read framebuffer contents"""
        # Bind framebuffer
        gl.glBindFramebuffer(gl.GL_FRAMEBUFFER, fbo_id)
        
        # Read pixels
        pixels = gl.glReadPixels(0, 0, self.width, self.height, gl.GL_RGBA, gl.GL_UNSIGNED_BYTE)
        
        # Convert to QImage
        image = QImage(pixels, self.width, self.height, QImage.Format.Format_RGBA8888)
        return image.mirrored(False, True)  # Flip vertically
