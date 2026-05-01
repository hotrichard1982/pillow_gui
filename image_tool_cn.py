import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk
import os
import threading
import webbrowser

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    HAS_DND = True
except ImportError:
    HAS_DND = False
    DND_FILES = None
    TkinterDnD = type("_FakeDnD", (tk.Tk,), {})


class CropCanvas(tk.Canvas):
    HANDLE_SIZE = 6
    MIN_CROP_SIZE = 5
    HANDLE_TAGS = ("tl", "tc", "tr", "ml", "mr", "bl", "bc", "br")

    def __init__(self, master, **kwargs):
        kwargs.setdefault("bg", "#d9d9d9")
        kwargs.setdefault("cursor", "cross")
        super().__init__(master, **kwargs)

        self.original_image = None
        self.display_image = None
        self.photo = None
        self.scale = 1.0
        self.offset_x = 0
        self.offset_y = 0
        self.disp_w = 0
        self.disp_h = 0

        self.crop_rect = None
        self._cached_handles = None

        self._drag_mode = None
        self._drag_start = (0, 0)
        self._drag_start_rect = None

        self._on_crop_changed = None
        self._on_display_changed = None

        self.bind("<ButtonPress-1>", self._on_press)
        self.bind("<B1-Motion>", self._on_drag)
        self.bind("<ButtonRelease-1>", self._on_release)
        self.bind("<Configure>", self._on_resize)
        self.bind("<KeyPress-Escape>", self._on_escape)
        self.bind("<Motion>", self._on_motion)
        self.focus_set()

    def set_callbacks(self, on_crop_changed, on_display_changed):
        self._on_crop_changed = on_crop_changed
        self._on_display_changed = on_display_changed

    def load_image(self, path):
        try:
            img = Image.open(path)
            self.original_image = img
            self.display_image = img.copy()
            self.crop_rect = None
            self._update_display()
            if self._on_display_changed:
                self._on_display_changed(*self.display_image.size)
            return True
        except Exception:
            return False

    def get_display_image(self):
        return self.display_image

    def apply_crop(self):
        if self.crop_rect is None:
            return
        x, y, w, h = self.crop_rect
        self.display_image = self.display_image.crop((x, y, x + w, y + h))
        self.crop_rect = None
        self._update_display()
        if self._on_display_changed:
            self._on_display_changed(*self.display_image.size)

    def apply_resize(self, tw, th):
        self.display_image = self.display_image.resize(
            (tw, th), Image.Resampling.LANCZOS)
        self.crop_rect = None
        self._update_display()
        if self._on_display_changed:
            self._on_display_changed(*self.display_image.size)

    def reset_to_original(self):
        self.display_image = self.original_image.copy()
        self.crop_rect = None
        self._update_display()
        if self._on_display_changed:
            self._on_display_changed(*self.display_image.size)

    def has_crop(self):
        return self.crop_rect is not None

    def get_crop_rect(self):
        return self.crop_rect

    def set_crop_rect_numeric(self, x, y, w, h):
        if self.display_image is None:
            return
        iw, ih = self.display_image.size
        x = max(0, min(x, iw - 1))
        y = max(0, min(y, ih - 1))
        w = max(self.MIN_CROP_SIZE, min(w, iw - x))
        h = max(self.MIN_CROP_SIZE, min(h, ih - y))
        self.crop_rect = (x, y, w, h)
        self._update_display()
        if self._on_crop_changed:
            self._on_crop_changed(self.crop_rect)

    def clear_crop(self):
        self.crop_rect = None
        self._update_display()
        if self._on_crop_changed:
            self._on_crop_changed(None)

    # ---------- display ----------

    def _to_image(self, cx, cy):
        return ((cx - self.offset_x) / self.scale,
                (cy - self.offset_y) / self.scale)

    def _to_canvas(self, ix, iy):
        return (ix * self.scale + self.offset_x,
                iy * self.scale + self.offset_y)

    def _update_display(self):
        if self.display_image is None:
            return
        cw = self.winfo_width()
        ch = self.winfo_height()
        if cw < 10 or ch < 10:
            return

        iw, ih = self.display_image.size
        self.scale = min(cw / iw, ch / ih)
        self.disp_w = int(iw * self.scale)
        self.disp_h = int(ih * self.scale)
        self.offset_x = (cw - self.disp_w) // 2
        self.offset_y = (ch - self.disp_h) // 2

        self.display_image_copy = self.display_image.resize(
            (self.disp_w, self.disp_h), Image.Resampling.LANCZOS)
        self.photo = ImageTk.PhotoImage(self.display_image_copy)

        self.delete("all")
        self._cached_handles = None
        self.create_image(self.offset_x, self.offset_y, anchor="nw",
                          image=self.photo, tags="bgimg")
        if self.crop_rect:
            self._draw_crop_overlay()

    def _draw_crop_overlay(self):
        x, y, w, h = self.crop_rect
        cx1, cy1 = self._to_canvas(x, y)
        cx2, cy2 = self._to_canvas(x + w, y + h)

        self.delete("crop")
        self.create_rectangle(cx1, cy1, cx2, cy2,
                              outline="red", width=2, tags="crop")

        hs = self.HANDLE_SIZE
        mid_x = (cx1 + cx2) // 2
        mid_y = (cy1 + cy2) // 2

        handle_pos = {
            "tl": (cx1, cy1), "tc": (mid_x, cy1), "tr": (cx2, cy1),
            "ml": (cx1, mid_y), "mr": (cx2, mid_y),
            "bl": (cx1, cy2), "bc": (mid_x, cy2), "br": (cx2, cy2),
        }
        for _tag, (hx, hy) in handle_pos.items():
            self.create_rectangle(
                hx - hs, hy - hs, hx + hs, hy + hs,
                fill="white", outline="red", width=1, tags="crop")

    def _on_motion(self, event):
        if self.crop_rect is None or self.display_image is None:
            self.config(cursor="cross")
            return
        ox, oy = self.offset_x, self.offset_y
        if not (ox <= event.x <= ox + self.disp_w and
                oy <= event.y <= oy + self.disp_h):
            self.config(cursor="")
            return
        handle = self._hit_test_handle(event.x, event.y)
        if handle is not None:
            cursors = {
                "tl": "size_nw_se", "br": "size_nw_se",
                "tr": "size_ne_sw", "bl": "size_ne_sw",
                "tc": "sb_v_double_arrow", "bc": "sb_v_double_arrow",
                "ml": "sb_h_double_arrow", "mr": "sb_h_double_arrow",
            }
            self.config(cursor=cursors.get(handle, "cross"))
            return
        if self._inside_rect(event.x, event.y):
            self.config(cursor="fleur")
            return
        self.config(cursor="cross")

    def _on_resize(self, event):
        if self.display_image:
            self._update_display()

    # ---------- mouse ----------

    def _on_press(self, event):
        if self.display_image is None:
            return
        ox, oy = self.offset_x, self.offset_y
        if not (ox <= event.x <= ox + self.disp_w and
                oy <= event.y <= oy + self.disp_h):
            return

        if self.crop_rect is not None:
            handle = self._hit_test_handle(event.x, event.y)
            if handle is not None:
                self._drag_mode = handle
                self._drag_start = self._to_image(event.x, event.y)
                self._drag_start_rect = self.crop_rect
                return
            if self._inside_rect(event.x, event.y):
                self._drag_mode = "move"
                self._drag_start = self._to_image(event.x, event.y)
                self._drag_start_rect = self.crop_rect
                return

        self._drag_mode = "new"
        self._drag_start = self._to_image(event.x, event.y)
        self._drag_start_rect = None
        self.crop_rect = None
        self.delete("crop")

    def _on_drag(self, event):
        if self._drag_mode is None:
            return

        ix, iy = self._to_image(event.x, event.y)

        if self._drag_mode == "new":
            sx, sy = self._drag_start
            x1, y1 = min(sx, ix), min(sy, iy)
            x2, y2 = max(sx, ix), max(sy, iy)
            iw, ih = self.display_image.size
            x1 = max(0, int(x1))
            y1 = max(0, int(y1))
            x2 = min(iw, int(x2))
            y2 = min(ih, int(y2))
            self.crop_rect = (x1, y1, x2 - x1, y2 - y1)
            self._update_display()

        elif self._drag_mode == "move":
            sx, sy = self._drag_start
            dx, dy = ix - sx, iy - sy
            ox, oy, ow, oh = self._drag_start_rect
            iw, ih = self.display_image.size
            nx = max(0, min(int(ox + dx), iw - ow))
            ny = max(0, min(int(oy + dy), ih - oh))
            self.crop_rect = (nx, ny, ow, oh)
            self._update_display()

        elif self._drag_mode in self.HANDLE_TAGS:
            self.crop_rect = self._compute_handle_rect(
                self._drag_mode, ix, iy)
            self._update_display()

    def _on_release(self, event):
        if self._drag_mode is None:
            return

        if self._drag_mode == "new" and self.crop_rect is not None:
            x, y, w, h = self.crop_rect
            if w < self.MIN_CROP_SIZE or h < self.MIN_CROP_SIZE:
                self.crop_rect = None
                self._update_display()
            else:
                self._update_display()

        self._drag_mode = None
        self._drag_start = (0, 0)
        self._drag_start_rect = None

        if self._on_crop_changed:
            self._on_crop_changed(self.crop_rect)

    # ---------- handle / hit test ----------

    def _handle_positions(self):
        if self._cached_handles is not None:
            return self._cached_handles
        x, y, w, h = self.crop_rect
        cx1, cy1 = self._to_canvas(x, y)
        cx2, cy2 = self._to_canvas(x + w, y + h)
        mid_x = (cx1 + cx2) // 2
        mid_y = (cy1 + cy2) // 2
        self._cached_handles = {
            "tl": (cx1, cy1), "tc": (mid_x, cy1), "tr": (cx2, cy1),
            "ml": (cx1, mid_y), "mr": (cx2, mid_y),
            "bl": (cx1, cy2), "bc": (mid_x, cy2), "br": (cx2, cy2),
        }
        return self._cached_handles

    def _hit_test_handle(self, cx, cy):
        if self.crop_rect is None:
            return None
        tol = self.HANDLE_SIZE + 3
        for tag, (hx, hy) in self._handle_positions().items():
            if abs(cx - hx) <= tol and abs(cy - hy) <= tol:
                return tag
        return None

    def _inside_rect(self, cx, cy):
        if self.crop_rect is None:
            return False
        x, y, w, h = self.crop_rect
        cx1, cy1 = self._to_canvas(x, y)
        cx2, cy2 = self._to_canvas(x + w, y + h)
        return cx1 <= cx <= cx2 and cy1 <= cy <= cy2

    def _compute_handle_rect(self, handle, ix, iy):
        x, y, w, h = self._drag_start_rect
        x2, y2 = x + w, y + h
        iw, ih = self.display_image.size
        m = self.MIN_CROP_SIZE

        if handle == "tl":
            nx = max(0, min(int(ix), x2 - m))
            ny = max(0, min(int(iy), y2 - m))
            return (nx, ny, x2 - nx, y2 - ny)
        elif handle == "tr":
            nx2 = min(iw, max(int(ix), x + m))
            ny = max(0, min(int(iy), y2 - m))
            return (x, ny, nx2 - x, y2 - ny)
        elif handle == "bl":
            nx = max(0, min(int(ix), x2 - m))
            ny2 = min(ih, max(int(iy), y + m))
            return (nx, y, x2 - nx, ny2 - y)
        elif handle == "br":
            nx2 = min(iw, max(int(ix), x + m))
            ny2 = min(ih, max(int(iy), y + m))
            return (x, y, nx2 - x, ny2 - y)
        elif handle == "tc":
            ny = max(0, min(int(iy), y2 - m))
            return (x, ny, w, y2 - ny)
        elif handle == "bc":
            ny2 = min(ih, max(int(iy), y + m))
            return (x, y, w, ny2 - y)
        elif handle == "ml":
            nx = max(0, min(int(ix), x2 - m))
            return (nx, y, x2 - nx, h)
        elif handle == "mr":
            nx2 = min(iw, max(int(ix), x + m))
            return (x, y, nx2 - x, h)
        return (x, y, w, h)

    def _on_escape(self, event):
        self.clear_crop()


