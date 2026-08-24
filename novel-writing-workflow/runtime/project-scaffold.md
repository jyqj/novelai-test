# Project Scaffold — `new_project` 强制脚手架协议

> **定位**：`intent=new_project` / `MODE_INIT` 的**强制**项目初始化契约。  
> **依赖**：`protocol.md`（BOOT / writeback / BLOCK）、`asset-types.md`（type / id / Manifest）、`phase-contracts.md`（P1 I/O、route）、`glossary.md`（术语 SSOT）。  
> **知识**：仅引用 `K-xxx` ID；本文件不粘贴方法论正文。  
> **硬约束**：通用工程层 only；禁止绑定具体书名、角色名、作品目录作规范正文。

---

## 0. 原则

| ID | 规则 |
|----|------|
| S0 | 脚手架是 **gate 前置**：未过本文件完成 gate 不得宣称 `new_project` 成功，也不得进入 `advance` 当项目已存在 |
| S1 | **Type 一等公民**：业务逻辑只认 `type` + `id` + `rev` + `status`；路径仅 storage adapter |
| S2 | 强制产物缺一 → BLOCK `SCAFFOLD_INCOMPLETE`（本文件定义；可映射为 protocol `MISSING_INPUT` 子类） |
| S3 | 未注册 Manifest 的磁盘文件 = orphan，**不**算脚手架完成 |
| S4 | 默认 `route`：用户明确网文/连载/日更意图 → **`web`**；否则 **`traditional`**（与 phase-contracts 未声明默认一致） |
| S5 | `new_project` **禁止**打开 `knowledge-index.md`；P1 知识仅按 phase-contracts 白名单 K-ID 拉取 |
| S6 | 脚手架阶段 **禁止**产出 PlotSpine / SequenceMap / SceneBeat / ChapterPlan / ManuscriptUnit（那是后续 phase） |
| S7 | status 枚举仅：`draft \| review \| canon \| locked \| stale \| archived` |

---

## 1. 触发条件

### 1.1 必须进入脚手架

满足任一即强制跑本协议（不可跳过「只聊概念不建盘」而伪装项目已存在）：

| # | 条件 |
|---|------|
| T1 | `intent == new_project`（含别名归一：`new` → `new_project`） |
| T2 | BOOT 判定 `project_state == NONE`（无 `Manifest` / 无 `manifest_root` 可读）且用户确认「创建/初始化工作区」 |
| T3 | 用户显式要求「重建脚手架 / 重新初始化」且经确认；已有项目须先 `change` 或 Decision 归档旧资产，禁止静默覆盖 canon/locked |
| T4 | 用户**已有大纲/人物表/正文等既有材料**要求接管、导入、迁移 → **Adopt 模式**（§1.4；仍属 new_project 变体） |

### 1.2 不得进入（应路由别处）

| 信号 | 正确 intent |
|------|-------------|
| 已有 Manifest + 推进阶段 | `advance` |
| 已有 ChapterPlan，写正文 | `write_unit` |
| 只学方法、解释 K-xxx | `learn` |
| 无项目仅症状咨询 | `diagnose`（knowledge-only） |
| 改既有设定 / 冲突 | `change` |

### 1.3 预检（preflight）

```
preflight_scaffold(workspace):
  if exists(Manifest.manifest_root) and not user.force_reinit:
    return BLOCK(code=SCAFFOLD_ALREADY_EXISTS,
                 detail="项目已存在；改用 advance/change 或显式 reinit+Decision")
  if user.force_reinit and any_asset.status in {canon, locked}:
    require Decision(decision_type=scope_change|deprecate) or user_turn_override
  return OK
```

### 1.4 Adopt 模式——接管已有稿件（new_project 变体）

> 用户已在系统外写有大纲/人物/设定/正文时**禁止**两种伪路径：①只聊不建盘假装 EXISTS；②把未验证材料直接标 canon 后 `advance`。

**流程（在标准脚手架之上叠加）：**

```
AD_1    标准脚手架六件套照常创建（§2）；Blueprint 从既有材料预填而非空壳
AD_2    材料盘点 → 按内容归类到 type（映射表见下）
AD_3    逆向注册：每份材料建资产 + manifest_register
        status 一律 = review（待校验）；例外：已公开发布的正文直接注册 **locked**（「已发布」判据全库唯一 = status==locked）
AD_3.5  分批消化 pass（可跨多轮会话；`Status.adopt_cursor` 记进度）：
        逐批 ≤10 章通读旧稿正文 →
          每章生成 `summary_after`；
          提取 `facts`（含 entity_ids）upsert 入 `canon_continuity_v{n}`；
          登记/推进 Thread（plant/advance/payoff 对齐正文既成事实）
        批级验收（每批完成时自检；任一 FAIL → 本批重跑，不推进 adopt_cursor）：
          ① 本批每章 `summary_after` 非空
          ② 本批新增 fact 每条带 `entity_ids`
          ③ 本批触及的 Thread 均有 plant/advance 章号
        全部批次完成 → 生成 `recap_book` + 重写 `recap_state`
AD_4    逐 phase dry-run gate（**仅 AD_3.5 完成后进入**）：从 P1 起依序跑各 phase gate（只判定不产出）
        第一个 FAIL 的 phase = Status.current_phase；其 gate 缺口写入 blockers
AD_5    report：已注册资产清单 + 消化进度（adopt_cursor）+ 各 phase gate 判定 + 缺口修补建议（下一步 advance@current_phase）
```

