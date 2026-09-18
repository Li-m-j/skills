#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""paper_search_client.py — mbai_paper_search 检索客户端（v0.4.0 · 零第三方依赖）

定位：医学 / 生物信息学 / 人工智能 主题的检索客户端。
      与 `qm_paper_search_shared/data/scripts/paper_search_client.py` **同构**——
      代码骨架、CLI 参数、输出约定完全一致；**只有数据源与扩展字段不同**：
        qm  ：Semantic Scholar → OpenAlex → Crossref（+ X-Mol 跳转）
        mbai：Semantic Scholar → OpenAlex → **PubMed E-utilities** → **Europe PMC** → Crossref
              额外字段：MeSH 主题词 / Publication Type（证据等级）/ 临床试验注册号 / PMID / 预印本服务器

职责：
    1. 多源检索 + 规范化 + 合并去重（DOI 优先，无 DOI 回退 PMID / 标准化标题）
    2. 医学扩展字段抽取：MeSH、Publication Type → 证据等级、NCT/ChiCTR 注册号
    3. 方案 H 宽召回二次方向过滤（`--concept-pattern`，不额外发请求）
    4. seen_papers.json 读写（`fine_*` / `broad_*` 前缀 + 跨 topic 合并去重，含 seen_pmids）
    5. 导出 SKILL.md §6.2 规定的 Markdown（含 MeSH / 证据等级 / 注册号行）
    6. `--verify`：交付前复用 `validate_output.py` 做 DOI + PMID 反查

依赖：仅 Python 3.8+ 标准库（urllib + xml.etree）。Windows / Linux / macOS 通用（UTF-8）。

用法：
    python paper_search_client.py -q "PD-1 inhibitor NSCLC" --pretty
    python paper_search_client.py -q "single-cell spatial transcriptomics" --mode broad --count 15
    python paper_search_client.py -q "medical LLM" --evidence RCT优先 --sources pubmed,openalex
    python paper_search_client.py -q "AlphaFold" --include-preprint --verify --out "D:/papers"

退出码：
    0 成功；2 全部数据源失败；3 参数错误；4 检索成功但 DOI/PMID 校验未达标（--verify）
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
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

# ---------------------------------------------------------------------------
# 路径与常量
# ---------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).resolve().parent          # .../data/scripts
DATA_DIR = SCRIPT_DIR.parent                          # .../data
USER_AGENT = "mbai_paper_search_skill/0.4 (paper search client)"
TOOL_TAG = "mbai_paper_search"
NA = "N/A"

SS_SEARCH = "https://api.semanticscholar.org/graph/v1/paper/search"
SS_FIELDS = (
    "title,abstract,year,venue,publicationVenue,externalIds,authors,"
    "fieldsOfStudy,tldr,citationCount,openAccessPdf,publicationTypes"
)
OPENALEX_WORKS = "https://api.openalex.org/works"
PUBMED_ESEARCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
PUBMED_EFETCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
EUROPEPMC_SEARCH = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
CROSSREF_WORKS = "https://api.crossref.org/works"

STOPWORDS = {
    "the", "a", "an", "of", "in", "on", "for", "and", "or", "with", "via",
    "using", "study", "review", "analysis", "toward", "towards", "based",
    "文献", "检索", "综述", "概览", "立项", "摸底", "深度", "方法",
}
REVIEW_HINT = re.compile(
    r"(?i)\b(review|meta[\-\s]?analysis|systematic|overview|advances?\s+in|"
    r"perspective|progress\s+in|guideline|consensus)\b"
)
PREPRINT_HINT = re.compile(r"(?i)(biorxiv|medrxiv|chemrxiv|arxiv|research\s*square|ssrn|preprint)")
TRIAL_ID_RE = re.compile(r"\b(NCT\d{8}|ChiCTR[\w\-]{4,}|ISRCTN\d{8}|UMIN\d{9}|CTRI/\d{4}/\d+/\d+)\b")

# PubMed Publication Type → 证据等级
EVIDENCE_MAP = [
    ("randomized controlled trial", "RCT"),
    ("meta-analysis", "Meta-analysis"),
    ("systematic review", "Systematic Review"),
    ("practice guideline", "Guideline"),
    ("guideline", "Guideline"),
    ("consensus development conference", "Consensus"),
    ("cohort", "Cohort"),
    ("observational study", "Observational"),
    ("case reports", "Case Report"),
    ("clinical trial", "Clinical Trial"),
    ("review", "Review"),
    ("editorial", "Editorial"),
    ("comment", "Comment"),
]


# ---------------------------------------------------------------------------
# 基础工具
# ---------------------------------------------------------------------------
def http_get_text(
    url: str, headers: Optional[Dict[str, str]] = None, timeout: int = 25,
    retries: int = 2, sleep_base: float = 1.0, log: Optional[List[Dict[str, Any]]] = None,
) -> Tuple[Optional[str], Optional[str]]:
    hdr = {"User-Agent": USER_AGENT, "Accept": "*/*"}
    if headers:
        hdr.update(headers)
    last_err: Optional[str] = None
    for attempt in range(retries + 1):
        t0 = time.time()
        try:
            req = urllib.request.Request(url, headers=hdr)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                status = getattr(resp, "status", 200)
                text = resp.read().decode("utf-8", errors="replace")
            if log is not None:
                log.append({"ts": datetime.now().isoformat(timespec="seconds"),
                            "url": url.split("?")[0], "status": status,
                            "latency_ms": int((time.time() - t0) * 1000)})
            return text, None
        except urllib.error.HTTPError as exc:
            last_err = f"HTTP {exc.code} {exc.reason}"
            if log is not None:
                log.append({"ts": datetime.now().isoformat(timespec="seconds"),
                            "url": url.split("?")[0], "status": exc.code,
                            "latency_ms": int((time.time() - t0) * 1000), "note": last_err})
            if exc.code in (400, 401, 403, 404):
                break
        except urllib.error.URLError as exc:
            last_err = f"网络层失败: {exc.reason}"
        except Exception as exc:  # noqa: BLE001
            last_err = f"未预期错误: {type(exc).__name__}: {exc}"
        if attempt < retries:
            time.sleep(sleep_base * (attempt + 1))
    return None, last_err or "unknown error"


