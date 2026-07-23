# -*- coding: utf-8 -*-
"""导入落库助手：去重、关联分类/行程、保存附件。"""
from __future__ import annotations

import os
from typing import Optional, Tuple

from db.database import InvoiceDB
from db.models import Invoice
from .parser import InvoiceDraft


def save_draft(db: InvoiceDB, draft: InvoiceDraft,
               trip_id: Optional[int] = None,
               status: Optional[str] = None,
               copy_attachment: bool = True) -> Tuple[int, bool]:
    """将草稿保存为发票。返回 (发票id, 是否因重复而跳过)。
    若发票号码已存在则视为重复，不重复写入，返回原 id。
    """
    dup = db.find_duplicate(draft.invoice_number, draft.invoice_code)
    if dup:
        return dup.id, True

    cat = db.get_category_by_key(draft.category_key) or db.get_category_by_key("other")
    final_status = status or cat.default_status
    inv = Invoice(
        invoice_code=draft.invoice_code,
        invoice_number=draft.invoice_number,
        category_id=cat.id,
        amount=draft.amount,
        tax_amount=draft.tax_amount,
        amount_excl_tax=draft.amount_excl_tax,
        currency=draft.currency,
        issue_date=draft.issue_date,
        vendor_name=draft.vendor_name,
        vendor_tax_id=draft.vendor_tax_id,
        buyer_name=draft.buyer_name,
        buyer_tax_id=draft.buyer_tax_id,
        trip_id=trip_id,
        status=final_status,
        payment_method="",
        note="",
        source=draft.source,
        source_detail=draft.source_detail or "",
    )
    iid = db.create_invoice(inv)
    if draft.file_path and os.path.exists(draft.file_path):
        db.add_attachment(iid, draft.file_path, copy_to_storage=copy_attachment)
    return iid, False
