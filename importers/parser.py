# -*- coding: utf-8 -*-
"""
差旅搭子 - 发票解析器
从发票文本（PDF 抽取 / OCR 识别）中，用正则抽取关键字段，并给出分类建议与置信度。
解析为「尽力而为」，所有结果均可在导入确认环节人工修正。
"""
from __future__ import annotations

import re
import os
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class InvoiceDraft:
    """解析得到的发票草稿，供用户确认/编辑后再落库。"""
    invoice_code: str = ""
    invoice_number: str = ""
    category_key: str = "other"
    category_name: str = ""
    amount: float = 0.0
    tax_amount: float = 0.0
    amount_excl_tax: float = 0.0
    currency: str = "CNY"
    issue_date: str = ""
    vendor_name: str = ""
    vendor_tax_id: str = ""
    buyer_name: str = ""
    buyer_tax_id: str = ""
    source: str = "local"
    source_detail: str = ""
    raw_text: str = ""
    file_path: str = ""          # 原始文件（导入后作为附件）
    file_name: str = ""
    parse_confidence: float = 0.0
    warnings: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "invoice_code": self.invoice_code,
            "invoice_number": self.invoice_number,
            "category_key": self.category_key,
            "category_name": self.category_name,
            "amount": self.amount,
            "tax_amount": self.tax_amount,
            "amount_excl_tax": self.amount_excl_tax,
            "currency": self.currency,
            "issue_date": self.issue_date,
            "vendor_name": self.vendor_name,
            "vendor_tax_id": self.vendor_tax_id,
            "buyer_name": self.buyer_name,
            "buyer_tax_id": self.bendor_tax_id if hasattr(self, "bendor_tax_id") else self.buyer_tax_id,
            "source": self.source,
            "source_detail": self.source_detail,
            "file_path": self.file_path,
            "file_name": self.file_name,
            "parse_confidence": self.parse_confidence,
            "warnings": self.warnings,
        }


# ---------------------------------------------------------------------------
# 文本抽取
# ---------------------------------------------------------------------------
def extract_pdf_text(path: str) -> str:
    """用 pdfplumber 抽取 PDF 文本；失败返回空串。"""
    try:
        import pdfplumber
        texts = []
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                t = page.extract_text() or ""
                texts.append(t)
        return "\n".join(texts)
    except Exception as e:
        return ""


def extract_image_text(path: str) -> str:
    """对图片尝试 OCR；若未安装 tesseract/pytesseract 则返回空串。"""
    try:
        import pytesseract
        from PIL import Image
        return pytesseract.image_to_string(Image.open(path), lang="chi_sim+eng")
    except Exception:
        return ""


def extract_text(path: str) -> str:
    ext = os.path.splitext(path)[1].lower()
    if ext == ".pdf":
        return extract_pdf_text(path)
    if ext in (".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp"):
        return extract_image_text(path)
    # ofd / 其他：暂不支持文本抽取
    return ""


# ---------------------------------------------------------------------------
# 正则工具
# ---------------------------------------------------------------------------
def _first(pattern, text, flags=re.IGNORECASE):
    m = re.search(pattern, text, flags)
    return m


def _num(s: str) -> float:
    if not s:
        return 0.0
    s = s.replace(",", "").replace("，", "").strip()
    try:
        return float(s)
    except Exception:
        return 0.0


def _clean_name(s: str) -> str:
    if not s:
        return ""
    s = s.strip().strip("：:").strip()
    s = re.sub(r"\s+", " ", s)
    return s[:120]


# ---------------------------------------------------------------------------
# 字段解析
# ---------------------------------------------------------------------------
def _parse_invoice_number(text: str):
    # 优先 发票号码 + 数字（8~20 位）
    m = _first(r"发票号码[:：]?\s*([0-9]{8,20})", text)
    if m:
        return m.group(1)
    # No. 形式
    m = _first(r"(?:No\.?|NO\.?)\s*([0-9]{8,20})", text)
    if m:
        return m.group(1)
    # 电子发票 20 位
    m = _first(r"\b([0-9]{20})\b", text)
    if m:
        return m.group(1)
    return ""


def _parse_invoice_code(text: str):
    m = _first(r"发票代码[:：]?\s*([0-9]{10,12})", text)
    if m:
        return m.group(1)
    return ""


def _parse_date(text: str):
    # 2026年07月02日 / 2026-07-02 / 2026/07/02 / 2026.07.02
    m = _first(r"(20\d{2})\s*[-/年.]?\s*([0-1]?\d)\s*[-/月.]?\s*([0-3]?\d)", text)
    if m:
        y, mo, d = m.group(1), m.group(2).zfill(2), m.group(3).zfill(2)
        return f"{y}-{mo}-{d}"
    return ""


def _parse_amount_label(text: str, label: str):
    # 形如 价税合计 ¥553.00 或 价税合计：553.00
    m = _first(rf"{label}[:：]?\s*[¥￥]?\s*([0-9][0-9,]*\.?[0-9]*)", text)
    if m:
        return _num(m.group(1))
    return None


