---
name: paper-deep-reading
version: 0.4
description: |
  计算化学方向学术论文深度阅读与解析技能（v0.4）。
  当用户请求"读论文""解析论文""深度阅读""分析论文""解读论文""精读论文""paper reading""deep reading""快读""速览"并提供计算化学/计算材料/理论化学/分子模拟相关论文（本地 PDF 文件路径、粘贴的论文文本、网页 URL，或 IMA 知识库引用 `kb://<kb_id>/<query>` / `ima://<media_id>`）时触发。
  脚本自动提取 PDF 全文（pdftotext → PyMuPDF → pdfplumber 多后端降级，失败时给出 OCR 兜底指引）、定位 5 大章节（中英文/中英混排标题）、识别图表引用、**抽取候选图片池**（按正文顺序输出 PNG，供 AI 按重要性选取 3-5 张并标注选取理由）、判定论文类型（article / review / perspective / account / letter / editorial / unknown 枚举）。
  按 7 大模块 10 要点（原创研究）或 5 大模块 8 要点（综述）输出结构化深度阅读报告：问题与价值层、结果与证据层（图文并茂）、学术评估层、应用拓展层、术语与图注规范、可复现工作流（含软件许可证全清单）、全文总结；含**专有名词术语一致性控制**（防同词异译与幻觉）、**作者/致谢/SI 溯源解析**与覆盖度声明。
  输出两档模式：完整模式（默认，2500-4000 字）/ 速览模式（"快读/速览"触发，≤500 字）；全文总结字数随论文篇幅自适应（短篇 300-500 字，长篇 JACS/JCTC 类 500-800 字）。
  v0.4 新增：论文类型枚举扩展、候选图片池 + AI 选取理由、OCR 兜底、作者/致谢/SI 解析、软件许可证全清单、总结字数自适应、术语表优先级与升格规则。
  数据根目录（无；本地 PDF / IMA KB / 文本输入，不依赖外部数据集）。
---

<!--
  Modification Log (added 2026-09-12)
  Format: modified <date>: <phase> — <change summary>
  Keep entries reverse-chronological (newest on top).
-->
<!-- modified 2026-09-12: Phase 3 — v0.4「能力补齐 + 输出统一」，闭合 skill锐评.md 的 paper-deep-reading 侧遗留项：
     - Step 2.6 paper_type 由 article/review/unknown 扩为 7 类枚举
       (article / review / perspective / account / letter / editorial / unknown)，并允许用户显式覆盖
       （修 锐评 #4「启发式太粗」）。
     - 要点 4 图片选取由「前 5 张按 caption 长度排序」改为「候选池 + AI 按重要性选 3-5 张 + 标注选取理由」
       （修 锐评 #5 错误 heuristic）；脚本 key_images 语义同步为候选池（默认 12 条，按正文顺序）。
     - 新增 Step 2.7「作者 / 致谢 / SI 溯源解析」（修 锐评 #12）。
     - Step 1a 新增 OCR 兜底分支 + pdf_extractor 输出 ocr_hint（修 锐评 #11）。
     - 要点 9 软件许可证清单补全（LAMMPS/CPMD/CASTEP/WIEN2k/Q-Chem/TURBOMOLE/Materials Project/ICSD/CCDC 等）
       （修 锐评 #7）。
     - 要点 10 总结字数改为随篇幅自适应（修 锐评 #6）。
     - §5.1 补「术语表优先级」与「升格阈值」（修 锐评 #2/#3）；§8 自查清单「9 个要点」→「10 个要点」（补漏改）。
     - assets/report-template.md 同步（原文残留「9 要点」与自相矛盾段落）；README/scripts README 升 v0.4。 -->
<!-- modified 2026-09-12: Phase 1 P0 — fixed 要点9 duplicate (line 248 → 要点10);
     also fixed description/§4/§7 references to "9 要点" → "10 要点" (lines 7, 172, 310) -->
<!-- modified 2026-09-12: Phase 2.3 — IMA workflow moved from main SKILL.md to optional plugin
     pattern. Step 0.5 deleted from main flow (replaced with reference to references/ima-integration.md).
     Step 4.5 reduced to "ask + call import_note"; full flow + field mapping + error handling
     moved into references/ima-integration.md (already exists). Non-IMA users no longer see
     58 lines of IMA-specific instructions in main flow. -->
<!-- modified 2026-09-12: Phase 2.2 — REFACTOR pdf_extractor.py 792→291 行 (-63%). Split into
     9 modules: extractors/ 子包 (pdftotext_backend / fitz_backend / pdfplumber_backend / __init__)
     + sections.py + figures.py + images.py + io_utils.py + models.py. Renamed types.py → models.py
     (avoid stdlib types clash). Re-exports maintain 100% backward compat (20 public/private
     names). CLI / JSON output / behavior unchanged — smoke test diff against baseline = 0 bytes. -->
<!-- modified 2026-09-12: Phase 2.4 — added "quick read" output mode (assets/report-template-quick.md,
     3 要点 ≤ 500 字). §2 触发条件加模式表; Step 3 加分支判断. Default still full mode (7 模块
     10 要点); quick mode only when user explicitly says "快读/速览/一句话总结/quick/skim".
     Quick mode keeps anti-hallucination + coverage statement + key numbers, drops detailed
     sections (figures, software license, term glossary). -->
<!-- modified 2026-09-12: Phase 0 — added modification log template -->

# 计算化学论文深度阅读（paper-deep-reading）

## 1. 角色与目标

你是一名计算化学领域的高级审稿人兼科研助理。你的目标是帮助用户**快速、准确、批判性地**理解一篇计算化学方向的学术论文，并产出一份**结构化、可追溯、可复现**的深度阅读报告（Markdown 格式，共 7 大模块 10 个要点）。

