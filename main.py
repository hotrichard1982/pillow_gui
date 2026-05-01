"""图轻剪 PicCraft - PySide6 主窗口"""
import sys
import os
import webbrowser
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QFrame, QLabel, QPushButton, QTabWidget, QSizePolicy
)
from PySide6.QtCore import Qt, QSettings
from PySide6.QtGui import QFont, QPixmap, QPalette, QColor

from tabs.single_tab import SingleTab
from tabs.batch_tab import BatchTab
from tabs.about_tab import AboutTab

# ═══════════════════ QSS 样式表 ═══════════════════

LIGHT_QSS = """
/* ===== 全局 ===== */
QWidget {
    font-family: "Segoe UI", "Microsoft YaHei", "PingFang SC", sans-serif;
    font-size: 13px;
    color: #1e293b;
}
QMainWindow {
    background-color: #f8fafc;
}

/* ===== 标题栏 ===== */
#headerBar {
    background-color: #0f172a;
    border: none;
}
#headerBar QLabel#titleLabel {
    color: #ffffff;
    font-size: 18px;
    font-weight: bold;
}
#headerBar QLabel#companyLabel {
    color: #64748b;
    font-size: 11px;
}
#headerBar QLabel#infoLabel {
    color: #64748b;
    font-size: 10px;
}
#headerBar QLabel#linkLabel {
    color: #3b82f6;
    font-size: 10px;
}
#headerBar QPushButton#themeBtn {
    background: transparent;
    border: 1px solid #334155;
    border-radius: 6px;
    color: #f8fafc;
    padding: 4px 10px;
    font-size: 14px;
}
#headerBar QPushButton#themeBtn:hover {
    background: #1e293b;
    border-color: #475569;
}

/* ===== 选项卡 ===== */
QTabWidget::pane {
    border: none;
    background: #f8fafc;
    top: -1px;
}
QTabBar::tab {
    background: #f8fafc;
    color: #64748b;
    padding: 10px 24px;
    border: none;
    font-size: 13px;
}
QTabBar::tab:selected {
    color: #3b82f6;
    font-weight: bold;
    border-bottom: 2px solid #3b82f6;
}
QTabBar::tab:hover:!selected {
    color: #1e293b;
}

/* ===== 按钮 ===== */
QPushButton {
    background-color: #3b82f6;
    color: #ffffff;
    border: none;
    border-radius: 6px;
    padding: 8px 16px;
    font-size: 13px;
}
QPushButton:hover {
    background-color: #2563eb;
}
QPushButton:pressed {
    background-color: #1d4ed8;
}
QPushButton:disabled {
    background-color: #e2e8f0;
    color: #94a3b8;
}
QPushButton#secondaryBtn {
    background-color: #f1f5f9;
    color: #1e293b;
}
QPushButton#secondaryBtn:hover {
    background-color: #e2e8f0;
}
QPushButton#secondaryBtn:disabled {
    background-color: #f8fafc;
    color: #94a3b8;
}
QPushButton#successBtn {
    background-color: #10b981;
    color: #ffffff;
}
QPushButton#successBtn:hover {
    background-color: #059669;
}

/* ===== 输入框 ===== */
QLineEdit {
    border: 1px solid #e2e8f0;
    border-radius: 6px;
    padding: 6px 10px;
    background: #ffffff;
    color: #1e293b;
}
QLineEdit:focus {
    border-color: #3b82f6;
}
QLineEdit:disabled {
    background: #f8fafc;
    color: #94a3b8;
}

/* ===== 滚动条 ===== */
QScrollBar:vertical {
    background: #f8fafc;
    width: 8px;
    border: none;
}
QScrollBar::handle:vertical {
    background: #cbd5e1;
    border-radius: 4px;
    min-height: 24px;
}
QScrollBar::handle:vertical:hover {
    background: #94a3b8;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}

/* ===== 复选框 ===== */
QCheckBox {
    spacing: 8px;
}
QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border: 2px solid #cbd5e1;
    border-radius: 4px;
    background: #ffffff;
}
QCheckBox::indicator:checked {
    background: #3b82f6;
    border-color: #3b82f6;
}

/* ===== 分割线 ===== */
.separator {
    background-color: #e2e8f0;
    max-height: 1px;
}

/* ===== 卡片 ===== */
.card {
    background: #ffffff;
    border-radius: 0px;
}

/* ===== 警告条 ===== */
.warningBar {
    background: #fff7ed;
    border-radius: 6px;
    padding: 8px 12px;
}
.warningBar QLabel {
    color: #c2410c;
    font-size: 11px;
}
"""

