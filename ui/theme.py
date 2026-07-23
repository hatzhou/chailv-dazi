# -*- coding: utf-8 -*-
"""
差旅搭子 - 设计系统
集中管理：蓝青调色板、字体栈、全局 QSS 主题、matplotlib 图表主题。
应用入口（main.py）调用 apply_theme(app) 即可整体换肤。
"""
from __future__ import annotations

from PySide6.QtGui import QFont, QColor
from PySide6.QtWidgets import QApplication

# ---------------------------------------------------------------------------
# 调色板（专业蓝青）
# ---------------------------------------------------------------------------
C = {
    # 品牌
    "brand":       "#2563EB",
    "brand_dark":  "#1D4ED8",
    "brand_light": "#3B82F6",
    "accent":      "#06B6D4",
    "brand_tint":  "#EFF6FF",   # 主色极浅底，用于 hover / 激活背景
    # 中性
    "bg":          "#F1F5F9",   # 应用底色（slate-100）
    "surface":     "#FFFFFF",
    "surface_2":   "#F8FAFC",
    "border":      "#E2E8F0",
    "border_2":    "#CBD5E1",
    "text":        "#0F172A",
    "text_2":      "#475569",
    "text_3":      "#94A3B8",
    # 语义
    "success":     "#16A34A",
    "warning":     "#F59E0B",
    "danger":      "#DC2626",
    "info":        "#2563EB",
    "purple":      "#7C3AED",
}

# 主色横向渐变（按钮 / Logo 用）
GRADIENT = "qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0EA5E9, stop:1 #2563EB)"

# 发票状态 -> 颜色（与 config.INVOICE_STATUS 对应，色值更精致）
STATUS_COLORS = {
    "draft":      "#64748B",
    "pending":    "#F59E0B",
    "submitted":  "#2563EB",
    "reimbursed": "#16A34A",
    "rejected":   "#DC2626",
}

# 图表调色板（分类占比 / 趋势）
CHART_COLORS = ["#2563EB", "#06B6D4", "#16A34A", "#F59E0B",
                "#7C3AED", "#EC4899", "#0EA5E9", "#64748B"]

FONT_STACK = "Microsoft YaHei, PingFang SC, Noto Sans CJK SC, WenQuanYi Micro Hei, sans-serif"


