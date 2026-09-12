# mbai_paper_search — 医学 / 生物信息学 / AI 学术文献检索 skill（README · v0.4.0）

> 统一 skill：原 `mbai_paper_search_fine`（v0.2）+ `mbai_paper_search_broad`（v0.2）已合并；
> v0.4.0 补齐 Quickstart、调用契约、代码化校验、统一输出规范，并新增五源检索客户端。
>
> 完整定义见 [`SKILL.md`](./SKILL.md)；本文件是**用户视角的操作说明**。
>
> ⚠️ **本 skill 是学术调研工具，不替代临床判断，不提供用药 / 诊疗建议。**

---

## 一、30 秒上手

```powershell
# 1) 配 key（可全部留空跳过）
cd $env:USERPROFILE\.minimax\skills\mbai_paper_search_shared\data\scripts
.\mbai_paper_search_setup.ps1

# 2) 直接说人话触发（无需记命令）
#    "文献检索 PD-1 抑制剂 非小细胞肺癌"
#    "粗放检索 医学大模型 综述"
```

产出：`<default_save_dir>\paper_search_{fine|broad}_<query>_<YYYYMMDD>.md`

### 一条命令跑完整链路（v0.4.0 推荐）

```powershell
cd $env:USERPROFILE\.minimax\skills\mbai_paper_search_shared\data\scripts

# 精细：近 3 年 / article / 10 篇，导出后自动做 DOI + PMID 校验
python paper_search_client.py -q "PD-1 inhibitor NSCLC" --pretty --verify

# 粗放：综述为主 / 15 篇 + 方案 H 方向过滤 + 证据等级偏好
python paper_search_client.py -q "medical large language model" --mode broad `
    --evidence Meta优先 --concept-pattern "large language model|clinical|diagnos" --pretty --verify

# 只用 PubMed + OpenAlex，纳入预印本，试跑不落盘
python paper_search_client.py -q "spatial transcriptomics" --sources pubmed,openalex `
    --include-preprint --dry-run --json-out raw.json
```

脚本内部依次完成：五源检索（SS / OpenAlex / PubMed / Europe PMC / Crossref）→ 合并去重 → 方案 H 过滤 → 证据偏好排序 → 去重池读写 → Markdown 导出 → DOI + PMID 校验。
**交付前自检**（未用 `--verify` 时手动跑）：

```powershell
python validate_output.py "C:\...\paper_search_broad_xxx_20260912.md" --pretty
```

---

## 二、触发方式

| 你想做的事 | 触发说法 | 推断模式 |
|---|---|---|
| 已知方向深度调研 | `文献检索 PD-1 抑制剂 NSCLC` / `精细检索 scRNA-seq` | 精细（fine） |
| 新领域摸底 / 找综述 | `文献检索 概览 医学大模型` / `粗放检索 肿瘤免疫 综述` | 粗放（broad） |
| 显式指定 | `精细检索 X` / `粗放检索 X` | 显式覆盖 |
| 数量 / 年份 | `文献检索 AlphaFold 找 20 篇 近 5 年` | 跟随当前模式 |
| 引用图谱 | `文献检索 ctDNA 查引用` | 跟随当前模式 |

### 自动模式推断

- 命中 `概览 / 立项 / 综述 / 摸底 / survey / landscape / 全景 / review / 指南 / guideline` → **粗放**
- 命中 `深度 / 机制 / 通路 / 算法 / 方法 / 创新 / 对比 / 复现` → **精细**
- 都不命中 → **精细**（默认）

### 与 qm_paper_search 的共存

按主题关键词自动选择：`PD-1 / AlphaFold / scRNA-seq / 医学大模型` 走本 skill；`COF / 酶催化 / 钙钛矿` 走 `qm_paper_search`。

---

## 三、参数

| 参数 | 精细默认 | 粗放默认 | 可选值 |
|---|---|---|---|
| 文献类型 `type` | article-only | review-only | article / letter / case-report / review / systematic-review / meta-analysis / guideline / all / mixed |
| 篇数 `count` | 10 | **15** | 1-100（粗放建议 10-25） |
| 时间 `years` | 近 3 年 | 不限 | 1-10 / 不限 |
| 期刊严格度 | strict | loose | strict / loose |
| 排序 | 相关度 | 时间+被引 | relevance / time / citations / time+citations |
| 引用图谱 | on | on | on / off |
| 摘要主源 | openalex | openalex | openalex / pubmed / europe_pmc / semantic_scholar / crossref |
| TLDR | optional | optional | required / optional / off（质量警告见 SKILL §4.3） |
| 预印本 | optional | off | required / optional / off |
| MeSH 优先 | optional | optional | required / optional / off |
| **证据等级偏好** | 不限 | 不限 | **RCT优先 / Meta优先 / 队列优先 / 不限** |
| 综述来源偏好 | — | auto | auto / Nature Reviews / Cochrane / Annual Review / Lancet / NEJM |
| 临床范围 | — | 不限 | pediatric / adult / geriatric / global / 不限 |
| 宽召回 `concept_pattern` | — | 空 | regex（粗放专属，方案 H） |

### 显式命令

| 命令 | 行为 |
|---|---|
| "新方向：XXX" | 新建研究方向 |
| "清空当前方向记忆" | 清空当前 topic 的 seen_dois / seen_pmids |
| "清空全部记忆" | 清空 seen_papers.json |
| "全局去重" | 打开跨 topic 全局去重 |
| "本方向不去重" | 关闭本次跨 pool 合并去重 |
| "换路径" | 重新询问默认保存路径 |

---

## 四、输出

