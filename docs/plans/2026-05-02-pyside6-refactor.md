# PySide6 重构 PicCraft GUI 实施方案

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development

**Goal:** 用 PySide6 完全重写 PicCraft/图轻剪 的 GUI，保持全部现有功能，新增"关于我们"标签页，实现现代化软件界面。

**Architecture:** QMainWindow + QTabWidget（3 个标签页），QGraphicsView 实现裁剪画布，QSS 样式表统一样式（支持明/暗双模式）。模块化拆分：主窗口、画布组件、三个标签页各自独立文件，工具函数抽离。

**Tech Stack:** Python 3.10+, PySide6, Pillow, PyInstaller（打包）

**UI 设计目标：** Flat modern design（参考 Linear / VS Code / Notion），明暗双模式一键切换，平滑过渡，良好信息层级。绝不使用灰色卡片边框，靠间距和色块区分区域。

---

## 项目结构

```
pillow_gui/
├── main.py                     # 入口 + QMainWindow + QTabWidget
├── canvas.py                   # CropCanvas → QGraphicsView 重写
├── tabs/
│   ├── __init__.py
│   ├── single_tab.py           # 单张处理
│   ├── batch_tab.py            # 批量处理
│   └── about_tab.py            # 关于我们
├── utils/
│   ├── __init__.py
│   └── image_ops.py            # 图片保存/格式转换工具函数
├── resources/
│   └── style.qss               # QSS 全局样式表
├── logo.png                    # Logo（透明背景 256×256）
├── logo.ico                    # exe 图标
├── image_tool_cn.spec          # PyInstaller 配置（更新为 PySide6）
└── test_image_tool.py          # 保留现有测试（纯逻辑测试，无需改动）
```

**删除的文件：**
- `image_tool_cn.py`（被新模块替代）

**不再需要的依赖：**
- `tkinter` / `tkinterdnd2`（PySide6 内置 DnD）

---

## 任务拆解

### 任务 0: 环境准备

**目标：** 安装 PySide6，创建项目骨架

**步骤：**
1. 安装依赖
   ```bash
   pip install PySide6
   ```
2. 创建模块目录结构
   ```bash
   mkdir tabs utils resources
   ```
3. 创建 `tabs/__init__.py` 和 `utils/__init__.py`（空文件）
4. 提交
   ```bash
   git add -A
   git commit -m "chore: init PySide6 project skeleton"
   ```

---

### 任务 1: 主窗口框架 + QSS 样式

**目标：** 创建 QMainWindow，集成 QTabWidget（3 个空白标签页），加载 QSS 样式表

**文件：**
- Create: `main.py`
- Create: `resources/style.qss`
- Create: `tabs/single_tab.py`（占位）
- Create: `tabs/batch_tab.py`（占位）
- Create: `tabs/about_tab.py`（占位）

**QSS 配色方案（明/暗双模式）：**

**亮色模式：**
```css
--primary: #3b82f6;    --primary-hover: #2563eb;
--bg: #f8fafc;         --surface: #ffffff;
--text: #1e293b;       --text-muted: #64748b;
--border: #e2e8f0;     --success: #10b981;
--header: #0f172a;     /* 标题栏始终深色 */
```

**暗色模式：**
```css
--primary: #3b82f6;    --primary-hover: #60a5fa;
--bg: #0f172a;         --surface: #1e293b;
--text: #e2e8f0;       --text-muted: #94a3b8;
--border: #334155;     --success: #10b981;
--header: #020617;     /* 标题栏更深 */
```

**切换机制：** 标题栏右侧 ☀/🌙 图标按钮，切换时动态替换 `qApp.setStyleSheet()` 并更新 `QPalette`。

**关键代码片段：**

```python
# main.py 骨架
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("图轻剪 PicCraft")
        self.setMinimumSize(900, 600)
        self.resize(1120, 820)
        self._build_ui()

    def _build_ui(self):
        # 标题栏（QFrame 模拟）
        #  左侧: logo + 标题 + 公司名
        #  右侧: 版本 + GitHub + 官网 + 联系 + ☀/🌙 切换
        # QTabWidget + 3 个标签页
        ...
    
    def _toggle_theme(self):
        self._dark_mode = not self._dark_mode
        if self._dark_mode:
            qApp.setStyleSheet(DARK_QSS)
            qApp.setPalette(dark_palette())
        else:
            qApp.setStyleSheet(LIGHT_QSS)
            qApp.setPalette(light_palette())
        # 保存到 QSettings 记住用户偏好
```

