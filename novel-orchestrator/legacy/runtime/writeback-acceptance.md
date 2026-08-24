# Writeback Acceptance — 每轮回写硬验收

> **定位**：`writeback` 步骤的可判定硬门禁（PASS / FAIL）。  
> **指针**：事务顺序与默认可写范围见 [`protocol.md`](protocol.md) **§6**（`WB_1`…`WB_10`）；本文件只定义**验收谓词**与报告字段，不重定义状态机。  
> **依赖**：`asset-types.md`（信封/最小字段）、`phase-contracts.md`（gate/边界）、`conflict-playbook.md`（冲突未决时阻断）、`glossary.md`（术语 SSOT）。  
> **范围**：通用工程层 only；禁止绑定具体书名/角色/作品目录。  
> **知识**：仅允许资产字段中引用 `K-xxx` ID，禁止粘贴理论长文。

---

## 0. 何时执行

```
AFTER run(mode) returns outputs
IF intent == learn:
  SKIP writeback_acceptance   # 禁止写项目资产；仅会话呈现
ELSE:
  accept = writeback_acceptance(outputs, intent, manifest, status)
  IF accept.verdict == FAIL:
    abort persist of contested assets   # 对齐 protocol §7 on_BLOCK
    emit session_report with fail_codes
  ELSE:
    execute protocol §6 WB_4…WB_9
    emit session_report
```

| 规则 | 说明 |
|------|------|
| 时机 | 每轮 `run` 结束后、**持久化前**必跑（`learn` 除外） |
| 粒度 | **一轮 intent 一次**；多资产打包验收，任一条 MUST 失败 → 整轮 FAIL（除非标注 `partial_ok` 且用户当轮授权） |
| 与 phase gate | phase-contracts `gate` 管**内容合格**；本文件管**落盘合规**（信封、范围、Manifest、术语、冲突） |
| 与 BLOCK | 验收 FAIL 使用 §3 FAIL 码；可映射到 protocol §7 阻断码（见 §3.2） |
| 复合流程 | adopt/revise/publish（protocol §2.4）按**归并后的 intent** 走对应 MUST；`report` 快径零写 → 不进验收。publish 为 status-only 晋升 → **`locked`（唯一默认）**：touch，**rev 不递增**（M03 publish 例外），仍须 M05 / M06；用户确认（支持「第 N–M 章」批量区间一次确认）即满足「非静默晋升」 |

### 0.1 硬约束对齐（不得分叉；枚举/召回指针化）

| 项 | 合法值 / 指针 |
|----|--------|
| `status` / 洋葱层 id / 序列复合键 | 以 `glossary.md` 枚举为准（status 六值；洋葱 `surface…wound`；序列 `{volume_id, sequence_index}`，index `0..23` 含 Hook） |
| type 闭集与别名归一 | 以 `asset-types.md` §0.3 为准（`ProseUnit→ManuscriptUnit`；`ThreadMap`/`ForeshadowLedger` 禁独立注册） |
| 召回集 | 以 `protocol.md` §4.2 为准（全库唯一召回 SSOT；本文件不定义召回） |
| intent 闭集 | `new_project \| advance \| write_unit \| diagnose \| change \| learn`（不变；复合流程归并见 protocol §2.4） |

---

## 1. 全局 MUST 表（每轮 writeback，learn 除外）

凡本轮有**任何**项目资产写入意图，下列全部为 `must`。任一项 FAIL → 禁止宣称写回成功。  
标 **[脚本]** 的项可由 `tools/validate.py --project` 机器判定；环境不可运行时按手工清单逐项勾选。

