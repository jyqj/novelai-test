# stage:vol — 卷庭 配套知识包

| 键 | 值 |
|---|---|
| 阶段 | vol：卷 N+1 蓝图九节（court.md §1 卷庭行 + §2 卷庭行） |
| 进入 | 上卷 checkpoint 完成（serial-ops.md §4；**checkpoint 未完成不开卷庭**）→ `court open vol_NN` |
| 退出 | vol_NN/volume.md 九节 committed + dec 落盘 |
| 下一阶段 | arc（新卷首弧规划） |
| 本包读者 | 编排者（装配 R0 设计简报时） |

## 必读（装配本场必带）

- `protocol/court.md` §2 卷庭行 + §3 回合协议
- 上卷 exports + 卷报告 `state/reports/vol_NN.md`（三态对账后版本）+ imports 预填
- `tree/book.md` / `tree/world.md`（书级约束）+ 主线电缆当前位置
- 所选 `rhythm/` 模板（卷内弧划分；模板所有权=s4，本场沿用 S4 所选）
- `rubrics/power.md`（卷级增幅预算，所有权=s2）、`rubrics/redline.md`（所有权=s1）、
  `rubrics/payoff.md`（卷爽点大节奏，所有权=write）

## 选读池（庭审附件 K 池，6 块；本场 ≤4 块、只取锚点段）

| K-ID | 名称 | 何时挑 |
|---|---|---|
| K-STRUCT-012 | 回报递减定理 | 跨卷升级预算 |
| K-STRUCT-015 | 高潮设计 | 卷高潮设计 |
| K-STRUCT-016 | 结局设计 | 卷末/全书收束 |
| K-STRUCT-019 | 幕节奏公式 | 节拍间隔参数（卷蓝图级） |
| K-STRUCT-022 | 卷级0–23嵌套法 | rhythm/classic24 卷内套用（本场自有的序列变体块） |
| K-CHAR-011 | 配角生命周期状态机 | 阵容变化节（群像运营） |

## 禁读

- knowledge/ 池外任何块；往期 transcript
- 全书级序列总论/详解块（所有权=s4）——卷内嵌套用本场自有的「卷级0–23嵌套法」，
  不回读 S4 池
- 上卷各章正文（卷庭以 exports/报告/摘要为准，不重读正文）

## 锚点读法

K-ID → `knowledge-blocks.md` 锚点取段（L1/L2 优先）；附件进设计简报，不进章简报。
