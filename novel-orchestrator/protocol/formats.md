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
  entities/{char|item|loc|fac}_{slug}.md   entities/aliases.json
  threads/thread_{slug}.md
  ledgers/timeline.tsv  payoff.tsv  power.tsv  facts/vol_01.json  lessons.md  recap.md
  court/dec_001_{slug}.md   court/transcripts/*.md
  reviews/ch_0001.light.md  ch_0001.deep.md
  data/feedback/            # 读者反馈收件箱(自由格式)
  data/compliance/          # 平台合规材料:敏感词表/审核规范/申诉记录(自由格式,
                            # safety-auditor 与发布前自查按需读取,编排者只读)
  tasks/queue.json  tasks/archive.json      # archive = task archive 归档的 done 任务
  state/index.json  dashboard.md  ngram_cache.json   # 生成物,禁止手改
  state/reports/vol_NN.md   # 卷报告(report volume 生成;唯一可编辑处=对账三态标注)
  state/court/              # 庭审中间态工作区(R0 简报/R1 提案/R2 评审/R3 主编稿,
                            # 按场次建子目录;中断恢复用,永不入简报召回,checkpoint 后可清)
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
| chapter | `planned → drafted → approved → published`;另 `stale / archived` | drafted=写手落盘;approved=轻评 pass+check 绿;published=不可变 |
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
{"summary_after":"3–8句","continuity_delta":[{"fact":"…","entity_ids":["char_a"],"spoiler":0,"key":"持有"}],
 "time_advance":{"elapsed":"2天","story_date":""},
 "thread_ops":[{"id":"thread_x","op":"advance","note":"…"}],
 "payoff_realized":["payoff_0212_1"],"hooks_realized":{"open":true,"close":true},
 "cast_actual":["char_a"],
 "power_delta":[{"entity_ids":["char_a"],"from":"炼气三层","to":"炼气四层","note":"…"}],
 "issues":[],"word_count":3120}
```

`payoff_*.kind` 枚举:`dopamine|upgrade|reveal|reversal|emotion|humor|other`。`thread op` 枚举:`plant|advance|payoff|tangle|ready`。
可选键:`continuity_delta[].key`(实体状态键位,如 位置/持有/知晓——填了可让 facts 冲突扫描精确到同键矛盾);`power_delta`(战力/位阶变化时必填,commit 追加 `ledgers/power.tsv`)。
**越权纪律**:`cast_actual`/`continuity_delta`/`thread_ops`/`power_delta` 引用的实体与线索必须已登记(entities/aliases/threads),否则 `check --unit` FAIL、commit 拒绝落盘——写手不得发明实体,缺卡走 issues。`continuity_delta` 每条必含 fact/entity_ids/spoiler。

## 6. 简报 briefs/ch_NNNN.brief.md(`novel.py brief` 生成)

frontmatter:`id: brief_ch_0212`, `kind: review` 除外——用 `kind: brief` 不入信封枚举?**裁决**:brief 无信封,首节前仅三行注释(chapter / brief_rev / compiled_at / budget_chars 以 HTML 注释行 `<!-- key: value -->` 写)。
固定十节:

```
## 0 任务卡            (task.json 渲染)
## 1 文风与禁忌        (style.md 摘录 + 范文锚)
## 2 直接上文          (前章尾 500 字原文 + 前 3 章 summary_after)
## 3 出场实体状态卡    (cast 对应实体卡的 设定要点+现状+最近3条事件)
## 4 活跃线索          (active ∩ 本卷 或 payoff_planned 命中;spoiler>0 项前缀【读者未知,只可潜台词】)
## 5 弧内位置          (弧因果链位置 + 前后章一句话目标)
## 6 相关事实与设定    (facts 实体键查,superseded 者连带 retcon;world.md 相关规则条目)
## 7 写作提示          (≤60 行;按主导内容类型选配)
## 8 回写契约          (meta.json schema 原文 + 提交格式说明)
## 附 溯源             (表:资产|rev|用途——本简报引用的每个文件)
```

预算:超 `brief_budget_chars` 时按 7→6→4→3 顺序裁剪并在溯源节留痕(第 3 节为末位:只裁实体卡「设定要点」,保留现状与最近事件)。已存在则 `brief_rev+1` 重写(git 保历史)。
第 2 节尾部注入 `ledgers/recap.md` 尾 12 行(存在且非空时);第 4 节召回=任务卡 threads ∪ live 态线中(must_not_drop ∪ volume_scope 含本卷 ∪ payoff_planned 命中本卷或 ≤15 章内,后者加【payoff 临近】标记);第 7 节按 `config.route` 切换 web/traditional 提示组。

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

- `ledgers/timeline.tsv`:`chapter	story_date	elapsed	note`
- `ledgers/payoff.tsv`:`chapter	payoff_id	kind	intent	realized`(0/1)
- `ledgers/power.tsv`:`chapter	entity	from	to	note`(commit 自 writeback 可选 `power_delta` 追加;`check --window` 对近 10 章同实体 ≥3 次变动告警;设定审计/深评按 rubrics/power.md 对账卷预算)
- `ledgers/facts/vol_NN.json`(**commit 自动登记**:自 continuity_delta 分配全局递增 `fact_id` 写入本章所属卷文件,同文同章去重;`key` 可选,继承自 delta):

```json
{"facts":[{"id":"fact_0001","fact":"…","entity_ids":["char_a"],"revealed_ch":212,"spoiler":0,"superseded_by":null,"key":"持有"}],
 "retcons":[{"id":"ret_001","entity_ids":[],"old_fact_id":"fact_0001","new_fact":"…",
             "strategy":"reconcile|fade_out|explicit_fix","decision_ref":"dec_00x"}]}
```

- `ledgers/lessons.md`:`- [ch_0212|vol_02|book] 教训一句话(来源 review id)`——例外:本台账由**编排者**经 commit 附笔追加(格式固定),非 novel.py 生成
- `ledgers/recap.md`:全局梗概,**编排者维护**(卷末 checkpoint 必更,期间每 ~10 章可追加一段,每段 3–6 行);`novel.py brief` 注入尾 12 行进 §2——长程记忆的轻量层,与 summary_after 链/实体卡互补

纪律:retcon 经 `novel.py retcon` 落盘(校验 old_fact 存在未覆盖 + decision 存在),旧 fact 填 `superseded_by`;简报第 6 节命中此类 fact 必须连带 retcon 条目。

## 10. 任务队列 tasks/queue.json

```json
{"next_seq":232,"tasks":[
 {"id":"t_000231","type":"design","target":"vol_04","state":"pending",
  "blocked_on":[],"attempts":0,"note":"","evidence":"","created_at":"…","updated_at":"…"}]}
```

`type` 枚举:`design | revise_design | write | revise | review_deep | publish | retcon | checkpoint | reconcile`。
`state` 枚举:`pending | blocked | running | done | failed`。
纪律:`write/revise` 同 target `attempts ≥ 2` 再 fail → novel.py 自动追加一条 `revise_design` 任务(升级);`revise_design` 创建须带 `--evidence`,novel.py 提示比对 court/ 否决案。
队列自动化:`blocked` 任务在 `blocked_on` 全部 done 后由任意 task/status 命令自动解锁 → `pending`;`task reset <id>` 将 failed/running 拉回 pending(done 不可 reset,负例拒绝);`task archive [--keep N]` 把多余 done 任务移入 `tasks/archive.json` 防队列膨胀。

## 11. 裁决记录 court/dec_NNN_{slug}.md

frontmatter:`id`, `kind: decision`, `node`(目标节点), `session: S1|S2|S3|S4|volume|arc|adhoc`, `date`, `status: active`。
节:`## 选项`(`- 案id | 提案角色 | 一句话`);`## 裁决`(选择+理由);`## 否决案`(`- 案id | 否决理由 | reopen_requires: 重开所需新证据`);`## 异议`(`- 角色 | 意见 | resolution: disagree_and_commit|adopted`)。
transcripts 归档 `court/transcripts/`,**永不进入简报召回**。

## 12. 评审 reviews/ch_NNNN.{light|deep}.md

frontmatter:`id`, `kind: review`, `chapter`, `depth: light|deep`, `verdict: pass|revise|escalate`, `rev_reviewed`(章 rev), `date`。
节:`## 问题清单`(`- [定位≤20字] 问题 → 建议`,revise 时每条须可执行);`## 教训`(可选,编排者摘入 lessons)。
落盘规则:deep 必落盘(commit type=review_deep);light 默认不落盘(结论记任务 note),verdict=revise|escalate 或需存证时按 review_deep 行为落盘、frontmatter `depth: light`。

## 13. config.json(init 默认)

```json
{"preset":"standard","route":"web","word_target":[2000,4500],
 "buffer":{"target":3,"min_before_publish":1},
 "critic":{"light_every":1,"deep_every":5},
 "approvals":{"book_commit":true,"volume_commit":true,"publish":true,"checkpoint":true},
 "unattended":false,"reconcile_every":10,"brief_budget_chars":24000,
 "volume_defaults":{"arcs":[5,12],"chapters":[80,250]},
 "ngram_window_chapters":30}
```

`route ∈ {web, traditional}`:traditional 差分(无 buffer/publish、章尾钩与爽点窗口降级、简报 §7 提示切换)见 `modes/route-traditional.md`;`check`/`brief` 按此键自动切换。(历史注:早期草案含 `models` 键为各角色预留模型档位,从未被读取,已删除;角色模型选择属产品层配置,不入项目 config。)

## 14. 生成物(禁手改;标注例外除外)

- `state/index.json`:`{generated_at, nodes[], chapters[], entities[], threads[], tasks:{pending,blocked,head}, cursor:{last_published,last_drafted,last_approved}, last_deep_review_ch, warnings[]}`(nodes 含 id/kind/status/rev/parent/path;chapters 含 id/status/rev/parent/mtime——mtime 用于 `status` 的章级增量重算,未变更章直接复用旧条目)
- `state/dashboard.md` 段落:项目一行(含深评游标与逾期提醒)· 树进度表(卷|状态|弧|章数)· 树节点 · 章按状态 · 队列头 5 条 · 告警(check --window 摘要)· 最近 3 次 git commit
- `state/ngram_cache.json`:`{"ch_0210": {"n12": […], "n8": […]}}` 两级指纹,保留最近 `ngram_window_chapters` 章,commit 更新(旧版扁平数组格式读取时视为 n12,兼容)
- `state/reports/vol_NN.md`:`report volume` 生成;**例外**——「exports 对账」节的三态标注(`[待对账]` → `[兑现 ch_NNNN]|[移交]|[废止 dec_xxx]`)由编排者手工编辑,checkpoint 机检
- `state/court/`:庭审中间态工作区(非生成物,编排者按场次存 R0–R4 中间产物;见 court.md §3)

## 15. novel.py CLI(退出码:0=通过 / 1=校验失败 / 2=用法或环境错误)

```
novel.py init <dir> [--name X]            # 脚手架+git init+首 commit
novel.py status                           # 重算 index+dashboard(章级增量),打印 dashboard、深评逾期提醒与可恢复断点
novel.py tree add <kind> <id> [--parent P]   # 由模板实例化空壳节点(volume|arc|chapter)
novel.py tree show [id]
novel.py tree set-status <id> <status> [--evidence E]
                                          # 含迁移合法性校验;chapter→approved 需评审 pass 回执
                                          # (reviews/ 文件、任务 note 含 light=pass、或 --evidence)
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
novel.py fsck                             # = check --project
```

reconcile 汇总仍按 serial-ops §5 由编排者执行(`entity due` + `entity update` 已覆盖机械部分)。`status` 重算 index/dashboard;其余命令按需读取。项目根定位:cwd 向上探测或 `--root`。实现覆盖表与差异细节见 `tools/README.md`。

## 16. commit 按 task.type 行为表(唯一写路径)

| type | 输入 | 校验(全过才落盘) | 落盘动作 |
|---|---|---|---|
| write | `--chapter`(信封+##正文) `--writeback`(json) | `check --unit` 绿;task.json 存在;writeback schema;**引用越权=拒绝**(cast_actual/delta/thread_ops/power_delta 的实体线索必须已登记,thread 迁移必须合法);hooks_realized.close=true(config 网文默认);payoff_realized ⊆ quota 且章号匹配 | 章 md(status=drafted)+meta.json;实体事件日志追加;**facts 登记**(自 continuity_delta 分配 fact_id 写 ledgers/facts/vol_NN.json);thread 推进日志+state+plant_ch 回填;payoff/timeline/power 台账;ngram_cache(两级);git commit |
| revise | 同 write | 同 write;目标章非 published | 章 rev+1,余同(facts 同文同章去重,不重复登记) |
| design | `--file F ...`(节点 md;**可附带**裁决记录 dec_*.md、新实体卡、transcript) | 主文件必需节齐全非空;信封合法;附带文件各按其 kind 校验。**`--draft`** 例外:跳过必需节校验,节点以 status=draft 部分落盘(书庭中间态持久化,不算定稿,不触发 stale) | 全部落盘(节点 committed;--draft 时 draft);git 一次提交 |
| revise_design | `--file F ...` + task.evidence 非空 | 同上 + evidence | 落盘;**受影响下游沿 parent 链递归标 stale(卷→弧→章)**;git |
| review_deep | `--file`(review md) | frontmatter 合法 | 落 reviews/;verdict=escalate 时自动开 revise_design 任务 |
| reconcile | `--file`(实体现状节) | 目标实体存在 | entity update;last_reconcile_ch=游标 |
| publish | 章号区间 | 连续自 last_published+1;各章 approved;buffer 满足 | status→published;git |
| retcon | `retcon` 命令参数 | old_fact 存在且未被覆盖;decision 文件存在;strategy 枚举 | retcons[] 追加+旧 fact 填 superseded_by;git |
| checkpoint | `checkpoint <vol_NN>` | 卷 committed;`state/reports/vol_NN.md` 存在;exports 三态标注无残留 `[待对账]`;卷内无 planned/drafted/stale 章 | 卷 frontmatter 记 checkpoint_at;下卷 volume.md(缺则实例化)imports 节预填(移交项+未收 must_not_drop 线+终章摘要);git |

git 提交消息:`[t_000231] write(ch_0212): 摘要`。
实现映射:write/revise/design/revise_design/review_deep 走 `commit`;reconcile 走 `entity update`;publish/retcon/checkpoint 各走同名命令;任务仍入队留痕(task add → 执行命令 → task done)。

## 17. check 断言集

**--unit <ch>**:字数 ∈ word_target±15%(任务卡可覆盖);style.md 禁忌命中=0(列出行);连续 3 句同首词;连续 3 段同首 WARN;章内字符级 4-gram 重复率 >2% WARN;末段总结化黑名单(「这一夜注定」「谁也没想到」类);**跨章两级指纹**——12-gram 精确重复(防句级套话)WARN + 单章 8-gram 重合率 >6% WARN(撞梗/桥段自我复用嫌疑,深评抽查);meta.json schema 齐全 + continuity_delta 每条含 fact/entity_ids/spoiler;**引用越权 FAIL**(cast_actual/delta/thread_ops/power_delta 的实体线索未登记、thread 迁移非法);**facts 冲突扫描**(新 delta vs 既有未覆盖 facts:同实体同键矛盾或高相似文本 → NEEDS_REVIEW;同文异章 → WARN);hooks_realized.close(route=web 强制,issues 说明降 WARN);payoff_realized ⊆ quota 且 **id 章号 = 本章**。主观项(遮名指认/智商漂移/关键场面占比/爽点有效性/毒点)输出 NEEDS_REVIEW 交评审。支持 `--candidate/--writeback` 对未落盘产物执行。
**--window [--since CH]**:任意 3 章窗口 payoff realized ≥1、10 章窗口处境级(upgrade/reveal/reversal)≥1;promise 线(thread_kind=promise ∧ live)余额 ∈[2,5];promise >15 章无推进;**power 台账近 10 章同实体 ≥3 次变动 WARN**;timeline elapsed 非负;buffer 计数与章 status 一致。`--since` 限定窗口扫描起点(长连载增量检查)。
**--leak <候选> --brief <简报>**:候选正文中出现、但简报未投递的**已登记专名**(aliases.json + 实体卡 aliases)→ FAIL(信息沙箱违规);未登记的新发明专名机器无法枚举 → NEEDS_REVIEW 交轻评(pipeline §5)。
**--project**:信封键齐+枚举合法——**按 kind 分级**:内容资产(book/volume/arc/chapter/entity/thread/style/world)查全信封(id/kind/status/rev/updated_at,+parent 除 book);`decision` 查 §11 键集+四节存在+否决案行含 reopen_requires;`review` 查 §12 键集+depth/verdict 枚举+问题清单节;brief 用注释头不查信封。parent 存在;章三件套齐;cast/entity 引用可解析(经 aliases);must_not_drop ∧ dropped 无 decision 引用**或引用的 dec 文件不存在** → FAIL;facts schema + superseded 引用存在;published 连续无空洞;必需标题节(§4);queue target 均存在。

## 18. git 纪律

项目内一切写入经 `novel.py commit`;编排者在**每个 worker 子代理返回后**跑 `git status --porcelain`(项目根),非空 → `git checkout -- . && git clean -fd`,任务 note 记违规。中断恢复:reset 未提交内容,task 回 pending。

## 19. 审批点

`approvals.*=true` 的动作(book/volume 定稿、publish、卷末 checkpoint)需用户当轮确认;`unattended=true` 降级为执行+`note: pending_human_review` 留痕。

## 20. skill 侧目录与所有权(实施期)

```
novel-orchestrator/
  SKILL.md README.md          # L0 入口(薄路由 ≤20KB)/ 人类快速开始
  modes/                      # 三模式:mode-orchestrated / mode-solo / route-traditional
  protocol/formats.md         # 本文件(机器契约 SSOT)
  protocol/court.md pipeline.md serial-ops.md glossary.md
  protocol/manual-check.md    # 无 shell 环境人工自查清单(可判项 vs 丢失能力,诚实降级)
  protocol/adopt.md           # 存量文稿/半途项目收编协议
  tools/novel.py tools/README.md tools/tests/
  templates/                  # init/tree add 母版(清单见下)
  roles/                      # 11 角色卡
  rubrics/                    # 8 张共享判据卡(自包含 ≤120 行/张)
  personas/                   # 7 张读者人设卡
  rhythm/                     # 5 节奏模板(含结构评审检查单)
  knowledge/ knowledge-blocks.md knowledge-index.md   # 深读图书馆(经 knowledge-map 进入)
  knowledge-map.md            # 111 块归属 + 防膨胀规则
```

(历史注:v1 前身 `novel-writing-workflow` 与其只读存档 `legacy/` 已随技术债清理移除;
v1→v2 术语与资产映射保留在 `protocol/glossary.md` §2,供迁移旧项目时查阅。)

**templates/ 清单(A2)**:`config.json` `book.md` `style.md` `world.md` `volume.md` `arc.md` `chapter.md` `chapter.task.json` `chapter.meta.json` `entity-char.md` `entity-item.md` `entity-loc.md` `entity-fac.md` `thread.md` `decision.md` `review.md` `README.md`(清单+init 映射)。模板占位一律 `[方括号]`;frontmatter 合法可解析(占位不破坏解析)。

---

*rev 2 · 2026-08-24 · 落地增补:facts 生产环/越权机检/线索状态机表/retcon·report·checkpoint·adopt CLI/两级 ngram/power·recap 台账/队列自动化/state.court 与 --draft/decision·review 机检;删除 models 死键与 legacy 引用。*
