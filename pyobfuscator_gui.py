#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import sys
import threading
import time
import tkinter as tk
import tkinter.font as tkfont
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

# 优先从当前目录导入混淆器核心
try:
    import pyobfuscator as obf_core
except Exception as exc:  # pragma: no cover
    messagebox.showerror(
        "导入失败",
        f"无法导入 pyobfuscator 模块。请确保 pyobfuscator.py 与本 GUI 文件在同一目录。\n\n{exc}",
    )
    raise


# ============================================================
# 设计令牌
# ============================================================

COLORS = {
    "bg_deep": "#050508",
    "bg_dark": "#0a0a0f",
    "bg_panel": "#101018",
    "bg_card": "#161622",
    "bg_card_hover": "#1c1c2d",
    "bg_input": "#0e0e15",
    "border": "#27273a",
    "border_focus": "#00f0ff",
    "text_main": "#e8e8f2",
    "text_dim": "#7a7a99",
    "text_muted": "#55556b",
    "accent_cyan": "#00f0ff",
    "accent_green": "#00ff9d",
    "accent_red": "#ff3860",
    "accent_yellow": "#ffd166",
    "accent_purple": "#b983ff",
}

# 选择系统上最可能存在的字体，优先等宽以呼应代码主题
MONO_FONTS = [
    "JetBrains Mono", "Fira Code", "Source Code Pro", "Consolas",
    "DejaVu Sans Mono", "Liberation Mono", "Ubuntu Mono", "Noto Sans Mono",
    "Courier New", "monospace",
]
UI_FONTS = [
    "Segoe UI", "Helvetica Neue", "Arial", "Roboto",
    "Noto Sans", "DejaVu Sans", "Ubuntu", "Cantarell", "sans-serif",
]


def pick_font(preferred, fallback=("monospace",), default_name="TkDefaultFont"):
    """选择字体：枚举系统可用字体族，返回第一个存在的候选字体。

    同时检查 Tk 默认字体族；若默认字体在候选列表中且系统可用，优先使用。
    """
    try:
        available = set(tkfont.families())
    except Exception:
        available = set()

    try:
        default_family = tkfont.nametofont(default_name).actual("family")
        if default_family in available:
            available.add(default_family)
            if default_family.lower() in {p.lower() for p in preferred}:
                return default_family
    except Exception:
        pass

    for name in preferred:
        if name in available:
            return name
    return fallback[0] if fallback else "TkDefaultFont"


MONO = pick_font(MONO_FONTS, default_name="TkFixedFont")
UI = pick_font(UI_FONTS, fallback=("sans-serif",), default_name="TkDefaultFont")

FONTS = {
    "title": (MONO, 26, "bold"),
    "subtitle": (UI, 10, "normal"),
    "h2": (MONO, 13, "bold"),
    "h3": (MONO, 11, "bold"),
    "body": (UI, 10, "normal"),
    "mono": (MONO, 10, "normal"),
    "mono_small": (MONO, 9, "normal"),
    "button": (MONO, 10, "bold"),
    "stat_value": (MONO, 18, "bold"),
    "stat_label": (UI, 9, "normal"),
}


# ============================================================
# 辅助工具
# ============================================================

def format_bytes(n: int) -> str:
    for unit in ("B", "KB", "MB"):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} GB"


def clamp(value, min_v, max_v):
    return max(min_v, min(max_v, value))


def hex_lerp(a: str, b: str, t: float) -> str:
    """两个 #RRGGBB 颜色之间的线性插值。"""
    t = clamp(t, 0.0, 1.0)
    a = a.lstrip("#")
    b = b.lstrip("#")
    out = []
    for i in range(0, 6, 2):
        av = int(a[i : i + 2], 16)
        bv = int(b[i : i + 2], 16)
        out.append(f"{int(av + (bv - av) * t):02x}")
    return "#" + "".join(out)


