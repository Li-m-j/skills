# mbai_paper_search_fine — README（历史归档）

> ⚠️ **本 skill 已于 2026-09-12 合并入单 skill `mbai_paper_search` v0.4.0。**
>
> - **请改用**：`文献检索 X`（mode 自动推断）／ `精细检索 X`（显式）
> - **新位置**：[`../mbai_paper_search/`](../mbai_paper_search/)（[SKILL.md](../mbai_paper_search/SKILL.md) · [README.md](../mbai_paper_search/README.md)）
> - **重定向说明**：[`DEPRECATED.md`](./DEPRECATED.md)
>
> 本目录的 `SKILL.md` 仅作 v0.2 历史归档，不再被 skill 系统加载。

---

## 原 v0.2 内容摘要（供回溯）

- 触发：`精细文献检索 X` / `mbai_paper_search_fine X`（默认在没有"粗放/概览"时生效）
- 默认：article-only、10 篇、近 3 年、相关度排序、引用图谱开
- 数据源：OpenAlex（主）→ PubMed E-utilities → Europe PMC → Semantic Scholar → Crossref
- 医学扩展字段：MeSH 主题词 / 临床试验注册号 / 证据等级
- 一站式脚本：`mbai_search_and_export.ps1 -Mode fine`（v0.2，33 KB）
- 去重池：`seen_papers.json` 的 `fine_*` topic（v0.4.0 继续识别）

完整 v0.2 定义见本目录 [`SKILL.md`](./SKILL.md)。
