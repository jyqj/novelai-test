# 资产类型系统（Asset Types）

> **定位**：与路径解耦的类型系统。Agent 对 **type** 编程，不对接具体目录名或书名。  
> **依赖**：`runtime/glossary.md`（术语 SSOT）、`runtime/protocol.md`（状态·召回·回写）、`runtime/phase-contracts.md`（阶段 I/O）。  
> **知识**：仅引用 `K-xxx` ID；不复制方法论正文。

---

## 0. 对 type 编程原则

### 0.1 核心公理

| # | 原则 | 可执行含义 |
|---|------|------------|
| P1 | **Type 一等公民** | 读写、召回、门禁、冲突裁决均以 `type` + `id` 寻址；禁止硬编码文件路径为业务逻辑 |
| P2 | **路径是 adapter** | `uri` / `path` 仅由 storage adapter 解析；主协议只认 `type`、`id`、`rev`、`status` |
| P3 | **Manifest 为注册表** | 任何可执行资产必须在 `Manifest` 有条目；未注册 = 不可被门禁/召回视为存在 |
| P4 | **status 统一语义** | 全局枚举见 §1；working/critique 类草稿无执行权（不得作 gate 输入的唯一依据） |
| P5 | **rev 单调** | 每次写回 `rev += 1`；引用方记录 `depends_on_rev`；上游 rev 变化 → 下游可标 `stale` |
| P6 | **先资产后知识** | 召回顺序：必召回 assets → 相关 Decision/Canon → 再按 budget 拉 `K-xxx` |
| P7 | **Canon / Decision 优先** | 冲突时优先级见 `conflict-playbook`；本文件只定义字段与依赖，不重定义裁决链 |
| P8 | **最小字段可门禁** | 下列「最小字段」= gate 可读的最小可验证面；扩展字段允许，但不得替代最小字段 |

### 0.2 通用信封（所有资产实例）

每个资产实例在逻辑层必须具备下列元字段（可内嵌 frontmatter 或并列 sidecar）：

```yaml
id: string              # 全局唯一，建议 {type_short}_{slug} 或 uuid
type: AssetType         # 见 §2 枚举
rev: integer            # 从 1 起，单调递增
status: AssetStatus     # 见 §1
title: string           # 人读标签，非业务键
created_at: datetime
updated_at: datetime
depends_on:             # 逻辑依赖（type + id + 可选 min_rev）
  - { type: string, id: string, min_rev?: integer }
stale_reason: string | null
tags: string[]          # 可选，检索辅助
uri: string | null      # adapter 填充；协议层可空
```

### 0.3 类型枚举 `AssetType`

```
Status | Canon | Manifest | Decision |
Blueprint | PlotSpine | SequenceMap |
SceneBeat | ChapterPlan | Character |
WorldRule | Thread | ManuscriptUnit | Recap
```

### 0.3.1 类型别名（写回时归一，禁止再注册为独立 type）

| 别名 / 旧称 | 正式 type | 说明 |
|-------------|-----------|------|
| `ProseUnit` | `ManuscriptUnit` | P6 正文单元 |
| `ThreadMap` | `Thread`（多实例集合视图） | 电缆/引线/支线用多个 Thread 或 PlotSpine.cable/fuses 字段承载 |
| `ConflictMatrix` | 嵌入 `PlotSpine.conflict_matrix` 或 Canon 注释 | 非独立 AssetType |
| `ForeshadowLedger` | `Thread`（plant/payoff 账本） | 用 Thread.advance_log / payoff |
| `RhythmMap` / `ExpositionPlan` | 嵌入 `ChapterPlan` / `SceneBeat` 字段 | 非独立 AssetType |

**字段/枚举级废弃别名**（写回时归一；术语裁决见 glossary §1.1）：

| 废弃写法 | 正式形 | 落点 |
|----------|--------|------|
| `hook: {type, note}` | `hooks: {open, close, close_type?}` | ChapterPlan §2.9 |
| `value_in` / `value_out` | `value_start` / `value_end` | SequenceMap / SceneBeat |
| `sequence_id`、跨资产裸 int 序列引用 | `sequence_ref: {volume_id, sequence_index}`（速记 `v3:s12`） | §2.8 / §2.12 |
| `pay off` | `payoff` | Thread op |
| `narrative_function` / `value_arc` | `dramatic_function` / `value_shift` | SequenceMap §2.7 |
| `plot_turn_1/surprise_1`、`plot_turn_2/surprise_2`、`climax_zone` | `shock1`、`shock2`、`climax` | PlotSpine anchor |
| `route: hybrid` | route ∈ {traditional, web}；混合只写 `flags.dual_track` | Status §2.1 |
| `voice_notes`（裸字符串） | `voice: {tics[], sentence_style, taboo_words[], sample_line}` | Character §2.10 |
| `trauma`（洋葱键） | `wound` | Character §2.10 |
| `continuity_facts` | `facts` | Canon continuity 分片 §2.2（写回归一，兼容旧项目） |
| `narration`（content_blocks.type / unit_type） | `exposition` | ChapterPlan §2.9 五值闭集 |
| `emotion`（作 content_blocks.type / unit_type 时） | `interior` | ChapterPlan §2.9 五值闭集；洋葱层/元素类 `emotion` 不受影响 |

### 0.4 写回伪代码

```
function writeback(asset, patch, intent):
  assert asset.id in Manifest.entries
  if asset.status in {locked, archived}:
    require Decision.allow_mutate(asset.id) or intent.user_override
  asset = merge(asset, patch)
  asset.rev += 1
  asset.updated_at = now()
  if broke_downstream(asset):
    # locked 下游例外：不标 stale，改写 retcon_note（见 §2.2 / glossary §6）
    mark_stale(dependents_of(asset.id) where status != locked, reason="upstream_rev_bump")
  Manifest.touch(asset.id, rev=asset.rev, status=asset.status)
  return asset

# publish 例外：status-only touch（升 locked，唯一默认），不走本函数、rev 不递增（见 §3.2）
```

---

## 1. 状态枚举 `AssetStatus`

**唯一合法值**（禁止别名分叉）：

