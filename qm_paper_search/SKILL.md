---
name: qm_paper_search
version: 0.4.1
description: |
  化学领域学术文献检索 v0.4.1（统一 skill；原 qm_paper_search_fine v0.2.3 + qm_paper_search_broad v0.2.2 已于 v0.3.0 合并为单 skill）。
  触发词：文献检索 X（mode 由 skill 内部自动推断）；显式覆盖："精细检索 X" / "粗放检索 X"。
  精细默认触发：深度调研 / 方法学 / 创新点 / 单篇分析 / 对比 / 复现。
  粗放默认触发：概览 / 立项 / 综述 / 摸底 / survey / landscape / 全景。
  精细默认：article-only、10 篇、近 3 年、相关度排序。
  粗放默认：review-only、15 篇、时间不限、时间+被引排序、含宽召回。
  强制反幻觉：全部元数据 only from API，缺则 N/A；交付前用 scripts/validate_output.py 做 DOI 级代码校验。
  检索执行：优先用 scripts/paper_search_client.py（SS/OpenAlex/Crossref 三源合并 + 去重 + Markdown 导出 + --verify 校验）。
  首次使用请先跑 shared/data/scripts/qm_paper_search_setup.ps1（见 §0 Quickstart）。
  数据根目录：%USERPROFILE%\.minimax\skills\qm_paper_search_shared\data\
---

<!--
  Modification Log (added 2026-09-12)
  Format: modified <date>: <phase> — <change summary>
  Keep entries reverse-chronological (newest on top).
-->
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

# qm_paper_search — 化学领域学术文献检索 v0.4.1

## 0. Quickstart（首次使用 3 步）

> 目标：从"看完文档"到"跑出第一个结果"不超过 3 步。若你只想快速验证，直接跳到第 3 步（无 key 也能跑，只是限流更低）。

**步骤 1 · 配 key（可选但强烈建议，1 分钟）**

```powershell
cd $env:USERPROFILE\.minimax\skills\qm_paper_search_shared\data\scripts
.\qm_paper_search_setup.ps1          # 按提示输入 OpenAlex / Semantic Scholar key（可全部留空跳过）
.\Set-ApiKey.ps1 -List               # 查看当前 key 状态
```

**步骤 2 · 确认输出目录（首次会自动问，之后记住）**

- 首次检索时 skill 会问一次"默认保存路径"，答案写入 `shared/data/user_prefs.json` 的 `default_save_dir`。
- 想改：说"换路径"，或直接编辑 `user_prefs.json`。

**步骤 3 · 直接说人话触发**

| 你想做的事 | 就这么说 |
|---|---|
| 已知方向的深度调研 | `文献检索 machine learning potential` ／ `精细检索 COF 催化 近 3 年` |
| 新领域摸底 / 找综述 | `文献检索 概览 钙钛矿太阳能电池` ／ `粗放检索 单原子催化 综述` |
| 直接给出数量/年份 | `文献检索 MOF 气体分离 找 20 篇 近 5 年` |
| 查引用图谱 | `文献检索 CO2 还原 查引用` |

**产出**：`<default_save_dir>\paper_search_{fine|broad}_<query>_<YYYYMMDD>.md`（结构见 §6）。

**步骤 4（推荐）· 用脚本一键跑完整链路**

不想让 Agent 逐步拼请求时，直接用随包脚本——它把"检索 → 去重 → 过滤 → 导出 → 校验"一次做完：

```powershell
cd $env:USERPROFILE\.minimax\skills\qm_paper_search_shared\data\scripts

# 精细检索（近 3 年 / article / 10 篇）
python paper_search_client.py -q "machine learning potential" --pretty --verify

# 粗放检索（综述为主 / 时间不限 / 15 篇）+ 方案 H 方向过滤
python paper_search_client.py -q "钙钛矿太阳能电池" --mode broad `
    --concept-pattern "perovskite|solar[ ]cell" --pretty --verify

# 先看不落盘（dry-run）+ 另存原始 JSON
python paper_search_client.py -q "MOF 气体分离" --count 20 --dry-run `
    --json-out raw.json
```

**交付前自检（必做，30 秒）**：

```powershell
python validate_output.py "<刚生成的 .md 路径>" --pretty     # 校验率 <95% 退出码为 2
```
（若上一步用了 `--verify`，此步已自动完成。）

### 0.1 常见困惑速答

| 困惑 | 答案 |
|---|---|
| 为什么只给关键词也能跑？ | mode 会在 §5.1 的规则下自动推断，默认精细。 |
| 为什么"不爬 Google Scholar"？ | 合规 + 稳定性原因，替代路径见 §3.4。 |
| 摘要为什么是 N/A？ | 出版商屏蔽，规则禁止用 AI 总结兜底，见 §4.1 / §11.6。 |
| 为什么第二次检索少了论文？ | 去重池生效，见 §5.2（含跨 topic 去重策略）。 |
| 每次跑多久？ | 精细约 1-2 分钟；粗放（含宽召回 + 引用图谱）约 5-10 分钟。 |

