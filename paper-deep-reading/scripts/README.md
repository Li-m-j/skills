# paper-deep-reading 脚本使用说明（v0.4）

本目录是 paper-deep-reading Skill 的脚本层。**v0.4 起 `pdf_extractor.py` 是"编排 + CLI + 向后兼容 re-export"的薄层**，实际逻辑在以下模块中：

```
scripts/
├── pdf_extractor.py      编排 / CLI / re-export（对外接口保持不变）
├── extractors/           PDF 多后端：pdftotext_backend / fitz_backend / pdfplumber_backend
├── sections.py           章节定位（abstract/introduction/method/result/conclusion）
├── figures.py            图表引用提取（Figure/Fig./Table/Scheme/Chart）
├── images.py             候选图片池（默认 ≤12 张，按正文顺序）
├── io_utils.py           UTF-8 I/O 工具
├── models.py             共享数据结构（dataclass）
└── ima_bridge.py         IMA 知识库胶水层（可选功能）
```

> `from pdf_extractor import extract_pdf, detect_sections, ...` 仍然有效（完整的向后兼容 re-export）。

## 功能

### pdf_extractor.py — PDF 文本提取与结构化（v0.4）

1. **多后端自动提取 PDF 文本**，按优先级自动降级：
   - 后端 1：`pdftotext`（poppler 命令行工具，优先）
   - 后端 2：PyMuPDF（`fitz`）
   - 后端 3：pdfplumber
   - 全部不可用时：给出 `warning` + **`ocr_hint`**（v0.4：自动探测本机 Tesseract / PaddleOCR / pdftoppm，给出可复制命令）
2. **自动定位核心章节**：abstract / introduction / method / result / conclusion。
   - 支持中英文标题（含编号前缀，如 `1 Introduction`、`2 计算方法`）
   - 支持中英混排标题（如 `1. Introduction 引言`、`2. 计算方法 Computational Methods`）
   - `Discussion` 单独成章时合并入 `result`（"结果与讨论"语义）
   - 正文末尾或 SI 中的 `Computational Details` / `Supporting Information` / `补充材料` 也能识别
3. **自动提取图表引用**：扫描全文中的 `Figure N` / `Fig. N` / `Table N` / `Scheme N` / `Chart N`，
   输出 `figures_and_tables` 列表（含 `label` / `raw_label` / `caption_preview` / `position`）。
4. **自动提取候选图片池**（v0.4 语义变更）：用 PyMuPDF 对每个 figure 所在页抽取真实图像，
   输出 `key_images` 列表（含 `label` / `image_path` / `page` / `width` / `height` / `area` / `byte_size` / `caption_preview` / `index`）。
   - **默认最多 12 张、按正文出现顺序**（v0.3 是"按 caption 长度排序前 5 张"，该 heuristic 已废弃）
   - 去重（MD5）；过滤 <80px 的小图
   - 上层 AI 从该候选中选取 3-5 张最核心的图，并写出选取理由
5. **启发式识别论文类型**（v0.4：3 类 → **7 类枚举**）：
   `article` / `review` / `perspective` / `account` / `letter` / `editorial` / `unknown`
6. 输出 JSON，供上层 Skill 直接解析使用。

**CLI 自检**：

```powershell
# 基本
python pdf_extractor.py paper.pdf --pretty

# 指定候选图片输出目录（默认 12 张候选，按正文顺序）
python pdf_extractor.py paper.pdf --image-dir ./extracted_images

# 自定义候选数量与排序（position 默认 / caption / area）
python pdf_extractor.py paper.pdf --max-images 20 --images-sort area --image-dir ./imgs

# 纯文本模式
python pdf_extractor.py notes.txt --text --pretty
```

### ima_bridge.py — IMA 知识库胶水层（v0.3）

调用 ima-skill 的 Node CLI 间接访问 IMA OpenAPI：

