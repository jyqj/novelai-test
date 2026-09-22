# novel-orchestrator — 长篇小说创作工作流

面向长篇/超长篇小说的分层规划、章节写作、连续性维护、评审与连载管理。保留作者对作品的最终选择；工具保证可检查的状态与证据，不宣称用工程规则自动保证文学质量。

Agent 从 [SKILL.md](SKILL.md) 进入。当前版本的安全写入、评审与历史语义见 [protocol/reliability.md](protocol/reliability.md)，文件细节见 [protocol/formats.md](protocol/formats.md)。

## 结构与模式

协议与阶段包负责导航；角色/判据负责分工；项目文件是长期记忆；Python 标准库 CLI 负责编译简报、账本、事务和闸门。knowledge/ 是按需方法论，不全量灌入每次写作。

可调度子代理用 orchestrated；单代理用 solo（自评并不等于独立评审）；传统长篇在其上叠加 traditional，允许强规划或探索式写作，classic24 是可选工具。无 shell 环境会失去自动事务与机械验证能力，必须明示降级。

## 初始化：工具安装目录与小说目录分离

需要 Python 3.10+；Git 可选，自动提交需要已配置身份。下段在 skill 目录执行，之后始终使用工具的绝对路径。`WORKSPACE` 是一个尚不存在的新小说目录。

<!-- quickstart-test:start -->
```bash
NOVEL="$PWD/tools/novel.py"
python3 "$NOVEL" --help
python3 "$NOVEL" init "$WORKSPACE" --name 我的书
cd "$WORKSPACE"
python3 "$NOVEL" status
python3 "$NOVEL" stage enter s1
python3 "$NOVEL" court open S1 --node book
python3 "$NOVEL" stage current
```
<!-- quickstart-test:end -->

接着按书庭 S1–S4 完成 book/world/style，提交首卷和首弧，再进入 write。脚手架只是待设计模板，不是假装已经批准的故事。可执行初始化由 test_quickstart.py 验证。

## 单章循环

在已有 committed 弧和完整任务卡的项目中，先 `stage enter write`、`task add write ch_0001`、`task start <实际返回的任务ID>`。首次建章用 `tree add chapter ch_0001 --parent arc_01_1`；重复创建会拒绝覆盖。

```bash
python3 "$NOVEL" brief ch_0001
python3 "$NOVEL" gate write ch_0001
# 写手返回候选正文和 writeback，存项目外临时目录；以下文件名需替换成真实产物。
python3 "$NOVEL" check --unit ch_0001 --candidate /tmp/chapter.md --writeback /tmp/writeback.json
python3 "$NOVEL" commit <任务ID> --chapter /tmp/chapter.md --writeback /tmp/writeback.json -m 首章
python3 "$NOVEL" review checklist ch_0001 > /tmp/review.json
# 评审者读稿并填写 review.json 中的 summary / disposition / rationale；pending 不能通过。
python3 "$NOVEL" review add ch_0001 --depth light --verdict pass --evidence /tmp/review.json
python3 "$NOVEL" gate approve ch_0001
python3 "$NOVEL" tree set-status ch_0001 approved
python3 "$NOVEL" task done <任务ID>
```

返修使用新 `revise` 任务，不能再用 write 覆盖。发布先 `stage enter ops` 再 `publish`，受连续性、存稿和新鲜评审约束；不能用 set-status 绕过。traditional 不使用连载发布链。

## 历史、恢复与按需咨询

```bash
python3 "$NOVEL" knowledge query --entity char_zhu --at ch_0050
python3 "$NOVEL" knowledge grant fact_000001 --to char_zhu --ch ch_0051
python3 "$NOVEL" stage consult K-CONCEPT-001 --target ch_0001 --reason "本章核心冲突缺少可展开性"
python3 "$NOVEL" recover
python3 "$NOVEL" recover --rollback
python3 "$NOVEL" gate next
```

这些命令要求对应实体/事实/节点已存在。咨询不改当前阶段或知识所有权；成员变动不自动改变已经发生的获知。必需记忆缺失或简报超预算返回失败，旧的有效简报不会被覆盖。

## 测试与已知边界

在 skill 目录运行：

```bash
for suite in tools/tests/test_*.py; do python3 "$suite" || exit 1; done
```

覆盖原有冒烟、35 章长程、重构、阶段、知识矩阵，以及新的故障注入/历史召回/证据回执/文档初始化测试。CI 保留日志与精确源码快照，合成评审只存在于测试夹具。

旧评审需重新生成证据，旧简报需重编译；迁移前备份项目。旧知识或人物记录没有历史证据时不会被伪造补齐。单章评审票不代表整卷通过，历史返修仍需下游语义复评，召回与 rollup 仍包含全量扫描。真实创作质量和百万字成本没有在本轮得到实验验证，验证计划见 [protocol/evaluation.md](protocol/evaluation.md)。
