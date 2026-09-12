# ⚠️ DEPRECATED · 此目录已重定向

> **状态**：qm_paper_search_broad v0.2.2 已于 2026-09-12 合并入单 skill。
> **新位置**：`qm_paper_search/`（当前 **v0.4.0**；合并发生在 v0.3.0）
> **合并原因**：v0.2.x 期间 fine + broad 双 skill 60% 文档重复（反幻觉 / 法规 / API key 等章节）、三线维护成本高。v0.3.0 合并后用户只需用"文献检索 X"统一触发词，mode 由 skill 内部自动推断。

---

## 重定向规则

| 旧调用 | 新调用 | 备注 |
|---|---|---|
| `qm_paper_search_broad 概览 XXX` | `qm_paper_search XXX` | mode 自动推断为 broad（命中"概览"） |
| `qm_paper_search_broad 立项摸底 XXX` | `qm_paper_search XXX` | mode 自动推断为 broad（命中"立项摸底"） |
| `qm_paper_search_broad review of MOF` | `qm_paper_search review of MOF` | mode 自动推断为 broad（命中"review"） |
| `qm_paper_search_fine XXX` | `qm_paper_search XXX` | 精细默认（未命中 broad 关键词） |
| 显式指定 mode | `qm_paper_search 粗放检索 XXX` | 新增"粗放检索 X"显式覆盖（向后兼容 v0.2.x 习惯） |

**mode 推断详见** `qm_paper_search/SKILL.md §5.1`。

---

## 此目录剩余内容

| 文件 | 状态 | 用途 |
|---|---|---|
| `SKILL.md` | **历史归档** | v0.2.2 完整内容，**不再被 skill 系统加载**（frontmatter `name: qm_paper_search_broad` 不再注册到 skill 表） |
| `README.md` | **历史归档** | v0.2.2 时期的 README |
| `DEPRECATED.md` | **本文件** | 重定向说明 |

> 注意：skill 系统如果仍能识别 `qm_paper_search_broad` 这个名字（取决于 skill 扫描机制），会优先加载 v0.3.0 的 `qm_paper_search` 而不是这里的 v0.2.2。
> 如发现实际仍加载本目录 SKILL.md，请联系 skill 维护者更新扫描逻辑。

---

## 数据连续性

- **去重池** `qm_paper_search_shared/data/seen_papers.json` 中以 `broad_*` 为前缀的 topic 在 v0.3.0+ 中**继续识别**——不会因为合并而丢数据。
- **`api_keys.local.json` / `user_prefs.json` / `cas_journal_zones.json`** 仍在 `shared/data/`，未受影响。
- **脚本** `qm_openalex_to_md.ps1` 仍在 `shared/data/scripts/`，`-Mode broad` 参数继续生效。
- **v0.4.0 变更提醒**：粗放模式默认 `count` 由 25 收敛为 **15**（见 `qm_paper_search/SKILL.md §2`）。若你依赖旧的 25 篇默认值，请在 query 里显式写"找 25 篇"。

---

## 何时删除本目录

**不建议主动删除**——保留作为历史归档便于回溯。如需清理：

1. 确认 v0.4.0 在生产中稳定运行 ≥ 3 个月
2. 确认无 skill 系统按目录名加载本目录
3. 备份整个 `qm_paper_search_broad/` 到外部存储
4. 删除

**清理决策权归 skill 维护者**。本 DEPRECATED.md 不会自动删除。
