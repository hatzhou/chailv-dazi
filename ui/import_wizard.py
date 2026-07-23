# -*- coding: utf-8 -*-
"""差旅搭子 - 导入向导：本地文件 / 邮件 / 链接 三种来源。"""
from __future__ import annotations

import os
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTabWidget,
                               QWidget, QPushButton, QLineEdit, QComboBox, QSpinBox,
                               QCheckBox, QLabel, QTableWidget, QTableWidgetItem,
                               QDialogButtonBox, QFileDialog, QMessageBox, QHeaderView,
                               QFormLayout, QProgressBar, QFrame)
from PySide6.QtCore import Qt, Signal, QThread
from PySide6.QtGui import QFont

from db.database import InvoiceDB
from db.models import Invoice
from importers.parser import InvoiceDraft
from importers.local_importer import parse_local_files
from importers.email_importer import fetch_email_invoices
from importers.url_importer import fetch_url_invoice
from importers.save import save_draft
from ui.widgets import (fill_category_combo, fill_trip_combo, fmt_money,
                        status_label)
from ui.icons import icon as _icon
import config


# --------------------------- 邮件拉取后台线程 --------------------------- #
class EmailFetchThread(QThread):
    done = Signal(list, list)   # drafts, errors

    def __init__(self, host, user, pw, since_days, folder, ssl):
        super().__init__()
        self.args = (host, user, pw, since_days, folder, ssl)

    def run(self):
        drafts, errors = fetch_email_invoices(*self.args)
        self.done.emit(drafts, errors)


