# formats.md — v2 文件格式与工具接口契约(实施期 SSOT)

> 本文件钉死**项目侧全部文件格式**与 **novel.py CLI 接口**,是本 skill 的机器契约 SSOT。
> (历史注:文中 `spec §x` 指外部设计稿 `novel-workflow-v2-spec-20260813.md`,该文件**不随本库分发**,仅作出处溯源;一切以本文件为准,偏差记录见 §0.2。)
> 读者:全部实施 agent(工具/模板/角色/协议)与后续运行期编排者。CLI 实现覆盖表见 `tools/README.md`;未覆盖命令按对应协议人工执行。

---

## 0. 解析约束与载体裁决

### 0.1 三种载体(python3 stdlib,无 yaml 库)

| 载体 | 用途 | 解析规则 |
|---|---|---|
| **md + 扁平 frontmatter** | 人读内容资产(节点/实体/线索/裁决/评审/简报) | 文件首行 `---`,随后每行 `key: value`,再遇 `---` 结束。value = 标量,或以 `[` / `{` 开头的**内联 JSON**(json.loads)。**禁止**多行值与缩进嵌套 |
| **JSON** | 纯机器文件(config/队列/task/meta/facts/index/缓存/别名) | 标准 json |
| **TSV** | 追加式台账 | 首行表头,`\t` 分隔 |

### 0.2 与设计书的显式偏差

1. spec 中的 yaml 机器文件(config/queue/facts)一律改 **json**(stdlib 无 yaml 解析器)。
2. 写手回写块不入章文件 frontmatter,持久化为**伴生 `ch_NNNN.meta.json`**(嵌套结构不适合扁平 frontmatter)。
3. 简报预算按**字符数**计(`brief_budget_chars`,默认 24000 ≈ 12K token)。
4. 世界观细则单列 `tree/world.md`(book.md 只留核心两节);简报第 6 节改名「相关事实与设定」。
5. Recap 三层不迁移:长程记忆由 实体状态卡 + meta.json 摘要链 + 卷蓝图 imports/exports 承担。
6. 设计庭简报无专用 CLI(spec §4.3 的 `brief --design` 不实现):设计简报由编排者按 court.md R0 手工装配——低频且内容判断重,不值得工具化。
7. 庭预算与满编阵容冲突(spec §4.2 vs §4.3):以预算为准,court.md 用合并评审/轮换评审消化。

---

## 1. 项目目录布局(`novel.py init` 生成;项目根 = git 仓库)

```
<project>/
  config.json
  tree/
    book.md  style.md  world.md
    vol_01/volume.md  vol_01/arc_01_1.md ...
  chapters/ch_0001.md  ch_0001.task.json  ch_0001.meta.json
  briefs/ch_0001.brief.md
  entities/{char|item|loc|fac}_{slug}.md   entities/aliases.json  entities/scopes.json
  threads/thread_{slug}.md
  ledgers/timeline.tsv  payoff.tsv  power.tsv  facts/vol_01.json  lessons.md  recap.md
  court/dec_001_{slug}.md   court/transcripts/*.md
  reviews/ch_0001.light.md  ch_0001.deep.md
  data/feedback/            # 读者反馈收件箱(自由格式)
  data/compliance/          # 平台合规材料:敏感词表/审核规范/申诉记录(自由格式,
                            # safety-auditor 与发布前自查按需读取,编排者只读)
  tasks/queue.json  tasks/archive.json      # archive = task archive 归档的 done 任务
  state/index.json  dashboard.md  ngram_cache.json  rollup.json   # 生成物,禁止手改
  state/stage.json          # 已进入阶段(stage enter 独占维护;阶段闸门的裁决依据,§14)
  state/txn/                # 原子提交事务日志(txn_begin/txn_end;done=false 残留 = 半事务,fsck 检出)
  state/reports/vol_NN.md   # 卷报告(report volume 生成;唯一可编辑处=对账三态标注)
  state/court/              # 庭审中间态工作区(R0 简报/R1 提案/R2 评审/R3 主编稿,
                            # court open/status/close 机械管理;中断恢复用,永不入简报召回)
  corpus/                   # 用户自备范文(可空)
```

## 2. id 约定

`book` · `style` · `world`(三单例) · `vol_01` · `arc_01_1`(卷号_卷内序) · `ch_0001`(全局四位) · `char_/item_/loc_/fac_{slug}` · `thread_{slug}` · `t_000001`(任务) · `dec_001_{slug}` · `payoff_0001_1`(章号_序)。别名→id 对账:`entities/aliases.json`(`{"李衡": "char_li_heng"}`)。

## 3. 信封与状态机

**公共 frontmatter 键**:`id`, `kind`, `status`, `rev`(int,从 1), `parent`(book 无), `updated_at`(ISO8601)。
`kind` 枚举:`book | volume | arc | chapter | entity | thread | style | world | decision | review`。

**status 枚举(按 kind)**:

| kind | 枚举 | 说明 |
|---|---|---|
| book/volume/arc/world/style | `empty → draft → committed`;另 `stale / archived` | committed=设计庭/简流程定稿 |
| chapter | `planned → drafted → approved → published`;另 `stale / archived` | drafted=写手落盘;approved=**落盘回执**(§12)+check 绿;published=不可变 |
| entity/thread/decision/review | `active / archived` | 线索业务状态另见 §8 `state` |

**迁移纪律**:`draft→committed` 由编排者经 `novel.py commit` 执行;`committed→stale` 由 revise_design 波及标记;`published` 不可改,变更走 retcon(§9 facts);`stale` 节点修复后回原 status。

## 4. 树节点 payload(必需标题节;`check --project` 机检「节存在且非空」)

**tree/book.md**:`## 主旨与主控思想` `## 高概念与题材定位` `## 世界观核心` `## 金手指与力量体系` `## 主线电缆`(5–9 个阶段目标,粒度=卷群) `## 人物主阵容` `## 反派梯队` `## 分卷草案` `## 红线自查结论`

