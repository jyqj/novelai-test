# Runtime Protocol

> Agent 可执行运行时协议。  
> 管线：`intent → mode → load_policy → run → writeback`（落盘前过 `writeback-acceptance`）。  
> 本文件是 runtime 总控；阶段细节见 `phase-contracts.md`，类型系统见 `asset-types.md`，分歧见 `conflict-playbook.md`，术语 SSOT 见 `glossary.md`。  
> **扩展指针**：`new_project` → [`project-scaffold.md`](project-scaffold.md)；`route=web` → [`web-serial-playbook.md`](web-serial-playbook.md)；DONE 前 → [`writeback-acceptance.md`](writeback-acceptance.md)。

---

## 0. 硬约束

| ID | 规则 |
|----|------|
| C0 | 通用工程层 only：禁止绑定具体书名、角色名、作品目录作为规范正文 |
| C1 | `knowledge/` 只读服务；runtime 只引用 `K-xxx` ID，禁止复制大段理论 |
| C2 | 术语以 `glossary.md` 为唯一 SSOT；阶段文只引用不重定义 |
| C3 | 资产 `status` 枚举仅允许：`draft \| review \| canon \| locked \| stale \| archived` |
| C4 | 序列引用复合键 `{volume_id, sequence_index}`（速记 `v3:s12`），index `0–23`（含 0 = Hook）；洋葱五层 id：`surface/behavior/emotion/belief/wound`（表象/行为/情感/信念/创伤） |
| C5 | 先资产后知识；有 budget（`max_blocks` 块数上限 + 每块片段 ≤120 行）；感知 stale（按 intent 豁免，§4.4） |
| C6 | **仅 `diagnose` / `learn` 意图允许打开 `knowledge-index.md` 做检索路由**；其余意图禁止全文扫 knowledge。**例外**：`knowledge-blocks.md` 是 K-ID → 位置的**解析器**，任何 intent 均可只读查询（仅限解析白名单/用户点名的 K-ID 条目与锚点，禁止借机浏览目录扩集）；块定位用源文件内 `<!-- K-ID -->` 锚点 |
| C7 | 资产满足 contract `min_status` 即可作为下游输入执行，**无需当轮人工授权**。「授权」（`Decision.approved_by ∈ {user, agent_auto}`，级别表见 asset-types §2.4）仅约束三类动作：(a) `canon`/`locked` 晋升；(b) publish；(c) 破坏 locked / 砍 `must_not_drop` 线 / 推翻 `Canon.invariants`。critique 无执行权 |

---

## 1. 启动顺序（BOOT）

Agent 每次被调用必须按序执行，不可跳步。

```
BOOT_1  resolve_workspace
        → 定位 skill 根：skills/novel-writing-workflow/
        → 确认 runtime/ 七件套可读：protocol, phase-contracts, asset-types,
          conflict-playbook, glossary, writeback-acceptance（route=web 时 + web-serial-playbook）

BOOT_2  load_glossary_min
        → 装载 glossary 中的枚举与术语表（不装 knowledge 正文）

BOOT_3  detect_project_context
        → 若存在项目 Manifest → 读 manifest_root（分片设计见 asset-types §3）+ Status
        → write_unit / advance(P5/P6) 轮加读当前卷 manifest_units_v{n}；禁止全分片装载
        → 不读 decision 分片 manifest_decisions_v{n}（change/diagnose/审计轮按需加载，见 §1.1）
        → 若不存在 → project_state = NONE

BOOT_4  parse_user_utterance → Intent
        → 见 §2 intent 路由表；无法判定 → 向用户澄清，不擅自选 mode

BOOT_5  mode_enter(intent)
        → 绑定 LoadPolicy / Gate / Writeback 策略（§3–§6）

BOOT_6  preflight_checks
        → 检查 depends_on、stale 依赖（按 intent 豁免，§4.4）、locked 冲突、budget 上限
        → 失败 → BLOCK（§7），不进入 run

BOOT_7  load_policy.execute
        → 按 intent 召回必选资产 types；knowledge 仅在策略允许时按 ID 拉取

BOOT_8  run
        → 执行 mode 主循环（§8 伪代码）

BOOT_9  writeback
        → **先** [`writeback-acceptance.md`](writeback-acceptance.md)（learn 跳过）
        → PASS 后落盘资产 + 更新 Manifest + rev/status（§6）

BOOT_10 report
        → 向用户返回：产出摘要、status 变更、阻断项、下一步建议
```

### 1.1 启动最小装载（任何 intent 都先装）

| 优先级 | type | 条件 | 用途 |
|--------|------|------|------|
| 0 | Glossary | 始终 | 术语/枚举 SSOT |
| 1 | Manifest | 项目存在时 | `manifest_root`：注册表 + 卷分片指针（asset-types §3） |
| 2 | Status | 项目存在时 | 当前 phase、cursor、flags |
| 3 | Decision | 存在 open/recent 时 | 用户裁决与优先级覆盖；仅 manifest_root 内 open/active 条目——非 open 已迁 decision 分片（`manifest_decisions_v{n}`），BOOT 不读，`change`/`diagnose`/审计轮按需加载 |

**禁止**：BOOT 阶段读取 `knowledge-index.md` 或任意 `knowledge/**`（`diagnose`/`learn` 在 BOOT_7 之后按策略打开）。

