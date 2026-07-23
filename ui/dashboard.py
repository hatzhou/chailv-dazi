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

# 适配中文显示（在具备 CJK 字体的系统上生效）
plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei", "PingFang SC",
                                   "Noto Sans CJK SC", "WenQuanYi Micro Hei",
                                   "Arial Unicode MS", "sans-serif"]
plt.rcParams["axes.unicode_minus"] = False


class Dashboard(QWidget):
    def __init__(self, db: InvoiceDB):
        super().__init__()
        self.db = db
        self._build()
        self.refresh()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(14)

        # 顶部卡片
        self.card_total = Card("发票总数", "0", "")
        self.card_amount = Card("发票总金额", "¥0", "", "#2e7d32")
        self.card_pending = Card("待报销金额", "¥0", "", "#f57c00")
        self.card_reimb = Card("已报销金额", "¥0", "", "#1565c0")
        grid = QGridLayout()
        grid.setSpacing(12)
        for i, c in enumerate([self.card_total, self.card_amount,
                               self.card_pending, self.card_reimb]):
            grid.addWidget(c, 0, i)
        root.addLayout(grid)

        # 图表区
        charts = QHBoxLayout()
        charts.setSpacing(12)
        self.cat_canvas = FigureCanvas(plt.Figure(figsize=(4, 3)))
        self.trend_canvas = FigureCanvas(plt.Figure(figsize=(4, 3)))
        charts.addWidget(self._wrap(self.cat_canvas, "分类金额占比"))
        charts.addWidget(self._wrap(self.trend_canvas, "近 12 个月趋势"))
        root.addLayout(charts)

        # 行程汇总
        self.trip_area = QVBoxLayout()
        trip_frame = QFrame()
        trip_frame.setLayout(self.trip_area)
        sa = QScrollArea()
        sa.setWidgetResizable(True)
        sa.setWidget(trip_frame)
        sa.setFrameShape(QFrame.NoFrame)
        root.addWidget(sa, 1)

    def _wrap(self, canvas, title):
        w = QFrame()
        w.setStyleSheet("background:#fff;border-radius:10px;border:1px solid #eaeaea;")
        v = QVBoxLayout(w)
        v.setContentsMargins(10, 8, 10, 8)
        t = QLabel(title)
        t.setStyleSheet("color:#555;font-weight:bold;font-size:13px;")
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
            ax.text(0.5, 0.5, "暂无数据", ha="center", va="center", color="#bbb")
        else:
            labels = [f"{r['icon']} {r['name']}" for r in rows]
            vals = [r["total"] for r in rows]
            ax.barh(labels[::-1], vals[::-1], color="#42a5f5")
            ax.set_xlabel("金额")
            for i, v in enumerate(vals[::-1]):
                ax.text(v, i, " " + fmt_money_short(v), va="center", fontsize=9)
        ax.set_title("")
        fig.tight_layout()
        self.cat_canvas.draw()

    def _draw_trend(self):
        fig = self.trend_canvas.figure
        fig.clf()
        ax = fig.add_subplot(111)
        rows = self.db.stats_monthly(12)
        if not rows:
            ax.text(0.5, 0.5, "暂无数据", ha="center", va="center", color="#bbb")
        else:
            months = [r["month"][2:] for r in rows]
            vals = [r["total"] for r in rows]
            ax.bar(months, vals, color="#66bb6a")
            ax.set_ylabel("金额")
            ax.tick_params(axis="x", rotation=45, labelsize=8)
        fig.tight_layout()
        self.trend_canvas.draw()

    def _draw_trips(self):
        # 清空
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
        title.setStyleSheet("color:#555;font-weight:bold;font-size:13px;")
        self.trip_area.addWidget(title)
        for r in rows:
            line = QFrame()
            line.setFrameShape(QFrame.HLine)
            line.setStyleSheet("color:#eee;")
            row = QHBoxLayout()
            row.setContentsMargins(0, 6, 0, 6)
            name = QLabel(f"✈ {r['name']}")
            name.setStyleSheet("font-weight:bold;")
            amt = QLabel(fmt_money(r["total"]))
            amt.setStyleSheet("color:#2e7d32;font-weight:bold;")
            cnt = QLabel(f"{r['cnt']} 张")
            cnt.setStyleSheet("color:#999;")
            budget = QLabel(f"预算 {fmt_money(r['budget'])}" if r["budget"] else "")
            budget.setStyleSheet("color:#999;")
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