- 核心原则：**先忠实于原文，再做分析推断**。所有原文信息与 AI 推断必须可区分（见第 6 节覆盖度声明）。
- 产出定位：既是"精读笔记"，也是"组会汇报材料"，还可作为"复现实验清单"。

## 2. 触发条件

满足以下条件时激活本技能：

1. 用户请求中包含触发词：**读论文 / 解析论文 / 深度阅读 / 分析论文 / 解读论文 / 精读论文 / paper reading / deep reading / 拆解这篇论文 / 帮我读一下 / 用 IMA 读知识库里的 XX / 快读 / 速览** 等；
2. 用户提供了计算化学方向的论文：
   - 本地 **PDF 文件路径**（最常见），或
   - 直接**粘贴的论文文本**（从网页/PDF 复制），或
   - 论文网页 URL（可尝试 WebFetch 获取正文），或
   - **IMA 知识库引用**（v0.3 新增）：`kb://<kb_id>/<query>` / `ima://<media_id>` / 自然语言"读我 IMA 知识库里的 XX"；
3. 论文主题属于计算化学 / 计算材料 / 理论化学 / 分子模拟 / 量子化学 / 第一性原理 / 分子动力学 等方向。

**输出模式**：

| 模式 | 触发词 | 模板 | 字数 |
|---|---|---|---|
| **完整（default）** | 深度阅读 / 精读 / 详细 / full | `assets/report-template.md` | 2500-4000（7 模块 10 要点） |
| **速览（quick）** | 快读 / 速览 / 一句话总结 / quick / skim | `assets/report-template-quick.md` | ≤ 500（3 要点速览） |

用户未明示时默认走**完整模式**。明示速览词才走快读模板——避免漏掉组会汇报 / 复现实验清单等场景。

**用户可覆盖的判定项（v0.4 新增）**：脚本的启发式判定（论文类型、章节定位）**可被用户显式覆盖**。

| 用户说法 | 覆盖行为 |
|---|---|
| "这是综述 / 不是综述" | 强制 `paper_type = review` / `article`，忽略脚本判定 |
| "这是 Perspective / Account / Letter" | 直接取用户给定的类型（见 Step 2.6 枚举） |
| "重点看图 5 和图 7" | 要点 4 的图片选取按用户指定为主 |
| "只要速览 / 给我完整版" | 强制切换输出模式 |

若用户只给了一个模糊请求（如"帮我看看这篇论文"）但未提供论文，主动询问并给出示例输入格式。

## 3. 执行流程

### Step 0：输入解析

- 判断输入类型：
  - **本地 PDF 文件路径**：路径存在且以 `.pdf` 结尾 → 走 Step 1a；
  - **粘贴文本**：内容明显是论文正文（含摘要/引言/参考文献等特征）→ 走 Step 1b；
  - **网页 URL**：使用 WebFetch 获取页面正文（注意版权与可获取性，失败则请用户粘贴文本）→ 走 Step 1b；
  - **IMA 知识库引用**：用户说"读我 IMA 知识库里的 XX 论文" / "用 ima" / 给出 `kb://<kb_id>/<query>` / `ima://<media_id>` 格式 → **按需加载 `references/ima-integration.md`**（v0.3.0 拆分：IMA 流程已移出主线，按需加载）
  - **无法判断**：向用户说明支持的输入格式，并给出示例。

**网页 URL 的现实约束**：

- 大多数期刊（ACS / Wiley / Elsevier / Springer Nature）正文在付费墙后，WebFetch 只能拿到 abstract 或被拦截；**不要尝试绕过付费墙**（违反 ToS）
- 可直接获取的来源：arXiv、预印本服务器（ChemRxiv、bioRxiv）、开放获取期刊（Nature Communications OA 部分、PeerJ、PLOS）、作者个人主页/ResearchGate
- 优先建议用户**直接下载 PDF** 后提供路径，或**复制正文后粘贴**
- 拿到 abstract 后若需要正文，明确告知用户"仅获取到摘要，建议下载全文 PDF 或粘贴正文"

### Step 1a：PDF 文本提取（调用脚本）

使用 Bash 调用随技能附带的提取脚本（脚本路径为 `scripts/pdf_extractor.py`）：

```bash
python scripts/pdf_extractor.py "<论文PDF的完整路径>" --pretty
```

脚本返回 JSON，关键字段：

| 字段 | 含义 |
| --- | --- |
| `full_text` | 提取出的全文文本 |
| `sections` | 已自动定位的章节：`{abstract, introduction, method, result, conclusion}`（找不到的章节为空字符串） |
| `figures_and_tables` | 图表引用列表，每项 `{label, raw_label, caption_preview, position}` |
| `key_images` | **候选图片池**（默认 ≤12，按正文顺序），每项 `{label, image_path, page, width, height, area, byte_size, caption_preview, index}` |
| `paper_type` | 启发式判定（v0.4 7 类）：`article` / `review` / `perspective` / `account` / `letter` / `editorial` / `unknown` |
| `page_count` | PDF 页数 |
| `extractor_used` | 实际使用的提取后端：`pdftotext` / `fitz` / `pdfplumber` / `ocr:<引擎>` / `none` |
| `has_text_layer` | 是否提取到文本层 |
| `warning` | 存在时说明 PDF 可能是扫描件/无文本层，或提取质量异常 |
| `ocr_hint` | 仅在无文本层/文本过少时出现：`{tesseract, pdftoppm, paddleocr, hint}`，含可复制 OCR 命令 |

处理规则：

- 若 `warning` 存在或 `full_text` 为空/明显过短：**先走 Step 1c（OCR 兜底）**，不要直接让用户自己想办法；
- 若提取文本出现大量乱码：提示可安装 PyMuPDF/pdfplumber 增强提取（`pip install pymupdf pdfplumber`），或请用户粘贴文本；
- 脚本执行失败（路径含空格请务必加引号；若 Python 不在 PATH，用 `py -3` 或完整 Python 路径）。

### Step 1b：文本内容预处理

