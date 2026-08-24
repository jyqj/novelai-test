# Conflict Playbook — 分歧与变更裁决协议

> **定位**：Agent 可执行的变更/冲突工程协议（非文学理论）。  
> **依赖**：`runtime/glossary.md`（术语 SSOT）、`runtime/asset-types.md`（类型与 status）、`runtime/protocol.md`（召回/回写/阻断）。  
> **知识引用**：仅按需拉 K-xxx ID，不复制理论正文。  
> **禁止**：绑定具体书名、角色名、作品目录作为主规范。

---

## 0. 总览

```
detect → classify → decide → record(Decision) → mark_stale(deps) → sync | block
```

| 阶段 | 职责 | 产出 |
|------|------|------|
| `detect` | 发现不一致、漂移、双源、未合并批评 | ConflictCandidate |
| `classify` | 归入 taxonomy + 严重度 | ConflictRecord |
| `decide` | 按优先级栈裁决 | Decision 草案 |
| `record` | 固化 Decision 资产 | Decision (canon/review) |
| `mark_stale` | 标记依赖资产过期 | status=stale + stale_reason |
| `sync \| block` | 同步下游或阻断推进 | SyncPlan / BlockGate |

**硬规则**：
1. 未分类不得静默覆盖任何 `canon` / `locked` 资产。
2. 未写 Decision 不得批量改多类型资产。
3. `working` / 批评稿默认**无执行权**，须经 Decision 合并后才进入 canon 链路。
4. status 枚举仅允许：`draft | review | canon | locked | stale | archived`。

### 0.1 simple_change 短路（轻量层级）

任何变更**先跑本判定，再决定是否进完整流水线**（判定顺序固定）：

```
IF 目标未发布（status != locked）
   AND 不触 Canon.invariants
   AND 不砍 must_not_drop Thread
   AND 不追溯任何 locked 章的既成事实（只影响未来章）:
  → simple_change：
      写 Decision(approved_by=agent_auto) 留痕；
      仅对直接依赖（依赖图一跳）mark_stale，免全矩阵扫描；
      懒同步：标记后允许推进，写到受影响单元时再局部 resync
ELSE → 完整流水线 detect → classify → decide → record → mark_stale → sync|block
```

四条件任一不满足**或存疑**，一律走完整链；触及 locked 章既成事实的变更走完整流水线并落 `retcon_note`（§5.1 规则 6/7）；simple_change 仍受硬规则 1–4 约束。

---

## 1. Taxonomy（分歧分类）

| code | 中文名 | 定义 | 典型信号 | 默认严重度 |
|------|--------|------|----------|------------|
| `vertical_drift` | 纵向漂移 | 上下游阶段/抽象层级之间陈述不一致（高层约束 vs 低层展开） | Blueprint/Canon 与 SequenceMap/ChapterPlan 矛盾；主控思想与场景选择相悖 | high |
| `lateral_conflict` | 横向冲突 | 同层并列资产互相矛盾（角色 A vs 角色 B；WorldRule vs Character 能力） | 同一事实两套说法；势力动机互斥却无解释 | high |
| `version_skew` | 版本错位 | 同 type 多 rev/多副本，或 Manifest 指针与正文 rev 不一致 | 双文件 SSOT 不明；rev 回退；引用旧 rev 写作 | medium |
| `intent_gap` | 意图缺口 | 用户当轮意图与既有 Canon/计划未对齐，或任务目标未写入任何资产 | 「这次只改 X」但实际触达 Y；目标无 Decision/Thread | medium–high |
| `critique_unmerged` | 批评未合并 | 诊断/评审结论存在，但未回写到目标资产，仍按旧 canon 执行 | critique 文件有结论、目标 asset 无 rev 变更 | medium |

### 1.1 复合分类

一条冲突可挂 **primary + secondary**：

```yaml
taxonomy:
  primary: vertical_drift
  secondary: [critique_unmerged, version_skew]
```

裁决以 `primary` 驱动默认动作；`secondary` 进入 impact 与 stale 范围计算。

### 1.2 非冲突（勿误报）

| 现象 | 处理 |
|------|------|
| 仅措辞差异、语义等价 | 记 note，不升 Decision |
| `draft` 内自我探索未声称覆盖 canon | 忽略，直到 promote |
| 知识块 K-xxx 与项目 canon 不同 | **知识永不覆盖项目资产**；仅作方法参考 |
| glossary 术语 vs 旧文档别名 | 以 glossary 为准，开 `version_skew` 或术语修正任务，不改故事事实 |

