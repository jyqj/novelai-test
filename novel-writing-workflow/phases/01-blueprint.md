# P1 — Blueprint（蓝图）

**goal**: 将灵感收敛为可传播、可探索、可类型定位的故事蓝图，作为全链路唯一起点契约。

> schema 与字段名以 `runtime/asset-types.md` 为准，本清单只列操作步骤。

> **前置**：若 `project_state=NONE` / `intent=new_project`，先完成 [`runtime/project-scaffold.md`](../runtime/project-scaffold.md)（Scaffold Gate PASS 后本清单才充实 Blueprint 内容）；Scaffold PASS ≠ 本 phase content gate PASS。

---

## 1. 契约指针（SSOT）

| 文档 | 用途 |
|------|------|
| [`runtime/phase-contracts.md`](../runtime/phase-contracts.md) **§2 P1 Blueprint** | depends_on / I/O / gate / budget / on_fail / route_delta |
| [`runtime/asset-types.md`](../runtime/asset-types.md) **§2.5 Blueprint** | 类型字段与职责（schema SSOT） |
| [`runtime/protocol.md`](../runtime/protocol.md) | `intent → mode → load_policy → run → writeback` |
| [`runtime/project-scaffold.md`](../runtime/project-scaffold.md) | `new_project` 强制脚手架（本 phase 前置） |
| [`runtime/glossary.md`](../runtime/glossary.md) | 术语 SSOT（本文件不重定义） |
| [`templates/blueprint.md`](../templates/blueprint.md) | 落盘模板 |

`knowledge_budget`：contracts **§2.3**（`max_blocks: 12`，每块片段 ≤120 行，白名单以 contracts §2.3 `core ∪ situational` 为准；`on_overflow: truncate`，溢出组记 `session_report.knowledge_deferred` 下轮优先补拉）。先资产后知识。

---

## 2. 硬边界

**允许**: 高概念/前提/主控方向/类型惯例；高概念元素（六类+tier）；角色概念；世界种子；开中结**走向**；更新 `Status`、`Manifest`（创建属 scaffold）。

**禁止**: 序列表（0–23）、场景/节拍/对话、章纲/内容块/字数/正文；不得把「填充序列」当本阶段产出（P2+）。

对齐 contracts **§0.2** P1 行。

---

## 3. 输入 / 产出

| 方向 | type | min / target status | required |
|------|------|---------------------|----------|
| in | Intent / 用户素材 | — | yes |
| in | `Status` | draft | yes（由 scaffold 创建） |
| in | `Decision` / `Manifest` | — / — | no |
| in | `Canon`（`canon_root` / `canon_style`） | draft | yes（scaffold 必建种子，本 phase 充实对象） |
| out | `Blueprint` | ≥ `review` | yes |
| out | `Canon`（`canon_root` seed 充实） | ≥ `review` | yes（gate PASS 时自检晋升，draft→review 无需授权） |
| out | `Canon`（`canon_style` 确认） | ≥ `review` | yes（同上；保留 LLM 腔黑名单） |
| out | `Status` | draft（`current_phase=P1`；`route` 属 Status，Blueprint 不含） | yes |
| out | `Manifest` | draft（注册 Blueprint） | yes |

---

## 4. 有序操作步骤

每步仅动作 + 可选 K-ID；理论不展开。总拉取 ≤ 12 块。

1. **装载** — Intent/素材；load `Status`/`Manifest`（scaffold 已建）/`Decision`（若有）/`Canon` 种子（`canon_root`/`canon_style`，scaffold 必建）；确认 `Status.route`（`traditional`|`web`，默认 traditional）。
2. **整理灵感** — 核心想法 vs 碎片；禁区/偏好。禁止序列/场景。
3. **高概念** — 给出 **3 个候选卖点**（各附一句吸引力论证），选定 1 个为 `high_concept`（≤2 句，陈述句卖点）。`K-CONCEPT-001`…
4. **前提** — `premise`「如果…会怎样」开放问句；与 high_concept 区分（传播 vs 探索）。`K-CONCEPT-006`…
5. **主控方向** — `ending_mode_tendency`：`idealist|pessimist|positive_irony|negative_irony`（≠unset）；`controlling_idea_draft` 草案。
6. **类型** — `genre.primary` + secondary；`must_keep_conventions` ≥3；`cliches_to_avoid`。网文 `K-CONCEPT-019/020`（route=web 组，含 021/022）。
7. **元素** — `element_seeds` ≥3，覆盖 ≥3 类：`identity|relation|event|conflict|emotion|growth`；`tier: bronze|silver|gold|ssr`（四档）。
8. **角色概念** — `spine_intent.protagonist_desire / opposing_force / core_conflict_one_liner`；`cast_seeds[{role, label, function}]`（key supports ≤3）；含 protagonist 且 Character 未建 → 讨喜度/代入感预检 `K-CHAR-014`（protagonist_design）。
9. **世界种子** — `world_seeds` 四维 `era|duration|place|conflict_scale`（≥3/4）；`core_rules_draft` ≥1 条独特性种子。可选 `K-WORLD-003|004`。
10. **走向** — `plot_vector.opening / midpoint_direction / ending_direction` 各一句；故事三角定位为方法参考（`K-STRUCT-001`）。**禁止** 0–23/场景。
11. **web 附加** — 开篇钩子意图；可升级/爽点空间；细分类型惯例；题材红线自查（`K-CONCEPT-021`）；开书包装建议（书名候选/简介草案，`K-CONCEPT-022`，模板可选节）。
12. **canon 种子充实** — `canon_root` seed 按 Blueprint 充实（主控方向/不变量种子，无占位符）；`canon_style` 确认（保留 LLM 腔黑名单）；gate PASS 时二者自检晋升 ≥review（draft→review 无需授权）。
13. **gate → writeback** — 对齐 `templates/blueprint.md`；`Blueprint.status≥review` + `Canon` 种子 ≥review；更新 Manifest + Status。