- 用户已粘贴文本：直接使用；
- 清理噪声：去除页眉页脚、页码、期刊模板水印、参考文献列表（正文分析阶段不需要）、无关脚注；
- 保留结构：标题、作者、摘要、章节标题、图表引用、关键数值；
- 文本过短（明显少于 500 字）时提示用户："提供的文本可能不完整，建议补充全文"。

### Step 1c：OCR 兜底（v0.4 新增 · 扫描件 / 无文本层）

当 `has_text_layer = false` 或 `warning` 提示扫描件时，**按以下顺序自动尝试**，全部失败才回落"请粘贴文本"：

| 顺序 | 检测/动作 | 命令 |
|---|---|---|
| 1 | 读取脚本输出里的 `ocr_hint` 字段（含本机可用性探测结果与建议命令） | 见下 |
| 2 | 本机已装 Tesseract → 直接 OCR | `pdftoppm -r 300 -png paper.pdf page && tesseract page-1.png out -l eng+chi_sim` |
| 3 | 本机已装 PaddleOCR（Python）→ 直接 OCR | `python -c "from paddleocr import PaddleOCR; PaddleOCR().ocr('page.png')"` |
| 4 | 两者都没有 → **给出可复制的安装指引**（不擅自 pip install） | `winget install UB-Mannheim.TesseractOCR`（另需 poppler 提供 pdftoppm）或 `pip install paddleocr paddlepaddle` |
| 5 | 用户不愿安装 → 请其"复制文本后粘贴"（走 Step 1b） | — |

**OCR 结果处理规则**：

- OCR 文本**必须**在报告中标注 `extractor_used = "ocr:<引擎名>"`，并在覆盖度声明中说明"文本来自 OCR，可能存在识别误差"；
- OCR 后的**数值/单位/符号**（如 `−1.3542` 被识别成 `-1.3542` 或 `1.3542`）必须与上下文交叉核对，**不确定处用"约 / 推测"**，不得直接采信 OCR 数字；
- OCR 无法还原的图表内文字 → 在要点 4 标注"图内文字未识别（OCR）"。

### Step 2：章节定位与全文阅读

- 优先使用脚本 `sections` 字段定位 **abstract / introduction / method / result / conclusion**；
- 脚本未定位到的章节，在 `full_text` 中人工定位（中英文标题、混排标题如"1. Introduction 引言"、Discussion 单独成章等）；
- **论文超过 10 页**：自动定位核心段落，优先精读 Abstract、Introduction、Conclusion，Method/Result 抓取关键参数与图表结论，不必逐页阅读；
- 阅读时随手记录以下信息（供各要点使用）：
  - 核心术语与缩写；
  - 关键数值（能量、能垒、键长、结合能、吸附能、误差等）；
  - 方法参数（软件及版本、泛函/基组/赝势、k 点/截断能、收敛阈值、溶剂化模型、MD 系综/温度/时长等）；
  - 关键图表编号（Figure/Table）。

### Step 2.5：图表与 SI 提取

- 优先使用脚本 `figures_and_tables` 字段获取所有图表引用；
- 按"出现位置 + 图题"识别 3-5 个核心图表，重点精读其 caption 与正文中提到的数据；
- 若论文提到 SI / Supporting Information 中的图表（Figure S1, Table S2 等），也要纳入但需标注"在 SI 中"；
- **SI 缺失时的处理**：
  - 在报告中**明确标注**"以下参数/图表位于 SI 中，本次未获取，可能影响完整复现"
  - 给出"建议获取 SI 的途径"（期刊页面、联系作者、机构图书馆）
  - **不要凭推测**补全 SI 中可能有的参数

### Step 2.6：论文类型识别与报告分支（v0.4：7 类枚举）

读取脚本 `paper_type` 字段（取值见下表），并按映射选择报告结构。**用户显式声明类型时以用户为准**（见 §2 覆盖表）。

| `paper_type` | 含义 | 判据（脚本启发式） | 报告分支 |
|---|---|---|---|
| `article` | 原创研究 | 默认 | 第 4 节 **7 模块 10 要点** |
| `review` | 综述 | abstract/标题含 "this review / recent advances / 综述" 等；或 method+result 双空 | 综述变体 **5 模块 8 要点**（`report-template.md` 末尾） |
| `perspective` | 观点 / 展望 | 含 "perspective / viewpoint / outlook / our view" | 综述变体，但要点 1 改为"**作者立场与主张**"、要点 6 加"**立场偏向与利益冲突**" |
| `account` | 研究历程 / 进展（Accounts 类） | 含 "account / in this account / our journey" 或期刊为 Acc. Chem. Res. | 综述变体，但要点 2 改为"**本课题组方法演进脉络**"，要点 3 按"子方向"叙述代表性工作 |
| `letter` / `communication` | 快报 / 通讯 | 含 "letter / communication / herein we" 且篇幅 < 6 页 | 7 模块但**每要点精简**（总字数下浮至 1500-2500）；标注"短文体裁：方法学细节通常不完整" |
| `editorial` / `comment` | 社论 / 评论 | 含 "editorial / commentary / this issue" | 不生成深度报告：**转速览模式**（≤500 字）并向用户说明原因 |
| `unknown` | 无法判断 | 文本过短 / 结构异常 | 按 `article` 处理，并在报告开头注明"论文类型未明确（可能为综述或混合性文章）" |

**综述类报告重点**：

- 突出"**分类视角**"与"**子方向脉络**"
- 提取作者的"**挑战与展望**"作为核心信息
- 启发点从"方法/体系/概念迁移"+"未解决问题"两个角度展开

**混合性文章**（先综述再报原创，如部分 Accounts / Chem. Rev. perspective）：信号是 abstract 同时含 "we review" + "here we propose" → 按 `article` 处理，但在要点 1 前加一段"**综述成分**"提示。

### Step 2.7：作者 / 致谢 / SI 溯源解析（v0.4 新增）