| ID | MUST | 可判定检查 | [脚本] | FAIL 码 |
|----|------|------------|--------|---------|
| **M01** | intent 可写范围内 | 每个待写 `type` ∈ protocol §6.2 该 intent 允许集（write_unit 按收编后允许集判定：含 Status 指针 / Manifest touch / `ChapterPlan.serial_notes.payoff_entries[].realized`）；无 `knowledge/**` 写 | — | `WB_SCOPE` |
| **M02** | 类型合法且归一 | `type` ∈ AssetType 闭集；别名已归一（`ProseUnit→ManuscriptUnit` 等，见 asset-types §0.3.1） | ✓ | `WB_TYPE` |
| **M03** | 通用信封齐全 | 每资产具备：`id`, `type`, `rev`, `status`, `updated_at`；语义写回后 `rev = prev+1`（新建 `rev≥1`）。**publish 例外**：仅 status 晋升 → `locked`（唯一默认），touch 不递增 rev，`action=publish` | ✓ | `WB_ENVELOPE` |
| **M04** | status 枚举闭集 | `status` 仅六值；口头词已规范化（初稿→`draft` 等，glossary §6.3） | ✓ | `WB_STATUS` |
| **M05** | locked / archived 保护 | 目标原 `status∈{locked,archived}` 时：有 `Decision` unlock/允许 或用户当轮显式授权，并已 record | ✓ | `WB_LOCKED` |
| **M06** | Manifest 同步 | 写前 `asset_id ∈ Manifest.entries`（root 或对应卷分片；或同事务 `manifest_register`）；写后 `entries[].rev/status` 与信封一致 | ✓ | `WB_MANIFEST` |
| **M07** | Status 指针更新 | 成功写回后更新 `Status`：`last_writeback.{asset_id,rev,at}`；必要时 `phase` / `active_unit` / `blockers` | ✓ | `WB_STATUS_PTR` |
| **M08** | deps 可解析 | `depends_on` / `deps` 引用的 id 均在 Manifest 或本轮新建集；无悬空边 | ✓ | `WB_DEPS` |
| **M09** | 冲突扫描通过 | 与 `canon`/`locked` 无未裁决矛盾；blocking 冲突须先 Decision（conflict-playbook） | — | `WB_CONFLICT` |
| **M10** | 术语规范化 | 洋葱层 / 序列复合键 / 元素类 / status 已 `normalize_terms`（glossary §11）；无 `trauma` 作洋葱键 | ✓ | `WB_TERM` |
| **M11** | 无 knowledge 污染 | 资产正文/规范区未粘贴 knowledge 长文；知识引用仅 `knowledge_refs: [K-…]` 形 | — | `WB_KNOWLEDGE` |
| **M12** | 最小字段可门禁 | 本轮主产出 type 的 asset-types「最小字段」齐全（缺字段不得标 `review+` 假装可 gate） | ✓ | `WB_SCHEMA` |
| **M13** | 写回报告可生成 | 能产出 §4 会话结束报告最小字段（即使 FAIL 也要报告） | — | `WB_REPORT` |

### 1.1 事务序（验收插入点）

对齐 protocol §6.1，验收切面：

```
WB_1  validate_outputs_against_contract   → M01 M02 M12
WB_2  conflict_scan                       → M09
WB_3  if conflict → CONFLICT_LOOP         → FAIL WB_CONFLICT（contested 不落盘）
—— acceptance gate（本节 M* 全集）——
WB_4  assign_rev                          → M03
WB_5  set_status                          → M04 M05
WB_6  persist_assets                      → M10 M11（落盘内容）
WB_7  update_manifest                     → M06 M08
WB_8  update_status_cursor                → M07
WB_9  propagate_stale_if_needed           → 见 intent MUST（change / 破坏性 advance）
WB_10 emit_writeback_report               → M13 + §4
```

**默认落盘 status**：未用户确认时主产出 ≤ `draft` 或 contract 允许的 `review`；**禁止**无确认静默升 `canon`/`locked`（`diagnose` 尤严）。**例外（满足非静默要求）**：按 `Status.web_serial.auto_promote` 配置的晋升（`p4_canon` / `p4_canon_seed` / `chapter_canon_on_gate_pass` / `facts_upsert`）且已写 `Decision(approved_by=agent_auto)` 留痕 = 满足；publish 之用户会话确认 = 满足。

### 1.2 豁免与降级

| 情况 | 规则 |
|------|------|
| `intent=learn` | 整表跳过；若误写资产 → `WB_SCOPE` |
| 仅会话说明、零资产变更 | 可不跑 M06–M08；须在报告 `assets_written=[]` |
| gate 内容 FAIL 但保留 draft | 允许落 `draft` + `phase_gate=failed`；**禁止**升 `current_phase`；报告 `gate_result=FAIL` |
| 用户当轮 `partial_ok` | 仅非 contested 资产可写；contested 仍 FAIL 分项列出 |

---

## 2. 按 intent 额外 MUST

在 §1 全局 MUST 之上叠加。未列出的 intent 无额外条（仍受 §1 约束）。

### 2.1 `new_project`

