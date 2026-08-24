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
[状态机(合法迁移表由 novel.py 强制,formats §8):plant→planted;advance→active;tangle→tangled;ready→payoff_ready;payoff→paid_off。paid_off/dropped 为终态,不接受任何 op;部分兑现保持 active 并在日志记 partial]
[纪律:must_not_drop=true 置 dropped 须裁决引用(note 含 dec_id 且 court/ 中真实存在);paid_off/dropped 不入简报召回;召回=live 态 ∩ (must_not_drop ∪ 本卷 volume_scope ∪ payoff_planned 临近)]

## 推进日志

[novel.py commit 自 thread_ops 追加「- ch_0212: advance 一句话」;op 枚举 plant|advance|payoff|tangle|ready;plant 自动回填 plant_ch;推进写法:加压/假线索/半揭示/关系位移;禁手改]
