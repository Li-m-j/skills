---
name: mbai_paper_search_broad
version: 0.2
description: |
  医学 / 生物信息学 / 人工智能 学术文献粗放检索 v0.1。
  触发词：粗放文献检索 / 粗放搜索 / mbai_paper_search_broad / 领域概览 / 立项摸底 / 综述集合。
  用途：新领域摸底、立项调研、综述集合（Nature Reviews、Cochrane、Annual Review 系列优先）。
  主源：OpenAlex API + PubMed E-utilities（综述/系统综述/Meta-analysis 过滤）。
  备链：Europe PMC → Semantic Scholar → Crossref。
  文献类型默认 review-only（综述为主；系统综述、Meta-analysis、Scoping Review、Annual Review、Nature Reviews、Clinical Practice Guideline）。
  默认 25 篇，时间范围不限，强制反幻觉。
  数据根目录：%USERPROFILE%\.minimax\skills\mbai_paper_search_shared\data\
---

# mbai_paper_search_broad — 医学/生信/AI 粗放文献检索 v0.2

> **v0.2 重大更新**（2026-09-09）：
> - 共享 `mbai_search_and_export.ps1` v0.2 一站式入口（fine + broad 复用）
> - broad 模式额外：Publication Type 过滤限定为 Review / Systematic Review / Meta-Analysis / Practice Guideline
> - SS tldr / 引用数 / 完整作者 / PII 脱敏 / 探活 / seen_papers 全部继承 fine
> - 默认篇数 25（fine 是 10），用 `-Count` 覆盖

> 本 skill 是 `qm_paper_search_broad`（化学）的同源孪生版，主题切换为 **Medicine · Bioinformatics · Artificial Intelligence**。  
> 整体框架继承自 qm 系列；医学领域扩展：综述类型细化（系统综述 / Meta / 临床指南 / Cochrane）、Cochrane Library / PubMed 综述优先。

## 1. 适用与不适用

**适用**
- 新研究方向立项摸底（如：胶质母细胞瘤免疫治疗、单细胞多组学、医学大模型）
- 找综述、进展、领域概览
- 找高被引、高影响力论文
- 跨子领域的全景式扫描（如：医学 AI 的整体进展）
- 引用图谱（references + cited by，一层）
- 临床实践指南（CPG）摸底

**不适用**
- 已知方向的深度调研 → 用 `mbai_paper_search_fine`
- 非医学 / 非生信 / 非 AI 领域
- 全文下载、翻译、润色

## 2. 检索参数（v0.1）

| 参数 | 默认 | 可选值 | 说明 |
|---|---|---|---|
| `type` | review-only | review / systematic-review / meta-analysis / guideline / all / mixed | 文献类型过滤（医学领域细化） |
| `count` | 25 | 1-100 | 返回篇数 |
| `years` | 不限 | 1-10 / 不限 | 时间范围（年） |
| `journal_filter` | loose | strict / loose | 顶刊过滤严格度（综述类放宽） |
| `sort_by` | time+citations | relevance / time / citations / time+citations | 排序方式 |
| `citation_graph` | on | on / off | 引用图谱开关 |
| `abstract_source` | openalex | openalex / pubmed / europe_pmc / semantic_scholar / crossref | 摘要主源 |
| `keywords_required` | true | true / false | 是否必须返回关键词（含 MeSH） |
| `tldr` | optional | required / optional / off | TLDR 开关 |
| `include_preprint` | optional | required / optional / off | 是否纳入预印本（综述类通常不含） |
| `prefer_journal` | auto | auto / Nature Reviews / Cochrane / Annual Review / Lancet / NEJM | 综述来源偏好 |
| `clinical_scope` | optional | pediatric / adult / geriatric / global / 不限 | 临床范围（医学专属） |

## 3. 数据源（v0.1 主链）

