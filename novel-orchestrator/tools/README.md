# tools/ — 工具链说明

python3 标准库实现，零第三方依赖。契约 SSOT 见 `../protocol/formats.md`（§15–17）。

## novel.py — v2 项目核心 CLI

```bash
python3 tools/novel.py --help          # 全部子命令
python3 tools/tests/test_smoke.py      # 端到端冒烟（31 步，含 2 条负例）
```

### 实现覆盖表（对照 formats §15/§16）

| 命令 | 状态 | 说明 |
|---|---|---|
| `init` `status` `fsck` | ✅ | status 重算 `state/index.json` + `dashboard.md`，打印可恢复断点 |
| `tree add/show/set-status` | ✅ | add 支持 volume/arc/chapter；set-status 校验迁移合法性 |
| `task add/next/list/start/done/fail` | ✅ | fail 达 2 次自动升级 revise_design；revise_design 强制 `--evidence` |
| `entity new/show/log/due/update`、`thread new` | ✅ | new 为便捷扩展（formats 未列，模板实例化） |
| `brief <ch>` | ✅ | 十节+溯源；预算超限按 §7→§6→§4 顺序裁剪并留痕；生成后自动 git commit |
| `check --unit [--candidate F --writeback F]` | ✅ | 支持未落盘 staging 机检；断言明细见下 |
| `check --window` / `check --project` | ✅ | route=traditional 时爽点窗口降为 WARN |
| `commit`（write/revise/design/revise_design/review_deep） | ✅ | 唯一写路径：机检绿才落盘；含实体/线索/台账/ngram 回写与 stale 传播 |
| `publish` | ✅ | 连续性谓词（自 last_published+1）+ approved 校验 + 首发 buffer 校验 |
| `ledger payoff/promise/timeline` | ✅ | 台账视图 |
| `retcon` | ⬜ 手工 | 按 `protocol/serial-ops.md` §3 编辑 facts；引用完整性由 `check --project` 兜底 |
| `report volume` / `checkpoint` / reconcile 汇总 | ⬜ 手工 | 以 `status`/`ledger`/`check` 输出为素材，按 serial-ops §4–5 执行 |

### check 断言分级

- **FAIL（阻塞 commit）**：信封/必需节缺失、状态枚举/迁移非法、字数越带、style 黑名单命中、
  连续 3 句同首、writeback 缺键、payoff 越界、published 空洞、facts 断链、must_not_drop 被弃线。
- **WARN（放行但留痕）**：章内 4-gram 重复率 >2%、连续 3 段同首、跨章 12 字指纹重复、
  word_count 偏差 >10%、promise 余额失衡、线索悬置 >15 章、buffer=0。
- **NEEDS_REVIEW（必须由评审角色裁定，工具不假装通过）**：声纹遮名指认、智商漂移、
  关键场面占比、爽点有效性、毒点七问、句式级口癖——对应 `rubrics/` 各卡。

### 实现注记

- frontmatter 为**宽松行解析**（扁平 `key: value` + 内联 JSON），非完整 YAML；
  模板占位 `[方括号]` 不破坏解析。
- 黑名单从项目 `tree/style.md`「口癖与句式禁忌」节逐条解析：全角括号交替展开
  （`一道（倩影/身影）闪过` → 两个候选串）、二选一共尾启发（`眼底/眼中闪过一丝`）、
  `>N 次` 阈值条目按合计计数；`句式级` 描述性条目转 NEEDS_REVIEW。
- 跨章重复用 **12 字级指纹**（formats §17 已注：较 4-gram 少误报），
  缓存于 `state/ngram_cache.json`，保留最近 `ngram_window_chapters` 章。
- git 操作全部 best-effort：无 git 时降级为原子写入并提示。

## validate.py — v1 收编校验器

v1（legacy）原版工具，两个仍然有用的场景：

```bash
python3 tools/validate.py --skill ..                 # 知识库锚点/登记处对账（K-ID 锚点在 v2 继续服役）
python3 tools/validate.py --project <v1项目目录>     # 校验按 v1 格式建的旧项目（迁移前体检）
python3 tools/validate.py --unit <ms.md> --style <style_card.md>   # v1 格式单章机检
```

v2 项目一律用 `novel.py check`；validate.py 的 `--skill` 模式部分检查项针对 v1 目录布局
（runtime/phases），对 v2 会报 SKIP/WARN，属预期。

## tests/

`test_smoke.py`：临时目录内完整跑一遍 init → 设计 commit → 排批 → brief → staging 机检
→ commit → 窗口/全库检查 → approve → publish，并验证两条拒绝路径（黑名单命中、跳章发布）。
CI/本地一条命令复跑，绿=工具链可用。