## 1. 适用与不适用

**适用**

| 场景 | 推荐模式 | 触发关键词 |
|---|---|---|
| 已知方向深度调研、单篇分析、方法学比较 | **精细（fine）** | 默认 / 深度 / 方法 / 创新 / 对比 / 复现 |
| 新方向立项、领域概览、综述集合、宽召回 | **粗放（broad）** | 概览 / 立项 / 综述 / 摸底 / survey / landscape / 全景 |
| 找原创研究、Letter、案例分析 | 精细 | article / letter / case |
| 找高被引、高影响力综述 | 粗放 | review / 高被引 / 综述 |
| 引用图谱（references + cited by，一层） | 两者 | 引用 / 参考文献 |

**不适用**

- 非化学领域（医学 / 生信 / AI 请用 `mbai_paper_search` 系列；生物、物理、材料工程请用对应领域 skill）
- 全文下载、翻译、润色（下载与精读 → 用 `paper-deep-reading`）
- 已知方向但需要逐篇精读 → 用 `paper-deep-reading`（两者衔接方式见该 skill 的 `references/pipeline-orchestration.md`）

## 2. 检索参数

| 参数 | 精细默认 | 粗放默认 | 可选值 | 说明 |
|---|---|---|---|---|
| `type` | article-only | review-only | article / review / all / mixed / letter | 文献类型过滤 |
| `count` | 10 | **15** | 1-100 | 返回篇数（**粗放建议 10-25**；>25 会显著拉长耗时与限流风险） |
| `years` | 3 | 不限 | 1-10 / 不限 | 时间范围（年） |
| `journal_filter` | strict | loose | strict / loose | 顶刊过滤严格度 |
| `sort_by` | relevance | time+citations | relevance / time / citations / time+citations | 排序方式 |
| `citation_graph` | on | on | on / off | 引用图谱开关 |
| `abstract_source` | ss | ss | ss / crossref / openalex / xmol | 摘要主源 |
| `keywords_required` | true | true | true / false | 是否必须返回关键词 |
| `tldr` | optional | optional | required / optional / off | TLDR 开关（质量警告见 §4.3） |
| `concept_pattern` | — | *(空)* | regex | **粗放专属** 宽召回概念过滤（v0.2.2 方案 H，详见 §3.3） |
| `min_concept_match` | — | 1 | 0-10 | **粗放专属** 宽召回最少命中概念数 |

> **粗放默认 count 调整说明（v0.4.0）**：v0.2.x 默认 25 篇，叠加引用图谱后单次约 250 req，实测一次要 10+ 分钟，对立项摸底场景过重。v0.4.0 收敛为 **15 篇**（覆盖"方向全貌"的典型需求），用户显式说"找 30 篇"时再放宽。

## 3. 数据源（v0.4.0 主链）

### 3.1 主链与口径澄清

```
Semantic Scholar API        主检索源（2 亿+ 论文；带 key 可享更高限流）
  ↓ 缺 abstract / keywords
Crossref                    元数据权威（DOI 反查、卷期页、作者）
  ↓ 缺
OpenAlex                    覆盖最广的兜底（含 concepts、OA 链接）
  ↓ 缺
X-Mol                       中文友好 + 国内化学社区（仅跳转，不入结构化字段）
  ↓ 缺
返回 N/A
```

**口径澄清（v0.4.0 修正 v0.2.x 的表述不一致）**：

- v0.2.1 的 changelog 写"主源从 Google Scholar 切换到 OpenAlex"，v0.2.3 的 description 又写"主源 Semantic Scholar API"——两处口径冲突，现统一为：
  - **主检索源 = Semantic Scholar**（负责"发现论文"）；
  - **元数据权威源 = Crossref**（负责"校准元数据"）；
  - **覆盖兜底 = OpenAlex**（负责"补漏 + concepts 过滤"）。
- **不爬 Google Scholar**（v0.2 决定，理由与替代路径见 §3.4）。
- **不依赖 LLM 编造**（强制反幻觉规则，§4）。

### 3.2 调用契约（Agent 执行主体 · v0.4.0 新增）

> **执行主体二选一**：
> 1. **首选（v0.4.1 起推荐）**：直接跑 `shared/data/scripts/paper_search_client.py`——它已按本表实现全部请求、
>    合并、去重、导出与校验，`--pretty --verify` 一条命令交付成品。**能用脚本就用脚本**，避免 Agent 现场拼参数出错。
> 2. **兜底**：脚本不可用（无 Python / 需定制字段）时，由 **Agent（LLM runtime）** 按下表直接发起请求。
>
> 仓库内其他脚本职责单一：`qm_openalex_to_md.ps1`（JSON→Markdown 转换）、`validate_output.py`（DOI 反查校验）。
>
> 下表是**唯一权威的调用参数**。请不要临场发明 endpoint 或字段名——这是 v0.2.x"文档承诺与实现脱节"的根因。

