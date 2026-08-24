# Glossary — 术语 SSOT（Single Source of Truth）

> **权威级别**：本文件是 runtime 与 phases 的**唯一术语源**。  
> 阶段文、协议文、模板、召回策略**只引用、不重定义**此处已定术语。  
> 若与 `knowledge/` 叙述冲突：方法论细节以知识块为准；**工程命名与枚举以本文件为准**。

---

## 0. 文档目的

| 字段 | 值 |
|------|-----|
| `doc_id` | `runtime.glossary` |
| `role` | 术语与枚举的唯一 SSOT |
| `audience` | Agent / 人类协作者（可执行协议，非文学讲义） |
| `scope` | 通用创作工程层；**禁止**绑定具体书名、角色名、作品目录 |
| `non_goals` | 不复制知识块正文；不规定存储路径；不写情节示例 |

### 0.1 使用规则（Agent 必须遵守）

```
ON term_ambiguity:
  1. resolve via this glossary
  2. if missing → mark term as open_issue; do NOT invent parallel names
  3. never redefine onion layers / sequence index / status / asset_type elsewhere

ON writing_assets_or_protocol:
  use formal_name / snake_case id only
  map legacy aliases → formal_name before writeback
```

### 0.2 变更规则

- 增删术语：只改本文件，并 bump 文末 `glossary_rev`
- 废弃名：进入「废弃别名映射」，**禁止**在新产出中使用
- 知识块 ID（`K-*`）变更：同步更新 §7 前缀表；不改正文理论

---

## 1. 核心术语表

