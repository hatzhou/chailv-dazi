# -*- coding: utf-8 -*-
"""差旅搭子 - UI 公共组件与工具函数。"""
from __future__ import annotations

from typing import List
from PySide6.QtWidgets import QComboBox, QCompleter
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont

import config
from db.database import InvoiceDB
from db.models import Category


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

STATUS_COLORS = {
    "draft": "#9e9e9e",
    "pending": "#1976d2",
    "submitted": "#f57c00",
    "reimbursed": "#388e3c",
    "rejected": "#d32f2f",
}


def status_label(status: str) -> str:
    return STATUS_LABELS.get(status, status)


def status_color(status: str) -> QColor:
    return QColor(STATUS_COLORS.get(status, "#9e9e9e"))


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


from PySide6.QtWidgets import QLabel, QVBoxLayout, QFrame


class Card(QFrame):
    """统计卡片：标题 + 大号数值 + 可选副标题。"""

    def __init__(self, title: str, value: str, sub: str = "", color: str = "#1976d2"):
        super().__init__()
        self.setFrameShape(QFrame.StyledPanel)
        self.setLineWidth(0)
        self.setStyleSheet(
            f"Card{{background:#fff;border-radius:10px;border:1px solid #eaeaea;}}"
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(4)
        t = QLabel(title)
        t.setStyleSheet("color:#888;font-size:12px;")
        v = QLabel(value)
        v.setStyleSheet(f"color:{color};font-size:22px;font-weight:bold;")
        self.value_label = v
        layout.addWidget(t)
        layout.addWidget(v)
        if sub:
            s = QLabel(sub)
            s.setStyleSheet("color:#aaa;font-size:11px;")
            layout.addWidget(s)


def empty_hint(text: str) -> QLabel:
    lab = QLabel(text)
    lab.setAlignment(Qt.AlignCenter)
    lab.setStyleSheet("color:#bbb;padding:30px;font-size:13px;")
    return lab
