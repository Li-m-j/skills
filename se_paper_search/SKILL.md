---
name: se_paper_search
version: 0.1.0
description: |
  统计科学 / 计量经济学 / 经济学领域学术文献检索（统一 skill，fine/broad 双模式，mode 由查询关键词自动推断）。
  触发词："文献检索 X"；显式覆盖："精细检索 X" / "粗放检索 X"。粗放默认触发词：概览 / 立项 / 综述 / 摸底 / survey / landscape / 全景；未命中则默认精细。
  精细默认：article-only、10 篇、近 3 年、相关度排序；粗放默认：综述+工作论文、15 篇、时间不限、含方案 H 宽召回。
  主链 arXiv（econ.EM/stat.* 预印本主渠道，免 key）→ OpenAlex → Semantic Scholar → Crossref。
  反幻觉红线：全部元数据 only from API，缺则 N/A；交付前必须用 scripts/validate_output.py 做 DOI + arXiv ID 双反查。
  领域红线：检索结果不构成投资建议；未发表工作论文必须显式标注；不替代官方统计发布口径。
  执行：优先运行 scripts/paper_search_client.py（四源合并 + 去重 + Markdown 导出 + --verify）；首次使用先按 §0 Quickstart 配置。
  不适用：化学/材料 → qm_paper_search；医学/生信/AI → mbai_paper_search；论文 PDF 深度阅读 → paper-deep-reading。
---

<!-- 历次修订记录见 ./CHANGELOG.md -->

# se_paper_search — 统计经济学领域学术文献检索 v0.1.0

## 0. Quickstart（首次使用 3 步）

> 目标：从"看完文档"到"跑出第一个结果"不超过 3 步。**本 skill 零 key 即可完整跑通**（arXiv / Crossref / OpenAlex 免 key，SS 共享 IP 限流），配 key 只是提速。

**步骤 1 · 配 key（可选，1 分钟）**

```powershell
cd $env:USERPROFILE\.minimax\skills\se_paper_search_shared\data\scripts
.\se_paper_search_setup.ps1          # 按提示输入 OpenAlex / Semantic Scholar key（可全部留空跳过）
.\Set-ApiKey.ps1 -List               # 查看当前 key 状态
```

**步骤 2 · 确认输出目录（首次会自动问，之后记住）**

- 首次检索时 skill 会问一次"默认保存路径"，答案写入 `shared/data/user_prefs.json` 的 `default_save_dir`。
- 想改：说"换路径"，或直接编辑 `user_prefs.json`。

**步骤 3 · 直接说人话触发**

| 你想做的事 | 就这么说 |
|---|---|
| 已知方向的深度调研 | `文献检索 difference-in-differences` ／ `精细检索 因果推断 双重差分 近 3 年` |
| 新领域摸底 / 找综述 | `文献检索 概览 高维统计推断` ／ `粗放检索 劳动经济学 综述` |
| 直接给出数量/年份 | `文献检索 regression discontinuity 找 20 篇 近 5 年` |
| 找方法论文 + 对应软件实现 | `文献检索 instrument variable Stata R 实现` |
| 查引用图谱 | `文献检索 synthetic control 查引用` |

**产出**：`<default_save_dir>\paper_search_{fine|broad}_<query>_<YYYYMMDD>.md`（结构见 §6）。

**步骤 4（推荐）· 用脚本一键跑完整链路**

不想让 Agent 逐步拼请求时，直接用随包脚本——它把"检索 → 去重 → 过滤 → 导出 → 校验"一次做完：

```powershell
cd $env:USERPROFILE\.minimax\skills\se_paper_search_shared\data\scripts

# 精细检索（近 3 年 / article / 10 篇）
python paper_search_client.py -q "difference-in-differences treatment effects" --pretty --verify

# 粗放检索（综述+工作论文 / 时间不限 / 15 篇）+ 方案 H 方向过滤
python paper_search_client.py -q "machine learning causal inference" --mode broad `
    --concept-pattern "causal|treatment[ ]effect|instrumental" --pretty --verify