| 正式名 (zh) | id (snake_case) | 定义（工程可判定） | 关联 |
|-------------|-----------------|-------------------|------|
| 高概念 | `high_concept` | 面向传播的一句话卖点；可独立勾起阅读欲 | K-CONCEPT-001,006,008 |
| 前提 | `premise` | 面向创作的探索性假设（「如果…将会发生什么」） | K-CONCEPT-007,008 |
| 高概念元素 | `concept_element` | 可分类、可分级、可组合的情节积木 | K-CONCEPT-002~006 |
| 主控思想 | `controlling_idea` | `价值 + 原因`；在高潮被事件确证 | K-CONCEPT-013 |
| 思想 / 反思想 | `idea` / `counter_idea` | 正负主题在叙事中交替占优的论辩双方 | K-CONCEPT-014; K-CONFLICT-002 |
| 电缆结构 | `cable_structure` | 支线向心搅合主线，禁止树形分叉喧宾 | K-CONCEPT-010 |
| 引线 | `fuse_line` | 隐藏信息：埋设→暗示→揭示的时间表 | K-CONCEPT-011 |
| 支线 | `subplot` | 须收束、差异化、预埋；比例受主线约束 | K-CONCEPT-012 |
| 故事脊椎 | `story_spine` | 贯穿全篇的核心动作因果链 | K-STRUCT-017 |
| 五部分结构 | `five_part_structure` | 激励事件→进展纠葛→危机→高潮→结局 | K-STRUCT-009 |
| 激励事件 | `inciting_incident` | 打破平衡的动态重大事件 | K-STRUCT-008 |
| 鸿沟 | `gap` | 期望与结果之间的裂缝；场景动力源 | K-STRUCT-011 |
| 场景 | `scene` | 有价值极性变化的最小可交付戏剧单元 | K-STRUCT-010,013 |
| 节拍 | `beat` | 场景内动作/反应的最小结构单元 | K-STRUCT-002,018 |
| 序列 | `sequence` | 索引 `0..23` 的结构节点（见 §4） | K-STRUCT-003~007 |
| 幕 | `act` | 序列聚合：Act1=`0-6`，Act2a=`7-12`，Act2b=`13-18`，Act3=`19-23` | K-STRUCT-003 |
| 洋葱五层 | `onion_layers` | 人物深层性格五层模型（见 §2） | K-CHAR-004 |
| 人物弧光 | `character_arc` | 起点→压力→选择→转变/坚守→验证 | K-CHAR-005 |
| 塑造 / 深层 | `characterization` / `true_character` | 外在面具 vs 压力下选择揭示的真相 | K-CHAR-001 |
| 冲突三层面 | `conflict_levels` | 内心 / 人际 / 外部，须可交织标注 | K-CONFLICT-001 |
| 负面价值递进 | `negative_value_ladder` | 矛盾→对立→否定之否定…逐层加深 | K-CONFLICT-005 |
| 三层同心圆 | `world_concentric` | 法则→文化/历史→日常生活 | K-WORLD-002 |
| 背景四维度 | `setting_four_dims` | 时期 / 时长 / 地点 / 冲突层面 | K-WORLD-004 |
| 知识块 | `knowledge_block` | 只读方法论单元，ID 形如 `K-{DOMAIN}-{NNN}` | 见 §7 |
| 知识深度 | `knowledge_depth` | 阅读策略提示 `L1|L2|L3|L4`（非预算单位） | 见 §7.2 |
| 资产 | `asset` | 项目可写回实体；有 `type`/`status`/`rev` | 见 §6,§8 |
| 清单 / 注册表 | `manifest` | 资产索引与依赖注册，不承载正文理论 | 见 §8 |
| 阶段 | `phase` | 契约化工作单元（inputs/outputs/gate） | phase-contracts |
| 门禁 | `gate` | 阶段通过条件；失败走 `on_fail` | phase-contracts |
| 召回 | `recall` | 按 task 装载必选 `asset_type` + 限量 `K-*` | protocol |
| 回写 | `writeback` | 产出写入资产并更新 `status`/`rev`/依赖 | protocol |
| 分歧 | `conflict_case` | 设定/资产不一致事件，走 conflict-playbook | conflict-playbook |
| 过期 | `stale` | 依赖上游变更后未同步的状态标记 | §6 |
| 正典 | `canon` | 已采纳/已过 gate 的**存稿**；可被下游依赖的权威快照态（未发布） | §6 |
| 双轨 | `dual_track` | 传统长篇轨 / 网文连载轨；共享术语与类型，策略可分 | SKILL 路由 |
| 主笔角色 | `primary_cast` | 当前 scope 内持有 POV 或承担关键选择/弧光节点的角色集合；P4 gate 要求 canon 的即此集合 | K-CHAR-005 |
| 分层摘要 | `recap` | Recap 资产：`kind: book/volume/state`（滚动书摘/卷摘/现状快照），长程召回用 | asset-types §2.15 |
| 复合序列键 | `sequence_ref` | `{volume_id, sequence_index}` 跨卷唯一序列定位（索引为卷内 0–23）；速记 `v3:s12` | asset-types §2.8 |
| 追溯修正账 | `retcon_note` | locked（已发布）资产遇上游变更时的向前兼容账本条目；不回改已发布正文 | asset-types §2.2 |
| 常任晋升授权 | `auto_promote` | `Status.web_serial` 配置（`p4_canon`/`p4_canon_seed`/`chapter_canon_on_gate_pass`/`facts_upsert`）：gate PASS 后自动晋升，免逐次人批 | asset-types §2.1 |
| 卷末审计点 | `volume_checkpoint` | `open_next_volume` 前强制审计节点：卷报告（摘要/伏笔账/战力/blockers）+ 用户确认（`approved_by=user`；`unattended_mode=true` 时降级 agent_auto + pending_human_review 留痕后继续） | web-serial-playbook |
| 授权主体 | `approved_by` | `Decision` 必填字段：`user` / `agent_auto`；授权级别表见 asset-types §2.4 | asset-types §2.4 |
| 轻量变更 | `simple_change` | 目标未发布、不触 invariants / must_not_drop、且不追溯任何 locked 章既成事实（只影响未来章；触及 → 完整流水线 + retcon_note）：自批 Decision + 仅直接依赖标 stale + 懒同步 | conflict-playbook |
| 声纹卡 | `voice` | Character 结构化口吻：口癖 `tics` / 句长 `sentence_style` / 禁用词 `taboo_words` / 例句 `sample_line` | asset-types §2.10; K-CHAR-013 |
| 爽点 | `payoff` | 正面价值释放记录；`kind` 六枚举 `dopamine/upgrade/reveal/reversal/emotion/humor`（另 `other` 兜底） | K-STRUCT-020 |
| 发布 | `publish` | status-only touch 晋升：**唯一默认升 `locked`**、rev 不递增、action=publish；「已发布」判定全库唯一 = `status == locked` | asset-types §3.2；§6.2 |

