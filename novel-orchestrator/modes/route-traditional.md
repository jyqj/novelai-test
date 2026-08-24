# route-traditional — 传统长篇差分层

适用：出版向长篇/严肃文学/一次写完再发、无连载压力。**这不是独立模式**：先按能力选
`mode-orchestrated` 或 `mode-solo`，再叠加本文件的覆盖规则。收编自 v1（已移除）的
`route_delta` 双轨差分思想（术语映射见 protocol/glossary.md §2）。

启用：`config.json` 设 `"route": "traditional"`。CLI 已按此降级相应断言（见 §3）。

## 1. 工序差分（对照 web 默认）

| 环节 | web（默认） | traditional（本差分） |
|---|---|---|
| 发布 | buffer 水位 + publish + retcon | **无 buffer/publish**。章止于 `approved`；全书完稿后统一定稿导出，`publish`/`serial-ops §1–3` 不使用 |
| 全书骨架 | 分卷草案 + 卷内自选节奏 | 书庭 S4 以 **rhythm/classic24.md 做全书 24 节拍骨架**（节拍映射到卷/弧边界），弧内模板仍五选一 |
| 排批粒度 | 章任务卡（goal+3 拍+钩） | **加细纲工序**：见 §2 |
| 章长 | 2000–4500 硬带 | 节奏优先、章长灵活：在 task.json 逐章覆盖 `word_target`（如 [1500, 9000]） |
| 章尾钩 | 强制（close=false 即 FAIL） | 建议级：close=false 且 issues 说明 → WARN；但**连续 3 章无价值翻转仍违规**（深评把关） |
| 爽点窗口 | 3 章/10 章硬窗口 | 降为建议（check --window 输出 WARN）；改盯「每章价值转变」与 classic24 节拍达成 |
| 人物/世界定稿 | 开书卷级 canon，其余可延 | **全书级 canon**：书庭一次把主阵容/世界规则做全做实，写作期不留 TBD |
| 修订 | 逐章轻评+抽样深评即定稿 | 逐章闸门照走，另加**全书三遍修订**（§4）后才算完稿 |
| 红线自查 | 底线项，逐级强制 | 建议级自查（出版合规仍建议过 `rubrics/redline.md` 一遍） |

其余一切不变：文件契约、writeback 闸门、实体/线索台账、设计庭、否决案台账照常。

## 2. 细纲工序（新增在「排批」与「写作」之间）

对每章 task.json 做加厚，替代 web 的三拍粗批：

1. `beats` 扩到 **6–10 拍**，每拍一句「谁做什么→值变什么」；
2. 增补键 `"scene_intents"`：每拍标 `场景|过场`，场景须有目标/障碍/转折之一被显式命名；
3. `hook.close` 可为 null，但必须写 `"turn"`：本章价值翻转一句话（正负极性标明，如
   `"信任+ → 背叛-"`）；
4. 细纲以弧为批次成批产出（一次 5–10 章），戴 Architect 帽/spawn 架构师完成，
   过一次 structure-critic 检查（盯因果链与节拍对位）再进入写作。

> 附加键是 formats.md 章任务卡的可选扩展，机器不校验其内容，写手照拍执行、
> 深评照 `turn` 验收。

## 3. CLI 断言差分（route=traditional 时自动生效）

| 断言 | web | traditional |
|---|---|---|
| `check --unit` hooks_realized.close=false | FAIL（issues 说明可降 WARN） | WARN（同样要求 issues 说明） |
| `check --window` 3 章小爽 / 10 章大爽 | FAIL | WARN（参考信号，不阻塞） |
| 其余全部断言（信封/黑名单/同首句/ngram/台账/连续性） | 不变 | 不变 |

## 4. 全书三遍修订（完稿闸门）

全部章 `approved` 后、宣布完稿前，依次执行；每遍产出问题清单 → 逐条修复走
`revise` 任务（机检+评审照常）：

1. **结构遍**：戴 structure-critic 帽对全书跑 classic24 检查单 + `check --project`
   + 线索台账清账（`ledger promise` 无未回收 must_not_drop 线）；
2. **场景遍**：抽全书 20% 章深评（关键节拍章必抽），盯 `turn` 兑现与人物弧一致性；
3. **语言遍**：逐章重跑 `check --unit`（style 黑名单可能已迭代），同喻体全书频次、
   口癖跨章聚集由深评抽查。

三遍全绿 → 全书 `tree set-status` 各章保持 approved，book 节点记 decision「完稿」，
导出交付（导出格式按用户要求，协议不约束）。