class ImageToolCN:
    IMG_EXTS = (".jpg", ".jpeg", ".png", ".webp", ".bmp")

    # ========== 现代配色方案 (Software 3.0) ==========
    C_PRIMARY = "#3b82f6"          # 明亮蓝 - 主操作
    C_PRIMARY_HOVER = "#2563eb"    # 深蓝 - 悬停
    C_DARK = "#0f172a"             # 深 slate - 头部/底部
    C_BG = "#f8fafc"               # 极浅灰蓝 - 主背景
    C_SURFACE = "#ffffff"          # 纯白 - 卡片表面
    C_SURFACE_ALT = "#f1f5f9"      # 浅灰蓝 - 交替表面
    C_ACCENT = "#ef4444"           # 红 - 警告/强调
    C_TEXT = "#1e293b"             # 深 slate - 主文本
    C_TEXT_MUTED = "#64748b"       # 中灰 - 次要文本
    C_SUCCESS = "#10b981"          # 翠绿 - 成功
    C_SUCCESS_HOVER = "#059669"    # 深绿 - 成功悬停
    C_BORDER = "#e2e8f0"           # 浅灰 - 边框
    C_BORDER_HOVER = "#cbd5e1"     # 中浅灰 - 悬停边框
    C_WARNING_BG = "#fff7ed"       # 浅橙 - 警告背景
    C_WARNING_TEXT = "#c2410c"     # 深橙 - 警告文本

    # ========== 字体方案 ==========
    FONT_FAMILY = "Segoe UI"

    def _on_file_drop(self, event):
        raw = event.data
        path = raw.strip().strip('{}').strip('"').strip()
        if not os.path.isfile(path):
            return
        if not path.lower().endswith(self.IMG_EXTS):
            messagebox.showwarning("格式不支持",
                                   f"不支持的文件格式，请拖入图片文件\n"
                                   f"支持：JPG、JPEG、PNG、WebP、BMP")
            return
        self.single_input.set(path)
        self._load_single_image()

    def __init__(self, root):
        self.root = root
        self.root.title("图轻剪 PicCraft")
        self.root.geometry("1120x820")
        self.root.minsize(900, 600)
        self.root.resizable(True, True)
        self.root.configure(bg=self.C_BG)

        self._apply_theme()

        # ---- 顶部导航栏 ----
        header = tk.Frame(root, bg=self.C_DARK, height=80)
        header.pack(fill=tk.X, side=tk.TOP)
        header.pack_propagate(False)

        # 左侧：Logo + 标题
        header_left = tk.Frame(header, bg=self.C_DARK)
        header_left.pack(side=tk.LEFT, fill=tk.Y)

        logo_path = os.path.join(os.path.dirname(__file__), "logo.png")
        if os.path.isfile(logo_path):
            self.logo_img = ImageTk.PhotoImage(
                Image.open(logo_path).resize((48, 48), Image.Resampling.LANCZOS))
            tk.Label(header_left, image=self.logo_img, bg=self.C_DARK).pack(
                side=tk.LEFT, padx=(20, 12), pady=16)

        title_frame = tk.Frame(header_left, bg=self.C_DARK)
        title_frame.pack(side=tk.LEFT, pady=12)
        tk.Label(title_frame, text="图轻剪 PicCraft",
                 font=(self.FONT_FAMILY, 18, "bold"),
                 fg="#ffffff", bg=self.C_DARK).pack(anchor="w")
        tk.Label(title_frame, text="重庆三人众科技有限公司",
                 font=(self.FONT_FAMILY, 9,), fg=self.C_TEXT_MUTED,
                 bg=self.C_DARK).pack(anchor="w")

        # 右侧：信息区
        header_right = tk.Frame(header, bg=self.C_DARK)
        header_right.pack(side=tk.RIGHT, fill=tk.Y, padx=20, pady=8)

        # 行1：版权 + 版本
        row1 = tk.Frame(header_right, bg=self.C_DARK)
        row1.pack(anchor="e")
        tk.Label(row1, text="v20260502", font=(self.FONT_FAMILY, 8,),
                 fg=self.C_TEXT_MUTED, bg=self.C_DARK).pack(side=tk.RIGHT, padx=(10, 0))
        tk.Label(row1, text="© 重庆三人众科技有限公司",
                 font=(self.FONT_FAMILY, 8,), fg=self.C_TEXT_MUTED,
                 bg=self.C_DARK).pack(side=tk.RIGHT)

        # 行2：GitHub + 官网
        row2 = tk.Frame(header_right, bg=self.C_DARK)
        row2.pack(anchor="e", pady=(2, 0))
        gh_lbl = tk.Label(row2, text="⭐ GitHub 求Star",
                         font=(self.FONT_FAMILY, 8, "underline"),
                         fg=self.C_PRIMARY, bg=self.C_DARK, cursor="hand2")
        gh_lbl.pack(side=tk.RIGHT, padx=(12, 0))
        gh_lbl.bind("<Button-1>", lambda e: webbrowser.open(
            "https://github.com/hotrichard1982/pillow_gui"))
        gh_lbl.bind("<Enter>", lambda e: gh_lbl.config(fg="#60a5fa"))
        gh_lbl.bind("<Leave>", lambda e: gh_lbl.config(fg=self.C_PRIMARY))
        web_lbl = tk.Label(row2, text="https://www.cq30.com/",
                          font=(self.FONT_FAMILY, 8, "underline"),
                          fg=self.C_PRIMARY, bg=self.C_DARK, cursor="hand2")
        web_lbl.pack(side=tk.RIGHT)
        web_lbl.bind("<Button-1>", lambda e: webbrowser.open("https://www.cq30.com/"))
        web_lbl.bind("<Enter>", lambda e: web_lbl.config(fg="#60a5fa"))
        web_lbl.bind("<Leave>", lambda e: web_lbl.config(fg=self.C_PRIMARY))

        # 行3：联系方式
        row3 = tk.Frame(header_right, bg=self.C_DARK)
        row3.pack(anchor="e", pady=(2, 0))
        tk.Label(row3, text="QQ: 7602069  |  7602069@qq.com",
                 font=(self.FONT_FAMILY, 8,), fg=self.C_TEXT_MUTED,
                 bg=self.C_DARK).pack(side=tk.RIGHT)

        # ---- 主体内容区 ----
        body = tk.Frame(root, bg=self.C_BG)
        body.pack(fill=tk.BOTH, expand=True, padx=16, pady=(12, 0))

        self.notebook = ttk.Notebook(body)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        self.single_frame = ttk.Frame(self.notebook)
        self.batch_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.single_frame, text="  单张处理  ")
        self.notebook.add(self.batch_frame, text="  批量处理  ")

        self._build_single_tab()
        self._build_batch_tab()

        # ---- 快捷键 ----
        self.root.bind("<Control-s>", lambda e: self._overwrite_original())
        self.root.bind("<Control-S>", lambda e: self._overwrite_original())
        self.root.bind("<Control-Shift-s>", lambda e: self._save_as())
        self.root.bind("<Control-Shift-S>", lambda e: self._save_as())

    def _apply_theme(self):
        style = ttk.Style()
        style.theme_use("clam")

        # 全局字体
        style.configure(".", font=(self.FONT_FAMILY, 10,))

        # Notebook - 现代标签页
        style.configure("TNotebook", background=self.C_BG, borderwidth=0)
        style.configure("TNotebook.Tab",
                       padding=[20, 8],
                       font=(self.FONT_FAMILY, 10,),
                       background=self.C_BG,
                       foreground=self.C_TEXT_MUTED)
        style.map("TNotebook.Tab",
                  background=[("selected", self.C_SURFACE), ("active", self.C_SURFACE_ALT)],
                  foreground=[("selected", self.C_PRIMARY), ("active", self.C_TEXT)],
                  expand=[("selected", [2, 2, 2, 0])])

        # Frame
        style.configure("TFrame", background=self.C_BG)

        # LabelFrame - 卡片风格
        style.configure("TLabelframe",
                       background=self.C_SURFACE,
                       borderwidth=1,
                       relief="solid",
                       padding=16)
        style.configure("TLabelframe.Label",
                       font=(self.FONT_FAMILY, 10, "bold"),
                       foreground=self.C_TEXT,
                       background=self.C_SURFACE)

        # 标准按钮 - 扁平主色
        style.configure("TButton",
                       padding=[12, 6],
                       font=(self.FONT_FAMILY, 9,),
                       borderwidth=0,
                       relief="flat",
                       anchor="center")
        style.map("TButton",
                  background=[("active", self.C_PRIMARY_HOVER),
                             ("pressed", self.C_PRIMARY_HOVER),
                             ("!disabled", self.C_PRIMARY),
                             ("disabled", self.C_BORDER)],
                  foreground=[("active", "#ffffff"),
                             ("pressed", "#ffffff"),
                             ("!disabled", "#ffffff"),
                             ("disabled", self.C_TEXT_MUTED)])

        # 主要按钮样式 (蓝)
        style.configure("Primary.TButton", padding=[12, 6])
        style.map("Primary.TButton",
                  background=[("active", self.C_PRIMARY_HOVER),
                             ("pressed", self.C_PRIMARY_HOVER),
                             ("!disabled", self.C_PRIMARY),
                             ("disabled", self.C_BORDER)],
                  foreground=[("active", "#ffffff"),
                             ("pressed", "#ffffff"),
                             ("!disabled", "#ffffff"),
                             ("disabled", self.C_TEXT_MUTED)])

        # 成功按钮样式 (绿)
        style.configure("Success.TButton", padding=[12, 6])
        style.map("Success.TButton",
                  background=[("active", self.C_SUCCESS_HOVER),
                             ("pressed", self.C_SUCCESS_HOVER),
                             ("!disabled", self.C_SUCCESS),
                             ("disabled", self.C_BORDER)],
                  foreground=[("active", "#ffffff"),
                             ("pressed", "#ffffff"),
                             ("!disabled", "#ffffff"),
                             ("disabled", self.C_TEXT_MUTED)])

        # 次要按钮样式 (灰底)
        style.configure("Secondary.TButton",
                       padding=[12, 6],
                       background=self.C_SURFACE,
                       foreground=self.C_TEXT)
        style.map("Secondary.TButton",
                  background=[("active", self.C_BG),
                             ("pressed", self.C_BG),
                             ("!disabled", self.C_SURFACE),
                             ("disabled", self.C_SURFACE)],
                  foreground=[("active", self.C_TEXT),
                             ("pressed", self.C_TEXT),
                             ("!disabled", self.C_TEXT),
                             ("disabled", self.C_TEXT_MUTED)])

        # 输入框
        style.configure("TEntry", padding=6)

        # 复选框
        style.configure("TCheckbutton",
                       background=self.C_SURFACE,
                       font=(self.FONT_FAMILY, 9,))
        style.map("TCheckbutton",
                  background=[("active", self.C_SURFACE)])

        # 单选框
        style.configure("TRadiobutton",
                       background=self.C_SURFACE,
                       font=(self.FONT_FAMILY, 9,))
        style.map("TRadiobutton",
                  background=[("active", self.C_SURFACE)])

        # 标签
        style.configure("TLabel",
                       background=self.C_SURFACE,
                       font=(self.FONT_FAMILY, 10,))

        # 进度条
        style.configure("Horizontal.TProgressbar",
                       background=self.C_PRIMARY,
                       troughcolor=self.C_BG,
                       borderwidth=0,
                       lightcolor=self.C_PRIMARY,
                       darkcolor=self.C_PRIMARY)

    # ======================== 单张处理 ========================
    def _build_single_tab(self):
        # 顶部工具栏
        top_frame = tk.Frame(self.single_frame, bg=self.C_BG)
        top_frame.pack(fill=tk.X, padx=12, pady=(12, 8))

        tk.Label(top_frame, text="选择图片", bg=self.C_BG, fg=self.C_TEXT,
                 font=(self.FONT_FAMILY, 10, "bold")).pack(side=tk.LEFT)
        self.single_input = tk.StringVar()
        ttk.Entry(top_frame, textvariable=self.single_input, width=55).pack(
            side=tk.LEFT, padx=10)
        ttk.Button(top_frame, text="浏览", command=self._select_single_input,
                   style="Secondary.TButton").pack(side=tk.LEFT, padx=2)
        ttk.Button(top_frame, text="加载", command=self._load_single_image,
                   style="Primary.TButton").pack(side=tk.LEFT, padx=2)

        # 主体区域：画布 + 侧边栏
        bottom_frame = tk.Frame(self.single_frame, bg=self.C_BG)
        bottom_frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=(8, 12))

        # 画布区域（无边框，嵌入式效果）
        canvas_bg = tk.Frame(bottom_frame, bg="#ebeff3")
        canvas_bg.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 12))
        self.canvas = CropCanvas(canvas_bg, bg="#f1f5f9")
        self.canvas.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
        self.canvas.set_callbacks(
            on_crop_changed=self._on_canvas_crop_changed,
            on_display_changed=self._on_canvas_display_changed,
        )

        # 右侧控制面板（带滚动条）
        sidebar_scroll = ttk.Scrollbar(bottom_frame, orient="vertical")
        sidebar_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        sidebar_canvas = tk.Canvas(bottom_frame, bg=self.C_BG, width=300,
                                   highlightthickness=0, bd=0)
        sidebar_canvas.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        sidebar_canvas.configure(yscrollcommand=sidebar_scroll.set)

        ctrl_panel = tk.Frame(sidebar_canvas, bg=self.C_BG)
        self._ctrl_inner_id = sidebar_canvas.create_window(
            (0, 0), window=ctrl_panel, anchor="nw")

        def _on_inner_configure(event):
            sidebar_canvas.configure(scrollregion=sidebar_canvas.bbox("all"))
        ctrl_panel.bind("<Configure>", _on_inner_configure)

        def _on_canvas_configure(event):
            sidebar_canvas.itemconfig(self._ctrl_inner_id, width=event.width)
        sidebar_canvas.bind("<Configure>", _on_canvas_configure)

        def _on_mousewheel(event):
            sidebar_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        def _bind_wheel(event):
            sidebar_canvas.bind_all("<MouseWheel>", _on_mousewheel)
        def _unbind_wheel(event):
            sidebar_canvas.unbind_all("<MouseWheel>")
        sidebar_canvas.bind("<Enter>", _bind_wheel)
        sidebar_canvas.bind("<Leave>", _unbind_wheel)

        self._build_single_resize_panel(ctrl_panel)
        self._build_single_crop_panel(ctrl_panel)
        self._build_single_action_panel(ctrl_panel)

        if HAS_DND:
            self.canvas.drop_target_register(DND_FILES)
            self.canvas.dnd_bind('<<Drop>>', self._on_file_drop)

    def _build_single_resize_panel(self, parent):
        self.resize_width = tk.IntVar(value=800)
        self.resize_height = tk.IntVar(value=600)
        self.keep_aspect = tk.BooleanVar(value=True)
        self.single_quality = tk.IntVar(value=85)
        self._internal_update = False

        # 区块（无卡片边框，靠色块和间距区分）
        section = tk.Frame(parent, bg=self.C_BG)
        section.pack(fill=tk.X, pady=(0, 12))

        tk.Label(section, text="尺寸缩放", font=(self.FONT_FAMILY, 10, "bold"),
                fg=self.C_TEXT, bg=self.C_BG).pack(anchor="w", pady=(0, 6))
        tk.Frame(section, bg=self.C_BORDER, height=1).pack(fill=tk.X, pady=(0, 10))

        # 白色内容区（无边框）
        content = tk.Frame(section, bg=self.C_SURFACE)
        content.pack(fill=tk.X)

        # 宽度
        r0 = tk.Frame(content, bg=self.C_SURFACE)
        r0.pack(fill=tk.X, padx=12, pady=(10, 4))
        tk.Label(r0, text="宽度", font=(self.FONT_FAMILY, 9,),
                fg=self.C_TEXT, bg=self.C_SURFACE, width=4, anchor="e").pack(side=tk.LEFT, padx=(0, 8))
        ttk.Entry(r0, textvariable=self.resize_width, width=12).pack(side=tk.LEFT, padx=(0, 4))
        tk.Label(r0, text="px", font=(self.FONT_FAMILY, 9,),
                fg=self.C_TEXT_MUTED, bg=self.C_SURFACE).pack(side=tk.LEFT)

        # 高度
        r1 = tk.Frame(content, bg=self.C_SURFACE)
        r1.pack(fill=tk.X, padx=12, pady=4)
        tk.Label(r1, text="高度", font=(self.FONT_FAMILY, 9,),
                fg=self.C_TEXT, bg=self.C_SURFACE, width=4, anchor="e").pack(side=tk.LEFT, padx=(0, 8))
        ttk.Entry(r1, textvariable=self.resize_height, width=12).pack(side=tk.LEFT, padx=(0, 4))
        tk.Label(r1, text="px", font=(self.FONT_FAMILY, 9,),
                fg=self.C_TEXT_MUTED, bg=self.C_SURFACE).pack(side=tk.LEFT)

        # 比例
        ttk.Checkbutton(content, text="保持原图比例", variable=self.keep_aspect,
                        command=self._on_keep_aspect_toggle).pack(
            anchor="w", padx=12, pady=(6, 4))

        # 质量
        r3 = tk.Frame(content, bg=self.C_SURFACE)
        r3.pack(fill=tk.X, padx=12, pady=4)
        tk.Label(r3, text="质量", font=(self.FONT_FAMILY, 9,),
                fg=self.C_TEXT, bg=self.C_SURFACE, width=4, anchor="e").pack(side=tk.LEFT, padx=(0, 8))
        ttk.Entry(r3, textvariable=self.single_quality, width=7).pack(side=tk.LEFT, padx=(0, 4))
        tk.Label(r3, text="(1-100)", font=(self.FONT_FAMILY, 9,),
                fg=self.C_TEXT_MUTED, bg=self.C_SURFACE).pack(side=tk.LEFT)

        # PNG 警告
        self.lbl_png_warn = tk.Frame(content, bg=self.C_WARNING_BG)
        self.lbl_png_warn.pack(fill=tk.X, padx=12, pady=(6, 0))
        self.lbl_png_warn.pack_forget()
        warn_icon = tk.Label(self.lbl_png_warn, text="⚠", font=(self.FONT_FAMILY, 10,),
                            fg=self.C_WARNING_TEXT, bg=self.C_WARNING_BG)
        warn_icon.pack(side=tk.LEFT, padx=(10, 4), pady=6)
        warn_text = tk.Label(self.lbl_png_warn,
                            text="PNG 为无损格式，压缩无效，保存时默认转 JPG",
                            font=(self.FONT_FAMILY, 8,), fg=self.C_WARNING_TEXT,
                            bg=self.C_WARNING_BG, wraplength=250, justify="left")
        warn_text.pack(side=tk.LEFT, padx=(0, 10), pady=6)

        # 按钮
        btn_area = tk.Frame(content, bg=self.C_SURFACE)
        btn_area.pack(fill=tk.X, padx=12, pady=(4, 12))
        self.btn_resize = ttk.Button(btn_area, text="应用缩放", command=self._apply_resize,
                                     state=tk.DISABLED, style="Primary.TButton")
        self.btn_resize.pack(fill=tk.X)

        self.resize_width.trace_add("write", self._on_resize_width_change)
        self.resize_height.trace_add("write", self._on_resize_height_change)
        self.single_quality.trace_add("write", self._on_quality_change)

    def _build_single_crop_panel(self, parent):
        self.crop_x = tk.IntVar(value=0)
        self.crop_y = tk.IntVar(value=0)
        self.crop_w = tk.IntVar(value=100)
        self.crop_h = tk.IntVar(value=100)

        # 区块（无卡片边框）
        section = tk.Frame(parent, bg=self.C_BG)
        section.pack(fill=tk.X, pady=(0, 12))

        tk.Label(section, text="自由裁剪", font=(self.FONT_FAMILY, 10, "bold"),
                fg=self.C_TEXT, bg=self.C_BG).pack(anchor="w", pady=(0, 6))
        tk.Frame(section, bg=self.C_BORDER, height=1).pack(fill=tk.X, pady=(0, 10))

        # 白色内容区（无边框）
        content = tk.Frame(section, bg=self.C_SURFACE)
        content.pack(fill=tk.X)

        # 第一行：X / Y
        r0 = tk.Frame(content, bg=self.C_SURFACE)
        r0.pack(fill=tk.X, padx=12, pady=(10, 4))
        tk.Label(r0, text="X", font=(self.FONT_FAMILY, 9,),
                fg=self.C_TEXT, bg=self.C_SURFACE, width=3, anchor="e").pack(side=tk.LEFT, padx=(0, 4))
        ttk.Entry(r0, textvariable=self.crop_x, width=8).pack(side=tk.LEFT, padx=2)
        tk.Label(r0, text="Y", font=(self.FONT_FAMILY, 9,),
                fg=self.C_TEXT, bg=self.C_SURFACE, width=3, anchor="e").pack(side=tk.LEFT, padx=(12, 4))
        ttk.Entry(r0, textvariable=self.crop_y, width=8).pack(side=tk.LEFT, padx=2)

        # 第二行：宽 / 高
        r1 = tk.Frame(content, bg=self.C_SURFACE)
        r1.pack(fill=tk.X, padx=12, pady=4)
        tk.Label(r1, text="宽", font=(self.FONT_FAMILY, 9,),
                fg=self.C_TEXT, bg=self.C_SURFACE, width=3, anchor="e").pack(side=tk.LEFT, padx=(0, 4))
        ttk.Entry(r1, textvariable=self.crop_w, width=8).pack(side=tk.LEFT, padx=2)
        tk.Label(r1, text="高", font=(self.FONT_FAMILY, 9,),
                fg=self.C_TEXT, bg=self.C_SURFACE, width=3, anchor="e").pack(side=tk.LEFT, padx=(12, 4))
        ttk.Entry(r1, textvariable=self.crop_h, width=8).pack(side=tk.LEFT, padx=2)

        # 操作按钮
        r2 = tk.Frame(content, bg=self.C_SURFACE)
        r2.pack(fill=tk.X, padx=12, pady=(8, 4))
        ttk.Button(r2, text="应用数值", command=self._apply_crop_numeric,
                   style="Secondary.TButton").pack(side=tk.LEFT, padx=(0, 4))
        ttk.Button(r2, text="清除", command=self._clear_crop,
                   style="Secondary.TButton").pack(side=tk.LEFT)

        # 应用裁剪按钮
        btn_area = tk.Frame(content, bg=self.C_SURFACE)
        btn_area.pack(fill=tk.X, padx=12, pady=(0, 12))
        self.btn_crop = ttk.Button(btn_area, text="应用裁剪", command=self._apply_crop,
                                   state=tk.DISABLED, style="Primary.TButton")
        self.btn_crop.pack(fill=tk.X)

    def _build_single_action_panel(self, parent):
        # 操作按钮区（无卡片，直接放置）
        frame = tk.Frame(parent, bg=self.C_BG)
        frame.pack(fill=tk.X, pady=(10, 10))

        btn_frame = tk.Frame(frame, bg=self.C_BG)
        btn_frame.pack(fill=tk.X)

        self.btn_reset = ttk.Button(btn_frame, text="重置", command=self._reset_preview,
                                    state=tk.DISABLED, style="Secondary.TButton")
        self.btn_reset.pack(side=tk.RIGHT, padx=(6, 0))
        self.btn_overwrite = ttk.Button(btn_frame, text="覆盖原图", command=self._overwrite_original,
                                        state=tk.DISABLED, style="Primary.TButton")
        self.btn_overwrite.pack(side=tk.RIGHT, padx=(6, 0))
        self.btn_save_as = ttk.Button(btn_frame, text="另存为", command=self._save_as,
                                      state=tk.DISABLED, style="Secondary.TButton")
        self.btn_save_as.pack(side=tk.RIGHT)

        shortcuts = tk.Label(frame, text="Ctrl+S 覆盖原图  |  Ctrl+Shift+S 另存为",
                             font=(self.FONT_FAMILY, 8,), fg=self.C_TEXT_MUTED, bg=self.C_BG)
        shortcuts.pack(anchor="e", pady=(6, 0))

        self.single_hint = tk.StringVar(
            value="提示：拖拽鼠标选择裁剪区域，拖动方框手柄可调整")
        tk.Label(frame, textvariable=self.single_hint,
                 font=(self.FONT_FAMILY, 9,), fg=self.C_TEXT_MUTED,
                 bg=self.C_BG, wraplength=280, justify="left").pack(anchor="w", pady=(6, 0))

    # ---------- 回调（保持不变）----------
    def _on_canvas_crop_changed(self, rect):
        if rect is None:
            self.crop_x.set(0); self.crop_y.set(0)
            self.crop_w.set(100); self.crop_h.set(100)
            self.btn_crop.config(state=tk.DISABLED)
        else:
            x, y, w, h = rect
            self.crop_x.set(x); self.crop_y.set(y)
            self.crop_w.set(w); self.crop_h.set(h)
            self.btn_crop.config(state=tk.NORMAL)

    def _on_canvas_display_changed(self, w, h):
        self._internal_update = True
        try:
            self.resize_width.set(w); self.resize_height.set(h)
        finally:
            self._internal_update = False
        ow, oh = self.canvas.original_image.size
        fmt = self.canvas.original_image.format
        hint = f"原图：{ow}×{oh}  |  当前：{w}×{h}"
        if fmt == "PNG":
            hint += "  |  PNG 无法压缩"
            self.lbl_png_warn.pack()
        else:
            self.lbl_png_warn.pack_forget()
        self.single_hint.set(hint)

    def _on_resize_width_change(self, *args):
        if self._internal_update:
            return
        if self.keep_aspect.get() and self.canvas.display_image:
            try: w = self.resize_width.get()
            except Exception:
                import traceback; traceback.print_exc(); return
            if w <= 0: return
            dw, dh = self.canvas.display_image.size
            self._internal_update = True
            try: self.resize_height.set(int(w * dh / dw))
            finally: self._internal_update = False

    def _on_resize_height_change(self, *args):
        if self._internal_update:
            return
        if self.keep_aspect.get() and self.canvas.display_image:
            try: h = self.resize_height.get()
            except Exception:
                import traceback; traceback.print_exc(); return
            if h <= 0: return
            dw, dh = self.canvas.display_image.size
            self._internal_update = True
            try: self.resize_width.set(int(h * dw / dh))
            finally: self._internal_update = False

    def _on_keep_aspect_toggle(self):
        if self.keep_aspect.get() and self.canvas.display_image:
            dw, dh = self.canvas.display_image.size
            self._internal_update = True
            try: self.resize_height.set(int(self.resize_width.get() * dh / dw))
            finally: self._internal_update = False

    def _on_quality_change(self, *args):
        try: v = self.single_quality.get()
        except Exception: return
        if v < 1: self.single_quality.set(1)
        elif v > 100: self.single_quality.set(100)

    def _on_batch_quality_change(self, *args):
        try: v = self.quality.get()
        except Exception: return
        if v < 1: self.quality.set(1)
        elif v > 100: self.quality.set(100)

    # ---------- 操作 ----------
    def _apply_resize(self):
        if self.canvas.display_image is None: return
        try: tw = self.resize_width.get(); th = self.resize_height.get()
        except Exception:
            messagebox.showwarning("提示", "请输入有效的尺寸数值"); return
        if tw <= 0 or th <= 0:
            messagebox.showwarning("提示", "宽度和高度必须大于 0"); return
        self.canvas.apply_resize(tw, th)

    def _apply_crop(self):
        if not self.canvas.has_crop():
            messagebox.showwarning("提示", "请先在图片上选择裁剪区域"); return
        self.canvas.apply_crop(); self.btn_crop.config(state=tk.DISABLED)

    def _apply_crop_numeric(self):
        try: x = self.crop_x.get(); y = self.crop_y.get()
        except Exception:
            messagebox.showwarning("提示", "请输入有效的裁剪数值"); return
        try: w = self.crop_w.get(); h = self.crop_h.get()
        except Exception:
            messagebox.showwarning("提示", "请输入有效的裁剪数值"); return
        self.canvas.set_crop_rect_numeric(x, y, w, h)
        if self.canvas.has_crop(): self.btn_crop.config(state=tk.NORMAL)

    def _clear_crop(self): self.canvas.clear_crop()

    def _save_as(self):
        if self.canvas.display_image is None: return
        orig_fmt = (self.canvas.original_image.format
                    if self.canvas.original_image else None)
        ext_map = {"JPEG": ".jpg", "PNG": ".png", "WEBP": ".webp", "BMP": ".bmp"}
        if orig_fmt in ("PNG", "BMP"): def_ext = ".jpg"
        else: def_ext = ext_map.get(orig_fmt, ".jpg")
        out_path = filedialog.asksaveasfilename(
            title="另存为", defaultextension=def_ext,
            filetypes=[("JPEG", "*.jpg"), ("PNG", "*.png"),
                       ("WebP", "*.webp"), ("BMP", "*.bmp")])
        if not out_path: return
        try:
            img = self.canvas.get_display_image()
            self._save_image(img, out_path)
            size_kb = os.path.getsize(out_path) / 1024
            messagebox.showinfo("完成", f"另存成功！\n{out_path}\n大小：{size_kb:.0f} KB")
        except Exception as e:
            messagebox.showerror("错误", f"保存失败：{e}")

    def _overwrite_original(self):
        if self.canvas.original_image is None: return
        src = self.canvas.original_image
        if not (hasattr(src, 'filename') and src.filename and os.path.isfile(src.filename)):
            messagebox.showwarning("提示", "原图路径无效，无法覆盖。请使用「另存为」"); return
        orig_fmt = src.format
        if orig_fmt in ("PNG", "BMP"):
            new_path = os.path.splitext(src.filename)[0] + ".jpg"
            ok = messagebox.askyesno("确认转换",
                                     f"PNG 为无损格式，压缩无效。\n将另存为 JPG：\n{new_path}\n\n原文件保留不变。是否继续？")
            if not ok: return
            out_path = new_path
        else:
            out_path = src.filename
            ok = messagebox.askyesno("确认覆盖", f"将覆盖原图：\n{src.filename}\n\n确定继续？")
            if not ok: return
        try:
            old_info = ""
            if os.path.exists(out_path):
                old_info = f"，原大小：{os.path.getsize(out_path)/1024:.0f} KB"
            img = self.canvas.get_display_image()
            self._save_image(img, out_path)
            new_size = os.path.getsize(out_path) / 1024
            messagebox.showinfo("完成",
                f"保存成功！\n{out_path}\n大小：{new_size:.0f} KB{old_info}")
        except Exception as e:
            messagebox.showerror("错误", f"保存失败：{e}")

    def _reset_preview(self):
        self.canvas.reset_to_original(); self.btn_crop.config(state=tk.DISABLED)

    def _save_image(self, img, out_path):
        ext = os.path.splitext(out_path)[1].lower()
        fmt = {".jpg": "JPEG", ".jpeg": "JPEG", ".png": "PNG",
               ".webp": "WEBP", ".bmp": "BMP"}.get(ext, "JPEG")
        if fmt in ("JPEG", "WEBP"):
            if img.mode not in ("RGB", "L"): img = img.convert("RGB")
        elif fmt == "PNG" and img.mode not in ("RGB", "RGBA", "L", "P"):
            img = img.convert("RGBA")
        save_kwargs = {}
        q = max(1, min(100, self.single_quality.get()))
        if fmt == "JPEG":
            save_kwargs["quality"] = q; save_kwargs["optimize"] = True
        elif fmt == "WEBP":
            save_kwargs["quality"] = q
        elif fmt == "PNG":
            save_kwargs["compress_level"] = max(4, min(9, 9 - (q - 1) * 5 // 99))
        img.save(out_path, fmt, **save_kwargs)

    def _select_single_input(self):
        path = filedialog.askopenfilename(
            title="选择图片",
            filetypes=[("图片文件", "*.jpg *.jpeg *.png *.webp *.bmp"), ("所有文件", "*.*")])
        if path:
            self.single_input.set(path); self._load_single_image()

    def _load_single_image(self):
        path = self.single_input.get()
        if not path or not os.path.isfile(path):
            messagebox.showwarning("提示", "请先选择有效的图片文件"); return
        if self.canvas.load_image(path):
            self.btn_resize.config(state=tk.NORMAL)
            self.btn_save_as.config(state=tk.NORMAL)
            self.btn_overwrite.config(state=tk.NORMAL)
            self.btn_reset.config(state=tk.NORMAL)
            self.btn_crop.config(state=tk.DISABLED)
        else:
            messagebox.showerror("错误", "无法打开图片文件")

    # ======================== 批量处理 ========================
    def _build_batch_tab(self):
        self.input_dir = tk.StringVar()
        self.output_dir = tk.StringVar()
        self.target_width = tk.IntVar(value=1000)
        self.quality = tk.IntVar(value=60)

        wrapper = tk.Frame(self.batch_frame, bg=self.C_BG)
        wrapper.pack(fill=tk.BOTH, expand=True, padx=16, pady=16)

        # 文件夹设置
        sec1 = tk.Frame(wrapper, bg=self.C_BG)
        sec1.pack(fill=tk.X, pady=(0, 12))
        tk.Label(sec1, text="文件夹设置", font=(self.FONT_FAMILY, 10, "bold"),
                fg=self.C_TEXT, bg=self.C_BG).pack(anchor="w", pady=(0, 6))
        tk.Frame(sec1, bg=self.C_BORDER, height=1).pack(fill=tk.X, pady=(0, 10))

        content1 = tk.Frame(sec1, bg=self.C_SURFACE)
        content1.pack(fill=tk.X)
        r0 = tk.Frame(content1, bg=self.C_SURFACE)
        r0.pack(fill=tk.X, padx=12, pady=(10, 4))
        tk.Label(r0, text="图片文件夹", font=(self.FONT_FAMILY, 9,),
                fg=self.C_TEXT, bg=self.C_SURFACE, width=8, anchor="e").pack(side=tk.LEFT, padx=(0, 8))
        ttk.Entry(r0, textvariable=self.input_dir, width=55).pack(side=tk.LEFT, padx=4)
        ttk.Button(r0, text="选择", command=self._select_input_dir,
                   style="Secondary.TButton").pack(side=tk.LEFT, padx=2)

        r1 = tk.Frame(content1, bg=self.C_SURFACE)
        r1.pack(fill=tk.X, padx=12, pady=(4, 10))
        tk.Label(r1, text="输出文件夹", font=(self.FONT_FAMILY, 9,),
                fg=self.C_TEXT, bg=self.C_SURFACE, width=8, anchor="e").pack(side=tk.LEFT, padx=(0, 8))
        ttk.Entry(r1, textvariable=self.output_dir, width=55).pack(side=tk.LEFT, padx=4)
        ttk.Button(r1, text="选择", command=self._select_output_dir,
                   style="Secondary.TButton").pack(side=tk.LEFT, padx=2)

        # 处理参数
        sec2 = tk.Frame(wrapper, bg=self.C_BG)
        sec2.pack(fill=tk.X, pady=(0, 12))
        tk.Label(sec2, text="处理参数", font=(self.FONT_FAMILY, 10, "bold"),
                fg=self.C_TEXT, bg=self.C_BG).pack(anchor="w", pady=(0, 6))
        tk.Frame(sec2, bg=self.C_BORDER, height=1).pack(fill=tk.X, pady=(0, 10))

        content2 = tk.Frame(sec2, bg=self.C_SURFACE)
        content2.pack(fill=tk.X)
        r2 = tk.Frame(content2, bg=self.C_SURFACE)
        r2.pack(fill=tk.X, padx=12, pady=10)
        tk.Label(r2, text="目标宽度", font=(self.FONT_FAMILY, 9,),
                fg=self.C_TEXT, bg=self.C_SURFACE, width=8, anchor="e").pack(side=tk.LEFT, padx=(0, 8))
        ttk.Entry(r2, textvariable=self.target_width, width=12).pack(side=tk.LEFT, padx=4)
        ttk.Label(r2, text="px").pack(side=tk.LEFT, padx=(2, 20))
        tk.Label(r2, text="压缩质量", font=(self.FONT_FAMILY, 9,),
                fg=self.C_TEXT, bg=self.C_SURFACE, width=8, anchor="e").pack(side=tk.LEFT, padx=(0, 8))
        ttk.Entry(r2, textvariable=self.quality, width=12).pack(side=tk.LEFT, padx=4)
        ttk.Label(r2, text="(1-100)").pack(side=tk.LEFT, padx=(2, 0))

        # 操作区
        action_frame = tk.Frame(wrapper, bg=self.C_BG)
        action_frame.pack(fill=tk.X, pady=(8, 0))

        self.batch_btn = ttk.Button(action_frame, text="开始处理", command=self._batch_start,
                                    style="Success.TButton")
        self.batch_btn.pack(pady=(10, 6))

        self.batch_status = tk.StringVar(value="准备就绪")
        tk.Label(action_frame, textvariable=self.batch_status, font=(self.FONT_FAMILY, 10,),
                 fg=self.C_SUCCESS, bg=self.C_BG).pack()

        self.quality.trace_add("write", self._on_batch_quality_change)

    def _select_input_dir(self):
        folder = filedialog.askdirectory(title="选择图片文件夹")
        if folder: self.input_dir.set(folder)

    def _select_output_dir(self):
        folder = filedialog.askdirectory(title="选择输出文件夹")
        if folder: self.output_dir.set(folder)

    def _batch_start(self):
        if not self.input_dir.get() or not self.output_dir.get():
            messagebox.showwarning("提示", "请先选择输入和输出文件夹"); return
        output_folder = self.output_dir.get()
        if os.path.isdir(output_folder):
            existing = [f for f in os.listdir(output_folder)
                        if f.lower().endswith(self.IMG_EXTS)]
            if existing:
                ok = messagebox.askyesno("确认",
                    f"输出文件夹中已有 {len(existing)} 张图片，同名文件将被覆盖。\n是否继续？")
                if not ok: return
        threading.Thread(target=self._batch_worker, daemon=True).start()

    def _batch_worker(self):
        self.root.after(0, lambda: self.batch_btn.config(state=tk.DISABLED))
        self.root.after(0, lambda: self.batch_status.set("正在处理..."))
        input_folder = self.input_dir.get()
        output_folder = self.output_dir.get()
        os.makedirs(output_folder, exist_ok=True)
        files = [f for f in os.listdir(input_folder) if f.lower().endswith(self.IMG_EXTS)]
        total = len(files); errors = []
        for i, f in enumerate(files, 1):
            in_path = os.path.join(input_folder, f)
            out_path = os.path.join(output_folder, f)
            try:
                img = Image.open(in_path).convert("RGB")
                w, h = img.size
                tw = self.target_width.get(); th = int(h * (tw / w))
                img = img.resize((tw, th), Image.Resampling.LANCZOS)
                img.save(out_path, "JPEG", quality=self.quality.get(), optimize=True)
            except Exception as e:
                errors.append(f); print(f"处理失败 {f}: {e}")
            self.root.after(0, lambda i=i, t=total:
                           self.batch_status.set(f"处理中... {i}/{t}"))
        self.root.after(0, lambda t=total, e=errors:
                       self.batch_status.set(f"完成！共 {t} 张"
                                             + (f"，{len(e)} 张失败" if e else "")))
        self.root.after(0, lambda: self.batch_btn.config(state=tk.NORMAL))
        msg = f"已处理 {total} 张图片！"
        if errors: msg += f"\n失败 {len(errors)} 张：{', '.join(errors[:5])}"
        self.root.after(0, lambda m=msg: messagebox.showinfo("完成", m))


if __name__ == "__main__":
    if HAS_DND:
        root = TkinterDnD.Tk()
    else:
        root = tk.Tk()
    ImageToolCN(root)
    root.mainloop()