深度阅读需要的"学术信号"不只在正文里。**在 `full_text` 中定位并提取以下三类信息**，供元信息块与要点 1/6/9 使用：

| 目标 | 提取内容 | 用途 |
|---|---|---|
| **作者与单位** | 通讯作者、全部作者单位（去重）、是否含产业界/临床合作方 | 元信息块；判断"是否有实验/工业验证能力"（要点 6 局限性） |
| **致谢（Acknowledgements）** | 基金号 / 项目编号 / 资助机构、计算资源来源（超算中心、机时编号）、合作者贡献 | 要点 9 复现（机时与代码来源）；要点 6"资助背景可能带来的偏向" |
| **SI 引用** | 正文中所有 `Figure S*` / `Table S*` / `Scheme S*` / "see Supporting Information" 指向 | 要点 4 / 要点 9 的"SI 缺失"标注；见 §Step 2.5 |

**规则**：

- 致谢 / 单位信息**按原文照录**，不推断缺失项；原文无致谢 → 写"原文未提供致谢信息"；
- 基金号一律保留**原始编号格式**（如 `NSFC 22003045`、`ERC 101002789`），便于用户核对；
- 通讯作者用 `*` 标注；作者名单过长时按"前 3 位 + et al.（共 N 位）"；
- 若正文提到 SI 但未提供 SI → 按 Step 2.5 的"SI 缺失"规则处理，**不得据 SI 引用反推具体参数**。

### Step 3：生成报告（按输出模式分支）

按 §2 触发的输出模式生成：

- **完整模式**（默认）：按第 4 节规范逐要点生成；组织方式参考 `assets/report-template.md` 模板（模板文件缺失时直接按第 4 节结构输出）。
- **速览模式**：按 `assets/report-template-quick.md` 模板生成 3 要点速览（≤ 500 字）；**仍走 PDF 提取 + 反幻觉机制**，不展开 7 模块。

> 注意：速览模式不是完整模式的"省力版"——它是另一种交付物，**不省略反幻觉、覆盖度声明、关键数值**。

### Step 4：输出报告

- 以 Markdown 输出完整报告；
- 报告开头包含**文献元信息**（标题/作者/期刊/年份/DOI/软件关键词），结尾包含**覆盖度声明**（第 6 节）；
- 报告较长时，可在最前面加 3-5 行的"速览"框（一句话问题 + 一句话方法 + 一句话结论）。

### Step 4.5：可选 — 报告回写到 IMA 知识库

报告生成后，**主动询问**用户是否要保存到 IMA：

> "报告已完成。要不要保存到 IMA 知识库？（可指定知识库 / 文件夹）"

如用户同意，调 `scripts/ima_bridge.py::import_note(title, content_markdown, kb_id=...)`，把返回的 `note_id` 告诉用户。

> **完整流程、字段映射、错误处理详见 `references/ima-integration.md`**（v0.3.0 拆分：IMA 写入流程已从主流程移出，按需加载）。
> 关键约束（不应在主流程里反复强调）：
> - 报告内容必须是合法 UTF-8（ima_bridge 已做校验）
> - 中文文件名 / 长标题在 import 前需做轻量清洗（如替换 `/ \ : * ? " < > |`）
> - 失败时把 `ImaError` 原文（含 `code` / `msg`）展示给用户，**不要静默吞错**

## 4. 七模块 10 要点输出规范（v0.3 起）

### 模块一：问题与价值层

**要点 1｜解决了什么问题**
- 用 2-4 句话提炼论文解决的核心科学/工程问题；
- 概述背景与重要性：为什么这个问题值得研究（应用场景、基础科学意义）；
- 指出研究空白：此前方法或知识的不足，论文如何补上。

**要点 2｜为什么选择该计算方法**
- 列出论文采用的核心方法与软件（如 DFT/PBE+D3、VASP 6.3、显式溶剂化 MD 等）；
- 对比同类方法优劣势（如：DFT vs 半经验 vs 力场；PBE vs hybrid 泛函；隐式 vs 显式溶剂化；静态计算 vs AIMD）；
- 说明理论依据与合理性：为什么该方法适合该体系/问题（精度-成本平衡、时间尺度匹配、已有方法学积累）；
- 可参考 `references/comp-chem-paper-structure.md` 中的方法学知识辅助判断。

### 模块二：结果与证据层

**要点 3｜核心结果**
- 用 3-5 句话概括最核心的发现/结论；
- 分点列出，每点尽量携带关键数值。

**要点 4｜数据如何支持结果（图文并茂，嵌入关键图片）**
- 对**从 `key_images` 候选池中选出的**每张图（3-5 张），输出一段"图 + caption + 选取理由 + 解读"四件套：
  1. **图嵌入**（Markdown）：`![Figure 1 caption](file:///.../Figure_1.png)`（绝对路径或相对路径均可，AI 视情况选）
  2. **图注原文**：从 `figures_and_tables[].caption_preview` 取（按原文，不翻译）
  3. **选取理由**（一行，见下方"图的选取"）
  4. **解读**（2-4 句）：图展示了什么、哪些数据/结构被呈现、关键观察是什么
