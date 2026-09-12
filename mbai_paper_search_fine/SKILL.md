---
name: mbai_paper_search_fine
version: 0.2
description: |
  医学 / 生物信息学 / 人工智能 学术文献精细检索 v0.1。
  触发词：精细文献检索 / 精细搜索 / mbai_paper_search_fine / 深度调研 / 文献综述深挖。
  用途：已知研究方向（疾病机制、算法、组学方法、临床应用等）做深度文献调研。
  主源：OpenAlex API（覆盖广，含临床医学、生物、AI 三类，2.5 亿+ 论文）。
  备链：PubMed E-utilities（生物医学最权威，PubMed/MEDLINE）→ Europe PMC（开放获取 + 预印本）→ Semantic Scholar → Crossref。
  预印本覆盖：bioRxiv / medRxiv / arXiv（cs.AI / cs.LG / q-bio）。
  文献类型默认 article-only（原创研究为主，Letter、Case Report 也算）。
  默认 10 篇，时间范围近 3 年，强制反幻觉。
  数据根目录：%USERPROFILE%\.minimax\skills\mbai_paper_search_shared\data\
---

# mbai_paper_search_fine — 医学/生物信息学/AI 精细文献检索 v0.2

> **v0.2 重大更新**（2026-09-09）：
> - 新增一站式脚本 `mbai_search_and_export.ps1` v0.2，集成**主源探活**、**三段式检索**、**seen_papers 自动化**、**SS tldr 补全**、**PII 脱敏**
> - OpenAlex 主源异常自动切 PubMed（#1 改进）
> - 检索三段式：试探 → 放宽 → 本地过滤（#2 改进，规避 per_page>=10 / page>=2 触发 0 bug）
> - 日期/类型过滤本地化（#3 改进，规避 OpenAlex filter 字段返 0）
> - SS tldr 字段拉取（#4 改进，避免 LLM 编造）
> - efetch XML 解析完整作者列表（#5 改进，esummary 截断版弃用）
> - 引用数 cited_by_count（#6 改进，via SS API）
> - stdout 实时告警 + `api_logs.json` 累计（#7 改进）
> - seen_papers.json 自动落盘（#8 改进，topic_id + seen_pmids + seen_dois）
> - PII 脱敏检查（#11 改进，13-18 位数字串检测）
> - `-Count` 参数暴露（#12 改进，默认 10，可拉 1-100）
> - UPDATE_NOTES 增量（#10 改进，`-AppendUpdateNote`）

> 本 skill 是 `qm_paper_search_fine`（化学）的同源孪生版，主题切换为 **Medicine · Bioinformatics · Artificial Intelligence**。  
> 全部反幻觉规则、引用规范、API 限流约束、key 管理流程继承自 qm 系列并按医学/AI 领域特性扩展（PubMed、预印本、临床试验元数据）。

## 1. 适用与不适用

**适用**
- 已知研究方向，需要深度调研具体研究进展（如：某个基因通路、某种 AI 模型、某类临床干预）
- 找原创研究（Article / Letter / Case Report / Brief Communication）
- 找方法学、新算法、新数据库、新临床指南的具体研究
- 引用图谱（references + cited by，一层）
- 临床证据追溯（PubMed 强相关：RCT / Meta-analysis / Cohort study）

**不适用**
- 领域概览、立项摸底 → 用 `mbai_paper_search_broad`
- 非医学 / 非生物信息学 / 非 AI 领域（如纯物理、地学）→ 用 `qm_paper_search` 或另立 skill
- 全文下载、翻译、润色、本地 PDF 管理

## 2. 检索参数（v0.1）

| 参数 | 默认 | 可选值 | 说明 |
|---|---|---|---|
| `type` | article-only | article / letter / case-report / mixed | 文献类型过滤（医学领域细化） |
| `count` | 10 | 1-50 | 返回篇数 |
| `years` | 3 | 1-10 / 不限 | 时间范围（年） |
| `journal_filter` | strict | strict / loose | 顶刊过滤严格度 |
| `sort_by` | relevance | relevance / time / citations | 排序方式 |
| `citation_graph` | on | on / off | 引用图谱开关 |
| `abstract_source` | openalex | openalex / pubmed / europe_pmc / semantic_scholar / crossref | 摘要主源 |
| `keywords_required` | true | true / false | 是否必须返回关键词（MeSH / keywords） |
| `tldr` | optional | required / optional / off | TLDR（AI 总结）开关 |
| `include_preprint` | optional | required / optional / off | 是否纳入 bioRxiv / medRxiv / arXiv 预印本 |
| `mesh_required` | optional | required / optional / off | 是否优先返回 PubMed MeSH 主题词 |
| `evidence_level` | optional | RCT优先 / Meta优先 / 队列优先 / 不限 | 临床证据等级偏好（医学专属） |

