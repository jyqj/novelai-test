#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""novel.py — novel-orchestrator 项目 CLI 薄壳（python3 stdlib only）。

实现按工作流关切拆分在 tools/novel_lib/ 包内（模块清单见 novel_lib/__init__.py 与
tools/README.md）；本文件只负责把 `python3 tools/novel.py …` 转发到 novel_lib.cli.main，
对外入口与退出码契约不变：

  init <dir> [--name X]              脚手架 + （可选）git init
  status                             重算 index/dashboard 并打印（可恢复断点；章级增量）
  tree add <kind> <id> [--parent P]  由模板实例化节点（volume/arc/chapter）
  tree show [id] / tree set-status <id> <status> [--evidence E]
  task add <type> <target> [...] / next / list / start / done / fail / reset / archive
  entity new <id> / show <id> / log <id> / due / update <id> --file F
  thread new <id> [--kind K]
  brief <ch_id>                      机械装配十节简报（预算裁剪 + 溯源）
  check --unit <ch> [--candidate F --writeback F] | --window [--since CH] | --project
  check --leak <候选章> --brief <简报>   简报外专名泄漏扫描
  commit <task_id> [--chapter F --writeback F] [--file F ...] [--draft] [-m 摘要]
  publish <ch_from> [<ch_to>]        连续性谓词；approved → published
  retcon <old_fact_id> --new … --strategy … --decision dec_id
  report volume <vol_NN>             汇编卷报告（exports 对账底稿 + 台账统计）
  checkpoint <vol_NN>                卷末结账：校验对账三态 + 下卷 imports 预填
  adopt <file> --as ch_NNNN          收编外部文稿为项目章（protocol/adopt.md）
  ledger payoff|promise|timeline|power   台账窗口视图
  review add/list ｜ facts import/list ｜ knowledge grant/reveal/query
  extract <ch> ｜ rollup ｜ gate next/write/approve/publish/checkpoint
  stage list/show/current ｜ court open/status/close ｜ fsck

退出码：0=通过（可含 WARN/NEEDS_REVIEW）；1=存在 FAIL/校验拒绝；2=用法或环境错误。
主观判定项（遮名指认/智商漂移/关键场面占比等）输出 NEEDS_REVIEW，交由评审角色执行，
本工具不假装通过。frontmatter 为宽松行解析（扁平 key: value + 内联 JSON），非完整 YAML。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from novel_lib.cli import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
