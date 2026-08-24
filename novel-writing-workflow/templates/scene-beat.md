# SceneBeat 模板（P4 细纲 / 场景节拍）

> **本模板实例化** `runtime/asset-types.md` §2.8 `SceneBeat`；门禁以 `runtime/phase-contracts.md` §5（P4）为准。  
> 前置：父场景已在 `SequenceMap.scenes[]` 登记同一 id（`status ≥ review`）；相关 `Character` / `WorldRule` 本阶段升 `canon`；无未处理 `stale`。  
> 禁止：以章号为主键的内容块章纲（P5）、完整正文段落（P6）、静默改上游 canon。  
> `[方括号]` 占位。通用工程层，禁止绑定具体作品；知识仅引用 `K-xxx`。

---

## 1. YAML（信封 + 最小字段；唯一真值）

```yaml
---
# ── 通用信封 ──
id: scene_v[v]_[s]_[nn]           # 卷v_序列s(0..23)_场次nn，如 scene_v1_0_01；速记 v1:s0
                                  # 单 ID 体系：SequenceMap.scenes[].scene_id 用同一 id，无第二编号
type: SceneBeat
rev: 1
status: draft                     # draft|review|canon|locked|stale|archived
title: "[场景人读标签]"
created_at: "[YYYY-MM-DDTHH:MM:SSZ]"
updated_at: "[YYYY-MM-DDTHH:MM:SSZ]"
depends_on:
  - { type: SequenceMap, id: seqmap_v[n], min_rev: 1 }
  # - { type: Character, id: char_[slug], min_rev: 1 }
  # - { type: Thread, id: thread_[slug], min_rev: 1 }
stale_reason: null
tags: []
uri: null

# ── 归属（复合键）──
sequence_ref:
  volume_id: vol_01
  sequence_index: 0               # integer 0..23；0 = Hook
order_in_sequence: 1              # 本序列内序位 1-based；与 id 尾号 nn 一致

# ── 时空 / 视角 ──
pov: char_[slug]
location: "[地点一语，非描写散文]"
time_marker: null                 # string | null；相对时间锚

# ── 目标 / 冲突（goal 即驱动目标，唯一字段；不设 driver_goal 别名）──
goal: "[本场驱动者要达成什么]"
conflict:
  opposition: "[对抗力量 / 障碍 / 对手意志]"
  stakes: "[若不达会怎样]"
  escalation: "[压力如何升级一句话；可空]"

# ── 价值弧（唯一命名；gate：起 ≠ 终）──
value_start: "[进入场景时的价值状态]"
value_end: "[离开场景时的价值状态；必须 ≠ value_start]"

# ── 转折 / 鸿沟 ──
outcome: "[场景结果：得 / 失 / 得而有代价 / 失而有收获]"
turning_point:
  expectation: "[角色/读者期望发生什么]"
  result: "[实际发生什么]"
  gap: "[期望与结果之间的裂缝；gate 非空]"   # K-STRUCT-011

# ── 节拍链（gate：≥2 轮 action↔reaction；禁止写成正文）──
beats:
  - { n: 1, action: "[驱动动作 / 可见行为]", reaction: "[对抗反应 / 世界回击]", value_delta: "[本拍价值微移；可空]" }
  - { n: 2, action: "[……]", reaction: "[……]", value_delta: null }

# ── 四重效果（gate：≥3/4 有效——每键填一句依据，无效留 null；非裸 bool，见 contracts §5.5 #3）──   K-STRUCT-012
four_effects:
  surprise: null                  # 惊奇：一句依据 | null
  curiosity: null                 # 好奇：一句依据 | null
  insight: null                   # 见解：一句依据 | null
  new_direction: null             # 新方向：一句依据 | null

# ── 人物压力 / 洋葱揭示（单账；层 id 固定五键，wound=创伤，禁止另造键名）──
character_pressure:
  - character_id: char_[slug]
    pressure: "[本场对该角色的压力点]"
    reveal_layer: surface         # surface|behavior|emotion|belief|wound（表象|行为|情感|信念|创伤）
    note: "[揭示什么；可空。高压场景不得长期停在 surface，除非有意伪装并注明]"

# ── Thread 操作（只写引用；账本细节唯记 Thread）──
thread_ops:
  - { thread_id: thread_[slug], op: plant, note: "[本场动作一句]" }   # op: plant|advance|payoff|tangle

exposition_ammo: []               # string[]；信息→冲突弹药要点（K-WRITE-002）；可空

# ── 节奏标注（嵌入字段，非独立 type）──
rhythm:
  kind: peak                      # peak|ease|transition|build|release
  note: "[本场在序列内的张弛角色]"
  positive_release: false         # route=web：正面价值释放
  power_upgrade_hook: false       # route=web：挂钩力量/地位升级节点

# ── 作家六问：以 K-WRITE-008 原文为准（不在此重抄）；写作前后各过一遍，评估入 ManuscriptUnit.evidence_checks ──

route: traditional                # traditional | web
phase_home: P4
---
```

## 2. 填写指引

- id / `sequence_ref` 为卷命名空间复合键；与 `SequenceMap.scenes[].scene_id` 严格同名（单 ID 体系，先在序列图登记再建本实例）。
- `beats` 末拍应落到 `value_end` / `outcome`；中段有可辨升级（K-STRUCT-002/010/018）。
- `four_effects` 有效 = `true` 或该键改写为一句说明；与邻接场景对照，避免连续同类刺激。
- `character_pressure.reveal_layer` 与 `Character.onion` 同一五层枚举；wound 层信息须「赚到」，冲突走 conflict-playbook。
- `thread_ops` 只挂引用；写回后与 `Thread.advance_log` 对齐。
- 写回：`rev += 1` + touch 所属卷 `manifest_units_v{n}`；目标 status ≥ `review`（P4 gate 细则见 phase-contracts §5）。

## 3. 正文区

frontmatter 为唯一真值；本节以下为自由撰写区（场景备忘 / 待决问题），不作机器对账输入。

---

## 修订

| rev | 变更 |
|----:|------|
| 1 | 初版（双编号 + value 双写 + 六问答案块 + 镜像表，约 79 叶字段） |
| 2 | 2026-08-12 重构落地：瘦身至 49 叶字段——id 改 scene_v{v}_{s}_{nn} 单 ID 体系（删场景双编号与父场景桥接字段）；sequence_ref{volume_id,sequence_index} 复合键替代裸 int 与序列别名；value_start/end 唯一（删价值双写别名）；conflict 只留对象形态且驱动目标并入顶层 goal；onion_reveal 并入 character_pressure；六问改一行引用 K-WRITE-008（评估入 ManuscriptUnit.evidence_checks，删本模板内答案块与自评布尔）；删 turn 别名、conflict_five_steps、gate_self_check 与全部镜像表；修 turning_point.gap 引号内伪注释 bug |
| 3 | 2026-08-13 修复轮：核对 locked 发布语义与 facts 字段名引用，本文件无涉及项；页脚 schema_rev 对齐字样统一（schema_rev 3）；第三波收尾（V1 复检修正：冷启动条件行/六件套允许集/小节指针/编号/口径对齐） |

*template_of: SceneBeat | phase: P4 | schema_rev: 对齐 asset-types（schema_rev 3） | 通用工程层 · 不绑定具体作品*
