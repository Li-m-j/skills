# paper-deep-reading — 修订记录（CHANGELOG）

> 原为 SKILL.md 顶部 HTML `<!-- modified ... -->` 注释块，2026-09-18 结构瘦身时迁移至此。
> 倒序排列（最新在上）。代码级修复不升版本号。

## 2026-09-18 · 结构瘦身（不改运行行为）

- 本文件创建：SKILL.md 顶部 HTML Modification Log 注释块 + 原 §10「版本变更」逐版明细整体迁入（见下方分隔线后）。
- frontmatter `description` 压缩为触发/能力/红线要点（原 8 行长句 → 7 行）。
- §4 七模块 10 要点逐条规则迁至 `references/report-modules-spec.md`，主文档保留编号占位 + 模块↔要点映射表；Step 3 增加必读链接。§10 收敛为指针。
- README 目录结构同步；SKILL.md 580 → 352 行。

<!-- modified 2026-09-18: 回归测试修复（代码级，不动版本号）——PDF 文本提取在 v0.3.0 拆分后
     三个后端全部失效，任何 PDF 都返回 extractor_used="none"：
     - fitz_backend.py / pdfplumber_backend.py：函数体引用了未导入的 fitz/pdfplumber，
       NameError 被 `except Exception: return "", 0` 静默吞掉 → 后端恒失败。已在函数内延迟导入。
     - extractors/__init__.py `_pdftotext_available()`：以 `pdftotext -v` returncode==0 判定，
       但 poppler/xpdf 各版本普遍返回 99 → 已装 pdftotext 也被判不可用。改为"能启动即可用"。
     - extract_with_fallback() 新增质量比较：pdftotext raw 模式会把章节标题并入同行段落，
       导致 sections.py 行锚定正则全空；当首选结果无任何独立成行章节标题时，
       自动改用下一后端（fitz → pdfplumber）的逐行输出。
     验证：合成论文 PDF 端到端 5/5 章节定位、图表引用、候选图片池、paper_type 判定全部恢复。 -->
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

---

## 版本变更明细（原 SKILL.md §10，逐版长文）

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
