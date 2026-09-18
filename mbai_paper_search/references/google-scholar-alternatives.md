# 为什么不用 Google Scholar（及替代路径）

> 本文件由 `SKILL.md`「3.4 」于 2026-09-18 结构瘦身时原样迁出；主文档保留编号占位，跨引用 `§` 仍然有效。

### 3.4 为什么不用 Google Scholar（及替代路径）

1. **合规**：GS 的 ToS 明确禁止自动化抓取，且无官方 API；
2. **稳定**：反爬导致的封禁常**静默失败**（流程看似成功、结果为空）；
3. **可复现**：结果与个人会话 / cookie / 地域相关，同一 query 不同人跑出不同结果。

| GS 独有能力 | 本 skill 的替代方式 |
|---|---|
| 中文医学期刊覆盖 | 万方 / CNKI / 中华医学期刊网人工跳转（**不入结构化字段**）；PubMed 亦收录部分中文刊 |
| 作者 h-index / 影响力 | SS `author.hIndex`；OpenAlex `authorships` + `summary_stats` |
| 引用图谱 | SS `/references` + `/citations`；OpenAlex `referenced_works` / `cited_by_api_url` |
| "被引 N 次" | SS `citationCount`；OpenAlex `cited_by_count`；Europe PMC `citedByCount` |
| 全文 PDF 直达 | OpenAlex `open_access.oa_url`；Europe PMC `isOpenAccess=Y` → PMC 全文；Unpaywall 按 DOI 反查 OA 版本 |
| 临床证据等级 | **PubMed `PublicationType`**（GS 没有这个维度，本 skill 更强） |
| 相关文章推荐 | SS `paper/{paperId}/recommendations`；Europe PMC `cited-by` / `references` |
