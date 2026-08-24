# ManuscriptUnit 模板（P6 正文单元）

> **本模板实例化** `runtime/asset-types.md` §2.13 `ManuscriptUnit`；门禁以 `runtime/phase-contracts.md` §7（P6）为准。别名 `ProseUnit` 写回归一，禁止独立 type。  
> 前置：`ChapterPlan` ≥ `review`；本章 `SceneBeat` ≥ `review`；出场 `Character` / 触达 `WorldRule` = `canon`；无未处理 `stale`。  
> **P6 硬边界**：只写正文与章内语言微调；禁止静默改 `PlotSpine` / `SequenceMap` / `Character` / `WorldRule` canon；大改章价值弧 → 回 P5 修 `ChapterPlan`。  
> `[方括号]` 占位。通用工程层，禁止绑定具体作品；知识仅引用 `K-xxx`。

---

## 1. YAML（信封 + 最小字段；唯一真值）

```yaml
---
# ── 通用信封 ──
id: ms_[nnnn]                     # 与四位章号对齐，如 ms_0001
type: ManuscriptUnit
rev: 1
status: draft                     # draft|review|canon|locked|stale|archived；review→canon（gate PASS 存稿）→locked（发布）
title: "[章题 / 人读标签]"
created_at: "[YYYY-MM-DDTHH:MM:SSZ]"
updated_at: "[YYYY-MM-DDTHH:MM:SSZ]"
depends_on:
  - { type: ChapterPlan, id: chapter_[nnnn], min_rev: 1 }      # 强制
  # - { type: SceneBeat, id: scene_v[v]_[s]_[nn], min_rev: 1 }
stale_reason: null
tags: []
uri: null

# ── 最小字段 ──
chapter_plan_id: chapter_[nnnn]   # 必须解析到 Manifest 中 ChapterPlan(review+)
word_count: 0                     # 成稿后统计；与 ChapterPlan.word_count_target 对表（web ±15%）
pov: "[POV 角色 id 或叙述视角标签]"
tense: past                       # past | present | mixed（mixed 须有理由）
body_uri: null                    # 正文位置；正文内嵌本文件正文区时可填相对锚点

summary_after: "[必填：写后摘要 3–8 句——发生了什么、谁变了、悬在哪；下一章召回的第一入口]"

continuity_delta:                 # 必填（无新事实也须显式给空数组）；按 auto_promote.facts_upsert 入卷分片
  - fact: "[本章确立/揭示的事实一句话]"
    entity_ids: []                # 涉及实体 id；作 canon_continuity_v{n} 检索键
    spoiler_level: 0              # 0=已向读者揭示；≥1=读者未知，正文只可潜台词

hooks_realized:                   # 对齐 ChapterPlan.hooks；web 强制 close=true
  open: null                      # true | false | null
  close: null

evidence_checks:                  # 证据制自查（替代自评 bool 矩阵）：每条附正文摘引 quote（≤30字）+ 一句论证 note
  # 必须覆盖五类：六问要点 / 钩子实现 / canon 无冲突 / 未泄密 / 口癖自查
  - { claim: "六问·谁在推动场景", quote: "[≤30字摘引]", note: "[一句论证]" }
  - { claim: "六问·他想要什么", quote: "", note: "" }
  - { claim: "六问·为什么他想要它", quote: "", note: "" }
  - { claim: "六问·什么在阻止他", quote: "", note: "" }
  - { claim: "六问·后果是什么", quote: "", note: "" }
  - { claim: "六问·下一步是什么", quote: "", note: "" }
  - { claim: "钩子实现：open/close 在正文落地", quote: "", note: "" }   # 与 hooks_realized 互证
  - { claim: "canon 无冲突：未静默引入新设定", quote: "", note: "" }
  - { claim: "未泄密：对照 Thread.reveal_point 与 facts.spoiler_level", quote: "", note: "" }
  - { claim: "口癖自查：对照 canon_style.taboo_list 无命中", quote: "", note: "" }   # K-WRITE-018
  - { claim: "对话三原则抽检（K-WRITE-016）", quote: "", note: "" }                    # contracts §7.5 必查
  - { claim: "描写六要诀抽检（K-WRITE-017）", quote: "", note: "" }                    # contracts §7.5 必查

thread_ids_touched: []            # 本章实际触及的 Thread id（仅触线引用；埋/推/收明细唯记 Thread 账本）

issues: []                        # 残留问题；非空不宜升 canon

serial_notes:
  payoff_realized: []             # 本章实际兑现的 ChapterPlan.serial_notes.payoff_entries[].id，如 [payoff_0001_1]
---
```

## 2. 填写指引

- **六问以 `K-WRITE-008` 原文为准**（不在此重抄）；写前写后各过一遍，答案落进 evidence_checks 对应六条。
- `evidence_checks` 每条 quote 取自本章正文（≤30 字），note 一句论证；答不出 = 该项 fail → repair_in_phase；结构性问题 → 回 P5。
- `summary_after` / `continuity_delta` 为必填 gate 项：是下一章 write_unit 召回的最低成本入口（召回表见 protocol §4.2；「前章 ManuscriptUnit」为条件召回行，首章无前章可豁免）。
- Thread 只留 `thread_ids_touched[]` 触线引用：正文实际埋/推/收直接回写 `Thread.advance_log` / `payoff`（唯一伏笔账本）；兑现的爽点条目 id 记入 `serial_notes.payoff_realized[]` 并同步 ChapterPlan 侧 `realized`。
- 写回清单：`rev += 1`；touch 所属卷 `manifest_units_v{n}`；更新 `Status`（active_unit / last_writeback / serial_cursor / buffer）；回写相关 `Thread` 与 `ChapterPlan.payoff_entries[].realized`（此同步已入 protocol §6.2 write_unit 允许集）；更新 `recap_state` 并滚动追加 `recap_book`（见 templates/recap.md）。
- 发现设定冲突 → block 发布，走 conflict-playbook；触及已发布（locked）事实 → 写 `retcon_note` 入 canon_continuity_v{n}，不回改旧章。

## 3. 正文区

frontmatter 为唯一真值；**本节以下即正文区**：直接撰写本章正文（或以 `body_uri` 外置，此处留空）。正文区自由撰写，不作字段对账。

---

## 修订

| rev | 变更 |
|----:|------|
| 1 | 初版（six_questions bool 矩阵 + craft_checks + canon_drift_scan + 镜像表，约 80 叶字段） |
| 2 | 2026-08-12 重构落地：瘦身至 28 叶字段——evidence_checks[]（claim/quote≤30字/note，预置条目覆盖六问/craft 口癖/canon 无冲突/未泄密）替代六问 bool 矩阵与 craft_checks/canon_drift_scan；summary_after 与 continuity_delta 升必填（delta 补 entity_ids/spoiler_level）；thread_ops_realized 删除改留 thread_ids_touched[]（Thread 账本唯一）；serial_notes 收敛为 payoff_realized[]；删 handoff_to_next/continuity_from_prev/buffer_count_hint、value/voice 冗余块、route/phase_home、gate_self_check 与全部镜像表；id 改 ms_{nnnn} |
| 3 | 2026-08-13 修复轮：状态链注释统一为 review→canon（gate PASS 存稿）→locked（发布），删「发布=canon」旧表述；写回清单 ChapterPlan realized 同步步骤注明已入 protocol §6.2 write_unit 允许集；前章召回注释补条件行首章豁免；页脚 schema_rev 对齐字样统一（schema_rev 3） |

*template_of: ManuscriptUnit | phase: P6 | schema_rev: 对齐 asset-types（schema_rev 3） | 通用工程层 · 不绑定具体作品*
