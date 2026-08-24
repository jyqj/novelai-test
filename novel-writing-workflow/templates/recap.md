# Recap 模板 — 滚动书摘 / 卷摘要 / 现状快照

> **本模板实例化** `runtime/asset-types.md` `type: Recap`。职责：为千章级连载提供低成本「读过前文」替身——write_unit 轮必召回 `recap_book` + `recap_vol_{当前卷-1}` + `recap_state`；其中 `recap_book` / `recap_vol_{当前卷-1}` 为**条件召回项**——尚不存在时跳过（首章/首卷豁免），存在则必装（权威召回表见 `runtime/protocol.md` §4.2）。  
> Recap 是**读模型不是真值源**：与 `Canon` / facts 冲突时以 Canon 为准并修 Recap；禁止把未发生的计划写入（计划属 Thread / SceneBeat）。  
> `[方括号]` 占位。通用工程层，禁止绑定具体作品。

---

## 1. YAML（信封 + 最小字段；唯一真值）

```yaml
---
id: recap_state                   # recap_book | recap_vol_{n} | recap_state
type: Recap
rev: 1
status: canon                     # 常态 canon（随章更新只 rev++）；初建可 draft
title: "[现状快照 / 滚动书摘 / vol_n 卷摘要]"
created_at: "[YYYY-MM-DDTHH:MM:SSZ]"
updated_at: "[YYYY-MM-DDTHH:MM:SSZ]"
depends_on: []
stale_reason: null
tags: [recap]
uri: null

kind: state                       # book | volume | state
covers_chapters: [1, 1]           # 覆盖章区间 [start, end]；随维护更新 end

# ── kind = book | volume：填 body（state 置 null）──
body: null
# book：≤800 字滚动书摘——只留因果主干与现存悬念；超限时压缩最旧段落
# volume：≤1500 字/卷——卷内主线因果 + 伏笔埋收账 + 人物关系变化 + 卷末状态

# ── kind = state：填六要点（合计 ≤600 字；body 置 null）──
state:
  realm: "[主角境界 / 力量位阶一句话]"
  location: "[当前位置 / 所处势力范围]"
  possessions: []                 # 关键持有物 / 资源 / 底牌
  relationships: []               # 关键关系现状；[{ character_id, note }]
  current_goal: "[当前目标一句话]"
  open_crises: []                 # 未解危机 / 悬而未决的威胁
---
```

## 2. 三形态与维护纪律

| kind | 实例 id | 上限 | 维护时机 |
|---|---|---|---|
| `state` | `recap_state`（单例） | 六要点合计 ≤600 字 | **P6 每章写回后更新**（write_unit 写回清单固定项） |
| `book` | `recap_book`（单例） | ≤800 字滚动 | P6 每章写回后滚动追加；超限先压缩最旧段落 |
| `volume` | `recap_vol_{n}`（每卷一份） | ≤1500 字 | 卷末 volume_checkpoint 生成，随卷报告供用户确认；此后只修错不追加 |

- scaffold（new_project / adopt）时创建空壳 `recap_state`；adopt 消化 pass 逐批读旧稿后补齐 `recap_book` / `recap_state`（进度记 `Status.web_serial.adopt_cursor`）。
- 三形态各自独立 rev / Manifest entry，注册于 `manifest_root`；每次更新 `rev += 1` + touch。
- 写作时的时间精度分工：远端历史靠 `recap_book`，上一卷靠 `recap_vol_{n}`，当下状态靠 `recap_state`，逐章细节靠前章 `ManuscriptUnit.summary_after`——四层互补，勿互相复制内容。

## 3. 正文区

frontmatter 为唯一真值；本节以下为自由撰写区（维护备忘），不作机器对账输入。

---

## 修订

| rev | 变更 |
|----:|------|
| 1 | 2026-08-12 新建：Recap 三形态模板（book ≤800 字滚动 / volume ≤1500 字 / state 六要点）+ 维护纪律 |
| 2 | 2026-08-13 修复轮：召回注释补条件召回半句（recap_book / recap_vol_{当前卷-1} 尚不存在时跳过——首章/首卷豁免，存在则必装） |

*template_of: Recap | ids: recap_book \| recap_vol_{n} \| recap_state | schema_rev: 对齐 asset-types（schema_rev 3） | 通用工程层 · 不绑定具体作品*
