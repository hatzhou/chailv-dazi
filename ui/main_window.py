# -*- coding: utf-8 -*-
"""差旅搭子 - 主窗口。"""
from __future__ import annotations

import os
from PySide6.QtWidgets import (QMainWindow, QStackedWidget, QToolBar, QMenuBar,
                               QMessageBox, QFileDialog, QStatusBar, QWidget,
                               QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget,
                               QTableWidgetItem, QHeaderView, QLabel, QFrame)
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QKeySequence, QIcon

from db.database import InvoiceDB
from db.models import Trip
from ui.dashboard import Dashboard
from ui.invoice_table import InvoiceList
from ui.import_wizard import ImportWizard
from ui.trip_dialog import TripDialog
from ui.settings_dialog import SettingsDialog
from ui.widgets import fmt_money, empty_hint
import config


class MainWindow(QMainWindow):
    def __init__(self, db: InvoiceDB):
        super().__init__()
        self.db = db
        self.setWindowTitle(f"{config.APP_NAME} v{config.APP_VERSION}")
        self.resize(1080, 720)
        self._build_ui()
        self._refresh_status()

    # --------------------------- UI --------------------------- #
    def _build_ui(self):
        menubar = self.menuBar()
        # 文件
        fmenu = menubar.addMenu("文件")
        a_import = fmenu.addAction("导入发票...")
        a_import.setShortcut(QKeySequence("Ctrl+I"))
        a_import.triggered.connect(self.open_import)
        a_xlsx = fmenu.addAction("导出 Excel 报销表...")
        a_xlsx.triggered.connect(lambda: self.export_file("xlsx"))
        a_pdf = fmenu.addAction("导出 PDF 报销单...")
        a_pdf.triggered.connect(lambda: self.export_file("pdf"))
        fmenu.addSeparator()
        a_exit = fmenu.addAction("退出")
        a_exit.triggered.connect(self.close)
        # 管理
        mmenu = menubar.addMenu("管理")
        a_trip = mmenu.addAction("行程管理")
        a_trip.triggered.connect(lambda: self.nav(2))
        a_set = mmenu.addAction("设置 / 关于")
        a_set.triggered.connect(self.open_settings)
        # 帮助
        hmenu = menubar.addMenu("帮助")
        a_about = hmenu.addAction("关于差旅搭子")
        a_about.triggered.connect(self.about)

        # 工具栏
        tb = QToolBar("主工具栏")
        self.addToolBar(tb)
        self.act_dash = tb.addAction("📊 仪表盘")
        self.act_inv = tb.addAction("🧾 发票")
        self.act_trip = tb.addAction("✈ 行程")
        tb.addSeparator()
        self.act_import = tb.addAction("⬆ 导入")
        self.act_new_trip = tb.addAction("＋ 新建行程")
        self.act_export = tb.addAction("⬇ 导出")
        self.act_dash.triggered.connect(lambda: self.nav(0))
        self.act_inv.triggered.connect(lambda: self.nav(1))
        self.act_trip.triggered.connect(lambda: self.nav(2))
        self.act_import.triggered.connect(self.open_import)
        self.act_new_trip.triggered.connect(self.new_trip)
        self.act_export.triggered.connect(lambda: self.export_file("xlsx"))

        # 中央堆叠
        self.stack = QStackedWidget()
        self.dashboard = Dashboard(self.db)
        self.invoice_list = InvoiceList(self.db)
        self.trips_page = self._build_trips_page()
        self.stack.addWidget(self.dashboard)
        self.stack.addWidget(self.invoice_list)
        self.stack.addWidget(self.trips_page)
        self.setCentralWidget(self.stack)

        self.invoice_list.open_requested.connect(self._on_open_invoice)
        self.invoice_list.changed.connect(self._on_data_changed)

        self.setStatusBar(QStatusBar())

    def _build_trips_page(self):
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(16, 12, 16, 12)
        bar = QHBoxLayout()
        self.btn_trip_add = QPushButton("＋ 新建行程")
        self.btn_trip_add.clicked.connect(self.new_trip)
        self.btn_trip_edit = QPushButton("编辑")
        self.btn_trip_edit.clicked.connect(self._edit_trip)
        self.btn_trip_del = QPushButton("删除")
        self.btn_trip_del.clicked.connect(self._del_trip)
        self.btn_trip_view = QPushButton("查看该行程发票")
        self.btn_trip_view.clicked.connect(self._view_trip_invoices)
        bar.addWidget(self.btn_trip_add)
        bar.addWidget(self.btn_trip_edit)
        bar.addWidget(self.btn_trip_del)
        bar.addWidget(self.btn_trip_view)
        bar.addStretch(1)
        v.addLayout(bar)

        self.trip_table = QTableWidget(0, 6)
        self.trip_table.setHorizontalHeaderLabels(
            ["行程名称", "目的地", "起止日期", "预算", "已归集金额", "张数"])
        self.trip_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.trip_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.trip_table.verticalHeader().setVisible(False)
        self.trip_table.doubleClicked.connect(self._view_trip_invoices)
        hdr = self.trip_table.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        hdr.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        v.addWidget(self.trip_table, 1)
        self._refresh_trips()
        return w

    # --------------------------- 导航 --------------------------- #
    def nav(self, idx: int):
        self.stack.setCurrentIndex(idx)
        if idx == 0:
            self.dashboard.refresh()
        elif idx == 1:
            self.invoice_list.refresh()
        elif idx == 2:
            self._refresh_trips()

    # --------------------------- 发票 --------------------------- #
    def _on_open_invoice(self, inv_id: int):
        from ui.invoice_dialog import InvoiceDialog
        dlg = InvoiceDialog(self.db, invoice_id=inv_id, parent=self)
        if dlg.exec():
            self.invoice_list.refresh()
            self._on_data_changed()

    def open_import(self):
        dlg = ImportWizard(self.db, parent=self)
        dlg.imported.connect(self._on_data_changed)
        dlg.exec()
        self._on_data_changed()

    # --------------------------- 行程 --------------------------- #
    def new_trip(self):
        dlg = TripDialog(self.db, parent=self)
        if dlg.exec():
            self._refresh_trips()
            self._on_data_changed()

    def _selected_trip_id(self):
        r = self.trip_table.currentRow()
        if r < 0 or not hasattr(self, "_trip_rows"):
            return None
        if r >= len(self._trip_rows):
            return None
        return self._trip_rows[r].id

    def _edit_trip(self):
        tid = self._selected_trip_id()
        if tid is None:
            QMessageBox.information(self, "提示", "请先选择行程")
            return
        dlg = TripDialog(self.db, trip_id=tid, parent=self)
        if dlg.exec():
            self._refresh_trips()
            self._on_data_changed()

    def _del_trip(self):
        tid = self._selected_trip_id()
        if tid is None:
            QMessageBox.information(self, "提示", "请先选择行程")
            return
        t = self.db.get_trip(tid)
        r = QMessageBox.question(self, "确认删除",
                                 f"删除行程「{t.name}」？\n其中的发票将变为未归集，不会被删除。",
                                 QMessageBox.Yes | QMessageBox.No)
        if r == QMessageBox.Yes:
            self.db.delete_trip(tid)
            self._refresh_trips()
            self._on_data_changed()

    def _view_trip_invoices(self):
        tid = self._selected_trip_id()
        if tid is None:
            QMessageBox.information(self, "提示", "请先选择行程")
            return
        self.invoice_list.set_trip_filter(tid)
        self.nav(1)

    def _refresh_trips(self):
        trips = self.db.list_trips()
        self._trip_rows = trips
        self.trip_table.setRowCount(len(trips))
        stats = {r["trip_id"]: r for r in self.db.stats_by_trip()}
        for i, t in enumerate(trips):
            s = stats.get(t.id, {"total": 0, "cnt": 0})
            self.trip_table.setItem(i, 0, QTableWidgetItem(t.name))
            self.trip_table.setItem(i, 1, QTableWidgetItem(t.destination))
            self.trip_table.setItem(i, 2, QTableWidgetItem(t.date_range))
            b = QTableWidgetItem(fmt_money(t.budget))
            b.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.trip_table.setItem(i, 3, b)
            amt = QTableWidgetItem(fmt_money(s["total"]))
            amt.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.trip_table.setItem(i, 4, amt)
            self.trip_table.setItem(i, 5, QTableWidgetItem(str(s["cnt"])))
            self.trip_table.setRowHeight(i, 30)

    # --------------------------- 导出 --------------------------- #
    def export_file(self, kind: str):
        if kind == "xlsx":
            path, _ = QFileDialog.getSaveFileName(
                self, "导出 Excel", f"差旅报销_{_stamp()}.xlsx", "Excel (*.xlsx)")
            if path:
                try:
                    from utils.export import export_excel
                    n = export_excel(self.db, path)
                    QMessageBox.information(self, "导出成功",
                                            f"已导出 {n} 张发票到：\n{path}")
                except Exception as e:
                    QMessageBox.critical(self, "导出失败", str(e))
        else:
            path, _ = QFileDialog.getSaveFileName(
                self, "导出 PDF", f"差旅报销_{_stamp()}.pdf", "PDF (*.pdf)")
            if path:
                try:
                    from utils.export import export_pdf
                    n = export_pdf(self.db, path)
                    QMessageBox.information(self, "导出成功",
                                            f"已导出 {n} 张发票到：\n{path}")
                except Exception as e:
                    QMessageBox.critical(self, "导出失败", str(e))

    # --------------------------- 其它 --------------------------- #
    def open_settings(self):
        dlg = SettingsDialog(self.db, parent=self)
        dlg.exec()

    def about(self):
        QMessageBox.about(self, f"关于 {config.APP_NAME}",
                          f"{config.APP_NAME} v{config.APP_VERSION}\n\n"
                          "面向频繁出差人群的发票集中管理工具。\n"
                          "支持本地文件 / 邮件 / 链接多源采集，\n"
                          "智能解析发票字段，按行程与分类归集，\n"
                          "一键导出 Excel / PDF 报销单。\n\n"
                          "技术栈：Python + PySide6 + SQLite")

    def _on_data_changed(self):
        self.dashboard.refresh()
        self._refresh_status()
        if self.stack.currentIndex() == 1:
            self.invoice_list.refresh()
        if self.stack.currentIndex() == 2:
            self._refresh_trips()

    def _refresh_status(self):
        s = self.db.stats_summary()
        self.statusBar().showMessage(
            f"发票 {s['total_count']} 张　|　总金额 {fmt_money(s['total_amount'])}　"
            f"|　待报销 {fmt_money(s['pending_amount'])}　"
            f"|　已报销 {fmt_money(s['reimbursed_amount'])}")


def _stamp():
    from datetime import datetime
    return datetime.now().strftime("%Y%m%d")