---

## 5. 产出 schema 要点

字段 SSOT：**asset-types §2.5**（契约点名见 contracts §2.2）。落盘：[`templates/blueprint.md`](../templates/blueprint.md)。

```yaml
Blueprint:   # 最小字段见 asset-types §2.5；此处仅列名
  high_concept, premise, controlling_idea_draft, ending_mode_tendency
  genre: { primary, secondary[], web_serial_tags[], must_keep_conventions[], cliches_to_avoid[] }
  element_seeds: [{ category, text, tier }]   # tier 四档 bronze|silver|gold|ssr
  spine_intent: { protagonist_desire, opposing_force, core_conflict_one_liner }
  cast_seeds: [{ role, label, function }]
  world_seeds: { era, duration, place, conflict_scale, core_rules_draft[] }
  plot_vector: { opening, midpoint_direction, ending_direction }  # 仅走向
  # route 属 Status，Blueprint 不含 route 字段
```

---

## 6. Gate 摘要

全部 `must`。细则：**见 `runtime/phase-contracts.md` §2.4 gate #1–#11**（#11 = route=web 题材红线自查，对照 K-CONCEPT-021 六域清单，结论记入 gate 记录）。

| # | 检查项标题 |
|---|------------|
| 1 | **卖点证据制**：3 候选卖点 + 各一句吸引力论证，选定 1 个（≤2 句） |
| 2 | premise 与 high_concept 已区分（问句 vs 陈述句） |
| 3 | genre.primary + must_keep_conventions ≥3 |
| 4 | spine_intent.protagonist_desire + opposing_force 非空 |
| 5 | world_seeds 四维 ≥3/4；core_rules_draft ≥1 条独特性种子 |
| 6 | plot_vector 开/中/结三向各一句 |
| 7 | element_seeds ≥3 且 ≥3 类；tier 四档合法 |
| 8 | ending_mode_tendency ≠ unset；controlling_idea_draft 已有草案 |
| 9 | **web**：开篇钩子意图 / 爽点空间 / 细分惯例（web_serial_tags） |
| 10 | **canon 种子自检**：canon_root 已按 Blueprint 充实（无占位符）+ canon_style 已确认（LLM 腔黑名单保留）；PASS 时自检晋升 ≥review |

未过 → 不得 ADVANCE 到 P2。

---

## 7. on_fail / next / rollback

| 字段 | 值 |
|------|-----|
| `on_fail` | `repair_in_phase`（contracts §2.5） |
| 用户否定根本方向 | `escalate` → `Decision` |
| 同一 gate 条款连续 3 次 FAIL | `escalate`（contracts §0.5 repair 重试上限） |
| `next` | `P2` |
| `rollback_to` | `null` |

---

## 8. route_delta（traditional vs web）

| | traditional | web |
|--|-------------|-----|
| 类型 | 文学/类型片惯例 | 网文细分 + 读者期待清单 |
| 钩子 | 可选 | **必须**标「开篇钩子」意图 |
| 元素 | tier 可选 | 建议 ≥1 `gold`/`ssr` 长线 |

见 contracts **§2.6**。

---

## 9. Agent 伪代码

```
run_P1(intent):
  load Status, Manifest (scaffold 已建), Decision if any, Canon(canon_root/canon_style 种子)
  route = Status.route || traditional
  # assets first; budget_pull(§2.3, max_blocks=12)
  draft 3 candidate high_concepts + 论证 → pick 1
  draft Blueprint from intent   # no sequences/scenes/chapters
  if route == web: annotate hook_intent + power_curve_space
  enrich canon_root seed + confirm canon_style   # gate PASS 自检晋升 ≥review
  self_check(gate §2.4 #1..#11)
  if fail:
    repair_in_phase               # 同一条款连续 3 次 FAIL → escalate（contracts §0.5）
    if user rejects core direction: escalate → Decision
  writeback Blueprint(≥review), Canon(canon_root/canon_style ≥review), Status(current_phase=P1), Manifest
  return next=P2
```

---

*操作清单；冲突以 `runtime/phase-contracts.md` §2 为准。*

> 修订注 rev2（2026-08-12）：字段名对齐 asset-types §2.5（element_seeds/spine_intent/cast_seeds/world_seeds/plot_vector；route 属 Status）；tier 四档；gate#1 改 3 候选卖点证据制；产出统一 ≥review；Status 由 scaffold 创建。
>
> 修订注 rev3（2026-08-13 修复轮）：I/O 补 canon_root/canon_style 种子（in draft → out ≥review，gate PASS 自检晋升）+ gate#10 + 操作步骤 12；max_blocks 10→12；白名单表述改「以 contracts §2.3 core∪situational 为准」；web 组扩为 K-CONCEPT-019..022 + protagonist_design→K-CHAR-014；on_fail 补 3 次 FAIL→escalate。；第三波收尾（V1 复检修正：冷启动条件行/六件套允许集/小节指针/编号/口径对齐）
