# 计算化学论文结构参考

本文件供 AI 在生成深度阅读报告时查阅，用于：
- 判断论文采用的计算方法与同类方法优劣（要点 2）；
- 提取与补全复现流程所需参数（要点 9）；
- 识别创新点与局限性（要点 5、6）。

---

## 1. 计算化学常见软件与关键词

| 软件 | 类型 | 常见关键词 |
| --- | --- | --- |
| Gaussian (G09/G16) | 分子量子化学 | DFT, TD-DFT, 基组, PCM/SMD 溶剂化, 频率分析, 过渡态, IRC |
| ORCA | 分子量子化学 | DFT, 多参考 CASSCF/NEVPT2, 光谱性质, DLPNO-CCSD(T) |
| NWChem | 大规模并行量子化学 | DFT, 耦合簇, 平面波 |
| Q-Chem / Psi4 / PySCF | 量子化学 | DFT, 多体微扰, 激发态 |
| VASP | 周期性 DFT | 平面波, PAW 赝势, k 点, 能带, DOS, NEB, AIMD |
| CP2K | 大体系 DFT / AIMD | 高斯-平面波混合基, AIMD, MetaDynamics |
| Quantum ESPRESSO | 周期性 DFT | 平面波, 赝势, 声子 |
| LAMMPS | 分子动力学 | 力场 MD, 系综, 粗粒化 |
| GROMACS / AMBER | 生物分子 MD | 力场, 溶剂化盒子, 周期性边界条件 |
| ASE | Python 原子模拟环境 | 结构构建、计算流程编排 |
| MOPAC / xTB | 半经验 | GFN-xTB, 大体系快速估算 |

## 2. 论文标准结构

计算化学论文通常遵循 IMRaD 变体结构：

1. **标题/作者/单位**（Title/Authors/Affiliations）
2. **摘要**（Abstract）：背景 → 方法 → 关键结果（定量）→ 结论/意义
3. **关键词**（Keywords）
4. **引言**（Introduction）：研究背景、动机、文献综述、研究空白、本文贡献
5. **计算方法**（Computational Methods / Computational Details）：
   软件与版本、理论级别、基组/赝势、k 点、收敛阈值、溶剂化、色散校正、MD 参数
6. **结果与讨论**（Results and Discussion）：结果呈现、图表、对比、机理解释
7. **结论**（Conclusion）：总结、意义、展望
8. **支撑信息**（Supporting Information / 附录）

## 3. 方法章节复现细节要求（要点 9 必备字段）

复现工作流必须覆盖以下参数；论文未给出的要标注"原文未明确给出"：

**电子结构计算**
- 软件名称与版本号（如 VASP 6.3.2、Gaussian 16 Rev. C.01）
- 泛函（PBE, B3LYP, M06-2X, HSE06, r2SCAN…）与色散校正（DFT-D3(BJ), D4）
- 基组（6-311+G(d,p), def2-TZVP, cc-pVTZ…）或赝势（PAW, ultrasoft, ECP）
- 平面波截断能（如 520 eV）与 k 点网格（如 3×3×1 Monkhorst-Pack）
- SCF 收敛阈值、几何优化收敛判据（能量/力/位移）
- 溶剂化模型（PCM, SMD, COSMO, 隐式/显式）
- 对称性、自旋态、磁性处理

**分子动力学/蒙特卡洛**
- 系综（NVT/NPT/NVE）、温度、压力
- 温度热浴：
  - Nosé-Hoover（确定性，NVT 主流）
  - Nosé-Hoover chain（长链改进，NPT 常用）
  - Langevin（随机性，耗散大；适合构型采样）
  - Bussi-Donadio-Parrinello / CSVR（Velocity-rescale，温和热浴，平衡阶段友好）
  - Berendsen（弱耦合，仅适合平衡，不严格采样）
  - Andersen（随机碰撞，NVT）
- 压力控制（barostat）：
  - Berendsen（弱耦合，仅适合平衡）
  - Parrinello-Rahman（严格采样，可变胞）
  - Martyna-Tuckerman-Tobias / MTTK（与 Nosé-Hoover chain 配合）
  - Monte Carlo 体积涨落（NPT-MC）
