"""io_utils.py — 跨平台 I/O 辅助函数（Windows GBK 控制台兼容、文本编码探测）。"""

from __future__ import annotations

import sys
from typing import Optional


def _setup_io() -> None:
    """确保 stdin/stdout/stderr 使用 UTF-8（Windows GBK 控制台兼容）。"""
    for stream in (sys.stdin, sys.stdout, sys.stderr):
        try:
            if stream is not None and hasattr(stream, "reconfigure"):
                stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


def _write_stdout(text: str) -> None:
    """以 UTF-8 安全地写标准输出（Windows 控制台兼容）。"""
    try:
        sys.stdout.write(text)
        sys.stdout.flush()
    except UnicodeEncodeError:
        sys.stdout.buffer.write(text.encode("utf-8", errors="replace"))
        sys.stdout.buffer.flush()


def _read_text_file(path: str) -> str:
    """读取文本文件，自动尝试多种编码（UTF-8 → GBK → latin-1 兜底）。"""
    for enc in ("utf-8-sig", "utf-8", "gb18030", "gbk", "latin-1"):
        try:
            with open(path, "r", encoding=enc) as fh:
                return fh.read()
        except (UnicodeDecodeError, UnicodeError):
            continue
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        return fh.read()


__all__ = ["_setup_io", "_write_stdout", "_read_text_file"]
