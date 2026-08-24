# P3 — Sequence Outline / SequenceMap

> **goal**: 将每个序列填充为「事件摘要 + 场景列表」（非章纲、非节拍定稿）。
>
> schema 与字段名以 `runtime/asset-types.md` 为准，本清单只列操作步骤。

---

## 1. 契约指针

| 文档 | 锚点 |
|------|------|
| `runtime/phase-contracts.md` | **§4 P3 SequenceMap**（边界 / I/O / gate / budget / route_delta） |
| `runtime/asset-types.md` | `SequenceMap` · `Thread` · `Character` · `WorldRule` |
| `runtime/protocol.md` | 召回 → run → writeback；stale 阻断 |
| `runtime/glossary.md` | 序列 0–23；洋葱五层；status |
| `runtime/conflict-playbook.md` | 冲突裁决与 stale 传播 |

```yaml
phase_id: P3
depends_on: [P2]
next: P4
rollback_to: P2
# knowledge_budget → phase-contracts §4.4（max_blocks:16，每块片段 ≤120 行，allow 白名单）
```

---

## 2. 硬边界

**允许**

1. 序列级 `event_summary`（因果链 + 核心冲突）
2. **场景列表**：`scene_id, name, driver, goal, opposition, value_start, value_end, turn_hint`（+ 可选 `setting_hint`）
3. 伏笔 plant/payoff/hint 挂到序列或 `scene_id`（写回 `Thread`）
4. 人物本序列 reveal 意图（洋葱层标签，非定稿）
5. 世界观渐进展开点（条目级，非圣经）

**禁止**

1. 章号 / 内容块 / 潜文本逐句 / 字数章纲 → P5 `ChapterPlan`
2. 动作↔反应节拍链、四重效果精修、冲突五步定稿 → P4 `SceneBeat`
3. 跳过 `scenes[]` 只写长散文；正文；静默改 PlotSpine 节点价值

**邻阶段**：P2 = 标题+一句话价值；P3 = 事件+场景列表；P4 = 节拍+canon。

---

## 3. 输入 / 输出

| inputs | min_status | req |
|--------|------------|-----|
| `PlotSpine` | review | yes |
| `Thread` | draft/review | yes |
| `Character` | draft | yes |
| `WorldRule` | draft | yes |
| `Blueprint` | review | yes（只读） |
| `Status`/`Manifest` | draft | yes |

| outputs | target_status |
|---------|---------------|
| `SequenceMap` | review（事件 + scenes[]） |
| `Thread` | review（埋回收挂载） |
| `Character` | draft→review（reveal_plan） |
| `WorldRule` | draft→review（展开点） |
| `Status` | draft（current_phase 进展） |

---

## 4. 有序操作步骤

前置：depends_on gate 已过；inputs 无 stale；先资产后知识；未超 budget。

1. **定 scope**：`all|volume|sequence_range`（web 可 1–3 序列/轮）。
2. **装载**：PlotSpine + 相关 Thread + Character/WorldRule draft + Blueprint。
3. **按需 K（仅 ID）**：`K-STRUCT-003`…`017`；`K-CONFLICT-001/005`；`K-CHAR-002/005`；`K-WORLD-020/021`；`K-WRITE-001`；`K-CONCEPT-004/005/014`；route=web 补 `K-STRUCT-020/021`（钩子谱系/期待链的序列级布点参考）；long_serial 补 `K-STRUCT-022`（卷级 0–23 嵌套）。`on_overflow: truncate`。详见 §4.4。
4. **写 `event_summary`**：自节点 title + value_one_liner 展开；对齐 `dramatic_function` / `value_shift`。锚点 `0,6,8,12,16,18,19,22,23` 须含不可逆/转向/终局语义。
5. **拆 scenes（1–5，目标 2–5）**：时空/人物/冲突维/价值翻转任一变即拆。每场填齐 driver/goal/opposition + value 起止（必须不同）+ `turn_hint`；`scene_id = scene_v{v}_{s}_{nn}`。**停在 turn_hint，不写 beats**。
6. **冲击力自检**：序列内递增，末场最强；删后无损则删。
7. **Thread 挂载**：plant/payoff/hint → seq 或 scene_id；引线 hints 规划可见。
8. **reveal_plan + info_to_pay**：`onion_layer=surface|behavior|emotion|belief|wound`；压力与层不倒挂。info 只列「传什么」，方式留 P4/P5。
9. **越界扫描**：无章纲字段、内容块表、`beats[]`、可开写节拍链。
10. **gate → writeback**：SequenceMap/Thread ≥ review；Manifest rev；`next=P4`。

