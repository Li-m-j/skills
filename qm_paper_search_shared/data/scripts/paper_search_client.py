#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""paper_search_client.py — qm_paper_search 检索客户端（v0.4.0 · 零第三方依赖）

背景（补 `skill锐评.md` 处置建议 #1）：
    v0.2.x 只有两个脚本——`qm_openalex_to_md.ps1`（JSON→MD 转换器，HTTP 调用数为 0）
    与 `validate_output.py`（DOI 反查校验）。**没有任何真正的检索客户端**，
    检索全靠 Agent 临场手写 HTTP 请求，与 SKILL.md「主链 Semantic Scholar → Crossref →
    OpenAlex」的承诺对不上。本脚本把检索固化为可复用、可测试的代码。

职责：
    1. 多源检索：Semantic Scholar（主）→ OpenAlex（覆盖兜底）→ Crossref（元数据权威）
    2. 规范化 + 合并：DOI / 标题去重，字段级补全，**缺则 N/A，绝不编造**
    3. 方案 H 宽召回：`--concept-pattern` regex 二次方向过滤（不额外发请求）
    4. seen_papers.json 读写：topic_id 前缀 + 跨 pool 合并去重（v0.4 规则）
    5. 导出 SKILL.md §6.2 规定的 Markdown 名录（元信息块 + 速览 + 详细条目 + 4 引用格式）
    6. `--verify`：交付前复用 `validate_output.py` 做 DOI 反查

依赖：仅 Python 3.8+ 标准库（urllib）。Windows / Linux / macOS 通用（UTF-8）。

用法：
    python paper_search_client.py -q "machine learning potential" --pretty
    python paper_search_client.py -q "COF 催化" --mode fine --count 20 --years 5
    python paper_search_client.py -q "钙钛矿太阳能电池" --mode broad --concept-pattern "perovskite|solar cell"
    python paper_search_client.py -q "single atom catalysis" --out "D:/papers" --verify
    python paper_search_client.py -q "MOF" --dry-run --json-out raw.json      # 只打印+存 JSON

退出码：
    0 成功；2 全部数据源失败；3 参数错误；4 检索成功但 DOI 校验未达标（--verify）
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

# ---------------------------------------------------------------------------
# 路径与常量
# ---------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).resolve().parent          # .../data/scripts
DATA_DIR = SCRIPT_DIR.parent                          # .../data
USER_AGENT = "qm_paper_search_skill/0.4 (paper search client)"
NA = "N/A"

SS_SEARCH = "https://api.semanticscholar.org/graph/v1/paper/search"
SS_FIELDS = (
    "title,abstract,year,venue,publicationVenue,externalIds,authors,"
    "fieldsOfStudy,tldr,citationCount,referenceCount,openAccessPdf,publicationTypes"
)
OPENALEX_WORKS = "https://api.openalex.org/works"
CROSSREF_WORKS = "https://api.crossref.org/works"

STOPWORDS = {
    "the", "a", "an", "of", "in", "on", "for", "and", "or", "with", "via",
    "using", "study", "review", "analysis", "toward", "towards", "based",
    "文献", "检索", "综述", "概览", "立项", "摸底", "深度", "方法",
}

REVIEW_HINT = re.compile(
    r"(?i)\b(review|meta[\-\s]?analysis|systematic|overview|advances?\s+in|"
    r"perspective|progress\s+in)\b"
)
PREPRINT_HINT = re.compile(r"(?i)(biorxiv|medrxiv|chemrxiv|arxiv|research\s*square|ssrn|preprint)")


# ---------------------------------------------------------------------------
# 基础工具
# ---------------------------------------------------------------------------
def http_get_json(
    url: str,
    headers: Optional[Dict[str, str]] = None,
    timeout: int = 20,
    retries: int = 2,
    sleep_base: float = 1.0,
    log: Optional[List[Dict[str, Any]]] = None,
) -> Tuple[Optional[Any], Optional[str]]:
    """GET 并解析 JSON。返回 (data, error)。4xx（除 429）不重试。"""
    hdr = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    if headers:
        hdr.update(headers)

    last_err: Optional[str] = None
    for attempt in range(retries + 1):
        t0 = time.time()
        status: Any = None
        try:
            req = urllib.request.Request(url, headers=hdr)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                status = getattr(resp, "status", 200)
                payload = resp.read().decode("utf-8", errors="replace")
            data = json.loads(payload)
            if log is not None:
                log.append({
                    "ts": datetime.now().isoformat(timespec="seconds"),
                    "url": url.split("?")[0], "status": status,
                    "latency_ms": int((time.time() - t0) * 1000),
                })
            return data, None
        except urllib.error.HTTPError as exc:
            status = exc.code
            last_err = f"HTTP {exc.code} {exc.reason}"
            if log is not None:
                log.append({
                    "ts": datetime.now().isoformat(timespec="seconds"),
                    "url": url.split("?")[0], "status": status,
                    "latency_ms": int((time.time() - t0) * 1000),
                    "note": last_err,
                })
            if exc.code in (400, 401, 403, 404):
                break
        except urllib.error.URLError as exc:
            last_err = f"网络层失败: {exc.reason}"
        except ValueError as exc:
            last_err = f"JSON 解析失败: {exc}"
        except Exception as exc:  # noqa: BLE001 - 兜底，避免脚本崩溃
            last_err = f"未预期错误: {type(exc).__name__}: {exc}"

        if attempt < retries:
            time.sleep(sleep_base * (attempt + 1))
    return None, last_err or "unknown error"


