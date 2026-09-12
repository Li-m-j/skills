# qm_paper_search — 化学领域学术文献检索 skill（README · v0.4.1）

> 统一 skill：原 `qm_paper_search_fine`（v0.2.3）+ `qm_paper_search_broad`（v0.2.2）已于 v0.3.0 合并；
> v0.4.0 补齐 Quickstart、调用契约、代码化校验与统一输出规范；v0.4.1 补上零依赖 **Python 检索客户端**。
>
> 面向用户的完整定义见 [`SKILL.md`](./SKILL.md)；本文件是**用户视角的操作说明**。

---

## 一、30 秒上手

```powershell
# 1) 配 key（可全部留空跳过）
cd $env:USERPROFILE\.minimax\skills\qm_paper_search_shared\data\scripts
.\qm_paper_search_setup.ps1

# 2) 直接说人话触发（无需记命令）
#    "文献检索 machine learning potential"
#    "粗放检索 单原子催化 综述"
```

产出：`<default_save_dir>\paper_search_{fine|broad}_<query>_<YYYYMMDD>.md`

### 一条命令跑完整链路（v0.4.1 推荐）

```powershell
cd $env:USERPROFILE\.minimax\skills\qm_paper_search_shared\data\scripts

# 精细：近 3 年 / article / 10 篇，导出后自动做 DOI 校验
python paper_search_client.py -q "machine learning potential" --pretty --verify

# 粗放：综述为主 / 时间不限 / 15 篇 + 方案 H 方向过滤
python paper_search_client.py -q "钙钛矿太阳能电池" --mode broad `
    --concept-pattern "perovskite|solar[ ]cell" --pretty --verify

# 试跑不落盘 / 另存原始 JSON
python paper_search_client.py -q "MOF 气体分离" --count 20 --dry-run --json-out raw.json
```

脚本内部依次完成：三源检索（SS→OpenAlex→Crossref）→ 合并去重 → 方案 H 过滤 → 去重池读写 → Markdown 导出 → DOI 校验。
**交付前自检**（未用 `--verify` 时手动跑）：

```powershell
python validate_output.py "C:\...\paper_search_broad_xxx_20260912.md" --pretty
```

---

## 二、触发方式

| 你想做的事 | 触发说法 | 推断模式 |
|---|---|---|
| 已知方向深度调研 | `文献检索 MLP` / `精细检索 COF 催化 近 3 年` | 精细（fine） |
| 新领域摸底 / 找综述 | `文献检索 概览 钙钛矿` / `粗放检索 单原子催化 综述` | 粗放（broad） |
| 显式指定 | `精细检索 X` / `粗放检索 X` | 显式覆盖 |
| 数量 / 年份 | `文献检索 MOF 找 20 篇 近 5 年` | 跟随当前模式 |
| 引用图谱 | `文献检索 CO2 还原 查引用` | 跟随当前模式 |

### 自动模式推断

- 命中 `概览 / 立项 / 综述 / 摸底 / survey / landscape / 全景 / review` → **粗放**
- 命中 `深度 / 方法 / 创新 / 对比 / 复现` → **精细**
- 都不命中 → **精细**（默认）

---

## 三、参数

| 参数 | 精细默认 | 粗放默认 | 可选值 |
|---|---|---|---|
| 文献类型 `type` | article-only | review-only | article / review / all / mixed / letter |
| 篇数 `count` | 10 | **15** | 1-100（粗放建议 10-25） |
| 时间 `years` | 近 3 年 | 不限 | 1-10 / 不限 |
| 期刊严格度 | strict | loose | strict / loose |
| 排序 | 相关度 | 时间+被引 | relevance / time / citations / time+citations |
| 引用图谱 | on | on | on / off |
| 摘要主源 | ss | ss | ss / crossref / openalex / xmol |
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
  - 📋 速览表（标题 / 作者 / 年份 / DOI）+ 统计行（Top / 1区 / 预警 / Preprint / 跳过重复）
  - 📚 详细条目（9 个核心字段 + 4 种引用格式折叠）
- **9 个核心字段**：作者 / 年份 / 期刊 / 影响因子 / DOI / 关键词 / 摘要原文 / TLDR（AI 总结）/ 标记
- **4 种引用格式**：BibTeX / APA 7 / GB/T 7714 / RIS

---

## 五、数据源与合规

| 顺位 | 源 | 角色 |
|---|---|---|
| 1 | Semantic Scholar | **主检索源**（发现论文） |
| 2 | Crossref | **元数据权威**（DOI 反查 / 卷期页） |
| 3 | OpenAlex | **覆盖兜底**（concepts / OA 链接） |
| 4 | X-Mol | 中文友好跳转（不入结构化字段） |

- **不爬 Google Scholar**（合规 + 稳定性 + 可复现），替代路径见 SKILL §3.4。
- 反幻觉：所有字段 only from API，缺则 `N/A`；交付前用 `validate_output.py` 做 DOI 级校验。

---

## 六、目录结构

```
qm_paper_search/
├── SKILL.md       (skill 主定义，v0.4.0)
├── README.md      (本文件)
└── assets/
    └── eval-checklist.md

