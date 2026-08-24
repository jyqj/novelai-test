# Phase Contracts — 六阶段契约

> Agent 可执行协议。阶段是契约链，不是散文顺序。  
> 知识库只读：仅引用 `K-xxx` ID，不复制理论正文。  
> 术语 SSOT 见 `runtime/glossary.md`；**schema/字段名 SSOT 见 `runtime/asset-types.md`**（本文件对各类型只点名 gate 相关字段，不再内嵌完整 schema）；状态机/回写见 `runtime/protocol.md`。  
> 资产 `status` 统一：`draft | review | canon | locked | stale | archived`。  
> 序列编号：卷内 `0–23`（含序列 0 Hook）；跨卷引用一律复合键 `{volume_id, sequence_index}`（速记 `v3:s12`）。  
> 洋葱五层键：`surface / behavior / emotion / belief / wound`（表象/行为/情感/信念/创伤；中文仅注释）。

---

## 0. 契约元模型

每个 phase 必须声明以下字段（缺一不可）：

| 字段 | 类型 | 含义 |
|------|------|------|
| `phase_id` | enum | `P1`…`P6` |
| `name` | string | 阶段名 |
| `goal` | string | 本阶段唯一目标（一句话） |
| `depends_on` | phase_id[] | 前置阶段（其关键 outputs 须达 gate 通过态） |
| `inputs` | AssetRef[] | 必装载资产类型 + 最低 status |
| `outputs` | AssetSpec[] | 产出类型 + 目标 status + gate 相关字段点名 |
| `knowledge_budget` | object | 允许拉取的 K-ID 与块数预算 |
| `gate` | GateRule[] | 全部通过才可进入 next |
| `on_fail` | FailAction | gate 失败时动作 |
| `next` | phase_id \| null | 默认下一阶段 |
| `rollback_to` | phase_id \| null | 结构性失败时回退目标 |

### 0.1 双轨 route

| route | 说明 |
|-------|------|
| `traditional` | 传统长篇：全链路锁级更严，可整书推进后再正文 |
| `web` | 网文连载：允许按卷/按章分批过 gate；强制章末钩子与开篇钩子意图 |

未声明时默认 `traditional`。字段差异写在各 phase 的 `route_delta`。

### 0.2 职责硬边界（防重叠）

| phase | 允许 | 禁止 |
|-------|------|------|
| **P1** | 高概念/类型/前提/主控方向/角色概念/世界种子/走向 | 序列表、场景、章纲、正文 |
| **P2** | **节点标题 + 一句话价值**；电缆/引线/支线/冲突**骨架**；人物·世界**初稿** | **任何场景级**描述、节拍、对话、章分割 |
| **P3** | 序列**事件**填充 + **场景列表**（名/目标/价值起止） | 章纲、内容块、潜文本精修、正文 |
| **P4** | **场景节拍** + 人物/世界**定稿**（canon） | 按章内容块编排、正文成稿 |
| **P5** | **章纲**（内容块/潜文本/解说/钩子/字数） | 完整正文段落 |
| **P6** | **正文** | 擅自改 canon 设定（须走 change 流程） |

### 0.3 status 推进约定

```
draft → review → canon → locked
         ↘ stale（上游变更）→ 修复后回 review/canon
archived = 废弃不再参与执行
```

- `gate` 通过：本阶段主产出至少 `review`；跨阶段依赖资产建议 `canon`。`canon` = 已采纳/已过 gate 的**存稿**（未发布）。
- `locked` = **已发布**（publish 快径默认即晋升 locked；「已发布」判定全库唯一 = `status == locked`）或显式冻结快照（P4 圣经快照等）；**不参与 stale 传播**——上游变更触及 locked 资产改写 `retcon_note`（见 §8.2 与 conflict-playbook）。
- 上游变更为 `stale` 的下游资产：阻断对应 phase，直到 conflict/sync 完成（见 `conflict-playbook`；按 intent 的 stale 豁免见 protocol §4.4）。

### 0.4 knowledge_budget 语义

```yaml
knowledge_budget:
  max_blocks: <int>          # 本 phase 单次 run 最多拉取块数（唯一预算维度）
  core: [K-xxx, ...]         # 进入本 phase 默认必拉；列表顺序 = 优先级
  situational:               # 条件触发；满足 when 才拉，未触发不占预算
    - when: <触发标签，闭集见 §0.4.1>
      pull: [K-xxx, ...]
  deny: [K-xxx, ...]         # 可选黑名单
  on_overflow: truncate|block # 超预算：先截断 situational 低优先，core 最后动
```

- **计量**：预算只按**块数**计；单块单次装载片段 **≤120 行**（超出按块内小节裁剪）。无 token 上限维度；L1–L4 是阅读策略提示（见 glossary），不作预算计量。
- **白名单 = `core ∪ situational[*].pull`**；`fetch_knowledge` 的 `allowed_k_ids` 断言以该并集为准。
- **优先级**：core 按序 > 已触发的 situational 按声明序；`on_overflow: truncate` 从队尾截。
- **溢出补拉**：situational 因溢出被截断的组记入 `session_report.knowledge_deferred`；同 phase 下一轮 run 优先补拉（排在 core 之后、新触发之前）。
- **解析与定位**：K-ID → 源文件位置一律查 `knowledge-blocks.md`（检索协议 + `<!-- K-ID -->` 锚点），任何 intent 可只读查询；`knowledge-index.md` 仍仅 diagnose/learn（C6）。

#### 0.4.1 触发标签闭集（situational.when）

`when` **只能取本表标签**（自由短语禁止）；判定条件绑定资产字段或用户输入特征，可机械勾选。

**通用标签**

| 标签 | 判定 | 主用 |
|------|------|------|
| `route=web` | `Status.route == web` | P1–P6 |
| `has_power_system` | Blueprint/WorldRule 含力量·技能·修炼体系（`world_power` 域存在或 `world_seeds` 点名） | P2 骨架 / P4 细化 |
| `has_faction_play` | `WorldRule.factions` ≥3，或 Blueprint 声明阵营博弈 | P2–P4 |
| `element_driven` | `Blueprint.element_seeds` 非空且以元素法组织大纲 | P2/P3 |
| `theme_debate` | `Canon.theme.counter_idea` 非空，或本轮需思想/反思想布局 | P2/P3 |
| `preach_risk` | 自检或用户反馈存在说教倾向（Critique 记录 / 用户点名） | P2/P4 |
| `long_serial` | 预计 >100 章或 ≥3 卷（`volume_map` / `Status.web_serial`） | P2/P3 |
| `ensemble_cast` | 主要视角/主笔角色 ≥4（`cast_seeds` 或 Character 实例数） | P2 |
| `scope∩act_N` | 本轮 scope 与幕区间相交（act_1=0–6 / act_2a=7–12 / act_2b=13–18 / act_3=19–23；卷内索引） | P3 |
| `unit_type=X` | 目标单元内容特征 ∈ `{dialogue, description, action, interior, exposition}`（按 `ChapterPlan.content_blocks` 主导类型判定；无 content_blocks 时按 protocol §4.2 语义特征表判定） | P6 |
| `user_named` | 用户当轮点名的 K-ID（始终允许，占预算） | 全部 |

**阶段专属标签**

