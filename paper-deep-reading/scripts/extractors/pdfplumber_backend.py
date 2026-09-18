"""pdfplumber_backend.py — pdfplumber 后端。

适合表格密集型论文（pdfplumber 对 table 提取较好）。
- 优点：表格提取准确
- 缺点：纯文本提取速度比 fitz 慢

依赖：`pip install pdfplumber`
检测：通过 `extractors.HAS_PDFPLUMBER`
"""

from __future__ import annotations

from typing import Tuple

from . import HAS_PDFPLUMBER


def extract_with_pdfplumber(pdf_path: str) -> Tuple[str, int]:
    """后端 3：pdfplumber。"""
    if not HAS_PDFPLUMBER:
        return "", 0
    import pdfplumber  # type: ignore  # 延迟 import；HAS_PDFPLUMBER 已确认
    try:
        with pdfplumber.open(pdf_path) as pdf:  # type: ignore
            page_count = len(pdf.pages)
            parts = []
            for page in pdf.pages:
                parts.append(page.extract_text() or "")
        return "\n".join(parts), page_count
    except Exception:
        return "", 0
