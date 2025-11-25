from __future__ import annotations
from typing import Callable, Optional, Tuple
from dataclasses import dataclass

from PyQt6.QtCore import QObject, QTimer, QSize, QRect, QRectF, QEasingCurve, QElapsedTimer, Qt
from PyQt6.QtGui import QImage, QPainter, QColor, QPainterPath
import math

try:
    import cv2  # type: ignore
    import numpy as np  # type: ignore
    _HAS_CV = True
except Exception:
    _HAS_CV = False
    np = None  # type: ignore


@dataclass
class TransitionSpec:
    name: str
    duration_ms: int = 400
    easing: str = "ease_in_out"  # linear | ease_in | ease_out | ease_in_out


class TransitionManager(QObject):
    """
    Non-intrusive transition engine.

    Usage:
      mgr = TransitionManager(parent)
      mgr.start_transition(
          current_image, next_image,
          transition_type="fade", duration_ms=400,
          on_frame=display_callback, on_done=done_callback
      )

    This module is standalone and does not modify existing app behavior.
    The caller is responsible for supplying full-size, composited QImage frames
    (e.g., via GraphicsOutputWidget.render_to_image(size)).
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._on_tick)
        try:
            # Use precise timer for smoother cadence
            self._timer.setTimerType(Qt.TimerType.PreciseTimer)
        except Exception:
            pass
        self._interval_ms = 8  # ~120 fps for ultra-smooth motion
        self._t_elapsed = 0
        self._elapsed = QElapsedTimer()
        self._spec: Optional[TransitionSpec] = None
        self._img_a: Optional[QImage] = None
        self._img_b: Optional[QImage] = None
        self._on_frame: Optional[Callable[[QImage], None]] = None
        self._on_done: Optional[Callable[[], None]] = None
        # Enhanced butter mode: temporal supersampling with more samples
        self._butter_samples: int = 3  # 1 = off; 3 = light smoothing; 5 = ultra
        self._butter_delta: float = 0.005  # progress offset between samples (smaller = smoother)

    # --- Public API ---
    def start_transition(
        self,
        current_img: QImage,
        next_img: QImage,
        transition_type: str = "fade",
        duration_ms: int = 1000,  # Increased default duration for smoother transitions
        easing: str = "ease_in_out_quad",  # Smoother default easing
        on_frame: Optional[Callable[[QImage], None]] = None,
        on_done: Optional[Callable[[], None]] = None,
    ) -> None:
        if current_img is None or current_img.isNull() or next_img is None or next_img.isNull():
            return
        if current_img.size() != next_img.size():
            # Letterbox next_img to match current size (no crop, preserve aspect)
            try:
                target_size = current_img.size()
                scaled = next_img.scaled(target_size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                canvas = QImage(target_size, QImage.Format.Format_ARGB32)
                canvas.fill(QColor(0, 0, 0, 255))
                p = QPainter(canvas)
                try:
                    x = (target_size.width() - scaled.width()) // 2
                    y = (target_size.height() - scaled.height()) // 2
                    p.drawImage(x, y, scaled)
                finally:
                    p.end()
                next_img = canvas
            except Exception:
                # Fallback to simple smooth scale
                next_img = next_img.scaled(current_img.size(), Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)
        # Debug sizes
        try:
            print(f"[Transition] start {transition_type} A={current_img.width()}x{current_img.height()} B={next_img.width()}x{next_img.height()} dur={duration_ms}")
        except Exception:
            pass
        # Pre-normalize format for faster painting
        try:
            if current_img.format() != QImage.Format.Format_ARGB32:
                current_img = current_img.convertToFormat(QImage.Format.Format_ARGB32)
            if next_img.format() != QImage.Format.Format_ARGB32:
                next_img = next_img.convertToFormat(QImage.Format.Format_ARGB32)
        except Exception:
            pass
        self._img_a = current_img.copy()
        self._img_b = next_img.copy()
        self._spec = TransitionSpec(name=transition_type.lower().strip(), duration_ms=max(50, int(duration_ms)), easing=easing)
        self._on_frame = on_frame
        self._on_done = on_done
        self._t_elapsed = 0
        try:
            self._elapsed.invalidate()
            self._elapsed.start()
        except Exception:
            pass
        if self._timer.isActive():
            self._timer.stop()
        self._timer.start(self._interval_ms)
        # Emit first frame immediately
        self._emit_frame(self._render_progress(0.0))

    def is_running(self) -> bool:
        return self._timer.isActive()

    def stop(self):
        if self._timer.isActive():
            self._timer.stop()

    # --- Internal ---
    def _on_tick(self):
        if not self._spec or not self._img_a or not self._img_b:
            self.stop(); return
        try:
            # Use real elapsed time for smoother animation
            if self._elapsed.isValid():
                self._t_elapsed = int(self._elapsed.elapsed())
            else:
                self._t_elapsed += self._interval_ms
            p = min(1.0, max(0.0, self._t_elapsed / float(max(1, self._spec.duration_ms))))
            pe = self._apply_easing(p, self._spec.easing)
            frame = self._render_progress_smoothed(pe)
            self._emit_frame(frame)
            if p >= 1.0:
                self.stop()
                if self._on_done:
                    try:
                        self._on_done()
                    except Exception:
                        pass
        except Exception:
            # Any error: stop gracefully and emit final frame B
            try:
                self.stop()
                self._emit_frame(self._img_b)
                if self._on_done:
                    self._on_done()
            except Exception:
                pass

    def _emit_frame(self, img: Optional[QImage]):
        if img is None or img.isNull():
            return
        cb = self._on_frame
        if cb:
            try:
                cb(img)
            except Exception:
                pass

    def _apply_easing(self, p: float, easing: str) -> float:
        """Apply easing function to progress value (0-1)."""
        if easing == "linear":
            return p
        elif easing == "ease_in":
            return p * p
        elif easing == "ease_out":
            return 1.0 - (1.0 - p) * (1.0 - p)
        elif easing == "ease_in_out_quad":
            # Smoother quadratic easing
            p *= 2.0
            if p < 1.0:
                return 0.5 * p * p
            p -= 1.0
            return -0.5 * (p * (p - 2) - 1)
        elif easing == "ease_in_out_cubic":
            # Even smoother cubic easing
            p *= 2.0
            if p < 1.0:
                return 0.5 * p * p * p
            p -= 2.0
            return 0.5 * (p * p * p + 2)
        else:  # Default ease_in_out (quadratic)
            if p < 0.5:
                return 2.0 * p * p
            p = 1.0 - p
            return 1.0 - 2.0 * p * p

    # --- Rendering implementations ---
    def _render_progress_smoothed(self, p_center: float) -> QImage:
        """Temporal supersampling: average multiple nearby progress frames for extra smoothness."""
        try:
            n = int(max(1, self._butter_samples))
        except Exception:
            n = 1
        if n <= 1:
            return self._render_progress(p_center)
        # Build list of sample progress values around center
        half = n // 2
        samples = []
        for i in range(-half, half + 1):
            pp = max(0.0, min(1.0, p_center + i * self._butter_delta))
            samples.append(pp)
        # Render first to get size
        img0 = self._render_progress(samples[0])
        if img0 is None or img0.isNull():
            return self._render_progress(p_center)
        out = QImage(img0.size(), QImage.Format.Format_ARGB32)
        out.fill(QColor(0, 0, 0, 0))
        painter = QPainter(out)
        try:
            painter.setRenderHints(QPainter.RenderHint.SmoothPixmapTransform | QPainter.RenderHint.Antialiasing, on=True)
            w = 1.0 / float(len(samples))
            for pp in samples:
                img = self._render_progress(pp)
                if img is None or img.isNull():
                    continue
                painter.setOpacity(w)
                painter.drawImage(0, 0, img)
        finally:
            painter.end()
        return out
    def _render_progress(self, p: float) -> QImage:
        a = self._img_a
        b = self._img_b
        spec = self._spec
        assert a and b and spec
        t = spec.name
        if t in ("fade",):
            return self._r_fade(a, b, p)
        if t in ("slide left", "slide_left", "slide-left"):
            return self._r_slide(a, b, p, axis="x", direction=+1)
        if t in ("slide right", "slide_right", "slide-right"):
            return self._r_slide(a, b, p, axis="x", direction=-1)
        if t in ("slide up", "slide_up", "slide-up"):
            return self._r_slide(a, b, p, axis="y", direction=+1)
        if t in ("slide down", "slide_down", "slide-down"):
            return self._r_slide(a, b, p, axis="y", direction=-1)
        if t in ("wipe horizontal", "wipe_h", "wipe-x"):
            return self._r_wipe(a, b, p, axis="x")
        if t in ("wipe vertical", "wipe_v", "wipe-y"):
            return self._r_wipe(a, b, p, axis="y")
        if t in ("zoom in", "zoom_in"):
            return self._r_zoom(a, b, p, zoom_in=True)
        if t in ("zoom out", "zoom_out"):
            return self._r_zoom(a, b, p, zoom_in=False)
        if t in ("circle reveal", "circle"):
            return self._r_circle_reveal(a, b, p)
        if t in ("blur dissolve", "blur"):
            return self._r_blur_dissolve(a, b, p)
        if t in ("pixelate dissolve", "pixelate"):
            return self._r_pixelate_dissolve(a, b, p)
        if t in ("parallax slide", "parallax"):
            return self._r_parallax(a, b, p)
        if t in ("diagonal wipe", "diag wipe", "diagonal"):
            return self._r_diagonal_wipe(a, b, p)
        if t in ("curtain open vertical", "curtain open (vertical)", "curtain v"):
            return self._r_curtain(a, b, p, orientation="v")
        if t in ("curtain open horizontal", "curtain open (horizontal)", "curtain h"):
            return self._r_curtain(a, b, p, orientation="h")
        if t in ("random blocks", "random blocks transition"):
            return self._r_random_blocks(a, b, p)
        if t in ("fade to black", "fade to black + next frame fade in", "fade_black"):
            return self._r_fade_to_black(a, b, p)
        if t in ("push left", "push_left"):
            return self._r_push(a, b, p, axis="x", direction=+1)
        if t in ("push right", "push_right"):
            return self._r_push(a, b, p, axis="x", direction=-1)
        if t in ("push up", "push_up"):
            return self._r_push(a, b, p, axis="y", direction=+1)
        if t in ("push down", "push_down"):
            return self._r_push(a, b, p, axis="y", direction=-1)
        if t in ("iris in", "iris_in"):
            return self._r_iris(a, b, p, iris_in=True)
        if t in ("iris out", "iris_out"):
            return self._r_iris(a, b, p, iris_in=False)
        if t in ("flip left", "flip_left"):
            return self._r_flip(a, b, p, direction="left")
        if t in ("flip right", "flip_right"):
            return self._r_flip(a, b, p, direction="right")
        if t in ("checkerboard",):
            return self._r_checkerboard(a, b, p)
        if t in ("venetian blinds", "venetian_blinds", "blinds"):
            return self._r_venetian_blinds(a, b, p)
        if t in ("barn door", "barn_door"):
            return self._r_barn_door(a, b, p)
        if t in ("clock wipe", "clock_wipe", "clock"):
            return self._r_clock_wipe(a, b, p)
        # Fallback
        return self._r_fade(a, b, p)

    # --- Helper renderers ---
    def _blank(self, size: QSize, color: QColor = QColor(0, 0, 0, 255)) -> QImage:
        img = QImage(size, QImage.Format.Format_ARGB32)
        img.fill(color)
        return img

    def _r_fade(self, a: QImage, b: QImage, p: float) -> QImage:
        size = a.size()
        out = self._blank(size, QColor(0, 0, 0, 0))
        painter = QPainter(out)
        try:
            # Improve quality of scaling/alpha
            painter.setRenderHints(QPainter.RenderHint.SmoothPixmapTransform | QPainter.RenderHint.Antialiasing, on=True)
            alpha_a = int(round(255 * (1.0 - p)))
            alpha_b = 255
            painter.setOpacity(1.0)
            if alpha_a > 0:
                painter.setOpacity(alpha_a / 255.0)
                painter.drawImage(0, 0, a)
            if p > 0:
                painter.setOpacity(p)
                painter.drawImage(0, 0, b)
        finally:
            painter.end()
        return out

    def _r_slide(self, a: QImage, b: QImage, p: float, *, axis: str, direction: int) -> QImage:
        w, h = a.width(), a.height()
        out = self._blank(a.size(), QColor(0, 0, 0, 255))
        painter = QPainter(out)
        try:
            painter.setRenderHints(QPainter.RenderHint.SmoothPixmapTransform | QPainter.RenderHint.Antialiasing, on=True)
            if axis == "x":
                dx_a = float(direction * -p * w)
                dx_b = dx_a + float(w * direction)
                painter.drawImage(QRectF(dx_a, 0.0, float(w), float(h)), a)
                painter.drawImage(QRectF(dx_b, 0.0, float(w), float(h)), b)
            else:
                dy_a = float(direction * -p * h)
                dy_b = dy_a + float(h * direction)
                painter.drawImage(QRectF(0.0, dy_a, float(w), float(h)), a)
                painter.drawImage(QRectF(0.0, dy_b, float(w), float(h)), b)
        finally:
            painter.end()
        return out

    def _r_wipe(self, a: QImage, b: QImage, p: float, *, axis: str) -> QImage:
        out = self._blank(a.size(), QColor(0, 0, 0, 255))
        painter = QPainter(out)
        try:
            painter.setRenderHints(QPainter.RenderHint.SmoothPixmapTransform | QPainter.RenderHint.Antialiasing, on=True)
            painter.drawImage(0, 0, a)
            painter.save()
            path = QPainterPath()
            if axis == "x":
                w = float(a.width() * p)
                path.addRect(QRectF(0.0, 0.0, w, float(a.height())))
            else:
                h = float(a.height() * p)
                path.addRect(QRectF(0.0, 0.0, float(a.width()), h))
            painter.setClipPath(path)
            painter.drawImage(0, 0, b)
            painter.restore()
        except Exception:
            # Defensive fallback to fade to avoid crashes if any issue arises
            try:
                painter.restore()
            except Exception:
                pass
            return self._r_fade(a, b, p)
        finally:
            painter.end()
        return out

    def _r_zoom(self, a: QImage, b: QImage, p: float, *, zoom_in: bool) -> QImage:
        out = self._blank(a.size(), QColor(0, 0, 0, 255))
        painter = QPainter(out)
        try:
            painter.setRenderHints(QPainter.RenderHint.SmoothPixmapTransform | QPainter.RenderHint.Antialiasing, on=True)
            # Slight zoom on A while blending to B
            factor = 1.0 + (0.08 * p if zoom_in else -0.08 * p)
            wa, ha = a.width(), a.height()
            sw, sh = float(wa) * factor, float(ha) * factor
            ax = (float(wa) - sw) / 2.0
            ay = (float(ha) - sh) / 2.0
            painter.drawImage(QRectF(ax, ay, sw, sh), a)
            painter.setOpacity(p)
            painter.drawImage(0, 0, b)
        finally:
            painter.end()
        return out

    def _r_circle_reveal(self, a: QImage, b: QImage, p: float) -> QImage:
        out = self._blank(a.size(), QColor(0, 0, 0, 255))
        painter = QPainter(out)
        try:
            painter.setRenderHints(QPainter.RenderHint.SmoothPixmapTransform | QPainter.RenderHint.Antialiasing, on=True)
            painter.drawImage(0, 0, a)
            cx, cy = a.width() // 2, a.height() // 2
            max_r = int((a.width() ** 2 + a.height() ** 2) ** 0.5)
            r = int(max(1, max_r * p))
            path = QPainterPath()
            path.addEllipse(cx - r, cy - r, 2 * r, 2 * r)
            painter.setClipPath(path)
            painter.drawImage(0, 0, b)
        finally:
            painter.end()
        return out

    def _r_blur_dissolve(self, a: QImage, b: QImage, p: float) -> QImage:
        # Prefer OpenCV-based blur if available for quality and speed
        if _HAS_CV:
            try:
                a_cv = self._qimage_to_cv(a)
                b_cv = self._qimage_to_cv(b)
                k = max(1, int(3 + p * 15))
                if k % 2 == 0:
                    k += 1
                a_blur = cv2.GaussianBlur(a_cv, (k, k), 0)
                blend = cv2.addWeighted(a_blur, 1.0 - p, b_cv, p, 0.0)
                return self._cv_to_qimage(blend, a.size())
            except Exception:
                pass  # fall back below

        # Fallback: downscale-upscale to approximate blur
        scale = max(1, int(8 - 7 * (1.0 - p)))
        small = a.scaled(max(1, a.width() // scale), max(1, a.height() // scale))
        a_pix = small.scaled(a.size())
        out = self._blank(a.size(), QColor(0, 0, 0, 0))
        painter = QPainter(out)
        try:
            painter.setRenderHints(QPainter.RenderHint.SmoothPixmapTransform | QPainter.RenderHint.Antialiasing, on=True)
            painter.drawImage(0, 0, a_pix)
            painter.setOpacity(p)
            painter.drawImage(0, 0, b)
        finally:
            painter.end()
        return out

    def _r_pixelate_dissolve(self, a: QImage, b: QImage, p: float) -> QImage:
        # Pixel size grows for A, then blend B on top
        block = max(2, int(2 + p * 24))
        small = a.scaled(max(1, a.width() // block), max(1, a.height() // block))
        a_pix = small.scaled(a.size())
        out = self._blank(a.size(), QColor(0, 0, 0, 0))
        painter = QPainter(out)
        try:
            painter.setRenderHints(QPainter.RenderHint.SmoothPixmapTransform | QPainter.RenderHint.Antialiasing, on=True)
            painter.drawImage(0, 0, a_pix)
            painter.setOpacity(p)
            painter.drawImage(0, 0, b)
        finally:
            painter.end()
        return out

    def _r_parallax(self, a: QImage, b: QImage, p: float) -> QImage:
        # Foreground (b) moves slightly faster than background (a)
        w, h = a.width(), a.height()
        shift_bg = float(-p * w * 0.5)
        shift_fg = float((1.0 - p) * w * 0.5)
        out = self._blank(a.size(), QColor(0, 0, 0, 255))
        painter = QPainter(out)
        try:
            painter.setRenderHints(QPainter.RenderHint.SmoothPixmapTransform | QPainter.RenderHint.Antialiasing, on=True)
            painter.drawImage(QRectF(shift_bg, 0.0, float(w), float(h)), a)
            painter.setOpacity(min(1.0, p + 0.2))
            painter.drawImage(QRectF(shift_fg - float(w), 0.0, float(w), float(h)), b)
        finally:
            painter.end()
        return out

    def _r_diagonal_wipe(self, a: QImage, b: QImage, p: float) -> QImage:
        out = self._blank(a.size(), QColor(0, 0, 0, 255))
        painter = QPainter(out)
        try:
            painter.setRenderHints(QPainter.RenderHint.SmoothPixmapTransform | QPainter.RenderHint.Antialiasing, on=True)
            painter.drawImage(0, 0, a)
            path = QPainterPath()
            w, h = a.width(), a.height()
            # Diagonal line from top-left to bottom-right; progress expands the revealed polygon
            x = int(w * p)
            path.moveTo(0, 0)
            path.lineTo(x, 0)
            path.lineTo(0, x)
            path.closeSubpath()
            painter.setClipPath(path)
            painter.drawImage(0, 0, b)
        finally:
            painter.end()
        return out

    def _r_curtain(self, a: QImage, b: QImage, p: float, *, orientation: str) -> QImage:
        out = self._blank(a.size(), QColor(0, 0, 0, 255))
        painter = QPainter(out)
        try:
            painter.setRenderHints(QPainter.RenderHint.SmoothPixmapTransform | QPainter.RenderHint.Antialiasing, on=True)
            painter.drawImage(0, 0, a)
            painter.save()
            w, h = a.width(), a.height()
            if orientation == "v":
                half = w // 2
                delta = int(half * p)
                # Left and right curtains reveal center
                painter.setClipRect(QRect(half - delta, 0, 2 * delta, h))
            else:
                half = h // 2
                delta = int(half * p)
                painter.setClipRect(QRect(0, half - delta, w, 2 * delta))
            painter.drawImage(0, 0, b)
            painter.restore()
        finally:
            painter.end()
        return out

    def _r_random_blocks(self, a: QImage, b: QImage, p: float) -> QImage:
        # Deterministic pseudo-random block reveal based on grid
        cols, rows = 16, 9
        total = cols * rows
        reveal = int(total * p)
        out = self._blank(a.size(), QColor(0, 0, 0, 255))
        painter = QPainter(out)
        try:
            painter.setRenderHints(QPainter.RenderHint.SmoothPixmapTransform | QPainter.RenderHint.Antialiasing, on=True)
            painter.drawImage(0, 0, a)
            import random
            rng = random.Random(42)  # deterministic
            order = list(range(total))
            rng.shuffle(order)
            w, h = a.width(), a.height()
            bw, bh = w // cols, h // rows
            painter.save()
            path = QPainterPath()
            for i in range(reveal):
                idx = order[i]
                cx = idx % cols
                cy = idx // cols
                path.addRect(QRect(cx * bw, cy * bh, bw + 1, bh + 1))
            painter.setClipPath(path)
            painter.drawImage(0, 0, b)
            painter.restore()
        finally:
            painter.end()
        return out

    def _r_fade_to_black(self, a: QImage, b: QImage, p: float) -> QImage:
        # First half fade to black; second half fade in next
        if p < 0.5:
            k = p / 0.5
            out = self._blank(a.size(), QColor(0, 0, 0, 255))
            painter = QPainter(out)
            try:
                painter.setRenderHints(QPainter.RenderHint.SmoothPixmapTransform | QPainter.RenderHint.Antialiasing, on=True)
                painter.setOpacity(1.0 - k)
                painter.drawImage(0, 0, a)
                overlay = QColor(0, 0, 0, int(255 * k))
                painter.fillRect(QRect(0, 0, a.width(), a.height()), overlay)
            finally:
                painter.end()
            return out
        else:
            k = (p - 0.5) / 0.5
            out = self._blank(b.size(), QColor(0, 0, 0, 255))
            painter = QPainter(out)
            try:
                painter.setRenderHints(QPainter.RenderHint.SmoothPixmapTransform | QPainter.RenderHint.Antialiasing, on=True)
                painter.fillRect(QRect(0, 0, b.width(), b.height()), QColor(0, 0, 0, 255))
                painter.setOpacity(k)
                painter.drawImage(0, 0, b)
            finally:
                painter.end()
            return out

    def _r_push(self, a: QImage, b: QImage, p: float, *, axis: str, direction: int) -> QImage:
        # Push: both frames move together, no gap between them
        w, h = a.width(), a.height()
        out = self._blank(a.size(), QColor(0, 0, 0, 255))
        painter = QPainter(out)
        try:
            painter.setRenderHints(QPainter.RenderHint.SmoothPixmapTransform | QPainter.RenderHint.Antialiasing, on=True)
            if axis == "x":
                offset = float(direction * p * w)
                painter.drawImage(QRectF(offset, 0.0, float(w), float(h)), a)
                painter.drawImage(QRectF(offset - float(w * direction), 0.0, float(w), float(h)), b)
            else:
                offset = float(direction * p * h)
                painter.drawImage(QRectF(0.0, offset, float(w), float(h)), a)
                painter.drawImage(QRectF(0.0, offset - float(h * direction), float(w), float(h)), b)
        finally:
            painter.end()
        return out

    def _r_iris(self, a: QImage, b: QImage, p: float, *, iris_in: bool) -> QImage:
        # Iris: circular mask that grows or shrinks
        out = self._blank(a.size(), QColor(0, 0, 0, 255))
        painter = QPainter(out)
        try:
            painter.setRenderHints(QPainter.RenderHint.SmoothPixmapTransform | QPainter.RenderHint.Antialiasing, on=True)
            cx, cy = a.width() // 2, a.height() // 2
            max_r = int((a.width() ** 2 + a.height() ** 2) ** 0.5)
            if iris_in:
                # Start full, shrink to reveal B
                r = int(max_r * (1.0 - p))
                painter.drawImage(0, 0, b)
                if r > 0:
                    path = QPainterPath()
                    path.addEllipse(cx - r, cy - r, 2 * r, 2 * r)
                    painter.setClipPath(path)
                    painter.drawImage(0, 0, a)
            else:
                # Start small, grow to reveal B
                r = int(max_r * p)
                painter.drawImage(0, 0, a)
                if r > 0:
                    path = QPainterPath()
                    path.addEllipse(cx - r, cy - r, 2 * r, 2 * r)
                    painter.setClipPath(path)
                    painter.drawImage(0, 0, b)
        finally:
            painter.end()
        return out

    def _r_flip(self, a: QImage, b: QImage, p: float, *, direction: str) -> QImage:
        # Simple flip effect using scale transform
        out = self._blank(a.size(), QColor(0, 0, 0, 255))
        painter = QPainter(out)
        try:
            painter.setRenderHints(QPainter.RenderHint.SmoothPixmapTransform | QPainter.RenderHint.Antialiasing, on=True)
            w, h = float(a.width()), float(a.height())
            if p < 0.5:
                # First half: scale A down horizontally
                scale_x = 1.0 - (p * 2.0)
                if direction == "left":
                    painter.drawImage(QRectF(w * (1.0 - scale_x), 0.0, w * scale_x, h), a)
                else:
                    painter.drawImage(QRectF(0.0, 0.0, w * scale_x, h), a)
            else:
                # Second half: scale B up horizontally
                scale_x = (p - 0.5) * 2.0
                if direction == "left":
                    painter.drawImage(QRectF(w * (1.0 - scale_x), 0.0, w * scale_x, h), b)
                else:
                    painter.drawImage(QRectF(0.0, 0.0, w * scale_x, h), b)
        finally:
            painter.end()
        return out

    def _r_checkerboard(self, a: QImage, b: QImage, p: float) -> QImage:
        # Optimized checkerboard with fewer blocks for performance
        cols, rows = 8, 6  # Reduced from 16x9 for better performance
        out = self._blank(a.size(), QColor(0, 0, 0, 255))
        painter = QPainter(out)
        try:
            painter.setRenderHints(QPainter.RenderHint.SmoothPixmapTransform | QPainter.RenderHint.Antialiasing, on=True)
            painter.drawImage(0, 0, a)
            w, h = a.width(), a.height()
            bw, bh = w // cols, h // rows
            painter.save()
            path = QPainterPath()
            for row in range(rows):
                for col in range(cols):
                    # Checkerboard pattern with progress threshold
                    if (row + col) % 2 == 0 and p > (row * cols + col) / float(cols * rows):
                        path.addRect(QRectF(col * bw, row * bh, bw + 1, bh + 1))
            painter.setClipPath(path)
            painter.drawImage(0, 0, b)
            painter.restore()
        finally:
            painter.end()
        return out

    def _r_venetian_blinds(self, a: QImage, b: QImage, p: float) -> QImage:
        # Horizontal strips like venetian blinds
        strips = 12  # Reasonable number for performance
        out = self._blank(a.size(), QColor(0, 0, 0, 255))
        painter = QPainter(out)
        try:
            painter.setRenderHints(QPainter.RenderHint.SmoothPixmapTransform | QPainter.RenderHint.Antialiasing, on=True)
            painter.drawImage(0, 0, a)
            w, h = a.width(), a.height()
            strip_h = h // strips
            painter.save()
            path = QPainterPath()
            for i in range(strips):
                y = i * strip_h
                strip_progress = max(0.0, min(1.0, (p - i * 0.05) * 2.0))
                if strip_progress > 0:
                    reveal_h = int(strip_h * strip_progress)
                    path.addRect(QRectF(0, y, w, reveal_h))
            painter.setClipPath(path)
            painter.drawImage(0, 0, b)
            painter.restore()
        finally:
            painter.end()
        return out

    def _r_barn_door(self, a: QImage, b: QImage, p: float) -> QImage:
        # Doors open from center outward
        out = self._blank(a.size(), QColor(0, 0, 0, 255))
        painter = QPainter(out)
        try:
            painter.setRenderHints(QPainter.RenderHint.SmoothPixmapTransform | QPainter.RenderHint.Antialiasing, on=True)
            painter.drawImage(0, 0, a)
            w, h = a.width(), a.height()
            center_x = w // 2
            reveal_w = int(w * p * 0.5)
            painter.save()
            path = QPainterPath()
            path.addRect(QRectF(center_x - reveal_w, 0, 2 * reveal_w, h))
            painter.setClipPath(path)
            painter.drawImage(0, 0, b)
            painter.restore()
        finally:
            painter.end()
        return out

    def _r_clock_wipe(self, a: QImage, b: QImage, p: float) -> QImage:
        # Simplified clock wipe using triangular sectors
        out = self._blank(a.size(), QColor(0, 0, 0, 255))
        painter = QPainter(out)
        try:
            painter.setRenderHints(QPainter.RenderHint.SmoothPixmapTransform | QPainter.RenderHint.Antialiasing, on=True)
            painter.drawImage(0, 0, a)
            cx, cy = a.width() // 2, a.height() // 2
            max_r = max(a.width(), a.height())
            angle = p * 360.0  # degrees
            painter.save()
            path = QPainterPath()
            path.moveTo(cx, cy)
            path.lineTo(cx, 0)  # Start at 12 o'clock
            # Simple approximation: draw sectors
            steps = max(4, int(angle / 45))  # Fewer steps for performance
            for i in range(steps + 1):
                a_rad = min(angle, i * 45) * 3.14159 / 180.0
                x = cx + max_r * math.sin(a_rad)
                y = cy - max_r * math.cos(a_rad)
                path.lineTo(x, y)
            path.closeSubpath()
            painter.setClipPath(path)
            painter.drawImage(0, 0, b)
            painter.restore()
        finally:
            painter.end()
        return out

    # --- cv2 helpers ---
    def _qimage_to_cv(self, img: QImage):
        if not _HAS_CV:
            return None
        img = img.convertToFormat(QImage.Format.Format_RGBA8888)
        width = img.width()
        height = img.height()
        ptr = img.bits()
        ptr.setsize(height * width * 4)
        arr = np.frombuffer(ptr, np.uint8).reshape((height, width, 4))
        # Convert RGBA -> BGR
        bgr = cv2.cvtColor(arr, cv2.COLOR_RGBA2BGR)
        return bgr

    def _cv_to_qimage(self, arr, size: QSize) -> QImage:
        if arr is None:
            return self._blank(size)
        # Convert BGR -> RGBA
        rgba = cv2.cvtColor(arr, cv2.COLOR_BGR2RGBA)
        h, w, _ = rgba.shape
        qimg = QImage(rgba.data, w, h, 4 * w, QImage.Format.Format_RGBA8888)
        return qimg.copy()


# Catalog of transitions for UI listing (name -> description)
TRANSITIONS_CATALOG: list[tuple[str, str]] = [
    ("Fade", "Smooth crossfade between current and next frame by blending opacity."),
    ("Slide Left", "Current frame slides left, next slides in from right."),
    ("Slide Right", "Current frame slides right, next slides in from left."),
    ("Slide Up", "Current frame slides up, next slides in from bottom."),
    ("Slide Down", "Current frame slides down, next slides in from top."),
    ("Wipe Horizontal", "Vertical band reveals the next frame from left to right."),
    ("Wipe Vertical", "Horizontal band reveals the next frame from top to bottom."),
    ("Zoom In", "Current frame zooms in slightly while switching to next."),
    ("Zoom Out", "Current frame zooms out slightly revealing the next frame."),
    ("Circle Reveal", "Expanding circle reveals the next frame from the center."),
    ("Blur Dissolve", "Current frame blurs while next fades in."),
    ("Pixelate Dissolve", "Current pixelates progressively as next fades in."),
    ("Parallax Slide", "Both frames slide at different speeds for a 3D feel."),
    ("Diagonal Wipe", "Diagonal reveal from top-left to bottom-right."),
    ("Curtain Open (Vertical)", "Frame splits vertically to reveal the next."),
    ("Curtain Open (Horizontal)", "Frame splits horizontally to reveal the next."),
    ("Random Blocks Transition", "Random blocks disappear to reveal the next frame."),
    ("Fade to Black + Next Frame Fade In", "Fade to black, then fade in next frame."),
    ("Push Left", "Current frame pushes out left as next pushes in from right."),
    ("Push Right", "Current frame pushes out right as next pushes in from left."),
    ("Push Up", "Current frame pushes out up as next pushes in from bottom."),
    ("Push Down", "Current frame pushes out down as next pushes in from top."),
    ("Iris In", "Circular iris closes to reveal next frame from center."),
    ("Iris Out", "Circular iris opens from center to reveal next frame."),
    ("Flip Left", "Current frame flips horizontally left to reveal next."),
    ("Flip Right", "Current frame flips horizontally right to reveal next."),
    ("Checkerboard", "Alternating squares reveal next frame in pattern."),
    ("Venetian Blinds", "Horizontal strips reveal next frame like blinds."),
    ("Barn Door", "Frame splits from center and moves to edges."),
    ("Clock Wipe", "Reveals next frame in clockwise sweeping motion."),
]