| 标签 | 判定 | phase |
|------|------|-------|
| `fragmented_inspiration` | 灵感碎片 ≥5 条且尚无 `element_seeds` | P1 |
| `premise_gap` | `premise` 为空，或与 `high_concept` 未区分（同句/互为改写） | P1 |
| `ending_undecided` | `ending_mode_tendency == unset` | P1 |
| `genre_blend` | `genre.secondary` 非空 | P1 |
| `fantasy_seed` | `world_seeds` 含超自然/异世界要素 | P1 |
| `protagonist_design` | `cast_seeds` 含 protagonist 且对应 Character 未建 | P1 |
| `antagonist_design` | `cast_seeds` 含 antagonist 而无对应 Character(draft)，或对抗骨架待建 | P2 |
| `conflict_ladder` | `conflict_matrix` 有层为空，或冲突递进未映射到节点 | P2 |
| `char_skeleton` | `cast_seeds` 有条目而 Character(draft) 未建/待扩 | P2 |
| `world_frame` | `world_seeds` 有条目而 WorldRule(draft) 未建/待扩 | P2 |
| `node_function_detail` | 存在 `nodes[].function` 为空的节点 | P2 |
| `scene_split_detail` | 有序列 `scenes` <2，或无法定位拆分维度（时空/人物/冲突/价值） | P3 |
| `conflict_depth_low` | 有序列 `conflict_layers` 仅一层非空 | P3 |
| `reveal_planning` | 本轮序列涉及主笔角色而 `reveal_plan` 未填 | P3 |
| `info_seeding` | 本轮有 `info_to_pay` 待分配条目 | P3 |
| `rhythm_tuning` | 预检发现连续 ≥3 场同类刺激（回报递减风险） | P4 |
| `char_canonize` | 主笔 Character 内容未完备（洋葱键空 / `arc.milestones` 缺本卷） | P4 |
| `world_canonize` | 触及的 WorldRule 含 `pending/TBD` | P4 |
| `crowd_reaction` | 单场出场角色 ≥4 | P4 |
| `conflict_layer_check` | 连续多场 `conflict` 停留同一层面 | P4 |
| `card_workflow` | scope 场景数 >20，或用户要求卡片工作法 | P4 |
| `exposition_binding` | 本章 `exposition.must_pay` 非空 | P5 |
| `backstory_flashback` | `content_blocks` 含闪回/幕后故事块（block `summary` 标注可辨） | P5 |
| `surprise_coincidence` | 本章设计依赖巧合或惊奇转折 | P5 |
| `imagery_system` | `canon_style`/Blueprint 声明形象系统母题 | P5 |
| `char_chapter_play` | `character_play` 含 mask 切换 | P5 |
| `expectation_chain` | `serial_notes.payoff_entries` 含 promise/兑现项，或连续 3 章无兑现 | P5 |
| `chapter_rhythm` | 本章 `scene_ids` ≥2 或 `content_blocks` ≥3（章内微结构需求） | P6 |
| `critic_round` | 命中 `Status.flags.critic_cadence`（默认每 5 章 + 卷末，见 §7.9） | P6 |
| `style_polish` | 文字级修订/打磨轮（用户点名或 revise 流程） | P6 |

原则：**先资产后知识**；预算用尽不得继续灌方法论文。

### 0.5 FailAction 枚举

| on_fail | 行为 |
|---------|------|
| `block` | 停止推进，列出未过 gate 项 |
| `repair_in_phase` | 留在本 phase 修 outputs |
| `rollback` | 回 `rollback_to`，标记相关资产 `stale` |
| `escalate` | 写入 Decision 待用户裁决 |

- **repair 重试上限**：同一 phase 的同一 gate 条款连续 **3** 次 FAIL → 停止 `repair_in_phase`，转 `escalate`（产出 Decision 草案 + BLOCK 等待 user）。

---

## 1. 全局阶段图

```
P1 Blueprint
    │ outputs: Blueprint (review+) + Canon 种子（canon_root/canon_style ≥review）
    ▼
P2 RoughOutline / PlotSpine
    │ outputs: PlotSpine + Thread[] + Character(draft) + WorldRule(draft)
    │ ※ 节点 = 标题 + 一句话价值；无场景
    ▼
P3 SequenceOutline / SequenceMap
    │ outputs: SequenceMap (事件+场景列表)
    │ ※ 非章纲
    ▼
P4 DetailOutline / SceneBeat + Canon lock
    │ outputs: SceneBeat[] + Character(canon) + WorldRule(canon)
    ▼
P5 ChapterOutline / ChapterPlan
    │ outputs: ChapterPlan[]
    ▼
P6 Writing / ManuscriptUnit
    │ outputs: ManuscriptUnit (chapter)  # 别名 ProseUnit 禁止注册为独立 type
    ▼
  (loop P5/P6 per unit；结构性问题 rollback)
```

### 1.1 必保结构锚点（P2 即须占位；正式词表）

锚点闭集（`PlotSpine.nodes[].anchor`，允许数组；序位映射 SSOT：glossary §4.2）：
`hook | shock1 | growth1 | midpoint | growth2 | shock2 | growth3 | growth4 | climax | resolution`

| 锚点 id | 序列 | 说明 |
|---------|------|------|
| `hook` | 0 | 开篇钩子 |
| `shock1` | 6 | 惊人意外#1（第一幕高潮，不可逆） |
| `growth1`–`growth4` | 8 / 12 / 16 / 19 | 成长步骤（弧光节点） |
| `midpoint` | 12 | 中间点（与 growth2 同位，允许 `anchor: [midpoint, growth2]`） |
| `shock2` | 18 | 惊人意外#2（第二幕高潮） |
| `climax` | 22 | 最终高潮（价值不可逆终局；21–22「白热化带」仅描述性用语） |
| `resolution` | 23 | 收束（余波） |

模式 B（route=web 分卷）：书级锚点降为 soft，卷内锚点在卷级 gate 强制（见 §3.5 #3、§4.5 #5）。

---

## 2. P1 — Blueprint（蓝图）

```yaml
phase_id: P1
name: blueprint
goal: 将灵感收敛为可传播、可探索、可类型定位的故事蓝图，作为全链路唯一起点契约。
depends_on: []
next: P2
rollback_to: null
```

### 2.1 inputs

| type | min_status | required | 说明 |
|------|------------|----------|------|
| `Intent` / 用户素材 | — | yes | 灵感、偏好、禁区、route 选择 |
| `Status` | draft | yes | 项目状态机（由 project-scaffold 创建；route 已写入） |
| `Decision` | — | no | 既有裁决 |
| `Manifest` | — | no | 资产注册表（scaffold 创建 `manifest_root`） |
| `Canon`（`canon_root` / `canon_style`） | draft | yes | scaffold 必建种子（本 phase 充实对象） |

### 2.2 outputs

| type | target_status | 说明 |
|------|---------------|------|
| `Blueprint` | ≥ review | 最小字段见 asset-types §2.5 |
| `Canon`（`canon_root`） | ≥ review | seed 按 Blueprint 充实（主控方向/不变量种子非占位）；gate PASS 时自检晋升（draft→review 无需授权） |
| `Canon`（`canon_style`） | ≥ review | scaffold 预置文风卡确认/项目化（保留 LLM 腔黑名单）；同上自检晋升 |
| `Status` | — | `current_phase=P1`（`route` 属 Status，scaffold 写入） |
| `Manifest` | — | `manifest_root` 注册 Blueprint |

**Blueprint gate 相关字段点名**（schema SSOT：asset-types §2.5；模板 `templates/blueprint.md`）：

- `high_concept` / `premise`（传播卖点 vs 探索设问，二者必须可区分）
- `genre.primary` + `must_keep_conventions[]` + `cliches_to_avoid[]`
- `element_seeds[].tier ∈ bronze|silver|gold|ssr`（四档）
- `spine_intent`（protagonist_desire / opposing_force / core_conflict_one_liner）
- `cast_seeds[]`；`world_seeds`（era/duration/place/conflict_scale + core_rules_draft）
- `plot_vector`（opening / midpoint_direction / ending_direction；仅走向，非序列）
- `controlling_idea_draft` + `ending_mode_tendency`

### 2.3 knowledge_budget

