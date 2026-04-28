# AGENTS.md

## 项目概述

单文件 Python GUI 工具，支持批量/单张图片的压缩、缩放、裁剪。基于 `tkinter` + `Pillow`。

两个标签页：
- **单张处理** — 第一页（默认），缩放 + 鼠标拖拽裁剪 + 数值裁剪 + 预览
- **批量处理** — 按目标宽度批量等比缩放 + JPEG 压缩

## 命令速查

```bash
# 运行应用
python image_tool_cn.py

# 构建 exe（Windows）
pyinstaller image_tool_cn.spec
```

## 依赖

- **Pillow**: `pip install Pillow`
- **tkinter**: Windows 下通常随 Python 自带；Linux 下可能需要 `sudo apt install python3-tk`
- **PyInstaller**: 仅打包时需要，`pip install pyinstaller`

## 结构说明

| 文件 | 用途 |
|------|------|
| `image_tool_cn.py` | 唯一源码，约 420 行。包含 `CropCanvas`（图片预览 + 鼠标裁剪）和 `ImageToolCN`（GUI 主体）|
| `image_tool_cn.spec` | PyInstaller 打包配置 |
| `build/`、`dist/` | 构建产物，**不要手动修改** |

### 类关系

```
CropCanvas(tk.Canvas)       ← 图片预览 + 鼠标拖拽红色裁剪矩形框
    └── ImageToolCN 中使用   ← 单张标签页右侧预览区

ImageToolCN                 ← 应用主体，创建 Notebook 双标签页
    ├── 单张标签页           ← 缩放 + 裁剪 + 预览 + 保存/重置
    └── 批量标签页           ← 保留原有逻辑（ttk 化）
```

### 单张缩放 2 种模式

| 模式 | 输入 | 行为 |
|---|---|---|
| 保持比例 (勾选) | 修改宽或高 | 另一维度自动等比计算 |
| 自由尺寸 (取消勾选) | 宽 + 高 | 分别设置，不保持比例 |

### 裁剪框交互

| 操作 | 行为 |
|---|---|
| 拖拽四角手柄 | 同时调整宽高（鼠标变为对角箭头） |
| 拖拽四边中点 | 调整单边（鼠标变为水平/垂直箭头） |
| 拖拽框内部 | 整体移动裁剪框（鼠标变为十字移动箭头） |
| 点击框外部 | 绘制新裁剪框 |
| ESC 键 | 清除裁剪框 |

## 注意事项

- 无测试、无 lint、无 CI 配置，裸仓库
- 批量处理输出固定为 JPEG，`convert("RGB")` 丢弃透明通道
- 单张处理保存时弹出格式选择对话框，JPEG 使用界面质量参数
- 选择图片后自动加载并显示到画布；单张标签页无输出路径输入框
- 单张处理保存时弹出格式选择对话框，默认后缀匹配原图格式；每次保存均需选择路径，避免覆盖
- 鼠标裁剪坐标自动换算：Canvas 预览缩放 → 原图真实像素；`_internal_update` 标志防止 trace 回调循环
- 加载新图片时自动清空裁剪区域、填充原图尺寸到缩放输入框
- 「应用裁剪」/「应用缩放」修改内存中的 `display_image` 并立即刷新画布预览；「保存到文件」才写入磁盘
- 「重置」恢复 `display_image` 为原始图片
