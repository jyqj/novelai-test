---
id: [arc_01_1]
kind: arc
status: empty
rev: 1
parent: [vol_01]
updated_at: [YYYY-MM-DDTHH:MM:SSZ]
---

## 弧目标与节奏模板

[弧目标一句话(价值从 X 到 Y)+模板 id 与参数。模板五选一:classic24|wave|dungeon|episodic|ensemble,结构评审按所选模板检查单审]

- 目标: [一句话]
- 模板: [wave] | 参数: [如:两轮升级,回落 1 章]

## 因果链

[5–10 个事件,每个一句话,标价值方向。判据:相邻事件有因果,删任一环链条即断]

- [事件一句话]（价值 [-→+]）
- [事件一句话]（价值 [+→-]）

## 章分配草案

[每章一行,生成章任务卡的原料;出场/线索op 用 id]

| ch | 一句话目标 | 出场 | 线索op | 爽点意图 |
|---|---|---|---|---|
| [ch_0001] | [一句话] | [char_slug] | [thread_slug:advance] | [dopamine] |

## 线索操作计划

[thread 埋/推/收落点;op 枚举 plant|advance|payoff|tangle。payoff_planned 命中本弧的线必须在列]

- [thread_slug] | [op] | [ch_NNNN 或章区间] | [一句话]

## 爽点与期待操作表

[对接 payoff 台账与承诺账户;kind 枚举 dopamine|upgrade|reveal|reversal|emotion|humor|other。窗口约束:3 章 ≥1 小爽,10 章 ≥1 处境级]

- [ch_NNNN] | [kind] | [意图一句话]

## 出场实体清单

[本弧出场实体 id,触发简报编译的状态卡预取。判据:每个 id 经 entities/aliases.json 可解析]

- [char_slug]
- [fac_slug]
