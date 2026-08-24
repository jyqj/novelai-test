# capability-profiles.md — 四档能力边界（L5 适配层 SSOT）

> 取代散落各文件的降级注记；冷启动时按探测结果选用一档并向用户明示损失清单。

## 1. 四档定义

| 档位 | 条件 | 可用能力 |
|---|---|---|
| **full** | spawn + shell + git | 全套 gate / 机检 / 指纹 / 队列 / journal |
| **no-subagent** | solo 模式 | 同 full 机器层；庭审合并为帽子协议 |
| **no-shell** | 无 python3 CLI | 文件契约手工维护；**丢失**：指纹、facts 扫描、队列自动化、gate 强制 |
| **no-git** | 无 git | 同 shell 但无 autocommit；journal/fsck 仍可用 |

## 2. no-shell 最小人工台账

每章 commit 后手工核对：

| 台账 | 核对项 |
|---|---|
| payoff.tsv | 行数 = quota 数；realized 与正文一致 |
| timeline.tsv | elapsed 非负 |
| entities/*.md | 事件日志无重复 `- ch_NNNN:` 行 |
| facts/vol_*.json | 无同 key 矛盾 |

## 3. 用户告知话术（SKILL §1）

「当前环境为 **{profile}** 档：{损失清单}。强烈建议争取 shell 以启用完整一致性引擎。」