| status | 含义 | 可作 gate 输入 | 默认可被 Agent 改写 |
|--------|------|----------------|---------------------|
| `draft` | 工作稿，未自检 | 否（仅作参考） | 是 |
| `review` | 待确认 | 是：满足 contract `min_status` 即可作下游输入（glossary §6） | 是 |
| `canon` | 已采纳/已过 gate 的**存稿**（未发布的项目真值） | 是 | 需变更协议 |
| `locked` | **已发布/冻结**（publish 唯一默认晋升位），防误写；**不参与 stale 传播**——上游变更不标 stale，改写 `retcon_note` 入 `canon_continuity_v{n}`（语义见 glossary §6） | 是 | 否（unlock 需 `Decision(approved_by=user)`） |
| `stale` | 因上游变更失效 | 否（必须先 sync） | 是（仅允许 sync/归档路径） |
| `archived` | 历史保留，不参与召回默认集 | 否 | 否 |

### 1.1 合法迁移（状态机）

```
draft ──► review ──► canon ──► locked (发布/冻结)
  │          │          │
  │          │          └──► archived
  ▼          ▼
archived  ◄──┘

draft | review | canon ──上游变更/冲突裁决──► stale ──sync 完成──► 原 status（draft | review | canon）| archived
locked ──上游变更──► 不入 stale；写 retcon_note（§2.2）
locked ──Decision(approved_by=user).unlock──► canon | draft
```

规则：
- `stale` **不得**直接升 `locked`。
- `archived` 回活 → 必须新 `rev` 且先入 `draft` 或 `review`。
- 用户当轮明确指令可强制迁移；须写 `Decision` 留痕（见 §2.4）。
- publish = status-only 晋升：升 `locked`（唯一默认；「已发布」判定全库唯一 = `status == locked`，`last_published_chapter` 仅作游标）；rev 不递增、action=publish（§3.2）。

### 1.2 `Status` 资产 vs `status` 字段

- **字段** `status`：每个资产实例上的生命周期标记。
- **类型** `Status`：项目级「当前跑到哪」的单例运行时状态（§2.1）。二者勿混用。

---

## 2. 类型目录

下列每型固定给出：`id` 约定 / 职责 / 最小字段 / 允许 status / 主属阶段 / 依赖。

阶段代号（与 phase-contracts 对齐）：

| code | 名称 |
|------|------|
| P1 | 蓝图 blueprint |
| P2 | 粗纲 rough-outline |
| P3 | 序列大纲 sequence-outline |
| P4 | 细纲 detail-outline |
| P5 | 章纲 chapter-outline |
| P6 | 正文 writing |
| * | 跨阶段 / 全程 |

---

### 2.1 Status

| 项 | 契约 |
|----|------|
| **type id** | `Status` |
| **实例 id** | 固定单例：`status_project`（每作品/工作区一个） |
| **职责** | 记录当前 mode、phase、阻塞点、上次 writeback、召回策略版本；供 protocol 路由 |
| **允许 status** | `draft` \| `review` \| `canon`（通常保持 `canon`；结构变更时短暂 `draft`） |
| **主属阶段** | `*` |
| **依赖** | 无硬依赖；软引用 `Manifest` |

**最小字段**

```yaml
id: status_project
type: Status
mode: idle | new_project | advance | write_unit | diagnose | change | learn
# 兼容别名（写回时归一）：new→new_project, continue→advance；idle=空档（scaffold G5 即合法）
phase: P1 | P2 | P3 | P4 | P5 | P6 | idle
phase_gate: pending | passed | failed | blocked
route: traditional | web    # 闭集；混合形态只写 flags.dual_track（scaffold §4 写入）
blockers:          # 空数组 = 可推进
  - { code: string, message: string, related_asset_ids: string[] }
active_unit:       # 当前写作/规划焦点，可空
  type: SceneBeat | ChapterPlan | ManuscriptUnit | null
  id: string | null
last_writeback:
  asset_id: string | null
  rev: integer | null
  at: datetime | null
load_policy_rev: integer    # 与 protocol 中召回策略版本对齐
flags:
  dual_track: traditional | web_serial | hybrid   # 须与 route 对齐（scaffold §4.2）
  knowledge_budget_default: integer
  critic_cadence: string    # critic 抽检节奏；默认 "every_5_chapters + volume_end"（phase-contracts §7）
  unattended_mode: boolean  # 默认 false；true = 无人值守降级：volume_checkpoint 改 agent_auto + pending_human_review 留痕后继续（§2.4）
web_serial:        # route=web 必填（运行细则见 web-serial-playbook §0.2）
  current_volume: string    # 如 vol_01；复合序列键 {volume_id, sequence_index} 的 volume 侧
  opening_scope: { volume_id, sequence_range, chapter_range }
  buffer: { target_chapters, ready_count, min_before_publish }
  serial_cursor: { last_published_chapter, next_write_chapter, next_plan_chapter }
  adopt_cursor: { last_digested_chapter }   # Adopt 旧稿消化进度（project-scaffold AD_3.5）
  last_critic_chapter: integer   # 最近一次 critic 抽检章号；落后 critic_cadence 周期即漏跑可检（phase-contracts §7.9）
  auto_promote: { p4_canon: bool, p4_canon_seed: bool, chapter_canon_on_gate_pass: bool, facts_upsert: bool }
    # 常任晋升授权：gate PASS 后自动升 canon / facts 入卷分片；route=web 默认全 true；配置变更须 Decision(user)
    # p4_canon_seed：P4 gate PASS 时 canon_root/canon_style 随 Character/WorldRule 一同升 canon（写 Decision(agent_auto)）
  auto_publish: boolean     # 默认 false（发布人批，支持「第 N–M 章」批量区间确认）；true 时行为协议见 web-serial-playbook §6.4
```

---

### 2.2 Canon

| 项 | 契约 |
|----|------|
| **type id** | `Canon` |
| **实例 id** | `canon_root`（主包）+ 分片 `canon_continuity_v{n}`（卷级连续性事实）+ `canon_style`（全书文风基准） |
| **职责** | 存放**不可轻易违背**的不变量与已锁定设定摘要；冲突裁决的高优先级源之一 |
| **允许 status** | `draft` → `review` → `canon` → `locked`；变更后相关切片可 `stale` |
| **主属阶段** | 起于 P1，全程维护 |
| **依赖** | 通常聚合自 `Blueprint`、`WorldRule`、`Character`、`Decision` 的已采纳结论 |

**最小字段（`canon_root`）**

```yaml
id: canon_root
type: Canon
invariants:                 # 硬约束，违反即 conflict；推翻/修改须 Decision(approved_by=user)
  - { id: string, statement: string, source_asset_ids: string[] }
theme:
  controlling_idea: string  # 主控思想（K-CONCEPT-013）
  counter_idea: string      # 反思想（K-CONFLICT-002）
  ending_mode: idealist | pessimist | positive_irony | negative_irony | unset
forbidden:                  # 明确禁止的走向/设定
  - string
open_questions: string[]    # 尚未裁决；不得假装已 canon
```

