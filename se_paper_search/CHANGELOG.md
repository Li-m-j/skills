# se_paper_search — 修订记录（CHANGELOG）

> 倒序排列（最新在上）。代码级修复不升版本号。
> 本 skill 由 `qm_paper_search` v0.4.1 派生；qm 侧 v0.2~v0.4.1 的演进史（fine/broad 合并、
> 调用契约、代码化校验、零依赖客户端等）**随派生一并继承**，不在此重复记录，见
> `qm_paper_search/CHANGELOG.md`。

## v0.1.0 · 2026-09-18 — 统计经济学首发

**派生改造（相对 qm 孪生 v0.4.1 的差异）**：

- **检索链**：SS 主链 → **arXiv（econ.EM/econ.GN/econ.TH/stat.ME/AP/ML/TH/CO/OT/math.ST）→ OpenAlex → SS → Crossref** 四源；
  arXiv 免 key、礼仪限速 1 req/3s 内置；多词精确短语 0 命中自动退回逐词 AND 再查一次。
- **校验器**：`validate_output.py` 升级为 **DOI→Crossref + arXiv ID→arXiv API 双反查**；
  阈值改按合并通过率（`combined_rate`），保留 `total_dois`/`verified` 等旧字段兼容。
- **期刊口径**：`cas_journal_zones.json`（中科院分区+IF）→ `se_journal_tiers.json`
  （经济 Top5 / 统计四大 / 金融 Top3 / 中文权威，约 45 本）；**`if_2024` 一律 null**，
  渲染为 `Tier N / ⭐ Top`，不报 IF 数值（编辑共识口径，避免编造/过时数字）；预警名单留空待社区补充。
- **模式口径**：broad 类型过滤 = 综述 **+ 工作论文**（经济学预印本是主要流通形态）；
  fine 中 arXiv 原创研究按 article 处理并保留 `[Preprint]` 标记。
- **反幻觉**：§4.1 放宽"DOI 强制"为 **DOI 与 arXiv ID 至少其一**，两者皆无标 ⚠️ 需人工复核；
  新增"不得凭印象补经典文献""工作论文不得写成正式发表"两条经济域禁令。
- **HTTP 层**：新增 SSL 证书链验证失败兜底（本机 Windows 对 export.arxiv.org 缺中间证书，
  实测 unverified context 可用；先正常验证、失败才降级）。
- **领域红线（§9）**：不构成投资建议；不替代官方统计发布；禁止挑选性引用（p-hacking 式）；
  arXiv 全文按单篇 license 使用。
- **工具改名**：`qm_openalex_to_md.ps1`→`se_openalex_to_md.ps1`（化学 ISSN→IF 表替换为
  经济/统计 ISSN→档位表）、`qm_paper_search_setup.ps1`→`se_paper_search_setup.ps1`、
  env `QM_PAPER_SHARED_DIR`→`SE_PAPER_SHARED_DIR`。
- **mode 推断**：broad 词 +`handbook`；fine 词 +`估计量|识别`（与 SKILL §5.1 同步）。

**已知限制（v0.2 候选）**：seen 池仍为 DOI-only（arXiv-only 预印本不入池）；SSRN/NBER
编号页无法机器反查；RePEc handle 未富化。