### 1.3 判定序（前三类的边界裁决）

按序执行，先命中先得（落选维度可进 `secondary`）：

```
① 查 rev 指针：任一方引用 rev != Manifest 指针 rev → version_skew
② 查阶段序（§2.1）：双方资产 order 不同     → vertical_drift
③ 同 order                                  → lateral_conflict
```

`intent_gap` / `critique_unmerged` 由触发源直判（当轮意图对照 / 未合并批评），不入此序。

**Character 归层按字段路径**（同 type 跨 order 2/4 的唯一裁决）：
- 骨架字段（order 2）：`name / role / desire / need / relationships / arc.start_state / arc.arc_type`
- 洋葱展开（order 4）：`onion.*`、`masks[]`、`voice.*`、`secrets`、`key_choices[]`、`arc.{milestones,pressure_design,forced_choice,end_state}`

字段清单以 asset-types §2.10 为准；一次变更跨两层 → 按 order 2 归层。

---

## 2. 优先级栈（Priority Stack）

裁决时自上而下，**高者胜**；同级再比 `locked > canon > review > draft`，再比 `rev` 新者胜（若栈允许）。

```
P0  user_turn_intent          # 当轮用户显式指令（含「强制/覆盖/以我为准」）
P1  Decision.canon            # 已 canon/locked 的历史裁决
P2  Canon.invariant           # 不变量：主控思想、核心前提、硬世界规则
P3  higher_locked_phase       # 更高锁定阶段资产（见阶段序）
P4  peer_canon                # 同层 canon（需 lateral 消解）
P5  lower_phase_or_working    # 下游展开、working、critique、draft
P6  knowledge_readonly        # K-xxx 只读服务，永不作事实源压过项目
```

### 2.1 阶段序（higher = 更抽象/更先锁定）

用于 `P3` / impact 方向（数字越小越高层）：

| order | phase_id | 典型资产 types |
|------:|----------|----------------|
| 1 | blueprint | Blueprint, Canon(invariant 子集) |
| 2 | rough_outline | PlotSpine, Thread(主), WorldRule(框架), Character(骨架) |
| 3 | sequence_outline | SequenceMap (序列 0–23，含序列 0 Hook) |
| 4 | detail_outline | SceneBeat, Character(洋葱展开), Thread(支) |
| 5 | chapter_outline | ChapterPlan |
| 6 | prose | ManuscriptUnit（强制注册 type） |

**纵向默认**：高层 `locked/canon` 约束低层；低层发现高层错误 → 升 `vertical_drift`，**不得**静默改高层，须 Decision。

### 2.2 栈冲突速查

| 冲突方 A | 冲突方 B | 默认胜方 | 备注 |
|----------|----------|----------|------|
| user_turn_intent | 任意 | A | 若改 invariant，必须 Decision + 用户确认 |
| Decision.canon | peer_canon | Decision | 除非 Decision 被 supersede |
| Canon.invariant | SequenceMap | invariant | 序列让步或升级改 invariant |
| locked 高层 | draft 低层 | 高层 | 低层标 stale 或改写 |
| critique | canon | canon | 直至 Decision 合并 |
| 两份 peer_canon | — | block | 强制 Decision，禁静默选边 |
| knowledge K-xxx | 项目资产 | 项目 | 知识可提示，不可覆盖 |

---

## 3. 流水线契约

### 3.1 detect — 冲突候选

**触发源**：
- 写入/晋升资产前的一致性扫描
- mode=`diagnose` / `change` 的强制扫描
- gate 失败回传的 inconsistency 列表
- 用户显式「有冲突/对不上」

**ConflictCandidate 最小字段**：

```yaml
id: cc_<ulid>
source: gate | scan | user | write_hook
signals:
  - path_or_ref: <asset_ref>
    claim: "<短陈述>"
  - path_or_ref: <asset_ref>
    claim: "<矛盾陈述>"
touched_types: [Character, SequenceMap]   # asset-types 枚举
touched_phases: [sequence_outline, detail_outline]
user_intent_snippet: "<可选，当轮意图摘要>"
```

