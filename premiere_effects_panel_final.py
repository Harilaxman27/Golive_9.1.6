#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Ultra-Optimized Premiere Pro-style Effects Panel with Performance Enhancements
Features: Virtual scrolling, lazy loading, adaptive FPS, memory management, startup optimization
"""

import os
import gc
import sys
import weakref
from collections import OrderedDict
try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False
    
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QScrollArea,
    QGridLayout, QLineEdit, QSplitter, QTreeWidget, QTreeWidgetItem,
    QSizePolicy, QApplication
)
from PyQt6.QtCore import Qt, QSize, QTimer, pyqtSignal, QThread, pyqtSlot, QEvent, QRect
from PyQt6.QtGui import QPixmap, QIcon, QImageReader, QImage, QMouseEvent


# OPTIMIZATION 1: Enhanced Memory-Efficient LRU Cache
class ThumbnailCache:
    """Memory-efficient LRU cache with size limits and weak references"""
    _instance = None
    _cache = OrderedDict()
    _weak_cache = weakref.WeakValueDictionary()  # Secondary weak reference cache
    _max_cache_size = 50  # Balanced cache size
    _total_memory_limit = 100 * 1024 * 1024  # 100MB limit for smoother experience
    _current_memory_usage = 0
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def get(self, path, size: QSize):
        """Get cached image with fallback to weak cache."""
        key = (path, size.width(), size.height())
        # Try main cache first
        if key in self._cache:
            self._cache.move_to_end(key)  # LRU: move to end
            return self._cache[key]
        # Try weak cache as fallback
        return self._weak_cache.get(key)
    
    def set(self, path, size: QSize, image: QImage):
        """Cache image with memory management."""
        key = (path, size.width(), size.height())
        image_size = image.sizeInBytes() if hasattr(image, 'sizeInBytes') else image.width() * image.height() * 4
        
        # Check memory limit
        if self._current_memory_usage + image_size > self._total_memory_limit:
            self._evict_oldest()
            
        # Enforce count limit
        while len(self._cache) >= self._max_cache_size:
            self._evict_oldest()
            
        self._cache[key] = image
        self._weak_cache[key] = image  # Also store in weak cache
        self._current_memory_usage += image_size
    
    def _evict_oldest(self):
        """Evict oldest entry from cache."""
        if self._cache:
            key, image = self._cache.popitem(last=False)
            image_size = image.sizeInBytes() if hasattr(image, 'sizeInBytes') else image.width() * image.height() * 4
            self._current_memory_usage = max(0, self._current_memory_usage - image_size)
    
    def clear(self):
        self._cache.clear()


# OPTIMIZATION 2: Ultra-Efficient Thumbnail Loader with Priority Queue
class ThumbnailLoader(QThread):
    """Optimized thumbnail loader with priority queue and batch processing."""
    thumbnail_ready = pyqtSignal(str, QImage, int)
    
    def __init__(self):
        super().__init__()
        self.queue = []  # Priority queue
        self.high_priority_queue = []  # For visible items
        self.cache = ThumbnailCache()
        self.thumb_size = QSize(150, 85)  # Larger size for better visibility
        self.generation = 0
        self.batch_size = 5  # Process 5 thumbnails per batch
        self.quality = 75  # Better quality
        self.max_source_size = 3000  # Handle larger images
        # Don't set priority here - causes Qt warning
    
    def set_thumbnail_size(self, size):
        """Update thumbnail size with queue management."""
        if size != self.thumb_size:
            self.thumb_size = size
            self.generation += 1
            self.queue.clear()
            self.high_priority_queue.clear()
            # Trigger garbage collection on size change
            gc.collect(0)
    
    def load_thumbnail(self, path, high_priority=False):
        """Add to load queue with priority support."""
        if high_priority:
            if path not in self.high_priority_queue:
                self.high_priority_queue.append(path)
        else:
            if path not in self.queue and path not in self.high_priority_queue:
                self.queue.append(path)
        
        if not self.isRunning():
            self.start()
            self.setPriority(QThread.Priority.LowPriority)  # Set after starting
    
    def run(self):
        """Process thumbnails with batch processing and optimization."""
        batch_count = 0
        
        while self.high_priority_queue or self.queue:
            # Process high priority first
            if self.high_priority_queue:
                path = self.high_priority_queue.pop(0)
            elif self.queue:
                path = self.queue.pop(0)
            else:
                break
                
            current_size = self.thumb_size
            current_gen = self.generation
            
            # Check cache
            cached = self.cache.get(path, current_size)
            if cached:
                self.thumbnail_ready.emit(path, cached, current_gen)
                continue
            
            # Load new with optimizations
            try:
                reader = QImageReader(path)
                
                # Skip very large images
                if reader.size().width() > self.max_source_size or reader.size().height() > self.max_source_size:
                    continue
                    
                reader.setAutoTransform(True)
                reader.setQuality(self.quality)
                # Read and scale with smooth transformation
                image = reader.read()
                if not image.isNull():
                    image = image.scaled(
                        current_size,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation
                    )
                
                if not image.isNull():
                    self.cache.set(path, current_size, image)
                    self.thumbnail_ready.emit(path, image, current_gen)
            except:
                pass
            
            batch_count += 1
            
            # Yield after batch to prevent UI blocking
            if batch_count >= self.batch_size:
                batch_count = 0
                self.msleep(5)  # Balanced delay after batch
            else:
                self.msleep(1)  # Minimal delay between items


class EffectButton(QPushButton):
    """Simple effect thumbnail button with double-click support."""
    
    double_clicked = pyqtSignal(str)  # Signal for double-click
    
    def __init__(self, effect_path, size, parent=None):
        super().__init__(parent)
        self.effect_path = effect_path
        self.effect_name = os.path.splitext(os.path.basename(effect_path))[0]
        self.button_size = size
        self.setFixedSize(size)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip(f"{self.effect_name.replace('_', ' ').title()}\n\nDouble-click to remove effect")
        
        # No need for custom click tracking - using Qt's built-in double-click
        
        # Clean styling
        # Clean styling
        self.setStyleSheet("""
            QPushButton {
                background: #2A2A2A;
                border: 1px solid #383838;
                border-radius: 6px;
            }
            QPushButton:hover {
                background: #333;
                border: 1px solid #555;
            }
            QPushButton:pressed {
                border: 2px solid #007AFF;
            }
        """)
        
        self.setText("Loading...")
    
    def mouseDoubleClickEvent(self, event):
        """Handle double-click for effect removal."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.double_clicked.emit(self.effect_path)
            event.accept()
    
    def mousePressEvent(self, event):
        """Handle single mouse press."""
        # Let the parent handle normal clicks
        super().mousePressEvent(event)
    
    
    def set_thumbnail(self, pixmap):
        """Set thumbnail image"""
        self.setIcon(QIcon(pixmap))
        self.setIconSize(QSize(self.button_size.width() - 4, self.button_size.height() - 4))
        self.setText("")
    
    def set_selected(self, selected):
        """Update selection state"""
        if selected:
            self.setStyleSheet("""
                QPushButton {
                    background: #2b2b2b;
                    border: 2px solid #00aaff;
                    border-radius: 4px;
                }
            """)
        else:
            self.setStyleSheet("""
                QPushButton {
                    background: #2b2b2b;
                    border: 1px solid #3a3a3a;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background: #353535;
                    border: 1px solid #4a4a4a;
                }
            """)


