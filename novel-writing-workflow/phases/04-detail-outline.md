# P4 Detail Outline — 细纲 / SceneBeat + Canon

**goal**: 将 `SequenceMap` 场景列表深化为节拍级 `SceneBeat`，并把主笔 `Character` / `WorldRule` 升至 `canon`。

> schema 与字段名以 `runtime/asset-types.md` 为准，本清单只列操作步骤。

---

## 1. 契约指针（SSOT）

| 文档 | 锚点 | 用途 |
|------|------|------|
| `runtime/phase-contracts.md` | **§5 P4**（§5.1–§5.8） | I/O、gate、budget、边界、on_fail |
| 同上 | **§0.2** 硬边界表 P4 行 | 与 P3/P5 分界 |
| `runtime/asset-types.md` | `SceneBeat` / `Character` / `WorldRule` / `Thread` | 字段与 type |
| `runtime/protocol.md` | 召回·写回·status | 执行主循环 |
| `runtime/glossary.md` | 洋葱五层 / 序列 0–23 / status | 术语 SSOT |
| `runtime/conflict-playbook.md` | detect→… | 设定冲突 |

> gate / knowledge_budget / 理论 **只引用不重定义**。K 白名单见 contracts §5.4。

---

## 2. 硬边界

**允许**

1. 每场景：冲突要点、节拍链（动作↔反应）、转折鸿沟、四重效果。
2. 人物洋葱五层写全（`surface|behavior|emotion|belief|wound`）；弧光里程碑按卷落位（`arc.milestones`）。
3. 世界观消除 pending/TBD；力量/势力若有则规则+代价闭环 → `WorldRule=canon`。
4. 场景序列层节奏标注；`Thread` 埋/收对齐。
5. 可选 `scene→chapter` 建议映射，`status≤draft`，**不进 gate**。

**禁止**

1. 以「第 N 章」为主键的内容块章纲 / `ChapterPlan`（**P5**）。
2. 正文段落、逐句潜文本排版表（P5/P6）。
3. 跳过 `SequenceMap.scenes[]` 直接写章；或把 P3 场景散文当定稿节拍。
4. 静默改 `locked` 上游；冲突走 change / conflict-playbook。

---

## 3. 输入 / 输出

| direction | type | min / target status | required |
|-----------|------|---------------------|----------|
| in | `SequenceMap` | ≥ review | yes |
| in | `PlotSpine` | ≥ review | yes |
| in | `Character` | draft / review | yes |
| in | `WorldRule` | draft / review | yes |
| in | `Thread` | review（draft 仅补充） | yes（相关） |
| in | `Status` / `Manifest` | draft+ | yes |
| out | `SceneBeat` | → review | scope 内每场景 |
| out | `Character` | → **canon** | 主笔；洋葱+弧光 |
| out | `WorldRule` | → **canon** | 无 pending |
| out | `Canon`（`canon_root` / `canon_style`） | → **canon** | gate PASS 后按 auto_promote.p4_canon_seed 随升 |
| out | `Thread` | → review | plant/payoff 对齐 |
| out | `Status` | draft | phase 完成态按 protocol |

---

## 4. 有序操作（checklist）

0. **前置**：P3 gate 已过；inputs 无 `stale`；读 `Status.route` 与 scope（`all|volume|sequence_range`）。
1. **装载**：先资产（SequenceMap 场景表 + Thread/Character/WorldRule/PlotSpine），**后** budget 拉 K（§5.4）。
2. **枚举场景**：仅从 `SequenceMap.scenes[]` 取 `scene_id`（`scene_v{v}_{s}_{nn}`）；禁止无父场景的游离节拍。
3. **写 `SceneBeat`**（K-STRUCT-010~013, 018~019, K-CONFLICT-*；模板：`templates/scene-beat.md`）：
   - `value_start` ≠ `value_end`；冲突 = 场景目标 vs opposition；`sequence_ref` 复合键。
   - `beats[]` ≥2 轮 action↔reaction（可带 `value_delta`）。
   - `turn`（转折/鸿沟）非空、期望 vs 结果落差可辨；四重效果至少 3/4 有效，**每项一句依据**（非裸 bool）。
   - `character_pressure[].reveal_layer` ∈ 五层；六问逐问一句依据（K-WRITE-008 源文；contracts §5.5 #8）或 `Decision` 豁免。
4. **节奏抽检**：关键序列避免连续同类刺激回报递减（非独立 RhythmMap type）。
5. **Character 内容完备**（K-CHAR-001~010 + K-CHAR-013/014；`templates/character-sheet.md`）：洋葱五键全非空；`arc.milestones` 覆盖本卷弧光节点；`masks` / `key_choices ≥3` / `voice` 声纹卡（遮名可辨 K-CHAR-013）；主角讨喜度/记忆点自检（K-CHAR-014）。
6. **WorldRule 内容完备**（K-WORLD-*；has_power_system 细化层 K-WORLD-013~017/022~024；`templates/world-setting.md`）：去 pending/TBD；力量代价/限制可查。
7. **Thread 对齐**：`thread_ops` 回写 plant/advance/payoff。
8. **边界扫描**：outputs **无** `ChapterPlan` / 章号主键内容块 / 正文段。
9. **gate（只判内容完备）** → PASS 后按 `Status.web_serial.auto_promote.p4_canon` 升 Character/WorldRule 至 canon、按 `auto_promote.p4_canon_seed` 将 `canon_root`/`canon_style` 随升 canon + `Decision(agent_auto)` → writeback Manifest → `next=P5`。

---

## 5. 产出 schema 要点