**检测启发式（可执行）**：

```
FOR each write/promote target T:
  load recall set R per protocol (assets first, budget)
  IF T.claims contradict any r in R where status in {canon, locked}:
    emit candidate
  IF Manifest.pointer(T).rev != T.rev:
    emit version_skew candidate
  IF exists Critique targeting T.id AND Critique.merged != true:
    emit critique_unmerged candidate
  IF user_intent requires change set C AND planned edits ⊄ C:
    emit intent_gap candidate
```

> `Critique` 不是 AssetType；其登记落点与 `merged` / `merge_decision` 字段契约见 `asset-types.md` **§2.14 工作记录**（`notes/critiques/{id}.md`）。批评的采纳/驳回走 revise 复合流程（protocol §2.4）：逐条 Decision 后回写 `merged=true`。

### 3.2 classify — 归类与严重度

```yaml
id: cr_<ulid>
candidate_id: cc_<ulid>
taxonomy:
  primary: vertical_drift | lateral_conflict | version_skew | intent_gap | critique_unmerged
  secondary: []
severity: low | medium | high | critical
scope:
  types: []
  asset_ids: []
  phases: []
  sequences: { volume_id: "", indices: [] }   # 复合键（速记 v3:s12）；卷内编号 0-23，可选
blocking: true | false   # critical/high 纵向或同层双 canon 默认真
rationale: "<一句话>"
```

ConflictRecord 落盘 `notes/conflicts/{id}.md`（工作记录，非 AssetType，契约见 asset-types §2.14；默认不进召回集）。

**严重度规则**：

| 条件 | severity |
|------|----------|
| 触及 `Canon.invariant` 或 `locked` | critical / high |
| 双 `canon` 同事实互斥 | high + blocking |
| 仅 `draft` 内 | low |
| critique 未合并但不阻断当章 | medium，blocking=false 可先记 |
| version_skew 且写作已用旧 rev | high |

### 3.3 decide — 裁决

按 §2 优先级栈计算 `winner` / `loser` / `action`。

```yaml
winner_ref: <asset_ref | user_intent | decision_ref>
loser_refs: [<asset_ref>...]
action: keep_winner | merge | rewrite_loser | supersede_decision | split_scope | escalate_user
requires_user_confirm: true | false
```

**默认动作表**：

| primary | 默认 action | requires_user_confirm |
|---------|-------------|------------------------|
| vertical_drift | rewrite_loser（低层）或 escalate（若证伪高层） | 改高层时 true |
| lateral_conflict | merge 或 escalate_user | 双 canon 时 true |
| version_skew | keep 高 rev + 指针校正；或 keep locked 指针 | 丢弃已发布 rev 时 true |
| intent_gap | 对齐范围：缩编辑集或新 Decision 扩 scope | 扩 scope 触 invariant 时 true |
| critique_unmerged | merge（采纳）/ keep_winner（驳回）+ 标记 merged | 驳回 high 级批评时建议 true |

### 3.4 record — 写入 Decision

必须落为 **Decision** 资产（见 §4 模板），不得仅会话口述。

**自动门（正式定义）**：`Decision.approved_by = agent_auto` **且**该动作落在授权级别表的 `agent_auto` 行内（级别表以 asset-types §2.4 为准，此处不重抄）。表列 `user` 级动作（unlock、砍 `must_not_drop`、动 `Canon.invariants` 等）必须 `approved_by=user`。

- 新裁决：`status=review`，用户确认或自动门通过后 → `canon`
- 覆盖旧裁决：新 Decision `supersedes: dec_xxx`，旧 Decision → `archived` 或保留并标 `superseded_by`
- `locked` Decision 仅 P0 + 显式 unlock 可动

### 3.5 mark_stale — 依赖过期

```
impact = IMPACT_MATRIX[changed_type] ∪ Decision.impact_extra
FOR each asset A in impact where A.id != winners:
  IF A.status in {canon, review, draft}:
    A.status = stale
    A.stale_reason = {
      decision_id, taxonomy_primary, summary, since_rev
    }
  IF A.status == locked:              # 已发布/冻结，不参与 stale 传播
    DO NOT mark stale
    IF 变更波及其内容事实（如已发布 ManuscriptUnit）:
      write retcon_note → canon_continuity_v{n}   # 见 §5.1 规则 6
    ELIF 必须改写 locked 本体:
      emit unlock_request（Decision, approved_by=user）
```