```yaml
knowledge_budget:
  max_blocks: 12
  core:                        # 每次进 P1 必拉（按序即优先级）
    - K-CONCEPT-001   # 高概念提问法
    - K-CONCEPT-008   # 前提 vs 高概念（区分传播/探索）
    - K-CONCEPT-017   # 类型常规提炼
    - K-CONCEPT-013   # 主控思想公式（方向草案）
    - K-STRUCT-001    # 故事三角定位
  situational:
    - when: fragmented_inspiration
      pull: [K-CONCEPT-002, K-CONCEPT-003, K-CONCEPT-006]
    - when: premise_gap
      pull: [K-CONCEPT-007]
    - when: ending_undecided
      pull: [K-CONCEPT-015]
    - when: genre_blend
      pull: [K-CONCEPT-018]
    - when: route=web            # 网文定位 + 开篇三道门 + 题材红线 + 开书包装
      pull: [K-CONCEPT-019, K-CONCEPT-020, K-CONCEPT-021, K-CONCEPT-022]
    - when: protagonist_design
      pull: [K-CHAR-014]
    - when: fantasy_seed
      pull: [K-WORLD-003, K-WORLD-004]
  on_overflow: truncate
```

### 2.4 gate

全部为 `must`：

1. `high_concept` 证据制：给出 **≥3 个候选卖点**，各附**一句吸引力论证**（类型信号/新奇度/目标读者），选定其一为 `high_concept`（≤2 句）。
2. `premise` 与 `high_concept` 已区分（开放设问「如果…会怎样」 vs 第三人称陈述句卖点）。
3. `genre.primary` + ≥3 条 `must_keep_conventions`。
4. `spine_intent.protagonist_desire` 明确；`opposing_force` 非空。
5. `world_seeds` 四维（era/duration/place/conflict_scale）至少 3/4，且含一句可指认的独特性种子。
6. `plot_vector` 开/中/结均有一句话。
7. `element_seeds` ≥3 且覆盖 ≥3 个类别；`tier` 四档合法。
8. `controlling_idea_draft` 非空；`ending_mode_tendency` 已选（≠unset）。
9. **route=web 附加**：开篇钩子意图明确；存在可升级/爽点空间标注；细分类型惯例已列。
10. **canon 种子自检**：`canon_root` 已按 Blueprint 充实（主控方向/不变量种子无占位符）；`canon_style` 已确认（LLM 腔黑名单保留）；gate PASS 时两者自检晋升 ≥ review（draft→review 属自检晋升，无需授权）。
11. **route=web 附加·题材红线自查**：对照 K-CONCEPT-021 六域判定清单逐域答「否」（或已按处置列改造后重答），结论一行记入 gate 记录/evidence（内容安全属底线项，不与 #9 包装项混判；traditional 轨为建议级自查）。

### 2.5 on_fail

```yaml
on_fail: repair_in_phase
# 仅当用户否定高概念根本方向时 escalate → Decision
# 同一 gate 条款连续 3 次 FAIL → escalate（§0.5 repair 重试上限）
```

### 2.6 route_delta

| | traditional | web |
|--|-------------|-----|
| 类型 | 文学/类型片惯例 | 网文细分类型 + 读者期待清单 |
| 钩子 | 可选 | **必须**在 Blueprint 标注「开篇钩子」意图 |
| 元素等级 | 可选 | 建议至少 1 个 gold/ssr 承载长线 |

### 2.7 agent 伪代码

```
run_P1(intent):
  load Status, Manifest if any, Canon(canon_root/canon_style 种子)
  budget_pull(knowledge_budget)
  draft Blueprint from intent
  enrich canon_root seed + confirm canon_style   # gate PASS 自检晋升 ≥review
  self_check(gate)
  if fail → repair_in_phase / escalate
  writeback Blueprint(status≥review), Canon(canon_root/canon_style ≥review), Status.current_phase=P1_done
  return next=P2
```

---

## 3. P2 — Rough Outline / PlotSpine（粗纲）

```yaml
phase_id: P2
name: rough_outline
goal: 建立全故事节点脊骨（PlotSpine）：每节点仅「标题 + 一句话价值」，并挂接电缆/引线/支线/冲突骨架与人物·世界初稿。禁止场景级。
depends_on: [P1]
next: P3
rollback_to: P1
```

### 3.1 边界（强制）

**允许：**

- 序列 `0–23` 每个节点：`title` + `value_one_liner`（价值变化方向一句话）
- 可选：`function`（建置/递进/转折/高潮/收束等标签）
- 电缆主线、引线时间表（锚点级）、支线表（类型/收束/比例）、冲突三层面**分配到节点级**
- Character / WorldRule **draft**

**禁止：**

- 场景列表、场景内冲突、节拍、对话、地点场次拆分
- 章号/字数/钩子句式
- 「50–500 字事件散文」若含多场景过程 → 压缩回一句话价值 + 节点标题

### 3.2 inputs

| type | min_status | required |
|------|------------|----------|
| `Blueprint` | review | yes |
| `Status` | draft | yes |
| `Decision` | — | no |
| `Manifest` | draft | yes |

### 3.3 outputs

| type | target_status | 说明 |
|------|---------------|------|
| `PlotSpine` | review | 24 节点；必保锚点齐（模式 B 书级 soft）；最小字段见 asset-types §2.6 |
| `Thread` | draft→review | 主线/引线/支线（多实例；旧称 ThreadMap）；最小字段见 asset-types §2.12 |
| `Character` | draft | 主角/反派/关键配角概念扩展（asset-types §2.10） |
| `WorldRule` | draft | 核心规则 + 限制 + 势力骨架（asset-types §2.11） |
| `Status` | — | `current_phase=P2` |

**PlotSpine / Thread gate 相关字段点名**（模板 `templates/plot-spine.md`）：

- `nodes[24]`：仅 `{id 0..23, title, value_one_liner, function?, anchor?}`；禁止 `scenes/beats/chapters/dialogue`
- `anchor`：闭集见 §1.1；**允许数组**（节点 12 `anchor: [midpoint, growth2]`）
- `cable.mainline` + `strands[].budget_ratio`；`fuses[]`（hidden_info / plant_points ≥3 / reveal_point）
- `volume_map`（模式 B 必填；书级锚点 soft 注记见 asset-types §2.6）
- `Thread`：`kind` / `state` / `plant_at`（`sequence_ref` 复合键）/ `must_not_drop`
- `controlling_idea_draft` =「价值 + 原因」（落 PlotSpine 或 Canon）

### 3.4 knowledge_budget

```yaml
knowledge_budget:
  max_blocks: 16
  core:                        # 粗纲的骨架方法（按序即优先级）
    - K-CONCEPT-010   # 电缆理论（主线结构）
    - K-CONCEPT-011   # 引线系统
    - K-CONCEPT-012   # 支线系统
    - K-STRUCT-003    # 序列 0–23 总论（节点功能标签）
    - K-STRUCT-009    # 五部分结构骨架
    - K-CONFLICT-001  # 冲突三层面分配
    - K-CHAR-001      # 塑造 vs 深层（人物骨架起点）
    - K-WORLD-002     # 三层同心圆（世界框架起点）
  situational:
    - when: route=web            # 毒点预防 + 融梗边界（骨架期自查）
      pull: [K-WRITE-022, K-WRITE-023]
    - when: ensemble_cast
      pull: [K-CONCEPT-009, K-CHAR-011, K-CHAR-012]
    - when: element_driven
      pull: [K-CONCEPT-004, K-CONCEPT-005]
    - when: theme_debate
      pull: [K-CONCEPT-013, K-CONCEPT-014, K-CONFLICT-002]
    - when: preach_risk
      pull: [K-CONCEPT-016]
    - when: antagonist_design
      pull: [K-CONFLICT-003, K-CONFLICT-004, K-CONFLICT-006]
    - when: conflict_ladder
      pull: [K-CONFLICT-005]
    - when: char_skeleton
      pull: [K-CHAR-003, K-CHAR-004, K-CHAR-007, K-CHAR-008, K-CHAR-010]
    - when: world_frame
      pull: [K-WORLD-001, K-WORLD-004, K-WORLD-007, K-WORLD-008]
    - when: has_power_system          # P2 只拉骨架；细化表在 P4
      pull: [K-WORLD-005, K-WORLD-011, K-WORLD-012]
    - when: has_faction_play
      pull: [K-WORLD-018, K-WORLD-019, K-WORLD-020]
    - when: long_serial
      pull: [K-WRITE-012, K-STRUCT-022]
    - when: node_function_detail
      pull: [K-STRUCT-002, K-STRUCT-004, K-STRUCT-005,
             K-STRUCT-006, K-STRUCT-007, K-STRUCT-017]
      # K-STRUCT-001（故事三角）与 core 的 K-STRUCT-003/009 功能重叠，不入本组（预算 8+2+6=16=max_blocks，web 首轮最坏恰满）
  on_overflow: truncate
```