---

## 2. Intent 路由

### 2.1 Intent 枚举

| intent | 别名/触发信号（示例） | 主目标 |
|--------|----------------------|--------|
| `new_project` | 从零开始、新建、初始化工作区 | **强制** [`project-scaffold.md`](project-scaffold.md)：Manifest/Status/Canon(seed)/Blueprint(draft) + Scaffold Gate；进入 P1 |
| `advance` | 继续下一阶段、推进大纲、做粗纲/序列… | 按 phase-contracts 推进一个 phase 单元 |
| `write_unit` | 写某章/某场景/某序列正文或细纲落地 | 在已有 plan 上产出可交付写作单元 |
| `diagnose` | 诊断、为什么不行、堵车、节奏/人物问题 | 症状→分类→K-ID 定位→方案，不默认改 canon |
| `change` | 改设定、推翻、同步、冲突、修订 | 变更传播 + 分歧裁决 + stale 标记 |
| `learn` | 学习某方法、解释 K-xxx、方法论 | 只读知识服务，不写项目资产 |

### 2.2 路由决策表

```
IF project_state == NONE:
  IF user wants create → new_project
  ELIF user wants methodology only → learn
  ELIF user describes symptom without project → diagnose (knowledge-only path)
  ELSE → ASK: 新建项目 / 纯学习 / 纯诊断？

IF project_state == EXISTS:
  IF utterance 含变更/冲突/推翻/同步 → change
  ELIF utterance 含症状/诊断/为什么/不通 → diagnose
  ELIF utterance 含学习/解释/方法论 → learn
  ELIF utterance 指向具体 unit（章/场景/序列写作）→ write_unit
  ELIF utterance 推进阶段或“继续” → advance
  ELSE → ASK 澄清 intent

# 复合流程/快径信号（先于上表判定；见 §2.4）
IF utterance 含 已有大纲/已有正文/接管/导入/迁移旧稿 → adopt（new_project 变体）
IF utterance 含 修订/二稿/beta 反馈/编辑意见/读者批评落地 → revise（组合流程）
IF utterance 含 发布/定稿/冻结第 N 章 → publish（write_unit 快径）
IF utterance 仅询问 进度/状态/到哪了 → report（只读快径）
```

### 2.3 Intent → Mode 绑定

| intent | mode | 默认可写 | 默认可读 knowledge | 打开 knowledge-index |
|--------|------|----------|--------------------|----------------------|
| `new_project` | MODE_INIT | Manifest, Status, Blueprint(draft), Canon(`canon_root` seed,draft), Canon(`canon_style` 空壳,draft), Recap(`recap_state` 空壳,draft)（六件套清单见 project-scaffold §2） | 否（phase budget 内可按 ID 拉） | **否** |
| `advance` | MODE_ADVANCE | 当前 phase 产出 types | 仅 contract.knowledge_budget 内 K-ID | **否** |
| `write_unit` | MODE_WRITE | SceneBeat/ChapterPlan/正文 unit | 仅 budget 内 K-ID | **否** |
| `diagnose` | MODE_DIAG | 默认可写 Decision/诊断记录；改 canon 需确认 | **是**（经 index 路由） | **是** |
| `change` | MODE_CHANGE | Decision + 目标资产 + 依赖 stale | 否（除非 diagnose 子流程） | **否**（冲突分类不靠 index） |
| `learn` | MODE_LEARN | **禁止**写项目资产 | **是** | **是** |

> **关键规则（C6）**：`knowledge-index.md` 是诊断/学习路由表，不是日常创作入口。`advance` / `write_unit` / `new_project` / `change` 只通过 phase-contract 或用户点名的 **K-ID** 拉取知识块，禁止“先翻 index 再创作”。K-ID → 位置解析一律查 `knowledge-blocks.md`（全 intent 只读可查）+ 源文件 `<!-- K-ID -->` 锚点。

### 2.4 复合流程与快径（不扩 intent 闭集）

下列高频场景**归并到六 intent 执行**，路由时优先识别；`session_report.intent` 填归并后的 intent。

| 流程 | 触发信号（例） | 分解 | 关键约束 |
|------|----------------|------|----------|
| **adopt** 接管已有稿 | 已有大纲/正文、导入、迁移、半路接管 | `new_project` 变体 → [`project-scaffold.md`](project-scaffold.md) **Adopt 模式**：脚手架四件套 + 既有材料逆向注册（status=review）+ 逐 phase dry-run gate 定位 `current_phase` | 未验证材料**禁止**直接标 canon；未注册材料不算存在 |
| **revise** 修订轮 | 修订、二稿、beta 反馈、编辑意见、读者批评落地 | ① `diagnose`：归因 + 批评记录登记（落点见 asset-types 工作记录节）→ ② 逐条 `Decision`（accept/reject）→ ③ 结构性改动走 `change`；纯文字修缮走 `write_unit`（repair）→ ④ 重跑受影响 gate | 批评稿无执行权（C7）；未合并批评 = `critique_unmerged`，禁止静默采纳 |
| **publish** 发布/定稿 | 发布第 N\[–M\] 章、定稿、冻结 | `write_unit` 快径：**仅 status 晋升 → `locked`（唯一默认；ready 存稿 review/canon → locked）** + Manifest touch（**publish=touch，rev 不递增**，`action=publish`）+ `Status.serial_cursor`/buffer 更新；内容零变更 | **发布顺序谓词**：目标必须是自 `last_published_chapter+1` 起的连续区间，乱序 → BLOCK `GATE_FAIL`（message 指出缺口章号）；须用户确认，支持**批量区间**（「发布第 N–M 章」一次确认覆盖全区间）；`auto_publish` 默认 false（开启后的自动发布协议见 web-serial-playbook §6.4）；**无需 Decision**（除非目标已是 locked 或伴随内容变更）；仍过 writeback-acceptance |
| **report** 进度查询 | 到哪了、进度、当前状态 | 只读快径：BOOT_1–3 → 汇报 `Status.phase/route/blockers` + Manifest 关键资产 status/stale + 下一步建议；**零 run、零 writeback** | 不进入 mode；不消耗 knowledge 预算 |

