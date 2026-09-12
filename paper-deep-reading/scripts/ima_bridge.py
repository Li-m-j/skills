#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ima_bridge.py — paper-deep-reading 与 IMA（ima.qq.com）知识库的胶水层。

功能（仅依赖 Python 标准库 + ima-skill 自带的 Node）：
  - list_knowledge_bases()          列出用户可访问的知识库
  - search_knowledge(kb_id, query)  在指定知识库中搜索条目（按标题/内容）
  - list_knowledge_items(kb_id)     列出知识库所有条目
  - get_media_info(media_id)        获取条目元信息（含原始文件下载 URL）
  - download_paper(media_id, dest)  下载条目原始文件到本地（PDF / 文本等）
  - import_note(kb_id, title, md)   把 Markdown 报告写为知识库中的新笔记
                                    （走 notes 模块的 import_doc）

凭证：
  按 ima-skill 文档，从以下位置按优先级读取：
    1. 环境变量 IMA_CLIENT_ID / IMA_API_KEY
    2. 文件 ~/.config/ima/client_id + ~/.config/ima/api_key
  凭证**绝不**打印到 stdout / 日志。

依赖：
  - ima-skill 已安装（默认查找 ~/.workbuddy/skills/ima-skill，可通过
    IMA_SKILL_DIR 环境变量覆盖；Mavis 端用 ~/.minimax/skills/ima-skill/）
  - Node 18+（优先 PATH 中的 `node`，否则回退到 WorkBuddy 自带 node）
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# 路径与依赖探测
# ---------------------------------------------------------------------------
def _homedir() -> Path:
    return Path(os.path.expanduser("~"))


def _ima_skill_dir() -> Path:
    """查找 ima-skill 安装目录。"""
    env = os.environ.get("IMA_SKILL_DIR")
    if env:
        return Path(env)
    candidates = [
        # Mavis 端（v0.3 迁移后）
        _homedir() / ".minimax" / "skills" / "ima-skill",
        # WorkBuddy 端
        _homedir() / ".workbuddy" / "skills" / "ima-skill",
        # Claude Code 端
        _homedir() / ".claude" / "skills" / "ima-skill",
        Path("C:/workbuddy/skills/ima-skill"),
    ]
    for c in candidates:
        if (c / "ima_api.cjs").is_file():
            return c
    raise FileNotFoundError(
        "未找到 ima-skill。请安装到 ~/.minimax/skills/ima-skill/ 或 ~/.workbuddy/skills/ima-skill/，"
        "或设置环境变量 IMA_SKILL_DIR 指向含 ima_api.cjs 的目录。"
    )


def _node_binary() -> str:
    """查找可用的 node 可执行文件。"""
    # 优先 PATH
    on_path = shutil.which("node")
    if on_path:
        return on_path
    # 回退到 WorkBuddy 自带
    candidates = [
        _homedir() / ".workbuddy" / "binaries" / "node" / "versions" / "22.22.2-2" / "node.exe",
        _homedir() / ".workbuddy" / "binaries" / "node" / "versions" / "22.22.2-2" / "node",
    ]
    for c in candidates:
        if c.is_file():
            return str(c)
    raise FileNotFoundError(
        "未找到 node 可执行文件。请安装 Node 18+，或确保 WorkBuddy 自带 node 存在。"
    )