**材料 → type 映射：**

| 既有材料 | 目标 type | 初始 status |
|----------|-----------|-------------|
| 一句话卖点/立意/类型定位 | `Blueprint` 字段 | draft→review |
| 全书节点级大纲 | `PlotSpine`（压缩为 title + value_one_liner；场景级内容**降级拆出**） | review |
| 分卷/序列级大纲、场景列表 | `SequenceMap` | review |
| 场景节拍/细纲 | `SceneBeat` | review |
| 章纲 | `ChapterPlan` | review |
| 人物表/人设卡 | `Character`（洋葱五键缺失处标 open） | review |
| 设定集/世界观文档 | `WorldRule`（可拆 domain） | review |
| 伏笔/支线备忘 | `Thread` | review |
| 已写正文 | `ManuscriptUnit` | review；已公开发布 → **locked** |
| 主题/禁区/既定事实 | `Canon`（invariants / forbidden / facts） | draft |

逆向注册 id 按 §3.1 约定：章纲 `chapter_{nnnn}`（全局四位章号）、正文 `ms_{nnnn}`、场景 `scene_v{v}_{s}_{nn}`。

**禁止：** 跳过 AD_3.5 / AD_4 直接宣称某 phase 已过；消化未完成即生成 recap 或跑 dry-run；把材料中的矛盾静默择一（应 emit conflict 走 playbook）；为凑 gate 虚构材料中不存在的字段值。

---

## 2. 强制产物清单

脚手架 **PASS** 时下列七类必须齐备（**六件套**资产 + 目录骨架；逻辑完备；物理路径见 §3，可改）。

| # | type | 实例 id（固定/约定） | 目标 status | 模板 | 职责摘要 |
|---|------|----------------------|-------------|------|----------|
| 1 | `Status` | `status_project` | `canon`（允许短暂 `draft` 后升） | `templates/status.md` | mode/phase/route/指针 |
| 2 | `Manifest` | `manifest_root` | `canon`（或 `draft` 后升） | `templates/manifest.md` | 资产注册表；自描述 + 全部种子 entry |
| 3 | `Canon` | `canon_root` | **`draft`**（seed） | `templates/canon.md`（字段对齐 asset-types §2.2） | 不变量/主题/禁区占位；**禁止假装已 canon** |
| 4 | `Blueprint` | `blueprint_main` | **`draft`** | `templates/blueprint.md`（字段对齐 asset-types §2.5） | P1 主产出起点；**禁止**序列/场景/章纲/正文 |
| 5 | `Recap` | `recap_state` | **`draft`**（空壳） | `templates/recap.md` | 现状快照空壳；P6 起每章重写（protocol §4.2 召回项） |
| 6 | `Canon` | `canon_style` | **`draft`**（style-card 实例化） | `templates/style-card.md` | 全书文风基准卡；**保留模板预置的 15 条 LLM 腔 `taboo_list` 黑名单**；write_unit 必召回（protocol §4.2） |
| 7 | 目录骨架 | —（adapter 布局） | — | 本文件 §3 | 可写工作区骨架；**非**业务 type |

> 与 `protocol.md` §6.2 对齐：`new_project` 默认可写 = Manifest, Status, Blueprint(draft), 初始 Canon(`canon_root` seed,draft), Canon(`canon_style` 空壳,draft), Recap(`recap_state` 空壳,draft)。  
> **系统单例豁免**：Status / Manifest 由脚手架直接以 `canon` 创建（运行态必需），属 writeback-acceptance **M05 既定例外**；不构成静默晋升先例，其余资产仍按 protocol §3.2 晋升规则（禁静默升 canon）。

### 2.1 每产物契约表（type / id / 模板 / status / Manifest）

#### A. Status

| 字段 | 值 |
|------|-----|
| `type` | `Status` |
| `id` | `status_project`（单例，禁止另起） |
| `template` | `templates/status.md` |
| 初始化 `status` | 建议 `canon`（运行态可用）；至少 `draft` |
| `rev` | `1` |
| Manifest entry | **必须**；`phase_home: "*"` |

