# se_paper_search — 统计经济学文献检索 skill（README · v0.1.0）

> 统一 skill：fine/broad 双模式，mode 由查询关键词自动推断（与 qm/mbai 孪生同构）。
> v0.1.0 由 `qm_paper_search` v0.4.1 派生改造：新增 arXiv 主渠道、DOI+arXiv ID 双反查、
> 期刊档位表（替代 CAS 分区）、工作论文口径。
>
> 面向 Agent 的完整定义见 [`SKILL.md`](./SKILL.md)；本文件是**用户视角的操作说明**。

---

## 一、30 秒上手

```powershell
# 1) 配 key（arXiv/Crossref 免 key，可全部留空跳过）
cd $env:USERPROFILE\.minimax\skills\se_paper_search_shared\data\scripts
.\se_paper_search_setup.ps1

# 2) 直接说人话触发（无需记命令）
#    "文献检索 difference-in-differences"
#    "粗放检索 因果推断 综述"
```

产出：`<default_save_dir>\paper_search_{fine|broad}_<query>_<YYYYMMDD>.md`

### 一条命令跑完整链路（推荐）

```powershell
cd $env:USERPROFILE\.minimax\skills\se_paper_search_shared\data\scripts

# 精细：近 3 年 / article / 10 篇，导出后自动做 DOI + arXiv 双反查
python paper_search_client.py -q "difference-in-differences treatment effects" --pretty --verify

# 粗放：综述+工作论文 / 时间不限 / 15 篇 + 方案 H 方向过滤
python paper_search_client.py -q "machine learning causal inference" --mode broad `
    --concept-pattern "causal|treatment[ ]effect" --pretty --verify

# 试跑不落盘 / 另存原始 JSON / 裁剪 arXiv 分类
python paper_search_client.py -q "panel data" --count 20 --dry-run --json-out raw.json
python paper_search_client.py -q "bayesian econometrics" --arxiv-cats "econ.EM,stat.ME"
```

脚本内部依次完成：四源检索（arXiv→OpenAlex→SS→Crossref）→ 合并去重 → 方案 H 过滤 → 去重池读写 → Markdown 导出 → 双反查校验。
**交付前自检**（未用 `--verify` 时手动跑）：

```powershell
python validate_output.py "C:\...\paper_search_broad_xxx_20260918.md" --pretty
```

---

## 二、触发方式

| 你想做的事 | 触发说法 | 推断模式 |
|---|---|---|
| 已知方向深度调研 | `文献检索 regression discontinuity` / `精细检索 双重差分 近 3 年` | 精细（fine） |
| 新领域摸底 / 找综述 | `文献检索 概览 高维统计` / `粗放检索 劳动经济学 综述` | 粗放（broad） |
| 显式指定 | `精细检索 X` / `粗放检索 X` | 显式覆盖 |
| 数量 / 年份 | `文献检索 IV 找 20 篇 近 5 年` | 跟随当前模式 |
| 引用图谱 | `文献检索 synthetic control 查引用` | 跟随当前模式 |

### 自动模式推断

- 命中 `概览 / 立项 / 综述 / 摸底 / survey / landscape / 全景 / review / handbook` → **粗放**
- 命中 `深度 / 方法 / 创新 / 对比 / 复现 / 估计量 / 识别` → **精细**
- 都不命中 → **精细**（默认）

> 注意：粗放模式的候选池在经济学口径下**包含工作论文/预印本**（arXiv 首发是该领域常态）。

---

## 三、参数

| 参数 | 精细默认 | 粗放默认 | 可选值 |
|---|---|---|---|
| 文献类型 `type` | article-only | 综述+工作论文 | article / review / all / mixed |
| 篇数 `count` | 10 | **15** | 1-100（粗放建议 10-25） |
| 时间 `years` | 近 3 年 | 不限 | 1-10 / 不限 |
| arXiv 分类 | 全 10 类 | 同左 | econ.EM/GN/TH, stat.ME/AP/ML/TH/CO/OT, math.ST |
| 期刊严格度 | strict | loose | strict / loose |
| 排序 | 相关度 | 时间+被引 | relevance / time / citations / time+citations |
| 引用图谱 | on | on | on / off |
| 摘要主源 | ss | ss | ss / crossref / openalex / arxiv |
| TLDR | optional | optional | required / optional / off（质量警告见 SKILL §4.3） |
| 宽召回 `concept_pattern` | — | 空 | regex（粗放专属，方案 H） |

### 显式命令

| 命令 | 行为 |
|---|---|
| "新方向：XXX" | 新建研究方向 |
| "清空当前方向记忆" | 清空当前 topic 的 seen_dois |
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
  - 📋 速览表（标题 / 作者 / 年份 / DOI）+ 统计行（Tier-1 / Preprint / 跳过重复 / 方向过滤剔除）
  - 📚 详细条目（核心字段含 **arXiv 行** + 4 种引用格式折叠）
- **核心字段**：作者 / 年份 / 期刊（档位） / DOI / arXiv / 卷期页 / 关键词 / 摘要原文 / TLDR（AI 总结）/ 标记
- **4 种引用格式**：BibTeX / APA 7 / GB/T 7714 / RIS

---

## 五、数据源与合规

| 顺位 | 源 | 角色 | 需要 key？ |
|---|---|---|---|
| 1 | arXiv Export API | **预印本主渠道**（econ.EM / stat.* / math.ST） | ❌ 免 key（礼仪限速 1 req/3s） |
| 2 | OpenAlex | 覆盖主链（期刊文献发现 + concepts + OA 链接） | 可选（带 key 提速 10 倍） |
| 3 | Semantic Scholar | 引用数 / TLDR / 引用图谱 | 可选 |
| 4 | Crossref | **元数据权威**（DOI 反查 / 卷期页） | ❌ 免 key（建议 mailto） |

- **不爬 Google Scholar**（合规 + 稳定性 + 可复现），替代路径见 SKILL §3.4；SSRN/NBER 无公开 API，编号页条目需人工复核。
- 反幻觉：所有字段 only from API，缺则 `N/A`；交付前用 `validate_output.py` 做 **DOI + arXiv ID 双反查**。
- 领域红线：**不构成投资建议、不替代官方统计发布、工作论文必须显式标注**（SKILL §9）。

---

## 六、目录结构

```
se_paper_search/
├── SKILL.md       (skill 主定义，v0.1.0)
├── CHANGELOG.md   (修订记录)
├── README.md      (本文件)
├── assets/
│   └── eval-checklist.md
└── references/
    ├── google-scholar-alternatives.md
    ├── legal-compliance.md
    ├── api-limits.md
    └── api-key-management.md

