# se_paper_search — 评测清单（eval suite）

> 用途：让"改一行 SKILL.md 是否变好/变坏"可被**观察到**。skill 的 prompt 层没有自动化测试，
> 因此用「gold 查询 + 可核查的判定标准」做回归评测。
>
> 每次改动 SKILL.md / 脚本后，跑一遍下表并记录结果（建议追加到 `_eval/YYYY-MM-DD.md`）。

---

## 一、评测方法

1. 固定用同一份 `user_prefs.json` 的 `default_save_dir`，并在每次评测前把 `seen_papers.json` 备份后清空（避免去重干扰）。
2. 按下表逐条发起检索，得到 `.md` 输出。
3. 逐条勾选验收项（A/B/C 三组）。
4. 全 A 组通过才算"可用"；A+B 通过才算"可交付"；C 组用于诊断回归。

---

## 二、A 组 · 硬性正确性（必须 100% 通过）

| # | 检查项 | 判定方式 |
|---|---|---|
| A1 | 标识符真实可查 | `python validate_output.py <文件> --pretty --threshold 0.95` 退出码 = 0（DOI→Crossref 与 arXiv ID→arXiv 双反查，合并通过率 ≥95%） |
| A2 | 无编造字段 | 抽查 3 条：作者 / 年份 / 卷期页 与 Crossref/arXiv 响应一致；缺失项为 `N/A` 而非补全；**无编造 IF、无凭印象补"经典文献"** |
| A3 | 摘要为原文 | 逐条确认 `摘要原文` 长度 > 200 字符且非 snippet（不出现 "…" 截断结尾） |
| A4 | TLDR 标注 | 每条 TLDR 均带"（AI 总结）"字样 |
| A5 | 输出命名与位置 | 文件名符合 `paper_search_{fine|broad}_<query>_<YYYYMMDD>.md`，落在 `default_save_dir` |
| A6 | 引用格式 4 件套 | 每条含 BibTeX / APA 7 / GB/T 7714 / RIS 四个折叠块，且 BibTeX 可解析 |
| A7 | 预印本标注 | 所有 `is_preprint` 条目带 `[Preprint arXiv:…]` 标记，未被渲染为正式发表 |

## 三、B 组 · 交付质量（应通过）

| # | 检查项 | 判定方式 |
|---|---|---|
| B1 | 模式推断正确 | §5.1 示例 query（含 handbook→broad、估计量/识别→fine）全部推断正确 |
| B2 | 参数生效 | "找 20 篇" / "近 5 年" / "--arxiv-cats econ.EM" 均在输出中如实体现 |
| B3 | 去重透明 | 速览行注明"已跳过重复 N 篇"；跨 topic 场景注明来源 pool |
| B4 | 期刊档位正确 | 命中的 Tier 1 / ⭐ Top / [Preprint] 标记与 `se_journal_tiers.json` 一致；影响因子一律 `N/A` |
| B5 | 元信息块 | 7 个字段齐全且顺序符合 §6.1；数据源列表与实到源一致 |
| B6 | 失败语义正确 | 未见 abstract 的条目为 `N/A（出版商屏蔽…）` 而非空；无 DOI 条目有 arXiv 行或 ⚠️ 人工复核标注 |

## 四、C 组 · 回归诊断（用于定位退化点）

| # | 检查项 | 判定方式 |
|---|---|---|
| C1 | 粗放宽召回生效 | `concept_pattern` 命中数 = N 时，输出注明"过滤后 N 篇"；broad 结果含综述**与**工作论文 |
| C2 | 限流行为 | 人为设错 key → 输出一条 401 提示 + 自动回退（不阻塞） |
| C3 | 全部源失败路径 | 断网跑一次 → 输出 §7.1 的"全部数据源失败"话术，而非静默空文件 |
| C4 | 非经济/统计主题 | 用"分子催化 COF"触发 → 输出二次确认话术并建议 qm_paper_search |
| C5 | 中文 query 提示 | 纯中文查询 → 明确提示"检索源仅支持英文"并给英译建议 |
| C6 | arXiv 降级 | `--sources openalex,crossref` 时报告头部声明 arXiv 未参与；单源挂掉时逐源降级话术正确 |
| C7 | arXiv 礼仪 | 抓包/日志确认相邻 arXiv 请求间隔 ≥3s，fallback 逐词 AND 查询也遵守 |

---

## 五、Gold 查询集（固定，便于跨版本比对）

| # | 查询 | 期望模式 | 期望要点 |
|---|---|---|---|
| G1 | `文献检索 difference-in-differences treatment effects` | fine | article-only、10 篇、近 3 年、arXiv+下游源合并 |
| G2 | `文献检索 概览 高维统计推断` | broad | 综述+工作论文、15 篇、时间不限 |
| G3 | `文献检索 因果推断机器学习中 handbook 综述` | broad | 命中 handbook/review |
| G4 | `文献检索 regression discontinuity design` | fine | 英文 query 不误判；含 Journal of Econometrics/AER 类条目 |
| G5 | `文献检索 synthetic control method 对比` | fine | 命中"对比" |
| G6 | `精细检索 panel data estimator 近 5 年 找 20 篇` | fine | 参数覆盖生效 |
| G7 | `文献检索 贝叶斯计量经济学` | — | 中文 0 命中 → 触发 C5 提示路径或 OpenAlex 英文回退命中 |
| G8 | `文献检索 bayesian econometrics`（脚本加 `--arxiv-cats econ.EM,stat.ME`） | fine | 分类裁剪生效，无 stat.ML 混入 |

---

## 六、记录模板

```
## 评测记录 YYYY-MM-DD · skill vX.Y.Z
- 环境：network=ok / keys=none / python=3.13
- A 组：A1 ✅  A2 ✅  A3 ✅  A4 ✅  A5 ✅  A6 ✅  A7 ✅   → A 通过
- B 组：B1 ✅  B2 ⚠️(B2 篇数未体现)  ……                  → B 6/6
- C 组：C1 ✅  C2 ✅  C3 ✅  C4 ✅  C5 ✅  C6 ✅  C7 ✅
- 结论：可交付。
- 退化点：无 / <描述>
- 备注：<本次改动点>
```