| 函数 | 用途 |
| --- | --- |
| `list_knowledge_bases()` | 列出用户可访问的知识库 |
| `search_knowledge(kb_id, query)` | 在指定 KB 中按关键词搜索 |
| `list_knowledge_items(kb_id, folder_id=...)` | 列出 KB 全部条目（可下钻文件夹） |
| `get_media_info(media_id)` | 获取条目元信息（含下载 URL 与签名 headers） |
| `download_paper(media_id, dest_dir, filename=None)` | 下载原始 PDF 到本地（自动追加下载参数与签名） |
| `import_note(title, content, kb_id=None)` | 把 Markdown 内容写为新笔记（可选关联到 KB） |

**凭证读取**（按优先级）：
1. 环境变量 `IMA_CLIENT_ID` / `IMA_API_KEY`（或 `IMA_OPENAPI_CLIENTID` / `IMA_OPENAPI_APIKEY`）
2. `~/.config/ima/client_id` 与 `~/.config/ima/api_key`（ima-skill 文档指定位置）

**依赖**：
- ima-skill 安装在 `~/.minimax/skills/ima-skill/`（Mavis 端）或 `~/.workbuddy/skills/ima-skill/`（WorkBuddy 端）— 可由 `IMA_SKILL_DIR` 环境变量覆盖
- Node 18+（优先 PATH；缺则回退到 `~/.workbuddy/binaries/node/versions/<ver>/node.exe`）

**CLI 自检**：

```powershell
# 列 KB
python ima_bridge.py list-kbs

# 搜论文
python ima_bridge.py search --kb <kb_id> --query "fentanyl" --limit 10

# 列 KB 条目
python ima_bridge.py list --kb <kb_id> --limit 20

# 下载
python ima_bridge.py download --media-id <media_id> --dest ./tmp
```

## pdf_extractor.py 输出 JSON 结构

```json
{
  "input_file": "C:/.../paper.pdf",
  "input_type": "pdf",
  "full_text": "……全文文本……",
  "sections": {
    "abstract": "……摘要文本……",
    "introduction": "……引言文本……",
    "method": "……方法文本……",
    "result": "……结果文本（含 Discussion 单独成章的内容）……",
    "conclusion": "……结论文本……"
  },
  "figures_and_tables": [
    {
      "label": "Figure 1",
      "raw_label": "Fig. 1.",
      "caption_preview": "Optimized geometry of CO on Pt(111)...",
      "position": 4521
    }
  ],
  "key_images": [
    {
      "label": "Figure 1",
      "image_path": "C:/Users/.../Figure_1.png",
      "page": 3,
      "xref": 42,
      "width": 1019,
      "height": 620,
      "area": 631780,
      "byte_size": 88213,
      "caption_preview": "Optimized geometry of CO on Pt(111)...",
      "index": 0
    }
  ],
  "paper_type": "article",
  "page_count": 12,
  "extractor_used": "pdftotext",
  "has_text_layer": true
}
```

字段说明：

| 字段 | 类型 | 含义 |
| --- | --- | --- |
| `input_file` | string | 输入文件绝对路径 |
| `input_type` | string | `pdf` 或 `text` |
| `full_text` | string | 提取出的全文（未定位章节时也可整体使用） |
| `sections` | object | 五个核心章节文本；未定位到的章节为空字符串 |
| `figures_and_tables` | array | 图表引用列表（按出现顺序，去重）；`label` 是标准化标签（`Figure 1` / `Table S2`），`caption_preview` 是紧随的 caption 预览（最多约 220 字符） |
| `key_images` | array | **候选图片池**（默认 ≤12，按正文顺序）；每项含 `image_path` / `page` / `width` / `height` / `area` / `index`；为空表示未装 PyMuPDF 或无图 |
| `paper_type` | string | `article` / `review` / `perspective` / `account` / `letter` / `editorial` / `unknown`（v0.4 枚举） |
| `page_count` | int | PDF 页数（文本模式为 0） |
| `extractor_used` | string | `pdftotext` / `fitz` / `pdfplumber` / `plain_text` / `ocr:<引擎>` / `none` |
| `has_text_layer` | bool | 是否提取到文本层 |
| `warning` | string（可选） | 扫描件/无文本层/文本过少时的提示 |
| `ocr_hint` | object（可选） | v0.4：`{tesseract, pdftoppm, paddleocr, hint}`；无文本层时给出 OCR 兜底指引 |