**tree/style.md**:`## 叙述基准`(人称/时态/句长) `## 口癖与句式禁忌`(每行 `- 词或句式`;`check --unit` 取用) `## 比喻与意象纪律` `## 范文锚`(2–3 段,可引 corpus/)

**tree/world.md**:`## 核心规则`(表:规则|硬度|代价) `## 力量体系与位阶`(锚定表:tier|稳赢|五五|必败|基准人物|代价) `## 势力格局` `## 禁忌与红线`

**tree/vol_NN/volume.md** 九节:`## 卷主旨与价值走向` `## 卷级冲突结构` `## 弧划分表` `## imports` `## exports` `## 阵容变化` `## 力量与资源预算` `## 爽点大节奏` `## 红线与毒点自查结论`
— 弧划分表列:`arc_id | 章数预算 | 一句话目标 | 节奏模板`

**tree/vol_NN/arc_NN_n.md** 六节:`## 弧目标与节奏模板` `## 因果链`(5–10 事件,标价值方向) `## 章分配草案` `## 线索操作计划` `## 爽点与期待操作表` `## 出场实体清单`
— 章分配草案列:`ch | 一句话目标 | 出场 | 线索op | 爽点意图`

## 5. 章文件三件套

**chapters/ch_0212.md** = 信封(kind: chapter, parent: arc_03_2, + `title`, `word_count`)+ `## 正文`(其后即正文,无其他节)。

**chapters/ch_0212.task.json**(任务卡;骨架由 novel.py 从弧计划抽取,beats/hook 由编排者排批时补全):

```json
{"id":"ch_0212","arc":"arc_03_2","goal":"…","beats":["…","…"],
 "hook":{"open":null,"close":"…"},
 "payoff_quota":[{"kind":"dopamine","intent":"…"}],
 "threads":[{"id":"thread_x","op":"advance"}],
 "cast":["char_a","fac_b"],"word_target":[2000,4500]}
```

**chapters/ch_0212.meta.json**(writeback 持久化;写手回写块与此同构):

```json
{"summary_after":"3–8句","continuity_delta":[{"fact":"…","entity_ids":["char_a"],"spoiler":0,"key":"持有","known_by":["char_a"]}],
 "time_advance":{"elapsed":"2天","story_date":""},
 "thread_ops":[{"id":"thread_x","op":"advance","note":"…"}],
 "payoff_realized":["payoff_0212_1"],"hooks_realized":{"open":true,"close":true},
 "cast_actual":["char_a"],
 "power_delta":[{"entity_ids":["char_a"],"from":"炼气三层","to":"炼气四层","note":"…"}],
 "issues":[],"word_count":3120}
```

`payoff_*.kind` 枚举:`dopamine|upgrade|reveal|reversal|emotion|humor|other`。`thread op` 枚举:`plant|advance|payoff|tangle|ready`。
可选键:`continuity_delta[].key`(实体状态键位,如 位置/持有/知晓——填了可让 facts 冲突扫描精确到同键矛盾);`continuity_delta[].known_by`(**知识矩阵角色半边**:剧中知晓此事实的实体清单;不填=不设知情约束,见 §9);`power_delta`(战力/位阶变化时必填,commit 追加 `ledgers/power.tsv`)。
**越权纪律**:`cast_actual`/`continuity_delta`(含 known_by)/`thread_ops`/`power_delta` 引用的实体与线索必须已登记(entities/aliases/threads),否则 `check --unit` FAIL、commit 拒绝落盘——写手不得发明实体,缺卡走 issues。`continuity_delta` 每条必含 fact/entity_ids/spoiler。

## 6. 简报 briefs/ch_NNNN.brief.md(`novel.py brief` 生成)

frontmatter:`id: brief_ch_0212`, `kind: review` 除外——用 `kind: brief` 不入信封枚举?**裁决**:brief 无信封,首节前仅三行注释(chapter / brief_rev / compiled_at / budget_chars 以 HTML 注释行 `<!-- key: value -->` 写)。
固定十节:

```
## 0 任务卡            (task.json 渲染;must-not-drop)
## 1 文风与禁忌        (叙述基准+口癖禁忌 must;比喻纪律/范文锚可裁)
## 2 直接上文          (前章尾 500 字+前 3 章 summary_after must;弧/卷 rollup 与 recap 可裁)
## 3 出场实体状态卡    (声纹速查块+现状+最近3事件 must;「设定要点」可裁——先裁非主角)
## 4 活跃线索          (任务卡 threads ∪ must_not_drop 线 must;scope/payoff 临近命中可裁)
## 5 弧内位置          (弧因果链 + 前后章位置;可裁)
## 6 相关事实与设定    (facts 实体键查逐条记分,superseded 者连带 retcon;spoiler 注
                        【读者未知】,known_by 注【知情仅】+【在场不知情】硬约束;world 规则;可裁)
## 7 写作提示          (route 选配纪律速记 + lessons 尾 5 条;可裁)
## 8 回写契约          (meta.json schema 原文;must-not-drop)
## 附 溯源             (表:资产|rev|用途 + 裁剪留痕行)
```

**条目级预算(P1-2)**:每个内容条目带优先级分与 must-not-drop 标记;超 `brief_budget_chars` 时从**最低分条目**逐条裁起(非整节丢弃),裁剪逐项记入对应节内提示行与溯源表。must-not-drop 集(永不裁):任务卡、回写契约、叙述基准+口癖禁忌、前章尾+summary 链、声纹速查、实体现状+最近事件、任务卡指定线与 must_not_drop 线。fact 条目按 时近(≤30 章 +10)/键位(+3)/retcon 连带(+5) 加分。已存在则 `brief_rev+1` 重写(git 保历史)。
记忆分层(§2):近景=前章尾 500 字+前 3 章 summary 链(must);中景=本弧 rollup 行(距今 >3 章的章级卷积);远景=卷级 rollup 行+`ledgers/recap.md` 尾 12 行——距离越远颗粒越粗,百万字仍在预算内。
**声纹速查(P1-3)**:cast 各实体卡「设定」内声纹条目(口癖/句式/禁词/例句)抽出为 §3 首个独立块,must-not-drop——设定可裁,声纹不裁(防千人一腔)。
第 4 节召回=任务卡 threads ∪ live 态线中(must_not_drop ∪ volume_scope 含本卷 ∪ payoff_planned 命中本卷或 ≤15 章内,后者加【payoff 临近】标记);第 7 节按 `config.route` 切换 web/traditional 提示组。