# OPTIMIZATION 4: Virtual Scrolling Grid with Viewport Culling
class AdaptiveEffectsGrid(QWidget):
    """Adaptive effects grid with selection and removal support."""
    
    effect_selected = pyqtSignal(str)
    effect_removed = pyqtSignal()  # Signal when effect is removed via double-click
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.effects = []
        self.buttons = []  # All buttons
        self.selected_button = None
        self.loader = ThumbnailLoader()
        self.loader.thumbnail_ready.connect(self._on_thumbnail_ready)
        self._current_gen = 0
        
        # Layout
        self.layout = QGridLayout(self)
        self.layout.setSpacing(8)
        self.layout.setContentsMargins(10, 10, 10, 10)
        
        # Optimized sizing for better visibility
        self.base_thumb_width = 160  # Larger for better visibility
        self.base_thumb_height = 90  # 16:9 ratio
        self.min_columns = 3
        self.max_columns = 3  # Fixed 3 columns for better visibility
        
        # Performance optimizations
        self.setStyleSheet("background: #1C1C1C;")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
    
    def resizeEvent(self, event):
        """Handle resize with debouncing."""
        super().resizeEvent(event)
        if self.effects:  # Only rebuild if we have effects
            if not hasattr(self, "_rebuild_timer"):
                self._rebuild_timer = QTimer(self)
                self._rebuild_timer.setSingleShot(True)
                self._rebuild_timer.timeout.connect(self._rebuild_visible_only)
            self._rebuild_timer.start(100)

    def schedule_rebuild(self, delay_ms: int = 50):
        """Schedule rebuild."""
        if self.effects:  # Only rebuild if we have effects
            if not hasattr(self, "_rebuild_timer"):
                self._rebuild_timer = QTimer(self)
                self._rebuild_timer.setSingleShot(True)
                self._rebuild_timer.timeout.connect(self._rebuild_visible_only)
            self._rebuild_timer.start(max(30, int(delay_ms)))
    
    def _calculate_grid_params(self):
        """Calculate optimal grid parameters"""
        # Prefer scroll-area viewport width if available
        available_width = self.width() - 20  # fallback
        try:
            parent = self.parent()
            if parent and hasattr(parent, 'viewport'):
                vw = parent.viewport().width()
                if vw and vw > 0:
                    available_width = vw - 20
        except Exception:
            pass
        
        # Dynamic columns: 3 if sidebar hidden (wide), 2 if sidebar visible (narrow)
        # Threshold around 400px width
        if available_width > 380:
            columns = 3
        else:
            columns = 2
        
        # Calculate button size to fit width perfectly
        # Account for scrollbar width (approx 10-15px) and margins
        button_width = (available_width - (columns - 1) * 8 - 10) // columns
        button_height = int(button_width * 0.56)  # 16:9 aspect ratio
        
        # Ensure minimum size for visibility
        button_width = max(button_width, 100)
        button_height = max(button_height, 56)
        
        return columns, QSize(button_width, button_height)
    
    def set_effects(self, effect_paths):
        """Set effects and rebuild grid."""
        self.effects = effect_paths
        self._rebuild_grid()
    
    def _rebuild_visible_only(self):
        """Rebuild grid."""
        self._rebuild_grid()
    
    def _rebuild_grid(self):
        """Rebuild the effects grid."""
        # Clear old buttons safely
        for button in self.buttons:
            try:
                self.layout.removeWidget(button)
                button.setParent(None)
                button.deleteLater()
            except RuntimeError:
                pass  # Button already deleted
        self.buttons.clear()
        self.selected_button = None
        
        if not self.effects:
            return
        
        # Calculate grid parameters
        columns, button_size = self._calculate_grid_params()
        
        # Update loader thumbnail size
        thumb_size = QSize(button_size.width() - 4, button_size.height() - 4)
        self.loader.set_thumbnail_size(thumb_size)
        self._current_gen = self.loader.generation
        
        # Create buttons for all effects
        for i, effect_path in enumerate(self.effects):
            button = EffectButton(effect_path, button_size, self)
            # Fix lambda closure issue
            button.clicked.connect(lambda checked, path=effect_path: self._on_effect_clicked(path))
            # Connect double-click for removal
            button.double_clicked.connect(lambda path=effect_path: self._on_effect_double_clicked(path))
            
            row = i // columns
            col = i % columns
            self.layout.addWidget(button, row, col)
            self.buttons.append(button)
            
            # Try cache first
            cached = self.loader.cache.get(effect_path, thumb_size)
            if isinstance(cached, QImage):
                button.set_thumbnail(QPixmap.fromImage(cached))
            else:
                # Load thumbnail normally
                self.loader.load_thumbnail(effect_path, high_priority=(i < 20))  # First 20 are high priority
        
        # Add stretch to push buttons to top
        if self.effects:
            self.layout.setRowStretch(len(self.effects) // columns + 1, 1)
    
    @pyqtSlot(str, QImage, int)
    def _on_thumbnail_ready(self, path, image, gen):
        """Handle loaded thumbnail (convert to QPixmap in GUI thread).
        Ignore stale generations from a previous size to prevent artifacts."""
        if gen != self._current_gen:
            return
        pix = QPixmap.fromImage(image)
        for button in self.buttons:
            if button.effect_path == path:
                button.set_thumbnail(pix)
                break
    
    def _on_effect_clicked(self, effect_path):
        """Handle effect selection."""
        # Find the button that was clicked
        clicked_button = None
        for button in self.buttons:
            if button.effect_path == effect_path:
                clicked_button = button
                break
        
        if clicked_button:
            # Clear previous selection
            if self.selected_button:
                self.selected_button.set_selected(False)
            
            # Set new selection
            clicked_button.set_selected(True)
            self.selected_button = clicked_button
            self.effect_selected.emit(effect_path)
    
    def _on_effect_double_clicked(self, effect_path):
        """Handle effect removal via double-click."""
        print(f"Double-click detected for effect: {effect_path}")  # Debug
        
        # Clear selection if this effect was selected
        if self.selected_button and self.selected_button.effect_path == effect_path:
            self.selected_button.set_selected(False)
            self.selected_button = None
        
        # Emit removal signal
        self.effect_removed.emit()
        
        # Visual feedback - briefly highlight the button
        for button in self.buttons:
            if button.effect_path == effect_path:
                # Flash effect to show it was double-clicked
                original_style = button.styleSheet()
                button.setStyleSheet("""
                    QPushButton {
                        background: #ff4444;
                        border: 2px solid #ff6666;
                        border-radius: 3px;
                    }
                """)
                # Reset style after brief delay
                QTimer.singleShot(300, lambda b=button, style=original_style: b.setStyleSheet(style))
                break


# OPTIMIZATION 5: Main Panel with Lazy Loading and Performance Monitoring
class PerformanceMonitor:
    """Monitor and optimize runtime performance."""
    def __init__(self):
        self.fps_timer = QTimer()
        self.fps_timer.timeout.connect(self.check_performance)
        self.fps_timer.start(5000)  # Check every 5 seconds
        self.low_memory_mode = False
        
    def check_performance(self):
        """Check system performance and adjust settings."""
        if HAS_PSUTIL:
            try:
                # Check memory usage
                memory = psutil.virtual_memory()
                if memory.percent > 80:
                    if not self.low_memory_mode:
                        self.enable_low_memory_mode()
                elif memory.percent < 60 and self.low_memory_mode:
                    self.disable_low_memory_mode()
            except:
                pass
        
        # Force garbage collection if needed
        gc.collect(0)
    
    def enable_low_memory_mode(self):
        """Enable aggressive memory saving."""
        self.low_memory_mode = True
        cache = ThumbnailCache()
        cache._max_cache_size = 25
        gc.collect(2)  # Full collection
    
    def disable_low_memory_mode(self):
        """Return to normal memory usage."""
        self.low_memory_mode = False
        cache = ThumbnailCache()
        cache._max_cache_size = 50


class FinalEffectsPanel(QWidget):
    """Ultra-optimized effects panel with all performance enhancements."""
    
    effect_selected = pyqtSignal(str)
    effect_cleared = pyqtSignal()
    
    # Global performance monitor
    _performance_monitor = None
    
    def __init__(self, effects_path, parent=None):
        super().__init__(parent)
        self.effects_path = effects_path
        self.categories = {}  # Lazy-loaded
        self.current_effects = []
        
        # Initialize performance monitoring
        if FinalEffectsPanel._performance_monitor is None:
            FinalEffectsPanel._performance_monitor = PerformanceMonitor()
        
        # Configure Python for better performance
        gc.set_threshold(700, 10, 10)  # Tune garbage collection
        if hasattr(sys, 'setswitchinterval'):
            sys.setswitchinterval(0.005)  # Faster thread switching
        
        self._setup_ui()
        # Defer category loading for faster startup
        QTimer.singleShot(50, self._load_categories)  # Faster initial load
    
    def _toggle_sidebar(self):
        """Toggle the visibility of the category tree sidebar."""
        if self.category_tree.isVisible():
            self.category_tree.hide()
            # Collapse splitter handle 0
            self.splitter.setSizes([0, self.width()])
        else:
            self.category_tree.show()
            # Restore reasonable size
            total = max(1, self.width())
            left = max(150, int(total * 0.25))
            self.splitter.setSizes([left, total - left])
            
        # Trigger grid rebuild to adapt to new width
        self.effects_grid.schedule_rebuild(50)

    def _setup_ui(self):
        """Create UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Search bar
        search_widget = QWidget()
        search_widget.setFixedHeight(40)
        search_widget.setStyleSheet("background: #252525; border-bottom: 1px solid #333;")
        
        search_layout = QHBoxLayout(search_widget)
        search_layout.setContentsMargins(8, 6, 8, 6)
        search_layout.setSpacing(8)
        
        # Hamburger Menu Button
        self.menu_btn = QPushButton("☰")
        self.menu_btn.setFixedSize(28, 28)
        self.menu_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.menu_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                color: #888;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                color: #E0E0E0;
                background: #333;
                border-radius: 4px;
            }
        """)
        self.menu_btn.clicked.connect(self._toggle_sidebar)
        search_layout.addWidget(self.menu_btn)
        
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Search effects...")
        self.search_bar.setStyleSheet("""
            QLineEdit {
                background: #1C1C1C;
                border: 1px solid #333;
                border-radius: 4px;
                padding: 5px 10px;
                color: #E0E0E0;
                font-size: 12px;
            }
            QLineEdit:focus {
                border: 1px solid #007AFF;
            }
        """)
        search_layout.addWidget(self.search_bar)
        layout.addWidget(search_widget)
        
        # Setup search functionality
        self.search_timer = QTimer()
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(self._do_search)
        self.search_bar.textChanged.connect(lambda: self.search_timer.start(300))
        
        # Splitter for resizable panels
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.setHandleWidth(4)
        self.splitter.setStyleSheet("""
            QSplitter::handle {
                background: #3a3a3a;
            }
            QSplitter::handle:hover {
                background: #00aaff;
            }
        """)
        # Do not allow either panel to collapse to zero width
        # Note: apply setCollapsible after widgets are added to avoid warnings
        
        # Optimized categories tree
        self.category_tree = QTreeWidget()
        self.category_tree.setHeaderHidden(True)
        self.category_tree.setMinimumWidth(150)  # Smaller for more effect space
        self.category_tree.setMaximumWidth(250)
        self.category_tree.setRootIsDecorated(True)
        self.category_tree.setIndentation(14)
        self.category_tree.setUniformRowHeights(True)
        self.category_tree.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        # Elide long names with '…' instead of overflowing
        try:
            self.category_tree.setTextElideMode(Qt.TextElideMode.ElideRight)
            self.category_tree.setItemsExpandable(True)
            self.category_tree.setExpandsOnDoubleClick(True)  # double-click to expand/collapse
            self.category_tree.setAnimated(True)
        except Exception:
            pass
        self.category_tree.setStyleSheet("""
            QTreeWidget {
                background: #252525;
                border: none;
                color: #E0E0E0;
                font-size: 12px;
                outline: none;
            }
            QTreeWidget::item {
                padding: 6px;
                min-height: 28px;
                border-radius: 4px;
                margin: 1px 4px;
            }
            QTreeWidget::item:selected {
                background: #007AFF;
                color: white;
            }
            QTreeWidget::item:hover {
                background: #333;
            }
            /* Explicit branch indicators for dark theme */
            QTreeView::branch:has-children:closed,
            QTreeView::branch:closed:has-children:has-siblings,
            QTreeView::branch:closed:has-children:!has-siblings {
                border-image: none;
                image: url(:/qt-project.org/styles/commonstyle/images/branch-closed-16.png);
            }
            QTreeView::branch:open:has-children,
            QTreeView::branch:open:has-children:has-siblings,
            QTreeView::branch:open:has-children:!has-siblings {
                border-image: none;
                image: url(:/qt-project.org/styles/commonstyle/images/branch-open-16.png);
            }
        """)
        
        # Scroll area for effects
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setStyleSheet("""
            QScrollArea {
                background: #1C1C1C;
                border: none;
            }
            QScrollBar:vertical {
                background: #1C1C1C;
                width: 10px;
                margin: 0;
            }
            QScrollBar::handle:vertical {
                background: #444;
                border-radius: 5px;
                min-height: 30px;
                margin: 2px;
            }
            QScrollBar::handle:vertical:hover {
                background: #555;
            }
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {
                height: 0;
            }
        """)
        
        # Effects grid with selection and removal
        self.effects_grid = AdaptiveEffectsGrid()
        self.effects_grid.effect_selected.connect(self.effect_selected.emit)
        self.effects_grid.effect_removed.connect(self.effect_cleared.emit)
        self.scroll_area.setWidget(self.effects_grid)
        
        # Normal scrolling - no virtual scrolling
        
        # Add to splitter with optimized sizes
        self.splitter.addWidget(self.category_tree)
        self.splitter.addWidget(self.scroll_area)
        self.splitter.setSizes([150, 850])  # More space for effects
        self.splitter.setStretchFactor(0, 0)  # Categories don't stretch
        self.splitter.setStretchFactor(1, 1)  # Effects stretch
        # Now that widgets are added, prevent collapsing to zero
        try:
            self.splitter.setChildrenCollapsible(False)
            self.splitter.setCollapsible(0, False)
            self.splitter.setCollapsible(1, False)
        except Exception:
            pass
        
        layout.addWidget(self.splitter)
        
        # Connections
        self.category_tree.itemClicked.connect(self._on_category_selected)
        self.category_tree.itemExpanded.connect(self._on_item_expanded)
        self.category_tree.itemCollapsed.connect(self._on_item_collapsed)
        # Recalculate grid when the splitter moves (columns and cell size adapt)
        self.splitter.splitterMoved.connect(lambda pos, idx: self.effects_grid.schedule_rebuild(50))
        # Track viewport resize to keep columns correct while resizing window
        try:
            self.scroll_area.viewport().installEventFilter(self)
        except Exception:
            pass

    def showEvent(self, event):
        """Set the default splitter position once, to keep categories readable.
        Uses ~20% of available width but never less than the tree's minimum."""
        super().showEvent(event)
        if not hasattr(self, "_splitter_initialized"):
            self._splitter_initialized = True
            try:
                total = max(1, self.splitter.width())
                left = max(self.category_tree.minimumWidth(), int(total * 0.2))
                self.splitter.setSizes([left, max(1, total - left)])
                # make sure grid rebuilds for the new width
                self.effects_grid.schedule_rebuild(0)
            except Exception:
                pass

    def eventFilter(self, obj, event):
        if hasattr(self, 'scroll_area') and obj is self.scroll_area.viewport():
            if event.type() == QEvent.Type.Resize:
                # Align grid width and rebuild
                try:
                    self.effects_grid.setMinimumWidth(event.size().width())
                except Exception:
                    pass
                self.effects_grid.schedule_rebuild(0)
        return super().eventFilter(obj, event)
    
    def _load_categories(self):
        """Load categories and subcategories from actual folder structure."""
        if not os.path.exists(self.effects_path):
            return
        
        # Clear existing
        self.category_tree.clear()
        self.categories.clear()
        
        # Scan for actual category folders
        try:
            category_folders = sorted([f for f in os.listdir(self.effects_path)
                                     if os.path.isdir(os.path.join(self.effects_path, f))])
        except Exception:
            return
        
        for category_name in category_folders:
            category_path = os.path.join(self.effects_path, category_name)
            
            # Check for subfolders first
            subfolders = []
            direct_effects = []
            
            try:
                for item in os.listdir(category_path):
                    item_path = os.path.join(category_path, item)
                    if os.path.isdir(item_path):
                        # It's a subfolder - check if it has effects
                        sub_effects = [f for f in os.listdir(item_path)
                                     if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
                        if sub_effects:
                            subfolders.append((item, len(sub_effects)))
                    elif item.lower().endswith(('.png', '.jpg', '.jpeg')):
                        # It's a direct effect file
                        direct_effects.append(item)
            except Exception:
                continue
            
            # Skip empty categories
            if not subfolders and not direct_effects:
                continue
            
            # Create category item
            total_effects = len(direct_effects) + sum(count for _, count in subfolders)
            cat_item = QTreeWidgetItem([f"▸ {category_name} ({total_effects})"])
            cat_item.setData(0, Qt.ItemDataRole.UserRole, ('category', category_name))
            cat_item.setData(0, Qt.ItemDataRole.UserRole + 1, category_path)
            cat_item.setData(0, Qt.ItemDataRole.UserRole + 2, category_name)
            
            # If there are direct effects in the category folder, store them
            if direct_effects:
                self.categories[category_name] = [os.path.join(category_path, f) for f in sorted(direct_effects)]
            
            # Add subfolders as subcategories
            for subfolder_name, effect_count in sorted(subfolders):
                sub_item = QTreeWidgetItem([f"{subfolder_name} ({effect_count})"])
                sub_key = f"{category_name}/{subfolder_name}"
                sub_item.setData(0, Qt.ItemDataRole.UserRole, ('subcategory', sub_key))
                sub_item.setData(0, Qt.ItemDataRole.UserRole + 1, os.path.join(category_path, subfolder_name))
                cat_item.addChild(sub_item)
            
            self.category_tree.addTopLevelItem(cat_item)
        
        # Default selection: first category expanded and applied
        if self.category_tree.topLevelItemCount() > 0:
            first = self.category_tree.topLevelItem(0)
            first.setExpanded(True)
            self._set_category_label(first, True)
            self._on_category_selected(first, 0)

    def _on_category_selected(self, item, column):
        """Load and display effects from selected category or subcategory."""
        data = item.data(0, Qt.ItemDataRole.UserRole)
        folder_path = item.data(0, Qt.ItemDataRole.UserRole + 1)
        
        if not data or not folder_path:
            return
            
        item_type, key = data
        
        # Load effects on demand if not cached
        if key not in self.categories:
            try:
                if item_type == 'category':
                    # Load all effects from category folder (including subfolders)
                    all_effects = []
                    
                    # First, add direct effects from category folder
                    for f in os.listdir(folder_path):
                        if f.lower().endswith(('.png', '.jpg', '.jpeg')):
                            all_effects.append(os.path.join(folder_path, f))
                    
                    # Then, add effects from all subfolders
                    for item_name in os.listdir(folder_path):
                        subfolder_path = os.path.join(folder_path, item_name)
                        if os.path.isdir(subfolder_path):
                            for f in os.listdir(subfolder_path):
                                if f.lower().endswith(('.png', '.jpg', '.jpeg')):
                                    all_effects.append(os.path.join(subfolder_path, f))
                    
                    self.categories[key] = sorted(all_effects)
                    
                elif item_type == 'subcategory':
                    # Load effects only from the specific subfolder
                    subfolder_effects = [
                        os.path.join(folder_path, f)
                        for f in os.listdir(folder_path)
                        if f.lower().endswith(('.png', '.jpg', '.jpeg'))
                    ]
                    self.categories[key] = sorted(subfolder_effects)
                    
            except Exception:
                self.categories[key] = []
        
        # Update grid with effects
        if key in self.categories:
            self.current_effects = self.categories[key]
            self.effects_grid.set_effects(self.current_effects)

    def _is_category_item(self, item):
        data = item.data(0, Qt.ItemDataRole.UserRole)
        return bool(data and isinstance(data, tuple) and data[0] == 'category')

    def _set_category_label(self, item, expanded: bool):
        raw = item.data(0, Qt.ItemDataRole.UserRole + 2) or item.text(0)
        if '(' in raw:  # Keep count if present
            parts = raw.split('(')
            raw = parts[0].strip()
            count = '(' + parts[1] if len(parts) > 1 else ''
        else:
            count = ''
        prefix = '▾ ' if expanded else '▸ '
        item.setText(0, f"{prefix}{raw} {count}".strip())

    def _on_item_expanded(self, item):
        if self._is_category_item(item):
            self._set_category_label(item, True)

    def _on_item_collapsed(self, item):
        if self._is_category_item(item):
            self._set_category_label(item, False)
    
    def _do_search(self):
        """Perform search with result limit."""
        text = self.search_bar.text().lower().strip()
        if not text:
            # Restore current category
            if self.current_effects:
                self.effects_grid.set_effects(self.current_effects)
            return
        
        # Search through loaded categories first (faster)
        results = []
        max_results = 30
        
        # Search in already loaded categories
        for category_effects in self.categories.values():
            for effect_path in category_effects:
                filename = os.path.basename(effect_path).lower()
                if text in filename:
                    results.append(effect_path)
                    if len(results) >= max_results:
                        break
            if len(results) >= max_results:
                break
        
        # If not enough results, search filesystem
        if len(results) < max_results:
            try:
                for folder in os.listdir(self.effects_path):
                    if len(results) >= max_results:
                        break
                    folder_path = os.path.join(self.effects_path, folder)
                    if os.path.isdir(folder_path):
                        for f in os.listdir(folder_path):
                            if text in f.lower() and f.lower().endswith(('.png', '.jpg', '.jpeg')):
                                full_path = os.path.join(folder_path, f)
                                if full_path not in results:
                                    results.append(full_path)
                                    if len(results) >= max_results:
                                        break
            except Exception:
                pass
        
        self.effects_grid.set_effects(results)
    
    def clear_selection(self):
        """Clear the current effect selection."""
        if hasattr(self, 'effects_grid') and self.effects_grid:
            if self.effects_grid.selected_button:
                self.effects_grid.selected_button.set_selected(False)
                self.effects_grid.selected_button = None
    
    def closeEvent(self, event):
        """Comprehensive cleanup on close."""
        try:
            # Stop performance monitor
            if FinalEffectsPanel._performance_monitor:
                FinalEffectsPanel._performance_monitor.fps_timer.stop()
                
            # Stop and clean up loader thread
            if hasattr(self.effects_grid, 'loader') and self.effects_grid.loader:
                if self.effects_grid.loader.isRunning():
                    self.effects_grid.loader.quit()
                    self.effects_grid.loader.wait(100)  # Wait max 100ms
                
            # Clear cache
            ThumbnailCache().clear()
            
            # Force garbage collection
            gc.collect()
        except Exception:
            pass  # Don't let cleanup errors prevent closing
        
        super().closeEvent(event)
