# IMA 知识库联用参考

本文件供 AI 在处理 IMA 联用流程时查阅。描述 paper-deep-reading 与 IMA（ima.qq.com）知识库的集成方式、字段映射与错误处理。

---

## 1. IMA 是什么

IMA（ima.qq.com）是腾讯的 AI 知识库产品。用户可上传 PDF / 网页 / 创建笔记到自己的知识库中。本 skill 通过 ima-skill（WorkBuddy / Mavis 的 IMA 适配层）调用其 OpenAPI。

## 2. 联用流程总览

```
┌──────────────┐                  ┌─────────────────┐                ┌──────────────┐
│   AI Agent   │ ─── 触发词 ───> │ paper-deep-     │ ── 调用 API ──> │ ima-skill    │
│              │                  │ reading SKILL   │                 │ (Node CLI)   │
│              │                  │                 │ <── JSON ──── │              │
└──────┬───────┘                  └────────┬────────┘                 └──────┬───────┘
       │                                   │                                  │
       │                                   v                                  v
       │                            ┌──────────────┐                  ┌──────────────┐
       │                            │ ima_bridge.py│                  │ ima.qq.com   │
       │                            │ (Python 包)  │                  │ OpenAPI      │
       │                            └──────┬───────┘                  └──────────────┘
       │                                   │
       │                                   v
       │                            ┌──────────────┐
       │  <─── 报告 markdown ───── │ pdf_extractor │
       │                            │    .py        │
       └────────────────────────────│  (常规流程)   │
                                    └──────────────┘
```

## 3. 触发词（用户说这些就应触发 IMA 联用）

| 用户说法 | 路由 |
| --- | --- |
| "读我 IMA 知识库里的 XX" | Step 0.5 → list_kbs → search/list → download |
| "用 IMA 知识库" | 同上（带 context） |
| "ima://<media_id>" | Step 0.5 → 直接 download 该 media |
| "kb://<kb_id>/<query>" | Step 0.5 → list_kbs 比对，匹配后 search |
| 给出 kb_id + 论文名 | Step 0.5 → search 该 KB |

不触发 IMA 联用（仅是提及）的反例：
- "IMA 是什么" → 不触发，走普通问答
- "把这段传到 IMA" → 应是 ima-skill 自身的上传场景，不是 paper-deep-reading 的活

## 4. 字段映射

### 4.1 list_knowledge_bases → 知识库选择

API: `openapi/wiki/v1/get_addable_knowledge_base_list`

响应（实测）：

```json
{
  "code": 0,
  "data": {
    "addable_knowledge_base_list": [
      {"id": "Lp6pja3-ryhXRoSvX28svnQNRRbrRf1O5FQ9rHi47nc=", "name": "个人知识库"},
      {"id": "NkEjGKj7LYkrf2S5qZIUyprW-D1rsLRGOMtS5YCfxog=", "name": "文献库"}
    ],
    "next_cursor": "...",
    "is_end": true
  }
}
```

展示给用户时：**只展示 name，让用户挑 id**（id 太长，名称易记）。

### 4.2 search_knowledge / list_knowledge_items → 论文定位

API: `openapi/wiki/v1/search_knowledge` 或 `get_knowledge_list`

- 文件条目 `media_type = 1`（PDF / Office / 图片 等）
- 文件夹条目 `media_type = 99`（`folder_type` 字段区分）
- 笔记条目 `media_type = 11`（来自 notes 模块）

论文类 PDF 重点关注 `media_type=1` 的条目。

### 4.3 get_media_info → 下载 URL 提取

API: `openapi/wiki/v1/get_media_info`

响应（实测）：

```json
{
  "code": 0,
  "data": {
    "media_type": 1,
    "url_info": {
      "url": "https://res-skb.ima.qq.com/.../file.pdf?sign=...&t=...",
      "headers": {
        "X-IMA-Sign": "...",
        "X-IMA-Trace-ID": "...",
        "X-IMA-UID-SHA256": "...",
        "X-IMA-Create-URL-Time": "..."
      }
    }
  }
}
```

**下载必须**：
1. 追加 `?response-content-type=application/octet-stream&response-content-disposition=attachment` 到 URL
2. 携带 `url_info.headers` 中的所有字段（特别是 `X-IMA-Sign`，否则会被 IMA 拒签）
3. 文件名从 URL 推断（取 path 的最后一段）；标题在 `media_title` 查询参数里（URL 解码后可用作原始标题，但写入报告时仍以 PDF 元信息或正文首行为准）

### 4.4 import_note → 报告回写

API: `openapi/notes/v1/import_doc`

请求体：

```json
{
  "title": "非血红素酶催化...（计算化学论文深度阅读）",
  "content": "# 文献元信息\n\n- ...\n\n## 一、问题与价值层\n\n...",
  "content_format": 1
}
```

**强制校验**：
- `title` 与 `content` 都必须是合法 UTF-8（`content.encode("utf-8").decode("utf-8")` 不抛错）
- `title` 长度建议 ≤ 100 字符（IMA 笔记标题显示限制）
- 文件名非法字符清洗：`/ \ : * ? " < > |` → `_` 或删除

成功响应包含 `note_id`，可继续用 `add_knowledge` 关联到知识库（`media_type=11` + `note_info.content_id`）。

## 5. 错误处理

| 错误码 | 含义 | 处理 |
| --- | --- | --- |
| IMA `-100` | 凭证缺失 / 参数非法 / 网络错误 | 直接展示 `msg` 给用户，提示去 ima.qq.com 申请或检查参数 |
| IMA `-200` | skill 需要更新 | 提示用户按 `instruction` 更新 ima-skill |
| 后端业务 `code≠0` | 参数不合法 / 权限不足 / 资源不存在 | 直接展示 `msg`（已含原因） |
| 网络超时 | urllib.error.URLError | 提示重试；不要无限重试 |
| BOM 错误 | 凭证文件有 UTF-8 BOM | ima_bridge 已自动剥；如还有错提示用户重写文件 |

**绝不要**：
- 静默吞错
- 把 `apiKey` 写进报告 / 日志 / 任何可见输出
- 凭推测继续（如不知道 kb_id 不要硬编码）

## 6. 与 ima-skill 的边界

| 责任 | ima-skill | paper-deep-reading |
| --- | --- | --- |
| IMA OpenAPI 调用 | ✅（Node CLI） | 通过 ima_bridge 间接调用 |
| 文件上传到 KB | ✅（cos-upload） | 不做 |
| 笔记 CRUD | ✅ | 仅做 import_note（写报告） |
| PDF 文本提取 | 不做 | ✅（pdf_extractor.py） |
| 论文深度阅读 | 不做 | ✅（7 模块 10 要点） |

**两 skill 协作的典型场景**：

1. 用户用 ima-skill 把论文 PDF 批量上传到 KB
2. 用户对 paper-deep-reading 说 "读 KB 里的 XX"
3. paper-deep-reading 通过 ima_bridge 拉取 PDF
4. 生成报告
5. 询问是否回写 → 用 ima-skill 的 import_doc 把报告写为新笔记

## 7. 安全约束（再次强调）

- 凭证仅走环境变量或 `~/.config/ima/` 文件，**绝不**在命令行 / 日志 / 报告中明文出现
- 下载的临时 PDF 在会话结束后清理（避免占用磁盘；用户决定保存则保留）
- 不读取论文正文之外的内容（如 metadata 中的私有字段）
- 写回的笔记标题/正文不包含本地文件路径（仅论文标题 / 作者 / 期刊等公开元信息）
