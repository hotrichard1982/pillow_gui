import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk
import os
import threading

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

    # 配色
    C_PRIMARY = "#3498db"
    C_DARK = "#2c3e50"
    C_BG = "#f5f6fa"
    C_SURFACE = "#ffffff"
    C_ACCENT = "#e74c3c"
    C_TEXT = "#2c3e50"
    C_MUTED = "#7f8c8d"
    C_SUCCESS = "#27ae60"

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
        self.root.geometry("1060x780")
        self.root.minsize(800, 550)
        self.root.resizable(True, True)
        self.root.configure(bg=self.C_BG)

        self._apply_theme()

        # ---- 顶部 ----
        header = tk.Frame(root, bg=self.C_DARK, height=70)
        header.pack(fill=tk.X)
        header.pack_propagate(False)

        logo_path = os.path.join(os.path.dirname(__file__), "logo.png")
        if os.path.isfile(logo_path):
            self.logo_img = ImageTk.PhotoImage(
                Image.open(logo_path).resize((44, 44), Image.Resampling.LANCZOS))
            tk.Label(header, image=self.logo_img, bg=self.C_DARK).pack(
                side=tk.LEFT, padx=(15, 10), pady=13)

        title_frame = tk.Frame(header, bg=self.C_DARK)
        title_frame.pack(side=tk.LEFT, pady=10)
        tk.Label(title_frame, text="图轻剪 PicCraft", font=("Microsoft YaHei", 16, "bold"),
                 fg=self.C_PRIMARY, bg=self.C_DARK).pack(anchor="w")
        tk.Label(title_frame, text="重庆三人众科技有限公司",
                 font=("Microsoft YaHei", 9), fg=self.C_MUTED,
                 bg=self.C_DARK).pack(anchor="w")

        # ---- 主体 ----
        body = tk.Frame(root, bg=self.C_BG)
        body.pack(fill=tk.BOTH, expand=True, padx=8, pady=(8, 0))

        self.notebook = ttk.Notebook(body)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        self.single_frame = ttk.Frame(self.notebook)
        self.batch_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.single_frame, text="  单张处理  ")
        self.notebook.add(self.batch_frame, text="  批量处理  ")

        self._build_single_tab()
        self._build_batch_tab()

        # ---- 底部 ----
        footer = tk.Frame(root, bg=self.C_DARK, height=28)
        footer.pack(fill=tk.X, side=tk.BOTTOM)
        footer.pack_propagate(False)
        tk.Label(footer, text="QQ: 7602069  |  7602069@qq.com",
                 font=("Microsoft YaHei", 8), fg=self.C_MUTED,
                 bg=self.C_DARK).pack(side=tk.RIGHT, padx=15, pady=4)
        tk.Label(footer, text="© 重庆三人众科技有限公司",
                 font=("Microsoft YaHei", 8), fg=self.C_MUTED,
                 bg=self.C_DARK).pack(side=tk.LEFT, padx=15, pady=4)

        # ---- 快捷键 ----
        self.root.bind("<Control-s>", lambda e: self._overwrite_original())
        self.root.bind("<Control-S>", lambda e: self._overwrite_original())
        self.root.bind("<Control-Shift-s>", lambda e: self._save_as())
        self.root.bind("<Control-Shift-S>", lambda e: self._save_as())

    def _apply_theme(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure(".", font=("Microsoft YaHei", 9))
        style.configure("TNotebook", background=self.C_BG, borderwidth=0)
        style.configure("TNotebook.Tab", padding=[18, 6], font=("Microsoft YaHei", 10))
        style.map("TNotebook.Tab",
                  background=[("selected", self.C_PRIMARY)],
                  foreground=[("selected", "white")])
        style.configure("TFrame", background=self.C_BG)
        style.configure("TLabelframe", background=self.C_SURFACE, borderwidth=1,
                        relief="solid", padding=12)
        style.configure("TLabelframe.Label", font=("Microsoft YaHei", 10, "bold"),
                        foreground=self.C_DARK)
        style.configure("TButton", padding=[10, 4], font=("Microsoft YaHei", 9))
        style.map("TButton",
                  background=[("active", self.C_PRIMARY), ("!disabled", self.C_PRIMARY)],
                  foreground=[("active", "white"), ("!disabled", "white")])
        style.configure("Accent.TButton", background=self.C_SUCCESS)
        style.map("Accent.TButton",
                  background=[("active", "#219a52"), ("!disabled", self.C_SUCCESS)],
                  foreground=[("active", "white"), ("!disabled", "white")])
        style.configure("TEntry", padding=4)
        style.configure("TCheckbutton", background=self.C_SURFACE)
        style.configure("TRadiobutton", background=self.C_SURFACE)

    # ======================== 单张处理 ========================
    def _build_single_tab(self):
        top_frame = tk.Frame(self.single_frame, bg=self.C_BG)
        top_frame.pack(fill=tk.X, padx=8, pady=(8, 4))

        tk.Label(top_frame, text="选择图片：", bg=self.C_BG, fg=self.C_TEXT,
                 font=("Microsoft YaHei", 9)).pack(side=tk.LEFT)
        self.single_input = tk.StringVar()
        ttk.Entry(top_frame, textvariable=self.single_input, width=52).pack(
            side=tk.LEFT, padx=6)
        ttk.Button(top_frame, text="浏 览", command=self._select_single_input).pack(
            side=tk.LEFT, padx=2)
        ttk.Button(top_frame, text="加 载", command=self._load_single_image).pack(
            side=tk.LEFT, padx=2)

        bottom_frame = ttk.Frame(self.single_frame)
        bottom_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=(4, 8))

        self.canvas = CropCanvas(bottom_frame)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.canvas.set_callbacks(
            on_crop_changed=self._on_canvas_crop_changed,
            on_display_changed=self._on_canvas_display_changed,
        )

        ctrl_panel = tk.Frame(bottom_frame, bg=self.C_BG, width=290)
        ctrl_panel.pack(side=tk.RIGHT, fill=tk.Y)
        ctrl_panel.pack_propagate(False)

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

        frame = ttk.LabelFrame(parent, text=" 尺寸缩放 ", padding=12)
        frame.pack(fill=tk.X, pady=(0, 8))

        ttk.Label(frame, text="宽度").grid(row=0, column=0, sticky="e", pady=3, padx=(0, 6))
        ttk.Entry(frame, textvariable=self.resize_width, width=9).grid(row=0, column=1)
        ttk.Label(frame, text="px").grid(row=0, column=2, padx=(4, 0))

        ttk.Label(frame, text="高度").grid(row=1, column=0, sticky="e", pady=3, padx=(0, 6))
        ttk.Entry(frame, textvariable=self.resize_height, width=9).grid(row=1, column=1)
        ttk.Label(frame, text="px").grid(row=1, column=2, padx=(4, 0))

        ttk.Checkbutton(frame, text="保持原图比例", variable=self.keep_aspect,
                        command=self._on_keep_aspect_toggle).grid(
            row=2, column=0, columnspan=3, pady=6, sticky="w", padx=(0, 0))

        ttk.Label(frame, text="质量").grid(row=3, column=0, sticky="e", pady=3, padx=(0, 6))
        q_frame = ttk.Frame(frame)
        q_frame.grid(row=3, column=1, columnspan=2, sticky="w")
        ttk.Entry(q_frame, textvariable=self.single_quality, width=6).pack(side=tk.LEFT)
        ttk.Label(q_frame, text=" (1-100)").pack(side=tk.LEFT)

        self.lbl_png_warn = tk.Label(frame, text="⚠ PNG 为无损格式，压缩无效，保存时默认转 JPG",
                                     fg=self.C_ACCENT, font=("Microsoft YaHei", 7), bg=self.C_SURFACE)
        self.lbl_png_warn.grid(row=4, column=0, columnspan=3, pady=(4, 0))
        self.lbl_png_warn.grid_remove()

        self.btn_resize = ttk.Button(frame, text="应用缩放", command=self._apply_resize,
                                     state=tk.DISABLED)
        self.btn_resize.grid(row=5, column=0, columnspan=3, pady=(12, 0))

        self.resize_width.trace_add("write", self._on_resize_width_change)
        self.resize_height.trace_add("write", self._on_resize_height_change)
        self.single_quality.trace_add("write", self._on_quality_change)

    def _build_single_crop_panel(self, parent):
        self.crop_x = tk.IntVar(value=0)
        self.crop_y = tk.IntVar(value=0)
        self.crop_w = tk.IntVar(value=100)
        self.crop_h = tk.IntVar(value=100)

        frame = ttk.LabelFrame(parent, text=" 自由裁剪 ", padding=12)
        frame.pack(fill=tk.X, pady=(0, 8))

        ttk.Label(frame, text="X").grid(row=0, column=0, sticky="e", pady=3, padx=(0, 4))
        ttk.Entry(frame, textvariable=self.crop_x, width=7).grid(row=0, column=1, padx=2)
        ttk.Label(frame, text="Y").grid(row=0, column=2, sticky="e", pady=3, padx=(10, 4))
        ttk.Entry(frame, textvariable=self.crop_y, width=7).grid(row=0, column=3, padx=2)

        ttk.Label(frame, text="宽").grid(row=1, column=0, sticky="e", pady=3, padx=(0, 4))
        ttk.Entry(frame, textvariable=self.crop_w, width=7).grid(row=1, column=1, padx=2)
        ttk.Label(frame, text="高").grid(row=1, column=2, sticky="e", pady=3, padx=(10, 4))
        ttk.Entry(frame, textvariable=self.crop_h, width=7).grid(row=1, column=3, padx=2)

        btn_row = ttk.Frame(frame)
        btn_row.grid(row=2, column=0, columnspan=4, pady=(10, 0))
        ttk.Button(btn_row, text="应用数值", command=self._apply_crop_numeric).pack(
            side=tk.LEFT, padx=2)
        ttk.Button(btn_row, text="清除", command=self._clear_crop).pack(side=tk.LEFT, padx=2)

        self.btn_crop = ttk.Button(frame, text="应用裁剪", command=self._apply_crop,
                                   state=tk.DISABLED)
        self.btn_crop.grid(row=3, column=0, columnspan=4, pady=(8, 0))

    def _build_single_action_panel(self, parent):
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.X, pady=(6, 0))

        tk.Label(frame, text="保存", bg=self.C_BG, fg=self.C_TEXT,
                 font=("Microsoft YaHei", 9, "bold")).pack(anchor="w", pady=(0, 3))

        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill=tk.X)

        self.btn_save_as = ttk.Button(btn_frame, text="另存为", command=self._save_as,
                                      state=tk.DISABLED)
        self.btn_save_as.pack(side=tk.LEFT, padx=(0, 4))
        self.btn_overwrite = ttk.Button(btn_frame, text="覆盖原图", command=self._overwrite_original,
                                        state=tk.DISABLED)
        self.btn_overwrite.pack(side=tk.LEFT, padx=(0, 4))
        self.btn_reset = ttk.Button(btn_frame, text="重置", command=self._reset_preview,
                                    state=tk.DISABLED)
        self.btn_reset.pack(side=tk.LEFT)

        shortcuts = tk.Label(frame, text="Ctrl+S 覆盖原图  |  Ctrl+Shift+S 另存为",
                             font=("Microsoft YaHei", 7), fg=self.C_MUTED, bg=self.C_BG)
        shortcuts.pack(anchor="w", pady=(3, 0))

        self.single_hint = tk.StringVar(
            value="提示：拖拽鼠标选择裁剪区域，拖动方框手柄可调整")
        tk.Label(frame, textvariable=self.single_hint,
                 font=("Microsoft YaHei", 8), fg=self.C_MUTED,
                 bg=self.C_BG).pack(anchor="w", pady=(8, 0))

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
            hint += "  |  ⚠ PNG 无法压缩"
            self.lbl_png_warn.grid()
        else:
            self.lbl_png_warn.grid_remove()
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
        wrapper.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        frame = ttk.LabelFrame(wrapper, text=" 文件夹设置 ", padding=14)
        frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(frame, text="图片文件夹").grid(row=0, column=0, sticky="e", pady=6, padx=(0, 8))
        ttk.Entry(frame, textvariable=self.input_dir, width=52).grid(row=0, column=1, padx=4)
        ttk.Button(frame, text="选择", command=self._select_input_dir).grid(row=0, column=2, padx=2)

        ttk.Label(frame, text="输出文件夹").grid(row=1, column=0, sticky="e", pady=6, padx=(0, 8))
        ttk.Entry(frame, textvariable=self.output_dir, width=52).grid(row=1, column=1, padx=4)
        ttk.Button(frame, text="选择", command=self._select_output_dir).grid(row=1, column=2, padx=2)

        frame2 = ttk.LabelFrame(wrapper, text=" 处理参数 ", padding=14)
        frame2.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(frame2, text="目标宽度").grid(row=0, column=0, sticky="e", padx=(0, 8))
        ttk.Entry(frame2, textvariable=self.target_width, width=10).grid(row=0, column=1, padx=4)
        ttk.Label(frame2, text="px").grid(row=0, column=2, padx=(2, 30))

        ttk.Label(frame2, text="压缩质量").grid(row=0, column=3, sticky="e", padx=(0, 8))
        ttk.Entry(frame2, textvariable=self.quality, width=10).grid(row=0, column=4, padx=4)
        ttk.Label(frame2, text="(1-100)").grid(row=0, column=5, padx=(2, 0))

        self.batch_btn = ttk.Button(wrapper, text="开始处理", command=self._batch_start)
        self.batch_btn.pack(pady=(10, 6))

        self.batch_status = tk.StringVar(value="准备就绪")
        tk.Label(wrapper, textvariable=self.batch_status, font=("Microsoft YaHei", 9),
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