## 7. 实体卡 entities/*.md

frontmatter:`id`, `kind: entity`, `entity_type: char|item|loc|fac`, `status: active`, `rev`, `aliases: ["…"]`(内联 JSON), `updated_at`, `last_event_ch`(int), `last_reconcile_ch`(int)。

节:
- `## 设定`(设计真值,设计庭/卷庭产出)— char:欲望/需要/洋葱五层(表象|行为|情感|信念|创伤)/声纹(口癖·句式·禁词·例句)/弧光里程碑(按卷)/关系;item/loc/fac:各自设定要点
- `## 现状`(产线维护)— bullet `- 键: 值`。char 固定键:`位置/状态/持有/知晓/关系现状/未了承诺`;item:`持有者/状态/能力`;loc:`控制方/现况`;fac:`目标/实力/与主角关系`
- `## 事件日志` — `- ch_0212: 一句话`,append-only(commit 机械追加自 continuity_delta)

对账轮:`entity due` 列出 `last_event_ch - last_reconcile_ch ≥ config.reconcile_every` 的实体;资料员产出新「现状」节,经 `entity update <id> --file` 落卡(仅替换现状节,日志不动)。

## 8. 线索 threads/*.md

frontmatter:`id`, `kind: thread`, `thread_kind: fuse|subplot|relationship|mystery|promise|other`, `state: planted|active|tangled|payoff_ready|paid_off|dropped`, `must_not_drop: true|false`, `volume_scope: ["vol_01"]`, `plant_ch: int|null`, `payoff_planned: "vol_03"|"ch_0250"|null`, `status: active`, `rev`, `updated_at`。
节:`## 陈述`(一段);`## 推进日志`(`- ch_0212: advance 一句话`,commit 追加自 thread_ops)。

**状态机合法迁移表**(novel.py 强制;非法迁移 = check FAIL,commit 拒绝):

| op \ 当前态 | planted | active | tangled | payoff_ready | paid_off/dropped |
|---|---|---|---|---|---|
| plant(回填 plant_ch) | planted | ✗ | ✗ | ✗ | ✗ |
| advance | active | active | active | payoff_ready(仅记日志) | ✗ |
| tangle | tangled | tangled | tangled | tangled | ✗ |
| ready | payoff_ready | payoff_ready | payoff_ready | payoff_ready | ✗ |
| payoff | paid_off | paid_off | paid_off | paid_off | ✗ |

纪律:`paid_off/dropped` 为终态,复活需 decision + 登记新线;`must_not_drop=true` 的线置 `dropped` 需 decision 引用且该 dec 文件在 court/ 真实存在(check --project 校验);`paid_off/dropped` 不入简报召回。`dropped` 由编排者手工置(附 dec 引用),不经 thread_ops。

## 9. 台账(novel.py 独占维护)

- `ledgers/timeline.tsv`:`chapter	story_date	elapsed	note	rev`
- `ledgers/payoff.tsv`:`chapter	payoff_id	kind	intent	realized	rev`(realized 0/1)
- `ledgers/power.tsv`:`chapter	entity	from	to	note	rev`(commit 自 writeback 可选 `power_delta` 追加;`check --window` 对近 10 章同实体 ≥3 次变动告警;设定审计/深评按 rubrics/power.md 对账卷预算)

**(chapter, rev) 语义(P0-1)**:三张 TSV 文件本体 append-only(revise 追加新 rev 行,旧行保留为审计痕);一切**读取**(ledger 视图/check/深评统计)按 (chapter) 分组只取**最新 rev** 行——修订零双计。实体「事件日志」与线索「推进日志」在 revise commit 时先**撤销重放**:剔除本章旧 rev 行(实体 last_event_ch 回退、线索 state 以剩余日志重推),再追加新 rev 贡献——终态线(paid_off)在修订裁决撤回 payoff op 后可合法回到 active。facts 先剪后登:剪除本章旧 rev 登记的未被引用事实(fact_id 不复用),再登新 delta。
- `ledgers/facts/vol_NN.json`(**commit 自动登记**:自 continuity_delta 分配全局递增 `fact_id` 写入本章所属卷文件,同文同章去重;`key` 可选,继承自 delta):

```json
{"facts":[{"id":"fact_0001","fact":"…","entity_ids":["char_a"],"revealed_ch":212,"spoiler":0,
           "superseded_by":null,"key":"持有","known_by":["char_a","char_b"],"revealed_reader_ch":230}],
 "retcons":[{"id":"ret_001","entity_ids":[],"old_fact_id":"fact_0001","new_fact":"…",
             "strategy":"reconcile|fade_out|explicit_fix","decision_ref":"dec_00x"}]}
```

**知识矩阵语义(P4-K/v2:fact × 角色/范围 × 读者)**——每条 fact 两条正交轴:
- **读者轴** `spoiler`:1=读者未知(简报注【读者未知,只可潜台词】;check 做剧透相似扫描)。读者揭示经 `novel.py knowledge reveal <fact_id> --ch <ch>` 销账(spoiler→0,记 `revealed_reader_ch`;悬念资产的欠账盘点用 `knowledge query`,弧末/卷末例行,workflow §4)。
- **角色轴** `known_by`(可选):剧中知晓者清单,条目为 `char_`(个体)或 `fac_/loc_/item_`(**范围知情,v2**)。**缺省=未建模,不设约束**(旧数据兼容);一经填写即为白名单——简报 §6 注【知情仅:…】与【本章出场 X 不知情】硬约束,check 抽取器做「越界候选」扫描(有效知情集外的在场角色明写该事实 → NEEDS_REVIEW)。来源两路:commit 自 `continuity_delta[].known_by` 自动登记;剧情中后续获知走 `novel.py knowledge grant <fact_id> --to <实体> [--ch <获知章>]`(获知场景须有正文/日志支撑,评审抽查账实一致)。

