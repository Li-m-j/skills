#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""validate_output.py — 反幻觉代码化校验器。

读取 qm_paper_search 生成的 .md 文献名录，提取所有 DOI，向 Crossref 反查确认
每篇论文真实存在。生成验证报告，标记 ✅ verified / ⚠️ unverified / ❌ invalid。

这是 v0.3.0 代码化反幻觉的关键工具——之前"严禁 LLM 编造"是文档恳求，
现在是脚本校验：DOI 必须在 Crossref API 响应里能找到对应 title。

用法：
    python validate_output.py paper_search_fine_xxx_20260912.md
    python validate_output.py paper_search_*.md --pretty
    python validate_output.py *.md --json-out report.json
    python validate_output.py *.md --threshold 0.95  # 校验率 < 95% 视为失败

跨平台：仅依赖 Python 3.8+ 标准库 + urllib；不需要 pip install。
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import OrderedDict
from pathlib import Path
from typing import Dict, List, Optional, Tuple

CROSSREF_API = "https://api.crossref.org/works/{doi}"
USER_AGENT = "qm_paper_search/0.3.0 (Mavis; DOI validation; +https://github.com/minimax)"
DEFAULT_TIMEOUT = 15  # 秒
DEFAULT_RATE_LIMIT_SLEEP = 0.1  # Crossref polite pool: 50 req/s

# DOI 提取正则（10.xxxx/xxxx 形式 + 链接形式 https://doi.org/...）
# 注意：必须排除 BibTeX 的包裹字符 {}（否则 doi = {10.x/y} 会被抽成 "10.x/y}"）
_DOI_RE = re.compile(r"(?:https?://(?:dx\.)?doi\.org/)?(10\.\d{4,9}/[^\s\)\]\"'<>{},;]+)", re.I)
# 行尾可能残留的分隔符
_DOI_TRAIL = ".,;:}）)\u3002\uff0c"


def extract_dois(md_text: str) -> List[str]:
    """从 .md 文本中提取所有 DOI。

    匹配 markdown 链接 `[10.xxxx](https://doi.org/10.xxxx)`、裸 DOI、以及
    BibTeX/RIS 里的 `doi = {10.xxxx}`（自动剥掉包裹花括号）。
    返回去重后的列表（按出现顺序）。
    """
    seen = set()
    out = []
    for m in _DOI_RE.finditer(md_text):
        doi = m.group(1).rstrip(_DOI_TRAIL)
        # 去掉可能附带的 query string (e.g. 10.xxxx/xxx?foo=bar)
        if "?" in doi:
            doi = doi.split("?")[0]
        doi = doi.rstrip(_DOI_TRAIL)
        if doi.lower().startswith("10.") and doi not in seen:
            seen.add(doi)
            out.append(doi)
    return out


def crossref_lookup(doi: str, timeout: int = DEFAULT_TIMEOUT) -> Tuple[Optional[str], Optional[str]]:
    """向 Crossref API 查 DOI，返回 (title, error)。

    成功：返回 (title, None)
    失败：返回 (None, error_message)
    """
    url = CROSSREF_API.format(doi=urllib.parse.quote(doi, safe="/"))
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            if resp.status != 200:
                return None, f"HTTP {resp.status}"
            data = json.loads(resp.read().decode("utf-8"))
            msg = data.get("message", {})
            title_list = msg.get("title") or []
            if title_list:
                return title_list[0], None
            return None, "no title in Crossref response"
    except urllib.error.HTTPError as e:
        return None, f"HTTP {e.code} {e.reason}"
    except urllib.error.URLError as e:
        return None, f"URL error: {e.reason}"
    except (json.JSONDecodeError, KeyError) as e:
        return None, f"parse error: {e}"
    except Exception as e:
        return None, f"unexpected: {type(e).__name__}: {e}"


def validate_doi(doi: str, retries: int = 2) -> Tuple[str, Optional[str], Optional[str]]:
    """校验单个 DOI，retries 次重试，返回 (status, crossref_title, error)。

    status: 'verified' | 'not_found' | 'error'
    """
    last_error = None
    for attempt in range(retries + 1):
        title, err = crossref_lookup(doi)
        if title is not None:
            return "verified", title, None
        last_error = err
        if err and "HTTP 4" in err:
            # 4xx: 客户端错误（DOI 不存在、权限），不重试
            if "404" in err:
                return "not_found", None, err
            break
        if attempt < retries:
            time.sleep(DEFAULT_RATE_LIMIT_SLEEP * (attempt + 1))
    return "error", None, last_error or "unknown error"


