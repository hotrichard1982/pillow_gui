"""批量处理标签页 — QThread 后台处理"""
import os
import webbrowser
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel, QLineEdit,
    QPushButton, QFileDialog, QMessageBox, QApplication
)
from PySide6.QtCore import Qt, Signal, QThread
from PIL import Image

from utils.image_ops import IMG_EXTS


class BatchWorker(QThread):
    """后台批量处理线程"""
    progress = Signal(int, int)  # current, total
    finished = Signal(int, list)  # total, errors
    log = Signal(str)

    def __init__(self, input_dir, output_dir, target_width, quality):
        super().__init__()
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.target_width = target_width
        self.quality = quality

    def run(self):
        os.makedirs(self.output_dir, exist_ok=True)
        files = [f for f in os.listdir(self.input_dir)
                 if f.lower().endswith(IMG_EXTS)]
        total = len(files)
        errors = []
        for i, f in enumerate(files, 1):
            in_path = os.path.join(self.input_dir, f)
            out_path = os.path.join(self.output_dir, f)
            try:
                img = Image.open(in_path).convert("RGB")
                w, h = img.size
                tw = self.target_width
                th = int(h * (tw / w))
                img = img.resize((tw, th), Image.Resampling.LANCZOS)
                img.save(out_path, "JPEG", quality=self.quality, optimize=True)
            except Exception as e:
                errors.append(f)
                self.log.emit(f"处理失败 {f}: {e}")
            self.progress.emit(i, total)
        self.finished.emit(total, errors)


class BatchTab(QWidget):
    def __init__(self):
        super().__init__()
        self._worker = None
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # 文件夹设置
        section1 = QVBoxLayout()
        title1 = QLabel("文件夹设置")
        title1.setStyleSheet("font-weight: bold; font-size: 13px;")
        section1.addWidget(title1)
        sep1 = QFrame()
        sep1.setFrameShape(QFrame.HLine)
        section1.addWidget(sep1)

        row0 = QHBoxLayout()
        row0.addWidget(QLabel("图片文件夹"))
        self.input_dir = QLineEdit()
        self.input_dir.setReadOnly(True)
        row0.addWidget(self.input_dir, 1)
        self.select_input_btn = QPushButton("选择")
        self.select_input_btn.setObjectName("secondaryBtn")
        row0.addWidget(self.select_input_btn)
        section1.addLayout(row0)

        row1 = QHBoxLayout()
        row1.addWidget(QLabel("输出文件夹"))
        self.output_dir = QLineEdit()
        self.output_dir.setReadOnly(True)
        row1.addWidget(self.output_dir, 1)
        self.select_output_btn = QPushButton("选择")
        self.select_output_btn.setObjectName("secondaryBtn")
        row1.addWidget(self.select_output_btn)
        section1.addLayout(row1)
        layout.addLayout(section1)

        # 处理参数
        section2 = QVBoxLayout()
        title2 = QLabel("处理参数")
        title2.setStyleSheet("font-weight: bold; font-size: 13px;")
        section2.addWidget(title2)
        sep2 = QFrame()
        sep2.setFrameShape(QFrame.HLine)
        section2.addWidget(sep2)

        row2 = QHBoxLayout()
        row2.addWidget(QLabel("目标宽度"))
        self.width_input = QLineEdit("1000")
        self.width_input.setMaximumWidth(120)
        row2.addWidget(self.width_input)
        row2.addWidget(QLabel("px"))
        row2.addSpacing(24)
        row2.addWidget(QLabel("压缩质量"))
        self.quality_input = QLineEdit("60")
        self.quality_input.setMaximumWidth(80)
        row2.addWidget(self.quality_input)
        row2.addWidget(QLabel("(1-100)"))
        row2.addStretch()
        section2.addLayout(row2)
        layout.addLayout(section2)

        # 操作
        action = QVBoxLayout()
        self.start_btn = QPushButton("开始处理")
        self.start_btn.setObjectName("successBtn")
        action.addWidget(self.start_btn)
        self.status_label = QLabel("准备就绪")
        self.status_label.setAlignment(Qt.AlignCenter)
        action.addWidget(self.status_label)
        layout.addLayout(action)

        layout.addStretch()

        # 信号
        self.select_input_btn.clicked.connect(self._select_input)
        self.select_output_btn.clicked.connect(self._select_output)
        self.start_btn.clicked.connect(self._start)
        self.quality_input.textChanged.connect(self._on_quality_change)

    def _select_input(self):
        d = QFileDialog.getExistingDirectory(self, "选择图片文件夹")
        if d:
            self.input_dir.setText(d)

    def _select_output(self):
        d = QFileDialog.getExistingDirectory(self, "选择输出文件夹")
        if d:
            self.output_dir.setText(d)

    def _start(self):
        if not self.input_dir.text() or not self.output_dir.text():
            QMessageBox.warning(self, "提示", "请先选择输入和输出文件夹"); return
        output = self.output_dir.text()
        if os.path.isdir(output):
            existing = [f for f in os.listdir(output)
                        if f.lower().endswith(IMG_EXTS)]
            if existing:
                ok = QMessageBox.question(self, "确认",
                    f"输出文件夹中已有 {len(existing)} 张图片，同名文件将被覆盖。\n是否继续？")
                if not ok:
                    return
        self.start_btn.setEnabled(False)
        self.status_label.setText("正在处理...")

        try:
            tw = int(self.width_input.text())
            q = int(self.quality_input.text())
        except ValueError:
            QMessageBox.warning(self, "提示", "请输入有效数值"); self.start_btn.setEnabled(True); return

        self._worker = BatchWorker(self.input_dir.text(), output, tw, q)
        self._worker.progress.connect(self._on_progress)
        self._worker.finished.connect(self._on_finished)
        self._worker.log.connect(lambda m: print(m))
        self._worker.start()

    def _on_progress(self, current, total):
        self.status_label.setText(f"处理中... {current}/{total}")

    def _on_finished(self, total, errors):
        self.start_btn.setEnabled(True)
        msg = f"完成！共 {total} 张"
        if errors:
            msg += f"，{len(errors)} 张失败"
        self.status_label.setText(msg)
        QMessageBox.information(self, "完成",
            f"已处理 {total} 张图片！"
            + (f"\n失败 {len(errors)} 张：{', '.join(errors[:5])}" if errors else ""))

    def _on_quality_change(self):
        try:
            v = int(self.quality_input.text())
        except ValueError:
            return
        if v < 1:
            self.quality_input.setText("1")
        elif v > 100:
            self.quality_input.setText("100")