### 1.1 禁止并行命名（漂移清单摘要）

下列说法若出现在旧文档中，**解析时映射到正式 id，写回时只用正式名**：

| 漂移说法 | 映射到 |
|----------|--------|
| 「24序列」「23点不含0」「序列1-23无Hook」 | `sequence` 索引 **0–23**（含序列0） |
| 「洋葱=面具/习惯/防御/恐惧/真相」等五词组 | §2 正式五层 |
| 「高概念六类」的 SKILL 旧六名 | §3 正式六类 |
| 「已定稿/终稿/锁定」混用无枚举 | §6 `status` |
| 「黄金三章」「golden_three」（章级特殊 gate / Status 字段 / ch≤3 分支） | **已废弃机制，无替代术语**：开篇章与其他章同标准，逐章过常规 P5/P6 web gate（钩子/字数/爽点）；发布就绪见 web-serial-playbook §6.2。禁止在新产出中重新引入 |
| 「黄金开篇」（作字段/gate 名时） | `opening_hook_intent` / 「开篇钩子」意图（P1 web gate 项） |
| `hook: {type, note}`（章计划旧钩子对象） | `hooks: {open, close, close_type?}` |
| `value_in` / `value_out` | `value_start` / `value_end` |
| `sequence_id`、跨资产裸 int 序列引用 | `sequence_ref: {volume_id, sequence_index}`（SequenceMap 条目内 `index` 仍为卷内 0–23） |
| `pay off`（Thread op 含空格） | `payoff` |
| `route: hybrid` | route 闭集 `traditional/web`；混合形态只写 `flags.dual_track` |
| `plot_turn_1` / `surprise_1`（锚点名） | `shock1` |
| `plot_turn_2` / `surprise_2`（锚点名） | `shock2` |
| `climax_zone`（作锚点 id） | `climax`（=序列 22）；「白热化带 21–22」仅为描述性用语 |

---

## 2. 洋葱五层（正式命名）

**正式名**：`onion_layers`  
**顺序**：由外到内（压力越大，揭示越内层）  
**知识锚点**：K-CHAR-004（操作细节只读知识块，不在此复述理论）

| 层序 | 正式名 (zh) | id | 工程含义（可标注） |
|------|-------------|-----|-------------------|
| L1 最外 | **表象** | `surface` | 社交面具、对外人设、场合切换的可见面 |
| L2 | **行为** | `behavior` | 习惯性应对、决策风格、处事模式 |
| L3 | **情感** | `emotion` | 核心情感需求、恐惧触发、真实情绪反应 |
| L4 | **信念** | `belief` | 价值体系、信条、自我叙事规则 |
| L5 最内 | **创伤** | `wound` | 根源性伤痛/核心事件；塑造上四层的「因」 |

### 2.1 压力 → 揭示层（标注约定）

| 压力等级 id | 默认揭示层 |
|-------------|------------|
| `pressure.low` | `surface` |
| `pressure.mid_low` | `behavior` |
| `pressure.mid` | `emotion` |
| `pressure.mid_high` | `belief` |
| `pressure.high` / `pressure.extreme` | `wound` |

资产字段建议：`reveal_layer: surface|behavior|emotion|belief|wound`

### 2.2 废弃别名映射（写回时禁止再用）