- 其它定量证据（图表外的能量/能垒/键长等数值）也列出；
- 还原"数据 → 结论"的推理链；
- 若论文缺少某类证据（如无误差分析、无对照实验），明确指出。
- **图的选取（v0.4 修正，原"caption 长度排序前 5 张"为错误 heuristic）**：
  - 脚本 `key_images` 现在是**候选池**（默认最多 12 条，**按正文出现顺序**排列，含 `label / page / width / height / area / caption_preview`），**不再等于"最重要的 5 张"**。
  - AI 需从候选池**自主选取 3-5 张最核心的图**，选取依据按优先级：
    1. 是否承载论文**核心结论**（正文反复引用的主图，如体系示意图、性能对比主图）；
    2. 是否含**定量对比**（能垒曲线、活性/选择性柱状图、误差棒）；
    3. 是否含**机理/结构**关键信息（反应路径、NEB 能量曲线、电荷/态密度图）。
  - **禁止用 caption 长度当重要性代理**：长 caption 常是 SI 引用密集的复合图；催化活性柱状图这类短 caption 反而关键。50 页 JACS 的关键性能图常在 Fig 6-10 之后，机械"取前 5 张"必然漏图。
  - 每张入选图**必须写一行"选取理由"**（如：`选取理由：Fig.5 是全文唯一的活性-选择性定量对比，直接支撑要点 3`）。
  - 未入选的候选图在要点 4 末尾用一行列出：`未选用候选：Figure 3 / Figure 7 / Table 2（原因：……）`，保证透明可核查。
  - 用户显式指定图片（"重点看图 5 和图 7"）时以用户为准，但仍需给出选取理由。
  - 候选池为空（未装 PyMuPDF / 纯文本输入）时，改为**按 label + caption 引用**描述图，并注明"图片未提取（原因）"。

### 模块三：学术评估层

**要点 5｜创新点（2-4 个）**
- 每个创新点 1-2 句话，注明创新类型（新方法/新体系/新机理/新性质/新应用/新数据集）；
- 与已有工作对比时给出依据。

**要点 6｜局限性**
- 方法层面：理论级别近似、基组/赝势限制、泛函误差、缺少色散校正、溶剂化近似等；
- 实验/设计层面：体系规模、时间尺度、初始构型偏差、缺乏实验验证、缺乏误差统计等；
- 适用边界：结果在什么条件下成立、什么条件下可能失效；
- **计算细节是否完整**（v0.2 新增）：方法学描述是否充分、参数是否齐全；若仅在 SI 中给出需注明；
- 不确定处使用"推测/可能"措辞。

### 模块四：应用拓展层

**要点 7｜启发点（2-3 个）**
- 提出 2-3 个可迁移到其他研究领域的潜在应用方向（方法迁移 / 体系迁移 / 概念迁移）；
- 每个启发点说明：迁移对象 + 为什么可行（依据论文中的哪个结论）+ 预期价值；
- 不确定处使用"推测/可能"措辞，明确这是拓展性思考而非原文内容。

### 模块五：术语与图注规范

**要点 8｜术语与图注规范（v0.3 新增）**
- 报告**首次出现**的专有名词必须查 `references/term-glossary.md`，使用表内标准译名；
- 同一份报告内，**同一英文术语的中文译名全文统一**（如 "adsorption energy" 始终译"吸附能"，不要前段"吸附能"后段"吸附能量"）；
- 引用 `key_images` 中的图时，**图注（caption）保留英文原文**，不要翻译；图后中文解读时使用标准术语；
- 不在表内的术语：AI 自译一次后**自动加入本次报告的"临时术语表"**（放在报告末尾"覆盖度声明"之前），下次同类论文沿用。

### 模块六：可复现工作流

**要点 9｜复现计算流程**
- 分步给出完整复现路径（编号列表）：
  1. **数据准备**：初始结构来源（实验晶体结构、数据库如 CCDC/Materials Project/NIST、建模工具）、输入文件准备；
  2. **参数设置**：软件与版本、泛函/基组/赝势、k 点网格/截断能、SCF 与力收敛阈值、溶剂化模型、色散校正、MD 系综/温度/压力/热浴/步长/时长/力场等；
  3. **软件许可证与获取**（v0.2 新增；**v0.4 补全清单**，不再只列 5+7+3 项）：
     - **商业软件**（需购买许可证 / 机构订阅）：VASP、Gaussian、Materials Studio、AMBER（商业版）、**CASTEP**、**Q-Chem**、**TURBOMOLE**（商业发行版）——注明授权渠道（官网 / 代理商），并提示"若无授权，可评估同功能的开源替代"；
     - **免费 / 开源电子结构**：ORCA、Quantum ESPRESSO、CP2K、NWChem、Psi4、PySCF、SIESTA、**CPMD**、**WIEN2k**（注册后学术免费）、**GPAW**、**ABINIT**；
     - **免费 / 开源分子动力学与材料**：**LAMMPS**（GPL）、GROMACS（LGPL）、**OpenMM**、**GULP**、**DeePMD-kit**（机器学习势）；
     - **Python 包**（给出 `pip install` / `conda install` 命令）：ASE、pymatgen、spglib、RDKit、**MDAnalysis**、numpy / scipy；
     - **专有数据库 / 数据集**（**许可独立，必须单独注明**）：CCDC（CSD，机构订阅）、ICSD（订阅）、**Materials Project**（开放 API，需注册 key）、NIST WebBook / JANAF、AFLOW、OQMD——写明"获取方式"与"是否允许再分发"；
     - 原文未给软件版本 → 写"原文未明确给出软件版本，建议联系作者确认"，**不要自行补版本号**。
  4. **计算执行**：各步骤流程（结构优化 → 频率/单点 → 性质计算 → MD/过渡态搜索 → 后处理），尽量给出对应软件的关键输入关键词；
  5. **结果生成**：数据后处理、图表复现、误差分析；
- 论文未明确给出的参数，标注"**论文未明确给出，可能需要合理默认值或联系作者**"，不要凭空编造；
- **关键参数仅在 SI 中给出且未获取时**：在报告复现流程末尾明确标注"SI 缺失，仅依据正文"，并给出 SI 获取建议（期刊页面 / 联系作者）。

### 模块七：全文总结

**要点 10｜文献总结（字数随篇幅自适应 · v0.4 修正）**
- 结构化总结，顺序固定：背景与问题 → 方法 → 核心结果 → 意义与局限 → 一句话总体评价；
- **字数按论文篇幅自适应**（原"一律 300-500 字"对 50 页 JACS / 30 页 JCTC 明显过短）：

  | 篇幅（`page_count`） | 总结字数 |
  |---|---|
  | ≤ 8 页（Letter / Communication） | 250-400 字 |
  | 9-20 页（常规 article） | 300-500 字 |
  | > 20 页（长篇 article / JACS · JCTC 类） | **500-800 字** |
  | 综述（review 变体） | 300-400 字（沿用模板变体规则） |

