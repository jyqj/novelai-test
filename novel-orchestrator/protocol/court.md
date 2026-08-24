# court.md — 设计庭运行协议(Phase A · 编排者操作手册)

> 依据 spec §4;文件格式与 CLI 一律以 `protocol/formats.md`(下记 F§n)为准,本文零重复、只指针。
> 通则:worker 只返回文本,唯一写者=编排者;**每个 worker 返回后立即执行泄漏检查**(pipeline.md §5,F§18)。

## 1. 庭型总表

| 庭型 | 触发 | 场次与议题 | 产出 | 预算/场 |
|---|---|---|---|---|
| **书庭** | 开新书(`novel.py init <dir> [--name X]` 之后) | S1 主旨/高概念/题材定位 · S2 世界观核心/金手指/力量体系(**先于大纲**) · S3 主线电缆/人物主阵容/反派梯队 · S4 分卷草案+卷1蓝图 | tree/book.md + world.md + style.md + vol_01/volume.md + dec_*×4 | ≤6 次 agent 运行 |
| **卷庭** | 卷 N 末 checkpoint 完成(serial-ops.md §4) | 一场:卷蓝图九节(F§4) | vol_{N+1}/volume.md + dec_* | ≤5 |
| **弧简流程** | 写作游标距弧前沿 ≤1 弧 | 不开庭:架构师 1 提案 → 结构评审+1 读者合并评审 → 主编合成 | arc_NN_n.md 六节(F§4)+ dec_*(session: arc) | ≤3 |

预算口径:计 agent 运行总次数,**含 R4**;基线阵容未满上限的场预留 1 次给 R4;基线已满的场(S1/卷庭/弧)不设 R4,blocking 直接走 §4 超限处置。

## 2. 每场规格表

| 场 | 阵容(R1 提案 / R2 评审;主编×1 另计) | 编排者投递(设计简报构成,R0) | 产出物(树节点+裁决记录) | 运行数 |
|---|---|---|---|---|
| S1 | 架构师×2(stance:市场派/概念派)/ 读者×2(异人设卡)+ 安全×1 | 用户想法与硬约束;目标平台与题材市场输入;personas 七卡概览(选卡依据);rubrics/redline.md、toxicity.md | book.md「主旨与主控思想/高概念与题材定位」素材 + dec_001(session: S1) | 6(无 R4) |
| S2 | 架构师×2(stance:体系派/代价派)/ 设定×1 + 读者×1 | S1 暂存稿+dec_001;金手指与体系诉求;rubrics/power.md;world.md 必需节结构(F§4) | world.md 四节 + book.md「世界观核心/金手指与力量体系」素材 + dec_002 | 5 + R4 预留 |
| S3 | 架构师×2(stance:人物派/冲突派)/「结构+设定」合并×1 + 读者×1 | S1–S2 暂存稿+dec;rubrics/structure.md、power.md(锚定表核对)、voice.md(声纹种子);人设卡 | book.md「主线电缆/人物主阵容/反派梯队」素材 + 实体卡种子清单 + dec_003 | 5 + R4 预留 |
| S4 | 架构师×1(分卷推演,无需方案对撞)/ 结构×1 + 安全×1 + 读者×1 | S1–S3 全部暂存稿+dec;rhythm/ 五模板(弧划分选配);volume.md 九节结构(F§4);rubrics/redline.md、payoff.md | book.md「分卷草案/红线自查结论」+ vol_01/volume.md + style.md 定稿(承 S1 题材与 S3 声纹;范文锚可引 corpus/ 或留占位)+ dec_004 | 5 + R4 预留 |
| 卷庭 | 架构师×2 /「结构+安全」合并×1 + 读者×1 | 上卷 exports+卷报告(编排者据 `novel.py status` + `ledger payoff|promise|timeline` 汇编,见 serial-ops §4)+imports 预填;book.md/world.md;主线电缆当前位置;所选 rhythm 模板;rubrics/power.md、redline.md、payoff.md | vol_NN/volume.md 九节 + dec_*(session: volume) | 5(无 R4) |
| 弧 | 架构师×1 / 合并评审×1(结构检查单+读者投票) | 卷蓝图(弧划分行)+前弧收尾摘要+active threads+payoff/promise 窗口(`novel.py ledger payoff|promise|timeline`)+所选 rhythm 模板检查单 | arc_NN_n.md 六节 + dec_*(简式) | 3 |

注:读者代表**每场必到、必投票**(spec §4.3 R2)。「合并评审」=单次运行附两份角色文件与判据,产出分两节。安全审查在 S1 把题材红线、在 S4 签署书级与卷级「红线自查结论」节。

