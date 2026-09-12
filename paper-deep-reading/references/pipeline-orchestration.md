# 检索 → 精读 → 存档：两个 skill 的流水线衔接（v0.4）

> 本文解决 `skill锐评.md` 的跨 skill 问题①"闭环没接上"与②"数据资产分散"。
> 适用：`qm_paper_search`（化学检索）+ `paper-deep-reading`（深度阅读报告），以及同构的 `mbai_paper_search_*`（医学/生信/AI）。

---

## 一、为什么需要衔接

两个 skill 单独都能跑，但连起来用会卡在三处：

| 断裂点 | 现象 | 本方案的接法 |
|---|---|---|
| 检索 → 精读 | 检索结果只有 DOI / 摘要，没有 PDF；要精读还得手工下载 | **Step A2 下载环节**：按 `open_access.oa_url` → Unpaywall → 预印本 → 用户自备，四级取 PDF |
| 精读 → 反查文献 | 读完想找"这篇的相关文献"，没有反向回路 | **Step C 反向检索**：用报告里的 DOI / 关键词回灌 `qm_paper_search`（带 `seen` 去重） |
| 产物分散 | 检索 md 在 `papers/`，报告在会话里，术语表在 references/ | **Step D 归档约定**：统一的 `papers/{search,reports,terms}` 结构 |

---

## 二、流水线定义（4 步）

```
① 检索（qm_paper_search）         →  papers/search/paper_search_*_<date>.md
        ↓ 选定 N 篇（DOI 列表）
② 取 PDF（4 级链路，合规优先）      →  papers/pdf/<doi-slug>.pdf
        ↓ 本地 PDF 路径
③ 精读（paper-deep-reading）      →  papers/reports/<doi-slug>_report.md
        ↓ 需要延伸
④ 反向检索 / 存档（可选）          →  回灌 ①（带 seen 去重）；报告回写 IMA 或 Obsidian
```

### Step A · 检索

```
用户：检索 单原子催化 综述，然后挑 3 篇最新的精读
```

Agent 动作：
1. 调 `qm_paper_search`（mode 自动推断为 broad）→ 得到 `paper_search_broad_<...>.md`
2. 跑 `validate_output.py` 确认 DOI 校验率 ≥ 95%
3. 从"详细条目"中按 `sort_by` + 用户偏好挑 N 篇，形成 DOI 清单

### Step B · 取 PDF（合规四级链路）

| 级别 | 来源 | 命令 / 方式 | 合规要求 |
|---|---|---|---|
| 1 | OpenAlex `open_access.oa_url` | 直接下载该 URL | 开放获取，允许 |
| 2 | Unpaywall 按 DOI 反查 OA 版本 | `GET https://api.unpaywall.org/v2/{doi}?email=<you>` | 仅取 OA 版本 |
| 3 | 预印本 | arXiv / ChemRxiv / bioRxiv 按标题检索 | 保留 license |
| 4 | 用户自备 / IMA 知识库 | 用户给本地路径，或 `ima://<media_id>` | **不绕过付费墙** |

- 全部失败 → 明确告知用户"该论文为付费墙内容，本工具不代抓"，并请其自行下载。
- 文件名规范化：`<一作姓氏>_<年份>_<doi后缀>.pdf`（去掉 `/` 等非法字符）。

### Step C · 精读

```
读一下 papers/pdf/smith_2025_10xxxx.pdf
```

Agent 动作：
1. 调 `paper-deep-reading` → 得到 7 模块 10 要点报告（或按 `paper_type` 走变体）
2. 报告中"关键图片候选池"由 AI 选取 3-5 张 + 写选取理由
3. 报告落盘 `papers/reports/<slug>_report.md`

### Step D · 反向检索与存档（可选）

- **反向检索**：以报告中的 DOI 作为种子，让 `qm_paper_search` 走 SS `/references` + `/citations`（引用图谱）找上下游文献；**注意把已读 DOI 写入 seen 池**，避免重复推荐。
- **存档**：
  - 报告 → IMA 知识库（`paper-deep-reading` Step 4.5）或 Obsidian；
  - 检索结果 → 保留在 `papers/search/`；
  - 术语 → `paper-deep-reading/references/term-glossary.md` 按升格规则累积。

---

## 三、推荐的目录结构

```
<你的论文工作区>\
├── search\      paper_search_fine_*.md / paper_search_broad_*.md
├── pdf\         <slug>.pdf
├── reports\     <slug>_report.md
└── terms\       （可选）按主题导出的术语快照
```

> `papers/` 路径来自 `qm_paper_search_shared/data/user_prefs.json` 的 `default_save_dir`；改路径用"换路径"。

---

## 四、统一输出约定（两个 skill 共用的 6 条）

| 约定 | 规则 |
|---|---|
| 元信息块 | 置于文件/报告开头，字段一行一个 `**字段**：值` |
| DOI 形式 | `[10.xxxx/yyy](https://doi.org/10.xxxx/yyy)` 可点击 |
| 来源标注 | 【原文】/【AI分析】/【推测】三色，全文一致 |
| 期刊标记 | 1区 / ⭐ Top / 🔴 预警 / [Preprint] / 🔒 付费墙（与 `cas_journal_zones.json` 一致） |
| 术语 | 首次出现给中英对照；全文译名统一（主表 > 参考表 > 临时表 > 自译） |
| 结论口径 | 只陈述事实 + 可核查链接；**不输出决策建议** |

---

## 五、一次串起来的完整示例

```
用户：帮我检索 单原子催化 的综述，然后精读其中最新的 2 篇

Agent：
1) [qm_paper_search] mode=broad，count=15 → papers/search/paper_search_broad_单原子催化_20260912.md
   → validate_output.py 校验率 97% ✅
2) 挑出 2 篇最新 review，逐个走 Step B 取 PDF
   - 第 1 篇 OA（OpenAlex oa_url）→ papers/pdf/wang_2025_10xxx.pdf
   - 第 2 篇付费墙 → 告知用户不代抓，请其提供 PDF
3) [paper-deep-reading] 读第 1 篇 → papers/reports/wang_2025_10xxx_report.md
   （review 变体，5 模块 8 要点；候选池 12 张 → 选 5 张 + 选取理由）
4) 询问是否回写 IMA；并建议"要不要用引用图谱找它的上游综述"
```

---

## 六、维护要点

- 两个 skill **版本需同步升级**（同一批改动里改），否则输出约定会漂移。
- 三端（minimax / TRAE / zcode）各有独立副本；改完一处需要同步拷贝（见 `minimax技能迁移安装报告.md`）。
- 每次改动跑各自 `assets/eval-checklist.md`。