# 先看不落盘（dry-run）+ 另存原始 JSON
python paper_search_client.py -q "panel data" --count 20 --dry-run --json-out raw.json
```

**交付前自检（必做，30 秒）**：

```powershell
python validate_output.py "<刚生成的 .md 路径>" --pretty   # DOI + arXiv ID 双反查，合并通过率 <95% 退出码为 2
```
（若上一步用了 `--verify`，此步已自动完成。）

### 0.1 常见困惑速答

| 困惑 | 答案 |
|---|---|
| 为什么只给关键词也能跑？ | mode 会在 §5.1 的规则下自动推断，默认精细。 |
| 为什么中文查不到？ | arXiv/OpenAlex/SS 全文检索只支持英文，改用英文关键词（本 skill 会自动提示）。 |
| 为什么这篇没有 DOI？ | 经济学工作论文常只有 arXiv ID 或 SSRN/NBER 编号；只有 arXiv ID 的会走 arXiv 反查，编号页需人工复核（§4.2）。 |
| 摘要为什么是 N/A？ | 出版商屏蔽，规则禁止用 AI 总结兜底，见 §4.1 / §9。 |
| 为什么第二次检索少了论文？ | 去重池生效，见 §5.2（arXiv-only 预印本暂不入池）。 |
| 每次跑多久？ | 精细约 1-2 分钟；粗放约 3-8 分钟（arXiv 礼仪限速 1 req/3s）。 |

## 1. 适用与不适用

**适用**

| 场景 | 推荐模式 | 触发关键词 |
|---|---|---|
| 已知方向深度调研、方法学比较、复现配套 | **精细（fine）** | 默认 / 深度 / 方法 / 创新 / 对比 / 复现 / 估计量 |
| 新方向立项、领域概览、综述与工作论文集合 | **粗放（broad）** | 概览 / 立项 / 综述 / 摸底 / survey / landscape / 全景 |
| 找原创研究、Quantitative Economics 类短文 | 精细 | article / letter / case |
| 找高被引综述、JEL Surveys and Reviews 类 | 粗放 | review / 高被引 / 综述 |
| 计量方法 + 软件实现（Stata/R/Python 配套论文） | 精细 | 软件 / 实现 / command / package |
| 引用图谱（references + cited by，一层） | 两者 | 引用 / 参考文献 |

**不适用**

- 非统计/经济学领域（化学/材料 → `qm_paper_search`；医学/生信/AI → `mbai_paper_search`）
- 全文下载、翻译、润色（下载与精读 → 用 `paper-deep-reading`）
- **投资建议、政策解读、市场预测**——本 skill 只罗列文献事实，见 §9 红线
- **官方统计数据本身**（GDP/CPI/失业率数值）——只检索研究这些数据的文献，数值以统计局/BEA/FRED 原发布方为准
- 已知方向但需要逐篇精读 → 用 `paper-deep-reading`（衔接见该 skill 的 `references/pipeline-orchestration.md`）

## 2. 检索参数

| 参数 | 精细默认 | 粗放默认 | 可选值 | 说明 |
|---|---|---|---|---|
| `type` | article-only | 综述+工作论文 | article / review / all / mixed | 文献类型过滤（broad 含 arXiv 预印本） |
| `count` | 10 | **15** | 1-100 | 返回篇数（粗放建议 10-25；>25 显著拉长耗时与限流风险） |
| `years` | 3 | 不限 | 1-10 / 不限 | 时间范围（年） |
| `arxiv_cats` | 全 10 类 | 同左 | econ.EM/GN/TH, stat.ME/AP/ML/TH/CO/OT, math.ST | arXiv 分类过滤（`--arxiv-cats`） |
| `journal_filter` | strict | loose | strict / loose | 顶刊（档位表）过滤严格度 |
| `sort_by` | relevance | time+citations | relevance / time / citations / time+citations | 排序方式 |
| `citation_graph` | on | on | on / off | 引用图谱开关（SS 提供） |
| `abstract_source` | ss | ss | ss / crossref / openalex / arxiv | 摘要主源（arXiv 条目自带 abstract） |
| `keywords_required` | true | true | true / false | 是否必须返回关键词 |
| `tldr` | optional | optional | required / optional / off | TLDR 开关（质量警告见 §4.3） |
| `concept_pattern` | — | *(空)* | regex | **粗放专属** 宽召回概念过滤（方案 H，详见 §3.3） |
| `min_concept_match` | — | 1 | 0-10 | **粗放专属** 宽召回最少命中概念数 |

> **粗放默认 15 篇口径沿用 qm v0.4.0 结论**：叠加宽召回与 arXiv 限速后单次已足够重，用户显式要更多再放宽。

## 3. 数据源（v0.1.0 主链）

### 3.1 主链与口径澄清

```
arXiv Export API            主检索渠道之一（econ.EM/econ.GN/econ.TH/stat.*/math.ST；
  ↓                          计量与统计理论的工作论文首发地；免 key；礼仪限速 1 req/3s）
OpenAlex                    覆盖主链（期刊发表文献发现 + concepts + OA 链接）
  ↓ 缺
Semantic Scholar            引用数 / TLDR / 引用图谱
  ↓ 缺
