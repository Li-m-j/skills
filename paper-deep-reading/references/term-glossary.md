# 计算化学专有名词对照表

> 本文件供 AI 在生成深度阅读报告时查阅，确保专有名词的**中文译名全文统一**，避免"同词异译"与"幻觉式中文"。
>
> **使用规则**（详见 `SKILL.md §5.1`）：
> 1. 报告首次出现某术语时**按优先级查表**：本表（主表，必须 100% 沿用）→ `comp-chem-paper-structure.md §7`（参考表，可参考）→ 本次报告临时术语表 → AI 自译
> 2. 同一份报告内，同一英文术语必须使用同一中文译名
> 3. 不在本表的术语：AI 自译一次 → 登记到本次报告"临时术语表"
> 4. 用户主动修正 → 追加到本表（**用户贡献的累积机制**）
> 5. 升格为"标准译法"的条件（v0.4）：**用户确认 / 领域公认术语 → 1 次即可升格**；一般自译术语需在 ≥2 个报告稳定使用且用户确认；标"待核实"的不升格

---

## 1. 计算化学核心术语（主表 · 必须 100% 沿用）

| 英文 | 标准中文 | 缩写 | 备注 |
| --- | --- | --- | --- |
| Density Functional Theory | 密度泛函理论 | DFT | 最常用 |
| ab initio Molecular Dynamics | 从头算分子动力学 | AIMD | 也作 "First-principles MD" |
| Projector Augmented Wave | 投影缀加平面波 | PAW | VASP 默认 |
| Self-Consistent Field | 自洽场 | SCF | |
| Potential Energy Surface | 势能面 | PES | |
| Transition State | 过渡态 | TS | **不要译为"中间态"**（中间态 = intermediate） |
| Nudged Elastic Band | 微动弹性带 | NEB | 也译"弹性带"；**统一为"微动弹性带"** |
| Climbing Image NEB | 爬坡图像微动弹性带 | CI-NEB | 不要译为"上升图像" |
| Intrinsic Reaction Coordinate | 内禀反应坐标 | IRC | |
| Projected Density of States | 投影态密度 | PDOS / PLDOS | 不要译为"局部态密度" |
| Adsorption Energy | 吸附能 | — | **不要混用"吸附能量"** |
| Binding Energy | 结合能 | — | 与吸附能区分：结合能指分子内/界面总结合 |
| Reaction Barrier | 反应能垒 | — | 与活化能（activation energy）在文献中常混用，按原文语境 |
| Periodic Boundary Condition | 周期性边界条件 | PBC | |
| Zero-Point Energy | 零点能 | ZPE | |
| Machine Learning Potential | 机器学习势函数 | MLP | 也作 ML interatomic potential |
| Umbrella Sampling | 伞形采样 | — | 自由能计算 |
| Metadynamics | 元动力学 | MetaD | 增强采样 |
| Density of States | 态密度 | DOS | |
| Bader Charge | Bader 电荷 | — | 基于零通量面的电荷分配 |

> 更全的一次性对照（约 33 条）见 [`comp-chem-paper-structure.md §7`](./comp-chem-paper-structure.md)——那是**参考表**，与主表冲突时**以主表为准**。

## 2. 待补充 / 升格候选

> 这一节是空白的，等待 AI 读论文时自动累积。**累积与升格流程（v0.4 更新）**：
>
> 1. AI 读论文遇到本表未覆盖的术语（如 `kinetic Monte Carlo`）→ 查 `comp-chem-paper-structure.md §7` 参考表
> 2. 参考表也没有 → AI 自译一个候选译名
> 3. 写入本次报告"临时术语表"（覆盖度声明前）
> 4. 下次遇到同一术语时**沿用上次译法**
> 5. **升格为本表标准译法（写入 §1）的条件**：
>    - 用户主动确认（"X 应译为 Y"）→ **1 次即可升格**（用户是权威）
>    - 化学领域**公认术语**（如 CI-NEB / PLDOS / NEB / MetaD）→ **1 次即可升格**
>    - 一般自译术语 → 在 **≥2 个不同报告**中稳定使用同一译法，且用户未反对 → AI **主动建议**升格，用户确认后写入
>    - 标有"推测，待核实"的译法 → **不升格**，直至用户核实（防幻觉固化）
>
> **用户主动贡献**：如果你认为某译法不对或要改，直接说"X 应译为 Y"，AI 会把这条映射追加到本表（你确认后）。

## 3. 与"参考表"的优先级关系（v0.4 明确）

| 优先级 | 表 | 效力 |
|---|---|---|
| **1（最高）** | **本文件 §1 主表** | AI **必须 100% 沿用**；与参考表冲突时以主表为准 |
| 2 | [`comp-chem-paper-structure.md §7`](./comp-chem-paper-structure.md) 参考速查表（约 33 条） | AI **可参考**；选定后同一报告内必须统一 |
| 3 | 本次报告"临时术语表" | 报告内统一，并作为下次同类论文的优先译法 |
| 4 | AI 自译 | 仅当前三处都没有时使用，且必须登记到临时术语表 |

## 4. 录入规范

新增条目时：
- 英文名要规范（首字母大写其余小写，缩写全大写）
- 中文名要 4-6 字内为佳
- 缩写要全大写
- 备注列：说明易混/多译情形（如"有时译'过渡态'或'中间态'，本表统一为'过渡态'"）

示例（待填）：
```
| Climbing Image Nudged Elastic Band | 爬坡图像微动弹性带 | CI-NEB | NEB 的改进方法；不要译为"上升图像" |
```
