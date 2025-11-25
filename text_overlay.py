from __future__ import annotations
from typing import Dict, Any
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QLabel, QSlider,
    QPushButton, QColorDialog, QSpinBox, QCheckBox, QGroupBox, QComboBox,
    QDialog, QDialogButtonBox, QFontComboBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor


class TextOverlayControls(QWidget):
    """
    Compact controls for a text overlay:
    - Toggle on/off
    - Text input
    - Font size
    - Color, Stroke color/width
    - Background box + opacity
    - Position sliders (X/Y normalized 0..100)
    - Scroll toggle + speed

    Emits overlayChanged(dict) on any change with a properties dict.
    """

    overlayChanged = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._building = False
        self._init_state()
        self._build_ui()
        self._hook_signals()

    def _init_state(self):
        self.props: Dict[str, Any] = {
            'visible': False,
            'text': 'Your text here',
            'font_size': 36,
            'font_family': '',
            'color': QColor(255, 255, 255, 255),
            'stroke_color': QColor(0, 0, 0, 255),
            'stroke_width': 3,
            'bg_enabled': False,
            'bg_color': QColor(0, 0, 0, 160),
            'pos_x': 50,  # percent
            'pos_y': 90,  # percent (near bottom)
            'anchor': 'center',  # left/center/right
            'scroll': False,
            'scroll_speed': 50,  # px/sec
        }

    def _build_ui(self):
        self._building = True
        root = QGroupBox('Text Overlay')
        root.setCheckable(True)
        root.setChecked(self.props['visible'])

        v = QVBoxLayout(root)
        v.setContentsMargins(8, 8, 8, 8)
        v.setSpacing(6)
        # Ensure children stay editable even when the group is unchecked
        # (QGroupBox disables children by default when unchecked)
        def _force_enable_children():
            for w in root.findChildren(QWidget):
                # Don't toggle the groupbox itself
                if w is root:
                    continue
                w.setEnabled(True)
        self._force_enable_children = _force_enable_children

        # Row: text
        row_text = QHBoxLayout()
        row_text.setSpacing(6)
        row_text.addWidget(QLabel('Text:'))
        self.txt_text = QLineEdit(self.props['text'])
        row_text.addWidget(self.txt_text)
        v.addLayout(row_text)

        # Row: font size / family / colors
        row_font = QHBoxLayout()
        row_font.addWidget(QLabel('Size:'))
        self.spin_size = QSpinBox()
        self.spin_size.setRange(8, 200)
        self.spin_size.setValue(self.props['font_size'])
        row_font.addWidget(self.spin_size)

        row_font.addWidget(QLabel('Font:'))
        self.font_combo = QFontComboBox()
        self.font_combo.setEditable(False)
        # Set current family if provided
        if self.props['font_family']:
            self.font_combo.setCurrentFont(self.font_combo.currentFont())
        row_font.addWidget(self.font_combo)

        v.addLayout(row_font)

        # Row: font colors
        row_font_colors = QHBoxLayout()
        self.btn_color = QPushButton('Text Color')
        self.btn_color.setStyleSheet(f'background-color: {self.props["color"].name()};')
        row_font_colors.addWidget(self.btn_color)
        self.btn_stroke_color = QPushButton('Stroke')
        self.btn_stroke_color.setStyleSheet(f'background-color: {self.props["stroke_color"].name()};')
        row_font_colors.addWidget(self.btn_stroke_color)
        row_font_colors.addWidget(QLabel('W'))
        self.spin_stroke = QSpinBox()
        self.spin_stroke.setRange(0, 20)
        self.spin_stroke.setValue(self.props['stroke_width'])
        row_font_colors.addWidget(self.spin_stroke)
        v.addLayout(row_font_colors)

        # Background box
        row_bg = QHBoxLayout()
        self.chk_bg = QCheckBox('Background')
        self.chk_bg.setChecked(self.props['bg_enabled'])
        row_bg.addWidget(self.chk_bg)
        self.btn_bg = QPushButton('Color')
        self._apply_bg_button_style()
        row_bg.addWidget(self.btn_bg)
        row_bg.addWidget(QLabel('Opacity'))
        self.spin_bg_opacity = QSpinBox()
        self.spin_bg_opacity.setRange(0, 255)
        self.spin_bg_opacity.setValue(self.props['bg_color'].alpha())
        row_bg.addWidget(self.spin_bg_opacity)
        v.addLayout(row_bg)

        # Anchor
        row_anchor = QHBoxLayout()
        row_anchor.addWidget(QLabel('Anchor'))
        self.combo_anchor = QComboBox()
        self.combo_anchor.addItems(['left', 'center', 'right'])
        self.combo_anchor.setCurrentText(self.props['anchor'])
        row_anchor.addWidget(self.combo_anchor)
        v.addLayout(row_anchor)

        # Position sliders
        row_pos = QHBoxLayout()
        row_pos.addWidget(QLabel('X'))
        self.slider_x = QSlider(Qt.Orientation.Horizontal)
        self.slider_x.setRange(0, 100)
        self.slider_x.setValue(self.props['pos_x'])
        row_pos.addWidget(self.slider_x)
        row_pos.addWidget(QLabel('Y'))
        self.slider_y = QSlider(Qt.Orientation.Horizontal)
        self.slider_y.setRange(0, 100)
        self.slider_y.setValue(self.props['pos_y'])
        row_pos.addWidget(self.slider_y)
        v.addLayout(row_pos)

        # Scrolling
        row_scroll = QHBoxLayout()
        self.chk_scroll = QCheckBox('Scroll')
        self.chk_scroll.setChecked(self.props['scroll'])
        row_scroll.addWidget(self.chk_scroll)
        row_scroll.addWidget(QLabel('Speed'))
        self.spin_scroll = QSpinBox()
        self.spin_scroll.setRange(10, 600)
        self.spin_scroll.setValue(self.props['scroll_speed'])
        row_scroll.addWidget(self.spin_scroll)
        v.addLayout(row_scroll)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(root)
        self.grp_root = root
        self._building = False

    def _apply_bg_button_style(self):
        c = self.props['bg_color']
        self.btn_bg.setStyleSheet(f'background-color: rgba({c.red()},{c.green()},{c.blue()},{c.alpha()});')

    def _pick_color(self, initial: QColor) -> QColor | None:
        c = QColorDialog.getColor(initial, self, 'Choose Color', QColorDialog.ColorDialogOption.ShowAlphaChannel)
        if c.isValid():
            return c
        return None

    def _hook_signals(self):
        self.grp_root.toggled.connect(self._on_visible_toggled)
        self.txt_text.textChanged.connect(self._on_text_changed)
        self.spin_size.valueChanged.connect(self._on_size_changed)
        self.btn_color.clicked.connect(self._on_color_clicked)
        self.btn_stroke_color.clicked.connect(self._on_stroke_color_clicked)
        self.spin_stroke.valueChanged.connect(self._on_stroke_width_changed)
        self.chk_bg.toggled.connect(self._on_bg_toggled)
        self.btn_bg.clicked.connect(self._on_bg_clicked)
        self.spin_bg_opacity.valueChanged.connect(self._on_bg_opacity_changed)
        self.slider_x.valueChanged.connect(self._on_pos_changed)
        self.slider_y.valueChanged.connect(self._on_pos_changed)
        self.combo_anchor.currentTextChanged.connect(self._on_anchor_changed)
        self.font_combo.currentFontChanged.connect(self._on_font_changed)
        self.chk_scroll.toggled.connect(self._on_scroll_toggled)
        self.spin_scroll.valueChanged.connect(self._on_scroll_speed_changed)
        # On init, make sure controls stay enabled regardless of checkbox state
        try:
            self._force_enable_children()
        except Exception:
            pass

    # Handlers
    def _on_visible_toggled(self, checked: bool):
        # Update visibility used by renderer, but keep controls editable even when off
        self.props['visible'] = checked
        try:
            self._force_enable_children()
        except Exception:
            pass
        self._emit()

    def _on_text_changed(self, s: str):
        self.props['text'] = s
        self._emit()

    def _on_size_changed(self, v: int):
        self.props['font_size'] = v
        self._emit()

    def _on_font_changed(self, f):
        try:
            self.props['font_family'] = f.family()
        except Exception:
            self.props['font_family'] = ''
        self._emit()

    def _on_color_clicked(self):
        c = self._pick_color(self.props['color'])
        if c:
            self.props['color'] = c
            self.btn_color.setStyleSheet(f'background-color: {c.name()};')
            self._emit()

    def _on_stroke_color_clicked(self):
        c = self._pick_color(self.props['stroke_color'])
        if c:
            self.props['stroke_color'] = c
            self.btn_stroke_color.setStyleSheet(f'background-color: {c.name()};')
            self._emit()

    def _on_stroke_width_changed(self, v: int):
        self.props['stroke_width'] = v
        self._emit()

    def _on_bg_toggled(self, checked: bool):
        self.props['bg_enabled'] = checked
        self._emit()

    def _on_bg_clicked(self):
        c = self._pick_color(self.props['bg_color'])
        if c:
            # preserve alpha via opacity spin
            c.setAlpha(self.spin_bg_opacity.value())
            self.props['bg_color'] = c
            self._apply_bg_button_style()
            self._emit()

    def _on_bg_opacity_changed(self, v: int):
        c = self.props['bg_color']
        c.setAlpha(v)
        self.props['bg_color'] = c
        self._apply_bg_button_style()
        self._emit()

    def _on_pos_changed(self, _v: int):
        self.props['pos_x'] = self.slider_x.value()
        self.props['pos_y'] = self.slider_y.value()
        self._emit()

    def _on_anchor_changed(self, s: str):
        self.props['anchor'] = s
        self._emit()

    def _on_scroll_toggled(self, checked: bool):
        self.props['scroll'] = checked
        self._emit()

    def _on_scroll_speed_changed(self, v: int):
        self.props['scroll_speed'] = v
        self._emit()

    def _emit(self):
        if self._building:
            return
        # Normalize to a serializable dict
        d: Dict[str, Any] = {
            **self.props,
            'color': self.props['color'].rgba(),
            'stroke_color': self.props['stroke_color'].rgba(),
            'bg_color': self.props['bg_color'].rgba(),
        }
        self.overlayChanged.emit(d)

    def apply_props(self, p: Dict[str, Any], emit: bool = True):
        """Apply incoming properties to controls. Accepts QColor or rgba-int for colors."""
        def _to_qcolor(v):
            if isinstance(v, QColor):
                return v
            try:
                c = QColor()
                c.setRgba(int(v))
                return c
            except Exception:
                return QColor(255, 255, 255)
        self._building = True
        try:
            self.props['visible'] = bool(p.get('visible', self.props['visible']))
            self.props['text'] = str(p.get('text', self.props['text']))
            self.props['font_size'] = int(p.get('font_size', self.props['font_size']))
            self.props['color'] = _to_qcolor(p.get('color', self.props['color']))
            self.props['stroke_color'] = _to_qcolor(p.get('stroke_color', self.props['stroke_color']))
            self.props['stroke_width'] = int(p.get('stroke_width', self.props['stroke_width']))
            self.props['bg_enabled'] = bool(p.get('bg_enabled', self.props['bg_enabled']))
            self.props['bg_color'] = _to_qcolor(p.get('bg_color', self.props['bg_color']))
            self.props['pos_x'] = int(p.get('pos_x', self.props['pos_x']))
            self.props['pos_y'] = int(p.get('pos_y', self.props['pos_y']))
            self.props['font_family'] = str(p.get('font_family', self.props['font_family']))
            self.props['anchor'] = str(p.get('anchor', self.props['anchor']))
            self.props['scroll'] = bool(p.get('scroll', self.props['scroll']))
            self.props['scroll_speed'] = int(p.get('scroll_speed', self.props['scroll_speed']))

            # Reflect on UI
            self.grp_root.setChecked(self.props['visible'])
            # Keep controls enabled regardless of visibility toggle
            try:
                self._force_enable_children()
            except Exception:
                pass
            self.txt_text.setText(self.props['text'])
            self.spin_size.setValue(self.props['font_size'])
            # Font family
            try:
                if self.props['font_family']:
                    self.font_combo.setCurrentText(self.props['font_family'])
            except Exception:
                pass
            self.btn_color.setStyleSheet(f'background-color: {self.props["color"].name()};')
            self.btn_stroke_color.setStyleSheet(f'background-color: {self.props["stroke_color"].name()};')
            self.spin_stroke.setValue(self.props['stroke_width'])
            self.chk_bg.setChecked(self.props['bg_enabled'])
            self.spin_bg_opacity.setValue(self.props['bg_color'].alpha())
            self._apply_bg_button_style()
            self.slider_x.setValue(self.props['pos_x'])
            self.slider_y.setValue(self.props['pos_y'])
            idx = self.combo_anchor.findText(self.props['anchor'])
            if idx >= 0:
                self.combo_anchor.setCurrentIndex(idx)
            self.chk_scroll.setChecked(self.props['scroll'])
            self.spin_scroll.setValue(self.props['scroll_speed'])
        finally:
            self._building = False
        if emit:
            self._emit()


