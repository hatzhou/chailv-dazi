# -*- coding: utf-8 -*-
"""差旅搭子 - 自定义现代日期选择器（替代原生 QDateEdit / QCalendarWidget）。

原生 QCalendarWidget 的样式在很多平台/主题下改不彻底、易走样，故用代码
完全自绘：圆角输入框 + 弹出式月历，日格为像素级绘制（今天描边、选中填充、
悬停浅底），与蓝青设计系统一致。对外暴露与 QDateEdit 对齐的接口：
date() / setDate() / setDisplayFormat() / dateChanged 信号。
"""
from __future__ import annotations

from PySide6.QtWidgets import (QWidget, QLabel, QHBoxLayout, QVBoxLayout,
                               QFrame, QPushButton, QGridLayout)
from PySide6.QtCore import Qt, QDate, QRectF, Signal
from PySide6.QtGui import QPainter, QColor, QPen, QFont

from ui.theme import C
from ui.icons import pixmap as _pixmap


_WEEKDAYS = ["一", "二", "三", "四", "五", "六", "日"]


class _CalDayButton(QPushButton):
    """自绘的单个日期格。"""

    def __init__(self, date: QDate, parent=None):
        super().__init__(parent)
        self._date = date
        self._other = False     # 是否属相邻月份
        self._today = False
        self._selected = False
        self._hover = False
        self.setMinimumSize(34, 34)
        self.setCursor(Qt.PointingHandCursor)
        self.setText(str(date.day()))

    def set_states(self, other: bool, today: bool, selected: bool):
        self._other = other
        self._today = today
        self._selected = selected
        self.update()

    def enterEvent(self, e):
        self._hover = True
        self.update()
        super().enterEvent(e)

    def leaveEvent(self, e):
        self._hover = False
        self.update()
        super().leaveEvent(e)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        rect = self.rect()
        inset = 3
        r = QRectF(rect.x() + inset, rect.y() + inset,
                   rect.width() - 2 * inset, rect.height() - 2 * inset)

        # 背景
        if self._selected:
            bg = QColor(C["brand"])
        elif self._today:
            bg = QColor(C["brand_tint"])
        elif self._hover:
            bg = QColor(C["surface_2"])
        else:
            bg = QColor(0, 0, 0, 0)
        if bg.alpha() > 0:
            p.setPen(Qt.NoPen)
            p.setBrush(bg)
            p.drawRoundedRect(r, 8, 8)

        # 今天描边
        if self._today and not self._selected:
            p.setPen(QPen(QColor(C["brand"]), 1.2))
            p.setBrush(Qt.NoBrush)
            p.drawRoundedRect(r, 8, 8)

        # 文字颜色
        if self._selected:
            fg = QColor("#FFFFFF")
        elif self._today:
            fg = QColor(C["brand"])
        elif self._other:
            fg = QColor(C["text_3"])
        else:
            fg = QColor(C["text"])
        p.setPen(fg)
        p.setFont(self.font())
        p.drawText(rect, Qt.AlignCenter, str(self._date.day()))


