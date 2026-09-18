# se_paper_search_shared — 共享数据层（v0.1.0）

> 给 `se_paper_search`（统计科学 / 计量经济学 / 经济学主题单 skill）使用的数据 / 配置层。
> 与 `qm_paper_search_shared`（化学/材料）、`mbai_paper_search_shared`（医学/生信/AI）**完全独立**，
> 不共享数据；目录结构 / 文件命名 / 加载顺序与两者对齐（本目录由 qm 孪生 v0.4.1 派生改造）。

---

## 一、目录结构

```
se_paper_search_shared/
├── README.md                          (本文件)
└── data/
    ├── se_journal_tiers.json         ← 经济学/统计/金融期刊档位表（档/Tier，无 IF 数值）
    ├── seen_papers.json               ← 去重池（topic_id 前缀 fine_/broad_；gitignore，首次运行自动创建）
    ├── user_prefs.json                ← 默认保存路径、用户偏好（gitignore）
    ├── user_prefs.template.json       ← 上述文件的模板
    ├── api_keys.template.json         ← 团队共享模板（commit 入仓）
    ├── api_keys.local.json            ← 个人本地（gitignore）
    ├── api_logs.json                  ← API 调用日志（本地，90 天清理）
    ├── README_API_KEYS.md             ← API key 管理文档
    ├── UPDATE_NOTES.md                ← 共享层变更记录
    ├── .gitignore
    └── scripts/
        ├── _lib_paths.ps1                ← 共享路径解析（env: SE_PAPER_SHARED_DIR）
        ├── se_paper_search_setup.ps1     ← 首次配置向导
        ├── Set-ApiKey.ps1                ← 单个 key 管理
        ├── se_openalex_to_md.ps1         ← JSON → Markdown 转换 + 方案 H 宽召回过滤（遗留工具）
        ├── paper_search_client.py        ← ★ 四源检索客户端（推荐入口）
        └── validate_output.py            ← ★ DOI + arXiv ID 双反查校验
```

---

## 二、谁会读这里

| 进程 / skill | 读什么 |
|---|---|
| `se_paper_search` | `se_journal_tiers.json`（期刊档位）、`seen_papers.json`（去重）、`user_prefs.json`（保存路径）、`api_keys.local.json` / 环境变量（限额） |
| `scripts/paper_search_client.py` | 上述全部 + 回写 `seen_papers.json`、追加 `api_logs.json` |
| `scripts/validate_output.py` | 无（仅向外请求 Crossref / arXiv 做反查） |
| 用户（首次配置） | `se_paper_search_setup.ps1` 写入 `api_keys.local.json` |
| 用户（手动管理） | `Set-ApiKey.ps1` |

---

## 三、三个领域孪生的关系

| 维度 | qm（化学/材料） | mbai（医学/生信/AI） | **se（统计/经济）** |
|---|---|---|---|
| 主检索链 | SS → OpenAlex → Crossref | OpenAlex → PubMed/EM → SS → Crossref | **arXiv** → OpenAlex → SS → Crossref |
| 顶刊口径 | 中科院分区 + IF + 预警名单 | 同 qm + 临床期刊 | **档位制**：经济 Top5 / 统计四大 / 金融 Top3 / 中文权威（无 IF 数值） |
| 去重键 | DOI | DOI + PMID | DOI（arXiv-only 预印本暂不入池） |
| 反查校验 | DOI → Crossref | DOI → Crossref | DOI → Crossref **＋ arXiv ID → arXiv API** |
| 必需 key | 0（有则更快） | 0（可选 NCBI/EM） | **0**（arXiv/Crossref 免 key；OpenAlex/SS 可选） |

三个 shared 互不影响，**同一台机器可同时安装**。

---

## 四、首次使用

```powershell
cd se_paper_search_shared\data\scripts
.\se_paper_search_setup.ps1        # OpenAlex / Semantic Scholar key 均可留空（arXiv 免 key）
```

**推荐直接跑客户端**（一条命令完成检索 → 去重 → 导出 → 校验）：

```powershell
python paper_search_client.py -q "difference-in-differences treatment effects" --pretty --verify
```

- 精细模式（article-only，近 3 年）默认；`--mode broad` 为综述/工作论文宽召回。
- `--concept-pattern "causal|policy"` 启用方案 H 二次方向过滤。
- `--verify` 交付前自动做 DOI + arXiv ID 反查，合并通过率 < 95% 时退出码非 0。

---

## 五、变更记录

详见 `data/UPDATE_NOTES.md`。

### v0.1.0（2026-09-18）

- 从 qm 孪生 v0.4.1 派生：新增 arXiv 主渠道（econ.EM/econ.GN/econ.TH/stat.*/math.ST），
  精确短语 0 命中自动退回逐词 AND。
- `validate_output.py` 升级为 DOI + arXiv ID 双反查；阈值改按合并通过率。
- 期刊档位表 `se_journal_tiers.json` 替换 CAS 分区表；IF 置空防编造。
- HTTP 层加 SSL 证书链验证失败兜底（本机 Windows 缺 arXiv 中间证书场景）。