| 步骤 | 方法 / endpoint | 关键参数 | 需取用的字段 |
|---|---|---|---|
| ① 主检索 | `GET https://api.semanticscholar.org/graph/v1/paper/search` | `query`、`limit`（≤100）、`year=YYYY-YYYY`、`publicationTypes=JournalArticle\|Review`、`fields=title,abstract,year,venue,publicationVenue,externalIds,authors,fieldsOfStudy,tldr,citationCount,referenceCount,openAccessPdf` | `data[]` → `paperId / title / abstract / year / venue / externalIds.DOI / authors[].name / fieldsOfStudy / tldr.text / citationCount` |
| ② 引用图谱 | `GET https://api.semanticscholar.org/graph/v1/paper/{paperId}/references` 或 `/citations` | `limit=20`、`fields=title,year,venue,externalIds` | `data[].citedPaper` / `data[].citingPaper` |
| ③ DOI 反查 | `GET https://api.crossref.org/works/{doi}` | `mailto=<你的邮箱>` | `message.title / author / container-title / volume / issue / page / published.date-parts / publisher` |
| ④ 兜底检索 | `GET https://api.openalex.org/works` | `search=`、`per-page=`、`filter=type:review,from_publication_date:YYYY-MM-DD`、`mailto=`、`sort=relevance_score:desc` | `results[]` → `display_name / publication_year / doi / authorships[].author.display_name / primary_location.source.display_name / abstract_inverted_index / concepts[] / cited_by_count / open_access.oa_url` |
| ⑤ 接收头 | 所有请求 | `User-Agent: qm_paper_search_skill/0.4 (paper retrieval)`；有 key 时附 `x-api-key`（SS）/ `api_key`（OpenAlex）或 `mailto` | — |

**字段还原注意**：

- OpenAlex **不返回 `abstract` 字段**，需用 `abstract_inverted_index`（`{词: [位置...]}`）还原成句子，还原后标注来源为 `openalex`。
- Crossref **多数条目无 abstract**，只取元数据；不要用 Crossref 的 `abstract` 字段填充（往往是出版商模板 HTML）。
- SS 的 `abstract` 可能为 `null`、`tldr` 可能缺失 → 按 §3.1 主链继续降级，不要编造。

### 3.3 宽召回机制（粗放专属 · v0.2.2 方案 H · 配套脚本 `qm_openalex_to_md.ps1`）

> **为什么需要宽召回**：粗放模式默认 `type=review-only` + `years=不限` 时，OpenAlex / SS 直出结果常返回 200+ 条候选，但其中大量是与查询方向无关的"边缘综述"。直接按相关度排序容易漏掉方向核心综述。
>
> **方案 H 核心思路**：先宽召回（不筛方向），再用 `concept_pattern`（regex）做二次方向过滤。

**两步流程**：

1. **宽召回**：不带方向过滤，全量拉取 `count × 3-5` 条候选。
2. **方向过滤**（脚本层，**不增加 API 调用**）：
   - 对每条候选的 `title + abstract + concepts` 用 `concept_pattern`（regex）做匹配
   - 命中数 ≥ `min_concept_match` 才保留
   - 不足时**不补调 API**，仅在最终报告里声明"过滤后 N 篇，命中原 query 核心 M 篇（M < N）"

**典型用法**（生物催化方向）：

```powershell
.\qm_openalex_to_md.ps1 `
    -InputJsonFile "raw_search.json" `
    -OutputMdFile "biocatalysis_broad_20260912.md" `
    -Mode broad `
    -TopicName "biocatalysis" `
    -BroadConceptPattern "biocatalysis|enzymatic[ ]catalysis|enzyme[ ]catalysis" `
    -BroadMinMatch 1
```

**与 §2 参数的关系**：

- `count` = **最终输出数**（过滤后）
- 实际 API 拉取数 = `count × 3-5`（count=15 时约 45-75 条候选）
- 单次粗放检索 API 请求量 ≈ **40-90 req**（引用图谱默认开时另计，见 §10.6）

**为什么不内置到 LLM 决策**：

- 概念过滤涉及 regex 性能 + 候选遍历，LLM prompt 里描述不如脚本一行实现
- `concept_pattern` 决定"什么算这个方向"，跨 topic 不一致 → 需用户 / 脚本显式指定

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

## 4. 强制反幻觉规则

### 4.1 字段级规则

| 字段 | 来源 | 缺失处理 |
|---|---|---|
| 标题 | API 原始 | 强制必须有 |
| 作者 | API 原始 | 缺则 `N/A`，**严禁 LLM 补全** |
| 年份 | API 原始 | 强制必须有 |
| 期刊 | API 原始 | 缺则 `N/A` |
| 卷/期/页 | API 原始（Crossref 优先） | 缺则 `N/A` |
| DOI | API 原始 | 强制必须有 |
| 影响因子 | 本地 `cas_journal_zones.json` | 缺则 `N/A` |
| 摘要原文 | SS / Crossref / OpenAlex / X-Mol | 缺则 `N/A` |
| 关键词 | API 原始（SS `fieldsOfStudy` / OpenAlex `concepts`） | 缺则 `N/A` |
| TLDR | Semantic Scholar `tldr` 字段 | AI 总结必须明确标"（AI 总结）"，且受 §4.3 约束 |