**范围知情圈(v2)** `entities/scopes.json`(novel.py 独占维护):

```json
{"fac_shadow": ["char_a", "char_b"], "loc_capital": ["char_c"], "item_sword": ["char_a"]}
```

- 键=已登记的 `fac_/loc_/item_` 群体实体;值=已登记 `char_` 成员(势力成员/常驻知情者/持有人)。经 `novel.py knowledge scope add|remove <群体> <char…>` 维护(入圈/出圈须有正文/日志支撑:入伙、驻留、易手),`scope list` 查圈。
- **展开口径(全链一致)**:known_by 内群体条目的**有效知情者 = 群体本身 ∪ 圈成员**(简报【知情仅】显示 `fac_x圈(char_a,char_b)`、不知情名单按展开后计算;extract 越界扫描同口径;`knowledge query --entity` 对个体列「经 X 圈」知情,对群体列圈成员)。圈成员变化即时生效于所有引用该群体的 fact——**改圈=改一处,矩阵各处同步**。
- 空圈:范围授予但圈无成员 = 展开后无人知情(grant 时打提醒;`check --project` 出 WARN);圈键/成员未登记或类型不符 → `check --project` FAIL。矩阵改账(grant/scope add/remove)受阶段闸门辖 `write|review`(§15)——矩阵更新只发生在章循环/周期回路内,不是自由运维。

- `ledgers/lessons.md`:`- [ch_0212|vol_02|book] 教训一句话(来源 review id)`——例外:本台账由**编排者**经 commit 附笔追加(格式固定),非 novel.py 生成
- `ledgers/recap.md`:全局梗概,**编排者维护**(卷末 checkpoint 必更,期间每 ~10 章可追加一段,每段 3–6 行);`novel.py brief` 注入尾 12 行进 §2——长程记忆的轻量层,与 summary_after 链/实体卡互补

纪律:retcon 经 `novel.py retcon` 落盘(校验 old_fact 存在未覆盖 + decision 存在),旧 fact 填 `superseded_by`;简报第 6 节命中此类 fact 必须连带 retcon 条目。

## 10. 任务队列 tasks/queue.json

```json
{"next_seq":232,"tasks":[
 {"id":"t_000231","type":"design","target":"vol_04","state":"pending",
  "blocked_on":[],"attempts":0,"note":"","evidence":"","created_at":"…","updated_at":"…"}]}
```

`type` 枚举:`design | revise_design | write | revise | review_deep | publish | retcon | checkpoint | reconcile | revise_rubric`。
`state` 枚举:`pending | blocked | running | done | failed`。
纪律:`write/revise` 同 target `attempts ≥ 2` 再 fail → novel.py 自动追加一条 `revise_design` 任务(升级);`revise_design` 创建须带 `--evidence`,novel.py 提示比对 court/ 否决案;`revise_rubric` 创建须带 `--evidence`(lessons/review 条目引用)且 target 限 `style`(蒸馏回路,workflow §6)。
队列自动化:`blocked` 任务在 `blocked_on` 全部 done 后由任意 task/status 命令自动解锁 → `pending`;`task reset <id>` 将 failed/running 拉回 pending(done 不可 reset,负例拒绝);`task archive [--keep N]` 把多余 done 任务移入 `tasks/archive.json` 防队列膨胀。

## 11. 裁决记录 court/dec_NNN_{slug}.md

frontmatter:`id`, `kind: decision`, `node`(目标节点), `session: S1|S2|S3|S4|volume|arc|adhoc`, `date`, `status: active`。
节:`## 选项`(`- 案id | 提案角色 | 一句话`);`## 裁决`(选择+理由);`## 否决案`(`- 案id | 否决理由 | reopen_requires: 重开所需新证据`);`## 异议`(`- 角色 | 意见 | resolution: disagree_and_commit|adopted`)。
transcripts 归档 `court/transcripts/`,**永不进入简报召回**。

## 12. 评审 reviews/ch_NNNN.{light|deep}.md

frontmatter:`id`, `kind: review`, `chapter`, `depth: light|deep`, `verdict: pass|revise|escalate`, `rev_reviewed`(章 rev), `date`。
节:`## 问题清单`(`- [定位≤20字] 问题 → 建议`,revise 时每条须可执行);`## 教训`(可选,编排者摘入 lessons)。
**落盘规则(P0-2 收紧)**:一切评审结论必须落盘 reviews/——轻评 pass 用 `novel.py review add <ch> --depth light --verdict pass [--note 要点]`(rev_reviewed 自动取章当前 rev);deep 经 commit type=review_deep 落盘。任务 note 的 `light=pass` 与 `--evidence` 自证通道**已删除**。
**approved 闸门**:`tree set-status <ch> approved` 仅认 reviews/ 文件且 `verdict=pass ∧ rev_reviewed == 章当前 rev`——章 revise 后旧回执自动失效(打印过期告警),须对新 rev 复评。回执引用写入章 frontmatter `approved_evidence`。

## 13. config.json(init 默认)

```json
{"preset":"standard","route":"web","word_target":[2000,4500],
 "buffer":{"target":3,"min_before_publish":1},
 "critic":{"light_every":1,"deep_every":5},
 "approvals":{"book_commit":true,"volume_commit":true,"publish":true,"checkpoint":true},
 "unattended":false,"reconcile_every":10,"brief_budget_chars":24000,
 "volume_defaults":{"arcs":[5,12],"chapters":[80,250]},
 "ngram_window_chapters":30,"ngram_archive_sample":400,
 "spoiler_debt_chapters":15}
```