---

## 3. 状态机

### 3.1 项目级 phase

```
NONE
  └─(new_project ok)→ P1_BLUEPRINT
                        └─(gate pass)→ P2_ROUGH
                                         └─→ P3_SEQUENCE
                                               └─→ P4_DETAIL
                                                     └─→ P5_CHAPTER
                                                           └─→ P6_WRITING
                                                                 └─→ idle（维护态；Status.phase=idle）
```

| phase_id | 名称 | 主产出 types（见 asset-types） |
|----------|------|--------------------------------|
| P1 | Blueprint | Blueprint, Canon(canon_root seed 充实→review), Canon(canon_style→review) |
| P2 | Rough | PlotSpine, Character(core), WorldRule(frame), Thread(seed) |
| P3 | Sequence | SequenceMap (seq 0–23) |
| P4 | Detail | SceneBeat, Character(full), Thread(weave) |
| P5 | Chapter | ChapterPlan |
| P6 | Writing | ManuscriptUnit（正文单元；别名 ProseUnit） |

转换条件：**仅**当 `phase-contracts[phase].gate == PASS` 且无阻断级 stale 依赖时，`Status.current_phase` 才可 +1。

> **volume_checkpoint（卷末人工审计点）**：route=web 多卷连载下，`open_next_volume` 前必须产出卷报告（卷摘要 + 伏笔账 + 战力变化 + 残留 blockers，并生成 `recap_vol_{n}`）且获用户确认（`Decision(approved_by=user)`；`unattended_mode=true` 时降级为 `Decision(agent_auto, flags.pending_human_review=true)` 继续开卷）——每卷唯一强制人工节点；卷内写作不因该确认缺失而阻断。卷末同时把本卷非 open 的 Decision entries 从 manifest_root 迁入 `manifest_decisions_v{当前卷}`。细节见 web-serial-playbook。

### 3.2 资产 status 状态机

```
                  ┌──────────┐
                  │ archived │←──(显式归档/废弃：draft·review·canon 均可入)
                  └──────────┘
                       ↑
draft → review → canon → locked（=已发布/冻结；不参与 stale 传播）
  │        │        │
  ↓        ↓        ↓
  └────────┴──→  stale ←─(上游变更或冲突后标记；draft 亦可标；locked 例外→retcon_note)
                   │
                   └─(resync + re-gate PASS)→ 恢复 stale 前原 status（不视为晋升）
```

| status | 含义 | 可被下游 depends_on | 可直接用于写作执行 |
|--------|------|---------------------|--------------------|
| `draft` | 工作稿 | 否（除非 contract 允许 draft 输入） | 否 |
| `review` | 待确认 | **是（按 contract `min_status`）** | **是（作为输入）**；晋升/publish 仍需授权（C7） |
| `canon` | 已采纳 SSOT（章资产语义 = 已过 gate 的**存稿**，尚未发布） | 是 | 是 |
| `locked` | 已发布/冻结——**「已发布」判定全库唯一 = `status == locked`**（`last_published_chapter` 仅作游标不作判据） | 是 | 是；**不参与 stale 传播**——上游变更改写 `retcon_note` 入 `canon_continuity_v{n}`，后续章按 `forward_strategy` 向前兼容 |
| `stale` | 内容可能过期 | 否（阻断下游，按 intent 豁免见 §4.4） | 否 |
| `archived` | 历史保留 | 否 | 否 |

**晋升规则**：
- `draft → review`：作者/Agent 自检完成
- `review → canon`：用户确认、`Decision(approved_by=user|agent_auto)` 通过，或 gate PASS 后按 `Status.web_serial.auto_promote` 常任授权自动晋升（须写 `Decision(approved_by=agent_auto)` 留痕；级别表见 asset-types §2.4）
- `review|canon → locked`：publish（**唯一默认发布晋升**，顺序谓词见 §2.4）或显式锁定（防 change 误伤）
- 任意非 archived 非 locked → `stale`：上游 change 传播或冲突裁决后标记（**draft 亦可标 stale**；locked 改记 `retcon_note`）
- **stale 修复回位**：resync + re-gate PASS 后恢复到 stale 前原 status（canon 恢复 canon），**不视为晋升、无需授权**；若修复中内容实质变更 → 按上列晋升规则重走

> 章资产（ManuscriptUnit）状态链：`draft →(自检) review →(gate PASS 按 auto_promote.chapter_canon_on_gate_pass) canon（存稿）→(publish) locked（已发布）`。

