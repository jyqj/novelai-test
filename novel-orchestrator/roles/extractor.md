# extractor — 正文反向抽取与对账（L2 一致性 · 机器半边）

> 完整双记账需配合 `novel.py check --unit` 的 extractor 断言 + 轻评人工裁定。

## 输入

- 候选正文（或已落盘章）
- writeback JSON
- 项目 entities/aliases、tree/world.md 位阶表

## 输出契约

```json
{
  "cast_mentioned": ["char_*"],
  "cast_missing_in_writeback": ["char_*"],
  "power_terms_hit": ["位阶词"],
  "spoiler_leaks": ["fact 片段"],
  "issues": []
}
```

## 纪律

- 只报**已登记**专名/位阶词；新发明专名交 NEEDS_REVIEW + 轻评。
- 不修改任何项目文件；diff 附进轻评 spawn 附件。
- CLI 已实现：`check --unit` 内 `extract_reconcile()`。
