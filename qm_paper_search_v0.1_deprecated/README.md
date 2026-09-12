# qm_paper_search — README [DEPRECATED]

> ⚠️ **本 skill 已弃用**。v0.1 仅作历史归档。
> 请使用 `qm_paper_search_fine` 或 `qm_paper_search_broad`。

---

## 弃用说明

- **弃用版本**：v0.1
- **弃用日期**：2026-09-08
- **原因**：v0.2 拆分成精细 + 粗放两个 skill，主源改为 Semantic Scholar API，加入强制反幻觉规则
- **替代**：
  - `qm_paper_search_fine` — 精细搜索
  - `qm_paper_search_broad` — 粗放搜索

## 历史摘要

v0.1 是 qm_paper_search skill 的初始版本，包含：
- 主题检索 + 引用图谱两种模式
- 顶刊白名单 + 中科院分区过滤
- 4 种引用格式（BibTeX / APA / GB/T 7714 / RIS）折叠输出
- topic 分组去重机制

v0.2 主要变化：
- 拆分为 fine + broad 两个 skill
- 主源改为 Semantic Scholar API（不再爬 Google Scholar）
- 接入 X-Mol 作为中文兜底
- 增加 `type` 参数（article / review / letter / mixed）
- 强制反幻觉规则：所有元数据 only from API
- 输出增加 `**关键词**` + `**摘要原文**` + `**TLDR**` 字段

详细见 `qm_paper_search_fine/SKILL.md` 和 `qm_paper_search_broad/SKILL.md`。
