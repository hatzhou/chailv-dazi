# -*- coding: utf-8 -*-
"""链接导入：粘贴发票文件 URL，下载后解析。"""
from __future__ import annotations

import os
import tempfile
from typing import Optional, Tuple

import requests

from config import SUPPORTED_EXTS
from .parser import parse_file, InvoiceDraft


def fetch_url_invoice(url: str, timeout: int = 30,
                      headers: dict = None) -> Tuple[Optional[InvoiceDraft], str]:
    """下载 URL 指向的发票文件并解析，返回 (草稿, 错误信息)。"""
    if not url or not url.startswith("http"):
        return None, "无效的 URL（需以 http/https 开头）"
    try:
        resp = requests.get(url, timeout=timeout, headers=headers or {},
                            allow_redirects=True)
        if resp.status_code != 200:
            return None, f"下载失败：HTTP {resp.status_code}"
        content = resp.content
        if not content:
            return None, "下载内容为空"

        # 从 URL 或 Content-Type 推断扩展名
        fname = os.path.basename(url.split("?")[0]) or "invoice"
        ctype = resp.headers.get("Content-Type", "")
        ext = os.path.splitext(fname)[1].lower()
        if not ext:
            if "pdf" in ctype:
                ext = ".pdf"
            elif "image" in ctype:
                ext = ".png"
            elif "ofd" in ctype:
                ext = ".ofd"
            else:
                ext = ".pdf"
        if ext not in SUPPORTED_EXTS:
            return None, f"不支持的文件类型 {ext}"

        tmp = os.path.join(tempfile.gettempdir(), f"cld_url_{abs(hash(url))}{ext}")
        with open(tmp, "wb") as f:
            f.write(content)

        if ext == ".ofd":
            d = InvoiceDraft(source="url", file_path=tmp, file_name=fname,
                             source_detail=url)
            d.warnings.append("OFD 暂不支持文本抽取，请手工录入")
            return d, ""
        d = parse_file(tmp, source="url")
        d.source_detail = url
        return d, ""
    except Exception as e:
        return None, f"链接下载/解析失败：{e}"
