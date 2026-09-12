# mbai_paper_search_shared — 共享数据层（v0.4.0）

> 给 `mbai_paper_search`（单 skill，v0.4.0 起 fine + broad 已合并）使用的数据 / 配置层。
> 与 `qm_paper_search_shared`（化学主题）**完全独立**，不共享数据；目录结构 / 文件命名 / 加载顺序与 qm 对齐。

---

## 一、目录结构

```
mbai_paper_search_shared/
├── README.md                          (本文件)
└── data/
    ├── cas_journal_zones.json         ← 顶刊白名单 + 分区 + 影响因子 + 分类 + 预警
    ├── seen_papers.json               ← 去重池（topic_id 前缀 fine_/broad_；seen_dois + seen_pmids）
    ├── user_prefs.json                ← 默认保存路径、用户偏好
    ├── api_keys.template.json         ← 团队共享模板（commit 入仓）
    ├── api_keys.local.json            ← 个人本地（gitignore）
    ├── api_logs.json                  ← API 调用日志（本地，500 条上限）
    ├── README_API_KEYS.md             ← API key 管理文档
    ├── UPDATE_NOTES.md                ← 共享层变更记录
    ├── .gitignore
    └── scripts/
        ├── mbai_paper_search_setup.ps1   ← 首次配置向导
        ├── Set-ApiKey.ps1                ← 单个 key 管理
        ├── mbai_openalex_to_md.ps1       ← OpenAlex JSON → Markdown 转换器（v0.1，保留）
        ├── mbai_search_and_export.ps1    ← v0.2 一站式 PowerShell 入口（保留向后兼容）
        ├── paper_search_client.py        ← ★ v0.4.0 五源检索客户端（推荐入口）
        └── validate_output.py            ← ★ v0.4.0 DOI + PMID 反查校验
```

---

## 二、谁会读这里

| 进程 / skill | 读什么 |
|---|---|
| `mbai_paper_search` | `cas_journal_zones.json`（分区/分类/预警）、`seen_papers.json`（去重）、`user_prefs.json`（保存路径）、`api_keys.local.json` / 环境变量（限额） |
| `scripts/paper_search_client.py` | 上述全部 + 回写 `seen_papers.json`、追加 `api_logs.json` |
| `scripts/validate_output.py` | 无（仅向外请求 Crossref / PubMed 做反查） |
| 用户（首次配置） | `mbai_paper_search_setup.ps1` 写入 `api_keys.local.json` |
| 用户（手动管理） | `Set-ApiKey.ps1` |

---

## 三、与 qm_paper_search_shared 的关系

| 维度 | qm | mbai |
|---|---|---|
| 主题 | 化学 | 医学 / 生信 / AI |
| 顶刊 | JACS / Angew / Chem. Rev. | NEJM / Lancet / Nat. Mach. Intell. / Nat. Methods / ... |
| 关键字段 | 期刊分区、IF | 同上 + 分类（临床/基础/生信/AI/综合）+ 预警 |
| 共享 API | OpenAlex / SS / Crossref | OpenAlex / PubMed / Europe PMC / SS / Crossref |
| Key 字段 | 2 个 | 4 个（+ NCBI key、Europe PMC email） |
| 去重键 | DOI | DOI + **PMID** |
| 数据文件 | 独立 | **独立**（不与 qm 共享 seen_papers / user_prefs / keys） |

两个 shared 互不影响，**同一台机器可同时安装**。

---

## 四、首次使用

```powershell
cd $env:USERPROFILE\.minimax\skills\mbai_paper_search_shared\data\scripts
.\mbai_paper_search_setup.ps1
```

按提示填入 OpenAlex / Semantic Scholar / NCBI key 与 Europe PMC email（**全部可留空**，无 key 也能跑，只是限流更严）。

**推荐直接跑客户端**（一条命令完成检索 → 去重 → 导出 → 校验）：

```powershell
python paper_search_client.py -q "PD-1 inhibitor NSCLC" --pretty --verify
```

---

## 五、变更记录

详见 `data/UPDATE_NOTES.md`。

### v0.4.0（2026-09-12）

- 新增 `scripts/paper_search_client.py`：五源检索（SS / OpenAlex / PubMed / Europe PMC / Crossref）+ 合并去重 + 方案 H 过滤 + seen 池读写 + Markdown 导出 + `--verify`。
- 新增 `scripts/validate_output.py`：DOI（Crossref）+ PMID（PubMed esummary）双反查校验。
- 服务对象由 fine + broad 双 skill 变为单 skill `mbai_paper_search`（两旧目录已标 DEPRECATED，数据与脚本全部保留）。
- `seen_papers.json` 结构不变；`seen_pmids` 字段继续维护。