**提交：**
```bash
git add main.py resources/style.qss tabs/
git commit -m "feat: PySide6 main window + QSS + 3 tab stubs"
```

---

### 任务 2: CropCanvas → QGraphicsView 重写（最复杂）

**目标：** 用 QGraphicsView + QGraphicsScene 实现完整的裁剪画布交互

**文件：**
- Create: `canvas.py`

**需要实现的类：**

1. **`CropCanvas(QGraphicsView)`** — 主画布
   - `load_image(path)` → 加载图片到 QGraphicsPixmapItem
   - `get_display_image()` → 返回当前 PIL Image
   - `apply_crop()` → 裁剪 display_image
   - `apply_resize(tw, th)` → 缩放 display_image
   - `reset_to_original()` → 恢复原图
   - `has_crop()` / `get_crop_rect()` / `set_crop_rect_numeric()`
   - `clear_crop()`
   - Signal: `crop_changed(rect)` / `display_changed(w, h)`

2. **`CropOverlay(QGraphicsObject)`** — 裁剪选区覆盖层
   - 8 个可拖拽手柄（四角 + 四边中点）
   - 拖拽行为：新建 / 移动 / 调整大小
   - 鼠标悬浮时手柄高亮 + 光标变化
   - ESC 键清除选区
   - 半透明遮罩（选区外的区域变暗）

**坐标转换：** QGraphicsView 内置 `mapToScene()` / `mapFromScene()` 自动处理缩放，无需手动换算。

**对比 tkinter 版本的等价映射：**

| tkinter | PySide6 |
|---------|---------|
| `_to_image(cx, cy)` | `mapToScene(vx, vy)` + pixmap 尺寸换算 |
| `_to_canvas(ix, iy)` | `mapFromScene(sx, sy)` |
| `<ButtonPress-1>` | `mousePressEvent` |
| `<B1-Motion>` | `mouseMoveEvent` |
| `<ButtonRelease-1>` | `mouseReleaseEvent` |
| `<Motion>` | `hoverMoveEvent`（或 scene item 的 hover） |
| `<KeyPress-Escape>` | `keyPressEvent` |
| `create_rectangle(...)` | `QGraphicsRectItem` |

**优化交互（用户要求可以优化）：**
- 裁剪选区外半透明暗色遮罩
- 手柄悬停时放大 + 变色
- 选区边框增加虚线或动画效果
- 增加吸附辅助线（可选）

**提交：**
```bash
git add canvas.py
git commit -m "feat: QGraphicsView-based CropCanvas with crop overlay"
```

---

### 任务 3: 工具函数提取

**目标：** 从原 `image_tool_cn.py` 提取图片保存/格式转换逻辑

**文件：**
- Create: `utils/image_ops.py`

**函数：**
```python
def save_image(img: Image.Image, out_path: str, quality: int = 85) -> None
def convert_for_save(img: Image.Image, fmt: str) -> Image.Image
def get_ext_for_format(fmt: str) -> str
```

**提交：**
```bash
git add utils/image_ops.py
git commit -m "feat: extract image save/convert utilities"
```

---

### 任务 4: 单张处理标签页

**目标：** 实现完整的单张图片处理界面（最复杂的标签页）

**文件：**
- Create: `tabs/single_tab.py`

**布局（QHBoxLayout 主布局）：**
```
┌─────────────────────────────────────────────┐
│ [文件路径输入框] [浏览] [加载]               │
├──────────────┬──────────────────────────────┤
│              │ 尺寸缩放                      │
│              │ ──────────────────────────    │
│              │ 宽度 [    ] px                 │
│  CropCanvas  │ 高度 [    ] px                 │
│  (QGraphics  │ ☐ 保持比例                     │
│   View)      │ 质量 [  ] (1-100)              │
│              │ [═══ 应用缩放 ═══]             │
│              │ ──────────────────────────    │
│              │ 自由裁剪                       │
│              │ X [  ] Y [  ]                  │
│              │ 宽[  ] 高[  ]                  │
│              │ [应用数值] [清除]               │
│              │ [═══ 应用裁剪 ═══]             │
│              │ ──────────────────────────    │
│              │ [重置] [覆盖原图] [另存为]      │
│              │ Ctrl+S / Ctrl+Shift+S          │
└──────────────┴──────────────────────────────┘
```

