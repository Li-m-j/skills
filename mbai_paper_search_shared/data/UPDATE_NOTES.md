# mbai_paper_search_shared — 变更记录

> 共享数据/分区表/去重池/keys 的版本与变更说明。

---

## v0.4.0 · 2026-09-12 · 单 skill 化 + 检索/校验客户端

- **服务对象变化**：`mbai_paper_search_fine` + `mbai_paper_search_broad` 合并为单 skill
  `mbai_paper_search` v0.4.0；两个旧目录保留数据、标记 DEPRECATED（重定向说明见各自目录）。
- **新增 `scripts/paper_search_client.py`**（五源检索客户端）：
  - 检索：SS → OpenAlex → PubMed E-utilities（esearch + efetch XML）→ Europe PMC → Crossref，源失败自动降级并打印告警
  - 医学字段：MeSH 主题词 / Publication Type → 证据等级 / NCT·ChiCTR·ISRCTN·UMIN 注册号 / PMID
  - 合并去重：DOI → PMID → 标准化标题三级回退；Crossref 覆盖卷/期/页
  - 方案 H：`--concept-pattern` + `--min-concept-match`（纯本地过滤，不额外发请求）
  - 去重池：读写 `seen_papers.json`，同时维护 `seen_dois` + `seen_pmids`；默认跨 topic 合并去重
  - 导出：SKILL §6.2 格式 Markdown（含 MeSH / 证据等级 / 注册号 + 4 种引用格式）
  - 安全：**PII 硬拦截**（查询含 13-18 位连续数字时拒绝执行）
  - 退出码：0 成功 / 2 全源失败 / 3 参数错误或 PII 拦截 / 4 校验未达标
- **新增 `scripts/validate_output.py`**：DOI（Crossref）+ PMID（PubMed esummary）双反查校验；
  校验率 < 0.95（可配 `--threshold`）时退出码 2，即"不应交付"。
- **默认篇数调整**：粗放模式 `count` 25 → 15（精细仍为 10）。
- **去重池结构不变**：v0.2 已写入的 `fine_*` / `broad_*` topic 与 `seen_pmids` 全部继续生效。
- `cas_journal_zones.json` / `user_prefs.json` / `api_keys*.json` **未改动**。

---

## v0.1.0 · 2026-09-08 · 初版

- 沿用 qm_paper_search_shared 的目录结构（`data/` + `data/scripts/`）
- 新增 **医学 / 生物信息学 / 人工智能** 顶刊白名单与分区数据：
  - 临床医学：NEJM / Lancet / JAMA / BMJ / Nature Medicine / Lancet Oncology / JCO / Cancer Cell 等
  - 基础医学：Nature Reviews 系列 / Cell / Nature / Science
  - 生物信息学：Nature Methods / Bioinformatics / NAR / Cell Systems / PLOS Computational Biology
  - 人工智能：Nature Machine Intelligence / JMLR / TPAMI / Lancet Digital Health / npj Digital Medicine
  - 交叉：Medical Image Analysis / Journal of Biomedical Informatics / Briefings in Bioinformatics
- 模板字段扩展：`ncbi_api_key`（PubMed E-utilities）、`europe_pmc_contact_email`（Europe PMC）
- 引用了 2024 年中科院《国际期刊预警名单》JMIR 低风险记录（仅 1 条）

## 后续