**禁止**：

- LLM 编造任何字段
- snippet 截取当 abstract
- 推断页码 / 作者 / 卷期
- 把 OpenAlex `concepts` 直接当作论文"关键词"（二者语义不同，需标注为"概念标签"）

### 4.2 代码化校验（v0.4.0 新增 · 把"恳求"变成"可验证"）

§4.1 是**写给 AI 的规则**；`shared/data/scripts/validate_output.py` 是**可执行的校验层**：

```powershell
cd $env:USERPROFILE\.minimax\skills\qm_paper_search_shared\data\scripts
python validate_output.py "C:\...\paper_search_broad_xxx_20260912.md" --pretty --threshold 0.95
```

| 行为 | 说明 |
|---|---|
| 输入 | 生成的 `.md` 名录（支持 glob 多文件） |
| 动作 | 抽取全部 DOI → 逐个向 Crossref 反查 → 标记 ✅ verified / ❌ not_found / ⚠️ error |
| 判定 | 校验率 < `--threshold`（默认 0.95）→ 退出码 **2**，即"不应交付" |
| 离线 | `--no-network` 仅做 DOI 抽取自检；`--json-out` 输出机器可读报告 |

**交付纪律**：**任何 .md 名录在交付给用户前必须跑一次 validate_output.py**；不达标时按 §7.1 的"DOI 校验不达标"话术如实告知用户，不要静默交付。

### 4.3 TLDR 字段质量警告（v0.4.0 新增）

- SS 的 `tldr` 是**第三方模型生成的压缩摘要**，不是作者原文，质量参差（长文 / 多结论论文尤其容易失真）。
- 因此：`tldr` 一律标注"（AI 总结）"，**不得**作为"关键发现 / 结论"的唯一依据。
- 化学 / 材料类论文的定量结论（能垒、产率、选择性、误差）**必须**回到 `abstract` 原文核对。
- 用户表示"只看 TLDR"时，需明确提示"该字段可能遗漏关键限定条件与数值"。
- 默认 `tldr=optional`；追求严谨时设 `tldr=off`。

## 5. 触发与去重

### 5.1 触发方式

**统一触发词**：`文献检索 X`（mode 由 skill 内部自动推断）。

**mode 推断规则**：

```python
# 伪代码（实际由 LLM 在执行时按规则匹配）
if re.search(r"概览|立项|综述|摸底|survey|landscape|全景|review", query, re.I):
    mode = "broad"
elif re.search(r"深度|方法|创新|对比|复现", query, re.I):
    mode = "fine"
else:
    mode = "fine"  # 默认精细
```

**显式覆盖**（向后兼容）：用户说"精细检索 X" / "粗放检索 X" 可显式指定。

**auto-mode 推断示例**：

| Query | 推断 mode | 理由 |
|---|---|---|
| `文献检索 machine learning potential` | fine | 默认 |
| `文献检索 概览 钙钛矿太阳能电池` | broad | 命中"概览" |
| `文献检索 立项摸底 单原子催化` | broad | 命中"立项摸底" |
| `文献检索 综述 COF 催化` | broad | 命中"综述" |
| `文献检索 survey of MOF synthesis` | broad | 命中"survey" |
| `文献检索 DFT 计算方法对比` | fine | 命中"对比" |
| `文献检索 单篇分析 JACS 2024` | fine | 默认（精细） |

### 5.2 去重机制

- 数据源：`%USERPROFILE%\.minimax\skills\qm_paper_search_shared\data\seen_papers.json`
- `topic_id` 前缀：
  - 精细 topic 用 `fine_<topic_name>`
  - 粗放 topic 用 `broad_<topic_name>`
  - **合并后两个前缀并存识别**——旧 v0.2.x 数据无缝保留
- 同 topic 重复检索自动跳过 `seen_dois`
- 显式命令：新方向 / 清空当前方向记忆 / 清空全部记忆 / 全局去重

**跨 topic 去重策略（v0.4.0 修正，原"跨 topic 默认不去重"反用户）**：

v0.2.x 的"跨 topic 默认不去重"在实践中反用户：做过"机器学习力场"再开"分子动力学力场"，会重复收到同一批 JCTC / J. Chem. Phys. 论文。v0.4.0 规则：

| 情形 | 默认行为 | 用户可覆盖 |
|---|---|---|
| 同 topic 重复检索 | 跳过 `seen_dois` | — |
| 新 topic 与已有 topic **共享 ≥1 个核心关键词**（如"力场"/"催化"） | **跨 pool 合并去重**（默认开启） | "本方向不去重" |
| 新 topic 与已有 topic 无共同关键词 | 不去重（视为真新方向） | "全局去重" |
| 用户显式说"全局去重" | 全局去重 | "清空全部记忆" |