## 3. 数据源（v0.2 主链 + 探活机制）

```
mbai_search_and_export.ps1 v0.2 入口
  ↓
[1] 主源探活（Test-OpenAlexHealth / Test-PubMedHealth）
  ↓ 健康
OpenAlex API（主，免费，2.5 亿+ 论文，覆盖医学/AI/生信全领域）
  ↓ 异常 / 0 命中
PubMed E-utilities（生物医学最权威，MEDLINE 3200 万+）
  ↓ 缺 / 非生物医学
Europe PMC（开放获取 + 预印本 + 专利 + 临床指南）
  ↓ 缺
Semantic Scholar API（AI/ML 论文覆盖好，2 亿+）
  ↓ 缺
Crossref（DOI 反查，元数据权威）
  ↓ 缺
返回 N/A
```

**预印本并行通道**（可与主链并行检索）：
```
bioRxiv / medRxiv API  ← 生命科学 + 临床预印本
arXiv API (cs.AI/cs.LG/q-bio)  ← AI + 定量生物学
```

**不爬 Google Scholar**（v0.1 决定）。  
**不依赖 LLM 编造**（强制反幻觉规则，详见 §4）。

### 3.1 数据源选择策略

| 主题 | 主源 | 备选 |
|---|---|---|
| 临床医学（疾病、药物、试验） | **PubMed** | OpenAlex → Europe PMC |
| 基础医学（机制、信号通路） | **PubMed** | OpenAlex → Europe PMC |
| 生物信息学（算法、组学工具） | **OpenAlex** | PubMed → Semantic Scholar |
| 机器学习 / 深度学习（通用方法） | **Semantic Scholar** | OpenAlex → arXiv |
| 医学 AI（影像、诊断、LLM 临床应用） | **PubMed** | OpenAlex → Semantic Scholar |
| 单细胞 / 空间组学 | **OpenAlex**（预印本并行） | PubMed → bioRxiv |

## 4. 强制反幻觉规则

| 字段 | 来源 | 缺失处理 |
|---|---|---|
| 标题 | API 原始 | 强制必须有 |
| 作者 | API 原始 | 缺则 `N/A`，**严禁 LLM 补全** |
| 年份 | API 原始 | 强制必须有 |
| 期刊 | API 原始 | 缺则 `N/A` |
| 卷/期/页 | API 原始 | 缺则 `N/A` |
| DOI | API 原始 | 强制必须有；预印本可缺但保留源链接 |
| 影响因子 | 本地 cas_journal_zones.json | 缺则 `N/A` |
| 摘要原文 | OpenAlex / PubMed / Europe PMC / SS | 缺则 `N/A` |
| 关键词 | API 原始（含 MeSH） | 缺则 `N/A` |
| MeSH | PubMed MeSH 字段 | 缺则 `N/A`（医学主题词） |
| 临床试验注册号 | PubMed secondary_source / CT.gov | 缺则 `N/A`（临床类优先） |
| TLDR | Semantic Scholar tldr 字段 | AI 总结必须明确标"AI 总结" |
| 证据等级 | PubMed publication type | 缺则 `N/A`（RCT / Meta / Cohort） |

**禁止**：
- LLM 编造任何字段
- snippet 截取当 abstract
- 推断页码 / 作者 / 卷期 / 影响因子
- 把预印本说成"已发表"
- 把综述说成"原创研究"

## 5. 触发与去重

### 5.1 触发方式
- "精细文献检索 X" / "深度搜索 X"
- "mbai_paper_search_fine X"
- 默认自动使用（如果用户没说"粗放"或"概览"）
- 与 `qm_paper_search_fine` 共存：用领域关键词区分（如"PD-1" "AlphaFold" "scRNA-seq" "LLM 临床" 走 mbai；"COF" "酶催化" 走 qm）

