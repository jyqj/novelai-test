# P6 — Writing / ManuscriptUnit

**goal:** 按章纲产出可发布正文，通过证据制自检（六问/craft/canon/泄密）；不静默修改 canon。

> schema 与字段名以 `runtime/asset-types.md` 为准，本清单只列操作步骤。

---

## 1. 契约指针

| 文档 | 锚点 |
|------|------|
| `runtime/phase-contracts.md` | **§7 P6 ManuscriptUnit**（边界 / I/O / budget / gate / route_delta） |
| `runtime/asset-types.md` | `ManuscriptUnit` §2.13；别名 `ProseUnit→ManuscriptUnit` |
| `runtime/protocol.md` | `write_unit` 召回；writeback / Manifest / status |
| `runtime/conflict-playbook.md` | 设定漂移 → detect→classify→decide（禁止静默改 canon） |
| `runtime/glossary.md` | 术语 SSOT（本文件不重定义） |

`phase_id: P6` · `depends_on: [P5]` · `next: null`（或循环下一 ChapterPlan）· `rollback_to: P5`

---

## 2. 硬边界（§0.2 / §7.1）

**允许：** 对话/描写/动作/内心/叙述落地；语言打磨与章内微调（不改章级价值弧）；按 `ChapterPlan.content_blocks` 实现；回写 `Thread` 埋/收；前章 `ManuscriptUnit` 衔接；POV/时态/声音校准。

**禁止：**

1. 擅自改 `PlotSpine` / `SequenceMap` / `Character` / `WorldRule` canon（须 `change` + conflict）
2. 大改章价值弧或场景目标（回 P5 修 `ChapterPlan`）
3. 注册独立 type `ProseUnit`（归一 `ManuscriptUnit`）
4. 超 budget 灌方法论文；先资产后知识

---

## 3. 输入 / 产出

### inputs（§7.2）

| type | min_status | required |
|------|------------|----------|
| `ChapterPlan` | review | yes（当前章） |
| `ManuscriptUnit`（前章） | — | **条件行**：前章尚不存在时跳过（首章豁免），存在则必装 `summary_after` + 尾段（衔接） |
| `Character` | canon | yes（本章**出场**） |
| `WorldRule` | canon | yes（本章**触达**） |
| `SceneBeat` | review | yes（本章场景） |
| `Canon`（`canon_style` + invariants + continuity 分片） | canon | yes |
| `Recap` | — | `recap_state` 必装；`recap_book` / `recap_vol_{n-1}` **条件行**：尚不存在时跳过（首章/首卷豁免），存在则必装 |
| `Blueprint` | review | no（语气/类型） |
| `Status` / `Manifest` / `Thread` | — | 指针与 active∩当前卷伏笔 |

> **权威召回表 = `protocol §4.2`**（含 canon_style、continuity 分片、历史 facts 检索、spoiler 标注纪律）；上表仅列 gate 依赖最低集。

### outputs（§7.3）

| type | target_status | 说明 |
|------|---------------|------|
| `ManuscriptUnit` | draft →(自检) review →(gate PASS 按 auto_promote.chapter_canon_on_gate_pass) canon（存稿）→(publish) locked（已发布） | 章节正文 |
| `ChapterPlan` | —（status 不变） | 仅同步 `serial_notes.payoff_entries[].realized`（protocol §6.2 允许集） |
| `Thread` | review | 实际埋收回写 |
| `Recap` | canon | `recap_state` 更新 + `recap_book` 滚动追加 |
| `Status` | draft | `last_written_chapter`、存稿计数；critic 轮写 `last_critic_chapter` |

**knowledge_budget：** 见 §7.4 — `max_blocks: 10`；craft 向 K-WRITE-*（对话密集章 K-CHAR-013；action 章 K-WRITE-019；章内节奏 K-WRITE-020；critic 轮四查支撑 K-WRITE-018/021 + K-CHAR-013 + K-WRITE-022）+ K-WORLD-010；`on_overflow: truncate`（溢出组记 `session_report.knowledge_deferred`，下轮优先补拉，contracts §0.4）。

---

## 4. 有序操作步骤

