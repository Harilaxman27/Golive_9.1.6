#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Text Overlay Renderer - Functional Implementation
Renders text overlays onto video frames using the settings from TextOverlaySettingsDialog
"""

from PyQt6.QtGui import QPainter, QFont, QColor, QPen, QBrush, QFontMetrics, QImage, QPainterPath
from PyQt6.QtCore import Qt, QRect, QPoint, QPointF, QMutex, QMutexLocker
from typing import Dict, Optional, Tuple
import math

class TextOverlayRenderer:
    """Renders text overlays onto QImage frames with full styling support."""
    
    def __init__(self):
        self.current_settings: Optional[Dict] = None
        self.cached_font: Optional[QFont] = None
        self.cached_metrics: Optional[QFontMetrics] = None
        # Thread safety: protect rendering operations from concurrent access
        self._render_mutex = QMutex()
    
    def update_settings(self, settings: Dict):
        """Update text overlay settings and invalidate cache."""
        self.current_settings = settings
        self._update_font_cache()
    
    def _update_font_cache(self):
        """Update cached font and metrics when settings change."""
        if not self.current_settings:
            return
            
        self.cached_font = QFont(
            self.current_settings.get('font_family', 'Arial'),
            self.current_settings.get('font_size', 36)
        )
        
        self.cached_font.setBold(self.current_settings.get('bold', False))
        self.cached_font.setItalic(self.current_settings.get('italic', False))
        self.cached_font.setUnderline(self.current_settings.get('underline', False))
        
        self.cached_metrics = QFontMetrics(self.cached_font)
    
    def render_overlay(self, frame: QImage) -> QImage:
        """Render text overlay onto the provided frame with thread safety."""
        if not self.current_settings or not self.current_settings.get('text'):
            return frame
        
        # THREAD SAFETY: Acquire mutex to protect rendering from concurrent access
        # This prevents Qt crashes when QPainter/QImage operations happen on wrong thread
        locker = QMutexLocker(self._render_mutex)
        
        try:
            # Create a copy to avoid modifying the original
            # The copy is created under mutex protection so no interference occurs
            result = frame.copy()
            if result.isNull():
                return frame  # If copy failed, return original
            
            # Create painter under mutex protection
            painter = QPainter(result)
            if not painter.isActive():
                return frame  # If painter failed to activate, return original
            
            try:
                # Enable antialiasing for smooth text
                painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
                painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
                
                # Render text while mutex is held
                self._render_text(painter, result.size())
                
            finally:
                painter.end()
            
            return result
        except KeyboardInterrupt:
            # Allow keyboard interrupt to propagate cleanly without crash
            return frame
        except Exception as e:
            # If rendering fails, log and return original frame
            print(f"[TEXT_OVERLAY] Rendering failed: {e}")
            return frame
        finally:
            # Mutex is automatically released when locker goes out of scope
            pass
    
    def _render_text(self, painter: QPainter, frame_size):
        """Render the text with all styling options."""
        if not self.cached_font:
            return
        
        # --- WINDOWS CRASH FIX: FONT SANITIZATION ---
        # The crash happens later at path.addText if using "MS Sans Serif".
        # We catch it here and swap it for a safe vector font.
        current_family = self.cached_font.family()
        if "Sans Serif" in current_family or "MS Shell Dlg" in current_family:
            # Force update to Segoe UI to prevent DirectWrite crash
            safe_font = QFont("Segoe UI", self.cached_font.pointSize())
            safe_font.setBold(self.cached_font.bold())
            safe_font.setItalic(self.cached_font.italic())
            safe_font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
            self.cached_font = safe_font
            
            # Re-calculate metrics since font changed
            self.cached_metrics = QFontMetrics(self.cached_font)
        # ---------------------------------------------

        if not self.cached_metrics:
             return

        text = self.current_settings['text']
        if not text.strip():
            return
        
        painter.setFont(self.cached_font)
        
        # Calculate text dimensions
        text_rect = self.cached_metrics.boundingRect(text)
        text_width = text_rect.width()
        text_height = text_rect.height()
        
        # Calculate position based on percentage and alignment
        pos_x_percent = self.current_settings.get('position_x', 50)
        pos_y_percent = self.current_settings.get('position_y', 50)
        alignment = self.current_settings.get('alignment', 'center')
        
        # Convert percentage to pixel coordinates
        base_x = int((pos_x_percent / 100.0) * frame_size.width())
        base_y = int((pos_y_percent / 100.0) * frame_size.height())
        
        # Adjust for alignment
        if alignment == 'left':
            text_x = base_x
        elif alignment == 'center':
            text_x = base_x - text_width // 2
        else:  # right
            text_x = base_x - text_width
        
        text_y = base_y - text_height // 2
        
        # Ensure text stays within frame bounds
        text_x = max(10, min(text_x, frame_size.width() - text_width - 10))
        text_y = max(text_height, min(text_y, frame_size.height() - 10))
        
        # Note: QPainterPath expects baseline, so we add text_height
        text_position = QPoint(text_x, text_y + self.cached_metrics.ascent())
        
        # Render background if enabled
        if self.current_settings.get('bg_enabled', False):
            self._render_background(painter, text_x, text_y, text_width, text_height)
        
        # Render shadow if enabled
        if self.current_settings.get('shadow_enabled', False):
            self._render_shadow(painter, text, text_position)
        
        # Build vector path for text once
        path = QPainterPath()
        # This is the line that was crashing:
        path.addText(QPointF(text_position.x(), text_position.y()), self.cached_font, text)
        
        # Render outline if enabled
        if self.current_settings.get('outline_enabled', False):
            self._render_outline(painter, path)
        
        # Render main text
        text_color = QColor(self.current_settings.get('text_color', '#ffffff'))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(text_color))
        painter.fillPath(path, QBrush(text_color))
    
    def _render_background(self, painter: QPainter, x: int, y: int, width: int, height: int):
        """Render background rectangle behind text."""
        bg_color = QColor(self.current_settings.get('bg_color', '#000000'))
        bg_opacity = self.current_settings.get('bg_opacity', 0.5)
        
        # Apply opacity
        bg_color.setAlphaF(bg_opacity)
        
        # Add padding around text
        padding = 10
        bg_rect = QRect(x - padding, y - padding, width + 2 * padding, height + 2 * padding)
        
        painter.fillRect(bg_rect, QBrush(bg_color))
    
    def _render_shadow(self, painter: QPainter, text: str, position: QPoint):
        """Render drop shadow behind text."""
        shadow_offset = 3
        shadow_color = QColor(0, 0, 0, 128)  # Semi-transparent black
        
        shadow_position = QPoint(position.x() + shadow_offset, position.y() + shadow_offset)
        painter.setPen(QPen(shadow_color))
        painter.drawText(shadow_position, text)
    
    def _render_outline(self, painter: QPainter, text_path: QPainterPath):
        """Render outline around text using vector stroking with safety checks."""
        try:
            if not painter.isActive():
                return  # Painter is in invalid state
            
            outline_width = int(self.current_settings.get('outline_width', self.current_settings.get('stroke_width', 2)))
            color_value = self.current_settings.get('stroke_color', '#000000')
            outline_color = QColor(color_value)
            
            if outline_width > 0 and not text_path.isEmpty():
                pen = QPen(outline_color)
                pen.setWidth(outline_width)
                pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
                pen.setCapStyle(Qt.PenCapStyle.RoundCap)
                painter.setPen(pen)
                painter.setBrush(Qt.BrushStyle.NoBrush)
                # Final safety check before drawing
                if painter.isActive():
                    painter.drawPath(text_path)
        except KeyboardInterrupt:
            raise
        except Exception as e:
            # Silently handle outline errors to prevent crashes
            pass
    
    def is_enabled(self) -> bool:
        """Check if text overlay is currently enabled."""
        return (self.current_settings is not None and 
                bool(self.current_settings.get('text', '').strip()))
    
    def get_preview_image(self, width: int = 400, height: int = 300) -> QImage:
        """Generate a preview image showing the current text overlay."""
        if not self.current_settings:
            # Return blank preview
            preview = QImage(width, height, QImage.Format.Format_RGB32)
            preview.fill(QColor(30, 30, 30))  # Dark gray background
            return preview
        
        # Create preview with sample background
        preview = QImage(width, height, QImage.Format.Format_RGB32)
        preview.fill(QColor(60, 60, 60))  # Medium gray background
        
        # Add some sample content to make preview more realistic
        painter = QPainter(preview)
        painter.setPen(QPen(QColor(100, 100, 100)))
        painter.drawText(QRect(10, 10, width-20, 30), Qt.AlignmentFlag.AlignCenter, "Preview Background")
        painter.end()
        
        # Apply text overlay
        return self.render_overlay(preview)

# Global instance for the application
text_overlay_renderer = TextOverlayRenderer()
