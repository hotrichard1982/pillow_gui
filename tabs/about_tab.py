"""关于我们标签页（占位）"""
from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout


class AboutTab(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("关于我们 - 即将实现"))
