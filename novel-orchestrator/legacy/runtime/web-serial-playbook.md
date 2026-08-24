# Web Serial Playbook — 网文完整生长播放书

> **定位**：`route=web` 专用的可执行生长协议（非文学讲义、非单书手册）。  
> **依赖**：`runtime/protocol.md`（intent/召回/回写）、`runtime/phase-contracts.md`（P1–P6 gate）、`runtime/asset-types.md`（type/status）、`runtime/conflict-playbook.md`（反馈与变更）、`runtime/glossary.md`（术语 SSOT）。  
> **知识**：仅引用 `K-xxx` ID；不复制理论正文。  
> **硬约束**：通用工程层 only——禁止绑定具体书名、角色名、作品剧情作规范正文。

---

## 0. 启用条件与绑定

### 0.1 何时启用本 playbook

| 条件 | 动作 |
|------|------|
| 用户声明「网文 / 连载 / 日更 / 开书」 | 启用本文件，覆盖 traditional 默认节奏 |
| `Status.route = web` | 全程按本 playbook 的 Fast-Start / 存稿 / 连载循环 |
| `Status.flags.dual_track = web_serial` | 与 `route=web` 同步；矛盾时以当轮用户指令 + `Decision` 为准 |
| 未声明 route | **不**自动启用；默认 `traditional`（见 phase-contracts §0.1） |

### 0.2 Status 必写字段（开书时一次钉死）

```yaml
# status_project 增补 / 覆盖
# 本块已入 asset-types §2.1 Status 最小字段（非旁路建议）
route: web
flags:
  dual_track: web_serial
  knowledge_budget_default: 12   # 可被 phase budget 覆盖
  critic_cadence: every_5_chapters + volume_end   # critic 抽检（规格 phase-contracts §7.9）
  unattended_mode: false         # true = 无人值守：卷界 checkpoint 降级留痕续跑（§9.2）；配置变更须 Decision(user)
web_serial:
  current_volume: vol_01
  opening_scope:                 # 开书窗口
    volume_id: vol_01
    sequence_range: [0, 6]       # 默认 Act1；可扩到 [0, 12]
    chapter_range: [1, 3]        # 开篇批次 = 首个 P5/P6 写作窗口（普通批量，无特殊 gate）
  buffer:
    target_chapters: 3           # 存稿目标章数（可配置 2–7）
    ready_count: 0               # 已达 review+ 且未发布的 ManuscriptUnit 数
    min_before_publish: 1        # 首次公开发布前至少存稿章数
  serial_cursor:
    last_published_chapter: 0
    next_write_chapter: 1
    next_plan_chapter: 1
  last_critic_chapter: 0         # 最近一次 critic 轮覆盖章号（漏跑可检；规格 phase-contracts §7.9）
  auto_publish: false            # true = 存稿超 target 自动发布最旧 ready 章（§6.4）；配置变更须 Decision(user)
  auto_promote:                  # 常任授权（web 默认全 true；改动须 Decision(user)）
    p4_canon: true               # P4 gate PASS → Character/WorldRule 自动升 canon
    p4_canon_seed: true          # P4 gate PASS → canon_root/canon_style 随同升 canon
    chapter_canon_on_gate_pass: true
    facts_upsert: true
  payoff_log_enabled: true       # 爽点/信息增量记录开关
# 章状态链：draft →(自检) review →(gate PASS 按 auto_promote.chapter_canon_on_gate_pass) canon（存稿）→(publish) locked（已发布）
```

### 0.3 与主协议关系

| 层 | 职责 |
|----|------|
| `protocol.md` | intent 路由、BOOT、BLOCK、writeback 事务 |
| `phase-contracts.md` | 各 phase 的 I/O、硬边界、`route_delta`、gate |
| **本文件** | web 轨的**推进顺序、scope 裁剪、存稿、发布就绪、反馈入口、分卷循环** |
| `conflict-playbook.md` | 读者/作者反馈落地必须走 change 流水线 |

冲突时：术语与枚举以 `glossary` 为准；phase 边界与 gate 以 `phase-contracts` 为准；**节奏与开书策略以本 playbook 为准**。

---

## 1. 设计原则（网文轨）