---

## 5. 产出 schema 要点

SSOT：`asset-types.md` **§2.7**（契约点名：`phase-contracts.md` §4.3）。落盘模板：[`templates/sequence-map.md`](../templates/sequence-map.md)。

```yaml
SequenceMap:   # 每卷一实例 seqmap_v{n}；模式 A 单卷视为 vol_01；最小字段见 asset-types §2.7
  volume_id: vol_{n}           # 复合序列键 {volume_id, sequence_index}，速记 v3:s12
  sequences:
    - index: 0..23             # 卷内索引
      name, event_summary, dramatic_function, value_shift: string
      scenes:                   # 1–5
        - scene_id: "scene_v{v}_{s}_{nn}"
          name, setting_hint, driver, goal, opposition
          value_start, value_end  # ≠
          turn_hint: string
      reveal_plan: [{ character_id, onion_layer }]  # surface|…|wound
      info_to_pay: [string]
  status: review
  rev: int
```

---

## 6. Gate 摘要

细则见 **`runtime/phase-contracts.md` §4.5 gate #1–#9**（本文件不重定义）。

| # | 检查项 |
|---|--------|
| 1 | scope 内每 PlotSpine 节点有 SequenceMap 条目 |
| 2 | 每序列 scenes.length ∈ [1,5] |
| 3 | 每场景 value_start ≠ value_end |
| 4 | 序列内冲击力意图递增（末场最强） |
| 5 | 必保锚点 event_summary 语义到位（**模式 B：锚点以当前卷 `seqmap_v{n}` 为准，此处即强制点**，K-STRUCT-022） |
| 6 | 无 ChapterPlan / 内容块表 |
| 7 | 引线 hints 已挂载 |
| 8 | reveal_plan 压力与洋葱层不倒挂 |
| 9 | route=web：开书/当前卷序列 scenes 完整 + 每序列爽点/信息增量意图 |

---

## 7. on_fail / next / rollback_to

```yaml
on_fail: repair_in_phase
# 节点价值 ↔ 场景列表系统性冲突 → rollback_to P2，PlotSpine 相关节点 stale
# 同一 gate 条款连续 3 次 FAIL → escalate（contracts §0.5 repair 重试上限）
next: P4
rollback_to: P2
```

局部缺场/未翻转 → repair；上游脊骨撑不住 → rollback + conflict-playbook；设定分歧 → escalate Decision。

---

## 8. route_delta

| | traditional | web |
|--|-------------|-----|
| scope | 倾向一次 0–23 | 按卷/batch 1–3 序列 |
| 密度 | 全序列 scenes→review | 连载前沿优先 review |
| 附加 | 价值翻转自检 | 每序列爽点或信息增量意图；模式 B 卷内锚点强制；gate #9 |

---

## 9. Agent 伪代码

```
run_P3(scope=all|volume|seq_range):
  require PlotSpine.status ≥ review
  load PlotSpine, Thread[], Character[], WorldRule, Blueprint
  assert no_stale(inputs)
  budget_pull(§4.4)
  for seq in scope:            # 序列引用 = {volume_id, sequence_index}
    event_summary ← expand(node.title, value_one_liner)
    scenes ← split_1..5(value_flip + turn_hint only)  # NO beats；scene_v{v}_{s}_{nn}
    attach Thread plant/payoff/hints → sequence_ref|scene_id
    reveal_plan ← onion tags; info_to_pay list only
  assert not chapter_outline(outputs) and not scene_beats(outputs)
  gate_check(§4.5) → repair | rollback P2 | escalate
  writeback SequenceMap(≥review), Thread, Character/WorldRule, Manifest
  return next=P4
```

---

> 修订注 rev2（2026-08-12）：头部加 asset-types 为准声明；字段名对齐 §2.7（dramatic_function/value_shift，driver 保留）；序列引用复合键 {volume_id, sequence_index} 与 scene_v{v}_{s}_{nn}；long_serial 补 K-STRUCT-022；gate#9 补模式 B 卷内锚点强制。
>
> 修订注 rev3（2026-08-13 修复轮）：白名单新增 route=web 组 `K-STRUCT-020/021`（contracts §4.4）；on_fail 补同一 gate 条款 3 次 FAIL→escalate。