```
OpenAlex API（主，覆盖全领域）
  ↓ 缺 abstract / 缺综述过滤
PubMed E-utilities（Publication Type: Review / Systematic Review / Meta-Analysis / Guideline）
  ↓ 缺 / 非生物医学
Europe PMC（开放获取 + 综述 + 指南）
  ↓ 缺
Semantic Scholar API（AI/ML 综述覆盖好）
  ↓ 缺
Crossref（DOI 反查）
  ↓ 缺
返回 N/A
```

**Cochrane Library**（系统综述金标准）：本 skill 不直连 Cochrane API（付费 + 限流严），通过 PubMed 标注 `Publication Type: Systematic Review` + Europe PMC 开放获取版兜底。

**不爬 Google Scholar**。

### 3.1 综述类型识别（PubMed Publication Type 优先）

| 类型 | PubMed 标识 | 说明 |
|---|---|---|
| Review | `Review` | 综述（泛指） |
| Systematic Review | `Systematic Review` | 系统综述（Cochrane 风格） |
| Meta-Analysis | `Meta-Analysis` | Meta 分析（合并统计） |
| Scoping Review | `Review`（不细分，关键词过滤） | 范围综述 |
| Clinical Practice Guideline | `Practice Guideline` | 临床实践指南 |
| Consensus | `Consensus Development Conference` | 共识声明 |
| Editorial | `Editorial` | 社论（**不计入综述**，仅参考） |
| Annual Review | ISSN 匹配 Annual Reviews Inc. | 年评系列 |
| Nature Reviews | ISSN 匹配 Nature Reviews 系列 | 自然综述系列 |

## 4. 强制反幻觉规则

| 字段 | 来源 | 缺失处理 |
|---|---|---|
| 标题 | API 原始 | 强制必须有 |
| 作者 | API 原始 | 缺则 `N/A`，**严禁 LLM 补全** |
| 年份 | API 原始 | 强制必须有 |
| 期刊 | API 原始 | 缺则 `N/A` |
| 卷/期/页 | API 原始 | 缺则 `N/A` |
| DOI | API 原始 | 强制必须有 |
| 影响因子 | 本地 cas_journal_zones.json | 缺则 `N/A` |
| 摘要原文 | OpenAlex / PubMed / Europe PMC / SS | 缺则 `N/A` |
| 关键词 | API 原始（含 MeSH） | 缺则 `N/A` |
| MeSH | PubMed MeSH 字段 | 缺则 `N/A` |
| Publication Type | PubMed PT 字段 | 缺则 `N/A` |
| 综述层级（PRISMA） | 摘要中查找 | 缺则 `N/A` |
| TLDR | Semantic Scholar tldr 字段 | AI 总结必须明确标"AI 总结" |

**禁止**：
- LLM 编造任何字段
- snippet 截取当 abstract
- 推断页码 / 作者 / 卷期
- 把 Editorial / Commentary / Letter 标成"综述"
- 把系统综述说成"原创研究"

## 5. 触发与去重

### 5.1 触发方式
- "粗放文献检索 X" / "概览 X" / "立项调研 X"
- "mbai_paper_search_broad X"
- "找 X 的综述"
- "X 领域有哪些进展"

### 5.2 去重
- 数据源：`shared/data/seen_papers.json`
- topic_id 前缀：`broad_`（与 fine 隔离；与 qm 的 broad_ 前缀不冲突——两个 skill 各自 seen_papers.json）
- 同 topic 重复检索自动跳过
- 跨 topic 默认不去重
- 显式命令：新方向 / 清空当前方向记忆 / 清空全部记忆 / 全局去重

## 6. 输出格式

输出文件：`paper_search_broad_<query>_<YYYYMMDD>.md`  
保存路径：`shared/data/user_prefs.json` 的 `default_save_dir`。

### 6.1 文件结构