| # | 原则 | 可执行含义 |
|---|------|------------|
| W1 | **分批过 gate** | gate 只强制 `opening_scope` / 当前 `scope`；scope 外允许 `draft` 占位 |
| W2 | **禁止以 draft 充发布** | 开书窗与发布窗内：ChapterPlan ≥ `review`，核心 Character/WorldRule 开书相关 ≥ `canon` |
| W3 | **强钩子** | 每章 `ChapterPlan.hooks.close` 非空；P6 须 `hooks_realized.close=true` |
| W4 | **先脊骨后细节** | P2 全节点占位；仅开书 scope 细填；禁止 P2 写场景 |
| W5 | **存稿缓冲** | 公开发布节奏与写作节奏解耦；见 §5 |
| W6 | **反馈不静默改设定** | 读者/平台反馈 → `diagnose`（可选）→ **`change` + Decision**；禁止 P6 静默改 canon |
| W7 | **先资产后知识** | 与 protocol C5 一致；日常 `advance`/`write_unit` 禁止扫 knowledge-index |

**序列 / 洋葱 / status（禁止分叉）**：

- 序列索引：`0..23`（含序列 0 = Hook）
- 洋葱五层 id：`surface | behavior | emotion | belief | wound`（zh：表象/行为/情感/信念/创伤）
- 资产 status：`draft | review | canon | locked | stale | archived`
- 正文 type 正式名：`ManuscriptUnit`（别名 `ProseUnit` 写回时归一，禁止独立注册）
- 悬线/伏笔正式 type：`Thread`

---

## 2. Fast-Start — 从零到连载

> 目标：用最短可验证路径跑通「可日更」状态，而非一次做完全书细纲。

### 2.1 总流程图

```
new_project (route=web)
    │
    ▼
[FS1] P1 Blueprint          ── 全量 gate（web 附加项必过）
    │
    ▼
[FS2] P2 PlotSpine          ── 24 节点全占位 + 锚点齐；细填仅 opening_scope
    │                          volume_map 至少 vol_01
    ▼
[FS3] P3 SequenceMap        ── 仅 opening_scope 序列：事件 + scenes[]
    │
    ▼
[FS4] P4 SceneBeat + Canon  ── 仅 opening 场景节拍；开书卷 Character/WorldRule → canon
    │
    ▼
[FS5] P5 ChapterPlan        ── 开篇批次（默认 ch1–3）；逐章过常规 P5 web gate
    │
    ▼
[FS6] P6 ManuscriptUnit     ── 写开篇批次；逐章过 P6 web gate；填存稿 buffer
    │
    ▼
[FS7] 连载循环              ── 见 §8
         P5(下一批章) ⇄ P6(写/改) + 按需 advance 扩 P3/P4 scope
```

### 2.2 阶段裁剪契约

| 步骤 | phase | scope 强制 | 产出最低 status | 明确禁止 |
|------|--------|------------|-----------------|----------|
| FS1 | P1 | 全书蓝图（不可半截） | `Blueprint` ≥ `review` | 序列表、场景、章纲、正文 |
| FS2 | P2 | **nodes 0–23 全占位**；`value_one_liner` 开书窗须可执行；远端可粗 | `PlotSpine` ≥ `review`（开书锚点齐） | **任何场景级**；对话；章号 |
| FS3 | P3 | `sequence_range` 默认 `0–6`（可扩到 0–12） | 窗内序列条目 ≥ `review` | 章纲、节拍定稿、正文 |
| FS4 | P4 | 窗内全部 `scenes[]` → `SceneBeat` | 窗内 `SceneBeat` ≥ `review`；开书相关 Character/WorldRule = **`canon`** | 按章内容块成稿；全书强制 canon |
| FS5 | P5 | `chapter_range`（默认 [1,3]，普通批量） | 批内每章 `ChapterPlan` ≥ `review`（常规 P5 web gate：钩子/字数/爽点） | 完整正文；改 canon（须 change） |
| FS6 | P6 | `chapter_range`（开篇批次） | 批内每章 `ManuscriptUnit` 走状态链：draft →(自检) review →(gate PASS 按 auto_promote.chapter_canon_on_gate_pass) canon（存稿）→(publish) locked（已发布） | 静默改 PlotSpine/SequenceMap/Character/WorldRule |

### 2.3 Fast-Start 伪代码