def validate_markdown_file(md_path: Path, verbose: bool = True) -> Dict:
    """校验单个 .md 文件，返回结构化报告。"""
    text = md_path.read_text(encoding="utf-8", errors="replace")
    dois = extract_dois(text)

    if verbose:
        print(f"  找到 {len(dois)} 个 DOI，开始校验...")

    results = []
    for i, doi in enumerate(dois, 1):
        status, crossref_title, err = validate_doi(doi)
        results.append({
            "doi": doi,
            "status": status,
            "crossref_title": crossref_title,
            "error": err,
        })
        if verbose:
            icon = {"verified": "✅", "not_found": "❌", "error": "⚠️"}.get(status, "?")
            print(f"    [{i}/{len(dois)}] {icon} {doi}" + (f" — {crossref_title[:60]}" if crossref_title else f" — {err}"))
        # Polite rate limit
        if i < len(dois):
            time.sleep(DEFAULT_RATE_LIMIT_SLEEP)

    summary = {
        "file": str(md_path),
        "total_dois": len(dois),
        "verified": sum(1 for r in results if r["status"] == "verified"),
        "not_found": sum(1 for r in results if r["status"] == "not_found"),
        "errors": sum(1 for r in results if r["status"] == "error"),
        "verification_rate": (
            sum(1 for r in results if r["status"] == "verified") / len(dois)
            if dois else 1.0
        ),
        "results": results,
    }
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="validate_output.py",
        description="qm_paper_search .md 文件反幻觉校验器（Crossref DOI 反查）",
    )
    parser.add_argument("files", nargs="+", help=".md 文件路径（支持 glob）")
    parser.add_argument("--pretty", action="store_true", help="输出人类可读报告")
    parser.add_argument("--json-out", help="输出 JSON 报告到指定文件")
    parser.add_argument("--threshold", type=float, default=0.95,
                        help="校验率阈值（默认 0.95）；低于此值退出码 2")
    parser.add_argument("--no-network", action="store_true",
                        help="跳过实际校验，仅做 DOI 提取（用于离线/单元测试）")
    parser.add_argument("--rate-limit", type=float, default=DEFAULT_RATE_LIMIT_SLEEP,
                        help=f"请求间隔（秒，默认 {DEFAULT_RATE_LIMIT_SLEEP}）")
    args = parser.parse_args()

    all_summaries = []
    overall_pass = True
    for fpath in args.files:
        path = Path(fpath)
        if not path.exists():
            print(f"❌ 文件不存在: {fpath}", file=sys.stderr)
            overall_pass = False
            continue

        print(f"\n=== {path.name} ===")
        if args.no_network:
            # 仅做 DOI 提取
            text = path.read_text(encoding="utf-8", errors="replace")
            dois = extract_dois(text)
            summary = {
                "file": str(path),
                "total_dois": len(dois),
                "verified": 0,
                "not_found": 0,
                "errors": 0,
                "verification_rate": None,
                "results": [{"doi": d, "status": "skipped", "crossref_title": None, "error": "no-network mode"} for d in dois],
            }
            print(f"  找到 {len(dois)} 个 DOI（--no-network 模式未校验）")
        else:
            summary = validate_markdown_file(path, verbose=True)

        all_summaries.append(summary)
        if summary.get("verification_rate") is not None and summary["verification_rate"] < args.threshold:
            overall_pass = False

    # 汇总
    if args.pretty:
        print("\n" + "=" * 60)
        print("  校验汇总")
        print("=" * 60)
        for s in all_summaries:
            rate = s.get("verification_rate")
            rate_str = f"{rate*100:.1f}%" if rate is not None else "skipped"
            print(f"  {Path(s['file']).name}: {s['verified']}/{s['total_dois']} verified ({rate_str})")
        print(f"\n  阈值: {args.threshold*100:.0f}%")
        print(f"  总体: {'✅ PASS' if overall_pass else '❌ FAIL'}")

    if args.json_out:
        Path(args.json_out).write_text(
            json.dumps(all_summaries, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"\n  JSON 报告已写入: {args.json_out}")

    return 0 if overall_pass else 2


if __name__ == "__main__":
    sys.exit(main())
