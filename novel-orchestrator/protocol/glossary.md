# glossary.md — v2 术语单一事实源（SSOT）+ v1→v2 迁移映射

任何文档/角色卡/工具输出中的术语以本表为准；发现漂移（同义新词、旧词复活）按本表归一，
勿在其他文件另立定义。文件与字段的机器契约见 `protocol/formats.md`（本表不重复阈值）。

## 1. v2 核心术语

| 术语 | 定义 | 落点 |
|---|---|---|
| 编排者 | 主 agent；只调度不写正文；一切落盘经其手 | modes/ 两篇 |
| 主循环 | 全书生命周期的端到端剧本：冷启动→设计庭→卷/弧→章循环→周期项→checkpoint；`gate next` 是其机器半边 | protocol/workflow.md |
| 设计庭 | 高风险设计决策的对抗评审会（书/卷/弧三庭型，R0–R4 回合） | protocol/court.md |
| 产线 | 单章写作的固定时序：排批→简报→写→机检→轻评→commit | protocol/pipeline.md |
| 简报（brief） | 写手唯一输入；十节 + 溯源，字符预算内机械装配 | `novel.py brief`，formats §6 |
| 信息沙箱 | worker 只见投递材料；产出超出输入的专名/设定=泄漏 | pipeline §5 |
| 帽子 | solo 模式下的角色时分复用单位；一次一顶，产物落盘再换 | modes/mode-solo.md |
| 树节点 | book/volume/arc/world/style 五种设计资产 | tree/，formats §4 |
| 章三件套 | ch_*.md（正文）+ .task.json（任务卡）+ .meta.json（回写） | chapters/，formats §5 |
| 信封 | 文件头部扁平 frontmatter（id/kind/status/rev/updated_at…） | formats §3 |
| 状态机 | 节点 empty→draft→committed（+stale/archived）；章 planned→drafted→approved→published | formats §3 |
| stale | 上游设计变更导致下游待重验的标记；修复后回原状态 | `commit`（revise_design 自动传播） |
| writeback（回写） | 写手随章提交的结构化 JSON；经 commit 分发进实体/线索/台账 | formats §5 |
| 抽取器 | 从正文实测反推申报的对账角色：出场/新专名/剧透/知识越界四类候选 | roles/extractor.md，`novel.py extract` |
| 机检 | `novel.py check` 的机器断言；不可判项显式输出 NEEDS_REVIEW | tools/README.md 覆盖表 |
| NEEDS_REVIEW | 机器不可判、必须由评审角色按 rubric 裁定的项 | check 输出 |
| 判据卡（rubric） | 从 knowledge 蒸馏的带阈值评审标准；运行期唯一评审依据 | rubrics/ |
| 人设卡（persona） | 读者画像 + 毒点权重 + 投票纪律；庭审与冷读用 | personas/ |
| 节奏模板 | 弧/卷的节拍骨架（classic24/wave/dungeon/episodic/ensemble） | rhythm/ |
| 实体卡 | char/item/loc/fac 四类设定资产；含现状节与事件日志 | entities/，formats §7 |
| 线索（thread） | 跨章叙事承诺（fuse/subplot/relationship/mystery/promise） | threads/，formats §8 |
| 台账（ledger） | 只追加的全局账本：payoff/timeline/facts/lessons | ledgers/，formats §9 |
| facts / retcon | 已揭示事实层；改已发布内容=登记新事实覆盖旧事实，不改正文 | serial-ops §3 |
| 知识矩阵 | fact × 角色（known_by 知情名单）× 读者（spoiler/revealed_reader_ch）的三轴知情台账 | formats §9，`novel.py knowledge` |
| rollup（卷积） | 章 summary_after → 弧/卷摘要的机械重算；commit 自动做，批量手改后可手动触发 | `novel.py rollup` |
| 蒸馏（revise_rubric） | 教训→style 黑名单/判据的轻量修订任务：限 style、rev 自动+1、不传播 stale | serial-ops §6，workflow §6 |
| 爽点配额（payoff_quota） | 章任务卡规定的情绪兑现指标；realized ⊆ quota | formats §5 |
| buffer | 已 approved 未 published 的存稿水位 | serial-ops §1 |
| checkpoint | 卷末结账：三态对账+深评+价值交接 | serial-ops §4 |
| 对账（reconcile） | 实体现状节与事件日志的周期性合并 | serial-ops §5，`entity due` |
| 否决案台账 | dec_*.md 的「否决案」节 + reopen_requires；重开裁决的唯一入口 | court §4 |
| 一票升级 | 红线命中时安全审计员的不可否决上报权 | roles/safety-auditor.md |
| 泄漏检查 | worker 返回后比对产物专名与其输入范围 | pipeline §5 |
| 阶段（stage） | 生命周期的知识装载单位（11 个：s1–s4/vol/arc/write/review/ops/trad/diag）；每阶段一个配套知识包；`novel.py stage` 导航 | protocol/knowledge-orchestration.md |
| 阶段包（配套知识包） | protocol/stages/ 下的薄路由文件：必读 / 选读池（K 池）/ 禁读 / 退出判据；进环节先读包 | protocol/stages/ |
| K 池 | 某阶段有权投递的庭审附件 K-ID 白名单（≡ knowledge-map 场次标注，机检对账）；每场挑 ≤4 块、只取锚点段 | 各阶段包「选读池」节 |
| 深读 | 仅 diag 阶段：症状路由定位 K-ID 后按锚点段读 knowledge/ 原文（≤2 块/次）；读完即弃 | protocol/stages/diagnose.md |