**分片约定 `canon_continuity_v{n}`（每卷一片；write_unit 召回当前卷片 + 按出场实体 id 检索历史片）**

```yaml
id: canon_continuity_v{n}
type: Canon
facts:                      # 已发生/已揭示的连续性事实（不再内嵌 canon_root）
  - { id: string, fact: string, entity_ids: string[], revealed_at: string, spoiler_level: int,
      superseded_by: string | null }   # 被 retcon 推翻时填 retcon_id；旧 fact 原文不删不改
retcon_notes:               # locked 资产向前兼容账本（不回改已发布正文）
  - { id, entity_ids: string[], affected_asset_ids: string[], old_fact, new_fact,
      forward_strategy: reconcile | fade_out | explicit_fix,   # 圆回 | 淡出 | 显式修正
      decision_id }
  # 纪律：retcon 落盘时必须在被推翻的旧 fact 上追加 superseded_by=<retcon_id>；
  # 实体检索命中带 superseded_by 的 fact 时必须连带装载对应 retcon_note，正文以 new_fact 为准
```

**实例约定 `canon_style`（全书文风基准）**：叙述人称/时态、句长基线、口癖黑名单、对话风格等；模板 `templates/style-card.md`；write_unit 必召回（protocol §4.2）。

---

### 2.3 Manifest

| 项 | 契约 |
|----|------|
| **type id** | `Manifest` |
| **实例 id** | `manifest_root`（根注册表）+ 卷分片 `manifest_units_v{n}` / `manifest_decisions_v{n}` |
| **职责** | 分片注册表：root 存项目元信息 + 单例/设计资产 entries + 分片指针；units 分片存该卷章级资产 entries；decisions 分片存该卷已完结（非 open）Decision entries |
| **允许 status** | 自身通常为 `canon`；损坏修复时 `draft` |
| **主属阶段** | `*`（任何 writeback 必 touch 所属实例） |
| **依赖** | 无；被所有类型依赖（注册意义） |

**最小字段（`manifest_root`）**

```yaml
id: manifest_root
type: Manifest
schema_rev: integer         # 对齐本文件 schema_rev
project:
  name: string              # 工作区显示名，非书名绑定逻辑
  created_at: datetime
entries: ManifestEntry[]    # 仅单例/设计资产：Status/Canon系/Blueprint/PlotSpine/SequenceMap系/Character/WorldRule/Thread/Recap；Decision 只留 open/active（可判定定义：status ∈ {draft, review, canon}；locked 长效裁决属例外——留 root 须 tags 标注 long_term，否则视为可迁）；非 open 迁 decision 分片
unit_shards: string[]       # 卷分片指针，如 [manifest_units_v1, manifest_units_v2, ...]
decision_shards: string[]   # Decision 卷分片指针，如 [manifest_decisions_v1, ...]；卷末 checkpoint 迁入，可空
```

**卷分片 `manifest_units_v{n}`**

```yaml
id: manifest_units_v{n}
type: Manifest
volume_id: vol_{n}
entries: ManifestEntry[]    # 仅该卷 SceneBeat / ChapterPlan / ManuscriptUnit
```

**卷分片 `manifest_decisions_v{n}`**

```yaml
id: manifest_decisions_v{n}
type: Manifest
volume_id: vol_{n}
entries: ManifestEntry[]    # 仅该卷已完结（非 open）的 Decision；卷末 volume_checkpoint 从 root 迁入
```

**装载纪律**：BOOT 只读 `manifest_root`（不读 decision 分片）；P5/P6/write_unit 轮加读**当前卷** units 分片；decision 分片仅 `change`/`diagnose`/审计轮按需加载（protocol §1.1/§4.2）；**禁止全分片装载**。每资产 entry 归属唯一（root 或某一分片）。

---

### 2.4 Decision

| 项 | 契约 |
|----|------|
| **type id** | `Decision` |
| **实例 id** | `decision_{yyyyMMdd}_{slug}` 或 `decision_{uuid_short}` |
| **职责** | 记录分歧裁决、用户覆盖、破 lock 授权、范围变更；供审计与冲突回放 |
| **允许 status** | `draft` \| `review` \| `canon` \| `locked` \| `archived`（生效中的裁决宜 `canon`/`locked`） |
| **主属阶段** | `*`（change / diagnose 高频） |
| **依赖** | 被裁决资产的 `id` 列表；可选关联 `Canon` |

**最小字段**

```yaml
id: decision_...
type: Decision
decision_type: conflict_resolve | user_override | unlock | scope_change | simple_change | deprecate
priority_basis: user_turn | decision | canon_invariant | higher_phase_lock | working
approved_by: user | agent_auto   # 必填；授权主体（级别表见下）
problem_summary: string
options_considered: string[]
chosen: string
affects_asset_ids: string[]
follow_up:
  mark_stale: string[]      # 必须标 stale 的下游 id
  sync_required: boolean
  block_phase_until: string | null
expires_at: datetime | null # 临时覆盖可过期
```

**授权级别表（`approved_by` 合法性；与 conflict-playbook 对齐）**

| 级别 | 允许的动作 |
|------|------------|
| 必须 `user` | unlock locked；砍 `must_not_drop` 线；推翻/修改 `Canon.invariants`；分卷模式 A/B 切换；弃档重开；开新卷确认（volume_checkpoint；`unattended_mode=true` 时降级为 agent_auto + `pending_human_review` 留痕）；publish 确认（默认人批；`auto_publish=true` 除外）；`auto_promote` / `auto_publish` / `unattended_mode` 配置变更 |
| 允许 `agent_auto`（自批即生效，须留痕） | scope_change（扩窗/远端占位细化/开新卷准备）；Thread 常规增删（非 must_not_drop）；gate PASS 后按 `auto_promote` 的晋升（p4_canon / p4_canon_seed / chapter_canon_on_gate_pass / facts_upsert）；`auto_publish=true` 时的顺序 publish（web-serial-playbook §6.4）；非 invariant 的 stale 风险接受；simple_change |

---

### 2.5 Blueprint

| 项 | 契约 |
|----|------|
| **type id** | `Blueprint` |
| **实例 id** | `blueprint_main`（单主蓝图；变体用 `blueprint_{variant}`） |
| **职责** | P1 产出：高概念、前提、类型定位、主控思想方向、人物/世界种子（K-CONCEPT-001~022 等） |
| **允许 status** | 全枚举；P2 启动门禁要求 ≥ `review`，建议 `canon` |
| **主属阶段** | P1（下游只读引用） |
| **依赖** | 无硬前置；可引用外部灵感笔记（非本 type 系统） |