Crossref                    元数据权威（DOI 反查、卷期页校准）+ 独立检索
  ↓ 缺
返回 N/A
```

**口径澄清**：

- **发现层** = arXiv + OpenAlex + SS + Crossref 四源并联（脚本按此序尝试，单源失败自动降级并在报告头部声明）；
- **元数据权威 = Crossref**（卷/期/页以 Crossref 覆盖其他源）；
- **预印本权威 = arXiv**（有 journal_ref/DOI 则按正式发表处理，否则标 `[Preprint arXiv:xxxx.xxxxx]`）；
- SSRN / NBER 无合法公开 API：其论文若被 OpenAlex/Crossref 收录会正常出现，否则只能由用户给链接、skill 做结构化补全（不编造）；
- **不爬 Google Scholar**（理由与替代路径见 §3.4）；**不依赖 LLM 编造**（§4）。

### 3.2 调用契约（Agent 执行主体 · 沿用 qm v0.4.0 机制）

> **执行主体二选一**：
> 1. **首选**：直接跑 `shared/data/scripts/paper_search_client.py`——已按本表实现全部请求、合并、去重、导出与校验，`--pretty --verify` 一条命令交付成品。**能用脚本就用脚本**，避免 Agent 现场拼参数出错。
> 2. **兜底**：脚本不可用（无 Python / 需定制字段）时，由 **Agent（LLM runtime）** 按下表直接发起请求。
>
> 下表是**唯一权威的调用参数**。不要临场发明 endpoint 或字段名。

| 步骤 | 方法 / endpoint | 关键参数 | 需取用的字段 |
|---|---|---|---|
| ⓪ arXiv 检索 | `GET http://export.arxiv.org/api/query` | `search_query=all:"<query>" AND (cat:econ.EM OR ... OR cat:math.ST)`（短语 0 命中自动退回逐词 AND）、`max_results≤100`、Atom XML | `entry[]` → `id（arXiv ID）/ title / summary / published / authors[].name / arxiv:primary_category / arxiv:journal_ref / arxiv:doi / link[pdf]` |
| ① 主检索 | `GET https://api.semanticscholar.org/graph/v1/paper/search` | `query`、`limit`（≤100）、`year=YYYY-YYYY`、`fields=title,abstract,year,venue,publicationVenue,externalIds,authors,fieldsOfStudy,tldr,citationCount,referenceCount,openAccessPdf` | `data[]` → `title / abstract / externalIds.DOI / externalIds.ArXiv / authors[].name / tldr.text / citationCount` |
| ② 引用图谱 | `GET .../paper/{paperId}/references` 或 `/citations` | `limit=20`、`fields=title,year,venue,externalIds` | `data[].citedPaper / citingPaper` |
| ③ DOI 反查 | `GET https://api.crossref.org/works/{doi}` | `mailto=<你的邮箱>` | `message.title / author / container-title / volume / issue / page / publisher` |
| ④ 兜底检索 | `GET https://api.openalex.org/works` | `search=`、`per-page=`、`filter=type:review,from_publication_date:YYYY-MM-DD`、`mailto=` | `results[]` → `display_name / publication_year / doi / authorships / primary_location.source / abstract_inverted_index / concepts / cited_by_count / open_access.oa_url` |
| ⑤ 接收头 | 所有请求 | `User-Agent: se_paper_search_skill/0.1 (paper retrieval)`；SS/OpenAlex 有 key 时附 `x-api-key` / `api_key` 或 `mailto`；arXiv 无需 key 但**两次请求间隔 ≥3s** | — |

**字段还原注意**：

- OpenAlex 不返回 `abstract` 字段，需用 `abstract_inverted_index` 还原，还原后标来源 `openalex`。
- Crossref 多数条目无 abstract，只取元数据，不要拿它的模板 HTML 填摘要。
- arXiv 的 `journal_ref` 非空 → 已正式发表，期刊名取 `journal_ref`；为空 → 保持 `[Preprint]` 标记，**绝不**把 arXiv 分类当期刊。
- SS 的 `abstract`/`tldr` 可能为 null → 沿主链降级，不要编造。

### 3.3 宽召回机制（粗放专属 · 方案 H · 配套 `se_openalex_to_md.ps1`）

> **为什么需要**：粗放模式不筛方向时常见 200+ 候选，其中大量边缘文献；且 econ.EM 工作论文标题高度相似（"difference-in-differences" 一词会命中全部应用文章）。
>
> **方案 H 核心思路**：先宽召回（不筛方向），再用 `concept_pattern`（regex）做二次方向过滤——**纯本地操作，不增加 API 调用**。

**两步流程**：

