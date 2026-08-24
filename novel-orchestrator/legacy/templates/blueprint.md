# Blueprint 模板 — 项目蓝图（P1 构思产出）

> **本模板实例化** `runtime/asset-types.md` §2.5 `type: Blueprint`。  
> 门禁/预算见 `runtime/phase-contracts.md`（P1）；术语见 `runtime/glossary.md`；本文件不重定义 gate / 理论。  
> 方法知识仅引用 `K-xxx` ID（构思方法族 `K-CONCEPT-001~022`），不粘贴理论长文。  
> 填写规则：`[方括号]` 为占位，填后删除括号；扩展字段允许，但不得替代最小字段（asset-types §0.1 P8）。  
> 通用工程层 only：禁止绑定具体已有作品名作规范正文。  
> **route 不在本资产**：发布路线 `route: traditional | web` 记录于 `Status`（asset-types §2.1）；Blueprint 只管故事本体。

---

## 0. 职责与边界

| 项 | 契约 |
|----|------|
| **type id** | `Blueprint` |
| **实例 id** | `blueprint_main`（单主蓝图；变体 `blueprint_{variant}`） |
| **职责** | P1 产出：高概念、前提、类型定位、脊骨意图、主控思想草案、元素/人物/世界种子、剧情向量 |
| **允许 status** | 全枚举；P2 启动门禁要求 ≥ `review`，建议 `canon` |
| **主属阶段** | P1（下游只读；种子在 P2–P4 展开为 PlotSpine / Character / WorldRule） |
| **依赖** | 无硬前置 |

---

## 1. YAML frontmatter（可直接复制）

```yaml
---
# === 通用信封（asset-types §0.2）===
id: blueprint_main
type: Blueprint
rev: 1
status: draft                    # draft | review | canon | locked | stale | archived
title: "[作品暂定名 — 蓝图]"
created_at: "[YYYY-MM-DDTHH:MM:SSZ]"
updated_at: "[YYYY-MM-DDTHH:MM:SSZ]"
depends_on: []                   # P1 无硬前置
stale_reason: null
tags: [blueprint]
uri: null                        # storage adapter 填充；协议层可空

# === Blueprint 最小字段（asset-types §2.5）===
high_concept: "[第三人称陈述句卖点 + 类型信号；不是问句]"
premise: "[「如果……会怎样？」开放问句：真正想探索的问题]"
genre:
  primary: "[主类型]"
  secondary: []                  # 真正影响结构的混合类型，可空
  web_serial_tags: []            # 网文频道标签；发布路线为 web 时建议 ≥1
  must_keep_conventions:
    - "[读者底线期待，3–5 条；违反即货不对板]"
  cliches_to_avoid:
    - "[本作刻意回避/颠覆的套路；最好附替代方向]"
spine_intent:
  protagonist_desire: "[主角最想得到什么]"
  opposing_force: "[谁/什么在阻碍：人、制度、自身缺陷、法则……]"
  core_conflict_one_liner: "[谁]想要[目标]，但[对抗力量]阻碍，因为[原因]"
controlling_idea_draft: "[「某价值 得以实现/被摧毁，因为 某原因」；终态升入 Canon.theme]"
ending_mode_tendency: unset      # idealist | pessimist | positive_irony | negative_irony | unset
element_seeds:                   # 高概念元素清单；tier 四档判据见 §2.2
  - { category: "[身份/关系/事件/冲突/情感/成长]", text: "[元素一句话]", tier: bronze }
cast_seeds:                      # role 闭集：protagonist | antagonist | support
  - { role: protagonist, label: "[身份标签，可未起名]", function: "[对主线的故事功能]" }
  - { role: antagonist,  label: "[……]", function: "[……]" }
  - { role: support,     label: "[……]", function: "[……]" }
world_seeds:
  era: "[时代]"
  duration: "[故事时间跨度]"
  place: "[主要地点 / 地理范围]"
  conflict_scale: personal       # personal | interpersonal | societal | larger
  core_rules_draft:
    - "[世界根本法则草案，≤3 条；P2 后展开为 WorldRule]"
plot_vector:
  opening: "[开局：初始状态 + 触发事件]"
  midpoint_direction: "[中段：冲突升级方向]"
  ending_direction: "[结局大方向，可粗]"

# === 可选：开书包装（方法 K-CONCEPT-022；Status.route=web 时建议必填）===
title_candidates: []             # 书名候选 ≥3：类型词+爽点词+差异词，≤12 字
blurb_draft: null                # 简介三段式草案：人设钩 1 句 / 冲突钩 1-2 句 / 爽点承诺 1 句，全文 ≤200 字
---
```

