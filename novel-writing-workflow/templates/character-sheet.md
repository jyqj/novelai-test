# Character 模板 — 人物卡（char_{slug}）

> **本模板实例化** `runtime/asset-types.md` §2.10 `type: Character`。  
> 洋葱五键为固定英文 id：`surface / behavior / emotion / belief / wound`（SSOT 见 `runtime/glossary.md`）；禁止中文键名，禁止把 `wound` 改写为 `trauma`。  
> 方法知识仅引用 K-xxx（洋葱 `K-CHAR-004`、声纹 `K-CHAR-013`、人物方法族 `K-CHAR-001~014`），不粘贴理论长文。  
> 填写规则：`[方括号]` 为占位，填后删除括号；扩展字段（外貌/感官标签等）允许，但不得替代最小字段（asset-types §0.1 P8）。  
> 通用工程层 only：禁止绑定具体已有作品。  
> 精简纪律：主角/核心反派全字段；重要配角 `masks` / `key_choices` 可各留 1 条；功能性角色填到 `voice` 即止。

---

## 0. 职责与边界

| 项 | 契约 |
|----|------|
| **type id** | `Character` |
| **实例 id** | `char_{slug}` |
| **职责** | 人物真值卡：欲望/需要、洋葱五层、弧光与按卷里程碑、关系功能、声纹、情境面具、关键选择、信息差 |
| **允许 status** | 全枚举；进细纲/正文的核心卡建议 ≥ `canon` |
| **主属阶段** | P2 种子 → P4 充实 → 全程维护（连载中 `arc.milestones` 按卷滚动追加） |
| **依赖** | `Blueprint.cast_seeds`；主题强相关时引用 `Canon.theme` |

---

## 1. YAML frontmatter（可直接复制）

```yaml
---
# === 通用信封（asset-types §0.2）===
id: char_[slug]
type: Character
rev: 1
status: draft                    # draft | review | canon | locked | stale | archived
title: "[角色名 — 人物卡]"
created_at: "[YYYY-MM-DDTHH:MM:SSZ]"
updated_at: "[YYYY-MM-DDTHH:MM:SSZ]"
depends_on:
  - { type: Blueprint, id: blueprint_main, min_rev: 1 }
  # 主题强相关可加：{ type: Canon, id: canon_root, min_rev: 1 }
stale_reason: null
tags: [character]
uri: null

# === Character 最小字段（asset-types §2.10）===
name: "[姓名 / 称号]"
role: protagonist                # protagonist | antagonist | secondary | tertiary | ensemble
desire: "[TA 自觉追求、说得出口的目标]"
need: "[TA 真正需要、未必自知的东西；可 null]"
onion:                           # 洋葱五层：固定英文键；自外向内，下层生成上层
  surface: "[表象：初见的陌生人看到什么]"
  behavior: "[行为：压力下的第一反应模式]"
  emotion: "[情感：核心情感需求 + 最深恐惧]"
  belief: "[信念：可被剧情证伪的价值排序]"
  wound: "[核心驱动层：创伤/欲望/信念/气质 四选一 + 它如何生成上面四层]"
arc:
  start_state: "[起点：性格核心 / 主要缺陷]"
  pressure_design: "[压力类型序列：什么样的事会逼 TA 变化；不写具体剧情]"
  forced_choice: "[不可两全的核心取舍，「A 还是 B」句式；可 null]"
  end_state: "[终点状态；连载可 null，滚动确定]"
  arc_type: unset                # change | steadfast | flat | unset
  milestones:                    # 按卷弧光里程碑；不与固定序列号绑定
    - { volume_id: vol_01, milestone: "[本卷末 TA 应到达的认知/立场/位阶]" }
relationships:
  - { target_id: "char_[slug]", relation: "[关系]", dramatic_function: "[对戏功能：镜像/压力源/信息口/秤砣…]" }
voice:                           # 声纹卡（K-CHAR-013）；旧字段 voice_notes 已废弃
  tics: ["[口癖1]", "[口癖2]"]   # ≤3 个
  sentence_style: "[句长与句式倾向，一句话锁死]"
  taboo_words: ["[该角色词汇表里不存在的词]"]
  sample_line: "[一句最能定调的台词]"
masks:                           # 情境面具：不同情境呈现的不同面向
  - { context: "[情境：对上级/对亲近者/独处…]", mask: "[该情境下呈现的面向]" }
key_choices:                     # 揭示性格真相的关键选择；主角建议 ≥3
  - situation: "[两难情境]"
    choice: "[TA 的选择]"
    reveals: belief              # surface | behavior | emotion | belief | wound
    pressure: high               # low | mid | high | extreme（对照 §2.3）
secrets:
  - "[对读者或其他角色的信息差；正文只可写潜台词/征兆，防剧透纪律见 protocol]"
---
```

---

## 2. 填写指引

### 2.1 每字段一行判据