```
function fast_start_web(user_intent):
  # INIT
  assert intent in {new_project} or (EXISTS and route missing → set route=web via Decision)
  writeback Status:
    route=web, flags.dual_track=web_serial
    web_serial.opening_scope = default_or_user
    web_serial.buffer.target_chapters = user_or_3
    phase=P1, mode=new_project|advance

  # FS1 P1 全量
  run_advance(P1)  # phase-contracts §2；web: 开篇钩子意图 + 爽点空间 + 细分类型
  require Blueprint.status ≥ review
  require gate.web_extra pass   # high_concept 钩子意图、可升级空间

  # FS2 P2 锚点全占位 + 开书细填
  run_advance(P2):
    nodes[0..23] = { title, value_one_liner }  # 禁止 scenes
    anchors must exist: 0,6,8,12,16,18,19,22,23
    detail_fill(sequence_range = opening_scope.sequence_range)  # 价值句更可执行
    volume_map ≥ [vol_01 with node_range covering opening]
    Thread seed: mainline + fuses (≥3 plant hints planned)
  require no_scene_level(PlotSpine)
  require PlotSpine.status ≥ review

  # FS3–FS4 仅开书 scope
  run_advance(P3, scope=opening.sequence_range)
  # 每序列：event_summary + scenes[1..5]；value_start ≠ value_end
  # web: 每序列至少一处 payoff_or_info_intent
  run_advance(P4, scope=scenes_in_opening)
  # SceneBeat beats + gap；gate 只判内容完备（洋葱五键齐、WorldRule 无 TBD）
  # PASS 后按 auto_promote.p4_canon / p4_canon_seed 升 canon（Character/WorldRule + canon_root/canon_style；agent_auto）；远期 domain 可 draft

  # FS5 开篇批次章纲
  run_advance(P5, scope=opening_scope.chapter_range)
  # 批内每章过常规 P5 web gate（§6.5 #6：钩子/字数/爽点）；无特殊开篇 gate
  if fail → repair_in_phase；未过章不得进入 FS6

  # FS6 开篇批次正文
  for ch in opening_scope.chapter_range:
    run_write_unit(chapter=ch)    # 逐章过 P6 web gate（§7.5 #7）
    # ManuscriptUnit + Thread advance + Status.serial_cursor
    append payoff_log if any  # §7
  update buffer.ready_count

  # FS7
  enter serial_loop()  # §8
```

### 2.4 开书 scope 默认值与合法扩展

```yaml
opening_scope_presets:
  minimal:   { sequence_range: [0, 6],  chapter_range: [1, 3] }   # Act1 + 首批 3 章
  standard:  { sequence_range: [0, 12], chapter_range: [1, 5] }   # 到中间点带
  # 禁止：opening_scope 跳过序列 0；禁止 chapter_range 不含 1
  # chapter_range 仅是首个写作批量（与连载期 1–3 章/批同性质），不附加任何特殊 gate
```

扩展 scope 时：

1. 先 `advance` 扩 P3/P4，再扩 P5/P6。  
2. 不得在 P6 写尚未有 `ChapterPlan(review+)` 的章。  
3. 扩 scope 触达新 Character/WorldRule 硬事实 → 先升 `canon` 或写 `Decision`。

---

## 3. 用户最小指令表

用户只需发短指令；Agent 负责映射 intent / phase / scope。

| 用户说法（例） | intent | Agent 动作摘要 |
|----------------|--------|----------------|
| 开一本网文 / 从零网文 | `new_project` | FS1：`route=web` + P1 |
| 继续 / 推进 | `advance` | 按 Status.phase 与 web_serial 游标推进下一 FS 步 |
| 写第 N 章 / 写下一章 | `write_unit` | 校验 ChapterPlan；写 `ManuscriptUnit`；更新 buffer |
| 补存稿 / 多写两章库存 | `write_unit` 或 `advance(P5)`→`write_unit` | 优先填满 `buffer.target_chapters` |
| 卡了 / 为什么不爽 / 诊断节奏 | `diagnose` | 经 knowledge-index；**不**自动改 canon；可建议 change |
| 读者说 XX 不行 / 改设定 / 砍线 | `change` | conflict-playbook 全流水线 + Decision + stale |
| 开第二卷 / 推进分卷 | `advance` + scope 换 `volume_id` | 见 §9 |
| 学网文钩子 / 解释 K-xxx | `learn` | 只读知识；不写项目资产 |
| 发布第 N 章 / 第 N–M 章 | **publish 快径**（protocol §2.4） | 逐章判定就绪（§6.2，须自 `last_published_chapter+1` 起连续）后一次确认（支持区间）；touch 晋升 `locked`，rev 不递增；游标与 buffer 重算；无需 Decision（除非目标已 locked 或含内容改动） |
| 现在到哪了 / 进度 | **report 快径**（只读） | 汇报 phase / serial_cursor / buffer / blockers；零写回 |

**澄清规则**：一句含多 intent 时 ASK 拆单；禁止在 `write_unit` 中顺手改 PlotSpine canon。

---

## 4. 分 scope 召回（web 收紧注记）

**召回表唯一真源 = `protocol.md §4.2`**（含 write_unit 权威召回表）。本文件不再维护召回表。

web 轨仅追加收紧：

- `write_unit` 窗口 = **单章 ± 邻接**（前章尾 + 后章钩子衔接）；禁止灌全书正文
- `advance` P3/P4/P5 只装当前 scope 序列/场景，远端占位不装
- Manifest 只读 `manifest_root` + **当前卷** `manifest_units_v{n}`，禁止全分片装载
- 知识仍仅 contract 白名单；diagnose/learn 经 index（C6），报告须标 scope