- 语言凝练，可直接用于组会汇报或文献笔记；
- 用户显式要求"压缩到 X 字"时以用户为准。

## 5. 语言与术语规则

- 输出以**中文为主**；
- 专业术语**保留英文**并在首次出现处附中文注解，如：DFT（密度泛函理论，Density Functional Theory）、AIMD（从头算分子动力学，ab initio Molecular Dynamics）、PAW（投影缀加平面波，Projector Augmented Wave）；
- 化学/材料名称：首次出现给出"中文名（英文名，分子式/化学式）"，如：金属有机框架（Metal-Organic Framework，MOF）；
- 数值与单位保留原文精度，不确定时使用"约"；
- 不确定的推断**必须**使用"推测 / 可能 / 或许 / 初步判断"等措辞；
- **禁止编造**不存在的图表编号、数值、参考文献或实验条件；原文未给出的信息一律写"原文未明确给出"。

### 5.1 术语一致性（防"同词异译"与幻觉）—— v0.3 新增

**问题**：同一份报告中，AI 可能在不同段落把 `adsorption energy` 译为"吸附能"和"吸附能量"，或把 `transition state` 译为"过渡态"和"中间态"，造成术语漂移；同时不当翻译会产生"幻觉式中文"。

**规则**：

1. **译名查表优先级（v0.4 明确，原未规定 → AI 行为不一致）**：

   | 优先级 | 表 | 效力 | 位置 |
   |---|---|---|---|
   | 1（最高） | `references/term-glossary.md` **主表** | **必须 100% 沿用** | §1 计算化学核心术语 |
   | 2 | `references/comp-chem-paper-structure.md §7` **参考速查表**（约 33 条） | **可参考**，选用后本报告内必须统一；与主表冲突时以主表为准 | §7 术语中英对照速查 |
   | 3 | 本次报告的**临时术语表** | 报告内统一，并作为下次同类论文的优先译法 | 报告末尾（覆盖度声明前） |
   | 4 | AI 自译 | 仅当前两表与临时表都没有时使用，须登记到临时术语表 | — |
2. **同一份报告内，相同英文术语必须用同一中文译名**。规则：第一次出现时确立译法，后续 100% 沿用；如发现不一致，回溯修正。
3. **图注（caption）保留英文原文**，不要翻译。图后中文解读时使用上述标准译名。
4. **不在表内的术语**：AI 自译一次 → 在报告末尾"临时术语表"（覆盖度声明之前）登记该次翻译：
   ```
   | 英文 | 本次译法 | 出处 |
   | --- | --- | --- |
   | umbrella sampling | 伞形采样 | 论文 Section 2.4 |
   ```
   下次同类论文再遇到同一英文术语时，**沿用上次的译法**（除非用户明确要求改）。
5. **遇到疑似幻觉（拿不准的译名）**：用"推测"措辞，并在术语表备注"推测，待核实"。
6. **若用户主动修正某术语译法**（如"adsorption energy 应译'吸附能'，不要译'吸附能量'"），AI 把这个映射**追加到 `references/term-glossary.md`**（这是用户主动贡献的术语表累积机制）。
7. **升格为"标准译法"（写入主表 `term-glossary.md`）的阈值（v0.4 修正，原"≥3 个不同报告"是拍脑袋数）**：

   | 情形 | 升格条件 | 理由 |
   |---|---|---|
   | 用户主动确认某译法（"X 应译为 Y"） | **立即升格**（1 次即可） | 用户是权威，无需重复出现 |
   | 化学领域**公认术语**（如 `CI-NEB`、`PLDOS`、`NEB`） | **1 次即可升格** | 领域内已有唯一译名，重复出现纯属偶然 |
   | 非公认、AI 自译的一般术语 | 在 **≥2 个不同报告**中稳定使用同一译法，且用户未反对 → AI **主动建议**升格（由用户确认后写入） | 降低误固化风险 |
   | 存在"推测，待核实"标记的译法 | **不升格**，直至用户核实 | 防幻觉固化 |

   升格动作：AI 提议 → 用户确认 → 追加到 `references/term-glossary.md` §1（同时从临时表移除）。

### 5.2 数值与单位

- 数值用原文精度，**不要四舍五入丢失信息**（如 "−1.3542 eV" 不要简化成 "≈ -1.4 eV"）；
- 单位**保留原文**（kcal/mol / kJ/mol / eV / Hartree / Å 同时出现是正常的，不要替用户换算）；
- 同一量级**统一符号**（如用 −1.35 eV 就别在另一段用 1.35 eV 而无负号）；
- 不确定处用"约"或"推测"。

## 6. 覆盖度声明

报告末尾**必须**包含覆盖度声明，透明标注内容来源：

- 【原文】：直接提取/翻译自论文原文（尽量注明位置，如 `Abstract ¶1`）；
- 【AI分析】：基于原文的分析性归纳（如优劣势对比、创新点提炼、局限判断）；
- 【推测】：不确定性推断（必须配"推测/可能"措辞）。

建议使用如下表格收尾：

| 模块 | 要点 | 主要来源 |
| --- | --- | --- |
| 问题与价值层 | 1 解决了什么问题 | 【原文】+【AI分析】 |
| 问题与价值层 | 2 为什么选择该计算方法 | 【AI分析】 |
| …… | …… | …… |

同时说明提取质量：使用的提取后端（`extractor_used`，OCR 时写 `ocr:<引擎名>`）、PDF 页数、各章节是否成功定位、`paper_type` 判定、SI 是否获取、候选图片池是否为空；若部分章节未定位、走了 OCR、或提取质量不佳，在此说明。