class TextOverlayMiniBar(QWidget):
    """
    Compact 1-row controls intended to sit beside 'Switching Controls':
    - Visible toggle
    - Inline text edit
    - Font size spin
    - Color button
    - Advanced... button opens full TextOverlayControls dialog
    Emits overlayChanged(dict) with the same shape as TextOverlayControls (colors as rgba ints)
    """

    overlayChanged = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.props_ref = TextOverlayControls(self)  # reuse logic/state
        self.props_ref.hide()
        self._build_ui()
        self._wire()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(6, 2, 6, 2)
        root.setSpacing(2)

        row1 = QHBoxLayout()
        row1.setSpacing(6)
        self.chk_visible = QCheckBox('Text Overlay')
        self.chk_visible.setChecked(self.props_ref.props['visible'])
        row1.addWidget(self.chk_visible)
        row1.addWidget(QLabel('Text:'))
        self.txt = QLineEdit(self.props_ref.props['text'])
        self.txt.setPlaceholderText('Your text...')
        self.txt.setMinimumWidth(130)
        self.txt.setMaximumWidth(200)
        row1.addWidget(self.txt)
        row1.addWidget(QLabel('Size'))
        self.size = QSpinBox()
        self.size.setRange(8, 200)
        self.size.setValue(self.props_ref.props['font_size'])
        self.size.setFixedWidth(56)
        row1.addWidget(self.size)
        row1.addStretch(1)

        row2 = QHBoxLayout()
        row2.setSpacing(6)
        row2.addWidget(QLabel('Font'))
        self.font_combo_mini = QFontComboBox()
        self.font_combo_mini.setEditable(False)
        self.font_combo_mini.setMaximumWidth(180)
        row2.addWidget(self.font_combo_mini)
        self.btn_color = QPushButton('Color')
        self.btn_color.setStyleSheet(f'background-color: {self.props_ref.props["color"].name()};')
        self.btn_color.setFixedWidth(60)
        row2.addWidget(self.btn_color)
        self.btn_adv = QPushButton('Advanced…')
        self.btn_adv.setFixedWidth(92)
        row2.addWidget(self.btn_adv)
        row2.addStretch(1)

        root.addLayout(row1)
        root.addLayout(row2)
        # Keep width compact
        self.setMaximumWidth(500)

    def _emit(self):
        d = {
            **self.props_ref.props,
            'visible': self.chk_visible.isChecked(),
            'text': self.txt.text(),
            'font_size': self.size.value(),
            'font_family': self.props_ref.props.get('font_family', ''),
            'color': self.props_ref.props['color'].rgba(),
            'stroke_color': self.props_ref.props['stroke_color'].rgba(),
            'bg_color': self.props_ref.props['bg_color'].rgba(),
        }
        self.overlayChanged.emit(d)

    def _wire(self):
        self.chk_visible.toggled.connect(lambda _: self._emit())
        self.txt.textChanged.connect(lambda _: self._emit())
        self.size.valueChanged.connect(lambda _: self._emit())
        self.btn_color.clicked.connect(self._pick_color)
        self.btn_adv.clicked.connect(self._open_advanced)
        self.font_combo_mini.currentFontChanged.connect(self._on_font_changed_mini)

        # Relay updates from advanced panel back to mini bar
        self.props_ref.overlayChanged.connect(self._on_advanced_changed)

    def _pick_color(self):
        c = QColorDialog.getColor(self.props_ref.props['color'], self, 'Choose Text Color', QColorDialog.ColorDialogOption.ShowAlphaChannel)
        if c.isValid():
            self.props_ref.props['color'] = c
            self.btn_color.setStyleSheet(f'background-color: {c.name()};')
            self._emit()

    def _on_font_changed_mini(self, f):
        try:
            self.props_ref.props['font_family'] = f.family()
        except Exception:
            self.props_ref.props['font_family'] = ''
        self._emit()

    def _open_advanced(self):
        # Open modern dialog with live preview; apply only on Save
        from text_overlay_settings_dialog import TextOverlaySettingsDialog
        from PyQt6.QtGui import QColor
        from PyQt6.QtWidgets import QDialog

        dlg = TextOverlaySettingsDialog(self)

        # Seed dialog with current properties
        p = self.props_ref.props
        seed = {
            'text': p.get('text', ''),
            'font_family': p.get('font_family', ''),
            'font_size': p.get('font_size', 36),
            'text_color': p.get('color', QColor(255, 255, 255)).name(),
            'stroke_color': p.get('stroke_color', QColor(0, 0, 0)).name(),
            'stroke_width': p.get('stroke_width', 3),
            'position_x': p.get('pos_x', 50),
            'position_y': p.get('pos_y', 50),
            'alignment': p.get('anchor', 'center'),
            'bg_enabled': p.get('bg_enabled', False),
            'bg_color': p.get('bg_color', QColor(0, 0, 0)).name(),
            'bg_opacity': float(p.get('bg_color', QColor(0, 0, 0, 0)).alpha()) / 255.0,
        }
        try:
            dlg.apply_settings(seed)
        except Exception:
            pass

        if dlg.exec() == QDialog.DialogCode.Accepted:
            s = dlg.get_settings()
            pr = self.props_ref.props
            # Apply chosen settings
            pr['text'] = s.get('text', pr['text'])
            pr['font_family'] = s.get('font_family', pr.get('font_family', ''))
            try:
                pr['font_size'] = int(s.get('font_size', pr['font_size']))
            except Exception:
                pass
            pr['color'] = QColor(s.get('text_color', pr['color'].name()))
            pr['stroke_color'] = QColor(s.get('stroke_color', pr['stroke_color'].name()))
            try:
                pr['stroke_width'] = int(s.get('stroke_width', pr['stroke_width']))
            except Exception:
                pass
            try:
                pr['pos_x'] = int(s.get('position_x', pr['pos_x']))
                pr['pos_y'] = int(s.get('position_y', pr['pos_y']))
            except Exception:
                pass
            pr['anchor'] = str(s.get('alignment', pr['anchor']))
            pr['bg_enabled'] = bool(s.get('bg_enabled', pr['bg_enabled']))
            bgc = QColor(s.get('bg_color', pr['bg_color'].name()))
            try:
                a = int(round(float(s.get('bg_opacity', pr['bg_color'].alpha()/255.0)) * 255))
                a = max(0, min(255, a))
                bgc.setAlpha(a)
            except Exception:
                pass
            pr['bg_color'] = bgc

            # Reflect on mini UI immediately
            self.txt.setText(pr['text'])
            self.size.setValue(pr['font_size'])
            try:
                if pr.get('font_family'):
                    self.font_combo_mini.setCurrentText(pr['font_family'])
            except Exception:
                pass
            self.btn_color.setStyleSheet(f'background-color: {pr["color"].name()};')

            # Emit unified props for renderer
            self._emit()

    def _on_advanced_changed(self, d: dict):
        # Keep mini inputs in sync when user tweaks advanced options
        try:
            self.chk_visible.setChecked(bool(d.get('visible', True)))
        except Exception:
            pass
        try:
            self.size.setValue(int(d.get('font_size', self.size.value())))
        except Exception:
            pass
        try:
            self.txt.setText(str(d.get('text', self.txt.text())))
        except Exception:
            pass
        try:
            fam = str(d.get('font_family', self.props_ref.props.get('font_family', '')))
            if fam:
                self.font_combo_mini.setCurrentText(fam)
        except Exception:
            pass
        # Emit unified props to renderer
        self.overlayChanged.emit(d)
