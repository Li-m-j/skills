# 更新日志 (UPDATE_NOTES)

> 记录 qm_paper_search skill 的所有数据更新历史。**只增不删**。

---

## 2025-initial — 2025-12-31

- **version**：2025-initial
- **date**：2025-12-31
- **operator**：qm_paper_search v0.1 初始填充
- **scope**：
  - 内置精简版 `cas_journal_zones.json`
  - 覆盖 SKILL.md §4.1 顶刊白名单所有期刊（37 本）
  - 预警期刊预填 4 本（待补充）
- **变更期刊清单**：
  - 新增：JACS, Angew. Chem. Int. Ed., Chem, Chem. Rev., Acc. Chem. Res., Nature Chem., Nature Catal., Nature Synth., Nature Rev. Chem., Chem. Soc. Rev., Coord. Chem. Rev., ACS Catal., Adv. Mater., Adv. Funct. Mater., Adv. Energy Mater., Adv. Sci., Energy Environ. Sci., Environ. Sci. Technol., Water Res., Inorg. Chem., Dalton Trans., Org. Lett., Green Chem., Adv. Synth. Catal., Chem. Mater., J. Phys. Chem. Lett., Nano Lett., ACS Nano, Anal. Chem., TrAC, Chem. Eng. J., AIChE J., Ind. Eng. Chem. Res., Mater. Today, Joule, ChemSusChem, ACS Sustain. Chem. Eng.
  - 预警：J. Hazard. Mater., J. Mol. Struct., Desalin. Water Treat., Int. J. Electrochem. Sci.
- **notes**：
  - 本次为 v0.1 内置精简版
  - 完整中科院分区数据待 2026 年《期刊分区表》发布后年度更新
  - IF 数据为 v0.1 估算，年度更新时一并校正

---

## 2026-v0.2-split — 2026-09-08

- **version**：v0.2 架构重组
- **date**：2026-09-08
- **operator**：Mavis + user
- **scope**：
  - skill 拆分：qm_paper_search v0.1 → DEPRECATED
  - 新建 qm_paper_search_fine v0.2（精细，article-only）
  - 新建 qm_paper_search_broad v0.2（粗放，review-only）
  - 抽出 shared data 目录到 `qm_paper_search_shared/data/`
  - 主源改为 Semantic Scholar API（不再爬 Google Scholar）
  - 接入 X-Mol 作为中文兜底
  - 强制反幻觉规则：所有元数据 only from API，缺失 N/A
  - 输出增加 `关键词` + `摘要原文` + `TLDR` 字段
  - topic_id 加 `fine_` / `broad_` 前缀隔离
- **变更文件清单**：
  - 新增：`qm_paper_search_fine/SKILL.md`, `qm_paper_search_fine/README.md`
  - 新增：`qm_paper_search_broad/SKILL.md`, `qm_paper_search_broad/README.md`
  - 新增：`qm_paper_search_shared/data/` (复制的 v0.1 数据)
  - 修改：`qm_paper_search/SKILL.md` (顶部加 DEPRECATED)
  - 修改：`qm_paper_search/README.md` (顶部加 DEPRECATED)
- **notes**：
  - v0.1 data 同步复制到 shared/，两份独立维护不再同步
  - v0.1 目录保留作历史归档，不更新
  - shared/data 后续由 v0.2 统一更新
  - 待 v0.2 实测后再决定是否进一步调整

---

## 2026-v0.2-api-live — 2026-09-08

- **version**：v0.2 API 实测
- **date**：2026-09-08 21:35–21:45
- **operator**：Mavis + user
- **scope**：
  - 用户提供 OpenAlex API key（polite pool）
  - key 存于 `shared/data/api_keys.json`（v0.2.3 后改为 `api_keys.local.json`）
  - 调通 OpenAlex API（带 key 50 req/s）
  - 跑通 2 次精细模式实测
  - 添加 §11 法律约束与合规
  - 添加 §12 API 限制约束
- **变更文件清单**：
  - 修改：`qm_paper_search_fine/SKILL.md`
  - 修改：`qm_paper_search_broad/SKILL.md`
  - 新增：`shared/data/api_keys.json`（v0.2.3 改名为 `api_keys.local.json`）
  - 新增：用户 `papers/` 目录下两份 .md 演示
- **notes**：v0.2.1 待办

---

## 2026-v0.2.3-apikey-management — 2026-09-08

- **version**：v0.2.3 API key 个体管理
- **date**：2026-09-08 23:00
- **operator**：Mavis + user
- **scope**：
  - 引入 API key 团队协作管理（共享代码 + 个人本地 key）
  - 新增 `api_keys.template.json`（commit，团队共享）
  - 新增 `api_keys.local.json`（gitignore，个人本地）
  - 新增 `.gitignore`（保护 `*.local.json`）
  - 新增 `Set-ApiKey.ps1`（key 管理脚本：List / Set / Remove / Validate / EnvVar）
  - 新增 `qm_paper_search_setup.ps1`（首次初始化脚本）
  - 新增 `README_API_KEYS.md`（详细文档）
  - 删除旧明文 `api_keys.json`（防止 key 泄露）
  - 迁移现有 OpenAlex key 到 `api_keys.local.json`
  - SKILL.md 加 §13 API key 管理
  - SKILL.md 加 §13.6 输出规范（出版商屏蔽不再 AI 总结兜底，标 N/A 交付用户）
- **变更文件清单**：
  - 新增：`shared/data/api_keys.template.json`（占位符）
  - 新增：`shared/data/api_keys.local.json`（用户实际 key）
  - 新增：`shared/data/.gitignore`
  - 新增：`shared/data/README_API_KEYS.md`
  - 新增：`shared/data/scripts/Set-ApiKey.ps1`
  - 新增：`shared/data/scripts/qm_paper_search_setup.ps1`
  - 修改：`shared/data/UPDATE_NOTES.md`（本条）
  - 修改：`qm_paper_search_fine/SKILL.md`（加 §13）
  - 修改：`qm_paper_search_broad/SKILL.md`（加 §13, §14）
  - 删除：`shared/data/api_keys.json`（明文 key，已用 mavis-trash 移到回收站）
- **notes**：
  - 现有用户需重新跑 `qm_paper_search_setup.ps1` 一次（自动创建 local 文件）
  - 团队成员各自配置，不互相影响
  - key 失效时（401/403）跑 `Set-ApiKey.ps1 -Validate` 检查
  - 输出规范更新：出版商屏蔽 abstract 不再用 AI 总结兜底，标 N/A + 🔒 交付用户