| 废弃 / 别名 | 正式 id | 备注 |
|-------------|---------|------|
| 社会面具、面具、保护壳（作「层名」时） | `surface` | 「保护壳」可作剧作机制描述，**不作层枚举名** |
| 习惯行为、习惯、处事模式（作层名） | `behavior` | |
| 防御机制、防御（作层名） | `behavior` 或上下文的 `emotion` | 旧五词把「防御」单列为层 → **废弃**；防御机制写入行为/情感字段说明 |
| 核心恐惧、恐惧（作层名） | `emotion`（恐惧触发）或 `wound`（根源） | 不得再作为独立层名 |
| 本性真相、真相、深层真相（作层名） | `wound` 或「选择揭示的 true_character」 | 层名只用 **创伤** |
| `trauma`（作洋葱层 id） | `wound` | 字段键名禁止 trauma，统一 wound |
| 面具→习惯→防御→恐惧→真相 | 全组废弃 | 见上逐条映射 |
| 社会面具→习惯行为→防御机制→核心恐惧→本性真相 | 全组废弃 | SKILL 旧表述 |

```
function normalize_onion_layer(raw: string) -> formal_id:
  table = ALIAS_MAP above
  if raw in formal_ids: return raw
  if raw in table: return table[raw]
  raise TermError("unknown onion layer")
```

---

## 3. 高概念元素六类（正式分类）

**正式名**：`concept_element_category`  
**知识锚点**：K-CONCEPT-002~005；知识正文与 templates 对齐下列六类。

| 正式名 (zh) | id | 判定要点 |
|-------------|-----|----------|
| **身份类** | `identity` | 身份、血统、地位、天赋、隐藏出身等角色属性卖点 |
| **关系类** | `relationship` | 人物间纽带及其戏剧性变化 |
| **事件类** | `event` | 改变格局的情节事件/倒计时/事变 |
| **冲突类** | `conflict` | 不可调和矛盾、对立、谜团、对抗结构 |
| **情感类** | `emotion` | 情感驱动力、羁绊、共鸣点（**元素类**，勿与洋葱 `emotion` 层混淆：元素用 `concept_element.emotion`，层用 `onion.emotion`） |
| **成长类** | `growth` | 能力/地位/认知蜕变与弧光卖点 |

### 3.1 元素等级（正式）

| 正式名 | id | 工程含义 |
|--------|-----|----------|
| 青铜 | `bronze` | 常见有效，撑局部小节 |
| 白银 | `silver` | 较有新鲜感，撑中段情节 |
| 黄金 | `gold` | 高冲击，可撑一卷级单元 |
| SSR | `ssr` | 极稀缺，可撑长跨度主线引擎 |

> 旧文仅写「青铜/白银/SSR」三档时：缺省将中间档写为 `silver`，不自动升 `gold`。

### 3.2 废弃别名映射（六类）

| 废弃 / 并行名（常见于旧 SKILL） | 正式 id |
|--------------------------------|---------|
| 人物关系类 | `relationship` |
| 世界观构建类 | **无独立类** → 拆入 `identity`/`event`/`conflict` 等，或记入资产 `WorldRule`，不单开第七类 |
| 主线推进类 | `event` 和/或 `growth`（按元素实际功能） |
| 冲突对抗类 | `conflict` |
| 情感发展类 | `emotion` |
| 信息揭示类 | `event` 或 `conflict`（谜团/揭示型）；或记入 `Thread` 伏笔，不单开类 |
| 六大类口语：身份/关系/事件/冲突/情感/成长 | 已是正式名，id 用上表 |

```
function normalize_element_category(raw: string) -> category_id:
  # prefer formal six; map legacy six-names; never invent 7th category in schema
```

---

## 4. 序列 0–23 约定

**正式名**：`sequence`  
**索引**：整数 **`0` 到 `23` 共 24 个节点**（口语「23序列法」= 该方法论名；**实现必须含序列0**）。  
**知识锚点**：K-STRUCT-003~007。

### 4.1 硬约束

| 规则 | 说明 |
|------|------|
| `sequence_index ∈ {0,1,…,23}` | 禁止 1–23 漏 0；禁止改成 1–24 |
| 序列0 正式名 | **Hook**（前置铺垫 / 引人入胜） |
| 编号书写 | `seq_00`…`seq_23` 或 `sequence: 0`；展示可用「序列0」「S0」 |
| 幕映射固定 | 见下表；阶段文不得重划幕边界 |

