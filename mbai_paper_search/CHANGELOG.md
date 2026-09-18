# mbai_paper_search — 修订记录（CHANGELOG）

> 原为 SKILL.md 顶部 HTML `<!-- modified ... -->` 注释块，2026-09-18 结构瘦身时迁移至此。
> 倒序排列（最新在上）。代码级修复不升版本号。

## 2026-09-18 · 结构瘦身（不改运行行为）

- 本文件创建：SKILL.md 顶部 HTML Modification Log 注释块整体迁入。
- frontmatter `description` 压缩为触发/默认值/红线要点。
- §3.4 / §9 / §10 / §11 全文迁至 `references/`；因属医学安全约束，§9.4（PII 硬拦截）与 §9.7（医学红线）**原文保留在 SKILL.md 内**。
- §2 `include_preprint` 行修正为与 `paper_search_client.py` 实际行为一致（预印本恒纳入并标 [Preprint]，`--include-preprint` 仅显式声明，无排除开关）。
- §12 文件清单同步；SKILL.md 731 → 553 行。

<!-- modified 2026-09-18: 回归测试修复（代码级，不动版本号）：
     - validate_output.py：stdout/stderr 强制 UTF-8（Windows GBK 控制台打印 ✅ 崩溃）。
     - paper_search_client.py：OpenAlex concepts 导出改标「关键词（概念标签，来自 OpenAlex
       concepts）」落实 §4.1；文章号期刊 first==last 不再输出重复页码。
     - shared/data/scripts/*.ps1：补 UTF-8 BOM（PowerShell 5.1 必需）；
       mbai_openalex_to_md.ps1 的 `"```"` 反引号转义导致字符串不终止，改单引号。
     - 实测确认：五源降级、DOI+PMID 双校验、PII 硬拦截（退出码 3）、跨 topic 去重池均工作正常。 -->
<!-- modified 2026-09-12: v0.4.0 — 与 qm_paper_search v0.4.x 对齐的「合并 + 可复用性」升级：
     - MERGED mbai_paper_search_fine v0.2 + mbai_paper_search_broad v0.2 → 单 skill
       `mbai_paper_search` v0.4.0；统一触发词"文献检索 X" + mode 自动推断。
       目录：mbai_paper_search_fine/ → mbai_paper_search/；mbai_paper_search_broad/ 标 DEPRECATED。
     - 新增 §0 Quickstart（补 onboarding 缺口）。
     - 新增 §3.2 调用契约（OpenAlex / PubMed E-utilities / Europe PMC / SS / Crossref 的
       endpoint + 参数 + 字段映射逐条写死），并说明"脚本优先、Agent 直连兜底"。
     - 新增 §3.4「为什么不用 Google Scholar + 6 条替代路径」（医学场景版）。
     - 新增 §4.2 代码化校验：validate_output.py（DOI + PMID 双反查；PMID 反查为医学专属扩展）。
     - 新增 §4.3 TLDR 质量警告。
     - §5.2 去重策略重写：跨 topic 共享关键词时默认合并去重；seen_papers 同时维护 seen_dois + seen_pmids。
     - 新增 §7.1 面向用户的错误提示模板。
     - 粗放默认 count 25 → 15。
     - 新增 §6.1 统一输出约定（与 qm / paper-deep-reading 同一套）。
     - 医学红线保留并强化：PII 脱敏、预印本明示、不输出诊疗建议、人类遗传资源条例。
     - 新增 scripts/paper_search_client.py（五源检索客户端）与 scripts/validate_output.py。 -->
<!-- modified 2026-09-09: v0.2.0（fine/broad 共享）— 主源探活 / 检索三段式 / 本地化日期与类型过滤 /
     SS tldr / efetch 完整作者 / 引用数 / stdout 告警 + api_logs / seen_papers 自动落盘 /
     PII 脱敏 / -Count 参数 / UPDATE_NOTES 增量；新增 mbai_search_and_export.ps1（33 KB 一站式入口）。
     ⚠️ 注意：`mbai_search_and_export.ps1` 的**检索结果为作者列表可用性依赖 PubMed/OpenAlex 直连**，
     不属于反幻觉校验层；交付前校验请用 scripts/validate_output.py。 -->
<!-- modified 2026-09-08: v0.1.0 — 从 qm_paper_search_fine / broad 切换主题到医学/生信/AI；
     扩展数据源（PubMed / Europe PMC / 预印本）；扩展字段（MeSH / 临床试验注册号 / 证据等级）；
     扩展合规约束（医学临床道德 / HIPAA / 人类遗传资源条例）。 -->
