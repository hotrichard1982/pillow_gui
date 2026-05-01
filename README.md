# 图轻剪 PicCraft 🖼️

模块化 Python GUI 图片处理工具 — 批量/单张图片压缩、缩放、裁剪。

**PySide6（Qt）+ Pillow · 暗色主题**

**重庆三人众科技有限公司** | QQ: 7602069 | 邮箱: 7602069@qq.com | [官网](https://www.cq30.com/)

---

## 功能

### 单张处理
- 缩放：按目标尺寸等比或自由缩放，支持保持原图比例
- 裁剪：鼠标拖拽选区 + 8 个可拖动手柄（四角/四边）+ 数值输入，ESC 取消
- 实时预览：半透明裁剪遮罩，即时反馈
- 拖拽加载：从资源管理器直接拖入图片
- 另存为（Ctrl+Shift+S）/ 覆盖原图（Ctrl+S）

### 批量处理
- 按目标宽度等比缩放文件夹内所有图片
- JPEG 压缩质量可调（1-100）
- QThread 后台处理，进度实时显示

### 关于我们
- 版本号、技术栈依赖、开源协议、公司信息

---

## 快速开始

```bash
pip install PySide6 Pillow
python main.py
```

## 构建 exe（Windows）

```bash
pip install pyinstaller
pyinstaller image_tool_cn.spec
```
输出：`dist/PicCraft.exe`

## 运行测试

```bash
pip install pytest
python -m pytest test_image_tool.py -v
```

---

## 项目结构

```
PicCraft/
├── main.py                # 入口 · QMainWindow
├── canvas.py              # QGraphicsView 裁剪画布
├── tabs/
│   ├── single_tab.py      # 单张处理
│   ├── batch_tab.py       # 批量处理（QThread）
│   └── about_tab.py       # 关于我们
├── utils/image_ops.py     # 图片保存/格式转换
├── image_tool_cn.spec     # PyInstaller 打包配置
├── logo.png / logo.ico
└── test_image_tool.py     # 16 个 pytest
```

---

## 快捷键

| 快捷键 | 功能 |
|--------|------|
| `Ctrl+S` | 覆盖原图 |
| `Ctrl+Shift+S` | 另存为 |
| `ESC` | 取消裁剪框 |

---

## 系统要求

- Python 3.10+
- PySide6：`pip install PySide6`
- Pillow：`pip install Pillow`

## 协议

MIT License · ⭐ [github.com/hotrichard1982/PicCraft](https://github.com/hotrichard1982/PicCraft)