class ImportWizard(QDialog):
    imported = Signal()   # 导入完成后通知刷新

    def __init__(self, db: InvoiceDB, parent=None):
        super().__init__(parent)
        self.db = db
        self.drafts: list[InvoiceDraft] = []
        self.setWindowTitle("导入发票")
        self.resize(820, 600)
        self._build()

    def _build(self):
        root = QVBoxLayout(self)
        self.tabs = QTabWidget()
        self.tabs.addTab(self._tab_local(), _icon("file", "#475569", 18), "本地文件")
        self.tabs.addTab(self._tab_email(), _icon("inbox", "#475569", 18), "邮件导入")
        self.tabs.addTab(self._tab_url(), _icon("download", "#475569", 18), "链接下载")
        root.addWidget(self.tabs, 1)

        # 解析结果预览
        prev = QLabel("解析结果预览（可勾选导入、修改分类与金额）")
        prev.setStyleSheet("font-weight:bold;margin-top:6px;")
        root.addWidget(prev)
        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(
            ["导入", "发票号码", "分类", "金额", "开票日期", "销售方", "置信度/警告"])
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        hdr = self.table.horizontalHeader()
        hdr.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        hdr.setSectionResizeMode(5, QHeaderView.Stretch)
        root.addWidget(self.table, 2)

        # 底部：行程归集 + 导入
        bottom = QHBoxLayout()
        bottom.addWidget(QLabel("归集到行程："))
        self.trip_combo = QComboBox()
        fill_trip_combo(self.trip_combo, self.db.list_trips(),
                        include_none=True, none_text="不归集（仅入库）")
        bottom.addWidget(self.trip_combo)
        bottom.addStretch(1)
        self.btn_import = QPushButton(" 确认导入选中")
        self.btn_import.setObjectName("primary")
        self.btn_import.setIcon(_icon("upload", "#FFFFFF", 16))
        self.btn_import.clicked.connect(self._do_import)
        self.btn_import.setEnabled(False)
        bottom.addWidget(self.btn_import)
        root.addLayout(bottom)

    # ---------------------------- 本地页 ---------------------------- #
    def _tab_local(self):
        w = QWidget()
        v = QVBoxLayout(w)
        bar = QHBoxLayout()
        self.local_list = QLabel("尚未选择文件")
        self.local_list.setStyleSheet("color:#888;")
        btn_sel = QPushButton(" 选择文件（可多选）")
        btn_sel.setIcon(_icon("file", "#475569", 16))
        btn_sel.clicked.connect(self._pick_local)
        btn_parse = QPushButton(" 开始解析")
        btn_parse.setObjectName("primary")
        btn_parse.setIcon(_icon("upload", "#FFFFFF", 16))
        btn_parse.clicked.connect(self._parse_local)
        bar.addWidget(btn_sel)
        bar.addWidget(btn_parse)
        bar.addStretch(1)
        v.addLayout(bar)
        v.addWidget(self.local_list)
        self._local_paths = []
        return w

    def _pick_local(self):
        paths, _ = QFileDialog.getOpenFileNames(
            self, "选择发票文件", "",
            "发票文件 (*.pdf *.ofd *.png *.jpg *.jpeg *.bmp *.gif *.webp);;所有文件 (*)")
        if paths:
            self._local_paths = paths
            self.local_list.setText(f"已选择 {len(paths)} 个文件")

    def _parse_local(self):
        if not self._local_paths:
            QMessageBox.information(self, "提示", "请先选择文件")
            return
        results = parse_local_files(self._local_paths)
        drafts = [d for d, _ in results if d]
        for d, warns in results:
            if d and warns:
                d.warnings.extend(w for w in warns if w not in d.warnings)
        self._set_drafts(drafts)
        self.tabs.setCurrentIndex(0)

    # ---------------------------- 邮件页 ---------------------------- #
    def _tab_email(self):
        w = QWidget()
        f = QFormLayout(w)
        self.email_host = QComboBox()
        self.email_host.setEditable(True)
        for name, host in config.COMMON_IMAP_HOSTS:
            self.email_host.addItem(f"{name} ({host})", host)
        saved_host = self.db.get_setting("email_host", "")
        if saved_host:
            idx = self.email_host.findData(saved_host)
            if idx >= 0:
                self.email_host.setCurrentIndex(idx)
        self.email_user = QLineEdit(self.db.get_setting("email_user", ""))
        self.email_pw = QLineEdit(self.db.get_setting("email_pw", ""))
        self.email_pw.setEchoMode(QLineEdit.Password)
        self.email_days = QSpinBox()
        self.email_days.setRange(1, 365)
        self.email_days.setValue(30)
        self.email_ssl = QCheckBox("使用 SSL")
        self.email_ssl.setChecked(True)
        f.addRow("IMAP 服务器", self.email_host)
        f.addRow("邮箱账号", self.email_user)
        f.addRow("密码 / 授权码", self.email_pw)
        f.addRow("检索近 N 天", self.email_days)
        f.addRow("加密", self.email_ssl)
        bar = QHBoxLayout()
        self.btn_fetch = QPushButton(" 拉取发票附件")
        self.btn_fetch.setObjectName("primary")
        self.btn_fetch.setIcon(_icon("inbox", "#FFFFFF", 16))
        self.btn_fetch.clicked.connect(self._fetch_email)
        bar.addWidget(self.btn_fetch)
        bar.addStretch(1)
        f.addRow(bar)
        self.email_bar = QProgressBar()
        self.email_bar.setRange(0, 0)
        self.email_bar.setVisible(False)
        f.addRow(self.email_bar)
        return w

    def _fetch_email(self):
        host = self.email_host.currentData() or self.email_host.currentText().strip()
        user = self.email_user.text().strip()
        pw = self.email_pw.text().strip()
        if not (host and user and pw):
            QMessageBox.warning(self, "提示", "请填写邮箱服务器、账号与密码/授权码")
            return
        # 记住配置
        self.db.set_setting("email_host", host)
        self.db.set_setting("email_user", user)
        self.db.set_setting("email_pw", pw)
        self.email_bar.setVisible(True)
        self.btn_fetch.setEnabled(False)
        self._thread = EmailFetchThread(
            host, user, pw, self.email_days.value(), "INBOX", self.email_ssl.isChecked())
        self._thread.done.connect(self._on_email_done)
        self._thread.start()

    def _on_email_done(self, drafts, errors):
        self.email_bar.setVisible(False)
        self.btn_fetch.setEnabled(True)
        if errors:
            QMessageBox.information(self, "邮件导入", "\n".join(errors[:5]))
        self._set_drafts(drafts)

    # ---------------------------- 链接页 ---------------------------- #
    def _tab_url(self):
        w = QWidget()
        v = QVBoxLayout(w)
        f = QFormLayout()
        self.url_edit = QLineEdit()
        self.url_edit.setPlaceholderText("粘贴发票文件链接，例如 https://.../发票.pdf")
        f.addRow("发票链接", self.url_edit)
        v.addLayout(f)
        bar = QHBoxLayout()
        btn = QPushButton(" 解析链接")
        btn.setObjectName("primary")
        btn.setIcon(_icon("download", "#FFFFFF", 16))
        btn.clicked.connect(self._parse_url)
        bar.addWidget(btn)
        bar.addStretch(1)
        v.addLayout(bar)
        v.addStretch(1)
        return w

    def _parse_url(self):
        url = self.url_edit.text().strip()
        draft, err = fetch_url_invoice(url)
        if err:
            QMessageBox.warning(self, "链接导入", err)
            return
        if draft:
            self._set_drafts([draft])

    # ---------------------------- 草稿表 ---------------------------- #
    def _set_drafts(self, drafts: list[InvoiceDraft]):
        # 合并（去重同类草稿按发票号码）
        seen = {d.invoice_number for d in self.drafts}
        for d in drafts:
            if d.invoice_number and d.invoice_number in seen:
                continue
            self.drafts.append(d)
            if d.invoice_number:
                seen.add(d.invoice_number)
        self._rebuild_table()
        self.btn_import.setEnabled(len(self.drafts) > 0)

    def _rebuild_table(self):
        cats = self.db.list_categories()
        self.table.setRowCount(len(self.drafts))
        for i, d in enumerate(self.drafts):
            # 导入勾选
            chk = QCheckBox()
            chk.setChecked(True)
            cell = QWidget()
            h = QHBoxLayout(cell)
            h.setContentsMargins(4, 0, 4, 0)
            h.addWidget(chk)
            self.table.setCellWidget(i, 0, cell)
            # 发票号码
            self.table.setItem(i, 1, QTableWidgetItem(d.invoice_number or "(未识别)"))
            # 分类
            ccat = QComboBox()
            fill_category_combo(ccat, cats)
            cat_obj = self.db.get_category_by_key(d.category_key) or \
                self.db.get_category_by_key("other")
            idx = ccat.findData(cat_obj.id) if cat_obj else 0
            if idx >= 0:
                ccat.setCurrentIndex(idx)
            self.table.setCellWidget(i, 2, ccat)
            # 金额
            amt = QTableWidgetItem(fmt_money(d.amount))
            amt.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.table.setItem(i, 3, amt)
            # 开票日期
            self.table.setItem(i, 4, QTableWidgetItem(d.issue_date or ""))
            # 销售方
            self.table.setItem(i, 5, QTableWidgetItem(d.vendor_name or ""))
            # 置信度/警告
            warn = f"置信度 {int(d.parse_confidence*100)}%"
            if d.warnings:
                warn += " ⚠ " + "; ".join(d.warnings[:1])
            self.table.setItem(i, 6, QTableWidgetItem(warn))
            self.table.setRowHeight(i, 30)

    def _do_import(self):
        cats = self.db.list_categories()
        trip_id = self.trip_combo.currentData()
        if trip_id == -1:
            trip_id = None
        ok, skip = 0, 0
        errs = []
        for i, d in enumerate(self.drafts):
            chk_widget = self.table.cellWidget(i, 0)
            chk = chk_widget.findChild(QCheckBox)
            if chk and not chk.isChecked():
                continue
            # 从表格取最新编辑值
            ccat = self.table.cellWidget(i, 2)
            if ccat and ccat.currentData():
                co = self.db.get_category(ccat.currentData())
                if co:
                    d.category_key = co.key
                    d.category_name = co.name
            d.amount = self._parse_money(self.table.item(i, 3).text())
            d.issue_date = self.table.item(i, 4).text().strip()
            d.vendor_name = self.table.item(i, 5).text().strip()
            try:
                iid, was_dup = save_draft(self.db, d, trip_id=trip_id)
                if was_dup:
                    skip += 1
                else:
                    ok += 1
            except Exception as e:
                errs.append(f"{d.invoice_number or '?'}：{e}")
        msg = f"成功导入 {ok} 张，跳过重复 {skip} 张。"
        if errs:
            msg += "\n失败：\n" + "\n".join(errs[:5])
        QMessageBox.information(self, "导入完成", msg)
        self.imported.emit()
        self.accept()

    @staticmethod
    def _parse_money(s: str) -> float:
        s = s.replace("¥", "").replace(",", "").strip()
        try:
            return float(s)
        except Exception:
            return 0.0
