# tools/ — 工具链说明

python3 标准库实现，零第三方依赖。契约 SSOT 见 `../protocol/formats.md`（§15–17）。

## novel.py — 项目核心 CLI

```bash
python3 tools/novel.py --help          # 全部子命令
python3 tools/tests/test_smoke.py      # 端到端冒烟（113 步，含 17 条负例）
python3 tools/tests/test_longrun.py    # 35 章长程合成（规模化不变量+中途返修）
python3 tools/tests/test_refactor.py   # P0–P4 重构专项回归（148 步）
python3 tools/tests/test_stage.py      # 阶段×知识编排（文档对账+所有权分区+阶段闸门）
python3 tools/tests/test_matrix.py     # P8-M 知识矩阵 v2（范围知情圈全链路）
```

### 代码布局：novel.py 薄壳 + novel_lib/ 按工作流关切拆分

`tools/novel.py` 只是转发壳（对外入口与退出码不变）；实现在 `tools/novel_lib/`
按工作流环节分模块（一模块 = 一关切，依赖单向无环）：

| 模块 | 关切（对应 protocol/workflow.md 环节） |
|---|---|
| `common.py` | 共享底座：frontmatter/节解析、原子写、git、线索状态机、文本指纹、故事日历、Report |
| `project.py` | 项目对象（Project）与任务队列读写 |
| `stagectl.py` | 阶段状态机：`state/stage.json` 持久化、stage enter/current、stage_guard 闸门 |
| `bootstrap.py` | init 脚手架 / adopt 存量收编 |
| `structure.py` | 树节点（tree）与任务队列 CLI（task） |
| `journal.py` | 台账与卡片：entity / thread / ledger / facts |
| `brief.py` | 简报编译器（十节装配 + 条目级预算裁剪 + 知识矩阵注入） |
| `extract.py` | 抽取器：正文反向解析 + writeback 对账 + 知识越界候选 |
| `checks.py` | 断言集：check --unit/--leak/--window/--project |
| `commitflow.py` | 唯一写路径：commit（事务日志 + 撤销重放 + 台账回写 + ngram） |
| `rollup.py` | 章→弧→卷摘要卷积 |
| `serial_ops.py` | 连载运营：publish / retcon / report volume / checkpoint |
| `review.py` | 评审回执（review add/list） |
| `knowledge.py` | 知识矩阵（fact × 角色 × 读者 × 域）：grant/reveal/scope/query |
| `gate.py` | 闸门家族：next/write/approve/publish/checkpoint（只判不写） |
| `court.py` | 庭审工作区（state/court/ open/status/close） |
| `status.py` | status（index/dashboard 重算） |
| `cli.py` | argparse 装配与子命令分发 |

### 实现覆盖表（对照 formats §15/§16）