| ID | MUST | FAIL 码 |
|----|------|---------|
| **N1** | 本轮创建或 upsert：`Manifest`（`manifest_root`）、`Status`（`status_project`） | `WB_INIT_CORE` |
| **N2** | 至少注册 `Blueprint`（可为 `draft`）；`Status.phase` ∈ {`P1`, 契约等价} | `WB_INIT_BP` |
| **N3** | 禁止写入 P3+ 主产出冒充初始化（`SequenceMap` / `SceneBeat` / `ChapterPlan` / `ManuscriptUnit` 完整定稿链） | `WB_SCOPE` |
| **N4** | `Manifest.entries` 含 Status/Manifest 自描述条目（asset-types AT4） | `WB_MANIFEST` |

### 2.2 `advance`

| ID | MUST | FAIL 码 |
|----|------|---------|
| **A1** | 写入 types ⊆ 当前 `phase-contracts[phase].outputs`（+ Status/Manifest）；禁止跳 phase 写下游主产出 | `WB_SCOPE` |
| **A2** | 若声称 phase 前进：`gate==PASS` 且 depends_on 输入无 `stale`、达 `min_status` | `WB_GATE` |
| **A3** | gate FAIL：可保留 draft outputs，**不得** `Status.phase` 前进；`phase_gate=failed` 或 blockers 含 `GATE_FAIL` | `WB_GATE` |
| **A4** | 尊重硬边界：P2 产出无场景级字段；P3 无 ChapterPlan 字段；P6 路径不得静默改 PlotSpine/SequenceMap/Character/WorldRule canon | `WB_BOUNDARY` |
| **A5** | 涉及序列的产出：索引覆盖约定满足 contract（P2 `nodes` 0..23；P3 `sequences` 索引语义 0..23） | `WB_SEQ` |
| **A6** | 破坏性改上游已依赖节点时：已 `mark_stale` 下游或显式 Decision 接受风险 | `WB_STALE_PROP` |

### 2.3 `write_unit`

| ID | MUST | [脚本] | FAIL 码 |
|----|------|--------|---------|
| **W1** | 主产出为 `ManuscriptUnit` 和/或 局部 `SceneBeat` 注释 / `Thread` 进度；Recap、facts 追加、Status 指针、Manifest touch、`ChapterPlan.serial_notes.payoff_entries[].realized`（仅此字段）同属允许集（protocol §6.2 收编），不判 `WB_SCOPE`；禁止擅自改 `PlotSpine` / `SequenceMap` canon | — | `WB_SCOPE` |
| **W2** | `ManuscriptUnit.chapter_plan_id`（或等价）可解析到 Manifest 中 `ChapterPlan` | ✓ `--project` deps 解析（chapter_plan_id ∈ Manifest） | `WB_DEPS` |
| **W3** | 召回依赖中无未处理 `stale` 作为唯一事实源（否则应已 BLOCK，不得假写成功） | — | `WB_STALE` |
| **W4** | 未引入与 `Character`/`WorldRule` canon 冲突的新设定；必要新增 → 应转 `change`，本轮不得静默写入设定 canon | — | `WB_CANON_DRIFT` |
| **W5** | `Status.active_unit` / 写作指针与本轮 unit 一致（`last_written` 类字段若存在则更新） | ✓ `--project` Status 指针一致性（active_unit/last_written） | `WB_STATUS_PTR` |
| **W6** | `summary_after` 与 `continuity_delta` 非空（P6 产出必填；delta 入 `canon_continuity_v{n}` 卷分片） | ✓ `--project` ManuscriptUnit.summary_after 非空 | `WB_SCHEMA` |
| **W7** | `evidence_checks` 每条含正文摘引 quote（≤30 字）+ 一句论证（替代 bool 自评） | 部分：quote 为正文子串 → `--project`（body 可读时）；论证句人工 | `WB_SCHEMA` |
| **W8** | `recap_state` 已更新（`recap_book` 已滚动追加；快照与本章写后现状一致） | ✓ `--project` Recap.covers_chapters 上界 ≥ Status.last_written | `WB_STATUS_PTR` |

### 2.4 `diagnose`

