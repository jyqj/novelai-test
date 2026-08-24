# pipeline.md — 写作产线协议(Phase B · 编排者操作手册)

> 依据 spec §5;格式与 CLI 以 `protocol/formats.md`(F§n)为准。角色文件在 roles/,判据在 rubrics/。
> 不变量:worker 只返回文本;项目内一切写入经 `novel.py commit`(附笔纪律见 court.md §3);**任何 worker spawn 前工作区必须干净**。

## 0. 冷启动与会话纪律

- 冷启动三步:`novel.py status`(读 dashboard)→ `novel.py task next` → 按本文时序干活。
- 每编排者会话处理 **≤8–10 个任务**(约 3–5 章)后轮换新会话;队列即记忆,零交接成本。轮换前把在跑任务收敛到可恢复点(commit 或 task note 记临时文件路径)。
- worker 双产出与中间稿一律存**项目外**临时目录(如 `$TMPDIR/novel/<task_id>/`),防 git 污染;路径记入 task note 便于中断恢复。

## 1. 全链时序(单章 write 任务)

```
0 排批(每批 1–3 章;从弧计划「章分配草案」逐行取料):
    novel.py tree add chapter ch_NNNN --parent arc_NN_n     # 实例化章三件套骨架(F§5)
    编排者补全 ch_NNNN.task.json 的 goal/beats(3–6 拍)/hook(close 必填)/payoff_quota/threads/cast
      ——编排者唯一内容性动作;quality 档可委派架构师出草案(附录 T0),编排者仍负定稿
    novel.py task add write ch_NNNN
    排批参考: novel.py ledger payoff|promise|timeline(窗口欠账)、novel.py check --window(告警)
1 novel.py task start <t>  ;  novel.py brief ch_NNNN        # 机械装配十节+溯源(F§6)
2 资料员审包: spawn T1 → 返回补漏/裁剪指令清单(资料员只读,不改文件)
3 落简报: 编排者按指令修订 briefs/ch_NNNN.brief.md(溯源节追加一行 librarian_patch 摘要);
    确保基线干净后再进 4(§5 注)
4 写手: spawn T2(只附简报这一个文件)→ 返回 正文 + writeback JSON 双产出
5 提取: 双产出分存 <tmp>/ch_NNNN.md(信封+## 正文,F§5)与 <tmp>/ch_NNNN.writeback.json
6 机检: novel.py check --unit ch_NNNN --candidate <tmp章> --writeback <tmp json>
    # 对未落盘候选执行 staging 机检(novel.py 已支持);NEEDS_REVIEW 项转 7 轻评裁定
    不绿 → 输出并入 §2 修订循环(计一次修订)
7 轻评: spawn T3(附:简报+候选正文+前章尾 500 字+后章任务卡+rubrics)→ verdict(F§12):
    pass     → 8
    revise   → §2 修订循环
    escalate → §3 升级
8 提交: novel.py commit <t> --chapter <tmp章> --writeback <tmp json> -m "摘要"   # → drafted(F§16)
    novel.py task done <t> --note "light=pass; <轻评要点一行>"   # 回执先落 note
    novel.py tree set-status ch_NNNN approved       # 轻评 pass + check 绿(F§3)
      # CLI 校验回执(P1-5):reviews/ 有 verdict=pass、或任务 note 含 light=pass、
      # 或 --evidence "<回执>";三者皆无 → 拒绝置 approved
9 深评采样(§4) → lessons 摘录(§4)
※ 每个 worker 返回后先执行 §5 泄漏检查,再处理其产出。
```

## 2. 修订循环(轻评 revise / 机检不绿)

```
n = 0
while verdict == revise and n < 2:
    n += 1
    spawn 写手(T2 修订变体): 附 原简报 + 自稿(临时) + 问题清单(轻评 patch 清单/机检输出)
    → 新双产出 → 重跑 §1 步骤 5–7
if 仍 revise:
    novel.py task fail <t> --note "轻评未过×2: <问题要点>"
    # F§10: write/revise 同 target attempts 达限后,novel.py 自动追加 revise_design 任务(升级)
```