- `seen_papers.json` 结构**不变**（仍按 `topic_id` 分组）；"跨 pool 去重"是**读取时合并**，不破坏历史数据。
- 报告末尾必须注明："跨主题去重跳过 N 篇（来自 pool: X, Y）"，保证透明可核查。

## 6. 输出格式

输出文件命名：

- 精细：`paper_search_fine_<query>_<YYYYMMDD>.md`
- 粗放：`paper_search_broad_<query>_<YYYYMMDD>.md`

保存路径：`shared/data/user_prefs.json` 的 `default_save_dir`。

### 6.1 统一输出约定（与 paper-deep-reading 对齐 · v0.4.0）

跨两个 skill 的**同一套约定**，便于"检索结果 → 精读报告 → 知识库存档"流水线直接串联：

| 约定 | 规则 |
|---|---|
| 元信息块 | 置于文件开头，字段顺序：查询/主题 → 时间范围 → 文献类型 → 数据源 → 检索时间 → 模式；**每字段一行 `**字段**：值`** |
| DOI 形式 | 一律 `[10.xxxx/yyy](https://doi.org/10.xxxx/yyy)` 可点击链接 |
| 期刊标记 | `（1区 / ⭐ Top / 🔴 预警 / [Preprint] / 🔒 付费墙）`，与 `cas_journal_zones.json` 一致 |
| 来源标注 | 【原文】= API 原始；【AI分析】= 归纳（含 TLDR）；【推测】= 不确定推断 |
| 术语 | 化学术语遵循"首次出现给中英对照、全文译名统一" |
| 结论 | 不输出"决策建议"，仅陈述检索事实 + 可核查链接 |

### 6.2 文件结构

