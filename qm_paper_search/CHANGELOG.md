# qm_paper_search — 修订记录（CHANGELOG）

> 原为 SKILL.md 顶部 HTML `<!-- modified ... -->` 注释块，2026-09-18 结构瘦身时迁移至此。
> 倒序排列（最新在上）。代码级修复不升版本号。

## 2026-09-18 · 结构瘦身（不改运行行为）

- 本文件创建：SKILL.md 顶部 HTML Modification Log 注释块整体迁入。
- frontmatter `description` 压缩为触发/默认值/红线要点（原 11 行 → 7 行）。
- §3.4 / §9 / §10 / §11 全文迁至 `references/`（google-scholar-alternatives / legal-compliance / api-limits / api-key-management），主文档保留章节编号占位 + 红线速记，`§` 跨引用不受影响。
- §12 文件清单同步；SKILL.md 788 → 557 行。

<!-- modified 2026-09-18: Phase 4 — 打包后端到端回归测试发现并修复（代码级，不动版本号）：
     - validate_output.py：stdout/stderr 强制 UTF-8——Windows GBK 控制台打印 ✅ 直接
       UnicodeEncodeError 崩溃，交付前校验在中文环境下不可用。
     - paper_search_client.py：OpenAlex concepts 导出改标「关键词（概念标签，来自 OpenAlex
       concepts）」，落实 §4.1"禁止把 concepts 当关键词"；GB/T 7714 `[J]` 后补句点；
       文章号期刊 first==last 不再输出 "10247-10247"；0 命中不再误报"不可用：None"，
       并提示 OpenAlex/SS 全文检索仅支持英文（中文 query 需先转英文关键词）。
     - shared/data/scripts/*.ps1：全部补 UTF-8 BOM（Windows PowerShell 5.1 无 BOM 会把
       中文注释/字符串解析成乱码报错）；qm_openalex_to_md.ps1 的 `"```bibtex"` / `"```"`
       因反引号是 PS 转义符导致字符串永不终止、整脚本不可解析，改为单引号字符串。 -->
<!-- modified 2026-09-12: Phase 3.1 — 补上 锐评 处置建议 #1 的真正缺口：新增
     `shared/data/scripts/paper_search_client.py`（唯一零依赖 Python 检索客户端）：
     SS/OpenAlex/Crossref 三源检索 → DOI+标题去重合并 → 方案 H 概念过滤 → seen_papers 去重
     → §6.2 格式 Markdown 导出 → `--verify` 复用 validate_output.py 做 DOI 反查。
     同时在 §0 Quickstart / §3.2 调用契约 / §12 文件清单 中登记该脚本。
     顺带修复 validate_output.py 的两个真实缺陷：
       (1) line 205 f-string 引号错位（`'total_dois]`）导致整文件 SyntaxError；
       (2) DOI 正则未排除 BibTeX 花括号，抽取 `doi = {10.x/y}` 会得到 `10.x/y}`（404）。
     新增 §3.2 的"执行主体"二选一说明（脚本优先，Agent 直连为兜底）。 -->
<!-- modified 2026-09-12: Phase 3 — v0.4.0「文档 ↔ 实现对齐 + 可复用性」修复，闭合 skill锐评.md 的 qm 侧遗留项：
     - 新增 §0 Quickstart（补 锐评 #5「Onboarding 完全缺失」）。
     - 新增 §3.2 调用契约（endpoint / 参数 / 字段映射 逐条写死），并在 §3 加"口径澄清"，
       消除 锐评 #1「文档承诺与代码实现对不上」——明确本 skill 由 Agent 直接发起 HTTP，
       脚本只做 JSON→MD 转换与 DOI 校验，不再让读者误以为存在 SS 客户端。
     - 新增 §3.4「为什么不用 Google Scholar + 5 条替代路径」（补 锐评 #3 反向偏执无解释）。
     - 新增 §4.2 代码化校验（validate_output.py）、§4.3 TLDR 质量警告（补 锐评 #6）。
     - §5.2 去重策略重写：跨 topic 共享关键词时默认识别合并去重（修 锐评 #4 反用户设计）。
     - 新增 §7.1 面向用户的错误提示模板（补 锐评 #8 错误处理不面向用户）。
     - 粗放默认 count 25 → 15（补 锐评 #7 限流劝退）；同步 §2 / §10.6 / README。
     - §12 文件清单同步实际目录（补 _lib_paths.ps1 / validate_output.py / sample_broad.json）。
     - §13 版本表补 v0.4.0。 -->
<!-- modified 2026-09-12: Phase 2.1 — MERGED qm_paper_search_fine v0.2.3 + qm_paper_search_broad v0.2.2
     into single skill qm_paper_search v0.3.0.
     - Directory: qm_paper_search_fine/ → qm_paper_search/ (consolidated).
     - v0.1 archive moved: qm_paper_search/ → qm_paper_search_v0.1_deprecated/ (data preserved).
     - Trigger unified to "文献检索 X"; mode auto-inferred from query keywords.
     - Auto-inference regex: /概览|立项|综述|摸底|survey|landscape|全景/i → broad;
       /深度|方法|创新|对比|复现/ → fine; default fine.
     - Explicit overrides still work: "精细检索 X" / "粗放检索 X" (backward compat).
     - topic_id prefix in seen_papers.json UNCHANGED: "fine_*" and "broad_*" coexist
       and are both recognized for cross-session dedup continuity.
     - Section count: 15 → 13 (removed standalone "与 broad 的区别" / "继承 fine" sections;
       placeholder §10 was removed as no longer needed).
     - qm_paper_search_broad/ now contains only DEPRECATED.md + README.md redirect.
-->
<!-- modified 2026-09-12: Phase 1 P1 — bumped version 0.2 → 0.2.3 in frontmatter + description;
     rewrote §15 维护 as a single-layer version table. -->
<!-- modified 2026-09-12: Phase 1 P0 — inserted §10 placeholder (章节编号兼容性占位)
     to fix the §9 → §11 numbering gap. (placeholder removed in v0.3.0 merge) -->
