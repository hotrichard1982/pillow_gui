"""关于我们标签页"""
import sys
import webbrowser
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel, QPushButton
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap

try:
    from PySide6 import __version__ as pyside6_ver
except ImportError:
    pyside6_ver = "N/A"
try:
    from PIL import __version__ as pillow_ver
except ImportError:
    pillow_ver = "N/A"


class AboutTab(QWidget):
    def __init__(self):
        super().__init__()
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 30, 40, 30)
        layout.setSpacing(12)
        layout.setAlignment(Qt.AlignTop | Qt.AlignCenter)

        # Logo
        logo = QLabel()
        try:
            pix = QPixmap("logo.png").scaled(128, 128, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            logo.setPixmap(pix)
            logo.setAlignment(Qt.AlignCenter)
        except Exception:
            pass
        layout.addWidget(logo)

        # 标题
        title = QLabel("图轻剪 PicCraft")
        title.setStyleSheet("font-size: 22px; font-weight: bold;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        version = QLabel("v20260503")
        version.setStyleSheet("font-size: 13px; color: #64748b;")
        version.setAlignment(Qt.AlignCenter)
        layout.addWidget(version)
        layout.addSpacing(10)

        # 技术栈
        self._add_section(layout, "技术栈", [
            ("Python", sys.version.split()[0]),
            ("PySide6", pyside6_ver),
            ("Pillow (PIL)", pillow_ver),
            ("PyInstaller", "6.19.0"),
        ])

        # 开源信息
        self._add_section(layout, "开源信息", [
            ("协议", "MIT License"),
        ])
        gh_btn = QPushButton("⭐ GitHub 求Star")
        gh_btn.clicked.connect(lambda: webbrowser.open(
            "https://github.com/hotrichard1982/pillow_gui"))
        gh_btn.setObjectName("secondaryBtn")
        layout.addWidget(gh_btn, alignment=Qt.AlignCenter)
        layout.addSpacing(6)

        # 公司
        self._add_section(layout, "联系方式", [
            ("公司", "重庆三人众科技有限公司"),
            ("官网", "https://www.cq30.com/"),
            ("QQ", "7602069"),
            ("邮箱", "7602069@qq.com"),
        ])

        layout.addStretch()

    def _add_section(self, parent_layout, title, items):
        parent_layout.addSpacing(8)
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        parent_layout.addWidget(sep)
        tl = QLabel(title)
        tl.setStyleSheet("font-weight: bold; font-size: 13px;")
        tl.setAlignment(Qt.AlignCenter)
        parent_layout.addWidget(tl)

        for label, value in items:
            row = QHBoxLayout()
            row.addStretch()
            k = QLabel(label)
            k.setStyleSheet("color: #64748b; font-size: 12px;")
            k.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            row.addWidget(k)
            v = QLabel(str(value))
            v.setStyleSheet("font-size: 12px;")
            row.addWidget(v)
            row.addStretch()
            parent_layout.addLayout(row)