---

## 5. 存稿 Buffer

### 5.1 语义

| 字段 | 含义 |
|------|------|
| `buffer.target_chapters` | 希望维持的「已写未发」章数 |
| `buffer.ready_count` | `ManuscriptUnit.status ∈ {review,canon}` 且 `chapter_no > last_published_chapter` 的计数 |
| `buffer.min_before_publish` | 首次对公发布前最低 ready 数（默认 1；稳妥 3） |

### 5.2 规则

```
R-BUF-1  write_unit 成功且 gate pass → ready_count 按章重算
R-BUF-2  发布确认后 last_published_chapter 前进；ready_count 下降
R-BUF-3  ready_count < target 时，默认优先 write_unit / P5 补章，而非扩远期 P3
R-BUF-4  ready_count == 0 且用户要求「日更发布」→ BLOCK 或警告：建议先补存稿
R-BUF-5  存稿章不得长期 draft 冒充 ready；对外可发须 ≥ review
```

### 5.3 与 Status 游标

```yaml
serial_cursor:
  last_published_chapter: int   # 0 = 尚未发布；仅作游标——「已发布」判定全库唯一 = status == locked
  next_write_chapter: int       # 下一 ManuscriptUnit
  next_plan_chapter: int        # 下一 ChapterPlan（可超前 write）
# 不变量：next_plan_chapter ≥ next_write_chapter ≥ last_published_chapter + 1（在正常推进时）
```

### 5.4 revision write 旁路（修订已有章）

修订已有章（含已发布与存稿章）**不是**新章推进：

```
R-REV-1  不动 serial_cursor（next_write / next_plan 不回拨、不前进）
R-REV-2  仅目标章 rev++，重跑该章 P6 web gate
R-REV-3  buffer.ready_count 按 §5.1 定义重算
R-REV-4  locked 章须先 unlock Decision(user)，否则 BLOCK LOCKED_TARGET
R-REV-5  修订 canon 存稿章且重跑 gate PASS 后：其后续已写存稿章中引用被修章
         summary_after / 尾段衔接的条目标 stale，在该章下轮写作前局部 resync（不全量重写）；
         修订 locked 章仍须 unlock Decision(user)（R-REV-4）
```

---

## 6. 开篇批次与发布就绪

> 「黄金三章」特殊 gate **已废弃**（glossary §1.1）；开篇无特殊检查窗，
> 质量由**常规逐章 gate** 覆盖：P5 §6.5（钩子/字数/爽点/价值翻转）+ P6 §7.5（钩子实现/字数/爽点）。

### 6.1 开篇批次语义

- `opening_scope.chapter_range`（默认 `[1,3]`）只是**首个 P5/P6 写作批量**，与连载期「1–3 章/批」同性质。
- 批内每章独立过常规 web gate；任何章未过 → `repair_in_phase`，不阻塞其他已过章。
- 卖点前置、激励事件落点等属于 P1 `plot_vector` / P2 节点 0–2 价值句 / P3 开书序列的**结构设计**问题，在各自 phase gate 里已判定，不在章级重复设卡。

### 6.2 发布就绪（publish-ready）判定

逐章判定，满足即可走 publish 快径（protocol §2.4）；「发布第 N–M 章」区间逐章判定、**一次确认**（`auto_publish` 默认 false，发布默认人批；自动发布协议见 §6.4）。publish 为 **touch**：**晋升 `locked`（唯一默认）**，**rev 不递增**，`action: publish`。`canon` 语义 = 已采纳/已过 gate 的**存稿**；「已发布」判定全库唯一 = `status == locked`（`last_published_chapter` 仅作游标不作判据）。

| 条件 | 数据源 |
|------|--------|
| 目标章 `ManuscriptUnit.status ≥ review`（过 P6 web gate） | Manifest |
| **发布顺序谓词**：目标章构成自 `last_published_chapter + 1` 起的**连续区间**；乱序/跳章请求 → BLOCK `GATE_FAIL`（message 指出缺口章号） | Status.serial_cursor |
| 无未裁决 blocking 冲突触及本章 | conflict-playbook |
| `buffer.ready_count ≥ buffer.min_before_publish`（首发时） | Status.web_serial |
| 用户当轮确认发布（或 §6.4 auto_publish 留痕） | 会话 / Decision |

### 6.3 修复路径

- 章级 craft 未达标 → `repair_in_phase`（P5 修章纲 / P6 修正文）。
- 结构性问题（开篇无卖点、激励事件缺位）→ `diagnose` 归因后回 P2/P3/P4 对应 phase 修，**不**通过加章级特殊 gate 兜底。

