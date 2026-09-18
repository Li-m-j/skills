# API 限制约束

> 本文件由 `SKILL.md`「10. 」于 2026-09-18 结构瘦身时原样迁出；主文档保留编号占位，跨引用 `§` 仍然有效。

## 10. API 限制约束

### 10.1 各源 API 规则

| API | 限流（带 key） | 限流（无 key） | 备注 |
|---|---|---|---|
| **OpenAlex** | 50 req/s | 5 req/s | polite pool 加 `mailto` |
| **PubMed E-utilities** | 10 req/s（NCBI key） | **3 req/s** | URL 必须带 `email` & `tool=mbai_paper_search` |
| **Europe PMC** | 礼貌标识 | 无硬限流 | URL 带 `email=` |
| **Semantic Scholar** | 100 req/s（key） | 共享 IP 100 req/min | 无 key 时易 429（脚本会自动跳过该源） |
| **Crossref** | 礼貌池 | 50 req/s（共享） | 建议加 `mailto` |
| **bioRxiv / medRxiv** | 公开 | 公开 | 月度更新 |
| **arXiv** | 公开 | 公开 | 建议加 `mailto` |

**强制行为**：✅ 加 User-Agent `mbai_paper_search_skill/0.4`；✅ 加 `mailto` 或 key；❌ 禁止 >10 req/s 持续刷；❌ 禁止镜像 / 转售；❌ 禁止用于 LLM 训练。

### 10.2 主源健康度与自动切换

1. **探活**：OpenAlex `per_page=1` 无 filter，`meta.count > 0` 视为健康；PubMed `einfo` 200 视为健康
2. **自动切换**：OpenAlex 异常 → PubMed；PubMed 异常 → Europe PMC（§3.1 兜底链）
3. **实时告警**：stdout 输出 `⚠️ OpenAlex 不可用，已切到 PubMed`
4. **日志与失败率**：每次调用（含探活）写入 `data/api_logs.json`，用于统计各源失败率
5. **阈值**：某源失败率 > 50% → 自动切兜底；429 连续 3 次 → 暂停 5 分钟；5xx 连续 5 次 → 警告并切兜底

### 10.3 错误码处理

| 状态码 | 含义 | 处理 |
|---|---|---|
| 200 | OK | 继续 |
| 401 | key 无效 | 按 §7.1 提示新 key；回退无 key 模式 |
| 403 | 禁止访问 | 检查 User-Agent / key / IP |
| 429 | 限流 | backoff 1s → 5s → 30s；最多 3 次 |
| 5xx | 服务端错误 | backoff 重试 3 次 → 切换兜底源 |
| network_error | 网络层失败 | 切换兜底源；全失败走 §7.1 |

### 10.4 调用频率建议

| 场景 | 建议频率 |
|---|---|
| 主题检索 | 2-4 req/search（esearch + efetch + OpenAlex + 引用图谱） |
| 引用图谱 | 1-5 req/paper |
| 批量检索 | ≤ 10 req/min（避免触发 PubMed 3 req/s 限制） |
| 持续监控 | 严禁（无合理学术场景） |

**粗放模式特别约束**：

- 15 篇 × 完整元数据 ≈ 30-50 req/search，**必须 sleep 防限流**
- 引用图谱默认开，1 篇 5-10 req，**最多约 150 req/search**
- 建议每次粗放检索后 sleep 30s 再做下一轮

### 10.5 调用日志

每次 API 调用记录 `endpoint / status / latency / date`；异常记录完整错误；日志仅本地（`data/api_logs.json`），**不上传**；最多保留 500 条 / 90 天清理。