### 3.3 Session 运行态

```
BOOT → READY → LOADING → RUNNING → WRITEBACK → DONE
                 │           │
                 │           ├─→ BLOCKED（§7；自愈范围内先自主恢复重试一次）→ 等待用户/Decision
                 │           └─→ CONFLICT_LOOP（conflict-playbook）
                 └─→ ABORT（preflight 失败且不可恢复）
```

---

## 4. 召回策略（LoadPolicy）

### 4.1 总原则

1. **先资产后知识**
2. **按 type 装载，不按目录全文拼接**：Manifest 只读 `manifest_root` + 当前卷分片（禁止全分片装载）
3. **有 budget**：`max_blocks` 块数上限 + 每块片段 ≤120 行；超限则降级（L1 摘要优先于 L2+）
4. **感知 stale**：`advance`/`write_unit` 的必召回集内有 `stale` → BLOCK 或强制 change 子流程；`change`/`diagnose`/`report` 豁免（§4.4）
5. **路径解耦**：只通过 Manifest 解析 type → 存储位置

### 4.2 按 intent 的必召回表

#### `new_project`

| 层 | types / 资源 | 必需 | budget 提示 |
|----|--------------|------|-------------|
| Asset | （无既有） | — | — |
| Runtime | protocol, **project-scaffold**, phase-contracts[P1], asset-types, glossary | 是 | 全量 runtime 元数据 |
| Runtime | **web-serial-playbook**（当网文信号 / 将设 `route=web`） | 条件 | Fast-Start 节奏 |
| Knowledge | 仅 P1 contract 列出的 K-ID（通常 L1–L2） | 按需 | `knowledge_budget.p1` |

> `run_init` **必须**按 [`project-scaffold.md`](project-scaffold.md) 完成 Scaffold Gate；未过不得宣称 `new_project` 成功或 `project_state=EXISTS`。

#### `advance`

| 层 | types | 必需 |
|----|-------|------|
| Asset | Status, manifest_root（P5/P6 轮加读当前卷 `manifest_units_v{n}`）, Decision(open) | 是 |
| Asset | phase.depends_on 全部 inputs（达 contract `min_status`；stale 仅校验本轮必召回集） | 是 |
| Asset | 当前 phase 已有 outputs（续写） | 若存在 |
| Knowledge | `phase-contracts[phase].knowledge_budget`：**core 按序必拉** + **situational 按触发标签拉**（phase-contracts §0.4.1） | 按 contract |
| Forbidden | knowledge-index 全文、无关 phase 知识 | 禁止 |

#### `write_unit`（**全库唯一召回 SSOT**：asset-types §6、web-serial-playbook 召回一律以本表为准）

| 层 | types / 切片 | 必需 |
|----|--------------|------|
| Asset | Status；manifest_root + 当前卷 `manifest_units_v{n}` | 是 |
| Asset | ChapterPlan（目标章，review+）；SceneBeat（本章场景） | 是 |
| Asset | Character（出场，canon）；WorldRule（触达，canon）；`canon_style`（文风卡） | 是 |
| Asset | Thread（active ∩ 当前卷 `volume_scope`，或 `waypoints` 命中本卷；paid_off/dropped 不召回） | 是 |
| Asset | `Canon.invariants` + `canon_continuity_v{当前卷}` + **实体检索**历史 facts（按本章出场 character/faction id 在历史卷分片中 rg）；命中带 `superseded_by` 的 fact **必须连带装载对应 retcon_note**，正文以 new_fact 为准 | 是——`canon_continuity_v{当前卷}` 为**条件行**：分片尚不存在时跳过（本卷尚无已确立 facts；首次 facts upsert 时创建并注册，初始 status=canon），存在则必装；历史分片实体检索同理（首卷天然为空） |
| Asset | Recap：`recap_state`（**必装**）；`recap_book` + `recap_vol_{当前卷-1}` 为条件行——尚不存在时跳过（首章/首卷豁免），存在则必装 | 是 |
| Asset | 前章 ManuscriptUnit：`summary_after` + 尾段 ≤500 字（条件行：首章豁免）；open Decision（恒必装） | 是 |
| Knowledge | **复用 P6 contract 预算**（core 见 phase-contracts §7.4）+ 按 unit 内容特征追加（下表）；上限 = P6 `max_blocks` | 可选，budget 紧 |
| Forbidden | 打开 knowledge-index；拉取整本序列 0–23 方法论；全分片 Manifest 装载 | 禁止 |

> **防剧透标注纪律**：召回 `Character.secrets`、fuse `hidden_info`、`spoiler_level>0` 的 facts 时，装载头加「以下信息读者未知，正文不得直说，只可写潜台词/征兆」。

**unit 内容特征 → 追加 K-ID（`unit_type` 闭集五值 `{dialogue, description, action, interior, exposition}`；判定优先按 `ChapterPlan.content_blocks` 主导类型，无 content_blocks 时按本表语义特征——contracts §0.4.1；此表与 phase-contracts P6 situational 同源一致）：**

