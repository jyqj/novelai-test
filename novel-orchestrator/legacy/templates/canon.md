# Canon 模板 — 项目真值 / 不变量包

> **本模板实例化** `runtime/asset-types.md` §2.2 `type: Canon`。门禁以 `runtime/phase-contracts.md` 为准；冲突优先级见 `runtime/conflict-playbook.md`（`Canon.invariant` 位于栈高位，仅次于用户当轮指令与 Decision）。  
> 填写规则：`[方括号]` 占位，填后删除。通用工程层 only，禁止绑定具体书名/角色名作规范正文；知识仅引用 `K-xxx`，不粘贴理论长文。

---

## 0. 实例族（一 type 多实例）

| 实例 id | 承载 | 备注 |
|---|---|---|
| `canon_root` | `invariants` / `theme` / `forbidden` / `open_questions` | 单例；召回默认必装载 |
| `canon_continuity_v{n}` | 该卷 `facts[]` + `retcon_notes[]` | **每卷一片**；P6 高频追加，历史卷分片按实体检索 |
| `canon_style` | 文风基准卡 | 模板见 `templates/style-card.md`；scaffold 必建（new_project 第 6 件种子）；write_unit 每轮必召回 |
| `canon_theme` / `canon_lore` | 可选细分 | 主包不够清晰时才拆 |

均为 `type: Canon`，各自独立 `rev` / `status` / Manifest entry（注册于 `manifest_root`）；禁止另造 AssetType。双包对同一事实互斥 → `lateral_conflict` + Decision。

## 1. canon_root（YAML）

```yaml
---
id: canon_root
type: Canon
rev: 1
status: draft                    # draft|review|canon|locked|stale|archived；生效真值宜 ≥ canon
title: "[工作区真值包]"
created_at: "[YYYY-MM-DDTHH:MM:SSZ]"
updated_at: "[YYYY-MM-DDTHH:MM:SSZ]"
depends_on: []                   # 可选聚合来源，如 { type: Blueprint, id: blueprint_main, min_rev: 1 }
stale_reason: null
tags: [canon]
uri: null

invariants:                      # 硬约束；违反即 conflict；可空数组但不得用 open_questions 冒充
  - id: inv_[slug]
    statement: "[不可轻易违背的陈述；一句话可验证]"
    source_asset_ids: []         # 来源资产 id；无则 []

theme:                           # 主控思想真值（K-CONCEPT-013 / K-CONFLICT-002）
  controlling_idea: "[价值 + 原因；可自 Blueprint/PlotSpine 草案升格]"
  counter_idea: "[反思想 / 对立价值命题]"
  ending_mode: unset             # idealist | pessimist | positive_irony | negative_irony | unset

forbidden: []                    # 明确禁止的走向/设定；可空；优先级高于下游设计
open_questions: []               # 未裁决问题；解决前不得当已 canon 事实引用
---
```

连续性事实**不存放在 root**：入当前卷分片 `canon_continuity_v{n}`（§2）。

## 2. canon_continuity_v{n}（YAML，卷分片）

```yaml
---
id: canon_continuity_v1          # 每卷一片；卷号对齐 Status.web_serial.current_volume
type: Canon
rev: 1
status: canon
title: "[vol_01 连续性事实分片]"
created_at: "[YYYY-MM-DDTHH:MM:SSZ]"
updated_at: "[YYYY-MM-DDTHH:MM:SSZ]"
depends_on:
  - { type: Canon, id: canon_root, min_rev: 1 }
stale_reason: null
tags: [canon, continuity]
uri: null

facts:                           # 只收「已发生 / 已向读者揭示」；未揭示计划属 Thread / SceneBeat
  - id: cf_[slug]
    fact: "[事实一句话]"
    revealed_at: "chapter_[nnnn]"   # chapter_{nnnn} | scene_v{v}_{s}_{nn} | unknown
    spoiler_level: 0             # 0=读者已知可直说；≥1=作者侧信息，正文只可潜台词/征兆（防剧透标注纪律）
    entity_ids: []               # 涉及实体 id（char_* / faction_* / world_*）；供历史分片实体检索（protocol §4.2）
    # superseded_by: rn_[slug]   # 被 retcon 推翻时追加（旧 fact 原文不删不改）；检索命中须连带装载对应 retcon_note，正文以 new_fact 为准

retcon_notes: []                 # 上游变更触及 locked（已发布）资产时：不标 stale，改记一条 retcon
# retcon_notes:
#   - id: rn_[slug]
#     affected_asset_ids: ["ms_0012"]
#     entity_ids: []             # 必填：涉及实体 id；实体检索命中被推翻旧 fact 时据此连带装载本条
#     old_fact: "[已发布章中的旧事实]"
#     new_fact: "[裁决后的新事实]"
#     forward_strategy: reconcile    # reconcile(圆回) | fade_out(淡出) | explicit_fix(显式修正)
#     decision_id: decision_[id]
---
```

## 3. 填写指引

- **invariants**：改写须 `change` intent + Decision（推翻/修改 invariants 的 `approved_by` 必须 `user`）；WorldRule 硬规则升 canon 后可提升入此并保留 `source_asset_ids`；删除或清空须 Decision。
- **facts 回写**：P6 `ManuscriptUnit.continuity_delta` 按 `Status.web_serial.auto_promote.facts_upsert` 自动 upsert 入当前卷分片（留 Decision(agent_auto) 痕）；开关关闭或 traditional 时需确认后写入。
- **召回**：`invariants` + 当前卷分片全量 + 按本章出场实体 id 在历史卷分片中检索命中的 facts；命中带 `superseded_by` 的 fact 必须连带装载对应 retcon_note，正文以 new_fact 为准（权威召回表以 protocol §4.2 为准）。
- **retcon 纪律**：`locked` = 已发布/冻结，不参与 stale 传播；触及 locked 的变更写 `retcon_notes` 一条（`entity_ids` 必填），并在被推翻的旧 fact 条目追加 `superseded_by: <retcon_id>`（旧 fact 原文不删不改）；后续章按 `forward_strategy` 向前兼容。
- **open_questions 关闭**：结论写入 `invariants` / `facts` / `theme` 并从列表移除（建议记 Decision）；禁止只删问题不落真值。
- **写回**：任一实例变更 → `rev += 1` + Manifest touch；改 `invariants` / `theme` / 关键 `forbidden` → 下游引用方按 conflict-playbook 标 `stale` 或 sync。

## 4. 正文区

frontmatter 为唯一真值；本节以下为自由撰写区（人读补充），不作机器对账输入。

---

## 修订

| rev | 变更 |
|----:|------|
| 1 | 初版（单包 continuity_facts） |
| 2 | 2026-08-12 重构落地：continuity_facts 改卷分片约定（canon_continuity_v{n}，条目补 entity_ids）；新增 retcon_notes[] 结构（locked 不 stale、forward_strategy 向前兼容）；新增 canon_style 切片（指向 templates/style-card.md）；invariants 不变；删正文镜像表与长自检单 |
| 3 | 2026-08-13 修复轮：连续性事实区块改名 facts（原 continuity_facts，子字段不变，注释同步）；retcon_notes 条目增必填 entity_ids；补 retcon superseded_by 纪律（旧 fact 追加、检索命中连带装载 retcon_note）；canon_style 标 scaffold 必建 |

*template_for: Canon | ids: canon_root \| canon_continuity_v{n} \| canon_style \| canon_{domain} | schema_rev: 对齐 asset-types（schema_rev 3） | 通用工程层 · 不绑定具体作品*