### 4.2 幕与关键节点

| 幕 id | 序列范围 | 功能摘要 |
|-------|----------|----------|
| `act_1` | 0–6 | 建立与启程；以惊人意外#1 收束 |
| `act_2a` | 7–12 | 试炼与成长；中间点在 12 |
| `act_2b` | 13–18 | 深化与压力升级；以惊人意外#2 收束 |
| `act_3` | 19–23 | 决战与收束 |

**锚点枚举（闭集；`PlotSpine.nodes[].anchor` 用，允许数组）**：
`hook | shock1 | growth1 | midpoint | growth2 | shock2 | growth3 | growth4 | climax | resolution`

| 锚点 id | 序列 | 正式标签 |
|---------|------|----------|
| `hook` | 0 | Hook |
| `shock1` | 6 | 惊人意外#1 |
| `growth1` | 8 | 成长第一步 |
| `midpoint`, `growth2` | 12 | 中间点 / 成长第二步（节点 12 允许数组 `[midpoint, growth2]`） |
| `growth3` | 16 | 成长第三步 |
| `shock2` | 18 | 惊人意外#2 |
| `growth4` | 19 | 成长第四步 |
| `climax` | 22 | 最终高潮（21–22 可称「白热化带」，仅为描述性用语；锚点=22） |
| `resolution` | 23 | 结局收束 |

必保锚点位：`0, 6, 8, 12, 16, 18, 19, 22, 23`（route=web 模式 B 下书级锚点降为 soft，见 asset-types §2.6）。

### 4.3 序列正式名称表（展示用；逻辑键仍用数字索引）

| # | 正式短名 | 结构标记 |
|---|----------|----------|
| 0 | Hook | 前置 |
| 1 | 出场时刻 | 铺垫/主题/保护壳展示 |
| 2 | 引发事件 | 冲突登场 |
| 3 | 历险召唤 | 海市蜃楼 |
| 4 | 开始上路 | 被迫上路 |
| 5 | 挣扎与陷阱 | — |
| 6 | 陷阱启动 | ⭐惊人意外#1 |
| 7 | 欢迎登船 | 计划/线索 |
| 8 | 遭遇风暴 | ⭐成长第一步 |
| 9 | 逐渐投入 | ⭐行动迸发#1 |
| 10 | 新的征程 | 误入雷区 |
| 11 | 接近虎穴 | — |
| 12 | 前线交战 | ⭐中间点 / 成长第二步 |
| 13 | 新的难题 | 新阶段目标 |
| 14 | 风雨前夜 | 启发 |
| 15 | 胜利假象 | ⭐行动迸发#2 |
| 16 | 战胜自己 | ⭐成长第三步 |
| 17 | 做好准备 | All-in |
| 18 | 全面战斗 | ⭐惊人意外#2 |
| 19 | 理清思路 | ⭐成长第四步 |
| 20 | 浴血重生 | 合力迎战 |
| 21 | 白热化 | — |
| 22 | 最终胜利或等价高潮 | 价值最大剧变带 |
| 23 | 分享果实 | 结局 |

### 4.4 废弃说法

| 废弃 | 正确 |
|------|------|
| 序列从1开始，Hook单独不算序列 | Hook = **序列0** |
| 「共23个序列即0-22」 | 共 **0–23** |
| 把中间点放在序列11或13当默认 | 默认中间点 = **12**（项目可标注变体，但须显式 `variant`） |

---

## 5. 五级叙事单元（结构层级）

| 层级（小→大） | id | 说明 |
|---------------|-----|------|
| 节拍 | `beat` | 最小 |
| 场景 | `scene` | 必须有价值变化 |
| 序列 | `sequence` | 0–23 |
| 幕 | `act` | act_1 / act_2a / act_2b / act_3 |
| 故事 | `story` | 整书或约定卷界 |

网文「章」是**发布单元**，映射到 `ChapterPlan`，**不是**插入五级之间的第六结构级；一章可含多场景，一场景可跨章（须在资产中声明）。

---

## 6. 资产 `status` 枚举语义

**字段**：`status`  
**枚举（闭集）**：