%USERPROFILE%\.minimax\skills\qm_paper_search_shared\data\
├── api_keys.template.json      (团队共享模板，commit)
├── api_keys.local.json         (个人本地，gitignore，不 commit)
├── cas_journal_zones.json      (中科院分区 + IF，年度更新)
├── seen_papers.json            (去重池，topic_id 分 fine_/broad_ 组)
├── user_prefs.json             (default_save_dir)
├── api_logs.json               (本地调用日志，90 天清理)
├── sample_broad.json           (粗放 JSON 样例)
├── README_API_KEYS.md / UPDATE_NOTES.md / .gitignore
└── scripts/
    ├── _lib_paths.ps1
    ├── Set-ApiKey.ps1
    ├── qm_paper_search_setup.ps1
    ├── qm_openalex_to_md.ps1
    ├── paper_search_client.py     (★ v0.4.1 检索客户端)
    └── validate_output.py
```

---

## 七、开发规范

- frontmatter 必填：`name` / `version` / `description`
- **每次改 SKILL.md 必须同步更新 README.md 与本文件**，并在 SKILL.md §13 版本表追加一行
- version 遵循 semver；**对外只暴露一个版本号**（v0.3.0 起不再有 fine/broad 双版本）
- 反幻觉：规则改动必须同时在 `validate_output.py` 或调用契约（SKILL §3.2）中可验证

---

## 八、常见问题

| 问题 | 处理 |
|---|---|
| 摘要显示 `N/A` | 出版商屏蔽，规则禁止 AI 兜底；点 DOI 到原页取（SKILL §11.6） |
| 为什么没有 Google Scholar？ | 合规/稳定性原因，替代路径见 SKILL §3.4 |
| 第二次检索篇数变少 | 去重池生效（SKILL §5.2，含跨 topic 合并去重） |
| 粗放检索很慢 | 15 篇 + 引用图谱约 5-10 分钟；可 `citation_graph=off` 或减 count |
| key 失效怎么办 | 按提示语运行 `Set-ApiKey.ps1 -Provider <源> -Key <NEW>`；会自动回退无 key 模式 |
| 想检查结果真假 | `python validate_output.py <文件> --pretty`（DOI 反查） |
| 非化学主题 | 化学以外的医学/生信/AI 请用 `mbai_paper_search` |

---

## 九、变更记录

| 版本 | 日期 | 说明 |
|---|---|---|
| **0.4.1** | 2026-09-12 | 新增 `paper_search_client.py`（零依赖检索客户端，一键交付 + `--verify`）；修复 `validate_output.py` 的 f-string 语法错误与 BibTeX 花括号 DOI 误抽 |
| 0.4.0 | 2026-09-12 | 补 Quickstart / 调用契约 / 代码化校验 / GS 替代路径 / 面向用户错误模板；粗放 count 25→15；统一输出约定 |
| 0.3.0 | 2026-09-12 | fine + broad 合并为单 skill；统一触发词"文献检索 X"，mode 自动推断 |
| 0.2.3 | 2026-09 | 精细：key 个体管理；出版商屏蔽不再用 AI 总结兜底 |
| 0.2.2 | 2026-09 | 粗放：方案 H 宽召回；SS 作为粗放主源 |
| 0.2.1 | 2026-09 | 主源从 Google Scholar 切到 OpenAlex |
| 0.2 | 2026-09-08 | 从 v0.1 拆分为 fine + broad |
| 0.1 | 2026-09-08 | 初版（已弃用，归档于 `qm_paper_search_v0.1_deprecated/`） |
