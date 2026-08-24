# tools/ — 工具链说明

python3 标准库实现，零第三方依赖。契约 SSOT 见 `../protocol/formats.md`（§15–17）。

## novel.py — 项目核心 CLI

```bash
python3 tools/novel.py --help          # 全部子命令
python3 tools/tests/test_smoke.py      # 端到端冒烟（101 步，含 15 条负例）
python3 tools/tests/test_longrun.py    # 35 章长程合成（规模化不变量）
```

### 实现覆盖表（对照 formats §15/§16）

| 命令 | 状态 | 说明 |
|---|---|---|
| `init` `status` `fsck` | ✅ | status 增量重算 `state/index.json`（章级按 mtime）+ `dashboard.md`，打印断点与深评逾期提醒 |
| `tree add/show/set-status` | ✅ | set-status 校验迁移合法性；chapter→approved 需评审 pass 回执或 `--evidence` |
| `task add/next/list/start/done/fail` | ✅ | 依赖完成的 blocked 自动解锁→pending；fail 达 2 次自动升级 revise_design |
| `task reset` / `task archive` | ✅ | reset：failed/running→pending；archive：done 迁入 `tasks/archive.json`（`--keep N`） |
| `entity new/show/log/due/update`、`thread new` | ✅ | new 为便捷扩展（模板实例化） |
| `brief <ch>` | ✅ | 十节+溯源；§2 注入 recap；§4 按 volume_scope/payoff_planned 召回；预算超限按 §7→§6→§4→§3 裁剪留痕 |
| `check --unit [--candidate F --writeback F]` | ✅ | 断言明细见下；回写引用越权（未登记实体/线索/非法迁移）FAIL |
| `check --window [--since ch]` / `check --project` | ✅ | 窗口含战力变更频率告警；project 含 decision/review 文件契约校验 |
| `check --leak <候选> --brief <简报>` | ✅ | 已登记专名（实体+别名）出现在候选但不在简报 → 逐条列出 |
| `commit`（write/revise/design/revise_design/review_deep） | ✅ | 唯一写路径：先验后写零部分落盘；含 facts 登记/战力台账/两级 ngram/stale 递归传播；design 支持 `--draft` 部分落盘 |
| `publish` | ✅ | 连续性谓词（自 last_published+1）+ approved 校验 + 首发 buffer 校验 |
| `ledger payoff/promise/timeline/power` | ✅ | 台账视图 |
| `retcon` | ✅ | 校验 old_fact_id 与 decision 文件真实存在；追加 retcons[] 作废链，不改旧事实原文 |
| `report volume` / `checkpoint` | ✅ | report 产出 `state/reports/vol_NN.md`（导出对账/线索健康/爽点·战力统计）；checkpoint 要求报告绿，收卷并预填下卷 imports |
| `adopt <file> --as ch_NNNN` | ✅ | 存量旧稿收编：落盘 drafted 章 + task/meta 骨架 + ngram 指纹（协议见 `protocol/adopt.md`） |

### check 断言分级

- **FAIL（阻塞 commit）**：信封/必需节缺失、状态枚举/迁移非法、字数越带、style 黑名单命中、
  连续 3 句同首、writeback 缺键、payoff 越界或 id 章号不匹配、continuity_delta 缺 spoiler、
  回写引用未登记实体/线索、线索状态机非法迁移、published 空洞、facts 断链、must_not_drop 被弃线、
  decision/review 契约违例。
- **WARN（放行但留痕）**：章内 4-gram 重复率 >2%、连续 3 段同首、跨章 12 字指纹复读、
  8 字指纹撞梗超阈、word_count 偏差 >10%、promise 余额失衡、线索悬置 >15 章、buffer=0、
  10 章内战力变更 ≥3 次。
- **NEEDS_REVIEW（必须由评审角色裁定，工具不假装通过）**：声纹遮名指认、智商漂移、
  关键场面占比、爽点有效性、毒点七问、句式级口癖、facts 同实体冲突候选——对应 `rubrics/` 各卡。

### 实现注记

- frontmatter 为**宽松行解析**（扁平 `key: value` + 内联 JSON），非完整 YAML；
  模板占位 `[方括号]` 不破坏解析。
- 黑名单从项目 `tree/style.md`「口癖与句式禁忌」节逐条解析：全角括号交替展开
  （`一道（倩影/身影）闪过` → 两个候选串）、二选一共尾启发（`眼底/眼中闪过一丝`）、
  `>N 次` 阈值条目按合计计数；`句式级` 描述性条目转 NEEDS_REVIEW。
- 跨章重复用**两级指纹**：12 字级（字面复读，per-章命中超阈升 FAIL 级告警）+
  8 字级（撞梗雷达，仅 WARN），缓存于 `state/ngram_cache.json`，
  保留最近 `ngram_window_chapters` 章。
- facts 登记：commit 时自 writeback 的 `continuity_delta` 自动分配全局递增 `fact_id`
  写入 `ledgers/facts/vol_NN.json`；冲突候选（同实体同 key 矛盾/高相似）在 check 期提示。
- git 操作全部 best-effort：无 git 时降级为原子写入并提示。

## tests/

- `test_smoke.py`：临时目录内完整跑 init → 设计 commit（含 --draft/缺节负例）→ 排批 →
  brief → staging 机检（黑名单/越权引用/payoff 章号/spoiler 缺失/非法线索迁移等负例）→
  commit 回写效应断言 → retcon → 队列 reset/archive → approved 回执闸门 → publish →
  report/checkpoint → check --leak → adopt → 两级 ngram → --since 窗口 →
  decision/review 契约负例 → fsck。101 步全绿（含 15 条负例拒绝）。
- `test_longrun.py`：35 章连载全链合成（固定 seed），验证规模化不变量：
  fact_id 无碰撞累积、ngram 窗口裁剪、entity due 阈值触发、power 台账、
  task archive 收缩、published 连续性与全库检查全绿。

CI/本地一条命令复跑，绿=工具链可用。