字段 SSOT：`asset-types.md` **§2.8/§2.10/§2.11**（契约点名 contracts §5.3）。最小门禁面：

```yaml
SceneBeat:  # 最小字段见 asset-types §2.8
  id: scene_v{v}_{s}_{nn}
  sequence_ref: { volume_id, sequence_index }   # 复合键
  value_start, value_end            # ≠
  beats: [{ n, action, reaction }]  # ≥2
  turn: string                      # 转折/鸿沟（期望 vs 结果落差）
  # 四重效果（惊奇/好奇/见解/新方向）≥3/4：gate 检查项，每项一句依据（非裸 bool）
  character_pressure: [{ character_id, pressure, reveal_layer }]  # 层 ∈ surface|behavior|emotion|belief|wound
  thread_ops: [{ thread_id, op: plant|advance|payoff|tangle }]
  # 六问预检：以 K-WRITE-008 源文为唯一文本，逐问一句依据，或 Decision 豁免

Character:  # → canon；最小字段见 asset-types §2.10
  onion: { surface, behavior, emotion, belief, wound }   # 英文键；中文仅注释
  arc: { milestones: [{ volume_id, milestone }] }        # 按卷弧光（替代 seq8/12/16/19 硬编码）
  masks: [{ context, presentation }]
  key_choices: [≥3]
  voice: { tics, sentence_style, taboo_words, sample_line }

WorldRule:  # → canon；无 pending|TBD（asset-types §2.11）
  rules[] / power_system? / factions?
```

可选 draft：`scene_chapter_hint[]` — **非 gate**。canon 晋升由 gate PASS 后 auto_promote 完成（非 gate 谓词）。

---

## 6. Gate 摘要

细则见 **`runtime/phase-contracts.md` §5.5 gate #1–#9**（此处仅标题；只判**内容完备**，不判 status）：

1. scope 内每场景均有 `SceneBeat`
2. 价值翻转 + `beats`≥2
3. `turn` 非空；四重效果 ≥3/4，每项一句依据
4. 无连续同类刺激回报递减（抽检）
5. Character 内容完备：洋葱英文五键非空；masks/key_choices≥3/voice 齐
6. 弧光覆盖：`arc.milestones` 覆盖本卷成长节点
7. WorldRule 内容完备：无 pending/TBD；力量有代价限制
8. 六问逐问一句依据（K-WRITE-008）或 Decision 豁免
9. **web**：正面价值释放节奏；升级节点挂场景

> gate PASS 后按 `auto_promote.p4_canon` 自动晋升 Character/WorldRule → canon，按 `auto_promote.p4_canon_seed`（web 默认 true）将 `canon_root`/`canon_style` 随升 canon，写 `Decision(approved_by=agent_auto)`；`auto_promote=false` 或触及 `Canon.invariants` → escalate。

---

## 7. on_fail / next / rollback_to

```yaml
on_fail: repair_in_phase          # contracts §5.6
# 价值与 SequenceMap 系统性偏离 → SceneBeat(+父 scene) stale；可 rollback_to P3
# 人物/世界自相矛盾 → escalate Decision | conflict-playbook
# 同一 gate 条款连续 3 次 FAIL → escalate（contracts §0.5 repair 重试上限）
next: P5
rollback_to: P3
depends_on: [P3]
```

---

## 8. route_delta

| | traditional | web |
|--|-------------|-----|
| 定稿范围 | 全书角色/世界一次 canon | 开书卷必须 canon；远期可 draft |
| 节拍粒度 | scope 全场景优先 review | 连载窗口优先 |
| 节奏 | 文学张弛 | gate#9 爽点/升级挂钩场景 |
| 分批 | 可全书 | `volume|sequence_range` 分批过 gate |

---

## 9. Agent 伪代码

```
run_P4(scope):
  require SequenceMap ≥ review and no stale(inputs)
  load SequenceMap, PlotSpine, Character[], WorldRule[], Thread[]  # assets first
  budget_pull(§5.4)                                               # K-IDs only
  for scene in scenes_in(scope):
    sb = design_SceneBeat(scene)   # beats≥2, turn, four_effects(附依据), pressure/reveal
    six_questions(sb, K-WRITE-008) or Decision.exempt
    writeback sb status≥review
  fill Character onion/milestones/masks/voice; WorldRule 去 TBD
  align Thread plant/payoff
  assert no ChapterPlan / chapter-keyed blocks in outputs
  gate_check(§5.5 #1..#9)          # 只判内容完备
  if PASS: auto_promote(Character, WorldRule → canon; p4_canon_seed: canon_root/canon_style → canon)
           + Decision(agent_auto)
  writeback Manifest, Status
  return next=P5 | on_fail
```

---

*操作清单 only · 契约 SSOT=`runtime/phase-contracts.md` §5 · 通用工程层*

> 修订注 rev2（2026-08-12）：头部加 asset-types 为准声明；four_effects/六问改 evidence 化表述（引 contracts §5.5 新 gate）；洋葱英文键；arc.milestones 替代 seq8/12/16/19 硬编码；gate 改「内容完备」、canon 晋升移至 gate PASS 后 auto_promote；力量体系细化层 K-WORLD-013~017/022~024。
>
> 修订注 rev3（2026-08-13 修复轮）：char_canonize 白名单追加 K-CHAR-013/014（声纹遮名/主角讨喜度，contracts §5.4 max_blocks 18→20）；晋升条款加 p4_canon_seed（canon_root/canon_style 随升 canon，outputs 同步补行）；on_fail 补 3 次 FAIL→escalate。