**强制初始化字段：**

```yaml
id: status_project
type: Status
rev: 1
status: canon
mode: new_project          # 枚举以 asset-types §2.1 为准（含 idle）；完成后可置 idle 或保持至首轮 advance
phase: P1
phase_gate: pending
blockers: []
active_unit: { type: null, id: null }
last_writeback: { asset_id: null, rev: null, at: null }
load_policy_rev: 1
route: traditional | web   # 见 §4
flags:
  dual_track: traditional | web_serial | hybrid   # 与 route 对齐，见 §4.2
  knowledge_budget_default: 12
  critic_cadence: every_5_chapters + volume_end   # critic 抽检默认节奏
  unattended_mode: false     # 默认半自动（publish/卷界人批）；语义见 asset-types §2.1
web_serial:                # route=web 时必写全块；字段以 asset-types §2.1 为准
  current_volume: vol_01
  serial_cursor: { last_published_chapter: 0, next_write_chapter: 1, next_plan_chapter: 1 }
  buffer: { target_chapters: 3, ready_count: 0, min_before_publish: 1 }
  auto_promote: { p4_canon: true, p4_canon_seed: true, chapter_canon_on_gate_pass: true, facts_upsert: true }
  last_critic_chapter: 0     # critic 抽检游标；漏跑可检（asset-types §2.1）
depends_on: []
```

#### B. Manifest

| 字段 | 值 |
|------|-----|
| `type` | `Manifest` |
| `id` | `manifest_root`（单例） |
| `template` | `templates/manifest.md` |
| 初始化 `status` | `canon` 或 `draft`→`canon` |
| `schema_rev` | `1`（与 asset-types 对齐） |
| Manifest entry | **自描述**（AT4）：`asset_id=manifest_root` 必须在 `entries[]` |

**强制 `project` 与种子 entries：**

```yaml
project:
  name: string              # 工作区显示名 only，非书名业务键
  created_at: datetime

unit_shards: []             # 卷级单元分片指针（manifest_units_v{n}）；P3+ 追加，脚手架为空

entries:                    # 至少含下列六条（脚手架完成时）
  - asset_id: manifest_root
    type: Manifest
    rev: 1
    status: canon           # 或 draft
    phase_home: "*"
    depends_on: []
  - asset_id: status_project
    type: Status
    rev: 1
    status: canon           # 与 Status 信封一致
    phase_home: "*"
    depends_on: []
  - asset_id: canon_root
    type: Canon
    rev: 1
    status: draft           # seed
    phase_home: "*"
    depends_on: []
  - asset_id: canon_style
    type: Canon
    rev: 1
    status: draft           # style-card 实例化空壳
    phase_home: "*"
    depends_on: []
  - asset_id: blueprint_main
    type: Blueprint
    rev: 1
    status: draft
    phase_home: P1
    depends_on: []          # 或 soft cite Canon 后补
  - asset_id: recap_state
    type: Recap
    rev: 1
    status: draft
    phase_home: "*"
    depends_on: []
```

#### C. Canon（seed）

| 字段 | 值 |
|------|-----|
| `type` | `Canon` |
| `id` | `canon_root` |
| `template` | `templates/canon.md`（字段对齐 `asset-types.md` §2.2） |
| 初始化 `status` | **`draft` only**（seed；禁止脚手架直接写 `canon`/`locked` 当真值） |
| Manifest entry | 必须；`phase_home: "*"` |

**seed 最小字段（可空列表，但键必须存在）：**

```yaml
id: canon_root
type: Canon
rev: 1
status: draft
invariants: []              # 后续从 Blueprint/WorldRule/Decision 提升
theme:
  controlling_idea: ""      # 可空；K-CONCEPT-013 指导填充，不粘贴理论
  counter_idea: ""
  ending_mode: unset        # idealist|pessimist|positive_irony|negative_irony|unset
facts: []                   # 原 continuity_facts（废弃别名，见 asset-types §0.3.1）；正式承载位 = canon_continuity_v{n} 卷分片（P6 起按卷建），此处仅种子空占位
forbidden: []               # 用户禁区可在脚手架写入
open_questions: []          # 未裁决项；不得假装已定
```

#### D. Blueprint（draft）

| 字段 | 值 |
|------|-----|
| `type` | `Blueprint` |
| `id` | `blueprint_main` |
| `template` | `templates/blueprint.md`（填写时字段须可映射 asset-types §2.5 / phase-contracts P1） |
| 初始化 `status` | **`draft`** |
| Manifest entry | 必须；`phase_home: P1` |

**脚手架最低完备（可极简占位，但禁止缺键冒充已 register）：**