## 2. 填写指引

### 2.1 每字段一行判据

| 字段 | 判据 |
|------|------|
| `high_concept` | 第三人称**陈述句**卖点 + 类型信号；30 秒能向陌生读者转述出画面；写成问句 = 填错位 |
| `premise` | 「如果…会怎样」**开放问句**；答案不唯一，触及人性/社会层；写成卖点陈述 = 填错位 |
| （两者区分） | 高概念 = 市场端「卖点」，前提 = 创作端「灵魂」；可同源不可同文——一个陈述句、一个问句，句式即校验器 |
| `genre.primary / secondary / web_serial_tags` | primary 单值定读者契约；secondary 只列真正改变结构的混合；tags 用频道语汇（系统流/种田/女强…），`Status.route=web` 时 ≥1 |
| `genre.must_keep_conventions / cliches_to_avoid` | 常规每条自测「违反它读者会弃书吗」，不会弃的不入表；套路只列本作真会碰到的，附替代方向更佳 |
| `spine_intent.core_conflict_one_liner` | 四要素齐：谁 / 要什么 / 被谁挡 / 为何挡；缺一即打回 |
| `controlling_idea_draft` | 「价值 + 原因」单句（K-CONCEPT-013）；draft 后缀 = 可变，锁定动作发生在 Canon.theme |
| `ending_mode_tendency` | P1 只记倾向，允许 `unset`；不作终局承诺 |
| `element_seeds[]` | 每条一句话可独立转述；category 建议六选一；tier 判据见 §2.2 |
| `cast_seeds[]` | role 三选一闭集；label 允许无名（「夜班维保员」即可）；function 写主线功能而非性格形容 |
| `world_seeds.*` | conflict_scale 四选一闭集；core_rules_draft 每条可判真伪、≤3 条，其余留给 WorldRule |
| `plot_vector.*` | 三个方向各一句即止；出现具体场景/对话 = 越阶（那是 P3/P4 的事） |
| `title_candidates` / `blurb_draft`（可选） | 开书包装草案：书名候选 ≥3、简介三段式全文 ≤200 字；组合律与三段式判据见 K-CONCEPT-022；`Status.route=web` 建议必填 |

### 2.2 `element_seeds[].tier` 四档判据（按可支撑章数区间；旧三档「青铜/白银/SSR」写法废弃，一律小写英文四档）

| tier | 判据 |
|------|------|
| `bronze` | 常见但有效；可支撑 ≤10 章的局部情节 |
| `silver` | 较稀缺；可支撑约一个情节单元 |
| `gold` | 稀缺；可支撑约一卷 |
| `ssr` | 极稀缺；长跨度主线引擎，可跨卷持续产出冲突与期待 |

## 3. 示例（三组异质；只列最小字段，信封同 §1）

### 3.A 都市规则怪谈