## 2. v1 → v2 迁移映射

v1 = 原 `novel-writing-workflow` skill（**已随技术债清理整体移除**，本表是其术语与资产的唯一存续映射）。旧词只在迁移按 v1 格式建的旧项目时会遇到；新文档禁用。

| v1 术语/资产 | v2 对应 | 说明 |
|---|---|---|
| BOOT 序列 / 意图路由 | SKILL.md 能力探测 + 三模式路由 + 任务型加载契约表 | 意图枚举改为任务行 |
| P1 蓝图（Blueprint） | 书庭 S1 概念 → `tree/book.md` | 高概念/主控思想进 book 必需节 |
| P2 粗纲（PlotSpine，24 节点） | book「分卷草案」+ `rhythm/classic24.md` | traditional 路线保留全书 24 节拍（modes/route-traditional §1） |
| P3 序列纲（SequenceMap） | 弧规划 `tree/vol_*/arc_*.md` | 因果链 + 章分配草案 |
| P4 人物/世界定稿（Character/WorldRule → canon） | 书庭 S2/S3 + `entities/` + `tree/world.md` | canon 状态 → 节点 committed + facts 台账 |
| P5 章纲（ChapterPlan/SceneBeat） | 章任务卡 `chapter.task.json` | traditional 加细纲工序（route-traditional §2） |
| P6 正文（ManuscriptUnit） | 章三件套 | unit_type 五值不再强制标注 |
| Status / Manifest | `state/index.json` + `dashboard.md`（生成物）+ `config.json` | 对账逻辑进 `check --project` |
| Canon（资产状态） | committed / facts | 「已定稿可依赖」语义拆为节点状态与事实层 |
| locked | published（章）/ committed（节点） | 已发布不可变，改动走 retcon |
| Decision | `court/dec_*.md` | 增加否决案 + reopen_requires |
| Recap | 简报 §2 直接上文 + meta.json 的 summary_after 链 | 不再单独维护 Recap 资产 |
| writeback-acceptance（M01–M13） | `check --unit/--window/--project` + commit 闸门 | 机器化断言进 CLI；主观项 NEEDS_REVIEW |
| conflict-playbook | court §4 否决案台账 + revise_design 升级 + stale 传播 | 冲突分类不再单列文档 |
| web-serial-playbook（Fast-Start/缓冲） | `protocol/serial-ops.md` | buffer 语义化为水位动作表 |
| validate.py | `tools/novel.py check`（全部机检断言已收编并扩展） | v1 校验器已随清理移除 |
| route: traditional/web + dual_track | `config.json "route"` + modes/route-traditional.md | dual_track/hybrid 取消：混合需求按卷切 route |
| knowledge-index（diagnose/learn 意图） | `knowledge-map.md`（归属）+ `knowledge-index.md`（症状检索，收编） | 运行期默认不进知识库 |
| 阶段门禁（phase gate） | 机检闸门 + 设计庭 R0–R4 + 审批点（formats §19） | gate 谓词机器化的部分全部进 CLI |
| 恢复点（Status.mode/current_phase） | `tasks/queue.json` + `novel.py status` | 断点=队列头，不依赖会话记忆 |
| 洋葱五层（surface…wound） | 实体卡「设定」节自由结构 + `rubrics/voice.md` 声纹判据 | 五层可作写卡参考，不再机器校验 |
| 别名归一（ProseUnit/ThreadMap 等废弃名） | 本表 §1 即归一登记处 | 旧项目文件中出现照旧，勿迁移 |