1. **宽召回**：不带方向过滤，全量拉取 `count × 3-5` 条候选。
2. **方向过滤**：对每条候选的 `title + abstract + keywords` 用 `concept_pattern` 匹配，命中数 ≥ `min_concept_match` 才保留；不足时不补调 API，仅在报告里声明"过滤后 N 篇"。

**经济学典型 pattern**（示例，不构成推荐）：

| 方向 | concept_pattern 示例 |
|---|---|
| 因果推断新方法 | `causal\|treatment[ ]effect\|instrumental\|regression[ ]discontinuity` |
| 高维统计 | `high[\s-]?dimension\|lasso\|regulariz\|spars` |
| 金融机器学习 | `machine[ ]learning\|neural\|boosted\|forecast` |

**与 §2 参数的关系**：`count` = 过滤后最终输出数；实际 API 拉取数 = `count × 3-5`；arXiv 礼仪限速使粗放模式整体耗时更长（每次 arXiv 请求间隔 ≥3s）。

### 3.4 为什么不用 Google Scholar（及替代路径）— 沿用 qm v0.4.0

Google Scholar 无合法公开 API、ToS 禁止自动化抓取、结果随会话/地域变化不可复现，本 skill 一律不代抓。
六类 GS 常见需求（中文期刊、h-index、引用图谱、被引数、PDF 直达、相关文章推荐）的合规替代路径对照表见
[references/google-scholar-alternatives.md](references/google-scholar-alternatives.md)（含经济学专属的 RePEc/IDEAS、NBER、SSRN 指引）。

## 4. 强制反幻觉规则

### 4.1 字段级规则

| 字段 | 来源 | 缺失处理 |
|---|---|---|
| 标题 | API 原始 | 强制必须有 |
| 作者 | API 原始 | 缺则 `N/A`，**严禁 LLM 补全** |
| 年份 | API 原始 | 强制必须有 |
| 期刊 | API 原始（arXiv 条目取 journal_ref 或 `arXiv:<分类>`） | 缺则 `N/A` |
| 卷/期/页 | API 原始（Crossref 优先） | 缺则 `N/A` |
| DOI | API 原始 | 工作论文可无；**DOI 与 arXiv ID 至少其一**，两者皆无 → 标 `⚠️ 需人工复核` |
| arXiv ID | arXiv API / SS externalIds.ArXiv | 缺则 `N/A`，不推测 |
| 期刊档位 | 本地 `se_journal_tiers.json` | 缺则 `N/A`；表内无 IF 数值字段，**不得口头报 IF** |
| 摘要原文 | arXiv / SS / OpenAlex / Crossref | 缺则 `N/A` |
| 关键词 | API 原始（SS `fieldsOfStudy` / OpenAlex `concepts` / arXiv cats） | 缺则 `N/A`；OpenAlex concepts 必须标注"概念标签"，arXiv 分类标注"学科分类标签" |
| TLDR | Semantic Scholar `tldr` 字段 | AI 总结必须明确标"（AI 总结）"，且受 §4.3 约束 |

**禁止**：

- LLM 编造任何字段；snippet 截取当 abstract；推断页码/作者/卷期
- 把未检索到的"经典文献"凭印象补进名录（经济学尤易发生：Agent 倾向塞 AER 老文）
- 把 OpenAlex `concepts` / arXiv 分类直接当作论文"关键词"而不加标注
- 把工作论文标成正式发表、或省略其 `[Preprint]` 标记

### 4.2 代码化校验（DOI + arXiv ID 双反查）

§4.1 是**写给 AI 的规则**；`shared/data/scripts/validate_output.py` 是**可执行的校验层**：

```powershell
cd $env:USERPROFILE\.minimax\skills\se_paper_search_shared\data\scripts
python validate_output.py "C:\...\paper_search_broad_xxx_20260918.md" --pretty --threshold 0.95
```

| 行为 | 说明 |
|---|---|
| 输入 | 生成的 `.md` 名录（支持 glob 多文件） |
| 动作 | 抽取全部 DOI → Crossref 反查；抽取全部 arXiv ID → arXiv API 反查；逐条标 ✅ verified / ❌ not_found / ⚠️ error |
| 判定 | **合并通过率**（DOI+arXiv 共同分母）< `--threshold`（默认 0.95）→ 退出码 **2**，即"不应交付" |
| 盲区 | 既无 DOI 又无 arXiv ID 的条目（SSRN/NBER 编号页）**无法机器反查**——交付时此类条目必须人工复核 |
| 离线 | `--no-network` 仅做抽取自检；`--json-out` 输出机器可读报告 |

