# P2 — Rough Outline / PlotSpine（粗纲）

> **goal**: 建立全故事节点脊骨（`PlotSpine`）：每节点仅「标题 + 一句话价值」，并挂接电缆/引线/支线/冲突骨架与人物·世界初稿。**禁止场景级。**
>
> schema 与字段名以 `runtime/asset-types.md` 为准，本清单只列操作步骤。

---

## 1. 契约指针（SSOT，本文件不重定义）

| 文档 | 锚点 |
|------|------|
| `runtime/phase-contracts.md` | **§3 P2 Rough/PlotSpine**；§0.2 硬边界；§1.1 必保锚点 |
| `runtime/asset-types.md` | §2.6 `PlotSpine`；§2.12 `Thread`；Character / WorldRule |
| `runtime/protocol.md` | `intent → mode → load_policy → run → writeback` |
| `runtime/glossary.md` / `conflict-playbook.md` | 术语 SSOT；分歧流程 |

知识仅 `K-xxx`；白名单/预算见 contracts **§3.4**，不得据此展开场景。

---

## 2. 硬边界（§0.2 / §3.1）

**允许**：节点 `0–23` 的 `title` + `value_one_liner`（可选 `function`/`anchor`）；电缆/引线/支线/冲突**骨架**（节点级）；`Character`/`WorldRule` **draft**；可选 `volume_map`。

**禁止**：

1. **任何场景级**（列表、场内冲突、节拍、对话、场次拆分）
2. 章号/字数/钩子句式/内容块/章纲
3. 「50–500 字事件散文」含多场景过程 → 压回 title + value_one_liner
4. `SceneBeat` / `ChapterPlan` / `ManuscriptUnit`（P4–P6）
5. 静默改 Blueprint canon（须 change）

---

## 3. 输入 / 输出

| inputs | min_status | req | outputs | target_status |
|--------|------------|-----|---------|---------------|
| `Blueprint` | review | yes | `PlotSpine` | review |
| `Status` | draft | yes | `Thread`[] | draft→review |
| `Manifest` | draft | yes | `Character` | draft |
| `Decision` | — | no | `WorldRule` | draft |
| | | | `Status` | draft（`current_phase=P2`） |

---

## 4. 有序操作步骤

> 先资产后知识；超 budget → truncate（§3.4）。

- [ ] **0. 启动** — `Blueprint.status ∈ {review,canon,locked}`；无 stale；读 `Status.route`
- [ ] **1. 装载+预算** — load Blueprint/Status/Manifest/Decision；按需 pull §3.4 白名单（`K-STRUCT-*` 功能标签、`K-CONCEPT-009..016` 电缆/引线、`K-CONFLICT-*`、`K-CHAR-001,003,004`；route=web 补 `K-WRITE-022/023` 毒点预防与融梗边界骨架自查；群像补 `K-CHAR-011/012`；long_serial 补 `K-STRUCT-022`；`has_power_system` 仅拉骨架层 `K-WORLD-005/011/012`，细化层留 P4）。**禁**用知识写场景
- [ ] **2. 锚点占位** — `0` hook · `6` shock1 · `8` growth1 · `12` `[midpoint, growth2]`（数组锚点）· `16` growth3 · `18` shock2 · `19` growth4 · `22` climax · `23` resolution（词表 §1.1 / glossary §4.2）
- [ ] **3. 填满 24 节点** — 每条仅 `title` + `value_one_liner`（价值方向可辨）；可选 `function`；禁字段：`scenes/beats/chapters/dialogue`
- [ ] **4. 电缆** — `cable.mainline` 或主线 `Thread`；可选 strands + `budget_ratio`（`K-CONCEPT-010`；多主线搭配 `K-CONCEPT-009`）
- [ ] **5. 引线** — `hidden_info` + plant/hint **≥3** + `reveal_point`（节点级）；`fuses` 和/或 `Thread.kind=fuse`（`K-CONCEPT-011`）
- [ ] **6. 支线** — 每条 planned payoff 节点；总意图 **≤30%** 主线（`K-CONCEPT-012`）
- [ ] **7. 冲突骨架** — 内心/人际/外部 → 幕或关键节点（`conflict_matrix`）；不写场次过程（`K-CONFLICT-001..003`）
- [ ] **8. 主控思想草稿** — `controlling_idea_draft` =「价值+原因」（`K-CONCEPT-013`；说教风险自检 `K-CONCEPT-016`）
- [ ] **9. Character/WorldRule draft** — 扩 Blueprint `cast_seeds`/`world_seeds`；洋葱 id：`surface|behavior|emotion|belief|wound`。模板：`templates/character-sheet.md`、`templates/world-setting.md`
- [ ] **10. route=web** — `volume_map` 至少首卷 `node_range`；节点 0–2 价值句强调钩子/信息增量（仍禁场景）
- [ ] **11. 扫描+gate+写回** — 无场景表/节拍/「场景1」；过 gate #1–#10 → writeback + Manifest.rev