def load_keys(verbose: bool = False) -> Dict[str, str]:
    """读取 API key：api_keys.local.json（个人本地）> 环境变量。"""
    keys: Dict[str, str] = {}
    local = DATA_DIR / "api_keys.local.json"
    if local.is_file():
        try:
            cfg = json.loads(local.read_text(encoding="utf-8-sig"))
        except Exception:  # noqa: BLE001
            cfg = {}
        if isinstance(cfg, dict):
            prov = cfg.get("providers") if isinstance(cfg.get("providers"), dict) else cfg
            for name in ("openalex", "semantic_scholar"):
                node = prov.get(name)
                if isinstance(node, dict):
                    val = (node.get("key") or "").strip()
                    if val and not val.upper().startswith(("YOUR_", "REPLACE")):
                        keys[name] = val
            # 兼容扁平写法（mbai 风格字段名）
            flat = {"openalex_api_key": "openalex", "semantic_scholar_api_key": "semantic_scholar"}
            for field, name in flat.items():
                val = cfg.get(field)
                if isinstance(val, str) and val.strip() and not val.upper().startswith("REPLACE"):
                    keys.setdefault(name, val.strip())
    for env, name in (("OPENALEX_API_KEY", "openalex"),
                      ("SEMANTIC_SCHOLAR_API_KEY", "semantic_scholar")):
        val = os.environ.get(env)
        if val and val.strip():
            keys[name] = val.strip()
    if verbose:
        print(f"   key 状态: " + ", ".join(f"{k}={'✓' if v else '✗'}" for k, v in
                                          (("openalex", keys.get("openalex")),
                                           ("semantic_scholar", keys.get("semantic_scholar")))))
    return keys


def norm_doi(doi: Any) -> str:
    if not doi:
        return ""
    s = str(doi).strip().lower()
    s = re.sub(r"^https?://(dx\.)?doi\.org/", "", s)
    return s.rstrip(".,;: ").strip()


def title_key(title: Any) -> str:
    if not title:
        return ""
    s = unicodedata.normalize("NFKD", str(title)).lower()
    s = re.sub(r"<[^>]+>", " ", s)
    s = re.sub(r"[^a-z0-9]+", "", s)
    return s[:120]


def query_tokens(text: str) -> Set[str]:
    toks = re.findall(r"[a-z0-9\u4e00-\u9fff]{2,}", (text or "").lower())
    return {t for t in toks if t not in STOPWORDS}


def slugify(text: str, maxlen: int = 40) -> str:
    s = re.sub(r"[^\w\u4e00-\u9fff]+", "_", (text or "").strip())
    s = re.sub(r"_+", "_", s).strip("_")
    return (s or "topic")[:maxlen]


def clean_tag(text: Any) -> str:
    """去掉摘要里的 JATS/HTML 标签与多余空白。"""
    if not text:
        return ""
    s = re.sub(r"<[^>]+>", " ", str(text))
    s = re.sub(r"\s+", " ", s)
    return s.strip()


def infer_mode(query: str, explicit: Optional[str]) -> str:
    """§5.1 mode 推断规则。"""
    if explicit in ("fine", "broad"):
        return explicit
    if re.search(r"(?i)概览|立项|综述|摸底|survey|landscape|全景|review", query):
        return "broad"
    if re.search(r"(?i)深度|方法|创新|对比|复现", query):
        return "fine"
    return "fine"


# ---------------------------------------------------------------------------
# 记录结构与各源解析
# ---------------------------------------------------------------------------
def blank_record() -> Dict[str, Any]:
    return {
        "title": "", "authors": [], "year": None, "venue": "",
        "volume": "", "issue": "", "page": "", "doi": "", "abstract": "",
        "keywords": [], "tldr": "", "citation_count": None, "pub_types": [],
        "source": "", "sources": [], "oa_url": "", "is_preprint": False,
        "preprint_server": "", "concepts": [], "pmid": "", "kw_note": "",
    }


