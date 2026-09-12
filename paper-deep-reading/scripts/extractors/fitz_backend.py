"""fitz_backend.py — PyMuPDF (fitz) 后端。

Python 原生 PDF 解析库，无需 CLI。
- 优点：无外部依赖；layout 信息丰富；可与图片提取共享
- 缺点：pip install pymupdf（首次较慢）

依赖：`pip install pymupdf`
检测：通过 `extractors.HAS_FITZ`
"""

from __future__ import annotations

from typing import List, Tuple

from . import HAS_FITZ


def extract_with_fitz(pdf_path: str) -> Tuple[str, int]:
    """后端 2：PyMuPDF(fitz)。"""
    if not HAS_FITZ:
        return "", 0
    doc = None
    try:
        doc = fitz.open(pdf_path)
        page_count = doc.page_count
        parts: List[str] = []
        for page in doc:
            parts.append(page.get_text("text") or "")
        return "\n".join(parts), page_count
    except Exception:
        return "", 0
    finally:
        if doc is not None:
            try:
                doc.close()
            except Exception:
                pass
