# -*- coding: utf-8 -*-
"""差旅搭子 - 主窗口（侧边栏导航 + 顶部操作条 + 堆叠页）。"""
from __future__ import annotations

import os
from PySide6.QtWidgets import (QMainWindow, QStackedWidget, QMenuBar, QToolBar,
                               QMessageBox, QFileDialog, QStatusBar, QWidget,
                               QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget,
                               QTableWidgetItem, QHeaderView, QLabel, QFrame,
                               QSizePolicy, QSpacerItem)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QAction, QKeySequence, QIcon

from db.database import InvoiceDB
from db.models import Trip
from ui.dashboard import Dashboard
from ui.invoice_table import InvoiceList
from ui.import_wizard import ImportWizard
from ui.trip_dialog import TripDialog
from ui.settings_dialog import SettingsDialog
from ui.widgets import (fmt_money, NavButton, icon_chip)
from ui.icons import icon as _icon
from ui.theme import C
import config


# 各页元信息（标题 / 副标题 / 图标）
_PAGES = [
    ("dashboard", "仪表盘", "报销全景 · 分类占比 · 月度趋势", "dashboard"),
    ("invoice",   "发票",   "全部发票集中管理与归集",        "receipt"),
    ("trip",      "行程",   "按行程归集 · 预算管控",          "plane"),
]