def http_get_json(url: str, **kw: Any) -> Tuple[Optional[Any], Optional[str]]:
    text, err = http_get_text(url, **kw)
    if text is None:
        return None, err
    try:
        return json.loads(text), None
    except ValueError as exc:
        return None, f"JSON 解析失败: {exc}"


def load_keys(verbose: bool = False) -> Dict[str, str]:
    """读取 key：api_keys.local.json > 环境变量。"""
    keys: Dict[str, str] = {}
    local = DATA_DIR / "api_keys.local.json"
    if local.is_file():
        try:
            cfg = json.loads(local.read_text(encoding="utf-8-sig"))
        except Exception:  # noqa: BLE001
            cfg = {}
        if isinstance(cfg, dict):
            prov = cfg.get("providers") if isinstance(cfg.get("providers"), dict) else {}
            for name in ("openalex", "semantic_scholar", "ncbi"):
                node = prov.get(name)
                if isinstance(node, dict):
                    val = (node.get("key") or "").strip()
                    if val and not val.upper().startswith(("YOUR_", "REPLACE")):
                        keys[name] = val
            flat = {
                "openalex_api_key": "openalex",
                "semantic_scholar_api_key": "semantic_scholar",
                "ncbi_api_key": "ncbi",
            }
            for field, name in flat.items():
                val = cfg.get(field)
                if isinstance(val, str) and val.strip() and not val.upper().startswith("REPLACE"):
                    keys.setdefault(name, val.strip())
            email = (cfg.get("europe_pmc_contact_email") or cfg.get("mailto_for_openalex") or "").strip()
            if email and "example.com" not in email and "@" in email:
                keys["email"] = email
    for env, name in (("OPENALEX_API_KEY", "openalex"),
                      ("SEMANTIC_SCHOLAR_API_KEY", "semantic_scholar"),
                      ("NCBI_API_KEY", "ncbi"),
                      ("MABI_CONTACT_EMAIL", "email")):
        val = os.environ.get(env)
        if val and val.strip():
            keys[name] = val.strip()
    if verbose:
        print("   key 状态: " + ", ".join(
            f"{k}={'✓' if keys.get(k) else '✗'}" for k in ("openalex", "semantic_scholar", "ncbi")))
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


def clean_text(text: Any) -> str:
    if not text:
        return ""
    s = re.sub(r"<[^>]+>", " ", str(text))
    return re.sub(r"\s+", " ", s).strip()


def infer_mode(query: str, explicit: Optional[str]) -> str:
    if explicit in ("fine", "broad"):
        return explicit
    if re.search(r"(?i)概览|立项|综述|摸底|survey|landscape|全景|review|指南|guideline", query):
        return "broad"
    if re.search(r"(?i)深度|方法|创新|对比|复现|机制|通路|算法", query):
        return "fine"
    return "fine"


def evidence_of(pub_types: Sequence[str]) -> str:
    joined = " ; ".join(t or "" for t in pub_types).lower()
    for needle, label in EVIDENCE_MAP:
        if needle in joined:
            return label
    return ""


# ---------------------------------------------------------------------------
# 记录结构
# ---------------------------------------------------------------------------
def blank_record() -> Dict[str, Any]:
    return {
        "title": "", "authors": [], "year": None, "venue": "", "volume": "",
        "issue": "", "page": "", "doi": "", "pmid": "", "abstract": "",
        "keywords": [], "mesh": [], "pub_types": [], "evidence": "",
        "trial_ids": [], "tldr": "", "citation_count": None, "source": "",
        "sources": [], "oa_url": "", "is_preprint": False, "preprint_server": "",
        "concepts": [], "kw_note": "",
    }