| 命令 | 状态 | 说明 |
|---|---|---|
| `init` `status` `fsck` | ✅ | status 增量重算 `state/index.json`（章级按 mtime）+ `dashboard.md`，打印断点与深评逾期提醒；fsck 含半事务检出 |
| `tree add/show/set-status` | ✅ | set-status 校验迁移合法性；chapter→approved **仅认 reviews/ 落盘回执**（verdict=pass ∧ rev_reviewed=章当前 rev） |
| `task add/next/list/start/done/fail` | ✅ | 依赖完成的 blocked 自动解锁→pending；fail 达 2 次自动升级 revise_design |
| `task reset` / `task archive` | ✅ | reset：failed/running→pending；archive：done 迁入 `tasks/archive.json`（`--keep N`） |
| `entity new/show/log/due/update`、`thread new` | ✅ | new 为便捷扩展（模板实例化） |
| `brief <ch>` | ✅ | **条目级预算**：逐条打分排序+must-not-drop 集，超预算从最低分裁起逐项留痕；§2 注入 rollup（弧/卷卷积）+recap；§3 声纹速查独立块；§4 按 volume_scope/payoff_planned 召回 |
| `check --unit [--candidate F --writeback F]` | ✅ | 断言明细见下；回写引用越权（未登记实体/线索/非法迁移）FAIL；含抽取器对账 |
| `check --window [--since ch]` / `check --project` | ✅ | 窗口含战力变更频率告警+**故事日历**（elapsed 数值化/story_date 单调）；project 含 decision/review 契约校验+半事务检出 |
| `check --leak <候选> --brief <简报>` | ✅ | 已登记专名（实体+别名）出现在候选但不在简报 → 逐条列出 |
| `commit`（write/revise/design/revise_design/review_deep/revise_rubric） | ✅ | 唯一写路径：先验后写零部分落盘+**state/txn 事务日志**；台账带 rev 列（(chapter,rev) 语义）；**revise 撤销重放零双计**；design 两遍制多文件原子；含 facts 登记（**含 known_by 知情名单**）/rollup 重算/分层 ngram/stale 递归传播；`--draft` 部分落盘；**revise_rubric=蒸馏轻量路径**（限 style，rev 自动+1，无 stale） |
| `publish` | ✅ | 连续性谓词（自 last_published+1）+ approved 校验 + 首发 buffer 校验 |
| `ledger payoff/promise/timeline/power` | ✅ | 台账视图（读侧按 (chapter) 取最新 rev 去重；timeline 含累计天数） |
| `retcon` | ✅ | 校验 old_fact_id 与 decision 文件真实存在；追加 retcons[] 作废链，不改旧事实原文 |
| `report volume` / `checkpoint` | ✅ | report 产出 `state/reports/vol_NN.md`（导出对账/线索健康/爽点·战力统计）；checkpoint 要求报告绿，收卷并预填下卷 imports |
| `adopt <file> --as ch_NNNN` | ✅ | 存量旧稿收编：落盘 drafted 章 + task/meta 骨架 + ngram 指纹（协议见 `protocol/adopt.md`） |
| `review add/list` | ✅ | 评审回执落盘 reviews/（rev_reviewed 默认=章当前 rev）——approved 闸门唯一回执载体 |
| `facts import/list` | ✅ | import=adopt 补录机械半边（幂等，顺带刷新 rollup）；list 支持 `--entity` 过滤，视图带 spoiler/知情名单标记 |
| `knowledge grant/reveal/scope/query` | ✅ | 知识矩阵 v2（fact×角色/范围×读者）：grant 授予知情（known_by 追加；char 个体或 fac/loc/item 范围）；reveal 读者揭示销账（spoiler→0 记 revealed_reader_ch）；scope add/remove/list 知情圈维护（群体→char 成员，entities/scopes.json）；query 矩阵视图（单条/个体或群体知与不知含圈展开/读者未知欠账盘点） |
| `rollup` | ✅ | 手动重算章→弧→卷摘要卷积（批量手改 meta.json/adopt 补录后；commit 路径已自动） |
| `extract <ch> [--candidate --writeback]` | ✅ | 抽取器独立入口：出场实测 vs cast_actual、引号新专名候选、剧透泄漏候选、known_by 角色知识越界候选（角色卡 `roles/extractor.md`） |
| `gate next/write/approve/publish/checkpoint` | ✅ | 编排剧本机器半边：next 输出优先级调度（修账>深评>对账>**欠账**[spoiler 挂账 ≥`spoiler_debt_chapters` 章]>缓冲>推进），末段附**已进入阶段+配套知识包路径**（未进入时打提醒，advisory）；其余为各关口前置谓词（只判不写，且受阶段闸门辖区约束）；**每条 FAIL 附「↳ 下一步」可执行修复命令** |
| `court open/status/close` | ✅ | 庭审工作区机械管理：open 建场次+R0 骨架；close 校验裁决落盘后清场 |
| `stage list/show/enter/current` | ✅ | 阶段状态机（P6-S/P7-S）：list=11 阶段总表；show=打印配套知识包全文（`protocol/stages/`）；**enter=进入阶段（写 `state/stage.json`，受辖操作的钥匙）**；current=读持久化阶段+启发式核对（未进入任何阶段 exit 1）。受辖命令（court open/brief/commit/publish/checkpoint/gate write…）阶段不匹配即拒绝并给 enter 提示——辖区表见 `protocol/formats.md` §15（SSOT=`protocol/knowledge-orchestration.md` §5） |

### check 断言分级

- **FAIL（阻塞 commit）**：信封/必需节缺失、状态枚举/迁移非法、字数越带、style 黑名单命中、
  连续 3 句同首、writeback 缺键、payoff 越界或 id 章号不匹配、continuity_delta 缺 spoiler、
  回写引用未登记实体/线索、线索状态机非法迁移、published 空洞、facts 断链、must_not_drop 被弃线、
  decision/review 契约违例。
- **WARN（放行但留痕）**：章内 4-gram 重复率 >2%、连续 3 段同首、跨章 12 字指纹复读、
  8 字指纹撞梗超阈、word_count 偏差 >10%、promise 余额失衡、线索悬置 >15 章、buffer=0、
  10 章内战力变更 ≥3 次、抽取器未申报出场/幽灵出场。
