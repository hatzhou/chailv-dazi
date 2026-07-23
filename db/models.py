# -*- coding: utf-8 -*-
"""
差旅搭子 - 数据模型定义
使用 dataclass 描述业务对象，便于在 UI 与数据库层之间传递。
"""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class Category:
    id: Optional[int] = None
    key: str = ""
    name: str = ""
    icon: str = "📄"
    default_status: str = "pending"
    sort_order: int = 0

    def __str__(self) -> str:
        return f"{self.icon} {self.name}"


@dataclass
class Trip:
    id: Optional[int] = None
    name: str = ""
    destination: str = ""
    start_date: str = ""     # YYYY-MM-DD
    end_date: str = ""       # YYYY-MM-DD
    budget: float = 0.0
    note: str = ""
    created_at: str = ""

    @property
    def date_range(self) -> str:
        if self.start_date and self.end_date:
            return f"{self.start_date} ~ {self.end_date}"
        return self.start_date or self.end_date or "-"


@dataclass
class Attachment:
    id: Optional[int] = None
    invoice_id: Optional[int] = None
    file_path: str = ""
    file_name: str = ""
    file_type: str = ""      # pdf / image / ofd
    file_size: int = 0
    created_at: str = ""


@dataclass
class Invoice:
    id: Optional[int] = None
    invoice_code: str = ""        # 发票代码
    invoice_number: str = ""      # 发票号码
    category_id: Optional[int] = None
    category_name: str = ""       # 冗余存储，便于列表展示
    category_icon: str = ""
    amount: float = 0.0           # 价税合计（元）
    tax_amount: float = 0.0       # 税额
    amount_excl_tax: float = 0.0  # 不含税金额
    currency: str = "CNY"
    issue_date: str = ""          # 开票日期 YYYY-MM-DD
    vendor_name: str = ""         # 销售方名称
    vendor_tax_id: str = ""       # 销售方税号
    buyer_name: str = ""          # 购买方名称
    buyer_tax_id: str = ""        # 购买方税号
    trip_id: Optional[int] = None
    trip_name: str = ""           # 冗余
    status: str = "pending"
    payment_method: str = ""      # 支付方式
    note: str = ""
    source: str = "manual"
    source_detail: str = ""
    created_at: str = ""
    updated_at: str = ""
    attachments: list = field(default_factory=list)

    @property
    def status_label(self) -> str:
        from config import INVOICE_STATUS
        return dict(INVOICE_STATUS).get(self.status, self.status)

    @property
    def source_label(self) -> str:
        from config import SOURCE_LABELS
        return SOURCE_LABELS.get(self.source, self.source)
