---
name: novel-writing-workflow
description: |
  小说创作全流程工程化工作流（薄路由入口）。
  管线 intent → mode → load_policy → run → writeback；
  六阶段契约链 P1–P6；资产类型 + 门禁 + 召回预算 + 分歧裁决；
  复合流程 adopt（接管旧稿）/ revise（修订轮）/ publish / report。
  知识库 111 块只读服务：contracts core+situational 白名单 → blocks 解析 → 源文件 K-ID 锚点取片段；
  含连载运营域（爽点工程 / 战力运营 / 群像 / AI 正文病防治）。
  支持 traditional / web 双轨。触发：写小说、大纲、人物、世界观、诊断、变更、修订、接管、学习。
trigger:
  - 写小说
  - 小说创作
  - 故事设计
  - 大纲设计
  - 人物设计
  - 世界观构建
  - 技能体系设计
  - 写作指导
  - 网文创作
  - 故事结构
  - 高概念
  - 冲突设计
  - 势力设计
  - 大纲诊断
  - 设定变更
  - 修订稿件
  - 接管旧稿
  - 导入大纲
  - 创作进度
---

# 小说创作工作流 — 薄路由入口

> **本文件只做路由与启动**。可执行细节以 `runtime/` 为准。  
> 禁止在此重定义术语、复制 knowledge 正文、绑定具体书名/角色/作品目录。

---

## 1. 定位

| 项 | 值 |
|----|-----|
| 角色 | Agent 可执行的**通用创作工程系统**入口 |
| 非目标 | 文学理论课、单书项目手册、方法论全文索引 |
| 知识 | `knowledge/` = **只读服务**（111 块）；仅引 `K-xxx`，有 `knowledge_budget` |
| 术语 SSOT | [`runtime/glossary.md`](runtime/glossary.md) |
| 状态枚举 | `draft \| review \| canon \| locked \| stale \| archived`（`locked` = 已发布/冻结） |
| 序列 | `0–23`（含序列 0 = Hook） |
| 洋葱五层 | 表象 / 行为 / 情感 / 信念 / 创伤（`surface\|behavior\|emotion\|belief\|wound`） |
| 正文 / 悬线 | 正式 type：`ManuscriptUnit` / `Thread` |

---

## 2. 架构

```
用户 utterance
    │
    ▼
 SKILL.md（本文件：intent 路由）
    │
    ▼
 runtime/protocol.md     intent → mode → load_policy → run → writeback
    │
    ├─ phase-contracts.md      P1–P6：depends_on / I/O / gate / on_fail / budget
    ├─ asset-types.md          type 系统 + Manifest（与路径解耦）
    ├─ conflict-playbook.md    detect→classify→decide→record→stale→sync|block
    ├─ glossary.md             术语/枚举唯一 SSOT
    ├─ project-scaffold.md     new_project 强制脚手架（Status/Manifest/Canon/Blueprint）
    ├─ web-serial-playbook.md  route=web：Fast-Start / 存稿 / 发布就绪 / 连载循环
    └─ writeback-acceptance.md 每轮 DONE 前硬验收（M01–M13 + intent MUST）
    │
    ├─ phases/01–06            薄操作清单（越界时以 phase-contracts 为准）
    ├─ templates/              资产草稿壳
    ├─ knowledge/*             只读 K-xxx，111 块含 05-连载运营（diagnose/learn 可经 knowledge-index）
    └─ tools/validate.py       结构校验器（--skill 库检 / --project 项目检）
```

**BOOT 七件套**：protocol · phase-contracts · asset-types · conflict-playbook · glossary · writeback-acceptance · web-serial-playbook（route=web 条件装载）；`project-scaffold` 仅 `new_project` 强制装载。

**原则**：先资产后知识；有 budget；感知 `stale`；working/critique 默认无执行权。

---

## 3. 启动协议（BOOT）

每次调用必须按序，不可跳步（完整定义见 [`runtime/protocol.md`](runtime/protocol.md) §1）：

