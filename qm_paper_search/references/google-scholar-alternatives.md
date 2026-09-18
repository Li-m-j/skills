# 为什么不用 Google Scholar（及替代路径）

> 本文件由 `SKILL.md`「3.4 为什么不用 Google Scholar」于 2026-09-18 结构瘦身时原样迁出；主文档保留编号占位，跨引用 `§` 仍然有效。

### 3.4 为什么不用 Google Scholar（及替代路径）— v0.4.0 新增

**三条原因（明确写出，避免"反向偏执"观感）**：

1. **合规**：GS 的 ToS 明确禁止自动化抓取，且没有官方 API；
2. **稳定**：反爬导致的封禁常常**静默失败**——流程"看起来成功"，但结果为空；
3. **可复现**：GS 结果与个人会话 / cookie / 地域相关，同一 query 不同人跑出不同结果，与本 skill 的"可复现检索"定位冲突。

**GS 独有能力的替代路径**（避免用户在化学场景被卡住）：

| GS 独有能力 | 本 skill 的替代方式 |
|---|---|
| 中文期刊覆盖 | X-Mol 关键词检索；CNKI / 万方按标题人工跳转（**不入结构化字段**） |
| 作者影响力 / h-index | SS `author.hIndex`、`author.paperCount`；OpenAlex `authorships` + `summary_stats` |
| 引用图谱 | SS `/references` + `/citations`（一层）；OpenAlex `referenced_works` / `cited_by_api_url` |
| "被引 N 次" | SS `citationCount`；OpenAlex `cited_by_count` |
| 全文 PDF 直达 | OpenAlex `open_access.oa_url`；Unpaywall 按 DOI 反查 OA 版本；预印本 ChemRxiv / arXiv（**仅取链接，不镜像、不绕过付费墙**） |
| 相关文章推荐 | SS `paper/{paperId}/recommendations` 或 `/references` 的首层结果 |

> 结论：GS **不可替代的是它自己的索引**，但上表六类需求都有合规替代。若用户坚持要 GS 结果，明确告知"需手动在浏览器检索，本 skill 不代抓"。
