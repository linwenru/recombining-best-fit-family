# 组件预测的前瞻检验：实验方案（运行前定稿）

定稿时间：2026-09-11。本方案在任何新实例生成与评估运行**之前**落盘；
三个检验的预测、实例分布、配置子空间与统计协议在此固定，运行后不再
调整；结果无论是否支持预测都如实报告。

## 1. 目的与背景

BF 谱系统一复现与组件分析的全部组件级结论、组合集
3.80%、LOFO 4.67%——都是从同一批 104 个经典实例（C/BKW/NT）上归纳的。
本实验的补强目标是：**在新的实例族上，预先固定组件层面的预测，
再检验这些设计认识是否成立**（价值高于继续在原 104 例上寻找更低 gap）。
本实验即为此而做。被检验的认识选自机制分析的核心：

- TN（tallest-neighbour）放置的 buried-waste 优势（机理分析 F3）；
- 拆塔（tower removal, TR）的改善主要来自 top-waste 减少（F3 的匹配测量）；
- vertical niche（VN）在组合层的贡献（F4：单配置平均有害、枚举下有益——
  该证据全部来自原 104 例，外部有效性未知）。

## 2. 新实例生成

四组几何分布 × 两种规模 × 15 个独立实例 = 120 个实例。条带宽度 W = 1000；
旋转规则：RF 亚型，规范化 w ≥ h 后允许旋转尝试。

每件物品独立抽边长参数 s ~ U[80, 120]，然后按组规则生成 (w, h)，四舍五入
取整、最小为 1：

| 组 | 形状 | 尺寸规则 | 混合 |
|---|---|---|---|
| A | 近方集中 | w, h ~ U[0.7s, 1.3s] | 全部件按此 |
| B | 细长集中 | w ~ U[2s, 4s]，h ~ U[0.3s, 0.6s] | 全部件按此 |
| C | 近方混合 | 同 A（70%） | 30% 小件 w, h ~ U[0.15s, 0.35s] |
| D | 细长混合 | 同 B（70%） | 30% 小件同 C |

规模 n ∈ {100, 300}。随机种子：实例 (g, n, i)（g ∈ {A,B,C,D} 取 0–3，
n 取 0/1 代 100/300，i = 1..15）用 `random.Random(20260911 + g*10000 +
n_idx*100 + i)` 独立派生——单实例可复现，不依赖生成顺序。生成器与全部
120 个实例文件入库（`data/prospective/*.ins2D`，2DPackLib 格式），生成后
报告各组描述统计（平均面积、平均长宽比、LB）。

## 3. 运行矩阵与口径

- **网格臂（grid）**：width 排序 × 6 选件 × 6 放置 × TR{±} × VN{±}
  = 144 配置 × 120 实例 = 17,280 次评估。width 排序固定，与机制实验
  （stage-4 mechanisms）口径一致。
- **组合臂（portfolio）**：两个**预先固定**的等规模组合，各 12 配置：
  - **P_mix**：现有组合（`docs/stage4-portfolio.csv` 的 12 成员，含 6 个
    VN 成员，TR 全开），从 864 全因子候选池 greedy 前向选择所得；
  - **P_noVN**：禁 VN 候选池（432 = 216 基配置 × 2 TR 态，stage1-runs.csv
    + stage2-tower-runs.csv）用**同一 greedy 方法**重选 12 个。成员名单在
    评估运行前回填到本方案附录 A。
  - 组合臂共 ≤ 2 × 12 × 120 = 2,880 次评估。
- LB = max(⌈总面积/W⌉, 最高件高)，gap = (H − LB)/LB。
- 浪费分解恒等式 H×W = area + buried + top；buried/top 以 LB×W 为分母
  归一（与 stage-4 口径一致）。
- 引擎：VN 关的配置用 `cch.mechanisms.measure`（带浪费记账，支持 TR
  记账）；VN 开的配置用 `cch.solver.solve_config`。运行前自检：VN 关的
  72 配置 × 3 个抽查实例上两引擎高度逐一对齐，不一致则中止排查；另对
  每组每规模的 01 号实例全配置跑 `validate_solution` 几何校验。
- 每次运行记录 wall time（毫秒），供组合臂运行时间对比。

## 4. 三个检验（预测先行）

### P1：TN 放置降低 buried waste（方向性预测）

- 配对：网格臂 TR 关、VN 关子集内，同实例同选件规则 s（6 个）下
  (width/s/TN) 对 (width/s/LM)。
- 主终点：d_i = mean_s[ buried%(LM) − buried%(TN) ]（正值 = TN 埋洞更少）。
- 副终点：同配对的 gap 差。
- 判定：跨实例均值 95% CI 不含 0 且方向为正 → 支持。

### P2：TR 的改善主要来自 top-waste 减少（方向性预测）