| ID | MUST | FAIL 码 |
|----|------|---------|
| **D1** | 默认可写：诊断记录（draft）和/或 `Decision` **草案**；**禁止**自动把业务资产升 `canon` | `WB_PROMOTE` |
| **D2** | 禁止静默改 `PlotSpine` / `SequenceMap` / `Character` / `WorldRule` / `Canon.invariant` 正文 | `WB_SCOPE` |
| **D3** | 若产出建议改设定：报告中 `next_intent_hint=change`，且本轮无执行设定写 | `WB_REPORT` |
| **D4** | 诊断引用知识仅 `K-xxx`；不把 K 正文写入项目 SSOT | `WB_KNOWLEDGE` |

### 2.5 `change`

| ID | MUST | FAIL 码 |
|----|------|---------|
| **CH1** | 存在本轮 `Decision` 记录（至少 `review`；blocking 冲突不得无 Decision 结束）；`approved_by ∈ {user, agent_auto}` 且动作在授权级别表内（asset-types §2.4；`agent_auto` 越权 = 非法） | `WB_DECISION` |
| **CH2** | `Decision.affects_asset_ids` / `impact.mark_stale` 与真实 touch 集一致 | `WB_DECISION` |
| **CH3** | 按 conflict-playbook impact：应 stale 的下游已 `status=stale` 且 `stale_reason` 非空；locked 下游不标 stale，改写 `retcon_note` | `WB_STALE_PROP` |
| **CH4** | `locked` 目标：已 unlock `Decision(approved_by=user)` 或用户当轮显式授权 | `WB_LOCKED` |
| **CH5** | Manifest 边与 entries 已反映 rev/status/decision 索引变更 | `WB_MANIFEST` |
| **CH6** | taxonomy 若声明：`primary ∈ {vertical_drift, lateral_conflict, version_skew, intent_gap, critique_unmerged}` | `WB_TERM` |

### 2.6 `learn`

| ID | MUST | FAIL 码 |
|----|------|---------|
| **L0** | **零**项目资产 writeback；无 Manifest/Status 变更 | 误写 → `WB_SCOPE` |

---

## 3. FAIL 码

### 3.1 Writeback 验收码（本文件权威）

| code | 含义 | 典型恢复 |
|------|------|----------|
| `WB_SCOPE` | 超出 intent 可写范围或硬边界 | 缩写入 / 切换 intent |
| `WB_TYPE` | 非法 type 或未归一别名 | 归一后重写 |
| `WB_ENVELOPE` | 缺 id/type/rev/status/updated_at 或 rev 未递增 | 补信封 |
| `WB_STATUS` | status 非闭集 | 规范化枚举 |
| `WB_LOCKED` | 无授权改 locked/archived | Decision.unlock 或放弃 |
| `WB_MANIFEST` | 未注册 / rev·status 与 Manifest 不一致 | register + touch |
| `WB_STATUS_PTR` | Status 指针/last_writeback 未更新；write_unit 后 `recap_state` 未更新（W8） | 补 Status / Recap 写回 |
| `WB_DEPS` | 依赖悬空或 min_rev 不满足 | 补资产或修 depends_on |
| `WB_CONFLICT` | 与 canon/locked 冲突未裁决 | conflict-playbook |
| `WB_TERM` | 术语/枚举漂移（洋葱/序列/status/taxonomy） | normalize_terms |
| `WB_KNOWLEDGE` | 粘贴理论长文或非法 K 引用 | 删正文，只留 K-ID |
| `WB_SCHEMA` | 最小字段缺失 | 按 asset-types 补全 |
| `WB_REPORT` | 无法生成会话报告最小字段 | 补齐报告元数据 |
| `WB_GATE` | 宣称过 gate 或升 phase 但 gate 未 PASS | 修 outputs / 勿升 phase |
| `WB_BOUNDARY` | 阶段硬边界违规（场景级进 P2 等） | 压缩到合法粒度 |
| `WB_SEQ` | 序列编号违规（缺 0、越 0–23、复合键缺 `volume_id`、漏锚点等） | 按 glossary §4 修正 |
| `WB_STALE` | 输入 stale 仍当成功执行写 | 先 resync / change |
| `WB_STALE_PROP` | 应传播 stale 未标记 | mark_stale |
| `WB_CANON_DRIFT` | 正文/单元写回夹带设定漂移 | 剥离设定或转 change |
| `WB_PROMOTE` | 非法自动晋升 canon/locked | 降回 draft/review |
| `WB_DECISION` | change 缺 Decision 或 impact 不一致 | 补 Decision |
| `WB_INIT_CORE` | new_project 缺 Manifest/Status | 补初始化 |
| `WB_INIT_BP` | new_project 缺 Blueprint 注册 | 建 blueprint_main |