**最小字段**

```yaml
id: blueprint_main
type: Blueprint
high_concept: string        # 传播向一句话
premise: string             # 创作向探索问题
genre:
  primary: string
  secondary: string[]
  web_serial_tags: string[] # 可空
  must_keep_conventions: string[]
  cliches_to_avoid: string[]
spine_intent:
  protagonist_desire: string
  opposing_force: string
  core_conflict_one_liner: string
controlling_idea_draft: string
ending_mode_tendency: idealist | pessimist | positive_irony | negative_irony | unset
element_seeds:              # 高概念元素初步清单
  - { category: string, text: string, tier: bronze | silver | gold | ssr }
cast_seeds:
  - { role: protagonist | antagonist | support, label: string, function: string }
world_seeds:
  era: string
  duration: string
  place: string
  conflict_scale: personal | interpersonal | societal | larger
  core_rules_draft: string[]
plot_vector:
  opening: string
  midpoint_direction: string
  ending_direction: string
```

---

### 2.6 PlotSpine

| 项 | 契约 |
|----|------|
| **type id** | `PlotSpine` |
| **实例 id** | `plotspine_main` |
| **职责** | P2 粗纲：**24 节点脊骨**（每节点仅 title + 一句话价值）+ 电缆/引线/支线骨架（K-CONCEPT-009~012, K-STRUCT-001~002） |
| **允许 status** | 全枚举；P3 门禁要求 ≥ `review` |
| **主属阶段** | P2 |
| **依赖** | `Blueprint`（min_rev 建议）；软依赖 `Canon`、`WorldRule` 草案 |

**最小字段**

```yaml
id: plotspine_main
type: PlotSpine
nodes:                      # 必须 24 条；id/index = 0..23（含 0=Hook）；禁止 scenes/beats
  - id: integer             # 0..23
    title: string           # 节点标题 ONLY
    value_one_liner: string # 一句话价值方向
    function: string | null # 建置/递进/转折/高潮/收束等
    anchor: null | hook | shock1 | growth1 | midpoint | growth2 | shock2 | growth3 | growth4 | climax | resolution
    # 允许数组：节点 12 可标 anchor: [midpoint, growth2]（枚举见 glossary §4.2）
cable:                      # 电缆：主线 + 搅合支线（亦可拆为 Thread 实例）
  mainline: string
  strands:
    - { id: string, name: string, sync_with_main: string, budget_ratio: number }
fuses:                      # 引线（亦可拆为 Thread.kind=fuse）
  - { id: string, hidden_info: string, plant_points: string[], reveal_point: string }
conflict_matrix:            # 可选：内心/人际/外部 × 幕或关键节点（非独立 AssetType）
  inner: string | null
  inter: string | null
  extra: string | null
volume_map:                 # 分卷映射（模式 B 必填）
  - { volume_id: string, theme: string, node_range: [int, int], element_ids: string[] }
  # 模式 B（每卷 seqmap_v{n}）：书级 24 节点降为规划资产——锚点 gate 只强制卷内 seqmap 锚点，
  # 书级锚点为 soft（缺失仅 warning 不 BLOCK）；远端节点可占位到「卷级主题一句话」
anti_goals: string[]        # 明确不做的情节
# 禁止字段: scenes[], beats[], chapters[], dialogue
```

**硬约束（P2 边界）**：`nodes.length == 24` 且覆盖 `0..23`；必保锚点位 `0,6,8,12,16,18,19,22,23`（模式 B 下书级锚点齐备降为 soft，见 volume_map 注）；**无任何场景级**内容。

---

### 2.7 SequenceMap

| 项 | 契约 |
|----|------|
| **type id** | `SequenceMap` |
| **实例 id** | 模式 A（单卷/传统全书）= 单实例 `seqmap_main`（视为 `vol_01`）；模式 B（分卷连载）= 每卷一实例 `seqmap_v{n}`，索引均为**卷内 0–23** |
| **职责** | P3：序列 0–23 填充（**含序列 0 Hook**）、事件摘要 + **场景列表**（非章纲、非节拍定稿） |
| **允许 status** | 全枚举；P4 门禁要求目标序列条目 ≥ `review` |
| **主属阶段** | P3 |
| **依赖** | `PlotSpine`；`Blueprint`；相关 `Thread` |

**最小字段**

```yaml
id: seqmap_main | seqmap_v{n}   # 模式 A 单实例视为 vol_01；模式 B 每卷一实例
type: SequenceMap
volume_id: string           # vol_{n}；复合序列键的 volume 侧
numbering: 0-23             # 常量说明：本实例必须覆盖卷内序列 0..23
sequences:
  - index: integer          # 卷内 0..23，0 = Hook
    name: string
    event_summary: string   # 本序列事件因果（非场景散文堆砌）
    dramatic_function: string   # 唯一名（废弃 narrative_function）
    value_shift: string     # 进入值 → 离开值；唯一名（废弃 value_arc）
    scenes:                 # 1–5 条；P3 核心产出；禁止写成 P4 节拍链
      - scene_id: string    # 格式 scene_v{v}_{s}_{nn}，与 SceneBeat id 同格式
        name: string
        goal: string
        driver: string      # 场景驱动者：谁的目标推动本场（P3 gate 检查）
        opposition: string
        value_start: string
        value_end: string   # 必须 ≠ value_start
        turn_hint: string
    conflict_layers:        # 内心 / 人际 / 外部
      inner: string | null
      inter: string | null
      extra: string | null
    thread_ids: string[]
    reveal_plan:            # 可选；洋葱层标签
      - { character_id: string, onion_layer: surface|behavior|emotion|belief|wound }
    status: AssetStatus     # 条目级 status，可细于文档级
coverage_check:
  has_seq0_hook: boolean
  missing_indices: integer[]
```

**硬约束**：每实例 `sequences` 逻辑全集为卷内索引 `0,1,...,23`；缺序必须出现在 `coverage_check.missing_indices`；**无 ChapterPlan 字段**；场景不得展开为定稿节拍（那是 P4 `SceneBeat`）。

---

### 2.8 SceneBeat

| 项 | 契约 |
|----|------|
| **type id** | `SceneBeat` |
| **实例 id** | `scene_v{v}_{s}_{nn}`（v=卷号，s=卷内序列 0–23，nn=序内序号；唯一格式，废弃 `S{seq}.{n}` 与 `scene_{slug}`） |
| **职责** | P4 细纲：场景级节拍、转折、人物压力点（K-STRUCT-008~019, K-CHAR-*） |
| **允许 status** | 全枚举 |
| **主属阶段** | P4（P5 拆章时只读） |
| **依赖** | 所属 `SequenceMap` 条目；出场 `Character`；触及 `Thread` |

