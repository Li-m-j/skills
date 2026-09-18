# paper-skills — 学术文献检索 + 论文深度阅读 Skill 套件

面向科研工作者的 AI Agent Skill 集合，覆盖 **文献检索 → 取全文 → 精读报告 → 知识库存档** 的完整链路。

- **化学**、**医学 / 生物信息学 / AI** 与 **统计 / 计量经济学 / 经济学** 三套检索 skill（同源孪生，主题与数据源不同）
- **计算化学论文深度阅读** skill（PDF 解析 → 结构化报告）
- 反幻觉落到**代码层**：所有检索结果交付前都必须通过 DOI / PMID / arXiv ID 反查校验

**License**：[MIT](./LICENSE)（代码与文档同许可）· 通过 API 获取的文献数据与期刊分区数据**不适用 MIT**，见 [§八 许可](#八许可)。

---

## 目录结构

```
paper-skills/
├── .gitignore
├── README.md
│
├── qm_paper_search/                    ← 化学文献检索（v0.4.1）
├── qm_paper_search_shared/             ← 化学套件共享数据层 + 脚本
│
├── mbai_paper_search/                  ← 医学/生信/AI 文献检索（v0.4.0）
├── mbai_paper_search_shared/           ← 医学套件共享数据层 + 脚本
│
├── se_paper_search/                    ← 统计/计量经济/经济学文献检索（v0.1.0）
├── se_paper_search_shared/             ← 经济学套件共享数据层 + 脚本
│
├── paper-deep-reading/                 ← 计算化学论文深度阅读报告（v0.4）
│
└── 历史归档（DEPRECATED；SKILL.md 已改名为 SKILL.md.disabled，确认不参与加载）
    ├── qm_paper_search_broad/
    ├── qm_paper_search_v0.1_deprecated/
    ├── mbai_paper_search_fine/
    └── mbai_paper_search_broad/
```

---

## 一、四个 skill 分别做什么

| Skill | 主题 | 输入 | 输出 |
|---|---|---|---|
| `qm_paper_search` | 化学 / 材料 / 催化 | 一句话检索需求 | `paper_search_{fine\|broad}_*.md` 文献名录（9 核心字段 + 4 种引用格式） |
| `mbai_paper_search` | 医学 / 生信 / AI | 一句话检索需求 | 同上，额外含 MeSH 主题词 / 证据等级 / 临床试验注册号 / PMID |
| `se_paper_search` | 统计 / 计量经济学 / 经济学 | 一句话检索需求（中英皆可，英文命中更稳） | 同上，但期刊口径为**档位制**（Top5 经济 / 统计四大 / Finance Top3 / 中文权威），无影响因子；额外含 arXiv ID 字段 |
| `paper-deep-reading` | 计算化学 | 论文 PDF / 文本 / URL / IMA 引用 | 7 模块 10 要点深度阅读报告（或综述变体 5 模块 8 要点） |

四者可串联：**检索 → 取 PDF → 精读 → 存档**（衔接说明见 `paper-deep-reading/references/pipeline-orchestration.md`）。

### 检索模式（三个检索 skill 共用）

| 模式 | 触发词 | 默认参数 |
|---|---|---|
| 精细 `fine` | 深度调研 / 机制 / 方法 / 对比 | article-only、10 篇、近 3 年、相关度排序 |
| 粗放 `broad` | 概览 / 立项 / 综述 / 摸底 / survey | review-only、15 篇、时间不限、时间+被引排序 + 宽召回 |

统一触发词 `文献检索 X`，模式自动推断；也可用 `精细检索 X` / `粗放检索 X` 显式指定。经济学套件在通用触发词之外额外识别 `handbook`（→ broad）与 `估计量 / 识别`（→ fine）。

经济学套件的差异：**arXiv（econ.EM/econ.GN/stat.ME 等）为主检索链**、免 key；broad 模式保留综述**并纳入 working papers（预印本）**；预印本一律标注 `[Preprint]`；期刊无中科院分区/IF，只标注人工整理的档位（未收录则不标）。

---

## 二、安装

Skill 按约定放在 agent 的 user-level skills 目录：

```powershell
# Windows（MiniMax Code / Mavis 约定路径）
$dst = "$env:USERPROFILE\.minimax\skills"
New-Item -ItemType Directory -Force -Path $dst | Out-Null
Copy-Item -Path ".\qm_paper_search", ".\qm_paper_search_shared" -Destination $dst -Recurse -Force
Copy-Item -Path ".\mbai_paper_search", ".\mbai_paper_search_shared" -Destination $dst -Recurse -Force
Copy-Item -Path ".\se_paper_search", ".\se_paper_search_shared" -Destination $dst -Recurse -Force
Copy-Item -Path ".\paper-deep-reading" -Destination $dst -Recurse -Force
```

> SKILL.md 中 `/references/`、`/scripts/`、`/assets/` 的路径均按**相对于本 skill 目录**解析；
> 共享数据层（`*_shared/`）与其对应 skill 必须放在**同一父目录**下。

```bash
# macOS / Linux 等价操作
mkdir -p ~/.minimax/skills
cp -r qm_paper_search qm_paper_search_shared mbai_paper_search mbai_paper_search_shared se_paper_search se_paper_search_shared paper-deep-reading ~/.minimax/skills/
```

### 首次配置（API key，可选）

```powershell
cd "$env:USERPROFILE\.minimax\skills\qm_paper_search_shared\data\scripts"
.\qm_paper_search_setup.ps1        # 化学套件：OpenAlex / Semantic Scholar

cd "$env:USERPROFILE\.minimax\skills\mbai_paper_search_shared\data\scripts"
.\mbai_paper_search_setup.ps1      # 医学套件：OpenAlex / SS / NCBI / Europe PMC email

cd "$env:USERPROFILE\.minimax\skills\se_paper_search_shared\data\scripts"
.\se_paper_search_setup.ps1        # 经济学套件：OpenAlex / SS（arXiv、Crossref 免 key）
```

**全部可留空**——无 key 也能跑，只是限流更严。

---

## 三、快速开始

### 检索（一条命令跑完整链路）

```powershell
cd "$env:USERPROFILE\.minimax\skills\qm_paper_search_shared\data\scripts"
python paper_search_client.py -q "machine learning potential" --pretty --verify

cd "$env:USERPROFILE\.minimax\skills\mbai_paper_search_shared\data\scripts"
python paper_search_client.py -q "PD-1 inhibitor NSCLC" --pretty --verify

cd "$env:USERPROFILE\.minimax\skills\se_paper_search_shared\data\scripts"
python paper_search_client.py -q "difference-in-differences heterogeneous treatment effects" --pretty --verify
```

脚本内部依次完成：多源检索 → 合并去重 → 方案 H 方向过滤 → 去重池读写 → Markdown 导出 → DOI/PMID/arXiv ID 反查校验（经济学套件为 DOI + arXiv 双反查）。

主要参数：

| 参数 | 说明 |
|---|---|
| `-q/--query` | 检索关键词（必填） |
| `--mode auto\|fine\|broad` | 模式（默认 auto 自动推断） |
| `--count` / `--years` / `--type` / `--sort` | 篇数 / 年限 / 类型 / 排序 |
| `--concept-pattern` / `--min-concept-match` | 方案 H 宽召回二次方向过滤（正则） |
| `--sources` | 参与检索的源（逗号分隔） |
| `--evidence RCT优先\|Meta优先\|队列优先` | 医学套件专属：证据等级偏好 |
| `--no-dedup` / `--global-dedup` / `--no-cross-topic` | 去重池行为覆盖 |
| `--verify` | 导出后做 DOI（+PMID）反查校验 |
| `--dry-run` / `--json-out` | 试跑不落盘 / 另存原始 JSON |

### 交付前校验（独立使用）

```powershell
python validate_output.py "C:\path\to\paper_search_broad_xxx_20260912.md" --pretty --threshold 0.95
```

- 化学版：DOI → Crossref 反查
- 医学版：DOI → Crossref **+** PMID → PubMed esummary 双反查
- 经济学版：DOI → Crossref **+** arXiv ID → arXiv Export API 双反查（仅含 SSRN/NBER 链接、无 DOI/arXiv ID 的条目无法机器反查，须人工复核）
- 校验率 < 阈值 → 退出码 `2`（即"不应交付"）；`--no-network` 可离线自检

### 深度阅读

```
帮我读论文：C:\papers\xxx.pdf
快读一下 C:\papers\xxx.pdf          # 速览模式（≤500 字）
```

---

## 四、依赖

| 组件 | 必需性 | 说明 |
|---|---|---|
| Python **3.8+** | 必需 | 所有 `*.py` 仅用标准库，**零第三方依赖** |
| PowerShell 5.1+ | Windows 上用 `.ps1` 时需要 | key 管理 / 旧版入口脚本 |
| `pymupdf` | 可选 | `paper-deep-reading` 抽取论文图片；未装则自动降级 |
| `pdfplumber` | 可选 | 增强 PDF 文本提取 |
| `pdftotext`（poppler） | 可选 | 首选 PDF 文本后端 |
| Tesseract / PaddleOCR | 可选 | 扫描件 PDF 的 OCR 兜底；未装时给出安装指引 |
| Node 18+ | 可选 | `paper-deep-reading` 的 IMA 知识库联用 |

```bash
pip install pymupdf pdfplumber
```

---

## 五、数据与隐私

### 本仓库**不包含**（已在 `.gitignore` 中）

| 文件 | 原因 |
|---|---|
| `api_keys.local.json` | **个人 API key（机密）** |
| `seen_papers.json` | 个人检索去重池（含检索历史） |
| `user_prefs.json` | 含本机绝对路径 |
| `api_logs.json` | 本地调用日志 |
| `_backup/` | 本地备份 |

仓库只提供模板：`api_keys.template.json`、`user_prefs.template.json`（复制去掉 `.template` 即可用）。

### ⚠️ 安全提醒

**如果你之前把本仓库（或这些 skill 目录）提交到过任何公开位置，请立即轮换 OpenAlex / Semantic Scholar / NCBI key**——
打包前做泄漏扫描时，在 `qm_paper_search_shared/data/scripts/Set-ApiKey.ps1` 的**用法注释里发现了一个真实的 OpenAlex key**，
该处已在本次打包中替换为占位符。为确保安全，建议直接去 https://openalex.org/users/sign_up 重新生成 key。
（生成新 key 后用 `Set-ApiKey.ps1 -Provider openalex -Key "<NEW_KEY>"` 更新，或改用环境变量 `OPENALEX_API_KEY`。）

---

## 六、合规与学术边界

- **不爬 Google Scholar**（ToS 禁止自动化 + 结果不可复现）；替代路径见各 SKILL.md
- **不绕过付费墙**、不存储付费墙后的 PDF 原文、不镜像出版商数据库
- 引用必须以**原文献**为准；本工具输出仅作辅助，**不输出决策建议**
- 医学套件额外红线：**不替代临床判断、不输出用药/诊疗建议**；预印本必须标注 `[Preprint]`；
  查询含 13–18 位连续数字（疑似患者 ID）时**直接拒绝执行**
- 经济学套件额外红线：**不构成投资建议、不替代官方统计发布、不做政策立场输出**；禁止选择性引用；
  预印本/working paper 必须标注 `[Preprint]`；SSRN/NBER 专有条目须人工复核
- 数据源许可：OpenAlex / Crossref / PubMed 为 CC0 或公有领域；Europe PMC、预印本按各自 license 标注

---

## 七、版本

| Skill | 版本 | 日期 | 要点 |
|---|---|---|---|
| `qm_paper_search` | v0.4.1 | 2026-09-12 | fine+broad 合并；Quickstart；调用契约；代码化校验；跨 topic 去重；新增三源检索客户端 |
| `mbai_paper_search` | v0.4.0 | 2026-09-12 | fine+broad 合并；五源检索客户端；DOI+PMID 双校验；MeSH/证据等级/注册号字段 |
| `se_paper_search` | v0.1.0 | 2026-09-18 | 由化学孪生派生；arXiv 主链（免 key）；DOI+arXiv 双反查；期刊档位制替代分区/IF；working papers 纳入 broad |
| `paper-deep-reading` | v0.4 | 2026-09-12 | paper_type 7 类枚举；候选图片池 + 选取理由；OCR 兜底；作者/致谢/SI 溯源；字数自适应 |
| 历史归档 | — | 2026-09-08 ~ 09-09 | `*_broad` / `*_fine` / `v0.1_deprecated`，仅重定向与回溯 |

完整逐版本变更记录见各 skill 目录的 `CHANGELOG.md`（2026-09-18 起：原 SKILL.md 顶部 HTML 修订注释已迁出至此；paper-deep-reading 的原 §10 明细一并迁入）。

---

## 八、许可

本项目采用 **MIT License** —— 全文见 [LICENSE](./LICENSE)。你可以自由使用、修改、分发、商用，只需保留版权声明。

### 8.1 三类权利是分开的（重要）

| 对象 | 适用条款 |
|---|---|
| **代码**（`*.py` / `*.ps1`） | **MIT**（本仓库 `LICENSE`） |
| **文档与提示词**（`SKILL.md` / `README.md` / `assets/` / `references/`） | 同 MIT；如需以 CC-BY-4.0 单独发布可自行调整 |
| **第三方数据与 API 内容** | **不适用 MIT**。见下 |

### 8.2 第三方数据与 API 内容（不适用 MIT）

MIT 只覆盖本仓库的**代码与文档**，不覆盖下列内容的原始权利：

| 内容 | 权利归属 | 使用要求 |
|---|---|---|
| `*_shared/data/cas_journal_zones.json` 中的**中科院分区** | 中国科学院文献情报中心 | 手工整理的参考数据；**请以官方发布为准**，未经授权不得再分发或商用 |
| `se_paper_search_shared/data/se_journal_tiers.json` 中的**期刊档位** | 人工整理（经济学界通行口径） | 仅供排序参考，**不代表任何官方评价**；未收录期刊不标注 |
| 同文件中的**影响因子（IF / JIF）** | Clarivate 商标产品 | 同上；商用请自行获取授权 |
| OpenAlex / Crossref / PubMed 元数据 | CC0 / 公有领域 | 建议注明来源 |
| Semantic Scholar | 其 API 条款 | **限非商业用途** |
| Europe PMC / Europe PMC 预印本 / bioRxiv / medRxiv / arXiv | 各自 license（CC BY / CC BY-NC 等） | 引用时保留 license 信息 |

> 换言之：**MIT 授权的是"这套工具"，不是"通过它拿到的数据"。** 用本工具做商业用途前，请自行确认各数据源条款。
> 详见 [§六 合规与学术边界](#六合规与学术边界)。

### 8.3 免责声明

本软件按"现状"（AS IS）提供，不附带任何明示或暗示的担保。文献检索结果与阅读报告均由程序与模型自动生成，
**可能存在错误或遗漏**，不构成学术结论、临床建议或任何形式的专业意见；使用者应自行核对原始文献并承担使用风险。
`LICENSE` 中的责任限制条款适用于本项目，医学相关内容另见 [§六](#六合规与学术边界) 的临床红线。
