"""单张处理标签页（占位）"""
from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout


class SingleTab(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("单张处理 - 即将实现"))
