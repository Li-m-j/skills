# API key 管理

> 本文件由 `SKILL.md`「11. API key 管理」于 2026-09-18 结构瘦身时原样迁出；主文档保留编号占位，跨引用 `§` 仍然有效。

## 11. API key 管理

### 11.1 设计原则

- **团队共享代码 + 个人本地 key** —— 代码 commit 到 git，key 不共享
- 每个成员独立管理自己的 key
- 支持后续 key 变更（失效、续期、轮换）

### 11.2 读取顺序

1. `data/api_keys.local.json`（个人本地，最优先）
2. 环境变量 `OPENALEX_API_KEY` / `SEMANTIC_SCHOLAR_API_KEY`（User 级别）
3. 不使用 key（限流低但能跑）

`api_keys.template.json` 是占位符，**不会被读**。

### 11.3 首次配置

```powershell
cd $env:USERPROFILE\.minimax\skills\qm_paper_search_shared\data\scripts
.\qm_paper_search_setup.ps1
# 按提示输入 OpenAlex / SS key（或留空跳过）
```

### 11.4 后续管理

```powershell
# 查看当前 key 状态
.\Set-ApiKey.ps1 -List

# 更新 OpenAlex key
.\Set-ApiKey.ps1 -Provider openalex -Key "NEW_KEY"

# 改用环境变量
.\Set-ApiKey.ps1 -Provider openalex -EnvVar

# 删除 key
.\Set-ApiKey.ps1 -Provider openalex -Remove

# 验证 key 有效性
.\Set-ApiKey.ps1 -Validate
```

### 11.5 安全约束

- ❌ 不要把 `api_keys.local.json` 加入 git
- ❌ 不要在聊天/邮件/截图中分享 key
- ✅ key 失效时（401/403）立即更新
- ✅ 详细文档见 `data/README_API_KEYS.md`

### 11.6 输出规范

- 出版商屏蔽 abstract → 标 `N/A（出版商屏蔽，到 DOI 原页拉）`，**不用 AI 总结兜底**
- 标记为 `🔒 待人工处理`，交付用户
- 不在 .md 中编造 abstract 内容

**粗放模式特别约束**：

- 粗放模式更频繁使用 SS API，可能需要 Semantic Scholar key
- OpenAlex key 申请：https://openalex.org/users/sign_up
- Semantic Scholar key 申请：https://www.semanticscholar.org/product/api
- 详细管理流程见 `data/README_API_KEYS.md`