## paper_type 判定规则（v0.4 · 7 类）

按优先级，先命中先返回：

1. 无文本 → `unknown`
2. `in this account` / `our journey` / `lessons learned` → `account`
3. `perspective` / `viewpoint` / `our view` / `outlook` → `perspective`
4. `editorial` / `this issue of` → `editorial`
5. `this review` / `we review` / `recent advances in` / `progress in` / `综述` / `minireview` 等 → `review`
6. `method` 与 `result` 都为空，且 `introduction` + `conclusion` 都非空（典型综述结构）→ `review`
7. `in this communication` / `we report herein` / `rapid communication` → `letter`
8. 否则 → `article`

> 该判定为启发式，准确率约 85%；**用户可显式覆盖**（见 SKILL.md §2）。类型信号与期刊先验的对照表见 `references/comp-chem-paper-structure.md §8.4`。

## 章节定位规则

- 标题正则覆盖：
  - 英文：摘要/Abstract、引言/Introduction、方法/Methods/Computational Details、结果/Results/Results and Discussion、结论/Conclusion
  - 中文：摘要、引言/绪论/前言、计算方法/理论方法、结果/结果与讨论、结论
  - **中英混排**：`1. Introduction 引言`、`2. 计算方法 Computational Methods`、`3. 结果与讨论 Results and Discussion`
  - **Discussion 单独成章** → 合并入 `result`（语义上属"结果讨论"）
  - **SI/正文末尾**：`Computational Details` / `Supporting Information` / `补充材料` 等变体也匹配 `method`
- 支持编号前缀（`1 Introduction`、`2.1 计算方法`、`3.2.1 DFT Setup`）；
- 通过"标题后是否有实质性内容（≥50 个非空白字符）"过滤目录（Table of Contents）与页眉页脚误匹配；
- 每个章节取"本标题 → 下一个任意章节标题"之间的文本；
- 已知局限：正文中与章节标题完全相同的行（如每页页眉"Methods"）可能造成定位偏移，属正则提取的正常现象；上层 Skill 可结合 `full_text` 复核。

## Windows 注意事项

- 脚本内部统一使用 UTF-8 读写与输出，兼容 GBK 控制台；
- 路径含空格时请用引号包裹：`python pdf_extractor.py "C:/My Papers/paper.pdf"`；
- 若 `python` 不在 PATH，可用 `py -3 pdf_extractor.py ...`；
- 不会弹出命令行窗口（已设置 `CREATE_NO_WINDOW`）。

## 退出码

- `0`：成功（包括"无文本层但已给出 warning"的情况，便于上层判断）；
- `1`：输入文件不存在或参数错误。

## 常见问题

| 问题 | 处理 |
| --- | --- |
| 输出为空且 `warning` 提示扫描件 | 读取返回的 `ocr_hint`：已装引擎按命令直接 OCR；未装则按 `hint` 里的安装指引；或粘贴文本 |
| 提取文本乱码 | 安装增强后端：`pip install pymupdf pdfplumber`，或更换输入 |
| 章节定位不全 | 论文可能使用了非标准章节标题，可直接使用 `full_text` 人工定位 |
| 中文字体显示为方块 | 终端编码问题，输出到文件后用 UTF-8 编辑器查看 |
| ima_bridge 报 "未找到 ima-skill" | 在 `~/.minimax/skills/ima-skill/` 安装 ima-skill |
| ima_bridge 报 "未配置 IMA 凭证" | 写入 `~/.config/ima/{client_id,api_key}` |
| ima_bridge 报 "未找到 node" | 安装 Node 18+，或确认 `~/.workbuddy/binaries/node/...` 存在 |