## 3. 回合协议 R0–R4(可执行伪代码)

```
court_session(场, node):
  R0 编排者备设计简报(手工装配;F§15 无设计简报子命令):
     内容 = 议题与决策清单(本场要定什么,逐条)
          + 上游约束(已 committed 节点/前场暂存稿)
          + 兄弟契约(卷庭:上卷 exports+卷报告)
          + 市场输入(用户诉求/平台定位/人设集摘要)
          + 判据附件路径清单(按 §2 投递列)
          + 本节点相关否决案(court/dec_* 的「## 否决案」节全文)
     纪律: transcripts 永不入简报(F§11);体量对齐 brief_budget_chars(F§13)
     存项目外临时目录;路径记入 task note
  R1 提案(并行,一轮,不迭代):
     for 架构师 i in 阵容: spawn(T-arch, stance_i, 简报)  # 互相独立,不见他案
     → 各返回一份完整提案(按目标节点必需标题节组织,F§4)
  R2 评审(并行,一轮,全评审角色 × 全部提案):
     spawn 读者代表(T-reader): 每提案必给【弃读|追读】票 + 人设化理由
     spawn 结构/设定/安全(T-critic): 逐提案缺陷清单,每条标 blocking|minor
  R3 主编合成(1 次,T-editor):
     输入 = 简报 + R1 全部提案 + R2 全部评审与读者票
     输出 = (a) 节点资产草稿(必需节齐全非空,可择一可杂交)
            (b) 裁决记录草稿(F§11 四节)——否决案每条必填 reopen_requires;
                未采纳的评审意见逐条记 resolution: disagree_and_commit
  R4 定向修订(至多 1 轮;仅当 R3 留有 blocking 且预算未满):
     spawn 单一对口角色(T-fix),只修 blocking 项 → 编排者把补丁合入主编稿 → 强制定稿
  收尾(编排者):
     红线类 blocking 未解 → 升级用户,场挂起(task note 记「红线待人裁」,等用户当轮裁决)
     预算耗尽仍有非红线 blocking → 以主编现稿定稿,写入 dec「## 异议」留痕
     暂存三件: 节点稿 / dec_NNN 稿 / transcript(R1–R4 原文汇编)
     每场末向用户一页纸呈报(非阻塞;spec §10)
```

```
定稿落盘(书庭在 S4 收尾后一次性;卷庭/弧当场):
  审批(F§19): book/volume 定稿呈报用户当轮确认;unattended=true → 执行+note: pending_human_review
  附笔(编排者手笔,第一个 commit 前一刻写入,随事务同 git 入库):
    court/dec_NNN_{slug}.md ×N ; court/transcripts/dec_NNN.md ×N
    实体卡/线索卡种子: 从 templates/entity-*.md、thread.md 实例化(F§15 无 entity 创建子命令)
  for 节点 in 定稿包:                # 书庭: book, world, style, vol_01;卷庭: vol_NN;弧: arc_NN_n
    novel.py task add design <节点>   # 已有任务则略
    novel.py commit <task_id> --file <节点稿> -m "<场次摘要>"   # → committed(F§16 design 行)
  novel.py status                    # 复核 dashboard
```

- 附笔纪律:编排者自写的附属产物(dec/transcripts/实体种子/lessons 等)**只允许在某次 `novel.py commit` 前一刻写入**,随该事务入库;任何 worker 运行期间工作区必须干净(pipeline.md §5)。
- 书庭中间场次(S1–S3)产物只暂存不落盘:节不齐的 book.md 过不了 design 校验(F§16「必需节齐全非空」)。会话中断 → 当场作废重跑(≤6 次,廉价);已定稿场次不受影响。
- 书庭期间对同一节点的多场累积**属首次定稿过程**,不触发重开纪律;重开纪律自定稿 commit 起生效(§4)。

## 4. 超限处置与收敛纪律

| 情形 | 处置 |
|---|---|
| 运行数触顶仍有 blocking | 以主编现稿定稿;blocking 与反对意见写入 dec「## 异议」(disagree_and_commit),不加轮 |
| 红线类 blocking(rubrics/redline.md 命中) | 不得自动定稿;升级用户(task note 记「红线待人裁」),用户裁决前不推进该任务 |
| 评审全否全部提案且无可合成 | 视为 blocking;按上两行处置(用户可决定重开一场,计新预算) |
| 场间用户变卦 | 未定稿场次作废重跑;已 committed 节点走下方重开纪律 |

**否决案台账拦截(X7)**——任何人(含用户)重提设计变更时:

