# -*- coding: utf-8 -*-
"""差旅搭子 - UI 公共组件与工具函数。"""
from __future__ import annotations

from typing import List
from PySide6.QtWidgets import (QComboBox, QLabel, QVBoxLayout, QHBoxLayout,
                               QFrame, QPushButton, QWidget, QSizePolicy)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QColor, QFont, QIcon

import config
from db.database import InvoiceDB
from db.models import Category

from ui.theme import C, status_color as _status_color
from ui.icons import icon as _icon


def fmt_money(x) -> str:
    try:
        return f"¥{float(x):,.2f}"
    except Exception:
        return "¥0.00"


def fmt_money_short(x) -> str:
    try:
        v = float(x)
        if v >= 10000:
            return f"¥{v/10000:.1f}万"
        return f"¥{v:,.0f}"
    except Exception:
        return "¥0"


STATUS_LABELS = dict(config.INVOICE_STATUS)
STATUS_ORDER = [k for k, _ in config.INVOICE_STATUS]


def status_label(status: str) -> str:
    return STATUS_LABELS.get(status, status)


def status_color(status: str) -> QColor:
    return QColor(_status_color(status))


def fill_category_combo(combo: QComboBox, categories: List[Category],
                        include_all: bool = False, all_text: str = "全部分类"):
    combo.clear()
    if include_all:
        combo.addItem(all_text, None)
    for c in categories:
        combo.addItem(f"{c.icon} {c.name}", c.id)


def fill_trip_combo(combo: QComboBox, trips, include_all: bool = False,
                    include_none: bool = False, all_text: str = "全部行程",
                    none_text: str = "未归集行程"):
    combo.clear()
    if include_all:
        combo.addItem(all_text, None)
    if include_none:
        combo.addItem(none_text, -1)
    for t in trips:
        combo.addItem(f"{t.name} ({t.date_range})", t.id)


def fill_status_combo(combo: QComboBox, include_all: bool = False,
                      all_text: str = "全部状态"):
    combo.clear()
    if include_all:
        combo.addItem(all_text, None)
    for k, v in config.INVOICE_STATUS:
        combo.addItem(v, k)


def make_bold(font: QFont, size: int = None) -> QFont:
    f = QFont(font)
    f.setBold(True)
    if size:
        f.setPointSize(size)
    return f


def primary_button(text: str, parent=None) -> QPushButton:
    b = QPushButton(text, parent)
    b.setObjectName("primary")
    return b


def icon_chip(icon_name: str, color: str = C["brand"], size: int = 18,
              chip: int = 34) -> QLabel:
    """圆形 / 圆角方块图标chip，带主色浅底。"""
    lab = QLabel()
    lab.setFixedSize(chip, chip)
    lab.setAlignment(Qt.AlignCenter)
    tint = QColor(color)
    bg = f"rgba({tint.red()},{tint.green()},{tint.blue()},45)"
    lab.setStyleSheet(
        f"background:{bg};border-radius:{chip//2}px;"
    )
    px = _icon(icon_name, color, size).pixmap(QSize(size, size))
    lab.setPixmap(px)
    return lab


# ---------------------------------------------------------------------------
# 统计卡片（支持图标 + 主色点缀）
# ---------------------------------------------------------------------------
class Card(QFrame):
    """统计卡片：标题 + 大号数值 + 可选副标题 + 可选图标。"""

    def __init__(self, title: str, value: str, sub: str = "", color: str = C["brand"],
                 icon_name: str = None):
        super().__init__()
        self.setObjectName("card")
        self.setFrameShape(QFrame.StyledPanel)
        self.setLineWidth(0)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(6)

        top = QHBoxLayout()
        t = QLabel(title)
        t.setStyleSheet(f"color:{C['text_2']};font-size:12px;font-weight:600;")
        top.addWidget(t)
        top.addStretch(1)
        if icon_name:
            top.addWidget(icon_chip(icon_name, color, 18, 32))
        layout.addLayout(top)

        v = QLabel(value)
        v.setStyleSheet(f"color:{color};font-size:24px;font-weight:700;")
        self.value_label = v
        layout.addWidget(v)

        if sub:
            s = QLabel(sub)
            s.setStyleSheet(f"color:{C['text_3']};font-size:11px;")
            layout.addWidget(s)


def empty_hint(text: str) -> QLabel:
    lab = QLabel(text)
    lab.setAlignment(Qt.AlignCenter)
    lab.setStyleSheet(f"color:{C['text_3']};padding:30px;font-size:13px;")
    return lab


class EmptyState(QWidget):
    """空状态：大图标 + 标题 + 说明 + 可选操作按钮。"""

    def __init__(self, icon_name: str = "inbox", title: str = "暂无数据",
                 subtitle: str = "", action_text: str = None,
                 on_action=None, parent=None):
        super().__init__(parent)
        v = QVBoxLayout(self)
        v.setAlignment(Qt.AlignCenter)
        v.setSpacing(10)
        v.addStretch(1)

        ico = QLabel()
        px = _icon(icon_name, C["text_3"], 56).pixmap(QSize(56, 56))
        ico.setPixmap(px)
        ico.setAlignment(Qt.AlignCenter)
        v.addWidget(ico)

        tt = QLabel(title)
        tt.setStyleSheet(f"color:{C['text_2']};font-size:15px;font-weight:600;")
        tt.setAlignment(Qt.AlignCenter)
        v.addWidget(tt)

        if subtitle:
            st = QLabel(subtitle)
            st.setStyleSheet(f"color:{C['text_3']};font-size:12px;")
            st.setAlignment(Qt.AlignCenter)
            st.setWordWrap(True)
            v.addWidget(st)

        if action_text:
            btn = QPushButton(action_text)
            btn.setObjectName("primary")
            if on_action:
                btn.clicked.connect(on_action)
            h = QHBoxLayout()
            h.addStretch(1)
            h.addWidget(btn)
            h.addStretch(1)
            v.addLayout(h)

        v.addStretch(1)


class StatusBadge(QLabel):
    """彩色状态药丸（用于表格状态列）。"""

    def __init__(self, status: str = "", label: str = "", parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignCenter)
        self.set_status(status, label)

    def set_status(self, status: str, label: str = None):
        color = _status_color(status)
        txt = label if label is not None else status_label(status)
        self.setText(f" {txt} ")
        qc = QColor(color)
        tint = QColor(color)
        tint.setAlpha(26)
        self.setStyleSheet(
            f"background:{tint.name()};color:{color};"
            f"border-radius:10px;padding:3px 10px;font-size:12px;font-weight:600;"
        )
        self.adjustSize()


class NavButton(QPushButton):
    """侧边栏导航项：图标 + 文字，支持激活态（双色图标 + 主色高亮）。"""

    def __init__(self, icon_name: str, text: str, parent=None):
        super().__init__(parent)
        self._icon_name = icon_name
        self._text = text
        self.setObjectName("navBtn")
        self.setText(f"  {text}")
        self.setIcon(_icon(icon_name, C["text_2"], 20))
        self.setIconSize(QSize(20, 20))
        self.setCursor(Qt.PointingHandCursor)
        self.setCheckable(True)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        self.setProperty("active", False)

    def set_active(self, on: bool):
        self.setProperty("active", on)
        color = C["brand"] if on else C["text_2"]
        self.setIcon(_icon(self._icon_name, color, 20))
        # 触发样式刷新
        self.style().unpolish(self)
        self.style().polish(self)