**关键实现细节：**
- 右侧控制栏用 QScrollArea 包裹，小窗口可滚动
- 尺寸输入框联动：勾选"保持比例"时修改宽度自动更新高度
- PNG 警告用 QFrame + 橙色样式显示
- 拖拽加载：`setAcceptDrops(True)` + `dropEvent`
- 快捷键：`QShortcut(QKeySequence("Ctrl+S"), ...)`
- 所有按钮逻辑从原代码迁移，Signal/Slot 连接

**状态管理：**
- 按钮初始 disabled，加载图片后 enabled
- 裁剪按钮：有选区时 enabled

**提交：**
```bash
git add tabs/single_tab.py
git commit -m "feat: PySide6 single image tab with resize/crop/save"
```

---

### 任务 5: 批量处理标签页

**目标：** 实现批量图片处理界面

**文件：**
- Modify: `tabs/batch_tab.py`

**布局：**
```
┌──────────────────────────────────────┐
│ 文件夹设置                            │
│ ──────────────────────────────────── │
│ 图片文件夹 [_________] [选择]         │
│ 输出文件夹 [_________] [选择]         │
│ ──────────────────────────────────── │
│ 处理参数                              │
│ 目标宽度 [____] px   压缩质量 [__]     │
│ ──────────────────────────────────── │
│           [═══ 开始处理 ═══]          │
│           准备就绪                     │
└──────────────────────────────────────┘
```

**线程处理：**
- `QThread` + `pyqtSignal` 在工作线程处理图片，主线程更新进度
- 开始前检查输出目录已有文件，弹确认框
- 完成后弹结果对话框

**提交：**
```bash
git add tabs/batch_tab.py
git commit -m "feat: PySide6 batch processing tab with QThread"
```

---

### 任务 6: 关于我们标签页

**目标：** 展示软件信息、依赖、开源信息

**文件：**
- Modify: `tabs/about_tab.py`

**内容：**
```
┌────────────────────────────────────┐
│                                    │
│      [Logo 128×128]               │
│      图轻剪 PicCraft              │
│      v20260502                     │
│                                    │
│  ──────── 技术栈 ────────         │
│  Python     3.13.3                 │
│  PySide6    6.x.x                  │
│  Pillow     11.x.x                 │
│  PyInstaller 6.x.x                 │
│                                    │
│  ──────── 开源信息 ────────       │
│  本项目基于 MIT 协议开源            │
│  ⭐ GitHub 求Star                 │
│  github.com/hotrichard1982/        │
│  pillow_gui                        │
│                                    │
│  ──────── 联系方式 ────────       │
│  © 重庆三人众科技有限公司          │
│  https://www.cq30.com/            │
│  QQ: 7602069                       │
│  7602069@qq.com                    │
└────────────────────────────────────┘
```

**动态获取依赖版本：**
```python
import sys, platform
from PySide6 import __version__ as pyside6_ver
from PIL import __version__ as pillow_ver
```

**提交：**
```bash
git add tabs/about_tab.py
git commit -m "feat: about tab with version/deps/open source info"
```

---

### 任务 7: main.py 集成 + 标题栏美化

**目标：** 将所有组件集成到主窗口，实现自定义标题栏

**文件：**
- Modify: `main.py`

