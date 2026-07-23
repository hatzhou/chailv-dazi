# -*- coding: utf-8 -*-
"""邮件导入：通过 IMAP 拉取发票附件并解析。"""
from __future__ import annotations

import os
import imaplib
import email
import email.header
import tempfile
from datetime import datetime, timedelta
from typing import List, Tuple

from config import SUPPORTED_EXTS
from .parser import parse_file, InvoiceDraft

# 已知发票发送方特征（邮箱名/域名关键字）
KNOWN_SENDERS = ["12306", "air", "flight", "ctrip", "trip", "hotel", "hilton",
                 "marriott", "huazhu", "dida", "didi", "uber", "tax", "invoice",
                 "fapiao", "增值税", "电子发票"]


def _decode_header(val: str) -> str:
    if not val:
        return ""
    parts = email.header.decode_header(val)
    out = []
    for b, enc in parts:
        if isinstance(b, bytes):
            out.append(b.decode(enc or "utf-8", "ignore"))
        else:
            out.append(str(b))
    return "".join(out)


def _looks_like_invoice(filename: str, from_addr: str) -> bool:
    fn = (filename or "").lower()
    if any(fn.endswith(ext) for ext in SUPPORTED_EXTS):
        if "发票" in fn or "invoice" in fn or "fp" in fn or fn.endswith((".pdf", ".ofd")):
            return True
    # 来自已知发送方且为可解析附件
    if any(k in (from_addr or "").lower() for k in KNOWN_SENDERS):
        if fn.endswith((".pdf", ".ofd", ".png", ".jpg", ".jpeg")):
            return True
    return False


def fetch_email_invoices(host: str, user: str, password: str,
                         since_days: int = 30, folder: str = "INBOX",
                         use_ssl: bool = True) -> Tuple[List[InvoiceDraft], List[str]]:
    """连接 IMAP 邮箱，拉取近期含发票附件的邮件，返回 (草稿列表, 错误/提示)。"""
    drafts: List[InvoiceDraft] = []
    errors: List[str] = []
    if not (host and user and password):
        return drafts, ["请填写完整的邮箱、密码（授权码）与服务器信息"]

    try:
        if use_ssl:
            conn = imaplib.IMAP4_SSL(host, 993, timeout=30)
        else:
            conn = imaplib.IMAP4(host, 143, timeout=30)
            try:
                conn.starttls()
            except Exception:
                pass
        conn.login(user, password)
    except Exception as e:
        return drafts, [f"邮箱连接/登录失败：{e}"]

    try:
        typ, _ = conn.select(folder)
        if typ != "OK":
            errors.append(f"无法打开邮箱文件夹：{folder}")
            conn.logout()
            return drafts, errors

        since = (datetime.now() - timedelta(days=since_days)).strftime("%d-%b-%Y")
        typ, data = conn.search(None, "SINCE", since)
        if typ != "OK" or not data or not data[0]:
            errors.append(f"近 {since_days} 天未检索到邮件")
            conn.logout()
            return drafts, errors

        msg_ids = data[0].split()
        for mid in msg_ids:
            try:
                typ, msg_data = conn.fetch(mid, "(RFC822)")
                if typ != "OK":
                    continue
                raw = msg_data[0][1]
                msg = email.message_from_bytes(raw)
                from_addr = _decode_header(msg.get("From", ""))
                for part in msg.walk():
                    if part.get_content_maintype() == "multipart":
                        continue
                    fn = part.get_filename()
                    if not fn:
                        continue
                    fn = _decode_header(fn)
                    if not _looks_like_invoice(fn, from_addr):
                        continue
                    payload = part.get_payload(decode=True)
                    if not payload:
                        continue
                    ext = os.path.splitext(fn)[1].lower() or ".pdf"
                    tmp = os.path.join(tempfile.gettempdir(), f"cld_mail_{mid.decode()}_{fn}")
                    with open(tmp, "wb") as f:
                        f.write(payload)
                    if ext == ".ofd":
                        d = InvoiceDraft(source="email", file_path=tmp, file_name=fn,
                                         source_detail=from_addr)
                        d.warnings.append("OFD 暂不支持文本抽取，请手工录入")
                    else:
                        d = parse_file(tmp, source="email")
                        d.source_detail = from_addr
                    drafts.append(d)
            except Exception as e:
                errors.append(f"处理邮件 {mid} 出错：{e}")
        conn.logout()
    except Exception as e:
        errors.append(f"邮件处理异常：{e}")
        try:
            conn.logout()
        except Exception:
            pass

    if not drafts:
        errors.append("未找到可解析的发票附件（可放宽时间范围或检查发件人）")
    return drafts, errors