```markdown
# 文献检索结果（精细模式）/（粗放模式 · 综述为主）

**查询**：<query>
**研究方向**：<topic_name>
**时间范围**：YYYY–YYYY（精细）/ 不限（粗放）
**文献类型**：article-only（精细）/ review-only（粗放）
**数据源**：<sources>
**检索时间**：<timestamp>
**模式**：fine / broad

## 📋 速览（10 篇 / 15 篇）

| # | 标题 | 作者 | 年份 | DOI |
|---|------|------|------|-----|
| 1 | [Title](#title-1) | Author1, Author2, ... | 2025 | [10.xxxx](https://doi.org/10.xxxx) |
| 2 | ... | ... | ... | ... |

> ⭐ Top X 篇 · 1 区 X 篇 · 🔴 预警 X 篇 · [Preprint] X 篇 · 已跳过重复 X 篇（跨主题去重 X 篇）

---

## 📚 详细条目

### # 1 <a id="title-1"></a> Title
- **作者**：...（仅来自 API）
- **年份**：YYYY
- **期刊**：<Name>（1区 / ⭐ Top / 🔴 预警）
- **影响因子**：XX.X
- **DOI**：[10.xxxx](https://doi.org/10.xxxx)
- **关键词**：k1, k2, k3, k4, k5
- **摘要原文**：<来自 Semantic Scholar 的完整 abstract>
- **TLDR**（AI 总结）：<一句话总结>
- **标记**：⭐ Top / 1区 / 🔴 预警 / [Preprint]

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

**字段说明**：9 个核心字段 = 作者 / 年份 / 期刊 / 影响因子 / DOI / 关键词 / 摘要原文 / TLDR / 标记。4 种引用格式（BibTeX / APA 7 / GB/T 7714 / RIS）按学术规范折叠。

### 6.3 交付前自检清单

- [ ] 已跑 `validate_output.py` 且校验率 ≥ 0.95（否则按 §7.1 如实告知）
- [ ] 元信息块字段齐全且顺序正确（§6.1）
- [ ] 所有 DOI 均为可点击链接
- [ ] 跳过的重复条目数已在速览行注明（含跨主题去重来源 pool）
- [ ] 缺失字段统一写 `N/A`，无 LLM 补全痕迹
- [ ] 摘要为完整 abstract 原文，非 snippet 截取

## 7. 失败处理

| 场景 | 行为 |
|---|---|
| SS API 限流（429） | 等待 + 重试 1 次 → 切 Crossref |
| DOI 查无 | 走兜底链 |
| 全部源缺 abstract | 标记 `摘要：N/A`，不编造 |
| 付费墙 | 保留条目，标 `🔒 付费墙` |
| 全部源失败 | 返回兜底提示 |
| 非化学 | 二次确认 |

### 7.1 面向用户的错误提示模板（v0.4.0 新增）

错误处理必须**对用户可见**，不能只写日志或静默降级；也**不要**用一问一答把无人值守流程卡死：

| 场景 | 用户可见输出（一行即可） | 自动动作（不打断用户） |
|---|---|---|
| API key 401/403 | "⚠️ 配置的 {source} key 已失效，已自动回退无 key 模式（限流 5 req/s）。更新：`Set-ApiKey.ps1 -Provider {source} -Key <NEW>`" | 回退并继续 |
| 429 限流 | "⏳ {source} 限流，已退避 30s 后重试（第 N/3 次）" | backoff 重试 |
| 某源整体不可用 | "⚠️ {source} 当前不可用，已改用 {fallback}；本次结果按 {fallback} 口径返回" | 切兜底源 |
| 全部源失败 | "❌ 全部数据源失败：<每源一行原因>。请检查网络或稍后重试；也可改用 web_search 兜底（覆盖率会下降）" | 停止 |
| 非化学主题 | "「X」看起来属于 {领域}，本 skill 专精化学。仍按化学口径检索吗？（Y/N）；或改用 mbai_paper_search（医学/生信/AI）" | **唯一允许的交互**，其余场景不应阻塞 |
| DOI 校验不达标 | "⚠️ 交付前校验：N 个 DOI 中 M 个未通过 Crossref 反查，已标 ❌，请人工复核这些条目" | 标记并交付 |

> 原则：**能自动降级就自动降级**（附一条 ⚠️ 说明），只在"必须由用户决策"时才提问。

## 8. 数据维护

- 分区数据：`shared/data/cas_journal_zones.json`（年度更新）
- 去重池：`shared/data/seen_papers.json`（topic_id 加 `fine_` / `broad_` 前缀，**合并后两个并存识别**；跨 pool 去重见 §5.2）
- 用户偏好：`shared/data/user_prefs.json`
- 调用日志：`shared/data/api_logs.json`（本地，90 天自动清理）
- 路径策略：首次调用询问，后续使用默认，用户说"换路径"再询问

## 9. 法律约束与合规

### 9.1 数据来源合规

| 数据源 | 协议 | 使用范围 |
|---|---|---|
| **OpenAlex** | CC0（公有领域） | 可自由使用、修改、分发，无需署名（建议注明 "Data from OpenAlex"） |
| **Crossref** | CC0 | 同上 |
| **Semantic Scholar** | API 协议 | 注明来源；非商业用途建议遵守 |
| **X-Mol** | 学术聚合 | 仅用于学术检索，不存原文 |
| **PubMed** | 公有领域 | 可自由使用 |
| **arXiv / ChemRxiv** | 各预印本协议 | 引用时保留 license 信息 |

### 9.2 引用规范

- **必须保留**：原始作者、期刊、DOI、出版商信息
- **必须输出**：4 种引用格式（BibTeX / APA 7 / GB/T 7714 / RIS），按学术规范
- **严禁**：去除作者署名、期刊信息、DOI
- **翻译字段**（GB/T 7714 中文版）：由 LLM 拼装，**不作为权威引用**，仅供中文用户参考；以英文原版为准

### 9.3 内容使用边界

**允许**：

- 保存论文元数据（标题、作者、DOI、摘要、引用数、概念标签）
- 保存 inverted index 还原的 abstract
- 复制 OpenAlex concepts（CC0）
- 通过 DOI 链接到出版商原页（仅作跳转，不存 PDF）

**禁止**：

- ❌ 存储付费墙后的 PDF 原文
- ❌ 批量下载/镜像出版商数据库
- ❌ 商业转售聚合数据
- ❌ 去除来源标识
- ❌ 用于生成假论文、伪造数据
- ❌ 替代人工阅读原文作为决策唯一依据

### 9.4 隐私与个人信息

- 不存储用户搜索历史到云端
- `seen_papers.json` 仅存 DOI（公开标识符）
- `user_prefs.json` 存本地路径，不上传
- `api_keys.local.json` 存本机，仅 skill 内部使用
- ❌ 严禁分享他人提供的 API key
- ❌ 严禁把用户搜索内容上传到第三方

### 9.5 学术道德

- 本 skill 是**辅助工具**，不替代人工阅读
- 检索结果仅供学术调研，**不作为决策唯一依据**
- 引用必须以**原文献**为准，本工具输出仅作辅助
- 严禁用于：代写论文、伪造数据、剽窃、学术不端
- 严禁绕过付费墙抓取全文
- 严禁批量爬取造成出版商服务器压力

### 9.6 适用法律

- 本 skill 仅在用户所在司法辖区**合法使用**
- 涉及跨境学术资源时遵守当地法规：
  - **中国境内**：遵守《网络安全法》《数据安全法》《个人信息保护法》《科学技术进步法》
  - **欧盟**：遵守 GDPR
  - **美国**：遵守 CFAA、DMCA
- 学术出版商协议以各出版商 ToS 为准
- 如发现违规使用，立即停止相关功能

## 10. API 限制约束

### 10.1 OpenAlex API 规则

| 项目 | 限制 |
|---|---|
| **限流（带 key）** | 50 req/s |
| **限流（无 key）** | 5 req/s |
| **polite pool** | 建议带 `mailto=your@email.com` 或 key 标识 |
| **User-Agent** | 强烈建议带标识（OpenAlex 用于诊断） |
| **数据更新** | 每月一次完整更新，每月新增 ~500 万论文 |

**强制行为**：

- ✅ 加 User-Agent：`qm_paper_search_skill/0.4 (paper retrieval)`
- ✅ 加 key 或 mailto
- ❌ 禁止并发批量刷（> 10 req/s 持续）
- ❌ 禁止镜像/转售数据
- ❌ 禁止用于 LLM 训练

### 10.2 当前 key 使用情况

- key 存于 `%USERPROFILE%\.minimax\skills\qm_paper_search_shared\data\api_keys.local.json`
- 仅用于本 skill，**不分享**
- ❌ 不嵌入到代码仓库公开处
- key 失效时（401/403）：按 §7.1 提示用户提供新 key，并自动回退无 key 模式（5 req/s）

### 10.3 错误码处理

| 状态码 | 含义 | 处理 |
|---|---|---|
| 200 | OK | 继续 |
| 401 | key 无效 | 提示新 key（§7.1）；回退无 key 模式 |
| 403 | 禁止访问 | 检查 User-Agent / key / IP |
| 429 | 限流 | backoff 1s → 5s → 30s 后重试；最多 3 次 |
| 5xx | 服务端错误 | backoff 重试 3 次 → 切换兜底源 |
| network_error | 网络层失败 | 切换 web_search 兜底 |

### 10.4 调用频率建议

| 场景 | 建议频率 |
|---|---|
| 主题检索 | 1-2 req/search（搜索 + 详情） |
| 引用图谱 | 1-5 req/paper（references + cited by） |
| 批量检索 | ≤ 10 req/min（避免触发限流） |
| 持续监控 | 严禁（无合理学术场景） |

### 10.5 调用日志

- 每次 API 调用记录：endpoint / status / latency / date
- 异常时记录完整错误
- 日志仅本地（`shared/data/api_logs.json`），**不上传**
- 用于诊断 API 健康度
- 90 天后自动清理过期日志

### 10.6 API 健康度监控

- 当 OpenAlex 失败率 > 50% 时：自动切兜底源
- 当 429 连续 3 次：暂停 5 分钟
- 当 5xx 连续 5 次：警告用户并切兜底

**粗放模式特别约束**：

- 15 篇 × 完整元数据 ≈ 20-40 req/search，**必须 sleep 防限流**
- 引用图谱默认开，1 篇拉 5-10 req，**最多约 150 req/search**
- 建议每次粗放检索后 sleep 30s 再做下一轮
- SS API 共享 IP 100 req/min 限流，无 key 也能跑（带 key 提升）

## 11. API key 管理

### 11.1 设计原则

- **团队共享代码 + 个人本地 key** —— 代码 commit 到 git，key 不共享
- 每个成员独立管理自己的 key
- 支持后续 key 变更（失效、续期、轮换）

### 11.2 读取顺序

1. `data/api_keys.local.json`（个人本地，最优先）
2. 环境变量 `OPENALEX_API_KEY` / `SEMANTIC_SCHOLAR_API_KEY`（User 级别）
3. 不使用 key（限流低但能跑）

`api_keys.template.json` 是占位符，**不会被读**。

### 11.3 首次配置

```powershell
cd $env:USERPROFILE\.minimax\skills\qm_paper_search_shared\data\scripts
.\qm_paper_search_setup.ps1
# 按提示输入 OpenAlex / SS key（或留空跳过）
```

### 11.4 后续管理

```powershell
# 查看当前 key 状态
.\Set-ApiKey.ps1 -List