# ---------------------------------------------------------------------------
# 全局 QSS
# ---------------------------------------------------------------------------
def stylesheet() -> str:
    return f"""
    /* ===================== 基础 ===================== */
    QWidget {{
        font-family: {FONT_STACK};
        font-size: 13px;
        color: {C['text']};
        background: {C['bg']};
    }}
    QMainWindow, MainWindow {{
        background: {C['bg']};
        border: none;
    }}

    /* ===================== 侧边栏 ===================== */
    #sidebar {{
        background: {C['surface']};
        border-right: 1px solid {C['border']};
    }}
    #sidebarLogo {{
        font-size: 18px;
        font-weight: 700;
        color: {C['text']};
        padding: 4px 0;
    }}
    #sidebarLogoSub {{
        font-size: 11px;
        color: {C['text_3']};
    }}
    #navBtn {{
        background: transparent;
        border: none;
        border-left: 3px solid transparent;
        border-radius: 0;
        color: {C['text_2']};
        text-align: left;
        padding: 10px 14px;
        font-size: 14px;
        min-height: 22px;
    }}
    #navBtn:hover {{
        background: {C['surface_2']};
        color: {C['text']};
    }}
    #navBtn[active="true"] {{
        background: {C['brand_tint']};
        border-left: 3px solid {C['brand']};
        color: {C['brand']};
        font-weight: 600;
    }}
    #navBtnSecondary {{
        background: transparent;
        border: none;
        color: {C['text_3']};
        text-align: left;
        padding: 9px 14px;
        font-size: 13px;
    }}
    #navBtnSecondary:hover {{
        background: {C['surface_2']};
        color: {C['text_2']};
    }}

    /* ===================== 顶部操作条 ===================== */
    #topbar {{
        background: {C['surface']};
        border-bottom: 1px solid {C['border']};
    }}
    #pageTitle {{
        font-size: 18px;
        font-weight: 700;
        color: {C['text']};
    }}
    #pageSubtitle {{
        font-size: 12px;
        color: {C['text_3']};
    }}

    /* ===================== 按钮 ===================== */
    QPushButton {{
        background: {C['surface']};
        border: 1px solid {C['border']};
        border-radius: 8px;
        padding: 7px 14px;
        color: {C['text']};
        min-height: 18px;
    }}
    QPushButton:hover {{
        background: {C['surface_2']};
        border-color: {C['border_2']};
    }}
    QPushButton:pressed {{
        background: {C['bg']};
    }}
    QPushButton:disabled {{
        color: {C['text_3']};
        background: {C['surface_2']};
        border-color: {C['border']};
    }}
    QPushButton#primary {{
        background: {GRADIENT};
        border: none;
        color: #FFFFFF;
        font-weight: 600;
        padding: 8px 18px;
    }}
    QPushButton#primary:hover {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #06B6D4, stop:1 #1D4ED8);
    }}
    QPushButton#primary:pressed {{
        background: #1D4ED8;
    }}
    QPushButton#danger {{
        color: {C['danger']};
        border-color: #FCA5A5;
    }}
    QPushButton#danger:hover {{
        background: #FEF2F2;
        border-color: #F87171;
    }}
    QPushButton#ghost {{
        background: transparent;
        border: none;
        color: {C['brand']};
    }}
    QPushButton#ghost:hover {{
        background: {C['brand_tint']};
    }}

    /* ===================== 输入控件 ===================== */
    QLineEdit, QComboBox, QDateEdit, QSpinBox, QDoubleSpinBox, QTextEdit {{
        background: {C['surface']};
        border: 1px solid {C['border']};
        border-radius: 8px;
        padding: 6px 10px;
        color: {C['text']};
        selection-background-color: {C['brand']};
    }}
    QLineEdit:focus, QComboBox:focus, QDateEdit:focus,
    QSpinBox:focus, QDoubleSpinBox:focus, QTextEdit:focus {{
        border: 1px solid {C['brand']};
        background: {C['brand_tint']};
    }}
    QLineEdit:disabled, QTextEdit:disabled {{
        background: {C['surface_2']};
        color: {C['text_3']};
    }}

    /* --- 下拉框：现代化弹出层 --- */
    QComboBox {{
        padding: 6px 34px 6px 12px;   /* 右侧为默认箭头留出空间 */
        min-height: 20px;
    }}
    QComboBox:on {{
        border: 1px solid {C['brand']};
    }}
    QComboBox::drop-down {{
        subcontrol-origin: padding;
        subcontrol-position: center right;
        width: 30px;
        border: none;
        background: transparent;
    }}
    /* 弹出层容器：圆角 + 细边 + 内边距，去掉复古的方框感 */
    QComboBox QAbstractItemView {{
        background: {C['surface']};
        border: 1px solid {C['border']};
        border-radius: 10px;
        outline: 0;                         /* 去掉键盘聚焦的矩形描边 */
        padding: 6px;                       /* 列表与边框的呼吸空间 */
        selection-background-color: {C['brand']};
        selection-color: #FFFFFF;
    }}
    /* 单个选项：舒适的行高与内边距，圆角行背景 */
    QComboBox QAbstractItemView::item {{
        background: transparent;
        color: {C['text']};
        padding: 9px 12px;
        min-height: 20px;
        border-radius: 6px;
    }}
    /* 鼠标悬停：中性浅底，与“已选中”形成层次区分 */
    QComboBox QAbstractItemView::item:hover {{
        background: {C['surface_2']};
        color: {C['text']};
    }}
    QDateEdit::drop-calendar {{
        background: {C['surface']};
    }}
    QCalendarWidget QTableView {{
        selection-background-color: {C['brand']};
        selection-color: #FFFFFF;
    }}

    /* ===================== 卡片 ===================== */
    QFrame#card {{
        background: {C['surface']};
        border: 1px solid {C['border']};
        border-radius: 12px;
    }}

    /* ===================== 表格 ===================== */
    QTableWidget {{
        background: {C['surface']};
        border: 1px solid {C['border']};
        border-radius: 10px;
        gridline-color: {C['border']};
        selection-background-color: {C['brand_tint']};
        selection-color: {C['text']};
    }}
    QTableWidget::item {{
        padding: 8px 10px;
        border: none;
    }}
    QTableWidget::item:selected {{
        background: {C['brand_tint']};
        color: {C['text']};
    }}
    QHeaderView::section {{
        background: {C['surface_2']};
        color: {C['text_2']};
        border: none;
        border-bottom: 1px solid {C['border']};
        padding: 10px 10px;
        font-weight: 600;
        font-size: 12px;
    }}
    QTableWidget::item:hover {{
        background: {C['brand_tint']};
    }}

    /* ===================== 标签页 ===================== */
    QTabWidget::pane {{
        border: 1px solid {C['border']};
        border-radius: 10px;
        background: {C['surface']};
        top: 6px;
    }}
    QTabBar::tab {{
        background: {C['surface_2']};
        border: 1px solid {C['border']};
        border-bottom: none;
        border-top-left-radius: 8px;
        border-top-right-radius: 8px;
        padding: 8px 18px;
        margin-right: 4px;
        color: {C['text_2']};
    }}
    QTabBar::tab:selected {{
        background: {C['surface']};
        color: {C['brand']};
        border-bottom: 2px solid {C['brand']};
        font-weight: 600;
    }}
    QTabBar::tab:hover {{
        color: {C['text']};
    }}

    /* ===================== 分组框 ===================== */
    QGroupBox {{
        background: {C['surface']};
        border: 1px solid {C['border']};
        border-radius: 10px;
        margin-top: 14px;
        padding: 14px 14px 12px;
        font-weight: 600;
        color: {C['text']};
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        left: 14px;
        padding: 0 6px;
        color: {C['text_2']};
        background: {C['surface']};
    }}

    /* ===================== 滚动区 ===================== */
    QScrollArea {{
        border: none;
        background: transparent;
    }}
    QScrollBar:vertical {{
        background: transparent;
        width: 10px;
        margin: 2px;
    }}
    QScrollBar::handle:vertical {{
        background: {C['border_2']};
        border-radius: 5px;
    }}
    QScrollBar::handle:vertical:hover {{
        background: {C['text_3']};
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0;
    }}

    /* ===================== 进度条 ===================== */
    QProgressBar {{
        border: 1px solid {C['border']};
        border-radius: 6px;
        background: {C['surface_2']};
        text-align: center;
        color: {C['text_2']};
        height: 14px;
    }}
    QProgressBar::chunk {{
        background: {GRADIENT};
        border-radius: 5px;
    }}

    /* ===================== 复选 / 单选 ===================== */
    QCheckBox::indicator, QRadioButton::indicator {{
        width: 16px;
        height: 16px;
    }}
    QCheckBox::indicator:checked, QRadioButton::indicator:checked {{
        background: {C['brand']};
        border: 1px solid {C['brand']};
        border-radius: 4px;
    }}

    /* ===================== 列表 ===================== */
    QListWidget {{
        background: {C['surface']};
        border: 1px solid {C['border']};
        border-radius: 10px;
        padding: 4px;
    }}
    QListWidget::item {{
        padding: 6px 8px;
        border-radius: 6px;
    }}
    QListWidget::item:selected {{
        background: {C['brand_tint']};
        color: {C['brand']};
    }}

    /* ===================== 对话框按钮盒 ===================== */
    QDialogButtonBox QPushButton {{
        min-width: 78px;
    }}

    /* ===================== 状态栏 ===================== */
    QStatusBar {{
        background: {C['surface']};
        border-top: 1px solid {C['border']};
        color: {C['text_2']};
        padding: 4px 10px;
    }}
    QStatusBar::item {{ border: none; }}

    /* ===================== 分隔线 ===================== */
    QFrame#sep {{
        background: {C['border']};
        max-height: 1px;
    }}
    """


