# 更新日志 (UPDATE_NOTES)

> 记录 se_paper_search skill 共享数据层的所有更新历史。**只增不删**。
> 本文件随 se_paper_search v0.1 新建；此前条目属 qm（化学）孪生的历史，不迁移。

---

## 2026-09-18 — v0.1.0 初始搭建

- **version**：v0.1.0
- **date**：2026-09-18
- **operator**：Mavis + user
- **scope**：
  - 从 `qm_paper_search_shared`（v0.4.1）派生统计经济学孪生共享层
  - 检索链改造：arXiv（econ.EM / stat.* 主渠道）→ OpenAlex → Semantic Scholar → Crossref
  - 校验器升级：DOI 反查 Crossref **＋ arXiv ID 反查 arXiv Export API**（双反查）
  - 分区表替换为期刊档位表 `se_journal_tiers.json`（经济 Top5 + 统计四大 + 金融 Top3 + 中文权威；IF 一律置空，避免编造数字）
  - 合并去重键：DOI（缺失时退回规范化标题）；`seen_papers.json` 池仍为 DOI-only（见已知限制）
  - HTTP 层新增 SSL 证书链验证失败兜底（本机 Windows 对 export.arxiv.org 缺中间证书）
  - `se_openalex_to_md.ps1`（JSON→MD 转换器）替换化学 ISSN→IF 表为经济/统计 ISSN→档位表
- **变更文件清单**：
  - 新增：`data/se_journal_tiers.json`（约 45 本期刊档位）
  - 新增：`data/scripts/paper_search_client.py`（四源检索客户端）
  - 新增：`data/scripts/validate_output.py`（DOI + arXiv 双反查）
  - 改名：`qm_openalex_to_md.ps1` → `se_openalex_to_md.ps1`，`qm_paper_search_setup.ps1` → `se_paper_search_setup.ps1`
  - 沿用：`Set-ApiKey.ps1`、`_lib_paths.ps1`（env 变量改 `SE_PAPER_SHARED_DIR`）
  - 更新：`api_keys.template.json`（新增 mailto_for_openalex 字段说明 + arXiv/Crossref 无 key 说明）
- **notes / 已知限制**：
  - 去重池以 DOI 为主键：仅有 arXiv ID 的预印本条目不参与跨检索去重（v0.2 候选改进）
  - arXiv 多词精确短语匹配过严：短语 0 命中时自动退回逐词 AND 再查（3s 礼仪间隔）
  - SSRN / NBER 编号页既无 DOI 也无 arXiv ID，无法机器反查，交付时必须人工复核
  - 预警名单目前为空：经济学暂无公认"预警期刊"名单，留待用户社区补充