`route ∈ {web, traditional}`:traditional 差分(无 buffer/publish、章尾钩与爽点窗口降级、简报 §7 提示切换)见 `modes/route-traditional.md`;`check`/`brief` 按此键自动切换。(历史注:早期草案含 `models` 键为各角色预留模型档位,从未被读取,已删除;角色模型选择属产品层配置,不入项目 config。)

## 14. 生成物(禁手改;标注例外除外)

- `state/index.json`:`{generated_at, nodes[], chapters[], entities[], threads[], tasks:{pending,blocked,head}, cursor:{last_published,last_drafted,last_approved}, last_deep_review_ch, warnings[]}`(nodes 含 id/kind/status/rev/parent/path;chapters 含 id/status/rev/parent/mtime——mtime 用于 `status` 的章级增量重算,未变更章直接复用旧条目)
- `state/dashboard.md` 段落:项目一行(含深评游标与逾期提醒)· 树进度表(卷|状态|弧|章数)· 树节点 · 章按状态 · 队列头 5 条 · 告警(check --window 摘要)· 最近 3 次 git commit
- `state/ngram_cache.json`:分层指纹(P2-4)——窗口内(最近 `ngram_window_chapters` 章)`{"n12": […], "n8": […]}` 两级全量;窗口外降级为归档层 `{"n12s": […]}`(12-gram 稳定降采样 ≤`ngram_archive_sample` 条/章,不留 n8)。12 字级自我复读检测覆盖**全史**而体积有界;commit 更新(旧版扁平数组格式读取时视为 n12,兼容)
- `state/rollup.json`:自动摘要卷积(P1-1)——`{arcs: {arc_id: {vol, span, lines[]}}, volumes: {vol_id: [弧一行摘要…]}}`;弧级=各成稿章 summary_after 首句,卷级=各弧首末摘要压缩;commit/adopt/facts import 后重算,brief §2 注入为远程记忆层
- `state/stage.json`(P7-S):`{stage, entered_at, history:[{from,to,at}…]}`——**当前已进入阶段**,由 `stage enter <id>` 独占维护(history 留最近 20 次迁移)。这是阶段闸门(§15 辖区表)的唯一裁决依据:受辖命令执行前校验之,不看启发式推断;缺失 = 项目未进入任何阶段,一切受辖操作被拒。禁手改;误进阶段的纠正方式就是再 `stage enter` 正确阶段(迁移留痕)
- `state/txn/txn_*.json`:原子提交事务日志——多文件落盘前写 `done=false`,全部写完置 `done=true`(保留最近 20 份完成事务);`done=false` 残留 = 半事务,`fsck`/`check --project` FAIL,恢复=按 §18 reset 未提交内容后删除 journal
- `state/reports/vol_NN.md`:`report volume` 生成;**例外**——「exports 对账」节的三态标注(`[待对账]` → `[兑现 ch_NNNN]|[移交]|[废止 dec_xxx]`)由编排者手工编辑,checkpoint 机检
- `state/court/`:庭审中间态工作区(非生成物,编排者按场次存 R0–R4 中间产物;见 court.md §3)

## 15. novel.py CLI(退出码:0=通过 / 1=校验失败 / 2=用法或环境错误)