**交付纪律**：**任何 .md 名录在交付前必须跑一次 validate_output.py**；不达标时按 §7.1 话术如实告知，不要静默交付。

### 4.3 TLDR 字段质量警告

- SS 的 `tldr` 是第三方模型生成的压缩摘要，不是作者原文；对经济学长文（多定理/多设定）尤其容易失真。
- `tldr` 一律标注"（AI 总结）"，不得作为"关键发现/结论"的唯一依据。
- 论文里的**因果识别设定、估计量假设、数据区间**必须回到 `abstract` 原文核对；引用数值（弹性、处理效应大小）以原文为准。
- 用户说"只看 TLDR"时，明确提示"该字段可能遗漏识别假设与适用条件"——这在计量文献里是实质性风险，不是客套。
- 默认 `tldr=optional`；追求严谨时设 `tldr=off`。

## 5. 触发与去重

### 5.1 触发方式

**统一触发词**：`文献检索 X`（mode 由 skill 内部自动推断）。

**mode 推断规则**：

```python
# 伪代码（实际由 LLM 在执行时按规则匹配）
if re.search(r"概览|立项|综述|摸底|survey|landscape|全景|review| Handbook", query, re.I):
    mode = "broad"
elif re.search(r"深度|方法|创新|对比|复现|估计量|识别", query, re.I):
    mode = "fine"
else:
    mode = "fine"  # 默认精细
```

**显式覆盖**：用户说"精细检索 X" / "粗放检索 X" 可显式指定。

**auto-mode 推断示例**：

| Query | 推断 mode | 理由 |
|---|---|---|
| `文献检索 difference-in-differences` | fine | 默认 |
| `文献检索 概览 高维统计推断` | broad | 命中"概览" |
| `文献检索 立项 分布式面板计量` | broad | 命中"立项" |
| `文献检索 综述 因果推断机器学习中 handbook` | broad | 命中"综述/handbook" |
| `文献检索 双重差分 异质处理效应 对比` | fine | 命中"对比" |
| `文献检索 合成控制 复现` | fine | 命中"复现" |

### 5.2 去重机制

- 数据源：`se_paper_search_shared/data/seen_papers.json`
- `topic_id` 前缀：精细 `fine_<topic>`、粗放 `broad_<topic>`，两个前缀并存识别
- 同 topic 重复检索自动跳过 `seen_dois`
- **v0.1.0 已知限制**：池以 DOI 为主键——只有 arXiv ID 的预印本不入池，跨检索可能重复出现（报告会如实展示，v0.2 候选改进）
- 显式命令：新方向 / 清空当前方向记忆 / 清空全部记忆 / 全局去重

**跨 topic 去重策略（沿用 qm v0.4.0 规则）**：

| 情形 | 默认行为 | 用户可覆盖 |
|---|---|---|
| 同 topic 重复检索 | 跳过 `seen_dois` | — |
| 新 topic 与已有 topic 共享 ≥1 个核心关键词（如"causal"/"面板"） | **跨 pool 合并去重**（默认开启） | "本方向不去重" |
| 无共同关键词 | 不去重（视为真新方向） | "全局去重" |
| 用户显式说"全局去重" | 全局去重 | "清空全部记忆" |

- `seen_papers.json` 结构按 `topic_id` 分组；"跨 pool 去重"是**读取时合并**，不破坏历史数据。
- 报告末尾必须注明："跨主题去重跳过 N 篇（来自 pool: X, Y）"。

## 6. 输出格式

输出文件命名：

- 精细：`paper_search_fine_<query>_<YYYYMMDD>.md`
- 粗放：`paper_search_broad_<query>_<YYYYMMDD>.md`

保存路径：`shared/data/user_prefs.json` 的 `default_save_dir`。

### 6.1 统一输出约定（与 paper-deep-reading 对齐）

跨 skill 的**同一套约定**，便于"检索结果 → 精读报告 → 知识库存档"流水线串联：

| 约定 | 规则 |
|---|---|
| 元信息块 | 置于文件开头，字段顺序：查询/主题 → 时间范围 → 文献类型 → 数据源 → 检索时间 → 模式；**每字段一行 `**字段**：值`** |
| DOI 形式 | 一律 `[10.xxxx/yyy](https://doi.org/10.xxxx/yyy)` 可点击链接；arXiv 形式 `[arXiv:2309.12345](https://arxiv.org/abs/2309.12345)` |
| 期刊标记 | `（Tier 1 / ⭐ Top / [Preprint …] / 🔒 付费墙）`，档位口径见 `se_journal_tiers.json`（**无 IF 数值**） |
| 来源标注 | 【原文】= API 原始；【AI分析】= 归纳（含 TLDR）；【推测】= 不确定推断 |
| 术语 | 经济/统计术语遵循"首次出现给中英对照、全文译名统一"（如 DID=双重差分、IV=工具变量） |
| 结论 | 不输出"决策建议/投资含义"，仅陈述检索事实 + 可核查链接 |

