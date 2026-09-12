"""figures.py — 论文图表引用提取（Figure / Fig. / Table / Tab. / Scheme / Chart）。

仅扫描文本中的图表引用 + caption 预览，**不提取图片本身**（图片提取在 images.py）。
"""

from __future__ import annotations

import re
from typing import Dict, List

# 匹配 "Figure 1." / "Fig. 2" / "Table 1" / "Tab. 3" / "Scheme 1" / "Chart 1"
# 注意：仅匹配引用（caption 起点），不做整段解析。
_FIG_LABEL_RE = re.compile(
    r"(?i)\b(figure|fig\.?|table|tab\.?|scheme|chart)\s*(\d+[a-z]?)\s*[\.:：]?\s+"
)
# 截取 caption 预览的最大字符数
_CAPTION_PREVIEW_MAX = 220


def extract_figures_and_tables(full_text: str) -> List[Dict[str, object]]:
    """扫描全文，定位 Figure/Fig./Table/Tab./Scheme/Chart 引用与紧随其后的 caption 预览。

    返回列表，每项：
      {
        "label":      "Figure 1",       # 标准化标签（Figure 1 / Table S2 等）
        "raw_label":  "Fig. 1.",        # 原文写法
        "caption_preview": "...",        # 紧随标题的 caption 前 _CAPTION_PREVIEW_MAX 字符
        "position":   1234,              # 在 full_text 中的字符偏移
      }

    去重：同一 label 只保留首次出现。
    """
    out: List[Dict[str, object]] = []
    if not full_text:
        return out

    seen: set = set()
    for m in _FIG_LABEL_RE.finditer(full_text):
        kind_raw = m.group(1).rstrip(".").lower()
        # 标准化
        if kind_raw in ("fig", "figure"):
            kind_norm = "Figure"
        elif kind_raw in ("tab", "table"):
            kind_norm = "Table"
        elif kind_raw == "scheme":
            kind_norm = "Scheme"
        elif kind_raw == "chart":
            kind_norm = "Chart"
        else:
            kind_norm = kind_raw.capitalize()
        num = m.group(2)
        label = f"{kind_norm} {num}"
        if label in seen:
            continue
        seen.add(label)

        # caption 预览：从匹配结束位置起，截取直到下一个换行 / 句末 / 引文标记
        start = m.end()
        snippet = full_text[start:start + _CAPTION_PREVIEW_MAX]
        # 在 ~160 字符处尝试找一个自然的 caption 终点（句号或换行）
        cut = _CAPTION_PREVIEW_MAX
        for stop_char in ("\n", "。", "．", ". "):
            idx = snippet.find(stop_char, 40)  # 至少保留 40 字符
            if 0 < idx < cut:
                cut = idx + (1 if stop_char == "\n" else 0)
        caption_preview = snippet[:cut].strip()

        out.append({
            "label": label,
            "raw_label": m.group(0).strip(),
            "caption_preview": caption_preview,
            "position": m.start(),
        })
    # 按出现顺序排序（finditer 已按位置）
    return out


__all__ = ["extract_figures_and_tables"]
