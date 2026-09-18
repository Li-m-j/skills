# paper-deep-reading — 计算化学论文深度阅读 Skill（README · v0.4）

面向「计算化学方向学术论文阅读与解析」的 Skill。接收论文 PDF / 文本 / 网页 URL / IMA 知识库引用，
输出 **7 大模块 10 个要点**（原创研究）或 **5 大模块 8 要点**（综述变体）的结构化深度阅读报告（Markdown），
含关键图片选取、术语一致性控制、作者/致谢/SI 溯源、复现工作流与覆盖度声明。

> 完整定义见 [`SKILL.md`](./SKILL.md)；本文件是**用户视角的操作说明**。

---

## 一、30 秒上手

```
帮我读论文：C:\papers\gaussian_study.pdf
```

或（速览）：

```
快读一下 C:\papers\xxx.pdf
```

**输入格式支持**：本地 PDF 路径（推荐）/ 粘贴文本 / 网页 URL / IMA 知识库引用。

**输出模式**：

| 模式 | 触发词 | 模板 | 字数 |
|---|---|---|---|
| 完整（默认） | 深度阅读 / 精读 / 详细 | `assets/report-template.md` | 2500-4000 |
| 速览 | 快读 / 速览 / 一句话总结 / skim | `assets/report-template-quick.md` | ≤ 500 |

---

## 二、触发方式

- "帮我**读论文**：C:\papers\xxx.pdf"
- "**解析论文**：<粘贴论文全文>"
- "**深度阅读**这篇计算化学论文"
- "**快读**一下这篇"
- 读 IMA 知识库："读我 IMA 知识库里的 XX" / `ima://<media_id>` / `kb://<kb_id>/<query>`

### 用户可覆盖的判定（v0.4）

| 你说 | 效果 |
|---|---|
| "这是综述 / 不是综述" | 强制 `paper_type` |
| "这是 Perspective / Account / Letter" | 直接取指定类型（报告分支随之切换） |
| "重点看图 5 和图 7" | 要点 4 按你指定的图为主 |
| "只要速览 / 给我完整版" | 强制切换输出模式 |

---

## 三、报告结构

| 模块 | 要点 |
| --- | --- |
| 一、问题与价值层 | 1 解决了什么问题；2 为什么选择该计算方法 |
| 二、结果与证据层 | 3 核心结果；4 数据如何支持结果（**候选池选图 + 选取理由**） |
| 三、学术评估层 | 5 创新点（2-4 个）；6 局限性 |
| 四、应用拓展层 | 7 启发点（2-3 个） |
| 五、术语与图注规范 | 8 术语与图注规范 |
| 六、可复现工作流 | 9 复现计算流程（数据准备→参数→执行→结果，**含五组软件/数据库许可清单**） |
| 七、全文总结 | 10 文献总结（**字数随篇幅自适应**：≤8 页 250-400；9-20 页 300-500；>20 页 500-800） |

**论文类型分支（v0.4 · 7 类枚举）**：

| `paper_type` | 报告结构 |
|---|---|
| `article` | 7 模块 10 要点 |
| `review` | 5 模块 8 要点（综述变体） |
| `perspective` | 综述变体（要点 1 改"作者立场"、要点 6 加"立场偏向"） |
| `account` | 综述变体（要点 2 改"课题组方法演进脉络"） |
| `letter` / `communication` | 7 模块精简版（1500-2500 字） |
| `editorial` | 不生成深度报告，改走速览（≤500 字） |
| `unknown` | 按 `article` 处理并注明 |

附加特性：

- 超过 10 页自动定位核心段落，优先解析摘要、引言与结论；
- **图表自动提取**：`figures_and_tables` 含 Figure/Table/Scheme 引用与 caption 预览；
- **候选图片池**（v0.4）：`key_images` 默认最多 12 张、按正文顺序，由 AI 按重要性选取 3-5 张并**写选取理由**；
- **OCR 兜底**（v0.4）：无文本层时自动探测 Tesseract / PaddleOCR 并给出可复制命令；
- **溯源解析**（v0.4）：通讯作者、单位、基金号、机时来源、SI 引用清单；
- **术语一致性**（v0.3+）：主表 > 参考表 > 临时表 > 自译 四级优先级；
- **覆盖度声明**：透明标注【原文】/【AI分析】/【推测】。

---

## 四、目录结构

```
paper-deep-reading/
├── SKILL.md                              # 技能主文件（YAML frontmatter + 执行指令；低频长章节已迁出，主文档留 §编号占位）
├── README.md                             # 本说明
├── CHANGELOG.md                          # 修订记录 + 逐版本变更明细（原 SKILL.md 顶部注释块 + §10）
├── scripts/
│   ├── pdf_extractor.py                  # 编排 + CLI + 向后兼容 re-export
│   ├── extractors/                       # pdftotext / fitz / pdfplumber 三后端
│   ├── sections.py                       # 章节定位（中英混排标题）
│   ├── figures.py                        # 图表引用提取
│   ├── images.py                         # 候选图片池（默认 12 张，按正文顺序）
│   ├── io_utils.py / models.py           # I/O 工具 / 数据结构
│   ├── ima_bridge.py                     # IMA 知识库胶水层（可选）
│   └── README.md                         # 脚本使用说明
├── references/
│   ├── report-modules-spec.md            # 七模块 10 要点逐条规则（原 §4，生成报告前必读）
│   ├── comp-chem-paper-structure.md      # 论文结构 / 复现细节 / 术语参考表 / 软件许可清单
│   ├── term-glossary.md                  # 术语主表（必须 100% 沿用）
│   ├── ima-integration.md                # IMA 联用（可选）
│   └── pipeline-orchestration.md         # 检索→精读→存档 流水线衔接（v0.4）
└── assets/
    ├── report-template.md                # 完整报告模板（10 要点 + 综述变体）
    ├── report-template-quick.md          # 速览模板（3 要点）
    └── eval-checklist.md                 # 评测清单（10 篇 gold standard）
```