DARK_QSS = """
/* ===== 全局 ===== */
QWidget {
    font-family: "Segoe UI", "Microsoft YaHei", "PingFang SC", sans-serif;
    font-size: 13px;
    color: #e2e8f0;
}
QMainWindow {
    background-color: #0f172a;
}

/* ===== 标题栏 ===== */
#headerBar {
    background-color: #020617;
    border: none;
}
#headerBar QLabel#titleLabel {
    color: #ffffff;
    font-size: 18px;
    font-weight: bold;
}
#headerBar QLabel#companyLabel {
    color: #94a3b8;
    font-size: 11px;
}
#headerBar QLabel#infoLabel {
    color: #94a3b8;
    font-size: 10px;
}
#headerBar QLabel#linkLabel {
    color: #60a5fa;
    font-size: 10px;
}
#headerBar QPushButton#themeBtn {
    background: transparent;
    border: 1px solid #334155;
    border-radius: 6px;
    color: #f8fafc;
    padding: 4px 10px;
    font-size: 14px;
}
#headerBar QPushButton#themeBtn:hover {
    background: #1e293b;
    border-color: #475569;
}

/* ===== 选项卡 ===== */
QTabWidget::pane {
    border: none;
    background: #0f172a;
    top: -1px;
}
QTabBar::tab {
    background: #0f172a;
    color: #64748b;
    padding: 10px 24px;
    border: none;
    font-size: 13px;
}
QTabBar::tab:selected {
    color: #60a5fa;
    font-weight: bold;
    border-bottom: 2px solid #60a5fa;
}
QTabBar::tab:hover:!selected {
    color: #e2e8f0;
}

/* ===== 按钮 ===== */
QPushButton {
    background-color: #3b82f6;
    color: #ffffff;
    border: none;
    border-radius: 6px;
    padding: 8px 16px;
    font-size: 13px;
}
QPushButton:hover {
    background-color: #2563eb;
}
QPushButton:pressed {
    background-color: #1d4ed8;
}
QPushButton:disabled {
    background-color: #334155;
    color: #64748b;
}
QPushButton#secondaryBtn {
    background-color: #1e293b;
    color: #e2e8f0;
}
QPushButton#secondaryBtn:hover {
    background-color: #334155;
}
QPushButton#secondaryBtn:disabled {
    background-color: #1e293b;
    color: #475569;
}
QPushButton#successBtn {
    background-color: #10b981;
    color: #ffffff;
}
QPushButton#successBtn:hover {
    background-color: #059669;
}

/* ===== 输入框 ===== */
QLineEdit {
    border: 1px solid #334155;
    border-radius: 6px;
    padding: 6px 10px;
    background: #1e293b;
    color: #e2e8f0;
}
QLineEdit:focus {
    border-color: #3b82f6;
}
QLineEdit:disabled {
    background: #1e293b;
    color: #64748b;
}

/* ===== 滚动条 ===== */
QScrollBar:vertical {
    background: #0f172a;
    width: 8px;
    border: none;
}
QScrollBar::handle:vertical {
    background: #475569;
    border-radius: 4px;
    min-height: 24px;
}
QScrollBar::handle:vertical:hover {
    background: #64748b;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}

/* ===== 复选框 ===== */
QCheckBox {
    spacing: 8px;
}
QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border: 2px solid #475569;
    border-radius: 4px;
    background: #1e293b;
}
QCheckBox::indicator:checked {
    background: #3b82f6;
    border-color: #3b82f6;
}

/* ===== 分割线 ===== */
.separator {
    background-color: #334155;
    max-height: 1px;
}

/* ===== 卡片 ===== */
.card {
    background: #1e293b;
    border-radius: 0px;
}

/* ===== 警告条 ===== */
.warningBar {
    background: #451a03;
    border-radius: 6px;
    padding: 8px 12px;
}
.warningBar QLabel {
    color: #fbbf24;
    font-size: 11px;
}
"""

