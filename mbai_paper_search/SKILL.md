---
name: mbai_paper_search
version: 0.4.0
description: |
  医学 / 生物信息学 / AI 学术文献检索（统一 skill，fine/broad 双模式，mode 由查询关键词自动推断；qm_paper_search 化学版的同源孪生）。
  触发词："文献检索 X"；显式覆盖："精细检索 X" / "粗放检索 X"。粗放默认触发词：概览 / 立项 / 综述 / 摸底 / survey / landscape / 全景 / 指南；未命中则默认精细。
  精细默认：article-only（含 Letter/Case Report）、10 篇、近 3 年；粗放默认：review-only（系统综述/Meta/指南）、15 篇、时间不限、含方案 H 宽召回。
  主链：OpenAlex / PubMed E-utilities → Europe PMC → Semantic Scholar → Crossref；预印本并行 bioRxiv/medRxiv/arXiv；扩展字段：MeSH / 证据等级 / 临床试验注册号。
  反幻觉红线：元数据 only from API，缺则 N/A；交付前必须用 scripts/validate_output.py 做 DOI + PMID 双反查校验。
  医学红线：不替代临床判断、不输出用药/诊疗建议、预印本必须显式标注、PII 硬拦截。
  执行：优先运行 scripts/paper_search_client.py（五源合并 + 去重 + Markdown 导出 + --verify）；首次使用先按 §0 Quickstart 配置。
  不适用：化学文献检索 → qm_paper_search；统计/计量经济/经济学文献检索 → se_paper_search；论文 PDF 深度阅读 → paper-deep-reading。
---

<!-- 历次修订记录（原本文件顶部 HTML Modification Log 注释块）已迁移至 ./CHANGELOG.md -->

# mbai_paper_search — 医学 / 生物信息学 / AI 学术文献检索 v0.4.0

> 本 skill 是 `qm_paper_search`（化学）的**同源孪生版**，主题切换为 **Medicine · Bioinformatics · Artificial Intelligence**。
> 参数框架、反幻觉规则、引用规范、API 限流约束、key 管理流程与 qm 系列**同构**；
> 差异在数据源（PubMed / Europe PMC / 预印本并行）、字段扩展（MeSH / 证据等级 / 临床试验注册号）与合规约束（医学红线）。

## 0. Quickstart（首次使用 3 步）

**步骤 1 · 配 key（可选，1 分钟）**

```powershell
cd $env:USERPROFILE\.minimax\skills\mbai_paper_search_shared\data\scripts
.\mbai_paper_search_setup.ps1          # 按提示输入 OpenAlex / Semantic Scholar / NCBI key（可全部留空跳过）
.\Set-ApiKey.ps1 -List                 # 查看当前 key 状态
```

| key | 作用 | 申请 |
|---|---|---|
| OpenAlex | polite pool + 更高限流 | https://openalex.org/users/sign_up |
| Semantic Scholar | TLDR 字段 + 引用数 | https://www.semanticscholar.org/product/api |
| NCBI | PubMed 3 req/s → 10 req/s | https://www.ncbi.nlm.nih.gov/account/settings/ |
| Europe PMC email | 礼貌标识（无 key 概念，填邮箱即可） | — |

**步骤 2 · 确认输出目录**

首次检索会问一次"默认保存路径"，写入 `shared/data/user_prefs.json` 的 `default_save_dir`；改路径说"换路径"。

**步骤 3 · 直接说人话触发**

| 你想做的事 | 就这么说 |
|---|---|
| 已知方向深度调研 | `文献检索 PD-1 抑制剂 非小细胞肺癌` ／ `精细检索 scRNA-seq 空间转录组` |
| 新领域摸底 / 找综述 | `文献检索 概览 医学大模型` ／ `粗放检索 肿瘤免疫治疗 综述` |
| 临床证据追溯 | `文献检索 阿兹海默 单抗 RCT` ／ `精细检索 ctDNA 早筛 队列` |
| 直接给出数量/年份 | `文献检索 AlphaFold 找 20 篇 近 5 年` |

**步骤 4（推荐）· 用脚本一键跑完整链路**

```powershell
cd $env:USERPROFILE\.minimax\skills\mbai_paper_search_shared\data\scripts

# 精细：近 3 年 / article / 10 篇，导出后自动做 DOI + PMID 校验
python paper_search_client.py -q "PD-1 inhibitor NSCLC" --pretty --verify

# 粗放：综述为主 / 时间不限 / 15 篇 + 方案 H 方向过滤 + 证据等级偏好
python paper_search_client.py -q "medical large language model" --mode broad `
    --evidence Meta优先 --concept-pattern "large language model|clinical|diagnos" --pretty --verify

# 只看 PubMed + OpenAlex，纳入预印本，试跑不落盘
python paper_search_client.py -q "spatial transcriptomics" --sources pubmed,openalex `
    --include-preprint --dry-run --json-out raw.json
```

**交付前自检（必做，30 秒）**

```powershell
python validate_output.py "<刚生成的 .md 路径>" --pretty     # 校验率 <95% 退出码为 2
```
（若上一步用了 `--verify`，此步已自动完成。）

### 0.1 常见困惑速答