- **NEEDS_REVIEW（必须由评审角色裁定，工具不假装通过）**：声纹遮名指认、智商漂移、
  关键场面占比、爽点有效性、毒点七问、句式级口癖、facts 同实体冲突候选、
  引号新专名候选、剧透泄漏候选——对应 `rubrics/` 各卡。

### 实现注记

- frontmatter 为**宽松行解析**（扁平 `key: value` + 内联 JSON），非完整 YAML；
  模板占位 `[方括号]` 不破坏解析。
- 黑名单从项目 `tree/style.md`「口癖与句式禁忌」节逐条解析：全角括号交替展开
  （`一道（倩影/身影）闪过` → 两个候选串）、二选一共尾启发（`眼底/眼中闪过一丝`）、
  `>N 次` 阈值条目按合计计数；`句式级` 描述性条目转 NEEDS_REVIEW。
- 跨章重复用**分层指纹**：窗口内（最近 `ngram_window_chapters` 章）12 字级全量
  （字面复读，per-章命中超阈升 FAIL 级告警）+ 8 字级全量（撞梗雷达，仅 WARN）；
  窗口外降级为归档层（12 字指纹稳定降采样 ≤`ngram_archive_sample` 条/章）——
  自我复读检测覆盖全史而缓存体积有界。缓存于 `state/ngram_cache.json`。
- facts 登记：commit 时自 writeback 的 `continuity_delta` 自动分配全局递增 `fact_id`
  写入 `ledgers/facts/vol_NN.json`；冲突候选（同实体同 key 矛盾/高相似）在 check 期提示。
- 原子提交：多文件落盘以 `state/txn/` journal 包裹（写前 done=false、写毕 done=true）；
  崩溃残留由 fsck 检出。revise 的台账语义见 formats §9（TSV append-only + 读侧去重；
  实体/线索日志撤销重放）。
- git 操作全部 best-effort：无 git 时降级为原子写入并提示。

## tests/

- `test_smoke.py`：临时目录内完整跑 init → 设计 commit（含 --draft/缺节负例）→ 排批 →
  brief → staging 机检（黑名单/越权引用/payoff 章号/spoiler 缺失/非法线索迁移等负例）→
  commit 回写效应断言 → retcon → 队列 reset/archive → approved 回执闸门 → publish →
  report/checkpoint → check --leak → adopt → 两级 ngram → --since 窗口 →
  decision/review 契约负例 → fsck。101 步全绿（含 15 条负例拒绝）。
- `test_longrun.py`：35 章连载全链合成（固定 seed），验证规模化不变量：
  fact_id 无碰撞累积、分层 ngram（全史在册+窗口全量+归档降采样）、entity due 阈值触发、
  power 台账、task archive 收缩、published 连续性与全库检查全绿。
- `test_refactor.py`：P0–P3 重构专项（92 步）：(chapter,rev) 零双计（终态线撤销重放/
  facts 先剪后登/读侧去重）、回执收紧负例、半事务检出、facts import 幂等、rollup 卷积
  与简报注入、条目级预算裁剪与 must-not-drop、声纹独立块、抽取器对账、故事日历倒流、
  gate 家族、court 工作区。
- `test_stage.py`：阶段×知识编排（P6-S/P7-S/P8-K）——文档契约半边：11 个阶段包齐全且
  ≤80 行、六设计庭 K 池 ≡ knowledge-map 所有权标注（单场单标）、产线四包零 K-ID、
  diag 包 ≡ 诊断池、rubrics 脚注 ≡ 蒸馏列、knowledge/ 锚点 ≡ map 行、引用死链扫描、
  **所有权分区**（运行期各池两两不相交+三类归属切完 111 块+卡/人设/节奏唯一所有阶段
  +借用署名+全库索引零残留）；CLI 半边：stage enter/current 持久化与推断核对、
  阶段闸门正负例（未进阶段/错阶段拒绝+enter 提示、history 迁移轨迹）、traditional
  叠加提示、gate next 阶段行与 spoiler 欠账消费（超龄顶出/未超龄不出现）。
- `test_matrix.py`：P8-M 知识矩阵 v2（53 步）——知情圈 CLI 正负例（类型/登记/除名）、
  scope add/remove 受阶段闸门辖、范围 grant 与空圈提醒、query 圈展开（个体经圈/群体
  视图）、简报【知情仅】圈展开与在场不知情按展开计算、抽取器越界按有效知情集（圈成员
  不误报/入圈销案）、check --project 圈台账 FAIL/空圈 WARN。

CI/本地一条命令复跑，绿=工具链可用。
