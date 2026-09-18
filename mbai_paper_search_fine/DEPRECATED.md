# ⚠️ DEPRECATED · 此目录已重定向

> **2026-09-18**：本目录内的 `SKILL.md` 已改名为 `SKILL.md.disabled`，skill 加载器不再扫描本目录（此前旧版触发词会与新版 skill 冲突、覆盖默认参数）。


> **状态**：`mbai_paper_search_fine` v0.2 已于 2026-09-12 合并入单 skill。
> **新位置**：`mbai_paper_search/`（当前 **v0.4.0**）
> **合并原因**：v0.1/v0.2 期间 fine + broad 双 skill 文档重叠 ~60%（反幻觉 / 法规 / key 管理 / API 限流等章节逐份复制），
> 且 `mbai_search_and_export.ps1` 本来就是 `-Mode fine|broad` 单脚本双模式——代码层早已支持合并，文档层却复制成两份各自演化。
> 合并后用户只需"文献检索 X"，mode 由 skill 内部自动推断。

---

## 重定向规则

| 旧调用 | 新调用 | 备注 |
|---|---|---|
| `mbai_paper_search_fine PD-1 NSCLC` | `文献检索 PD-1 NSCLC` | 未命中 broad 关键词 → 默认精细 |
| `mbai_paper_search_fine X` | `精细检索 X` | 显式指定（向后兼容） |
| `mbai_paper_search_broad 概览 XXX` | `文献检索 概览 XXX` | 命中"概览" → broad |
| `mbai_paper_search_broad X` | `粗放检索 X` | 显式指定（向后兼容） |

**mode 推断规则详见** `mbai_paper_search/SKILL.md §5.1`；**两 skill 的差异对照**见该文件 §2。

---

## 此目录剩余内容

| 文件 | 状态 | 用途 |
|---|---|---|
| `SKILL.md` | **历史归档** | v0.2 完整内容，**不再被 skill 系统加载** |
| `README.md` | **历史归档** | v0.2 时期的 README（已被重定向说明替换） |
| `DEPRECATED.md` | **本文件** | 重定向说明 |

---

## 数据连续性

- **去重池** `mbai_paper_search_shared/data/seen_papers.json` 中以 `fine_*` 为前缀的 topic 在 v0.4.0 中**继续识别**——不会因为合并丢数据。
- **`seen_pmids`** 字段完整保留（v0.2 脚本写入的 PMID 去重记录在 v0.4.0 中继续生效）。
- **`api_keys.local.json` / `user_prefs.json` / `cas_journal_zones.json`** 仍在 `shared/data/`，未受影响。
- **脚本** `mbai_search_and_export.ps1`（`-Mode fine`）与 `mbai_openalex_to_md.ps1` 继续可用。
- **v0.4.0 变更提醒**：精细默认篇数仍为 10（未变）；**粗放默认由 25 收敛为 15**（见 `mbai_paper_search/SKILL.md §2`）。

---

## 何时删除本目录

**不建议主动删除**（保留作历史回溯）。如需清理：确认 v0.4.0 稳定运行 ≥ 3 个月 → 确认无 skill 扫描器按目录名加载 → 备份 → 删除。清理决策权归维护者。