| unit 特征 | 追加拉取 |
|-----------|----------|
| 对话密集（`unit_type=dialogue`） | `K-CHAR-013` |
| 描写/场面铺陈（`unit_type=description`） | `K-WRITE-017` + `K-WORLD-010` |
| 战斗/动作/强转折（`unit_type=action`） | `K-WRITE-019` |
| 情感/内心戏（`unit_type=interior`） | `K-CHAR-006` |
| 章内节奏/微结构 | `K-WRITE-020` |
| 解说/信息重章（`unit_type=exposition`） | `K-WRITE-002`, `K-WRITE-006` |
| 章末钩子（route=web） | `K-WRITE-011` |
| 文风/口癖自检（critic 轮或每 5 章） | `K-WRITE-018`, `K-WRITE-021`, `K-CHAR-013`, `K-WRITE-022` |
| 文风/意象打磨轮 | `K-WRITE-009`, `K-WRITE-015` |

#### `diagnose`（唯一默认走 index 的创作相关意图）

| 层 | 资源 | 必需 |
|----|------|------|
| Asset | Status, Manifest, 相关资产切片、Thread、Decision（**stale 豁免**：可装载 stale 资产供诊断） | 尽量 |
| Index | **`knowledge-index.md`**（场景索引/诊断表） | **是** |
| Knowledge | index 定位到的 K-ID → `diag_budget`：**max_blocks 6，深度 L1→L2**（L3/L4 仅用户要深挖；learn 同此预算） | 是 |
| Output | 诊断记录（可 draft）；方案；**不**自动改 canon | — |

诊断子流程：

```
symptom → classify(domain)
       → open knowledge-index (场景索引)
       → map to K-IDs
       → fetch knowledge by ID (depth ladder L1→L2→…)
       → compare with project assets (if any)
       → emit DiagnosisReport + optional Decision request
```

#### `change`

| 层 | types | 必需 |
|----|-------|------|
| Asset | 变更目标 + Manifest 依赖图 + Decision | 是 |
| Asset | 全部直接依赖 / 被依赖节点（**stale 豁免**：change 轮可装载 stale 资产） | 是 |
| Asset | 非 open Decision 历史：`manifest_decisions_v{n}` 分片 | 按需（BOOT 不读；追溯历史裁决时加载） |
| Runtime | conflict-playbook | 是 |
| Knowledge | 默认否 | — |

变更流水线（摘要，细节见 conflict-playbook）：

```
detect → classify(taxonomy) → decide(priority) → record(Decision)
      → mark_deps_stale → sync | block
```

taxonomy：`vertical_drift | lateral_conflict | version_skew | intent_gap | critique_unmerged`

#### `learn`

| 层 | 资源 | 必需 |
|----|------|------|
| Index | knowledge-index / knowledge-blocks | 是 |
| Knowledge | 用户主题对应 K-ID | 是 |
| Asset | 禁止写入 | — |

### 4.3 Knowledge 拉取规则（所有 mode 共用）

```
function fetch_knowledge(k_ids, depth_cap, budget):
  assert all ids match /^K-[A-Z]+-\d{3}$/
  if mode not in {MODE_DIAG, MODE_LEARN}:
    assert k_ids ⊆ (contract.core ∪ contract.situational[*].pull ∪ user_named)
  # 优先级：contract.core 按序 > 上轮 knowledge_deferred 补拉（contracts §0.4）> 已触发 situational 按声明序 > user_named
  for id in k_ids ordered by priority:
    if budget.blocks_used >= budget.max_blocks: break
    entry = resolve(knowledge-blocks.md, id)     # 解析器：任何 intent 可只读查询
    loc   = rg("<!-- " + id + " -->", knowledge/) # 源文件锚点定位（可多处）
    load_fragment(loc, until=next_anchor_or_section_end, max_lines=120)  # 每块片段 ≤120 行
    budget.blocks_used += 1
  return loaded
```

- **预算语义**：只计**块数**（`max_blocks`）+ 每块片段 ≤120 行；无 token 计数
- **深度梯子 = 阅读提示**（非物理分段）：默认 L1；执行步骤升 L2；原理争执升 L3；案例升 L4（需用户要或 diagnose 明确需要）。L1 定义/表格；L2 步骤/清单；L3 原理；L4 案例——各块内容提示见 knowledge-blocks
- **禁止**：把知识库当上下文预热；以「顺便读完整个知识文件」绕过预算；复制 knowledge 正文进 runtime 文档

### 4.4 Stale 感知（按 intent 豁免）

| 检测点 | 动作 |
|--------|------|
| `advance`/`write_unit`：**本轮必召回集内** input.status == stale | BLOCK `STALE_INPUT`（集外 stale 仅在报告提示，不阻断） |
| `change`/`diagnose`/`report`：装载到 stale 资产 | **豁免**——照常装载，在报告中标注，不 BLOCK |
| 必召回 input 缺失 | BLOCK `MISSING_INPUT` |
| input.status 低于 contract `min_status` | BLOCK `INPUT_NOT_CANON` |
| locked 目标被 change 请求修改 | BLOCK `LOCKED_TARGET`（需先 unlock `Decision(approved_by=user)`） |
| 上游变更触及 locked 资产 | 不标 stale；写 `retcon_note` 入 `canon_continuity_v{n}`（D3.2，见 conflict-playbook） |

---

## 5. 优先级链（裁决时）

从高到低：

1. **用户当轮显式指令**
2. **Decision**（已记录且 open/accepted）
3. **Canon.invariant**
4. **更高 phase 且 locked/canon 的资产**（防下游推翻上游，除非 vertical change）
5. **当前 working 产出（draft/review）**
6. **critique / 外部意见**（无执行权，除非合并为 Decision）

