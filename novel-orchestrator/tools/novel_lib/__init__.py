# -*- coding: utf-8 -*-
"""novel_lib — novel.py 的按工作流关切拆分的实现包（python3 stdlib only）。

模块 = 工作流关切（与 protocol/workflow.md 各环节对应）：

  common      共享底座：frontmatter/节解析、原子写、git、线索状态机、文本指纹、故事日历、Report
  project     项目对象（Project）与任务队列读写
  stagectl    阶段状态机：state/stage.json 持久化、stage enter/current、stage_guard 强制闸门
  bootstrap   init 脚手架 / adopt 存量收编
  structure   树节点（tree add/show/set-status）与任务队列 CLI（task ...）
  journal     台账与卡片：entity / thread / ledger / facts（register_facts 登记半边）
  brief       简报编译器（十节装配 + 条目级预算裁剪 + 知识矩阵注入）
  extract     抽取器（正文反向解析 + writeback 对账 + 知识越界候选）
  checks      断言集：check --unit/--leak/--window/--project（含黑名单/日历/指纹）
  commitflow  唯一写路径：commit（事务日志 + 撤销重放 + 台账回写 + ngram/rollup）
  rollup      章→弧→卷摘要卷积
  serial_ops  连载运营：publish / retcon / report volume / checkpoint
  review      评审回执（review add/list + approved 回执谓词）
  knowledge   知识矩阵（fact × 角色 × 读者 × 域）：grant/reveal/scope/query
  gate        闸门家族：next/write/approve/publish/checkpoint（只判不写）
  court       庭审工作区（state/court/ open/status/close）
  status      status（index/dashboard 重算）
  cli         argparse 装配与子命令分发（tools/novel.py 薄壳的唯一入口）

对外入口不变：python3 tools/novel.py …（tools/novel.py 是薄壳，转发 novel_lib.cli.main）。
"""