### 6.2 文件结构

```markdown
# 文献检索结果（精细模式）/（粗放模式 · 综述与工作论文为主）

**查询**：<query>
**研究方向**：<topic_name>
**时间范围**：YYYY–YYYY（精细）/ 不限（粗放）
**文献类型**：article-only（精细）/ 综述+工作论文（粗放）
**数据源**：arXiv, OpenAlex, Semantic Scholar, Crossref（实到源列表）
**检索时间**：<timestamp>
**模式**：fine / broad

## 📋 速览（10 篇 / 15 篇）

| # | 标题 | 作者 | 年份 | DOI |
|---|------|------|------|-----|
| 1 | [Title](#title-1) | Author1, Author2, ... | 2025 | [10.xxxx](https://doi.org/10.xxxx) |
| 2 | ... | ... | ... | ... |

> ⭐ Tier-1 X 篇 · [Preprint] X 篇 · 已跳过重复 X 篇（跨主题去重 X 篇）· 方向过滤剔除 X 篇

---

## 📚 详细条目

### # 1 <a id="title-1"></a> Title
- **作者**：...（仅来自 API）
- **年份**：YYYY
- **期刊**：<Name>（Tier 1 / ⭐ Top）或 arXiv:econ.EM（工作论文）
- **影响因子**：N/A（档位制，见 §9）
- **DOI**：[10.xxxx](https://doi.org/10.xxxx)
- **arXiv**：[arXiv:2309.12345](https://arxiv.org/abs/2309.12345)
- **卷/期/页**：v(i): pp 或 —
- **关键词**：k1, k2, ...（API 原始；OpenAlex 须标"概念标签"）
- **摘要原文**：<完整 abstract>
- **TLDR**（AI 总结）：<一句话>
- **标记**：[Preprint arXiv:xxxx.xxxxx] · [OA 全文](...) · 来源: arxiv, ss

#### 📎 引用格式
<details><summary>BibTeX</summary> ... </details>
<details><summary>APA 7</summary> ... </details>
<details><summary>GB/T 7714</summary> ... </details>
<details><summary>RIS</summary> ... </details>

---

### # 2 ...
```

**字段说明**：核心字段 = 作者 / 年份 / 期刊 / DOI / arXiv / 卷期页 / 关键词 / 摘要原文 / TLDR / 标记。4 种引用格式按学术规范折叠。工作论文的 BibTeX 用 `@misc`/`@unpublished` 时仍须保留 `[Preprint]` 语义（脚本输出 `@article` 骨架 + DOI/arXiv 字段，用户按目标期刊要求微调）。

### 6.3 交付前自检清单

- [ ] 已跑 `validate_output.py` 且合并通过率 ≥ 0.95（否则按 §7.1 如实告知）
- [ ] 元信息块字段齐全且顺序正确（§6.1）
- [ ] 所有 DOI / arXiv ID 均为可点击链接
- [ ] 每个工作论文条目都有 `[Preprint]` 标记，未被写成正式发表
- [ ] 跳过的重复条目数已在速览行注明（含跨主题去重来源 pool）
- [ ] 缺失字段统一写 `N/A`，无 LLM 补全痕迹；无编造 IF
- [ ] 摘要为完整 abstract 原文，非 snippet 截取

## 7. 失败处理

| 场景 | 行为 |
|---|---|
| arXiv 超时/5xx | 重试 ≤3 次（间隔递增）→ 降级到 OpenAlex 起下游链 |
| SS API 限流（429） | 退避重试 1 次 → 切 Crossref/OpenAlex |
| 中文 query 0 命中 | 明确提示"arXiv/OpenAlex/SS 仅支持英文"，给英译建议后重试 |
| DOI 查无 | 走兜底链；若命中 arXiv ID 则改走 arXiv 反查 |
| 全部源缺 abstract | 标记 `摘要：N/A`，不编造 |
| 付费墙 | 保留条目，标 `🔒 付费墙`；有 OA 版本（arXiv）则附 OA 链接 |
| 全部源失败 | 返回兜底提示 |
| 非统计/经济领域 | 二次确认（§7.1） |

### 7.1 面向用户的错误提示模板

错误处理必须**对用户可见**，不能只写日志或静默降级；也不用一问一答卡死无人值守流程：