```yaml
id: blueprint_main
type: Blueprint
rev: 1
status: draft
high_concept: ""            # 可空字符串占位；P1 gate 再强制非空
premise: ""
genre:
  primary: ""
  secondary: []
  web_serial_tags: []
  must_keep_conventions: []
  cliches_to_avoid: []
spine_intent:
  protagonist_desire: ""
  opposing_force: ""
  core_conflict_one_liner: ""
controlling_idea_draft: ""
ending_mode_tendency: unset
element_seeds: []
cast_seeds: []              # 仅 role/label/function；禁止当 Character canon
world_seeds:
  era: ""
  duration: ""
  place: ""
  conflict_scale: personal  # 或留空由 adapter 允许 null → 脚手架可用 personal 默认并标 open_questions
  core_rules_draft: []
plot_vector:
  opening: ""
  midpoint_direction: ""
  ending_direction: ""
# 禁止字段: sequences[], scenes[], beats[], chapters[], body/text
```

> 脚手架 **允许** `high_concept` 等仍为空：完成 gate 认「壳存在 + 已注册」；**P1 phase gate**（phase-contracts）才要求内容满填。二者勿混。

#### E. Recap（state 空壳）

| 字段 | 值 |
|------|-----|
| `type` | `Recap` |
| `id` | `recap_state`（单例；`recap_book` / `recap_vol_{n}` 由 P6/卷末产生，脚手架不建） |
| `template` | `templates/recap.md` |
| 初始化 `status` | **`draft`**（空壳） |
| Manifest entry | 必须；`phase_home: "*"` |

```yaml
id: recap_state
type: Recap
rev: 1
status: draft
kind: state
covers_chapters: [0, 0]
body: ""                    # ≤600 字现状快照；P6 每章写回后重写
```

#### F. Canon style（canon_style 空壳）

| 字段 | 值 |
|------|-----|
| `type` | `Canon` |
| `id` | `canon_style`（全书文风切片；实例族见 `templates/canon.md` §0） |
| `template` | `templates/style-card.md` |
| 初始化 `status` | **`draft`**（空壳；后续按 protocol §3.2 晋升规则升，禁止脚手架假 canon） |
| Manifest entry | 必须；`phase_home: "*"` |

**seed 要求**：按 `templates/style-card.md` 实例化信封 + 最小键；**保留模板预置的 15 条 LLM 腔 `taboo_list` 黑名单**（项目后续可增删）；人称/时态/句长等基准字段可空占位——P1 起充实并随 P1 outputs 晋升（`Canon(canon_style, target ≥ review)`，见 phase-contracts §2.2）。

#### G. 目录骨架

非 AssetType。由 storage adapter 创建；**默认树见 §3，非唯一布局**。  
完成条件：adapter 可 `resolve` Status/Manifest/Canon(`canon_root`+`canon_style`)/Blueprint/Recap 六 id 的 uri，且与 Manifest.entries[].uri 一致（uri 可暂 null，但落盘后应回填）。

---

## 3. Filesystem 默认树（非唯一）

> 协议层 **不依赖** 本树。仅当工作区选择「单库多文件」落地时参考。  
> **禁止**将目录名写进业务 if/else；与 `asset-types.md` 附录 A 对齐，可整体替换。

```
{project_root}/
├── runtime-state/
│   ├── status.yaml              # Status  → status_project
│   └── manifest.yaml            # Manifest → manifest_root
├── canon/
│   ├── canon_root.md            # Canon seed
│   └── canon_style.md           # Canon style 切片（style-card 实例化；脚手架必建）
├── design/
│   ├── blueprint.md             # Blueprint draft
│   ├── plot_spine.md            # （空位可选；P2 再写，脚手架可不建文件）
│   ├── sequence_map_v{n}.md     # （P3；按卷实例）
│   ├── scenes/                  # SceneBeat（P4）
│   └── chapters/                # ChapterPlan（P5）
├── cast/                        # Character
├── world/                       # WorldRule
├── threads/                     # Thread
├── decisions/                   # Decision
├── manuscript/                  # ManuscriptUnit（P6）
├── recaps/                      # Recap（recap_state / recap_book / recap_vol_{n}）
└── notes/                       # 非执行素材（灵感）；默认不进 Manifest
    └── conflicts/               # ConflictRecord 工作记录（asset-types §2.14）
```

### 3.1 默认 type → 相对路径映射（adapter 配置）