# ---------------------------------------------------------------------------
# 各源解析
# ---------------------------------------------------------------------------
def parse_semanticscholar(item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    title = (item.get("title") or "").strip()
    if not title:
        return None
    r = blank_record()
    r["title"] = title
    r["abstract"] = clean_text(item.get("abstract") or "")
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
    r["evidence"] = evidence_of(r["pub_types"])
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
    r["abstract"] = clean_text(reconstruct_abstract(item.get("abstract_inverted_index")))
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
    r["authors"] = [((a.get("author") or {}).get("display_name") or "").strip()
                    for a in (item.get("authorships") or [])]
    r["authors"] = [a for a in r["authors"] if a]
    concepts = [(c.get("display_name") or "").strip()
                for c in (item.get("concepts") or []) if c.get("display_name")]
    r["concepts"] = concepts[:12]
    r["keywords"] = r["concepts"][:8]
    if r["keywords"]:
        r["kw_note"] = "概念标签，来自 OpenAlex concepts"
    r["citation_count"] = item.get("cited_by_count")
    oa = item.get("open_access") or {}
    if isinstance(oa, dict):
        r["oa_url"] = (oa.get("oa_url") or "").strip()
    ids = item.get("ids") or {}
    if isinstance(ids, dict):
        r["pmid"] = str(ids.get("pmid") or "").replace("https://pubmed.ncbi.nlm.nih.gov/", "").strip("/")
    otype = (item.get("type") or "").lower()
    r["pub_types"] = ([otype] if otype else [])
    if otype == "review":
        r["pub_types"].append("Review")
    r["evidence"] = evidence_of(r["pub_types"])
    r["source"] = "openalex"
    r["sources"] = ["openalex"]
    r["is_preprint"] = otype == "preprint" or bool(PREPRINT_HINT.search(r["venue"]))
    if r["is_preprint"]:
        r["preprint_server"] = r["venue"]
    return r


def _find_text(node: Optional[ET.Element], path: str) -> str:
    if node is None:
        return ""
    found = node.find(path)
    return (found.text or "").strip() if found is not None and found.text else ""


def parse_pubmed_xml(xml_text: str) -> List[Dict[str, Any]]:
    """解析 efetch（retmode=xml）返回的 PubmedArticleSet。"""
    out: List[Dict[str, Any]] = []
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return out

    for art in root.iter("PubmedArticle"):
        cit = art.find("MedlineCitation")
        if cit is None:
            continue
        art_node = cit.find("Article")
        if art_node is None:
            continue
        r = blank_record()
        r["title"] = clean_text(_find_text(art_node, "ArticleTitle"))
        if not r["title"]:
            continue
        r["pmid"] = _find_text(cit, "PMID")
        # 摘要（可能多段 Label）
        chunks = []
        for ab in art_node.iter("AbstractText"):
            label = (ab.get("Label") or "").strip()
            body = clean_text("".join(ab.itertext()))
            if body:
                chunks.append(f"{label}: {body}" if label else body)
        r["abstract"] = " ".join(chunks)
        # 作者
        authors = []
        for a in art_node.iter("Author"):
            last = _find_text(a, "LastName")
            fore = _find_text(a, "ForeName") or _find_text(a, "Initials")
            coll = _find_text(a, "CollectiveName")
            name = " ".join(x for x in (fore, last) if x) or coll
            if name:
                authors.append(name)
        r["authors"] = authors
        # 期刊 / 卷期页 / 年
        journal = art_node.find("Journal")
        if journal is not None:
            r["venue"] = _find_text(journal, "Title") or _find_text(journal, "ISOAbbreviation")
            ji = journal.find("JournalIssue")
            if ji is not None:
                r["volume"] = _find_text(ji, "Volume")
                r["issue"] = _find_text(ji, "Issue")
                year = _find_text(ji, "PubDate/Year") or _find_text(ji, "PubDate/MedlineDate")
                m = re.search(r"(19|20)\d{2}", year or "")
                if m:
                    r["year"] = int(m.group(0))
        r["page"] = _find_text(art_node, "Pagination/MedlinePgn")
        if r["year"] is None:
            y = _find_text(art_node, "ArticleDate/Year")
            if y.isdigit():
                r["year"] = int(y)
        # DOI / PMC
        for eid in art_node.iter("ELocationID"):
            if (eid.get("EIdType") or "").lower() == "doi":
                r["doi"] = norm_doi(eid.text)
        pmc = ""
        for aid in art.iter("ArticleId"):
            itype = (aid.get("IdType") or "").lower()
            if itype == "doi" and not r["doi"]:
                r["doi"] = norm_doi(aid.text)
            if itype == "pmc":
                pmc = (aid.text or "").strip()
        if pmc:
            r["oa_url"] = f"https://www.ncbi.nlm.nih.gov/pmc/articles/{pmc}/"
        # MeSH
        r["mesh"] = [clean_text(_find_text(mh, "DescriptorName"))
                     for mh in cit.iter("MeshHeading")]
        r["mesh"] = [m for m in r["mesh"] if m]
        # Publication Type / 证据等级
        r["pub_types"] = [clean_text(pt.text) for pt in art_node.iter("PublicationType")
                          if clean_text(pt.text)]
        r["evidence"] = evidence_of(r["pub_types"])
        r["keywords"] = r["mesh"][:8]
        r["source"] = "pubmed"
        r["sources"] = ["pubmed"]
        # 临床试验注册号
        hay = r["abstract"] + " " + r["title"]
        r["trial_ids"] = sorted(set(TRIAL_ID_RE.findall(hay)))
        for db in art.iter("DataBankName"):
            name = clean_text(db.text)
            if name:
                r["trial_ids"] = sorted(set(r["trial_ids"]) | {name})
        out.append(r)
    return out


def parse_europepmc(item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    title = (item.get("title") or "").strip().rstrip(".")
    if not title:
        return None
    r = blank_record()
    r["title"] = clean_text(title)
    r["abstract"] = clean_text(item.get("abstractText") or "")
    try:
        r["year"] = int(item.get("pubYear"))
    except (TypeError, ValueError):
        r["year"] = None
    r["venue"] = clean_text(item.get("journalTitle") or "")
    r["volume"] = str(item.get("journalVolume") or "")
    r["issue"] = str(item.get("issue") or "")
    r["page"] = str(item.get("pageInfo") or "")
    r["doi"] = norm_doi(item.get("doi"))
    r["pmid"] = str(item.get("pmid") or "")
    al = item.get("authorString")
    if isinstance(al, str) and al.strip():
        r["authors"] = [a.strip() for a in re.split(r",|;", al) if a.strip()]
    r["pub_types"] = [clean_text(p) for p in (item.get("pubTypeList", {}) or {}).get("pubType", [])]
    r["evidence"] = evidence_of(r["pub_types"])
    mesh = ((item.get("meshHeadingList") or {}).get("meshHeading") or [])
    r["mesh"] = [clean_text((m.get("descriptorName") or "")) for m in mesh]
    r["mesh"] = [m for m in r["mesh"] if m]
    kws = ((item.get("keywordList") or {}).get("keyword") or [])
    r["keywords"] = [clean_text(k) for k in kws][:8] or r["mesh"][:8]
    r["citation_count"] = item.get("citedByCount")
    if item.get("isOpenAccess") == "Y":
        r["oa_url"] = f"https://europepmc.org/article/MED/{r['pmid']}" if r["pmid"] else ""
    src = (item.get("source") or "").upper()
    r["is_preprint"] = src == "PPR" or bool(PREPRINT_HINT.search(r["venue"]))
    if r["is_preprint"]:
        r["preprint_server"] = r["venue"] or "Europe PMC preprint"
    r["source"] = "europe_pmc"
    r["sources"] = ["europe_pmc"]
    r["trial_ids"] = sorted(set(TRIAL_ID_RE.findall(r["abstract"] + " " + r["title"])))
    return r


def parse_crossref(item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    titles = item.get("title") or []
    title = (titles[0] if titles else "").strip()
    if not title:
        return None
    r = blank_record()
    r["title"] = clean_text(title)
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
    ab = clean_text(item.get("abstract") or "")
    r["abstract"] = ab if len(ab) >= 200 else ""
    pt = item.get("type") or ""
    r["pub_types"] = ["Review"] if pt == "review" else ([pt] if pt else [])
    r["evidence"] = evidence_of(r["pub_types"])
    r["source"] = "crossref"
    r["sources"] = ["crossref"]
    return r


# ---------------------------------------------------------------------------
# 各源检索
# ---------------------------------------------------------------------------
def search_semanticscholar(query, limit, years_lo, years_hi, api_key, log):
    params = {"query": query, "limit": str(min(max(limit, 1), 100)), "fields": SS_FIELDS}
    if years_lo and years_hi:
        params["year"] = f"{years_lo}-{years_hi}"
    url = SS_SEARCH + "?" + urllib.parse.urlencode(params)
    data, err = http_get_json(url, headers={"x-api-key": api_key} if api_key else None, log=log)
    if data is None:
        return [], err
    out = [parse_semanticscholar(i) for i in (data.get("data") or [])]
    return [x for x in out if x], None


def openalex_filters(mode, years_lo, pub_type):
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


def search_openalex(query, limit, mode, years_lo, pub_type, api_key, email, log):
    params: Dict[str, str] = {"search": query,
                              "per-page": str(min(max(limit, 1), 200)),
                              "sort": "relevance_score:desc"}
    flt = openalex_filters(mode, years_lo, pub_type)
    if flt:
        params["filter"] = flt
    if email:
        params["mailto"] = email
    if api_key:
        params["api_key"] = api_key
    url = OPENALEX_WORKS + "?" + urllib.parse.urlencode(params)
    data, err = http_get_json(url, log=log)
    if data is None:
        return [], err
    out = [parse_openalex(i) for i in (data.get("results") or [])]
    return [x for x in out if x], None


def search_pubmed(query, limit, years_lo, api_key, email, log, mode="fine"):
    """esearch（拿 PMID）→ efetch（拿完整元数据 + MeSH）。"""
    term = query
    if mode == "broad":
        term += ' AND (review[pt] OR systematic[sb] OR "meta-analysis"[pt] OR guideline[pt])'
    if years_lo:
        term += f" AND {years_lo}:3000[dp]"
    params = {
        "db": "pubmed", "term": term, "retmax": str(min(max(limit, 1), 100)),
        "retmode": "json", "sort": "relevance", "tool": TOOL_TAG,
    }
    if api_key:
        params["api_key"] = api_key
    if email:
        params["email"] = email
    data, err = http_get_json(PUBMED_ESEARCH + "?" + urllib.parse.urlencode(params), log=log)
    if data is None:
        return [], err
    ids = ((data.get("esearchresult") or {}).get("idlist") or [])
    if not ids:
        return [], None
    time.sleep(0.4)
    fparams = {"db": "pubmed", "id": ",".join(ids), "retmode": "xml", "tool": TOOL_TAG}
    if api_key:
        fparams["api_key"] = api_key
    if email:
        fparams["email"] = email
    xml_text, err = http_get_text(PUBMED_EFETCH + "?" + urllib.parse.urlencode(fparams),
                                 timeout=40, log=log)
    if xml_text is None:
        return [], f"efetch 失败: {err}"
    return parse_pubmed_xml(xml_text), None


def search_europepmc(query, limit, years_lo, pub_type, email, log):
    query_str = f'({query}) AND (SRC:MED OR SRC:PMC OR SRC:PPR)'
    if pub_type == "review":
        query_str += ' AND (PUB_TYPE:"Review" OR PUB_TYPE:"systematic review")'
    if years_lo:
        query_str += f" AND (PUB_YEAR:[{years_lo} TO 3000])"
    params = {"query": query_str, "format": "json",
              "pageSize": str(min(max(limit, 1), 100)), "resultType": "core"}
    if email:
        params["email"] = email
    url = EUROPEPMC_SEARCH + "?" + urllib.parse.urlencode(params)
    data, err = http_get_json(url, log=log)
    if data is None:
        return [], err
    out = [parse_europepmc(i) for i in ((data.get("resultList") or {}).get("result") or [])]
    return [x for x in out if x], None


def search_crossref(query, limit, years_lo, email, log):
    params = {
        "query.bibliographic": query, "rows": str(min(max(limit, 1), 100)),
        "select": "DOI,title,author,container-title,volume,issue,page,published,issued,abstract,type",
    }
    if email:
        params["mailto"] = email
    if years_lo:
        params["filter"] = f"from-pub-date:{years_lo}-01-01"
    data, err = http_get_json(CROSSREF_WORKS + "?" + urllib.parse.urlencode(params), log=log)
    if data is None:
        return [], err
    out = [parse_crossref(i) for i in ((data.get("message") or {}).get("items") or [])]
    return [x for x in out if x], None


def enrich_via_crossref(records, max_items, email, log) -> int:
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
        if email:
            url += "?" + urllib.parse.urlencode({"mailto": email})
        data, _ = http_get_json(url, retries=1, log=log)
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
        key = norm_doi(rec.get("doi")) or (f"pmid:{rec['pmid']}" if rec.get("pmid") else "") \
            or title_key(rec["title"])
        if not key:
            continue
        if key not in buckets:
            buckets[key] = rec
            order.append(key)
            continue
        base = buckets[key]
        base["sources"] = sorted(set(base.get("sources") or []) | set(rec.get("sources") or []))
        for field in ("title", "abstract", "venue", "doi", "tldr", "oa_url",
                      "volume", "issue", "page", "pmid", "pmc"):
            if not base.get(field) and rec.get(field):
                base[field] = rec[field]
        if base.get("year") is None and rec.get("year"):
            base["year"] = rec["year"]
        if not base.get("authors") and rec.get("authors"):
            base["authors"] = rec["authors"]
        if not base.get("mesh") and rec.get("mesh"):
            base["mesh"] = rec["mesh"]
        if not base.get("keywords") and rec.get("keywords"):
            base["keywords"] = rec["keywords"]
            if rec.get("kw_note") and not base.get("kw_note"):
                base["kw_note"] = rec["kw_note"]
        if base.get("citation_count") is None and rec.get("citation_count") is not None:
            base["citation_count"] = rec["citation_count"]
        base["pub_types"] = sorted(set(base.get("pub_types") or []) | set(rec.get("pub_types") or []))
        base["evidence"] = base.get("evidence") or evidence_of(base["pub_types"])
        base["trial_ids"] = sorted(set(base.get("trial_ids") or []) | set(rec.get("trial_ids") or []))
        if rec.get("is_preprint"):
            base["is_preprint"] = True
            base["preprint_server"] = base.get("preprint_server") or rec.get("preprint_server") or ""
        if rec.get("source") == "crossref":
            for field in ("volume", "issue", "page"):
                if rec.get(field):
                    base[field] = rec[field]
    return [buckets[k] for k in order]


def looks_like_review(rec: Dict[str, Any]) -> bool:
    pts = " ".join(rec.get("pub_types") or [])
    if re.search(r"(?i)(review|guideline|consensus)", pts):
        return True
    return bool(REVIEW_HINT.search(rec.get("title") or ""))


def apply_type_filter(records, mode, pub_type):
    if pub_type in ("all", "mixed", ""):
        return records
    if pub_type == "review" or mode == "broad":
        kept = [r for r in records if looks_like_review(r)]
    elif pub_type == "article":
        kept = [r for r in records if not looks_like_review(r)]
    else:
        kept = records
    return kept or records


def apply_evidence_pref(records, evidence_pref: str) -> List[Dict[str, Any]]:
    """医学专属：证据等级优先（RCT优先 / Meta优先 / 队列优先）。"""
    if not evidence_pref or evidence_pref in ("不限", "any"):
        return records
    order = {"RCT优先": ["RCT"], "Meta优先": ["Meta-analysis", "Systematic Review"],
             "队列优先": ["Cohort", "Observational"]}.get(evidence_pref, [])
    if not order:
        return records
    preferred = [r for r in records if (r.get("evidence") or "") in order]
    rest = [r for r in records if r not in preferred]
    return preferred + rest


def apply_concept_filter(records, pattern, min_match):
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
        hay = " ".join([rec.get("title") or "", rec.get("abstract") or "",
                        " ".join(rec.get("keywords") or []), " ".join(rec.get("mesh") or [])])
        hits = {m.group(0).lower() for m in rx.finditer(hay)}
        rec["concept_hits"] = len(hits)
        if len(hits) >= max(min_match, 0):
            kept.append(rec)
    return kept, max(len(records) - len(kept), 0)


def sort_records(records, sort_by):
    if sort_by == "time":
        return sorted(records, key=lambda r: (r.get("year") or 0), reverse=True)
    if sort_by == "citations":
        return sorted(records, key=lambda r: (r.get("citation_count") or -1), reverse=True)
    if sort_by == "time+citations":
        return sorted(records, key=lambda r: ((r.get("year") or 0),
                                             (r.get("citation_count") or -1)), reverse=True)
    return records


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


def pool_scope(seen, topic_id, tokens, cross_topic, global_dedup):
    topics = seen.get("topics") or {}
    if global_dedup:
        chosen = list(topics.keys())
    else:
        chosen = [topic_id] if topic_id in topics else []
        if cross_topic:
            for tid, node in topics.items():
                if tid == topic_id or not isinstance(node, dict):
                    continue
                blob = " ".join([str(node.get("name") or ""), str(node.get("query") or ""),
                                 " ".join(str(q) for q in (node.get("queries") or []))])
                if query_tokens(blob) & tokens:
                    chosen.append(tid)
    dois: Set[str] = set()
    pmids: Set[str] = set()
    for tid in chosen:
        node = topics.get(tid) or {}
        for d in (node.get("seen_dois") or []):
            nd = norm_doi(d)
            if nd:
                dois.add(nd)
        for p in (node.get("seen_pmids") or []):
            if str(p).strip():
                pmids.add(str(p).strip())
    return dois, pmids, chosen


def mark_seen(seen, topic_id, topic_name, query, mode, records, data_source):
    topics = seen.setdefault("topics", {})
    node = topics.get(topic_id) or {"name": topic_name,
                                    "created_at": datetime.now().strftime("%Y-%m-%d")}
    node["name"] = topic_name
    node["mode"] = mode
    node["query"] = query
    node["last_query"] = query
    node["last_used"] = datetime.now().strftime("%Y-%m-%d")
    node["data_source"] = data_source
    dois = {norm_doi(d) for d in (node.get("seen_dois") or [])}
    pmids = {str(p) for p in (node.get("seen_pmids") or [])}
    for rec in records:
        nd = norm_doi(rec.get("doi"))
        if nd:
            dois.add(nd)
        if rec.get("pmid"):
            pmids.add(str(rec["pmid"]))
    node["seen_dois"] = sorted(dois)
    node["seen_pmids"] = sorted(pmids)
    topics[topic_id] = node


def save_seen(seen) -> None:
    seen["version"] = seen.get("version") or "0.4.0"
    seen["updated_at"] = datetime.now().isoformat(timespec="seconds")
    (DATA_DIR / "seen_papers.json").write_text(
        json.dumps(seen, ensure_ascii=False, indent=2), encoding="utf-8")


def _alpha_only(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", (text or "").lower())


def _acronym(text: str) -> str:
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
        for key in (name, node.get("abbr") or ""):
            norm = _alpha_only(key)
            if norm:
                index.setdefault(norm, entry)
            acr = _acronym(key)
            if acr and len(acr) >= 3:
                index.setdefault(acr, entry)
    return index


def journal_meta(venue, index):
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


def journal_mark(rec, index) -> str:
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
        if meta.get("code"):
            parts.append(f"{meta['code']} 预警")
        if meta.get("if_2024"):
            parts.append(f"IF {meta['if_2024']}")
    if rec.get("is_preprint"):
        parts.append(f"[Preprint {rec.get('preprint_server') or ''}]".strip())
    return " / ".join(parts)


# ---------------------------------------------------------------------------
# 引用格式
# ---------------------------------------------------------------------------
def _first_author_token(rec) -> str:
    authors = rec.get("authors") or []
    token = "anon"
    if authors:
        token = re.sub(r"[^A-Za-z]", "", authors[0].split()[-1]) or "anon"
    return f"{token.lower()}{rec.get('year') or 'nd'}"


def to_bibtex(rec) -> str:
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


def to_apa7(rec) -> str:
    authors = rec.get("authors") or []
    if not authors:
        auth = NA
    elif len(authors) == 1:
        auth = _apa_author(authors[0])
    elif len(authors) <= 20:
        auth = ", ".join(_apa_author(a) for a in authors[:-1]) + f", & {_apa_author(authors[-1])}"
    else:
        auth = ", ".join(_apa_author(a) for a in authors[:19]) + ", ... " + _apa_author(authors[-1])
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
    return f"{auth} ({rec.get('year') or NA}). {rec.get('title') or NA}. {tail}"


def to_gbt7714(rec) -> str:
    authors = rec.get("authors") or []
    if not authors:
        auth = NA
    elif len(authors) > 3:
        auth = ", ".join(authors[:3]) + ", et al"
    else:
        auth = ", ".join(authors)
    venue = rec.get("venue") or NA
    loc = f"{venue}, {rec.get('year') or NA}"
    if rec.get("volume"):
        loc += f", {rec['volume']}"
        if rec.get("issue"):
            loc += f"({rec['issue']})"
    if rec.get("page"):
        loc += f": {rec['page']}"
    s = f"{auth}. {rec.get('title') or NA}[J]. {loc}."
    if rec.get("doi"):
        s += f" DOI: {rec['doi']}."
    return s


def to_ris(rec) -> str:
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
    if rec.get("pmid"):
        lines.append(f"AN  - {rec['pmid']}")
    lines.append("ER  - ")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Markdown 渲染（对齐 SKILL.md §6.2）
# ---------------------------------------------------------------------------
def _vol_issue_page(rec) -> str:
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


def render_markdown(query, topic_name, mode, records, index, sources_used,
                    years_label, skipped, cross_pool, concept_dropped, concept_kept,
                    notes) -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    type_label = "article-only（含 Letter / Case Report）" if mode == "fine" \
        else "review-only（系统综述 / Meta / 指南）"
    out: List[str] = []
    out.append(f"# 文献检索结果（{'精细模式' if mode == 'fine' else '粗放模式 · 综述为主'}"
               f" · 医学/生信/AI）")
    out.append("")
    out.append(f"**查询**：{query}")
    out.append(f"**研究方向**：{topic_name}")
    out.append(f"**时间范围**：{years_label}")
    out.append(f"**文献类型**：{type_label}")
    out.append(f"**数据源**：{', '.join(sources_used) if sources_used else NA}")
    out.append(f"**检索时间**：{now}")
    out.append(f"**模式**：{mode}")
    out.append("")
    for note in notes:
        out.append(f"> {note}")
    if notes:
        out.append("")

    out.append(f"## 📋 速览（{len(records)} 篇）")
    out.append("")
    if mode == "broad":
        out.append("| # | 标题 | 作者 | 年份 | DOI | 综述类型 |")
        out.append("|---|------|------|------|-----|---------|")
    else:
        out.append("| # | 标题 | 作者 | 年份 | DOI |")
        out.append("|---|------|------|------|-----|")
    top = zone1 = warning = preprint = mesh_n = trial_n = 0
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
        if rec.get("mesh"):
            mesh_n += 1
        if rec.get("trial_ids"):
            trial_n += 1
        authors = rec.get("authors") or []
        author_cell = (", ".join(authors[:3]) + (", et al." if len(authors) > 3 else "")) \
            if authors else NA
        doi = rec.get("doi")
        doi_cell = f"[{doi}](https://doi.org/{doi})" if doi else NA
        row = f"| {i} | [{rec.get('title') or NA}](#title-{i}) | {author_cell} | " \
              f"{rec.get('year') or NA} | {doi_cell} |"
        if mode == "broad":
            row += f" {rec.get('evidence') or 'Review'} |"
        out.append(row)
    out.append("")
    stats = [f"⭐ Top {top} 篇", f"1 区 {zone1} 篇", f"🔴 预警 {warning} 篇",
             f"[Preprint] {preprint} 篇", f"已跳过重复 {skipped} 篇",
             f"含 MeSH {mesh_n} 篇", f"含临床试验注册号 {trial_n} 篇"]
    if concept_dropped:
        stats.append(f"方向过滤剔除 {concept_dropped} 篇（保留 {concept_kept} 篇）")
    out.append("> " + " · ".join(stats))
    if cross_pool and skipped:
        out.append(f"> 跨主题去重来源 pool：{', '.join(cross_pool)}")
    out.append("")
    out.append("---")
    out.append("")
    out.append("## 📚 详细条目")
    out.append("")

    for i, rec in enumerate(records, 1):
        out.append(f"### # {i} <a id=\"title-{i}\"></a> {rec.get('title') or NA}")
        authors = rec.get("authors") or []
        out.append(f"- **作者**：{', '.join(authors) if authors else NA}（仅来自 API）")
        out.append(f"- **年份**：{rec.get('year') or NA}")
        mark = journal_mark(rec, index)
        out.append(f"- **期刊**：{rec.get('venue') or NA}" + (f"（{mark}）" if mark else ""))
        meta = journal_meta(rec.get("venue"), index)
        out.append(f"- **影响因子**：{meta.get('if_2024') if meta and meta.get('if_2024') else NA}")
        doi = rec.get("doi")
        out.append(f"- **DOI**：{f'[{doi}](https://doi.org/{doi})' if doi else NA}")
        if rec.get("pmid"):
            out.append(f"- **PMID**：[{rec['pmid']}](https://pubmed.ncbi.nlm.nih.gov/{rec['pmid']}/)")
        out.append(f"- **卷/期/页**：{_vol_issue_page(rec)}")
        if mode == "broad":
            out.append(f"- **综述类型**：{rec.get('evidence') or NA}")
        out.append(f"- **证据等级 / Publication Type**："
                   f"{(rec.get('evidence') or NA)}"
                   + (f"（{'; '.join(rec.get('pub_types') or [])}）" if rec.get("pub_types") else ""))
        out.append(f"- **MeSH 主题词**：{', '.join(rec.get('mesh') or []) if rec.get('mesh') else NA}")
        out.append(f"- **临床试验注册号**："
                   f"{', '.join(rec.get('trial_ids') or []) if rec.get('trial_ids') else NA}")
        kws = rec.get("keywords") or []
        kw_label = f"关键词（{rec['kw_note']}）" if rec.get("kw_note") else "关键词"
        out.append(f"- **{kw_label}**：{', '.join(kws) if kws else NA}")
        ab = (rec.get("abstract") or "").strip()
        out.append(f"- **摘要原文**：{ab if ab else 'N/A（出版商屏蔽，到 DOI 原页拉）'}")
        out.append(f"- **TLDR**（AI 总结）：{rec.get('tldr') or NA}")
        marks = []
        if rec.get("is_preprint"):
            marks.append(f"[Preprint {rec.get('preprint_server') or ''}]".strip())
        if rec.get("oa_url"):
            marks.append(f"[OA 全文]({rec['oa_url']})")
        marks.append(f"来源: {', '.join(rec.get('sources') or [])}")
        if rec.get("concept_hits"):
            marks.append(f"方向命中 {rec['concept_hits']}")
        out.append(f"- **标记**：{' · '.join(marks)}")
        out.append("")
        out.append("#### 📎 引用格式")
        for label, body in (("BibTeX", to_bibtex(rec)), ("APA 7", to_apa7(rec)),
                            ("GB/T 7714", to_gbt7714(rec)), ("RIS", to_ris(rec))):
            fence = "bibtex" if label == "BibTeX" else "text"
            out.append("<details>")
            out.append(f"<summary>{label}</summary>")
            out.append("")
            out.append(f"```{fence}")
            out.append(body)
            out.append("```")
            out.append("")
            out.append("</details>")
            out.append("")
        out.append("---")
        out.append("")
    out.append("> ⚠️ 本结果仅供学术调研，**不替代临床判断**；预印本未经同行评审，"
               "临床决策请以原始文献 + 现行指南为准。")
    return "\n".join(out)


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="paper_search_client.py",
        description="mbai_paper_search 检索客户端（OpenAlex / PubMed / Europe PMC / SS / Crossref 多源合并）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "示例:\n"
            "  python paper_search_client.py -q \"PD-1 inhibitor NSCLC\" --pretty\n"
            "  python paper_search_client.py -q \"spatial transcriptomics\" --mode broad --count 15\n"
            "  python paper_search_client.py -q \"medical LLM\" --evidence RCT优先 --sources pubmed,openalex\n"
            "  python paper_search_client.py -q \"AlphaFold\" --include-preprint --verify\n"
        ),
    )
    p.add_argument("-q", "--query", required=True, help="检索关键词")
    p.add_argument("--mode", choices=["auto", "fine", "broad"], default="auto")
    p.add_argument("--topic", help="研究方向名（默认由 query 生成 slug）")
    p.add_argument("--count", type=int, default=0, help="返回篇数（默认精细 10 / 粗放 15）")
    p.add_argument("--years", default="", help="时间范围年数（空=精细 3 年、粗放不限）")
    p.add_argument("--type", dest="pub_type", choices=["auto", "article", "review", "all"],
                   default="auto")
    p.add_argument("--sort", choices=["relevance", "time", "citations", "time+citations"],
                   default="auto")
    p.add_argument("--evidence", default="不限",
                   choices=["不限", "RCT优先", "Meta优先", "队列优先"],
                   help="临床证据等级偏好（医学专属）")
    p.add_argument("--include-preprint", action="store_true",
                   help="纳入并保留 bioRxiv / medRxiv / arXiv 预印本（默认也保留，仅显式标注）")
    p.add_argument("--concept-pattern", help="方案 H 宽召回二次过滤正则")
    p.add_argument("--min-concept-match", type=int, default=1)
    p.add_argument("--sources", default="openalex,pubmed,europepmc,ss,crossref",
                   help="参与检索的源（逗号分隔）")
    p.add_argument("--enrich-max", type=int, default=8)
    p.add_argument("--no-dedup", action="store_true")
    p.add_argument("--global-dedup", action="store_true")
    p.add_argument("--no-cross-topic", action="store_true")
    p.add_argument("--out", help="输出目录或 .md 文件路径")
    p.add_argument("--json-out", help="额外输出原始 JSON")
    p.add_argument("--verify", action="store_true", help="导出后做 DOI + PMID 反查校验")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--pretty", action="store_true")
    p.add_argument("--quiet", action="store_true")
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

    # PII 脱敏（医学专属，继承 v0.2 脚本行为）
    if re.search(r"\b\d{13,18}\b", query):
        print("⚠️ 查询串检测到 13-18 位连续数字（疑似患者 ID / 身份证号）。", file=sys.stderr)
        print("   强烈建议脱敏后再检索（隐私风险）；本次已拒绝执行。", file=sys.stderr)
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
              f"years={years_label} type={pub_type} evidence={args.evidence}")

    keys = load_keys(verbose=args.pretty)
    email = keys.get("email")

    logs: List[Dict[str, Any]] = []
    notes: List[str] = []
    records: List[Dict[str, Any]] = []
    sources_used: List[str] = []
    warn = "⚠️"
    srcs = {s.strip() for s in args.sources.split(",") if s.strip()}

    fetchers = [
        ("ss", "Semantic Scholar", lambda: search_semanticscholar(
            query, max(count * 2, 20), years_lo, years_hi,
            keys.get("semantic_scholar"), logs)),
        ("openalex", "OpenAlex", lambda: search_openalex(
            query, max(count * 2, 20), mode, years_lo, pub_type,
            keys.get("openalex"), email, logs)),
        ("pubmed", "PubMed", lambda: search_pubmed(
            query, max(count * 2, 20), years_lo, keys.get("ncbi"), email, logs, mode)),
        ("europepmc", "Europe PMC", lambda: search_europepmc(
            query, max(count * 2, 20), years_lo, pub_type, email, logs)),
        ("crossref", "Crossref", lambda: search_crossref(
            query, max(count, 10), years_lo, email, logs)),
    ]

    for key, label, fn in fetchers:
        if key not in srcs:
            continue
        try:
            got, err = fn()
        except Exception as exc:  # noqa: BLE001
            got, err = [], f"{type(exc).__name__}: {exc}"
        if got:
            records.extend(got)
            sources_used.append(f"{label}({len(got)})")
        else:
            notes.append(f"{warn} {label} 不可用或 0 命中（{err}），已跳过该源。")
            print(f"{warn} {label}：{err}；已切下游源。", file=sys.stderr)

    if not records:
        print("❌ 全部数据源失败：", file=sys.stderr)
        for note in notes:
            print("   " + note, file=sys.stderr)
        print("   请检查网络或稍后重试；也可只给关键词让我改用 web_search 兜底（覆盖率会下降）。",
              file=sys.stderr)
        return 2

    merged = merge_records(records)
    merged = apply_type_filter(merged, mode, pub_type)
    if args.enrich_max > 0:
        enrich_via_crossref(merged, args.enrich_max, email, logs)
    merged, concept_dropped = apply_concept_filter(
        merged, args.concept_pattern, args.min_concept_match)
    concept_kept = len(merged)
    merged = apply_evidence_pref(merged, args.evidence)

    seen = load_seen()
    tokens = query_tokens(query)
    skipped = 0
    cross_pool: List[str] = []
    if not args.no_dedup:
        seen_dois, seen_pmids, cross_pool = pool_scope(
            seen, topic_id, tokens, not args.no_cross_topic, args.global_dedup)
        before = len(merged)

        def _is_dup(r: Dict[str, Any]) -> bool:
            nd = norm_doi(r.get("doi"))
            if nd and nd in seen_dois:
                return True
            return bool(r.get("pmid")) and str(r["pmid"]) in seen_pmids

        kept = [r for r in merged if not _is_dup(r)]
        skipped = before - len(kept)
        if len(kept) >= max(count // 2, 3) or not kept:
            merged = kept
        elif skipped:
            notes.append(f"{warn} 去重后仅剩 {len(kept)} 篇（跳过 {skipped} 篇），"
                         f"已放宽为不去重以保证交付数量。")
            skipped = 0

    merged = sort_records(merged, sort_by)[:count]

    index = load_journal_index()
    markdown = render_markdown(
        query=query, topic_name=topic_name, mode=mode, records=merged, index=index,
        sources_used=sources_used, years_label=years_label, skipped=skipped,
        cross_pool=cross_pool, concept_dropped=concept_dropped, concept_kept=concept_kept,
        notes=notes)

    out_dir = Path(args.out) if args.out else default_out_dir()
    if out_dir.suffix.lower() == ".md":
        md_path = out_dir
        out_dir = md_path.parent
    else:
        md_path = out_dir / f"paper_search_{mode}_{slugify(topic_name)}_{datetime.now():%Y%m%d}.md"

    if args.json_out:
        jp = Path(args.json_out)
        jp.parent.mkdir(parents=True, exist_ok=True)
        jp.write_text(json.dumps({"query": query, "mode": mode, "topic": topic_name,
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
    import importlib.util

    vp = SCRIPT_DIR / "validate_output.py"
    if not vp.is_file():
        print("⚠️ 未找到 validate_output.py，跳过 --verify", file=sys.stderr)
        return 0
    spec = importlib.util.spec_from_file_location("mbai_validate_output", vp)
    if spec is None or spec.loader is None:
        return 0
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    summary = mod.validate_markdown_file(md_path, verbose=True)
    rate = summary.get("verification_rate")
    total = summary.get("total_ids", summary.get("total_dois", 0))
    if rate is not None and rate < 0.95:
        print(f"❌ 校验率 {rate * 100:.1f}% < 95%：{summary['verified']}/{total}")
        return 2
    print(f"✅ 校验通过：{summary['verified']}/{total}")
    return 0


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:  # noqa: BLE001
        pass
    sys.exit(main())
