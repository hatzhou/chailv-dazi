# -*- coding: utf-8 -*-
"""差旅搭子 - 仪表盘：统计卡片 + 分类/月度图表 + 行程汇总。"""
from __future__ import annotations

import matplotlib
matplotlib.use("QtAgg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
                               QLabel, QScrollArea, QFrame)
from PySide6.QtCore import Qt

from db.database import InvoiceDB
from ui.widgets import Card, fmt_money, fmt_money_short, empty_hint
from ui.theme import CHART_COLORS, chart_rcparams, C, status_color
from ui.icons import icon as _icon

plt.rcParams.update(chart_rcparams())


class Dashboard(QWidget):
    def __init__(self, db: InvoiceDB):
        super().__init__()
        self.db = db
        self._build()
        self.refresh()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 18, 20, 18)
        root.setSpacing(16)

        # 顶部卡片（带图标与主色点缀）
        self.card_total = Card("发票总数", "0", "张", C["brand"], "receipt")
        self.card_amount = Card("发票总金额", "¥0", "价税合计", "#16A34A", "banknote")
        self.card_pending = Card("待报销金额", "¥0", "待提交/待审批", "#F59E0B", "clock")
        self.card_reimb = Card("已报销金额", "¥0", "已到账", "#2563EB", "check")
        grid = QGridLayout()
        grid.setSpacing(14)
        for i, c in enumerate([self.card_total, self.card_amount,
                               self.card_pending, self.card_reimb]):
            grid.addWidget(c, 0, i)
        root.addLayout(grid)

        # 图表区
        charts = QHBoxLayout()
        charts.setSpacing(14)
        self.cat_canvas = FigureCanvas(plt.Figure(figsize=(4.2, 3.2)))
        self.trend_canvas = FigureCanvas(plt.Figure(figsize=(4.2, 3.2)))
        charts.addWidget(self._wrap(self.cat_canvas, "分类金额占比"))
        charts.addWidget(self._wrap(self.trend_canvas, "近 12 个月趋势"))
        root.addLayout(charts)

        # 行程汇总
        self.trip_area = QVBoxLayout()
        self.trip_area.setSpacing(0)
        trip_frame = QFrame()
        trip_frame.setLayout(self.trip_area)
        sa = QScrollArea()
        sa.setWidgetResizable(True)
        sa.setWidget(trip_frame)
        sa.setFrameShape(QFrame.NoFrame)
        root.addWidget(sa, 1)

    def _wrap(self, canvas, title):
        w = QFrame()
        w.setObjectName("card")
        v = QVBoxLayout(w)
        v.setContentsMargins(14, 12, 14, 12)
        t = QLabel(title)
        t.setStyleSheet(f"color:{C['text']};font-weight:700;font-size:14px;")
        v.addWidget(t)
        v.addWidget(canvas, 1)
        return w

    def refresh(self):
        s = self.db.stats_summary()
        self.card_total.value_label.setText(str(s["total_count"]))
        self.card_amount.value_label.setText(fmt_money(s["total_amount"]))
        self.card_pending.value_label.setText(fmt_money(s["pending_amount"]))
        self.card_reimb.value_label.setText(fmt_money(s["reimbursed_amount"]))

        self._draw_category()
        self._draw_trend()
        self._draw_trips()

    def _draw_category(self):
        fig = self.cat_canvas.figure
        fig.clf()
        ax = fig.add_subplot(111)
        rows = [r for r in self.db.stats_by_category() if r["total"] > 0]
        if not rows:
            ax.text(0.5, 0.5, "暂无数据", ha="center", va="center",
                    color=C["text_3"], fontsize=12)
        else:
            labels = [f"{r['icon']} {r['name']}" for r in rows]
            vals = [r["total"] for r in rows]
            colors = [CHART_COLORS[i % len(CHART_COLORS)] for i in range(len(rows))]
            y = range(len(rows))
            ax.barh(list(y), vals, color=colors, height=0.62, zorder=2)
            ax.set_yticks(list(y))
            ax.set_yticklabels(labels)
            ax.invert_yaxis()
            ax.set_xlabel("金额")
            ax.grid(axis="x", color=C["border"], linewidth=0.8, zorder=0)
            ax.set_axisbelow(True)
            for spine in ["top", "right"]:
                ax.spines[spine].set_visible(False)
            for i, v in enumerate(vals):
                ax.text(v, i, "  " + fmt_money_short(v), va="center", fontsize=9)
        ax.set_title("")
        fig.tight_layout()
        self.cat_canvas.draw()

    def _draw_trend(self):
        fig = self.trend_canvas.figure
        fig.clf()
        ax = fig.add_subplot(111)
        rows = self.db.stats_monthly(12)
        if not rows:
            ax.text(0.5, 0.5, "暂无数据", ha="center", va="center",
                    color=C["text_3"], fontsize=12)
        else:
            months = [r["month"][2:] for r in rows]
            vals = [r["total"] for r in rows]
            bars = ax.bar(months, vals, color=C["brand"], width=0.6,
                          zorder=2, edgecolor="white", linewidth=0.6)
            ax.set_ylabel("金额")
            ax.tick_params(axis="x", rotation=45, labelsize=8)
            ax.grid(axis="y", color=C["border"], linewidth=0.8, zorder=0)
            ax.set_axisbelow(True)
            for spine in ["top", "right"]:
                ax.spines[spine].set_visible(False)
            for b, v in zip(bars, vals):
                ax.text(b.get_x() + b.get_width() / 2, v,
                        fmt_money_short(v), ha="center", va="bottom", fontsize=8)
        fig.tight_layout()
        self.trend_canvas.draw()

    def _draw_trips(self):
        while self.trip_area.count():
            item = self.trip_area.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
        rows = self.db.stats_by_trip()
        if not rows:
            self.trip_area.addWidget(empty_hint("还没有行程，点击「新建行程」开始归集发票"))
            return
        title = QLabel("行程报销汇总")
        title.setStyleSheet(f"color:{C['text']};font-weight:700;font-size:14px;padding-bottom:6px;")
        self.trip_area.addWidget(title)
        for r in rows:
            line = QFrame()
            line.setFrameShape(QFrame.HLine)
            line.setStyleSheet(f"color:{C['border']};")
            row = QHBoxLayout()
            row.setContentsMargins(0, 8, 0, 8)
            chip = QLabel()
            chip.setFixedSize(28, 28)
            chip.setAlignment(Qt.AlignCenter)
            chip.setStyleSheet(f"background:{C['brand_tint']};border-radius:8px;")
            chip.setPixmap(_icon("map", C["brand"], 16).pixmap(16, 16))
            name = QLabel(f"{r['name']}")
            name.setStyleSheet("font-weight:600;font-size:13px;")
            amt = QLabel(fmt_money(r["total"]))
            amt.setStyleSheet(f"color:#16A34A;font-weight:700;font-size:13px;")
            cnt = QLabel(f"{r['cnt']} 张")
            cnt.setStyleSheet(f"color:{C['text_3']};font-size:12px;")
            budget = QLabel(f"预算 {fmt_money(r['budget'])}" if r["budget"] else "")
            budget.setStyleSheet(f"color:{C['text_3']};font-size:12px;")
            row.addWidget(chip)
            row.addWidget(name)
            row.addStretch(1)
            row.addWidget(cnt)
            row.addWidget(budget)
            row.addWidget(amt)
            box = QFrame()
            box.setLayout(row)
            self.trip_area.addWidget(box)
            self.trip_area.addWidget(line)
        self.trip_area.addStretch(1)