- 配对：网格臂 width/fitness-number/六放置 × TR{±}（VN 关）。
- d_i(Δtop) = mean_p[ top%(TR关) − top%(TR开) ]；同理 Δburied、ΔH
  （恒等式 ΔH = Δtop + Δburied 在归一口径下成立，作 sanity check）。
- 判定：Δtop 均值 95% CI 不含 0 且为正值，且 mean(Δtop) > mean(Δburied)
  → 支持"改善主要来自顶部浪费"。

### P3：VN 成员对组合的外部贡献（**待检验的推广假设，非方向性预测**）

- d_i = best-gap(P_noVN) − best-gap(P_mix)（逐实例最优 gap 的配对差；
  负值 = 含 VN 组合更优）。
- 报告：均值 + 95% CI、胜/平/负计数、分组与总体、两组合逐实例总运行
  时间之比。
- 注意：我们自己的 F4 证据（VN 单配置平均有害、枚举下有益）预示该优势
  在新分布上**可能不成立**。若不成立，解释为"几何认识可迁移、组合优势
  有分布依赖"，与 LOFO 结果（4.67% vs FH 4.50% 未保持）呼应——这正是
  本检验要边界化的内容。

## 5. 统计协议

- 实例内对匹配配置求平均，使每实例每终点恰有一个值；跨实例（组内 n = 30，
  总体 n = 120）汇总均值、标准差、95% t 置信区间。
- 四个组分别报告 + 总体报告；组间比较为描述性，不做检验。
- 正式检验共三个（P1 主终点、P2 主终点、P3），BH 程序控制 FDR（α = 0.05）。
- 不把 144 配置当作 144 个独立样本；所有配对均在实例内完成。
- 引擎自检或几何校验失败时不进入统计环节，先排查实现。

## 6. 产出清单

- `data/prospective/*.ins2D`（120 实例，入库）；
- `docs/prospective-runs.csv`（全部逐次运行，约 2 万行，流式可续跑）；
- `docs/prospective-instances.csv`（实例描述统计）；
- `docs/prospective-summary.csv`（三检验聚合：效应量、CI、p、BH）。

## 附录 A：P_noVN 组合成员（评估运行前回填）

回填时间：2026-09-11（120 个新实例生成之后、任何评估运行之前）。
候选池 432 配置（216 基配置 × 2 TR 态，全为 vnF），实例为原 104 个
C/BKW/NT；选择方法与 P_mix 完全相同（greedy 前向选择、k = 12、平局按
配置名取小）。原 104 例上的样本内均值 4.0047%（P_mix 为 3.8044%）。
成员按加入顺序（`docs/prospective-novn-portfolio.csv`）：

| k | 成员 | 样本内均值 gap% |
|---|---|---|
| 1 | perimeter/fitness-number/SN+twT+vnF | 6.9474 |
| 2 | area/widest-fit/MaxD+twT+vnF | 5.5692 |
| 3 | area/fitness-number/LM+twT+vnF | 5.0122 |
| 4 | perimeter/first-fit/TN+twT+vnF | 4.7037 |
| 5 | perimeter/tre/MinD+twT+vnF | 4.5442 |
| 6 | perimeter/first-fit/LM+twT+vnF | 4.3952 |
| 7 | diagonal/tre/TN+twT+vnF | 4.2838 |
| 8 | perimeter/nre/TN+twT+vnF | 4.2035 |
| 9 | perimeter/nre/LM+twT+vnF | 4.1362 |
| 10 | maxside/fitness-number/LM+twT+vnF | 4.0785 |
| 11 | height/fitness-number/LM+twF+vnF | 4.0352 |
| 12 | perimeter/tre/RM+twT+vnF | 4.0047 |

注：前 3 名成员与 P_mix 相同；11 名成员 TR 开、1 名（k=11）TR 关——
TR 构成由同一选择程序在无 VN 限制下自行决定，不设额外约束。

## 附录 B：TR 锁定敏感性变体（2026-09-11 事后补充，非预注册预测）

对照候选池"也固定启用 TR，避免把 TR 的差异混进来"。主对照
（附录 A）按"同一选择程序、仅限制 VN"的口径未锁 TR；作为敏感性核对，
补充 TR 锁定变体：候选池仅 stage2-tower-runs.csv 的 216 个 twT+vnF 配置，
同一 greedy 方法重选 12 个（`docs/prospective-novn-trl-portfolio.csv`）。
结果：成员与主对照仅在 k=11 处有差——主对照的
height/fitness-number/LM+twF+vnF 被替换为其 twT 孪生（样本内曲线逐点
相同，4.0047）—— TR 混淆在本数据上实际不构成影响。
该变体为主结果之后追加的稳健性核对，不构成预注册预测。同轮另补
FH 背景基线，swap 预算口径与
cch.baselines 一致（n≤250 全交换，否则 5000 次评估）。