### 5.2 去重机制（v0.2 自动化）
- 数据源：`%USERPROFILE%\.minimax\skills\mbai_paper_search_shared\data\seen_papers.json`
- topic_id 前缀：`fine_<topic_name_slug>`（与 broad 隔离；与 qm 的 fine_ 前缀不冲突——两个 skill 各自 seen_papers.json）
- **v0.2 新增**：`mbai_search_and_export.ps1` 完成后**自动**写 seen_pmids / seen_dois 到 `seen_papers.json`
- **v0.2 新增**：下一次同 topic 检索可自动跳过（脚本支持 `-SkipSeen` 参数，待 v0.3 实现完整跳过逻辑）
- 跨 topic 默认不去重
- 显式命令：新方向 / 清空当前方向记忆 / 清空全部记忆 / 全局去重

## 6. 输出格式

输出文件：`paper_search_fine_<query>_<YYYYMMDD>.md`  
保存路径：shared/data/user_prefs.json 的 default_save_dir。

### 6.1 文件结构

```markdown
# 文献检索结果（精细模式 · 医学/生信/AI）

**查询**：<query>
**研究方向**：<topic_name>
**时间范围**：YYYY–YYYY
**文献类型**：article-only
**数据源**：<sources>
**检索时间**：<timestamp>

## 📋 速览（10 篇）

| # | 标题 | 作者 | 年份 | DOI |
|---|------|------|------|-----|
| 1 | [Title](#title-1) | Author1, Author2, ... | 2025 | [10.xxxx](https://doi.org/10.xxxx) |
| 2 | ... | ... | ... | ... |

> ⭐ Top X 篇 · 1 区 X 篇 · 🔴 预警 X 篇 · [Preprint] X 篇 · 已跳过重复 X 篇 · 含 MeSH X 篇 · 含临床试验注册号 X 篇

---

## 📚 详细条目

### # 1 <a id="title-1"></a> Title
- **作者**：...（仅来自 API）
- **年份**：YYYY
- **期刊**：<Name>（1区 / ⭐ Top / 🔴 预警）
- **影响因子**：XX.X
- **DOI**：[10.xxxx](https://doi.org/10.xxxx)
- **关键词**：k1, k2, k3, k4, k5
- **MeSH 主题词**（如可用）：D001, D002, ...
- **证据等级 / Publication Type**：RCT / Meta-analysis / Cohort / Case Report / Article
- **临床试验注册号**（如可用）：NCTxxxxxxx / ChiCTR-xxxx
- **摘要原文**：<来自 OpenAlex / PubMed 的完整 abstract>
- **TLDR**（AI 总结）：<一句话总结>
- **标记**：⭐ Top / 1区 / 🔴 预警 / [Preprint bioRxiv] / [Preprint arXiv]

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
| 非医学/非生信/非 AI 主题 | 二次确认是否走错 skill（提示用 qm_paper_search_fine） |

## 8. 数据维护

- 分区数据：`shared/data/cas_journal_zones.json`（年度更新；2026 版已含医学/AI 顶刊白名单）
- 去重池：`shared/data/seen_papers.json`（topic_id 加 `fine_` 前缀）
- 用户偏好：`shared/data/user_prefs.json`
- 路径策略：首次调用询问，后续使用默认，用户说"换路径"再询问

## 9. 与 broad 的区别

| 维度 | fine（本 skill） | broad |
|---|---|---|
| 默认篇数 | 10 | 25 |
| 文献类型 | article（含 Letter / Case Report） | review |
| 顶刊过滤 | 严格 | 宽松 |
| 时间范围 | 近 3 年 | 不限 |
| 排序 | 相关度 | 时间 + 被引 |
| 引用图谱 | 一层 | 一层 |
| 适用 | 深度调研 | 领域概览 |
| 预印本 | 可选纳入 | 可选纳入 |

## 10. 与 qm_paper_search_fine 的关系

- 完全**独立**的 seen_papers.json / user_prefs.json / cas_journal_zones.json
- 共享：SKILL.md 的整体框架（参数表 / 反幻觉规则 / 引用规范 / key 管理）
- 差异：数据源（PubMed/Europe PMC 替代 X-Mol）、期刊白名单、字段扩展（MeSH / 临床试验注册号 / 证据等级）、预印本并行通道
- 共存：用户可同时安装两套，按主题关键词自动选择

---

## 11. 法律约束与合规（继承自 qm_paper_search_fine §11，医学领域扩展）

### 11.1 数据来源合规

| 数据源 | 协议 | 使用范围 |
|---|---|---|
| **OpenAlex** | CC0（公有领域） | 可自由使用、修改、分发，无需署名（建议注明 "Data from OpenAlex"） |
| **Crossref** | CC0 | 同上 |
| **Semantic Scholar** | API 协议 | 注明来源；非商业用途建议遵守 |
| **PubMed / MEDLINE** | 公有领域（NIH/NCBI） | 可自由使用；建议注明 "Data from PubMed" |
| **Europe PMC** | 开放获取（CC BY / CC BY-NC） | 标注 license；不可商业转售 |
| **bioRxiv / medRxiv** | 各预印本协议 | 引用时保留 license 信息；明示为预印本 |
| **arXiv** | 永久 CC | 引用保留 license |

### 11.2 引用规范

- **必须保留**：原始作者、期刊、DOI、出版商信息
- **必须输出**：4 种引用格式（BibTeX / APA 7 / GB/T 7714 / RIS）
- **严禁**：去除作者署名、期刊信息、DOI、MeSH 主题词
- **临床论文额外要求**：保留临床试验注册号、伦理批件号（如披露）、出版商限制声明
- **翻译字段**（GB/T 7714 中文版）：由 LLM 拼装，**不作为权威引用**，仅供中文用户参考；以英文原版为准

### 11.3 内容使用边界

**允许**：
- 保存论文元数据（标题、作者、DOI、摘要、MeSH、引用数、概念标签）
- 保存 PubMed/Europe PMC 还原的 abstract
- 通过 DOI 链接到出版商原页（仅作跳转，不存 PDF）
- 通过 ClinicalTrials.gov 链接到试验详情（仅作跳转）

**禁止**：
- ❌ 存储付费墙后的 PDF 原文
- ❌ 批量下载/镜像出版商数据库
- ❌ 商业转售聚合数据
- ❌ 去除来源标识（OpenAlex / PubMed / Europe PMC / bioRxiv / arXiv）
- ❌ 用于生成假论文、伪造数据、伪造临床试验
- ❌ 替代人工阅读原文作为临床决策唯一依据（**医疗高风险：误诊/误治责任由使用者承担**）
- ❌ 替代 Cochrane / UpToDate / 临床指南作为循证医学唯一来源

### 11.4 隐私与个人信息

- 不存储用户搜索历史到云端
- `seen_papers.json` 仅存 DOI（公开标识符）
- `user_prefs.json` 存本地路径，不上传
- `api_keys.json` 存本机，仅 skill 内部使用
- ❌ 严禁分享他人提供的 API key
- ❌ 严禁把用户搜索内容（包含 query、IP 等）上传到第三方
- ⚠️ 医学检索 query 可能含疾病名/基因名/患者相关 → 特别注意不写入公共 issue / 截图

### 11.5 学术与临床道德

- 本 skill 是**辅助工具**，**不替代人工阅读、不替代临床判断**
- 检索结果仅供学术调研，**不作为临床决策唯一依据**
- 引用必须以**原文献**为准，本工具输出仅作辅助
- 严禁用于：代写论文、伪造数据、剽窃、学术不端
- 严禁绕过付费墙抓取全文
- 严禁批量爬取造成出版商服务器压力
- 涉及临床决策的论文必须经由专业医师审阅原文 + 当前临床指南

### 11.6 适用法律

- 本 skill 仅在用户所在司法辖区**合法使用**
- 涉及跨境学术资源时遵守当地法规：
  - **中国境内**：遵守《网络安全法》《数据安全法》《个人信息保护法》《科学技术进步法》《人类遗传资源管理条例》（**特别注意：人类遗传资源相关数据出境须申报**）
  - **欧盟**：遵守 GDPR（医学数据 / 基因数据属敏感个人信息）
  - **美国**：遵守 CFAA、DMCA、HIPAA（不主动检索/存储受 HIPAA 保护的患者数据）
- 学术出版商协议以各出版商 ToS 为准
- 如发现违规使用，立即停止相关功能

### 11.7 医学领域特别约束

- **预印本明示**：bioRxiv / medRxiv / arXiv 预印本**未经同行评审**，必须在条目中标记 `[Preprint]`
- **临床试验检索**：仅供学术参考，不替代注册号查询（CT.gov / WHO ICTRP / ChiCTR）
- **药品 / 器械信息**：仅供学术参考，**不构成用药建议**；最终用药以国家药监局 / FDA 批准说明书为准
- **诊断 / 治疗建议**：本 skill 不输出任何"建议使用 XX 药 / XX 检查"的语句；如用户问"该用 XX 治吗"，**拒绝回答并引导就医**
- **未发表数据**：本 skill 仅检索已发表（含预印本）文献，不获取未发表 trial data / 内部报告

---

## 12. API 限制约束（继承自 qm_paper_search_fine §12，医学领域扩展）

### 12.1 各源 API 规则

| API | 限流（带 key） | 限流（无 key） | 备注 |
|---|---|---|---|
| **OpenAlex** | 50 req/s | 5 req/s | polite pool 加 mailto |
| **PubMed E-utilities** | 10 req/s（NCBI key） | 3 req/s | URL 必须带 `email` & `tool=mbai_paper_search` |
| **Europe PMC** | 礼貌标识 | 无硬限流 | URL 带 `email=` |
| **Semantic Scholar** | 100 req/s（API key） | 共享 IP 100 req/min | 详 Graph API 文档 |
| **Crossref** | 礼貌池 | 50 req/s（共享） | 建议加 mailto |
| **bioRxiv / medRxiv** | 公开 | 公开 | 月度更新 |
| **arXiv** | 公开 | 公开 | 建议加 mailto |

**强制行为**：
- ✅ 加 User-Agent：`mbai_paper_search_skill/0.2 (Mavis; paper retrieval)`
- ✅ 加 mailto 或 key
- ❌ 禁止并发批量刷（> 10 req/s 持续）
- ❌ 禁止镜像/转售数据
- ❌ 禁止用于 LLM 训练

### 12.7 主源健康度自动化（v0.2 新增）

`mbai_search_and_export.ps1` v0.2 入口处强制执行：

1. **OpenAlex 探活**：`per_page=1` 无 filter 调用，meta_count > 0 才认为健康
2. **PubMed 探活**：einfo 端点 200 才认为健康
3. **自动切换**：OpenAlex 异常自动切 PubMed（mbai §3 兜底链 #1）
4. **实时告警**：stdout 输出 `⚠ OpenAlex API 异常，自动切到 PubMed`
5. **API 日志**：每次调用（含探活）写入 `data/api_logs.json`（最多保留 500 条）
6. **失败计数**：基于 `api_logs.json` 可统计各源失败率（用于 §12.6 阈值判断）

### 12.2 当前 key 使用情况

- key 存于 `%USERPROFILE%\.minimax\skills\mbai_paper_search_shared\data\api_keys.json`
- 仅用于本 skill，**不分享**
- ❌ 不嵌入到代码仓库公开处
- key 失效时（401/403）：提示用户提供新 key，回退无 key 模式

### 12.3 错误码处理

| 状态码 | 含义 | 处理 |
|---|---|---|
| 200 | OK | 继续 |
| 401 | key 无效 | 提示用户提供新 key；回退无 key 模式 |
| 403 | 禁止访问 | 检查 User-Agent / key / IP |
| 429 | 限流 | backoff 1s → 5s → 30s 后重试；最多 3 次 |
| 5xx | 服务端错误 | backoff 重试 3 次 → 切换兜底源 |
| network_error | 网络层失败 | 切换 web_search 兜底 |

### 12.4 调用频率建议

| 场景 | 建议频率 |
|---|---|
| 主题检索 | 1-3 req/search（搜索 + PubMed 详情 + 引用图谱） |
| 引用图谱 | 1-5 req/paper（references + cited by） |
| 批量检索 | ≤ 10 req/min（避免触发 PubMed 限流） |
| 持续监控 | 严禁（无合理学术场景） |

### 12.5 调用日志

- 每次 API 调用记录：endpoint / status / latency / date
- 异常时记录完整错误
- 日志仅本地（`data/api_logs.json`），**不上传**
- 用于诊断 API 健康度
- 90 天后自动清理过期日志

### 12.6 API 健康度监控

- 当 OpenAlex 失败率 > 50% 时：自动切 PubMed
- 当 PubMed 失败率 > 50% 时：自动切 Europe PMC
- 当 429 连续 3 次：暂停 5 分钟
- 当 5xx 连续 5 次：警告用户并切兜底

---

## 13. API key 管理（继承自 qm §13）

### 13.1 设计原则
- **团队共享代码 + 个人本地 key** —— 代码 commit 到 git，key 不共享
- 每个成员独立管理自己的 key
- 支持后续 key 变更（失效、续期、轮换）

### 13.2 读取顺序
1. `data/api_keys.local.json`（个人本地，最优先）
2. 环境变量 `OPENALEX_API_KEY` / `SEMANTIC_SCHOLAR_API_KEY` / `NCBI_API_KEY`
3. 不使用 key（限流低但能跑）

`api_keys.template.json` 是占位符，**不会被读**。

### 13.3 首次配置
```powershell
.\mbai_paper_search_setup.ps1
# 按提示输入 OpenAlex / SS / NCBI key（或留空跳过）
```

### 13.4 后续管理
```powershell
# 查看当前 key 状态
.\Set-ApiKey.ps1 -List

