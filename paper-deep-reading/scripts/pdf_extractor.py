#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""pdf_extractor.py — 计算化学论文 PDF 文本提取与章节定位工具（thin orchestration · v0.3.0）。

v0.3.0 拆分：
- PDF 多后端提取 → `extractors/` 子包（pdftotext / fitz / pdfplumber）
- 章节定位 → `sections.py`
- 图表引用 → `figures.py`
- 关键图片抽取 → `images.py`
- I/O 工具 → `io_utils.py`
- 类型定义 → `models.py`（v0.3.0 命名；最初叫 `types.py`，但与 stdlib `types` 同名导致 import 失败，故改名）
- **本文件**：orchestration + CLI + 向后兼容 re-export

对外接口（向后兼容）：
  `from pdf_extractor import extract_pdf, detect_sections, ...` 仍然有效。

功能：
  1. 多后端自动提取 PDF 文本：pdftotext（poppler）→ PyMuPDF(fitz) → pdfplumber，
     任一后端失败自动降级到下一个，均不可用时给出明确提示。
  2. 自动定位核心章节：abstract / introduction / method / result / conclusion，
     支持中英文标题（含 "1 Introduction" / "2 计算方法" / "1. Introduction 引言" 等
     编号前缀与中英混排）。
  3. 自动提取图表引用（Figure / Fig. / Table / Scheme）与位置，输出
     figures_and_tables 列表，便于上层 Skill 重点精读。
  4. 自动提取候选图片池（按正文顺序，默认最多 12 张），输出 PNG 到临时目录，
     key_images 字段含本地路径，供上层 AI 选取 3-5 张嵌入 Markdown 报告。
  5. 启发式判断论文类型（7 类枚举）：article / review / perspective / account /
     letter / editorial / unknown。
  6. 自动识别正文末尾或 SI 中的"计算方法"补充，并入 method 章节。
  7. 无文本层时探测本机 OCR 能力，输出 ocr_hint 兜底指引。
  8. 输出 JSON：{full_text, sections, figures_and_tables, key_images, paper_type, ...}。

命令行用法：
  python pdf_extractor.py paper.pdf
  python pdf_extractor.py paper.pdf --pretty -o out.json
  python pdf_extractor.py paper.pdf --image-dir ./extracted_images --images-sort position
  python pdf_extractor.py notes.txt --text

依赖：
  仅使用 Python 标准库即可运行；PyMuPDF / pdfplumber 为可选增强，
  未安装时自动跳过对应后端。Windows / Linux / macOS 均兼容（UTF-8 编码）。
  图片提取依赖 PyMuPDF（fitz）；如未安装则 key_images 为空数组。

退出码：0 成功；1 输入文件不存在；2 提取失败（无文本层仍视为成功，通过
warning 字段提示，便于上层 Skill 判断）。
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from typing import Dict, List, Optional

# ---------------------------------------------------------------------------
# 拆分后子模块 import
# ---------------------------------------------------------------------------
from io_utils import _read_text_file, _setup_io, _write_stdout
from sections import SECTION_ORDER, SECTION_PATTERNS, detect_sections
from figures import extract_figures_and_tables
from images import extract_key_images
from extractors import (
    HAS_FITZ,
    HAS_PDFPLUMBER,
    extract_with_fallback,
    get_page_count,
)

# ---------------------------------------------------------------------------
# 向后兼容 re-export（让 `from pdf_extractor import X` 继续工作）
# ---------------------------------------------------------------------------
# 旧版 pdf_extractor.py 内部暴露的 public/private 名字
from extractors import _subprocess_flags, _pdftotext_available  # noqa: F401
from extractors.pdftotext_backend import extract_with_pdftotext  # noqa: F401
from extractors.fitz_backend import extract_with_fitz  # noqa: F401
from extractors.pdfplumber_backend import extract_with_pdfplumber  # noqa: F401
from figures import _FIG_LABEL_RE, _CAPTION_PREVIEW_MAX  # noqa: F401
from images import _DEFAULT_MIN_IMG_DIM  # noqa: F401
from sections import _is_substantial  # noqa: F401

