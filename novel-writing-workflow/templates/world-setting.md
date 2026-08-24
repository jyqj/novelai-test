# WorldRule 模板 — 世界规则包（world_{domain}）

> **本模板实例化** `runtime/asset-types.md` §2.11 `type: WorldRule`（文件名沿用 world-setting.md）。  
> 术语见 `runtime/glossary.md`；`hardness=hard` 条目是 `Canon.invariants` 候选（提升路径见 templates/canon.md §3.1）。  
> 方法知识仅引用 K-xxx（硬度三法则 `K-WORLD-005`、升级模式 `K-WORLD-014`、战力锚定 `K-WORLD-022`），不粘贴理论长文。  
> 填写规则：`[方括号]` 为占位，填后删除括号；扩展字段（历史编年/术语表等）允许，但不得替代最小字段（asset-types §0.1 P8）。  
> 通用工程层 only：禁止绑定具体已有作品。  
> **反圣经纪律**：世界观按「最小可行」分级供给（§2.2），不是自我满足的百科全书——每条设定都要答得出「它压迫谁、值多少章」。

---

## 0. 职责与边界

| 项 | 契约 |
|----|------|
| **type id** | `WorldRule` |
| **实例 id** | `world_{domain}`：`world_core` \| `world_power` \| `world_faction` \| `world_{slug}` |
| **职责** | 世界不变量与代价、力量体系、势力压力、三层同心圆、世界内禁忌 |
| **允许 status** | 全枚举；影响情节的硬规则应升 `canon` / `locked` |
| **主属阶段** | P1–P2 建立，全程引用；社会/自然层按卷懒加载（§2.2） |
| **依赖** | `Blueprint.world_seeds`；硬条可提升入 `Canon.invariants` |

---

## 1. YAML frontmatter（可直接复制）

```yaml
---
# === 通用信封（asset-types §0.2）===
id: world_[domain]               # world_core | world_power | world_faction | world_[slug]
type: WorldRule
rev: 1
status: draft                    # draft | review | canon | locked | stale | archived
title: "[世界名 · 域 — 规则包]"
created_at: "[YYYY-MM-DDTHH:MM:SSZ]"
updated_at: "[YYYY-MM-DDTHH:MM:SSZ]"
depends_on:
  - { type: Blueprint, id: blueprint_main, min_rev: 1 }
  # 非 core 域实例建议加：{ type: WorldRule, id: world_core, min_rev: 1 }
stale_reason: null
tags: [world]
uri: null

# === WorldRule 最小字段（asset-types §2.11）===
domain: core                     # core | culture | power | faction | geography | other
rules:                           # 法则条目；hard 条目是 Canon.invariants 候选
  - id: wr_[slug]
    statement: "[一句可判真伪的规则陈述]"
    hardness: hard               # hard | soft
    cost: "[遵守/使用/破例的代价；无则 null]"
power_system:                    # 无力量体系时：summary=null、sanderson_level=na
  summary: "[一段话：力量来源 / 获取方式 / 使用条件 / 代价]"
  sanderson_level: na            # 「硬度三法则等级」：1 | 2 | 3 | na（K-WORLD-005）
  upgrade_modes: []              # 擢升/遴选/升华/极致/顿悟/返照 多选（K-WORLD-014）；可空
factions:
  - { id: "fac_[slug]", name: "[势力名]", goal: "[核心诉求]", pressure_on_protagonist: "[对主角的具体压力]" }
concentric:                      # 三层同心圆：内层决定外层
  core: "[法则层：区别于其他世界的根本机制]"
  middle: "[文化/历史层：法则塑造出的社会形态]"
  outer: "[日常表象层：街面上可见可闻的生活质感]"
taboos:
  - "[世界之内不可轻易打破之事；打破 = 重大剧情事件]"
---
```

---

## 2. 填写指引

### 2.1 每字段一行判据