```
BOOT_1  resolve skill 根；确认 runtime 核心可读（七件套，见 §2）
BOOT_2  load glossary 枚举/术语（不装 knowledge 正文）
BOOT_3  有 Manifest → 只读 manifest_root + Status（单元 entries 在卷分片 manifest_units_v{n}，写作轮按当前卷加读）；否则 project_state=NONE
BOOT_4  parse utterance → Intent（不明则 ASK，不擅自选 mode）
BOOT_5  mode_enter(intent) 绑定 LoadPolicy / Gate / Writeback
BOOT_6  preflight：depends_on、stale、locked、budget → 失败则 BLOCK
BOOT_7  load_policy：必召回 assets；knowledge 仅策略允许时按 ID 拉
BOOT_8  run(mode)
BOOT_9  writeback → **须过 writeback-acceptance**（learn 跳过落盘）
BOOT_10 report：产出摘要 / status 变更 / 阻断项 / 下一步
```

**C6**：仅 `diagnose` / `learn` 可打开 `knowledge-index.md`；`advance` / `write_unit` / `new_project` / `change` 禁止扫 index，只走 contract 白名单 K-ID 或用户点名 ID。**K-ID → 位置解析**一律查 `knowledge-blocks.md`（全 intent 只读可查）→ 按源文件 `<!-- K-ID -->` 锚点取片段。

---

## 4. Intent 路由

### 4.1 枚举

| intent | 触发信号（例） | mode | 默认可写 |
|--------|----------------|------|----------|
| `new_project` | 从零、新建、初始化 | MODE_INIT | Manifest, Status, Blueprint(draft), Canon(canon_root seed), Canon(canon_style 空壳), Recap(recap_state 空壳) — **强制 scaffold 六件套** |
| `advance` | 继续、下一阶段、做粗纲/序列… | MODE_ADVANCE | 当前 phase outputs |
| `write_unit` | 写某章/场景/正文落地 | MODE_WRITE | ManuscriptUnit 等单元 |
| `diagnose` | 诊断、堵车、为什么不行 | MODE_DIAG | 诊断记录/Decision 草案；**不**自动改 canon |
| `change` | 改设定、推翻、同步、冲突 | MODE_CHANGE | Decision + 目标 + 下游 stale |
| `learn` | 学方法、解释 K-xxx | MODE_LEARN | **禁止**写项目资产 |

### 4.2 决策

```
IF project_state == NONE:
  创建意图 → new_project   # 强制 runtime/project-scaffold.md
  仅方法论 → learn
  仅症状无项目 → diagnose（knowledge-only）
  ELSE → ASK: 新建 / 学习 / 诊断？

IF project_state == EXISTS:
  变更/冲突/推翻/同步 → change
  症状/诊断/为什么 → diagnose
  学习/解释/方法论 → learn
  具体 unit 写作 → write_unit
  推进阶段/继续 → advance
  ELSE → ASK 澄清 intent
```

### 4.3 `new_project` 强制脚手架

1. **必须**执行 [`runtime/project-scaffold.md`](runtime/project-scaffold.md)（不可只聊概念伪装 EXISTS）。  
2. 强制产物（六件套）：`Status(status_project)` · `Manifest(manifest_root)` · `Canon(canon_root, draft)` · `Blueprint(blueprint_main, draft)` · `Canon(canon_style, draft)` · `Recap(recap_state, draft)` + 目录骨架。  
3. 网文/连载/日更信号 → `Status.route=web`、`flags.dual_track=web_serial`；否则默认 `traditional`。  
4. Scaffold Gate PASS ≠ P1 content gate PASS；下一步 = 充实 Blueprint 后 `advance@P1`。  
5. 失败 → BLOCK `SCAFFOLD_INCOMPLETE` 等，不声明成功。

### 4.4 复合流程与快径（归并六 intent，详见 protocol §2.4）

| 信号 | 流程 | 归并 |
|------|------|------|
| 已有大纲/正文要接管、导入 | **adopt** | `new_project` 变体 → scaffold §1.4 Adopt |
| 修订、二稿、beta/编辑/读者反馈落地 | **revise** | `diagnose` → Decision → `change` \| `write_unit`(repair) |
| 发布/定稿/冻结第 N 章 | **publish** | `write_unit` 快径：touch 晋升 `locked` + 用户确认（`auto_publish` 自动化见 playbook §6.4） |
| 进度/状态查询 | **report** | 只读快径：BOOT_1–3 + 汇报，零写回 |

### 4.5 优先级链（裁决摘要）