class MainWindow(QMainWindow):
    def __init__(self, db: InvoiceDB):
        super().__init__()
        self.db = db
        self.setWindowTitle(f"{config.APP_NAME} v{config.APP_VERSION}")
        self.resize(1120, 740)
        self._build_ui()
        self._refresh_status()
        self.nav(0)

    # --------------------------- UI --------------------------- #
    def _build_ui(self):
        self._build_menubar()

        root = QWidget()
        root_layout = QHBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # ---- 侧边栏 ----
        sidebar = self._build_sidebar()
        root_layout.addWidget(sidebar, 0)

        # ---- 右侧内容区 ----
        content = QVBoxLayout()
        content.setContentsMargins(0, 0, 0, 0)
        content.setSpacing(0)

        topbar = self._build_topbar()
        content.addWidget(topbar, 0)

        self.stack = QStackedWidget()
        self.dashboard = Dashboard(self.db)
        self.invoice_list = InvoiceList(self.db)
        self.trips_page = self._build_trips_page()
        self.stack.addWidget(self.dashboard)
        self.stack.addWidget(self.invoice_list)
        self.stack.addWidget(self.trips_page)
        content.addWidget(self.stack, 1)

        root_layout.addLayout(content, 1)
        self.setCentralWidget(root)

        self.invoice_list.open_requested.connect(self._on_open_invoice)
        self.invoice_list.changed.connect(self._on_data_changed)
        self.invoice_list.import_requested.connect(self.open_import)

        self.setStatusBar(QStatusBar())

    def _build_menubar(self):
        menubar = self.menuBar()
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

        hmenu = menubar.addMenu("帮助")
        a_about = hmenu.addAction("关于差旅搭子")
        a_about.triggered.connect(self.about)

    def _build_sidebar(self):
        sb = QWidget()
        sb.setObjectName("sidebar")
        sb.setFixedWidth(224)
        v = QVBoxLayout(sb)
        v.setContentsMargins(14, 16, 14, 16)
        v.setSpacing(4)

        # Logo
        logo_row = QHBoxLayout()
        logo = icon_chip("plane", "#FFFFFF", 22, 40)
        logo.setStyleSheet(f"background:{C['brand']};border-radius:10px;")
        name = QLabel("差旅搭子")
        name.setObjectName("sidebarLogo")
        sub = QLabel("差旅发票管理")
        sub.setObjectName("sidebarLogoSub")
        logo_row.addWidget(logo)
        logo_row.addWidget(name)
        logo_row.addStretch(1)
        v.addLayout(logo_row)
        v.addSpacing(4)
        v.addWidget(sub)
        v.addSpacing(14)

        # 导航
        self._nav_btns = []
        for key, title, _, ic in _PAGES:
            btn = NavButton(ic, title)
            btn.clicked.connect(lambda _checked, k=key: self._nav_to(k))
            v.addWidget(btn)
            self._nav_btns.append((key, btn))
        v.addStretch(1)

        # 底部：设置
        self.btn_settings = NavButton("settings", "设置 / 关于")
        self.btn_settings.clicked.connect(self.open_settings)
        v.addWidget(self.btn_settings)
        return sb

    def _nav_to(self, key: str):
        idx = next(i for i, (k, _) in enumerate(self._nav_btns) if k == key)
        self.nav(idx)

    def _build_topbar(self):
        bar = QWidget()
        bar.setObjectName("topbar")
        bar.setFixedHeight(60)
        h = QHBoxLayout(bar)
        h.setContentsMargins(20, 0, 20, 0)
        h.setSpacing(10)

        self.page_title = QLabel()
        self.page_title.setObjectName("pageTitle")
        self.page_subtitle = QLabel()
        self.page_subtitle.setObjectName("pageSubtitle")
        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        title_col.addWidget(self.page_title)
        title_col.addWidget(self.page_subtitle)
        h.addLayout(title_col)
        h.addStretch(1)

        self.act_import = QPushButton(" 导入发票")
        self.act_import.setObjectName("primary")
        self.act_import.setIcon(_icon("upload", "#FFFFFF", 18))
        self.act_import.clicked.connect(self.open_import)

        self.act_new_trip = QPushButton(" 新建行程")
        self.act_new_trip.setIcon(_icon("plus", C["text_2"], 18))
        self.act_new_trip.clicked.connect(self.new_trip)

        self.act_export = QPushButton(" 导出")
        self.act_export.setIcon(_icon("download", C["text_2"], 18))
        self.act_export.clicked.connect(lambda: self.export_file("xlsx"))

        h.addWidget(self.act_import)
        h.addWidget(self.act_new_trip)
        h.addWidget(self.act_export)
        return bar

    def _build_trips_page(self):
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(20, 16, 20, 16)
        v.setSpacing(12)

        bar = QHBoxLayout()
        bar.setSpacing(8)
        self.btn_trip_add = QPushButton(" 新建行程")
        self.btn_trip_add.setObjectName("primary")
        self.btn_trip_add.setIcon(_icon("plus", "#FFFFFF", 18))
        self.btn_trip_add.clicked.connect(self.new_trip)
        self.btn_trip_edit = QPushButton(" 编辑")
        self.btn_trip_edit.setIcon(_icon("edit", C["text_2"], 16))
        self.btn_trip_edit.clicked.connect(self._edit_trip)
        self.btn_trip_del = QPushButton(" 删除")
        self.btn_trip_del.setObjectName("danger")
        self.btn_trip_del.setIcon(_icon("trash", C["danger"], 16))
        self.btn_trip_del.clicked.connect(self._del_trip)
        self.btn_trip_view = QPushButton(" 查看该行程发票")
        self.btn_trip_view.setIcon(_icon("receipt", C["text_2"], 16))
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
        for i, (key, btn) in enumerate(self._nav_btns):
            btn.set_active(i == idx)
        _, title, sub, _ = _PAGES[idx]
        self.page_title.setText(title)
        self.page_subtitle.setText(sub)
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
            self.trip_table.setItem(i, 0, self._cell(t.name))
            self.trip_table.setItem(i, 1, self._cell(t.destination))
            self.trip_table.setItem(i, 2, self._cell(t.date_range))
            b = self._cell(fmt_money(t.budget))
            b.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.trip_table.setItem(i, 3, b)
            amt = self._cell(fmt_money(s["total"]))
            amt.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.trip_table.setItem(i, 4, amt)
            self.trip_table.setItem(i, 5, self._cell(str(s["cnt"])))
            self.trip_table.setRowHeight(i, 36)

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

    @staticmethod
    def _cell(text, color: QColor = None):
        from PySide6.QtGui import QFont
        it = QTableWidgetItem(str(text))
        if color:
            it.setForeground(color)
            f = QFont()
            f.setBold(True)
            it.setFont(f)
        return it


def _stamp():
    from datetime import datetime
    return datetime.now().strftime("%Y%m%d")
