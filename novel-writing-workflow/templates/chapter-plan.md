# ChapterPlan 模板（P5 章纲）

> **本模板实例化** `runtime/asset-types.md` §2.9 `ChapterPlan`；门禁以 `runtime/phase-contracts.md` §6（P5）为准，只填字段不重定义 gate。  
> 前置：`scene_ids` 对应 `SceneBeat` ≥ `review`；出场 `Character` / 触达 `WorldRule` = `canon`；无未处理 `stale`。  
> 禁止：完整正文段落（P6 `ManuscriptUnit`）；节拍链展开（P4 `SceneBeat`）；静默改上游 canon。  
> `[方括号]` 占位。通用工程层，禁止绑定具体作品；知识仅引用 `K-xxx`。

---

## 1. YAML（信封 + 最小字段；唯一真值）

```yaml
---
# ── 通用信封 ──
id: chapter_[nnnn]                # 全局四位章号，如 chapter_0001
type: ChapterPlan
rev: 1
status: draft                     # draft|review|canon|locked|stale|archived；P6 开写前须 ≥ review
title: "[人读标签]"
created_at: "[YYYY-MM-DDTHH:MM:SSZ]"
updated_at: "[YYYY-MM-DDTHH:MM:SSZ]"
depends_on:
  - { type: SceneBeat, id: scene_v[v]_[s]_[nn], min_rev: 1 }   # 按 scene_ids 逐条展开
  # - { type: Thread, id: thread_[slug], min_rev: 1 }
stale_reason: null
tags: []
uri: null

# ── 最小字段 ──
chapter_no: 1                     # integer；与 id 四位编号一致
volume_no: 1                      # integer | null；决定注册进哪片 manifest_units_v{n}
title_working: "[工作标题，可空最终名]"
scene_ids:                        # 有序；每条须可追溯 SceneBeat 实例
  - scene_v[v]_[s]_[nn]
word_count_target: null           # integer | null；route=web 默认 2000–4500（可被 Status 覆盖）

# ── 钩子（唯一结构）──
hooks:
  open: "[章首钩；traditional 可空]"
  close: "[章末钩；web 必填]"
  close_type: null                # suspense|turn|info|emotion|promise|other | null

# ── 内容块（P5 核心；order/type/summary 必填，`subtext` 可选键——asset-types §2.9；禁止写成正文）──
content_blocks:
  - { order: 1, type: action, summary: "[本块叙事摘要：可见行动 + 一句潜台词意图，非成稿段落]" }
  - { order: 2, type: dialogue, summary: "[……]" }
  # type: dialogue | description | action | interior | exposition（五值闭集；旧值 narration 归一为 exposition，别名表见 asset-types §0.3.1；保持交替意识）
  # 潜台词意图默认并入 summary 一句；需单列时用可选键 subtext（勿双写）

# ── 解说策略（K-WRITE-001~005/007）──
exposition:
  must_pay:
    - "[本章必须支付给读者的信息]"
  strategy: show                  # 本章主策略：show|ammo|backstory|dialogue|environment|conflict|other
  avoid: [table_dusting, california_scene, dump]   # 固定三禁自检

# ── 伏笔（只留 thread_id 引用；埋/推/收明细唯记 Thread 账本）──
thread_ids: []                    # 本章触及的 Thread id

# ── 人物表现（三键；面具/声纹基准在 Character，不在此重抄）──
character_play:
  - { character_id: char_[slug], mask: "[本章启用的面具/社会表象]", key_behavior: "[关键可见行为]" }

# ── 连载字段（route=web 相关 gate 输入；traditional 可整块置 null）──
serial_notes:
  cliffhanger_level: 0            # 0|1|2|3（0=无；3=强断章）
  payoff_density: mid             # low|mid|high
  payoff_entries:                 # 爽点/信息增量台账（正式 schema；kind 词表 K-STRUCT-020）
    - id: payoff_[nnnn]_[n]       # payoff_{四位章号}_{序}
      kind: reveal                # dopamine|upgrade|reveal|reversal|emotion|humor（六枚举）
      intent: "[计划一句话：本处爽点/信息增量是什么]"
      realized: false             # P6 由 ManuscriptUnit.serial_notes.payoff_realized 回写并同步本字段（此同步已入 protocol §6.2 write_unit 允许集）
      thread_ids: []              # 关联 Thread；长线承诺仍走 Thread 账本，此处只引用
---
```

## 2. 填写指引

- `scene_ids` 非空且逐条可追溯；一场景跨章须在双方章纲声明。章级价值走向由场景 `value_start/value_end` 聚合，不在此重记。
- `content_blocks` 必填 order/type/summary（`subtext` 可选键，见 asset-types §2.9），保持类型交替意识（K-WRITE-011/013）；关键块的潜台词意图写进 `summary` 一句或单列 `subtext`（表面 ≠ 实质须可辨）；详拍住在 SceneBeat。
- `exposition.must_pay` 每条须有承载策略意识；`avoid` 三禁固定自检。
- 伏笔只挂 `thread_ids` / `payoff_entries[].thread_ids`；如何埋收写进 `Thread.advance_log`（唯一伏笔账本）。
- `payoff_entries` web 章至少一条 intent（gate「爽点或信息增量」输入）；`realized` 由 P6 `ManuscriptUnit.serial_notes.payoff_realized` 回写同步（此同步已入 protocol §6.2 write_unit 允许集）。
- 开篇章与其他章**同标准**逐章过 gate；「黄金三章」特殊标记已废弃（glossary §1.1）。
- gate 细则（含 evidence 制）见 phase-contracts §6；写回 `rev += 1` + touch 所属卷 `manifest_units_v{n}`。

## 3. 正文区

frontmatter 为唯一真值；本节以下为自由撰写区（章纲补记 / 备忘），不作机器对账输入。

---

## 修订

| rev | 变更 |
|----:|------|
| 1 | 初版（含 beats_detail / 双 hook / 镜像表，约 72 叶字段） |
| 2 | 2026-08-12 重构落地：瘦身至 36 叶字段——id 改 chapter_{nnnn} 四位（删 chapter_id 双键）；hooks 收敛 {open, close, close_type?}（删 hook 双结构别名）；content_blocks 收敛 order/type/summary 三键（beats_detail 并入 summary，删 beat_count/word_ratio/subtext 键）；foreshadow/payoff_ids 删除只留 thread_ids[]（Thread 账本唯一）；character_play 精简三键 {character_id, mask, key_behavior}；serial_notes 收敛 {cliffhanger_level, payoff_density, payoff_entries[]}（正式 schema id/kind 六枚举/intent/realized/thread_ids）；exposition 收敛 {must_pay, strategy, avoid}；删序列索引列表双写、value_start/end/emotional_arc/info_reveal/strategy_map/route/phase_home/gate_self_check 与全部镜像表；保留黄金三章废弃声明 |
| 3 | 2026-08-13 修复轮：content_blocks.type 枚举改五值闭集 dialogue/description/action/interior/exposition（narration→exposition，别名归一见 asset-types §0.3.1）；payoff_entries[].realized 注明由 ManuscriptUnit.serial_notes.payoff_realized 回写同步、已入 write_unit 允许集（protocol §6.2）；页脚 schema_rev 对齐字样统一（schema_rev 3）；第三波收尾（V1 复检修正：冷启动条件行/六件套允许集/小节指针/编号/口径对齐） |

*template_of: ChapterPlan | phase: P5 | schema_rev: 对齐 asset-types（schema_rev 3） | 通用工程层 · 不绑定具体作品*