| type | id 模式 | 默认相对路径 |
|------|---------|--------------|
| Status | `status_project` | `runtime-state/status.yaml` |
| Manifest | `manifest_root` | `runtime-state/manifest.yaml` |
| Canon | `canon_root` | `canon/canon_root.md` |
| Canon | `canon_style` | `canon/canon_style.md` |
| Blueprint | `blueprint_main` | `design/blueprint.md` |
| Decision | `decision_*` | `decisions/{id}.md` |
| PlotSpine | `plotspine_main` | `design/plot_spine.md` |
| SequenceMap | `seqmap_v{n}`（模式 A 单卷 = `seqmap_v1`） | `design/sequence_map_v{n}.md` |
| SceneBeat | `scene_v{v}_{s}_{nn}` | `design/scenes/{id}.md` |
| ChapterPlan | `chapter_{nnnn}`（全局四位章号） | `design/chapters/{id}.md` |
| Character | `char_*` | `cast/{id}.md` |
| WorldRule | `world_*` | `world/{id}.md` |
| Thread | `thread_*` | `threads/{id}.md` |
| ManuscriptUnit | `ms_{nnnn}` | `manuscript/{id}.md` |
| Recap | `recap_state` \| `recap_book` \| `recap_vol_{n}` | `recaps/{id}.md` |

### 3.2 脚手架必建 vs 可选空目录

| 动作 | 路径/资产 |
|------|-----------|
| **必建文件** | Status、Manifest、Canon seed、Canon style（`canon_style` 空壳）、Blueprint draft、Recap state 空壳 |
| **建议空目录** | `design/scenes/`, `design/chapters/`, `cast/`, `world/`, `threads/`, `decisions/`, `manuscript/`, `recaps/`, `notes/conflicts/` |
| **禁止预写** | 假 PlotSpine 24 节点、假 Character canon、假 ManuscriptUnit |
| **禁止预注册** | 未创建资产的 Manifest entry（asset-types：未注册=不存在；预注册空壳 id 亦禁止，除本协议六种子） |

---

## 4. Route 初始化

### 4.1 判定规则

```
function resolve_route(user_utterance, user_flags):
  if user_flags.route in {traditional, web}:
    return user_flags.route                    # 用户显式优先
  if signals_web(user_utterance):
    # 网文 / 连载 / 日更 / 章推 / 存稿 / 平台连载 等
    return web
  if signals_traditional(user_utterance):
    return traditional
  return traditional                           # 未声明默认（phase-contracts §0.1）
```

**web 信号（示例，非穷尽）**：网文、连载、日更、存稿、章末钩子、订阅/追更、web_serial。  
**traditional 信号（示例）**：出版长篇、一次写完再发、文学向、无连载压力。

### 4.2 双字段同步

| 字段 | 合法值 | 脚手架写入 |
|------|--------|------------|
| `Status.route` | `traditional` \| `web` | 供 phase-contracts `route_delta` |
| `Status.flags.dual_track` | `traditional` \| `web_serial` \| `hybrid` | 资产层轨标记 |

**对齐表：**

| `route` | `flags.dual_track` |
|---------|-------------------|
| `traditional` | `traditional` |
| `web` | `web_serial` |
| （后续改轨 hybrid） | `hybrid` + 写 `Decision` |

### 4.3 web 轨脚手架附加要求

当 `route=web`：

1. `Status.flags.dual_track = web_serial`
2. `Status.web_serial` 全块写入（默认值见 §2.1 A；字段以 asset-types §2.1 为准）：`current_volume=vol_01`、`serial_cursor`、`buffer`、`auto_promote` 默认全 true；`flags.critic_cadence` 置默认
3. `Blueprint` seed 预留/标注字段意图（可空内容）：`genre.web_serial_tags`、开篇钩子意图位（P1 gate 强制，脚手架可写 `open_questions` 提示）
4. `Canon.open_questions` 可加入：`"opening_hook_intent"`、`"payoff_density_policy"`（提示项，非理论粘贴）
5. **不**在脚手架展开 0–23 节点或章纲

### 4.4 traditional 轨

- `route=traditional`，`dual_track=traditional`
- 无强制开篇钩子字段；P1 仍按 phase-contracts traditional gate

---

## 5. 完成 gate（Scaffold Gate）

全部 `must` 通过 → `SCAFFOLD_PASS`；否则 BLOCK，**不得**把 `project_state` 标为 EXISTS 成功态。

### 5.1 检查项