```markdown
# 文献检索结果（粗放模式 · 综述为主 · 医学/生信/AI）

**查询**：<query>
**研究方向**：<topic_name>
**时间范围**：不限（默认）
**文献类型**：review-only
**数据源**：<sources>
**检索时间**：<timestamp>

## 📋 速览（25 篇）

| # | 标题 | 作者 | 年份 | DOI | 综述类型 |
|---|------|------|------|-----|---------|
| 1 | [Title](#title-1) | Author1, Author2, ... | 2024 | [10.xxxx](https://doi.org/10.xxxx) | Systematic Review |
| 2 | ... | ... | ... | ... | Meta-Analysis |

> ⭐ Top X 篇 · 1 区 X 篇 · 🔴 预警 X 篇 · 系统综述 X 篇 · Meta 分析 X 篇 · 临床指南 X 篇 · 已跳过重复 X 篇

---

## 📚 详细条目

### # 1 <a id="title-1"></a> Title
- **作者**：...（仅来自 API）
- **年份**：YYYY
- **期刊**：<Name>（1区 / ⭐ Top / 🔴 预警）
- **影响因子**：XX.X
- **DOI**：[10.xxxx](https://doi.org/10.xxxx)
- **综述类型**：Systematic Review / Meta-Analysis / Review / Guideline / Nature Reviews / Cochrane
- **关键词**：k1, k2, k3, k4, k5
- **MeSH 主题词**（如可用）：D001, D002, ...
- **摘要原文**：<来自 OpenAlex / PubMed 的完整 abstract>
- **TLDR**（AI 总结）：<一句话总结>
- **标记**：⭐ Top / 1区 / 🔴 预警 / Cochrane / [Clinical Practice Guideline]

#### 📎 引用格式
<details>
<summary>BibTeX</summary>

```bibtex
@article{...}
```

</details>

<details>
<summary>APA 7</summary>

...

</details>

<details>
<summary>GB/T 7714</summary>

...

</details>

<details>
<summary>RIS</summary>

...

</details>

---

### # 2 ...
```

## 7. 失败处理

| 场景 | 行为 |
|---|---|
| OpenAlex API 限流（429） | 等待 + 重试 1 次 → 切 PubMed |
| PubMed API 限流（429） | backoff 1s → 5s → 30s 后重试；最多 3 次；切 Europe PMC |
| DOI 查无 | 走兜底链 |
| 全部源缺 abstract | 标记 `摘要：N/A`，不编造 |
| 付费墙 | 保留条目，标 `🔒 付费墙`；同时尝试 Europe PMC 开放版本 |
| 全部源失败 | 返回兜底提示 |
| 综述类混入原创研究 | 标 `[非综述，仅参考]`，不计入 review_only 主集 |
| 非医学/非生信/非 AI 主题 | 二次确认是否走错 skill（提示用 qm_paper_search_broad） |

## 8. 数据维护

- 分区数据：shared/data/cas_journal_zones.json（年度更新；2026 版已含医学/AI 顶刊白名单）
- 去重池：shared/data/seen_papers.json（topic_id 加 `broad_` 前缀）
- 用户偏好：shared/data/user_prefs.json
- 路径策略：首次调用询问，后续使用默认，用户说"换路径"再询问

## 9. 与 fine 的区别

| 维度 | fine | broad（本 skill） |
|---|---|---|
| 默认篇数 | 10 | 25 |
| 文献类型 | article（含 Letter / Case Report） | review（系统综述 / Meta / 指南） |
| 顶刊过滤 | 严格 | 宽松 |
| 时间范围 | 近 3 年 | 不限 |
| 排序 | 相关度 | 时间 + 被引 |
| 引用图谱 | 一层 | 一层 |
| 适用 | 深度调研 | 领域概览 |
| 预印本 | 可选纳入 | 通常不纳入（综述已发表） |

## 10. 与 qm_paper_search_broad 的关系

- 完全**独立**的 seen_papers.json / user_prefs.json / cas_journal_zones.json
- 共享：SKILL.md 的整体框架（参数表 / 反幻觉规则 / 引用规范 / key 管理）
- 差异：数据源（PubMed 替代 X-Mol）、期刊白名单、综述类型细化（PRISMA / Cochrane / CPG）、MeSH 优先
- 共存：用户可同时安装两套，按主题关键词自动选择

