"""
GoLive Studio - GPU Overlay Manager
GPU-accelerated overlay and effects management using renderer abstraction
"""

import os
from typing import Optional, Tuple, Dict
from PyQt6.QtGui import QImage, QColor
from PyQt6.QtCore import QSize, QRectF

from .base_renderer import BaseRenderer, RenderLayer, RenderTexture, BlendMode


class GPUOverlayManager:
    """
    GPU-accelerated overlay and effects manager
    Replaces overlay_manager.py with GPU-based rendering
    """
    
    def __init__(self, renderer: BaseRenderer):
        self.renderer = renderer
        
        # Current overlay state
        self._selected_path: Optional[str] = None
        self._overlay_image: Optional[QImage] = None
        self._overlay_texture: Optional[RenderTexture] = None
        self._overlay_layer: Optional[RenderLayer] = None
        
        # Opening detection cache
        self._opening_norm: Optional[Tuple[float, float, float, float]] = None
        self._mask_texture: Optional[RenderTexture] = None
        
        # Effect cache
        self._effect_cache: Dict[str, RenderTexture] = {}
    
    def get_selected(self) -> Optional[str]:
        """Get currently selected overlay path"""
        return self._selected_path
    
    def set_effect(self, path: str) -> bool:
        """
        Set overlay effect from path
        
        Args:
            path: Path to overlay image file
            
        Returns:
            bool: Success status
        """
        try:
            if not path or not os.path.exists(path):
                return False
            
            # Load image
            img = QImage(path)
            if img.isNull():
                return False
            
            self._selected_path = path
            self._overlay_image = img
            
            # Create or update GPU texture
            if self._overlay_texture:
                self.renderer.delete_texture(self._overlay_texture)
            
            self._overlay_texture = self.renderer.create_texture(
                img.width(),
                img.height()
            )
            
            # Upload image to GPU
            if not self.renderer.upload_texture(self._overlay_texture, img):
                return False
            
            # Detect opening area
            self._detect_opening()
            
            # Create/update overlay layer
            self._update_overlay_layer()
            
            return True
            
        except Exception as e:
            print(f"Failed to set GPU overlay effect: {e}")
            return False
    
    def clear_effect(self):
        """Clear current overlay effect"""
        self._selected_path = None
        self._overlay_image = None
        
        if self._overlay_texture:
            self.renderer.delete_texture(self._overlay_texture)
            self._overlay_texture = None
        
        if self._mask_texture:
            self.renderer.delete_texture(self._mask_texture)
            self._mask_texture = None
        
        if self._overlay_layer:
            self.renderer.remove_layer(self._overlay_layer)
            self._overlay_layer = None
        
        self._opening_norm = None
    
    def compose_with_source(self, source_texture: RenderTexture, target_size: QSize) -> RenderTexture:
        """
        Compose overlay with source texture using GPU
        
        Args:
            source_texture: Source video texture
            target_size: Target composition size
            
        Returns:
            RenderTexture: Composited result
        """
        if not self._overlay_texture or not source_texture:
            return source_texture
        
        try:
            # Create composition framebuffer
            comp_fbo = self.renderer.create_framebuffer(target_size.width(), target_size.height())
            if comp_fbo == 0:
                return source_texture
            
            # Bind composition framebuffer
            self.renderer.bind_framebuffer(comp_fbo)
            self.renderer.clear_framebuffer(QColor(0, 0, 0, 0))
            
            # Create temporary layers for composition
            layers = []
            
            # Background layer (source video)
            if self._opening_norm and self._mask_texture:
                # Apply opening mask to source
                source_layer = RenderLayer(
                    texture=source_texture,
                    transform=QRectF(0, 0, target_size.width(), target_size.height()),
                    z_order=0,
                    visible=True
                )
                # TODO: Apply mask shader here
                layers.append(source_layer)
            else:
                # Full source
                source_layer = RenderLayer(
                    texture=source_texture,
                    transform=QRectF(0, 0, target_size.width(), target_size.height()),
                    z_order=0,
                    visible=True
                )
                layers.append(source_layer)
            
            # Overlay layer
            overlay_layer = RenderLayer(
                texture=self._overlay_texture,
                transform=QRectF(0, 0, target_size.width(), target_size.height()),
                z_order=10,
                visible=True,
                blend_mode=BlendMode.ALPHA_BLEND
            )
            layers.append(overlay_layer)
            
            # Render layers
            for layer in sorted(layers, key=lambda l: l.z_order):
                self.renderer.draw_layer(layer)
            
            # Read result back to texture
            result_image = self.renderer.read_framebuffer(comp_fbo)
            
            # Create result texture
            result_texture = self.renderer.create_texture(
                result_image.width(),
                result_image.height()
            )
            
            self.renderer.upload_texture(result_texture, result_image)
            
            return result_texture
            
        except Exception as e:
            print(f"GPU overlay composition failed: {e}")
            return source_texture
    
    def _detect_opening(self):
        """Detect opening area in overlay image"""
        if not self._overlay_image:
            return
        
        try:
            # Try JSON sidecar first
            opening = self._load_opening_override(self._selected_path)
            if opening is None:
                # Try mask file
                opening = self._detect_opening_from_mask(self._selected_path)
            if opening is None:
                # Heuristic detection
                opening = self._detect_opening_heuristic(self._overlay_image)
            
            self._opening_norm = opening
            
            # Create mask texture if opening detected
            if opening:
                self._create_mask_texture()
                
        except Exception as e:
            print(f"Opening detection failed: {e}")
    
    def _load_opening_override(self, effect_path: str) -> Optional[Tuple[float, float, float, float]]:
        """Load opening from JSON sidecar file"""
        try:
            import json
            base, _ = os.path.splitext(effect_path)
            json_path = base + '.json'
            
            if not os.path.exists(json_path):
                return None
            
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            opening = data.get('opening') if isinstance(data, dict) else None
            if isinstance(opening, (list, tuple)) and len(opening) == 4:
                nx, ny, nw, nh = [float(v) for v in opening]
                return (max(0.0, min(1.0, nx)), max(0.0, min(1.0, ny)), 
                       max(0.01, min(1.0, nw)), max(0.01, min(1.0, nh)))
            
            return None
            
        except Exception:
            return None
    
    def _detect_opening_from_mask(self, effect_path: str) -> Optional[Tuple[float, float, float, float]]:
        """Detect opening from mask file"""
        try:
            base, _ = os.path.splitext(effect_path)
            mask_path = base + '_mask.png'
            
            if not os.path.exists(mask_path):
                return None
            
            mask_img = QImage(mask_path)
            if mask_img.isNull():
                return None
            
            w, h = mask_img.width(), mask_img.height()
            min_x, min_y, max_x, max_y = w, h, -1, -1
            
            # Find bounding box of white pixels
            for y in range(h):
                for x in range(w):
                    c = mask_img.pixelColor(x, y)
                    if c.red() > 200 and c.green() > 200 and c.blue() > 200 and c.alpha() > 200:
                        min_x = min(min_x, x)
                        min_y = min(min_y, y)
                        max_x = max(max_x, x)
                        max_y = max(max_y, y)
            
            if max_x <= min_x or max_y <= min_y:
                return None
            
            return (min_x / w, min_y / h, (max_x - min_x + 1) / w, (max_y - min_y + 1) / h)
            
        except Exception:
            return None
    
    def _detect_opening_heuristic(self, img: QImage) -> Optional[Tuple[float, float, float, float]]:
        """Heuristic opening detection from alpha channel"""
        try:
            # Scale down for faster processing
            target_w = 320
            small = img if img.width() < target_w else img.scaledToWidth(target_w)
            small = small.convertToFormat(QImage.Format.Format_ARGB32)
            
            w, h = small.width(), small.height()
            if w <= 10 or h <= 10:
                return None
            
            margin = max(4, w // 40)
            alpha_thresh = 10
            
            # Find largest transparent region
            from collections import deque
            
            visited = [[False] * w for _ in range(h)]
            best = None
            best_area = 0
            
            dirs = ((1, 0), (-1, 0), (0, 1), (0, -1))
            
            for y0 in range(margin, h - margin):
                for x0 in range(margin, w - margin):
                    c = small.pixelColor(x0, y0)
                    if c.alpha() < alpha_thresh and not visited[y0][x0]:
                        # BFS to find connected transparent region
                        q = deque([(x0, y0)])
                        visited[y0][x0] = True
                        min_x = min_y = 10**9
                        max_x = max_y = -1
                        area = 0
                        touches_edge = False
                        
                        while q:
                            x, y = q.popleft()
                            area += 1
                            min_x = min(min_x, x)
                            min_y = min(min_y, y)
                            max_x = max(max_x, x)
                            max_y = max(max_y, y)
                            
                            if x == 0 or y == 0 or x == w - 1 or y == h - 1:
                                touches_edge = True
                            
                            for dx, dy in dirs:
                                nx, ny = x + dx, y + dy
                                if (0 <= nx < w and 0 <= ny < h and 
                                    not visited[ny][nx] and 
                                    small.pixelColor(nx, ny).alpha() < alpha_thresh):
                                    visited[ny][nx] = True
                                    q.append((nx, ny))
                        
                        # Only consider internal regions (not touching edges)
                        if not touches_edge and area > best_area:
                            best_area = area
                            best = (min_x, min_y, max_x, max_y)
            
            if best is None:
                return None
            
            min_x, min_y, max_x, max_y = best
            return (min_x / w, min_y / h, (max_x - min_x + 1) / w, (max_y - min_y + 1) / h)
            
        except Exception:
            return None
    
    def _create_mask_texture(self):
        """Create GPU mask texture from opening"""
        if not self._opening_norm or not self._overlay_image:
            return
        
        try:
            # Create mask image
            w, h = self._overlay_image.width(), self._overlay_image.height()
            mask_img = QImage(w, h, QImage.Format.Format_ARGB32)
            mask_img.fill(QColor(0, 0, 0, 0))  # Transparent
            
            # Fill opening area with white
            nx, ny, nw, nh = self._opening_norm
            rx = int(nx * w)
            ry = int(ny * h)
            rw = max(1, int(nw * w))
            rh = max(1, int(nh * h))
            
            from PyQt6.QtGui import QPainter
            painter = QPainter(mask_img)
            painter.fillRect(rx, ry, rw, rh, QColor(255, 255, 255, 255))
            painter.end()
            
            # Create GPU texture
            if self._mask_texture:
                self.renderer.delete_texture(self._mask_texture)
            
            self._mask_texture = self.renderer.create_texture(w, h)
            self.renderer.upload_texture(self._mask_texture, mask_img)
            
        except Exception as e:
            print(f"Failed to create mask texture: {e}")
    
    def _update_overlay_layer(self):
        """Update overlay render layer"""
        if not self._overlay_texture:
            return
        
        if self._overlay_layer:
            self.renderer.remove_layer(self._overlay_layer)
        
        self._overlay_layer = RenderLayer(
            texture=self._overlay_texture,
            transform=QRectF(0, 0, self._overlay_texture.width, self._overlay_texture.height),
            z_order=20,
            visible=True,
            blend_mode=BlendMode.ALPHA_BLEND
        )
        
        self.renderer.add_layer(self._overlay_layer)
    
    def cleanup(self):
        """Clean up GPU resources"""
        if self._overlay_texture:
            self.renderer.delete_texture(self._overlay_texture)
        if self._mask_texture:
            self.renderer.delete_texture(self._mask_texture)
        
        # Clean up effect cache
        for texture in self._effect_cache.values():
            self.renderer.delete_texture(texture)
        self._effect_cache.clear()
