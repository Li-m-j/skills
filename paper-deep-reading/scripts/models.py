"""types.py — 共享类型定义（dataclasses / TypedDict）。

v0.3.0 拆分后引入，便于各模块之间传递结构化数据。
当前 dataclass 字段与 JSON 输出保持一致，便于向后兼容。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class SectionInfo:
    """单个章节的信息（来自 sections.py detect_sections）。"""
    name: str  # "abstract" / "introduction" / "method" / "result" / "conclusion"
    text: str  # 章节文本
    start_line: int = -1  # 起始行号（-1 表示未定位）


@dataclass
class FigureInfo:
    """单个图表引用（来自 figures.py extract_figures_and_tables）。"""
    label: str
    raw_label: str
    caption_preview: str
    position: int


@dataclass
class KeyImageInfo:
    """单张候选图片（来自 images.py extract_key_images）。

    v0.4：key_images 语义为**候选池**（默认最多 12 条，按正文顺序），
    由上层 AI 选取 3-5 张；新增 area / index 字段。
    """
    label: str
    image_path: str
    page: int
    width: int
    height: int
    byte_size: int
    caption_preview: str
    xref: int = 0
    area: int = 0
    index: int = 0


@dataclass
class ExtractionResult:
    """extract_pdf() 顶层返回类型（与原 JSON 输出字段一致）。"""
    input_file: str
    input_type: str  # "pdf" | "text"
    full_text: str
    sections: Dict[str, str]
    figures_and_tables: List[FigureInfo]
    key_images: List[KeyImageInfo]
    # v0.4：article | review | perspective | account | letter | editorial | unknown
    paper_type: str
    page_count: int
    extractor_used: str  # "pdftotext" | "fitz" | "pdfplumber" | "plain_text" | "ocr:<engine>" | "none"
    has_text_layer: bool
    warning: Optional[str] = None
    ocr_hint: Optional[Dict[str, object]] = None

    def to_dict(self) -> Dict[str, object]:
        """序列化为原版 JSON 格式（保证向后兼容）。"""
        result: Dict[str, object] = {
            "input_file": self.input_file,
            "input_type": self.input_type,
            "full_text": self.full_text,
            "sections": self.sections,
            "figures_and_tables": [
                {
                    "label": f.label,
                    "raw_label": f.raw_label,
                    "caption_preview": f.caption_preview,
                    "position": f.position,
                }
                for f in self.figures_and_tables
            ],
            "key_images": [
                {
                    "label": ki.label,
                    "image_path": ki.image_path,
                    "page": ki.page,
                    "width": ki.width,
                    "height": ki.height,
                    "area": ki.area,
                    "byte_size": ki.byte_size,
                    "caption_preview": ki.caption_preview,
                    "xref": ki.xref,
                    "index": ki.index,
                }
                for ki in self.key_images
            ],
            "paper_type": self.paper_type,
            "page_count": self.page_count,
            "extractor_used": self.extractor_used,
            "has_text_layer": self.has_text_layer,
        }
        if self.warning:
            result["warning"] = self.warning
        if self.ocr_hint:
            result["ocr_hint"] = self.ocr_hint
        return result


__all__ = [
    "SectionInfo",
    "FigureInfo",
    "KeyImageInfo",
    "ExtractionResult",
]
