"""单张处理标签页 — 缩放 + 裁剪 + 保存"""
import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel, QLineEdit,
    QPushButton, QCheckBox, QScrollArea, QFileDialog, QMessageBox,
    QSizePolicy, QApplication
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QKeySequence, QDragEnterEvent, QDropEvent, QShortcut
from PIL import Image

from canvas import CropCanvas
from utils.image_ops import save_image, get_default_ext, IMG_EXTS


class SingleTab(QWidget):
    def __init__(self):
        super().__init__()
        self.setAcceptDrops(True)
        self._internal_update = False

        self._build_ui()
        self._connect_signals()
        self._setup_shortcuts()

    # ───── UI 构建 ─────

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        layout.addWidget(self._build_top_bar())

        body = QHBoxLayout()
        body.setSpacing(12)

        self.canvas = CropCanvas()
        self.canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        body.addWidget(self.canvas, 1)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setMaximumWidth(320)
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        scroll_layout.setContentsMargins(0, 0, 0, 0)
        scroll_layout.setSpacing(0)

        scroll_layout.addWidget(self._build_resize_section())
        scroll_layout.addWidget(self._build_crop_section())
        scroll_layout.addWidget(self._build_save_section())
        scroll_layout.addStretch()

        scroll.setWidget(scroll_widget)
        body.addWidget(scroll)
        layout.addLayout(body)

    def _build_top_bar(self) -> QWidget:
        bar = QHBoxLayout()
        bar.setSpacing(8)
        lbl = QLabel("选择图片")
        lbl.setStyleSheet("font-weight: bold;")
        bar.addWidget(lbl)
        self.file_input = QLineEdit()
        self.file_input.setReadOnly(True)
        self.file_input.setPlaceholderText("拖拽图片到此处，或点击浏览选择...")
        bar.addWidget(self.file_input, 1)
        self.browse_btn = QPushButton("浏览")
        self.browse_btn.setObjectName("secondaryBtn")
        bar.addWidget(self.browse_btn)
        self.load_btn = QPushButton("加载")
        self.load_btn.setObjectName("")
        bar.addWidget(self.load_btn)
        w = QWidget()
        w.setLayout(bar)
        return w

    def _build_resize_section(self) -> QWidget:
        section = QVBoxLayout()
        section.setContentsMargins(0, 10, 0, 10)
        section.setSpacing(6)

        title = QLabel("尺寸缩放")
        title.setStyleSheet("font-weight: bold; font-size: 13px;")
        section.addWidget(title)
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        section.addWidget(sep)

        w_row = QHBoxLayout()
        w_row.addWidget(QLabel("宽度"))
        self.width_input = QLineEdit("800")
        self.width_input.setMaximumWidth(100)
        w_row.addWidget(self.width_input); w_row.addWidget(QLabel("px")); w_row.addStretch()
        section.addLayout(w_row)

        h_row = QHBoxLayout()
        h_row.addWidget(QLabel("高度"))
        self.height_input = QLineEdit("600")
        self.height_input.setMaximumWidth(100)
        h_row.addWidget(self.height_input); h_row.addWidget(QLabel("px")); h_row.addStretch()
        section.addLayout(h_row)

        self.keep_aspect = QCheckBox("保持原图比例")
        self.keep_aspect.setChecked(True)
        section.addWidget(self.keep_aspect)

        q_row = QHBoxLayout()
        q_row.addWidget(QLabel("质量"))
        self.quality_input = QLineEdit("85")
        self.quality_input.setMaximumWidth(70)
        q_row.addWidget(self.quality_input); q_row.addWidget(QLabel("(1-100)")); q_row.addStretch()
        section.addLayout(q_row)

        self.png_warn = QFrame()
        self.png_warn.setObjectName("warningBar")
        wl = QHBoxLayout(self.png_warn)
        wl.setContentsMargins(8, 6, 8, 6)
        wl.addWidget(QLabel("\u26a0\ufe0f"))
        wl.addWidget(QLabel("PNG \u4e3a\u65e0\u635f\u683c\u5f0f\uff0c\u538b\u7f29\u65e0\u6548\uff0c\u4fdd\u5b58\u65f6\u9ed8\u8ba4\u8f6c JPG"))
        self.png_warn.setVisible(False)
        section.addWidget(self.png_warn)

        self.resize_btn = QPushButton("应用缩放")
        self.resize_btn.setEnabled(False)
        section.addWidget(self.resize_btn)

        w = QWidget()
        w.setLayout(section)
        return w

    def _build_crop_section(self) -> QWidget:
        section = QVBoxLayout()
        section.setContentsMargins(0, 10, 0, 10)
        section.setSpacing(6)

        title = QLabel("自由裁剪")
        title.setStyleSheet("font-weight: bold; font-size: 13px;")
        section.addWidget(title)
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        section.addWidget(sep)

        xy_row = QHBoxLayout()
        xy_row.addWidget(QLabel("X"))
        self.crop_x = QLineEdit("0"); self.crop_x.setMaximumWidth(65)
        xy_row.addWidget(self.crop_x)
        xy_row.addWidget(QLabel("Y"))
        self.crop_y = QLineEdit("0"); self.crop_y.setMaximumWidth(65)
        xy_row.addWidget(self.crop_y); xy_row.addStretch()
        section.addLayout(xy_row)

        wh_row = QHBoxLayout()
        wh_row.addWidget(QLabel("宽"))
        self.crop_w = QLineEdit("100"); self.crop_w.setMaximumWidth(65)
        wh_row.addWidget(self.crop_w)
        wh_row.addWidget(QLabel("高"))
        self.crop_h = QLineEdit("100"); self.crop_h.setMaximumWidth(65)
        wh_row.addWidget(self.crop_h); wh_row.addStretch()
        section.addLayout(wh_row)

        btn_row = QHBoxLayout()
        self.apply_numeric_btn = QPushButton("应用数值")
        self.apply_numeric_btn.setObjectName("secondaryBtn")
        btn_row.addWidget(self.apply_numeric_btn)
        self.clear_crop_btn = QPushButton("清除")
        self.clear_crop_btn.setObjectName("secondaryBtn")
        btn_row.addWidget(self.clear_crop_btn); btn_row.addStretch()
        section.addLayout(btn_row)

        self.crop_btn = QPushButton("应用裁剪")
        self.crop_btn.setEnabled(False)
        section.addWidget(self.crop_btn)

        w = QWidget()
        w.setLayout(section)
        return w

    def _build_save_section(self) -> QWidget:
        section = QVBoxLayout()
        section.setContentsMargins(0, 10, 0, 10)
        section.setSpacing(6)

        btn_row = QHBoxLayout()
        self.reset_btn = QPushButton("重置")
        self.reset_btn.setObjectName("secondaryBtn"); self.reset_btn.setEnabled(False)
        btn_row.addWidget(self.reset_btn)
        self.overwrite_btn = QPushButton("覆盖原图")
        self.overwrite_btn.setEnabled(False)
        btn_row.addWidget(self.overwrite_btn)
        self.save_as_btn = QPushButton("另存为")
        self.save_as_btn.setObjectName("secondaryBtn"); self.save_as_btn.setEnabled(False)
        btn_row.addWidget(self.save_as_btn)
        section.addLayout(btn_row)

        shortcuts = QLabel("Ctrl+S 覆盖原图  |  Ctrl+Shift+S 另存为")
        shortcuts.setStyleSheet("color: #64748b; font-size: 11px;")
        shortcuts.setAlignment(Qt.AlignRight)
        section.addWidget(shortcuts)

        self.hint_label = QLabel("提示：拖拽鼠标选择裁剪区域，拖动方框手柄可调整")
        self.hint_label.setStyleSheet("color: #64748b; font-size: 12px;")
        self.hint_label.setWordWrap(True)
        section.addWidget(self.hint_label)

        w = QWidget()
        w.setLayout(section)
        return w

    # ───── 信号连接 ─────

    def _connect_signals(self):
        self.browse_btn.clicked.connect(self._select_file)
        self.load_btn.clicked.connect(self._load_image)
        self.resize_btn.clicked.connect(self._apply_resize)
        self.crop_btn.clicked.connect(self._apply_crop)
        self.apply_numeric_btn.clicked.connect(self._apply_crop_numeric)
        self.clear_crop_btn.clicked.connect(self.canvas.clear_crop)
        self.overwrite_btn.clicked.connect(self._overwrite_original)
        self.save_as_btn.clicked.connect(self._save_as)
        self.reset_btn.clicked.connect(self._reset_preview)

        self.canvas.crop_changed.connect(self._on_crop_changed)
        self.canvas.display_changed.connect(self._on_display_changed)

        self.width_input.textChanged.connect(self._on_width_change)
        self.height_input.textChanged.connect(self._on_height_change)
        self.keep_aspect.toggled.connect(self._on_aspect_toggle)
        self.quality_input.textChanged.connect(self._on_quality_change)

    def _setup_shortcuts(self):
        QShortcut(QKeySequence("Ctrl+S"), self, self._overwrite_original)
        QShortcut(QKeySequence("Ctrl+Shift+S"), self, self._save_as)

    # ───── 拖放支持 ─────

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        urls = event.mimeData().urls()
        if urls:
            path = urls[0].toLocalFile()
            if path.lower().endswith(IMG_EXTS):
                self.file_input.setText(path)
                self._load_image()
            else:
                QMessageBox.warning(self, "格式不支持",
                    "不支持的文件格式\n支持：JPG、JPEG、PNG、WebP、BMP")

    # ───── 操作逻辑 ─────

    def _select_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "选择图片", "",
            "图片文件 (*.jpg *.jpeg *.png *.webp *.bmp);;所有文件 (*.*)")
        if path:
            self.file_input.setText(path)
            self._load_image()

    def _load_image(self):
        path = self.file_input.text()
        if not path or not os.path.isfile(path):
            QMessageBox.warning(self, "提示", "请先选择有效的图片文件")
            return
        if self.canvas.load_image(path):
            self.resize_btn.setEnabled(True)
            self.save_as_btn.setEnabled(True)
            self.overwrite_btn.setEnabled(True)
            self.reset_btn.setEnabled(True)
            self.crop_btn.setEnabled(False)
        else:
            QMessageBox.critical(self, "错误", "无法打开图片文件")

    def _apply_resize(self):
        if self.canvas.display_image is None:
            return
        try:
            tw = int(self.width_input.text())
            th = int(self.height_input.text())
        except ValueError:
            QMessageBox.warning(self, "提示", "请输入有效的尺寸数值"); return
        if tw <= 0 or th <= 0:
            QMessageBox.warning(self, "提示", "宽度和高度必须大于 0"); return
        self.canvas.apply_resize(tw, th)

    def _apply_crop(self):
        if not self.canvas.has_crop():
            QMessageBox.warning(self, "提示", "请先在图片上选择裁剪区域"); return
        self.canvas.apply_crop()
        self.crop_btn.setEnabled(False)

    def _apply_crop_numeric(self):
        try:
            x = int(self.crop_x.text()); y = int(self.crop_y.text())
            w = int(self.crop_w.text()); h = int(self.crop_h.text())
        except ValueError:
            QMessageBox.warning(self, "提示", "请输入有效的裁剪数值"); return
        self.canvas.set_crop_rect_numeric(x, y, w, h)
        if self.canvas.has_crop():
            self.crop_btn.setEnabled(True)

    def _save_as(self):
        if self.canvas.display_image is None:
            return
        orig_fmt = self.canvas.original_image.format if self.canvas.original_image else None
        def_ext = get_default_ext(orig_fmt) if orig_fmt else ".jpg"
        path, _ = QFileDialog.getSaveFileName(
            self, "另存为", "", "JPEG (*.jpg);;PNG (*.png);;WebP (*.webp);;BMP (*.bmp)")
        if not path:
            return
        try:
            img = self.canvas.get_display_image()
            q = int(self.quality_input.text()) if self.quality_input.text().isdigit() else 85
            save_image(img, path, q)
            QMessageBox.information(self, "完成",
                f"另存成功！\n{path}\n大小：{os.path.getsize(path)/1024:.0f} KB")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"保存失败：{e}")

    def _overwrite_original(self):
        src = self.canvas.original_image
        if src is None:
            return
        if not (hasattr(src, 'filename') and src.filename and os.path.isfile(src.filename)):
            QMessageBox.warning(self, "提示", "原图路径无效，无法覆盖。请使用「另存为」"); return
        orig_fmt = src.format
        if orig_fmt in ("PNG", "BMP"):
            new_path = os.path.splitext(src.filename)[0] + ".jpg"
            ok = QMessageBox.question(self, "确认转换",
                f"PNG 为无损格式，压缩无效。\n将另存为 JPG：\n{new_path}\n\n原文件保留不变。是否继续？")
            if not ok:
                return
            out_path = new_path
        else:
            out_path = src.filename
            ok = QMessageBox.question(self, "确认覆盖", f"将覆盖原图：\n{src.filename}\n\n确定继续？")
            if not ok:
                return
        try:
            old_info = ""
            if os.path.exists(out_path):
                old_info = f"，原大小：{os.path.getsize(out_path)/1024:.0f} KB"
            img = self.canvas.get_display_image()
            q = int(self.quality_input.text()) if self.quality_input.text().isdigit() else 85
            save_image(img, out_path, q)
            QMessageBox.information(self, "完成",
                f"保存成功！\n{out_path}\n大小：{os.path.getsize(out_path)/1024:.0f} KB{old_info}")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"保存失败：{e}")

    def _reset_preview(self):
        self.canvas.reset_to_original()
        self.crop_btn.setEnabled(False)

    # ───── 回调 ─────

    def _on_crop_changed(self, rect):
        if rect is None:
            self.crop_x.setText("0"); self.crop_y.setText("0")
            self.crop_w.setText("100"); self.crop_h.setText("100")
            self.crop_btn.setEnabled(False)
        else:
            x, y, w, h = rect
            self.crop_x.setText(str(x)); self.crop_y.setText(str(y))
            self.crop_w.setText(str(w)); self.crop_h.setText(str(h))
            self.crop_btn.setEnabled(True)

    def _on_display_changed(self, w, h):
        self._internal_update = True
        self.width_input.setText(str(w))
        self.height_input.setText(str(h))
        self._internal_update = False
        src = self.canvas.original_image
        ow, oh = src.size if src else (0, 0)
        fmt = src.format if src else ""
        hint = f"原图：{ow}×{oh}  |  当前：{w}×{h}"
        if fmt == "PNG":
            hint += "  |  PNG 无法压缩"
            self.png_warn.setVisible(True)
        else:
            self.png_warn.setVisible(False)
        self.hint_label.setText(hint)

    def _on_width_change(self):
        if self._internal_update:
            return
        if self.keep_aspect.isChecked() and self.canvas.display_image:
            try:
                w = int(self.width_input.text())
            except ValueError:
                return
            if w <= 0:
                return
            dw, dh = self.canvas.display_image.size
            self._internal_update = True
            self.height_input.setText(str(int(w * dh / dw)))
            self._internal_update = False

    def _on_height_change(self):
        if self._internal_update:
            return
        if self.keep_aspect.isChecked() and self.canvas.display_image:
            try:
                h = int(self.height_input.text())
            except ValueError:
                return
            if h <= 0:
                return
            dw, dh = self.canvas.display_image.size
            self._internal_update = True
            self.width_input.setText(str(int(h * dw / dh)))
            self._internal_update = False

    def _on_aspect_toggle(self):
        if self.keep_aspect.isChecked() and self.canvas.display_image:
            dw, dh = self.canvas.display_image.size
            try:
                w = int(self.width_input.text())
            except ValueError:
                return
            self._internal_update = True
            self.height_input.setText(str(int(w * dh / dw)))
            self._internal_update = False

    def _on_quality_change(self):
        try:
            v = int(self.quality_input.text())
        except ValueError:
            return
        if v < 1:
            self.quality_input.setText("1")
        elif v > 100:
            self.quality_input.setText("100")