```yaml
high_concept: "深夜十一点后，全城电梯会多出一层不存在的『负一层半』，夜班维保员靠一本手抄《异层守则》在里面接单救人——都市规则怪谈。"
premise: "如果活下去的唯一方式是遵守一套明显不讲理的规则，人会在哪一条规则上选择不服从？"
genre:
  primary: "都市怪谈 / 悬疑"
  secondary: ["职业文"]
  web_serial_tags: ["规则怪谈", "单元推理"]
  must_keep_conventions:
    - "规则文本前置展示、事后可验证，不得马后炮改规则"
    - "怪异不能被火力硬平，只能被规则解"
    - "每个单元怪谈内部逻辑自洽、可复盘"
  cliches_to_avoid:
    - "开局金手指直接鉴定规则真伪（改为：靠代价试错换认知）"
    - "怪谈起源一律冤魂复仇（改为：制度性交换的遗留物）"
spine_intent:
  protagonist_desire: "查清师傅在异层失踪的真相，把人带回来"
  opposing_force: "维保公司高层——他们靠定期向异层『供人』换全城电梯平稳"
  core_conflict_one_liner: "维保员林晚秋想带回失踪的师傅，但公司高层全力阻拦，因为师傅正是当期『供人』协议的抵押品"
controlling_idea_draft: "平凡人的安全得以保全，因为有人拒绝把安全的代价转嫁给看不见的少数"
ending_mode_tendency: positive_irony
element_seeds:
  - { category: "事件", text: "每晚 23:00 后电梯多出『负一层半』", tier: gold }
  - { category: "冲突", text: "全城平稳运行 vs 每季度『供』一名误入者", tier: ssr }
  - { category: "身份", text: "唯一能带活人往返异层的持证维保员", tier: silver }
cast_seeds:
  - { role: protagonist, label: "夜班电梯维保员", function: "以职业权限进出异层，扛真相主线" }
  - { role: antagonist, label: "维保公司运维总监", function: "旧协议执行人，制度之恶的具象" }
  - { role: support, label: "异层里不肯走的老住户", function: "规则的活注脚与关键信息口" }
world_seeds:
  era: "当代大城市"
  duration: "一年，十二个月度检修节点"
  place: "单城，围绕电梯井、机房与地下管廊"
  conflict_scale: societal
  core_rules_draft:
    - "异层规则以书面文本显形，念出即生效，且对念诵者计费"
    - "在异层撒谎会成真，代价由说谎者最亲近的人承担"
plot_vector:
  opening: "例行夜检时发现师傅失踪当晚的工单签名被人调换"
  midpoint_direction: "查到『供人』协议，同时发现自己是候补名单第一位"
  ending_direction: "以一份可验证的新守则替换旧默契，终结献祭"
```

### 3.B 星际机甲种田

```yaml
high_concept: "退役机甲测试员在废弃农业殖民星上，把报废军用机甲改装成农机开荒，将战场残骸种成全星域最抢手的口粮田——星际种田文。"
premise: "如果战争机器最好的归宿是犁地，一个只被训练来破坏的人要如何学会经营与养育？"
genre:
  primary: "科幻"
  secondary: ["经营种田"]
  web_serial_tags: ["种田流", "机甲", "星际"]
  must_keep_conventions:
    - "产出有账目，丰收节点有阶段性爽点"
    - "机甲改装有零件来源与工时成本"
    - "经营成果不被一场战斗清零"
  cliches_to_avoid:
    - "系统面板白给种子图纸（改为：一切图纸靠拆解报废机甲反推）"
    - "邻星全员恶人轮番抢收成（改为：主要冲突来自条例与市场）"
spine_intent:
  protagonist_desire: "让垄七星连续三季合法产出，换回平民籍"
  opposing_force: "军方清算署——这颗星和他本人都是账面上的『待报废资产』"
  core_conflict_one_liner: "退役测试员温犁想把废星种成粮仓换回平民籍，但清算署要按期回收整星，因为它的账面残值等于一支舰队的报废金"
controlling_idea_draft: "被判报废的人与土地重获价值，因为耕作把破坏的技能翻译成了养育的技能"
ending_mode_tendency: idealist
element_seeds:
  - { category: "事件", text: "军用机甲首次下地犁田的直播意外爆红", tier: bronze }
  - { category: "身份", text: "全星域唯一持证的『机甲农夫』", tier: silver }
  - { category: "冲突", text: "报废条例 vs 土地上长出的新生计", tier: gold }
  - { category: "成长", text: "从『武器的手』到『种地的手』的身份重写", tier: ssr }
cast_seeds:
  - { role: protagonist, label: "退役机甲测试员", function: "以驾驶与改装技能开荒，扛经营与合法性主线" }
  - { role: antagonist, label: "清算署稽核官", function: "条例的人格化，按程序步步紧逼" }
  - { role: support, label: "留守星球的老农艺师", function: "农学知识口与本地人脉" }
world_seeds:
  era: "星际殖民时代，战后第七年"
  duration: "三个种植季"
  place: "边缘农业殖民星『垄七星』"
  conflict_scale: societal
  core_rules_draft:
    - "机甲动力核心衰变后只能降级民用，过程不可逆"
    - "星域法：连续三季有合法产出的土地不得强制回收"
plot_vector:
  opening: "回收舰抵达倒计时九十天，抢种第一季耐辐射麦"
  midpoint_direction: "增产真因指向地下战争遗骸，产地认证陷入合法性危机"
  ending_direction: "以『战场转农田』公证案例推动报废条例修订"
```