| 困惑 | 答案 |
|---|---|
| 为什么医学主题还查 OpenAlex？ | OpenAlex 覆盖医学/AI/生信全领域且免费；PubMed 是**权威补充**（MeSH + 证据等级），二者合并最优。 |
| 为什么综述里混进了 Editorial？ | 规则禁止把 Editorial / Letter 标成"综述"，会被过滤或标 `[非综述，仅参考]`（§7）。 |
| 摘要为什么是 N/A？ | 出版商屏蔽，规则禁止 AI 兜底（§4.1 / §11.6）。 |
| 预印本可信吗？ | **未经同行评审**，一律标 `[Preprint]`，不得参与临床结论（§9.7）。 |
| 我能问"该用什么药"吗？ | **不能**——本 skill 不输出用药/诊疗建议，会引导你就医（§9.7）。 |
| 每次跑多久？ | 精细约 1-3 分钟；粗放（含宽召回 + 引用图谱）约 5-10 分钟。 |

## 1. 适用与不适用

**适用**

| 场景 | 推荐模式 | 触发关键词 |
|---|---|---|
| 已知方向深度调研、机制/通路、单篇分析、方法学比较 | **精细（fine）** | 默认 / 深度 / 机制 / 通路 / 算法 / 对比 / 复现 |
| 新方向立项、领域概览、综述集合、临床指南摸底 | **粗放（broad）** | 概览 / 立项 / 综述 / 摸底 / survey / 全景 / 指南 |
| 找原创研究、Letter、Case Report、Brief Communication | 精细 | article / letter / case |
| 找系统综述 / Meta 分析 / 临床实践指南 | 粗放 | systematic review / meta / guideline / Cochrane |
| 引用图谱（references + cited by，一层） | 两者 | 引用 / 参考文献 |

**不适用**

- 非医学 / 非生物信息学 / 非 AI 领域（纯化学 → `qm_paper_search`；统计 / 计量经济 / 经济学 → `se_paper_search`；其他学科请用对应 skill）
- 全文下载、翻译、润色、本地 PDF 管理（精读 → `paper-deep-reading` 或对应领域阅读 skill）
- **临床诊疗决策**（明确禁止，见 §9.7）

## 2. 检索参数

| 参数 | 精细默认 | 粗放默认 | 可选值 | 说明 |
|---|---|---|---|---|
| `type` | article-only | review-only | article / letter / case-report / review / systematic-review / meta-analysis / guideline / all / mixed | 文献类型（医学细化） |
| `count` | 10 | **15** | 1-100 | 返回篇数（粗放建议 10-25；>25 显著拉长耗时） |
| `years` | 3 | 不限 | 1-10 / 不限 | 时间范围（年） |
| `journal_filter` | strict | loose | strict / loose | 顶刊过滤严格度 |
| `sort_by` | relevance | time+citations | relevance / time / citations / time+citations | 排序方式 |
| `citation_graph` | on | on | on / off | 引用图谱开关 |
| `abstract_source` | openalex | openalex | openalex / pubmed / europe_pmc / semantic_scholar / crossref | 摘要主源 |
| `keywords_required` | true | true | true / false | 是否必须返回关键词（含 MeSH） |
| `tldr` | optional | optional | required / optional / off | TLDR 开关（质量警告见 §4.3） |
| `include_preprint` | on | on | on（当前实现无排除开关） | bioRxiv / medRxiv / arXiv / Europe PMC PPR 恒纳入结果并强制显式标 `[Preprint]`（红线见 §9.7）；CLI `--include-preprint` 仅作显式声明 |
| `mesh_required` | optional | optional | required / optional / off | 是否优先返回 PubMed MeSH 主题词 |
| `evidence_level` | optional | optional | **RCT优先 / Meta优先 / 队列优先 / 不限** | 临床证据等级偏好（医学专属） |
| `prefer_journal` | — | auto | auto / Nature Reviews / Cochrane / Annual Review / Lancet / NEJM | 综述来源偏好（粗放专属） |
| `clinical_scope` | — | optional | pediatric / adult / geriatric / global / 不限 | 临床范围（粗放专属） |
| `concept_pattern` | — | *(空)* | regex | **粗放专属** 宽召回概念过滤（方案 H，详见 §3.3） |
| `min_concept_match` | — | 1 | 0-10 | **粗放专属** 宽召回最少命中概念数 |

> **粗放默认 count 调整说明（v0.4.0）**：v0.2 默认 25 篇，叠加引用图谱后单次可达 250 req，实测 10+ 分钟，对立项摸底过重。v0.4.0 收敛为 **15 篇**，用户显式说"找 30 篇"时再放宽。

## 3. 数据源与调用契约

### 3.1 主链与数据源选择

```
OpenAlex API                      主检索源（覆盖医学 / AI / 生信全领域，免费，2.5 亿+）
  ↓ 缺 MeSH / 证据等级 / 权威性不足
PubMed E-utilities                生物医学权威（MEDLINE 3200 万+；MeSH + Publication Type）
  ↓ 缺 / 非生物医学
Europe PMC                        开放获取 + 预印本 + 指南（多出 OA 全文与 PPR 预印本）
  ↓ 缺（尤其 AI/ML 预印本）
Semantic Scholar                  AI/ML 覆盖好 + TLDR + 引用数
  ↓ 缺
Crossref                          元数据权威（DOI 反查 / 卷期页 / 作者）
  ↓ 缺
返回 N/A
```

**预印本并行通道**：bioRxiv / medRxiv（生命科学 + 临床）、arXiv（cs.AI / cs.LG / q-bio）。

