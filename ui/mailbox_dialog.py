# -*- coding: utf-8 -*-
"""差旅搭子 - 邮箱拉取账号 新增/编辑对话框。"""
from __future__ import annotations

from PySide6.QtWidgets import (QDialog, QVBoxLayout, QFormLayout, QLineEdit,
                               QSpinBox, QCheckBox, QDialogButtonBox, QGroupBox,
                               QComboBox)
from PySide6.QtCore import Qt

from db.database import InvoiceDB
from db.models import Mailbox


class MailboxDialog(QDialog):
    def __init__(self, db: InvoiceDB, mailbox_id: int = None, parent=None):
        super().__init__(parent)
        self.db = db
        self.mb = self.db.get_mailbox(mailbox_id) if mailbox_id else None
        self.setWindowTitle("编辑邮箱账号" if mailbox_id else "新增邮箱账号")
        self.resize(440, 320)
        self._build()
        if self.mb:
            self._load()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(12)

        g = QGroupBox("邮箱账号")
        f = QFormLayout(g)
        f.setLabelAlignment(Qt.AlignRight)
        f.setSpacing(10)
        f.setContentsMargins(16, 18, 16, 16)

        self.name = QLineEdit()
        self.name.setPlaceholderText("如：工作邮箱")
        self.host = QComboBox()
        self.host.setEditable(True)
        for label, host in self._common_hosts():
            self.host.addItem(f"{label} ({host})", host)
        self.user = QLineEdit()
        self.user.setPlaceholderText("如：name@example.com")
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.Password)
        self.password.setPlaceholderText("邮箱密码或授权码")
        self.ssl = QCheckBox("使用 SSL")
        self.ssl.setChecked(True)
        self.days = QSpinBox()
        self.days.setRange(1, 365)
        self.days.setValue(30)
        self.enabled = QCheckBox("参与「拉取全部」")
        self.enabled.setChecked(True)

        f.addRow("备注名", self.name)
        f.addRow("IMAP 服务器", self.host)
        f.addRow("邮箱账号", self.user)
        f.addRow("密码 / 授权码", self.password)
        f.addRow("加密", self.ssl)
        f.addRow("检索近 N 天", self.days)
        f.addRow("启用", self.enabled)
        root.addWidget(g)

        bb = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        bb.button(QDialogButtonBox.Save).setObjectName("primary")
        bb.button(QDialogButtonBox.Save).setText(" 保存")
        bb.button(QDialogButtonBox.Cancel).setText(" 取消")
        bb.accepted.connect(self._accept)
        bb.rejected.connect(self.reject)
        root.addWidget(bb)

    @staticmethod
    def _common_hosts():
        from config import COMMON_IMAP_HOSTS
        return COMMON_IMAP_HOSTS

    def _load(self):
        mb = self.mb
        self.name.setText(mb.name)
        idx = self.host.findData(mb.host)
        if idx >= 0:
            self.host.setCurrentIndex(idx)
        else:
            self.host.setEditText(mb.host)
        self.user.setText(mb.user)
        self.password.setText(mb.password)
        self.ssl.setChecked(mb.use_ssl)
        self.days.setValue(mb.since_days)
        self.enabled.setChecked(mb.enabled)

    def _accept(self):
        user = self.user.text().strip()
        if not user:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "校验失败", "请填写邮箱账号")
            return
        host = self.host.currentData() or self.host.currentText().strip()
        if not host:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "校验失败", "请填写 IMAP 服务器")
            return
        if self.mb:
            mb = self.mb
            mb.name = self.name.text().strip()
            mb.host = host
            mb.user = user
            mb.password = self.password.text().strip()
            mb.use_ssl = self.ssl.isChecked()
            mb.since_days = self.days.value()
            mb.enabled = self.enabled.isChecked()
            self.db.update_mailbox(mb)
        else:
            mb = Mailbox(
                name=self.name.text().strip(),
                host=host,
                user=user,
                password=self.password.text().strip(),
                use_ssl=self.ssl.isChecked(),
                since_days=self.days.value(),
                enabled=self.enabled.isChecked(),
            )
            self.db.create_mailbox(mb)
        self.accept()