def draw_rounded_rect(canvas: tk.Canvas, x1: int, y1: int, x2: int, y2: int, radius: int, **kwargs):
    """用单个平滑多边形绘制圆角矩形，避免拼接造成的边缘凹凸。

    通过重复角点控制 smooth=True 的贝塞尔曲线，使直线段保持笔直。
    """
    r = min(radius, (x2 - x1) // 2, (y2 - y1) // 2)
    points = [
        x1 + r, y1, x1 + r, y1,
        x2 - r, y1, x2 - r, y1,
        x2, y1, x2, y1 + r, x2, y1 + r,
        x2, y2 - r, x2, y2 - r,
        x2, y2, x2 - r, y2, x2 - r, y2,
        x1 + r, y2, x1 + r, y2,
        x1, y2, x1, y2 - r, x1, y2 - r,
        x1, y1 + r, x1, y1 + r,
        x1, y1,
    ]
    return canvas.create_polygon(points, smooth=True, **kwargs)


# ============================================================
# 自定义组件
# ============================================================

class NeonButton(tk.Canvas):
    """带霓虹边框与微光动画的按钮。"""

    def __init__(self, parent, text, command=None, color=None, width=120, height=34, **kw):
        self.btn_color = color or COLORS["accent_cyan"]
        self.command = command
        self._hover = False
        self._pressed = False
        super().__init__(
            parent,
            width=width,
            height=height,
            bg=COLORS["bg_panel"],
            highlightthickness=0,
            cursor="hand2",
            **kw,
        )
        self._text_id = self.create_text(
            width // 2,
            height // 2,
            text=text,
            font=FONTS["button"],
            fill=COLORS["text_main"],
        )
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<ButtonPress-1>", self._on_press)
        self.bind("<ButtonRelease-1>", self._on_release)
        self._draw()

    def _draw(self):
        self.delete("border", "glow")
        w, h = int(self["width"]), int(self["height"])
        # 背景
        bg = COLORS["bg_card_hover"] if self._hover else COLORS["bg_card"]
        self.create_rectangle(2, 2, w - 2, h - 2, fill=bg, outline="", tags="border")
        # 边框
        shade = hex_lerp(self.btn_color, "#ffffff", 0.35) if self._hover else self.btn_color
        width = 2 if self._hover else 1
        self.create_rectangle(1, 1, w - 1, h - 1, fill="", outline=shade, width=width, tags="border")
        # 顶部微光
        if self._hover:
            self.create_line(4, 1, w - 4, 1, fill=shade, width=2, tags="glow")
        # 文字颜色
        self.itemconfig(self._text_id, fill=shade if self._hover else COLORS["text_main"])
        self.tag_raise(self._text_id)

    def _on_enter(self, _=None):
        self._hover = True
        self._draw()

    def _on_leave(self, _=None):
        self._hover = False
        self._pressed = False
        self._draw()

    def _on_press(self, _=None):
        self._pressed = True

    def _on_release(self, _=None):
        if self._pressed and self.command:
            self.command()
        self._pressed = False

    def set_text(self, text: str):
        self.itemconfig(self._text_id, text=text)


class ToggleSwitch(tk.Canvas):
    """Canvas 自定义开关，带滑块动画。"""

    WIDTH = 44
    HEIGHT = 22
    RADIUS = 10

    def __init__(self, parent, initial=False, command=None, **kw):
        self.value = bool(initial)
        self._command = command
        self._animating = False
        # 视觉进度 0.0=关, 1.0=开，确保初始状态与 value 一致
        self._visual_t = 1.0 if self.value else 0.0
        super().__init__(
            parent,
            width=self.WIDTH,
            height=self.HEIGHT,
            bg=COLORS["bg_card"],
            highlightthickness=0,
            cursor="hand2",
            **kw,
        )
        self.bind("<Button-1>", self._toggle)
        self._draw(self._visual_t)

    def _toggle(self, _=None):
        self.value = not self.value
        self._animate()
        if self._command:
            self._command(self.value)

    def _animate(self):
        if self._animating:
            return
        self._animating = True
        start_t = self._visual_t
        target_t = 1.0 if self.value else 0.0
        # 如果已经处于目标状态，直接结束
        if abs(start_t - target_t) < 0.001:
            self._animating = False
            return

        duration_ms = 120
        frames = 10
        step_ms = duration_ms // frames

        def step(frame):
            if frame >= frames:
                self._visual_t = target_t
                self._draw(self._visual_t)
                self._animating = False
                return
            raw = frame / frames
            # ease-out cubic
            eased = 1 - (1 - raw) ** 3
            self._visual_t = start_t + (target_t - start_t) * eased
            self._draw(self._visual_t)
            self.after(step_ms, step, frame + 1)

        step(0)

    def _draw(self, t: float):
        self.delete("all")
        w, h = self.WIDTH, self.HEIGHT
        r = self.RADIUS
        on_color = COLORS["accent_green"]
        off_color = COLORS["border"]
        # 轨道颜色插值
        bg = hex_lerp(off_color, on_color, t)
        # 轨道：单个平滑圆角矩形，消除拼接缝隙
        draw_rounded_rect(self, 1, 1, w - 1, h - 1, h // 2, fill=bg, outline="")
        # 滑块位置插值
        start_x = r
        end_x = (w - h) + r
        cx = start_x + (end_x - start_x) * t
        cy = h // 2
        self.create_oval(cx - r + 2, cy - r + 2, cx + r - 2, cy + r - 2, fill=COLORS["text_main"], outline="")

    def get(self) -> bool:
        return self.value

    def set(self, value: bool):
        if bool(value) != self.value:
            self.value = bool(value)
            self._animate()
            if self._command:
                self._command(self.value)

    def set_silent(self, value: bool):
        """仅更新视觉状态，不触发 command（用于批量同步档位）。"""
        if bool(value) != self.value:
            self.value = bool(value)
            self._visual_t = 1.0 if self.value else 0.0
            self._draw(self._visual_t)


class OptionToggle(tk.Canvas):
    """选项开关：将 ToggleSwitch 与文字合并到单个 Canvas，减少 widget 数量以加速启动。"""

    SW_W = 44      # 开关宽度
    SW_H = 22      # 开关高度
    SW_R = 10      # 滑块半径
    TOTAL_W = 180  # 控件总宽度

    def __init__(self, parent, text: str, initial=False, command=None, **kw):
        self.value = bool(initial)
        self.text = text
        self._command = command
        self._animating = False
        self._visual_t = 1.0 if self.value else 0.0
        super().__init__(
            parent,
            width=self.TOTAL_W,
            height=self.SW_H,
            bg=COLORS["bg_panel"],
            highlightthickness=0,
            cursor="hand2",
            **kw,
        )
        self.bind("<Button-1>", self._toggle)
        self._draw(self._visual_t)

    def _toggle(self, _=None):
        self.value = not self.value
        self._animate()
        if self._command:
            self._command(self.value)

    def _animate(self):
        if self._animating:
            return
        self._animating = True
        start_t = self._visual_t
        target_t = 1.0 if self.value else 0.0
        if abs(start_t - target_t) < 0.001:
            self._animating = False
            return

        duration_ms = 120
        frames = 10
        step_ms = duration_ms // frames

        def step(frame):
            if frame >= frames:
                self._visual_t = target_t
                self._draw(self._visual_t)
                self._animating = False
                return
            raw = frame / frames
            eased = 1 - (1 - raw) ** 3
            self._visual_t = start_t + (target_t - start_t) * eased
            self._draw(self._visual_t)
            self.after(step_ms, step, frame + 1)

        step(0)

    def _draw(self, t: float):
        self.delete("all")
        w, h, r = self.SW_W, self.SW_H, self.SW_R
        on_color = COLORS["accent_green"]
        off_color = COLORS["border"]
        bg = hex_lerp(off_color, on_color, t)

        # 开关轨道：单个平滑圆角矩形，消除拼接缝隙
        draw_rounded_rect(self, 1, 1, w - 1, h - 1, h // 2, fill=bg, outline="")

        # 滑块
        start_x = r
        end_x = (w - h) + r
        cx = start_x + (end_x - start_x) * t
        cy = h // 2
        self.create_oval(cx - r + 2, cy - r + 2, cx + r - 2, cy + r - 2, fill=COLORS["text_main"], outline="")

        # 文字
        self.create_text(
            w + 8,
            h // 2,
            text=self.text,
            font=FONTS["body"],
            fill=COLORS["text_main"],
            anchor="w",
        )

    def get(self) -> bool:
        return self.value

    def set(self, value: bool):
        if bool(value) != self.value:
            self.value = bool(value)
            self._animate()
            if self._command:
                self._command(self.value)

    def set_silent(self, value: bool):
        """仅更新视觉状态，不触发 command。"""
        if bool(value) != self.value:
            self.value = bool(value)
            self._visual_t = 1.0 if self.value else 0.0
            self._draw(self._visual_t)


class LevelCard(tk.Frame):
    """档位选择卡片：轻量 / 标准 / 强化。"""

    def __init__(self, parent, key, desc, color, command):
        super().__init__(parent, bg=COLORS["bg_card"], padx=0, pady=0)
        self.key = key
        self.desc = desc
        self._command = command
        self._selected = False
        self.color = color

        self.canvas = tk.Canvas(
            self,
            width=170,
            height=90,
            bg=COLORS["bg_card"],
            highlightthickness=0,
            cursor="hand2",
        )
        self.canvas.pack()
        self.canvas.bind("<Enter>", self._on_enter)
        self.canvas.bind("<Leave>", self._on_leave)
        self.canvas.bind("<Button-1>", self._on_click)

        self._draw()

    def _draw(self):
        self.canvas.delete("all")
        w, h = 170, 90
        fill = self.color if self._selected else COLORS["bg_card"]
        outline = self.color if self._selected else COLORS["border"]
        width = 2 if self._selected else 1
        # 外框
        self.canvas.create_rectangle(1, 1, w - 1, h - 1, fill=fill, outline=outline, width=width)
        # 标签
        label_color = COLORS["bg_deep"] if self._selected else self.color
        self.canvas.create_text(w // 2, 26, text=self.key.upper(), font=FONTS["h2"], fill=label_color)
        self.canvas.create_text(w // 2, 50, text=self.label, font=FONTS["body"], fill=COLORS["text_main"])
        self.canvas.create_text(w // 2, 70, text=self.desc, font=FONTS["mono_small"], fill=COLORS["text_dim"])

    @property
    def label(self):
        return obf_core.LEVEL_PRESETS[self.key]["label"]

    def _on_enter(self, _=None):
        if not self._selected:
            self.canvas.itemconfig(tk.ALL, fill=COLORS["bg_card_hover"])

    def _on_leave(self, _=None):
        self._draw()

    def _on_click(self, _=None):
        self._command(self.key)

    def set_selected(self, selected: bool):
        self._selected = selected
        self._draw()


class StatCard(tk.Frame):
    """结果统计卡片。"""

    def __init__(self, parent, label, value="—", color=COLORS["accent_cyan"]):
        super().__init__(parent, bg=COLORS["bg_panel"], padx=10, pady=8)
        self.color = color
        self.value_label = tk.Label(
            self,
            text=value,
            font=FONTS["stat_value"],
            bg=COLORS["bg_panel"],
            fg=self.color,
        )
        self.value_label.pack(anchor="w")
        tk.Label(
            self,
            text=label,
            font=FONTS["stat_label"],
            bg=COLORS["bg_panel"],
            fg=COLORS["text_dim"],
        ).pack(anchor="w")

    def set_value(self, value: str):
        self.value_label.config(text=value)


class TerminalLog(tk.Text):
    """终端风格的日志输出区。"""

    def __init__(self, parent, height=10):
        super().__init__(
            parent,
            height=height,
            bg=COLORS["bg_deep"],
            fg=COLORS["text_dim"],
            insertbackground=COLORS["accent_cyan"],
            font=FONTS["mono_small"],
            relief="flat",
            state="disabled",
            wrap="word",
            padx=10,
            pady=10,
            borderwidth=0,
            highlightthickness=1,
            highlightcolor=COLORS["border"],
            highlightbackground=COLORS["border"],
        )
        self.tag_config("info", foreground=COLORS["text_dim"])
        self.tag_config("ok", foreground=COLORS["accent_green"])
        self.tag_config("warn", foreground=COLORS["accent_yellow"])
        self.tag_config("err", foreground=COLORS["accent_red"])
        self.tag_config("cyan", foreground=COLORS["accent_cyan"])

    def log(self, message: str, tag: str = "info"):
        self.config(state="normal")
        timestamp = time.strftime("%H:%M:%S")
        self.insert("end", f"[{timestamp}] {message}\n", tag)
        self.see("end")
        self.config(state="disabled")

    def clear(self):
        self.config(state="normal")
        self.delete("1.0", "end")
        self.config(state="disabled")


# ============================================================
# 主应用
# ============================================================

class PyObfuscatorGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        # 先隐藏窗口，待 UI 构建完成并定位后再显示，减少启动时的闪烁与重绘
        self.withdraw()
        self.title("PYOBFUSCATOR // GUI")
        self.configure(bg=COLORS["bg_deep"])
        self.minsize(900, 700)

        # 所有选项开关引用
        self.option_vars: dict[str, tk.BooleanVar] = {}
        self.toggle_widgets: dict[str, OptionToggle] = {}
        self.current_level = tk.StringVar(value="standard")

        self._build_styles()
        self._build_ui()
        self._on_level_changed("standard")

        # 窗口居中并显示（放在最后，只做一次 geometry 更新）
        self.geometry("1080x820")
        self.update_idletasks()
        x = (self.winfo_screenwidth() // 2) - (1080 // 2)
        y = (self.winfo_screenheight() // 2) - (820 // 2)
        self.geometry(f"+{x}+{y}")
        self.deiconify()

    def _build_styles(self):
        style = ttk.Style(self)
        style.theme_use("clam")

        # 通用
        style.configure("TFrame", background=COLORS["bg_panel"])
        style.configure("TLabel", background=COLORS["bg_panel"], foreground=COLORS["text_main"], font=FONTS["body"])
        style.configure(
            "TEntry",
            fieldbackground=COLORS["bg_input"],
            foreground=COLORS["text_main"],
            insertcolor=COLORS["accent_cyan"],
            bordercolor=COLORS["border"],
            lightcolor=COLORS["border"],
            darkcolor=COLORS["border"],
            font=FONTS["mono"],
        )
        style.configure(
            "TCombobox",
            fieldbackground=COLORS["bg_input"],
            foreground=COLORS["text_main"],
            background=COLORS["bg_input"],
            bordercolor=COLORS["border"],
            font=FONTS["mono"],
        )
        style.map(
            "TCombobox",
            fieldbackground=[("readonly", COLORS["bg_input"])],
            selectbackground=[("readonly", COLORS["accent_cyan"])],
            selectforeground=[("readonly", COLORS["bg_deep"])],
        )
        style.configure(
            "TCheckbutton",
            background=COLORS["bg_card"],
            foreground=COLORS["text_main"],
            font=FONTS["body"],
        )
        style.layout("TCheckbutton", [("Checkbutton.padding", {"sticky": "nswe"})])

    def _build_ui(self):
        # 根容器
        main = tk.Frame(self, bg=COLORS["bg_deep"])
        main.pack(fill="both", expand=True, padx=18, pady=18)

        # 顶部标题
        header = tk.Frame(main, bg=COLORS["bg_panel"], height=90)
        header.pack(fill="x", pady=(0, 14))
        header.pack_propagate(False)

        title_container = tk.Frame(header, bg=COLORS["bg_panel"])
        title_container.pack(side="left", padx=(20, 0), pady=(10, 0))

        tk.Label(
            title_container,
            text="PYOBFUSCATOR",
            font=FONTS["title"],
            bg=COLORS["bg_panel"],
            fg=COLORS["accent_cyan"],
        ).pack(anchor="w")

        # 标题下方的霓虹下划线（8 段渐变，减少绘制开销）
        underline = tk.Canvas(
            title_container,
            width=260,
            height=3,
            bg=COLORS["bg_panel"],
            highlightthickness=0,
        )
        underline.pack(anchor="w", pady=(2, 0))
        segments = 8
        seg_w = 260 / segments
        for i in range(segments):
            t = i / (segments - 1)
            # 中心亮、两端暗
            alpha = 1.0 - abs(t - 0.5) * 1.8
            alpha = max(0.15, alpha)
            color = hex_lerp(COLORS["accent_cyan"], "#ffffff", alpha * 0.5)
            x1 = i * seg_w
            x2 = x1 + seg_w
            underline.create_rectangle(x1, 0, x2, 2, fill=color, outline="")

        tk.Label(
            header,
            text="// 终极 Python 代码混淆器 · 桌面控制终端",
            font=FONTS["subtitle"],
            bg=COLORS["bg_panel"],
            fg=COLORS["text_dim"],
        ).pack(side="left", padx=(12, 0), pady=(22, 0))

        # 主体：左侧控制 + 右侧结果
        body = tk.Frame(main, bg=COLORS["bg_deep"])
        body.pack(fill="both", expand=True)
        body.columnconfigure(0, weight=3)
        body.columnconfigure(1, weight=2)
        body.rowconfigure(0, weight=1)

        left = tk.Frame(body, bg=COLORS["bg_panel"], padx=16, pady=16)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 14))
        right = tk.Frame(body, bg=COLORS["bg_panel"], padx=16, pady=16)
        right.grid(row=0, column=1, sticky="nsew")

        self._build_file_section(left)
        self._build_level_section(left)
        self._build_options_section(left)
        self._build_action_section(left)
        self._build_result_section(right)

    def _build_file_section(self, parent):
        frame = tk.LabelFrame(
            parent,
            text=" 目标文件 ",
            bg=COLORS["bg_panel"],
            fg=COLORS["accent_cyan"],
            font=FONTS["h2"],
            bd=1,
            highlightthickness=0,
            relief="solid",
            labelanchor="n",
        )
        frame.pack(fill="x", pady=(0, 14))

        # 输入文件
        row1 = tk.Frame(frame, bg=COLORS["bg_panel"])
        row1.pack(fill="x", padx=12, pady=(10, 6))
        tk.Label(row1, text="输入文件", font=FONTS["body"], bg=COLORS["bg_panel"], fg=COLORS["text_dim"]).pack(
            side="left"
        )
        self.input_var = tk.StringVar()
        ttk.Entry(row1, textvariable=self.input_var, width=50).pack(side="left", padx=(10, 0), fill="x", expand=True)
        NeonButton(row1, text="选择", command=self._choose_input, width=70, height=26).pack(side="left", padx=(8, 0))

        # 输出文件
        row2 = tk.Frame(frame, bg=COLORS["bg_panel"])
        row2.pack(fill="x", padx=12, pady=(0, 12))
        tk.Label(row2, text="输出文件", font=FONTS["body"], bg=COLORS["bg_panel"], fg=COLORS["text_dim"]).pack(
            side="left"
        )
        self.output_var = tk.StringVar()
        ttk.Entry(row2, textvariable=self.output_var, width=50).pack(side="left", padx=(10, 0), fill="x", expand=True)
        NeonButton(row2, text="选择", command=self._choose_output, width=70, height=26, color=COLORS["accent_yellow"]).pack(
            side="left", padx=(8, 0)
        )

    def _build_level_section(self, parent):
        frame = tk.LabelFrame(
            parent,
            text=" 混淆档位 ",
            bg=COLORS["bg_panel"],
            fg=COLORS["accent_cyan"],
            font=FONTS["h2"],
            bd=1,
            highlightthickness=0,
            relief="solid",
            labelanchor="n",
        )
        frame.pack(fill="x", pady=(0, 14))

        cards = tk.Frame(frame, bg=COLORS["bg_panel"])
        cards.pack(padx=12, pady=(10, 12))

        self.level_cards = {}
        specs = [
            ("light", "轻量快速", COLORS["accent_green"]),
            ("standard", "均衡标准", COLORS["accent_cyan"]),
            ("heavy", "极限强化", COLORS["accent_red"]),
        ]
        for key, desc, color in specs:
            card = LevelCard(cards, key, desc, color, self._on_level_changed)
            card.pack(side="left", padx=6)
            self.level_cards[key] = card

    def _build_options_section(self, parent):
        frame = tk.LabelFrame(
            parent,
            text=" 混淆选项 ",
            bg=COLORS["bg_panel"],
            fg=COLORS["accent_cyan"],
            font=FONTS["h2"],
            bd=1,
            highlightthickness=0,
            relief="solid",
            labelanchor="n",
        )
        frame.pack(fill="both", expand=True, pady=(0, 14))

        container = tk.Frame(frame, bg=COLORS["bg_panel"])
        container.pack(fill="both", expand=True, padx=12, pady=(10, 12))

        groups = {
            "标识符": ["var-rename", "func-rename", "class-rename", "homoglyph-names"],
            "字符串与常量": [
                "string-encode",
                "string-multi-round",
                "number-obfuscate",
                "float-obfuscate",
                "container-obfuscate",
                "bytes-obfuscate",
            ],
            "代码流与结构": [
                "junk-code",
                "opaque-predicates",
                "dead-code",
                "control-flatten",
                "bool-obscure",
                "expr-wrap",
                "binop-wrap",
                "dynamic-attrs",
            ],
            "高级": [
                "import-hide",
                "scramble-annotations",
                "fstring-obfuscate",
                "marshal-wrap",
                "lambda-wrap",
                "anti-debug",
            ],
        }

        labels = {
            "var-rename": "变量重命名",
            "func-rename": "函数重命名",
            "class-rename": "类名重命名",
            "homoglyph-names": "同形异义符",
            "string-encode": "字符串编码",
            "string-multi-round": "多轮编码",
            "number-obfuscate": "数字混淆",
            "float-obfuscate": "浮点混淆",
            "container-obfuscate": "容器混淆",
            "bytes-obfuscate": "字节串混淆",
            "junk-code": "垃圾代码",
            "opaque-predicates": "不透明谓词",
            "dead-code": "死代码注入",
            "control-flatten": "控制流扁平化",
            "bool-obscure": "布尔值混淆",
            "expr-wrap": "表达式包裹",
            "binop-wrap": "二元运算包裹",
            "dynamic-attrs": "动态属性",
            "import-hide": "隐藏导入",
            "scramble-annotations": "剥离类型注解",
            "fstring-obfuscate": "f-string 混淆",
            "marshal-wrap": "marshal 包装",
            "lambda-wrap": "lambda 包装",
            "anti-debug": "反调试注入",
        }

        for col, (group_name, opts) in enumerate(groups.items()):
            col_frame = tk.Frame(container, bg=COLORS["bg_panel"])
            col_frame.grid(row=0, column=col, sticky="n", padx=6)
            tk.Label(
                col_frame,
                text=group_name,
                font=FONTS["h3"],
                bg=COLORS["bg_panel"],
                fg=COLORS["accent_yellow"],
            ).pack(anchor="w", pady=(0, 8))
            for opt in opts:
                var = tk.BooleanVar(value=False)
                self.option_vars[opt] = var
                toggle = OptionToggle(
                    col_frame,
                    text=labels.get(opt, opt),
                    initial=False,
                    command=lambda v, o=opt: self._on_option_toggled(o, v),
                )
                self.toggle_widgets[opt] = toggle
                toggle.pack(anchor="w", pady=2)

    def _build_action_section(self, parent):
        frame = tk.Frame(parent, bg=COLORS["bg_panel"])
        frame.pack(fill="x", pady=(0, 0))

        # 种子 + 保留 docstring
        controls = tk.Frame(frame, bg=COLORS["bg_panel"])
        controls.pack(fill="x")

        tk.Label(controls, text="随机种子", font=FONTS["body"], bg=COLORS["bg_panel"], fg=COLORS["text_dim"]).pack(
            side="left"
        )
        self.seed_var = tk.StringVar()
        ttk.Entry(controls, textvariable=self.seed_var, width=12).pack(side="left", padx=(8, 18))

        self.keep_doc_var = tk.BooleanVar(value=False)
        row = tk.Frame(controls, bg=COLORS["bg_panel"])
        row.pack(side="left")
        self.keep_doc_toggle = ToggleSwitch(row, initial=False, command=lambda v: self.keep_doc_var.set(v))
        self.keep_doc_toggle.pack(side="left")
        tk.Label(
            row,
            text="保留文档字符串",
            font=FONTS["body"],
            bg=COLORS["bg_panel"],
            fg=COLORS["text_main"],
        ).pack(side="left", padx=(8, 0))

        self.run_btn = NeonButton(
            controls,
            text="▶ 执行混淆",
            command=self._run_obfuscation,
            color=COLORS["accent_green"],
            width=160,
            height=38,
        )
        self.run_btn.pack(side="right")

    def _build_result_section(self, parent):
        # 统计卡片网格
        stats_frame = tk.Frame(parent, bg=COLORS["bg_panel"])
        stats_frame.pack(fill="x", pady=(0, 12))
        stats_frame.columnconfigure(0, weight=1)
        stats_frame.columnconfigure(1, weight=1)

        self.stat_cards = {
            "input_size": StatCard(stats_frame, "原始大小", "—", COLORS["accent_cyan"]),
            "output_size": StatCard(stats_frame, "混淆后大小", "—", COLORS["accent_green"]),
            "ratio": StatCard(stats_frame, "膨胀率", "—", COLORS["accent_yellow"]),
            "time": StatCard(stats_frame, "耗时", "—", COLORS["accent_purple"]),
        }
        self.stat_cards["input_size"].grid(row=0, column=0, sticky="nsew", padx=(0, 6), pady=(0, 6))
        self.stat_cards["output_size"].grid(row=0, column=1, sticky="nsew", padx=(6, 0), pady=(0, 6))
        self.stat_cards["ratio"].grid(row=1, column=0, sticky="nsew", padx=(0, 6), pady=(6, 0))
        self.stat_cards["time"].grid(row=1, column=1, sticky="nsew", padx=(6, 0), pady=(6, 0))

        # 日志终端
        tk.Label(
            parent,
            text="> 执行日志",
            font=FONTS["h3"],
            bg=COLORS["bg_panel"],
            fg=COLORS["accent_cyan"],
        ).pack(anchor="w", pady=(14, 6))
        self.log = TerminalLog(parent, height=18)
        self.log.pack(fill="both", expand=True)

    # ============================================================
    # 交互逻辑
    # ============================================================

    def _choose_input(self):
        path = filedialog.askopenfilename(
            title="选择要混淆的 Python 文件",
            filetypes=[("Python 文件", "*.py"), ("所有文件", "*.*")],
        )
        if path:
            self.input_var.set(path)
            if not self.output_var.get():
                p = Path(path)
                if p.suffix == ".py":
                    self.output_var.set(str(p.with_suffix("")) + "_obfuscated.py")
                else:
                    self.output_var.set(str(p) + "_obfuscated.py")

    def _choose_output(self):
        path = filedialog.asksaveasfilename(
            title="保存混淆后的文件",
            defaultextension=".py",
            filetypes=[("Python 文件", "*.py"), ("所有文件", "*.*")],
        )
        if path:
            self.output_var.set(path)

    def _on_level_changed(self, level: str):
        self.current_level.set(level)
        for key, card in self.level_cards.items():
            card.set_selected(key == level)
        self._apply_preset(level)

    def _apply_preset(self, level: str):
        preset = obf_core.LEVEL_PRESETS[level]
        for opt, var in self.option_vars.items():
            value = bool(preset.get(opt, False))
            var.set(value)
            toggle = self.toggle_widgets.get(opt)
            if toggle is not None:
                toggle.set_silent(value)
        # 保留文档字符串始终关闭
        self.keep_doc_var.set(False)
        if hasattr(self, "keep_doc_toggle"):
            self.keep_doc_toggle.set_silent(False)
        self.log.log(f"已加载混淆档位: {preset['label']} ({level})", "cyan")

    def _on_option_toggled(self, opt: str, value: bool):
        self.option_vars[opt].set(value)
        # 检查是否偏离当前档位
        level = self.current_level.get()
        preset_val = bool(obf_core.LEVEL_PRESETS[level].get(opt, False))
        if value != preset_val:
            self.level_cards[level].set_selected(False)
            # 提示用户已自定义
            self.log.log(f"自定义选项: {opt}={'开' if value else '关'}", "warn")

    def _build_obfuscator(self) -> obf_core.Obfuscator:
        # 解析随机种子
        seed_str = self.seed_var.get().strip()
        seed = int(seed_str) if seed_str else None

        return obf_core.Obfuscator(
            var_rename=self.option_vars["var-rename"].get(),
            func_rename=self.option_vars["func-rename"].get(),
            class_rename=self.option_vars["class-rename"].get(),
            string_encode=self.option_vars["string-encode"].get(),
            string_multi_round=self.option_vars["string-multi-round"].get(),
            number_obfuscate=self.option_vars["number-obfuscate"].get(),
            float_obfuscate=self.option_vars["float-obfuscate"].get(),
            container_obfuscate=self.option_vars["container-obfuscate"].get(),
            bytes_obfuscate=self.option_vars["bytes-obfuscate"].get(),
            junk_code=self.option_vars["junk-code"].get(),
            junk_count=obf_core.LEVEL_PRESETS[self.current_level.get()]["junk-count"],
            opaque_predicates=self.option_vars["opaque-predicates"].get(),
            opaque_prob=obf_core.LEVEL_PRESETS[self.current_level.get()]["opaque-prob"],
            dead_code=self.option_vars["dead-code"].get(),
            control_flatten=self.option_vars["control-flatten"].get(),
            import_hide=self.option_vars["import-hide"].get(),
            homoglyph_names=self.option_vars["homoglyph-names"].get(),
            bool_obscure=self.option_vars["bool-obscure"].get(),
            expr_wrap=self.option_vars["expr-wrap"].get(),
            binop_wrap=self.option_vars["binop-wrap"].get(),
            dynamic_attrs=self.option_vars["dynamic-attrs"].get(),
            scramble_annotations=self.option_vars["scramble-annotations"].get(),
            fstring_obfuscate=self.option_vars["fstring-obfuscate"].get(),
            strip_docstrings=not self.keep_doc_var.get(),
            string_methods=obf_core.LEVEL_PRESETS[self.current_level.get()]["string-methods"],
            seed=seed,
            marshal_wrap=self.option_vars["marshal-wrap"].get(),
            lambda_wrap=self.option_vars["lambda-wrap"].get(),
            anti_debug=self.option_vars["anti-debug"].get(),
        )

    def _run_obfuscation(self):
        input_path = self.input_var.get().strip()
        output_path = self.output_var.get().strip()

        if not input_path:
            messagebox.showwarning("缺少输入", "请先选择要混淆的 Python 文件。")
            return
        if not Path(input_path).exists():
            messagebox.showerror("文件不存在", f"找不到输入文件:\n{input_path}")
            return

        if not output_path:
            p = Path(input_path)
            output_path = str(p.with_suffix("")) + "_obfuscated.py" if p.suffix == ".py" else str(p) + "_obfuscated.py"
            self.output_var.set(output_path)

        # 在主线程读取所有 Tk 变量并构建混淆器，避免子线程访问 Tk 引发线程安全错误
        try:
            obf = self._build_obfuscator()
        except Exception as exc:
            self._on_error(f"构建混淆器失败: {exc}")
            return

        self.run_btn.set_text("运行中...")
        self.run_btn.config(state="disabled")
        self.log.clear()
        self.log.log(f"输入: {input_path}", "cyan")
        self.log.log(f"输出: {output_path}", "cyan")
        self.log.log(f"档位: {obf_core.LEVEL_PRESETS[self.current_level.get()]['label']}", "cyan")

        # 在后台线程运行混淆，避免阻塞 UI
        thread = threading.Thread(
            target=self._obfuscate_worker,
            args=(input_path, output_path, obf),
            daemon=True,
        )
        thread.start()

    def _obfuscate_worker(self, input_path: str, output_path: str, obf: obf_core.Obfuscator):
        try:
            with open(input_path, "r", encoding="utf-8") as f:
                source = f.read()
            if not source.strip():
                self.after(0, lambda: self._on_error("输入文件为空"))
                return

            start = time.perf_counter()
            obfuscated = obf.obfuscate(source)
            elapsed = time.perf_counter() - start

            with open(output_path, "w", encoding="utf-8") as f:
                f.write(obfuscated)

            self.after(0, lambda: self._on_success(input_path, output_path, source, obfuscated, elapsed, obf))
        except obf_core.ObfuscationError as exc:
            self.after(0, lambda: self._on_error(str(exc)))
        except SyntaxError as exc:
            self.after(0, lambda: self._on_error(f"输入文件存在语法错误: {exc}"))
        except Exception as exc:
            self.after(0, lambda: self._on_error(f"混淆失败: {exc}"))

    def _on_success(self, input_path: str, output_path: str, source: str, obfuscated: str, elapsed: float, obf):
        src_bytes = len(source.encode("utf-8"))
        out_bytes = len(obfuscated.encode("utf-8"))
        ratio = (len(obfuscated) / len(source) - 1) * 100 if source else 0

        self.stat_cards["input_size"].set_value(format_bytes(src_bytes))
        self.stat_cards["output_size"].set_value(format_bytes(out_bytes))
        self.stat_cards["ratio"].set_value(f"+{ratio:.1f}%")
        self.stat_cards["time"].set_value(f"{elapsed * 1000:.0f} ms")

        self.log.log("混淆完成", "ok")
        self.log.log(f"执行耗时: {elapsed:.2f} 秒", "ok")
        self.log.log(f"原始大小: {format_bytes(src_bytes)} ({source.count(chr(10)) + 1} 行)", "info")
        self.log.log(f"混淆后大小: {format_bytes(out_bytes)} ({obfuscated.count(chr(10)) + 1} 行)", "info")
        self.log.log("统计项:", "cyan")

        labels = {
            "vars_renamed": "变量重命名",
            "funcs_renamed": "函数重命名",
            "classes_renamed": "类名重命名",
            "strings_encoded": "字符串编码",
            "multi_round_strings": "多轮字符串编码",
            "numbers_obfuscated": "数字混淆",
            "floats_obfuscated": "浮点数混淆",
            "containers_obfuscated": "容器混淆",
            "bytes_obfuscated": "字节串混淆",
            "bools_obscured": "布尔值混淆",
            "junk_blocks": "垃圾代码块",
            "opaque_predicates": "不透明谓词",
            "dead_code_injected": "死代码注入",
            "flattened_blocks": "扁平化块",
            "hidden_imports": "隐藏导入",
            "exprs_wrapped": "表达式包裹",
            "binops_wrapped": "二元运算包裹",
            "attrs_dynamic": "动态属性",
            "annotations_scrambled": "类型注解剥离",
            "fstrings_obfuscated": "f-string混淆",
            "anti_debug_injected": "反调试注入",
            "marshal_wrapped": "代码包装",
        }
        for key, label in labels.items():
            v = obf.stats.get(key, 0)
            if v:
                self.log.log(f"  · {label}: {v}", "info")

        self.run_btn.set_text("▶ 执行混淆")
        self.run_btn.config(state="normal")

    def _on_error(self, message: str):
        self.log.log(f"错误: {message}", "err")
        self.stat_cards["input_size"].set_value("—")
        self.stat_cards["output_size"].set_value("—")
        self.stat_cards["ratio"].set_value("—")
        self.stat_cards["time"].set_value("—")
        self.run_btn.set_text("▶ 执行混淆")
        self.run_btn.config(state="normal")
        messagebox.showerror("混淆失败", message)


# ============================================================
# 入口
# ============================================================

def main():
    app = PyObfuscatorGUI()
    app.mainloop()


if __name__ == "__main__":
    main()