### 3.2 与 protocol §7 BLOCK 码映射

| WB code | 可映射 protocol code |
|---------|----------------------|
| `WB_SCOPE` | `WRITE_SCOPE_VIOLATION` |
| `WB_LOCKED` | `LOCKED_TARGET` |
| `WB_CONFLICT` | `CONFLICT_UNRESOLVED` |
| `WB_GATE` | `GATE_FAIL` |
| `WB_STALE` / `WB_STALE_PROP` | `STALE_INPUT`（输入侧）或变更未完成 |
| `WB_DEPS` / `WB_SCHEMA` | `MISSING_INPUT`（语义近时） |
| `WB_MANIFEST`（项目不存在） | `MISSING_MANIFEST` |
| 其余 | 保持 WB_* 报告；必要时并列 BLOCK code |

Agent 阻断行为对齐 protocol §7.2：`persist nothing contested`；不假装 success。

---

## 4. 会话结束报告（最小字段）

每轮 DONE / BLOCKED / FAIL 均须向用户（及可选机读 sidecar）给出下列**最小集**。字段名 `snake_case`。

### 4.1 必填

```yaml
session_report:
  intent: new_project | advance | write_unit | diagnose | change | learn
  mode: string                    # 如 MODE_ADVANCE
  verdict: PASS | FAIL | BLOCKED | SKIP  # learn 零写 → SKIP 或 PASS+assets_written=[]
  phase: P1 | P2 | P3 | P4 | P5 | P6 | idle | null
  route: traditional | web | null   # hybrid 已删（双轨用 flags.dual_track）

  assets_written:                 # learn 必须 []
    - id: string
      type: AssetType
      rev: int
      status: draft|review|canon|locked|stale|archived
      action: create | update | touch | stale_mark | archive | publish   # publish=touch 晋升 locked，rev 不变

  manifest_touched: boolean
  status_touched: boolean

  gate_result: PASS | FAIL | NA   # 无 phase gate 时 NA
  fail_codes: [string]            # 空 = 无 FAIL；含 WB_* 与/或 protocol BLOCK code
  blockers:                       # 可与 Status.blockers 对齐
    - code: string
      message: string
      related_asset_ids: [string]

  stale_marked: [string]          # asset_id 列表
  decisions_written: [string]     # Decision id 列表

  next_intent_hint: new_project | advance | write_unit | diagnose | change | learn | null
  notes: string                   # 人话摘要 ≤ 短段；禁止贴 knowledge 长文
```

### 4.2 条件必填

| 条件 | 额外字段 |
|------|----------|
| `intent=advance` | `phase_before`, `phase_after`；若 gate FAIL：`gate_failures: [string]` |
| `intent=write_unit` | `active_unit: { type, id }`；`word_count`（若 ManuscriptUnit） |
| `intent=change` | `decision_id`；`taxonomy_primary`（若有冲突） |
| `intent=diagnose` | `diagnosis_ids` 或等价；`knowledge_refs: [K-…]`（本轮用到的） |
| `verdict=FAIL\|BLOCKED` | `fail_codes` 非空；`recovery_hint: string` |
| 任意序列相关写回 | `sequence_indices_touched: {volume_id, indices: [0..23]}`（跨卷时列表多组；可选但推荐） |

### 4.3 禁止出现在报告中的内容

- 具体作品剧情长摘要充作规范  
- knowledge 理论正文  
- 未归一的废弃 type 名（`ProseUnit` 等）作为 `assets_written[].type`

### 4.4 最小机读示例

```yaml
session_report:
  intent: advance
  mode: MODE_ADVANCE
  verdict: PASS
  phase: P2
  route: traditional
  assets_written:
    - { id: plotspine_main, type: PlotSpine, rev: 3, status: review, action: update }
    - { id: thread_main_fuse, type: Thread, rev: 1, status: draft, action: create }
  manifest_touched: true
  status_touched: true
  gate_result: PASS
  fail_codes: []
  blockers: []
  stale_marked: []
  decisions_written: []
  next_intent_hint: advance
  notes: "P2 PlotSpine 已写回 review；可进 P3。"
  phase_before: P2
  phase_after: P2
```

---

## 5. Agent 伪代码