```
draft | review | canon | locked | stale | archived
```

| status | 语义 | 可被下游依赖？ | 典型转移 |
|--------|------|----------------|----------|
| `draft` | 草稿；可随意改 | 否（仅同行讨论） | → `review` / `stale`（上游变更） |
| `review` | 待审/待确认 | **是**：满足 contract `min_status` 即可作下游输入/写作执行，无需当轮人工授权 | → `canon` / `draft` / `stale`（上游变更） |
| `canon` | 正典；已采纳/已过 gate 的存稿（权威当前真相，未发布） | **是** | → `stale`（上游变更）/ `locked`（publish）/ `archived` |
| `locked` | **已发布/冻结**（publish 唯一默认晋升位）；禁止无裁决的内容变更 | 是（只读引用）；**不参与 stale 传播**——上游变更不标 stale，改写 `retcon_note` 入 `canon_continuity_v{n}` | 解锁需 `Decision(approved_by=user)` → `canon`/`draft` |
| `stale` | 因依赖变更而过期，内容可能错 | **否**（须同步或明示风险） | 同步后 → 原 status（`draft` / `review` / `canon`） |
| `archived` | 废弃保留历史 | 否 | 终态（一般不复活；复活视同新 `draft`） |

**授权边界（review 语义）**：资产满足 contract `min_status` 即可作为下游输入执行。「授权」（`Decision.approved_by`，级别表见 asset-types §2.4）只管三类动作：(a) `canon`/`locked` 晋升；(b) publish；(c) 破坏性动作（破坏 locked / 砍 `must_not_drop` 线 / 推翻 `Canon.invariants`）。

### 6.1 转移规则（最小状态机）

```
draft ──submit──► review ──approve──► canon ──freeze/publish──► locked
  ▲                 │                   │
  └──reject─────────┘                   └──retire──► archived

draft | review | canon ──upstream_change──► stale ──resync──► 原 status（draft | review | canon）
locked ──upstream_change──► 不标 stale；写 retcon_note 入 canon_continuity_v{n}
locked ──Decision(approved_by=user).unlock──► canon | draft
any_non_archived ──retire──► archived
```

### 6.2 与 `rev` 的关系

- 每次**语义写回**递增 `rev`（单调整数或内容哈希策略由 protocol 规定）
- `publish` = status-only 晋升（touch 操作）：**唯一默认升 `locked`**、action=publish；**`rev` 不递增**（见 asset-types §3.2）；「已发布」判定全库唯一 = `status == locked`
- `status=stale` 不自动改正文；只标记，直到 resync
- `locked` 资产：`rev` 冻结；违规写回 → gate fail

### 6.3 禁止的口头替代（写回时规范化）

| 口头 | 规范化 |
|------|--------|
| 初稿/WIP | `draft` |
| 待确认/PR中 | `review` |
| 已定/终版/权威 | `canon` |
| 冻结/签字 | `locked` |
| 过期/需更新 | `stale` |
| 废弃/作废 | `archived` |

---

## 7. K- 前缀与知识深度

### 7.1 知识块 ID

**格式**：`K-{DOMAIN}-{NNN}`

| DOMAIN | 含义 | 编号 |
|--------|------|------|
| `CONCEPT` | 构思 / 高概念 / 主线主题 / 类型 / 连载生态 / 内容安全 / 开书包装 | 001–022 |
| `STRUCT` | 故事结构 / 序列 / 事件 / 爽点工程 | 001–022 |
| `CHAR` | 人物 / 群像与配角运营 / 主角讨喜度 | 001–014 |
| `CONFLICT` | 冲突与对抗 | 001–006 |
| `WORLD` | 世界观 / 技能 / 势力 / 战力运营 | 001–024 |
| `WRITE` | 写作实践 / 解说 / 流程 / 正文病防治 / 毒点与融梗边界 | 001–023 |

合计 **111** 块（含 `knowledge/05-连载运营/` 补仓）。

**规则**：

