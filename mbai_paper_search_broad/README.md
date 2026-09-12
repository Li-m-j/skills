# mbai_paper_search_broad — README（历史归档）

> ⚠️ **本 skill 已于 2026-09-12 合并入单 skill `mbai_paper_search` v0.4.0。**
>
> - **请改用**：`文献检索 概览 X`（mode 自动推断）／ `粗放检索 X`（显式）
> - **新位置**：[`../mbai_paper_search/`](../mbai_paper_search/)（[SKILL.md](../mbai_paper_search/SKILL.md) · [README.md](../mbai_paper_search/README.md)）
> - **重定向说明**：[`DEPRECATED.md`](./DEPRECATED.md)
>
> 本目录的 `SKILL.md` 仅作 v0.2 历史归档，不再被 skill 系统加载。

---

## 原 v0.2 内容摘要（供回溯）

- 触发：`粗放文献检索 X` / `概览 X` / `立项调研 X` / `mbai_paper_search_broad X`
- 默认：review-only、**25 篇 → v0.4.0 收敛为 15 篇**、时间不限、时间+被引排序
- 数据源：OpenAlex（type=review）+ PubMed（PT: Systematic Review / Meta-Analysis / Practice Guideline）→ Europe PMC → SS → Crossref
- 综述类型细分：Review / Systematic Review / Meta-Analysis / Scoping Review / Clinical Practice Guideline / Consensus / Annual Review / Nature Reviews
- Cochrane Library：不直连（付费 + 限流严），通过 PubMed PT + Europe PMC 开放版兜底
- 去重池：`seen_papers.json` 的 `broad_*` topic（v0.4.0 继续识别）

完整 v0.2 定义见本目录 [`SKILL.md`](./SKILL.md)。
