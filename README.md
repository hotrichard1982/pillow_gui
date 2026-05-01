# 图轻剪 PicCraft 🖼️

模块化 Python GUI 图片处理工具，支持批量/单张图片的压缩、缩放、裁剪。

基于 **PySide6（Qt）** + **Pillow** | 明/暗模式一键切换

**重庆三人众科技有限公司** | QQ: 7602069 | 邮箱: 7602069@qq.com | [官网](https://www.cq30.com/)

---

## 功能

### 单张处理
- **缩放**：按目标尺寸等比或自由缩放，支持保持原图比例
- **裁剪**：鼠标拖拽选择裁剪区域，8 个可拖动手柄（四角/四边），ESC 取消，支持数值输入
- **实时预览**：每次操作立即刷新画布结果，半透明裁剪遮罩
- **拖拽加载**：从资源管理器拖入图片自动加载
- **另存为**（Ctrl+Shift+S）：JPG / PNG / WebP / BMP
- **覆盖原图**（Ctrl+S）：保存到原路径，PNG 自动转 JPG

### 批量处理
- 按目标宽度等比缩放文件夹内所有图片
- 设置 JPEG 压缩质量（1-100）
- 后台线程处理，进度实时显示
- 开始前检测覆盖风险

### 关于我们
- 版本号、技术栈依赖、开源协议、公司信息、GitHub 链接

## 界面

- 明/暗模式切换（标题栏 ☀/🌙 按钮），偏好自动记忆
- 响应式布局，小窗口右侧自动滚屏
- 现代扁平设计，无卡片边框

---

## 快速开始

```bash
# 安装依赖
pip install PySide6 Pillow

# 运行
python main.py
```

## 构建 exe（Windows）

```bash
pip install pyinstaller
pyinstaller image_tool_cn.spec
```

输出：`dist/PicCraft.exe`（约 67 MB）

## 运行测试

```bash
pip install pytest
python -m pytest test_image_tool.py -v
```

---

## 项目结构

```
pillow_gui/
├── main.py                # 入口，QMainWindow + 明暗模式
├── canvas.py              # QGraphicsView 裁剪画布
├── tabs/
│   ├── single_tab.py      # 单张处理标签页
│   ├── batch_tab.py       # 批量处理标签页（QThread）
│   └── about_tab.py       # 关于我们标签页
├── utils/
│   └── image_ops.py       # 图片保存/格式转换工具
├── image_tool_cn.spec     # PyInstaller 打包配置
├── logo.png / logo.ico    # Logo 与图标
└── test_image_tool.py     # pytest 单元测试（16 例）
```

---

## 快捷键

| 快捷键 | 功能 |
|--------|------|
| `Ctrl+S` | 覆盖原图（PNG 自动转 JPG） |
| `Ctrl+Shift+S` | 另存为 |
| `ESC` | 取消裁剪框 |

---

## 系统要求

- **Python 3.10+**
- **PySide6**：`pip install PySide6`
- **Pillow**：`pip install Pillow`

---

## 开源协议

MIT License

⭐ 欢迎 Star：[github.com/hotrichard1982/pillow_gui](https://github.com/hotrichard1982/pillow_gui)
