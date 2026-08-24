# calendar.md — 故事日历契约（L2 一致性引擎 · 时间维）

> 台账：`ledgers/timeline.tsv`（chapter, rev, story_date, elapsed, note）。

## 1. 字段语义

| 字段 | 格式 | 说明 |
|---|---|---|
| story_date | ISO8601 或 `Day N` | 章后故事绝对时点（卷内统一一种） |
| elapsed | 正整数+单位，如 `2天` `6时辰` | 本章推进量；机检拒绝负 elapsed |
| note | 自由文本 | 闰日/跳时/回忆杀标注 |

## 2. 断言（roadmap）

- v2.1：elapsed 非负（已实现）。
- v2.2：同卷 story_date 单调（NEEDS_REVIEW → 设定审计）。
- v2.3：elapsed 数值化字段 `elapsed_hours`（可选列）供窗口统计。

## 3. writeback

`time_advance` 必填 `elapsed`；有绝对日历时填 `story_date`。