- runtime **只引用 ID**，不复制大段知识正文
- 未知 ID → 查 `knowledge-blocks.md` / `knowledge-index.md`；禁止臆造 `K-FOO-999`
- 知识库为**只读服务**；创作状态写入 **资产**，不写入 `knowledge/`

### 7.2 知识深度 `L1`–`L4`（阅读策略提示）

**定位**：L1–L4 只提示「读一个块读到多深」，**非物理分段、不影响预算**。装载预算按块数计：`knowledge_budget = max_blocks + core/situational 白名单`（每块装载片段 ≤120 行，算法见 protocol）。

| id | 名称 | 用途 |
|----|------|------|
| `L1` | 概念层 | 定义与一句话；诊断/创意 |
| `L2` | 操作层 | 步骤与清单；默认执行深度 |
| `L3` | 原理层 | 抉择与争辩 |
| `L4` | 案例层 | 对照学习（**仍禁止**把案例书名写进通用协议规范） |

---

## 8. 资产类型约定

**原则**：`asset_type` 与**磁盘路径解耦**；路径由项目 storage adapter 映射，本 SSOT 只定**类型名与职责**。

### 8.1 正式类型表

| asset_type | 职责（工程） | 常见生产者 phase |
|------------|--------------|------------------|
| `Status` | 项目/阶段进度、当前 mode、阻塞原因 | 任意（协议维护） |
| `Manifest` | 资产注册表：id→type/status/rev/deps | 协议 |
| `Canon` | 跨阶段已确认事实的索引或摘要层（非情节正文库） | review 通过时 |
| `Blueprint` | 蓝图：高概念/前提/类型/元素初表/走向 | phase_1 |
| `PlotSpine` | 主线脊椎、电缆与引线计划 | phase_2 |
| `SequenceMap` | 序列0–23 填充与幕标记（事件+场景列表） | phase_3 / P3 |
| `SceneBeat` | 场景/节拍级设计 | phase_4 / P4 |
| `ChapterPlan` | 章节拆分、钩子、解说进度 | phase_5 |
| `Character` | 人物资产（含洋葱五层字段） | phase_2/4 |
| `WorldRule` | 世界法则/力量/势力规则 | phase_2 |
| `Thread` | 伏笔/引线/悬念线程（埋设-回收） | phase_3+ |
| `Decision` | 分歧裁决记录（可追溯，含 `approved_by`） | conflict-playbook |
| `ManuscriptUnit` | 正文单元（章/节草稿） | phase_6 |
| `Recap` | 分层滚动摘要：`kind: book/volume/state`；长程记忆读模型 | phase_6 / volume_checkpoint |

> 扩展新类型：先改本表 + `asset-types` 协议，再写适配器；禁止阶段文私自发明同义类型名。

### 8.2 资产最小元数据（逻辑字段）

```
asset:
  id: string
  type: asset_type          # §8.1 闭集或已注册扩展
  status: status_enum       # §6
  rev: int | string
  depends_on: list[asset_ref]   # 上游（与 asset-types §0.2 同名）
  stale_reason?: string
  glossary_rev: int         # 写入时对齐的本文件版本
```

### 8.3 与术语的字段对齐（强制）

| 概念 | 资产字段约定 |
|------|----------------|
| 洋葱层 | `onion.surface|behavior|emotion|belief|wound` 或 `reveal_layer` |
| 序列 | 卷内索引 `sequence_index: 0..23`；跨资产引用用复合键 `sequence_ref: {volume_id, sequence_index}`；禁止字符串「第一幕中段」代替索引 |
| 元素类 | `category: identity|relationship|event|conflict|emotion|growth` |
| 元素等级 | `tier: bronze|silver|gold|ssr` |
| 知识引用 | `knowledge_refs: [K-...]` |

---

## 9. 阶段与模式（名对齐，契约细节外置）