Manifest：touch 全部受影响资产（entry 的 rev/status 与信封同步）；不写入 Manifest 不存在的统计/索引字段。

### 3.6 sync | block

| 出口 | 条件 | Agent 行为 |
|------|------|------------|
| `sync` | blocking=false 或 Decision 已 canon 且 winner 已写 | 按 SyncPlan 改写 loser/下游；清 stale 当内容对齐 |
| `block` | blocking=true 且未决 / 缺用户确认 / locked 无 unlock | 停止 advance/write_unit；返回 BlockGate |

**BlockGate 最小形状**：

```yaml
gate: conflict_unresolved
conflict_id: cr_<ulid>
decision_id: dec_<ulid> | null
blocking_reasons: ["dual_canon", "invariant_touch", "await_user"]
allowed_modes: [diagnose, change]   # 禁止无裁决的 advance/write_unit
next_actions:
  - "填写 Decision 模板"
  - "用户确认 winner"
  - "执行 sync 后重跑 gate"
```

---

## 4. Decision 模板

写入资产 type=`Decision`。字段为契约；正文可用 markdown 包裹同一 YAML 头。

```yaml
# === Decision header (required) ===
type: Decision
id: dec_<ulid>
rev: 1
status: draft | review | canon | locked | stale | archived
title: "<短标题：改了什么>"
created_at: <iso8601>
updated_at: <iso8601>
supersedes: null | dec_<ulid>
superseded_by: null | dec_<ulid>
approved_by: user | agent_auto       # 必填；自动门定义见 §3.4

# === 冲突溯源 ===
conflict:
  conflict_id: cr_<ulid>
  taxonomy:
    primary: vertical_drift | lateral_conflict | version_skew | intent_gap | critique_unmerged
    secondary: []
  severity: low | medium | high | critical
  summary: "<冲突一句话>"

# === 优先级应用结果 ===
priority_applied:
  winner_rank: P0 | P1 | P2 | P3 | P4 | P5 | P6
  winner_ref: "<user_turn | asset_ref | decision_ref>"
  loser_refs: ["<asset_ref>", "..."]
  stack_notes: "<为何该 rank 获胜>"

# === 裁决内容 ===
ruling:
  action: keep_winner | merge | rewrite_loser | supersede_decision | split_scope | escalate_user
  claims_adopted:
    - claim: "<成为事实的陈述>"
      binds_to: [<asset_ref>]
  claims_rejected:
    - claim: "<废弃陈述>"
      from: <asset_ref>
  merge_notes: "<若 merge：如何拼合；禁空话>"

# === 影响面 ===
impact:
  must_update:          # 同步时必改
    - ref: <asset_ref>
      change: "<期望变更>"
  mark_stale:           # 先标 stale 再排期
    - ref: <asset_ref>
      reason: "<...>"
  do_not_touch:
    - ref: <asset_ref>
      reason: "locked | out_of_scope | unrelated"
  phases: []            # 波及 phase_id
  sequences: { volume_id: "", indices: [] }   # 复合键（速记 v3:s12），可选
  threads: []           # Thread ids 可选

# === 执行与门禁 ===
execution:
  requires_user_confirm: true | false
  confirmed_by: null | user
  sync_status: pending | in_progress | done | blocked
  block_advance: true | false
  exit: sync | block

# === 可选溯源 ===
related:
  critique_ids: []
  knowledge_refs: []    # 仅 K-xxx，方法参考
  evidence_quotes: []   # 短摘录，非大段粘贴
```

### 4.1 状态迁移（Decision）

```
draft → review → canon → locked
canon|review → archived（被 supersede 或废弃）
```

> Decision **无 stale 态**（对齐 asset-types §2.4 与 decision 模板）：被新事实部分证伪 → 以新 Decision `supersedes` 取代并将旧件 archived，不做原地降级。

任何非 `escalate_user` 的 blocking 冲突：Decision 至少到 `review` 才允许继续相关 write。

执行完成（`execution.sync_status=done`）且结论已并入 Canon/目标资产的 Decision 可转 `archived`；归档（非 open）Decision 的 manifest entry 于卷末 volume_checkpoint 迁入 `manifest_decisions_v{n}`（`manifest_root` 只留 open/active Decision，分片契约见 asset-types §3）；`decide` 阶段只对照 open/近期 Decision + canon 级裁决，不装载全量历史。