### 6.4 auto_publish 行为协议

- 默认 `auto_publish: false`：发布始终人批（§6.2 一次确认），本节不生效。
- `auto_publish: true` 时：`write_unit` gate PASS 后，若 `buffer.ready_count > buffer.target_chapters` → 自动 publish **最旧 ready 章**（仍须满足 §6.2 全部条件，含发布顺序谓词），写 `Decision(approved_by=agent_auto)`，session_report 记录本次自动发布。
- `auto_publish` 配置变更本身须 `Decision(approved_by=user)`（授权表条目：auto_promote / auto_publish / unattended_mode 配置变更）。

---

## 7. 爽点 / 信息增量记录（Payoff Log）

### 7.1 目的

连载中可审计「是否定期正面价值释放 / 升级 / 反转」，避免空转。  
**不是**独立 AssetType；正式落点为 `ChapterPlan.serial_notes.payoff_entries[]`（P5 计划、P6 回写 `realized`），在 Manifest `tags` 可检索。

### 7.2 字段落点（正式声明）

正式字段 **`ChapterPlan.serial_notes.payoff_entries[]`**；schema 唯一真源 = `asset-types.md §2.9`（序列引用复合键、`thread_ids` 关联 Thread），本文件不重复定义。

### 7.3 纪律

| 规则 | 说明 |
|------|------|
| P3 | 每序列至少一处 `payoff_or_info_intent`（phase-contracts web gate） |
| P5 | 每章标记 density 或具体 `payoff_entries[]`（含 thread_ids 引用） |
| P6 | 回写 `realized`；未实现 → `issues[]` 或下轮 repair |
| 禁止 | 用爽点记录替代 `Thread` 伏笔账本；长线承诺仍走 `Thread.state` |
| 统计 | diagnose 可按章/卷统计 `realized` 密度；连续 N 章无 realized → 症状码建议 |

---

## 8. 连载循环（FS7）

进入条件：开篇批次 `ManuscriptUnit` 全部 ≥ `review`（逐章过 P6 web gate）且 `buffer.ready_count ≥ min_before_publish`；或用户 Decision 豁免并留痕。

```
serial_loop:
  while project active:
    1. buffer_check:
         if ready_count < target_chapters → prioritize fill_buffer
    2. ensure_plan:
         if next_write_chapter 无 ChapterPlan(review+):
            if 所属序列缺 scenes[] → advance P3（先补场景清单）
            elif 场景缺 SceneBeat → advance P4（扩 scope）
            advance P5 for next batch (建议 1–3 章/批)
    3. write_unit(next_write_chapter)
         → ManuscriptUnit writeback（summary_after / continuity_delta 必填）
         → Thread advance_log / payoff；recap_state 更新 + recap_book 滚动追加
         → serial_cursor++, buffer 重算
         → critic_pass 按 critic_cadence（规格 = phase-contracts §7.9）：
             独立子代理/新会话执行（不携带本轮产出上下文——由执行环境保证）；
             输入 = 目标章正文 + 章纲 + canon + canon_style + 当前卷 SequenceMap 摘要 + PlotSpine 卷内节点表；
             必查四项：K-WRITE-018 口癖 / K-WRITE-021 水字 / K-CHAR-013 遮名抽检（对话 ≥3 段章）/ 方向偏航（本章价值走向 vs 卷内节点）；
             出 CritiqueReport + 更新 Status.web_serial.last_critic_chapter；不合格 → repair_in_phase
    4. optional publish:
         user confirm（「发布第 N–M 章」区间一次确认）→ status → locked; 游标前进
         # publish 快径（protocol §2.4）：touch 不递增 rev，无需 Decision；须满足 §6.2 发布顺序谓词
         # auto_publish=true → 按 §6.4 自动发布最旧 ready 章（Decision agent_auto 留痕）
    5. horizon_expand（触发：cursor 距 scope 覆盖上沿 ≤3 章）:
         扩 sequence_range / 下一 volume 节点细填；卷界 → 先过 §9.2 volume_checkpoint
    6. on feedback → §10（simple_change 或 change；不在本步静默改）
    7. on stuck → diagnose（§11）→ 再 change 或 repair
```

### 8.1 批次建议

| 水位 | 建议动作 |
|------|----------|
| 存稿 ≥ target | 可稳定发布；间歇扩 P3/P4 远期 |
| 存稿 = 1 | 发布与写作并行；暂停大改设定 |
| 存稿 = 0 | 停发或降频；只 `write_unit` / 必要 P5 |
| 结构性堵塞 | `diagnose`；禁止硬写空转章充数 |

### 8.2 章级 writeback 清单（操作顺序清单；验收以 writeback-acceptance 为准）

