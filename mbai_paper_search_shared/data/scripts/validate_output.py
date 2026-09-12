#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""validate_output.py — mbai_paper_search 反幻觉代码化校验器（v0.4.0）

读取 mbai_paper_search 生成的 .md 文献名录，提取所有 **DOI** 与 **PMID**，
分别向 Crossref / PubMed 反查确认条目真实存在，生成验证报告。

与 `qm_paper_search_shared/.../validate_output.py` 同构，差异：
    - 新增 **PMID 反查**（PubMed esummary），因为医学检索大量条目只有 PMID 没有 DOI；
    - 预印本（无 DOI / 无 PMID）计入 `preprint_skipped`，不计入分母。

用法：
    python validate_output.py paper_search_fine_xxx_20260912.md
    python validate_output.py paper_search_*.md --pretty
    python validate_output.py *.md --json-out report.json
    python validate_output.py *.md --threshold 0.95      # 校验率 < 95% 视为失败
    python validate_output.py *.md --no-network          # 仅做 ID 抽取（离线自检）

跨平台：仅依赖 Python 3.8+ 标准库 + urllib；不需要 pip install。
退出码：0 通过；2 校验率低于阈值或文件缺失。
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
from pathlib import Path
from typing import Dict, List, Optional, Tuple

CROSSREF_API = "https://api.crossref.org/works/{doi}"
PUBMED_ESUMMARY = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
USER_AGENT = "mbai_paper_search_skill/0.4 (Mavis; DOI+PMID validation)"
DEFAULT_TIMEOUT = 15
DEFAULT_RATE_LIMIT_SLEEP = 0.4  # PubMed 无 key 限 3 req/s

# DOI 提取：排除 BibTeX 花括号（否则 doi = {10.x/y} 会被抽成 "10.x/y}"）
_DOI_RE = re.compile(r"(?:https?://(?:dx\.)?doi\.org/)?(10\.\d{4,9}/[^\s\)\]\"'<>{},;]+)", re.I)
_DOI_TRAIL = ".,;:}）)\u3002\uff0c"
# PMID 提取：pubmed.ncbi.nlm.nih.gov/<id>/ 链接 或 "**PMID**：<id>"
_PMID_LINK_RE = re.compile(r"pubmed\.ncbi\.nlm\.nih\.gov/(\d{6,9})")
_PMID_FIELD_RE = re.compile(r"\*\*PMID\*\*[：:]\s*\[?(\d{6,9})")


def extract_dois(md_text: str) -> List[str]:
    seen = set()
    out: List[str] = []
    for m in _DOI_RE.finditer(md_text):
        doi = m.group(1).rstrip(_DOI_TRAIL)
        if "?" in doi:
            doi = doi.split("?")[0]
        doi = doi.rstrip(_DOI_TRAIL)
        if doi.lower().startswith("10.") and doi not in seen:
            seen.add(doi)
            out.append(doi)
    return out


def extract_pmids(md_text: str) -> List[str]:
    seen = set()
    out: List[str] = []
    for rx in (_PMID_FIELD_RE, _PMID_LINK_RE):
        for m in rx.finditer(md_text):
            pmid = m.group(1)
            if pmid not in seen:
                seen.add(pmid)
                out.append(pmid)
    return out


