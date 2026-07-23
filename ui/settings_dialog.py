# -*- coding: utf-8 -*-
"""差旅搭子 - 设置对话框（数据存储位置、发票识别、关于）。"""
from __future__ import annotations

import os
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QFormLayout, QLabel,
                               QPushButton, QDialogButtonBox, QMessageBox, QGroupBox,
                               QLineEdit, QHBoxLayout, QFileDialog)
from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices

import config
from db.database import InvoiceDB


class SettingsDialog(QDialog):
    def __init__(self, db: InvoiceDB, parent=None):
        super().__init__(parent)
        self.db = db
        self.setWindowTitle("设置 / 关于")
        self.resize(520, 400)
        self._build()

    def _build(self):
        root = QVBoxLayout(self)
        # 数据
        g1 = QGroupBox("数据存储")
        f1 = QFormLayout(g1)
        f1.addRow("数据库文件", QLabel(config.DB_PATH))
        # 文件存储位置（可编辑）
        self.storage_edit = QLineEdit(self.db.get_setting("attachment_dir", config.ATTACHMENT_DIR))
        browse = QPushButton(" 浏览")
        browse.setIcon(self._icon("file", "#475569", 15))
        browse.clicked.connect(self._browse_storage)
        storage_row = QHBoxLayout()
        storage_row.addWidget(self.storage_edit, 1)
        storage_row.addWidget(browse)
        f1.addRow("文件存储位置", storage_row)
        f1.addRow("说明", QLabel("下载 / 导入的发票原件（PDF、图片等）\n"
                              "会保存到此处；修改后新文件将存入新位置。\n"
                              "修改数据目录需退出后编辑启动配置并重启。"))
        btn_open = QPushButton(" 打开存储目录")
        btn_open.setIcon(self._icon("folder", "#475569", 15))
        btn_open.clicked.connect(lambda: QDesktopServices.openUrl(
            QUrl.fromLocalFile(self.storage_edit.text())))
        f1.addRow("", btn_open)
        root.addWidget(g1)

        # 解析
        g2 = QGroupBox("发票识别")
        f2 = QFormLayout(g2)
        f2.addRow("PDF 文本", QLabel("已启用（pdfplumber）"))
        f2.addRow("图片 OCR", QLabel("如已安装 tesseract + 中文包则自动启用，\n"
                                  "否则图片类发票请手工录入。"))
        root.addWidget(g2)

        # 关于
        g3 = QGroupBox("关于")
        f3 = QFormLayout(g3)
        f3.addRow("软件名称", QLabel(f"{config.APP_NAME} v{config.APP_VERSION}"))
        f3.addRow("技术栈", QLabel("Python + PySide6 + SQLite"))
        f3.addRow("用途", QLabel("差旅发票集中管理 / 报销归集"))
        root.addWidget(g3)
        root.addStretch(1)

        bb = QDialogButtonBox(QDialogButtonBox.Close)
        bb.button(QDialogButtonBox.Close).setText(" 关闭")
        bb.rejected.connect(self._save_and_close)
        root.addWidget(bb)

    def _icon(self, name, color, size):
        from ui.icons import icon as _icon
        return _icon(name, color, size)

    def _browse_storage(self):
        path = QFileDialog.getExistingDirectory(
            self, "选择文件存储位置", self.storage_edit.text() or os.path.expanduser("~"))
        if path:
            self.storage_edit.setText(path)

    def _save_and_close(self):
        path = self.storage_edit.text().strip()
        if path:
            try:
                self.db.set_attachment_dir(path)
            except Exception as e:
                QMessageBox.warning(self, "设置失败", f"无法使用该目录：{e}")
                return
        self.reject()