- 命名：`paper_search_fine_<query>_<YYYYMMDD>.md` / `paper_search_broad_<query>_<YYYYMMDD>.md`
- 位置：`shared/data/user_prefs.json` 的 `default_save_dir`
- 结构（完整示例见 SKILL §6.2）：
  - 元信息块（查询 / 研究方向 / 时间范围 / 文献类型 / 数据源 / 检索时间 / 模式）
  - 📋 速览表（标题 / 作者 / 年份 / DOI；**粗放模式加"综述类型"列**）+ 统计行（Top / 1区 / 预警 / Preprint / 跳过重复 / 含 MeSH / 含注册号）
  - 📚 详细条目（**11 个核心字段**：作者 / 年份 / 期刊 / 影响因子 / DOI / PMID / 卷期页 / 证据等级 / MeSH / 摘要原文 / TLDR / 标记）
  - 4 种引用格式：BibTeX / APA 7 / GB/T 7714 / RIS
  - 末尾"仅供学术调研，不替代临床判断"声明

---

## 五、数据源与合规

| 顺位 | 源 | 角色 |
|---|---|---|
| 1 | OpenAlex | 主检索（覆盖医学/AI/生信全领域） |
| 2 | PubMed E-utilities | 生物医学权威（MeSH + 证据等级 + 注册号） |
| 3 | Europe PMC | 开放获取 + 预印本 + 指南 |
| 4 | Semantic Scholar | AI/ML 覆盖 + TLDR + 引用数 |
| 5 | Crossref | 元数据权威（卷期页） |

- **不爬 Google Scholar**（合规 + 稳定性 + 可复现），替代路径见 SKILL §3.4。
- 反幻觉：所有字段 only from API，缺则 `N/A`；交付前用 `validate_output.py` 做 **DOI + PMID** 双反查。
- 医学红线：预印本必须标 `[Preprint]`；**不输出诊疗建议**；查询含疑似患者 ID 直接拒绝。

---

## 六、目录结构

```
mbai_paper_search/
├── SKILL.md       (skill 主定义，v0.4.0)
├── README.md      (本文件)
└── assets/
    └── eval-checklist.md

%USERPROFILE%\.minimax\skills\mbai_paper_search_shared\data\
├── api_keys.template.json      (团队共享模板，commit)
├── api_keys.local.json         (个人本地，gitignore)
├── cas_journal_zones.json      (医学/生信/AI 顶刊 + 分类 + 预警)
├── seen_papers.json            (去重池，seen_dois + seen_pmids)
├── user_prefs.json             (default_save_dir)
├── api_logs.json               (本地调用日志，500 条上限)
├── README_API_KEYS.md / UPDATE_NOTES.md / .gitignore
└── scripts/
    ├── Set-ApiKey.ps1
    ├── mbai_paper_search_setup.ps1
    ├── mbai_search_and_export.ps1     (v0.2 一站式入口，向后兼容)
    ├── mbai_openalex_to_md.ps1        (v0.1 转换器，向后兼容)
    ├── paper_search_client.py         (★ v0.4.0 五源检索客户端)
    └── validate_output.py             (★ v0.4.0 DOI+PMID 校验)
```

---

## 七、开发规范

- frontmatter 必填：`name` / `version` / `description`
- **每次改 SKILL.md 必须同步更新 README.md 与 §13 版本表**
- version 遵循 semver；**对外只暴露一个版本号**（v0.4.0 起不再有 fine/broad 双版本）
- 反幻觉规则改动必须同时在 `validate_output.py` 或调用契约（SKILL §3.2）中可验证
- 改动前先跑 `assets/eval-checklist.md`

---

## 八、常见问题

| 问题 | 处理 |
|---|---|
| 摘要显示 `N/A` | 出版商屏蔽，规则禁止 AI 兜底；点 DOI 到原页取（SKILL §11.6） |
| 为什么还查 OpenAlex？ | 覆盖全领域且免费；PubMed 是权威补充（MeSH + 证据等级），二者合并最优 |
| 综述里混进 Editorial？ | 会把 Editorial / Comment / Letter 标 `[非综述，仅参考]` 或过滤（SKILL §7） |
| 第二次检索篇数变少 | 去重池生效（SKILL §5.2，含跨 topic 合并去重） |
| 粗放检索很慢 | 15 篇 + 引用图谱约 5-10 分钟；可 `citation_graph=off` 或减 count |
| key 失效怎么办 | 按提示语运行 `Set-ApiKey.ps1 -Provider <源> -Key <NEW>`；会自动回退无 key 模式 |
| 想检查结果真假 | `python validate_output.py <文件> --pretty`（DOI + PMID 反查） |
| 可以问用什么药吗？ | **不可以**。本 skill 不提供用药 / 诊疗建议，请咨询医师（SKILL §9.7） |
| 查询被拒绝了 | 可能含 13-18 位连续数字（疑似患者 ID），请脱敏后重试（SKILL §9.4） |
| 非医学主题 | 化学请用 `qm_paper_search` |

---

## 九、变更记录

| 版本 | 日期 | 说明 |
|---|---|---|
| **0.4.0** | 2026-09-12 | fine + broad 合并为单 skill；补 Quickstart / 调用契约 / 代码化校验（DOI+PMID）/ GS 替代路径 / 统一输出约定 / 面向用户错误模板；跨 topic 去重重写；粗放 count 25→15；新增 `paper_search_client.py` 与 `validate_output.py` |
| 0.2.0 | 2026-09-09 | 主源探活 · 检索三段式 · 本地过滤 · SS tldr · efetch 完整作者 · api_logs · seen_papers 自动落盘 · PII 脱敏 · `-Count` 暴露 |
| 0.1.0 | 2026-09-08 | 初版：从 qm 系列切换主题到医学/生信/AI；扩展 PubMed / Europe PMC / 预印本；扩展 MeSH / 注册号 / 证据等级；扩展医学合规 |
