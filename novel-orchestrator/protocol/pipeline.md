# 单章产线协议

主循环定位见 workflow.md；格式见 formats.md；当前写入/评审/历史保证见 reliability.md。worker 只返回文本，CLI 负责正式项目变更。作者的已有改动不是可以随意清理的垃圾。

## 0. 启动与输入

`status → gate next → stage current → task next` 定位。写作进入 write，默认加载阶段包和角色/判据；具体方法论难题可由编排者 stage consult 留痕，不全量灌库。临时稿和评审 JSON 放项目外，任务 note 保存路径。

## 1. 单章顺序

1. 从 committed 弧计划排章，`tree add chapter` 只新建；补完整 task.json，设 goal/beats/cast/word_target，以及 context_entities/memory_keywords/fact_refs/memory_refs。规划草案不能当已发生事实。
2. `task add write <章>`，使用返回的真实 id；`task start <任务>`；`brief <章>` 编译。
3. 资料员审包，检查人物关系、内在驱动、历史截止点和关键记忆。缺料修源数据/任务依赖，再编译；**不直接改 brief 或 manifest**。预算拒绝时缩减无关材料或拆场。
4. `gate write <章>` 通过后，写手只读简报与 roles/writer.md。确认 Git 改动的归属，作者保存/提交自己的改动后继续；无 Git 明示降级，禁止 destructive clean。
5. 双产出存外部临时目录；`check --leak <正文> --brief <简报>` 和 `check --unit <章> --candidate <正文> --writeback <回写>`。机械 FAIL 修正后再继续，NEEDS_REVIEW 不当作自动通过。
6. `commit <任务> --chapter <正文> --writeback <回写>` 落为 drafted；`review checklist <章>` 导出确切版本的 pending 清单。
7. 轻评读实际稿、writeback、简报与上文，逐项填写 evidence.summary/findings。额外发现的阻塞也须列入。用 `review add <章> --depth light --verdict pass|revise|escalate --evidence <JSON>` 落盘。工具不提供默认通过票。
8. pass 后 `gate approve <章>`、`tree set-status <章> approved`、`task done <任务>`。所有批准入口复用相同检查；同版本深评阻塞优先。
9. 进入周期深评/对账；满足发布条件后切 ops，`publish <起章> [终章]` 再次验收。traditional 无连载发布链。

可以在提交前先做一次候选轻评减少返修，但正式批准票必须针对已提交确切版本，不照搬候选阶段的哈希。

## 2. 返修与重试

未提交草稿修订直接更新外部临时文件并重检。已提交章用新 revise 任务，正文版本递增、日志撤销重放、旧票失效，重新编译需要的简报并生成评审清单。published 不允许覆盖，走向后兼容 retcon。

同一任务完全相同输入的提交重试无副作用；不同输入不能复用已消费任务。失败两次按既有队列规则升级 revise_design，保留问题、证据和已尝试方案，不无限重复同一提示词。

## 3. 设计问题与创作发现

问题来自简报就标 brief_issue，修包，不逼写手脑补。问题来自设计则开 `task add revise_design <节点> --evidence <症状与影响>`。写手的 proposal 先评估后批准，不直接写 canon；作者可明确覆盖旧决定，记录代价与受影响章，不让否决台账否决作者。

## 4. 周期评审与学习

每 critic.deep_every 章以及弧末/卷末做深评。先冷读正文的实际效果，再对照计划、期待账户、人物关系、知识边界与伏笔。计划本身也可成为问题来源。

每份机械回执目前只绑定一章。跨章报告列清范围和受影响章，分别安排复评/返修；不能一张 pass 代替整卷验收。深评也使用 checklist + --evidence，或按 formats 当前回执格式提交完整文件。未消除的 escalate 不因轻评通过而消失。

记录失败教训，同时记录成功片段、原文证据、作用与适用边界；成功样本随回执 strengths 保存，编辑再选择进入 style 范文锚，不只增长黑名单。模拟读者反馈与真实读者反馈分开标记。

## 5. 工作区与事务恢复

spawn 前后比较 `git status --porcelain` 和 `git diff`；出现未知修改先列清归属、备份，并隔离 worker 候选。绝不运行全工作区丢弃/清理命令。只读 worker 返回不该直接改正式项目。

CLI 普通失败回滚其触及文件；崩溃后 `recover` 列 journal，`recover --rollback` 校验前镜像后恢复。存在作者后续编辑即拒绝覆盖。旧版半事务没有前镜像只能人工处理。恢复后重查 gate，不能只把任务改成 pending 就当数据已修复。

## 6. 成本档位

standard 每章轻评、按 deep_every 深评；quality 可增加资料员、候选方案和冷读；economy 可以少采样或降低调用预算，但**不能批准没有有效回执的章节**。预算不足留 drafted，不伪造 pass。复评次数、总 token、合格字数和作者介入时间见 evaluation.md。

## 7. worker 附件边界

写手：简报、角色卡，返修附上稿与明确问题。资料员：只读项目检索权，输出源数据/依赖修正建议。轻评：正文+writeback+简报+前章尾+本章 checklist+相关判据。深评：指定窗口正文、账本、人物/关系和计划，先冷读后比对。每个角色只返回结构化产物，不直接写文件、不自造裁决哈希。