__all__ = [
    # 顶层入口
    "extract_pdf",
    "process_text_file",
    "detect_paper_type",
    "build_ocr_hint",
    # 章节
    "detect_sections",
    "SECTION_ORDER",
    "SECTION_PATTERNS",
    # 图表与图片
    "extract_figures_and_tables",
    "extract_key_images",
    # 后端
    "extract_with_pdftotext",
    "extract_with_fitz",
    "extract_with_pdfplumber",
    "HAS_FITZ",
    "HAS_PDFPLUMBER",
    "get_page_count",
    # 内部（向后兼容）
    "_is_substantial",
    "_FIG_LABEL_RE",
    "_CAPTION_PREVIEW_MAX",
    "_DEFAULT_MIN_IMG_DIM",
    "_subprocess_flags",
    "_pdftotext_available",
]


# ---------------------------------------------------------------------------
# 论文类型启发式判断（v0.4：3 类 → 7 类枚举）
# ---------------------------------------------------------------------------
# 综述类典型信号（abstract / title 中）
_REVIEW_SIGNALS = re.compile(
    r"(?i)\b(this\s+review|a\s+review|we\s+review|reviews\s+of|"
    r"recent\s+advances?\s+in|progress\s+in|overview\s+of|"
    r"comprehensive\s+review|systematic\s+review|state[\-\s]of[\-\s]the[\-\s]art|"
    r"minireview|mini[\-\s]review|tutorial)\b"
    r"|[【\[(]?(综述|系统综述|综述论文|进展|评述|回顾)(?:[】\)\]、,;。 ]|$)"
)

# 观点 / 展望类（perspective / viewpoint / outlook）
_PERSPECTIVE_SIGNALS = re.compile(
    r"(?i)\b(perspective|viewpoint|our\s+view|outlook|opinion\s+piece|commentary\s+on)\b"
    r"|[【\[(]?(观点|展望|述评|见解)(?:[】\)\]、,;。 ]|$)"
)

# 研究历程 / 课题组进展类（Accounts 类）
_ACCOUNT_SIGNALS = re.compile(
    r"(?i)\b(in\s+this\s+account|this\s+account|our\s+journey|"
    r"lessons\s+learned|personal\s+account|accounts\s+of\s+chemical\s+research)\b"
)

# 社论 / 评论类
_EDITORIAL_SIGNALS = re.compile(
    r"(?i)\b(editorial|guest\s+editorial|this\s+issue\s+of|in\s+this\s+issue)\b"
)

# 快报 / 通讯类（Letter / Communication）
_LETTER_SIGNALS = re.compile(
    r"(?i)\b(rapid\s+communication|preliminary\s+communication|"
    r"we\s+report\s+herein|herein\s+we\s+report|"
    r"in\s+this\s+communication|in\s+this\s+letter|this\s+letter\s+describes)\b"
)


def detect_paper_type(
    full_text: str,
    sections: Dict[str, str],
    page_count: int = 0,
) -> str:
    """启发式判断论文类型，返回 7 类枚举之一。

    取值：`article` / `review` / `perspective` / `account` / `letter` / `editorial` / `unknown`

    规则（按优先级，先命中先返回）：
      1. 无文本 → "unknown"
      2. abstract / 开头含 "in this account" 等 → "account"
      3. abstract / 开头含 perspective / viewpoint / outlook → "perspective"
      4. abstract / 开头含 editorial / this issue → "editorial"
      5. abstract / 开头含综述信号（this review / 综述 / recent advances 等）→ "review"
      6. method 与 result 都为空，且 introduction + conclusion 非空（典型综述结构）→ "review"
      7. abstract / 开头含快报信号（in this communication / we report herein）→ "letter"
      8. 其余 → "article"

    注：该函数是启发式（准确率约 85%），用户可显式覆盖（见 SKILL.md §2 覆盖表）。
    """
    if not full_text or not full_text.strip():
        return "unknown"

    abstract = (sections.get("abstract") or "").strip()
    head = full_text[:400]
    probe = (abstract[:1500] + "\n" + head) if abstract else head

    # 2-4：细分类型信号
    if _ACCOUNT_SIGNALS.search(probe):
        return "account"
    if _PERSPECTIVE_SIGNALS.search(probe):
        return "perspective"
    if _EDITORIAL_SIGNALS.search(probe):
        return "editorial"

    # 5：综述信号
    if _REVIEW_SIGNALS.search(probe):
        return "review"

    # 6：结构信号（无方法/结果章，但有引言+结论）
    if not (sections.get("method") or "").strip() and not (sections.get("result") or "").strip():
        if (sections.get("introduction") or "").strip() and (
            sections.get("conclusion") or ""
        ).strip():
            return "review"

    # 7：快报信号（短篇幅时更可信）
    if _LETTER_SIGNALS.search(probe):
        return "letter"

    return "article"