| 字段 | 判据 |
|------|------|
| `role` | 五选一闭集；`ensemble` = 群像位 |
| `desire` / `need` | desire 具体、可受挫；need 是 TA 的盲区；两者落差 = 弧光燃料；坚守/扁平弧 need 可 null |
| `onion.*` | 逐层过 §2.2 判定问句；自检：抽掉 `wound` 层，上面四层应当塌 |
| `arc.start_state / end_state` | 两端可对照：认知/立场/位阶至少一项有位移；steadfast 弧写「被严酷验证的核心」 |
| `arc.pressure_design` | 写压力**类型**（资源稀缺/忠诚测试/身份暴露…）；出现具体剧情 = 越阶 |
| `arc.milestones[]` | 每卷一条；判据 = 卷末可验收的状态，不是「有所成长」这类空话 |
| `relationships[].dramatic_function` | 写功能不写感情形容词；自测：删掉此人，主角哪条压力/信息链会断？ |
| `masks[]` | ≥2 副面具才立体；`surface` 是默认脸，mask 是情境脸，不同层勿混 |
| `key_choices[]` | 两难 + 选择 + 揭示层 + 压力档齐备；揭示层随压力升级，走 §2.3 |
| `secrets[]` | 每条注明信息差对象（对读者 / 对角色）；写作召回时触发防剧透标注 |

### 2.2 洋葱五层：判定问句 + 反例（K-CHAR-004）

| 键 | 层 | 判定问句 | 反例 |
|----|----|----------|------|
| `surface` | 表象 | 初见的陌生人会怎么形容 TA？ | 「内心其实很孤独」——陌生人看不见内心，不属此层 |
| `behavior` | 行为 | 压力来了，TA 的第一反应动作是什么？ | 「勇敢正直」是评价不是动作；行为要能拍出来（先数钱 / 先冷笑 / 先找出口） |
| `emotion` | 情感 | 失去什么会让 TA 崩溃？ | 把当日情绪当核心需求——此层是长期饥渴，不是今天心情差 |
| `belief` | 信念 | 价值冲突时 TA 保哪个、牺牲哪个？ | 「相信正义」空泛口号——要写成可证伪的排序（如 秩序 > 亲情） |
| `wound` | 核心驱动层 | 上面四层由哪个源头生成？拿掉它是否全塌？ | 给每个角色硬安童年惨案——核心驱动**创伤/欲望/信念/气质四选一**，不强制创伤 |

### 2.3 压力等级 → 揭示层 对照（`key_choices[].pressure` 用同一枚举）

| pressure | 典型情境 | 通常揭示 |
|----------|----------|----------|
| `low` | 日常社交，无实际损失 | `surface` |
| `mid` | 利益 / 脸面受损 | `behavior` → `emotion` |
| `high` | 重要之物受威胁，必须取舍 | `belief` |
| `extreme` | 生死 / 身份根基被击穿 | `wound` |

### 2.4 voice 声纹卡（K-CHAR-013；防对话同质化）

- `tics` 口癖 **≤3 个**：多了写不稳、读者也记不住；
- `sentence_style`：一句话锁死句长与句式倾向（短促祈使 / 长句绕弯 / 惯用反问…）；
- `taboo_words`：受教育、时代、性格约束**说不出口**的词——比口癖更防同质化；
- `sample_line` 合格判据：遮住名字，读者仍能认出是谁说的。
- 方法：`K-CHAR-013`；讨喜度/代入感自检：`K-CHAR-014`。

---

## 3. 示例（两组异质；示例 A 为非创伤驱动型）

### 3.A 齐半夏 — 主角 · 核心驱动 = 气质（非创伤）

```yaml
id: char_qi_banxia               # 信封其余字段略，同 §1
name: "齐半夏"
role: protagonist
desire: "把县动物救助站做成自负盈亏、有正式编制的站点"
need: "接受『救不活的就是救不活』，把力气花在救得活的身上"
onion:
  surface: "笑呵呵好说话的『小齐大夫』，半夜来电话也接"
  behavior: "遇事先上手后讲理；人情账极抠，药品账从不抠"
  emotion: "需要『被托付』的感觉；最怕自己是多余的人"
  belief: "『活物比脸面金贵』——生命 > 信用 > 钱 > 体面"
  wound: "气质型（非创伤）：天生照看者气质，对幼弱之物有近乎生理性的责任反射；是出厂设置而非事件后果——它生成了有求必应的表象、先干后说的行为、被托付的渴望、生命至上的信念"
arc:
  start_state: "来者不拒，累到快垮，站里账目一塌糊涂"
  pressure_design: "资源稀缺型压力反复升级：床位/药品/人手三重不够，逼她做取舍"
  forced_choice: "只救得起一只时救哪只——以及承认『不救』也是医术的一部分"
  end_state: "会说『不』的照看者：立规则，也守规则"
  arc_type: change
  milestones:
    - { volume_id: vol_01, milestone: "第一次主动叫停治疗并主持安乐死" }
    - { volume_id: vol_02, milestone: "为救助站立下收治红线，并当众顶住舆论" }
relationships:
  - { target_id: char_lao_pan, relation: "返聘老兽医，半个师傅", dramatic_function: "立场镜像——他早学会放手，提前演示她的终点" }
  - { target_id: char_meng_ke, relation: "财政拨款对接科员", dramatic_function: "制度压力源兼账目信息口" }
voice:
  tics: ["先瞅瞅再说", "不碍事"]
  sentence_style: "短句起手，动词开头，几乎不用形容词"
  taboo_words: ["随缘", "认命"]
  sample_line: "先瞅瞅再说——你把它爪子松开，我不看片子不下结论。"
masks:
  - { context: "对弃养人", mask: "万事好商量的和气大夫（先把动物留下再说）" }
  - { context: "对拖欠拨款的科室", mask: "报表齐全、寸步不让的会计脸" }
  - { context: "独自值夜", mask: "对着输液瓶小声排练『拒绝的话』" }
key_choices:
  - { situation: "台风夜停电，备用氧只够一箱，两只重伤幼兽只能救一只", choice: "选存活率高的那只，亲手给另一只安乐死", reveals: wound, pressure: extreme }
  - { situation: "自带流量的『明星伤鸟』上门，收下有捐款但要挤掉三个普通床位", choice: "拒收，并公开床位规则", reveals: belief, pressure: high }
secrets:
  - "账上最大一笔『匿名捐款』是她抵押婚房凑的（对角色隐瞒；对读者第二卷揭示）"
```

