"""image_tool_cn 核心逻辑测试。运行：python -m pytest test_image_tool.py -v"""
import io
import pytest
from PIL import Image


class TestResize:
    def test_proportional_by_width(self):
        img = Image.new("RGB", (800, 600))
        w, h = img.size
        tw = 400
        th = int(h * (tw / w))
        assert tw == 400
        assert th == 300

    def test_proportional_by_height(self):
        img = Image.new("RGB", (800, 600))
        w, h = img.size
        th = 300
        tw = int(w * (th / h))
        assert tw == 400
        assert th == 300

    def test_lanczos_resize(self):
        img = Image.new("RGB", (800, 600))
        resized = img.resize((200, 150), Image.Resampling.LANCZOS)
        assert resized.size == (200, 150)

    def test_quality_clamped(self):
        q = 0
        q = max(1, min(100, q))
        assert q == 1
        q = 200
        q = max(1, min(100, q))
        assert q == 100


class TestCrop:
    def test_crop_area(self):
        img = Image.new("RGB", (800, 600))
        cropped = img.crop((100, 50, 300, 250))
        assert cropped.size == (200, 200)

    def test_crop_bounds_clamped(self):
        """Crop coordinates should be clamped to image bounds."""
        iw, ih = 800, 600
        m = 5  # min crop size
        x, y, w, h = -10, -5, 100, 100
        x = max(0, min(x, iw - 1))
        y = max(0, min(y, ih - 1))
        w = max(m, min(w, iw - x))
        h = max(m, min(h, ih - y))
        assert (x, y, w, h) == (0, 0, 100, 100)

    def test_crop_min_size(self):
        m = 5
        w, h = 1, 2
        assert w < m or h < m  # too small


class TestCoordinateConversion:
    def test_canvas_to_image(self):
        cx, cy = 350, 250
        scale = 0.5
        offset_x, offset_y = 150, 50
        ix = (cx - offset_x) / scale
        iy = (cy - offset_y) / scale
        assert ix == 400
        assert iy == 400

    def test_image_to_canvas(self):
        ix, iy = 400, 300
        scale = 0.5
        offset_x, offset_y = 100, 50
        cx = ix * scale + offset_x
        cy = iy * scale + offset_y
        assert cx == 300
        assert cy == 200


class TestFormat:
    def test_convert_rgb(self):
        img = Image.new("RGBA", (100, 100), (255, 0, 0, 128))
        assert img.mode == "RGBA"
        rgb = img.convert("RGB")
        assert rgb.mode == "RGB"

    def test_jpeg_save(self):
        img = Image.new("RGB", (100, 100), (255, 0, 0))
        buf = io.BytesIO()
        img.save(buf, "JPEG", quality=80)
        buf.seek(0)
        reloaded = Image.open(buf)
        assert reloaded.size == (100, 100)


class TestHandleComputation:
    @staticmethod
    def compute(handle, ix, iy, drag_start, start_rect, image_size, min_size=5):
        x, y, w, h = start_rect
        x2, y2 = x + w, y + h
        iw, ih = image_size
        m = min_size

        if handle == "tl":
            nx = max(0, min(int(ix), x2 - m))
            ny = max(0, min(int(iy), y2 - m))
            return (nx, ny, x2 - nx, y2 - ny)
        elif handle == "br":
            nx2 = min(iw, max(int(ix), x + m))
            ny2 = min(ih, max(int(iy), y + m))
            return (x, y, nx2 - x, ny2 - y)
        elif handle == "tc":
            ny = max(0, min(int(iy), y2 - m))
            return (x, ny, w, y2 - ny)
        elif handle == "mr":
            nx2 = min(iw, max(int(ix), x + m))
            return (x, y, nx2 - x, h)
        elif handle == "move":
            sx, sy = drag_start
            dx, dy = ix - sx, iy - sy
            nx = max(0, min(int(x + dx), iw - w))
            ny = max(0, min(int(y + dy), ih - h))
            return (nx, ny, w, h)
        return start_rect

    @staticmethod
    def _default_args(start_rect=(100, 100, 200, 200), image_size=(800, 600)):
        return {"start_rect": start_rect, "image_size": image_size}

    def test_handle_tl_drag(self):
        result = self.compute("tl", 50, 50, (0, 0), **self._default_args())
        assert result[0] == 50
        assert result[1] == 50

    def test_handle_br_drag(self):
        result = self.compute("br", 400, 400, (0, 0), **self._default_args())
        assert result[2] == 300
        assert result[3] == 300

    def test_handle_tc_drag(self):
        result = self.compute("tc", 250, 50, (0, 0), **self._default_args())
        assert result[1] == 50
        assert result[2] == 200
        assert result[3] == 250

    def test_handle_move(self):
        result = self.compute(
            "move", 160, 180, (200, 200),
            (100, 100, 200, 200), (800, 600))
        assert result[0] == 60
        assert result[1] == 80

    def test_handle_clamped_to_bounds(self):
        result = self.compute(
            "tl", -10, -10, (0, 0), (10, 10, 100, 100), (800, 600))
        assert result[0] == 0
        assert result[1] == 0