| # | 规则 | fail → |
|---|------|--------|
| G1 | 磁盘/存储上可 load：`status_project`, `manifest_root`, `canon_root`, `canon_style`, `blueprint_main`, `recap_state` | `SCAFFOLD_INCOMPLETE` |
| G2 | 六资产信封含：`id`, `type`, `rev`, `status`, `updated_at`（或等价） | `SCAFFOLD_INCOMPLETE` |
| G3 | `Manifest.entries` 含上述六 id；`entries[].rev/status` 与信封一致（AT2） | `version_skew` / `SCAFFOLD_INCOMPLETE` |
| G4 | `Manifest` 自描述：`manifest_root ∈ entries`（AT4） | `SCAFFOLD_INCOMPLETE` |
| G5 | `Status.phase == P1` 且 `Status.mode ∈ {new_project, idle, advance}`（枚举合法性以 asset-types §2.1 为准；初始化瞬间允许 `new_project`） | `SCAFFOLD_INCOMPLETE` |
| G6 | `Status.route ∈ {traditional, web}`；`flags.dual_track` 与 §4.2 对齐；route=web 时 `web_serial` 块已按 §4.3 写入 | `SCAFFOLD_INCOMPLETE` |
| G7 | `Canon.status == draft` 且 `open_questions` 键存在（可为 `[]`） | `SCAFFOLD_INCOMPLETE` |
| G8 | `Blueprint.status == draft`；**无** `sequences` / `scenes` / `beats` / 正文段 | `WRITE_SCOPE_VIOLATION` |
| G9 | 未注册非法 type 别名（`ProseUnit`/`ThreadMap` 等须归一，脚手架阶段不应出现） | `SCAFFOLD_INCOMPLETE` |
| G10 | 未打开 `knowledge-index.md`；未写入 `knowledge/**` | `KNOWLEDGE_INDEX_FORBIDDEN` / `WRITE_SCOPE_VIOLATION` |
| G11 | 网文信号下 `route==web`（用户未显式 traditional 覆盖时） | 提示修正 route，可 BLOCK 或 ASK |
| G12 | `blockers` 不含未处理的脚手架错误；`phase_gate` 非因脚手架失败而假 `passed` | `SCAFFOLD_INCOMPLETE` |
| G13 | `recap_state` 信封：`type=Recap`、`kind=state`、`status=draft`（`body` 可空）；`recaps/`、`notes/conflicts/` 目录可解析 | `SCAFFOLD_INCOMPLETE` |
| G14 | `canon_style` 信封可解析：`type=Canon`、`id=canon_style`、`status=draft`（style-card 实例化；模板预置 `taboo_list` 黑名单保留，其余基准字段可空壳） | `SCAFFOLD_INCOMPLETE` |

### 5.2 通过后状态

```yaml
# 逻辑结果
project_state: EXISTS
Status.phase: P1
Status.phase_gate: pending      # 等待 P1 Blueprint gate，非 scaffold 代劳
scaffold_gate: passed
next_intent_hint: advance       # 充实 Blueprint → 跑 P1 gate
# 可选：Status.mode → idle 或保持 new_project 至用户下一轮
```

### 5.3 失败 on_fail

```yaml
on_fail: repair_in_phase        # 留在 MODE_INIT 补齐产物
# 不创建半套 Manifest 却报告成功
# 不写入 knowledge
# 不 advance phase 到 P2
```

### 5.4 与 P1 phase gate 的边界

| gate | 负责 |
|------|------|
| **Scaffold Gate（本文件）** | 壳、注册表、route、目录、六资产存在且 draft/canon 合规 |
| **P1 Gate（phase-contracts）** | Blueprint **内容**满填：high_concept、genre、cast、world_seed、plot_direction 等 |

脚手架 PASS ≠ P1 PASS。

---

## 6. 回写顺序（脚手架专用）

对齐 `protocol.md` WB_*，收窄为 init 事务：

```
SC_WB_1  create_directory_skeleton(adapter_layout)   # §3（含 recaps/、notes/conflicts/）
SC_WB_2  write Manifest shell (rev=1) + self entry
SC_WB_3  write Status (route resolved, phase=P1；route=web → web_serial 全块)
SC_WB_4  write Canon seed (status=draft)
SC_WB_5  write Canon style 空壳 canon_style (status=draft；templates/style-card.md 实例化，保留预置 taboo_list)
SC_WB_6  write Blueprint draft (status=draft；可从用户素材预填字段)
SC_WB_7  write Recap 空壳 recap_state (status=draft, kind=state)
SC_WB_8  manifest_register/touch 全部六 id；uri 回填
SC_WB_9  validate Scaffold Gate (§5)
SC_WB_10 if fail → 不声明成功；列出缺失项
         if pass → Status.last_writeback 更新；report
```

**禁止**：先写 Blueprint 长文却不 register Manifest；先标 `phase=P2`。

---

## 7. 阻断码（脚手架扩展）

| code | 含义 | 恢复 |
|------|------|------|
| `SCAFFOLD_INCOMPLETE` | 强制产物缺失或 entry 不一致 | 补齐 §2 清单后重跑 gate |
| `SCAFFOLD_ALREADY_EXISTS` | 项目已存在却未授权 reinit | 改 `advance`/`change` 或 Decision 后 reinit |
| `ROUTE_MISMATCH` | dual_track 与 route 矛盾 | 按 §4.2 同步 |
| （复用 protocol）`MISSING_MANIFEST` | 后续 intent 发现无 Manifest | 回 `new_project` |
| （复用）`WRITE_SCOPE_VIOLATION` | 写入了 P2+ 类型或 knowledge | 删除/归档越权产出 |
| （复用）`KNOWLEDGE_INDEX_FORBIDDEN` | init 扫了 index | 关闭 index；仅 P1 白名单 K-ID |