### 4.2 一句话正文区（可选，跟在 header 后）

```markdown
## 叙事影响（非理论）
- 对读者可见变化：...
- 对序列 0–23 的节点影响：...
- 对人物洋葱层（表象/行为/情感/信念/创伤）是否下钻：是/否 + 层名
```

---

## 5. Impact 矩阵

行 = **被裁决改写/晋升的源 type**；列 = **可能需要 stale 或 sync 的目标 type**。  
`M` = 必检必处理；`C` = 条件（同实体/同 Thread/同序列交叠时）；`—` = 默认不波及。

| 源 \\ 目标 | Canon | Blueprint | PlotSpine | SequenceMap | SceneBeat | ChapterPlan | Character | WorldRule | Thread | ManuscriptUnit | Decision | Manifest |
|------------|:-----:|:---------:|:---------:|:-----------:|:---------:|:-----------:|:---------:|:---------:|:------:|:--------------:|:--------:|:--------:|
| **Canon** | M | M | M | M | M | M | M | M | M | C | C | M |
| **Blueprint** | C | M | M | M | C | C | C | C | C | — | C | M |
| **PlotSpine** | C | C | M | M | M | C | C | — | M | — | C | M |
| **SequenceMap** | — | — | C | M | M | M | C | — | M | — | C | M |
| **SceneBeat** | — | — | — | C | M | M | C | — | C | C | C | M |
| **ChapterPlan** | — | — | — | C | C | M | — | — | C | C | C | M |
| **Character** | C | C | C | C | C | C | M | C | C | C | C | M |
| **WorldRule** | C | C | C | C | C | C | M | M | C | C | C | M |
| **Thread** | — | — | C | M | M | C | C | — | M | — | C | M |
| **ManuscriptUnit** | C | — | — | — | — | — | — | — | — | C | C | M |
| **Decision** | C | C | C | C | C | C | C | C | C | C | M | M |
| **Manifest** | — | — | — | — | — | — | — | — | — | — | — | M |

**ManuscriptUnit 行列语义**（「已发布」判定全库唯一 = `status == locked`；`last_published_chapter` 仅为发布游标，不作判据）：
- 列（MU 为目标）：`C` 条件 = entity/thread/章 scope 相交**且 MU 未发布**（status ≠ locked，含 canon 存稿章）。locked（已发布）MU **不标 stale**：改写一条 `retcon_note` 入 `canon_continuity_v{n}`——`{ id, entity_ids, affected_asset_ids, old_fact, new_fact, forward_strategy, decision_id }`（结构以 asset-types §2.2 为准），后续章按 `forward_strategy`（圆回/淡出/显式修正）向前兼容。
- 行（MU 为源）：其 `continuity_delta` 与 Canon 既有事实冲突 → Canon 列 `C`（升 conflict 走流水线，禁静默改 Canon）；MU→MU 仅波及引用其 `summary_after`/尾段的后续**未发布**（status ≠ locked）章。

### 5.1 方向规则

1. **向下传播默认开启**：改高层 → 低层 `mark_stale` 后 sync。  
2. **向上传播默认关闭**：改低层不得改高层，除非 Decision.action 显式 `escalate` 且用户确认。  
3. **横向**：Character ↔ WorldRule、Thread ↔ SequenceMap 用 `C`，以 entity/thread id 相交为准。  
4. **Decision 自身**：`supersede` 时旧 Decision `archived`；引用旧 ruling 的资产进 `mark_stale`。  
5. **Manifest**：任何资产 rev/status 变更都 `M` 更新注册与指针。  
6. **locked/retcon**：`locked` = 已发布/冻结，不参与 stale 传播；上游变更触及 locked 资产 → 写 `retcon_note`（结构见 §5 注）而非 mark_stale；需改 locked 本体 → unlock 流程（Decision，`approved_by=user`）。
7. **retcon 纪律（superseded_by）**：retcon 落盘时必须在被推翻的旧 fact 条目上追加 `superseded_by: <retcon_id>`（旧 fact 原文不删不改）；实体检索命中带 `superseded_by` 的 fact 时**必须连带装载**对应 `retcon_note`，正文以 `new_fact` 为准。