> `Decision.approved_by ∈ {user, agent_auto}`：user 高于 agent_auto；`agent_auto` 仅对 asset-types §2.4 允许表内的动作有效，越权自批无效，须升级 user。

---

## 6. 回写（Writeback）

> **验收 SSOT**：[`writeback-acceptance.md`](writeback-acceptance.md)。每轮（`learn` 除外）在持久化前跑全局 MUST M01–M13 + intent 额外 MUST；FAIL → 不落 contested、不假装 DONE。

### 6.1 回写事务顺序

```
WB_1  validate_outputs_against_contract   # schema / 必填字段
WB_2  conflict_scan                       # 与 canon/locked 快速比对
WB_3  if conflict → CONFLICT_LOOP; abort write of contested fields
—— writeback-acceptance（M* 全集；FAIL 则中止）——
WB_4  assign_rev                          # rev = prev+1；写 updated_at
WB_5  set_status                          # 默认 draft；用户确认可 review/canon
                                          # publish 例外：仅 status 晋升 →locked（唯一默认），
                                          # touch 不递增 rev（跳过 WB_4 的 rev+1），action=publish
WB_6  persist_assets                      # 经 Manifest 解析路径
WB_7  update_manifest                     # 注册/更新 type, rev, status, deps
WB_8  update_status_cursor                # phase, unit pointer, flags
WB_9  propagate_stale_if_needed           # 仅 change 或破坏性 advance
WB_10 emit_writeback_report               # 对齐 acceptance §4 session_report
```

### 6.2 按 intent 的默认可写范围