- 积分步长（通常 0.5-2 fs）、模拟时长（平衡 + 生产）、平衡时间
- 周期性边界条件、盒子尺寸、截断半径、长程静电处理（PME / PPPM / Ewald）
- 力场/参数化来源（GAFF, OPLS-AA, CHARMM, AMBER, TraPPE, 自定义参数、DeePMD-kit 等 ML 势）

**性质与后处理**
- 过渡态搜索（NEB, CI-NEB, TS 优化 + 频率验证 + IRC）
- 频率分析（热力学修正：零点能、焓、自由能）
- 能量分解（EDA, ALMO-EDA, SAPT）
- 电子结构分析（Mulliken/Hirshfeld 电荷, 态密度, 能带, 前线轨道）
- 谱学性质（IR, Raman, UV-Vis, NMR, XPS 模拟）

**数据来源**
- 初始结构来源（实验晶体 CCDC、Materials Project、NIST、文献结构、建模工具构建）
- 数据库/数据集版本与筛选条件

## 4. 结构化摘要要求

高质量计算化学论文的摘要通常回答四个问题（可用于要点 1/3 快速定位）：

1. **问题**：研究的是什么体系/现象/问题？
2. **方法**：用了什么计算级别与软件？
3. **结果**：最关键的定量结果是什么（能量/能垒/趋势）？
4. **结论/意义**：对领域有何启示？

## 5. 图表与定量证据（要点 4 参考）

- **能量学**：相对能量、反应能垒、结合能、吸附能、溶剂化自由能（单位 kcal/mol 或 kJ/mol，注意换算 1 kcal/mol ≈ 4.184 kJ/mol）
- **结构**：键长/键角/二面角（Å、°）、晶格常数
- **电子结构**：带隙（eV）、HOMO-LUMO 能隙、电荷转移量（e）
- **统计**：误差棒、均方根偏差、收敛测试、系综平均
- **对比**：与实验值/其他方法/文献值的对比表

## 6. 评估要点（要点 5/6 参考）

**创新点常见类型**：
- 新方法/新算法（改进精度或效率）
- 新体系/新材料（首次计算某类体系）
- 新机理（提出新的反应路径或电子结构解释）
- 新性质（预测未报道的性质）
- 新应用/新数据集（方法迁移到新领域）

**局限性常见来源**：
- 理论级别近似（如纯泛函缺色散、单参考方法不适合强关联体系）
- 基组/赝势/截断能不够收敛
- 体系规模小、时间尺度短（MD 采样不足）
- 缺少实验验证或误差分析
- 泛函误差对特定性质（如带隙、过渡金属）的系统偏差

## 7. 术语中英对照速查（供报告注释使用）

> **v0.3 起**：下面这张表是"参考速查"（AI 可参考但不强求 100% 沿用），
> **标准译名表**（AI 必须 100% 沿用）见 [`term-glossary.md`](./term-glossary.md)。
> 累积机制：AI 读论文时遇到新术语 → 自译 + 登记到本报告"临时术语表"；用户主动修正 → 追加到 `term-glossary.md`。

| 英文 | 中文 |
| --- | --- |
| Density Functional Theory (DFT) | 密度泛函理论 |
| ab initio Molecular Dynamics (AIMD) | 从头算分子动力学 |
| Projector Augmented Wave (PAW) | 投影缀加平面波 |
| Plane Wave | 平面波 |
| Basis Set | 基组 |
| Pseudopotential | 赝势 |
| k-point mesh | k 点网格 |
| Cutoff Energy | 截断能 |
| Dispersion Correction | 色散校正 |
| Solvation Model | 溶剂化模型 |
| Transition State (TS) | 过渡态 |
| Nudged Elastic Band (NEB) | 爬坡弹性带方法 |
| Ensemble (NVT/NPT/NVE) | 系综（恒定粒子数-体积-温度 / 粒子数-压力-温度 / 粒子数-体积-能量） |
| Periodic Boundary Condition (PBC) | 周期性边界条件 |
| Convergence Criterion | 收敛判据 |
| Harmonic Frequency | 简谐频率 |
| Zero-Point Energy (ZPE) | 零点能 |
| Thermostat | 温度热浴/控温器 |
| Barostat | 压力控制/控压器 |
| Particle Mesh Ewald (PME) | 粒子网格 Ewald 方法（长程静电） |
| Climbing Image NEB (CI-NEB) | 爬坡图像 NEB（精确过渡态定位） |
| Intrinsic Reaction Coordinate (IRC) | 内禀反应坐标 |
| Density of States (DOS) | 态密度 |
| Projected DOS (PDOS) | 投影态密度 |
| Bader Charge | Bader 电荷（基于零通量面的电荷分配） |
| Highest Occupied Molecular Orbital (HOMO) | 最高已占分子轨道 |
| Lowest Unoccupied Molecular Orbital (LUMO) | 最低未占分子轨道 |
| Adsorption Energy | 吸附能 |
| Binding Energy | 结合能 |
| Reaction Barrier / Activation Energy | 反应能垒 / 活化能 |
| Potential Energy Surface (PES) | 势能面 |
| Self-Consistent Field (SCF) | 自洽场 |
| Machine Learning Potential (MLP) | 机器学习势函数 |

