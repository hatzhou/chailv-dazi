# -*- coding: utf-8 -*-
"""差旅搭子 - 设置对话框（数据目录、关于）。"""
from __future__ import annotations

import os
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QFormLayout, QLabel,
                               QPushButton, QDialogButtonBox, QMessageBox, QGroupBox)
from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices

import config
from db.database import InvoiceDB


class SettingsDialog(QDialog):
    def __init__(self, db: InvoiceDB, parent=None):
        super().__init__(parent)
        self.db = db
        self.setWindowTitle("设置 / 关于")
        self.resize(480, 360)
        self._build()

    def _build(self):
        root = QVBoxLayout(self)
        # 数据
        g1 = QGroupBox("数据存储")
        f1 = QFormLayout(g1)
        f1.addRow("数据库文件", QLabel(config.DB_PATH))
        f1.addRow("附件目录", QLabel(config.ATTACHMENT_DIR))
        f1.addRow("说明", QLabel("数据均保存在本机，未上传云端。\n"
                              "修改数据目录需退出后编辑启动配置并重启。"))
        btn_open = QPushButton("打开数据目录")
        btn_open.clicked.connect(lambda: QDesktopServices.openUrl(
            QUrl.fromLocalFile(os.path.dirname(config.DB_PATH))))
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
        bb.rejected.connect(self.reject)
        root.addWidget(bb)