```
1 编排者先查目标节点全部 dec_* 的「## 否决案」节
2 命中且无满足 reopen_requires 的新证据 → 拒绝重提,回引 dec_id 与所需证据类型
3 有新证据 → novel.py task add revise_design <node> --evidence "<新证据,引用 dec_id>"
     # --evidence 必填;novel.py 创建时提示比对 court/ 否决案(F§10)
4 开庭前编排者出影响面报告: 依 state/index.json 的 parent 链与实体/线索引用,
     列受影响子树、章区间、预计返工量(无专用子命令,读生成物汇总),呈报用户后才开庭
5 修订庭定稿 commit 后,novel.py 自动将受影响下游标 stale(F§16 revise_design 行);
     stale 的卷/弧/章由编排者按队列重排(design/revise/write 任务)
```

**transcript 归档纪律**:R1–R4 原文汇编唯一去处=`court/transcripts/`(随定稿附笔入库);**永不进入任何简报、召回或角色附件**(F§11);复盘用 dec 记录+`git log`,不重放 transcript。沉淀物只有节点资产与裁决记录。

## 5. 附录:spawn prompt 模板(各庭型通用,按 §2 填槽)

通用尾注(每模板必含):**产出只放最终回复;禁止写入任何文件、禁止执行任何写命令;除资料员外不读仓库,以附件为准。**

**T-arch 架构师(书庭/卷庭;弧简流程单人复用)**
```
你是本场设计庭的架构师。先读你的角色文件:skills/novel-orchestrator/roles/architect.md
stance:<市场派|概念派|稳健派|体系派|代价派|人物派|冲突派>;独立提案,不揣测他案。(建议异族模型)
本场议题:<§2 对应场次议题 + 决策清单>
附件(只读):设计简报 <临时路径>;<按 §2 投递列的文件路径,逐个列出>
产出(最终回复):一份完整提案,按 <目标节点> 必需标题节组织(节名见简报);每个关键选择附一句理由。
[通用尾注]
```

**T-reader 读者代表**
```
你是读者代表。先读:roles/reader.md 与人设卡 personas/<卡名>.md;
全程以该人设的弃读阈值/毒点权重/爽点偏好为唯一先验,不做通用文学评价。
本场议题:<同上>;待评提案 N 份。
附件:设计简报 <路径>;提案 A/B[/C] <路径>
产出:对每份提案给【弃读|追读】票 + ≤3 条人设化理由(引用提案原文定位);末行给出排序。
[通用尾注]
```

**T-critic 评审(结构/设定/安全;「合并评审」附两份角色文件,产出分两节)**
```
你是<结构评审|设定审计|安全审查>。先读:roles/<structure-critic|setting-auditor|safety-auditor>.md
判据:rubrics/<structure|power|redline+toxicity+anti-plagiarism>.md<;节奏模板 rhythm/<模板>.md 检查单>
本场议题:<同上>;待评提案 N 份。
产出:逐提案缺陷清单,每条 = - [提案id·定位] 问题 → 建议,标 blocking|minor;
安全审查额外把红线命中单列「红线」节(一票升级项,编排者必须呈报用户)。
[通用尾注]
```

**T-editor 主编(卷庭/弧用简式:资产+简式 dec)**
```
你是主编(synthesizer)。先读:roles/editor.md
输入附件:设计简报、全部提案、全部评审与读者票(路径逐个列出)。
产出(最终回复,两段):
【一】<目标节点> 资产定稿:必需标题节齐全非空(节名见简报);可择一、可杂交,吸收 minor 建议。
【二】裁决记录草稿:按 formats.md §11 四节(选项/裁决/否决案/异议);
     否决案每条必填 reopen_requires(重开所需新证据类型);
     未采纳的评审意见记 resolution: disagree_and_commit;仍未解的 blocking 明确单列。
[通用尾注]
```

**T-fix R4 定向修订**
```
你是本场 R4 修订人(角色=roles/<对口角色>.md)。只修下列 blocking 项,不得重开其他已决事项:
<blocking 清单(含评审原文定位)>
附件:主编现稿 <路径>、相关评审原文 <路径>。
产出:仅被修各节的整节替换文本;其余只字不动。
[通用尾注]
```

弧简流程填槽:T-arch(单人,附件=§2 弧行投递列)→ T-critic 合并变体(structure-critic + reader 两份角色文件+人设卡,产出=缺陷清单+一票)→ T-editor(简式)。

---

*rev 1 · 2026-08-13 · Wave1-A5;与 formats.md rev 1 对齐。*