def _load_credentials() -> Dict[str, str]:
    """从 env 或 ~/.config/ima/ 读取凭证（按优先级）。"""
    cid = (
        os.environ.get("IMA_CLIENT_ID")
        or os.environ.get("IMA_OPENAPI_CLIENTID")
        or ""
    )
    key = (
        os.environ.get("IMA_API_KEY")
        or os.environ.get("IMA_OPENAPI_APIKEY")
        or ""
    )
    if not cid or not key:
        cfg_dir = _homedir() / ".config" / "ima"
        cid_path = cfg_dir / "client_id"
        key_path = cfg_dir / "api_key"
        for target, path in (("cid", cid_path), ("key", key_path)):
            if not path.is_file():
                continue
            raw = path.read_bytes()
            # 剥 UTF-8 BOM（PowerShell 5.1 Set-Content -Encoding UTF8 会写 BOM）
            if raw.startswith(b"\xef\xbb\xbf"):
                raw = raw[3:]
            value = raw.decode("utf-8", errors="replace").strip()
            if target == "cid" and value and not cid:
                cid = value
            elif target == "key" and value and not key:
                key = value
    if not cid or not key:
        raise RuntimeError(
            "未配置 IMA 凭证。请在 https://ima.qq.com/agent-interface 申请后，"
            "写入 ~/.config/ima/client_id 与 ~/.config/ima/api_key，"
            "或设置 IMA_CLIENT_ID / IMA_API_KEY 环境变量。"
        )
    return {"clientId": cid, "apiKey": key}


# ---------------------------------------------------------------------------
# Node CLI 调用
# ---------------------------------------------------------------------------
class ImaError(RuntimeError):
    """IMA API 错误（含 stderr 中的 code / msg）。"""

    def __init__(self, code: int, msg: str, raw: str = ""):
        self.code = code
        self.msg = msg
        self.raw = raw
        super().__init__(f"[IMA {code}] {msg}")


def _call(api_short: str, body: Dict[str, Any]) -> Dict[str, Any]:
    """调用 ima-skill 的 Node CLI。api_short 是 API 短名（如 get_knowledge_list）。"""
    skill_dir = _ima_skill_dir()
    node = _node_binary()
    creds = _load_credentials()
    # 完整 API 路径：openapi/wiki/v1/<name>
    api_path = f"openapi/wiki/v1/{api_short}"

    cmd = [
        node,
        str(skill_dir / "ima_api.cjs"),
        api_path,
        json.dumps(body, ensure_ascii=False),
        json.dumps(creds, ensure_ascii=False),
    ]
    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=120,
    )
    if proc.returncode != 0:
        # 解析 stderr JSON 错误
        try:
            err = json.loads(proc.stderr.strip() or "{}")
            raise ImaError(err.get("code", -100), err.get("msg", "未知错误"), proc.stderr)
        except json.JSONDecodeError:
            raise ImaError(-100, f"Node CLI 失败：{proc.stderr.strip()[:200]}")
    # 成功：stdout 是后端业务响应
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError as e:
        raise ImaError(-100, f"无法解析响应：{proc.stdout[:200]}") from e


# ---------------------------------------------------------------------------
# 公开 API
# ---------------------------------------------------------------------------
def list_knowledge_bases(limit: int = 20) -> List[Dict[str, str]]:
    """列出当前用户可添加内容的知识库。返回 [{id, name}, ...]"""
    resp = _call("get_addable_knowledge_base_list", {"limit": limit})
    items = (resp.get("data") or {}).get("addable_knowledge_base_list") or []
    return [{"id": it.get("id", ""), "name": it.get("name", "")} for it in items]


def search_knowledge(
    kb_id: str, query: str, limit: int = 20
) -> List[Dict[str, Any]]:
    """在指定知识库中搜索条目。返回 [{id, name, type, ...}, ...]"""
    body: Dict[str, Any] = {"query": query, "knowledge_base_id": kb_id, "limit": limit}
    resp = _call("search_knowledge", body)
    items = (resp.get("data") or {}).get("knowledge_list") or []
    return items


def list_knowledge_items(
    kb_id: str, folder_id: Optional[str] = None, limit: int = 50
) -> List[Dict[str, Any]]:
    """列出知识库条目（含文件夹与文件）。"""
    body: Dict[str, Any] = {"knowledge_base_id": kb_id, "limit": limit}
    if folder_id:
        body["folder_id"] = folder_id
    resp = _call("get_knowledge_list", body)
    data = resp.get("data") or {}
    items = list(data.get("knowledge_list") or []) + list(data.get("folder_list") or [])
    return items