class _CalendarPopup(QFrame):
    """弹出式月历。"""

    dateSelected = Signal(QDate)

    def __init__(self, current: QDate, parent=None):
        super().__init__(parent, Qt.Popup)
        self._shown = QDate(current.year(), current.month(), 1)
        self._sel = current
        self._today = QDate.currentDate()
        self._day_buttons = []
        self.setObjectName("calPopup")
        self.setStyleSheet(f"""
            QFrame#calPopup {{
                background: {C['surface']};
                border: 1px solid {C['border']};
                border-radius: 14px;
            }}
        """)
        self._build_ui()
        self._render()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        # 顶部：上一月 / 标题 / 下一月
        head = QHBoxLayout()
        head.setSpacing(6)
        prev = QPushButton("‹")
        prev.setFixedSize(32, 32)
        prev.setCursor(Qt.PointingHandCursor)
        prev.setStyleSheet(self._nav_style())
        prev.clicked.connect(lambda: self._step(-1))
        self._title = QLabel()
        self._title.setAlignment(Qt.AlignCenter)
        self._title.setStyleSheet(f"color:{C['text']};font-weight:700;"
                                  f"font-size:14px;")
        nxt = QPushButton("›")
        nxt.setFixedSize(32, 32)
        nxt.setCursor(Qt.PointingHandCursor)
        nxt.setStyleSheet(self._nav_style())
        nxt.clicked.connect(lambda: self._step(1))
        head.addWidget(prev)
        head.addWidget(self._title, 1)
        head.addWidget(nxt)
        root.addLayout(head)

        # 星期表头
        wd = QHBoxLayout()
        wd.setSpacing(2)
        for w in _WEEKDAYS:
            lab = QLabel(w)
            lab.setAlignment(Qt.AlignCenter)
            lab.setStyleSheet(f"color:{C['text_3']};font-size:12px;")
            wd.addWidget(lab)
        root.addLayout(wd)

        # 日期网格
        grid = QGridLayout()
        grid.setSpacing(2)
        grid.setHorizontalSpacing(2)
        grid.setVerticalSpacing(2)
        for r in range(6):
            for c in range(7):
                b = _CalDayButton(QDate())
                b.clicked.connect(lambda _=False, btn=b: self._pick(btn))
                self._day_buttons.append(b)
                grid.addWidget(b, r, c)
        root.addLayout(grid)

        # 底部：今天
        foot = QHBoxLayout()
        foot.addStretch(1)
        today_btn = QPushButton("  今天  ")
        today_btn.setCursor(Qt.PointingHandCursor)
        today_btn.setStyleSheet(f"""
            QPushButton {{
                background: {C['brand_tint']};
                color: {C['brand']};
                border: none;
                border-radius: 8px;
                padding: 6px 14px;
                font-weight: 600;
            }}
            QPushButton:hover {{ background: {C['brand']}; color:#FFFFFF; }}
        """)
        today_btn.clicked.connect(lambda: self._pick_date(self._today))
        foot.addWidget(today_btn)
        root.addLayout(foot)

        self.setFixedWidth(296)

    def _nav_style(self):
        return f"""
            QPushButton {{
                background: transparent;
                border: none;
                border-radius: 8px;
                color: {C['text_2']};
                font-size: 18px;
            }}
            QPushButton:hover {{ background: {C['brand_tint']}; color: {C['brand']}; }}
        """

    def _step(self, delta: int):
        m = self._shown.month() + delta
        y = self._shown.year()
        if m < 1:
            m = 12
            y -= 1
        elif m > 12:
            m = 1
            y += 1
        self._shown = QDate(y, m, 1)
        self._render()

    def _pick(self, btn: _CalDayButton):
        self._pick_date(btn._date)

    def _pick_date(self, d: QDate):
        self._sel = d
        self.dateSelected.emit(d)
        self.close()

    def _render(self):
        self._title.setText(f"{self._shown.year()}年{self._shown.month()}月")
        first = QDate(self._shown.year(), self._shown.month(), 1)
        # 周一为起始列
        start_col = (first.dayOfWeek() - 1) % 7
        cur = first.addDays(-start_col)
        for b in self._day_buttons:
            b._date = cur
            b.setText(str(cur.day()))
            other = (cur.month() != self._shown.month())
            today = (cur == self._today)
            selected = (cur == self._sel)
            b.set_states(other, today, selected)
            cur = cur.addDays(1)


class DatePicker(QWidget):
    """现代日期选择框，接口对齐 QDateEdit。"""

    dateChanged = Signal(QDate)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._date = QDate.currentDate()
        self._fmt = "yyyy-MM-dd"
        self._popup = None
        self.setObjectName("datePicker")
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(34)
        self._build_ui()
        self._render()

    def _build_ui(self):
        lay = QHBoxLayout(self)
        lay.setContentsMargins(10, 0, 8, 0)
        lay.setSpacing(6)
        self._text = QLabel()
        self._text.setStyleSheet(f"color:{C['text']};font-size:13px;")
        self._icon = QLabel()
        self._icon.setPixmap(_pixmap("calendar", C["text_3"], 16))
        lay.addWidget(self._text, 1)
        lay.addWidget(self._icon)
        self.setStyleSheet(f"""
            QWidget#datePicker {{
                background: {C['surface']};
                border: 1px solid {C['border']};
                border-radius: 8px;
            }}
            QWidget#datePicker:hover {{ border-color: {C['border_2']}; }}
        """)

    def _render(self):
        self._text.setText(self._date.toString(self._fmt))

    # ---- 对外的 QDateEdit 兼容接口 ----
    def date(self) -> QDate:
        return self._date

    def setDate(self, d: QDate):
        if d != self._date:
            self._date = d
            self._render()

    def setDisplayFormat(self, fmt: str):
        self._fmt = fmt or "yyyy-MM-dd"
        self._render()

    def mousePressEvent(self, e):
        self._toggle_popup()
        super().mousePressEvent(e)

    def _toggle_popup(self):
        if self._popup and self._popup.isVisible():
            self._popup.close()
            return
        self._popup = _CalendarPopup(self._date, self)
        self._popup.dateSelected.connect(self._on_selected)
        gp = self.mapToGlobal(self.rect().bottomLeft())
        screen = self.screen()
        # 若下方空间不足则上移到字段上方（无屏幕信息时跳过判断）
        if screen is not None:
            bottom = screen.geometry().bottom()
            if gp.y() + self._popup.height() > bottom:
                gp = self.mapToGlobal(self.rect().topLeft())
                gp.setY(gp.y() - self._popup.height())
        self._popup.move(gp)
        self._popup.show()

    def _on_selected(self, d: QDate):
        self._date = d
        self._render()
        self.dateChanged.emit(d)