| 阶段正式名 | id | 主产出类型（逻辑） | 硬边界 |
|------------|-----|-------------------|--------|
| 蓝图 | `phase_blueprint` / P1 | `Blueprint` | 禁序列表/场景/章纲/正文 |
| 粗纲 | `phase_rough_outline` / P2 | `PlotSpine` 节点 0–23 + `Thread`/`Character`/`WorldRule`(草) | **禁任何场景级**；节点=标题+一句话价值 |
| 序列大纲 | `phase_sequence_outline` / P3 | `SequenceMap`（事件+场景列表） | 禁章纲/节拍定稿/正文 |
| 细纲 | `phase_detail_outline` / P4 | `SceneBeat` + `Character`/`WorldRule`(canon) | 禁按章内容块章纲/正文成稿 |
| 章纲 | `phase_chapter_outline` / P5 | `ChapterPlan` | 禁完整正文；改 canon 须 change |
| 正文 | `phase_writing` / P6 | `ManuscriptUnit` | 禁静默改 PlotSpine/SequenceMap/设定 |
| 空档 | `idle` | —（无产出） | 非工作阶段：scaffold 刚建成或阶段/卷间休整的合法驻留态 |

路由 intent（入口用，细节见 protocol）：`new_project` | `advance` | `write_unit` | `diagnose` | `change` | `learn`；`Status.mode` 记录当前 intent，空档时为 `idle`（见 asset-types §2.1）。

---

## 10. 冲突 taxonomy 用名（与 playbook 对齐）

| id | 含义 |
|----|------|
| `vertical_drift` | 上下游层级不一致（如章与序列脱节） |
| `lateral_conflict` | 同级资产互相矛盾 |
| `version_skew` | rev/status 不同步 |
| `intent_gap` | 作者意图与资产表达偏离 |
| `critique_unmerged` | 批评/反馈未回写正典 |

---

## 11. 规范化伪代码（Agent 写回前）

```
function normalize_terms(doc):
  doc.onion_layers = map(normalize_onion_layer, doc.onion_layers)
  doc.elements[].category = map(normalize_element_category, ...)
  doc.elements[].tier = map_tier(...)
  for s in doc.sequences:
    assert 0 <= s.index <= 23
  doc.status = map_status_alias(doc.status)  # must be closed enum
  doc.knowledge_refs = filter_valid_K(doc.knowledge_refs)
  doc.glossary_rev = CURRENT_GLOSSARY_REV
  return doc
```

---

## 12. 文档修订

| 字段 | 值 |
|------|-----|
| `glossary_rev` | `4` |
| `compatible_runtime` | `protocol`, `phase-contracts`, `asset-types`, `conflict-playbook`, `web-serial-playbook` |
| `notes` | 初版 SSOT：冻结洋葱五层、元素六类、序列0–23、status 六态、K- 前缀与资产类型名 |
| `rev2` | 新增「主笔角色」；废弃「黄金三章」机制与「黄金开篇」字段名（→ opening_hook_intent） |
| `rev3` | 锚点词表收编（十锚点闭集，climax=22，节点12可数组）；review 依赖语义重写（min_status 即输入）+ locked=已发布不 stale（→retcon_note）；新术语 recap/sequence_ref/retcon_note/auto_promote/volume_checkpoint/approved_by/simple_change/声纹卡/爽点 kind；废弃映射扩充（hook对象/value_in_out/sequence_id/pay off/hybrid/plot_turn_*）；K 域计数 106；L1–L4 降为阅读策略提示；phase/mode 补 idle、路由改称 intent；+Recap 类型 |
| `rev4` | 2026-08-13 修复轮：publish=locked 唯一默认（+publish 词条；canon=已过 gate 存稿；locked 注明 publish 默认晋升位）；draft→stale 边 + resync 恢复原 status；simple_change 第四条件（不追溯 locked 既成事实）；auto_promote +p4_canon_seed；volume_checkpoint 注 unattended_mode 降级；K 域计数 106→111（CONCEPT 22 / CHAR 14 / WRITE 23）；删原 §12 快速对照卡（纯展示，定义以各节为准） |

**变更检查清单**

- [ ] 是否只改本文件的正式名/枚举？
- [ ] 废弃名是否进入映射表而非直接删除历史可读性？
- [ ] phases/templates 若仍用废弃名 → 另开任务批量替换（本文件不绑作品）
- [ ] `glossary_rev` 已递增？