- 已 commit 章的返修(深评/反馈发起):`novel.py task add revise ch_NNNN --note "<来源 review id>"`,走同一链路;commit 走 revise 行(章 rev+1,F§16)。**published 章不可 revise**——走 serial-ops.md §3 retcon。

## 3. escalate 升级(开设计修订任务)

轻评/深评 verdict=escalate,或修订两轮后问题明确指向设计层(弧计划/卷蓝图/设定):

```
novel.py task add revise_design <设计节点> --evidence "<章号+症状+review 引用>"
novel.py task fail <t> --note "escalate → 见 revise_design"      # 本章挂起,等设计修订
```

- `--evidence` 必填,且先过否决案台账(court.md §4);
- 深评报告经 commit 落盘时若 verdict=escalate,novel.py 自动开 revise_design 任务(F§16 review_deep 行),编排者只需补 evidence 细节与影响面报告。

## 4. 深评采样与 lessons 摘录

触发:每 `critic.deep_every` 章(F§13)+ **弧末章** + **卷末**(卷级变体见 serial-ops.md §4)。

```
novel.py task add review_deep ch_NNNN
spawn T4 → 完整 review 文本(F§12,frontmatter depth: deep)存 <tmp>
附笔: 从报告「## 教训」摘一行,按 F§9 格式追加 ledgers/lessons.md(commit 前一刻写入,同事务入库)
novel.py commit <t> --file <tmp review>  ;  novel.py task done <t>
# verdict=escalate → novel.py 自动开 revise_design(F§16);verdict=revise → §2 返修任务
```

- 轻评报告默认**不单独落盘**:pass 记 task note;revise/escalate 的问题清单作为修订/升级输入即可。确需存证时,按 F§12 格式(depth: light)另开 review_deep 任务落盘 reviews/。

## 5. 泄漏检查(每个 worker 返回后,强制)

F§18 原文:

> 项目内一切写入经 `novel.py commit`;编排者在**每个 worker 子代理返回后**跑 `git status --porcelain`(项目根),非空 → `git checkout -- . && git clean -fd`,任务 note 记违规。中断恢复:reset 未提交内容,task 回 pending。

操作步骤:

```
1 worker 返回 → 项目根执行: git status --porcelain
2 输出非空 → git checkout -- . && git clean -fd
    task note 追记「违规: <角色>/<任务>/<文件清单>」;worker 产出仍以最终回复文本为准(未丢失)
3 输出为空 → 继续处理产出
4 写手产出另跑机械泄漏扫描: novel.py check --leak <tmp章> --brief briefs/ch_NNNN.brief.md
    # 已登记专名(aliases/实体卡)出现在正文但简报未投递 → FAIL,产物作废重 spawn(F§17);
    # 新发明专名机器无法枚举,仍靠轻评对照简报人工抽查(本条的主观半边)
中断恢复: 同款清理未提交内容;任务回 pending 重跑(临时文件按 task note 路径找回,找不到则整任务重跑)
```

注:检查有效的前提是 **spawn 时基线干净**——编排者附笔只在 commit 前一刻写;`novel.py brief` 若留下未提交改动(其 git 语义未在 F§15 定义),spawn 写手前先以 `git add`+`git commit`(message `[<t>] brief(ch_NNNN): 编译+补漏`)入库留痕。

## 6. 成本档位落地表(config.preset,F§13)

| 环节 | economy | standard(默认) | quality |
|---|---|---|---|
| 排批 beats/hook | 编排者亲笔 | 编排者亲笔 | 可委派架构师草案(T0,1 次/批) |
| 资料员审包(§1 步骤 2) | 抽样:新实体章/跨弧首章/对账后首章 | 每章 | 每章 |
| 轻评 | 隔章(light_every=2;跳过章仅机检) | 每章(light_every=1) | 每章 |
| 深评 | 仅弧末+卷末 | deep_every=5 + 弧末/卷末 | deep_every=3 + 弧末/卷末 |
| 读者抽检 | 无 | 无 | 深评时并行 1 次人设卡抽检票 |
| 修订态度 | 一轮未过即倾向 fail 升级 | ≤2 轮(F§10 上限) | ≤2 轮,预算容忍双轮 |

