# -*- coding: utf-8 -*-
"""本地文件导入：支持 PDF / OFD / 图片多选，逐个解析为发票草稿。"""
from __future__ import annotations

import os
from typing import List, Tuple

from config import SUPPORTED_EXTS
from .parser import parse_file, InvoiceDraft


def parse_local_files(paths: List[str]) -> List[Tuple[InvoiceDraft, List[str]]]:
    """解析本地文件列表，返回 [(草稿, 该文件警告)]。
    不支持的文本型文件（如 ofd 暂不支持文本抽取）仍会生成草稿，仅保留附件供手工录入。
    """
    results = []
    for p in paths:
        ext = os.path.splitext(p)[1].lower()
        warns = []
        if ext not in SUPPORTED_EXTS:
            warns.append(f"不支持的文件类型 {ext}，已跳过")
            results.append((None, warns))
            continue
        if not os.path.exists(p):
            warns.append(f"文件不存在：{p}")
            results.append((None, warns))
            continue
        if ext == ".ofd":
            warns.append("OFD 暂不支持文本抽取，已保留文件，请手工录入")
            d = InvoiceDraft(source="local", file_path=p,
                             file_name=os.path.basename(p))
            d.warnings.append(warns[0])
            results.append((d, warns))
            continue
        draft = parse_file(p, source="local")
        results.append((draft, draft.warnings))
    return results