def _parse_tax_id(text: str, anchor: str):
    # anchor 之后同行/就近的 纳税人识别号（15~20 位字母数字）
    m = _first(rf"{anchor}.*?纳税人识别号[:：]?\s*([A-Z0-9]{{15,20}})", text, re.DOTALL)
    if m:
        return m.group(1)
    # 宽松：全文找一处 15~20 位字母数字（兜底）
    m = _first(r"\b([A-Z0-9]{15,20})\b", text)
    if m:
        return m.group(1)
    return ""


def _parse_name(text: str, anchor: str):
    # anchor 之后就近的「名称：xxx」，捕获到行尾并剔除后续标签
    m = _first(rf"{anchor}.*?名称[:：]\s*([^\n]+)", text, re.DOTALL)
    if m:
        val = m.group(1).strip()
        # 截断到下一个字段标签之前
        val = re.split(r"纳税人识别号|地址|电话|开户行|账号|银行", val)[0].strip()
        return _clean_name(val)
    return ""


# 分类关键词（按顺序匹配，命中即返回）
CATEGORY_KEYWORDS = [
    ("train", ["铁路", "火车", "高铁", "城际", "车票", "购票", "列车"]),
    ("flight", ["航空", "航班", "机票", "行程单", "民航", "登机", "客票"]),
    ("hotel", ["酒店", "宾馆", "住宿", "旅馆", "客栈", "度假村"]),
    ("taxi", ["出租", "网约车", "滴滴", "的士", "顺风车", "出行", "打车"]),
    ("meal", ["餐饮", "餐费", "餐厅", "饭店", "美食", "食品", "宴"]),
    ("fuel", ["汽油", "柴油", "加油", "过路", "高速", "通行费", "油费"]),
    ("office", ["办公", "文具", "超市", "商场", "京东", "苏宁", "文具"]),
]


def _suggest_category(text: str, filename: str = ""):
    blob = (text + " " + (filename or "")).lower()
    for key, kws in CATEGORY_KEYWORDS:
        for kw in kws:
            if kw.lower() in blob:
                return key
    return "other"


# ---------------------------------------------------------------------------
# 主解析入口
# ---------------------------------------------------------------------------
def parse_invoice_text(text: str, filename: str = "", source: str = "local",
                       file_path: str = "") -> InvoiceDraft:
    draft = InvoiceDraft(
        raw_text=text, source=source, file_path=file_path,
        file_name=os.path.basename(file_path) if file_path else filename,
    )
    if not text:
        draft.warnings.append("未能从文件中抽取到文本，请手工录入或确认 OCR 已配置")
        draft.parse_confidence = 0.0
        return draft

    draft.invoice_number = _parse_invoice_number(text)
    draft.invoice_code = _parse_invoice_code(text)
    draft.issue_date = _parse_date(text)

    # 金额：优先 价税合计，其次 合计，再次 金额
    amount = _parse_amount_label(text, "价税合计")
    if amount is None:
        amount = _parse_amount_label(text, "合计")
    if amount is None:
        amount = _parse_amount_label(text, "金额")
    if amount is not None:
        draft.amount = amount

    tax = _parse_amount_label(text, "税额")
    if tax is not None:
        draft.tax_amount = tax

    excl = _parse_amount_label(text, "金额")
    if excl is not None:
        draft.amount_excl_tax = excl

    # 不含税金额推导：优先用识别到的「金额」，否则用 价税合计-税额
    if draft.amount:
        if draft.tax_amount and not draft.amount_excl_tax:
            draft.amount_excl_tax = round(draft.amount - draft.tax_amount, 2)
        elif not draft.amount_excl_tax:
            draft.amount_excl_tax = draft.amount

    draft.vendor_name = _parse_name(text, "销售方")
    if not draft.vendor_name:
        draft.vendor_name = _parse_name(text, "开票方")
    draft.vendor_tax_id = _parse_tax_id(text, "销售方")

    draft.buyer_name = _parse_name(text, "购买方")
    draft.buyer_tax_id = _parse_tax_id(text, "购买方")

    # 分类建议
    draft.category_key = _suggest_category(text, draft.file_name)

    # 置信度：关键字段命中数 / 总关键字段数
    keys = [draft.invoice_number, draft.amount > 0, draft.issue_date,
            draft.vendor_name]
    hit = sum(1 for k in keys if k)
    draft.parse_confidence = round(hit / len(keys), 2)
    if not draft.invoice_number:
        draft.warnings.append("未识别到发票号码，建议手工补充以便去重")
    if draft.amount <= 0:
        draft.warnings.append("未识别到金额，请手工填写")

    return draft


def parse_file(path: str, source: str = "local") -> InvoiceDraft:
    """直接解析一个本地文件（PDF/图片）。"""
    text = extract_text(path)
    return parse_invoice_text(text, filename=os.path.basename(path),
                              source=source, file_path=path)
