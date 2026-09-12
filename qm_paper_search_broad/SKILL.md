---
name: qm_paper_search_broad
version: 0.2.2
description: |
  化学领域学术文献粗放检索 v0.2。
  触发词：粗放文献检索 / 粗放搜索 / qm_paper_search_broad / 领域概览 / 立项摸底。
  用途：新领域摸底、立项调研、综述集合。
  主源：Semantic Scholar API。
  兜底：Crossref → OpenAlex → X-Mol。不爬 Google Scholar。
  文献类型默认 review-only（综述为主）。
  默认 25 篇，时间范围不限，强制反幻觉。
  数据根目录：%USERPROFILE%\.minimax\skills\qm_paper_search_shared\data\
---

<!--
  Modification Log (added 2026-09-12)
  Format: modified <date>: <phase> — <change summary>
  Keep entries reverse-chronological (newest on top).
-->
<!-- modified 2026-09-12: Phase 0 — added modification log template -->
<!-- modified 2026-09-12: Phase 1 P0 — bumped version to 0.2.2; added v0.2.2 方案 H wide-recall
     parameters (concept_pattern, min_concept_match) to §2 parameter table; added §3.1 explaining
     the two-step wide-recall + concept-filter mechanism, default pattern, typical PowerShell
     usage, API cost (~100-150 req/search), and rationale for keeping it in PS script rather
     than LLM prompt -->
<!-- modified 2026-09-12: Phase 1 P2 — §6.1 "详细条目" block replaced with explicit reference
     to fine §6.1; corrected "7 个核心字段" (wrong) → "9 个核心字段" (matches fine §6.1 actual
     fields: 作者/年份/期刊/影响因子/DOI/关键词/摘要原文/TLDR/标记); noted 4 citation formats
     (BibTeX/APA 7/GB/T 7714/RIS) reuse fine's folded structure. -->

# qm_paper_search_broad — 化学领域粗放文献检索 v0.2.2

## 1. 适用与不适用

**适用**
- 新研究方向立项摸底
- 找综述、进展、领域概览
- 找高被引、高影响力论文
- 跨子领域的全景式扫描
- 引用图谱（references + cited by，一层）

**不适用**
- 已知方向的深度调研 → 用 `qm_paper_search_fine`
- 非化学领域
- 全文下载、翻译、润色

## 2. 检索参数（v0.2）

| 参数 | 默认 | 可选值 | 说明 |
|---|---|---|---|
| `type` | review-only | review / all / mixed | 文献类型过滤 |
| `count` | 25 | 1-100 | 返回篇数 |
| `years` | 不限 | 1-10 / 不限 | 时间范围（年） |
| `journal_filter` | loose | strict / loose | 顶刊过滤严格度 |
| `sort_by` | time+citations | relevance / time / citations / time+citations | 排序方式 |
| `citation_graph` | on | on / off | 引用图谱开关 |
| `abstract_source` | ss | ss / crossref / openalex / xmol | 摘要主源 |
| `keywords_required` | true | true / false | 是否必须返回关键词 |
| `tldr` | optional | required / optional / off | TLDR 开关 |
| `concept_pattern` | *(空)* | regex | 宽召回概念过滤（v0.2.2 方案 H，详见 §3.1） |
| `min_concept_match` | 1 | 0-10 | 宽召回最少命中概念数（v0.2.2 方案 H，详见 §3.1） |

## 3. 数据源（v0.2 主链）

```
Semantic Scholar API（主）
  ↓ 缺
Crossref → OpenAlex → X-Mol
  ↓ 缺
返回 N/A
```

**不爬 Google Scholar**。

### 3.1 宽召回机制（v0.2.2 方案 H · 配套脚本 `qm_openalex_to_md.ps1`）

> **为什么需要宽召回**：broad 模式默认 `type=review-only` + `years=不限` 时，OpenAlex / SS 直出结果常返回 200+ 条候选，但其中大量与查询方向无关的"边缘综述"（如：方法学综述、应用综述、跨学科综述）。直接按相关度排序容易漏掉方向核心综述。
>
> **方案 H 核心思路**：先宽召回（不筛方向），再用 `concept_pattern`（regex）做二次方向过滤。

**两步流程**：

1. **宽召回**（第一次 API 调用）：
   - 不带方向过滤，全量拉取 `count × 3-5` 条候选
   - 接受 SS/OpenAlex 的相关度排序作为初排
2. **方向过滤**（脚本层，**不增加 API 调用**）：
   - 对每条候选的 `title + abstract + concepts` 用 `concept_pattern`（regex）做匹配
   - 命中数 ≥ `min_concept_match` 才保留
   - 不足时**不补调 API**，仅在最终报告里声明"过滤后 N 篇，命中原 query 核心 M 篇（M < N）"

**典型用法**（生物催化方向）：

```powershell
# PowerShell
.\qm_openalex_to_md.ps1 `
    -InputJsonFile "raw_search.json" `
    -OutputMdFile "biocatalysis_broad_20260912.md" `
    -Mode broad `
    -TopicName "biocatalysis" `
    -BroadConceptPattern "biocatalysis|enzymatic[ ]catalysis|enzyme[ ]catalysis" `
    -BroadMinMatch 1
```

**默认行为**：

| 参数 | 默认 | 说明 |
|---|---|---|
| `BroadConceptPattern` | `"biocatalysis\|enzymatic[ ]catalysis\|enzyme[ ]catalysis"` | 历史默认值（生物催化示例）。**新方向必须改** |
| `BroadMinMatch` | 1 | 至少命中 1 个概念 token |
| `BroadNoFilter` | false | 开关：true 时跳过方向过滤，退化为纯宽召回 |

