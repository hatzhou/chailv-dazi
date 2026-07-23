# -*- coding: utf-8 -*-
"""差旅搭子 - 行程新增/编辑对话框。"""
from __future__ import annotations

from PySide6.QtWidgets import (QDialog, QVBoxLayout, QFormLayout, QLineEdit,
                               QDoubleSpinBox, QTextEdit, QDialogButtonBox,
                               QLabel, QGroupBox)
from PySide6.QtCore import Qt, QDate

from db.database import InvoiceDB
from db.models import Trip
from ui.date_picker import DatePicker


class TripDialog(QDialog):
    def __init__(self, db: InvoiceDB, trip_id: int = None, parent=None):
        super().__init__(parent)
        self.db = db
        self.trip_id = trip_id
        self.trip = self.db.get_trip(trip_id) if trip_id else None
        self.setWindowTitle("编辑行程" if trip_id else "新建行程")
        self.resize(420, 320)
        self._build()
        if self.trip:
            self._load()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(12)
        g = QGroupBox("行程信息")
        f = QFormLayout(g)
        f.setLabelAlignment(Qt.AlignRight)
        f.setSpacing(10)
        f.setContentsMargins(16, 18, 16, 16)
        self.name = QLineEdit()
        self.dest = QLineEdit()
        self.start = DatePicker()
        self.start.setDisplayFormat("yyyy-MM-dd")
        self.start.setDate(QDate.currentDate())
        self.end = DatePicker()
        self.end.setDisplayFormat("yyyy-MM-dd")
        self.end.setDate(QDate.currentDate())
        self.budget = QDoubleSpinBox()
        self.budget.setRange(0, 99999999)
        self.budget.setDecimals(2)
        self.budget.setPrefix("¥")
        self.note = QTextEdit()
        self.note.setMaximumHeight(60)
        f.addRow("行程名称 *", self.name)
        f.addRow("目的地", self.dest)
        f.addRow("开始日期", self.start)
        f.addRow("结束日期", self.end)
        f.addRow("预算", self.budget)
        f.addRow("备注", self.note)
        root.addWidget(g)
        bb = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        bb.button(QDialogButtonBox.Save).setObjectName("primary")
        bb.button(QDialogButtonBox.Save).setText(" 保存")
        bb.button(QDialogButtonBox.Cancel).setText(" 取消")
        bb.accepted.connect(self._accept)
        bb.rejected.connect(self.reject)
        root.addWidget(bb)

    def _load(self):
        t = self.trip
        self.name.setText(t.name)
        self.dest.setText(t.destination)
        if t.start_date:
            self.start.setDate(QDate.fromString(t.start_date, "yyyy-MM-dd"))
        if t.end_date:
            self.end.setDate(QDate.fromString(t.end_date, "yyyy-MM-dd"))
        self.budget.setValue(t.budget)
        self.note.setPlainText(t.note)

    def _accept(self):
        name = self.name.text().strip()
        if not name:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "校验失败", "请填写行程名称")
            return
        if self.trip:
            t = self.trip
            t.name = name
            t.destination = self.dest.text().strip()
            t.start_date = self.start.date().toString("yyyy-MM-dd")
            t.end_date = self.end.date().toString("yyyy-MM-dd")
            t.budget = self.budget.value()
            t.note = self.note.toPlainText().strip()
            self.db.update_trip(t)
        else:
            t = Trip(
                name=name,
                destination=self.dest.text().strip(),
                start_date=self.start.date().toString("yyyy-MM-dd"),
                end_date=self.end.date().toString("yyyy-MM-dd"),
                budget=self.budget.value(),
                note=self.note.toPlainText().strip(),
            )
            self.db.create_trip(t)
        self.accept()
