# 图轻剪 PicCraft 🖼️

单文件 Python GUI 工具，支持批量/单张图片的压缩、缩放、裁剪。基于 `tkinter` + `Pillow`。

**重庆三人众科技有限公司** | QQ: 7602069 | 邮箱: 7602069@qq.com

---

## 功能

### 单张处理
- **缩放**：按目标宽高等比或自由缩放，支持保持原图比例
- **裁剪**：鼠标拖拽选择裁剪区域，8 个可拖动手柄编辑裁剪框（四角/四边），ESC 取消
- **拖拽加载**：从资源管理器拖入图片自动加载，非图片格式弹出警告
- **实时预览**：每次操作立即在画布上刷新结果
- **另存为**（Ctrl+Shift+S）：弹出格式选择对话框（JPG/PNG/WebP/BMP）
- **覆盖原图**（Ctrl+S）：保存到原文件路径；PNG 自动转为 JPG 压缩
- **PNG 提示**：加载 PNG 时显示红色警告「PNG 无法压缩，保存时默认转 JPG」

### 批量处理
- 按目标宽度等比缩放文件夹内所有图片
- 设置 JPEG 压缩质量（1-100）
- 输出到指定文件夹
- 开始处理前检查覆盖风险

---

## 快速开始

```bash
# 安装依赖
pip install Pillow

# 运行
python image_tool_cn.py
```

## 构建 exe（Windows）

```bash
pip install pyinstaller
pyinstaller image_tool_cn.spec
```

生成的可执行文件在 `dist/image_tool_cn.exe`。

## 运行测试

```bash
pip install pytest
python -m pytest test_image_tool.py -v
```

---

## 文件结构

| 文件 | 用途 |
|------|------|
| `image_tool_cn.py` | 主程序（含 `CropCanvas` 裁剪画布 + `ImageToolCN` GUI 主体）|
| `test_image_tool.py` | pytest 单元测试（缩放/裁剪/坐标换算/手柄拖动）|
| `image_tool_cn.spec` | PyInstaller 打包配置 |
| `AGENTS.md` | OpenCode 辅助指令文件 |
| `build/` | 构建产物（已 gitignore）|
| `dist/` | 打包输出目录（已 gitignore）|

---

## 系统要求

- **Python 3.10+**
- **Pillow**：`pip install Pillow`
- **tkinter**：Windows 下通常随 Python 自带；Linux 下可能需要 `sudo apt install python3-tk`
- **tkinterdnd2**（可选）：拖拽加载功能需要，`pip install tkinterdnd2`

---

## 快捷键

| 快捷键 | 功能 |
|--------|------|
| `Ctrl+S` | 覆盖原图（PNG 自动转 JPG） |
| `Ctrl+Shift+S` | 另存为 |
| `ESC` | 取消裁剪框 |

---

## 注意事项

- 批量处理输出固定为 JPEG，会自动丢弃 PNG 透明通道
- PNG 为无损格式，质量参数对其无效；界面会显示红色警告，保存时默认转 JPG
- 裁剪/缩放操作仅在内存中修改，点击保存才写入磁盘
- 拖拽功能需要安装 `tkinterdnd2`：`pip install tkinterdnd2`
