# Thread 模板 — 伏笔 / 引线 / 支线状态机

> **本模板实例化** `runtime/asset-types.md` §2.12 `type: Thread`。门禁 / 阶段 I/O 以 `runtime/phase-contracts.md` 为准；召回/回写见 `runtime/protocol.md`。  
> **唯一伏笔账本声明**：本 type 是全库唯一的悬线账本——`ChapterPlan.thread_ids/payoff_entries[].thread_ids`、`SceneBeat.thread_ops` 一律只写 `thread_id`(+op) 引用；`ManuscriptUnit` 只留 `thread_ids_touched[]` 触线引用，P6 正文落地直接回写本资产。  
> 别名归一：`ThreadMap` / `ForeshadowLedger` → 多个 Thread 实例，禁止注册独立 type。  
> `[方括号]` 占位。通用工程层，禁止绑定具体作品；知识仅引用 `K-xxx`。

---

## 1. YAML（信封 + 最小字段；唯一真值）

```yaml
---
# ── 通用信封 ──
id: thread_[slug]
type: Thread
rev: 1
status: draft                     # draft|review|canon|locked|stale|archived
title: "[人读短标签：本线功能一句话]"
created_at: "[YYYY-MM-DDTHH:MM:SSZ]"
updated_at: "[YYYY-MM-DDTHH:MM:SSZ]"
depends_on:
  - { type: PlotSpine, id: plotspine_main, min_rev: 1 }
  # - { type: SequenceMap, id: seqmap_v[n], min_rev: 1 }
stale_reason: null
tags: []
uri: null
phase_home: P2                    # 登记起点；推进贯穿 P2–P6

# ── 最小字段 ──
kind: fuse                        # fuse|subplot|relationship|mystery|promise|other
statement: "[本线一句话：埋什么 / 承诺什么 / 支线欲望对抗是什么]"
state: planted                    # planted|active|tangled|payoff_ready|paid_off|dropped

volume_scope: []                  # 本线活跃卷，如 [vol_01, vol_02]；召回集 = active ∩ 当前卷 scope（或 waypoint 命中本卷）
waypoints: []                     # 跨卷弧路标
# waypoints:
#   - { volume_id: vol_02, intent: "[本卷该线要到达的位置一句话]" }

plant_at:                         # 首次埋设（P2 骨架可全 null，P3+ 至少一项可寻址）
  sequence_ref: null              # { volume_id, sequence_index } 复合键 | null
  scene_id: null                  # scene_v{v}_{s}_{nn}
  chapter_id: null                # chapter_{nnnn}

advance_log: []                   # 轮转账本：只保留最近 10 条；每条 { at, note }
# advance_log:
#   - { at: "chapter_0012", note: "[如何推进：加压 / 假线索 / 半揭示 / 关系位移]" }
history_digest: null              # 历史摘要：每卷一行；卷末 volume_checkpoint 时把本卷溢出条目归并成该卷一行

payoff:
  planned_at: null                # 计划兑现位：{ volume_id, sequence_index } 复合键 | null
  actual_at: null                 # 实际落地锚点（chapter_{nnnn} 或 scene id）；未兑现 null
  description: null               # 兑现后读者得到什么真相/结果/关系落点

owner_character_ids: []           # 只引用 Character id，不在此改角色 canon
must_not_drop: false              # 默认 false；仅主线/核心承诺线设 true（禁默删，砍线须 Decision(approved_by=user)）

# ── kind=fuse 扩展（K-CONCEPT-011；hidden_info + 埋点规划 ≥3）──
hidden_info: null                 # 对读者或角色隐藏的真相一句话；非 fuse 填 null
plant_points: []                  # ≥3；复合速记，如 ["v1:s2", "v1:s6", "v1:s12"]
reveal_point: null                # 计划揭示锚点；可与 payoff.planned_at 对齐

# ── kind=subplot 扩展（不替代 PlotSpine.cable）──
budget_ratio: null                # 0.0–1.0 相对主线篇幅意图；支线合计建议 ≤ 0.30
sync_with_main: null              # 如何向心搅合主线；禁止树形喧宾
---
```

## 2. 填写指引

### 2.1 枚举与状态机

- `kind`：`fuse` 引线 / `subplot` 支线 / `relationship` 关系线 / `mystery` 谜团 / `promise` 读者承诺 / `other`（须在 statement 写清功能）。
- `state` 迁移：`planted → active → tangled → payoff_ready → paid_off`；任意态可 `dropped`（仅 `must_not_drop=false` 或 Decision）。部分兑现保持 `active` 并在 advance_log 记 partial。
- op 枚举（下游引用统一拼写）：`plant | advance | payoff | tangle`。

### 2.2 账本纪律

- **advance_log 轮转**：每次可见推进追加一条，只保留最近 10 条；`history_digest` **每卷一行**——卷末 volume_checkpoint 时把本卷溢出条目归并成该卷一行。
- **召回**：`state ∈ {paid_off, dropped}` 的线移出 active 召回集；跨卷线按 `volume_scope` / `waypoints` 决定何时回到召回窗（召回表以 protocol §4.2 为准）。
- **写回**：每次推进 `rev += 1` + touch `manifest_root`；P6 正文实际埋/推/收后**直接回写本账本**（ManuscriptUnit 不设 thread 记账字段）。
- `must_not_drop=true` 拟 dropped → 阻断，走 conflict-playbook + `Decision(approved_by=user)`。
- 同一 `hidden_info` 禁止在 PlotSpine.fuses 与本实例双源真值冲突（冲突走 Decision）。

## 3. 正文区

frontmatter 为唯一真值；本节以下为自由撰写区（缠绕说明 / 待决问题），不作机器对账输入。

---

## 修订

| rev | 变更 |
|----:|------|
| 1 | 初版（裸 int 埋点；op 枚举含空格拼写；无限增长 advance_log） |
| 2 | 2026-08-12 重构落地：新增 volume_scope[] 与 waypoints[{volume_id,intent}]；plant_at / payoff.planned_at 改复合键；advance_log 轮转（最近 10 条 + digest 一行历史摘要）；op 枚举修字 payoff；加「唯一伏笔账本」声明；paid_off/dropped 移出 active 召回集；删正文镜像表 |
| 3 | 2026-08-13 修复轮：must_not_drop 默认改 false（仅主线/核心承诺线设 true）；advance_log 轮转改「最近 10 条 + history_digest 每卷一行（卷末 checkpoint 归并）」 |

*template_of: Thread | phase_home: P2–P6 | schema_rev: 对齐 asset-types（schema_rev 3） | 通用工程层 · 不绑定具体作品*