```
function writeback_acceptance(outputs, intent, manifest, status):
  if intent == learn:
    assert outputs.project_writes is empty
    return Accept(SKIP, report=session_report_min(intent, assets_written=[]))

  fails = []
  fails += try_run("tools/validate.py --project DIR")  # [脚本] 标注项机器判定；
                                                       # 不可运行 → 按 §1 手工清单逐项
  for a in outputs.assets:
    fails += check_global_must(a, intent, manifest)   # M01–M13
  fails += check_intent_must(intent, outputs, status) # §2（write_unit 含 W6–W8；change 含 CH1–CH6）

  if outputs.conflict_blocking and not has_decision(outputs):
    fails += [WB_CONFLICT]

  if fails:
    return Accept(FAIL, fail_codes=unique(fails), persist=contested_none)

  # 仅此之后执行 protocol §6 WB_4…WB_9
  return Accept(PASS, fail_codes=[])


function emit_session_end(accept, wb_result):
  report = build_session_report(...)  # §4 必填全有
  assert report has all required keys  # M13
  present_to_user(report)
  return report
```

### 5.1 快速勾选（DONE 前）

```
[ ] 非 learn：已跑全局 MUST M01–M13（[脚本] 项经 tools/validate.py 或手工清单）
[ ] 已跑本 intent 额外 MUST（write_unit 含 W6–W8；change 编号 CH1–CH6）
[ ] publish：晋升 locked（唯一默认）；touch 不递增 rev；action=publish
[ ] change：Decision.approved_by 在授权级别表内
[ ] contested 未落盘；FAIL 有 WB_* 码
[ ] Manifest.rev/status 与资产信封一致（root + 触及卷分片）
[ ] Status.last_writeback 已更新；write_unit 后 recap_state 已更新
[ ] 序列复合键 {volume_id, index 0–23} / 洋葱 surface…wound / ManuscriptUnit·Thread 名未漂移
[ ] 会话报告最小字段齐全（route ∈ {traditional, web}）
[ ] 未写 knowledge/**；未粘贴理论长文
```

---

## 6. 与其它 runtime 文件的接口

| 文件 | 本文件职责边界 |
|------|----------------|
| `protocol.md` §6 | 回写**事务顺序**与 intent 默认可写范围；本文件 = 验收谓词 |
| `protocol.md` §7 | BLOCK 行为与通用阻断码；本文件 WB_* 可映射 |
| `asset-types.md` | 信封、最小字段、Manifest 不变量 AT1–AT4 |
| `phase-contracts.md` | 内容 gate / 硬边界；本文件 `WB_GATE` / `WB_BOUNDARY` 引用之 |
| `conflict-playbook.md` | 冲突未决 → `WB_CONFLICT`；change 的 Decision/stale |
| `glossary.md` | 术语归一；`WB_TERM` / `WB_SEQ` |
| `tools/validate.py` | §1 M 表 [脚本] 标注项的机器判定（`--project`）；环境不可运行时按手工清单 |

冲突时：术语以 glossary 为准；可写范围以 protocol §6.2 为准；类型字段以 asset-types 为准；**验收是否放行以本文件 MUST 为准**。

---

## 7. 修订

| rev | 说明 |
|----:|------|
| 1 | 初版：全局 MUST、六 intent 额外 MUST、WB_* FAIL 码、会话报告最小字段；指针 protocol §6 |
| 2 | 对齐 2026-08-12 决策书：M 表加 [脚本] 列（tools/validate.py）；M03 publish 例外（touch 不递增 rev）；write_unit 新增 W6–W8（summary_after/continuity_delta、evidence_checks 带 quote、recap_state）；change 编号 C→CH1–CH6 + approved_by 合法性；报告 route 删 hybrid、action 补 publish、sequence_indices_touched 升复合键；§0.1 枚举/召回指针化 |
| 3 | 2026-08-13 修复轮：publish=晋升 locked（唯一默认）对齐（§0/M03/§4.1/§5.1）；「禁止静默升」加例外钩子（auto_promote 配置晋升 + agent_auto Decision 留痕 = 满足非静默）；M01/W1 注 write_unit 收编后允许集（Status 指针/Manifest touch/payoff realized）；§2.3 加 [脚本] 列——W2/W5/W6/W8 标注对应 `validate --project` 检查名，quote 子串校验挂 W7 |

**doc_id**：`runtime.writeback_acceptance`  
**compatible_runtime**：`protocol`, `asset-types`, `phase-contracts`, `conflict-playbook`, `glossary`