def get_media_info(media_id: str) -> Dict[str, Any]:
    """获取条目元信息（含原始文件下载 URL）。"""
    return _call("get_media_info", {"media_id": media_id})


_DOWNLOAD_QUERY = {
    "response-content-type": "application/octet-stream",
    "response-content-disposition": "attachment",
}


def _build_download_url(media_info: Dict[str, Any]) -> Optional[str]:
    """从 get_media_info 响应中提取可下载的原始文件 URL。

    响应结构（实测）：
      data = {
        "media_type": 1,
        "url_info": {
          "url": "https://res-skb.ima.qq.com/.../file.pdf?...",
          "headers": { "X-IMA-Sign": "...", ... }
        },
        ...
      }
    """
    data = media_info.get("data") or {}
    # 主要来源：data.url_info.url（实际响应）
    url_info = data.get("url_info") or {}
    url = (
        url_info.get("url")
        or data.get("download_url")
        or data.get("url")
        or data.get("file_url")
        or data.get("source_url")
    )
    if not url:
        return None
    # 追加下载参数（按 SKILL 文档）
    parsed = urllib.parse.urlparse(url)
    qs = urllib.parse.parse_qs(parsed.query)
    qs.update(_DOWNLOAD_QUERY)
    new_query = urllib.parse.urlencode(qs, doseq=True)
    return urllib.parse.urlunparse(parsed._replace(query=new_query))


def _build_download_headers(media_info: Dict[str, Any]) -> Dict[str, str]:
    """从 get_media_info 响应中提取下载所需的 headers（含签名）。"""
    data = media_info.get("data") or {}
    url_info = data.get("url_info") or {}
    headers = dict(url_info.get("headers") or {})
    headers.setdefault("User-Agent", "paper-deep-reading/0.3")
    return headers


def download_paper(
    media_id: str, dest_dir: str, filename: Optional[str] = None
) -> str:
    """下载知识库条目的原始文件到本地。返回本地文件路径。

    - dest_dir: 目标目录（不存在会自动创建）
    - filename: 自定义文件名；缺省从 URL 推断
    """
    info = get_media_info(media_id)
    url = _build_download_url(info)
    if not url:
        raise ImaError(-100, f"无法从 get_media_info 提取下载 URL: {info!r}")
    Path(dest_dir).mkdir(parents=True, exist_ok=True)
    if not filename:
        # 从 URL 推断
        path = urllib.parse.urlparse(url).path
        filename = Path(path).name or f"{media_id}.bin"
        # URL 解码
        filename = urllib.parse.unquote(filename)
    dest = Path(dest_dir) / filename
    # 下载（含 IMA 签名 headers）
    headers = _build_download_headers(info)
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=180) as resp:
        with open(dest, "wb") as fh:
            shutil.copyfileobj(resp, fh)
    return str(dest)


# ---------------------------------------------------------------------------
# 笔记写入（notes 模块）
# ---------------------------------------------------------------------------
# notes 模块 API 路径：openapi/notes/v1/import_doc
def _call_notes(api_short: str, body: Dict[str, Any]) -> Dict[str, Any]:
    """调用 notes 模块的 Node CLI。"""
    skill_dir = _ima_skill_dir()
    node = _node_binary()
    creds = _load_credentials()
    api_path = f"openapi/notes/v1/{api_short}"
    cmd = [
        node,
        str(skill_dir / "ima_api.cjs"),
        api_path,
        json.dumps(body, ensure_ascii=False),
        json.dumps(creds, ensure_ascii=False),
    ]
    proc = subprocess.run(
        cmd, capture_output=True, text=True, encoding="utf-8",
        errors="replace", timeout=120,
    )
    if proc.returncode != 0:
        try:
            err = json.loads(proc.stderr.strip() or "{}")
            raise ImaError(err.get("code", -100), err.get("msg", "未知错误"), proc.stderr)
        except json.JSONDecodeError:
            raise ImaError(-100, f"Node CLI 失败：{proc.stderr.strip()[:200]}")
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError as e:
        raise ImaError(-100, f"无法解析响应：{proc.stdout[:200]}") from e


