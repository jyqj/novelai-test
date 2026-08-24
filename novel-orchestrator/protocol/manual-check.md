# manual-check.md — 无 shell 环境的人工自查清单（诚实降级协议）

> 适用：产品无法运行 `python3 tools/novel.py` 时。本文件回答两个问题：
> ① 哪些机检项**可以**人工执行（附步骤）；② 哪些能力在无 shell 时**直接丢失**，
> 不存在"人工替代"——必须向用户明示风险，不得假装等效。
> 有 shell 的环境一律用 CLI，本文件不适用。

## 0. 总纪律

1. 人工自查的每一项，结论写进该章 writeback 的 `issues`，前缀 `manual-check:`
   （例：`manual-check: 黑名单逐条扫描通过`）。没写 = 没查。
2. 本清单只覆盖 `check` 的机器断言。主观项（声纹遮名指认、智商漂移、爽点有效性、
   毒点七问）在有无 shell 时都走评审角色，见各 rubrics/ 卡，与本文件无关。
3. 无 shell 时文件仍按 `protocol/formats.md` 契约手工维护；没有 git 时，
   改文件前先复制一份 `.bak`（唯一的回滚手段）。

## 1. 可人工执行项（逐条替代表）

| 机检项（check 对应断言） | 人工步骤 | 可靠度 |
|---|---|---|
| 字数 ∈ word_target±15% | 数正文字符（去空白）；对照任务卡区间 | 高 |
| style 黑名单命中=0 | 打开 `tree/style.md` 禁忌节，逐条在正文里搜词 | 高（条目多时易漏） |
| 末段总结化句式 | 只查最后一段，对黑名单末段组逐条搜 | 高 |
| 连续 3 句同首词 | 通读正文，盯句首二字 | 中 |
| writeback schema 齐全 | 对照 `templates/chapter.meta.json` 九键逐一核对 | 高 |
| continuity_delta 实体已登记 | 每个 entity_id 去 `entities/` 与 aliases.json 里找 | 高 |
| thread_ops 线索已登记+迁移合法 | 查 `threads/`；对照 formats §8 迁移表核状态 | 高 |
| payoff_realized ⊆ quota 且章号匹配 | 数 quota 条数；核 id 中的章号 | 高 |
| hooks_realized.close（web 强制） | 核 writeback；false 时 issues 必须说明 | 高 |
| published 连续性 | 排 chapters/ 目录，确认 published 无空洞 | 高 |
| 时间线 elapsed 非负 | 查 `ledgers/timeline.tsv` 第三列 | 高 |
| facts/retcon 引用完整 | retcons[] 的 old_fact_id 逐条回查 facts[] | 中 |
| 必需标题节齐全（design 定稿前） | 对照 formats §4 节名清单逐节核对 | 高 |
| 3 章/10 章爽点窗口 | 翻 `ledgers/payoff.tsv` 手数 realized | 中（章多后极易错） |

人工替代 CLI 回写动作（commit 的落盘副作用，全部要手做，漏一项台账即断）：
实体事件日志追加、线索推进日志+state 迁移+plant_ch 回填、payoff/timeline/power 台账
追加、**facts 登记（自 continuity_delta 手工分配递增 fact_id 写入
`ledgers/facts/vol_NN.json`）**。

## 2. 无 shell 时直接丢失的能力（不可判定项，须向用户明示）

| 丢失能力 | 后果 | 缓解（非等效） |
|---|---|---|
| 跨章 12-gram / 8-gram 指纹 | 自我复读与撞梗**不可检**——人记不住 30 章的字级指纹 | 深评抽查窗口内肉眼比对，覆盖率低 |
| 章内 4-gram 重复率 | 无法量化；只能靠语感 | 评审主观判断 |
| ngram_cache / index / dashboard 生成物 | 无断点仪表盘；恢复靠通读队列文件 | 手工维护一页进度笔记（易漂移） |
| 队列自动化（blocked 解锁/fail 升级/归档） | 依赖关系靠人脑，长队列必错 | 队列保持 ≤10 条 |
| brief 机械装配与预算裁剪 | 简报靠手抄，溯源与预算不可保证 | 按 formats §6 十节清单手工装配 |
| facts 冲突扫描 | 同实体矛盾候选无人提示 | 写入前人工回读该实体全部 facts |
| 泄漏扫描（check --leak） | 已登记专名的机械比对丢失 | 轻评人工抽查 |
| git 事务与工作区清洁检查 | 无回滚、无泄漏检查基线 | `.bak` 副本 + 单写者纪律自觉 |

**结论**：无 shell 属**有损降级**。协议与文件契约可继续执行，但一致性保障从
"机器强制"退化为"人工尽力"。编排者必须在项目启动时向用户声明上表损失
（unattended 模式写入首个 task note），并强烈建议争取 shell。
