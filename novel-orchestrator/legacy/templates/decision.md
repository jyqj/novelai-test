# Decision 模板 — 分歧裁决 / 变更留痕

> **本模板实例化** `runtime/asset-types.md` §2.4 `type: Decision`。裁决流水线见 `runtime/conflict-playbook.md`（`detect → classify → decide → record → mark_stale → sync|block`）。  
> **默认用最小骨架（§1）**；仅冲突流水线需要完整溯源时再加 §3 可选块。  
> `[方括号]` 占位。通用工程层，禁止绑定具体作品；知识仅引用 `K-xxx`。

---

## 1. 最小骨架（YAML；默认形态）

```yaml
---
id: decision_[yyyyMMdd]_[slug]
type: Decision
rev: 1
status: draft                     # draft|review|canon|locked|archived（本 type 无 stale）
title: "[短标题：裁决了什么]"
created_at: "[ISO-8601]"
updated_at: "[ISO-8601]"
depends_on: []                    # 被裁决源 / 关联 Canon 等；无则 []
stale_reason: null
tags: []
uri: null

approved_by:                      # 必填：user | agent_auto（级别表 asset-types §2.4，速查见 §2）；留空 = validate FAIL
decision_type: conflict_resolve   # conflict_resolve | user_override | unlock | scope_change | simple_change | deprecate
priority_basis: user_turn         # user_turn | decision | canon_invariant | higher_phase_lock | working

problem_summary: "[一句话：矛盾 / 请求 / 解锁原因是什么]"
options_considered:
  - "[方案 A]"
  - "[方案 B]"
chosen: "[最终采纳：对应 options 中一项或合并表述]"

affects_asset_ids: []
follow_up:
  mark_stale: []                  # 须标 stale 的下游 id
  sync_required: false
  block_phase_until: null         # 阻断条件说明；无则 null
expires_at: null                  # 临时覆盖可设 ISO-8601；永久裁决 null
---
```

## 2. 填写指引

- **approved_by 速查**（全表以 asset-types §2.4 / conflict-playbook 为准，不在此重抄）：
  - 必须 `user`：解锁 locked、砍 `must_not_drop` 线、推翻/修改 `Canon.invariants`、分卷模式 A/B 切换、弃档重开、开新卷确认（volume_checkpoint）、`auto_promote` / `auto_publish` / `unattended_mode` 配置变更。
  - 允许 `agent_auto`（自批即生效，须留痕）：scope_change、Thread 常规增删（非 must_not_drop）、gate PASS 后按 `auto_promote` 的 canon 晋升、非 invariant 的 stale 风险接受、simple_change。
- 生效中的裁决建议 `status ≥ canon`；blocking 冲突至少 `review` 才允许相关 write。
- `follow_up.mark_stale` 须在 writeback 后真实改 status；`affects_asset_ids` 须 Manifest 可寻址。
- 改 `locked` 目标：`decision_type=unlock` 或 `user_override`，且 `approved_by=user`。
- 写回：注册/touch `manifest_root`；被本裁决取代的旧 Decision 用 §3 `supersedes` 链接后归档。

## 3. 可选溯源块（冲突流水线时追加进 frontmatter）

```yaml
# ── 以下全部可选；simple_change / 常规留痕不需要 ──
taxonomy:
  primary: null                   # vertical_drift | lateral_conflict | version_skew | intent_gap | critique_unmerged
  secondary: []
severity: null                    # low | medium | high | critical
conflict_id: null                 # cr_[id]
priority_applied:
  winner_ref: null                # user_turn | asset_ref | decision_ref
  loser_refs: []
ruling:
  action: null                    # keep_winner | merge | rewrite_loser | supersede_decision | split_scope | escalate_user
  claims_adopted: []              # [{ claim, binds_to: [asset_id] }]
  claims_rejected: []             # [{ claim, from: asset_id }]
impact:
  must_update: []                 # [{ ref, change }]
  do_not_touch: []                # [{ ref, reason }]
  sequences: []                   # 复合键 [{ volume_id, indices: [0..23] }]
  threads: []
execution:
  sync_status: pending            # pending | in_progress | done | blocked
  exit: sync                      # sync | block
supersedes: null                  # decision_[id] | null
superseded_by: null
related:
  critique_ids: []
  knowledge_refs: []              # 仅 K-xxx；永不覆盖项目事实
  evidence_quotes: []             # 短摘录
```

## 4. 正文区

frontmatter 为唯一真值；本节以下为自由撰写区（问题展开 / 备选对比 / 裁决理由），不作机器对账输入。

---

## 修订

| rev | 变更 |
|----:|------|
| 1 | 初版（problem/options 别名双写；status 含 stale；完整溯源块为默认形态） |
| 2 | 2026-08-12 重构落地：新增必填 `approved_by: user\|agent_auto` + 授权级别速查（引用 asset-types §2.4 不重抄）；status 枚举删 stale；problem_summary/options_considered 唯一（删短名别名）；最小骨架升为默认形态，溯源块降为可选；impact.sequences 改复合键；删正文镜像表 |
| 3 | 2026-08-13 修复轮：approved_by 删默认值 agent_auto，改空占位（留空 = validate FAIL）；速查 user 行补「开新卷确认（volume_checkpoint）」，配置变更扩为 auto_promote / auto_publish / unattended_mode |

*template_of: Decision | schema_rev: 对齐 asset-types（schema_rev 3） | 通用工程层 · 不绑定具体作品*