### 5.2 序列粒度

- SequenceMap / SceneBeat / ChapterPlan / Thread 变更：尽量填 `scope.sequences = {volume_id, indices[]}`（速记 `v3:s12`），只 stale 相交单元。  
- 序列编号规范：卷内 `0..23`（**含序列 0 Hook**）；跨卷引用必须带 `volume_id`，与 glossary 一致。

### 5.3 人物洋葱层

Character 变更若声明层：`surface(表象) | behavior(行为) | emotion(情感) | belief(信念) | wound(创伤)`：  
- 仅表象/行为：SceneBeat/ChapterPlan 多为 `C`  
- 信念/创伤：PlotSpine / Thread / 相关序列 `M` 或强 `C`

---

## 6. Override 规则

### 6.1 合法覆盖（override）

| 条件 | 允许覆盖对象 | 必做 |
|------|--------------|------|
| P0 用户当轮明确指令 | 非 locked 资产；locked 须先 unlock | Decision + `winner_rank=P0` |
| 新 Decision.canon supersede 旧 Decision | 旧 Decision 结论 | `supersedes` 链完整 |
| unlock 流程 | `locked` → `canon` 或 `stale` | 用户确认；记 Decision |
| split_scope | 局部事实 | 明确 do_not_touch 边界 |

### 6.2 非法覆盖（必须 block）

1. 无 Decision 直接改写他份 `canon`/`locked`。  
2. 用 `draft` / critique / K-xxx **静默**覆盖 `canon`。  
3. 删除或清空 `Canon.invariant` 无 P0 + Decision。  
4. 双 `canon` 互斥时「随便选一个继续写」。  
5. `sync_status=pending|blocked` 时对同一 scope 继续 `advance` / `write_unit`。  
6. 跳过 `mark_stale` 导致下游仍当有效事实引用。

### 6.3 Override 伪代码

```
function apply_override(intent, targets, stack):
  if any(t.status == locked for t in targets):
    if not intent.explicit_unlock:
      return block("locked_without_unlock")
    record_decision(unlock=true)

  winner = resolve_priority_stack(intent, targets, stack)

  if winner.rank > P0 and touches_invariant(targets):
    if not intent.user_confirm:
      return block("invariant_needs_confirm")

  if dual_canon_lateral(targets) and not decision_exists:
    return block("lateral_dual_canon")

  dec = write_decision(...)
  mark_stale(impact_matrix(dec))
  if dec.execution.block_advance:
    return block_gate(dec)
  return sync_plan(dec)
```

### 6.4 与 mode 的耦合

| mode | 冲突策略 |
|------|----------|
| `advance` | 遇 blocking → 立即 block；stale 仅阻断**本轮必召回集内**命中（protocol §4.4） |
| `write_unit` | 必召回集命中 stale 依赖 → block 或先 sync；集外 stale 不阻断 |
| `diagnose` | 只 detect+classify，默认可不写 Decision；装载 stale 资产**合法**（protocol §4.4） |
| `change` | 满足 §0.1 条件走 simple_change，否则全流水线强制；装载 stale 资产**合法**（protocol §4.4）；无 Decision 不得结束 change |
| `learn` | 只动知识理解，不改项目资产，不产生故事向 override |

---

## 7. 分类专册（可执行要点）

### 7.1 vertical_drift

```
IF low.claims ⊭ high.constraints:
  winner = high  IF high.status in {canon, locked}
  action = rewrite_loser(low)
ELSE IF evidence proves high wrong:
  action = escalate_user
  requires_user_confirm = true
  # 禁止 Agent 私自改 P2/P3
```

### 7.2 lateral_conflict

```
IF same_fact AND both status in {canon, locked}:
  blocking = true
  action = escalate_user | merge via Decision
ELSE:
  winner = higher status then higher phase then newer rev
```

### 7.3 version_skew

```
prefer: Manifest.canonical_pointer
else: max(rev) among status in {locked, canon}
pointers_fix; losers -> archived or stale
never write prose against non-pointer rev
```

### 7.4 intent_gap

```
scope = parse_user_intent.change_set
IF planned_edits - scope != ∅:
  either shrink plan to scope
  or Decision 扩 scope（触 invariant 则确认）
```

### 7.5 critique_unmerged