| 字段 | 判据 |
|------|------|
| `domain` | 六选一，一包一域；`core` 必建；其余域**本卷剧情用到才建实例** |
| `rules[].statement` | 单句、可判真伪；散文设定必须压成规则条目才能入库 |
| `rules[].hardness` | `hard` = 情节不得违反（Canon.invariants 候选）；`soft` = 默认成立、可付代价破例 |
| `rules[].cost` | 没有代价的规则撑不起冲突；hard 条目尽量非 null |
| `power_system.summary` | 一段话讲清 来源/获取/使用条件/代价；无体系填 `null` |
| `power_system.sanderson_level` | **硬度三法则等级**（K-WORLD-005）：1 = 读者可预判解题；2 = 限制比能力更有趣；3 = 深挖旧设定优于叠新能力；填体系已达到的最高级；无体系 `na` |
| `power_system.upgrade_modes` | 从 擢升/遴选/升华/极致/顿悟/返照 中多选（K-WORLD-014）；可空 |
| `factions[].pressure_on_protagonist` | 必须写「对主角的具体压力」；写不出 = 该势力本卷不入表 |
| `concentric.*` | core 法则层 / middle 文化历史层 / outer 日常表象层；判据：内层一变，外层必须跟着变 |
| `taboos[]` | **世界之内**的禁忌（打破 = 重大剧情事件）；创作层禁区写 `Canon.forbidden`，勿混 |

### 2.2 最小可行世界观：分级供给纪律

| 层 | 供给纪律 |
|----|----------|
| 核心规则层（`rules` + `concentric.core`） | **必填**：P1 草案、P2 定稿；无它不得开写 |
| 社会层（`factions` / `concentric.middle` / culture 域实例） | **按卷懒加载**：本卷剧情触达才建条目、才细化 |
| 自然层（geography 域 / 生态气候地理） | **用到才写**：没有情节引用的自然设定不建条目 |

章级剂量（写作侧红线，P5/P6 引用）：**单章新专有名词 ≤3；开篇三章禁止集中设定段**——设定以事件与代价的形式露出。

### 2.3 战力锚定表 `power_anchors`（`domain=power` 必填小节；K-WORLD-022）

对应 frontmatter 可选扩展字段 `power_anchors[]`（asset-types §2.11）。各区间必须是**可比对的动作**（如「单人可破一队甲兵」），禁止形容词堆叠；卷级增幅预算与越阶战斗配额见 K-WORLD-022 / K-WORLD-023，不得在表外私加境界。

| 境界/位阶 | 稳胜区间 | 五五开区间 | 必败区间 | 标尺人物 | 代价/瓶颈 |
|-----------|----------|------------|----------|----------|-----------|
| [第 1 阶名] | [可稳定碾压的对象] | [胜负难料的对象] | [不可力敌的对象] | [该阶代表人物] | [获得/维持/越阶的代价] |

---

## 3. 示例（两组异质）

### 3.A `world_core` · 近未来都市低幻「渡口城」（无力量体系分支）

```yaml
id: world_core                   # 信封其余字段略，同 §1
domain: core
rules:
  - id: wr_pawn_forget
    statement: "记忆可整段典当换取流通『当票』；典当后本人对该段记忆彻底遗忘"
    hardness: hard
    cost: "遗忘不可逆；赎回只得『旁观者视角』的复制品，情感温度归零"
  - id: wr_pawn_expire
    statement: "当票三十年到期；无人赎回的记忆归当铺入库，成为可查询的公共档案"
    hardness: hard
    cost: "私事终将公开——全城共有的缓慢恐惧"
  - id: wr_need_consent
    statement: "典当须本人『舍意』；胁迫或药物伪造舍意，记忆到手即腐坏"
    hardness: soft
    cost: "破例代价：腐坏记忆会污染经手人的相邻记忆"
power_system:
  summary: null                  # 规则怪谈式硬设定，不走升级线
  sanderson_level: na
  upgrade_modes: []
factions:
  - { id: fac_guild, name: "典当行会", goal: "垄断收忆定价与入库解释权", pressure_on_protagonist: "捏着主角一张即将到期的高额当票" }
  - { id: fac_ragpick, name: "拾忆人（地下赎忆网络）", goal: "劫库放忆，废除入库制", pressure_on_protagonist: "拉他做内应，暴露即身败名裂" }
concentric:
  core: "记忆是可典当的硬通货，遗忘是结算方式"
  middle: "阶层按『当没当过』划分：全忆者是新贵，穷人靠当记忆过冬；婚俗以『互存一段记忆』为最重的聘礼"
  outer: "当铺霓虹用暖光标收忆价目；酒馆流行猜『你当掉了什么』的搭讪游戏"
taboos:
  - "追问他人当掉了什么，等同于当街扒衣"
  - "把赎来的他人记忆据为己有（行话『穿忆』），是行会死罪"
```

