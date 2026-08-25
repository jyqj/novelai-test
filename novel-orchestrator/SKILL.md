---
name: novel-orchestrator
description: 长篇小说全生命周期作业系统：写小说/网文/长篇/百万字连载/开书/大纲/细纲/卷弧规划/章节写作/爽点节奏/一致性检查/设定库/人物卡/世界观/伏笔回收/战力体系/文风统一/正文病治理/红线自查/反抄袭/连载运营/断点续写。任何「写一本书、管一本书、查一本书」的任务都从本文件进入。
---

# novel-orchestrator 入口（L0 薄路由）

**你现在是本书的「编排者」。** 本文件只做路由：判定环境 → 选模式 → 冷启动或恢复断点 → 按任务加载最小文件集。**禁止通读全库**；每个任务只读契约表列出的文件。

> **全生命周期主循环的唯一总装图 = `protocol/workflow.md`**：每个环节的入口闸门/CLI/执行角色/判据卡/失败去向都在那一份里；solo、traditional、无 shell 档的覆盖差分也收敛在其 §7。迷路时：`novel.py status` → `novel.py gate next`（机器剧本，FAIL 自带「下一步」修复命令）→ 对照 workflow §1 定位。

## 0. 一切工作的三条公理

1. **文件即记忆**：上下文会丢，写进项目文件的才存在。一切共识（设定、决策、进度）落盘后才算发生。
2. **commit 是唯一写路径**：任何产物先机检（`novel.py check`）后落盘（`novel.py commit`）；机检不绿不入库。`published` 章**永不改写**，修错走 retcon（`protocol/serial-ops.md` §3）。
3. **知识按阶段装载，运行期读 rubrics，深读才回 knowledge**：全生命周期切成 11 个阶段，每阶段有唯一配套知识包（`protocol/stages/`；总目录与硬规则=`protocol/knowledge-orchestration.md`）——**进环节 = `novel.py stage enter <id>` + 读包**（进阶段写 `state/stage.json`，是各受辖操作的钥匙：court open/brief/commit/publish… 阶段不匹配即被闸门拒绝），按包内「必读/选读池/禁读」装载，不再自行翻库。可操作面已蒸馏进 rubrics/（带阈值判据），写作与评审只引用 rubrics；庭审附件从本场包 K 池挑 ≤4 块只取锚点段；仅 diag 阶段（诊断疑难/学理求教）经症状路由按块读 knowledge/（≤2 块），读完即弃，不进简报。`novel.py stage current` 读持久化阶段与包路径。

## 1. 能力探测（进入任务先答三问；四档剖面与降级矩阵详见 `modes/capability-profiles.md`）

| 探测 | 判定方法 | 结果 |
|---|---|---|
| 能否 spawn 子代理？ | 产品是否提供 Task/subagent 类工具 | 能 → `orchestrated`；不能 → `solo` |
| 有无 shell + python3？ | 尝试 `python3 tools/novel.py --help` | 有 → 全部机检交给 CLI；无 → **有损降级**：文件仍按 `protocol/formats.md` 契约手工维护，可人工项按 `protocol/manual-check.md` §1 逐条自查，但跨章指纹/队列自动化/facts 冲突扫描/git 事务等能力**直接丢失**（同文件 §2 损失清单），须在项目启动时向用户明示并强烈建议争取 shell |
| 人是否在环？ | 用户是否会回复审批请求 | 在 → 关键闸门（开书/卷末/发布）报批；不在 → `config.json` 设 `unattended: true`，按 `protocol/formats.md` §19 降级为「执行 + note: pending_human_review 留痕」 |

## 2. 三模式路由

| 用户意图 | 模式 | 必读（按序） |
|---|---|---|
| 网文/连载/百万字长篇，**可 spawn 子代理** | orchestrated | `modes/mode-orchestrated.md` → `protocol/pipeline.md` |
| 同上，**不可 spawn**（单代理产品） | solo | `modes/mode-solo.md`（帽子切换 + 庭审降级） |
| 传统长篇/严肃文学/无连载发布 | traditional | `modes/route-traditional.md`（叠加在前两者之上的差分） |

> traditional 是**差分层**：先按能力选 orchestrated/solo，再叠加 route-traditional 的覆盖规则（无 buffer/publish、细纲工序、classic24 全书节拍）。`config.json` 写 `"route": "traditional"`。

