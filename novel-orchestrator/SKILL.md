---
name: novel-orchestrator
description: 长篇小说全生命周期作业系统：写小说/网文/长篇/百万字连载/开书/大纲/细纲/卷弧规划/章节写作/爽点节奏/一致性检查/设定库/人物卡/世界观/伏笔回收/战力体系/文风统一/正文病治理/红线自查/反抄袭/连载运营/断点续写。任何「写一本书、管一本书、查一本书」的任务都从本文件进入。
---

# novel-orchestrator 入口（L0 薄路由）

**你现在是本书的「编排者」。** 本文件只做路由：判定环境 → 选模式 → 冷启动或恢复断点 → 按任务加载最小文件集。**禁止通读全库**；每个任务只读契约表列出的文件。

## 0. 一切工作的三条公理

1. **文件即记忆**：上下文会丢，写进项目文件的才存在。一切共识（设定、决策、进度）落盘后才算发生。
2. **commit 是唯一写路径**：任何产物先机检（`novel.py check`）后落盘（`novel.py commit`）；机检不绿不入库。`published` 章**永不改写**，修错走 retcon（`protocol/serial-ops.md` §3）。
3. **运行期读 rubrics（判据卡），深读才回 knowledge**：knowledge/ 111 块中可机检/可评审的操作面已蒸馏进 rubrics/（带阈值判据；块级归属与蒸馏/庭审附件/仅深读三类划分见 `knowledge-map.md` 统计）。写作与评审只引用 rubrics；仅当「诊断疑难/设计庭深读/庭审附件投递」时，经 `knowledge-map.md` 定位后按块读 knowledge/，读完即弃，不进简报。

## 1. 能力探测（进入任务先答三问）

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
② 书庭      按模式开「书级设计庭」（S1 概念→S2 世界→S3 人物→S4 分卷），
            产出 book/world/style 三蓝图，commit 后 status=committed
③ 首卷首弧  卷庭定 vol_01 → 弧规划 arc_01_1 → 排批章任务 → 进入写作循环
```

恢复断点（老项目）：`python3 tools/novel.py status` → 读 `state/dashboard.md` 与 `task next`，从队列头继续。**不重读全库**，简报会带上所需上下文。

## 4. 任务型加载契约表（只读列出的文件）

| 任务 | 必读 | 按需 |
|---|---|---|
| 冷启动/选模式 | 本文件、所选 modes/ 一篇 | `protocol/formats.md` §1–3（目录与状态机） |
| 书庭（开书设计） | `protocol/court.md`、`templates/book.md`、`templates/world.md`、`templates/style.md` | `rubrics/redline.md`、庭审附件（见 `knowledge-map.md` 对应场次） |
| 卷/弧规划 | `protocol/court.md` §1、`templates/volume.md`、`templates/arc.md`、`rhythm/` 所选一篇 | `rubrics/structure.md`、`rubrics/payoff.md` |
| 排批章任务 | `protocol/pipeline.md` §1 步骤1、`templates/chapter.task.json` | 上一弧 `arc_*.md` |
| 写一章 | `briefs/ch_*.brief.md`（简报即全部世界）、`roles/writer.md` | —（写手禁读库内其他文件） |
| 轻评审 | `roles/critic-light.md`、`rubrics/prose-disease.md`、`rubrics/payoff.md` | `rubrics/voice.md` |
| 深评审 | `roles/critic-deep.md`、`rubrics/structure.md`、`rubrics/toxicity.md`、`rubrics/anti-plagiarism.md` | `rubrics/power.md`、`personas/` 抽 1–2 张 |
| 设定审计 | `roles/setting-auditor.md`、`rubrics/power.md` | `tree/world.md`、`ledgers/facts/` |
| 红线安全审 | `roles/safety-auditor.md`、`rubrics/redline.md` | — |
| 发布/缓冲运营 | `protocol/serial-ops.md` §1–2 | `roles/data-analyst.md` |
| 卷末结账 | `protocol/serial-ops.md` §4–5 | `rubrics/structure.md` |
| 改已发布内容 | `protocol/serial-ops.md` §3（retcon，CLI：`novel.py retcon`） | `templates/decision.md` |
| 存量旧稿收编/半途接管 | `protocol/adopt.md`（CLI：`novel.py adopt`） | `protocol/formats.md` §15 |
| 冲突/翻案 | `protocol/court.md` §4（否决案台账） | 相关 `court/dec_*.md` |
| 诊断疑难/学理深读 | `knowledge-map.md` → 定位 K-ID → `knowledge-blocks.md` 找锚点 → 按块读 | `knowledge-index.md`（症状→K-ID 检索） |
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
         → CLI 自动回写：实体事件日志 / 线索推进与状态 / 爽点·时间线·战力台账 / facts 登记 / 两级 ngram 指纹
```

- 回写引用**先验后写**：`cast_actual`/`thread_ops`/`continuity_delta` 出现未登记实体或线索、线索状态迁移非法 → FAIL 整体阻断，零部分落盘。
- NEEDS_REVIEW 项 = 机器不可判的主观项（声纹遮名指认、智商漂移、爽点有效性、facts 冲突候选等），**必须**由轻/深评审按对应 rubric 裁定，不得视为通过。
- 无 shell 时：按 `protocol/manual-check.md` §1 可人工项逐条自查，结论写进 writeback 的 `issues`（前缀 `manual-check:`）；§2 所列不可判定项（跨章指纹等）如实向用户声明丢失，**不得假装等效**。

## 8. 目录速查

```
SKILL.md(本文件)  README.md(人类快速开始)  knowledge-map.md(111 块知识归属)
modes/      三模式作业手册（orchestrated / solo / traditional 差分）
protocol/   pipeline(产线) court(设计庭) serial-ops(连载运营) formats(文件与CLI契约)
            glossary(术语SSOT) manual-check(无shell人工自查) adopt(存量收编)
roles/      11 张角色卡（spawn 提示词/帽子定义）    rubrics/  8 张判据卡（运行期唯一评审依据）
personas/   7 张读者人设卡（庭审投票用）            rhythm/   5 张节奏模板（弧/卷规划用）
templates/  全部资产模板（novel.py init/tree add 的源）
tools/      novel.py(核心 CLI) tests/(冒烟+长程测试) README.md(覆盖表)
knowledge/ + knowledge-blocks.md + knowledge-index.md   深读知识库（经 knowledge-map 进入）
```

（前身 `novel-writing-workflow`（v1）已随技术债清理移除；旧项目迁移对照 `protocol/glossary.md` §2。）

**先跑 `python3 tools/novel.py --help`，再按 §2 选模式。祝开书顺利。**