**主题 → 主源选择策略**

| 主题 | 主源 | 备选 |
|---|---|---|
| 临床医学（疾病、药物、试验） | **PubMed** | OpenAlex → Europe PMC |
| 基础医学（机制、信号通路） | **PubMed** | OpenAlex → Europe PMC |
| 生物信息学（算法、组学工具） | **OpenAlex** | PubMed → Semantic Scholar |
| 机器学习 / 深度学习（通用方法） | **Semantic Scholar** | OpenAlex → arXiv |
| 医学 AI（影像、诊断、LLM 临床应用） | **PubMed** | OpenAlex → Semantic Scholar |
| 单细胞 / 空间组学 | **OpenAlex**（预印本并行） | PubMed → bioRxiv |

**口径澄清（v0.4.0）**：v0.2 的 fine/broad 各自声称"OpenAlex 主源"与"OpenAlex + PubMed 主源"，口径不一。
现统一为：**主检索源按上表按主题选择（医学类默认 PubMed 优先）**；**元数据权威 = Crossref**；**覆盖兜底 = Europe PMC / Semantic Scholar**。

**不爬 Google Scholar**（理由与替代路径见 §3.4）。**不依赖 LLM 编造**（§4）。

### 3.2 调用契约（执行主体 · v0.4.0 新增）

> **执行主体二选一**：
> 1. **首选（推荐）**：跑 `shared/data/scripts/paper_search_client.py`——五源检索、合并去重、MeSH/证据等级抽取、
>    seen_pools 读写、Markdown 导出、DOI+PMID 校验全部内置，`--pretty --verify` 一条命令交付成品。
> 2. **兜底**：脚本不可用（无 Python / 需定制字段）时，由 **Agent（LLM runtime）** 按下表直接发起请求。
>
> 下表是**唯一权威的调用参数**。请不要临场发明 endpoint 或字段名。

| 步骤 | 方法 / endpoint | 关键参数 | 需取用的字段 |
|---|---|---|---|
| ① 主检索（OpenAlex） | `GET https://api.openalex.org/works` | `search=`、`per-page=`、`filter=type:review,from_publication_date:YYYY-MM-DD,is_paratext:false`、`sort=relevance_score:desc`、`mailto=`、`api_key=` | `results[]` → `display_name / publication_year / doi / ids.pmid / authorships[].author.display_name / primary_location.source.display_name / biblio.volume,issue,first_page,last_page / abstract_inverted_index / concepts[] / cited_by_count / open_access.oa_url / type` |
| ② 主检索（PubMed） | `GET https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi` → `GET .../efetch.fcgi` | esearch：`db=pubmed`、`term=`、`retmax=`、`retmode=json`、`sort=relevance`、`tool=mbai_paper_search`、`email=`、`api_key=`；efetch：`db=pubmed`、`id=<逗号分隔 PMID>`、`retmode=xml` | XML：`MedlineCitation/PMID`、`Article/ArticleTitle`、`Article/Abstract/AbstractText`（含 `Label`）、`AuthorList/Author/LastName,ForeName`、`Journal/Title,ISOAbbreviation`、`JournalIssue/Volume,Issue,PubDate/Year`、`Pagination/MedlinePgn`、`ELocationID[@EIdType='doi']`、`ArticleIdList/ArticleId[@IdType='pmc']`、`MeshHeadingList/MeshHeading/DescriptorName`、`PublicationTypeList/PublicationType` |
| ③ 综述补充（Europe PMC） | `GET https://www.ebi.ac.uk/europepmc/webservices/rest/search` | `query=`、`format=json`、`pageSize=`、`resultType=core`、`email=` | `resultList.result[]` → `title / abstractText / pubYear / journalTitle / journalVolume / issue / pageInfo / doi / pmid / authorString / pubTypeList.pubType / meshHeadingList.meshHeading[].descriptorName / citedByCount / isOpenAccess / source(PPR=预印本)` |
| ④ AI/ML 补充（SS） | `GET https://api.semanticscholar.org/graph/v1/paper/search` | `query=`、`limit=`、`year=YYYY-YYYY`、`fields=title,abstract,year,venue,externalIds,authors,fieldsOfStudy,tldr,citationCount,publicationTypes` | `data[]` → `paperId / title / abstract / year / venue / externalIds.DOI,PubMed / authors[].name / tldr.text / citationCount` |
| ⑤ 元数据权威（Crossref） | `GET https://api.crossref.org/works/{doi}` 或 `?query.bibliographic=` | `mailto=` | `message.title / author / container-title / volume / issue / page / published.date-parts` |
| ⑥ 预印本 | bioRxiv/medRxiv 公开 API、`https://arxiv.org/abs/<id>` | 按标题检索 | 标题 / 作者 / 年份 / 预印本服务器（**必须标 `[Preprint]`**） |
| ⑦ 请求头 | 所有请求 | `User-Agent: mbai_paper_search_skill/0.4 (paper retrieval)`；`tool=mbai_paper_search`（PubMed 必需）+ `email=`；有 key 时附 `api_key` / `x-api-key` | — |

**字段还原注意**：