## 3. 冷启动三步（新书）

```
① init      python3 tools/novel.py init <项目目录> --name <书名>
② 书庭      novel.py stage enter s1（逐场 enter s1..s4）→ 按模式开「书级设计庭」
            （S1 概念→S2 世界→S3 人物→S4 分卷），产出 book/world/style 三蓝图，
            commit 后 status=committed
③ 首卷首弧  stage enter vol → 卷庭定 vol_01 → stage enter arc → 弧规划 arc_01_1
            → stage enter write → 排批章任务 → 进入写作循环
```

恢复断点（老项目）：`python3 tools/novel.py status` → **`novel.py gate next`**（按 修账>深评>对账>欠账>缓冲>推进 输出下一步，末段附已进入阶段与配套知识包路径）→ `stage current` 核对阶段（换环节先 `stage enter`）→ `task next` 从队列头继续。**不重读全库**，简报会带上所需上下文。主循环各环节定位见 `protocol/workflow.md` §1；该装载什么见对应 `protocol/stages/` 包。

## 4. 任务型加载契约表（只读列出的文件）

| 任务 | 必读 | 按需 |
|---|---|---|
| 冷启动/选模式 | 本文件、所选 modes/ 一篇 | `modes/capability-profiles.md`（档位存疑时）、`protocol/formats.md` §1–3（目录与状态机） |
| 主循环导航/交接契约 | `protocol/workflow.md`（总装图+交接验收谓词+三覆盖表） | 各环节指针到的专项协议 |
| **当前阶段该装载什么** | `protocol/knowledge-orchestration.md`（阶段目录+硬规则）→ 对应 `protocol/stages/` 包 | `novel.py stage current`（读持久化阶段与包路径；换环节先 `stage enter`） |
| 书庭（开书设计） | `protocol/court.md` + 本场阶段包 `protocol/stages/s1-concept.md`..`s4-volumes.md`（必读清单与庭审附件 K 池都在包内） | `templates/book.md`、`templates/world.md`、`templates/style.md` |
| 卷/弧规划 | `protocol/court.md` §1 + 阶段包 `protocol/stages/vol-court.md` / `arc-plan.md` | `templates/volume.md`、`templates/arc.md`、`rhythm/` 所选一篇 |
| 排批章任务 | `protocol/pipeline.md` §1 步骤1、`templates/chapter.task.json` | 上一弧 `arc_*.md` |
| 写一章 | `briefs/ch_*.brief.md`（简报即全部世界）、`roles/writer.md` | —（写手禁读库内其他文件） |
| 轻评审 | `roles/critic-light.md`、`rubrics/prose-disease.md`、`rubrics/payoff.md` | `rubrics/voice.md` |
| 深评审 | `roles/critic-deep.md`、`rubrics/structure.md`、`rubrics/toxicity.md`、`rubrics/anti-plagiarism.md` | `rubrics/power.md`、`personas/` 抽 1–2 张 |
| 传统路线细纲/三遍修订 | `modes/route-traditional.md`、`rubrics/scene-value.md` | `rubrics/theme.md`、`rubrics/imagery.md`、`personas/literary-purist.md`+`bookclub-mainstream.md` |
| 设定审计 | `roles/setting-auditor.md`、`rubrics/power.md` | `tree/world.md`、`ledgers/facts/` |
| 红线安全审 | `roles/safety-auditor.md`、`rubrics/redline.md` | — |
| 发布/缓冲运营 | `protocol/serial-ops.md` §1–2 | `roles/data-analyst.md` |
| 卷末结账 | `protocol/serial-ops.md` §4–5 | `rubrics/structure.md` |
| 改已发布内容 | `protocol/serial-ops.md` §3（retcon，CLI：`novel.py retcon`） | `templates/decision.md` |
| 知识矩阵（谁知道什么） | `protocol/formats.md` §9（known_by/spoiler 语义；CLI：`novel.py knowledge`） | `protocol/workflow.md` §4（弧末欠账盘点） |
| 教训蒸馏进判据 | `protocol/workflow.md` §6 蒸馏回路（CLI：`task add revise_rubric style`） | `ledgers/lessons.md`、`tree/style.md` |
| 存量旧稿收编/半途接管 | `protocol/adopt.md`（CLI：`novel.py adopt`；批量补录后 `novel.py rollup`） | `protocol/formats.md` §15 |
| 冲突/翻案 | `protocol/court.md` §4（否决案台账） | 相关 `court/dec_*.md` |
| 诊断疑难/学理深读 | `protocol/stages/diagnose.md`（诊断五步+预算）→ `knowledge-index.md` 症状路由 → `knowledge-blocks.md` 锚点按块读 | `knowledge-map.md`（块级归属台账） |
| 术语歧义 | `protocol/glossary.md`（SSOT） | — |