def parse_semanticscholar(item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    title = (item.get("title") or "").strip()
    if not title:
        return None
    r = blank_record()
    r["title"] = title
    r["abstract"] = clean_tag(item.get("abstract") or "")
    r["year"] = item.get("year")
    venue = (item.get("venue") or "").strip()
    pv = item.get("publicationVenue")
    if not venue and isinstance(pv, dict):
        venue = (pv.get("name") or "").strip()
    r["venue"] = venue
    ext = item.get("externalIds") or {}
    r["doi"] = norm_doi(ext.get("DOI"))
    r["pmid"] = str(ext.get("PubMed") or "")
    r["authors"] = [(a.get("name") or "").strip()
                    for a in (item.get("authors") or []) if a.get("name")]
    r["keywords"] = [f for f in (item.get("fieldsOfStudy") or []) if f]
    tldr = item.get("tldr")
    if isinstance(tldr, dict):
        r["tldr"] = (tldr.get("text") or "").strip()
    r["citation_count"] = item.get("citationCount")
    r["pub_types"] = [p for p in (item.get("publicationTypes") or []) if p]
    oap = item.get("openAccessPdf")
    if isinstance(oap, dict):
        r["oa_url"] = (oap.get("url") or "").strip()
    r["source"] = "semantic_scholar"
    r["sources"] = ["semantic_scholar"]
    r["is_preprint"] = bool(PREPRINT_HINT.search(venue)) or "Preprint" in r["pub_types"]
    if r["is_preprint"]:
        r["preprint_server"] = venue
    return r


def reconstruct_abstract(inverted: Any) -> str:
    """OpenAlex 的 abstract_inverted_index → 原始句子。"""
    if not isinstance(inverted, dict) or not inverted:
        return ""
    positions: Dict[int, str] = {}
    for word, idxs in inverted.items():
        if isinstance(idxs, list):
            for i in idxs:
                positions[int(i)] = word
    return " ".join(positions[k] for k in sorted(positions))


def parse_openalex(item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    title = (item.get("display_name") or item.get("title") or "").strip()
    if not title:
        return None
    r = blank_record()
    r["title"] = title
    r["abstract"] = clean_tag(reconstruct_abstract(item.get("abstract_inverted_index")))
    r["year"] = item.get("publication_year")
    src = ((item.get("primary_location") or {}).get("source") or {})
    r["venue"] = (src.get("display_name") or "").strip()
    biblio = item.get("biblio") or {}
    r["volume"] = str(biblio.get("volume") or "")
    r["issue"] = str(biblio.get("issue") or "")
    first, last = biblio.get("first_page"), biblio.get("last_page")
    r["page"] = (f"{first}-{last}" if first and last and str(first) != str(last)
                 else str(first or last or ""))
    r["doi"] = norm_doi(item.get("doi"))
    r["authors"] = [
        ((a.get("author") or {}).get("display_name") or "").strip()
        for a in (item.get("authorships") or [])
    ]
    r["authors"] = [a for a in r["authors"] if a]
    concepts = [((c.get("display_name") or "")).strip()
                for c in (item.get("concepts") or []) if c.get("display_name")]
    r["concepts"] = concepts[:12]
    r["keywords"] = r["concepts"][:8]
    if r["keywords"]:
        r["kw_note"] = "概念标签，来自 OpenAlex concepts"
    r["citation_count"] = item.get("cited_by_count")
    oa = item.get("open_access") or {}
    if isinstance(oa, dict):
        r["oa_url"] = (oa.get("oa_url") or "").strip()
    otype = (item.get("type") or "").lower()
    r["pub_types"] = [otype] if otype else []
    if otype == "review":
        r["pub_types"].append("Review")
    r["source"] = "openalex"
    r["sources"] = ["openalex"]
    r["is_preprint"] = otype == "preprint" or bool(PREPRINT_HINT.search(r["venue"]))
    if r["is_preprint"]:
        r["preprint_server"] = r["venue"]
    return r


def parse_crossref(item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    titles = item.get("title") or []
    title = (titles[0] if titles else "").strip()
    if not title:
        return None
    r = blank_record()
    r["title"] = clean_tag(title)
    r["doi"] = norm_doi(item.get("DOI"))
    parts = ((item.get("published") or {}).get("date-parts")
             or (item.get("issued") or {}).get("date-parts") or [])
    if parts and parts[0]:
        try:
            r["year"] = int(parts[0][0])
        except (TypeError, ValueError):
            r["year"] = None
    ct = item.get("container-title") or []
    r["venue"] = (ct[0] if ct else "").strip()
    r["volume"] = str(item.get("volume") or "")
    r["issue"] = str(item.get("issue") or "")
    r["page"] = str(item.get("page") or "")
    authors = []
    for a in (item.get("author") or []):
        name = " ".join(x for x in [(a.get("given") or "").strip(),
                                    (a.get("family") or "").strip()] if x)
        if name:
            authors.append(name)
    r["authors"] = authors
    # Crossref 的 abstract 常为出版商模板 HTML，仅当长度可观时保留
    ab = clean_tag(item.get("abstract") or "")
    r["abstract"] = ab if len(ab) >= 200 else ""
    r["source"] = "crossref"
    r["sources"] = ["crossref"]
    r["pub_types"] = []
    return r


# ---------------------------------------------------------------------------
# 各源检索
# ---------------------------------------------------------------------------
def search_semanticscholar(
    query: str, limit: int, years_lo: Optional[int], years_hi: Optional[int],
    api_key: Optional[str], log: List[Dict[str, Any]],
) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    params = {"query": query, "limit": str(min(max(limit, 1), 100)), "fields": SS_FIELDS}
    if years_lo and years_hi:
        params["year"] = f"{years_lo}-{years_hi}"
    url = SS_SEARCH + "?" + urllib.parse.urlencode(params)
    headers = {"x-api-key": api_key} if api_key else None
    data, err = http_get_json(url, headers=headers, log=log)
    if data is None:
        return [], err
    out = []
    for item in (data.get("data") or []):
        rec = parse_semanticscholar(item)
        if rec:
            out.append(rec)
    return out, None


def openalex_filters(mode: str, years_lo: Optional[int], pub_type: str) -> str:
    filters = []
    if mode == "broad" or pub_type == "review":
        filters.append("type:review")
    elif pub_type == "article":
        filters.append("type:article")
    if years_lo:
        filters.append(f"from_publication_date:{years_lo}-01-01")
    if filters:
        filters.append("is_paratext:false")
    return ",".join(filters)


def search_openalex(
    query: str, limit: int, mode: str, years_lo: Optional[int],
    pub_type: str, api_key: Optional[str], mailto: Optional[str],
    log: List[Dict[str, Any]],
) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    params: Dict[str, str] = {
        "search": query,
        "per-page": str(min(max(limit, 1), 200)),
        "sort": "relevance_score:desc",
    }
    flt = openalex_filters(mode, years_lo, pub_type)
    if flt:
        params["filter"] = flt
    if mailto:
        params["mailto"] = mailto
    if api_key:
        params["api_key"] = api_key
    url = OPENALEX_WORKS + "?" + urllib.parse.urlencode(params)
    data, err = http_get_json(url, log=log)
    if data is None:
        return [], err
    out = []
    for item in (data.get("results") or []):
        rec = parse_openalex(item)
        if rec:
            out.append(rec)
    return out, None


def search_crossref(
    query: str, limit: int, years_lo: Optional[int],
    mailto: Optional[str], log: List[Dict[str, Any]],
) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    params = {
        "query.bibliographic": query,
        "rows": str(min(max(limit, 1), 100)),
        "select": "DOI,title,author,container-title,volume,issue,page,published,issued,abstract,type",
    }
    if mailto:
        params["mailto"] = mailto
    if years_lo:
        params["filter"] = f"from-pub-date:{years_lo}-01-01"
    url = CROSSREF_WORKS + "?" + urllib.parse.urlencode(params)
    data, err = http_get_json(url, log=log)
    if data is None:
        return [], err
    out = []
    for item in ((data.get("message") or {}).get("items") or []):
        rec = parse_crossref(item)
        if rec:
            out.append(rec)
    return out, None


def enrich_via_crossref(
    records: List[Dict[str, Any]], max_items: int, mailto: Optional[str],
    log: List[Dict[str, Any]],
) -> int:
    """对缺卷/期/页的记录，按 DOI 向 Crossref 补元数据（元数据权威）。"""
    filled = 0
    for rec in records:
        if filled >= max_items:
            break
        if rec.get("volume") and rec.get("page"):
            continue
        doi = norm_doi(rec.get("doi"))
        if not doi:
            continue
        url = f"{CROSSREF_WORKS}/{urllib.parse.quote(doi, safe='/')}"
        if mailto:
            url += "?" + urllib.parse.urlencode({"mailto": mailto})
        data, _err = http_get_json(url, retries=1, log=log)
        if not data:
            continue
        msg = data.get("message") or {}
        for f in ("volume", "issue", "page"):
            if not rec.get(f) and msg.get(f):
                rec[f] = str(msg.get(f))
        if not rec.get("venue"):
            ct = msg.get("container-title") or []
            if ct:
                rec["venue"] = ct[0]
        rec["sources"] = sorted(set(rec.get("sources") or []) | {"crossref"})
        filled += 1
        time.sleep(0.1)
    return filled


# ---------------------------------------------------------------------------
# 合并 / 过滤
# ---------------------------------------------------------------------------
def merge_records(records: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    buckets: Dict[str, Dict[str, Any]] = {}
    order: List[str] = []
    for rec in records:
        if not rec.get("title"):
            continue
        key = norm_doi(rec.get("doi")) or title_key(rec["title"])
        if not key:
            continue
        if key not in buckets:
            buckets[key] = rec
            order.append(key)
            continue
        base = buckets[key]
        base["sources"] = sorted(set(base.get("sources") or []) | set(rec.get("sources") or []))
        for field in ("title", "abstract", "venue", "doi", "tldr", "oa_url",
                      "volume", "issue", "page", "pmid"):
            if not base.get(field) and rec.get(field):
                base[field] = rec[field]
        if base.get("year") is None and rec.get("year"):
            base["year"] = rec["year"]
        if not base.get("authors") and rec.get("authors"):
            base["authors"] = rec["authors"]
        if not base.get("keywords") and rec.get("keywords"):
            base["keywords"] = rec["keywords"]
            if rec.get("kw_note") and not base.get("kw_note"):
                base["kw_note"] = rec["kw_note"]
        if base.get("citation_count") is None and rec.get("citation_count") is not None:
            base["citation_count"] = rec["citation_count"]
        base["pub_types"] = sorted(set(base.get("pub_types") or []) | set(rec.get("pub_types") or []))
        if rec.get("is_preprint"):
            base["is_preprint"] = True
            base["preprint_server"] = base.get("preprint_server") or rec.get("preprint_server") or ""
        # Crossref 是元数据权威：卷/期/页覆盖
        if rec.get("source") == "crossref":
            for field in ("volume", "issue", "page"):
                if rec.get(field):
                    base[field] = rec[field]
    return [buckets[k] for k in order]


def looks_like_review(rec: Dict[str, Any]) -> bool:
    pts = " ".join(rec.get("pub_types") or [])
    if re.search(r"(?i)review", pts):
        return True
    return bool(REVIEW_HINT.search(rec.get("title") or ""))


def apply_type_filter(records: List[Dict[str, Any]], mode: str, pub_type: str) -> List[Dict[str, Any]]:
    if pub_type in ("all", "mixed", ""):
        return records
    if pub_type == "review" or mode == "broad":
        kept = [r for r in records if looks_like_review(r)]
    elif pub_type == "article":
        kept = [r for r in records if not looks_like_review(r)]
    else:
        kept = records
    return kept or records  # 全被滤掉时不强求，交由上层声明


def apply_concept_filter(
    records: List[Dict[str, Any]], pattern: Optional[str], min_match: int,
) -> Tuple[List[Dict[str, Any]], int]:
    """方案 H：宽召回后的二次方向过滤（不增加 API 调用）。"""
    if not pattern:
        for r in records:
            r["concept_hits"] = 0
        return records, 0
    try:
        rx = re.compile(pattern, re.I)
    except re.error as exc:
        print(f"⚠️ --concept-pattern 不是合法正则（{exc}），已跳过方向过滤", file=sys.stderr)
        return records, 0
    kept = []
    for rec in records:
        hay = " ".join([
            rec.get("title") or "",
            rec.get("abstract") or "",
            " ".join(rec.get("keywords") or []),
        ])
        hits = {m.group(0).lower() for m in rx.finditer(hay)}
        rec["concept_hits"] = len(hits)
        if len(hits) >= max(min_match, 0):
            kept.append(rec)
    return kept, max(len(records) - len(kept), 0)


def sort_records(records: List[Dict[str, Any]], sort_by: str) -> List[Dict[str, Any]]:
    if sort_by == "time":
        return sorted(records, key=lambda r: (r.get("year") or 0), reverse=True)
    if sort_by == "citations":
        return sorted(records, key=lambda r: (r.get("citation_count") or -1), reverse=True)
    if sort_by == "time+citations":
        return sorted(records, key=lambda r: ((r.get("year") or 0), (r.get("citation_count") or -1)),
                      reverse=True)
    return records  # relevance：保持 API 返回顺序


# ---------------------------------------------------------------------------
# seen_papers / 分区数据
# ---------------------------------------------------------------------------
def load_seen() -> Dict[str, Any]:
    path = DATA_DIR / "seen_papers.json"
    if path.is_file():
        try:
            data = json.loads(path.read_text(encoding="utf-8-sig"))
            if isinstance(data, dict):
                data.setdefault("topics", {})
                return data
        except Exception:  # noqa: BLE001
            pass
    return {"version": "0.4.0", "topics": {}}


def pool_scope(
    seen: Dict[str, Any], topic_id: str, tokens: Set[str],
    cross_topic: bool, global_dedup: bool,
) -> Tuple[Set[str], List[str]]:
    """按 v0.4 §5.2 规则选择参与去重的 pool。"""
    topics: Dict[str, Any] = seen.get("topics") or {}
    if global_dedup:
        chosen = list(topics.keys())
    else:
        chosen = [topic_id] if topic_id in topics else []
        if cross_topic:
            for tid, node in topics.items():
                if tid == topic_id or not isinstance(node, dict):
                    continue
                blob = " ".join([
                    str(node.get("name") or ""),
                    str(node.get("query") or ""),
                    " ".join(str(q) for q in (node.get("queries") or [])),
                ])
                if query_tokens(blob) & tokens:
                    chosen.append(tid)
    dois: Set[str] = set()
    for tid in chosen:
        node = topics.get(tid) or {}
        for d in (node.get("seen_dois") or []):
            nd = norm_doi(d)
            if nd:
                dois.add(nd)
    return dois, chosen


def mark_seen(
    seen: Dict[str, Any], topic_id: str, topic_name: str, query: str, mode: str,
    records: Sequence[Dict[str, Any]], data_source: str,
) -> None:
    topics: Dict[str, Any] = seen.setdefault("topics", {})
    node = topics.get(topic_id) or {
        "name": topic_name, "created_at": datetime.now().strftime("%Y-%m-%d"),
    }
    node["name"] = topic_name
    node["mode"] = mode
    node["query"] = query
    node["last_query"] = query
    node["last_used"] = datetime.now().strftime("%Y-%m-%d")
    node["data_source"] = data_source
    existing = {norm_doi(d) for d in (node.get("seen_dois") or [])}
    for rec in records:
        nd = norm_doi(rec.get("doi"))
        if nd:
            existing.add(nd)
    node["seen_dois"] = sorted(existing)
    topics[topic_id] = node


def save_seen(seen: Dict[str, Any]) -> None:
    seen["version"] = seen.get("version") or "0.4.0"
    seen["updated_at"] = datetime.now().isoformat(timespec="seconds")
    path = DATA_DIR / "seen_papers.json"
    path.write_text(json.dumps(seen, ensure_ascii=False, indent=2), encoding="utf-8")


def _alpha_only(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", (text or "").lower())


def _acronym(text: str) -> str:
    """'J. Am. Chem. Soc.' → 'jacs'（期刊缩写常见形态）。"""
    toks = re.findall(r"[A-Za-z]+", text or "")
    if not toks or len(toks) > 6:
        return ""
    return "".join(t[0] for t in toks).lower()


def load_journal_index() -> Dict[str, Dict[str, Any]]:
    path = DATA_DIR / "cas_journal_zones.json"
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:  # noqa: BLE001
        return {}
    index: Dict[str, Dict[str, Any]] = {}
    for name, node in (data.get("journals") or {}).items():
        if not isinstance(node, dict):
            continue
        entry = dict(node)
        entry["_name"] = name
        keys = [name, node.get("abbr") or ""]
        for key in keys:
            norm = _alpha_only(key)
            if norm:
                index.setdefault(norm, entry)
            acr = _acronym(key)
            if acr and len(acr) >= 3:
                index.setdefault(acr, entry)
    return index


def journal_meta(venue: Any, index: Dict[str, Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """按 全名 / 缩写 / 首字母缩写 匹配分区表。"""
    if not venue or not index:
        return None
    v = _alpha_only(str(venue))
    if not v:
        return None
    if v in index:
        return index[v]
    acr = _acronym(str(venue))
    if acr and acr in index:
        return index[acr]
    for key, entry in index.items():
        if len(key) >= 8 and (key in v or v in key):
            return entry
    return None


def journal_mark(rec: Dict[str, Any], index: Dict[str, Dict[str, Any]]) -> str:
    """返回「（1区 / ⭐ Top / 🔴 预警）」片段 + IF。"""
    meta = journal_meta(rec.get("venue"), index)
    parts: List[str] = []
    if meta:
        zone = str(meta.get("zone") or "").strip()
        if zone:
            parts.append(f"{zone}区")
        if meta.get("top"):
            parts.append("⭐ Top")
        if meta.get("warning"):
            parts.append("🔴 预警")
        if meta.get("if_2024"):
            parts.append(f"IF {meta['if_2024']}")
    if rec.get("is_preprint"):
        parts.append(f"[Preprint {rec.get('preprint_server') or ''}]".strip())
    return " / ".join(parts)


# ---------------------------------------------------------------------------
# 引用格式
# ---------------------------------------------------------------------------
def _first_author_token(rec: Dict[str, Any]) -> str:
    authors = rec.get("authors") or []
    token = "anon"
    if authors:
        token = re.sub(r"[^A-Za-z]", "", authors[0].split()[-1]) or "anon"
    return f"{token.lower()}{rec.get('year') or 'nd'}"


def to_bibtex(rec: Dict[str, Any]) -> str:
    entry = _first_author_token(rec)
    authors = " and ".join(rec.get("authors") or []) or NA
    fields = [
        ("title", "{" + (rec.get("title") or NA) + "}"),
        ("author", "{" + authors + "}"),
        ("journal", "{" + (rec.get("venue") or NA) + "}"),
        ("year", "{" + str(rec.get("year") or NA) + "}"),
        ("volume", "{" + (str(rec.get("volume")) if rec.get("volume") else NA) + "}"),
        ("number", "{" + (str(rec.get("issue")) if rec.get("issue") else NA) + "}"),
        ("pages", "{" + (str(rec.get("page")) if rec.get("page") else NA) + "}"),
        ("doi", "{" + (rec.get("doi") or NA) + "}"),
    ]
    body = ",\n  ".join(f"{k} = {v}" for k, v in fields)
    return f"@article{{{entry},\n  {body}\n}}"


def _apa_author(name: str) -> str:
    parts = name.split()
    if len(parts) == 1:
        return parts[0]
    return f"{parts[-1]}, " + " ".join(f"{p[0]}." for p in parts[:-1])


def to_apa7(rec: Dict[str, Any]) -> str:
    authors = rec.get("authors") or []
    if not authors:
        auth = NA
    elif len(authors) == 1:
        auth = _apa_author(authors[0])
    elif len(authors) <= 20:
        auth = ", ".join(_apa_author(a) for a in authors[:-1]) + f", & {_apa_author(authors[-1])}"
    else:
        auth = ", ".join(_apa_author(a) for a in authors[:19]) + ", ... " + _apa_author(authors[-1])
    year = rec.get("year") or NA
    title = rec.get("title") or NA
    venue = rec.get("venue") or NA
    vol = str(rec.get("volume")) if rec.get("volume") else ""
    iss = str(rec.get("issue")) if rec.get("issue") else ""
    page = str(rec.get("page")) if rec.get("page") else ""
    tail = f"*{venue}*"
    if vol:
        tail += f", *{vol}*"
        if iss:
            tail += f"({iss})"
    if page:
        tail += f", {page}"
    tail += "."
    if rec.get("doi"):
        tail += f" https://doi.org/{rec['doi']}"
    return f"{auth} ({year}). {title}. {tail}"


def to_gbt7714(rec: Dict[str, Any]) -> str:
    authors = rec.get("authors") or []
    if not authors:
        auth = NA
    elif len(authors) > 3:
        auth = ", ".join(authors[:3]) + ", et al"
    else:
        auth = ", ".join(authors)
    parts = [f"{auth}. {rec.get('title') or NA}[J]."]
    venue = rec.get("venue") or NA
    year = rec.get("year") or NA
    loc = f"{venue}, {year}"
    if rec.get("volume"):
        loc += f", {rec['volume']}"
        if rec.get("issue"):
            loc += f"({rec['issue']})"
    if rec.get("page"):
        loc += f": {rec['page']}"
    parts.append(loc + ".")
    if rec.get("doi"):
        parts.append(f"DOI: {rec['doi']}.")
    return " ".join(parts)


def to_ris(rec: Dict[str, Any]) -> str:
    lines = ["TY  - JOUR"]
    for a in (rec.get("authors") or []):
        lines.append(f"AU  - {a}")
    lines.append(f"TI  - {rec.get('title') or NA}")
    lines.append(f"JO  - {rec.get('venue') or NA}")
    lines.append(f"PY  - {rec.get('year') or NA}")
    if rec.get("volume"):
        lines.append(f"VL  - {rec['volume']}")
    if rec.get("issue"):
        lines.append(f"IS  - {rec['issue']}")
    if rec.get("page"):
        lines.append(f"SP  - {rec['page']}")
    if rec.get("doi"):
        lines.append(f"DO  - {rec['doi']}")
    lines.append("ER  - ")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Markdown 渲染（对齐 SKILL.md §6.2）
# ---------------------------------------------------------------------------
def _abstract_cell(rec: Dict[str, Any]) -> str:
    ab = (rec.get("abstract") or "").strip()
    if not ab:
        return "N/A（出版商屏蔽，到 DOI 原页拉）"
    return ab


def render_markdown(
    query: str, topic_name: str, mode: str, records: Sequence[Dict[str, Any]],
    index: Dict[str, Dict[str, Any]], sources_used: Sequence[str],
    years_label: str, skipped: int, cross_pool: Sequence[str],
    concept_dropped: int, concept_kept: int, notes: Sequence[str],
) -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    type_label = "article-only（精细）" if mode == "fine" else "review-only（粗放）"
    lines: List[str] = []
    lines.append(f"# 文献检索结果（{'精细模式' if mode == 'fine' else '粗放模式 · 综述为主'}）")
    lines.append("")
    lines.append(f"**查询**：{query}")
    lines.append(f"**研究方向**：{topic_name}")
    lines.append(f"**时间范围**：{years_label}")
    lines.append(f"**文献类型**：{type_label}")
    lines.append(f"**数据源**：{', '.join(sources_used) if sources_used else NA}")
    lines.append(f"**检索时间**：{now}")
    lines.append(f"**模式**：{mode}")
    lines.append("")
    if notes:
        for note in notes:
            lines.append(f"> {note}")
        lines.append("")

    # 速览
    lines.append(f"## 📋 速览（{len(records)} 篇）")
    lines.append("")
    lines.append("| # | 标题 | 作者 | 年份 | DOI |")
    lines.append("|---|------|------|------|-----|")
    top = zone1 = warning = preprint = 0
    for i, rec in enumerate(records, 1):
        meta = journal_meta(rec.get("venue"), index)
        if meta:
            if str(meta.get("zone")) == "1":
                zone1 += 1
            if meta.get("top"):
                top += 1
            if meta.get("warning"):
                warning += 1
        if rec.get("is_preprint"):
            preprint += 1
        authors = rec.get("authors") or []
        author_cell = ", ".join(authors[:3]) + (", et al." if len(authors) > 3 else "") if authors else NA
        doi = rec.get("doi")
        doi_cell = f"[{doi}](https://doi.org/{doi})" if doi else NA
        title = rec.get("title") or NA
        lines.append(f"| {i} | [{title}](#title-{i}) | {author_cell} | "
                     f"{rec.get('year') or NA} | {doi_cell} |")
    lines.append("")
    stats = [f"⭐ Top {top} 篇", f"1 区 {zone1} 篇", f"🔴 预警 {warning} 篇",
             f"[Preprint] {preprint} 篇", f"已跳过重复 {skipped} 篇"]
    if cross_pool and skipped:
        stats.append(f"（跨主题去重，来源 pool: {', '.join(cross_pool)}）")
    if concept_dropped:
        stats.append(f"方向过滤剔除 {concept_dropped} 篇（保留 {concept_kept} 篇）")
    lines.append("> " + " · ".join(stats))
    lines.append("")
    lines.append("---")
    lines.append("")

    # 详细条目
    lines.append("## 📚 详细条目")
    lines.append("")
    for i, rec in enumerate(records, 1):
        lines.append(f"### # {i} <a id=\"title-{i}\"></a> {rec.get('title') or NA}")
        authors = rec.get("authors") or []
        lines.append(f"- **作者**：{', '.join(authors) if authors else NA}（仅来自 API）")
        lines.append(f"- **年份**：{rec.get('year') or NA}")
        mark = journal_mark(rec, index)
        lines.append(f"- **期刊**：{rec.get('venue') or NA}" + (f"（{mark}）" if mark else ""))
        meta = journal_meta(rec.get("venue"), index)
        lines.append(f"- **影响因子**：{meta.get('if_2024') if meta and meta.get('if_2024') else NA}")
        doi = rec.get("doi")
        lines.append(f"- **DOI**：{f'[{doi}](https://doi.org/{doi})' if doi else NA}")
        lines.append(f"- **卷/期/页**：{_vol_issue_page(rec)}")
        kws = rec.get("keywords") or []
        kw_label = f"关键词（{rec['kw_note']}）" if rec.get("kw_note") else "关键词"
        lines.append(f"- **{kw_label}**：{', '.join(kws) if kws else NA}")
        lines.append(f"- **摘要原文**：{_abstract_cell(rec)}")
        lines.append(f"- **TLDR**（AI 总结）：{rec.get('tldr') or NA}")
        marks = []
        if rec.get("is_preprint"):
            marks.append(f"[Preprint {rec.get('preprint_server') or ''}]".strip())
        if rec.get("oa_url"):
            marks.append(f"[OA 全文]({rec['oa_url']})")
        marks.append(f"来源: {', '.join(rec.get('sources') or [])}")
        if rec.get("concept_hits"):
            marks.append(f"方向命中 {rec['concept_hits']}")
        lines.append(f"- **标记**：{' · '.join(marks)}")
        lines.append("")
        lines.append("#### 📎 引用格式")
        for label, body in (("BibTeX", to_bibtex(rec)), ("APA 7", to_apa7(rec)),
                            ("GB/T 7714", to_gbt7714(rec)), ("RIS", to_ris(rec))):
            fence = "bibtex" if label == "BibTeX" else ("text" if label == "RIS" else "text")
            lines.append("<details>")
            lines.append(f"<summary>{label}</summary>")
            lines.append("")
            lines.append(f"```{fence}")
            lines.append(body)
            lines.append("```")
            lines.append("")
            lines.append("</details>")
            lines.append("")
        lines.append("---")
        lines.append("")
    return "\n".join(lines)


def _vol_issue_page(rec: Dict[str, Any]) -> str:
    vol = str(rec.get("volume")) if rec.get("volume") else ""
    iss = str(rec.get("issue")) if rec.get("issue") else ""
    page = str(rec.get("page")) if rec.get("page") else ""
    if not any((vol, iss, page)):
        return NA
    s = vol or "—"
    if iss:
        s += f"({iss})"
    if page:
        s += f": {page}"
    return s


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="paper_search_client.py",
        description="qm_paper_search 检索客户端（SS → OpenAlex → Crossref 多源合并 + 去重 + Markdown 导出）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "示例:\n"
            "  python paper_search_client.py -q \"machine learning potential\" --pretty\n"
            "  python paper_search_client.py -q \"COF 催化\" --count 20 --years 5\n"
            "  python paper_search_client.py -q \"钙钛矿\" --mode broad --concept-pattern \"perovskite|solar\"\n"
            "  python paper_search_client.py -q \"MOF\" --dry-run --json-out raw.json\n"
        ),
    )
    p.add_argument("-q", "--query", required=True, help="检索关键词")
    p.add_argument("--mode", choices=["auto", "fine", "broad"], default="auto",
                   help="检索模式（默认 auto，按 SKILL §5.1 从 query 推断）")
    p.add_argument("--topic", help="研究方向名（默认由 query 生成 slug）")
    p.add_argument("--count", type=int, default=0, help="返回篇数（默认精细 10 / 粗放 15）")
    p.add_argument("--years", default="", help="时间范围年数（如 5；空=精细 3 年、粗放不限）")
    p.add_argument("--type", dest="pub_type", choices=["auto", "article", "review", "all"],
                   default="auto", help="文献类型过滤")
    p.add_argument("--sort", choices=["relevance", "time", "citations", "time+citations"],
                   default="auto", help="排序方式")
    p.add_argument("--concept-pattern", help="方案 H 宽召回二次过滤正则")
    p.add_argument("--min-concept-match", type=int, default=1, help="至少命中的概念数（默认 1）")
    p.add_argument("--sources", default="ss,openalex,crossref",
                   help="参与检索的源（逗号分隔，默认 ss,openalex,crossref）")
    p.add_argument("--enrich-max", type=int, default=8,
                   help="按 DOI 向 Crossref 补元数据的最大条数（默认 8）")
    p.add_argument("--no-dedup", action="store_true", help="关闭去重池（本方向）")
    p.add_argument("--global-dedup", action="store_true", help="跨全部 topic 全局去重")
    p.add_argument("--no-cross-topic", action="store_true", help="关闭跨 topic 合并去重")
    p.add_argument("--out", help="输出目录或 .md 文件路径（默认 user_prefs.json 的 default_save_dir）")
    p.add_argument("--json-out", help="额外输出原始 JSON（便于上层处理）")
    p.add_argument("--verify", action="store_true", help="导出后调用 validate_output.py 做 DOI 反查")
    p.add_argument("--dry-run", action="store_true", help="不写 seen_papers / 不写 .md，仅打印统计")
    p.add_argument("--pretty", action="store_true", help="打印人类可读摘要")
    p.add_argument("--quiet", action="store_true", help="静默模式（仅错误输出）")
    return p


def default_out_dir() -> Path:
    prefs = DATA_DIR / "user_prefs.json"
    if prefs.is_file():
        try:
            data = json.loads(prefs.read_text(encoding="utf-8-sig"))
            val = (data.get("default_save_dir") or "").strip()
            if val:
                return Path(val)
        except Exception:  # noqa: BLE001
            pass
    return Path.cwd() / "papers"


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)

    query = args.query.strip()
    if not query:
        print("❌ 查询为空", file=sys.stderr)
        return 3

    mode = infer_mode(query, None if args.mode == "auto" else args.mode)
    pub_type = args.pub_type
    if pub_type == "auto":
        pub_type = "article" if mode == "fine" else "review"
    sort_by = args.sort
    if sort_by == "auto":
        sort_by = "relevance" if mode == "fine" else "time+citations"

    count = args.count or (10 if mode == "fine" else 15)
    if args.years.strip():
        try:
            years_n = int(args.years.strip())
        except ValueError:
            print(f"❌ --years 需为整数，收到 {args.years!r}", file=sys.stderr)
            return 3
    else:
        years_n = 3 if mode == "fine" else 0
    this_year = datetime.now().year
    years_lo = this_year - years_n + 1 if years_n > 0 else None
    years_hi = this_year if years_lo else None
    years_label = f"{years_lo}–{years_hi}" if years_lo else "不限"

    topic_name = (args.topic or query).strip()
    topic_id = f"{mode}_{slugify(topic_name)}"

    if not args.quiet:
        print(f"⏳ 检索中：query={query!r} mode={mode} count={count} "
              f"years={years_label} type={pub_type} sort={sort_by}")

    keys = load_keys(verbose=args.pretty)
    mailto = None
    local = DATA_DIR / "api_keys.local.json"
    if local.is_file():
        try:
            cfg = json.loads(local.read_text(encoding="utf-8-sig"))
            mailto = (cfg.get("mailto_for_openalex") or "").strip() or None
        except Exception:  # noqa: BLE001
            mailto = None

    logs: List[Dict[str, Any]] = []
    notes: List[str] = []
    records: List[Dict[str, Any]] = []
    sources_used: List[str] = []
    warn = "⚠️"
    srcs = {s.strip() for s in args.sources.split(",") if s.strip()}

    # 1) 主检索：SS
    def _why(e: Optional[str]) -> str:
        return e or "连接正常但 0 命中（OpenAlex/SS 全文检索仅支持英文，中文查询请改用英文关键词）"

    if "ss" in srcs:
        got, err = search_semanticscholar(
            query, max(count * 2, 20), years_lo, years_hi, keys.get("semantic_scholar"), logs)
        if got:
            records.extend(got)
            sources_used.append("Semantic Scholar")
        else:
            notes.append(f"{warn} Semantic Scholar 不可用（{_why(err)}），已跳过该源。")
            print(f"{warn} Semantic Scholar 不可用：{_why(err)}；已切下游源。", file=sys.stderr)

    # 2) 覆盖兜底：OpenAlex
    if "openalex" in srcs:
        got, err = search_openalex(
            query, max(count * 2, 20), mode, years_lo, pub_type,
            keys.get("openalex"), mailto, logs)
        if got:
            records.extend(got)
            sources_used.append("OpenAlex")
        else:
            notes.append(f"{warn} OpenAlex 不可用（{_why(err)}），已跳过该源。")
            print(f"{warn} OpenAlex 不可用：{_why(err)}；已切下游源。", file=sys.stderr)

    # 3) 元数据权威：Crossref
    if "crossref" in srcs:
        got, err = search_crossref(query, max(count, 10), years_lo, mailto, logs)
        if got:
            records.extend(got)
            sources_used.append("Crossref")
        else:
            notes.append(f"{warn} Crossref 不可用（{_why(err)}），已跳过该源。")

    if not records:
        print("❌ 全部数据源失败：", file=sys.stderr)
        for note in notes:
            print("   " + note, file=sys.stderr)
        print("   请检查网络或稍后重试；也可只给关键词让我改用 web_search 兜底（覆盖率会下降）。",
              file=sys.stderr)
        return 2

    # 4) 合并 + 过滤
    merged = merge_records(records)
    merged = apply_type_filter(merged, mode, pub_type)

    # 5) 补元数据
    if args.enrich_max > 0:
        filled = enrich_via_crossref(merged, args.enrich_max, mailto, logs)

    # 6) 方案 H 方向过滤
    merged, concept_dropped = apply_concept_filter(
        merged, args.concept_pattern, args.min_concept_match)
    concept_kept = len(merged)

    # 7) 去重池
    seen = load_seen()
    tokens = query_tokens(query)
    skipped = 0
    cross_pool: List[str] = []
    if not args.no_dedup:
        seen_dois, cross_pool = pool_scope(
            seen, topic_id, tokens, not args.no_cross_topic, args.global_dedup)
        before = len(merged)
        kept = [r for r in merged if not (norm_doi(r.get("doi")) and norm_doi(r["doi"]) in seen_dois)]
        skipped = before - len(kept)
        # 若去重后不足目标篇数的 50%，退回不去重（避免"检索出来是空的"）
        if len(kept) >= max(count // 2, 3) or not kept:
            merged = kept
        elif skipped:
            notes.append(f"{warn} 去重后仅剩 {len(kept)} 篇（跳过 {skipped} 篇），"
                         f"已放宽为不去重以保证交付数量。")
            skipped = 0
    else:
        cross_pool = []

    merged = sort_records(merged, sort_by)[:count]

    # 8) 渲染
    index = load_journal_index()
    markdown = render_markdown(
        query=query, topic_name=topic_name, mode=mode, records=merged, index=index,
        sources_used=sources_used, years_label=years_label, skipped=skipped,
        cross_pool=cross_pool, concept_dropped=concept_dropped, concept_kept=concept_kept,
        notes=notes,
    )

    out_dir = Path(args.out) if args.out else default_out_dir()
    if out_dir.suffix.lower() == ".md":
        md_path = out_dir
        out_dir = md_path.parent
    else:
        md_path = out_dir / f"paper_search_{mode}_{slugify(topic_name)}_{datetime.now():%Y%m%d}.md"

    if args.json_out:
        json_path = Path(args.json_out)
        json_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.write_text(
            json.dumps({"query": query, "mode": mode, "topic": topic_name,
                        "sources": sources_used, "count": len(merged),
                        "records": merged}, ensure_ascii=False, indent=2),
            encoding="utf-8")

    if args.dry_run:
        if not args.quiet:
            print(f"🧪 dry-run：命中 {len(merged)} 篇（未写文件 / 未更新去重池）")
        return 0

    out_dir.mkdir(parents=True, exist_ok=True)
    md_path.write_text(markdown, encoding="utf-8")

    if not args.no_dedup:
        mark_seen(seen, topic_id, topic_name, query, mode, merged,
                  ", ".join(sources_used) or NA)
        save_seen(seen)

    if args.pretty:
        print(f"✅ 完成：{len(merged)} 篇 → {md_path}")
        if skipped:
            print(f"   （跳过重复 {skipped} 篇；跨主题 pool: {', '.join(cross_pool) or '—'}）")
        if concept_dropped:
            print(f"   （方向过滤剔除 {concept_dropped} 篇，保留 {concept_kept} 篇）")
        print(f"   数据源：{', '.join(sources_used)}")
    elif not args.quiet:
        print(f"✅ {len(merged)} 篇 → {md_path}")

    if args.verify:
        rc = run_verify(md_path)
        if rc != 0:
            print(f"{warn} 交付前校验未达标（详见上方输出）：请人工复核标 ❌ 的条目。",
                  file=sys.stderr)
            return 4
    return 0


def run_verify(md_path: Path) -> int:
    """复用同目录的 validate_output.py 做 DOI 反查。"""
    import importlib.util

    vp = SCRIPT_DIR / "validate_output.py"
    if not vp.is_file():
        print("⚠️ 未找到 validate_output.py，跳过 --verify", file=sys.stderr)
        return 0
    spec = importlib.util.spec_from_file_location("validate_output", vp)
    if spec is None or spec.loader is None:
        return 0
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    summary = mod.validate_markdown_file(md_path, verbose=True)
    rate = summary.get("verification_rate")
    if rate is not None and rate < 0.95:
        print(f"❌ DOI 校验率 {rate * 100:.1f}% < 95%：{summary['verified']}/{summary['total_dois']}")
        return 2
    print(f"✅ DOI 校验通过：{summary['verified']}/{summary['total_dois']}")
    return 0


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:  # noqa: BLE001
        pass
    sys.exit(main())
