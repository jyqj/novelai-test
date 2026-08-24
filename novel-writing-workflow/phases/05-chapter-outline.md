# P5 — Chapter Outline / ChapterPlan（章纲）

**goal:** 将已设计场景编排为可写的章纲：内容块、潜文本节拍、解说策略、钩子与字数。

> schema 与字段名以 `runtime/asset-types.md` 为准，本清单只列操作步骤。

---

## 1. 契约指针

| 文档 | 锚点 |
|------|------|
| `runtime/phase-contracts.md` | **§6 P5 ChapterPlan**（I/O·gate·budget·边界 SSOT） |
| `runtime/asset-types.md` | §2.9 `ChapterPlan` |
| `runtime/protocol.md` | 召回·写回·阻断 |
| `runtime/glossary.md` / `conflict-playbook.md` | 术语 / change·stale |

只列操作清单；**不重定义** gate/budget/理论。冲突以 `phase-contracts` 为准。

---

## 2. 硬边界

**允许：** 章级 `ChapterPlan`；场景→章映射；`content_blocks`；潜文本；解说策略；钩子/字数；伏笔追踪；`character_play`（对齐 Character canon）。

**禁止：** ①完整正文（P6 `ManuscriptUnit`）②静默改 Character/WorldRule canon（须 change）③以 P3 场景表/P4 节拍冒充章纲 ④无 SceneBeat 追溯的空章/散文。

---

## 3. 输入 / 输出

| 方向 | type | min/target | required |
|------|------|------------|----------|
| in | `SceneBeat` | review | yes |
| in | `Character` / `WorldRule` | canon | yes |
| in | `SequenceMap` | review | yes |
| in | `Thread` | review | no |
| in | `Status` / `Manifest` | draft+ | yes |
| out | `ChapterPlan` | **review** | yes |
| out | `Status` | draft（写作指针） | yes |

---

## 4. 有序操作步骤

> knowledge 仅按 §6.4 白名单按需拉 K-ID（先资产后知识；`max_blocks: 12`）。

1. **确认前置** — P4 gate 过；Character/WorldRule=`canon`；SceneBeat[scope]≥`review`；无 stale。
2. **划 scope** — `chapter_range` / 连载窗口 / 幕。
3. **场景→章映射** — `scene_ids`（有序，`scene_v{v}_{s}_{nn}`）；章级 value 翻转。K: `K-STRUCT-018/019`。
4. **content_blocks** — type+summary+beat_count+word_ratio；交替五类块。K: `K-WRITE-011/013`。
5. **beats_detail** — text_surface≠subtext；doing=「正在…」。K: `K-WRITE-014/015`。
6. **exposition** — must_pay 绑定 strategy；avoid table_dusting/california_scene/dump。K: `K-WRITE-001..005,007`。
7. **钩子与字数** — `hooks:{open, close}`（web `close` 必填）+ word_count_target（web 默认 **2000–4500**，Status 可覆盖）、爽点/增量入 `payoff_entries`；负面节拍/毒点降档自检（web）。K: `K-WRITE-011`, `K-STRUCT-020`, `K-WRITE-022`（web 组）；期待链自检（连续低 payoff 章）→ `K-STRUCT-021`。
8. **伏笔与人物** — foreshadow→Thread；character_play 对齐 canon。K: `K-CHAR-006`。
9. **写回** — ChapterPlan≥review；Manifest.touch；更新 Status；**不**写 ManuscriptUnit。

---

## 5. 产出 schema 要点

字段 SSOT：`asset-types` **§2.9**（契约点名 `phase-contracts` §6.3）。  
模板：`templates/chapter-plan.md`。

```yaml
ChapterPlan:   # 最小字段见 asset-types §2.9
  id: chapter_{nnnn}                # 四位全局章号
  scene_ids: [scene_v{v}_{s}_{nn}]  # 可追溯 SceneBeat
  value_start, value_end            # 必须可翻转
  word_count_target: int            # web 默认 2000–4500（Status 可覆盖）
  hooks: { open, close, close_type? }   # 术语统一；废弃 hook:{type,note}；web close 必填
  content_blocks: [{ order, type, summary, beat_count, word_ratio }]
  beats_detail: [{ block_order, text_surface, subtext, doing }]
  exposition: { must_pay, strategy, avoid }
  foreshadow: { plant, payoff }
  character_play: [{ character_id, situation, mask, key_behavior }]
  serial_notes: { payoff_entries[] }    # web 爽点/信息增量记账
```

---

## 6. Gate 摘要

细则见 **§6.5 gate #1–#8**（web 项逐章判定，无开篇特殊 gate）。

| # | 检查项标题 |
|---|------------|
| 1 | scene_ids 非空且可追溯 SceneBeat |
| 2 | 章级 value_start ≠ value_end |
| 3 | content_blocks 类型有交替意识 |
| 4 | 关键节拍均有 subtext |
| 5 | must_pay 绑定 strategy；三项错误自检 |
| 6 | **web**：`hooks.close` 非空；字数默认区间 **2000–4500**（Status 可覆盖）；爽点/信息增量（payoff_entries≥1） |
| 7 | **traditional**：不得连续三章无价值翻转 |
| 8 | character_play 与 Character canon 一致 |

> 「黄金三章」特殊 gate 已废弃（glossary §1.1）；开篇批次按上表逐章过常规 gate。

---

## 7. on_fail / next / rollback_to

| 字段 | 值 |
|------|-----|
| `on_fail` | `repair_in_phase` |
| 同一 gate 条款连续 3 次 FAIL | `escalate`（contracts §0.5 repair 重试上限） |
| `next` | `P6` |
| `rollback_to` | `P4`（场景撑不住章价值 → 修 SceneBeat，章标 stale） |

设定矛盾：`conflict-playbook` / Decision；禁止本 phase 静默改 canon。

---

## 8. route_delta

| | traditional | web |
|--|-------------|-----|
| 章长 | 灵活 | 默认 2000–4500 字 |
| 钩子 | 可选 | **强制**（hooks.close） |
| 批量 | 可按幕 | 连载窗口 + 存稿（开篇批次 = 首个普通批量） |
| 爽点/增量 | 可选 | 每章至少一处 |

---

## 9. Agent 伪代码

```
run_P5(chapter_scope):
  require Character+WorldRule canon; SceneBeat[scope]>=review; no stale
  load SequenceMap, Thread(active), Status, Manifest
  budget_pull(§6.4)                    # 先资产后知识
  map scenes → chapters (ids, value flip)
  for ch in chapter_scope:
    design content_blocks + beats_detail + exposition + hooks{open,close}
    attach foreshadow + character_play + payoff_entries(web)
  gate_check(§6.5)   # web 项逐章判定；无开篇特殊分支
  → repair_in_phase | rollback_to P4
  writeback ChapterPlan(>=review); Manifest.touch; Status pointer
  assert no full prose in outputs
  return next=P6
```

---

> 修订注 rev2（2026-08-12）：头部加 asset-types 为准声明；`hook:{type,note}` → `hooks:{open,close,close_type?}`；web 字数默认区间改 2000–4500（Status 可覆盖）；web 补 K-STRUCT-020、期待链检查 K-STRUCT-021；黄金三章废弃声明保留原样。
>
> 修订注 rev3（2026-08-13 修复轮）：route=web 白名单组追加 K-WRITE-022（毒点/负面节拍降档，contracts §6.4）；on_fail 补同一 gate 条款 3 次 FAIL→escalate。