`用户当轮指令 > Decision > Canon.invariant > 更高锁定阶段资产 > working > critique`  
完整流水线：[`runtime/conflict-playbook.md`](runtime/conflict-playbook.md)。

### 4.6 阻断（摘）

`MISSING_INPUT` / `STALE_INPUT` / `GATE_FAIL` / `LOCKED_TARGET` / `CONFLICT_UNRESOLVED` / `KNOWLEDGE_INDEX_FORBIDDEN` / `AMBIGUOUS_INTENT` / `SCAFFOLD_INCOMPLETE` → 停止并报告，不假装成功。

---

## 5. 六阶段一览

契约 SSOT：[`runtime/phase-contracts.md`](runtime/phase-contracts.md)。  
操作清单：`phases/01-blueprint.md` … `phases/06-writing.md`。

| phase | 名称 | 主产出 type | 硬边界（禁止） |
|-------|------|-------------|----------------|
| **P1** | Blueprint | `Blueprint` | 序列表、场景、章纲、正文 |
| **P2** | Rough / PlotSpine | `PlotSpine`, `Thread`… | **任何场景级**；节点=标题+一句话价值 |
| **P3** | SequenceMap | `SequenceMap` | 章纲、节拍定稿、正文 |
| **P4** | Detail / SceneBeat | `SceneBeat`, Character/World **canon**（gate=内容完备，晋升按 `auto_promote`） | 按章内容块章纲、正文成稿 |
| **P5** | ChapterPlan | `ChapterPlan` | 完整正文；擅改 canon（须 change） |
| **P6** | Writing | `ManuscriptUnit` | 静默改 PlotSpine/SequenceMap/设定 |

**必保锚点（P2 起占位）**：`hook(0)` · `shock1(6)` · `growth1(8)` · `midpoint(12，可并 growth2)` · `growth3(16)` · `shock2(18)` · `growth4(19)` · `climax(22)` · `resolution(23)`。

**双轨 `route`**：`traditional`（锁级更严）| `web`（分批 gate；逐章强钩子）。未声明默认 `traditional`。

**推进条件**：`depends_on` gate 全过 + 必装 inputs 无 `stale` + 达 `min_status` → 才可 `Status.current_phase` 前进。

```
P1 → P2 → P3 → P4 → P5 ⇄ P6（按 unit 循环）
         ↑ rollback / change / conflict 可回退或阻断
```

---

## 6. 网文 Fast-Start（`route=web`）

> 细节 SSOT：[`runtime/web-serial-playbook.md`](runtime/web-serial-playbook.md)。检测到网文/连载/日更 → **必须**装载本 playbook。

```
new_project (scaffold, route=web)
  → FS1 P1 Blueprint 全量 gate（含开篇钩子意图）
  → FS2 P2 PlotSpine：0–23 全占位；细填仅 opening_scope
  → FS3 P3 SequenceMap：仅 opening 序列
  → FS4 P4 SceneBeat + Canon：gate=内容完备；PASS 后按 auto_promote.p4_canon / p4_canon_seed 升 canon
  → FS5 P5 开篇批次 ChapterPlan（默认 ch1–3；逐章常规 gate）
  → FS6 P6 ManuscriptUnit 开篇批次 + 存稿 buffer
  → FS7 连载循环：buffer ⇄ P5/P6；critic 按 cadence 独立子代理抽检；反馈 → change（禁静默改 canon）；
         卷末 volume_checkpoint（卷报告 + 用户确认；unattended_mode=true 降级留痕续跑）后才开新卷
```

最小用户指令映射：开网文 → `new_project`；继续 → `advance`；写第 N 章 → `write_unit`；卡点 → `diagnose`；读者要改 → `change`。

---

## 7. 知识库用法