**最小字段**

```yaml
id: scene_v{v}_{s}_{nn}
type: SceneBeat
sequence_ref: { volume_id: string, sequence_index: integer }  # 复合键；卷内 0..23，速记 v3:s12
order_in_sequence: integer
pov: string
location: string
time_marker: string | null
goal: string                # 场景目标（驱动目标唯一字段）
conflict:
  { opposition: string, stakes: string, escalation: string | null }   # 对抗 / 赌注 / 升压一句话
turning_point:
  { expectation: string, result: string, gap: string }   # 期望 vs 结果；gap 为 gate 必查（K-STRUCT-011）
outcome: string
value_start: string
value_end: string
beats:                      # 节拍列表（五级单元最底层之一）
  - { n: integer, action: string, reaction: string | null }
character_pressure:
  - { character_id: string, pressure: string, reveal_layer: surface | behavior | emotion | belief | wound }
thread_ops:
  - { thread_id: string, op: plant | advance | payoff | tangle }
exposition_ammo: string[]   # 解说转弹药要点（K-WRITE-002），可空
```

**洋葱五层**（与 glossary 一致，禁止改名）：`surface` 表象 / `behavior` 行为 / `emotion` 情感 / `belief` 信念 / `wound` 创伤。  
**场景六问自检**：以 **K-WRITE-008 源文为准**（本文件与模板均不内嵌复本）。

---

### 2.9 ChapterPlan

| 项 | 契约 |
|----|------|
| **type id** | `ChapterPlan` |
| **实例 id** | `chapter_{nnnn}`（四位**全局**章号，如 `chapter_0042`；废弃 `chapter_{vol?}_{nnn}`） |
| **职责** | P5：章节边界、钩子、信息/爽点投放、场景归并（K-WRITE-011~014） |
| **允许 status** | 全枚举；P6 写章前目标章 ≥ `review` |
| **主属阶段** | P5 |
| **依赖** | 一个或多个 `SceneBeat`；`SequenceMap`；可选 `Thread` |

**最小字段**

```yaml
id: chapter_{nnnn}          # 四位全局章号
type: ChapterPlan
chapter_no: integer         # 全局章号，与 id 一致
volume_no: integer | null
title_working: string | null
scene_ids: string[]         # 有序；scene_v{v}_{s}_{nn}
content_blocks:             # 内容块序列；type 闭集五值（unit_type 判定主导来源，contracts §0.4.1）
  - { type: dialogue | description | action | interior | exposition,
      summary: string, subtext: string | null }
word_count_target: integer | null   # route=web 默认 2000–4500 字（Status 可覆盖）
hooks:
  open: string | null
  close: string | null      # 章末钩子（网文强需求）
  close_type: string | null # 可选：悬念/危机/反转/期待 等
thread_ids: string[]        # 本章触及的 Thread（仅引用；埋/推/收明细唯记 Thread 账本）
# 信息揭示与爽点兑现统一记 serial_notes.payoff_entries（kind=reveal 等六枚举）；章级价值走向由场景 value 起止聚合，不在此重记
serial_notes:
  cliffhanger_level: 0 | 1 | 2 | 3
  payoff_density: low | mid | high
  payoff_entries:           # 爽点/信息增量账（纪律见 web-serial-playbook §7）
    - id: payoff_{chapter_no}_{n}
      kind: dopamine | upgrade | reveal | reversal | emotion | humor | other
      intent: string                  # 计划时一句话
      realized: bool | null           # P6 后回写
      thread_ids: string[]
      sequence_ref: { volume_id, sequence_index } | null
      onion_reveal: { character_id, layer } | null
```

---

### 2.10 Character

| 项 | 契约 |
|----|------|
| **type id** | `Character` |
| **实例 id** | `char_{slug}` |
| **职责** | 人物真值卡：欲望、洋葱五层、弧光、声纹、关系功能（K-CHAR-001~014） |
| **允许 status** | 全枚举；进细纲/正文的核心卡建议 ≥ `canon` |
| **主属阶段** | P2 种子 → P4 充实 → 全程维护 |
| **依赖** | `Blueprint.cast_seeds`；主题相关时引用 `Canon.theme` |

**最小字段**

```yaml
id: char_...
type: Character
name: string
role: protagonist | antagonist | secondary | tertiary | ensemble
desire: string
need: string | null
onion:                      # 固定五键，术语 SSOT（id=wound，zh=创伤）
  surface: string           # 表象
  behavior: string          # 行为
  emotion: string           # 情感
  belief: string            # 信念
  wound: string             # 创伤（禁止用 trauma 作键名）
arc:
  start_state: string
  pressure_design: string
  forced_choice: string | null
  end_state: string | null
  arc_type: change | steadfast | flat | unset
  milestones: [{ volume_id: string, milestone: string }]   # 按卷弧光里程碑（替代硬编码 seq8/12/16/19 对位）
masks: [{ context: string, mask: string }]   # 情境面具：独处/权威/亲人/敌人/极限压力等场合的表象差异
key_choices:                # 压力下的关键抉择（主角建议 ≥3；揭示 true_character；P4 充实）
  - { situation: string, choice: string, reveals: surface|behavior|emotion|belief|wound, pressure: low|mid|high|extreme }
relationships:
  - { target_id: string, relation: string, dramatic_function: string }
voice:                      # 声纹卡（结构化；废弃裸 voice_notes；方法见 K-CHAR-013）
  { tics: string[], sentence_style: string, taboo_words: string[], sample_line: string }
  # 口癖 / 句长节奏特征 / 该角色禁用词 / 标志性例句
secrets: string[]           # 对读者/对其他角色的信息差（召回时按防剧透纪律标注）
```

---

### 2.11 WorldRule

| 项 | 契约 |
|----|------|
| **type id** | `WorldRule` |
| **实例 id** | `world_{domain}`（如 `world_core`, `world_power`, `world_faction`） |
| **职责** | 世界不变量、代价、势力交互约束、战力运营（K-WORLD-001~024） |
| **允许 status** | 全枚举；影响情节的硬规则应升 `canon`/`locked` |
| **主属阶段** | P1–P2 建立，全程引用 |
| **依赖** | `Blueprint.world_seeds`；可提升条目至 `Canon.invariants` |

**最小字段**