---

## 11. 法律约束与合规（继承自 mbai_paper_search_fine §11）

本 skill 继承 `mbai_paper_search_fine/SKILL.md` §11 的全部约束，包括：
- 数据来源合规（CC0 / API 协议 / 预印本协议）
- 引用规范（4 种格式必出，保留作者署名）
- 内容使用边界（禁存付费墙 PDF、禁镜像、禁商业转售）
- 隐私保护（不存用户搜索历史到云端；医学 query 含敏感词时尤其注意）
- 学术与临床道德（不替代人工阅读、不替代临床判断）
- 适用法律（按用户司法辖区；含 HIPAA / GDPR / 人类遗传资源条例）
- 医学领域特别约束（预印本明示 / 临床试验检索 / 药品 / 诊断建议 / 未发表数据）

**broad 模式特别约束**：
- 默认 25 篇，可能拉取大量数据 → 注意 API 限流（PubMed 3-10 req/s）
- review 论文引用他人图表要标注原始出处
- 不下载、不批量缓存 review 全文
- Cochrane 系统综述特别注意：PRISMA 流程图、检索策略、纳入/排除标准应在原文中查证
- 临床实践指南（CPG）须查证：**最新版本、发布机构、证据等级、推荐强度、更新日期**——本 skill 仅供索引

## 12. API 限制约束（继承自 mbai_paper_search_fine §12）

本 skill 继承 `mbai_paper_search_fine/SKILL.md` §12 的全部约束。

**broad 模式特别约束**：
- 25 篇 × 完整元数据 ≈ 30-50 req/search，**必须 sleep 防限流**
- 引用图谱默认开，1 篇拉 5-10 req，**最多 250 req/search**
- 建议每次 broad 检索后 sleep 30s 再做下一轮
- PubMed API 共享 IP 3 req/s（无 key），有 NCBI key 提升至 10 req/s
- Europe PMC 礼貌标识（email）即可无硬限流

## 13. API key 管理（继承自 mbai_paper_search_fine §13）

**关键差异**：broad 模式更频繁使用 PubMed API，可能需要 NCBI key。

- OpenAlex key 申请：https://openalex.org/users/sign_up
- PubMed / NCBI key 申请：https://www.ncbi.nlm.nih.gov/account/settings/
- Semantic Scholar key 申请：https://www.semanticscholar.org/product/api
- 详细管理流程见 `data/README_API_KEYS.md`

## 14. 输出规范（继承自 mbai_paper_search_fine §13.6）
- 出版商屏蔽 abstract → 标 `N/A（出版商屏蔽，到 DOI 原页拉）`
- 标记 `🔒 待人工处理`，不编造内容
- 综述层级未达系统综述标准 → 在综述类型中标 `Narrative Review`（叙述性综述），与 Systematic Review 区分
- 临床指南无证据等级 → 标 `证据等级：未披露`，提醒用户查原指南

## 15. 文件清单

```
mbai_paper_search_broad/
├── SKILL.md
└── README.md

共享数据（在 shared/）：
mbai_paper_search_shared/
└── data/
    ├── api_keys.template.json
    ├── api_keys.local.json
    ├── cas_journal_zones.json     (医学/生信/AI 顶刊)
    ├── UPDATE_NOTES.md
    ├── seen_papers.json           (topic_id 加 broad_ 前缀)
    ├── user_prefs.json
    ├── README_API_KEYS.md
    ├── .gitignore
    └── scripts/
        ├── Set-ApiKey.ps1
        ├── mbai_paper_search_setup.ps1
        └── mbai_openalex_to_md.ps1
```

## 16. 维护

- v0.1.0 初版（2026-09-08）：从 qm_paper_search_broad 切换主题到医学/生信/AI；扩展综述类型细分（PRISMA / Cochrane / CPG）；PubMed 综述过滤优先；MeSH 主题词优先