| 场景 | 用户可见输出（一行即可） | 自动动作（不打断用户） |
|---|---|---|
| API key 401/403 | "⚠️ 配置的 {source} key 已失效，已自动回退无 key 模式。更新：`Set-ApiKey.ps1 -Provider {source} -Key <NEW>`" | 回退并继续 |
| 429 限流 | "⏳ {source} 限流，已退避 30s 后重试（第 N/3 次）" | backoff 重试 |
| 某源整体不可用 | "⚠️ {source} 当前不可用（{原因}），已改用 {fallback}；本次结果按 {fallback} 口径返回" | 切兜底源 |
| 全部源失败 | "❌ 全部数据源失败：<每源一行原因>。请检查网络或稍后重试；也可改用 web_search 兜底（覆盖率会下降）" | 停止 |
| 中文查询 0 命中 | "⚠️ 检索源仅支持英文，建议改用 '{英文建议}' 重试" | 给建议，不硬翻 |
| 非经济/统计主题 | "「X」看起来属于 {领域}，本 skill 专精统计/经济学。仍按经济口径检索吗？（Y/N）；或改用 qm/mbai_paper_search" | **唯一允许的交互** |
| 校验不达标 | "⚠️ 交付前校验：N 个标识符中 M 个未通过反查，已标 ❌，请人工复核这些条目" | 标记并交付 |

> 原则：**能自动降级就自动降级**（附一条 ⚠️ 说明），只在"必须由用户决策"时才提问。

## 8. 数据维护

- 期刊档位：`shared/data/se_journal_tiers.json`（**编辑共识口径**，非官方分级；修订需注明依据，`if_2024` 字段一律置 null 以免过时失真）
- 去重池：`shared/data/seen_papers.json`（topic_id 加 `fine_` / `broad_` 前缀；跨 pool 去重见 §5.2）
- 用户偏好：`shared/data/user_prefs.json`
- 调用日志：`shared/data/api_logs.json`（本地，90 天自动清理）
- 路径策略：首次调用询问，后续使用默认，用户说"换路径"再询问
- 数据更新历史：`shared/data/UPDATE_NOTES.md`（只增不删）

## 9. 法律约束与领域红线

核心红线速记：
- **不构成投资建议**：输出仅为文献名录；任何政策/市场相关检索结果不附"应买入/规避/利好"类判断。
- **不替代官方统计发布**：涉及 GDP/CPI/就业等数据口径的文献可罗列，数值本身指向统计局 / BEA / FRED 原发布方。
- **工作论文必须显式标注**：`[Preprint]` 未过同行评审，不得作为既定结论引用。
- 元数据（标题/作者/DOI/摘要/引用数）可存；**付费墙后 PDF 禁存、不批量镜像、不绕付费墙抓全文、不转售**；arXiv 全文可链到官方 OA PDF，按单篇 license 使用。
- `api_keys.local.json`、`seen_papers.json`、搜索记录只存本机；**严禁分享他人 key、严禁把用户搜索内容上传第三方**。
- 禁止用于代写、伪造数据、挑选性引用（p-hacking 式"只留显著结果文献"属实质性学术不端，名录必须按检索事实完整交付）。

各数据源协议表、档位口径说明、引用规范、适用法律全文见
[references/legal-compliance.md](references/legal-compliance.md)。

## 10. API 限制约束

关键约束（执行检索时必须遵守）：
- **arXiv Export API：礼仪限速 1 req/3s**（脚本已内置；Agent 手工调用同样必须 sleep ≥3s），单次 `max_results ≤ 2000`（本 skill 封顶 100）。
- OpenAlex：无 key 5 req/s、带 key 50 req/s；必须带 User-Agent + `mailto=` 或 key。
- Crossref：建议带 `mailto`（polite pool 50 req/s）。SS：带 key 100 req/min，共享 IP 易 429。
- 429 → 1s/5s/30s 退避重试 ≤3 次；401/403 → 提示换 key 并回退无 key；5xx/网络 → 切兜底源。
- **粗放模式含 arXiv 重试链时耗时明显变长**，两轮粗放检索建议间隔 ≥30s。
- 调用日志只写本地 `shared/data/api_logs.json`，90 天自动清理。

完整限流表、错误码处理、健康度监控阈值见 [references/api-limits.md](references/api-limits.md)。

## 11. API key 管理

