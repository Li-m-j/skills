# mbai_paper_search — API Key 管理

> 本目录的 key 仅供本地 mbai_paper_search_fine / mbai_paper_search_broad 两个 skill 使用。  
> 严禁分享给他人、严禁上传到 git 远程、严禁写入聊天/截图。

---

## 1. 申请的 key

| Key | 用途 | 申请地址 | 限流（带 key） |
|---|---|---|---|
| `openalex_api_key` | OpenAlex 主源兜底 | <https://openalex.org/users/sign_up> | 50 req/s |
| `semantic_scholar_api_key` | Semantic Scholar 主源 | <https://www.semanticscholar.org/product/api> | 100 req/s（推荐填） |
| `ncbi_api_key` | PubMed E-utilities 加速 | <https://www.ncbi.nlm.nih.gov/account/settings/> | 10 req/s |
| `europe_pmc_contact_email` | Europe PMC 联系字段 | 自填邮箱 | 礼貌标识（无 key） |
| `mailto_for_openalex` | OpenAlex polite pool | 自填邮箱 | 进入 polite pool |

**无 key 也能跑**，但限流降低：OpenAlex 5 req/s、PubMed 3 req/s。

## 2. 读取顺序

1. `data/api_keys.local.json`（个人本地，gitignore，最优先）
2. 环境变量 `OPENALEX_API_KEY` / `SEMANTIC_SCHOLAR_API_KEY` / `NCBI_API_KEY`
3. 不使用 key

`api_keys.template.json` 是占位符，**永远不会被读**。

## 3. 首次配置

```powershell
cd $env:USERPROFILE\.minimax\skills\mbai_paper_search_shared\data\scripts
.\mbai_paper_search_setup.ps1
# 按提示逐项填入，留空跳过
```

## 4. 后续管理

```powershell
# 查看当前 key 状态
.\Set-ApiKey.ps1 -List

# 更新 OpenAlex key
.\Set-ApiKey.ps1 -Provider openalex -Key "NEW_KEY"

# 改用环境变量
.\Set-ApiKey.ps1 -Provider semantic_scholar -EnvVar

# 删除 key
.\Set-ApiKey.ps1 -Provider ncbi -Remove

# 验证 key 有效性
.\Set-ApiKey.ps1 -Validate
```

## 5. 安全约束

- ❌ 不要把 `api_keys.local.json` 加入 git（已在 .gitignore）
- ❌ 不要在聊天/邮件/截图中分享 key
- ✅ key 失效时（401/403）立即更新
- ✅ 轮换 key：旧 key 删除后再写入新 key

## 6. 失败回退

- OpenAlex 401/403：去掉 key，回退无 key 模式（5 req/s）
- Semantic Scholar 401/403：去掉 key，回退无 key 模式（共享 IP 100 req/min）
- PubMed 429：等待 Retry-After 后重试；持续失败则改用 OpenAlex / Europe PMC