### 3.B `world_power` · 玄幻海岛「云海列岛」骨哨风修（含战力锚定表）

```yaml
id: world_power                  # 信封其余字段略；depends_on 含 world_core
domain: power
rules:
  - id: wr_wind_debt
    statement: "御风即借风，借风必还息；超载未还者身体自指尖起逐节『风化』为石"
    hardness: hard
    cost: "风化不可逆；息债可由宗门共担，但不可豁免"
  - id: wr_whistle_bond
    statement: "骨哨须以持有者一段亲历之声炼成并认主；哨毁，则该段听觉记忆同毁"
    hardness: hard
    cost: "炼哨即永久抵押一段声音记忆"
  - id: wr_eye_silence
    statement: "台风眼内诸哨失效（传承说法，未证伪）"
    hardness: soft
    cost: "破例须重大剧情事件支撑，并回写本条"
power_system:
  summary: "以先人指骨炼哨，吹奏借取风息：御物、飞行、聚风为刃；借多少还多少，还不上以身体风化抵债"
  sanderson_level: 2             # 限制（息债/风化）比能力本身更有戏
  upgrade_modes: ["遴选", "升华", "返照"]
factions:
  - { id: fac_shaomen, name: "哨门（列岛官学）", goal: "垄断炼哨与『风籍』发放", pressure_on_protagonist: "主角是黑籍散修，见哨可收" }
  - { id: fac_fengshi, name: "风市（走私行会）", goal: "贩私哨、开禁风航路", pressure_on_protagonist: "主角欠它的息债利滚利" }
concentric:
  core: "风息是可借贷的力，代价是肉身风化"
  middle: "以『风籍』定身份；欠息破产者沦为『石民』，祠堂墙上镶着还清息债的石化手指作凭证"
  outer: "港口以哨音互致问候，屋脊一律背风开门，孩童游戏是猜风向压瓦片"
taboos:
  - "未经亡者生前允诺，取其骨炼哨"
  - "他人飞行途中夺其风息（『抢风』），视同谋杀"
```

**示例 3.B 附：战力锚定表（domain=power 必填）**

| 境界 | 战力参照（能稳定做到什么） | 代价/瓶颈 |
|------|----------------------------|-----------|
| 闻风 | 顺风跃屋自稳；御物不超随身行囊 | 息债日结；超载即指尖发麻示警 |
| 驭息 | 无风起飞，贴海独飞半日；风刃可破木盾 | 单次超载 = 一节指骨风化 |
| 裂云 | 携一人穿云层；风刃破铁甲；可在飓风边缘作业 | 息债须宗门共担；寿数按风化度折算 |
| 唤潮 | 引一场局地风暴，可改一港风向 | 一次唤潮 = 一肢风化；列岛法令限一年一用 |

---

## 修订

| rev | 日期 | 变更 |
|-----|------|------|
| 3 | 2026-08-13 | 修复轮：核对 locked 发布语义与 facts 字段名引用，本文件无涉及项；页脚 schema_rev 对齐字样统一（schema_rev 3） |
| 2 | 2026-08-12 | 重写为新代格式：通用信封 + asset-types §2.11 最小字段 + 一行判据指引 + 最小可行世界观分级纪律与章级剂量红线 + 战力锚定表小节（domain=power，引 K-WORLD-022）+ 两组异质示例；sanderson_level 采用中性名「硬度三法则等级」 |
| 1 | — | 初版「世界观圣经」散文模板（14 节百科式，无信封 / 协议字段） |

*template_for: WorldRule | id: world_{domain} | schema_rev: 对齐 asset-types（schema_rev 3） | 通用工程层 · 不绑定具体作品*