> 本阶段拉结构总论与序列**功能**知识，用于打节点标签；**不得**据此展开场景。

### 3.5 gate

1. `nodes.length == 24` 且 `id` 覆盖 `0..23`。
2. 每个 node 仅有 `title` + `value_one_liner`（无 `scenes`）。
3. 必保锚点存在：`0,6,8,12,16,18,19,22,23`。**模式 B（route=web 分卷）**：书级锚点缺失降为 **warning（不 BLOCK）**；卷内锚点由卷级 seqmap gate（§4.5 #5）强制。
4. 每节点 `value_one_liner` 含价值方向（正/负/翻转语义可辨）。
5. `PlotSpine.cable.mainline` 非空或存在 kind 标识主线的 `Thread`；引线有 `hidden_info` 且 plant/hint 规划 ≥3。
6. 支线 Thread 均有 planned payoff 节点；总篇幅意图 ≤30% 主线。
7. `controlling_idea_draft` 符合「价值+原因」。
8. Character / WorldRule 至少 draft 且与 Blueprint 不矛盾。
9. **无场景级内容**自动扫描：outputs 中不得出现场景表/节拍/「场景1」枚举。
10. **route=web**：`volume_map` 至少规划第一卷 node_range；开篇节点 0–2 价值句强调钩子与信息增量。

### 3.6 on_fail

```yaml
on_fail: repair_in_phase
# 若 Blueprint 高概念无法支撑 24 节点锚点 → rollback_to P1 + Blueprint=stale 候选
# 同一 gate 条款连续 3 次 FAIL → escalate（§0.5 repair 重试上限）
```

### 3.7 route_delta

| | traditional | web |
|--|-------------|-----|
| 推进粒度 | 可一次产出完整 0–23 | 24 节点仍须**全占位**；仅开书窗（默认 0–12）价值句达「可执行」标准。`PlotSpine` 为**文档级单一 status**，gate 只对「当前开书 scope」逐条判定 |
| 分卷 | 可选 | **建议** volume_map；**模式 B**：书级锚点 soft（缺失仅 warning），卷内锚点卷级强制，远端节点可占位到「卷级主题一句话」 |
| 节点文风 | 文学价值句 | 价值句可标注爽点/升级意图（仍禁止场景） |

### 3.8 agent 伪代码

```
run_P2():
  require Blueprint.status ∈ {review,canon,locked}
  load Blueprint, Status
  budget_pull(...)
  build PlotSpine.nodes[0..23]  # title + value only
  place anchors（§1.1 词表；模式 B 书级 soft）
  build PlotSpine.cable/fuses + Thread[]  # 电缆/引线/支线
  draft Character[], WorldRule
  assert no_scene_level(outputs)
  gate_check → writeback → next=P3
```

---

## 4. P3 — Sequence Outline / SequenceMap（序列大纲）

```yaml
phase_id: P3
name: sequence_outline
goal: 将每个序列填充为「事件摘要 + 场景列表」（非章纲、非节拍定稿）。
depends_on: [P2]
next: P4
rollback_to: P2
```

### 4.1 边界（强制）

**允许：**

- 序列级事件摘要（因果链、本序列核心冲突）
- **场景列表**：每场 `scene_id, name, driver, goal, opposition, value_start, value_end, turn_hint`
- 伏笔埋设/回收挂到序列或场景 id
- 人物在本序列的**揭示层意图**（洋葱层标签，非完整定稿）
- 世界观**渐进展开点**（条目级，非圣经定稿）

**禁止：**

- 章号编排、内容块比例、潜文本逐句、字数章纲
- 把场景写成可直接开写的节拍链（那是 P4）
- 跳过场景列表只写长散文

**与 P4 分界：** P3 场景有「价值起止 + 转折提示」即可；P4 才拆动作/反应节拍与鸿沟四重效果精修。

### 4.2 inputs

| type | min_status | required |
|------|------------|----------|
| `PlotSpine` | review | yes |
| `Thread` | draft/review | yes（相关主线/引线） |
| `Character` | draft | yes |
| `WorldRule` | draft | yes |
| `Blueprint` | review | yes（只读校验） |

### 4.3 outputs

| type | target_status | 说明 |
|------|---------------|------|
| `SequenceMap` | review | 每序列事件 + scenes[]；最小字段见 asset-types §2.7 |
| `Thread` | review | 更新埋设/回收挂载（旧称 ForeshadowLedger） |
| `Character` | draft→review | 序列级揭示计划 |
| `WorldRule` | draft→review | 展开点清单 |

**SequenceMap gate 相关字段点名**（模板 `templates/sequence-map.md`）：

- 实例：模式 A `seqmap_main`（视为 vol_01）/ 模式 B 每卷 `seqmap_v{n}`；`volume_id` + 卷内 `index 0..23`；跨卷引用复合键 `{volume_id, sequence_index}`
- 每序列：`event_summary` / `dramatic_function` / `value_shift`（唯一名；废弃 narrative_function / value_arc）
- `scenes[1–5]`：`scene_id`（格式 `scene_v{v}_{s}_{nn}`）/ `name` / `driver` / `goal` / `opposition` / `value_start ≠ value_end` / `turn_hint`
- `reveal_plan[].onion_layer ∈ surface|behavior|emotion|belief|wound`；`coverage_check`（缺序必须列出）
- `info_to_pay[]`（本序列需传递信息；投放方式留 P4/P5）

### 4.4 knowledge_budget

```yaml
knowledge_budget:
  max_blocks: 16
  core:                        # 序列展开与场景列表方法
    - K-STRUCT-003    # 序列总论（本轮 scope 校准）
    - K-STRUCT-010    # 场景转折点（scenes 的价值翻转依据）
    - K-STRUCT-017    # 故事脊椎（因果链自检）
    - K-CONFLICT-001  # 三层面到序列的分配
    - K-CHAR-005      # 弧光五步对齐成长节点
  situational:
    - when: route=web            # 章末钩子谱系 + 期待链（序列级布点参考）
      pull: [K-STRUCT-020, K-STRUCT-021]
    - when: scope∩act_1        # 卷内序列 0–6
      pull: [K-STRUCT-004, K-STRUCT-008]
    - when: scope∩act_2a       # 卷内序列 7–12
      pull: [K-STRUCT-005, K-STRUCT-011]
    - when: scope∩act_2b       # 卷内序列 13–18
      pull: [K-STRUCT-006, K-STRUCT-012]
    - when: scope∩act_3        # 卷内序列 19–23
      pull: [K-STRUCT-007, K-STRUCT-014, K-STRUCT-015, K-STRUCT-016]
    - when: scene_split_detail
      pull: [K-STRUCT-002, K-STRUCT-013, K-WRITE-010]
    - when: conflict_depth_low
      pull: [K-CONFLICT-005]
    - when: theme_debate
      pull: [K-CONCEPT-014]
    - when: reveal_planning
      pull: [K-CHAR-002]
    - when: has_faction_play
      pull: [K-WORLD-020, K-WORLD-021]
    - when: element_driven
      pull: [K-CONCEPT-004, K-CONCEPT-005]
    - when: long_serial
      pull: [K-WRITE-012, K-STRUCT-022]
    - when: info_seeding
      pull: [K-WRITE-001]      # 仅信息优先级意识，不写正文
  on_overflow: truncate
```