# 更新 OpenAlex key
.\Set-ApiKey.ps1 -Provider openalex -Key "NEW_KEY"

# 改用环境变量
.\Set-ApiKey.ps1 -Provider openalex -EnvVar

# 删除 key
.\Set-ApiKey.ps1 -Provider openalex -Remove

# 验证 key 有效性
.\Set-ApiKey.ps1 -Validate
```

### 11.5 安全约束

- ❌ 不要把 `api_keys.local.json` 加入 git
- ❌ 不要在聊天/邮件/截图中分享 key
- ✅ key 失效时（401/403）立即更新
- ✅ 详细文档见 `data/README_API_KEYS.md`

### 11.6 输出规范

- 出版商屏蔽 abstract → 标 `N/A（出版商屏蔽，到 DOI 原页拉）`，**不用 AI 总结兜底**
- 标记为 `🔒 待人工处理`，交付用户
- 不在 .md 中编造 abstract 内容

**粗放模式特别约束**：

- 粗放模式更频繁使用 SS API，可能需要 Semantic Scholar key
- OpenAlex key 申请：https://openalex.org/users/sign_up
- Semantic Scholar key 申请：https://www.semanticscholar.org/product/api
- 详细管理流程见 `data/README_API_KEYS.md`

## 12. 文件清单

```
qm_paper_search/
├── SKILL.md          (本文件，v0.4.0)
├── README.md         (用户视角的触发/参数/FAQ)
└── assets/
    └── eval-checklist.md   (检索评测：gold query 集 + DOI 校验阈值)