```
FOR critique in open_critiques(target):
  Decision: accept_all | accept_partial | reject
  on accept: update target + rev++
  critique.merged = true
  critique.merge_decision = dec_id
  # 未 merged 的 critique 无执行权
```

---

## 8. Agent 检查清单（每次变更）

```
[ ] detect：本轮是否引入/暴露冲突？是否先跑 §0.1 simple_change 判定？
[ ] classify：primary taxonomy（§1.3 判定序）+ severity + blocking？
[ ] decide：优先级栈 rank 是否写明？
[ ] record：Decision 模板字段是否齐全？
[ ] mark_stale：impact 矩阵是否落地到具体 asset_ref？
[ ] sync|block：exit 是否明确？block 时是否停止 advance/write_unit？
[ ] Manifest 是否 touch 全部受影响资产（entry rev/status 与信封对齐）？
[ ] 术语是否与 glossary 一致（洋葱五层、序列 0–23）？
[ ] 是否误用 K-xxx 覆盖项目事实？
[ ] 有无绑定具体书名/角色名作为规范？（禁止）
```

---

## 9. 与 runtime 其它文件的接口

| 文件 | 本 playbook 提供 | 期望对方提供 |
|------|------------------|--------------|
| `protocol.md` | BlockGate、变更中段挂起 | 召回序、writeback、mode 入口 |
| `asset-types.md` | Decision schema、status 用法 | 各 type 字段与合法迁移 |
| `phase-contracts.md` | gate 失败 → conflict 入口 | depends_on / gate / on_fail |
| `glossary.md` | 引用术语，不重定义 | 洋葱五层、序列 0–23、phase 名 SSOT |

### 9.1 知识块（按需，非默认加载）

冲突**叙事层**设计可参考（方法，非项目事实）：  
`K-CONFLICT-001`…、`K-CONCEPT-010`、`K-CHAR-004` 等——**仅**在 classify/decide 需要方法提示时按 ID 拉取，不得写入 claims_adopted 作为唯一依据。

---

## 10. 最小状态机（汇总）

```
                 ┌──────────────┐
                 │   detect     │
                 └──────┬───────┘
                        v
                 ┌──────────────┐
                 │  classify    │
                 └──────┬───────┘
                        v
              blocking? ──no──► optional Decision ──► continue
                        │
                       yes
                        v
                 ┌──────────────┐
                 │   decide     │
                 └──────┬───────┘
                        v
                 ┌──────────────┐
                 │ record Dec.  │
                 └──────┬───────┘
                        v
                 ┌──────────────┐
                 │ mark_stale   │
                 └──────┬───────┘
                        v
              confirmed & writable?
                   /        \
                 yes         no
                  v           v
               sync         block
                  v           v
            clear stale   BlockGate
            resume mode   allowed: diagnose|change
```

---

## 11. 修订

| rev | 说明 |
|----:|------|
| 1 | 初版：taxonomy 五类、优先级栈、六段流水线、Decision 模板、impact 矩阵、override |
| 2 | 对齐授权/规模工程裁决：impact 矩阵补 ManuscriptUnit 行列 + locked/retcon 语义（§5）；自动门正式定义 + Decision `approved_by`；新增 §0.1 simple_change 短路；§1.3 taxonomy 三步判定序 + Character 字段归层；序列复合键 `{volume_id, indices[]}`；ConflictRecord 落 `notes/conflicts/`；Manifest 改 touch 语义；stale 豁免对齐 protocol §4.4；Decision 完成后可 archived |
| 3 | 2026-08-13 修复轮：§0.1 simple_change 增第四条件（不追溯 locked 章既成事实；触及 → 完整流水线 + retcon_note）；§5 MU 行列注释钉死「已发布」唯一判据 = `status == locked`（`last_published_chapter` 仅游标），retcon_note 结构补 `entity_ids`（对齐 asset-types §2.2）；§5.1 新增规则 7 retcon 纪律（旧 fact 追加 `superseded_by`、实体检索命中连带装载 retcon_note）；§4.1 归档 Decision entry 卷末迁入 `manifest_decisions_v{n}`；第三波收尾（V1 复检修正：冷启动条件行/六件套允许集/小节指针/编号/口径对齐） |

**文档 status**：`canon`（runtime 协议层）  
**type**：RuntimeProtocol  
**id**：`runtime.conflict_playbook`