### 4.5 gate

1. 每个 `PlotSpine` 节点均有对应 `SequenceMap` 条目（当前 scope 内；web 可限定已开卷）。
2. 每序列 `scenes.length` ∈ [1,5]（缺省目标 2–5；极短序列至少 1）。
3. 每场景 `value_start ≠ value_end`。
4. 序列内场景冲击力意图递增（末场为序列最强，自检）。
5. 必保锚点序列的 `event_summary` 体现不可逆/方向转/终局语义（模式 B：锚点以**卷内** seqmap 为准，此处即强制点）。
6. 无 `ChapterPlan` 字段；无内容块表。
7. 引线 hints 在场景/序列上有挂载计划。
8. 人物 `reveal_plan` 压力与洋葱层不倒挂（高压力序列不得只停在 surface，除非有意伪装）。
9. **route=web**：开书/当前卷序列场景列表完整；标注每序列至少一处「爽点或信息增量」意图；**模式 B**：当前卷 `seqmap_v{n}` 卷内锚点齐备（强制）。

### 4.6 on_fail

```yaml
on_fail: repair_in_phase
# 节点价值与场景列表系统性冲突 → rollback_to P2，PlotSpine 相关节点标 stale
# 同一 gate 条款连续 3 次 FAIL → escalate（§0.5 repair 重试上限）
```

### 4.7 route_delta

| | traditional | web |
|--|-------------|-----|
| scope | 倾向一次 0–23 | 按卷分批；batch=1–3 序列/轮 亦可 |
| 产出密度 | 全序列 scenes | 连载前沿序列优先 review |

### 4.8 agent 伪代码

```
run_P3(scope=all|volume|seq_range):
  require PlotSpine.status ≥ review
  for seq in scope:
    expand event_summary from node
    split scenes 2..5 with value flip
    attach foreshadow + reveal_plan
  assert not chapter_outline(outputs)
  gate → writeback SequenceMap → next=P4
```

---

## 5. P4 — Detail Outline / SceneBeat + Canon（细纲）

```yaml
phase_id: P4
name: detail_outline
goal: 将场景列表深化为节拍级设计，并定稿人物档案与世界观圣经（canon）。
depends_on: [P3]
next: P5
rollback_to: P3
```

### 5.1 边界（强制）

**允许：**

- 每场景：冲突五步、节拍序列（动作↔反应）、转折点、四重效果（惊奇/好奇/见解/新方向）
- 人物洋葱五层**全部写明**；弧光里程碑按卷映射（`arc.milestones`）
- 世界观消除「待定」；技能/势力若存在则规则闭环
- 节奏曲线（高潮/缓和/过渡）在**场景序列**层标注

**禁止：**

- 以「第 N 章」为主键的内容块章纲（P5）
- 正文段落、逐句潜文本章纲表（可在节拍层写实质意图，但不做章节排版）

> 历史 phase 文档若把「章节规划」放在细纲：本契约以 **P5=章纲** 为准；P4 只产出 SceneBeat 与 canon 设定。章映射可在 P4 末给出**建议** `scene→chapter` 草稿，status 不得高于 draft，且不充当 gate。

### 5.2 inputs

| type | min_status | required |
|------|------------|----------|
| `SequenceMap` | review | yes |
| `PlotSpine` | review | yes |
| `Character` | draft/review | yes |
| `WorldRule` | draft/review | yes |
| `Thread` | review | yes（含伏笔/引线；draft 仅作补充） |

### 5.3 outputs

| type | target_status | 说明 |
|------|---------------|------|
| `SceneBeat` | review | 每场景节拍链；最小字段见 asset-types §2.8 |
| `Character` | canon（gate PASS 后按 auto_promote 晋升） | 最小字段见 asset-types §2.10 |
| `WorldRule` | canon（同上） | 最小字段见 asset-types §2.11 |
| `Canon`（`canon_root` / `canon_style`） | canon（gate PASS 后按 auto_promote.p4_canon_seed 晋升） | P1 种子随 Character/WorldRule 定稿 |
| `Thread` | review | 埋/收对齐 |

**gate 相关字段点名**：

- `SceneBeat`：`sequence_ref` 复合键；`goal / conflict{opposition,stakes} / turning_point.gap / outcome`；`value_start ≠ value_end`；`beats[] ≥2`（action↔reaction）；`character_pressure[].reveal_layer`（五键）；`thread_ops[].op ∈ plant|advance|payoff|tangle`；`exposition_ammo[]`
- 四重效果与作家六问是 **gate 谓词**（结论记入 gate 记录/evidence，不落 schema bool 字段）
- `Character`：`onion` 五键（surface/behavior/emotion/belief/wound）全非空；`arc.milestones[]`（按卷弧光，替代硬编码 seq 8/12/16/19 对位）；`masks[]`；`key_choices ≥3`；`voice`（tics/sentence_style/taboo_words/sample_line）
- `WorldRule`：`rules[].cost` 可查；`power_system` 闭环；全文无 `pending/TBD`

### 5.4 knowledge_budget

```yaml
knowledge_budget:
  max_blocks: 20
  core:                        # 节拍设计 + 人物/世界定稿方法
    - K-STRUCT-013    # 场景设计五步法
    - K-STRUCT-010    # 转折点
    - K-STRUCT-011    # 鸿沟机制
    - K-STRUCT-018    # 节拍与潜文本
    - K-CHAR-002      # 压力揭示
    - K-CHAR-004      # 洋葱五层定稿
    - K-CHAR-005      # 弧光对齐
    - K-WRITE-008     # 作家六问预检
  situational:
    - when: rhythm_tuning
      pull: [K-STRUCT-012, K-STRUCT-019]
    - when: char_canonize
      pull: [K-CHAR-001, K-CHAR-003, K-CHAR-006, K-CHAR-007, K-CHAR-008,
             K-CHAR-009, K-CHAR-010, K-CHAR-013, K-CHAR-014]
    - when: crowd_reaction
      pull: [K-WORLD-009]
    - when: conflict_layer_check
      pull: [K-CONFLICT-001, K-CONFLICT-002, K-CONFLICT-003, K-CONFLICT-005]
    - when: preach_risk
      pull: [K-CONCEPT-016]
    - when: world_canonize
      pull: [K-WORLD-001, K-WORLD-002, K-WORLD-004, K-WORLD-005, K-WORLD-006,
             K-WORLD-007, K-WORLD-008, K-WORLD-010]
    - when: has_power_system          # P4 细化层（P2 只拉骨架 005/011/012）
      pull: [K-WORLD-013, K-WORLD-014, K-WORLD-015, K-WORLD-016, K-WORLD-017,
             K-WORLD-022, K-WORLD-023, K-WORLD-024]
    - when: has_faction_play
      pull: [K-WORLD-018, K-WORLD-019]
    - when: card_workflow
      pull: [K-WRITE-010]
  on_overflow: truncate
```

### 5.5 gate

gate 只判**内容完备**；status 晋升移出 gate 谓词（见 gate 后晋升条款）。

