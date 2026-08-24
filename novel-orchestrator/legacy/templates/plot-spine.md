# PlotSpine 模板 — P2 粗纲脊骨

> **本模板实例化** `runtime/asset-types.md` §2.6 `PlotSpine`；门禁与知识预算以 `runtime/phase-contracts.md` §3（P2）为准。  
> `[方括号]` 占位。通用工程层，禁止绑定具体作品；知识仅引用 `K-xxx`（如 `K-CONCEPT-009~012`、`K-STRUCT-001~002`）。

---

## 0. 硬边界（P2）

| 允许 | 禁止 |
|---|---|
| 节点 `0..23`：`title` + `value_one_liner`（可选 `function` / `anchor`） | `scenes[]` / `beats[]` / `chapters[]` / `dialogue` / 场景散文 |
| `cable` / `fuses` / `conflict_matrix` / `volume_map` / `anti_goals` | 章号 / 字数 / 「场景1」枚举 |

**硬约束**：`nodes.length == 24` 且 `id` 覆盖 `0..23`；必保锚点 `0, 6, 8, 12, 16, 18, 19, 22, 23` 已填 `anchor`。

## 1. YAML（信封 + 最小字段；唯一真值）

```yaml
---
id: plotspine_main
type: PlotSpine
rev: 1
status: draft                    # draft|review|canon|locked|stale|archived；P3 门禁要求 ≥ review
title: "[人读标签，如：主脊骨 v1]"
created_at: "[YYYY-MM-DDTHH:MM:SSZ]"
updated_at: "[YYYY-MM-DDTHH:MM:SSZ]"
depends_on:
  - { type: Blueprint, id: blueprint_main, min_rev: 1 }
  # - { type: Canon, id: canon_root, min_rev: 1 }
stale_reason: null
tags: [p2, plot_spine]
uri: null
route: traditional               # traditional | web
controlling_idea_draft: "[价值 + 原因；可升格至 Canon.theme]"
anti_goals:
  - "[明确不做的情节走向 1]"
  - "[明确不做的情节走向 2]"

nodes:                           # 恰 24 条，id 覆盖 0..23；每条只 title + 一句话可辨价值方向
  - { id: 0,  title: "[Hook]",             value_one_liner: "[价值起→终；web 强调钩子/信息增量]", function: setup,      anchor: hook }
  - { id: 1,  title: "[节点标题]",          value_one_liner: "[一句话价值方向]",                  function: null,       anchor: null }
  - { id: 2,  title: "[节点标题]",          value_one_liner: "[一句话价值方向]",                  function: null,       anchor: null }
  - { id: 3,  title: "[节点标题]",          value_one_liner: "[一句话价值方向]",                  function: null,       anchor: null }
  - { id: 4,  title: "[节点标题]",          value_one_liner: "[一句话价值方向]",                  function: null,       anchor: null }
  - { id: 5,  title: "[节点标题]",          value_one_liner: "[一句话价值方向]",                  function: null,       anchor: null }
  - { id: 6,  title: "[惊人意外 #1]",       value_one_liner: "[不可逆变局的价值翻转]",            function: turn,       anchor: shock1 }
  - { id: 7,  title: "[节点标题]",          value_one_liner: "[一句话价值方向]",                  function: null,       anchor: null }
  - { id: 8,  title: "[成长 #1]",           value_one_liner: "[弧光压力 / 认知位移]",             function: escalation, anchor: growth1 }
  - { id: 9,  title: "[节点标题]",          value_one_liner: "[一句话价值方向]",                  function: null,       anchor: null }
  - { id: 10, title: "[节点标题]",          value_one_liner: "[一句话价值方向]",                  function: null,       anchor: null }
  - { id: 11, title: "[节点标题]",          value_one_liner: "[一句话价值方向]",                  function: null,       anchor: null }
  - { id: 12, title: "[中间点 / 成长 #2]",  value_one_liner: "[方向性转变的价值句]",              function: turn,       anchor: [midpoint, growth2] }
  - { id: 13, title: "[节点标题]",          value_one_liner: "[一句话价值方向]",                  function: null,       anchor: null }
  - { id: 14, title: "[节点标题]",          value_one_liner: "[一句话价值方向]",                  function: null,       anchor: null }
  - { id: 15, title: "[节点标题]",          value_one_liner: "[一句话价值方向]",                  function: null,       anchor: null }
  - { id: 16, title: "[成长 #3]",           value_one_liner: "[弧光加压]",                        function: escalation, anchor: growth3 }
  - { id: 17, title: "[节点标题]",          value_one_liner: "[一句话价值方向]",                  function: null,       anchor: null }
  - { id: 18, title: "[惊人意外 #2]",       value_one_liner: "[第二幕高潮的不可逆翻转]",          function: turn,       anchor: shock2 }
  - { id: 19, title: "[成长 #4]",           value_one_liner: "[终局前弧光落点]",                  function: escalation, anchor: growth4 }
  - { id: 20, title: "[节点标题]",          value_one_liner: "[一句话价值方向]",                  function: null,       anchor: null }
  - { id: 21, title: "[节点标题]",          value_one_liner: "[一句话价值方向]",                  function: null,       anchor: null }
  - { id: 22, title: "[高潮]",              value_one_liner: "[终局动作导致价值不可逆]",          function: climax,     anchor: climax }
  - { id: 23, title: "[收束]",              value_one_liner: "[余波 / 新常态]",                   function: resolution, anchor: resolution }

cable:                           # 电缆：主线 + 向心搅合支线（K-CONCEPT-009/010）；亦可拆 Thread 实例
  mainline: "[主线因果/欲望对抗一句话；非空或存在主线 Thread]"
  strands:
    - { id: strand_[slug], name: "[支线名]", sync_with_main: "[如何向心搅合主线]", budget_ratio: 0.0 }
    # 支线合计篇幅意图建议 ≤ 0.30

fuses:                           # 引线（K-CONCEPT-011）；可拆 Thread.kind=fuse
  - id: fuse_[slug]
    hidden_info: "[对读者或角色隐藏的真相一句话]"
    plant_points: ["node:2", "node:6", "node:12"]   # 节点级锚点 ≥3
    reveal_point: "node:[n]"     # 通常逼近 climax 前

conflict_matrix:                 # 冲突三层面，只分配到幕/关键节点（K-CONFLICT-001~003）
  inner: "[内心冲突如何沿锚点加压]"
  inter: "[人际冲突轴线与节点挂钩]"
  extra: "[外部/制度/世界压力轴线]"

volume_map:                      # 分卷（route=web 至少规划首卷）；模式语义见 §2.2
  - volume_id: vol_01
    theme: "[本卷主题/价值域一句话]"
    node_range: [0, 11]          # 须落在 0..23
    element_ids: []
---
```