---

## 5. 产出 schema 要点

- 类型 SSOT：`runtime/asset-types.md` **§2.6**；契约摘要：phase-contracts **§3.3**
- 模板指针：`templates/plot-spine.md`
- 实例建议路径：`design/plot_spine.md`
- 节点唯一形状：`{ id: 0..23, title, value_one_liner, function?, anchor? }` ×24（`anchor` 允许数组，如节点 12 `[midpoint, growth2]`）
- 旁路：`cable` / `fuses` / `Thread[]`（`plant_at` 复合键）/ `conflict_matrix?` / `volume_map?` / `controlling_idea_draft`
- **模式 B 注记**：书级 24 节点为规划资产——书级锚点 soft（缺失仅 warning 不 BLOCK），卷内锚点在 P3 卷级 gate 强制；远端节点可占位到卷级主题一句话
- **禁止**注册 `ThreadMap` 为独立 type（→ `Thread`）

---

## 6. Gate 摘要

细节：**`runtime/phase-contracts.md` §3.5 gate #1–#10**（本处仅标题）

| # | 标题 |
|---|------|
| 1 | `nodes.length==24` 且 id 覆盖 `0..23` |
| 2 | 每 node 仅 title + value_one_liner（无 scenes） |
| 3 | 必保锚点 `0,6,8,12,16,18,19,22,23`（web 模式 B：书级缺失仅 warning，卷内锚点 P3 强制） |
| 4 | 每节点价值方向可辨 |
| 5 | 主线电缆非空；引线 hidden_info + plant/hint≥3 |
| 6 | 支线均有 planned payoff；总意图≤30% |
| 7 | `controlling_idea_draft` = 价值+原因 |
| 8 | Character/WorldRule ≥draft 且与 Blueprint 不矛盾 |
| 9 | 无场景级内容扫描通过 |
| 10 | **web**：volume_map 首卷 + 开篇 0–2 钩子/增量 |

---

## 7. on_fail / next / rollback_to

```yaml
on_fail: repair_in_phase          # §3.6；锚点不可支撑 → rollback + Blueprint stale 候选
# 同一 gate 条款连续 3 次 FAIL → escalate（contracts §0.5 repair 重试上限）
next: P3
rollback_to: P1
```

---

## 8. route_delta

| | traditional | web |
|--|-------------|-----|
| 粒度 | 可一次 0–23 过 gate | 可先 0–12 review，其余 draft；**开书 scope 须全过** |
| 分卷 | 可选 | **建议** `volume_map`；模式 B 书级锚点 soft（见 §5 注记） |
| 文风 | 文学价值句 | 可注爽点/升级意图（**仍禁场景**） |
| 开篇 | Hook 占位 | 0–2 强化钩子与信息增量一句话 |

---

## 9. Agent 伪代码

```
run_P2(scope=all|volume):
  require Blueprint.status ∈ {review, canon, locked}
  load Blueprint, Status, Manifest          # 先资产
  budget_pull(§3.4)                         # 后知识；overflow=truncate
  build PlotSpine.nodes[0..23]              # title + value_one_liner ONLY
  place anchors {0,6,8,12,16,18,19,22,23}   # 12 = [midpoint, growth2]；web 模式 B 书级缺失→warning
  build cable + fuses + Thread[]            # 电缆/引线/支线
  draft conflict_matrix @ node level        # 非场景
  draft controlling_idea_draft              # 价值+原因
  draft Character[], WorldRule[]
  if route==web: volume_map + nodes[0..2] hook intent
  assert no_scene_level(outputs)
  gate_check(§3.5 #1..#10)
  if fail → repair_in_phase | rollback_to P1
  writeback PlotSpine(≥review), Thread, Character, WorldRule, Status
  return next=P3
```

---

*操作清单 · SSOT=`runtime/phase-contracts.md` §3 · 通用工程层*

> 修订注 rev2（2026-08-12）：头部加 asset-types 为准声明；anchor 数组语义（节点 12）；模式 B 书级锚点 soft 注记；K 白名单更新（群像 K-CHAR-011/012、long_serial K-STRUCT-022、力量体系仅骨架层）。
>
> 修订注 rev3（2026-08-13 修复轮）：白名单新增 route=web 组 `K-WRITE-022/023`（毒点预防/融梗边界，对应 contracts §3.4 max_blocks 14→16）；on_fail 补同一 gate 条款 3 次 FAIL→escalate。
