"""sections.py — 论文章节定位（中英文 + 中英混排标题）。

核心能力：
- 自动定位 abstract / introduction / method / result / conclusion 五章节
- 支持中英混排标题（如 "1. Introduction 引言" / "2. 计算方法 Computational Methods"）
- 过滤目录/页眉等误匹配（"实质性内容"启发式：标题后 ≥ 50 非空白字符）
"""

from __future__ import annotations

import re
from typing import Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# 章节输出顺序
# ---------------------------------------------------------------------------
SECTION_ORDER: List[str] = [
    "abstract",
    "introduction",
    "method",
    "result",
    "conclusion",
]

# ---------------------------------------------------------------------------
# 章节标题正则（中英文 + 中英混排；支持编号前缀，如 "1 Introduction" /
# "2.1 计算方法" / "1. Introduction 引言"）。
# 同一章节类型的多个模式按"英文+编号"→"中文+编号"→"中英混排"→"标题后跟分隔符"排列。
# ---------------------------------------------------------------------------
# 辅助：中文字符范围
_CN = r"\u4e00-\u9fa5"

SECTION_PATTERNS: Dict[str, List[str]] = {
    "abstract": [
        r"(?i)^\s*(abstract|summary)\s*$",
        r"(?i)^\s*(abstract|summary)\s*[:\-–—]",
        r"^\s*(摘\s*要)\s*$",
        r"^\s*(摘\s*要)\s*[：:\-–—]",
        r"(?i)^\s*(abstract|summary)\s+[【\[(]?\s*摘\s*要\s*[】\)\]]?\s*$",
        r"(?i)^\s*摘\s*要\s+[【\[(]?\s*(abstract|summary)\s*[】\)\]]?\s*$",
    ],
    "introduction": [
        r"(?i)^\s*(\d+(\.\d+)*\.?\s*)?introduction\s*$",
        r"(?i)^\s*(\d+(\.\d+)*\.?\s*)?introduction\s*[:\-–—]",
        r"^\s*(\d+(\.\d+)*\.?\s*)?(引言|绪论|前言|研究背景|介绍)\s*$",
        r"^\s*(\d+(\.\d+)*\.?\s*)?(引言|绪论|前言|研究背景)\s*[：:\-–—]",
        r"(?i)^\s*(\d+(\.\d+)*\.?\s*)?(introduction)\s+[" + _CN + r"\s]{1,8}(引言|绪论|前言|研究背景)?\s*$",
        r"(?i)^\s*(\d+(\.\d+)*\.?\s*)?(引言|绪论|前言|研究背景)\s+(introduction|background)\s*$",
    ],
    "method": [
        r"(?i)^\s*(\d+(\.\d+)*\.?\s*)?(methods?|methodology|computational\s+methods?|"
        r"computational\s+details|theoretical\s+methods?|theory\s+and\s+methods?|"
        r"experimental\s+methods?|experimental\s+section|simulation\s+details|"
        r"computational\s+procedure|calculation\s+details?|"
        r"supporting\s+information|supporting\s+methods?|"
        r"methods?\s+and\s+materials)\s*$",
        r"(?i)^\s*(\d+(\.\d+)*\.?\s*)?(methods?|methodology|computational\s+methods?|"
        r"computational\s+details|theoretical\s+methods?|experimental\s+methods?)\s*[:\-–—]",
        r"^\s*(\d+(\.\d+)*\.?\s*)?(计算方法|计算方法与细节|理论与计算方法|理论方法|"
        r"方法|实验方法|模拟方法|计算细节|模型与方法|"
        r"支持信息|补充材料|补充信息|补充方法)\s*$",
        r"^\s*(\d+(\.\d+)*\.?\s*)?(计算方法|理论与计算方法|理论方法|方法|实验方法|补充材料)\s*[：:\-–—]",
        r"(?i)^\s*(\d+(\.\d+)*\.?\s*)?(methods?|methodology|computational\s+(methods?|details?)|"
        r"theoretical\s+methods?|experimental\s+methods?|simulation\s+details?|"
        r"calculation\s+details?|supporting\s+information)\s+[" + _CN + r"\s]{1,12}(计算方法|理论方法|实验方法|模拟方法|计算细节|补充材料|支持信息)?\s*$",
        r"(?i)^\s*(\d+(\.\d+)*\.?\s*)?(计算方法|理论方法|实验方法|模拟方法|计算细节|补充材料|支持信息)\s+(methods?|methodology|computational\s+(methods?|details?)|supporting\s+information)\s*$",
    ],
    "result": [
        r"(?i)^\s*(\d+(\.\d+)*\.?\s*)?(results?|results?\s+and\s+discussion|findings|"
        r"computational\s+results?|results?\s+and\s+analysis|"
        r"discussion|discussions)\s*$",
        r"(?i)^\s*(\d+(\.\d+)*\.?\s*)?(results?|results?\s+and\s+discussion|discussion)\s*[:\-–—]",
        r"^\s*(\d+(\.\d+)*\.?\s*)?(结果|结果与讨论|计算结果|结果与分析|结果和讨论|讨论)\s*$",
        r"^\s*(\d+(\.\d+)*\.?\s*)?(结果|结果与讨论|计算结果|讨论)\s*[：:\-–—]",
        r"(?i)^\s*(\d+(\.\d+)*\.?\s*)?(results?\s+and\s+discussion|results?|discussion)\s+[" + _CN + r"\s]{1,12}(结果|结果与讨论|讨论|结果和分析)?\s*$",
        r"(?i)^\s*(\d+(\.\d+)*\.?\s*)?(结果|结果与讨论|计算结果|讨论)\s+(results?\s+and\s+discussion|results?|discussion)\s*$",
    ],
    "conclusion": [
        r"(?i)^\s*(\d+(\.\d+)*\.?\s*)?(conclusions?|summary\s+and\s+outlook|"
        r"concluding\s+remarks|discussion\s+and\s+conclusions?|summary|final\s+remarks|"
        r"outlook|conclusion\s+and\s+outlook)\s*$",
        r"(?i)^\s*(\d+(\.\d+)*\.?\s*)?(conclusions?|summary\s+and\s+outlook|"
        r"concluding\s+remarks|summary)\s*[:\-–—]",
        r"^\s*(\d+(\.\d+)*\.?\s*)?(结论|总结|结论与展望|结语|全文总结|总结与展望|展望)\s*$",
        r"^\s*(\d+(\.\d+)*\.?\s*)?(结论|总结|结论与展望|展望)\s*[：:\-–—]",
        r"(?i)^\s*(\d+(\.\d+)*\.?\s*)?(conclusions?|summary|outlook)\s+[" + _CN + r"\s]{1,10}(结论|总结|结论与展望|展望)?\s*$",
        r"(?i)^\s*(\d+(\.\d+)*\.?\s*)?(结论|总结|结论与展望|展望)\s+(conclusions?|summary|outlook)\s*$",
    ],
}


