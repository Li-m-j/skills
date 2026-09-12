# qm_paper_search_shared — 共享数据层（v0.4.1）

> 给 `qm_paper_search`（化学主题单 skill）使用的数据 / 配置层。
> 与 `mbai_paper_search_shared`（医学/生信/AI 主题）**完全独立**，不共享数据；目录结构 / 文件命名 / 加载顺序与 mbai 对齐。

---

## 一、目录结构

```
qm_paper_search_shared/
├── README.md                          (本文件)
└── data/
    ├── cas_journal_zones.json         ← 化学顶刊白名单 + 分区 + 影响因子 + 预警名单
    ├── seen_papers.json               ← 去重池（topic_id 前缀 fine_/broad_）
    ├── user_prefs.json                ← 默认保存路径、用户偏好
    ├── api_keys.template.json         ← 团队共享模板（commit 入仓）
    ├── api_keys.local.json            ← 个人本地（gitignore）
    ├── api_logs.json                  ← API 调用日志（本地，90 天清理）
    ├── sample_broad.json              ← 粗放模式 JSON 样例（离线调试用）
    ├── README_API_KEYS.md             ← API key 管理文档
    ├── UPDATE_NOTES.md                ← 共享层变更记录
    ├── .gitignore
    └── scripts/
        ├── _lib_paths.ps1                ← 共享路径解析
        ├── qm_paper_search_setup.ps1     ← 首次配置向导
        ├── Set-ApiKey.ps1                ← 单个 key 管理
        ├── qm_openalex_to_md.ps1         ← JSON → Markdown 转换 + 方案 H 宽召回过滤
        ├── paper_search_client.py        ← ★ v0.4.1 检索客户端（推荐入口）
        └── validate_output.py            ← ★ v0.4.0 DOI 反查校验
```

---

## 二、谁会读这里

| 进程 / skill | 读什么 |
|---|---|
| `qm_paper_search` | `cas_journal_zones.json`（分区/IF/预警）、`seen_papers.json`（去重）、`user_prefs.json`（保存路径）、`api_keys.local.json` / 环境变量（限额） |
| `scripts/paper_search_client.py` | 上述全部 + 回写 `seen_papers.json`、追加 `api_logs.json` |
| `scripts/validate_output.py` | 无（仅向外请求 Crossref 做 DOI 反查） |
| 用户（首次配置） | `qm_paper_search_setup.ps1` 写入 `api_keys.local.json` |
| 用户（手动管理） | `Set-ApiKey.ps1` |

---

## 三、与 mbai_paper_search_shared 的关系

| 维度 | qm | mbai |
|---|---|---|
| 主题 | 化学 / 材料 / 催化 | 医学 / 生信 / AI |
| 顶刊 | JACS / Angew / Chem. Rev. | NEJM / Lancet / Nat. Mach. Intell. / Nat. Methods |
| 关键字段 | 期刊分区、IF、预警 | 同上 + 分类（临床/基础/生信/AI/综合） |
| 共享 API | OpenAlex / SS / Crossref | OpenAlex / PubMed / Europe PMC / SS / Crossref |
| Key 字段 | 2 个 | 4 个（+ NCBI key、Europe PMC email） |
| 去重键 | DOI | DOI + **PMID** |
| 数据文件 | 独立 | 独立（不共享 seen_papers / user_prefs / keys） |

两个 shared 互不影响，**同一台机器可同时安装**。

---

## 四、首次使用

```powershell
cd $env:USERPROFILE\.minimax\skills\qm_paper_search_shared\data\scripts
.\qm_paper_search_setup.ps1        # 输入 OpenAlex / Semantic Scholar key（可全部留空）
```

**推荐直接跑客户端**（一条命令完成检索 → 去重 → 导出 → 校验）：

```powershell
python paper_search_client.py -q "machine learning potential" --pretty --verify
```

---

## 五、变更记录

详见 `data/UPDATE_NOTES.md`。

### v0.4.1（2026-09-12）

- 新增 `scripts/paper_search_client.py`：三源检索（SS / OpenAlex / Crossref）+ 合并去重 + 方案 H 过滤 + seen 池读写 + Markdown 导出 + `--verify`。
- 修复 `scripts/validate_output.py` 的两个缺陷：f-string 引号错位导致的 SyntaxError；DOI 正则未排除 BibTeX 花括号导致的误抽（`doi = {10.x/y}` → `10.x/y}`）。
- 期刊匹配升级为 全名 / 缩写 / 首字母缩写 三级（`J. Am. Chem. Soc.` → `JACS` 可命中分区表）。
- 新增 `user_prefs.template.json`，并把 `seen_papers.json` / `user_prefs.json` / `api_logs.json` 明确写入 `.gitignore`。