```yaml
id: world_...
type: WorldRule
domain: core | culture | power | faction | geography | other
rules:
  - { id: string, statement: string, hardness: hard | soft, cost: string | null }
power_system:
  summary: string | null
  sanderson_level: 1 | 2 | 3 | na   # 可知性/代价/延伸（K-WORLD-005）
  upgrade_modes: string[]           # 可空，K-WORLD-014
factions:
  - { id: string, name: string, goal: string, pressure_on_protagonist: string }
concentric:
  core: string                      # 法则层
  middle: string                    # 文化/历史
  outer: string                     # 日常表象
taboos: string[]                    # 世界内不可轻易打破之事
power_anchors:                      # 可选扩展（domain=power 建议必填）：战力锚定表（K-WORLD-022；落表 templates/world-setting.md §2.3）
  - { tier: string, sure_win: string, contested: string, sure_lose: string, benchmark_figure: string, cost: string | null }
```

---

### 2.12 Thread

| 项 | 契约 |
|----|------|
| **type id** | `Thread` |
| **实例 id** | `thread_{slug}` |
| **职责** | 跨序列/跨章的悬线、伏笔、支线状态机；支撑电缆收束与引线揭示 |
| **允许 status** | 全枚举；已收束可 `locked` 或 `archived` |
| **主属阶段** | P2 登记 → P3–P6 推进 |
| **依赖** | 可选挂靠 `PlotSpine.fuses` / `strands` |

**最小字段**

```yaml
id: thread_...
type: Thread
kind: fuse | subplot | relationship | mystery | promise | other
statement: string
state: planted | active | tangled | payoff_ready | paid_off | dropped
volume_scope: string[]      # 活跃卷 id 列表；write_unit 只召回 active ∩ 当前卷（或 waypoint 命中）
waypoints: [{ volume_id: string, intent: string }]   # 跨卷弧路标
plant_at:
  sequence_ref: { volume_id, sequence_index } | null   # 复合键
  scene_id: string | null
  chapter_id: string | null
advance_log:                # 轮转：仅保留最近 10 条；滚出窗口的条目于卷末 volume_checkpoint 归并进 history_digest
  - { at: string, note: string }
history_digest: string | null   # 历史摘要：每卷一行（卷末 checkpoint 归并），非一行全史
payoff:
  planned_at: { volume_id, sequence_index } | null     # 复合键
  actual_at: string | null      # 实际落点（chapter id）
  description: string | null
owner_character_ids: string[]
must_not_drop: boolean      # 砍此线须 Decision(approved_by=user)
```

**召回规则**：`state ∈ {paid_off, dropped}` 的线**移出 active 召回集**（仍可按 id 显式检索）。

---

### 2.13 ManuscriptUnit

| 项 | 契约 |
|----|------|
| **type id** | `ManuscriptUnit` |
| **实例 id** | `ms_{nnnn}`（四位全局章号，与 `chapter_{nnnn}` 对齐） |
| **职责** | P6 正文单元：与 `ChapterPlan` 对齐的可写可改稿件元数据 + 正文指针 |
| **允许 status** | `draft` \| `review` \| `canon` \| `locked` \| `stale` \| `archived` |
| **主属阶段** | P6 |
| **依赖** | 对应 `ChapterPlan`；场景事实依赖 `SceneBeat` / `Character` / `WorldRule` |

**最小字段**

```yaml
id: ms_{nnnn}
type: ManuscriptUnit
chapter_plan_id: string
word_count: integer
body_uri: string | null     # adapter 解析的正文位置；协议可空但 P6 writeback 后应有值
summary_after: string       # 必填（P6 writeback 后）：写后摘要，供续写召回与 recap 滚动
continuity_delta:           # 必填（P6 writeback 后；可为空数组）：本章造成的连续性变更
  - { fact: string, entity_ids: string[], spoiler_level: int, upsert_to_canon: boolean | null }
    # entity_ids/spoiler_level 与 canon_continuity 分片检索键对齐；upsert_to_canon 可选（null=按 auto_promote.facts_upsert）
hooks_realized:
  open: boolean | null
  close: boolean | null
evidence_checks:            # 证据制自检（替代自评 bool 矩阵）：六问/craft/canon 冲突/泄密逐条
  - { claim: string, quote: string, note: string }   # quote=正文摘引 ≤30 字；note=一句论证
issues: string[]            # 自检问题列表
```

---

### 2.14 工作记录（非 AssetType，落点约定）

下列产物**不是**独立 AssetType，禁止注册进 type 枚举；但必须有可检索落点，否则 `critique_unmerged` 等机制无法执行：

| 记录 | 生产者 | 落点 | 可检索性要求 |
|------|--------|------|--------------|
| `DiagnosisReport` | diagnose | `notes/diagnosis/{id}.md`，或作为 `Decision` 草案附件 | 报告内列 `asset_refs` + `k_ids`；若建议改设定 → `next_intent_hint=change` |
| `Critique`（批评/反馈/critic 抽检报告） | revise 流程 ①、外部意见登记、critic pass | `notes/critiques/{id}.md` | **必须**含 `target_asset_ids`、`merged: true|false`、`merge_decision: dec_id|null`；未 merged = `critique_unmerged` 检测源（conflict-playbook §3.1） |
| `PayoffLog`（爽点/信息增量） | P5/P6（route=web） | `ChapterPlan.serial_notes.payoff_entries[]`（正式 schema 见 §2.9）/ `ManuscriptUnit` 旁路字段 | 见 web-serial-playbook §7 |
| `ConflictRecord`（冲突处置记录） | conflict-playbook | `notes/conflicts/{id}.md` | 含 taxonomy 分类、涉及 asset_refs、处置结果（`decision_id` 或 simple_change 留痕） |

规则：`notes/**` 默认**不进** Manifest 召回集（无执行权，对齐 C7）；Critique 经 `Decision` accept 后其结论才进入 canon 链路，并回写 `merged=true` + `merge_decision`。

---

### 2.15 Recap

| 项 | 契约 |
|----|------|
| **type id** | `Recap` |
| **实例 id** | `recap_book` \| `recap_vol_{n}` \| `recap_state` |
| **职责** | 分层滚动摘要：长程记忆读模型；write_unit 必召回（protocol §4.2） |
| **允许 status** | `draft` \| `review` \| `canon`（常驻 `canon`，随章滚动更新） |
| **主属阶段** | P6 写回维护；`recap_vol_{n}` 产于 volume_checkpoint |
| **依赖** | `ManuscriptUnit.summary_after`；`canon_continuity_v{n}` |

