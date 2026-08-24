# Status 模板 — 项目运行态单例

> **本模板实例化** `runtime/asset-types.md` §2.1 `type: Status`（实例 id 固定 `status_project`）。  
> 门禁以 `runtime/phase-contracts.md` 为准；intent 路由 / writeback 指针 / 阻断码语义见 `runtime/protocol.md`；连载游标与存稿语义见 `runtime/web-serial-playbook.md` §5——本文件只引用不重定义。  
> `[方括号]` 为占位，填后删除括号。通用工程层 only，禁止绑定具体作品/角色名。

---

## 1. YAML（信封 + 最小字段；唯一真值）

```yaml
---
# ── 通用信封（asset-types §0.2）──────────────────────────
id: status_project
type: Status
rev: 1
status: canon                    # draft | review | canon（本 type 常态 canon；不用 locked/stale/archived）
title: "[工作区显示名 / 运行态]"
created_at: "[YYYY-MM-DDTHH:MM:SSZ]"
updated_at: "[YYYY-MM-DDTHH:MM:SSZ]"
depends_on: []
stale_reason: null
tags: []
uri: null                        # storage adapter 填充；协议层可空

# ── 运行态最小字段（asset-types §2.1）───────────────────
mode: idle                       # new_project | advance | write_unit | diagnose | change | learn | idle
phase: idle                      # P1 | P2 | P3 | P4 | P5 | P6 | idle
phase_gate: pending              # pending | passed | failed | blocked
blockers: []                     # 空数组=可推进；条目 { code, message, related_asset_ids[] }；code 语义见 protocol §7.1

active_unit:                     # 当前写作/规划焦点；无焦点均 null
  type: null                     # SceneBeat | ChapterPlan | ManuscriptUnit | null
  id: null
last_writeback:
  asset_id: null
  rev: null
  at: null                       # ISO-8601
load_policy_rev: 1               # 与 protocol 召回策略版本对齐；策略变更时 +1

flags:
  dual_track: traditional        # traditional | web_serial | hybrid（hybrid 只存在于本 flag，route 仍二值）
  knowledge_budget_default: 12   # 单轮知识块数上限默认；可被 phase budget 覆盖
  critic_cadence: "every_5_chapters + volume_end"   # critic 独立评审轮节律（phase-contracts §7）
  unattended_mode: false         # 默认 false = 半自动（publish/卷界 checkpoint 人批）；true = volume_checkpoint 降级协议（web-serial-playbook §9.2）；变更须 Decision(user)

route: traditional               # traditional | web（闭集二值；未声明默认 traditional）

# ── web_serial（route=web 必填；traditional 项目整块保持 null 值即可）──
web_serial:
  current_volume: vol_01         # 卷命名空间锚点；复合键 {volume_id, sequence_index} 的 volume 端
  opening_scope:                 # 开书窗口（语义与预设见 web-serial-playbook §2/§6）
    volume_id: vol_01
    sequence_range: [0, 6]
    chapter_range: [1, 3]
  buffer:
    target_chapters: 3           # 目标存稿章数（可配 2–7）
    ready_count: 0               # status ∈ {review,canon} 且 chapter_no > last_published_chapter 的 ManuscriptUnit 数（发布 = locked）
    min_before_publish: 1        # 首次公开发布前最低存稿
  serial_cursor:
    last_published_chapter: 0    # 0 = 尚未发布；仅作游标不作判据（已发布判定唯一 = status==locked）；修订已有章不动本游标（revision 旁路）
    next_write_chapter: 1        # 下一 ManuscriptUnit
    next_plan_chapter: 1         # 下一 ChapterPlan（可超前 write）
  last_critic_chapter: 0         # 最近完成 critic 轮的章号；落后 flags.critic_cadence 周期 = 漏跑可检（validate WARN）
  auto_promote:                  # 常任授权（route=web 默认全 true）；变更本块须 Decision(approved_by=user)
    p4_canon: true               # P4 gate PASS 后设计资产自动升 canon（留 Decision(agent_auto) 痕）
    p4_canon_seed: true          # P4 gate PASS 时 canon_root / canon_style 种子随之升 canon（留 Decision(agent_auto) 痕）
    chapter_canon_on_gate_pass: true   # 章过 P6 gate 后自动升 canon（存稿；publish 再升 locked）
    facts_upsert: true           # continuity_delta 自动 upsert 入 canon_continuity_v{n}
  auto_publish: false            # 默认 false：发布始终人批（支持「发布第 N–M 章」批量区间确认）；true 行为协议见 web-serial-playbook §6.4；变更须 Decision(user)
  adopt_cursor: null             # 接管旧稿消化进度（project-scaffold Adopt 消化 pass）；如 { last_digested_chapter: 120 }
---
```

## 2. 填写指引

| 项 | 规则 |
|---|---|
| `mode` | 七值闭集（含 `idle`）；写入别名归一：`new`→`new_project`、`continue`→`advance` |
| `phase` / `phase_gate` | gate 未 PASS 禁止把 `phase` 推到下一阶段；`blockers` 非空时 `phase_gate=blocked`，清空后回 `pending`/`passed` |
| 指针更新 | 每次 writeback 成功（protocol WB_8）必须更新本单例：`rev += 1`、`updated_at=now()`、`last_writeback` 三键；开写/规划某 unit 时置 `active_unit`，完成后归 null 或指向下一 unit |
| `route` / `dual_track` | `route` 二值闭集；`web` ⇔ `dual_track=web_serial`；中途改轨或 hybrid 须写 Decision |
| `web_serial` | 游标/存稿的重算与发布就绪规则见 web-serial-playbook §5–§6（publish = touch 晋升 locked，唯一默认）；`auto_promote` 的授权级别表见 asset-types §2.4，不在此重抄 |
| `flags.critic_cadence` | 到点触发独立评审轮（独立子代理/新会话执行；输入与动作规格见 phase-contracts §7.9），不合格 → repair_in_phase；完成后回写 `web_serial.last_critic_chapter`，漏跑可检 |
| `flags.unattended_mode` | 默认 `false` = 半自动（publish 与卷界 checkpoint 人批）；`true` 时 volume_checkpoint 降级：卷报告照常落盘 + Decision(agent_auto, pending_human_review) 后继续开卷，session_report 提示积压待审；配置变更须 Decision(user) |
| Manifest | 本单例在 `manifest_root` 占 entry（AT4 自描述）；每次写回 touch |

## 3. 正文区

frontmatter 为唯一真值；本节以下为自由撰写区（运行笔记 / 当前焦点 / 下一步建议），不作机器对账输入。

---

## 修订

| rev | 变更 |
|----:|------|
| 1 | 初版 |
| 2 | 2026-08-12 重构落地：补全 `web_serial` 块（opening_scope/buffer/serial_cursor/current_volume/auto_promote/auto_publish/adopt_cursor）与 `flags.critic_cadence`；`mode` 枚举收编 `idle`；`route` 收敛二值；删正文镜像表与长自检单 |
| 3 | 2026-08-13 修复轮：flags 增 unattended_mode（默认 false，卷界降级协议开关）；web_serial 增 last_critic_chapter（critic 漏跑可检）与 auto_promote.p4_canon_seed；publish/locked 语义注释统一（发布=locked、ready_count 判定、last_published_chapter 仅游标）；critic 轮指引改指针 phase-contracts §7.9 |

*template_for: Status | singleton: status_project | schema_rev: 对齐 asset-types（schema_rev 3） | 通用工程层 · 不绑定具体作品*
