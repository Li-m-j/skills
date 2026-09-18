# 为什么不用 Google Scholar（及替代路径）

> 本文件由 `SKILL.md`「3.4 为什么不用 Google Scholar」结构瘦身时迁出（se 版按经济学/统计领域改写）；主文档保留编号占位，跨引用 `§` 仍然有效。

### 3.4 为什么不用 Google Scholar（及替代路径）

**三条原因（明确写出，避免"反向偏执"观感）**：

1. **合规**：GS 的 ToS 明确禁止自动化抓取，且没有官方 API；
2. **稳定**：反爬导致的封禁常常**静默失败**——流程"看起来成功"，但结果为空；
3. **可复现**：GS 结果与个人会话 / cookie / 地域相关，同一 query 不同人跑出不同结果，与本 skill 的"可复现检索"定位冲突。

**GS 独有能力的替代路径**（避免用户在统计/经济场景被卡住）：

| GS 独有能力 | 本 skill 的替代方式 |
|---|---|
| 经济学工作论文 / 预印本 | **arXiv（econ.*/stat.*，本 skill 主渠道）**；NBER working papers（nber.org/papers，无公开 API，按编号人工跳转）；SSRN（elsevier.com 旗下，同上）；RePEc/IDEAS（ideas.repec.org，经济学专属索引，handle 形如 `RePEc:nbr:nberwo:31256`，不入结构化字段） |
| 中文期刊覆盖（经济研究/管理世界等） | CNKI / 万方按标题人工跳转（**不入结构化字段**）；OpenAlex/Crossref 对部分中文刊有收录但覆盖不稳定 |
| 作者影响力 / h-index | SS `author.hIndex`、`author.paperCount`；OpenAlex `authorships` + `summary_stats`；经济学者常用 RePEc 作者页（IDEAS） |
| 引用图谱 | SS `/references` + `/citations`（一层）；OpenAlex `referenced_works` / `cited_by_api_url` |
| "被引 N 次" | SS `citationCount`；OpenAlex `cited_by_count`（注意：经济学期刊慢引文化下近三年被引数系统性偏低，解读需谨慎） |
| 全文 PDF 直达 | arXiv `link[pdf]`（多数 econ.EM 论文有 OA）；OpenAlex `open_access.oa_url`；预印本与正式版并存时**以正式版为引用口径**（仅取链接，不镜像、不绕过付费墙） |
| 相关文章推荐 | SS `paper/{paperId}/recommendations` 或 `/references` 的首层结果 |

> 结论：GS **不可替代的是它自己的索引**，但上表各类需求都有合规替代。若用户坚持要 GS 结果（如 GS-only 的引用计数），明确告知"需手动在浏览器检索，本 skill 不代抓"。
>
> **经济学特别提醒**：GS 是经济学者查"工作论文被引"的常见来源，但其计数与 SS/OpenAlex 差异更大（GS 把 NBER/SSRN 版本合并计数）。跨源引用数对不上属正常现象，报告中以单一源口径呈现、不混搭。