---

## 五、安装（Mavis / MiniMax Code 端）

技能已就位在 `%USERPROFILE%\.minimax\skills\paper-deep-reading\`，下次启动自动加载。

```powershell
# 查看是否已加载
Get-ChildItem "$env:USERPROFILE\.minimax\skills\paper-deep-reading\SKILL.md"

# 重新安装（从源目录覆盖）
Copy-Item -Path ".\paper-deep-reading" -Destination "$env:USERPROFILE\.minimax\skills\paper-deep-reading" -Recurse -Force

# 卸载
Remove-Item "$env:USERPROFILE\.minimax\skills\paper-deep-reading" -Recurse -Force
```

---

## 六、脚本自测

```powershell
cd "$env:USERPROFILE\.minimax\skills\paper-deep-reading\scripts"
python -m py_compile pdf_extractor.py images.py models.py sections.py figures.py io_utils.py extractors/*.py
python pdf_extractor.py --help
python pdf_extractor.py paper.pdf --pretty --image-dir ./imgs --max-images 12 --images-sort position
python ima_bridge.py list-kbs        # 可选，验证 IMA 联通（需凭证已配）
```

可选增强（非必须）：

```bash
pip install pymupdf pdfplumber       # 图片提取 / 增强文本提取
# OCR（无文本层 PDF 时）
winget install UB-Mannheim.TesseractOCR   # 另需 poppler 的 pdftoppm
pip install paddleocr paddlepaddle
```

---

## 七、常见问题

| 问题 | 处理 |
|---|---|
| 报告提示"扫描件/无文本层" | 会给出 `ocr_hint`（可复制命令）；装了 OCR 引擎可自动走 OCR 分支 |
| 提取文本乱码 | 安装 `pymupdf pdfplumber` 增强提取 |
| 章节定位不全 | 论文使用非标准章节标题，AI 会结合全文复核 |
| 图片没提取到 | 未装 PyMuPDF，或纯文本输入；报告会注明"图片未提取（原因）" |
| 为什么图不是我期望的 | v0.4 起由 AI 按重要性选取并给理由；可直接说"重点看图 5"覆盖 |
| 术语译名不一致 | 查 `references/term-glossary.md` 主表；你也可以直接说"X 应译为 Y" |
| Skill 未生效 | 确认已复制到 `~/.minimax/skills/` 并刷新会话 |
| IMA 联通失败 | 检查 `~/.config/ima/{client_id,api_key}` 是否配置 |
| 改完怎么验证 | 跑 `assets/eval-checklist.md` 的 A/B/C 三组 |

---

## 八、IMA 联用前置条件（可选）

1. 在 https://ima.qq.com/agent-interface 申请 **Client ID** + **API Key**
2. 写入 `~/.config/ima/client_id` 与 `~/.config/ima/api_key`（一行一个，UTF-8 无 BOM）
3. `ima-skill` 安装到 `~/.minimax/skills/ima-skill/`（与本 skill 同级）
4. Node 18+

详见 `references/ima-integration.md`。**不配置 IMA 时，PDF / 文本 / URL 输入完全不受影响。**

---

## 九、许可与声明

本 Skill 用于学术论文阅读辅助，翻译与摘录仅供学习与研究使用；请尊重原论文版权，**不要尝试绕过付费墙**。

---

## 十、版本变更

### v0.4（2026-09-12）— 能力补齐 + 输出统一

- `paper_type` 3 类 → **7 类枚举**（article / review / perspective / account / letter / editorial / unknown）+ 报告分支映射 + 用户可覆盖
- 图片选取：`key_images` 改为**候选池（≤12，按正文顺序）**，AI 选取 3-5 张 + **必写选取理由** + 列出未选用候选
- 新增 **OCR 兜底**（Step 1c + `ocr_hint` 字段）
- 新增 **Step 2.7 作者 / 致谢 / SI 溯源解析**
- 要点 9 **软件/数据库许可清单补全**（五组）
- 要点 10 **总结字数随篇幅自适应**
- 术语：新增**查表优先级**与**升格阈值**
- 新增 `assets/eval-checklist.md`、`references/pipeline-orchestration.md`
- §7.1 **统一输出约定**（与 `qm_paper_search` 对齐）
- 脚本：`detect_paper_type` 扩 7 类；`--max-images` 默认 5→12；新增 `--images-sort`

### v0.3（2026-09-09）— IMA 联用 + 关键图片 + 术语一致性

- 新增 `scripts/ima_bridge.py`；SKILL.md 增 IMA 输入分支与报告回写
- 新增 `references/ima-integration.md`、`references/term-glossary.md`
- 报告结构 10 要点 → 9 要点（删"原文对照翻译"，增"术语与图注规范"）→ v0.4 再回到 10 要点
- 要点 4 改"图文并茂"；新增 §5.1 术语一致性

### v0.2（2026-09-09）

- 脚本章节检测支持中英混排标题、Discussion 合并、SI 变体
- 新增 `figures_and_tables` / `paper_type` 字段
- 模板：综述变体、软件许可证、SI 缺失标注

### v0.1（初版）

- 基础 7 模块 10 要点；多后端 PDF 提取；5 章节定位
