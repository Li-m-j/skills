---
name: qm_paper_search
version: 0.1
status: DEPRECATED
deprecated_at: 2026-09-08
replaced_by:
  - qm_paper_search_fine
  - qm_paper_search_broad
description: |
  ⚠️ 此 skill 已弃用（v0.1, 2026-09-08）。
  请改用 qm_paper_search_fine（精细）或 qm_paper_search_broad（粗放）。
  本文件仅作历史归档，不再更新维护。
---

# qm_paper_search v0.1 [DEPRECATED]

> ⚠️ **本 skill 已弃用**。请使用 `qm_paper_search_fine` 或 `qm_paper_search_broad`。
>
> **替代关系**：
> - 精细搜索（已知方向深度调研）→ `qm_paper_search_fine`
> - 粗放搜索（领域概览、立项摸底）→ `qm_paper_search_broad`
>
> v0.1 仅保留目录结构和 data 文件作历史参考。后续不会再更新。
>
> **脚本读数据请走 `qm_paper_search_shared/data/`，不要读本目录的 data/。**
> 详见 `data/ARCHIVE_NOTICE.md`（2026-09-12 添加）。

---

## 历史内容（v0.1 原始定义，仅作归档）

### 适用与不适用
- 适用：文献检索 / 找论文 / 引用图谱
- 不适用：非化学、全文下载、翻译润色

### 选源（v0.1 已弃用）
- Google Scholar → Semantic Scholar → Crossref → arXiv → PubMed → ChemRxiv
- v0.2 已改为 Semantic Scholar 为主

### 数据文件（v0.1 自有）
- `data/cas_journal_zones.json` — v0.1 内置版
- v0.2 统一从 shared 目录读取