```
novel.py init <dir> [--name X]            # 脚手架+git init+首 commit
novel.py status                           # 重算 index+dashboard(章级增量),打印 dashboard、深评逾期提醒与可恢复断点
novel.py tree add <kind> <id> [--parent P]   # 由模板实例化空壳节点(volume|arc|chapter)
novel.py tree show [id]
novel.py tree set-status <id> <status> [--evidence E]
                                          # 含迁移合法性校验;chapter→approved 仅认 reviews/ 落盘回执
                                          # (verdict=pass ∧ rev_reviewed=章当前 rev;先 review add)
novel.py task add <type> <target> [--note N] [--blocked-on t_x] [--evidence E]
novel.py task next|list [--state S]       # next 附深评逾期提醒;blocked 依赖完成自动解锁
novel.py task start|done|fail|reset <id> [--note N]   # reset: failed/running → pending
novel.py task archive [--keep N]          # done 任务归档 tasks/archive.json(默认留 20)
novel.py brief <ch_id>                    # §6 机械装配;重跑 brief_rev+1;生成后自动 git commit(保证 spawn 前基线干净)
novel.py commit <task_id> [--file F ...] [--chapter F --writeback F] [--draft] [-m 摘要]
                                          # --file 可多值;--draft = 设计节点 draft 态部分落盘(见 §16)
novel.py check --unit <ch_id> [--candidate F --writeback F] | --window [--since CH] | --project
                                          # --candidate/--writeback = 未落盘 staging 机检;--since = 窗口增量起点
novel.py check --leak <候选章> --brief <简报>   # 简报外已登记专名泄漏扫描(pipeline §5 机械辅助)
novel.py entity new|show|log <id> ; entity due ; entity update <id> --file F
novel.py thread new <id> [--kind K]       # 线索登记
novel.py ledger payoff|promise|timeline|power   # 窗口统计视图
novel.py publish <ch_from> [<ch_to>]      # 连续性谓词;approved→published
novel.py retcon <old_fact_id> --new … --strategy reconcile|fade_out|explicit_fix --decision dec_id [--entity E ...]
                                          # serial-ops §3:old_fact 存在未覆盖 + decision 存在才落盘
novel.py report volume <vol_NN>           # 卷报告汇编 → state/reports/vol_NN.md(exports 预标 [待对账])
novel.py checkpoint <vol_NN>              # 卷末结账:报告存在+三态齐+卷内无未完稿章 → 卷标记+下卷 imports 预填
novel.py adopt <file> --as ch_NNNN [--parent arc] [--title T]   # 外部文稿收编(protocol/adopt.md)
novel.py review add <ch_id> --depth light|deep --verdict pass|revise|escalate
                    [--note N] [--rev R]  # 评审回执落盘 reviews/(rev 默认=章当前 rev);review list
novel.py facts import <ch_id ...>         # adopt 补录机械半边:自 meta.json continuity_delta
                                          # 分配 fact_id 入账(幂等可重跑);facts list [--entity E]
novel.py knowledge grant <fact_id> --to <实体> [--to ...] [--ch <获知章>]
                                          # 角色/范围轴:known_by 追加——char 个体或 fac/loc/item
                                          #   范围(按知情圈展开;获知须有正文/日志支撑)
novel.py knowledge reveal <fact_id> --ch <ch>   # 读者轴:spoiler 1→0,记 revealed_reader_ch(悬念销账)
novel.py knowledge scope add|remove <群体> <char…>  # v2 知情圈维护(fac/loc/item→char 成员,
                                          #   entities/scopes.json);scope list [群体] 查圈
novel.py knowledge query [--fact F|--entity E]  # 矩阵视图:单条全貌/个体或群体知与不知(含圈展开)/
                                          #   默认盘点读者未知欠账(弧末/卷末例行,workflow §4)
novel.py rollup                           # 手动重算章→弧→卷摘要卷积(commit/adopt/facts import
                                          #   已自动;本命令用于批量手改 meta.json 后的显式对账)
novel.py extract <ch_id> [--candidate F] [--writeback F]
                                          # 抽取器独立入口:正文反向解析+对账(双记账机器半边;
                                          #   角色卡见 roles/extractor.md,C/D 档帽子用)
novel.py gate next                        # 机器版编排剧本:按优先级输出下一步(修账>深评>对账>
                                          #   欠账[spoiler 挂账 ≥spoiler_debt_chapters 章]>缓冲>推进)
                                          #   末行附当前阶段推断+配套知识包路径——迷路时的第一命令(workflow §0)
novel.py stage list|show <id>             # 阶段总表 / 打印某阶段配套知识包全文(只读)
novel.py stage enter <id>                 # 进入阶段:写 state/stage.json(§14)+git;受辖操作的前提;
                                          #   与启发式推断不一致时打印核对提醒(跨阶段进入须确认收口)
novel.py stage current                    # 读持久化阶段(不是启发式!)+配套包路径+启发式核对;
                                          #   未进入任何阶段 → exit 1 并给 enter 提示
                                          #   (SSOT=protocol/knowledge-orchestration.md §5)
novel.py gate write|approve <ch_id>       # 前置谓词闸门(只判不写):write=排批齐+简报在+基线净;
                                          #   approve=drafted+落盘回执 rev 匹配+机检绿
                                          #   P4-G:每条 FAIL 附「↳ 下一步」可执行修复命令
novel.py gate publish <ch_from> [<ch_to>] # publish 前置谓词试跑(不落盘;FAIL 附下一步)
novel.py gate checkpoint <vol_NN>         # checkpoint 前置谓词试跑(不落盘;FAIL 附下一步)
novel.py court open <场次> --node <节点>  # 建 state/court/<场次>/ + R0 简报骨架
novel.py court status                     # 盘点活跃场次与回合产物
novel.py court close <场次> --dec dec_id  # 校验裁决已落盘 court/ 后清理场次工作区
novel.py fsck                             # = check --project(含半事务检出)
```

reconcile 汇总仍按 serial-ops §5 由编排者执行(`entity due` + `entity update` 已覆盖机械部分)。`status` 重算 index/dashboard;其余命令按需读取。项目根定位:cwd 向上探测或 `--root`。实现覆盖表与差异细节见 `tools/README.md`。

**阶段闸门辖区表(P7-S;受辖命令执行前校验 `state/stage.json`,不匹配 = exit 1 + `stage enter` 修复提示)**:

| 受辖操作 | 允许阶段 |
|---|---|
| `court open S1/S2/S3/S4` | 对应 `s1/s2/s3/s4`(`vol_*` 场→`vol`;`arc_*` 场→`arc`;adhoc 场→任意已进入阶段) |
| `commit design\|revise_design`(book/world/style 级) | `s1\|s2\|s3\|s4` |
| `commit design\|revise_design`(`vol_*` 目标) | `s4\|vol` |
| `commit design\|revise_design`(`arc_*`/`ch_*` 目标) | `arc` |
| `brief` · `commit write\|revise` · `gate write` · `review add --depth light` | `write` |
| `gate approve` | `write\|review` |
| `commit revise_rubric`(蒸馏) | `review` |
| `commit review_deep` · `review add --depth deep` | `review\|ops` |
| `knowledge grant` · `knowledge scope add\|remove` | `write\|review` |
| `knowledge reveal` | `write\|review\|ops` |
| `publish` · `retcon` · `report volume` · `checkpoint` · `gate publish\|checkpoint` | `ops` |

不受辖(只读/记账/清理/引导):`init` `adopt` `status` `fsck` `check` `extract` `query` 类视图(`knowledge query`/`knowledge scope list`/`facts list`/`ledger`)、`tree`/`task`/`entity`/`thread` 登记、`rollup`、`review list`、`court status|close`、`stage *`、`gate next`(advisory——未进入阶段时打提醒而非拒绝)。

## 16. commit 按 task.type 行为表(唯一写路径)