### 3.B 祝连城 — 反派 · 核心驱动 = 创伤（幸存者负罪，非「亡亲」套路）

```yaml
id: char_zhu_liancheng           # 信封其余字段略，同 §1
name: "祝连城"
role: antagonist
desire: "把船队做成全港最大，让船员『生死状』制度成为行业标准"
need: "承认那一刀是选择而非唯一解，接受清算"
onion:
  surface: "港城最体面的慈善船东，海难遗属口中的『祝大恩人』"
  behavior: "凡事先做弃船预案；决策只算『最大存活数』，不认个案"
  emotion: "渴求被遗属需要；最怕被认出是『砍缆绳的人』"
  belief: "『船长的手不能抖』——群体存活 > 个体公道 > 真相"
  wound: "创伤型：十九年前风暴夜，他亲手砍断缆绳弃了姊妹船，十一人失踪。此后的慈善、章程与体面都是给那一刀修的堤——生成上面全部四层"
arc:
  start_state: "无懈可击的恩人与行规立法者"
  pressure_design: "真相逼近型压力：旧物证与幸存者证词步步进逼，同构抉择情境反复重演"
  forced_choice: "再遇同构风暴夜：砍缆保本船，还是赌上全员"
  end_state: "当众自认那一刀，散尽船队设立搜救基金"
  arc_type: change
  milestones:
    - { volume_id: vol_01, milestone: "对主角第一次撒谎失手，暴露『预案癖』" }
    - { volume_id: vol_02, milestone: "同构风暴夜作出与当年相反的选择" }
relationships:
  - { target_id: char_zhu_yin, relation: "侄女，船队法务", dramatic_function: "良知压力源——他最怕被看穿的那双眼睛" }
  - { target_id: char_mai_dong, relation: "失踪水手之子，他资助读完航海学校", dramatic_function: "对抗轴心兼债主——每次施恩都是自我审判" }
voice:
  tics: ["按章程来"]
  sentence_style: "慢而完整的长句，惯用『我们』代替『我』"
  taboo_words: ["运气", "赌"]
  sample_line: "海上没有运气，只有准备——按章程来。"
masks:
  - { context: "遗属答谢宴", mask: "谦和的大家长，记得每家孩子的名字" }
  - { context: "船队调度室", mask: "把人当吨位排布的冷面数字机器" }
  - { context: "独对海图", mask: "第一千次推演那晚的另一种解法" }
key_choices:
  - { situation: "主角申请调阅当年的航海日志", choice: "亲手递上重抄的假日志，还资助主角出海『寻访』", reveals: behavior, pressure: mid }
  - { situation: "同构风暴夜，砍缆即可保全本船", choice: "这一次把自己留在缆绳那头", reveals: wound, pressure: extreme }
secrets:
  - "真航海日志沉在他每年忌日出海投放的浮标下（对所有角色隐瞒）"
  - "他从第一天起就认出了主角是谁（对主角隐瞒；对读者第一卷末揭示）"
```

---

## 修订

| rev | 日期 | 变更 |
|-----|------|------|
| 3 | 2026-08-13 | 修复轮：§2.4 声纹卡补方法指针一句（方法 K-CHAR-013；讨喜度/代入感自检 K-CHAR-014）；人物方法族引用范围更新为 K-CHAR-001~014；页脚 schema_rev 对齐字样统一（schema_rev 3） |
| 2 | 2026-08-12 | 重写为新代格式：通用信封 + asset-types §2.10 终态最小字段（onion 英文五键、arc.milestones 按卷、结构化 voice、masks、key_choices）+ 判据指引（五层问句/反例、压力→揭示层表、声纹防同质化）+ 两组异质示例（含非创伤驱动型） |
| 1 | — | 初版散文表格模板（中文洋葱键，无信封 / 协议字段） |

*template_for: Character | id: char_{slug} | schema_rev: 对齐 asset-types（schema_rev 3） | 通用工程层 · 不绑定具体作品*
