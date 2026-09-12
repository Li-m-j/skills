"""pdftotext_backend.py — poppler pdftotext 命令行后端。

通过 `pdftotext <pdf> -` 调用 poppler-utils 提取文本。
- 优点：CLI 工具，无 Python 依赖；适合双栏论文（默认阅读顺序）
- 缺点：需要系统安装 poppler；不擅长复杂布局

依赖：系统 `pdftotext` 命令（poppler-utils / poppler-tools / xpdf）
"""

from __future__ import annotations

import subprocess
from typing import Tuple

from . import _subprocess_flags, get_page_count


def extract_with_pdftotext(pdf_path: str) -> Tuple[str, int]:
    """后端 1：调用 poppler 的 pdftotext（默认阅读顺序，适合双栏论文）。"""
    cmd = ["pdftotext", pdf_path, "-"]
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=180,
            check=False,
            creationflags=_subprocess_flags(),
        )
    except (FileNotFoundError, OSError, subprocess.TimeoutExpired):
        return "", 0
    if proc.returncode != 0:
        return "", 0
    text = proc.stdout or ""
    return text, get_page_count(pdf_path)