# 更新 OpenAlex key
.\Set-ApiKey.ps1 -Provider openalex -Key "NEW_KEY"

# 改用环境变量
.\Set-ApiKey.ps1 -Provider semantic_scholar -EnvVar

# 删除 key
.\Set-ApiKey.ps1 -Provider ncbi -Remove

# 验证 key 有效性
.\Set-ApiKey.ps1 -Validate
```

### 13.5 安全约束
- ❌ 不要把 `api_keys.local.json` 加入 git
- ❌ 不要在聊天/邮件/截图中分享 key
- ✅ key 失效时（401/403）立即更新
- ✅ 详细文档见 `data/README_API_KEYS.md`

### 13.6 输出规范
- 出版商屏蔽 abstract → 标 `N/A（出版商屏蔽，到 DOI 原页拉）`，**不用 AI 总结兜底**
- 标记为 `🔒 待人工处理`，交付用户
- 不在 .md 中编造 abstract 内容
- 预印本 abstract 缺 → 保留预印本链接，让用户自取

## 14. 文件清单

```
mbai_paper_search_fine/
├── SKILL.md
└── README.md

共享数据（在 shared/）：
mbai_paper_search_shared/
└── data/
    ├── api_keys.template.json     (团队共享，commit)
    ├── api_keys.local.json        (个人本地，gitignore)
    ├── cas_journal_zones.json     (医学/生信/AI 顶刊白名单)
    ├── UPDATE_NOTES.md
    ├── seen_papers.json           (topic_id 加 fine_ 前缀)
    ├── user_prefs.json
    ├── api_logs.json              (v0.2 新增：API 调用日志)
    ├── README_API_KEYS.md
    ├── .gitignore
    └── scripts/
        ├── Set-ApiKey.ps1
        ├── mbai_paper_search_setup.ps1
        ├── mbai_search_and_export.ps1   (v0.2 一站式入口)
        └── mbai_openalex_to_md.ps1      (v0.1 纯转换器，保留向后兼容)
```

## 15. 维护

- v0.2.0（2026-09-09）：
  - P0：主源探活（#1）· seen_papers 自动化（#8）
  - P1：检索三段式（#2）· SS tldr（#4）· efetch 完整作者（#5）
  - P2：日期/类型本地过滤（#3）· 引用数（#6）· 显式告警（#7）· UPDATE_NOTES 增量（#10）· PII 脱敏（#11）· -Count 暴露（#12）
  - 新建 `mbai_search_and_export.ps1` 一站式脚本（33 KB，含全部改进）
  - 保留 `mbai_openalex_to_md.ps1` 作为纯转换器（向后兼容）
  - 新增 `api_logs.json` 累计日志
- v0.1.0 初版（2026-09-08）：从 qm_paper_search_fine 切换主题到医学/生信/AI；扩展数据源（PubMed / Europe PMC / 预印本）；扩展字段（MeSH / 临床试验注册号 / 证据等级）；扩展合规约束（医学临床道德 / 遗传资源条例）