1. scope 内每个 `SequenceMap.scenes[]` 均有对应 `SceneBeat`。
2. 每场景 `value_start ≠ value_end`；`beats` ≥ 2 轮动作反应。
3. `turn`（转折/鸿沟）非空，期望 vs 结果落差可辨；四重效果（惊奇/好奇/见解/新方向）至少 3/4 有效，**每项一句依据**（非裸 bool）。
4. 无连续同类刺激导致回报递减（抽检关键序列）。
5. **Character 内容完备**：主笔角色 `onion` 五键（surface/behavior/emotion/belief/wound）全非空；`masks` / `key_choices ≥3` / `voice` 已填。
6. **弧光覆盖**：`arc.milestones` 覆盖本卷成长节点（替代 seq 8/12/16/19 硬编码对位）。
7. **WorldRule 内容完备**：无 `pending/TBD`；有力量体系则代价与限制可查。
8. 作家六问：每场景对照 K-WRITE-008 六问逐问一句依据，或列出豁免 Decision。
9. **route=web**：节奏图含「定期正面价值释放」标记；力量升级节点与场景挂钩。

**gate PASS 后的晋升（非 gate 谓词）**：按 `Status.web_serial.auto_promote.p4_canon` 自动将主笔 Character / WorldRule 升 `canon`；按 `auto_promote.p4_canon_seed`（web 默认 true）将 `canon_root` / `canon_style` 随同升 `canon`；均写 `Decision(approved_by=agent_auto)` 留痕；`auto_promote` 未启用（false / traditional 未配置）→ 待用户确认后晋升。

### 5.6 on_fail

```yaml
on_fail: repair_in_phase
# 场景价值与 SequenceMap 系统性偏离 → 相关 SceneBeat + 父 scene 标 stale，可 rollback_to P3
# 人物/世界自相矛盾 → escalate Decision 或走 conflict-playbook
# 同一 gate 条款连续 3 次 FAIL → escalate（§0.5 repair 重试上限）
```

### 5.7 route_delta

| | traditional | web |
|--|-------------|-----|
| 定稿范围 | 倾向全书角色/世界一次 canon | 允许「当前卷 canon + 远期 draft」但开书卷必须 canon |
| 节拍粒度 | 全场景 | 连载窗口优先；库存场景可 review 稍后 |

### 5.8 agent 伪代码

```
run_P4(scope):
  require SequenceMap ≥ review
  for scene in scope:
    design beats + gap + four_effects
    six_questions()          # K-WRITE-008
  complete Character onion+milestones / WorldRule（内容完备）
  gate → PASS 后按 auto_promote.p4_canon / p4_canon_seed 升 canon
         （Character/WorldRule + canon_root/canon_style）+ Decision(agent_auto)
  next=P5
```

---

## 6. P5 — Chapter Outline / ChapterPlan（章纲）

```yaml
phase_id: P5
name: chapter_outline
goal: 将已设计场景编排为可写的章纲：内容块、潜文本节拍、解说策略、钩子与字数。
depends_on: [P4]
next: P6
rollback_to: P4
```

### 6.1 边界

**允许：** 章为基本单位；内容块类型与比例；潜文本；解说金字塔；章末钩子；伏笔章级追踪。  
**禁止：** 完整正文；改写 Character/WorldRule canon 字段（须 change 流程）。

### 6.2 inputs

| type | min_status | required |
|------|------------|----------|
| `SceneBeat` | review | yes（本章覆盖场景） |
| `Character` | canon | yes |
| `WorldRule` | canon | yes |
| `SequenceMap` | review | yes |
| `Thread` | review | no（伏笔追踪） |

### 6.3 outputs

| type | target_status | 说明 |
|------|---------------|------|
| `ChapterPlan` | review | 最小字段见 asset-types §2.9（`chapter_{nnnn}` 四位全局章号） |
| `Status` | — | 写作指针 |

**ChapterPlan gate 相关字段点名**（模板 `templates/chapter-plan.md`）：

- `hooks: {open, close, close_type?}`（废弃 `hook:{type,note}`）
- `word_count_target`（route=web 默认 **2000–4500** 字，Status 可覆盖）
- `scene_ids[]`（`scene_v{v}_{s}_{nn}`，可追溯 SceneBeat）；章级价值走向由本章场景 `value_start/value_end` 聚合判定（章纲不重记）
- `content_blocks[].type`（五类交替）；关键块 `summary` 含潜台词意图（表面≠实质可辨；详拍在 SceneBeat）
- `exposition: {must_pay[], strategy, avoid[]}`
- `character_play[]`（对齐 Character `masks`/`voice`）
- `serial_notes.payoff_entries[]`（route=web 爽点/信息增量账）

### 6.4 knowledge_budget

```yaml
knowledge_budget:
  max_blocks: 12
  core:                        # 章纲编排方法
    - K-STRUCT-019    # 幕节奏 → 章节奏
    - K-STRUCT-018    # 潜文本节拍
    - K-WRITE-003     # 解说进度金字塔
    - K-WRITE-013     # 读者兴趣三策略
  situational:
    - when: exposition_binding
      pull: [K-WRITE-001, K-WRITE-002, K-WRITE-007]
    - when: backstory_flashback
      pull: [K-WRITE-004, K-WRITE-005]
    - when: route=web            # 钩子/连载章法 + 爽点工程 + 毒点降档
      pull: [K-WRITE-011, K-STRUCT-020, K-WRITE-022]
    - when: expectation_chain
      pull: [K-STRUCT-021]
    - when: surprise_coincidence
      pull: [K-WRITE-014]
    - when: imagery_system
      pull: [K-WRITE-015]
    - when: char_chapter_play
      pull: [K-CHAR-006]
  on_overflow: truncate
```

### 6.5 gate

1. 每章 `scene_ids` 非空且均可追溯至 SceneBeat。
2. 章级价值翻转成立（value 起止 ≠）。
3. 内容块类型不全为单一类型连续过长（对话/描写/动作有交替意识）。
4. 每个关键节拍潜台词可辨（文本≠实质；在 `content_blocks[].summary` 内注明，或单列可选键 `subtext`——schema 见 asset-types §2.9）。
5. 解说：`must_pay` 均绑定 strategy；禁止三项错误已自检。
6. **route=web 强制**：`hooks.close` 非空（`open` 建议填）；`word_count_target` ∈ 约定区间（默认 **2000–4500**，可被 Status 覆盖）；本章有爽点或信息增量标记（`payoff_entries` ≥1）。
7. **route=traditional**：钩子可选但节奏不得连续三章无价值翻转。
8. 人物表现与 Character canon `masks`/`voice` 一致。

### 6.6 on_fail

```yaml
on_fail: repair_in_phase
# 场景无法支撑章价值 → 回 P4 修 SceneBeat（rollback_to P4）
# 同一 gate 条款连续 3 次 FAIL → escalate（§0.5 repair 重试上限）
```

### 6.7 route_delta

| | traditional | web |
|--|-------------|-----|
| 章长 | 灵活 | 默认 2000–4500 字，强钩子 |
| 批量 | 可按幕 | 按连载窗口 + 存稿章（开篇批次 = 首个普通批量，默认 1–3 章） |

> 「黄金三章」特殊 gate **已废弃**（glossary §1.1）：开篇章不设章级特殊检查窗，逐章过本 phase 常规 web gate（§6.5 #6）即可。卖点前置/激励事件落点属 P1–P3 结构设计，在各自 gate 判定。

### 6.8 agent 伪代码

```
run_P5(chapter_scope):
  require Character+WorldRule canon
  map scenes → chapters
  design content_blocks + subtext + exposition + hooks{open,close}
  gate_check(§6.5)          # web 项逐章判定；无开篇特殊分支
  writeback ChapterPlan → next=P6
```

---

## 7. P6 — Writing / ManuscriptUnit（正文）

