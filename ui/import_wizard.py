# -*- coding: utf-8 -*-
"""差旅搭子 - 导入向导：本地文件 / 邮件（多邮箱）/ 链接 三种来源。"""
from __future__ import annotations

import os
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTabWidget,
                               QWidget, QPushButton, QLineEdit, QComboBox, QSpinBox,
                               QCheckBox, QLabel, QTableWidget, QTableWidgetItem,
                               QDialogButtonBox, QFileDialog, QMessageBox, QHeaderView,
                               QFormLayout, QProgressBar, QFrame, QListWidget,
                               QAbstractItemView)
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
from ui.mailbox_dialog import MailboxDialog
import config


# --------------------------- 后台线程 --------------------------- #
class EmailFetchThread(QThread):
    done = Signal(list, list)   # drafts, errors

    def __init__(self, host, user, pw, since_days, folder, ssl):
        super().__init__()
        self.args = (host, user, pw, since_days, folder, ssl)

    def run(self):
        drafts, errors = fetch_email_invoices(*self.args)
        self.done.emit(drafts, errors)


class PullAllThread(QThread):
    """一次性拉取所有启用邮箱：解析并保存到本地存储与数据库。"""
    finished = Signal(int, int, int, list, list)  # ok, skip, fail, drafts, errors

    def __init__(self, db: InvoiceDB, mailboxes, trip_id=None):
        super().__init__()
        self.db = db
        self.mailboxes = mailboxes
        self.trip_id = trip_id

    def run(self):
        from datetime import datetime
        ok = skip = fail = 0
        drafts: list = []
        errors: list = []
        for mb in self.mailboxes:
            try:
                ds, errs = fetch_email_invoices(
                    mb.host, mb.user, mb.password, mb.since_days, "INBOX", mb.use_ssl)
                errors.extend(errs)
                for d in ds:
                    try:
                        _, was_dup = save_draft(self.db, d, trip_id=self.trip_id)
                        drafts.append(d)
                        if was_dup:
                            skip += 1
                        else:
                            ok += 1
                    except Exception as e:
                        fail += 1
                        errors.append(f"{d.invoice_number or d.file_name}: {e}")
                if ds:
                    self.db.set_mailbox_last_pull(mb.id, datetime.now().strftime("%Y-%m-%d %H:%M"))
            except Exception as e:
                errors.append(f"邮箱 {mb.user}: {e}")
        self.finished.emit(ok, skip, fail, drafts, errors)