# ---------------------------------------------------------------------------
# 顶层流程
# ---------------------------------------------------------------------------
def build_ocr_hint() -> Dict[str, object]:
    """探测本机 OCR 能力，返回给上层的兜底指引（v0.4 新增）。

    返回：{tesseract: bool, pdftoppm: bool, paddleocr: bool, hint: str}
    """
    import importlib.util
    import shutil as _shutil

    has_tess = bool(_shutil.which("tesseract"))
    has_pdftoppm = bool(_shutil.which("pdftoppm"))
    has_paddle = importlib.util.find_spec("paddleocr") is not None

    if has_tess and has_pdftoppm:
        hint = (
            'OCR 可用：pdftoppm -r 300 -png "in.pdf" page && tesseract page-1.png out -l eng+chi_sim'
        )
    elif has_tess:
        hint = 'OCR 可用（需先转图）：tesseract page.png out -l eng+chi_sim'
    elif has_paddle:
        hint = "OCR 可用（PaddleOCR）：python -c \"from paddleocr import PaddleOCR; PaddleOCR().ocr('page.png')\""
    else:
        hint = (
            "本机未检测到 OCR 引擎。任选其一安装后重试："
            "① winget install UB-Mannheim.TesseractOCR（另需 poppler 的 pdftoppm）；"
            "② pip install paddleocr paddlepaddle。"
            "或直接复制正文后粘贴给 AI。"
        )
    return {
        "tesseract": has_tess,
        "pdftoppm": has_pdftoppm,
        "paddleocr": has_paddle,
        "hint": hint,
    }


def extract_pdf(
    pdf_path: str,
    image_dir: Optional[str] = None,
    max_images: int = 12,
    images_sort: str = "position",
) -> Dict[str, object]:
    """提取 PDF 全文并定位章节，返回可直接 JSON 序列化的字典。

    参数：
      pdf_path:    PDF 文件路径
      image_dir:   候选图片输出目录（None 用临时目录）
      max_images:  候选图片池上限（v0.4 默认 12，供上层 AI 选取 3-5 张）
      images_sort: 候选排序，position（默认，正文顺序）/ caption / area
    """
    if not os.path.isfile(pdf_path):
        raise FileNotFoundError(f"PDF 文件不存在: {pdf_path}")

    # 多后端级联（pdftotext → fitz → pdfplumber）
    full_text, page_count, extractor_used = extract_with_fallback(pdf_path)

    if page_count == 0:
        page_count = get_page_count(pdf_path)

    sections = detect_sections(full_text)
    figures_and_tables = extract_figures_and_tables(full_text)
    key_images = extract_key_images(
        pdf_path, figures_and_tables,
        max_count=max_images,
        dest_dir=image_dir,
        sort_by=images_sort,
    )
    paper_type = detect_paper_type(full_text, sections, page_count=page_count)

    result: Dict[str, object] = {
        "input_file": os.path.abspath(pdf_path),
        "input_type": "pdf",
        "full_text": full_text,
        "sections": sections,
        "figures_and_tables": figures_and_tables,
        "key_images": key_images,
        "paper_type": paper_type,
        "page_count": page_count,
        "extractor_used": extractor_used,
        "has_text_layer": bool(full_text and full_text.strip()),
    }

    if not result["has_text_layer"]:
        result["warning"] = (
            "未能从 PDF 提取到文本层。该 PDF 可能为扫描件/图片型 PDF，"
            "请按 ocr_hint 走 OCR 分支，或直接粘贴论文文本后再分析。"
        )
        result["ocr_hint"] = build_ocr_hint()
    elif len(full_text.strip()) < 200:
        result["warning"] = (
            "提取到的文本量很少（疑似空页或加密 PDF），建议检查文件、改用 OCR 或粘贴文本。"
        )
        result["ocr_hint"] = build_ocr_hint()
    return result