```yaml
phase_id: P6
name: writing
goal: 按章纲产出可发布正文，并以 evidence_checks 通过六问/craft/泄密检查；不静默修改 canon。
depends_on: [P5]
next: null   # 或循环下一 ChapterPlan
rollback_to: P5
```

### 7.1 边界

**允许：** 对话/描写/动作/内心/叙述落地；语言打磨；章内微调节奏。  
**禁止：** 擅自改 PlotSpine/SequenceMap/Character/WorldRule canon；大改章价值弧（应回 P5）。

### 7.2 inputs

| type | min_status | required |
|------|------------|----------|
| `ChapterPlan` | review | yes（当前章） |
| `ManuscriptUnit`（前章） | — | **条件行**：前章尚不存在时跳过（首章豁免），存在则必装 `summary_after` + 尾段（衔接） |
| `Character` | canon | yes（出场） |
| `WorldRule` | canon | yes（触达） |
| `SceneBeat` | review | yes（本章场景） |
| `Canon`（`canon_style` + invariants + continuity 分片） | canon | yes；`canon_continuity_v{当前卷}` 为**条件行**——分片尚不存在时跳过（本卷尚无已确立 facts；首次 facts upsert 时创建并注册，初始 status=canon），存在则必装 |
| `Recap` | — | yes：`recap_state` 必装；`recap_book` / `recap_vol_{n-1}` 为**条件行**——尚不存在时跳过（首章/首卷豁免），存在则必装 |
| `Blueprint` | review | no（语气/类型校准） |

> 完整召回切片（Thread 过滤、实体 facts 检索、防剧透标注等）以 **protocol §4.2 write_unit 表为唯一 SSOT**；本表只列 contract min_status。

### 7.3 outputs

| type | target_status | 说明 |
|------|---------------|------|
| `ManuscriptUnit` | draft →(自检) review →(gate PASS 按 auto_promote.chapter_canon_on_gate_pass) canon（存稿）→(publish) locked（已发布） | 章节正文；最小字段见 asset-types §2.13 |
| `ChapterPlan` | —（status 不变） | 仅同步 `serial_notes.payoff_entries[].realized`（write_unit 允许集见 protocol §6.2） |
| `Thread` | review | 实际埋收回写 |
| `Recap` | canon | `recap_state` 更新 + `recap_book` 滚动（asset-types §2.15） |
| `Status` | — | `last_written_chapter`、存稿计数 |

**ManuscriptUnit gate 相关字段点名**（模板 `templates/manuscript-unit.md`；ProseUnit 仅为别名，禁止独立注册）：

- `summary_after`（**必填**）/ `continuity_delta[]`（**必填**，可为空数组）
- `hooks_realized: {open, close}`
- `evidence_checks[]`：`{claim, quote ≤30字, note 一句论证}`——替代六问/craft 自评 bool 矩阵
- `body_uri` / `word_count` / `issues[]`

### 7.4 knowledge_budget

> `write_unit` 意图复用本预算（unit_type 追加表与 protocol §4.2 同源一致）。

```yaml
knowledge_budget:
  max_blocks: 10
  core:                        # 正文 craft 基线
    - K-WRITE-001     # 展示不要告诉
    - K-WRITE-008     # 作家六问
    - K-WRITE-016     # 对话三原则
    - K-WRITE-017     # 描写六要诀
  situational:
    - when: unit_type=dialogue     # 对话密集章（遮名声纹抽检）
      pull: [K-CHAR-013]
    - when: unit_type=exposition   # 解说/信息重章
      pull: [K-WRITE-002, K-WRITE-006]
    - when: unit_type=action       # 战斗/动作/强转折
      pull: [K-WRITE-019]
    - when: unit_type=interior     # 情感/内心戏
      pull: [K-CHAR-006]
    - when: unit_type=description  # 描写/场面铺陈
      pull: [K-WRITE-017, K-WORLD-010]
    - when: chapter_rhythm         # 章内微结构
      pull: [K-WRITE-020]
    - when: critic_round           # critic 轮四查支撑：口癖/水字/遮名 + 毒点（§7.9）
      pull: [K-WRITE-018, K-WRITE-021, K-CHAR-013, K-WRITE-022]
    - when: style_polish           # 文风/意象打磨
      pull: [K-WRITE-009, K-WRITE-015]
    - when: route=web              # 章末钩子实现
      pull: [K-WRITE-011]
  on_overflow: truncate
```

### 7.5 gate（evidence_checks 制）

主观条款一律产出 `evidence_checks[]` 条目——每条附正文摘引（`quote` ≤30 字）+ 一句论证（`note`），**替代自评 bool**：

1. **作家六问**（逐场）：谁在推动场景？他想要什么？为什么他想要它？什么在阻止他？后果是什么？下一步是什么？——六问文本以 **K-WRITE-008 原文为唯一版本**；每场至少 1 条 evidence。
2. **转折/钩子落地**：章纲 `hooks.open/close` 与转折在正文有对应实现（evidence 摘引钩子句）。
3. **对话**：对话三原则抽检 ≥1 条 evidence。
4. **描写与解说**：描写六要诀抽检 ≥1 条 evidence；重要信息 show > tell，解说走冲突/弹药。
5. **canon 无冲突**：未引入与 WorldRule/Character canon 冲突的新设定（evidence 写明比对结论）；必须新增 → 暂停走 change。
6. **泄密检查**：对照 `Thread.reveal_point`（fuse `hidden_info`）与 `facts.spoiler_level`——未揭示信息未在正文直说，只可潜台词/征兆（evidence 附自查说明）。
7. **一致性**：视角/时态/声音与 `canon_style` 一致。
8. **写回完备**：`summary_after` 非空；`continuity_delta` 已填（可空数组）；`recap_state` 已更新（+滚动 `recap_book`）。
9. **route=web**：章末钩子到位；字数在目标 ±15%（默认 2000–4500，Status 可覆盖）；至少一处爽点或信息增量（`payoff_entries.realized` 回写）。

### 7.6 on_fail

```yaml
on_fail: repair_in_phase
# 结构/价值弧错误 → rollback_to P5
# 设定冲突 → conflict-playbook（block 发布）
# 同一 gate 条款连续 3 次 FAIL → escalate（§0.5 repair 重试上限）
```

### 7.7 route_delta

| | traditional | web |
|--|-------------|-----|
| 发布节奏 | 可整部修订后 publish（晋升 locked） | 章级 canon 存稿；publish 晋升 locked（已发布）；保持存稿缓冲（Status 配置） |
| 读者反馈 | 可选 | 允许支线权重调整，但须 Decision + 下游 stale 传播 |

### 7.8 agent 伪代码

```
run_P6(chapter_id):
  load per protocol §4.2 write_unit 表（含 Recap / canon_style / 前章 summary_after）
  budget_pull(craft K-IDs only)
  write by content_blocks
  build evidence_checks（六问/对话/描写/canon/泄密）
  if setting_drift → block + conflict flow
  writeback ManuscriptUnit(summary_after+continuity_delta 必填), Thread
  sync ChapterPlan.serial_notes.payoff_entries[].realized   # web；write_unit 对 ChapterPlan 仅此字段
  update recap_state + recap_book, Status pointer
  if critic_cadence 命中 → critic pass（§7.9：独立子代理四查，写回 last_critic_chapter）
  if more ChapterPlan → next chapter else idle
```

### 7.9 critic pass（独立评审轮）