```
[ ] ManuscriptUnit 已注册 Manifest（当前卷分片）；rev+1
[ ] chapter_plan_id 指向 ChapterPlan(review+)
[ ] hooks_realized 与字数门禁；evidence_checks（摘引+论证）
[ ] summary_after / continuity_delta 必填
[ ] facts upsert 入 canon_continuity_v{n}（按 auto_promote.facts_upsert）
[ ] Thread 状态机更新（plant|advance|payoff…）
[ ] payoff_entries.realized 回写
[ ] recap_state 更新；recap_book 滚动追加
[ ] Status.serial_cursor / buffer / last_writeback
[ ] 无未裁决 conflict；无对 canon 的静默字段改写
```

---

## 9. 分卷推进

### 9.1 资产落点与序列语义（两种模式，开书时二选一并记入 Decision）

| 模式 | 适用 | 序列语义 | 资产布局 |
|------|------|----------|----------|
| **A. 全局脊骨**（默认） | 预计 ≤3 卷 / ≤100 章的紧凑长篇 | 全书共用**一条 0–23**；`volume_map[].node_range` 把卷划为节点带 | 单 `plotspine_main` + 单 `seqmap_main` |
| **B. 卷级脊骨** | `long_serial`（>100 章 / ≥3 卷的超长连载） | `plotspine_main` 保持**书级** 0–23（每节点≈一卷级主题弧）；**每卷**另开 `seqmap_v{n}`，卷内序列独立编号 0–23（含卷内 Hook） | `plotspine_main` + 每卷 `seqmap_v{n}`；卷内 0–23 与书级节点的对应关系写入 `volume_map` |

- 模式选择与 A/B 切换必须写 `Decision(approved_by=user)`；中途从 A 切 B → 既有 `seqmap_main` 归档或重命名为首卷实例，下游标 `stale`。
- **模式 B 锚点**：书级 PlotSpine 保留为规划资产；gate 只强制**卷内** `seqmap_v{n}` 锚点，书级锚点 **soft**（缺失仅 warning；远端节点可占位到卷级主题一句话）。
- 通用落点：`PlotSpine.volume_map[]`（`volume_id`, `theme`, `node_range`, `element_ids`）；`ChapterPlan.volume_no` / `Status.web_serial.current_volume`。
- 序列引用一律复合键 **`{volume_id, sequence_index}`**（速记 `v3:s12`；asset-types §2.7）；禁止裸索引跨卷两义。

### 9.2 卷切换协议

```
function open_next_volume(vol_id):
  require volume_checkpoint(prev_vol):   # 每卷唯一强制人工节点
    - 卷报告：卷摘要 + 伏笔账（Thread 对账）+ 战力变化 + 残留 blockers
    - 关卷生成 recap_vol_{prev}（templates/recap.md）
    - 本卷已完成（非 open）Decision entries 从 manifest_root 迁入 manifest_decisions_v{当前卷}
    - 须用户确认后才开新卷（卷内写作不因此阻断；unattended_mode=true 走下方降级协议）
  require previous volume 收束条件之一:
    - volume node_range 内主 Thread 阶段 payoff 已计划且关键章已 review
    - 或 Decision: soft_break（允许卷末钩子悬置）
  update opening_scope-like window → volume_scope:
    sequence_range = volume_map[vol_id].node_range 的「当前写作窗」切片
  P2: 若远端节点仍为极粗占位 → 细填本卷 node_range 价值句（仍禁场景；书级锚点 soft）
  P3→P4→P5→P6: 同 Fast-Start 裁剪；新卷开篇批次照常仅过常规逐章 gate
  write Decision(decision_type=scope_change, approved_by=user) 记录开新卷确认、卷界与不变量是否迁移
  # 降级协议（Status.flags.unattended_mode=true 时）：卷报告照常落盘，
  #   写 Decision(approved_by=agent_auto, flags.pending_human_review=true) 后继续开卷；
  #   session_report 醒目提示「卷界 Decision 积压待人审」
```

### 9.3 卷间禁止

- 不重写已 `locked` 正文，除非 unlock Decision  
- 不静默改已发布章连续性事实；需 `Canon.facts` + change  
- 不把新卷当 `new_project`（除非用户明确弃档重开）

---

## 10. 反馈 → change（禁止旁路）

### 10.1 触发源

- 读者评论、榜单数据、编辑意见、作者自感「要改线」  
- diagnose 产出的「建议改设定」类 actions  

### 10.2 强制路径

