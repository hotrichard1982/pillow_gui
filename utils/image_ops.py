"""图片保存/格式转换工具"""
import os
from PIL import Image


IMG_EXTS = (".jpg", ".jpeg", ".png", ".webp", ".bmp")


def _png_colors(quality: int) -> int:
    """质量值 → PNG 调色板颜色数（16~256）"""
    return 16 + int((max(1, min(100, quality)) - 1) * (256 - 16) / 99)


def save_image(img: Image.Image, out_path: str, quality: int = 85) -> None:
    """保存 PIL Image 到文件，自动处理格式转换"""
    ext = os.path.splitext(out_path)[1].lower()
    fmt = {".jpg": "JPEG", ".jpeg": "JPEG", ".png": "PNG",
           ".webp": "WEBP", ".bmp": "BMP"}.get(ext, "JPEG")

    q = max(1, min(100, quality))

    if fmt in ("JPEG", "WEBP"):
        if img.mode not in ("RGB", "L"):
            img = img.convert("RGB")
    elif fmt == "PNG" and img.mode not in ("RGB", "RGBA", "L", "P"):
        img = img.convert("RGBA")

    save_kwargs = {}
    if fmt == "JPEG":
        save_kwargs["quality"] = q
        save_kwargs["optimize"] = True
    elif fmt == "WEBP":
        save_kwargs["quality"] = q
    elif fmt == "PNG":
        if q < 100:
            colors = _png_colors(q)
            if img.mode == "RGBA":
                img = img.quantize(colors=colors, method=Image.Quantize.MEDIANCUT)
            else:
                img = img.convert("RGB").quantize(colors=colors, method=Image.Quantize.MEDIANCUT)
        save_kwargs["compress_level"] = max(4, min(9, 9 - (q - 1) * 5 // 99))

    img.save(out_path, fmt, **save_kwargs)


def get_default_ext(orig_format: str) -> str:
    """根据原始格式返回默认保存后缀"""
    ext_map = {"JPEG": ".jpg", "PNG": ".png", "WEBP": ".webp", "BMP": ".bmp"}
    if orig_format in ("BMP",):
        return ".jpg"
    return ext_map.get(orig_format, ".jpg")
