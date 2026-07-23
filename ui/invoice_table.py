# -*- coding: utf-8 -*-
"""差旅搭子 - 发票列表页：筛选 + 表格 + 增删改。"""
from __future__ import annotations

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget,
                               QTableWidgetItem, QLineEdit, QPushButton, QComboBox,
                               QLabel, QHeaderView, QMessageBox, QFrame,
                               QStackedWidget)
from PySide6.QtCore import Qt, Signal, QDate
from PySide6.QtGui import QColor

from db.database import InvoiceDB
from db.models import Invoice
from ui.widgets import (fill_category_combo, fill_trip_combo, fill_status_combo,
                        fmt_money, status_label, status_color, StatusBadge,
                        EmptyState, primary_button)
from ui.date_picker import DatePicker
from ui.icons import icon as _icon

COLUMNS = ["状态", "发票号码", "分类", "金额", "税额", "开票日期",
           "销售方", "行程", "来源"]


class InvoiceList(QWidget):
    open_requested = Signal(int)   # 双击打开详情
    changed = Signal()             # 数据变更后通知（刷新仪表盘等）
    import_requested = Signal()    # 空状态引导导入

    def __init__(self, db: InvoiceDB):
        super().__init__()
        self.db = db
        self._build()
        self.refresh()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 16, 20, 16)
        root.setSpacing(12)

        # 筛选栏
        fbar = QHBoxLayout()
        fbar.setSpacing(8)
        self.search = QLineEdit()
        self.search.setPlaceholderText("搜索发票号 / 税号 / 销售方 / 备注")
        self.search.returnPressed.connect(self.refresh)
        self.cat = QComboBox()
        self.trip = QComboBox()
        self.status = QComboBox()
        self.date_from = DatePicker()
        self.date_from.setDisplayFormat("yyyy-MM-dd")
        self.date_from.setDate(QDate(2000, 1, 1))
        self.date_to = DatePicker()
        self.date_to.setDisplayFormat("yyyy-MM-dd")
        self.date_to.setDate(QDate.currentDate())
        btn_filter = QPushButton(" 筛选")
        btn_filter.setIcon(_icon("filter", "#475569", 16))
        btn_filter.clicked.connect(self.refresh)
        btn_reset = QPushButton(" 重置")
        btn_reset.setIcon(_icon("refresh", "#475569", 16))
        btn_reset.clicked.connect(self._reset_filters)

        fbar.addWidget(QLabel("关键字"))
        fbar.addWidget(self.search, 2)
        fbar.addWidget(QLabel("分类"))
        fbar.addWidget(self.cat)
        fbar.addWidget(QLabel("行程"))
        fbar.addWidget(self.trip)
        fbar.addWidget(QLabel("状态"))
        fbar.addWidget(self.status)
        fbar.addWidget(QLabel("起"))
        fbar.addWidget(self.date_from)
        fbar.addWidget(QLabel("止"))
        fbar.addWidget(self.date_to)
        fbar.addWidget(btn_filter)
        fbar.addWidget(btn_reset)
        root.addLayout(fbar)

        # 操作栏
        abar = QHBoxLayout()
        abar.setSpacing(8)
        self.btn_add = primary_button(" 手工新增")
        self.btn_add.setIcon(_icon("plus", "#FFFFFF", 16))
        self.btn_add.clicked.connect(self._add)
        self.btn_edit = QPushButton(" 编辑")
        self.btn_edit.setIcon(_icon("edit", "#475569", 16))
        self.btn_edit.clicked.connect(self._edit_selected)
        self.btn_del = QPushButton(" 删除")
        self.btn_del.setObjectName("danger")
        self.btn_del.setIcon(_icon("trash", "#DC2626", 16))
        self.btn_del.clicked.connect(self._delete_selected)
        self.btn_refresh = QPushButton(" 刷新")
        self.btn_refresh.setIcon(_icon("refresh", "#475569", 16))
        self.btn_refresh.clicked.connect(self.refresh)
        self.lbl_count = QLabel("")
        self.lbl_count.setStyleSheet(f"color:#94A3B8;")
        abar.addWidget(self.btn_add)
        abar.addWidget(self.btn_edit)
        abar.addWidget(self.btn_del)
        abar.addWidget(self.btn_refresh)
        abar.addStretch(1)
        abar.addWidget(self.lbl_count)
        root.addLayout(abar)

        # 表格 + 空状态（二选一显示）
        self.stack = QStackedWidget()
        self.table = QTableWidget(0, len(COLUMNS))
        self.table.setHorizontalHeaderLabels(COLUMNS)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.doubleClicked.connect(self._on_double)
        hdr = self.table.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        hdr.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        hdr.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        hdr.setSectionResizeMode(6, QHeaderView.Stretch)
        hdr.setSectionResizeMode(8, QHeaderView.ResizeToContents)
        self.stack.addWidget(self.table)

        self.empty = EmptyState(
            icon_name="inbox", title="还没有发票",
            subtitle="导入本地 PDF / 邮件 / 链接，或手工新增一张",
            action_text="导入发票", on_action=lambda: self.import_requested.emit())
        self.stack.addWidget(self.empty)
        root.addWidget(self.stack, 1)

    def _reset_filters(self):
        self.search.clear()
        self.cat.setCurrentIndex(0)
        self.trip.setCurrentIndex(0)
        self.status.setCurrentIndex(0)
        self.date_from.setDate(QDate(2000, 1, 1))
        self.date_to.setDate(QDate.currentDate())
        self.refresh()

    def set_trip_filter(self, trip_id: int):
        """由行程页跳转：按指定行程筛选。"""
        self.search.clear()
        self.cat.setCurrentIndex(0)
        self.status.setCurrentIndex(0)
        self.date_from.setDate(QDate(2000, 1, 1))
        self.date_to.setDate(QDate.currentDate())
        idx = self.trip.findData(trip_id)
        if idx >= 0:
            self.trip.setCurrentIndex(idx)
        self.refresh()

    def _current_filters(self) -> dict:
        f = {}
        if self.search.text().strip():
            f["keyword"] = self.search.text().strip()
        cat_id = self.cat.currentData()
        if cat_id:
            f["category_id"] = cat_id
        trip_id = self.trip.currentData()
        if trip_id is not None and trip_id != -1:
            f["trip_id"] = trip_id
        elif trip_id == -1:
            f["trip_id"] = None
        st = self.status.currentData()
        if st:
            f["status"] = st
        f["date_from"] = self.date_from.date().toString("yyyy-MM-dd")
        f["date_to"] = self.date_to.date().toString("yyyy-MM-dd")
        return f

    def refresh(self):
        cats = self.db.list_categories()
        trips = self.db.list_trips()
        fill_category_combo(self.cat, cats, include_all=True)
        fill_trip_combo(self.trip, trips, include_all=True, include_none=True)
        fill_status_combo(self.status, include_all=True)

        rows = self.db.list_invoices(self._current_filters())
        if not rows:
            self.stack.setCurrentIndex(1)
            self.lbl_count.setText("共 0 张发票")
            self._rows = []
            return
        self.stack.setCurrentIndex(0)
        self.table.setRowCount(len(rows))
        for i, inv in enumerate(rows):
            self._set_row(i, inv)
        self.lbl_count.setText(f"共 {len(rows)} 张发票")
        self._rows = rows

    def _set_row(self, i, inv: Invoice):
        badge = StatusBadge(inv.status)
        self.table.setCellWidget(i, 0, badge)
        self.table.setItem(i, 1, self._cell(inv.invoice_number or "-"))
        self.table.setItem(i, 2, self._cell(f"{inv.category_icon} {inv.category_name}"))
        amt = self._cell(fmt_money(inv.amount))
        amt.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.table.setItem(i, 3, amt)
        tax = self._cell(fmt_money(inv.tax_amount))
        tax.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.table.setItem(i, 4, tax)
        self.table.setItem(i, 5, self._cell(inv.issue_date or "-"))
        self.table.setItem(i, 6, self._cell(inv.vendor_name or "-"))
        self.table.setItem(i, 7, self._cell(inv.trip_name or "-"))
        self.table.setItem(i, 8, self._cell(inv.source_label))
        self.table.setRowHeight(i, 36)

    def _cell(self, text, color: QColor = None) -> QTableWidgetItem:
        it = QTableWidgetItem(str(text))
        if color:
            it.setForeground(color)
            from PySide6.QtGui import QFont
            f = QFont()
            f.setBold(True)
            it.setFont(f)
        return it

    def _selected_id(self):
        idx = self.table.currentRow()
        if idx < 0 or not hasattr(self, "_rows") or idx >= len(self._rows):
            return None
        return self._rows[idx].id

    def _on_double(self, index):
        inv_id = self._selected_id()
        if inv_id:
            self.open_requested.emit(inv_id)

    def _add(self):
        from ui.invoice_dialog import InvoiceDialog
        dlg = InvoiceDialog(self.db, parent=self)
        if dlg.exec():
            self.refresh()
            self.changed.emit()

    def _edit_selected(self):
        inv_id = self._selected_id()
        if not inv_id:
            QMessageBox.information(self, "提示", "请先在表格中选择一张发票")
            return
        from ui.invoice_dialog import InvoiceDialog
        dlg = InvoiceDialog(self.db, invoice_id=inv_id, parent=self)
        if dlg.exec():
            self.refresh()
            self.changed.emit()

    def _delete_selected(self):
        inv_id = self._selected_id()
        if not inv_id:
            QMessageBox.information(self, "提示", "请先在表格中选择一张发票")
            return
        inv = self.db.get_invoice(inv_id)
        if not inv:
            return
        r = QMessageBox.question(self, "确认删除",
                                 f"确定删除发票「{inv.invoice_number or '未编号'}」吗？\n"
                                 "该操作将同时删除其附件，且不可恢复。",
                                 QMessageBox.Yes | QMessageBox.No)
        if r == QMessageBox.Yes:
            self.db.delete_invoice(inv_id)
            self.refresh()
            self.changed.emit()