- **节奏**：`Status.flags.critic_cadence`，默认 `every_5_chapters + volume_end`。
- **形式**：**必须以独立子代理/新会话执行**——不携带本轮产出上下文（由执行环境保证，非自觉）；产出 `CritiqueReport`（落点 `notes/critiques/{id}.md`，登记字段见 asset-types §2.14）。
- **输入**：目标章正文 + 章纲（ChapterPlan）+ canon + `canon_style` + **当前卷 SequenceMap 摘要 + PlotSpine 卷内节点表**（看方向，不只看文笔）。
- **动作（必含四查）**：K-WRITE-018 口癖扫描；K-WRITE-021 水字扫描；K-CHAR-013 遮名抽检（对话 ≥3 段的章）；方向偏航检查（本章价值走向 vs 卷内节点）。
- **写回**：`Status.web_serial.last_critic_chapter`（漏跑可检；字段见 asset-types §2.1）。
- **处置**：不合格 → `repair_in_phase`（结构性问题按 §7.6 回退）；Critique 结论经 Decision 采纳后才进 canon 链路。与 web-serial-playbook 对齐。

---

## 8. 跨阶段规则

### 8.1 依赖与阻断

```
ADVANCE(phase):
  for dep in phase.depends_on:
    if not gate_passed(dep): BLOCK
    if any input.status == stale: BLOCK → sync|conflict
    if any input.status < min_status: BLOCK
  run phase
  writeback outputs
  if gate ok: Status.current_phase = phase.phase_id
```

**advance 与 write_unit 在 P6 的关系**：`Status.current_phase == P6` 时，`advance` = 按 `serial_cursor` / 待写 ChapterPlan 队列**批量执行 write_unit**（逐 unit 过 P6 gate）；单点指定某章/场景 → `write_unit`。二者共用 §7 契约、边界与 knowledge_budget，不得各自另立召回或门禁。

### 8.2 变更传播（摘要）

| 变更源 | 标记 stale | 默认 rollback/repair |
|--------|------------|----------------------|
| Blueprint | PlotSpine 及以下 | 视锚点是否崩塌 |
| PlotSpine 节点 | SequenceMap 对应序列、下游 SceneBeat/Chapter/ManuscriptUnit | P3+ |
| SequenceMap 场景 | SceneBeat、ChapterPlan、ManuscriptUnit | P4+ |
| Character/WorldRule canon | 引用其的 SceneBeat/Chapter/ManuscriptUnit | 冲突裁决后 sync |
| ChapterPlan | ManuscriptUnit | P6 |
| ManuscriptUnit（未发布） | **C（条件 stale）**：仅衔接受影响的后续章/召回它的单元 | P6 局部 resync |
| ManuscriptUnit（locked=已发布） | **不 stale**：写 `retcon_note` 入 `canon_continuity_v{n}`，后续章按 `forward_strategy` 向前兼容 | conflict-playbook |

优先级：`用户当轮指令 > Decision > Canon.invariant > 更高锁定阶段资产 > working`。

### 8.3 分批 scope（尤其 web）

```yaml
scope:
  mode: all|volume|sequence_range|chapter_range
  from: ...
  to: ...
# gate 只强制 scope 内；scope 外允许 draft
# 但开书/发布窗口内资产不得以 draft 充数
```

### 8.4 与 phases/*.md 关系

| 文档 | 角色 |
|------|------|
| `runtime/phase-contracts.md` | **执行契约 SSOT**（I/O/gate/budget/边界） |
| `phases/0x-*.md` | 操作步骤与检查清单（方法论展开） |
| `knowledge-index.md` | K-ID 导航 |
| `knowledge/*` | 只读知识服务 |

冲突时：**以本文件边界表与 gate 为准**；phases 文中越界示例（如 P2 写场景、P3 写章纲、P4 写内容块章纲）不得执行。

---

## 9. 双轨总览速查

| phase | traditional 要点 | web 要点 |
|-------|------------------|----------|
| P1 | 类型惯例完整 | 细分类型 + 开篇钩子意图 |
| P2 | 24 节点一次齐 | 可按卷；书级锚点 soft（模式 B）；节点仍禁止场景 |
| P3 | 全序列场景列表 | 分批序列；爽点意图；卷内锚点强制 |
| P4 | 人物世界全书 canon | 开书卷 canon（gate PASS 后 auto_promote）；其余可延 |
| P5 | 节奏优先章长灵活 | 2000–4500 字 + 强制钩子（逐章常规 gate） |
| P6 | 修订后定稿 | 章级存稿（canon）→publish 升 locked；evidence_checks + critic 抽检；反馈经 Decision |

---

## 10. 契约自检（指针化）

写回/DONE 验收唯一权威 = **`runtime/writeback-acceptance.md`**；本文件不再维护重复清单。进 phase 前的契约独有自检（≤5 条）：

```
[ ] 已读 Status.route 与 current_phase；depends_on gate 已通过
[ ] inputs 类型/status 满足 min；无 stale 未处理（按 intent 豁免见 protocol §4.4）
[ ] knowledge_budget 白名单/块数已定（§0.4，先资产后知识）
[ ] 本 phase 硬边界禁止项已加载（§0.2）
[ ] gate 可逐条勾选（主观项备 evidence）；on_fail 路径明确（含 §0.5 3 次上限）
```

---

## 11. 枚举与类型引用（与 asset-types 对齐）

| phase_id | 主产出 type |
|----------|-------------|
| P1 | `Blueprint` |
| P2 | `PlotSpine`, `Thread`(draft), `Character(draft)`, `WorldRule(draft)` |
| P3 | `SequenceMap`, `Thread`(更新) |
| P4 | `SceneBeat`, `Character(canon)`, `WorldRule(canon)` |
| P5 | `ChapterPlan` |
| P6 | `ManuscriptUnit` |

共享：`Status`, `Manifest`, `Decision`, `Canon`（不变量子集）, `Recap`（P6/卷末维护）。  
别名归一：`ProseUnit→ManuscriptUnit`；`ThreadMap/ForeshadowLedger→Thread`；见 `asset-types.md` §0.3.1。

---

## 12. 修订记录

| rev | 变更 |
|-----|------|
| 1 | 初版六阶段契约 |
| 2 | 对齐 2026-08-12 决策书：schema 内嵌块全部指针化（SSOT=asset-types）；预算改块数+每块 ≤120 行、触发标签闭集收编全部自由短语；P1 卖点证据制；P2 力量体系拆层/锚点数组/模式 B 书级 soft；P3 复合键 + dramatic_function/value_shift；P4 内容完备谓词 + auto_promote 晋升移出 gate + 力量细化白名单；P5 hooks{open,close} + 2000–4500 + K-STRUCT-020/021；P6 evidence_checks gate + 泄密检查 + summary_after/continuity_delta/recap 必检 + §7.9 critic pass；§8.2 补 ManuscriptUnit 两行；§1.1 正式锚点词表 |
| 3 | 2026-08-13 修复轮：§7.3 章状态链统一 draft→review→canon（存稿）→locked（publish=已发布），§0.3/§7.7/§9 locked 语义同步；P1 outputs/gate 补 canon_root/canon_style 种子充实与自检晋升，§5.5 晋升加 p4_canon_seed；§7.2 前章/Recap 条件行（首章/首卷豁免）；unit_type 五值（emotion→interior）+ content_blocks 缺失回退 protocol §4.2；白名单挂载（P1 web 四块 + protagonist_design→K-CHAR-014、P2/P3 新增 web 组、P4 char_canonize 追加 K-CHAR-013/014、P5 web 追加 K-WRITE-022、P6 dialogue→K-CHAR-013 + critic_round 四块）；预算 P1 12 / P2 16 / P4 20 + §0.4 溢出补拉条款；§0.5 repair 3 次上限 + 各 phase on_fail 加注；§7.9 critic pass 独立子代理/四查/写回 last_critic_chapter；§7.3/§7.8 payoff realized 同步行；§10 压缩为指针 + 独有项；第三波收尾（V1 复检修正：冷启动条件行/六件套允许集/小节指针/编号/口径对齐） |

---

*rev: 3 | 通用工程层 | 不绑定具体作品*