# ═══════════════════ 主窗口 ═══════════════════


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("图轻剪 PicCraft")
        self.setMinimumSize(900, 600)
        self.resize(1120, 820)

        self._dark_mode = False
        self._settings = QSettings("PicCraft", "Theme")
        self._restore_theme()

        self._build_ui()

    # ───── 主题管理 ─────

    def _restore_theme(self):
        self._dark_mode = self._settings.value("darkMode", False, type=bool)
        if self._dark_mode:
            QApplication.instance().setStyleSheet(DARK_QSS)
        else:
            QApplication.instance().setStyleSheet(LIGHT_QSS)

    def _toggle_theme(self):
        self._dark_mode = not self._dark_mode
        if self._dark_mode:
            QApplication.instance().setStyleSheet(DARK_QSS)
            self.theme_btn.setText("☀")
        else:
            QApplication.instance().setStyleSheet(LIGHT_QSS)
            self.theme_btn.setText("🌙")
        self._settings.setValue("darkMode", self._dark_mode)

    # ───── UI 构建 ─────

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 标题栏
        main_layout.addWidget(self._build_header())

        # 选项卡
        self.tabs = QTabWidget()
        self.single_tab = SingleTab()
        self.batch_tab = BatchTab()
        self.about_tab = AboutTab()
        self.tabs.addTab(self.single_tab, "  单张处理  ")
        self.tabs.addTab(self.batch_tab, "  批量处理  ")
        self.tabs.addTab(self.about_tab, "  关于我们  ")
        main_layout.addWidget(self.tabs, 1)

    def _build_header(self) -> QFrame:
        header = QFrame()
        header.setObjectName("headerBar")
        header.setFixedHeight(80)
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(20, 10, 20, 10)
        h_layout.setSpacing(0)

        # ── 左侧：Logo + 标题 ──
        left = QHBoxLayout()
        left.setSpacing(12)
        logo_path = self._resource_path("logo.png")
        if os.path.isfile(logo_path):
            logo = QLabel()
            pix = QPixmap(logo_path).scaled(48, 48, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            logo.setPixmap(pix)
            left.addWidget(logo)

        title_col = QVBoxLayout()
        title_col.setSpacing(0)
        title_lbl = QLabel("图轻剪 PicCraft")
        title_lbl.setObjectName("titleLabel")
        company_lbl = QLabel("重庆三人众科技有限公司")
        company_lbl.setObjectName("companyLabel")
        title_col.addWidget(title_lbl)
        title_col.addWidget(company_lbl)
        left.addLayout(title_col)
        h_layout.addLayout(left)
        h_layout.addStretch()

        # ── 右侧：信息 + 主题切换 ──
        right = QVBoxLayout()
        right.setSpacing(2)
        right.setAlignment(Qt.AlignRight)

        # 行1：版权 + 版本
        row1 = QLabel("© 重庆三人众科技有限公司  |  v20260503")
        row1.setObjectName("infoLabel")
        right.addWidget(row1)

        # 行2：GitHub + 官网（可点击）
        row2 = QHBoxLayout()
        row2.setSpacing(12)
        row2.setAlignment(Qt.AlignRight)
        gh = QLabel("⭐ GitHub 求Star")
        gh.setObjectName("linkLabel")
        gh.setCursor(Qt.PointingHandCursor)
        gh.mousePressEvent = lambda e: webbrowser.open(
            "https://github.com/hotrichard1982/pillow_gui")
        web = QLabel("https://www.cq30.com/")
        web.setObjectName("linkLabel")
        web.setCursor(Qt.PointingHandCursor)
        web.mousePressEvent = lambda e: webbrowser.open("https://www.cq30.com/")
        row2.addWidget(gh)
        row2.addWidget(web)
        right.addLayout(row2)

        # 行3：联系方式
        row3 = QLabel("QQ: 7602069  |  7602069@qq.com")
        row3.setObjectName("infoLabel")
        right.addWidget(row3)

        h_layout.addLayout(right)
        h_layout.addSpacing(16)

        # 明/暗切换按钮
        self.theme_btn = QPushButton("🌙" if not self._dark_mode else "☀")
        self.theme_btn.setObjectName("themeBtn")
        self.theme_btn.setFixedSize(42, 42)
        self.theme_btn.setCursor(Qt.PointingHandCursor)
        self.theme_btn.clicked.connect(self._toggle_theme)
        h_layout.addWidget(self.theme_btn)

        return header

    @staticmethod
    def _resource_path(relative):
        """获取资源路径（兼容 PyInstaller 打包）"""
        if hasattr(sys, "_MEIPASS"):
            return os.path.join(sys._MEIPASS, relative)
        return os.path.join(os.path.dirname(__file__), relative)


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