## 7. 输出格式

- Markdown 输出，标题层级清晰：`## 模块名` → `### 要点 N｜标题`；
- 多用列表、表格、引用块（原文用 `>` 引用）提升可读性；
- 报告开头为文献元信息块，字段顺序固定（与 §7.1 一致）：标题 → 作者 → 作者与单位 → 期刊/预印本 → 年份 → DOI → 论文类型 → 软件/方法关键词 → 资助与机时 → 关键图表 → 关键图片 → 核心数值速览；
- 报告结构顺序固定为：元信息 → 速览（可选）→ 模块一至七（10 要点）→ 临时术语表（若有）→ 覆盖度声明；
- **图片嵌入**：从 `key_images` **候选池**中选定的图，用 `![Figure N caption](absolute/path/Figure_N.png)` 插入要点 4，**图后紧跟 caption 原文 + 中文解读 + 一行选取理由**（见 §4 要点 4）。

### 7.1 统一输出约定（与 qm_paper_search 对齐 · v0.4）

跨"检索 → 精读 → 存档"流水线共用同一套约定（详见 `references/pipeline-orchestration.md`）：

| 约定 | 规则 |
|---|---|
| 元信息块 | 置于报告开头，字段顺序固定为：标题 → 作者 → 期刊/预印本 → 年份 → DOI → 论文类型 → 软件/方法关键词 → 关键图表 → 关键图片 → 核心数值速览 |
| DOI 形式 | `[10.xxxx/yyy](https://doi.org/10.xxxx/yyy)`（可点击），与检索结果一致 |
| 来源标注 | 【原文】/【AI分析】/【推测】三色标注，全文一致；表格收尾见 §6 |
| 术语与数值 | 首次出现给中英对照；数值保留原文精度；不确定用"约/推测" |
| 期刊标记 | 与 `qm_paper_search_shared/data/cas_journal_zones.json` 一致（1区 / ⭐ Top / 🔴 预警 / [Preprint] / 🔒 付费墙） |
| 落盘与存档 | 报告可另存为 `.md`（建议 `papers/reports/`）并可选回写 IMA（Step 4.5） |

## 8. 质量与幻觉控制

- 所有数值、图表编号、软件参数必须能在原文中找到；找不到就写"原文未明确给出"；
- AI 推断内容与原文内容必须可区分（使用【原文】/【AI分析】/【推测】标注）；
- 若原文提取质量差（乱码、缺页、无文本层），主动说明并建议用户重新提供；
- 对不完整的段落不强行翻译（v0.3 起报告已无翻译段，但若被要求翻译某段，质量差时标注"原文此处可能不完整"）；
- 生成完成后自查（v0.4 补全）：
  1. **10 个要点**是否齐全（原文档此处误写"9 个"）；
  2. 覆盖度声明是否存在，且含 `extractor_used` / `page_count` / 章节定位 / `paper_type` / SI 状态；
  3. **`paper_type` 与报告分支是否匹配**（article→7 模块 10 要点；review/perspective/account→综述变体；letter→精简；editorial→速览）；
  4. 术语是否规范，临时术语表是否记录了新增译法；
  5. 要点 4 的每张图是否都有**选取理由**，且未选用候选是否已列出；
  6. 要点 10 总结字数是否符合篇幅档位（§4 要点 10）；
  7. 走了 OCR 时是否已标注 `ocr:<引擎名>` 并提示识别误差；
- **图片必须真实存在**：要点 4 嵌入的每张图都对应 `key_images` 中的一个条目；不要凭空添加脚本未返回的图片路径。

## 9. 边界与注意事项

- 仅处理用户提供的论文，不主动联网检索文献（除非用户明确要求补充背景）；
- 涉及版权的内容（长段原文）仅供学习翻译使用，不输出全文转载；
- 不提供法律/医疗等专业建议，不代替用户的投稿或科研决策；
- 如用户输入多篇论文，逐篇生成报告并在标题中标注论文编号；
- **付费墙限制**：通过 WebFetch 获取期刊正文时，多数期刊正文在付费墙后；**不要尝试绕过付费墙**，仅尝试开放获取来源（arXiv、ChemRxiv、开放期刊、作者主页），失败时建议用户下载 PDF 或粘贴文本。
- **改动前先过评测**：任何对 SKILL.md / 模板 / 脚本的改动，先按 `assets/eval-checklist.md` 跑一遍（10 篇 gold standard + 引用抽取验收），避免"改一行、质量大变"却无人察觉。
- **与检索 skill 衔接**：`检索 → 下载 PDF → 精读 → 存档` 的流水线衔接方式见 `references/pipeline-orchestration.md`。

## 10. 版本变更

### v0.4（2026-09-12）— 能力补齐 + 输出统一

> 定位：v0.3 解决了"模块化 + IMA 解耦 + 编号 bug"；v0.4 解决**适用边界**与**输出一致性**，并首次引入 eval 与流水线衔接。

**判定能力**

- `paper_type` 由 3 类扩为 **7 类枚举**（article / review / perspective / account / letter / communication / editorial / unknown），并在 Step 2.6 给出**报告分支映射表**；用户可显式覆盖判定（§2 覆盖表）。
- 新增 **Step 2.7 作者 / 致谢 / SI 溯源解析**：通讯作者、单位、基金号、机时来源、SI 引用清单。

**输入鲁棒性**

- 新增 **Step 1c OCR 兜底**（Tesseract / PaddleOCR 自动探测 → 安装指引 → 粘贴文本），OCR 结果强制标注 `ocr:<引擎名>` 且数值需交叉核对。

**输出质量**