**最小字段**

```yaml
id: recap_book | recap_vol_{n} | recap_state
type: Recap
kind: book | volume | state
body: string                # book ≤800字滚动书摘；volume ≤1500字/卷；state ≤600字现状快照
covers_chapters: [int, int]
```

`recap_state` 要点字段化：主角境界/位置/持有物/关键关系现状/当前目标/未解危机。  
**维护纪律**：P6 每章写回后更新 `recap_state` + 滚动追加 `recap_book`；卷末 volume_checkpoint 生成 `recap_vol_{n}`；scaffold 建空壳 `recap_state`。模板 `templates/recap.md`。

---

## 3. Manifest 条目 Schema

### 3.1 `ManifestEntry`

每条注册记录的**最小且完备**字段（瘦身版：无 `recall_priority` / `content_hash` / `edges`）：

```yaml
# ManifestEntry
asset_id: string            # = 资产 id，全局唯一
type: AssetType
rev: integer
status: AssetStatus
title: string
updated_at: datetime
uri: string | null          # storage adapter 填写
depends_on:
  - { type: string, id: string, min_rev?: integer }
tags: string[]
phase_home: P1 | P2 | P3 | P4 | P5 | P6 | "*"
```

### 3.2 注册 / 更新伪代码

```
function manifest_register(entry: ManifestEntry):
  shard = owning_manifest(entry)   # root 或 manifest_units_v{n} / manifest_decisions_v{n}，归属唯一
  assert entry.asset_id not in shard.entries or intent == upsert
  shard.entries[entry.asset_id] = entry
  shard.rev += 1

function manifest_touch(asset_id, rev, status, uri?=null, action?=null):
  e = find_entry(asset_id) || error(NOT_REGISTERED)
  e.rev = rev              # 例外：action=publish 时资产 rev 不递增，只改 status（升 locked，唯一默认）
  e.status = status
  e.updated_at = now()
  if uri: e.uri = uri
  owning_manifest(e).rev += 1   # manifest 自身 rev 照常递增

function manifest_query(filter):
  # filter: { types?, status_in?, phase_home?, tag?, stale_only?, volume? }
  return entries where match(filter)   # 只在 root + 当前卷分片内查
```

### 3.3 不变量

| ID | 规则 |
|----|------|
| AT1 | 任意 `writeback` 前：`asset_id` 已注册于 root 或所属卷分片（归属唯一，不得双登记） |
| AT2 | `entries[].rev` 必须与资产信封 `rev` 一致；不一致 → `version_skew` |
| AT3 | 删除资产：先 `status=archived`，再可选物理归档；禁止裸删导致悬空 depends_on |
| AT4 | `Status`/`Manifest` 自身也占 entry（自描述；分片登记于 root.unit_shards / decision_shards + 自身 entry） |

---

## 4. 类型依赖总图（逻辑）

```
Manifest (registry)
    ▲
Status ─────────────────────────────► (routes all)
    │
Blueprint ──► PlotSpine ──► SequenceMap ──► SceneBeat ──► ChapterPlan ──► ManuscriptUnit
    │              │              │              │              │
    ├──────────────┼──────────────┼──────────────┤              │
    ▼              ▼              ▼              ▼              │
Character     WorldRule       Thread         Thread            │
    │              │              │                             │
    └──────────► Canon ◄──────────┘                             │
                   ▲                                            │
                   └──────── Decision ──────────────────────────┘
```

箭头含义：`A ──► B` = B 的 gate/最小字段通常 **depends_on** A。

---

## 5. 阶段 × 产出类型矩阵

| 阶段 | 主产出 type | 升格目标 status | 同时维护 |
|------|-------------|-----------------|----------|
| P1 | `Blueprint` | `review`/`canon` | `Status`, `Manifest`, `Canon` seed（canon_root 充实 + canon_style，gate PASS 自检升 ≥ `review`）, `Character` 种子, `WorldRule` 种子 |
| P2 | `PlotSpine` | `review`/`canon` | `Thread`, `Character`, `WorldRule`, `Canon` |
| P3 | `SequenceMap` | 条目级 `review`+ | `Thread` 推进 |
| P4 | `SceneBeat` (+ 充实 `Character`) | `review`+；gate PASS 后按 `auto_promote.p4_canon` 升 canon（canon_root/canon_style 按 `p4_canon_seed` 同升） | `Thread` |
| P5 | `ChapterPlan` | `review`+ | `serial_notes.payoff_entries` |
| P6 | `ManuscriptUnit` | `draft →(自检) review →(gate PASS 按 auto_promote.chapter_canon_on_gate_pass) canon（存稿）→(publish) locked（已发布）` | `canon_continuity_v{n}` facts/retcon, `Thread` payoff, `Recap`(state/book) |

---

## 6. 召回提示

按 intent 的召回表 **SSOT 见 `protocol.md` §4.2**（本文件不再复制；旧版此处的表已删除）。默认排除 `status=archived`；`paid_off/dropped` 的 Thread 出 active 集（§2.12）。

---

## 7. 校验清单（Agent 自检）

```
[ ] 新资产是否已 manifest_register（root 或所属卷分片，归属唯一）？
[ ] status 是否在六值枚举内？
[ ] SequenceMap 每实例是否声明卷内 0..23 且 has_seq0_hook？
[ ] Character.onion 是否五键 surface/behavior/emotion/belief/wound（zh=表象/行为/情感/信念/创伤）？
[ ] PlotSpine.nodes 是否 24 条覆盖 0..23 且无场景级字段（模式 B 书级锚点缺失仅 warning）？
[ ] 跨资产序列引用是否用复合键 {volume_id, sequence_index}（禁裸 int）？
[ ] chapter/ms id 是否四位全局章号（chapter_{nnnn} / ms_{nnnn}）；scene id 是否 scene_v{v}_{s}_{nn}？
[ ] 是否误把 ProseUnit/ThreadMap 注册为独立 type（应归一）？
[ ] locked/archived 改写是否有 Decision（approved_by 级别合法）或用户当轮指令？
[ ] writeback 后是否 touch Manifest 且 rev 一致（publish=touch，rev 不递增）？
[ ] 上游 rev 提升后未发布下游是否标 stale；locked 下游是否改走 retcon_note？
[ ] P6 writeback 后 summary_after/continuity_delta/evidence_checks 是否已填、recap_state 是否已更新？
```

---

## 附录 A. 可选 Filesystem Storage Adapter（非强制）

> 协议层**不依赖**本附录。仅当工作区选择「单库多文件」落地时参考。  
> **禁止**将下列目录名写进业务 if/else；仅 adapter 配置使用。

