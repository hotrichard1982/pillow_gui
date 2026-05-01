"""QGraphicsView 裁剪画布 — 替代 tkinter CropCanvas"""
from PySide6.QtWidgets import QGraphicsView, QGraphicsScene
from PySide6.QtCore import (
    Qt, QRectF, QPointF, Signal, QSizeF, QLineF, QEvent
)
from PySide6.QtGui import (
    QPixmap, QImage, QPainter, QColor, QPen, QBrush, QCursor,
    QPainterPath, QFont, QFontMetrics
)
from PIL import Image


def pil2pixmap(img: Image.Image) -> QPixmap:
    """PIL Image → QPixmap"""
    if img.mode == "RGBA":
        data = img.convert("RGBA").tobytes("raw", "RGBA")
        qimg = QImage(data, img.width, img.height, QImage.Format_RGBA8888)
    else:
        data = img.convert("RGB").tobytes("raw", "RGB")
        qimg = QImage(data, img.width, img.height, QImage.Format_RGB888)
    return QPixmap.fromImage(qimg)


# ═══════════════════ CropCanvas ═══════════════════

class CropCanvas(QGraphicsView):
    """图片预览 + 鼠标拖拽裁剪画布"""

    HANDLE_SIZE = 8      # 手柄显示尺寸（view px）
    MIN_CROP_SIZE = 5    # 最小裁剪尺寸（image px）

    crop_changed = Signal(object)    # (x,y,w,h) or None
    display_changed = Signal(int, int)  # (w, h)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)
        self.setRenderHints(QPainter.Antialiasing)
        self.setDragMode(QGraphicsView.NoDrag)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setViewportUpdateMode(QGraphicsView.FullViewportUpdate)
        self.setFrameShape(QGraphicsView.NoFrame)
        self.setBackgroundBrush(QBrush(QColor("#f1f5f9")))

        # 图片
        self._pixmap_item = None
        self.original_image = None     # PIL Image
        self.display_image = None      # PIL Image

        # 裁剪状态
        self.crop_rect = None          # (x, y, w, h) image px
        self._drag_mode = None         # 'new'|'move'|'tl'|'tc'|'tr'|'ml'|'mr'|'bl'|'bc'|'br'
        self._drag_start = (0.0, 0.0)
        self._drag_start_rect = None
        self._hover_handle = None

        self.setCursor(Qt.CrossCursor)
        self.viewport().setMouseTracking(True)

    # ───── 公开 API ─────

    def load_image(self, path: str) -> bool:
        """加载图片，返回是否成功"""
        try:
            img = Image.open(path)
            self.original_image = img
            self.display_image = img.copy()
            self.crop_rect = None
            self._update_display()
            self.display_changed.emit(*self.display_image.size)
            return True
        except Exception:
            return False

    def get_display_image(self) -> Image.Image | None:
        return self.display_image

    def apply_crop(self):
        if self.crop_rect is None:
            return
        x, y, w, h = self.crop_rect
        self.display_image = self.display_image.crop((x, y, x + w, y + h))
        self.crop_rect = None
        self._update_display()
        self.display_changed.emit(*self.display_image.size)

    def apply_resize(self, tw: int, th: int):
        self.display_image = self.display_image.resize(
            (tw, th), Image.Resampling.LANCZOS)
        self.crop_rect = None
        self._update_display()
        self.display_changed.emit(*self.display_image.size)

    def reset_to_original(self):
        self.display_image = self.original_image.copy()
        self.crop_rect = None
        self._update_display()
        self.display_changed.emit(*self.display_image.size)

    def has_crop(self) -> bool:
        return self.crop_rect is not None

    def get_crop_rect(self):
        return self.crop_rect

    def set_crop_rect_numeric(self, x: int, y: int, w: int, h: int):
        if self.display_image is None:
            return
        iw, ih = self.display_image.size
        x = max(0, min(x, iw - 1))
        y = max(0, min(y, ih - 1))
        w = max(self.MIN_CROP_SIZE, min(w, iw - x))
        h = max(self.MIN_CROP_SIZE, min(h, ih - y))
        self.crop_rect = (x, y, w, h)
        self._update_display()
        self.crop_changed.emit(self.crop_rect)

    def clear_crop(self):
        self.crop_rect = None
        self._update_display()
        self.crop_changed.emit(None)

    # ───── 内部显示 ─────

    def _update_display(self):
        if self.display_image is None:
            return
        self._scene.clear()
        self._pixmap_item = None

        pix = pil2pixmap(self.display_image)
        self._pixmap_item = self._scene.addPixmap(pix)
        self._scene.setSceneRect(QRectF(pix.rect()))
        self.fitInView(self._scene.sceneRect(), Qt.KeepAspectRatio)

        if self.crop_rect:
            self._draw_crop_overlay()

    def _draw_crop_overlay(self):
        """在 scene 上绘制裁剪选区"""
        if self.crop_rect is None or self._pixmap_item is None:
            return
        x, y, w, h = self.crop_rect
        rect = QRectF(x, y, w, h)
        self._scene.addRect(rect,
            QPen(QColor("#ef4444"), 2),
            QBrush(QColor(239, 68, 68, 30)))

        hs = self.HANDLE_SIZE / self._view_scale()
        handle_positions = {
            "tl": rect.topLeft(),      "tc": QPointF(rect.center().x(), rect.top()),
            "tr": rect.topRight(),     "ml": QPointF(rect.left(), rect.center().y()),
            "mr": QPointF(rect.right(), rect.center().y()),
            "bl": rect.bottomLeft(),   "bc": QPointF(rect.center().x(), rect.bottom()),
            "br": rect.bottomRight(),
        }
        for pt in handle_positions.values():
            hr = QRectF(pt.x() - hs, pt.y() - hs, hs * 2, hs * 2)
            self._scene.addRect(hr, QPen(QColor("#ef4444"), 1), QBrush(QColor("#ffffff")))

    def _view_scale(self) -> float:
        """当前 view→scene 缩放比"""
        if self._pixmap_item is None:
            return 1.0
        tr = self.transform()
        return tr.m11()

    def _to_image(self, vx: float, vy: float) -> tuple[float, float]:
        """view 坐标 → image 坐标"""
        sp = self.mapToScene(int(vx), int(vy))
        return (sp.x(), sp.y())

    def _to_view(self, ix: float, iy: float) -> tuple[float, float]:
        """image 坐标 → view 坐标"""
        sp = self.mapFromScene(QPointF(ix, iy))
        return (sp.x(), sp.y())

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._pixmap_item:
            self.fitInView(self._scene.sceneRect(), Qt.KeepAspectRatio)

    # ───── 手柄命中检测 ─────

    def _hit_test_handle(self, vx: float, vy: float) -> str | None:
        """检测 view 坐标点是否在手柄上，返回手柄名称"""
        if self.crop_rect is None:
            return None
        ix, iy = self._to_image(vx, vy)
        x, y, w, h = self.crop_rect
        tol = (self.HANDLE_SIZE + 4) / self._view_scale()

        handles = {
            "tl": (x, y),        "tc": (x + w / 2, y),
            "tr": (x + w, y),    "ml": (x, y + h / 2),
            "mr": (x + w, y + h / 2),
            "bl": (x, y + h),    "bc": (x + w / 2, y + h),
            "br": (x + w, y + h),
        }
        for name, (hx, hy) in handles.items():
            if abs(ix - hx) <= tol and abs(iy - hy) <= tol:
                return name
        return None

    def _inside_rect(self, vx: float, vy: float) -> bool:
        if self.crop_rect is None:
            return False
        ix, iy = self._to_image(vx, vy)
        x, y, w, h = self.crop_rect
        return x <= ix <= x + w and y <= iy <= y + h

    # ───── 鼠标事件 ─────

    def _cursor_for_handle(self, handle: str) -> Qt.CursorShape:
        cursors = {
            "tl": Qt.SizeFDiagCursor, "br": Qt.SizeFDiagCursor,
            "tr": Qt.SizeBDiagCursor, "bl": Qt.SizeBDiagCursor,
            "tc": Qt.SizeVerCursor, "bc": Qt.SizeVerCursor,
            "ml": Qt.SizeHorCursor, "mr": Qt.SizeHorCursor,
        }
        return cursors.get(handle, Qt.CrossCursor)

    def mousePressEvent(self, event):
        if event.button() != Qt.LeftButton or self.display_image is None:
            super().mousePressEvent(event)
            return

        vx, vy = event.position().x(), event.position().y()

        if self.crop_rect is not None:
            handle = self._hit_test_handle(vx, vy)
            if handle is not None:
                self._drag_mode = handle
                self._drag_start = self._to_image(vx, vy)
                self._drag_start_rect = self.crop_rect
                return
            if self._inside_rect(vx, vy):
                self._drag_mode = "move"
                self._drag_start = self._to_image(vx, vy)
                self._drag_start_rect = self.crop_rect
                return

        self._drag_mode = "new"
        self._drag_start = self._to_image(vx, vy)
        self._drag_start_rect = None
        self.crop_rect = None
        self._update_display()

    def mouseMoveEvent(self, event):
        vx, vy = event.position().x(), event.position().y()

        if self._drag_mode is not None:
            self._handle_drag(vx, vy)
        else:
            self._update_cursor(vx, vy)

    def mouseReleaseEvent(self, event):
        if event.button() != Qt.LeftButton or self._drag_mode is None:
            super().mouseReleaseEvent(event)
            return

        if self._drag_mode == "new" and self.crop_rect is not None:
            _, _, w, h = self.crop_rect
            if w < self.MIN_CROP_SIZE or h < self.MIN_CROP_SIZE:
                self.crop_rect = None
            self._update_display()

        self._drag_mode = None
        self._drag_start = (0, 0)
        self._drag_start_rect = None
        self.crop_changed.emit(self.crop_rect)

    def _update_cursor(self, vx: float, vy: float):
        if self.crop_rect is None:
            self.setCursor(Qt.CrossCursor)
            return
        handle = self._hit_test_handle(vx, vy)
        if handle:
            self.setCursor(self._cursor_for_handle(handle))
        elif self._inside_rect(vx, vy):
            self.setCursor(Qt.SizeAllCursor)
        else:
            self.setCursor(Qt.CrossCursor)

    def _handle_drag(self, vx: float, vy: float):
        ix, iy = self._to_image(vx, vy)

        if self._drag_mode == "new":
            sx, sy = self._drag_start
            x1, y1 = min(sx, ix), min(sy, iy)
            x2, y2 = max(sx, ix), max(sy, iy)
            iw, ih = self.display_image.size
            x1 = max(0, int(x1)); y1 = max(0, int(y1))
            x2 = min(iw, int(x2)); y2 = min(ih, int(y2))
            self.crop_rect = (x1, y1, x2 - x1, y2 - y1)

        elif self._drag_mode == "move":
            sx, sy = self._drag_start
            dx, dy = ix - sx, iy - sy
            ox, oy, ow, oh = self._drag_start_rect
            iw, ih = self.display_image.size
            nx = max(0, min(int(ox + dx), iw - ow))
            ny = max(0, min(int(oy + dy), ih - oh))
            self.crop_rect = (nx, ny, ow, oh)

        else:
            self.crop_rect = self._compute_handle_rect(self._drag_mode, ix, iy)

        self._update_display()

    def _compute_handle_rect(self, handle: str, ix: float, iy: float):
        x, y, w, h = self._drag_start_rect
        x2, y2 = x + w, y + h
        iw, ih = self.display_image.size
        m = self.MIN_CROP_SIZE

        if handle == "tl":
            nx = max(0, min(int(ix), x2 - m))
            ny = max(0, min(int(iy), y2 - m))
            return (nx, ny, x2 - nx, y2 - ny)
        elif handle == "tr":
            nx2 = min(iw, max(int(ix), x + m))
            ny = max(0, min(int(iy), y2 - m))
            return (x, ny, nx2 - x, y2 - ny)
        elif handle == "bl":
            nx = max(0, min(int(ix), x2 - m))
            ny2 = min(ih, max(int(iy), y + m))
            return (nx, y, x2 - nx, ny2 - y)
        elif handle == "br":
            nx2 = min(iw, max(int(ix), x + m))
            ny2 = min(ih, max(int(iy), y + m))
            return (x, y, nx2 - x, ny2 - y)
        elif handle == "tc":
            ny = max(0, min(int(iy), y2 - m))
            return (x, ny, w, y2 - ny)
        elif handle == "bc":
            ny2 = min(ih, max(int(iy), y + m))
            return (x, y, w, ny2 - y)
        elif handle == "ml":
            nx = max(0, min(int(ix), x2 - m))
            return (nx, y, x2 - nx, h)
        elif handle == "mr":
            nx2 = min(iw, max(int(ix), x + m))
            return (x, y, nx2 - x, h)
        return (x, y, w, h)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.clear_crop()
        else:
            super().keyPressEvent(event)