- OpenAlex **不返回 `abstract`**，需用 `abstract_inverted_index`（`{词: [位置...]}`）还原，还原后标来源 `openalex`。
- PubMed XML 的 `AbstractText` **可能多段**（如 `BACKGROUND:` / `METHODS:` / `RESULTS:`），需按 `Label` 拼接，不要只取第一段。
- Crossref 多数条目无 abstract；其 `abstract` 字段常为出版商模板 HTML，仅在长度 ≥200 字符时使用。
- Semantic Scholar 的 `abstract` 可能为 `null`；`tldr` 为 AI 生成（§4.3）。

### 3.3 宽召回机制（粗放专属 · 方案 H）

> **为什么需要宽召回**：粗放模式默认 `type=review-only` + `years=不限`，直出结果常返回 200+ 条候选，其中大量是与查询方向无关的"边缘综述"。
>
> **方案 H**：先宽召回（不筛方向），再用 `concept_pattern`（regex）做二次方向过滤。

1. **宽召回**：不带方向过滤，全量拉取 `count × 3-5` 条候选。
2. **方向过滤**（脚本层，**不增加 API 调用**）：对每条候选的 `title + abstract + keywords + MeSH` 做 regex 匹配；命中数 ≥ `min_concept_match` 才保留；不足时不补调 API，仅在报告里声明"过滤后 N 篇，命中原 query 核心 M 篇（M < N）"。

```powershell
python paper_search_client.py -q "medical large language model" --mode broad `
    --concept-pattern "large language model|LLM|clinical|diagnos" --min-concept-match 2 --pretty
```

**与 §2 参数的关系**：`count` = **最终输出数**（过滤后）；实际 API 拉取数 = `count × 3-5`（count=15 时约 45-75 条候选）。

### 3.4 为什么不用 Google Scholar（及替代路径）

GS 无官方 API、ToS 禁止自动化抓取、结果随会话/地域变化不可复现，本 skill 一律不代抓。
七类 GS 常见需求（中文医学期刊、h-index、引用图谱、被引数、PDF 直达、证据等级、相关推荐）的
合规替代路径对照表见 [references/google-scholar-alternatives.md](references/google-scholar-alternatives.md)。

### 3.5 综述类型识别（PubMed Publication Type 优先）

| 类型 | PubMed 标识 | 说明 |
|---|---|---|
| Review | `Review` | 综述（泛指；未达系统综述标准时在报告中标 `Narrative Review`） |
| Systematic Review | `Systematic Review` | 系统综述（Cochrane 风格） |
| Meta-Analysis | `Meta-Analysis` | Meta 分析（合并统计） |
| Scoping Review | `Review`（不细分，关键词过滤） | 范围综述 |
| Clinical Practice Guideline | `Practice Guideline` | 临床实践指南 |
| Consensus | `Consensus Development Conference` | 共识声明 |
| Editorial / Comment | `Editorial` / `Comment` | **不计入综述**，仅参考 |
| Annual Review / Nature Reviews | ISSN 匹配系列刊 | 年评 / 自然综述系列 |

**Cochrane Library**：本 skill 不直连（付费 + 限流严），通过 PubMed `Publication Type: Systematic Review` + Europe PMC 开放获取版兜底；报告中标注 `Cochrane` 时需在原文查证 **PRISMA 流程图 / 检索策略 / 纳入排除标准**。

## 4. 强制反幻觉规则

### 4.1 字段级规则

| 字段 | 来源 | 缺失处理 |
|---|---|---|
| 标题 | API 原始 | 强制必须有 |
| 作者 | API 原始 | 缺则 `N/A`，**严禁 LLM 补全** |
| 年份 | API 原始 | 强制必须有 |
| 期刊 | API 原始 | 缺则 `N/A` |
| 卷/期/页 | API 原始（Crossref 优先） | 缺则 `N/A` |
| DOI | API 原始 | 强制必须有；**预印本可缺**，但必须保留源链接 |
| PMID | PubMed / SS externalIds / OpenAlex ids | 缺则 `N/A` |
| 影响因子 | 本地 `cas_journal_zones.json` | 缺则 `N/A` |
| 摘要原文 | OpenAlex / PubMed / Europe PMC / SS | 缺则 `N/A` |
| 关键词 | API 原始 | 缺则 `N/A` |
| **MeSH 主题词** | PubMed `MeshHeading`（医学专属） | 缺则 `N/A` |
| **证据等级 / Publication Type** | PubMed `PublicationType`（医学专属） | 缺则 `N/A` |
| **临床试验注册号** | PubMed 摘要正则 + `DataBankList`（NCT/ChiCTR/ISRCTN/UMIN/CTRI） | 缺则 `N/A` |
| TLDR | Semantic Scholar `tldr` | 必须标"（AI 总结）"，且受 §4.3 约束 |

**禁止**：

- LLM 编造任何字段
- snippet 截取当 abstract
- 推断页码 / 作者 / 卷期 / 影响因子
- 把预印本说成"已发表"
- 把 Editorial / Commentary / Letter 标成"综述"
- 把综述说成"原创研究"
- 把 OpenAlex `concepts` 直接当论文"关键词"（须标为"概念标签"）

### 4.2 代码化校验（DOI + PMID 双反查 · v0.4.0）

§4.1 是**写给 AI 的规则**；`scripts/validate_output.py` 是**可执行的校验层**（医学版扩展了 PMID 反查）：

```powershell
cd $env:USERPROFILE\.minimax\skills\mbai_paper_search_shared\data\scripts
python validate_output.py "C:\...\paper_search_broad_xxx_20260912.md" --pretty --threshold 0.95
```

| 行为 | 说明 |
|---|---|
| 输入 | 生成的 `.md` 名录（支持 glob 多文件） |
| 动作 | 抽 DOI → Crossref 反查；抽 PMID → PubMed esummary 反查；标 ✅/❌/⚠️ |
| 判定 | 校验率 < `--threshold`（默认 0.95）→ 退出码 **2**，即"不应交付" |
| 离线 | `--no-network` 仅做 ID 抽取自检；`--json-out` 输出机器可读报告 |

**交付纪律**：**任何 .md 名录在交付给用户前必须跑一次**；不达标时按 §7.1 的话术如实告知用户，不要静默交付。

### 4.3 TLDR 字段质量警告（v0.4.0）

- SS 的 `tldr` 是**第三方模型生成的压缩摘要**，不是作者原文；医学论文的**剂量、终点、置信区间**极易在压缩中失真。
- `tldr` 一律标注"（AI 总结）"，**不得**作为临床结论或关键数据的唯一依据。
- 定量结论（HR / OR / 95% CI / p 值 / 样本量）**必须**回到 `abstract` 原文核对。
- 默认 `tldr=optional`；临床证据类检索建议设 `tldr=off`。

## 5. 触发与去重

### 5.1 触发方式

**统一触发词**：`文献检索 X`（mode 由 skill 内部自动推断；默认精细）。

```python
# 伪代码（实际由 LLM 在执行时按规则匹配）
if re.search(r"概览|立项|综述|摸底|survey|landscape|全景|review|指南|guideline", query, re.I):
    mode = "broad"
