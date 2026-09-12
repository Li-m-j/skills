"""images.py — PDF 候选图片池提取（PyMuPDF）。

输入：PDF 路径 + `figures_and_tables` 列表（来自 figures.py）
输出：去重 + 过滤装饰图后的**候选图片池**（PNG 等格式），含本地路径。
      返回的是"候选池"而非"最重要的 N 张"——由上层 AI 按重要性选取 3-5 张。

策略：
  1. 对每个 figure 引用，按其 `position` 字符偏移估算出所在 page（按 max_position 等比例缩放）
  2. 读取该 page 上所有图片（page.get_images）
  3. 用 doc.extract_image(xref) 拿尺寸 + 字节流
  4. 过滤：宽或高 < min_dim 的视为装饰
  5. 去重：MD5 相同的图只保留一次
  6. 排序：默认按**正文出现顺序**（position）；可选 caption / area（v0.4 起不再默认按 caption 长度）
  7. 取前 max_count 条（默认 12，作为候选池）
  8. 输出到 `<dest_dir>/<safe_label>.<ext>`

依赖：`pip install pymupdf`（未安装时返回空数组）
"""

from __future__ import annotations

import hashlib
import os
import re
import tempfile
from pathlib import Path
from typing import Dict, List, Optional

from extractors import HAS_FITZ

# 默认最小尺寸：宽高都 < 80 像素的图视为图标/装饰，跳过
_DEFAULT_MIN_IMG_DIM = 80

# v0.4：默认输出为候选池（供 AI 选取），而非"前 5 张"
_DEFAULT_MAX_IMAGES = 12

# 排序策略
_SORT_BY_CHOICES = ("position", "caption", "area")


def extract_key_images(
    pdf_path: str,
    figures_and_tables: List[Dict[str, object]],
    max_count: int = _DEFAULT_MAX_IMAGES,
    dest_dir: Optional[str] = None,
    min_dim: int = _DEFAULT_MIN_IMG_DIM,
    sort_by: str = "position",
) -> List[Dict[str, object]]:
    """从 PDF 提取候选图片池（Figure 对应页上的真实图像），输出 PNG。

    参数：
      max_count: 候选池上限（默认 12）。上层 AI 从池中选 3-5 张。
      sort_by:   候选排序，`position`（默认，正文顺序）/ `caption`（caption 长度降序）/ `area`（像素面积降序）。

    返回列表，每项：
      {
        "label":           "Figure 1",
        "image_path":      "C:/.../Figure_1.png",
        "page":            3,            # 1-based page
        "width":           800,
        "height":          600,
        "area":            480000,
        "byte_size":       12345,
        "caption_preview": "...",
        "index":           0,            # 候选池内序号（0-based）
      }
    """
    if not HAS_FITZ or not figures_and_tables:
        return []
    if not os.path.isfile(pdf_path):
        return []

    if sort_by not in _SORT_BY_CHOICES:
        sort_by = "position"

    if dest_dir is None:
        dest_dir = tempfile.mkdtemp(prefix="pdr_images_")
    Path(dest_dir).mkdir(parents=True, exist_ok=True)

    import fitz  # 延迟 import，HAS_FITZ 已确认

    doc = None
    try:
        doc = fitz.open(pdf_path)
        page_count = doc.page_count

        if not figures_and_tables:
            return []

        max_pos = max((f.get("position", 0) or 0) for f in figures_and_tables) or 1
        candidates: List[Dict[str, object]] = []
        for order, fig in enumerate(figures_and_tables):
            pos = fig.get("position", 0) or 0
            ratio = pos / max_pos if max_pos > 0 else 0
            page_idx = min(int(ratio * page_count), page_count - 1)
            candidates.append({
                "label": fig.get("label", ""),
                "order": order,
                "position": pos,
                "page_idx": page_idx,
                "caption_preview": fig.get("caption_preview", "") or "",
            })

        # 排序（v0.4：默认正文顺序；caption 长度不再作为默认重要性代理）
        if sort_by == "caption":
            candidates.sort(key=lambda c: (-len(c["caption_preview"]), str(c["label"])))
        else:  # "position" / "area" 都先按正文顺序取候选，area 在提取后再排
            candidates.sort(key=lambda c: int(c["order"]))
        candidates = candidates[: max_count * 2]  # 多取一些容错

        seen_hashes: set = set()
        out: List[Dict[str, object]] = []
        for cand in candidates:
            label = cand["label"]
            page_idx = int(cand["page_idx"])  # type: ignore[arg-type]
            try:
                page = doc[page_idx]
            except Exception:
                continue
            image_list = page.get_images(full=True)
            if not image_list:
                # 兜底：往前/后翻 1 页
                for delta in (-1, 1):
                    p2 = page_idx + delta
                    if 0 <= p2 < page_count:
                        cand_imgs = doc[p2].get_images(full=True)
                        if cand_imgs:
                            page = doc[p2]
                            image_list = cand_imgs
                            page_idx = p2
                            break
            if not image_list:
                continue
            # 在该 page 上找最大且未重复的图
            best = None
            for img in image_list:
                xref = img[0]
                try:
                    base = doc.extract_image(xref)
                except Exception:
                    continue
                if not base:
                    continue
                ext = (base.get("ext") or "png").lower()
                w = int(base.get("width") or 0)
                h = int(base.get("height") or 0)
                data = base.get("image") or b""
                if not data or w < min_dim or h < min_dim:
                    continue
                digest = hashlib.md5(data).hexdigest()
                if digest in seen_hashes:
                    continue
                area = w * h
                if best is None or area > best["area"]:
                    best = {
                        "xref": xref, "ext": ext, "w": w, "h": h,
                        "data": data, "area": area, "digest": digest,
                    }
            if not best:
                continue
            seen_hashes.add(best["digest"])  # type: ignore[index]
            safe_label = re.sub(r"[^A-Za-z0-9_]+", "_", label).strip("_")
            if not safe_label:
                safe_label = f"img_{len(out)}"
            out_path = Path(dest_dir) / f"{safe_label}.{best['ext']}"  # type: ignore[index]
            try:
                out_path.write_bytes(best["data"])  # type: ignore[index]
            except Exception:
                continue
            out.append({
                "label": label,
                "image_path": str(out_path),
                "page": page_idx + 1,
                "xref": int(best["xref"]),  # type: ignore[index]
                "width": int(best["w"]),  # type: ignore[index]
                "height": int(best["h"]),  # type: ignore[index]
                "area": int(best["area"]),  # type: ignore[index]
                "byte_size": len(best["data"]),  # type: ignore[index]
                "caption_preview": cand["caption_preview"],
            })
            if len(out) >= max_count:
                break

        # 可选：按像素面积重排（大体量的图通常承载主结论）
        if sort_by == "area":
            out.sort(key=lambda item: -int(item.get("area", 0)))  # type: ignore[arg-type]

        # 补候选池序号（供 AI 引用与"未选用候选"清单使用）
        for i, item in enumerate(out):
            item["index"] = i
        return out
    finally:
        if doc is not None:
            try:
                doc.close()
            except Exception:
                pass


__all__ = ["extract_key_images", "_DEFAULT_MIN_IMG_DIM", "_DEFAULT_MAX_IMAGES", "_SORT_BY_CHOICES"]

