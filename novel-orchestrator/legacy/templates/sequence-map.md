# SequenceMap 模板 — P3 序列大纲

> **本模板实例化** `runtime/asset-types.md` §2.7 `SequenceMap`；门禁与知识预算以 `runtime/phase-contracts.md` §4（P3）为准。  
> 上游 P2 `PlotSpine`（节点 title + 一句话价值）→ 本资产（`event_summary` + `scenes[]`）→ 下游 P4 `SceneBeat`（beats）/ P5 `ChapterPlan`。  
> `[方括号]` 占位。通用工程层，禁止绑定具体作品；知识仅引用 `K-xxx`。

---

## 0. 硬边界（P3）

| 允许 | 禁止 |
|---|---|
| 序列 `0..23`：`event_summary` + `scenes[]`（每场 goal / opposition / value flip / turn_hint） | 章纲字段（章号、内容块、字数）；节拍定稿 `beats[]`（→ P4） |
| `reveal_plan` / `thread_ids` 挂载 / `info_to_pay` / 序列级 `conflict_layers` | 跳过 scenes 的长散文；正文；静默改 PlotSpine 节点价值 |

硬约束：逻辑全集 `0..23`（`0 = Hook` 必保）；缺序写入 `coverage_check.missing_indices`；每序列 `scenes.length ∈ [1,5]`；每场 `value_start ≠ value_end`；场景停在 `turn_hint`。

## 1. YAML（信封 + 最小字段；唯一真值）

```yaml
---
id: seqmap_v1                    # 每卷一份；模式 A 单卷视为 vol_01 → seqmap_v1
type: SequenceMap
rev: 1
status: draft                    # draft|review|canon|locked|stale|archived（文档级）
title: "[人读标签，如：vol_01 序列地图]"
created_at: "[YYYY-MM-DDTHH:MM:SSZ]"
updated_at: "[YYYY-MM-DDTHH:MM:SSZ]"
depends_on:
  - { type: PlotSpine, id: plotspine_main, min_rev: 1 }   # P3 门禁要求 ≥ review
  - { type: Blueprint, id: blueprint_main, min_rev: 1 }
  # - { type: Thread, id: thread_[slug], min_rev: 1 }
stale_reason: null
tags: [p3, sequence_map]
uri: null
route: traditional               # traditional | web
volume_id: vol_01                # 本图所属卷；与 id 卷号一致，供复合键 {volume_id, sequence_index}
numbering: "0-23"                # 卷内序列编号声明
scope:
  mode: all                      # all | sequence_range
  from: null
  to: null
coverage_check:
  has_seq0_hook: false           # seq 0 具备有效 event_summary + ≥1 scene 后改 true
  missing_indices: []            # 未产出条目的 index；scope 外列于此

sequences:
  - index: 0                     # 0..23；0 = Hook（必保）
    volume_id: vol_01            # 与文档级一致；条目自带复合键 {volume_id, sequence_index}，供报告/冲突 scope 摘出
    name: "[序列名；可继承 PlotSpine.nodes[N].title]"
    event_summary: "[本序列事件因果链 + 核心冲突；非场景散文；非章纲]"
    dramatic_function: setup     # 唯一命名：建置/递进/转折/高潮/收束等功能标签
    value_shift: "[进入值 → 离开值]"   # 唯一命名：序列级价值弧
    scenes:                      # 1–5 条；停在 turn_hint，不写 beats
      - scene_id: scene_v1_0_01  # 与 SceneBeat.id 同一 id 体系（scene_v{v}_{s}_{nn}，单 ID）
        name: "[场景名]"
        driver: "[驱动者/主动方；必填]"
        goal: "[场景目标]"
        opposition: "[阻力 / 对抗]"
        value_start: "[进入价值]"
        value_end: "[离开价值；必须 ≠ value_start]"
        turn_hint: "[期望 vs 结果一句话；停在此]"
        setting_hint: null       # 可选：时空一语，非描写
    conflict_layers:             # 序列级三层面；非场次过程
      inner: null
      inter: null
      extra: null
    thread_ids: []               # 本序列触及的 Thread id
    reveal_plan: []              # [{ character_id, onion_layer }]；层 id: surface|behavior|emotion|belief|wound
    info_to_pay: []              # 只列「传什么」；方式留 P4/P5
    web_payoff_intent: null      # route=web：爽点/信息增量意图一句话
    status: draft                # 条目级 status（Manifest 只记文档级 status，此键不进注册表）
  # —— 复制上块补齐 scope 内全部 index；scene_id 前缀随 index 变 ——
---
```

## 2. 填写指引

- **锚点序列**（`event_summary` 须体现不可逆/方向转/终局语义）：`0, 6, 8, 12, 16, 18, 19, 22, 23`，对齐 PlotSpine 锚点词表；route=web 模式 B 下锚点 gate 以**本卷图**为准。
- 拆场启发式（任一变化可拆，仍 ≤5）：时空变 / 主导人物目标变 / 冲突层面变 / 价值方向变；删后无损则删。序列内冲击力递增，末场最强。
- `scenes[].scene_id` 先在此登记，P4 以**同一 id** 建 `SceneBeat` 实例（禁止双编号体系）。
- `reveal_plan` 洋葱层五值固定；高压序列不得只停 surface（有意伪装须在 event_summary 可辨）。
- scope 分批（web 允许 1–3 序列/轮）：gate 只强制 scope 内条目；缺序必须进 `missing_indices`，禁止用 scope 逃避锚点占位责任。
- 写回：`rev += 1` + touch `manifest_root`（本资产属设计资产）；旁路推进 `Thread` / `Character` / `WorldRule` 在各自资产上写回。

## 3. 正文区

frontmatter 为唯一真值；本节以下为自由撰写区（序列备忘 / 待决问题），不作机器对账输入。

---

## 修订

| rev | 变更 |
|----:|------|
| 1 | 初版（seqmap_main + S{seq}.{n} 编号 + 三组同义别名 + 全锚点 YAML 重复骨架） |
| 2 | 2026-08-12 重构落地：id 改 seqmap_v{n}（文档级与序列条目均补 volume_id，复合键可摘出）；scenes.scene_id 改 scene_v{v}_{s}_{nn} 单 ID 体系（删 S0.1 speak）；driver 升必填；name/dramatic_function/value_shift 唯一（删 title/narrative_function/value_arc 三组别名）；条目级 status 保留并注明 Manifest 只记文档级；删 24 行索引镜像表、锚点重复骨架与人读场景表 |
| 3 | 2026-08-13 修复轮：核对 locked 发布语义与 facts 字段名引用，本文件无涉及项；页脚 schema_rev 对齐字样统一（schema_rev 3） |

*template_of: SequenceMap | phase_home: P3 | schema_rev: 对齐 asset-types（schema_rev 3） | 通用工程层 · 不绑定具体作品*