### 3.C 古代女商贾权谋

```yaml
high_concept: "盐引案抄家后，罪臣之女从一间漕运脚店起家，用商路账本撬动六部党争，成为王朝第一个持官凭的女盐商——古代商战权谋。"
premise: "如果权力只认账本不认人心，一个被权力碾碎过的人重建的秩序，会不会变成新的碾子？"
genre:
  primary: "古代权谋"
  secondary: ["商战"]
  web_serial_tags: ["女强", "经商", "朝堂"]
  must_keep_conventions:
    - "商战胜负落在货、银、信用的可核算变化上"
    - "对手智商在线，每局有可复盘的胜负手"
    - "女主权力来自经营积累，不靠单点恩宠"
  cliches_to_avoid:
    - "贵人一见倾心保驾护航（改为：每个盟友都要她付得起对价）"
    - "反派靠下毒绑架推剧情（改为：用规则与账目互杀）"
spine_intent:
  protagonist_desire: "拿到官盐引，让沈家脱罪籍"
  opposing_force: "主导当年盐引案的户部侍郎一系——翻案等于翻他们的账"
  core_conflict_one_liner: "沈观潮想凭盐引翻案脱罪籍，但户部侍郎一系全力阻杀，因为她每进一步都在掀当年构陷案的账底"
controlling_idea_draft: "公道得以重建，因为她让账目比出身更有权威——代价是她自己再不能有一笔糊涂账"
ending_mode_tendency: positive_irony
element_seeds:
  - { category: "身份", text: "罪籍女子持官凭经商", tier: gold }
  - { category: "关系", text: "与告发过她父亲的老账房结成互相校账的同盟", tier: silver }
  - { category: "冲突", text: "翻案救家 vs 翻案会掀翻庇护过她的人", tier: ssr }
cast_seeds:
  - { role: protagonist, label: "罪臣之女 / 脚店掌柜", function: "以账目与商路为武器，扛翻案主线" }
  - { role: antagonist, label: "户部侍郎", function: "旧案受益人，用制度绞杀翻案" }
  - { role: support, label: "告发过沈家的老账房", function: "技艺导师兼罪证信息口，互质同盟" }
world_seeds:
  era: "架空王朝，盐铁官营中期"
  duration: "六年，跨三届盐引大考"
  place: "漕运枢纽泗州至京城的两条商路"
  conflict_scale: societal
  core_rules_draft:
    - "盐引即朝廷信用凭证，伪造形同谋逆"
    - "罪籍不得持引、商籍不得科举——除非特旨"
plot_vector:
  opening: "抄家第三年，沈观潮借脚店过所文书发现当年案卷被调包"
  midpoint_direction: "党争两边都想收编这位『活账房』，她被迫在两本假账之间做局"
  ending_direction: "当庭对账翻案，同时给自己套上『账目永远公开』的枷锁"
```

## 修订

| rev | 日期 | 变更 |
|-----|------|------|
| 3 | 2026-08-13 | 修复轮：新增可选开书包装字段 title_candidates[]/blurb_draft（方法 K-CONCEPT-022；route=web 建议必填）+ §2.1 判据行；构思方法族引用范围更新为 K-CONCEPT-001~022；页脚 schema_rev 对齐字样统一（schema_rev 3） |
| 2 | 2026-08-12 | 重写为新代格式：通用信封 + asset-types §2.5 最小字段 + 一行判据指引 + 三组异质示例；高概念/前提判据钉死（陈述句 vs 问句）；tier 统一四档（判据=可支撑章数）；注明 route 属 Status |
| 1 | — | 初版散文表格模板（无信封 / 协议字段） |

*template_for: Blueprint | id: blueprint_main | schema_rev: 对齐 asset-types（schema_rev 3） | 通用工程层 · 不绑定具体作品*
