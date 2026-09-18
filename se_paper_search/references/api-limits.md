# API 限制约束

> 本文件由 `SKILL.md`「10. API 限制约束」结构瘦身时迁出，并按统计/经济领域调整（新增 §10.0 arXiv 规则）；主文档保留编号占位，跨引用 `§` 仍然有效。

## 10. API 限制约束

### 10.0 arXiv Export API 规则（本 skill 主渠道）

| 项目 | 限制 |
|---|---|
| **礼仪限速** | **1 req/3s**（arXiv 官方要求；违规可封 IP。脚本已内置 ≥3s 间隔，Agent 手工调用同样必须 sleep ≥3s） |
| **key** | 无需 |
| **单次上限** | `max_results ≤ 2000`（本 skill 封顶 100） |
| **协议** | Atom XML（`application/atom+xml`），解析用 `xml.etree.ElementTree` |
| **失败特征** | 偶发空 feed / 5xx / 证书链问题（脚本对 SSL 验证失败有 unverified 兜底） |

### 10.1 OpenAlex API 规则

| 项目 | 限制 |
|---|---|
| **限流（带 key）** | 50 req/s |
| **限流（无 key）** | 5 req/s |
| **polite pool** | 建议带 `mailto=your@email.com` 或 key 标识 |
| **User-Agent** | 强烈建议带标识（OpenAlex 用于诊断） |
| **数据更新** | 每月一次完整更新，每月新增 ~500 万论文 |

**强制行为**：

- ✅ 加 User-Agent：`se_paper_search_skill/0.1 (paper retrieval)`
- ✅ 加 key 或 mailto
- ❌ 禁止并发批量刷（> 10 req/s 持续）
- ❌ 禁止镜像/转售数据
- ❌ 禁止用于 LLM 训练

### 10.2 当前 key 使用情况

- key 存于 `%USERPROFILE%\.minimax\skills\se_paper_search_shared\data\api_keys.local.json`
- 仅用于本 skill，**不分享**
- ❌ 不嵌入到代码仓库公开处
- key 失效时（401/403）：按 §7.1 提示用户提供新 key，并自动回退无 key 模式（5 req/s）

### 10.3 错误码处理

| 状态码 | 含义 | 处理 |
|---|---|---|
| 200 | OK | 继续 |
| 401 | key 无效 | 提示新 key（§7.1）；回退无 key 模式 |
| 403 | 禁止访问 | 检查 User-Agent / key / IP |
| 429 | 限流 | backoff 1s → 5s → 30s 后重试；最多 3 次 |
| 5xx | 服务端错误 | backoff 重试 3 次 → 切换兜底源 |
| network_error | 网络层失败 | 切换 web_search 兜底 |

### 10.4 调用频率建议

| 场景 | 建议频率 |
|---|---|
| 主题检索 | 1-2 req/search（搜索 + 详情） |
| 引用图谱 | 1-5 req/paper（references + cited by） |
| 批量检索 | ≤ 10 req/min（避免触发限流） |
| 持续监控 | 严禁（无合理学术场景） |

### 10.5 调用日志

- 每次 API 调用记录：endpoint / status / latency / date
- 异常时记录完整错误
- 日志仅本地（`shared/data/api_logs.json`），**不上传**
- 用于诊断 API 健康度
- 90 天后自动清理过期日志

### 10.6 API 健康度监控

- 当 OpenAlex 失败率 > 50% 时：自动切兜底源
- 当 429 连续 3 次：暂停 5 分钟
- 当 5xx 连续 5 次：警告用户并切兜底

**粗放模式特别约束**：

- **arXiv 每次检索 1-2 req（短语 + 逐词 AND 回退），单次间隔 ≥3s 由脚本强制**；粗放整体耗时比 qm 孪生长 1-3 分钟，属预期
- 15 篇 × 完整元数据 ≈ 20-40 req/search，**必须 sleep 防限流**
- 引用图谱默认开，1 篇拉 5-10 req，**最多约 150 req/search**
- 建议每次粗放检索后 sleep 30s 再做下一轮
- SS API 共享 IP 100 req/min 限流，无 key 也能跑（带 key 提升）