原则：**团队共享代码、key 只存各自本机**。读取顺序 `api_keys.local.json` → 环境变量 → 无 key。
**本 skill 零 key 可完整跑通**（arXiv/Crossref 免 key），key 只影响 OpenAlex/SS 限速。
- 首次配置：`se_paper_search_setup.ps1`；日常管理：`Set-ApiKey.ps1 -List|-Key|-Validate|-Remove|-EnvVar`。
- 可选 `mailto_for_openalex`（api_keys.local.json）：OpenAlex/Crossref polite pool 联系方式，提升限速并避免误封。
- ❌ 严禁把 key 提交 git、在聊天/邮件/截图分享；key 失效（401/403）立即更新。
- 出版商屏蔽 abstract → 标 `N/A（出版商屏蔽，到 DOI 原页拉）`，**不用 AI 总结兜底**。

完整命令示例与 key 申请入口见
[references/api-key-management.md](references/api-key-management.md)。

## 12. 文件清单

```
se_paper_search/
├── SKILL.md          (本文件，v0.1.0)
├── CHANGELOG.md      (历次修订记录)
├── README.md         (用户视角的触发/参数/FAQ)
├── assets/
│   └── eval-checklist.md   (检索评测：gold query 集 + 双反查校验阈值)
└── references/
    ├── google-scholar-alternatives.md  (§3.4 全文 + RePEc/NBER/SSRN 指引)
    ├── legal-compliance.md             (§9 全文)
    ├── api-limits.md                   (§10 全文)
    └── api-key-management.md           (§11 全文)

se_paper_search_shared/data/
├── api_keys.template.json     (团队共享，commit)
├── api_keys.local.json        (个人本地，gitignore)
├── se_journal_tiers.json      (经济学/统计/金融期刊档位表，无 IF)
├── seen_papers.json           (去重池，topic_id 分组，gitignore)
├── user_prefs.json            (default_save_dir 等偏好，gitignore)
├── user_prefs.template.json
├── api_logs.json              (本地调用日志，90 天清理，gitignore)
├── README_API_KEYS.md
├── UPDATE_NOTES.md
├── .gitignore
└── scripts/
    ├── _lib_paths.ps1               (共享路径解析，env: SE_PAPER_SHARED_DIR)
    ├── Set-ApiKey.ps1               (单 key 管理)
    ├── se_paper_search_setup.ps1    (首次配置向导)
    ├── se_openalex_to_md.ps1        (JSON → Markdown 转换 + 方案 H 过滤，遗留工具)
    ├── paper_search_client.py       (★ 零依赖四源检索客户端 · 一键交付)
    └── validate_output.py           (★ 交付前 DOI + arXiv ID 双反查校验)
```

### 12.1 `paper_search_client.py` 速查

| 能力 | 说明 |
|---|---|
| 多源检索 | arXiv（免 key 主渠道）→ OpenAlex → SS → Crossref，源失败自动降级并打印告警 |
| 合并去重 | DOI 优先、无 DOI 回退标准化标题；Crossref 覆盖卷/期/页；arXiv ID 字段级合并 |
| 方案 H | `--concept-pattern` + `--min-concept-match`，纯本地过滤不额外发请求 |
| 类型口径 | fine=article-only；broad=综述+工作论文（经济学专属语义，见 §2/§3.1） |
| 去重池 | 自动读写 `seen_papers.json`（`fine_*`/`broad_*` 前缀）；默认跨 topic 合并去重；`--no-dedup`/`--no-cross-topic`/`--global-dedup` 可覆盖 |
| 导出 | §6.2 规定的 Markdown（元信息块 + 速览 + 详细条目 + BibTeX / APA 7 / GB/T 7714 / RIS） |
| 校验 | `--verify` 复用 `validate_output.py` 双反查，合并通过率 <95% 时退出码 4 |
| 其它 | `--arxiv-cats`（分类裁剪）、`--dry-run`、`--json-out`、`--pretty` / `--quiet` |

退出码：`0` 成功；`2` 全部数据源失败；`3` 参数错误；`4` 校验未达标。

## 13. 维护

**当前版本：v0.1.0**（与 frontmatter 一致）。

| 版本 | 日期 | 重点变更 |
|---|---|---|
| **v0.1.0** | 2026-09-18 | 统计经济学 skill 首发：由 qm_paper_search v0.4.1 派生孪生改造——arXiv 主渠道（短语 0 命中自动退逐词 AND）、validate_output 双反查（DOI+arXiv ID）、期刊档位表替代 CAS 分区（IF 置空）、SSL 证书链兜底、broad 模式纳入工作论文、经济领域红线（§9） |

**血缘说明**：本 skill 与 `qm_paper_search`（化学）、`mbai_paper_search`（医学）同构，共享层结构一致但**数据完全独立**；修共享逻辑类 bug 时三个孪生都要各自检查（用户已决定不做代码合并）。

**后续候选（未排期）**：seen 池支持 arXiv-ID 键；SSRN/NBER 编号页的半自动反查；RePEc handle 富化。
