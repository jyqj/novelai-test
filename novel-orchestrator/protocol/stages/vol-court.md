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
- 所选 `rhythm/` 模板（卷内弧划分）
- `rubrics/power.md`（卷级增幅预算）、`rubrics/redline.md`、`rubrics/payoff.md`（卷爽点大节奏）

## 选读池（庭审附件 K 池，11 块；本场 ≤4 块、只取锚点段）

| K-ID | 名称 | 何时挑 |
|---|---|---|
| K-STRUCT-003 | 23序列法总论 | 卷内 0–23 嵌套骨架 |
| K-STRUCT-004 | 序列0–6详解 | 卷首铺排 |
| K-STRUCT-005 | 序列7–12详解 | 卷中段布局 |
| K-STRUCT-006 | 序列13–18详解 | 卷后段布局 |
| K-STRUCT-007 | 序列19–23详解 | 卷高潮与收束 |
| K-STRUCT-012 | 回报递减定理 | 跨卷升级预算 |
| K-STRUCT-015 | 高潮设计 | 卷高潮设计 |
| K-STRUCT-016 | 结局设计 | 卷末/全书收束 |
| K-STRUCT-019 | 幕节奏公式 | 节拍间隔参数 |
| K-STRUCT-022 | 卷级0–23嵌套法 | rhythm/classic24 卷内套用 |
| K-CHAR-011 | 配角生命周期状态机 | 阵容变化节（群像运营） |

## 禁读

- knowledge/ 池外任何块；`knowledge-index.md`；往期 transcript
- 上卷各章正文（卷庭以 exports/报告/摘要为准，不重读正文）

## 锚点读法

K-ID → `knowledge-blocks.md` 锚点取段（L1/L2 优先）；附件进设计简报，不进章简报。
