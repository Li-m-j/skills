# ⚠️ 历史归档 · 不要让 skill 脚本读取本目录

> **状态**：qm_paper_search v0.1 已于 2026-09-08 弃用。
> **新位置**：所有 v0.2+ skill 共享数据位于 `qm_paper_search_shared/data/`
> **写入时间**：2026-09-12（Phase 1 清理）

---

## 本目录文件用途（仅供历史查阅）

| 文件 | 状态 | 说明 |
|---|---|---|
| `cas_journal_zones.json` | **已迁出** | v0.2 起统一从 `shared/data/cas_journal_zones.json` 读取，**本副本已废弃** |
| `seen_papers.json` | **仅作历史** | v0.1 时代的去重池（topic: "COF 催化"）。v0.2+ 不读本文件，**但保留作为用户历史记录** |
| `user_prefs.json` | **已迁出** | 内容与 `shared/data/user_prefs.json` 完全一致（SHA256 验证通过），可视为已迁 |
| `UPDATE_NOTES.md` | **历史日志** | v0.1 数据填充历史，仅作"考古"参考，**不更新** |

## 脚本读取路径

```
# ❌ 不要读这里
$dataDir = "$env:USERPROFILE\.minimax\skills\qm_paper_search\data"

# ✅ 读这里
$dataDir = "$env:USERPROFILE\.minimax\skills\qm_paper_search_shared\data"
```

所有 v0.2+ 的脚本（`qm_openalex_to_md.ps1` / `Set-ApiKey.ps1` / `qm_paper_search_setup.ps1`）
**只读 `shared/data/`**，不会读本目录。

## 何时删除

**不要主动删除**——这是用户 v0.1 时代的真实使用记录（topic: COF 催化，10 个 DOI）。
如未来要彻底清理 v0.1 痕迹：
1. 确认 `shared/data/seen_papers.json` 里有 v0.1 COF 催化的去重数据（备份）
2. 确认无 v0.1-era 引用需求
3. 备份整个 v0.1 目录到外部存储
4. 才能删除

**清理决策权归用户**。skill 不主动删除用户数据。