def _get_json(url: str, timeout: int = DEFAULT_TIMEOUT) -> Tuple[Optional[dict], Optional[str]]:
    req = urllib.request.Request(
        url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            if resp.status != 200:
                return None, f"HTTP {resp.status}"
            return json.loads(resp.read().decode("utf-8", errors="replace")), None
    except urllib.error.HTTPError as e:
        return None, f"HTTP {e.code} {e.reason}"
    except urllib.error.URLError as e:
        return None, f"URL error: {e.reason}"
    except (json.JSONDecodeError, ValueError) as e:
        return None, f"parse error: {e}"
    except Exception as e:  # noqa: BLE001
        return None, f"unexpected: {type(e).__name__}: {e}"


def validate_doi(doi: str, retries: int = 2) -> Tuple[str, Optional[str], Optional[str]]:
    url = CROSSREF_API.format(doi=urllib.parse.quote(doi, safe="/"))
    last = None
    for attempt in range(retries + 1):
        data, err = _get_json(url)
        if data is not None:
            titles = (data.get("message") or {}).get("title") or []
            return "verified", (titles[0] if titles else "(no title)"), None
        last = err
        if err and "HTTP 4" in err:
            if "404" in err:
                return "not_found", None, err
            break
        if attempt < retries:
            time.sleep(DEFAULT_RATE_LIMIT_SLEEP * (attempt + 1))
    return "error", None, last or "unknown error"


def validate_pmid(pmid: str, retries: int = 2) -> Tuple[str, Optional[str], Optional[str]]:
    url = PUBMED_ESUMMARY + "?" + urllib.parse.urlencode(
        {"db": "pubmed", "id": pmid, "retmode": "json", "tool": "mbai_paper_search"})
    last = None
    for attempt in range(retries + 1):
        data, err = _get_json(url)
        if data is not None:
            result = data.get("result") or {}
            node = result.get(pmid) if isinstance(result, dict) else None
            if isinstance(node, dict):
                title = node.get("title") or "(no title)"
                if node.get("error"):
                    return "not_found", None, str(node.get("error"))
                return "verified", title, None
            return "not_found", None, "PMID not in esummary result"
        last = err
        if err and "HTTP 4" in err:
            break
        if attempt < retries:
            time.sleep(DEFAULT_RATE_LIMIT_SLEEP * (attempt + 1))
    return "error", None, last or "unknown error"


def validate_markdown_file(md_path: Path, verbose: bool = True) -> Dict:
    text = md_path.read_text(encoding="utf-8", errors="replace")
    dois = extract_dois(text)
    pmids = extract_pmids(text)

    if verbose:
        print(f"  找到 {len(dois)} 个 DOI + {len(pmids)} 个 PMID，开始校验...")

    results: List[Dict] = []
    total = len(dois) + len(pmids)
    i = 0
    for doi in dois:
        i += 1
        status, title, err = validate_doi(doi)
        results.append({"id": doi, "kind": "doi", "status": status,
                        "matched_title": title, "error": err})
        if verbose:
            icon = {"verified": "✅", "not_found": "❌", "error": "⚠️"}.get(status, "?")
            print(f"    [{i}/{total}] {icon} DOI {doi}" +
                  (f" — {title[:60]}" if title else f" — {err}"))
        if i < total:
            time.sleep(DEFAULT_RATE_LIMIT_SLEEP)
    for pmid in pmids:
        i += 1
        status, title, err = validate_pmid(pmid)
        results.append({"id": pmid, "kind": "pmid", "status": status,
                        "matched_title": title, "error": err})
        if verbose:
            icon = {"verified": "✅", "not_found": "❌", "error": "⚠️"}.get(status, "?")
            print(f"    [{i}/{total}] {icon} PMID {pmid}" +
                  (f" — {title[:60]}" if title else f" — {err}"))
        if i < total:
            time.sleep(DEFAULT_RATE_LIMIT_SLEEP)

    verified = sum(1 for r in results if r["status"] == "verified")
    summary = {
        "file": str(md_path),
        "total_dois": len(dois),
        "total_pmids": len(pmids),
        "total_ids": total,
        "verified": verified,
        "not_found": sum(1 for r in results if r["status"] == "not_found"),
        "errors": sum(1 for r in results if r["status"] == "error"),
        "verification_rate": (verified / total) if total else 1.0,
        "results": results,
    }
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="validate_output.py",
        description="mbai_paper_search .md 文件反幻觉校验器（Crossref DOI + PubMed PMID 反查）",
    )
    parser.add_argument("files", nargs="+", help=".md 文件路径（支持 glob）")
    parser.add_argument("--pretty", action="store_true", help="输出人类可读报告")
    parser.add_argument("--json-out", help="输出 JSON 报告到指定文件")
    parser.add_argument("--threshold", type=float, default=0.95,
                        help="校验率阈值（默认 0.95）；低于此值退出码 2")
    parser.add_argument("--no-network", action="store_true",
                        help="跳过实际校验，仅做 ID 抽取（离线/单元测试）")
    parser.add_argument("--rate-limit", type=float, default=DEFAULT_RATE_LIMIT_SLEEP,
                        help=f"请求间隔秒数（默认 {DEFAULT_RATE_LIMIT_SLEEP}）")
    args = parser.parse_args()

    all_summaries: List[Dict] = []
    overall_pass = True
    for fpath in args.files:
        path = Path(fpath)
        if not path.exists():
            print(f"❌ 文件不存在: {fpath}", file=sys.stderr)
            overall_pass = False
            continue
        print(f"\n=== {path.name} ===")
        if args.no_network:
            text = path.read_text(encoding="utf-8", errors="replace")
            dois, pmids = extract_dois(text), extract_pmids(text)
            summary = {
                "file": str(path), "total_dois": len(dois), "total_pmids": len(pmids),
                "total_ids": len(dois) + len(pmids), "verified": 0, "not_found": 0,
                "errors": 0, "verification_rate": None,
                "results": [{"id": d, "kind": "doi", "status": "skipped",
                             "matched_title": None, "error": "no-network mode"} for d in dois]
                + [{"id": p, "kind": "pmid", "status": "skipped",
                    "matched_title": None, "error": "no-network mode"} for p in pmids],
            }
            print(f"  找到 {len(dois)} 个 DOI + {len(pmids)} 个 PMID（未校验）")
        else:
            summary = validate_markdown_file(path, verbose=True)
        all_summaries.append(summary)
        if summary.get("verification_rate") is not None and \
                summary["verification_rate"] < args.threshold:
            overall_pass = False

    if args.pretty:
        print("\n" + "=" * 60)
        print("  校验汇总")
        print("=" * 60)
        for s in all_summaries:
            rate = s.get("verification_rate")
            rate_str = f"{rate * 100:.1f}%" if rate is not None else "skipped"
            print(f"  {Path(s['file']).name}: {s['verified']}/{s['total_ids']} verified ({rate_str})"
                  f"  [DOI {s['total_dois']} · PMID {s['total_pmids']}]")
        print(f"\n  阈值: {args.threshold * 100:.0f}%")
        print(f"  总体: {'✅ PASS' if overall_pass else '❌ FAIL'}")

    if args.json_out:
        Path(args.json_out).write_text(
            json.dumps(all_summaries, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\n  JSON 报告已写入: {args.json_out}")

    return 0 if overall_pass else 2


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:  # noqa: BLE001
        pass
    sys.exit(main())