elif re.search(r"深度|机制|通路|算法|方法|创新|对比|复现", query, re.I):
    mode = "fine"
else:
    mode = "fine"
```

**显式覆盖**（向后兼容 v0.1/v0.2 习惯）：`精细检索 X` / `粗放检索 X`；旧写法 `mbai_paper_search_fine X` / `mbai_paper_search_broad X` 也识别并重定向（见两目录 `DEPRECATED.md`）。

**与 qm_paper_search 共存**：按主题关键词自动选择——`PD-1 / AlphaFold / scRNA-seq / 医学大模型` 走本 skill；`COF / 酶催化 / 钙钛矿` 走 `qm_paper_search`；`difference-in-differences / 面板数据 / 因果推断（经济口径）` 走 `se_paper_search`。

### 5.2 去重机制

- 数据源：`mbai_paper_search_shared/data/seen_papers.json`（**与 qm 完全独立**）
- `topic_id` 前缀：精细 `fine_<topic_name>`，粗放 `broad_<topic_name>`（两个前缀并存识别）
- 同 topic 重复检索自动跳过 `seen_dois` **与 `seen_pmids`**（医学条目常有 PMID 无 DOI）
- 显式命令：新方向 / 清空当前方向记忆 / 清空全部记忆 / 全局去重

**跨 topic 去重策略（v0.4.0 修正，原"跨 topic 默认不去重"反用户）**：

| 情形 | 默认行为 | 用户可覆盖 |
|---|---|---|
| 同 topic 重复检索 | 跳过 `seen_dois` / `seen_pmids` | — |
| 新 topic 与已有 topic **共享 ≥1 个核心关键词**（如"免疫治疗"/"转录组"） | **跨 pool 合并去重**（默认开启） | "本方向不去重" |
| 新 topic 与已有 topic 无共同关键词 | 不去重（视为真新方向） | "全局去重" |
| 用户显式说"全局去重" | 全局去重 | "清空全部记忆" |

- `seen_papers.json` 结构**不变**（仍按 `topic_id` 分组，v0.2 写入的 `seen_pmids` 完整保留）；"跨 pool 去重"是**读取时合并**。
- 报告末尾必须注明"跨主题去重跳过 N 篇（来自 pool: X, Y）"，保证透明。

## 6. 输出格式

输出文件命名：`paper_search_{fine|broad}_<query>_<YYYYMMDD>.md`（保存到 `user_prefs.json` 的 `default_save_dir`）。

### 6.1 统一输出约定（与 qm_paper_search / paper-deep-reading 对齐 · v0.4.0）

| 约定 | 规则 |
|---|---|
| 元信息块 | 置于文件开头，字段顺序：查询 → 研究方向 → 时间范围 → 文献类型 → 数据源 → 检索时间 → 模式；每字段一行 `**字段**：值` |
| DOI 形式 | `[10.xxxx/yyy](https://doi.org/10.xxxx/yyy)` 可点击；有 PMID 时同时给 `[PMID](https://pubmed.ncbi.nlm.nih.gov/<id>/)` |
| 期刊标记 | `（1区 / ⭐ Top / 🔴 预警 / [Preprint] / 🔒 付费墙）`，与 `cas_journal_zones.json` 一致 |
| 来源标注 | 【原文】= API 原始；【AI分析】= 归纳（含 TLDR）；【推测】= 不确定推断 |
| 术语 | 医学缩写首次出现给全称 + 中文（如 NSCLC（非小细胞肺癌，Non-Small Cell Lung Cancer）） |
| 结论口径 | 不输出"决策建议"、不输出用药/诊疗建议；临床类条目附"仅供学术参考，不替代临床判断" |

### 6.2 文件结构

```markdown
# 文献检索结果（精细模式）/（粗放模式 · 综述为主 · 医学/生信/AI）

**查询**：<query>
**研究方向**：<topic_name>
**时间范围**：YYYY–YYYY（精细）/ 不限（粗放）
**文献类型**：article-only（精细）/ review-only（粗放）
**数据源**：<sources>
**检索时间**：<timestamp>
**模式**：fine / broad

## 📋 速览（10 篇 / 15 篇）

| # | 标题 | 作者 | 年份 | DOI |            ← 粗放模式额外加"综述类型"列
|---|------|------|------|-----|
| 1 | [Title](#title-1) | Author1, Author2, ... | 2025 | [10.xxxx](https://doi.org/10.xxxx) | Systematic Review |
| 2 | ... | ... | ... | ... | Meta-Analysis |

> ⭐ Top X 篇 · 1 区 X 篇 · 🔴 预警 X 篇 · [Preprint] X 篇 · 已跳过重复 X 篇 · 含 MeSH X 篇 · 含临床试验注册号 X 篇

---

## 📚 详细条目

### # 1 <a id="title-1"></a> Title
- **作者**：...（仅来自 API）
- **年份**：YYYY
- **期刊**：<Name>（1区 / ⭐ Top / 🔴 预警）
- **影响因子**：XX.X
- **DOI**：[10.xxxx](https://doi.org/10.xxxx)
- **PMID**：[12345678](https://pubmed.ncbi.nlm.nih.gov/12345678/)
- **卷/期/页**：12(3): 45-67
- **综述类型**（粗放模式）：Systematic Review / Meta-Analysis / Review / Guideline
- **证据等级 / Publication Type**：RCT / Meta-analysis / Cohort / Guideline / Case Report / Article
- **MeSH 主题词**：D001, D002, ...
- **临床试验注册号**：NCTxxxxxxxx / ChiCTR-xxxx（如可用）
- **关键词**：k1, k2, k3, k4, k5
- **摘要原文**：<来自 OpenAlex / PubMed / Europe PMC 的完整 abstract>
- **TLDR**（AI 总结）：<一句话总结>
- **标记**：⭐ Top / 1区 / 🔴 预警 / [Preprint bioRxiv] / [OA 全文]

#### 📎 引用格式
<details><summary>BibTeX</summary> … </details>
<details><summary>APA 7</summary> … </details>
<details><summary>GB/T 7714</summary> … </details>
<details><summary>RIS</summary> … </details>

---

### # 2 ...

> ⚠️ 本结果仅供学术调研，**不替代临床判断**；预印本未经同行评审，临床决策请以原始文献 + 现行指南为准。
```

**字段说明**：精细 11 个核心字段 = 作者 / 年份 / 期刊 / 影响因子 / DOI / PMID / 卷期页 / 证据等级 / MeSH / 摘要原文 / TLDR / 标记；粗放额外加"综述类型"。4 种引用格式折叠输出。

### 6.3 交付前自检清单

- [ ] 已跑 `validate_output.py`（DOI + PMID）且校验率 ≥ 0.95
- [ ] 元信息块字段齐全且顺序正确（§6.1）
- [ ] 所有 DOI / PMID 均为可点击链接
- [ ] 预印本条目**全部**带 `[Preprint <server>]` 标记
- [ ] 未把 Editorial / Comment / Letter 标成"综述"
- [ ] MeSH / 证据等级 / 注册号缺失时统一 `N/A`，无 LLM 补全痕迹
- [ ] 跳过的重复条目数已注明（含跨主题 pool 来源）
- [ ] 末尾附"不替代临床判断"声明

## 7. 失败处理

| 场景 | 行为 |
|---|---|
| OpenAlex 限流（429） | 等待 + 重试 1 次 → 切 PubMed |
| PubMed 限流（429） | backoff 1s → 5s → 30s 重试最多 3 次 → 切 Europe PMC |
| Europe PMC 失败 | 切 SS / Crossref |
| DOI 查无 | 走兜底链；PMID 仍可用则保留 |
| 全部源缺 abstract | 标 `摘要：N/A（出版商屏蔽，到 DOI 原页拉）`，不编造 |
| 付费墙 | 保留条目，标 `🔒 付费墙`；同时尝试 Europe PMC 开放版本 |
| 全部源失败 | 按 §7.1 输出失败话术 |
| 综述类混入原创研究 | 标 `[非综述，仅参考]`，不计入 review 主集 |
| Editorial / Comment 混入 | 标 `[非综述，仅参考]` 或过滤 |
| 非医学 / 非生信 / 非 AI 主题 | 二次确认，并提示改用 `qm_paper_search` |
| 查询含 13-18 位连续数字（疑似患者 ID） | **拒绝执行**，提示脱敏（PII 保护，见 §9.4） |

### 7.1 面向用户的错误提示模板（v0.4.0 新增）

| 场景 | 用户可见输出（一行即可） | 自动动作（不打断用户） |
|---|---|---|
| API key 401/403 | "⚠️ 配置的 {source} key 已失效，已自动回退无 key 模式（PubMed 限流 3 req/s）。更新：`Set-ApiKey.ps1 -Provider {source} -Key <NEW>`" | 回退并继续 |
| 429 限流 | "⏳ {source} 限流，已退避 30s 后重试（第 N/3 次）" | backoff 重试 |
| 某源不可用 | "⚠️ {source} 当前不可用，已改用 {fallback}；本次结果按 {fallback} 口径返回" | 切兜底源 |
| 全部源失败 | "❌ 全部数据源失败：<每源一行原因>。请检查网络或稍后重试；也可改用 web_search 兜底（覆盖率会下降）" | 停止 |
| 非医学/生信/AI 主题 | "「X」看起来不属于医学/生信/AI，本 skill 不覆盖。要改用 qm_paper_search（化学）或 se_paper_search（统计/经济）吗？（Y/N）" | **唯一允许的交互** |
| 查询含疑似 PII | "⚠️ 查询含 13-18 位连续数字（疑似患者 ID / 身份证号），出于隐私保护已拒绝执行，请脱敏后重试。" | 停止 |
| 校验不达标 | "⚠️ 交付前校验：{N} 个 DOI/PMID 中 {M} 个未通过反查，已标 ❌，请人工复核。" | 标记并交付 |
| 用户问诊疗建议 | "本工具仅供学术检索，**不提供用药或诊疗建议**。请咨询专业医师并以现行临床指南为准。" | 拒答 |

> 原则：**能自动降级就自动降级**（附一条 ⚠️ 说明），只在"必须由用户决策"或"合规红线"时才提问/拒绝。

## 8. 数据维护

- 分区数据：`shared/data/cas_journal_zones.json`（年度更新；含医学/生信/AI 顶刊白名单与分类）
- 去重池：`shared/data/seen_papers.json`（`fine_` / `broad_` 前缀；同时维护 `seen_dois` + `seen_pmids`）
- 用户偏好：`shared/data/user_prefs.json`
- 调用日志：`shared/data/api_logs.json`（本地，最多 500 条 / 90 天清理）
- 路径策略：首次调用询问，后续使用默认，用户说"换路径"再询问

## 9. 法律约束与合规（医学领域扩展）

> §9.1 数据来源协议 / §9.2 引用规范 / §9.3 内容使用边界 / §9.5 学术与临床道德 / §9.6 适用法律
> 全文见 [references/legal-compliance.md](references/legal-compliance.md)。
> 速记：元数据可存、付费墙 PDF 禁存、不镜像不转售不去来源标识；引用必须以原文献为准，不替代人工阅读。
> §9.4 隐私与 §9.7 医学红线为执行时必守约束，**原文保留在下方**。

### 9.4 隐私与个人信息

- 不存储用户搜索历史到云端
- `seen_papers.json` 仅存 DOI / PMID（公开标识符）
- `user_prefs.json` 存本地路径，不上传
- `api_keys.local.json` 存本机，仅 skill 内部使用
- ❌ 严禁分享他人提供的 API key
- ❌ 严禁把用户搜索内容（query / IP 等）上传到第三方
- ⚠️ **医学 query 可能含疾病名 / 基因名 / 患者相关信息** → 不写入公共 issue / 截图
- ⚠️ **PII 硬拦截**：查询串含 13-18 位连续数字（疑似患者 ID / 身份证号 / 卡号）时**拒绝执行**并要求脱敏

### 9.7 医学领域特别约束（红线）

- **预印本明示**：bioRxiv / medRxiv / arXiv **未经同行评审**，必须在条目中标 `[Preprint]`，且**不得**作为临床结论依据
- **临床试验检索**：仅供学术参考，不替代注册号查询（CT.gov / WHO ICTRP / ChiCTR）
- **药品 / 器械信息**：不构成用药建议；以国家药监局 / FDA 批准说明书为准
- **诊断 / 治疗建议**：本 skill **不输出任何"建议使用 XX 药 / XX 检查"语句**；用户问"该用 XX 治吗"→ **拒绝回答并引导就医**
- **未发表数据**：仅检索已发表（含预印本）文献，不获取未发表 trial data / 内部报告
- **指南时效性**：引用临床实践指南（CPG）必须查证**最新版本、发布机构、证据等级、推荐强度、更新日期**；本 skill 仅供索引

## 10. API 限制约束

关键约束（执行检索时必须遵守）：
- PubMed E-utilities 无 key **3 req/s**（URL 必带 `email` + `tool`）；OpenAlex 无 key 5 req/s；SS 无 key 共享 IP 100 req/min（易 429，脚本自动跳过该源）。
- 429 → 1s/5s/30s 退避重试 ≤3 次；某源失败率 >50% → 沿 OpenAlex→PubMed→Europe PMC 链自动切兜底；429 连续 3 次暂停 5 分钟。
- **粗放模式一次约 30-50 req，必须 sleep 防限流**；两轮粗放检索间隔建议 30s。
- 调用日志仅本地 `data/api_logs.json`（≤500 条 / 90 天清理），不上传。

各源限流表、探活与自动切换规则、错误码处理、频率建议全文见 [references/api-limits.md](references/api-limits.md)。

## 11. API key 管理

原则：**团队共享代码、key 只存各自本机**。读取顺序 `api_keys.local.json` → 环境变量（OPENALEX / SEMANTIC_SCHOLAR / NCBI）→ 无 key。
- 首次配置：`mbai_paper_search_setup.ps1`；日常管理：`Set-ApiKey.ps1 -List|-Key|-EnvVar|-Remove|-Validate`。
- ❌ 严禁把 `api_keys.local.json` 提交 git、在聊天/邮件/截图分享 key；key 失效（401/403）立即更新。
- 出版商屏蔽 abstract → 标 `N/A（出版商屏蔽，到 DOI 原页拉）`，**不用 AI 总结兜底**；预印本缺 abstract 保留链接让用户自取。

完整命令示例见 [references/api-key-management.md](references/api-key-management.md)。

## 12. 文件清单

```
mbai_paper_search/
├── SKILL.md          (本文件，v0.4.0)
├── CHANGELOG.md      (历次修订记录，原本文件顶部 HTML 注释块)
├── README.md         (用户视角的触发/参数/FAQ)
├── assets/
│   └── eval-checklist.md   (检索评测：gold query 集 + DOI/PMID 校验阈值)
└── references/       (低频长章节，按需加载)
    ├── google-scholar-alternatives.md  (§3.4 全文)
    ├── legal-compliance.md             (§9 全文；§9.4/§9.7 红线同时保留在主文档)
    ├── api-limits.md                   (§10 全文)
    └── api-key-management.md           (§11 全文)

mbai_paper_search_shared/
├── README.md
└── data/
    ├── api_keys.template.json     (团队共享，commit)
    ├── api_keys.local.json        (个人本地，gitignore)
    ├── cas_journal_zones.json     (医学/生信/AI 顶刊 + 分类 + 预警)
    ├── seen_papers.json           (去重池，seen_dois + seen_pmids)
    ├── user_prefs.json
    ├── api_logs.json              (本地调用日志，500 条上限)
    ├── README_API_KEYS.md / UPDATE_NOTES.md / .gitignore
    └── scripts/
        ├── Set-ApiKey.ps1                 (单 key 管理，支持 openalex/ss/ncbi/europe_pmc)
        ├── mbai_paper_search_setup.ps1    (首次配置向导)
        ├── mbai_search_and_export.ps1     (v0.2 一站式 PowerShell 入口，保留向后兼容)
        ├── mbai_openalex_to_md.ps1        (v0.1 纯转换器，保留向后兼容)
        ├── paper_search_client.py         (★ v0.4.0：五源检索客户端 · 一键交付)
        └── validate_output.py             (★ v0.4.0：DOI + PMID 反查校验)
```

### 12.1 `paper_search_client.py` 速查（v0.4.0 新增）

| 能力 | 说明 |
|---|---|
| 五源检索 | SS → OpenAlex → PubMed（esearch+efetch）→ Europe PMC → Crossref，任一源失败自动降级并打印告警 |
| 医学字段 | MeSH 主题词、Publication Type → 证据等级、NCT/ChiCTR/ISRCTN/UMIN 注册号、PMID |
| 合并去重 | DOI 优先 → 无 DOI 回退 PMID → 再回退标准化标题；Crossref 覆盖卷/期/页 |
| 方案 H | `--concept-pattern` + `--min-concept-match`，纯本地过滤不额外发请求 |
| 证据偏好 | `--evidence RCT优先 / Meta优先 / 队列优先` |
| 去重池 | 自动读写 `seen_papers.json`（同时维护 `seen_dois` + `seen_pmids`）；跨 topic 合并去重 |
| 导出 | §6.2 规定的 Markdown（含 MeSH / 证据等级 / 注册号行 + 4 种引用格式） |
| 校验 | `--verify` 复用 `validate_output.py`（DOI + PMID 双反查），<95% 返回退出码 4 |
| 安全 | PII 硬拦截（13-18 位连续数字直接拒绝） |
| 其它 | `--dry-run` / `--json-out` / `--pretty` / `--quiet` / `--include-preprint` |

退出码：`0` 成功；`2` 全部数据源失败；`3` 参数错误或 PII 拦截；`4` 校验未达标。

## 13. 维护

**当前版本：v0.4.0**（与 frontmatter 一致）。

| 版本 | 日期 | 重点变更 |
|---|---|---|
| **v0.4.0** | 2026-09-12 | **合并 + 可复用性**：fine + broad 合并为单 skill，统一触发词"文献检索 X" + mode 自动推断；新增 §0 Quickstart、§3.2 调用契约、§3.4 GS 替代路径、§4.2 代码化校验（DOI+PMID）、§4.3 TLDR 警告、§6.1 统一输出约定、§7.1 面向用户错误模板；§5.2 跨 topic 去重重写；粗放 count 25→15；新增 `paper_search_client.py`（五源客户端）与 `validate_output.py`（DOI+PMID 校验） |
| v0.2.0 | 2026-09-09 | 主源探活 · 检索三段式 · 日期/类型本地过滤 · SS tldr · efetch 完整作者 · 引用数 · stdout 告警 + api_logs · seen_papers 自动落盘 · PII 脱敏 · `-Count` 暴露 · UPDATE_NOTES 增量；新增 `mbai_search_and_export.ps1` |
| v0.1.0 | 2026-09-08 | 初版：从 qm_paper_search_fine / broad 切换主题到医学/生信/AI；扩展数据源（PubMed / Europe PMC / 预印本）；扩展字段（MeSH / 临床试验注册号 / 证据等级）；扩展合规约束（医学临床道德 / HIPAA / 人类遗传资源条例） |

**版本口径**：v0.1 / v0.2 期间按 fine / broad 双 skill 各自标版；**v0.4.0 起为单一 skill、单一版本号**。外部导入时以本节表格 + frontmatter `version` 为准。

**废弃目录说明**：

- `mbai_paper_search_fine/` — 已重定向到本 skill（见该目录 `DEPRECATED.md`）
- `mbai_paper_search_broad/` — 已重定向到本 skill（见该目录 `DEPRECATED.md`）