---

## 8. Agent 伪代码

```
function run_init(ctx, user_utterance):
  # —— 触发与预检 ——
  assert intent == new_project
  pre = preflight_scaffold(ctx.workspace)
  if pre.blocked: return block_report(pre)

  # —— 解析 route（网文 → web）——
  route = resolve_route(user_utterance, ctx.user_flags)
  dual_track = (route == web) ? web_serial : traditional

  # —— 装载策略：无既有资产；runtime 元数据 + 可选 P1 K-ID ——
  # 禁止 open knowledge-index
  k_ids = []
  if user_provided_enough_for_p1_prefill:
    k_ids = phase_contracts.P1.knowledge_budget.allow  # 按需截断 max_blocks
    ctx.knowledge = fetch_knowledge(k_ids, depth_cap=L2, budget=p1_budget)

  # —— 目录骨架 ——
  adapter.ensure_tree(default_or_configured_layout)   # §3 非唯一

  now = utc_now()

  # —— 强制产物 ——
  manifest = new Manifest(
    id="manifest_root", type=Manifest, rev=1, status=canon,
    project={ name: workspace_display_name, created_at: now },
    entries=[], unit_shards=[]
  )

  status = new Status(
    id="status_project", type=Status, rev=1, status=canon,
    mode=new_project, phase=P1, phase_gate=pending, blockers=[],
    active_unit={type:null, id:null},
    load_policy_rev=1,
    route=route,
    flags={ dual_track: dual_track, knowledge_budget_default: 12,
            critic_cadence: "every_5_chapters + volume_end",
            unattended_mode: false }
  )
  if route == web:
    status.web_serial = web_serial_defaults()   # §2.1 A：current_volume=vol_01、serial_cursor、
                                                # buffer、auto_promote 全 true（字段以 asset-types §2.1 为准）

  canon = new Canon(
    id="canon_root", type=Canon, rev=1, status=draft,
    invariants=[], theme={ controlling_idea:"", counter_idea:"", ending_mode:unset },
    facts=[], forbidden=user_forbidden_or_empty,   # facts 正式承载位 = canon_continuity_v{n}（P6 起建）
    open_questions=seed_open_questions(route)
  )

  style = new Canon(
    id="canon_style", type=Canon, rev=1, status=draft,
    ...style_card_min_fields(templates.style_card)   # 保留模板预置 taboo_list（15 条 LLM 腔黑名单）；基准字段可空占位
  )

  blueprint = new Blueprint(
    id="blueprint_main", type=Blueprint, rev=1, status=draft,
    # 最小键齐全；内容可从 utterance 预填，禁止场景/序列/正文
    ...blueprint_min_fields_from(user_utterance, templates.blueprint)
  )

  recap = new Recap(
    id="recap_state", type=Recap, rev=1, status=draft,
    kind=state, covers_chapters=[0,0], body=""
  )

  # —— 注册 + 落盘（事务顺序 §6）——
  for asset in [manifest, status, canon, style, blueprint, recap]:
    adapter.save(resolve(asset.type, asset.id), asset)
    manifest_register(entry_from(asset))   # 含 self for manifest

  manifest.rev += 1
  adapter.save(manifest)

  # —— Scaffold Gate ——
  gate = evaluate_scaffold_gate(manifest, status, canon, style, blueprint, recap, adapter)
  if gate.fail:
    status.phase_gate = blocked
    status.blockers += [{ code: SCAFFOLD_INCOMPLETE, message: gate.detail, related_asset_ids: gate.ids }]
    writeback(status, manifest)
    return Block(SCAFFOLD_INCOMPLETE, gate)

  status.last_writeback = { asset_id: "blueprint_main", rev: blueprint.rev, at: now }
  # mode 可置 idle；phase 保持 P1；phase_gate=pending（等 P1 内容 gate）
  writeback([manifest, status, canon, blueprint, recap])

  return InitReport(
    project_state=EXISTS,
    route=route,
    assets=[
      {type:Status, id:status_project, rev, status},
      {type:Manifest, id:manifest_root, rev, status},
      {type:Canon, id:canon_root, rev, status:draft},
      {type:Canon, id:canon_style, rev, status:draft},
      {type:Blueprint, id:blueprint_main, rev, status:draft},
      {type:Recap, id:recap_state, rev, status:draft}
    ],
    scaffold_gate=passed,
    next="充实 Blueprint 字段后 advance@P1；P1 gate 见 phase-contracts"
  )
```

### 8.1 `seed_open_questions(route)` 提示（非理论）