**标题栏设计（QFrame 模拟，复用之前的 dark header 风格）：**
```
┌─────────────────────────────────────────────────────────┐
│ [Logo] 图轻剪 PicCraft      v20260502 © 重庆三人众科技   │
│        重庆三人众科技有限公司  ⭐ GitHub 官网  QQ: 7602069 │
├─────────────────────────────────────────────────────────┤
│  [单张处理] [批量处理] [关于我们]                         │
│                                                         │
│  ... tab content ...                                     │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

**PyInstaller 兼容处理：**
- 资源路径使用 `sys._MEIPASS` 检测打包环境

**提交：**
```bash
git add main.py
git commit -m "feat: integrate all tabs + custom header bar"
```

---

### 任务 8: 打包配置更新 + 测试

**目标：** 更新 PyInstaller spec，确认所有功能正常，编译 exe

**文件：**
- Modify: `image_tool_cn.spec`
- Keep: `test_image_tool.py`

**Spec 更新要点：**
- 移除 `hiddenimports=['tkinterdnd2']`
- 添加 `hiddenimports=['PySide6.QtCore', 'PySide6.QtGui', 'PySide6.QtWidgets']`
- 保留 `datas=[('logo.png', '.')]` 和 `icon='logo.ico'`
- 添加 `resources/style.qss` 到 datas

**测试清单：**
1. `pytest test_image_tool.py -v` — 16 个纯逻辑测试应全部通过
2. 手动测试：加载图片、拖拽裁剪、缩放、保存、批量处理、关于页
3. 快捷键测试：Ctrl+S / Ctrl+Shift+S / ESC
4. 拖拽加载测试
5. 小窗口滚动测试

**提交：**
```bash
git add image_tool_cn.spec
git commit -m "build: update spec for PySide6 + add QSS to datas"
```

---

### 任务 9: 重写 README.md

**目标：** 根据 PySide6 新版本完整重写项目文档

**文件：**
- Modify: `README.md`

**需覆盖的内容：**

```markdown
# 图轻剪 PicCraft 🖼️

单文件 → 模块化 Python GUI 工具，支持批量/单张图片的压缩、缩放、裁剪。
基于 PySide6（Qt）+ Pillow。

**重庆三人众科技有限公司** | QQ: 7602069 | 邮箱: 7602069@qq.com

## 功能

### 单张处理
- 缩放、裁剪（鼠标拖拽+数值输入）、实时预览
- 拖拽加载、快捷键 Ctrl+S / Ctrl+Shift+S / ESC

### 批量处理
- 按目标宽度批量等比缩放 + JPEG 压缩

### 关于我们
- 版本号、依赖信息、开源协议、公司信息

## 快速开始

pip install PySide6 Pillow
python main.py

## 构建 exe

pip install pyinstaller
pyinstaller image_tool_cn.spec

## 运行测试

pip install pytest
python -m pytest test_image_tool.py -v

## 项目结构

main.py            # 入口，主窗口
canvas.py          # QGraphicsView 裁剪画布
tabs/              # 三个标签页
  single_tab.py
  batch_tab.py
  about_tab.py
utils/image_ops.py # 图片工具函数
resources/style.qss # QSS 样式（明/暗双模式）

## 快捷键

Ctrl+S      覆盖原图
Ctrl+Shift+S 另存为
ESC         取消裁剪框

## 系统要求

Python 3.10+ | PySide6 | Pillow
明/暗模式切换：标题栏 ☀/🌙 按钮
```

**提交：**
```bash
git add README.md
git commit -m "docs: rewrite README for PySide6 modular version"
```

---

### 任务 10: 清理旧代码 + 最终发布

**目标：** 删除 image_tool_cn.py，编译 exe，发布 Release

**步骤：**
1. 删除 `image_tool_cn.py`
2. 编译 exe
   ```bash
   pyinstaller image_tool_cn.spec
   ```
3. 测试 exe 运行
4. 提交 + 发布 Release v20260503

**提交：**
```bash
git add -A
git commit -m "refactor: remove old tkinter code, complete PySide6 migration"
git push
gh release create v20260503 --title "v20260503 - PySide6 重构" ...
```

---

## 风险与注意事项

| 风险 | 缓解措施 |
|------|---------|
| QGraphicsView 裁剪交互细节不同 | 先写单元测试验证坐标换算，再实现交互 |
| PySide6 打包体积大 | 接受，约 70MB |
| 线程安全问题 | 严格使用 Signal/Slot，不在工作线程操作 GUI |
| PyInstaller 兼容性 | 提前测试打包，确认 Qt platform plugin 正确包含 |
| 旧 tkinter 代码未完全迁移 | 逐模块测试，对比功能清单 |

## 执行顺序

```
任务 0 (环境) → 任务 1 (框架) → 任务 2 (画布) → 任务 3 (工具)
                                                    ↓
任务 4 (单张) ← 任务 5 (批量) ← 任务 6 (关于) → 任务 7 (集成)
                                                    ↓
任务 8 (打包) → 任务 9 (README) → 任务 10 (清理发布)
```

任务 2 是瓶颈——画布重写工作量最大，但任务 4/5/6 可在任务 3 完成后并行开发。