# ---------------------------------------------------------------------------
# 主题应用
# ---------------------------------------------------------------------------
def apply_theme(app: QApplication):
    app.setStyle("Fusion")
    app.setFont(QFont(FONT_STACK, 10))
    app.setStyleSheet(stylesheet())

    # 调色板微调（确保 Fusion 下颜色一致）
    from PySide6.QtGui import QPalette
    pal = app.palette()
    pal.setColor(QPalette.Window, QColor(C["bg"]))
    pal.setColor(QPalette.WindowText, QColor(C["text"]))
    pal.setColor(QPalette.Base, QColor(C["surface"]))
    pal.setColor(QPalette.AlternateBase, QColor(C["surface_2"]))
    pal.setColor(QPalette.Text, QColor(C["text"]))
    pal.setColor(QPalette.Button, QColor(C["surface"]))
    pal.setColor(QPalette.ButtonText, QColor(C["text"]))
    pal.setColor(QPalette.Highlight, QColor(C["brand"]))
    pal.setColor(QPalette.HighlightedText, QColor("#FFFFFF"))
    pal.setColor(QPalette.Link, QColor(C["brand"]))
    app.setPalette(pal)


def chart_rcparams():
    """返回 matplotlib rcParams 字典（供 dashboard 统一图表风格）。"""
    return {
        # 注意：matplotlib 读取 .ttc 字体集合时仅注册首个字形面（多为 JP），
        # 故显式列入 Noto Sans CJK JP 以保证 Linux 环境下中文可正常渲染。
        "font.sans-serif": ["Microsoft YaHei", "PingFang SC", "Noto Sans CJK SC",
                            "Noto Sans CJK JP", "WenQuanYi Micro Hei",
                            "Arial Unicode MS", "sans-serif"],
        "axes.unicode_minus": False,
        "figure.facecolor": "white",
        "axes.facecolor": "white",
        "savefig.facecolor": "white",
        "axes.edgecolor": C["border"],
        "axes.labelcolor": C["text_2"],
        "text.color": C["text_2"],
        "xtick.color": C["text_3"],
        "ytick.color": C["text_3"],
        "axes.titlesize": 12,
        "axes.titleweight": "bold",
        "font.size": 11,
    }


def status_color(status: str) -> str:
    return STATUS_COLORS.get(status, C["text_3"])