def _is_substantial(lines: List[str], pos: int, all_matches: List[Tuple[int, str]]) -> bool:
    """判断某标题位置之后是否确实有正文内容（用于过滤目录/页眉等误匹配）。

    规则：从该标题行到下一个任意章节标题（或文末）之间的非空白字符数 >= 50，
    视为"实质性内容"。目录项（标题紧挨标题）通常不满足该条件。
    """
    next_pos: Optional[int] = None
    for p, _ in sorted(all_matches, key=lambda m: m[0]):
        if p > pos:
            next_pos = p
            break
    end = next_pos if next_pos is not None else len(lines)
    content = "\n".join(lines[pos:end])
    non_space_chars = len(re.sub(r"\s+", "", content))
    return non_space_chars >= 50


def detect_sections(full_text: str) -> Dict[str, str]:
    """定位 abstract / introduction / method / result / conclusion 章节文本。

    返回 dict：章节名 → 该章节文本（未定位到的章节为空字符串）。
    """
    empty: Dict[str, str] = {k: "" for k in SECTION_ORDER}
    if not full_text or not full_text.strip():
        return empty

    lines: List[str] = full_text.splitlines()
    all_matches: List[Tuple[int, str]] = []

    for idx, raw_line in enumerate(lines):
        line = raw_line.strip()
        if not line:
            continue
        for sec_type, patterns in SECTION_PATTERNS.items():
            for pat in patterns:
                if re.search(pat, line):
                    all_matches.append((idx, sec_type))
                    break

    if not all_matches:
        return empty

    # 每个章节类型挑选"第一个实质性"匹配位置
    starts: Dict[str, int] = {}
    for sec_type in SECTION_ORDER:
        candidates = [pos for pos, t in all_matches if t == sec_type]
        for pos in candidates:
            if _is_substantial(lines, pos, all_matches):
                starts[sec_type] = pos
                break

    if not starts:
        return empty

    # 按位置排序后切片：每个章节取"本标题 → 下一标题（任意类型）"之间的文本
    ordered: List[Tuple[str, int]] = sorted(starts.items(), key=lambda kv: kv[1])
    sections: Dict[str, str] = {}
    for i, (sec_type, start) in enumerate(ordered):
        end = ordered[i + 1][1] if i + 1 < len(ordered) else len(lines)
        sections[sec_type] = "\n".join(lines[start:end]).strip()
    return {k: sections.get(k, "") for k in SECTION_ORDER}


__all__ = ["SECTION_ORDER", "SECTION_PATTERNS", "detect_sections"]
