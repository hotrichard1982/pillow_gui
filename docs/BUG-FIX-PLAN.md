# PicCraft Bug 修复计划

> 基于代码审查报告，共 10 项。按优先级排列，每项给出了具体文件、行号、修复内容。

---

## Bug 1：画布背景色与暗色主题不协调

**文件：** `canvas.py:47`
**严重度：** 中

```python
# 当前（浅灰）
self.setBackgroundBrush(QBrush(QColor("#f1f5f9")))
# 修复为暗色
self.setBackgroundBrush(QBrush(QColor("#1e293b")))
```

---

## Bug 2：关于页 Logo 路径打包后失效

**文件：** `about_tab.py:34`
**严重度：** 中（exe 运行时 Logo 不显示）

```python
# 当前（裸路径，exe 中找不到）
pix = QPixmap("logo.png").scaled(...)

# 修复：从 main.py 复制 _resource_path 或改用 sys._MEIPASS
import sys, os
def _resource_path(relative):
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative)
    return os.path.join(os.path.dirname(__file__), relative)

pix = QPixmap(_resource_path("logo.png")).scaled(...)
```

---

## Bug 3：canvas.py 核心裁剪逻辑零测试覆盖

**文件：** `test_image_tool.py`（修改）/ `canvas.py`（被测）
**严重度：** 高（核心功能无测试保护）

需要新增测试覆盖：
| 函数 | 分支数 |
|---|---|
| `_compute_handle_rect` | 8 个手柄 + 默认返回 |
| `_handle_drag` | new / move / handle 3 种模式 |
| `_hit_test_handle` | 命中/未命中 |
| `_inside_rect` | 内部/外部/无选区 |

可复用 `TestHandleComputation` 中已有的测试数据直接编写 QTest 用例。

**执行步骤：**
1. 在 `test_image_tool.py` 新增 `TestCropCanvas` 类
2. 用 `QApplication` 创建画布实例
3. 加载测试图片，调用 `_compute_handle_rect` / `_hit_test_handle` 等方法
4. 断言结果与预期一致
5. 运行 `pytest test_image_tool.py -v` 确认通过

---

## Bug 4：批量处理错误信息不展示给用户

**文件：** `batch_tab.py:44-46`
**严重度：** 中

```python
# 当前：错误通过 print 输出到 stdout，GUI 用户看不到
except Exception as e:
    errors.append(f)
    self.log.emit(f"处理失败 {f}: {e}")

# 修复：在 _on_finished 中将完整错误列表放入对话框
```

**执行步骤：**
1. 修改 `BatchWorker.log` → `BatchWorker.error_detail` Signal
2. `_on_finished` 中展示完整失败列表（含原因），不限于前 5 个

---

## Bug 5：spec 文件 hiddenimports 不完整

**文件：** `image_tool_cn.spec:7-8`
**严重度：** 低（当前测试未触发，但打包后可能缺模块）

```python
# 当前
hiddenimports=['PySide6.QtCore', 'PySide6.QtGui', ...]

# 修复：补全
hiddenimports=[
    'PySide6.QtCore', 'PySide6.QtGui', 'PySide6.QtWidgets',
    'PySide6.QtSvg',          # Qt SVG 支持
    'PIL._imaging',            # Pillow C 扩展
    'PIL.Image', 'webbrowser',
]
```

---

## Bug 6：README 项目结构列了不存在的文件

**文件：** `README.md`
**严重度：** 低（文档不对）

README 项目结构一节列出了 `resources/style.qss`，但该文件不存在（QSS 在 `main.py` 内）。修复：从结构图中删掉该文件。

---

## Bug 7：拖拽到画布区域无效

**文件：** `canvas.py`（新增）、`tabs/single_tab.py`
**严重度：** 中（用户体验断裂）

当前只有 `SingleTab` 设置了 `setAcceptDrops(True)`，但 QGraphicsView 的 viewport 会拦截 drop 事件。拖图片到画布上无反应。

**修复：**
1. 在 `CropCanvas.__init__` 中 `self.setAcceptDrops(True)`
2. 重写 `dragEnterEvent` / `dropEvent`，获取文件路径后发出 Signal
3. `SingleTab` 连接该 Signal 调用 `_load_image`

---

## Bug 8：裁剪拖拽时全量重建 scene

**文件：** `canvas.py:131-140 (_update_display)`
**严重度：** 低（小图无感，大图可能闪烁）

```python
# 当前：每次鼠标移动都 scene.clear() + 重建所有 item
def _update_display(self):
    self._scene.clear()
    ...

# 修复思路：pixmap item 只在图片变化时重建
# 裁剪 overlay 用独立 QGraphicsItem，仅调用 update() 重绘
```

**执行步骤：**
1. 创建 `CropOverlayItem(QGraphicsItem)` 类，独立管理选区绘制
2. `_update_display` 拆为 `_rebuild_pixmap`（仅加载图片时调用）和 `_update_overlay`（拖拽时调用）
3. 拖拽 `_handle_drag` 中只调用 `_update_overlay`

---

## Bug 9：single_tab.py 三处重复的布局包装模式

**文件：** `tabs/single_tab.py:130,176,209`
**严重度：** 低（代码整洁）

```python
# 三处同样 3 行
w = QWidget()
w.setLayout(section)
return w

# 提取为辅助方法
def _wrap_section(self, layout):
    w = QWidget()
    w.setLayout(layout)
    return w
```

---

## Bug 10：批量处理 QMessageBox 可能在非 GUI 线程触发

**文件：** `batch_tab.py:137 (BatchWorker.run)`
**严重度：** 低（当前 `_on_finished` 在主线程，但如果有其他异常...）

`BatchWorker.run()` 在 QThread 中执行，结束后 `_on_finished` 通过 Signal 回到主线程调用 `QMessageBox`。当前实现是安全的，但在 `_start` 方法中 `self.start_btn.setEnabled(True)` 的异常恢复路径如果被绕过可能导致按钮永久禁用。建议在高负载场景添加超时保护或添加重试逻辑。