- 2026-Q4：扩充生物信息学期刊细分（单细胞、空间转录组、AlphaFold 衍生期刊）
- 2027-Q1：根据新一轮中科院分区表年度更新替换 `cas_journal_zones.json`
- 计划：增加临床试验主题（CT.gov / WHO ICTRP 索引字段）作为元数据扩展
- v0.2 (2026-09-09) · query="polygenic risk score cancer" mode=fine topic=prs_cancer_v2
  - 数据源: PubMed E-utilities (no key, 3 req/s)
  - 主源探活: OpenAlex 异常 → 切 PubMed (#1 兜底)
  - 命中: 10 篇
  - SS tldr: 10/10
  - 去重池: fine_prs_cancer_v2 (累计 11 PMID)
- v0.2 (2026-09-09) · query="single-cell RNA sequencing" mode=broad topic=scrna_review
  - 数据源: PubMed E-utilities (no key, 3 req/s)
  - 主源探活: OpenAlex 异常 → 切 PubMed (#1 兜底)
  - 命中: 25 篇
  - SS tldr: 25/25
  - 去重池: broad_scrna_review (累计 25 PMID)
- v0.2 (2026-09-09) · query="artificial intelligence oncology" mode=broad topic=oncology_ai_review
  - 数据源: PubMed E-utilities (no key, 3 req/s)
  - 主源探活: OpenAlex 异常 → 切 PubMed (#1 兜底)
  - 命中: 25 篇
  - SS tldr: 21/25
  - 去重池: broad_oncology_ai_review (累计 25 PMID)
- v0.2 (2026-09-09) · query="endometrial cancer NSMP no specific molecular profile" mode=fine topic=ec_nsmp_research
  - 数据源: PubMed E-utilities (no key, 3 req/s)
  - 主源探活: OpenAlex 异常 → 切 PubMed (#1 兜底)
  - 命中: 8 篇
  - SS tldr: 7/8
  - 去重池: fine_ec_nsmp_research (累计 8 PMID)
- v0.2 (2026-09-09) · query="endometrial cancer NSMP no specific molecular profile" mode=broad topic=ec_nsmp_review
  - 数据源: PubMed E-utilities (no key, 3 req/s)
  - 主源探活: OpenAlex 异常 → 切 PubMed (#1 兜底)
  - 命中: 2 篇
  - SS tldr: 2/2
  - 去重池: broad_ec_nsmp_review (累计 2 PMID)
- v0.2 (2026-09-09) · query="TCGA molecular subtypes integrated classification cancer" mode=fine topic=tcga_subtypes_research
  - 数据源: PubMed E-utilities (no key, 3 req/s)
  - 主源探活: OpenAlex 异常 → 切 PubMed (#1 兜底)
  - 命中: 8 篇
  - SS tldr: 8/8
  - 去重池: fine_tcga_subtypes_research (累计 8 PMID)
- v0.2 (2026-09-09) · query="TCGA molecular subtypes integrated classification cancer" mode=broad topic=tcga_subtypes_review
  - 数据源: PubMed E-utilities (no key, 3 req/s)
  - 主源探活: OpenAlex 异常 → 切 PubMed (#1 兜底)
  - 命中: 2 篇
  - SS tldr: 2/2
  - 去重池: broad_tcga_subtypes_review (累计 2 PMID)
- v0.2 (2026-09-09) · query="disease subtyping machine learning" mode=fine topic=disease_subtyping_ai
  - 数据源: PubMed E-utilities (no key, 3 req/s)
  - 主源探活: OpenAlex 异常 → 切 PubMed (#1 兜底)
  - 命中: 8 篇
  - SS tldr: 8/8
  - 去重池: fine_disease_subtyping_ai (累计 8 PMID)
- v0.2 (2026-09-09) · query="cancer subtyping artificial intelligence" mode=fine topic=cancer_subtyping_ai
  - 数据源: PubMed E-utilities (no key, 3 req/s)
  - 主源探活: OpenAlex 异常 → 切 PubMed (#1 兜底)
  - 命中: 8 篇
  - SS tldr: 7/8
  - 去重池: fine_cancer_subtyping_ai (累计 8 PMID)
- v0.2 (2026-09-09) · query="endometrial cancer molecular subtyping artificial intelligence" mode=fine topic=ec_subtyping_ai
  - 数据源: PubMed E-utilities (no key, 3 req/s)
  - 主源探活: OpenAlex 异常 → 切 PubMed (#1 兜底)
  - 命中: 8 篇
  - SS tldr: 8/8
  - 去重池: fine_ec_subtyping_ai (累计 8 PMID)
- v0.2 (2026-09-10) · query="("next-generation sequencing" OR NGS OR "next generation sequencing") AND (cancer OR tumor OR neoplasm OR oncology) AND ("artificial intelligence" OR "machine learning" OR "deep learning") AND (prognosis OR clinical OR outcome OR survival)" mode=broad topic=ngs_ai_cancer_prognosis
  - 数据源: PubMed E-utilities (no key, 3 req/s)
  - 主源探活: OpenAlex 异常 → 切 PubMed (#1 兜底)
  - 命中: 10 篇
  - SS tldr: 9/10
  - 去重池: broad_ngs_ai_cancer_prognosis (累计 10 PMID)
- v0.2 (2026-09-10) · query="("next-generation sequencing" OR NGS OR "next generation sequencing") AND (cancer OR tumor OR neoplasm OR oncology) AND ("artificial intelligence" OR "machine learning" OR "deep learning")" mode=fine topic=ngs_ai_cancer_fine
  - 数据源: PubMed E-utilities (no key, 3 req/s)
  - 主源探活: OpenAlex 异常 → 切 PubMed (#1 兜底)
  - 命中: 10 篇
  - SS tldr: 9/10
  - 去重池: fine_ngs_ai_cancer_fine (累计 10 PMID)
- v0.2 (2026-09-10) · query="("next-generation sequencing" OR NGS OR "next generation sequencing") AND (cancer OR tumor OR neoplasm OR oncology) AND ("artificial intelligence" OR "machine learning" OR "deep learning") AND ("New England Journal of Medicine"[Journal] OR "Lancet"[Journal] OR "JAMA"[Journal] OR "BMJ"[Journal] OR "Nature Medicine"[Journal] OR "Lancet Oncology"[Journal] OR "Journal of Clinical Oncology"[Journal] OR "Cancer Cell"[Journal] OR "Cell"[Journal] OR "Nature"[Journal] OR "Science"[Journal] OR "Nature Methods"[Journal] OR "Nature Machine Intelligence"[Journal] OR "Lancet Digital Health"[Journal] OR "npj Digital Medicine"[Journal] OR "Nature Communications"[Journal] OR "Nature Biotechnology"[Journal] OR "Nature Cancer"[Journal] OR "Cell Reports Medicine"[Journal] OR "Briefings in Bioinformatics"[Journal] OR "Nucleic Acids Research"[Journal] OR "Medical Image Analysis"[Journal])" mode=fine topic=ngs_ai_cancer_top_if
  - 数据源: PubMed E-utilities (no key, 3 req/s)
  - 主源探活: OpenAlex 异常 → 切 PubMed (#1 兜底)
  - 命中: 10 篇
  - SS tldr: 10/10
  - 去重池: fine_ngs_ai_cancer_top_if (累计 10 PMID)