```
[ ] 0. 自检：P5 gate 已过；inputs 无 stale；Status.route 已读
[ ] 1. 装载：按 protocol §4.2 权威召回表（ChapterPlan + SceneBeat[] + Character(出场,canon)
       + WorldRule(触达,canon) + canon_style + Thread(active∩当前卷) + Recap 三件
       + 前章 summary_after/尾段；recap_book/recap_vol_{n-1}/前章为条件行——首章/首卷豁免，
       存在则必装；spoiler 条目加「读者未知」标注）
[ ] 2. 锁定参数：pov / tense / voice；word_count_target；hooks{open,close}；value_start→end
[ ] 3. 按 content_blocks 起草（对话/描写/动作/内心/叙述）
       K-WRITE-002, K-WRITE-006, K-WRITE-011；章内节奏 K-WRITE-020
[ ] 4. 落地转折与钩子（章纲 gap / hooks.open+close 在 text 有对应）
       K-WRITE-001；打斗/动作章 K-WRITE-019
[ ] 5. 解说执行：must_pay 走冲突/弹药/show；禁 dump
       K-WRITE-001, K-WRITE-015
[ ] 6. 文风打磨：删冗余；具体细节；视角/时态/声音一致；口癖黑名单自检
       K-WRITE-008, K-WRITE-009, K-WRITE-016, K-WRITE-017；每 5 章/critic 轮 K-WRITE-018
[ ] 7. evidence_checks：六问（K-WRITE-008 源文逐问）/ craft / canon 冲突 / 泄密
       （对照 Thread.reveal_point × facts.spoiler_level）——每条 {claim, quote≤30字, note 一句论证}，禁裸 bool
[ ] 8. 填必填元数据：summary_after + continuity_delta（无变更也写 []）；hooks_realized{open,close}
[ ] 9. payoff realized 回写（route=web）：本章兑现的爽点/信息增量记入 ManuscriptUnit 旁路字段，
       并同步 ChapterPlan.serial_notes.payoff_entries[].realized（write_unit 对 ChapterPlan 仅
       允许此字段，protocol §6.2）
[ ] 10. canon 漂移扫描 → 暂停；走 change 或 conflict-playbook
[ ] 11. 更新 recap_state（+ recap_book 滚动追加；模板 templates/recap.md）
[ ] 12. writeback：ManuscriptUnit + Thread + Recap + Status 指针 + Manifest.rev
[ ] 13. critic_cadence 命中 → critic pass（contracts §7.9：独立子代理/新会话执行四查——
       口癖/水字/遮名/方向偏航；产 CritiqueReport；写回 Status.web_serial.last_critic_chapter）
[ ] 14. 若有下一 ChapterPlan → 循环本 phase；否则 idle
```

---

## 5. 产出 schema 要点

SSOT：`asset-types.md` **§2.13**（契约点名 `phase-contracts.md` §7.3）。正式 type：`ManuscriptUnit`。

```yaml
ManuscriptUnit:   # 最小字段见 asset-types §2.13
  id: ms_{nnnn}                # 与 chapter_{nnnn} 对齐
  chapter_plan_id: string
  body_uri: string             # 正文指针；writeback 后应有值
  word_count: int
  pov, tense: string
  hooks_realized: { open, close }
  evidence_checks:             # 证据制自检（替代 six_questions/craft_checks bool 矩阵）
    - { claim, quote, note }   # quote=正文摘引 ≤30 字；note=一句论证
  summary_after: string        # 必填：写后摘要，供续写召回与 recap 滚动
  continuity_delta: [...]      # 必填：本章连续性变更（无变更也写 []）
  issues: [string]             # 可选
```

落盘模板：[`templates/manuscript-unit.md`](../templates/manuscript-unit.md)。

---

## 6. Gate 摘要

细节：**见 `runtime/phase-contracts.md` §7.5 gate #1–#9**（evidence_checks 制，不重定义）。主观条款每条附 `{claim, quote≤30字, note}`，禁裸 bool。