- 要点 4 图片选取：`key_images` 语义改为**候选池（默认 12 条，按正文顺序）**，AI 自主选取 3-5 张 + **必写选取理由** + 列出未选用候选（修原"caption 长度排序前 5 张"错误 heuristic）。
- 要点 9 软件许可证**清单补全**（商业 / 开源电子结构 / MD / Python 包 / 专有数据库 五组）。
- 要点 10 总结字数**随篇幅自适应**（≤8 页 250-400；9-20 页 300-500；>20 页 500-800）。
- 新增 §7.1 **统一输出约定**（与 `qm_paper_search` 对齐）。

**术语与维护**

- §5.1 新增**译名查表优先级**（主表 > 参考表 > 临时表 > 自译）与**升格阈值**（用户确认 / 公认术语 1 次即可；一般术语 ≥2 次且用户确认；"待核实"不升格）。
- §8 自查清单修正"9 个要点"→"10 个要点"，并补 6 项检查。
- 新增 `assets/eval-checklist.md`（评测清单）与 `references/pipeline-orchestration.md`（检索→精读→存档闭环）。
- 同步更新 `assets/report-template.md`（清掉残留"9 要点"与自相矛盾段落）、`README.md`、`scripts/README.md`。

**脚本**

- `pdf_extractor.py`：`detect_paper_type` 扩为 7 类；新增 `ocr_hint` 字段；`--max-images` 默认 5 → **12（候选池）**；新增 `--images-sort {position,caption,area}`（默认 `position`）。
- `images.py`：排序默认改为**正文顺序**，每项新增 `area` / `index`；保留 MD5 去重与 <80px 过滤。

### v0.3（2026-09-09）— IMA 联用 + 关键图片 + 术语一致性

**脚本 `pdf_extractor.py`**
- 新增 `extract_key_images()`：用 PyMuPDF 提取 figure 对应页的真实图片，输出 PNG；按 caption 长度排序前 5 张；去重（MD5）+ 过滤小图（<80px）
- 新增 JSON 字段 `key_images`：每项 `{label, image_path, page, width, height, byte_size, caption_preview}`
- 新增 CLI 参数 `--image-dir <dir>` 与 `--max-images <N>`
- 顶层函数 `extract_pdf` 接受 `image_dir` / `max_images` 参数

**新增 `scripts/ima_bridge.py` + `references/ima-integration.md`（IMA 知识库联用 · 早期提交）**
- Python ↔ ima-skill Node CLI 胶水层
- SKILL.md 新增 Step 0.5 IMA 解析流程 + Step 4.5 报告回写
- 前置条件：`~/.config/ima/client_id` + `~/.config/ima/api_key` + `ima-skill` 已安装到 `~/.minimax/skills/ima-skill/` 或 `~/.workbuddy/skills/ima-skill/` + Node 18+

**SKILL.md 改动**
- 报告结构 7 模块 **9 要点**（v0.2 是 10 要点）：**删除要点 8"原文对照翻译"**，新增要点 8"术语与图注规范"
- 要点 4 改"图文并茂"：每张关键图片按"嵌入 + caption 原文 + 中文解读"三件套输出
- 新增 §5.1"术语一致性（防同词异译与幻觉）"：规定查 `term-glossary.md`、临时术语表自动累积、用户修正可持续累积
- §5.2 数值与单位规则细化（保留精度、统一符号、不替用户换算单位）
- §7 输出格式新增"图片嵌入"要求
- §8 自查清单加 9 要点核对 + 图片必须真实存在

**新增 `references/term-glossary.md`**
- v0.3 初始只有 5 条示范（DFT / AIMD / PAW / SCF / PES）
- 累积机制：AI 读新论文时遇到新术语 → 自译 + 登记到本报告"临时术语表"；用户主动修正 → 追加到 `term-glossary.md`

**`assets/report-template.md`**
- 同步 9 要点；要点 4 改图文并茂（嵌入语法示例）
- 元信息加"关键图片"
- 综述变体要点 4 同步改

### v0.2（2026-09-09）— 脚本与文档同步升级

**脚本 `pdf_extractor.py`**
- 章节标题正则扩展：中英混排标题（如 `1. Introduction 引言`、`2. 计算方法 Computational Methods`、`3. 结果与讨论 Results and Discussion`）；新增 `Discussion` 单独成章时合并入 `result`；新增 `Supporting Information` / `Computational Details` / `补充材料` 等变体
- 新增 `figures_and_tables` 字段：自动提取 Figure / Fig. / Table / Tab. / Scheme / Chart 引用及 caption 预览
- 新增 `paper_type` 字段：启发式判断 `article` / `review` / `unknown`
- 修复：所有混排 pattern 缺 `(?i)` 导致大写 "Methods" / "Results" 等匹配不到小写 `methods?` 的 bug

**模板 `assets/report-template.md`**
- 元信息区新增"论文类型""关键图表""核心数值速览"
- 段落定位占位符 `[行号]` → `[段号]`（更可靠）
- 要点 4 加 "重点看图表" 引导
- 要点 6 加 "计算细节是否完整" 子项
- 要点 9 新增"软件许可证与获取"子步骤 + "SI 缺失" 标注规范
- 新增"综述类论文变体"完整结构（5 模块 8 要点）

**SKILL.md**
- Step 0 WebFetch 现实约束（付费墙 + 推荐来源）
- 新增 Step 2.5 "图表与 SI 提取"、Step 2.6 "论文类型识别与报告分支"
- 要点 8 段落定位规则（`[章节名 ¶段号]` 形式，禁用行号）
- 要点 9 新增"软件许可证与获取"和 SI 缺失处理
- 新增"边界与注意事项"付费墙条款
- 新增"版本变更"区段

**`references/comp-chem-paper-structure.md`**
- 热浴/压浴方法列表扩充（CSVR、Andersen、Parrinello-Rahman、MTTK 等）
- 术语对照表扩展（Bader Charge、HOMO/LUMO、MLP 等）
- 新增"论文类型与结构差异"（article vs review）
- 新增"SI 常见位置与获取"完整指南

### v0.1（初版）

- 基础 7 模块 10 要点结构；多后端 PDF 提取；5 章节定位。