```
if route == web:
  return ["opening_hook_intent", "serial_payoff_policy", "volume_map_v1"]
else:
  return ["ending_mode_confirm"]
```

仅字符串标签；填充时参考 P1 `knowledge_budget.allow` 内 K-ID（如 `K-CONCEPT-001`、`K-CONCEPT-019`），**不**粘贴知识正文。

---

## 9. 用户可见报告最小集

`new_project` DONE 时向用户返回：

1. `intent=new_project`，`scaffold_gate=passed|failed`
2. `route` + `dual_track`
3. 六资产：`type` / `id` / `rev` / `status`
4. Manifest entry 计数与是否自洽
5. 失败时：缺失 id 列表 + 恢复动作
6. 下一步：`advance` 充实 `blueprint_main`（P1），勿跳 P2

---

## 10. 自检清单（Agent）

```
[ ] 是否确为 new_project / project_state=NONE（或授权 reinit）？
[ ] 是否创建 Status/Manifest/Canon(seed)/Canon(canon_style 空壳)/Blueprint(draft)/Recap(state 空壳) 且 id 固定正确？
[ ] Manifest.entries 是否含六种子且 rev/status 对齐？
[ ] 网文意图是否 route=web 且 dual_track=web_serial？
[ ] Canon/Blueprint 是否均为 draft seed/draft（未假 canon）？
[ ] 是否禁止了序列/场景/章纲/正文与非法 type 别名？
[ ] 是否未打开 knowledge-index、未写 knowledge/**？
[ ] 目录树是否仅 adapter 配置、业务未 hardcode 路径？
[ ] Scaffold Gate 是否逐条可勾选？失败是否 BLOCK？
[ ] 是否未把 Scaffold PASS 当作 P1 content gate PASS？
[ ] Adopt：AD_3.5 消化未完成时是否未跑 AD_4、未生成 recap？adopt_cursor 是否记录进度？批级验收 FAIL 时是否本批重跑、未推进 adopt_cursor？
```

---

## 11. 与其它 runtime 文件接口

| 文件 | 关系 |
|------|------|
| `protocol.md` | BOOT_3 NONE → `new_project`；§6.2 可写范围；主循环 `run_init` |
| `asset-types.md` | type/id/最小字段/ManifestEntry/附录路径 |
| `phase-contracts.md` | 脚手架之后 P1 contract；`route` / `route_delta` |
| `conflict-playbook.md` | reinit 覆盖 canon/locked 时裁决 |
| `glossary.md` | 术语/枚举 SSOT |

本文件 **不** 重定义 P1–P6 gate 正文、不重定义 AssetStatus、不粘贴 K-xxx 理论。

---

## 12. 修订

| rev | 说明 |
|-----|------|
| 1 | 初版：触发、强制产物、默认目录树、route 网文→web、完成 gate、伪代码 |
| 2 | 四件套 → 五件套（+`recap_state` 空壳）；目录补 `recaps/`、`notes/conflicts/` + Gate G13；系统单例 canon 豁免声明（M05）；G5 mode 枚举引 asset-types；route=web 写全量 `web_serial` 块 + `flags.critic_cadence`；Adopt 增 AD_3.5 分批消化 pass（`adopt_cursor`，可跨多轮）；id 约定对齐 `chapter_{nnnn}` / `scene_v{v}_{s}_{nn}` / `ms_{nnnn}` / `seqmap_v{n}`；Manifest 种子瘦身（删 recall_priority/edges，增 `unit_shards`） |
| 3 | 2026-08-13 修复轮：五件套 → 六件套（必建第 6 件 `canon_style`，style-card 实例化 draft、保留预置 15 条 LLM 腔黑名单；种子表/目录树/§3.1 映射/Manifest 种子 entries/回写顺序 SC_WB/伪代码/报告与自检同步，Gate 增 G14）；Adopt「已公开发布」正文注册 status 统一 **locked**（AD_3 + 材料映射表，原 canon；判据 = status==locked）；`continuity_facts` 全部更名 `facts`（canon_root 种子改名并注明正式承载位 = canon_continuity 卷分片、AD_3.5、材料映射、伪代码）；AD_3.5 增批级验收谓词（summary_after 非空 / fact 带 entity_ids / Thread 有 plant/advance 章号；FAIL 本批重跑不推进 adopt_cursor）；Status 种子对齐 asset-types 新键（`auto_promote.p4_canon_seed`、`web_serial.last_critic_chapter`、`flags.unattended_mode`）；第三波收尾（V1 复检修正：冷启动条件行/六件套允许集/小节指针/编号/口径对齐） |

---

*schema: project-scaffold rev 3 | 通用工程层 | 路径非唯一 | 对齐 protocol / asset-types / phase-contracts*
