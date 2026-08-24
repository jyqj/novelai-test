# StyleCard 模板 — canon_style 风格卡（Canon 切片）

> **本模板实例化** `type: Canon` 的文风切片，实例 id 固定 `canon_style`（实例族见 `templates/canon.md` §0）。  
> **用途**：① write_unit 每轮**必召回**，作为正文文风基准（权威召回表见 `runtime/protocol.md` §4.2）；② critic 抽检轮（`Status.flags.critic_cadence`）的对照基准——正文逐条对照 `taboo_list` 与句式约束，命中即 repair_in_phase（方法见 `K-WRITE-018` 口癖防治、`K-CHAR-013` 声纹卡）。  
> **建档**：scaffold 必建（new_project 第 6 件种子，status=draft；P1 充实后自检升 review；P4 gate PASS 按 `auto_promote.p4_canon_seed` 升 canon）。  
> `[方括号]` 占位。通用工程层，禁止绑定具体作品。

---

## 1. YAML（信封 + 最小字段；唯一真值）

```yaml
---
id: canon_style
type: Canon
rev: 1
status: draft                     # scaffold 建为 draft；P1 自检升 review；P4 gate 后按 auto_promote.p4_canon_seed 升 canon；正文轮以生效版为准
title: "[本书风格卡]"
created_at: "[YYYY-MM-DDTHH:MM:SSZ]"
updated_at: "[YYYY-MM-DDTHH:MM:SSZ]"
depends_on: []                    # 可挂 { type: Blueprint, id: blueprint_main, min_rev: 1 }
stale_reason: null
tags: [canon, style]
uri: null

narration:
  person: third_limited           # first | third_limited | third_omniscient
  tense: past                     # past | present
  distance: "[叙述距离/可靠度一句话，如：贴脸限知，偶尔拉远做章末收束]"

sentence_profile:                 # 句长分布倾向
  length_bias: "[如：短句为主，平均 ≤20 字；打斗段进一步压短至 ≤12 字]"
  paragraph_bias: "[如：2–5 句/段；禁止整屏单段]"
  variety_rule: "[如：连续 3 句禁止同结构开头；连续两段禁止同一收尾句式]"

imagery_domains:                  # 意象域：比喻/通感的取材范围（正面清单）
  - "[如：器物磨损与市井烟火]"
  - "[如：水文、潮汐与淤泥]"
avoid_imagery:
  - "[如：宝石类比眼睛、星辰大海式抒情]"

taboo_list:                       # 禁用词与口癖黑名单（critic 轮逐条扫描）
  # 预置项为常见 LLM 腔示例，项目可增删；命中 = 违规，改写后再过 gate
  - "嘴角勾起一抹（弧度/笑意/冷笑）"
  - "眼底/眼中闪过一丝（……）"
  - "眸中精光一闪"
  - "不由得倒吸一口凉气"
  - "空气仿佛凝固了"
  - "心中暗道 / 心中一凛"
  - "缓缓开口 / 缓缓说道"
  - "深深地看了一眼"
  - "声音很轻，却带着不容置疑的（……）"
  - "一道（倩影/身影）闪过"
  - "整个人如遭雷击"
  - "仿佛要把人吸进去一般"
  - "顿时/瞬间/霎时间——高频副词，单章合计 >3 次即违规"
  - "值得一提的是 / 要知道 / 殊不知——说明文腔转场语"
  - "句式级口癖：每段以感叹号收尾；三连排比抒情；连续段落以人名开头"

punctuation_habits:               # 标点习惯
  - "[如：省略号统一「……」一份六点，禁止连用两份]"
  - "[如：破折号「——」每千字 ≤2 处]"
  - "[如：叙述句禁用感叹号；对话内感叹号每章 ≤5 处]"

sample_passages:                  # 基准段落 2–3 段（150–300 字/段）；首批正文过 gate 后回填定稿真实段落
  - "[示例段落 1 占位：叙事+动作段，体现句长分布与意象域]"
  - "[示例段落 2 占位：对话段，体现口吻与标点习惯]"
  - "[示例段落 3 占位（可选）：情绪/描写段]"
---
```

## 2. 填写与使用纪律

- `taboo_list` 管**叙述层**全局口癖；角色个人声纹（口癖/句长/taboo_words/标志句）写在 `Character.voice`，不在本卡重抄。
- `sample_passages` 初期用占位描述语感；首批正文过 gate 后，从定稿正文回填真实段落作语感锚，此后 critic 轮以其为对照样本。
- 本卡是 Canon 切片：变更须 Decision 留痕并 `rev += 1` + touch `manifest_root`；已发布章不因本卡变更回改（必要时走 `retcon_note`）。
- 文风漂移诊断路径：critic 轮报告 → `diagnose`（K-WRITE-018 + 本卡对照）→ 修正入 repair_in_phase。

## 3. 正文区

frontmatter 为唯一真值；本节以下为自由撰写区（风格备忘 / 语感讨论），不作机器对账输入。

---

## 修订

| rev | 变更 |
|----:|------|
| 1 | 2026-08-12 新建：canon_style 实例模板（叙述人称/时态/句长分布/意象域/禁用词与口癖黑名单（预置 15 条常见 LLM 腔）/标点习惯/示例段落占位）+ write_unit 必召回与 critic 对照用途说明 |
| 2 | 2026-08-13 修复轮：加建档说明——scaffold 必建（new_project 第 6 件种子，draft）→ P1 自检升 review → P4 gate PASS 按 auto_promote.p4_canon_seed 升 canon |

*template_of: Canon(style 切片) | id: canon_style | schema_rev: 对齐 asset-types（schema_rev 3） | 通用工程层 · 不绑定具体作品*