qm_paper_search_shared/data/
├── api_keys.template.json     (团队共享，commit)
├── api_keys.local.json        (个人本地，gitignore)
├── cas_journal_zones.json     (中科院分区 + IF)
├── seen_papers.json           (去重池，topic_id 分组)
├── user_prefs.json            (default_save_dir 等偏好)
├── api_logs.json              (本地调用日志，90 天清理)
├── sample_broad.json          (粗放模式 JSON 样例，供离线调试)
├── README_API_KEYS.md
├── UPDATE_NOTES.md
├── .gitignore
└── scripts/
    ├── _lib_paths.ps1               (共享路径解析)
    ├── Set-ApiKey.ps1               (单 key 管理)
    ├── qm_paper_search_setup.ps1    (首次配置向导)
    ├── qm_openalex_to_md.ps1        (JSON → Markdown 转换 + 方案 H 宽召回过滤)
    ├── paper_search_client.py       (★ v0.4.1：零依赖 Python 检索客户端 · 一键交付)
    └── validate_output.py           (交付前 DOI 反查校验 · v0.4.0)
```

### 12.1 `paper_search_client.py` 速查（v0.4.1 新增）

| 能力 | 说明 |
|---|---|
| 多源检索 | Semantic Scholar（主）→ OpenAlex（覆盖兜底）→ Crossref（元数据权威），源失败自动降级并打印告警 |
| 合并去重 | DOI 优先、无 DOI 回退标准化标题；Crossref 覆盖卷/期/页 |
| 方案 H | `--concept-pattern` + `--min-concept-match`，纯本地过滤不额外发请求 |
| 去重池 | 自动读写 `seen_papers.json`（`fine_*` / `broad_*` 前缀）；默认跨 topic 合并去重，`--no-dedup` / `--no-cross-topic` / `--global-dedup` 可覆盖 |
| 导出 | §6.2 规定的 Markdown（元信息块 + 速览 + 详细条目 + BibTeX / APA 7 / GB/T 7714 / RIS） |
| 校验 | `--verify` 直接复用 `validate_output.py`，校验率 <95% 时返回退出码 4 |
| 其它 | `--dry-run`（不落盘）、`--json-out`（原始 JSON）、`--pretty` / `--quiet` |

退出码：`0` 成功；`2` 全部数据源失败；`3` 参数错误；`4` 校验未达标。

## 13. 维护

**当前版本：v0.4.1**（与 frontmatter 一致）。

| 版本 | 日期 | 重点变更 |
|---|---|---|
| **v0.4.1** | 2026-09-12 | **补 Python 检索客户端**：新增 `scripts/paper_search_client.py`（SS/OpenAlex/Crossref 三源合并 + 去重池 + 方案 H 过滤 + §6.2 Markdown 导出 + `--verify`），闭合锐评处置建议 #1；修复 `validate_output.py` 的 f-string 语法错误与 BibTeX 花括号导致的 DOI 误抽 |
| **v0.4.0** | 2026-09-12 | **文档 ↔ 实现对齐 + 可复用性**：新增 §0 Quickstart、§3.2 调用契约（endpoint/字段写死）、§3.4 GS 替代路径；新增 §4.2 代码化校验（validate_output.py）、§4.3 TLDR 警告；§5.2 跨 topic 去重策略重写；新增 §7.1 面向用户错误模板；粗放默认 count 25→15；§12 文件清单同步；§6.1 与 paper-deep-reading 统一输出约定 |
| v0.3.0 | 2026-09-12 | **合并**：原 `qm_paper_search_fine` v0.2.3 + `qm_paper_search_broad` v0.2.2 → 单 skill `qm_paper_search`。自动推断 mode，统一触发词"文献检索 X" |
| v0.2.3 | 2026-09 | 精细：API key 个体管理；输出规范（出版商屏蔽不再用 AI 总结兜底） |
| v0.2.2 | 2026-09 | 粗放：方案 H 宽召回 + 二次过滤（`qm_openalex_to_md.ps1`）；引入 Semantic Scholar API 作为粗放主源 |
| v0.2.1 | 2026-09 | 主源从 Google Scholar 切换到 OpenAlex（合规 + 稳定） |
| v0.2   | 2026-09 | 初始 v0.2 拆分：原 v0.1 单 skill 拆为 fine + broad 双 skill |
| v0.1   | 2026-09-08 | 弃用（保留于 `qm_paper_search_v0.1_deprecated/` 目录作历史归档，详见该目录 `data/ARCHIVE_NOTICE.md`） |

**版本口径（重要）**：v0.2.x 期间 `version` 字段先后标 0.2 / 0.2.1 / 0.2.2 / 0.2.3；**v0.3.0 起为单一 skill、单一版本号**。外部导入本 skill 时以本节表格 + frontmatter `version` 为准。

**废弃目录说明**：

- `qm_paper_search_v0.1_deprecated/` — v0.1 历史归档（**保留全部 user data**）
- `qm_paper_search_broad/` — v0.2.2 标 DEPRECATED，已重定向到本 skill（见该目录 `DEPRECATED.md`）