| intent | 允许写入 | 禁止 |
|--------|----------|------|
| `new_project` | Manifest, Status, Blueprint(draft), Canon(`canon_root` seed,draft), Canon(`canon_style` 空壳,draft), Recap(`recap_state` 空壳,draft)（六件套，见 project-scaffold §2） | knowledge/**, 未声明 types |
| `advance` | 当前 phase outputs；Status；Manifest | 跳 phase 写下游；未 gate 改 current_phase |
| `write_unit` | 目标 ManuscriptUnit；局部 SceneBeat 注释；Thread 进度；Recap（`recap_state` 重写 + `recap_book` 滚动追加）；`canon_continuity_v{n}` facts 追加（`continuity_delta` 入卷分片）；Status 指针（`serial_cursor`/`buffer`/`last_writeback`/`active_unit`/`last_critic_chapter`）；Manifest touch（root + 当前卷分片）；`ChapterPlan.serial_notes.payoff_entries[].realized` 同步（**仅此字段**） | 擅自改 PlotSpine/SequenceMap canon；ChapterPlan 其余字段 |
| `diagnose` | DiagnosisReport(draft)；可选 Decision 草案 | 自动晋升 canon；静默改设定 |
| `change` | 目标资产 + Decision + 依赖 stale 标记 + Manifest | 无 Decision 改 locked；删 knowledge |
| `learn` | **无**（可会话内说明，不落项目资产） | 任何项目资产 |

### 6.3 rev / status 字段最小集

每个可版本资产必须可序列化出：

```yaml
id: string
type: AssetType
rev: int              # 单调递增
status: draft|review|canon|locked|stale|archived
deps: [asset_id...]   # 用于 stale 传播
updated_at: iso8601
```

### 6.4 Gate 与 current_phase

- Gate 定义在 `phase-contracts.md`（checklist → 可判定 PASS/FAIL）
- `on_fail`：默认 BLOCK，保留 draft 产出，不升 phase
- 仅 `gate==PASS` 且用户未要求停留时，`Status.current_phase` 前进

---

## 7. 阻断（BLOCK）

### 7.1 阻断码

| code | 含义 | 恢复动作 | 自愈 |
|------|------|----------|------|
| `MISSING_MANIFEST` | 需要项目上下文但不存在 | `new_project` 或指定项目 | 需 user |
| `MISSING_INPUT` | depends_on 资产缺失 | 回退 advance 补齐 / 用户提供 | 自主（须用户提供材料时转 user） |
| `STALE_INPUT` | 依赖过期 | `change` resync 或接受风险的 Decision | 自主（resync 回位见 §3.2）；接受风险需 user |
| `INPUT_NOT_CANON` | 输入低于 contract `min_status` | 晋升输入至 `min_status`（按 §3.2 晋升规则） | 自主（draft→review 自检）；canon 晋升按授权表 |
| `GATE_FAIL` | phase gate 未过 | 按 on_fail 清单修补 | 自主（repair；重试上限见 contracts §0.5） |
| `LOCKED_TARGET` | 试图修改 locked | unlock Decision | 需 user |
| `BUDGET_EXCEEDED` | 知识/上下文超限 | 知识侧：降深度、减块数；资产侧：切窗到当前卷分片、缩小召回集、分轮 | 自主 |
| `SCAFFOLD_INCOMPLETE` | 脚手架强制产物缺失 / Scaffold Gate 未过（定义见 project-scaffold） | 补齐脚手架清单后重跑 gate | 自主 |
| `AMBIGUOUS_INTENT` | 路由失败 | 澄清问题 | 需 user |
| `CONFLICT_UNRESOLVED` | 分歧未裁决 | conflict-playbook decide | 授权表内可自裁则自主，否则需 user |
| `KNOWLEDGE_INDEX_FORBIDDEN` | 非 diagnose/learn 试图扫 index | 改用 contract K-ID 或转 diagnose | 自主 |
| `WRITE_SCOPE_VIOLATION` | 超出 intent 可写范围 | 缩小写入或切换 intent | 自主（缩小写入） |

### 7.2 阻断时 Agent 行为

自愈范围以 §7.1「自愈」列为准：恢复动作须同时落在本 intent 可写范围（§6.2）∩ 授权表 agent_auto 范围（asset-types §2.4）内。

```
on_BLOCK(code, detail):
  if 恢复动作 ∈ (本 intent 可写范围 ∩ agent_auto 授权范围):
    本轮自主执行该恢复动作并重试一次（仅一次；session_report 记录自愈尝试）
    if retry PASS: 恢复正常流程
  # 重试仍 FAIL，或恢复动作需 user 授权：
  persist nothing contested
  report:
    - code + 人话说明（含自愈尝试与结果，若有）
    - 缺失/冲突的 asset_id 列表
    - 建议的下一 intent 与最小动作
  await user_or_decision
  do NOT pretend success
```

---

## 8. Agent 主循环伪代码

```
function main(user_utterance, workspace):
  # —— BOOT ——
  skill_root = resolve_skill_root(workspace)
  assert_readable(skill_root / "runtime" / {
    "protocol.md", "phase-contracts.md", "asset-types.md",
    "conflict-playbook.md", "glossary.md", "writeback-acceptance.md"
  })  # 七件套；route=web 再加 web-serial-playbook.md
  glossary = load_min(skill_root / "runtime/glossary.md")
  manifest, status = try_load_project_assets()  # 只读 manifest_root；may be null
  intent = route_intent(user_utterance, manifest)  # 快径信号（§2.4）先判：publish/report/adopt/revise
  if intent == AMBIGUOUS: return ask_clarify()

  mode = bind_mode(intent)
  policy = LoadPolicy.for(intent, status)

  # —— PREFLIGHT（stale 检查按 intent，D3.3）——
  check = preflight(policy, manifest, status)
  if check.blocked: return block_report(check)

  # —— LOAD ——
  ctx.assets = load_assets(policy.required_types, manifest)  # write_unit/advance(P5/P6) 加读当前卷 manifest_units_v{n}
  if intent in {advance, write_unit} and any_stale(ctx.assets.required):
    return block_report(STALE_INPUT)   # 仅本轮必召回集；change/diagnose/report 豁免（§4.4）

  ctx.knowledge = []
  if intent in {diagnose, learn}:
    index = open(skill_root / "knowledge-index.md")   # 仅此二意图
    k_ids = route_via_index(index, user_utterance, ctx.assets)
    ctx.knowledge = fetch_knowledge(k_ids, depth_cap=policy.depth, budget=policy.budget)
  else:
    k_ids = phase_or_unit_contract_k_ids(intent, status)
    ctx.knowledge = fetch_knowledge(k_ids, depth_cap=policy.depth, budget=policy.budget)
    # 禁止 open knowledge-index

  # —— RUN ——
  # route=web 或网文信号：装载 web-serial-playbook（Fast-Start / buffer / serial_loop）
  result = match intent:
    case new_project: run_init(ctx, user_utterance)  # → project-scaffold（强制）
    case advance:     run_advance(ctx, phase_contracts[status.current_phase])
    case write_unit:
      if fastpath == publish:   # §2.4 批量快径：确认一次「第 N–M 章」
        assert_contiguous_from(last_published_chapter + 1)     # 发布顺序谓词；乱序 BLOCK GATE_FAIL（指出缺口章号）
        run_publish(ctx, parse_chapter_range(user_utterance))  # 逐章 touch 晋升 locked（唯一默认），rev 不递增
      else:
        run_write_unit(ctx, target_unit(user_utterance, status))
    case diagnose:    run_diagnose(ctx, user_utterance)
    case change:      run_change(ctx, user_utterance)  # → conflict-playbook
    case learn:       run_learn(ctx, user_utterance)

  if result.blocked: return block_report(result.block)

  # —— WRITEBACK ——
  if intent == learn:
    return present(result)  # no asset write
  accept = writeback_acceptance(result.outputs, intent, manifest, status)  # writeback-acceptance.md
  if accept.verdict == FAIL: return block_report(accept)
  wb = writeback(result.outputs, intent, manifest, status)
  if wb.blocked: return block_report(wb)
  if intent == write_unit and fastpath != publish:
    update_recap()  # Recap 更新点：recap_state 重写 + recap_book 滚动追加（acceptance W8）；
                    # 卷末 volume_checkpoint 另生成 recap_vol_{n}
  return present(result, wb)
```

### 8.1 `run_advance` 骨架

```
function run_advance(ctx, contract):
  assert all(contract.depends_on satisfied in ctx.assets)
  assert not blocked_by_stale(contract.inputs)
  draft_outputs = produce(contract.outputs, ctx)
  gate = evaluate_gate(contract.gate, draft_outputs, ctx)
  if gate.fail:
    return Block(GATE_FAIL, gate.failures) with draft_outputs kept as draft
  return Outputs(draft_outputs, next_phase=contract.on_pass.next)
```

### 8.2 `run_diagnose` 骨架

```
function run_diagnose(ctx, utterance):
  symptom = extract_symptom(utterance)
  domain = classify_symptom(symptom)   # structure|character|conflict|world|craft|webnovel|...
  k_ids = map_index(ctx.index, domain, symptom)  # 必须经 knowledge-index
  knowledge = fetch_knowledge(k_ids, depth_cap=L2, budget=diag_budget)
  findings = compare(knowledge, ctx.assets)  # 有项目则对照资产
  report = DiagnosisReport(symptom, domain, k_ids, findings, actions)
  # 默认不写 canon；若 actions 含改设定 → 建议切换 change
  return report
```

### 8.3 `run_change` 骨架

```
function run_change(ctx, utterance):
  delta = parse_change_request(utterance)
  conflicts = detect(ctx.assets, delta)
  for c in conflicts:
    class = classify(c)  # taxonomy
    decision = decide(c, priority_chain)  # §5；或 BLOCK 等用户
    record(Decision, decision)
  apply_allowed(delta, decisions)
  mark_deps_stale(affected_subgraph)
  return ChangeReport(...)
```

---

## 9. 与其它 runtime 文件的接口

| 文件 | 本协议依赖的内容 |
|------|------------------|
| `phase-contracts.md` | 每 phase 的 `depends_on / inputs / outputs / gate / on_fail / knowledge_budget` |
| `asset-types.md` | type 定义、必填字段、deps 语义、与路径解耦的 Manifest 约定 |
| `conflict-playbook.md` | detect→classify→decide→record→stale→sync\|block 全流程与 taxonomy |
| `glossary.md` | 术语 SSOT（洋葱五层、序列 0–23、status 枚举、phase 名等） |
| `project-scaffold.md` | **`new_project` / MODE_INIT 强制脚手架**与 Scaffold Gate |
| `web-serial-playbook.md` | **`route=web` 节奏**：Fast-Start、存稿 buffer、发布就绪、连载循环 |
| `writeback-acceptance.md` | **DONE 前** writeback 硬验收（M* / WB_* / session_report） |

本文件 **不** 复制上述文件的字段表；冲突时以各文件职责域为准，术语以 glossary 为准。

---

## 10. 快速合规检查（Agent 自检）

DONE 验收唯一权威 = [`writeback-acceptance.md`](writeback-acceptance.md)（全局 MUST M01–M13 + intent 额外 MUST + session_report）；本清单只留 protocol 独有项：

- [ ] intent 已显式绑定；复合流程信号（adopt/revise/publish/report）先于六 intent 判定（§2.4）
- [ ] BOOT_1–7 按序执行：七件套可读；非 diagnose/learn **未**打开 knowledge-index（knowledge-blocks 仅作 ID 解析）
- [ ] 召回按 §4.2 SSOT：core 必拉 + situational 按触发；块数 ≤ max_blocks、每块 ≤120 行
- [ ] stale 检查按 intent 豁免（§4.4）：advance/write_unit 仅限本轮必召回集
- [ ] BLOCK 处置按 §7.2：自愈范围内已自主重试一次；未假装 success

---

## 11. 修订

| rev | 说明 |
|-----|------|
| 1 | 初版：BOOT、六意图路由、状态机、召回、回写、阻断、伪代码 |
| 2 | 接线：new_project→project-scaffold；web→web-serial-playbook；DONE→writeback-acceptance |
| 3 | 知识调用落地：C6 增加 knowledge-blocks 解析器例外 + 锚点检索；budget 分 core/situational；write_unit 绑定 P6 预算 + unit_type 映射。新增 §2.4 复合流程快径（adopt/revise/publish/report）；idle 命名对齐 asset-types |
| 4 | 对齐 2026-08-12 决策书：C7 改 min_status + 三类授权动作；BOOT 七件套 + manifest_root/卷分片读取；publish 批量区间 + touch 不递增 rev；§3 review/locked 语义（retcon_note）+ auto_promote 晋升 + volume_checkpoint；§4.2 write_unit 召回 SSOT 重写（Recap/canon_style/实体 facts/summary_after/防剧透标注）+ unit_type 表更新；预算改块数+行数、深度=阅读提示；§4.4 stale 按 intent 豁免；补 SCAFFOLD_INCOMPLETE / diag_budget；§8 stale preflight 内移 + publish 分支 + Recap 更新点 |
| 5 | 2026-08-13 修复轮：publish = 晋升 locked（唯一默认，rev 不递增）+ 发布顺序谓词（§2.4/§8）；§3.2 章状态链（canon=存稿）、「已发布」= status==locked、draft→stale 边、stale 修复回位不算晋升；§1.1/§4.2/BOOT_3 decision 分片按需加载；§3.1 P1 行补 Canon(seed→review)+canon_style、卷末 Decision 迁分片；§4.2 Recap/前章条件行（首章/首卷豁免）+ superseded_by 连带装载注；unit_type 五值闭集 + critic 轮四块 + 对话行改 K-CHAR-013；§6.2 write_unit 允许集显式收编（Status 指针/Manifest touch/payoff realized）；§7 BLOCK 自愈语义 + 自愈列；§10 压缩指针化；第三波收尾（V1 复检修正：冷启动条件行/六件套允许集/小节指针/编号/口径对齐） |