## 2. 填写指引

### 2.1 锚点词表（`anchor` 枚举）

| anchor | 节点 | 功能标注 |
|---|---|---|
| `hook` | 0 | 开篇钩子 |
| `shock1` | 6 | 惊人意外 #1（第一幕高潮，不可逆） |
| `growth1` | 8 | 成长步骤 #1 |
| `midpoint` | 12 | 中间点（方向性转变） |
| `growth2` | 12 | 成长步骤 #2（与 midpoint 同位：写数组 `anchor: [midpoint, growth2]`） |
| `growth3` | 16 | 成长步骤 #3 |
| `shock2` | 18 | 惊人意外 #2（第二幕高潮） |
| `growth4` | 19 | 成长步骤 #4 |
| `climax` | 22 | 高潮（21–22 为「白热化带」——描述性用语，锚点只落 22） |
| `resolution` | 23 | 收束 / 余波 |

`anchor` 允许数组并列标注；非锚点填 `null`。`function` 建议词库：`setup / build / escalation / turn / payoff / climax / resolution`。
稳定人设型（steadfast）替代语义速查见 `K-STRUCT-022` 卷级降档表；重生/告别自我语义仅卷一有效。

### 2.2 volume_map 双模式

- **模式 A（单书一圈，默认）**：全书一条 0–23 脊骨，`volume_map` 用 `node_range` 把节点切给各卷；单卷作品视为 `vol_01` 全跨。
- **模式 B（卷级嵌套，route=web 长连载建议）**：本书级脊骨保留为**规划资产**（nodes 24 硬约束不变，远端节点可占位到卷级主题一句话）；每卷另建 `seqmap_v{n}` 走卷内 0–23。锚点 gate 只强制**卷内**序列图锚点，**书级锚点为 soft（缺失仅 warning，不 BLOCK）**。方法参考 `K-STRUCT-022`。
- 模式选择与中途切换须 `Decision(approved_by=user)`。

### 2.3 其余纪律

- `value_one_liner` 价值方向可辨（正/负/翻转）；引线 `plant_points ≥ 3` + `reveal_point`；支线须有 planned payoff 节点。
- 写回：`rev += 1` + touch `manifest_root`；旁路产出 `Thread[]` / `Character`(draft) / `WorldRule`(draft) 在各自资产登记；上游 Blueprint rev 提升 → 本资产可标 `stale`。
- 禁止写回字段：`scenes[]`、`beats[]`、`chapters[]`、`dialogue`。

## 3. 正文区

frontmatter 为唯一真值；本节以下为自由撰写区（工作备忘 / 待决问题），不作机器对账输入。

---

## 修订

| rev | 变更 |
|----:|------|
| 1 | 初版（24 行镜像表 + 部分 YAML 双写；节点 12 锚点「二选一勿拆两行」） |
| 2 | 2026-08-12 重构落地：anchor 允许数组（节点 12 `[midpoint, growth2]`，删「二选一勿拆两行」）；锚点词表收编 growth2、climax=22（白热化带为描述性用语）；volume_map 补模式 A/B 说明（模式 B 书级锚点 soft）；nodes 24 硬约束保留；nodes 收进 frontmatter 单份（删镜像节点表与重复 YAML 骨架） |
| 3 | 2026-08-13 修复轮：§2.1 anchor 注释补 steadfast 替代语义速查一行（K-STRUCT-022 卷级降档表；重生/告别自我语义仅卷一有效）；页脚 schema_rev 对齐字样统一（schema_rev 3） |

*template_of: PlotSpine | phase_home: P2 | schema_rev: 对齐 asset-types（schema_rev 3） | 通用工程层 · 不绑定具体作品*
