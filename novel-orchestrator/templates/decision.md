---
id: [dec_001_slug]
kind: decision
node: [book]
session: [S1]
date: [YYYY-MM-DD]
status: active
---

## 选项

[每行一案,含未采纳案。session 枚举:S1|S2|S3|S4|volume|arc|adhoc]

- [案id] | [提案角色] | [一句话]

## 裁决

[选择+理由:采纳哪案(可杂交)、为何、影响面(受波及节点/实体/章)。红线类 blocking 未解须升级用户;transcripts 归档 court/transcripts/,永不入召回]

## 否决案

[每案必填 reopen_requires;无新证据禁止重提——novel.py 建 revise_design 任务时以 evidence 字段比对本台账]

- [案id] | [否决理由] | reopen_requires: [重开所需的新证据类型]

## 异议

[保留 disagree_and_commit 痕迹,不重开讨论]

- [角色] | [意见] | resolution: [disagree_and_commit|adopted]