| type | 输入 | 校验(全过才落盘) | 落盘动作 |
|---|---|---|---|
| write | `--chapter`(信封+##正文) `--writeback`(json) | `check --unit` 绿;task.json 存在;writeback schema;**引用越权=拒绝**(cast_actual/delta/thread_ops/power_delta 的实体线索必须已登记,thread 迁移必须合法);hooks_realized.close=true(config 网文默认);payoff_realized ⊆ quota 且章号匹配 | **事务包裹(txn_begin→…→txn_end)**:章 md(status=drafted)+meta.json;实体事件日志追加;**facts 登记**(自 continuity_delta 分配 fact_id 写 ledgers/facts/vol_NN.json);thread 推进日志+state+plant_ch 回填;payoff/timeline/power 台账(带 rev 列);ngram_cache(分层);rollup 重算;git commit |
| revise | 同 write | 同 write;目标章非 published;**thread 迁移按撤销后剩余日志模拟**(本章旧 op 剔除再验) | 章 rev+1;**先撤销后重放(§9)**:实体事件日志/线索推进日志剔除本章旧行,facts 先剪后登,TSV 追加新 rev 行;余同 write |
| design | `--file F ...`(节点 md;**可附带**裁决记录 dec_*.md、新实体卡、transcript) | **两遍制**:第一遍全部文件校验(主文件必需节齐全非空;信封合法;附带文件各按其 kind 校验),任一失败=零落盘;第二遍事务内写入。**`--draft`** 例外:跳过必需节校验,节点以 status=draft 部分落盘(书庭中间态持久化,不算定稿,不触发 stale) | 全部落盘(节点 committed;--draft 时 draft);git 一次提交 |
| revise_design | `--file F ...` + task.evidence 非空 | 同上 + evidence | 落盘;**受影响下游沿 parent 链递归标 stale(卷→弧→章)**;git |
| review_deep | `--file`(review md) | frontmatter 合法 | 落 reviews/;verdict=escalate 时自动开 revise_design 任务 |
| reconcile | `--file`(实体现状节) | 目标实体存在 | entity update;last_reconcile_ch=游标 |
| revise_rubric | `--file`(staged style.md) + task.evidence 非空 | 蒸馏专用轻量路径(workflow §6):staged 文件 kind 必须=style;必需节齐全非空 | style.md 落盘(committed,**rev 自动+1**);**不递归标 stale**(黑名单只约束未来章的 check --unit);git |
| publish | 章号区间 | 连续自 last_published+1;各章 approved;buffer 满足 | status→published;git |
| retcon | `retcon` 命令参数 | old_fact 存在且未被覆盖;decision 文件存在;strategy 枚举 | retcons[] 追加+旧 fact 填 superseded_by;git |
| checkpoint | `checkpoint <vol_NN>` | 卷 committed;`state/reports/vol_NN.md` 存在;exports 三态标注无残留 `[待对账]`;卷内无 planned/drafted/stale 章 | 卷 frontmatter 记 checkpoint_at;下卷 volume.md(缺则实例化)imports 节预填(移交项+未收 must_not_drop 线+终章摘要);git |

git 提交消息:`[t_000231] write(ch_0212): 摘要`。
实现映射:write/revise/design/revise_design/review_deep 走 `commit`;reconcile 走 `entity update`;publish/retcon/checkpoint 各走同名命令;任务仍入队留痕(task add → 执行命令 → task done)。

## 17. check 断言集

**--unit <ch>**:字数 ∈ word_target±15%(任务卡可覆盖);style.md 禁忌命中=0(列出行);连续 3 句同首词;连续 3 段同首 WARN;章内字符级 4-gram 重复率 >2% WARN;末段总结化黑名单(「这一夜注定」「谁也没想到」类);**跨章分层指纹**——12-gram 精确重复(防句级套话,窗口内全量+窗口外归档采样,覆盖全史)WARN + 窗口内单章 8-gram 重合率 >6% WARN(撞梗/桥段自我复用嫌疑,深评抽查);meta.json schema 齐全 + continuity_delta 每条含 fact/entity_ids/spoiler;**引用越权 FAIL**(cast_actual/delta/thread_ops/power_delta 的实体线索未登记、thread 迁移非法——revise 按撤销后状态模拟);**facts 冲突扫描**(新 delta vs 既有未覆盖 facts:同实体同键矛盾或高相似文本 → NEEDS_REVIEW;同文异章 → WARN);**抽取器对账(P2-1 双记账)**——正文实测出场(aliases+实体卡别名命中)vs cast_actual:未申报出场 WARN、幽灵出场 WARN;引号内 ≥2 次未登记新专名 → NEEDS_REVIEW(简报外发明嫌疑);未揭示 spoiler 事实与正文句子高相似 → NEEDS_REVIEW(剧透泄漏候选);**known_by 有限定的事实被明写且在场角色不在有效知情集(个体+fac/loc/item 知情圈展开,v2)→ NEEDS_REVIEW(角色知识越界候选,P4-K——轻评裁定:改暗写/补获知场景后 knowledge grant 或 scope add 入圈/删句)**;hooks_realized.close(route=web 强制,issues 说明降 WARN);payoff_realized ⊆ quota 且 **id 章号 = 本章**。主观项(遮名指认/智商漂移/关键场面占比/爽点有效性/毒点)输出 NEEDS_REVIEW 交评审。支持 `--candidate/--writeback` 对未落盘产物执行。
**--window [--since CH]**:任意 3 章窗口 payoff realized ≥1、10 章窗口处境级(upgrade/reveal/reversal)≥1;promise 线(thread_kind=promise ∧ live)余额 ∈[2,5];promise >15 章无推进;**power 台账近 10 章同实体 ≥3 次变动 WARN**;**故事日历(P2-2)**——elapsed 中文数值化(「2天」「三个时辰」→天数)非负 FAIL、story_date(ISO 或中文日期)按章序单调不倒流 FAIL、`ledger timeline` 视图输出累计天数;buffer 计数与章 status 一致。`--since` 限定窗口扫描起点(长连载增量检查)。台账读取一律 (chapter) 取最新 rev(§9)。
**--leak <候选> --brief <简报>**:候选正文中出现、但简报未投递的**已登记专名**(aliases.json + 实体卡 aliases)→ FAIL(信息沙箱违规);未登记的新发明专名机器无法枚举 → NEEDS_REVIEW 交轻评(pipeline §5)。
**--project**:信封键齐+枚举合法——**按 kind 分级**:内容资产(book/volume/arc/chapter/entity/thread/style/world)查全信封(id/kind/status/rev/updated_at,+parent 除 book);`decision` 查 §11 键集+四节存在+否决案行含 reopen_requires;`review` 查 §12 键集+depth/verdict 枚举+问题清单节;brief 用注释头不查信封。parent 存在;章三件套齐;cast/entity 引用可解析(经 aliases);must_not_drop ∧ dropped 无 decision 引用**或引用的 dec 文件不存在** → FAIL;facts schema + superseded 引用存在;**知情圈台账(v2)**——scopes.json 圈键须为已登记 fac/loc/item、成员须为已登记 char(违者 FAIL),known_by 引用空圈 WARN;published 连续无空洞;必需标题节(§4);queue target 均存在;**半事务检出(P0-3)**——`state/txn/` 有 `done=false` journal → FAIL(上次 commit 中断,先按 §18 恢复)。

## 18. git 纪律

项目内一切写入经 `novel.py commit`;编排者在**每个 worker 子代理返回后**跑 `git status --porcelain`(项目根),非空 → `git checkout -- . && git clean -fd`,任务 note 记违规。中断恢复:reset 未提交内容,task 回 pending。

## 19. 审批点

`approvals.*=true` 的动作(book/volume 定稿、publish、卷末 checkpoint)需用户当轮确认;`unattended=true` 降级为执行+`note: pending_human_review` 留痕。

## 20. skill 侧目录与所有权(实施期)

```
novel-orchestrator/
  SKILL.md README.md          # L0 入口(薄路由 ≤20KB)/ 人类快速开始
  modes/                      # 三模式:mode-orchestrated / mode-solo / route-traditional
                              # + capability-profiles(宿主能力四档与降级矩阵)
  protocol/workflow.md        # L1 主循环总装图(环节×闸门×角色×判据+交接契约+三覆盖表)
  protocol/formats.md         # 本文件(机器契约 SSOT)
  protocol/knowledge-orchestration.md   # 阶段×知识装载 SSOT(11 阶段目录+硬规则+对账契约)
  protocol/stages/            # 11 个阶段配套知识包(薄路由:必读/K 池/禁读/退出判据)
  protocol/court.md pipeline.md serial-ops.md glossary.md
  protocol/manual-check.md    # 无 shell 环境人工自查清单(可判项 vs 丢失能力,诚实降级)
  protocol/adopt.md           # 存量文稿/半途项目收编协议
  tools/novel.py(薄壳入口) tools/novel_lib/(按工作流关切拆分的实现包) tools/README.md tools/tests/
  templates/                  # init/tree add 母版(清单见下)
  roles/                      # 12 角色卡(含 extractor 抽取器——CLI 对账的帽子/加强抽查版)
  rubrics/                    # 11 张判据卡(自包含 ≤120 行/张;每卡唯一所有阶段,见 knowledge-map §卡表)
  personas/                   # 9 张读者人设卡(所有权=s1;7 张网文/短篇 + 2 张传统路线文学口味)
  rhythm/                     # 5 节奏模板(所有权=s4;含结构评审检查单)
  knowledge/ knowledge-blocks.md   # 深读原文 + K-ID 锚点解析(无全库索引;进入只经所属阶段包)
  knowledge-map.md            # 全资产所有权台账(111 块+卡/人设/节奏,每资产唯一所有阶段) + 防膨胀规则
```

(历史注:v1 前身 `novel-writing-workflow` 与其只读存档 `legacy/` 已随技术债清理移除;
v1→v2 术语与资产映射保留在 `protocol/glossary.md` §2,供迁移旧项目时查阅。)

**templates/ 清单(A2)**:`config.json` `book.md` `style.md` `world.md` `volume.md` `arc.md` `chapter.md` `chapter.task.json` `chapter.meta.json` `entity-char.md` `entity-item.md` `entity-loc.md` `entity-fac.md` `thread.md` `decision.md` `review.md` `README.md`(清单+init 映射)。模板占位一律 `[方括号]`;frontmatter 合法可解析(占位不破坏解析)。

---

*rev 7 · 2026-08-25 · P8 批次:知识矩阵 v2——known_by 范围条目(fac/loc/item)与知情圈 entities/scopes.json(§1/§9)/knowledge scope CLI 与辖区行(§15)/check 越界扫描按知情圈展开+scopes 台账断言(§17);知识资产所有权对齐(§20 目录注释);novel.py 拆分为 novel_lib/ 包(入口不变)。*
*rev 6 · 2026-08-25 · P7-S 阶段强制闸门:state/stage.json 持久化(§1/§14)/stage enter·current 语义改版(§15)/阶段闸门辖区表(§15)/init 下一步指向 stage enter s1。*
*rev 5 · 2026-08-25 · P6-S 阶段×知识编排:stage CLI 与 gate next 阶段推断/欠账项(§15)/config 增 spoiler_debt_chapters(§13)/目录补 knowledge-orchestration.md 与 stages/(§20)。*
*rev 4 · 2026-08-25 · P4 批次:知识矩阵 known_by/revealed_reader_ch 与 knowledge CLI(§5/§9/§15/§17)/gate FAIL 附「下一步」修复命令(§15)/rollup 手动重算命令(§15)/revise_rubric 蒸馏任务类型与 commit 行(§10/§16)/新增 protocol/workflow.md 主循环总装图与 roles/extractor.md(§20)。*
*rev 3 · 2026-08-24 · 内核重构对齐:台账 (chapter,rev) 语义与撤销重放(§9/§16)/回执收紧与 review CLI(§12)/原子提交 state/txn 与半事务检出(§14/§17)/简报条目级预算+声纹速查+rollup 记忆分层(§6)/抽取器对账与故事日历入 check(§17)/分层指纹(§14)/gate·court·facts·extract CLI(§15)。*
*rev 2 · 2026-08-24 · 落地增补:facts 生产环/越权机检/线索状态机表/retcon·report·checkpoint·adopt CLI/两级 ngram/power·recap 台账/队列自动化/state.court 与 --draft/decision·review 机检;删除 models 死键与 legacy 引用。*
