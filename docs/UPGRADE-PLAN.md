# PicCraft 优化升级方案（待人工审核）

> 以下方案非 Bug，按优先级排列。审核通过后逐项执行。

---

## 高优先级

### 1. 明暗双主题切换
恢复 `docs/plans/2026-05-02-pyside6-refactor.md` 中的双主题设计。
- 标题栏右侧添加 ☀/🌙 切换按钮
- `QSettings` 记住用户偏好
- 亮色主题 QSS 在 `main.py` 中已注释待启用

### 2. EXIF 方向自动修正
手机拍照的图片含 Orientation 标签，直接 `Image.open()` 显示/裁剪会旋转。
- 在 `canvas.py:load_image` 中加一行 `img = ImageOps.exif_transpose(img)`
- 需要 `from PIL import ImageOps`

### 3. 批量处理输出格式可选
当前硬编码输出为 JPEG。添加下拉框（`QComboBox`）支持 PNG/WebP/BMP。
- 复用 `utils/image_ops.py` 的 `save_image` 逻辑
- UI 增加「输出格式」下拉框

---

## 中优先级

### 4. 撤销/重做
在 `CropCanvas` 中维护操作历史栈，支持 Ctrl+Z / Ctrl+Y。
- 每步裁剪/缩放入栈（`list[Image.Image]`）
- `single_tab.py` 添加两个按钮

### 5. 批量处理进度条可视化
当前仅文本显示进度。添加 `QProgressBar`，更直观。
- `BatchWorker.progress` Signal 携带当前/总数
- `QProgressBar.setRange(0, total)` + `setValue(current)`

### 6. 错误日志写入文件
`batch_tab.py` 错误通过 `print()` 输出到 stdout，GUI 用户看不到。
- 写入 `batch_errors.log` 临时文件
- 完成后提示用户查看或直接展示完整列表

### 7. 画布裁切选区性能优化
裁剪 overlay 从 scene 重建中分离。
- 创建独立的 `CropOverlayItem(QGraphicsItem)` 
- 详见 Bug 8 修复方案

---

## 低优先级

### 8. CI/CD 自动化
添加 `.github/workflows/build.yml`：lint → pytest → PyInstaller 打包。

### 9. 格式转换功能
单张标签页加格式下拉框 + 转换按钮（WebP→PNG、PNG→JPG 等）。

### 10. 多语言支持
提取 UI 字符串到 JSON 语言文件，支持中/英文切换。

### 11. 批量水印
批量处理中添加可选文字/图片水印叠加。

---

## 审核决策

| 编号 | 方案 | 是否执行 |
|------|------|----------|
| 1 | 明暗双主题 | |
| 2 | EXIF 方向修正 | |
| 3 | 批量输出格式可选 | |
| 4 | 撤销/重做 | |
| 5 | 进度条可视化 | |
| 6 | 错误日志写文件 | |
| 7 | 裁剪性能优化 | |
| 8 | CI/CD | |
| 9 | 格式转换 | |
| 10 | 多语言 | |
| 11 | 批量水印 | |