## 5. 最小回应契约（所有角色/帽子通用）

每次子代理返回（或 solo 模式每顶帽子收工）必须是**结构化交付**，不是散文：

1. **产物**：按简报 §8 或角色卡「输出契约」规定的格式（章文件+writeback JSON / 评审单 / 提案文件）。
2. **issues**：缺料、矛盾、无法判定项，逐条列出；**禁止脑补补洞**。
3. **泄漏自查**：产物中不得出现简报/任务卡之外的专名与设定（`protocol/pipeline.md` §5）。

## 6. 阻塞上报

遇下列情形**立即停手上报**（人在环）或**记 decision 后走保守默认**（unattended）：

- 红线嫌疑（`rubrics/redline.md` 任一条命中）——安全审计员一票上报，无人可否决；
- 需要翻已 commit 的书/卷级决策（先查 `court/` 否决案台账，无新证据不得重开）；
- `check --project` 出现无法自动修复的 FAIL（如 published 空洞、facts 断链）；
- 同一目标 write/revise 失败 2 次（队列自动升级 revise_design，勿硬写第 3 次）。

## 7. 写回闸门（writeback gate)

写手/评审的输出**不直接落库**。唯一路径：

```
候选产物 → novel.py check --unit <ch> --candidate <草稿> --writeback <json>
         → 绿（0 FAIL；WARN/NEEDS_REVIEW 可带走）→ novel.py commit <task_id> …
         → CLI 自动回写：实体事件日志 / 线索推进与状态 / 爽点·时间线·战力台账 /
           facts 登记（含 known_by 知情名单）/ 两级 ngram 指纹 / rollup 摘要卷积
```

- 回写引用**先验后写**：`cast_actual`/`thread_ops`/`continuity_delta` 出现未登记实体或线索、线索状态迁移非法 → FAIL 整体阻断，零部分落盘。
- NEEDS_REVIEW 项 = 机器不可判的主观项（声纹遮名指认、智商漂移、爽点有效性、facts 冲突候选、剧透泄漏与角色知识越界候选等），**必须**由轻/深评审按对应 rubric 裁定，不得视为通过。
- 无 shell 时：按 `protocol/manual-check.md` §1 可人工项逐条自查，结论写进 writeback 的 `issues`（前缀 `manual-check:`）；§2 所列不可判定项（跨章指纹等）如实向用户声明丢失，**不得假装等效**。

## 8. 目录速查

```
SKILL.md(本文件)  README.md(人类快速开始)  knowledge-map.md(111 块知识归属台账)
modes/      三模式作业手册（orchestrated / solo / traditional 差分）+ capability-profiles（宿主四档）
protocol/   workflow(主循环总装图) pipeline(产线) court(设计庭) serial-ops(连载运营)
            knowledge-orchestration(阶段×知识装载 SSOT) stages/(11 个阶段配套知识包)
            formats(文件与CLI契约) glossary(术语SSOT) manual-check(无shell人工自查) adopt(存量收编)
roles/      12 张角色卡（spawn 提示词/帽子定义；含 extractor 抽取器）
rubrics/    11 张判据卡（运行期唯一评审依据）
personas/   9 张读者人设卡（庭审投票用；含 2 张传统路线文学口味卡）  rhythm/   5 张节奏模板（弧/卷规划用）
templates/  全部资产模板（novel.py init/tree add 的源）
tools/      novel.py(核心 CLI) tests/(冒烟+重构回归+长程测试) README.md(覆盖表)
knowledge/ + knowledge-blocks.md + knowledge-index.md   深读知识库（经 knowledge-map 进入）
```

（前身 `novel-writing-workflow`（v1）已随技术债清理移除；旧项目迁移对照 `protocol/glossary.md` §2。）

**先跑 `python3 tools/novel.py --help`，再按 §2 选模式。祝开书顺利。**