def process_text_file(text_path: str) -> Dict[str, object]:
    """处理纯文本文件：读取全文并定位章节、图表、论文类型。

    注意：纯文本模式下 key_images 始终为空（无 PDF 图片可提）。
    """
    if not os.path.isfile(text_path):
        raise FileNotFoundError(f"文本文件不存在: {text_path}")
    full_text = _read_text_file(text_path)
    sections = detect_sections(full_text)
    figures_and_tables = extract_figures_and_tables(full_text)
    paper_type = detect_paper_type(full_text, sections)
    return {
        "input_file": os.path.abspath(text_path),
        "input_type": "text",
        "full_text": full_text,
        "sections": sections,
        "figures_and_tables": figures_and_tables,
        "key_images": [],
        "paper_type": paper_type,
        "page_count": 0,
        "extractor_used": "plain_text",
        "has_text_layer": bool(full_text and full_text.strip()),
    }


# ---------------------------------------------------------------------------
# 命令行入口
# ---------------------------------------------------------------------------
def main() -> int:
    parser = argparse.ArgumentParser(
        prog="pdf_extractor.py",
        description="计算化学论文 PDF 文本提取与章节定位工具（多后端自动降级）",
        epilog=(
            "示例:\n"
            "  python pdf_extractor.py paper.pdf\n"
            "  python pdf_extractor.py paper.pdf --pretty -o out.json\n"
            "  python pdf_extractor.py paper.pdf --image-dir ./imgs\n"
            "  python pdf_extractor.py notes.txt --text"
        ),
    )
    parser.add_argument("input", help="输入文件：PDF 文件路径，或纯文本文件路径（配合 --text）")
    parser.add_argument("-o", "--output", help="输出 JSON 文件路径（缺省打印到标准输出）")
    parser.add_argument("--text", action="store_true", help="将输入视为纯文本文件处理，不尝试 PDF 提取")
    parser.add_argument("--pretty", action="store_true", help="美化 JSON 输出（带缩进）")
    parser.add_argument("--no-sections", action="store_true", help="仅输出全文与元信息，不进行章节定位")
    parser.add_argument("--image-dir", help="候选图片输出目录（仅 PDF 模式生效；缺省用临时目录）")
    parser.add_argument("--max-images", type=int, default=12,
                        help="候选图片池上限（默认 12；上层 AI 从池中选 3-5 张）")
    parser.add_argument("--images-sort", choices=["position", "caption", "area"], default="position",
                        help="候选排序：position（默认，正文顺序）/ caption / area")
    args = parser.parse_args()

    try:
        if args.text:
            result = process_text_file(args.input)
        else:
            result = extract_pdf(
                args.input,
                image_dir=args.image_dir,
                max_images=args.max_images,
                images_sort=args.images_sort,
            )
    except FileNotFoundError as exc:
        print(f"错误: {exc}", file=sys.stderr)
        return 1

    if args.no_sections:
        result.pop("sections", None)

    indent = 2 if args.pretty else None
    payload = json.dumps(result, ensure_ascii=False, indent=indent)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as fh:
            fh.write(payload + "\n")
    else:
        _write_stdout(payload + "\n")
    return 0


if __name__ == "__main__":
    _setup_io()
    sys.exit(main())