```
feedback_raw
  → (optional) diagnose: 症状分类 + K-ID 方案 + 对照资产
  → simple_change 快路径（目标未发布，不触 invariants、不砍 must_not_drop）:
       Decision(agent_auto) → 仅直接依赖标 stale → 懒同步（写到受影响章时局部 resync）
     其余 → change 全流水线:
       detect → classify → decide → record(Decision) → mark_stale(deps) → sync | block
  → 波及已发布（locked）章: 不标 stale → 写 retcon_note 入 canon_continuity_v{n}，
       后续章按 forward_strategy 向前兼容（conflict-playbook）
  → 再 advance / write_unit
```

| 禁止 | 正确 |
|------|------|
| P6 里直接改 Character.onion / WorldRule | `change` + Decision，下游资产标 `stale` 后 sync |
| 按单条评论改主线无记录 | `critique_unmerged` 直至 Decision accept/reject |
| 用 K-xxx 压过项目 canon | 知识只读；项目事实以资产为准 |

优先级链（与 protocol §5 一致）：  
`用户当轮指令 > Decision > Canon.invariant > 更高锁定阶段资产 > working > critique`。

### 10.3 网文常见反馈 → taxonomy 提示

| 反馈类型 | 建议 primary | 默认动作方向 |
|----------|--------------|--------------|
| 人设崩了 | `lateral_conflict` 或 `vertical_drift` | 对照 Character canon；rewrite 低层或 escalate |
| 主线失忆/前后矛盾 | `vertical_drift` / `version_skew` | 以 Canon + 高 rev 为准 sync |
| 要加新金手指/体系 | `intent_gap` | 扩 WorldRule + Decision；标下游 stale |
| 某支线催更/嫌弃 | `critique_unmerged` | Thread budget 调整须 Decision；禁默删 must_not_drop |
| 只改文风 | 通常非 conflict | `write_unit` repair；不动结构资产 |

---

## 11. diagnose 衔接

### 11.1 何时转 diagnose

- 同一 gate 条款连续 3 次 FAIL（contracts §0.5 repair 上限）转 escalate 后仍不清  
- 存稿正常但「读感」崩（空转、无钩、人设平）  
- 用户只描述症状、未给出改法  
- 反馈方向不清，需要 K-ID 定位  

### 11.2 网文症状域（分类标签，非知识正文）

| domain 标签 | 常见信号 | 下一步 |
|-------------|----------|--------|
| `webnovel.hook` | 章末无力、弃读章 | index → `K-WRITE-011` + `K-WRITE-020`；对照 ChapterPlan.hooks |
| `webnovel.payoff` | 长期无释放/无升级 | 对照 payoff_log + Thread；P3/P5 density |
| `structure.sequence` | 中段塌、锚点无效 | 序列 0–23 / 锚点；K-STRUCT-* |
| `character.onion` | 压力大仍只表象 | Character.onion + reveal_layer |
| `world.rule` | 战力崩、代价消失 | WorldRule hardness/cost |
| `conflict.escalation` | 反派疲软、张力不升级 | index → `K-CHAR-012`（反派梯队/轮换）；对照卷级 Boss 与 Thread 升级线 |
| `craft.prose` | 对话/描写问题 | 仅 craft；少动结构 |

### 11.3 输出契约

```yaml
DiagnosisReport:  # draft；非独立强制 type 时可记入 Decision 附件
  symptom: string
  domain: string
  k_ids: [K-...]          # 经 knowledge-index 路由
  asset_refs: [string]
  findings: [string]
  actions:
    - type: repair_in_phase | suggest_change | write_unit_fix | learn
      detail: string
  # 默认：不写 canon；若 actions 含改设定 → 明确「请切换 change」
```

**C6**：仅 diagnose/learn 可打开 `knowledge-index.md`。

---

## 12. 阻断码（web 增补建议）

沿用 protocol §7.1；下列为 web 轨常用组装（`blockers[].code` 优先用已有码，message 人话化）：

| 场景 | code | message 要点 |
|------|------|----------------|
| 章未过 P5/P6 gate 就要公开发布 | `GATE_FAIL` | 目标章未达 review；见 §6.2 |
| 发布区间乱序 / 跳过未发布章 | `GATE_FAIL` | 指出缺口章号；见 §6.2 发布顺序谓词 |
| 无 ChapterPlan 硬写 | `MISSING_INPUT` | 缺 chapter_* |
| 开书 Character 仍 draft | `INPUT_NOT_CANON` | 开书窗人物/世界未 canon |
| 存稿为 0 仍要求日更且无豁免 | `GATE_FAIL` 或用户 Decision 豁免 | buffer 见 §5 |
| 反馈未裁决继续推进结构 | `CONFLICT_UNRESOLVED` | 先 change |
| 远端 scope 资产 stale | `STALE_INPUT` | resync 后再 write（仅必召回集内阻断） |
| 章写回缺 summary_after/continuity_delta/evidence_checks | `GATE_FAIL` | P6 必填缺失（§8.2） |
| 必召回集缺 Recap | `MISSING_INPUT` | 先补 recap（protocol §4.2） |
| 变更/修订触及 locked 章 | `LOCKED_TARGET` | retcon_note 或先 unlock（§5.4/§10.2） |
| 序列引用缺 volume_id（裸索引） | `GATE_FAIL` | 用复合键（§9.1） |