%USERPROFILE%\.minimax\skills\se_paper_search_shared\data\
├── api_keys.template.json      (团队共享模板，commit)
├── api_keys.local.json         (个人本地，gitignore，不 commit)
├── se_journal_tiers.json       (经济学/统计/金融期刊档位表，无 IF)
├── seen_papers.json            (去重池，topic_id 分 fine_/broad_ 组，gitignore)
├── user_prefs.json             (default_save_dir，gitignore)
├── api_logs.json               (本地调用日志，90 天清理，gitignore)
├── README_API_KEYS.md / UPDATE_NOTES.md / .gitignore
└── scripts/
    ├── _lib_paths.ps1
    ├── Set-ApiKey.ps1
    ├── se_paper_search_setup.ps1
    ├── se_openalex_to_md.ps1        (JSON → Markdown，遗留工具)
    ├── paper_search_client.py       (★ 四源检索客户端)
    └── validate_output.py           (★ DOI + arXiv 双反查)
```

---

## 七、开发规范

- frontmatter 必填：`name` / `version` / `description`
- **每次改 SKILL.md 必须同步更新 README.md**，修订写进 `CHANGELOG.md`（代码级修复不升版本号）
- version 遵循 semver；只暴露一个版本号
- 反幻觉：规则改动必须同时在 `validate_output.py` 或调用契约（SKILL §3.2）中可验证
- 三个领域孪生（qm/mbai/se）代码近似但**独立维护**（用户决定不合并）；修共享逻辑类 bug 时记得逐个检查

---

## 八、常见问题

| 问题 | 处理 |
|---|---|
| 中文查询 0 命中 | arXiv/OpenAlex/SS 全文检索仅支持英文，改英文关键词重试（脚本会自动提示） |
| 某篇没有 DOI 只有 arXiv ID | 正常——经济学工作论文常态；校验器会走 arXiv 反查 |
| 某篇 DOI 和 arXiv ID 都没有 | SSRN/NBER 编号页，无法机器反查，交付时已标 ⚠️ 需人工复核 |
| 摘要显示 `N/A` | 出版商屏蔽，规则禁止 AI 兜底；点 DOI/arXiv 链接到原页取 |
| 为什么不报影响因子 | 经济/统计期刊采用**档位制**（Top5/统计四大等），IF 数值易过时失真，一律 N/A |
| 第二次检索篇数变少 | 去重池生效（SKILL §5.2）；arXiv-only 预印本暂不入池，可能重复出现 |
| 粗放检索很慢 | arXiv 礼仪限速 1 req/3s 所致；约 3-8 分钟，可 `citation_graph=off` 或减 count |
| key 失效怎么办 | 按提示语运行 `Set-ApiKey.ps1 -Provider <源> -Key <NEW>`；自动回退无 key 模式 |
| 想检查结果真假 | `python validate_output.py <文件> --pretty`（DOI + arXiv 双反查） |
| 非统计/经济主题 | 化学/材料 → `qm_paper_search`；医学/生信/AI → `mbai_paper_search` |

---

## 九、变更记录

见 [`CHANGELOG.md`](./CHANGELOG.md)。当前 **v0.1.0**（2026-09-18 首发）。