| # | 检查项标题 |
|---|------------|
| 1 | 六问逐场景过检（文本以 K-WRITE-008 源文为唯一版本），每场 ≥1 条 evidence |
| 2 | 章纲转折/钩子已实现：hooks_realized{open,close} 对应 ChapterPlan.hooks（evidence 摘引钩子句） |
| 3 | 对话三原则抽检 ≥1 条 evidence |
| 4 | 描写六要诀抽检 evidence；show>tell、解说走冲突/弹药 |
| 5 | canon 无冲突：无未授权新设定（自查 evidence）；必须新增 → 走 change |
| 6 | **泄密检查**：对照 Thread.reveal_point × facts.spoiler_level，未揭示信息不直说（附 evidence） |
| 7 | 视角/时态/声音与 `canon_style` 一致 |
| 8 | summary_after / continuity_delta 非空（空变更显式 []）；recap_state 已更新（recap_book 已滚动） |
| 9 | **route=web**：章末钩子；字数 ±15%；爽点或信息增量（payoff_entries.realized 回写） |

---

## 7. on_fail / next / rollback_to

| 字段 | 值 |
|------|-----|
| `on_fail` | `repair_in_phase`（文风/六问/钩子未落地） |
| 同一 gate 条款连续 3 次 FAIL | `escalate`（contracts §0.5 repair 重试上限） |
| 结构/价值弧错误 | `rollback_to: P5`；相关 `ManuscriptUnit` 可标 stale |
| 设定冲突 | conflict-playbook → **block 发布**；禁止静默改 canon |
| `next` | `null`；有下一 `ChapterPlan` 则同 phase 循环 |
| `rollback_to` | `P5` |

---

## 8. route_delta（traditional vs web）

| | traditional | web |
|--|-------------|-----|
| 发布 | 可整部修订后 publish（晋升 `locked`） | 章级 canon 存稿；publish 晋升 locked（已发布）；存稿缓冲（Status） |
| 钩子/字数 | 钩子建议；字数灵活 | **强制**章末钩子；字数目标 ±15% |
| 爽点 | 节奏优先 | 每章至少一处爽点或信息增量 |
| 反馈 | 可选 | 支线调整须 Decision + 下游 stale |
| 开篇 | 建议打磨 | 与后续章同标准逐章过 gate，正文不得稀释章纲钩子 |

---

## 9. Agent 伪代码

```
run_P6(chapter_id):
  require ChapterPlan.status ≥ review
  require Character(出场).status == canon and WorldRule(触达).status == canon
  recall per protocol §4.2      # 权威召回表；含 Recap 三件 + spoiler 标注纪律
  if any input.status == stale: BLOCK → sync|conflict
  budget_pull(knowledge_budget)  # craft K-IDs only; assets first
  draft text by content_blocks; realize hooks {open, close}
  fill evidence_checks           # 六问/craft/canon/泄密 逐条 {claim, quote, note}
  fill summary_after + continuity_delta   # 必填
  if setting_drift: block + conflict-playbook  # never silent canon edit
  if chapter_value_flip_broken: rollback_to P5
  sync ChapterPlan.serial_notes.payoff_entries[].realized  # web；write_unit 对 ChapterPlan 仅此字段
  update recap_state (+ recap_book append)
  writeback ManuscriptUnit(status≥review), Thread, Recap, Status, Manifest
  if critic_cadence hit: critic pass (contracts §7.9 独立子代理四查；写回 last_critic_chapter)
  if more ChapterPlan pending: loop else idle
```

---

> 修订注 rev2（2026-08-12）：头部加 asset-types 为准声明；summary_after/continuity_delta 升必填；gate 改 evidence_checks 制（六问/craft/canon/泄密）+ recap 检查；hooks_realized{open,close}；伪代码 require 加「出场/触达」限定；操作清单补「evidence_checks」「更新 recap_state」两步与 critic pass 衔接；召回指针改 protocol §4.2。
>
> 修订注 rev3（2026-08-13 修复轮）：outputs 章状态链改 draft→review→canon（存稿）→locked（publish=已发布）+ ChapterPlan realized 同步行；inputs 表补 Canon 行并给前章/recap_book/recap_vol_{n-1} 标条件行（首章/首卷豁免）；操作清单插入步骤 9「payoff realized 回写」；critic pass 同步 contracts §7.9（独立子代理四查 + last_critic_chapter）；白名单同步（unit_type=dialogue→K-CHAR-013、critic_round 四块）；on_fail 补 3 次 FAIL→escalate。