---

## 8. 论文类型与结构差异

### 8.1 原创研究（article）

典型 IMRaD 变体结构（见第 2 节），核心特征：

- 有明确的"计算方法/实验方法"章节
- 有"结果与讨论"或独立的 Results / Discussion
- 围绕"一个或几个具体问题"展开
- 图表对应具体数据/结构
- 报告重点：问题→方法→结果→意义

### 8.2 综述（review / perspective / minireview）

典型结构：

- **背景与动机**：为什么需要这篇综述
- **分类视角**：按方法/时间/体系/应用等维度切分
- **子方向详述**：每个子方向 1-2 节，给代表性工作与进展
- **对比与讨论**：横向比较不同方法/子方向的优劣
- **挑战与展望**：未解决问题、未来方向
- 通常**无独立的"方法/结果"章节**（这是判定信号）
- 图表多以"概念图/对比表/统计图"为主，少有具体定量数据
- 引用量通常远高于 article（100+）

### 8.3 混合性文章（research article + review 成分）

少数文章会先综述再报告原创工作（如一些 Accounts of Chemical Research、Chemical Reviews 中的 perspective 类）。
判定信号：abstract 同时含 "we review" + "we propose" / "here we"。

### 8.4 `paper_type` 枚举与识别信号（v0.4）

脚本 `detect_paper_type()` 输出以下 7 类，全部为**启发式**，用户可覆盖（SKILL.md §2）：

| `paper_type` | 识别信号（正则要点） | 报告分支 |
|---|---|---|
| `account` | `in this account` / `our journey` / `lessons learned` / Accounts 期刊 | 综述变体（要点 2 改"课题组方法演进"） |
| `perspective` | `perspective` / `viewpoint` / `our view` / `outlook` | 综述变体（要点 1 改"作者立场"） |
| `editorial` | `editorial` / `this issue of` | 速览模式 |
| `review` | `this review` / `recent advances in` / `progress in` / `综述` / `minireview`；或 method+result 双空 | 综述变体（5 模块 8 要点） |
| `letter` | `in this communication` / `we report herein` / `rapid communication` | 7 模块但精简（1500-2500 字） |
| `article` | 默认（有方法章 + 结果章） | 7 模块 10 要点 |
| `unknown` | 无文本 / 结构异常 | 按 article 处理并注明 |

> 注意：`perspective` / `account` **不再被并入 review**（v0.3 及以前的盲区），因为它们有独特的"作者立场"与"课题组演进"维度。
> 期刊层面的先验也有用：`Acc. Chem. Res.` 多为 account；`Chem. Soc. Rev.` / `Chem. Rev.` 多为 review；`J. Phys. Chem. Lett.` 多为 letter。

---

## 9. Supporting Information（SI / 支撑信息）的常见位置与获取

### 9.1 SI 章节在正文章节中的位置模式

| 期刊 | 常见 SI 位置 | 特点 |
| --- | --- | --- |
| JACS / J. Am. Chem. Soc. | 正文末尾单独 PDF | 通常有详细参数表、收敛测试、补充图 |
| Angew. Chem. | 正文末尾单独 PDF / SI PDF | 同上 |
| Nature 系列 | 独立 Supplementary Information 文件 | 含 Extended Data Figures / Tables |
| Phys. Rev. / PRB | 末尾或独立 Supplemental Material | 公式、收敛测试 |
| ACS Catalysis | SI PDF | 详尽方法学、收敛表 |
| J. Chem. Phys. | 末尾 Supplementary Material | 公式推导、参数 |
| 计算化学专门期刊（JCTC / JCP） | 末尾 SI | 几乎所有细节都在 SI |

