"""extractors/ — PDF 多后端文本提取子包。

提供三个文本提取后端（pdftotext / PyMuPDF / pdfplumber）的统一探测与调度入口：

- `HAS_FITZ`, `HAS_PDFPLUMBER` — 可选依赖探测
- `_subprocess_flags()` — Windows 避免弹控制台窗口
- `_pdftotext_available()` — 探测 poppler pdftotext 命令
- `get_page_count()` — 多后端页数获取 + 正则兜底
- 各后端实现：`pdftotext_backend.py` / `fitz_backend.py` / `pdfplumber_backend.py`
- `extract_with_fallback()` — 按优先级尝试所有可用后端（v0.3.0 新增）
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from typing import List, Optional, Tuple

# ---------------------------------------------------------------------------
# 可选依赖探测（不强制安装，缺失时自动降级）
# ---------------------------------------------------------------------------
try:  # pragma: no cover - 取决于运行环境
    import fitz  # type: ignore  # PyMuPDF
    HAS_FITZ = True
except Exception:
    HAS_FITZ = False

try:  # pragma: no cover - 取决于运行环境
    import pdfplumber  # type: ignore
    HAS_PDFPLUMBER = True
except Exception:
    HAS_PDFPLUMBER = False


def _subprocess_flags() -> int:
    """Windows 下避免弹出控制台窗口。"""
    if os.name == "nt":
        return getattr(subprocess, "CREATE_NO_WINDOW", 0)
    return 0


def _pdftotext_available() -> bool:
    """探测 poppler 的 pdftotext 命令是否存在。

    注意：`pdftotext -v` 在 poppler/xpdf 各版本中普遍返回非 0（如 99），
    因此只要命令能启动（未抛 FileNotFoundError/OSError）即视为可用。
    """
    try:
        subprocess.run(
            ["pdftotext", "-v"],
            capture_output=True,
            timeout=10,
            check=False,
            creationflags=_subprocess_flags(),
        )
        return True
    except (FileNotFoundError, OSError, subprocess.TimeoutExpired):
        return False


def _page_count_regex(pdf_path: str) -> int:
    """正则兜底：统计 PDF 中 /Type /Page 对象（排除 /Type /Pages）。"""
    try:
        with open(pdf_path, "rb") as fh:
            data = fh.read()
        matches = re.findall(rb"/Type\s*/Page[^s]", data)
        return len(matches)
    except Exception:
        return 0


def get_page_count(pdf_path: str) -> int:
    """获取 PDF 页数：PyMuPDF → pdfplumber → 正则兜底。"""
    if HAS_FITZ:
        doc = None
        try:
            doc = fitz.open(pdf_path)  # type: ignore
            return doc.page_count
        except Exception:
            pass
        finally:
            if doc is not None:
                try:
                    doc.close()  # type: ignore
                except Exception:
                    pass
    if HAS_PDFPLUMBER:
        try:
            with pdfplumber.open(pdf_path) as pdf:  # type: ignore
                return len(pdf.pages)
        except Exception:
            pass
    return _page_count_regex(pdf_path)


# ---------------------------------------------------------------------------
# 多后端统一提取入口（v0.3.0 新增）
# ---------------------------------------------------------------------------
# 独立成行的章节标题（与 sections.py 的行锚定正则同源思路，用于后端质量比较）
_HEADING_LINE_RE = re.compile(
    r"(?im)^\s*(\d+(\.\d+)*\.?\s*)?"
    r"(abstract|summary|introduction|methods?|methodology|computational\s+\w+|"
    r"results?(?:\s+and\s+discussion)?|discussion|conclusions?|outlook|"
    r"摘\s*要|引言|绪论|前言|方法|计算.{0,4}法?|结果|讨论|结论|展望)\s*$"
)


def _heading_hits(text: str) -> int:
    return len(_HEADING_LINE_RE.findall(text))


def extract_with_fallback(pdf_path: str) -> Tuple[str, int, str]:
    """按优先级尝试所有可用后端，返回 (text, page_count, extractor_used)。

    优先级：pdftotext（poppler，CLI）→ PyMuPDF(fitz) → pdfplumber。
    pdftotext raw 模式会把章节标题并入同行段落，若其结果中没有任何
    独立成行的章节标题，则继续尝试后续后端并优先采用有标题行的结果。
    全部失败返回 ("", 0, "none")。

    这是 v0.3.0 拆分后由 `pdf_extractor.extract_pdf()` 调用的统一入口。
    """
    from extractors.pdftotext_backend import extract_with_pdftotext
    from extractors.fitz_backend import extract_with_fitz
    from extractors.pdfplumber_backend import extract_with_pdfplumber

    attempts: List[Tuple[str, object]] = []
    if _pdftotext_available():
        attempts.append(("pdftotext", extract_with_pdftotext))
    if HAS_FITZ:
        attempts.append(("fitz", extract_with_fitz))
    if HAS_PDFPLUMBER:
        attempts.append(("pdfplumber", extract_with_pdfplumber))

    first_ok: Optional[Tuple[str, int, str]] = None
    for name, func in attempts:
        text, pages = func(pdf_path)  # type: ignore
        if not (text and text.strip()):
            continue
        hits = _heading_hits(text)
        if hits > 0 or first_ok is None:
            if hits > 0:
                return text, pages, name
            first_ok = (text, pages, name)
    return first_ok if first_ok is not None else ("", 0, "none")


__all__ = [
    "HAS_FITZ",
    "HAS_PDFPLUMBER",
    "_subprocess_flags",
    "_pdftotext_available",
    "_page_count_regex",
    "get_page_count",
    "extract_with_fallback",
]