### A.1 建议映射（可改）

| type | 建议相对路径模式 |
|------|------------------|
| Status | `runtime-state/status.yaml` |
| Manifest | `runtime-state/manifest_root.yaml` + `runtime-state/manifest_units_v{n}.yaml` / `manifest_decisions_v{n}.yaml` |
| Canon | `canon/{id}.md`（canon_root / canon_style / canon_continuity_v{n}；style 用 `templates/style-card.md` 起草） |
| Decision | `decisions/{id}.md` |
| Blueprint | `design/blueprint.md` |
| PlotSpine | `design/plot_spine.md` |
| SequenceMap | `design/sequence_map_v{n}.md`（模式 A 单文件亦可） |
| SceneBeat | `design/scenes/{id}.md` |
| ChapterPlan | `design/chapters/{id}.md` |
| Character | `cast/{id}.md` |
| WorldRule | `world/{id}.md` |
| Thread | `threads/{id}.md` |
| ManuscriptUnit | `manuscript/{id}.md` |
| Recap | `recaps/{id}.md`（recap_book / recap_vol_{n} / recap_state；模板 `templates/recap.md`） |

> 校验工具：skill 侧 `tools/validate.py --project DIR` 可对上述落地做机检（工具非资产，不注册 Manifest）。

### A.2 Adapter 接口（逻辑）

```
interface StorageAdapter {
  resolve(type, id) -> uri
  load(uri) -> AssetEnvelope + body
  save(uri, asset) -> void
  list(type?) -> ManifestEntry[]  // 可与 Manifest 对账
}
```

对账规则：磁盘存在但 Manifest 无条目 → `orphan`（须 register 或忽略）；Manifest 有条目但磁盘无 → `missing`（`version_skew` / block）。

### A.3 非目标

- 不规定 VCS 策略  
- 不绑定任何具体作品仓库布局  
- 不要求 YAML/MD 二选一；envelope 可 frontmatter，body 可散文

---

## 附录 B. 与知识块的引用边界

| 资产行为 | 允许 | 禁止 |
|----------|------|------|
| 字段注释中写 `K-CHAR-004` | ✓ | 粘贴洋葱理论长文 |
| gate 失败时提示查阅 `K-STRUCT-003` | ✓ | 在资产文件内重定义 23 序列 |
| 用知识块指导如何填最小字段 | ✓ | 用知识块 ID 替代资产 id |

---

## 附录 C. 快速类型索引

| type | 单例? | 主阶段 | 关键枚举/约束 |
|------|-------|--------|----------------|
| Status | 是 | * | mode/phase（含 idle）+ web_serial |
| Manifest | root + 卷分片（units/decisions） | * | entries[] + unit_shards/decision_shards |
| Canon | root + continuity 分片 + style | * | invariants / facts / retcon_notes |
| Decision | 否 | * | decision_type + approved_by |
| Blueprint | 主单例 | P1 | high_concept |
| PlotSpine | 主单例 | P2 | nodes 0–23 + cable/fuses（anchor 可数组） |
| SequenceMap | 模式 A 单例 / 模式 B 每卷 | P3 | 卷内 0–23 + scenes[] |
| SceneBeat | 否 | P4 | sequence_ref 复合键 |
| ChapterPlan | 否 | P5 | hooks{open,close,close_type?} + content_blocks 五型 + payoff_entries |
| Character | 否 | P2–P6 | onion 五键（wound=创伤）+ voice 声纹卡 |
| WorldRule | 按 domain | P1–P2 | hard/soft rules |
| Thread | 否 | P2–P6 | state 机 + volume_scope/waypoints |
| ManuscriptUnit | 否 | P6 | body_uri + evidence_checks |
| Recap | 三实例 | P6/卷末 | kind: book/volume/state |

---

**文档版本**：`asset-types` schema_rev 3  
**变更规则**：新增 type 或改最小字段必须 bump `schema_rev`，并同步 `phase-contracts` / `protocol` 的引用面。

**修订**

| schema_rev | 说明 |
|-----------:|------|
| 1 | 初版类型系统（13 型 + Manifest 单例） |
| 2 | +`Recap` 类型；Manifest/Canon 分片（root + `*_v{n}`，Entry 删 recall_priority/content_hash/edges）；复合序列键 `sequence_ref` 与 id 约定（scene_v{v}_{s}_{nn} / chapter_{nnnn} / ms_{nnnn}）；locked=已发布不 stale（retcon_notes）+ publish=touch 不递增 rev；Status 补 idle/critic_cadence/web_serial 全量（current_volume/auto_promote/adopt_cursor/auto_publish）；Decision +approved_by 与授权级别表；Character +voice/milestones/masks/key_choices；Thread +volume_scope/waypoints/轮转；ManuscriptUnit +evidence_checks、summary_after/continuity_delta 必填；ChapterPlan hooks.close_type + payoff_entries；SequenceMap 双模式 + driver；新增字段/枚举级废弃别名表；tier 补 gold；召回表改指针 protocol §4.2；不变量 M→AT |
| 3 | schema 合流（V1 复检残差清零）：SceneBeat `conflict{opposition,stakes,escalation}`/`turning_point{expectation,result,gap}` 收编模板对象形；ChapterPlan 删 info_reveal/payoff_ids/emotional_arc、+thread_ids（payoff_entries 统一承载）；Character masks.mask / key_choices 对象数组；continuity_delta +entity_ids/spoiler_level；WorldRule +power_anchors 可选扩展；retcon forward_strategy 英文枚举 |
| 3（2026-08-13 修复轮；schema_rev 按修复决策书钉 3，正文宣称同步对齐） | publish=locked 唯一默认（canon=已过 gate 存稿；P6 状态链 §5 与 playbook/contracts 逐字一致）；draft→stale 边 + resync 恢复原 status；别名表 +continuity_facts→facts / narration→exposition / emotion(unit_type)→interior；facts +superseded_by、retcon_notes +entity_ids 与连带装载纪律；Manifest +`manifest_decisions_v{n}`/decision_shards（root 只留 open/active Decision，BOOT 不读）；auto_promote +p4_canon_seed；Status flags +unattended_mode、web_serial +last_critic_chapter；授权表 user 行 +开新卷确认/publish 确认/配置变更三键；ChapterPlan +content_blocks 五值闭集；Thread history_digest 改每卷一行；§5 P1 行补 Canon seed/canon_style；第三波收尾（V1 复检修正：冷启动条件行/六件套允许集/小节指针/编号/口径对齐） |
