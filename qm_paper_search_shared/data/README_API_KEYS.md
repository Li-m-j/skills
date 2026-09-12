# qm_paper_search - API key 管理指南

> 团队共享代码 + 个人本地 key。每个成员独立管理自己的 key，不上传到 git/共享目录。

## 🤔 两种做法的差异

| 维度 | ✅ 使用 API | ❌ 不使用 API |
|---|---|---|
| **OpenAlex 限流** | 50 req/s（带 key） | 5 req/s（无 key，共享 IP） |
| **Semantic Scholar 限流** | 100 req/min（带 key） | 共享 IP 100 req/min（多人共用易 429） |
| **检索速度** | 每次 ~1-2 秒 | 每次 ~3-10 秒（受限流拖累） |
| **引用图谱** | ✅ 可跑（5-10 req/篇） | ⚠️ 容易 429 |
| **大量主题检索** | ✅ 流畅 | ⚠️ 慢且需 sleep |
| **粗放模式 25 篇** | ✅ 顺畅 | ⚠️ 多次 429 要等 |
| **key 申请** | ❌ 需 5 分钟申请 | ✅ 0 配置 |
| **适合场景** | 频繁使用 / CI/CD / 团队 | 偶尔用 / 体验 / 试用 |

> 💡 **建议**：长期用 → 申请 key；试一下 → noapi 模式也跑得通。

## 📂 目录结构

```
qm_paper_search_shared/data/
├── api_keys.template.json     ← 团队共享（commit 到 git）
├── api_keys.local.json        ← 个人本地（**不** commit，加入 .gitignore）
├── scripts/
│   ├── Set-ApiKey.ps1        ← key 管理脚本
│   └── qm_paper_search_setup.ps1  ← 首次初始化
└── ...
```

## 🚀 首次使用（新用户向导）

```powershell
# 在 shared/data/scripts/ 目录下：
.\qm_paper_search_setup.ps1
```

向导会问你两个问题：
1. **使用 API 吗？** —— 详细对比见上方"两种做法的差异"
2. **输入 key 吗？** —— 可留空跳过

非交互模式（CI/CD）：

```powershell
# 完整 API 模式
.\qm_paper_search_setup.ps1 -Mode api -OpenAlexKey "l1..." -SSKey "abc..."

# 只 OpenAlex，不 SS
.\qm_paper_search_setup.ps1 -Mode api -OpenAlexKey "l1..."

# 无 API 模式（最简）
.\qm_paper_search_setup.ps1 -Mode noapi
```

## 🔑 后续管理

```powershell
# 查看当前 key 状态
.\Set-ApiKey.ps1 -List

# 更新 OpenAlex key
.\Set-ApiKey.ps1 -Provider openalex -Key "NEW_KEY"

# 改用环境变量（删除 local key）
.\Set-ApiKey.ps1 -Provider openalex -EnvVar

# 删除 key
.\Set-ApiKey.ps1 -Provider openalex -Remove

# 验证 key 有效性（401/403/429 都报告）
.\Set-ApiKey.ps1 -Validate
```

## 🔍 读取优先级

skill 读取 API key 的顺序：

1. **`api_keys.local.json`** （个人本地，最优先）
2. **环境变量** `OPENALEX_API_KEY` / `SEMANTIC_SCHOLAR_API_KEY`（User 级别）
3. **不使用 key**（限流低但能跑）

`api_keys.template.json` 是占位符，**不会被读**。

## 🛡️ 安全约束

- **不要**把 `api_keys.local.json` 加入 git 仓库
- **不要**在聊天/邮件/截图中分享 key
- **不要**把 key 写在代码注释里
- ✅ key 失效时（401/403）用 `Set-ApiKey.ps1 -Validate` 验证并更新
- ✅ 团队成员各自 `qm_paper_search_setup.ps1` 一次

## 📋 申请地址

| Provider | 申请 URL | 限流 |
|---|---|---|
| OpenAlex | https://openalex.org/users/sign_up | 带 key 50 req/s，无 key 5 req/s |
| Semantic Scholar | https://www.semanticscholar.org/product/api | 带 key 100 req/min，共享 IP |

## 🔄 团队协作流程

```
1. 开发者 pull 最新代码（不含 local key）
2. 运行 .\qm_paper_search_setup.ps1 一次
3. 后续运行只用 .ps1，不重新配置
4. key 失效时 Set-ApiKey.ps1 -Validate 后更新
```

## 🐛 故障排查

| 错误 | 原因 | 解决 |
|---|---|---|
| `401 Unauthorized` | key 无效 | `Set-ApiKey.ps1 -Validate` 检查 |
| `403 Forbidden` | key 被禁 | 申请新 key |
| `429 Too Many Requests` | 限流 | sleep 30-60s 重试；申请 key 提升限流 |
| `api_keys.local.json not found` | 未初始化 | 跑 `qm_paper_search_setup.ps1` |
| `key is placeholder` | 未替换占位符 | `Set-ApiKey.ps1 -Provider X -Key 'real_key'` |
