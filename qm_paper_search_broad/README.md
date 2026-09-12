# qm_paper_search_broad — README [DEPRECATED · 2026-09-12]

> ⚠️ **本目录已弃用**。v0.2.2 内容已合并入 `qm_paper_search/` v0.3.0。
> 详细重定向说明见 `DEPRECATED.md`。

---

## 历史摘要

qm_paper_search_broad v0.2.2 是化学文献粗放检索 skill 的最后一个独立版本，特性：
- 综述为主（review-only 默认）
- 25 篇默认，时间不限
- 方案 H 宽召回 + 二次过滤（v0.2.2 新增）
- 主源：Semantic Scholar API
- 兜底：Crossref → OpenAlex → X-Mol

## 重定向

请使用统一 skill：

```powershell
# 旧：qm_paper_search_broad 概览 钙钛矿太阳能电池
# 新：
qm_paper_search 概览 钙钛矿太阳能电池
```

详见 `qm_paper_search/SKILL.md §5.1` mode 推断规则。

## 历史 SKILL.md

`SKILL.md` 在此目录仍保留 v0.2.2 完整内容作为历史归档。**不再被 skill 系统加载**。
