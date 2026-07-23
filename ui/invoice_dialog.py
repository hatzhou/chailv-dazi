# -*- coding: utf-8 -*-
"""差旅搭子 - 发票新增/编辑对话框。"""
from __future__ import annotations

import os
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
                               QLineEdit, QComboBox, QDateEdit, QTextEdit, QPushButton,
                               QLabel, QDialogButtonBox, QListWidget, QFileDialog,
                               QMessageBox, QDoubleSpinBox, QGroupBox)
from PySide6.QtCore import Qt, QDate, QUrl
from PySide6.QtGui import QDesktopServices

from db.database import InvoiceDB
from db.models import Invoice
from ui.widgets import (fill_category_combo, fill_trip_combo, fill_status_combo,
                        fmt_money)
from ui.icons import icon as _icon
import config


class InvoiceDialog(QDialog):
    def __init__(self, db: InvoiceDB, invoice_id: int = None, parent=None):
        super().__init__(parent)
        self.db = db
        self.invoice_id = invoice_id
        self.inv = self.db.get_invoice(invoice_id) if invoice_id else None
        self.setWindowTitle("编辑发票" if invoice_id else "手工新增发票")
        self.resize(560, 620)
        self._build()
        if self.inv:
            self._load()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(12)

        g = QGroupBox("发票信息")
        form = QFormLayout(g)
        form.setLabelAlignment(Qt.AlignRight)
        form.setSpacing(10)
        form.setContentsMargins(16, 18, 16, 16)

        self.code = QLineEdit()
        self.number = QLineEdit()
        self.cat = QComboBox()
        self.amount = QDoubleSpinBox()
        self.amount.setRange(0, 99999999)
        self.amount.setDecimals(2)
        self.amount.setPrefix("¥")
        self.tax = QDoubleSpinBox()
        self.tax.setRange(0, 99999999)
        self.tax.setDecimals(2)
        self.tax.setPrefix("¥")
        self.currency = QLineEdit("CNY")
        self.date = QDateEdit()
        self.date.setCalendarPopup(True)
        self.date.setDisplayFormat("yyyy-MM-dd")
        self.date.setDate(QDate.currentDate())
        self.vendor = QLineEdit()
        self.vendor_tax = QLineEdit()
        self.buyer = QLineEdit()
        self.buyer_tax = QLineEdit()
        self.trip = QComboBox()
        self.status = QComboBox()
        self.pay = QLineEdit()
        self.note = QTextEdit()
        self.note.setMaximumHeight(60)

        fill_category_combo(self.cat, self.db.list_categories())
        fill_trip_combo(self.trip, self.db.list_trips(), include_none=True,
                        none_text="未归集行程")
        fill_status_combo(self.status)
        self.amount.valueChanged.connect(self._auto_excl)

        form.addRow("发票代码", self.code)
        form.addRow("发票号码 *", self.number)
        form.addRow("分类", self.cat)
        form.addRow("价税合计 *", self.amount)
        form.addRow("税额", self.tax)
        form.addRow("币种", self.currency)
        form.addRow("开票日期", self.date)
        form.addRow("销售方名称", self.vendor)
        form.addRow("销售方税号", self.vendor_tax)
        form.addRow("购买方名称", self.buyer)
        form.addRow("购买方税号", self.buyer_tax)
        form.addRow("所属行程", self.trip)
        form.addRow("状态", self.status)
        form.addRow("支付方式", self.pay)
        form.addRow("备注", self.note)
        root.addWidget(g)

        # 附件
        att_label = QLabel("附件（原图 / PDF）")
        att_label.setStyleSheet("font-weight:bold;color:#475569;")
        root.addWidget(att_label)
        self.att_list = QListWidget()
        self.att_list.itemDoubleClicked.connect(self._open_att)
        root.addWidget(self.att_list, 1)
        att_bar = QHBoxLayout()
        self.btn_add_att = QPushButton(" 添加附件")
        self.btn_add_att.setIcon(_icon("plus", "#475569", 15))
        self.btn_add_att.clicked.connect(self._add_att)
        self.btn_del_att = QPushButton(" 移除选中")
        self.btn_del_att.setObjectName("danger")
        self.btn_del_att.setIcon(_icon("trash", "#DC2626", 15))
        self.btn_del_att.clicked.connect(self._del_att)
        att_bar.addWidget(self.btn_add_att)
        att_bar.addWidget(self.btn_del_att)
        att_bar.addStretch(1)
        root.addLayout(att_bar)

        # 按钮
        bb = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        bb.button(QDialogButtonBox.Save).setObjectName("primary")
        bb.button(QDialogButtonBox.Save).setText(" 保存")
        bb.button(QDialogButtonBox.Cancel).setText(" 取消")
        bb.accepted.connect(self._accept)
        bb.rejected.connect(self.reject)
        root.addWidget(bb)

    def _auto_excl(self):
        # 不含税金额由 价税合计-税额 实时计算并提示（只读展示在备注区上方）
        excl = self.amount.value() - self.tax.value()
        self._excl_hint = excl

    def _load(self):
        inv = self.inv
        self.code.setText(inv.invoice_code)
        self.number.setText(inv.invoice_number)
        self._set_combo(self.cat, inv.category_id)
        self.amount.setValue(inv.amount)
        self.tax.setValue(inv.tax_amount)
        self.currency.setText(inv.currency)
        if inv.issue_date:
            self.date.setDate(QDate.fromString(inv.issue_date, "yyyy-MM-dd"))
        self.vendor.setText(inv.vendor_name)
        self.vendor_tax.setText(inv.vendor_tax_id)
        self.buyer.setText(inv.buyer_name)
        self.buyer_tax.setText(inv.buyer_tax_id)
        self._set_combo(self.trip, inv.trip_id if inv.trip_id else -1)
        self._set_combo(self.status, inv.status)
        self.pay.setText(inv.payment_method)
        self.note.setText(inv.note)
        self._refresh_atts()

    def _set_combo(self, combo, data):
        idx = combo.findData(data)
        if idx >= 0:
            combo.setCurrentIndex(idx)

    def _refresh_atts(self):
        self.att_list.clear()
        if not self.inv:
            return
        for a in self.db.list_attachments(self.inv.id):
            self.att_list.addItem(f"{a.file_name}  ({a.file_type})")

    def _add_att(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "选择附件", "",
            "发票文件 (*.pdf *.ofd *.png *.jpg *.jpeg *.bmp);;所有文件 (*)")
        if not path:
            return
        if self.inv:
            self.db.add_attachment(self.inv.id, path)
            self._refresh_atts()
        else:
            QMessageBox.information(self, "提示",
                                    "请先保存发票后再添加附件")

    def _del_att(self):
        if not self.inv:
            return
        row = self.att_list.currentRow()
        if row < 0:
            return
        atts = self.db.list_attachments(self.inv.id)
        if row < len(atts):
            self.db.delete_attachment(atts[row].id)
            self._refresh_atts()

    def _open_att(self, item):
        if not self.inv:
            return
        atts = self.db.list_attachments(self.inv.id)
        row = self.att_list.row(item)
        if 0 <= row < len(atts) and atts[row].file_path:
            QDesktopServices.openUrl(QUrl.fromLocalFile(atts[row].file_path))

    def _accept(self):
        number = self.number.text().strip()
        if not number:
            QMessageBox.warning(self, "校验失败", "请填写发票号码")
            return
        if self.amount.value() <= 0:
            QMessageBox.warning(self, "校验失败", "请填写大于 0 的金额（价税合计）")
            return

        cat_id = self.cat.currentData()
        trip_id = self.trip.currentData()
        if trip_id == -1:
            trip_id = None
        status = self.status.currentData() or "pending"
        excl = round(self.amount.value() - self.tax.value(), 2)

        if self.inv:
            inv = self.inv
            inv.invoice_code = self.code.text().strip()
            inv.invoice_number = number
            inv.category_id = cat_id
            inv.amount = self.amount.value()
            inv.tax_amount = self.tax.value()
            inv.amount_excl_tax = excl
            inv.currency = self.currency.text().strip() or "CNY"
            inv.issue_date = self.date.date().toString("yyyy-MM-dd")
            inv.vendor_name = self.vendor.text().strip()
            inv.vendor_tax_id = self.vendor_tax.text().strip()
            inv.buyer_name = self.buyer.text().strip()
            inv.buyer_tax_id = self.buyer_tax.text().strip()
            inv.trip_id = trip_id
            inv.status = status
            inv.payment_method = self.pay.text().strip()
            inv.note = self.note.toPlainText().strip()
            self.db.update_invoice(inv)
        else:
            inv = Invoice(
                invoice_code=self.code.text().strip(),
                invoice_number=number,
                category_id=cat_id,
                amount=self.amount.value(),
                tax_amount=self.tax.value(),
                amount_excl_tax=excl,
                currency=self.currency.text().strip() or "CNY",
                issue_date=self.date.date().toString("yyyy-MM-dd"),
                vendor_name=self.vendor.text().strip(),
                vendor_tax_id=self.vendor_tax.text().strip(),
                buyer_name=self.buyer.text().strip(),
                buyer_tax_id=self.buyer_tax.text().strip(),
                trip_id=trip_id,
                status=status,
                payment_method=self.pay.text().strip(),
                note=self.note.toPlainText().strip(),
                source=config.SOURCE_MANUAL,
            )
            self.db.create_invoice(inv)
        self.accept()