class ImportWizard(QDialog):
    imported = Signal()   # 导入完成后通知刷新

    def __init__(self, db: InvoiceDB, parent=None):
        super().__init__(parent)
        self.db = db
        self.drafts: list[InvoiceDraft] = []
        self.setWindowTitle("导入发票")
        self.resize(820, 620)
        self._build()

    def _build(self):
        root = QVBoxLayout(self)
        self.tabs = QTabWidget()
        self.tabs.addTab(self._tab_local(), _icon("file", "#475569", 18), "本地文件")
        self.tabs.addTab(self._tab_email(), _icon("inbox", "#475569", 18), "邮件导入")
        self.tabs.addTab(self._tab_url(), _icon("download", "#475569", 18), "链接下载")
        root.addWidget(self.tabs, 1)

        # 结果预览
        prev = QLabel("解析结果预览（可勾选导入、修改分类与金额）")
        prev.setStyleSheet("font-weight:700;color:#475569;margin-top:6px;")
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
        self.local_list.setStyleSheet("color:#94A3B8;")
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

    # ---------------------------- 邮件页（多邮箱） ---------------------------- #
    def _tab_email(self):
        w = QWidget()
        v = QVBoxLayout(w)
        v.setSpacing(10)

        # 账号列表
        head = QHBoxLayout()
        head.addWidget(QLabel("已配置邮箱账号"))
        head.addStretch(1)
        self.btn_mb_add = QPushButton(" 新增")
        self.btn_mb_add.setIcon(_icon("plus", "#475569", 15))
        self.btn_mb_add.clicked.connect(self._add_mailbox)
        self.btn_mb_edit = QPushButton(" 编辑")
        self.btn_mb_edit.setIcon(_icon("edit", "#475569", 15))
        self.btn_mb_edit.clicked.connect(self._edit_mailbox)
        self.btn_mb_del = QPushButton(" 删除")
        self.btn_mb_del.setObjectName("danger")
        self.btn_mb_del.setIcon(_icon("trash", "#DC2626", 15))
        self.btn_mb_del.clicked.connect(self._del_mailbox)
        head.addWidget(self.btn_mb_add)
        head.addWidget(self.btn_mb_edit)
        head.addWidget(self.btn_mb_del)
        v.addLayout(head)

        self.mb_list = QListWidget()
        self.mb_list.setSelectionMode(QAbstractItemView.SingleSelection)
        self.mb_list.itemDoubleClicked.connect(self._edit_mailbox)
        v.addWidget(self.mb_list, 1)

        # 拉取
        pull_bar = QHBoxLayout()
        self.btn_pull = QPushButton(" 拉取全部发票")
        self.btn_pull.setObjectName("primary")
        self.btn_pull.setIcon(_icon("inbox", "#FFFFFF", 16))
        self.btn_pull.clicked.connect(self._pull_all)
        pull_bar.addWidget(self.btn_pull)
        pull_bar.addStretch(1)
        v.addLayout(pull_bar)

        self.email_bar = QProgressBar()
        self.email_bar.setRange(0, 0)
        self.email_bar.setVisible(False)
        v.addWidget(self.email_bar)

        self._refresh_mailboxes()
        return w

    def _refresh_mailboxes(self):
        self.mb_list.clear()
        for mb in self.db.list_mailboxes():
            mark = "✓" if mb.enabled else "✗"
            label = f"{mark} {mb.name or mb.user}  <{mb.user}>"
            if mb.last_pull:
                label += f"  ·  上次 {mb.last_pull}"
            self.mb_list.addItem(label)

    def _selected_mailbox_id(self):
        row = self.mb_list.currentRow()
        mbs = self.db.list_mailboxes()
        if row < 0 or row >= len(mbs):
            return None
        return mbs[row].id

    def _add_mailbox(self):
        dlg = MailboxDialog(self.db, parent=self)
        if dlg.exec():
            self._refresh_mailboxes()

    def _edit_mailbox(self):
        mb_id = self._selected_mailbox_id()
        if mb_id is None:
            QMessageBox.information(self, "提示", "请先选择邮箱账号")
            return
        dlg = MailboxDialog(self.db, mailbox_id=mb_id, parent=self)
        if dlg.exec():
            self._refresh_mailboxes()

    def _del_mailbox(self):
        mb_id = self._selected_mailbox_id()
        if mb_id is None:
            QMessageBox.information(self, "提示", "请先选择邮箱账号")
            return
        mb = self.db.get_mailbox(mb_id)
        r = QMessageBox.question(self, "确认删除",
                                 f"删除邮箱账号「{mb.name or mb.user}」？",
                                 QMessageBox.Yes | QMessageBox.No)
        if r == QMessageBox.Yes:
            self.db.delete_mailbox(mb_id)
            self._refresh_mailboxes()

    def _pull_all(self):
        mbs = [m for m in self.db.list_mailboxes() if m.enabled]
        if not mbs:
            QMessageBox.information(self, "拉取发票",
                                    "尚未配置启用的邮箱账号。\n点击「新增」添加邮箱后重试。")
            return
        trip_id = self.trip_combo.currentData()
        if trip_id == -1:
            trip_id = None
        self.email_bar.setVisible(True)
        self.btn_pull.setEnabled(False)
        self._pull_thread = PullAllThread(self.db, mbs, trip_id=trip_id)
        self._pull_thread.finished.connect(self._on_pull_done)
        self._pull_thread.start()

    def _on_pull_done(self, ok, skip, fail, drafts, errors):
        self.email_bar.setVisible(False)
        self.btn_pull.setEnabled(True)
        self._refresh_mailboxes()
        if errors:
            QMessageBox.information(self, "拉取完成（含提示）", "\n".join(errors[:6]))
        msg = (f"拉取完成：成功导入 {ok} 张，跳过重复 {skip} 张"
               + (f"，失败 {fail} 张。" if fail else "。"))
        QMessageBox.information(self, "拉取完成", msg)
        self._set_drafts(drafts)
        self.imported.emit()
        self.accept()

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
            chk = QCheckBox()
            chk.setChecked(True)
            cell = QWidget()
            h = QHBoxLayout(cell)
            h.setContentsMargins(4, 0, 4, 0)
            h.addWidget(chk)
            self.table.setCellWidget(i, 0, cell)
            self.table.setItem(i, 1, QTableWidgetItem(d.invoice_number or "(未识别)"))
            ccat = QComboBox()
            fill_category_combo(ccat, cats)
            cat_obj = self.db.get_category_by_key(d.category_key) or \
                self.db.get_category_by_key("other")
            idx = ccat.findData(cat_obj.id) if cat_obj else 0
            if idx >= 0:
                ccat.setCurrentIndex(idx)
            self.table.setCellWidget(i, 2, ccat)
            amt = QTableWidgetItem(fmt_money(d.amount))
            amt.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.table.setItem(i, 3, amt)
            self.table.setItem(i, 4, QTableWidgetItem(d.issue_date or ""))
            self.table.setItem(i, 5, QTableWidgetItem(d.vendor_name or ""))
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
