---
id: [thread_slug]
kind: thread
thread_kind: fuse
state: planted
must_not_drop: false
volume_scope: []
plant_ch: null
payoff_planned: null
status: active
rev: 1
updated_at: [YYYY-MM-DDTHH:MM:SSZ]
---

## 陈述

[本线一句话:埋什么/承诺什么/欲望对抗是什么。thread_kind:fuse=引线|subplot=支线|relationship=关系|mystery=谜团|promise=承诺|other]
[状态机:planted→active→tangled→payoff_ready→paid_off;任意态可 dropped;部分兑现保持 active 并在日志记 partial]
[纪律:must_not_drop=true 置 dropped 须裁决引用(note 含 dec_id);paid_off/dropped 不入简报召回;召回=active ∩ 本卷 volume_scope 或 payoff_planned 命中]

## 推进日志

[novel.py commit 自 thread_ops 追加「- ch_0212: advance 一句话」;op 枚举 plant|advance|payoff|tangle;推进写法:加压/假线索/半揭示/关系位移;禁手改]