### 9.2 复现时 SI 缺失的处理

- **优先**：访问期刊页面下载 SI（多数需机构订阅）
- **备选**：联系作者（邮箱通常在论文首页）
- **退而求其次**：基于正文参数 + 合理默认值估算，**必须在报告中标注"SI 缺失，仅依据正文"**
- **AI 行为**：不要凭空编造 SI 中的参数；标注"原文未明确给出，可能在 SI 中"

### 9.3 复现计算时常见的"在 SI 不在正文"参数

- 收敛测试曲线（截断能、k 点、SCF 阈值）
- 完整力场参数表（特别是自定义/混合力场）
- 过渡态频率验证图（IRC 路径、能量曲线）
- 势能面扫描数据
- NEB 中间图像的能量-反应坐标曲线
- MD 平衡曲线（RMSD、能量、温度）
- 电荷/电子结构分析的完整数据表

> 当 SI 不可获取时，AI 应**主动声明**"以上复现流程基于正文 + 合理假设；如需精确复现请获取 SI"。

---

## 10. 软件 / 数据库许可证清单（要点 9 用 · v0.4 补全）

> 原清单只列 5 商业 + 7 免费 + 3 Python 包，覆盖不全；此处按"许可类型"分组给全，**要点 9 直接照此分组输出**。

### 10.1 商业软件（需购买许可证 / 机构订阅）

| 软件 | 类型 | 授权提示 |
|---|---|---|
| VASP | 周期性 DFT | 需购买 license（学术/商业分档）；无授权可用 QE / CP2K 替代部分功能 |
| Gaussian | 分子量子化学 | 商业许可；替代：ORCA / Psi4 |
| Materials Studio | 材料建模 + DFT/MD | 商业套件 |
| AMBER（商业版） | 生物分子 MD | 商业许可；学术可申请 AmberTools 免费部分 |
| CASTEP | 周期性 DFT | 商业（部分版随 Materials Studio 提供） |
| Q-Chem | 量子化学 | 商业许可 |
| TURBOMOLE | 量子化学 | 商业发行版（学术授权亦有） |

### 10.2 免费 / 开源电子结构

| 软件 | 协议 / 获取 | 备注 |
|---|---|---|
| ORCA | 学术免费注册 | 分子体系强 |
| Quantum ESPRESSO | GPL | 平面波 DFT |
| CP2K | GPL | 大体系 DFT / AIMD |
| NWChem | ECL-2.0 | 大规模并行 |
| Psi4 | LGPL | 高精度量子化学 |
| PySCF | Apache-2.0 | Python 原生 |
| SIESTA | GPL | 数值原子轨道 |
| CPMD | 开源（注册） | Car-Parrinello MD |
| WIEN2k | 商业发行 / 学术注册 | 全电子 LAPW |
| GPAW | GPL | 投影缀加波 |
| ABINIT | GPL | 平面波 DFT |

### 10.3 免费 / 开源 MD 与材料

| 软件 | 协议 | 备注 |
|---|---|---|
| LAMMPS | GPL | 力场 MD，可扩展 |
| GROMACS | LGPL | 生物分子 MD |
| OpenMM | MIT / LGPL | Python 友好 |
| GULP | 学术免费 | 离子/材料 |
| DeePMD-kit | LGPL-3.0 | 机器学习势训练/推理 |

### 10.4 Python 包

```bash
pip install ase pymatgen spglib rdkit-pypi MDAnalysis
# 或
conda install -c conda-forge ase pymatgen spglib rdkit mdanalysis
```

### 10.5 专有数据库 / 数据集（许可独立，必须单独注明）

| 数据源 | 获取方式 | 再分发限制 |
|---|---|---|
| CCDC / CSD | 机构订阅 | **不可再分发**原始结构 |
| ICSD | 订阅 | 不可再分发 |
| Materials Project | 开放 API（需注册 key） | CC-BY 4.0，需署名 |
| NIST WebBook / JANAF | 公开网页 | 引用需注明 NIST |
| AFLOW | 开放 | 引用需注明 |
| OQMD | 开放 | 引用需注明 |

> 输出规则：要点 9 按 10.1-10.5 五组**仅列出论文实际用到的**软件/数据；未用到的不要堆砌。原文未给版本 → 写"原文未明确给出软件版本，建议联系作者确认"。