---

## 13. Agent 主循环（web 包装）

```
function run_web_serial(utterance):
  BOOT per protocol.md          # 七件套；本 playbook 在 route=web 时装载
  intent = route_intent(...)
  if Status.route != web and utterance demands 网文:
    set route=web + dual_track=web_serial (Decision if flipping mid-project)

  match intent:
    new_project → fast_start_web from FS1
    advance     → next FS step or serial_loop.ensure_plan / horizon_expand
    write_unit  → buffer-aware write; forbid canon silent edit
    diagnose    → §11 then maybe handoff change
    change      → simple_change 判定或全流水线（§10.2）; 已发布章 → retcon_note; 已 review 章 → 重跑 P5/P6 gate
    learn       → readonly

  writeback + report:
    - intent, phase, scope
    - buffer / serial_cursor / recap_state
    - assets id/rev/status（序列引用复合键）
    - blockers + 下一步最小用户指令建议
```

---

## 14. 自检清单（每轮 DONE 前）

**DONE 验收唯一权威 = `runtime/writeback-acceptance.md`**（全局 M01–M13 + intent MUST，通用项不在此重复）。本节只保留 web 域独有项：

```
[ ] Status.route=web 且 dual_track 无矛盾
[ ] 发布就绪逐章过 §6.2（含发布顺序谓词）；publish 仅晋升 locked（touch，rev 不递增）
[ ] buffer.ready_count 与磁盘/Manifest 一致（§5.1 定义）
[ ] 序列引用为复合键 {volume_id, sequence_index}
[ ] critic 无漏跑：last_critic_chapter 落后当前章 ≤ critic_cadence 周期（§8 步骤 3）
```

---

## 15. 与其它 runtime 文件接口

| 文件 | 本 playbook 提供 | 期望对方 |
|------|------------------|----------|
| `protocol.md` | web 节奏包装、用户指令映射、buffer 游标 | BOOT、intent、BLOCK、writeback |
| `phase-contracts.md` | Fast-Start 裁剪顺序、开篇批次/发布就绪规则 | 各 phase gate / route_delta / 硬边界 |
| `asset-types.md` | web_serial / payoff_entries 使用纪律（schema 以其 §2.1 / §2.9 为准） | type 最小字段、status 枚举、Recap |
| `conflict-playbook.md` | 反馈→change 入口与网文 taxonomy 提示 | detect…sync 全链 |
| `glossary.md` | 只引用不重定义 | 序列/洋葱/status/type 正式名 |

---

## 16. 修订

| rev | 说明 |
|----:|------|
| 1 | 初版：route=web Fast-Start、存稿 buffer、爽点记录、反馈 change、分卷、diagnose、最小指令 |
| 2 | **废弃黄金三章机制**：删除 golden_three 字段与特殊 gate；§6 改为「开篇批次与发布就绪」；开篇质量回归常规逐章 P5/P6 web gate；publish 快径 + 分卷双模式 |
| 3 | **2026-08 审计重构**：web_serial 入 Status 正式字段；§4 召回改指针 protocol §4.2；§5.4 修订旁路；§6.2 批量发布（publish=touch）；§7 payoff_entries 正式化；§8 顺序/触发/写回修正；§9 volume_checkpoint+recap_vol+复合键+书级锚点 soft；§10 simple_change/retcon_note；§11–14 对齐 |
| 4 | **2026-08-13 修复轮**：publish 统一晋升 locked（唯一默认）+ 发布顺序谓词（连续区间，乱序 BLOCK）；章状态链统一表述（FS6 行 + §0.2 注释）；§5.4 增 R-REV-5；§6.4 auto_publish 行为协议；§9.2 开新卷 Decision 改 user + unattended_mode 降级协议 + Decision entries 迁 manifest_decisions_v{n}；critic 对齐 contracts §7.9（独立子代理、四查、last_critic_chapter）；auto_promote 增 p4_canon_seed；§9.3 Canon.facts 更名；§14 压缩为指针 + web 独有项；第三波收尾（V1 复检修正：冷启动条件行/六件套允许集/小节指针/编号/口径对齐） |

**文档 status**：`canon`（runtime 协议层）  
**id**：`runtime.web_serial_playbook`  
**schema_rev**：`1`