**与 §2 参数的关系**：

- `count=25` = **最终输出数**（过滤后）
- 实际 API 拉取数 = `count × 3-5`（约 75-125 条候选）
- 单次检索 API 请求量 ≈ 75-125 req + 25 req 元数据 ≈ **100-150 req**

**为什么不内置到 LLM 决策**：

- 概念过滤涉及 regex 性能 + 候选遍历，LLM prompt 里描述不如脚本一行实现
- `concept_pattern` 决定"什么算这个方向"，跨 topic 不一致 → 需用户/脚本显式指定
- v0.2.2 选 PS 脚本而非 Python，因为 PS 与 `qm_paper_search_setup.ps1` / `Set-ApiKey.ps1` 一致

## 4. 强制反幻觉规则

同 qm_paper_search_fine：所有元数据 only from API，缺失字段 `N/A`，严禁 LLM 编造。

## 5. 触发与去重

### 触发方式
- "粗放文献检索 X" / "概览 X" / "立项调研 X"
- "qm_paper_search_broad X"
- "找 X 的综述"

### 去重
- 数据源：`shared/data/seen_papers.json`
- topic_id 前缀：`broad_`（与 fine 隔离）
- 同 topic 重复检索自动跳过

## 6. 输出格式

输出文件：`paper_search_broad_<query>_<YYYYMMDD>.md`  
保存路径：`shared/data/user_prefs.json` 的 `default_save_dir`。

### 6.1 文件结构

```markdown
# 文献检索结果（粗放模式 · 综述为主）

**查询**：<query>
**研究方向**：<topic_name>
**时间范围**：不限（默认）
**文献类型**：review-only
**数据源**：<sources>
**检索时间**：<timestamp>

## 📋 速览（25 篇）

| # | 标题 | 作者 | 年份 | DOI |
|---|------|------|------|-----|
| 1 | [Title](#title-1) | ... | 2024 | [10.xxxx](https://doi.org/10.xxxx) |
| 2 | ... | ... | ... | ... |

> ⭐ Top X 篇 · 1 区 X 篇 · 🔴 预警 X 篇 · [Preprint] X 篇 · 已跳过重复 X 篇

---

## 📚 详细条目

> **格式与 `qm_paper_search_fine/SKILL.md §6.1` 完全一致**，仅以下两处差异：
> - 默认条数 10 → 25
> - `time+citations` 排序（fine 默认 `relevance`）
>
> 详细字段说明：见 `qm_paper_search_fine/SKILL.md §6.1`（9 个核心字段 = 作者 / 年份 / 期刊 / 影响因子 / DOI / 关键词 / 摘要原文 / TLDR / 标记）。
> 4 种引用格式（BibTeX / APA 7 / GB/T 7714 / RIS）也复用 fine 的折叠结构。
```

## 7. 失败处理

同 fine。

## 8. 数据维护

- 分区数据：shared/data/cas_journal_zones.json（年度更新）
- 去重池：shared/data/seen_papers.json（topic_id 加 `broad_` 前缀）
- 用户偏好：shared/data/user_prefs.json

## 9. 与 fine 的区别

| 维度 | fine | broad（本 skill） |
|---|---|---|
| 默认篇数 | 10 | 25 |
| 文献类型 | article | review |
| 顶刊过滤 | 严格 | 宽松 |
| 时间范围 | 近 3 年 | 不限 |
| 排序 | 相关度 | 时间 + 被引 |
| 引用图谱 | 一层 | 一层 |
| 适用 | 深度调研 | 领域概览 |

---

## 11. 法律约束与合规

本 skill 继承 `qm_paper_search_fine/SKILL.md` §11 的全部约束，包括：

- 数据来源合规（CC0 / API 协议 / 预印本协议）
- 引用规范（4 种格式必出，保留作者署名）
- 内容使用边界（禁存付费墙 PDF、禁镜像、禁商业转售）
- 隐私保护（不存用户搜索历史到云端）
- 学术道德（不替代人工阅读、严禁学术不端）
- 适用法律（按用户司法辖区）

**broad 模式特别约束**：
- 默认 25 篇，可能拉取大量数据 → 注意 API 限流
- review 论文引用他人图表要标注原始出处
- 不下载、不批量缓存 review 全文

## 12. API 限制约束

本 skill 继承 `qm_paper_search_fine/SKILL.md` §12 的全部约束。

**broad 模式特别约束**：
- 25 篇 × 完整元数据 ≈ 30-50 req/search，**必须 sleep 防限流**
- 引用图谱默认开，1 篇拉 5-10 req，**最多 250 req/search**
- 建议每次 broad 检索后 sleep 30s 再做下一轮
- SS API 共享 IP 100 req/min 限流，无 key 也跑（带 key 提升）

## 13. API key 管理（继承 fine §13）

**关键差异**：broad 模式更频繁使用 SS API，可能需要 Semantic Scholar key。

- OpenAlex key 申请：https://openalex.org/users/sign_up
- Semantic Scholar key 申请：https://www.semanticscholar.org/product/api
- 详细管理流程见 `data/README_API_KEYS.md`

## 14. 输出规范（继承 fine §13.6）
- 出版商屏蔽 abstract → 标 `N/A（出版商屏蔽，到 DOI 原页拉）`
- 标记 `🔒 待人工处理`，不编造内容
