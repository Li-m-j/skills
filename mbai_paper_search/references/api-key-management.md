# API key 管理

> 本文件由 `SKILL.md`「11. 」于 2026-09-18 结构瘦身时原样迁出；主文档保留编号占位，跨引用 `§` 仍然有效。

## 11. API key 管理

### 11.1 设计原则

- **团队共享代码 + 个人本地 key** —— 代码 commit，key 不共享
- 每个成员独立管理自己的 key；支持轮换（失效 / 续期 / 更换）

### 11.2 读取顺序

1. `data/api_keys.local.json`（个人本地，最优先）
2. 环境变量 `OPENALEX_API_KEY` / `SEMANTIC_SCHOLAR_API_KEY` / `NCBI_API_KEY`
3. 不使用 key（限流低但能跑）

`api_keys.template.json` 是占位符，**不会被读**。

### 11.3 首次配置

```powershell
cd $env:USERPROFILE\.minimax\skills\mbai_paper_search_shared\data\scripts
.\mbai_paper_search_setup.ps1     # OpenAlex / SS / NCBI key + Europe PMC email（可留空）
```

### 11.4 后续管理

```powershell
.\Set-ApiKey.ps1 -List                                    # 查看状态
.\Set-ApiKey.ps1 -Provider openalex -Key "NEW_KEY"        # 更新
.\Set-ApiKey.ps1 -Provider ncbi -EnvVar                   # 改用环境变量
.\Set-ApiKey.ps1 -Provider europe_pmc -Remove             # 删除
.\Set-ApiKey.ps1 -Validate                                # 验证有效性
```

### 11.5 安全约束

- ❌ 不要把 `api_keys.local.json` 加入 git
- ❌ 不要在聊天 / 邮件 / 截图中分享 key
- ✅ key 失效（401/403）立即更新
- ✅ 详细文档见 `data/README_API_KEYS.md`

### 11.6 输出规范

- 出版商屏蔽 abstract → 标 `N/A（出版商屏蔽，到 DOI 原页拉）`，**不用 AI 总结兜底**
- 预处理标记为 `🔒 待人工处理` 后交付
- 预印本 abstract 缺失 → 保留预印本链接，让用户自取
- 综述层级未达系统综述标准 → 标 `Narrative Review`，与 Systematic Review 区分
- 临床指南无证据等级 → 标 `证据等级：未披露`，提醒查原指南
