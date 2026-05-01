"""批量处理标签页（占位）"""
from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout


class BatchTab(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("批量处理 - 即将实现"))