## 7. 附录:spawn prompt 模板

通用尾注(每模板必含):**产出只放最终回复;禁止写入任何文件、禁止执行任何写命令。**(资料员可只读仓库;写手只见简报;评审只见附件。)
路径约定:`<skill根>` = 本 skill 在当前产品中的实际安装路径(spawn 时由编排者填充)。

**T0 排批委派(quality 档)**
```
你是架构师,担任排批助理。先读:<skill根>/roles/architect.md
附件:arc_NN_n.md、本批前一批各章 task.json(衔接)、payoff/promise 窗口摘要。
任务:为 ch_A..ch_B 逐章草拟 task.json 内容——goal/beats(3–6 拍)/hook(close 必填)/payoff_quota/threads/cast,
schema 与枚举以附件样例为准(formats.md §5)。
产出:每章一个 JSON 块,不加解释。 [通用尾注]
```

**T1 资料员(简报审包)**
```
你是资料员,唯一有仓库检索权的 worker(只读)。先读:roles/librarian.md
附件:ch_NNNN.task.json、briefs/ch_NNNN.brief.md(当前版)。
任务:对照任务卡审包——cast 各卡现状是否最新(读 entities/ 与事件日志核对)、活跃线索与相关事实
是否漏配、retcon 是否连带、超预算时可裁哪节(裁剪顺序 7→6→4,formats.md §6)。
产出:指令清单,每条=【补|裁|改】+ 目标节 + 内容/理由;无问题则回「PASS」。 [通用尾注]
```

**T2 写手(初写;[]为修订变体追加)**
```
你是写手。先读:roles/writer.md(文风纪律+负面清单)
附件:briefs/ch_NNNN.brief.md ——这是你唯一的世界,不得读其他任何文件。
[修订变体追加附件:自稿 <tmp>、问题清单 <tmp>;只修清单所列各条,不得顺手重写他处。]
任务:按简报 §0 任务卡写正文(word_target 区间内;hook.close 必须落实;beats 全覆盖)。
产出(最终回复,两段):【正文】…;【writeback】一个 JSON 块,schema=简报 §8 回写契约。 [通用尾注]
```

**T3 轻评 critic-light**
```
你是轻评。先读:roles/critic-light.md(建议与写手异族模型)
附件:简报、候选正文 <tmp>、前章尾 500 字、后章 task.json(若已排批)、
rubrics/prose-disease.md、voice.md、payoff.md。
任务:判 钩子力度/爽点兑现/人设声纹/前后衔接/概述病;对照简报分辨「写手错」还是「包错」
(包错在该条前标 brief_issue,编排者据此修包而非逼写手)。
产出:首行 verdict: pass|revise|escalate;随后问题清单,每条=- [定位≤20字] 问题 → 可执行建议(formats.md §12)。 [通用尾注]
```

**T4 深评 critic-deep**
```
你是深评。先读:roles/critic-deep.md
附件:采样窗各章正文与 meta 摘要、arc_NN_n.md、volume.md、active threads、
ledger payoff|promise|power 统计输出、rubrics/structure.md、payoff.md、
anti-plagiarism.md、**power.md(必附:战力预算与越阶配额对账)**。
任务:方向偏航(本窗价值走向 vs 弧/卷计划)/期待账户余额/伏笔健康(threads 逐线过)/
战力账本(power 台账 vs 卷预算与锚定表)/跨章重复与撞梗风险;给出 verdict 与问题清单。
产出:一份完整 review 文件文本(formats.md §12:frontmatter depth: deep + 问题清单 + ## 教训 节,
教训至少一条或写「无」)。 [通用尾注]
```

---

*rev 2 · 2026-08-24 · 步骤 8 回执顺序对齐 P1-5;泄漏检查补 check --leak 机械半边;T4 必附 power 卡;spawn 路径去硬编码。*