def import_note(title: str, content_markdown: str, kb_id: Optional[str] = None) -> Dict[str, Any]:
    """把 Markdown 内容导入为新笔记。

    - title: 笔记标题
    - content_markdown: Markdown 正文（必须是合法 UTF-8）
    - kb_id: 可选，导入后关联到指定知识库
    """
    if not title or not title.strip():
        raise ValueError("title 不能为空")
    # UTF-8 校验（强制要求：notes 写入必须是合法 UTF-8）
    if not isinstance(content_markdown, str):
        content_markdown = str(content_markdown)
    try:
        content_markdown.encode("utf-8").decode("utf-8")
    except UnicodeError as e:
        raise ValueError(f"content 不是合法 UTF-8: {e}")
    body: Dict[str, Any] = {
        "title": title,
        "content": content_markdown,
        "content_format": 1,  # 1 = Markdown（按 notes 模块约定）
    }
    result = _call_notes("import_doc", body)
    # 如果指定了知识库，关联过去
    if kb_id and result.get("code") == 0:
        data = result.get("data") or {}
        note_id = data.get("note_id") or data.get("id")
        if note_id:
            link = _call(
                "add_knowledge",
                {
                    "knowledge_base_id": kb_id,
                    "media_type": 11,  # 11 = 笔记类型
                    "note_info": {"content_id": note_id},
                },
            )
            result["linked_to_kb"] = link
    return result


# ---------------------------------------------------------------------------
# CLI 自检
# ---------------------------------------------------------------------------
def _main() -> int:
    import argparse
    parser = argparse.ArgumentParser(
        prog="ima_bridge.py",
        description="paper-deep-reading 的 IMA 知识库胶水层（Python ↔ Node）",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("list-kbs", help="列出可访问的知识库")

    p_search = sub.add_parser("search", help="在知识库中搜索")
    p_search.add_argument("--kb", required=True, help="知识库 ID")
    p_search.add_argument("--query", required=True, help="搜索关键词")
    p_search.add_argument("--limit", type=int, default=10)

    p_list = sub.add_parser("list", help="列出知识库条目")
    p_list.add_argument("--kb", required=True)
    p_list.add_argument("--limit", type=int, default=20)

    p_dl = sub.add_parser("download", help="下载条目到本地")
    p_dl.add_argument("--media-id", required=True)
    p_dl.add_argument("--dest", required=True, help="目标目录")
    p_dl.add_argument("--filename", help="自定义文件名")

    args = parser.parse_args()

    try:
        if args.cmd == "list-kbs":
            kbs = list_knowledge_bases()
            print(json.dumps(kbs, ensure_ascii=False, indent=2))
        elif args.cmd == "search":
            items = search_knowledge(args.kb, args.query, args.limit)
            # 精简输出
            out = [
                {"media_id": it.get("media_id") or it.get("id"),
                 "name": it.get("name") or it.get("title"),
                 "type": it.get("media_type")}
                for it in items
            ]
            print(json.dumps(out, ensure_ascii=False, indent=2))
        elif args.cmd == "list":
            items = list_knowledge_items(args.kb, limit=args.limit)
            out = [
                {"id": it.get("id") or it.get("media_id"),
                 "name": it.get("name") or it.get("title"),
                 "type": it.get("media_type") or it.get("folder_type")}
                for it in items
            ]
            print(json.dumps(out, ensure_ascii=False, indent=2))
        elif args.cmd == "download":
            path = download_paper(args.media_id, args.dest, args.filename)
            print(json.dumps({"downloaded": path}, ensure_ascii=False))
    except ImaError as e:
        print(f"[IMA ERROR {e.code}] {e.msg}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(_main())