| 规则 | 说明 |
|------|------|
| 身份 | 只读服务；**不**写入 `knowledge/` |
| 引用 | 仅 `K-{DOMAIN}-{NNN}`（CONCEPT/STRUCT/CHAR/CONFLICT/WORLD/WRITE） |
| 深度 | `L1–L4` 为**阅读策略提示**（非物理分段；默认取 L2 操作层，见 blocks 检索协议） |
| 预算 | 每 phase `knowledge_budget`：`max_blocks` 上限 + **core 必拉（有序）+ situational 按触发标签**（contracts §0.4） |
| 装载 | advance/write：**contract core+situational**；write_unit 复用 P6 预算 + unit_type 表（protocol §4.2）；diagnose/learn：**经 index 路由** |
| 解析 | K-ID → 位置：查 [`knowledge-blocks.md`](knowledge-blocks.md)（**全 intent 可查**）→ 源文件 `<!-- K-ID -->` 锚点取片段 |
| 路由 | [`knowledge-index.md`](knowledge-index.md)：**仅 diagnose/learn**（症状域枚举见其 §2.0） |
| 冲突 | K-xxx **永不**覆盖项目 canon/资产事实 |

Agent 需要方法时：contract 白名单（或 index 路由）→ blocks 解析 → 锚点取片段 → 填资产字段；禁止把 111 块当上下文预热，禁止整读知识文件绕过预算。

---

## 8. 文件地图

| 路径 | 职责 |
|------|------|
| `SKILL.md` | **本入口**：定位 / 启动 / intent / 阶段索引 / 网文 FS 短节 |
| `runtime/protocol.md` | 总控：BOOT、状态机、召回、回写、BLOCK |
| `runtime/phase-contracts.md` | P1–P6 契约链 |
| `runtime/asset-types.md` | 资产 type + Manifest + status |
| `runtime/conflict-playbook.md` | 分歧/变更裁决 |
| `runtime/glossary.md` | 术语 SSOT |
| `runtime/project-scaffold.md` | **`new_project` 强制脚手架** |
| `runtime/web-serial-playbook.md` | **`route=web` 生长播放书** |
| `runtime/writeback-acceptance.md` | **DONE 前 writeback 硬验收** |
| `phases/01–06-*.md` | **薄操作清单**（越界以 phase-contracts 为准） |
| `templates/*` | 资产草稿壳（status/manifest/decision/plot-spine/chapter-plan/recap/style-card/…） |
| `knowledge/**` | 111 知识块（含 `05-连载运营/`；只读；块首有 `<!-- K-ID -->` 锚点） |
| `knowledge-index.md` | 诊断/学习路由表（非日常创作入口；含症状域枚举） |
| `knowledge-blocks.md` | K-ID 目录 + **检索协议**（全 intent 解析器） |
| `tools/validate.py` | 结构校验器（`--skill` 库检 / `--project` 项目检；用法见 `tools/README.md`） |

类型依赖（逻辑）：`Blueprint → PlotSpine → SequenceMap → SceneBeat → ChapterPlan → ManuscriptUnit`，旁路 `Character` / `WorldRule` / `Thread` → `Canon`；全程 `Status` + `Manifest` + `Decision`。

---

## 9. 会话最小响应契约

1. 声明判定的 `intent` + `mode`（或澄清问题）  
2. 若有项目：报告 `Status.phase`、`route`、关键资产 `status`、`stale`/`blockers`  
3. 执行 load → run → **writeback-acceptance**（主观 gate 以 evidence_checks 留证）→ writeback（范围内）  
4. 返回：产出 type/id/rev/status、gate 结果、`fail_codes`（若有）、下一步 intent 建议  

**DONE 前必过**：[`runtime/writeback-acceptance.md`](runtime/writeback-acceptance.md)（全局 MUST M01–M13 + 本 intent 额外 MUST；`learn` 零写跳过）。

**用户可选起点（映射 intent）**：从零 → `new_project`；**已有稿件接管 → adopt（scaffold §1.4）**；已入轨推进 → `advance`；写一章 → `write_unit`；卡点 → `diagnose`；改设定/反馈落地 → `change`（修订轮见 protocol §2.4 revise）；发布 → publish 快径（touch 晋升 `locked`）；学方法 → `learn`；问进度 → report 快径。

---

## 修订

| rev | 说明 |
|----:|------|
| 1 | 2026-08-12 深度审计重构基线（薄路由入口） |
| 2 | **2026-08-13 修复轮**：知识块 106→111；publish 语义统一 = touch 晋升 locked；auto_promote 增 p4_canon_seed；FS7 补 critic 独立子代理抽检与 unattended_mode 降级注记；第三波收尾（V1 复检修正：冷启动条件行/六件套允许集/小节指针/编号/口径对齐） |
