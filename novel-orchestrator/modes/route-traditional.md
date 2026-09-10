> 当前创作与可靠性约定见 `../protocol/reliability.md`。传统路线不强制 classic24，也不要求在写作发现之前一次确定全部世界规则；下面的骨架与数值只在作者选定时适用。

# route-traditional — 传统长篇差分层

适用：出版向长篇/严肃文学/一次写完再发、无连载压力。**这不是独立模式**：先按能力选
`mode-orchestrated` 或 `mode-solo`，再叠加本文件的覆盖规则。收编自 v1（已移除）的
`route_delta` 双轨差分思想（术语映射见 protocol/glossary.md §2）。

启用：`config.json` 设 `"route": "traditional"`。CLI 已按此降级相应断言（见 §3）。
装载差分（哪个阶段换哪张判据卡/人设卡）收敛在 `protocol/stages/trad-overlay.md`——本文件是规则 SSOT，该包只管装载。

## 1. 工序差分（对照 web 默认）

| 环节 | web（默认） | traditional（本差分） |
|---|---|---|
| 发布 | buffer 水位 + publish + retcon | **无 buffer/publish**。章止于 `approved`；全书完稿后统一定稿导出，`publish`/`serial-ops §1–3` 不使用 |
| 全书骨架 | 分卷草案 + 卷内自选节奏 | 书庭 S4 选择强规划或探索式；rhythm/classic24.md 仅为可选骨架 |
| 排批粒度 | 章任务卡（goal+3 拍+钩） | **加细纲工序**：见 §2 |
| 章长 | 2000–4500 硬带 | 节奏优先、章长灵活：在 task.json 逐章覆盖 `word_target`（如 [1500, 9000]） |
| 章尾钩 | 强制（close=false 即 FAIL） | 建议级：close=false 且 issues 说明 → WARN；连续缺少事件、情感或认知变化时由深评检查原因，不用固定次数自动否定 |
| 爽点窗口 | 3 章/10 章硬窗口 | 降为建议（check --window 输出 WARN）；改盯场景作用与作品选定的结构 |
| 人物/世界定稿 | 开书卷级 canon，其余可延 | 先明确核心约束；未解决项保留 TBD，不作为既成事实，相关写作前再决策 |
| 修订 | 逐章轻评+抽样深评即定稿 | 逐章闸门照走，另加**全书三遍修订**（§4）后才算完稿 |
| 红线自查 | 底线项，逐级强制 | 安全与作者边界不降级；出版渠道约束单独确认 |

其余一切不变：文件契约、writeback 闸门、实体/线索台账、设计庭、否决案台账照常。

## 2. 细纲工序（新增在「排批」与「写作」之间）

对每章 task.json 做加厚，替代 web 的三拍粗批：

1. 依场景需要细化 `beats`（6–10 拍可作参考，探索式只承诺近期必要场面），每拍一句「谁做什么→值变什么」；
2. 增补键 `"scene_intents"`：每拍标 `场景|过场`，场景须有目标/障碍/转折之一被显式命名
   （场景合法性判据见 `rubrics/scene-value.md` §一）；
3. `hook.close` 可为 null，但必须写 `"turn"`：本章价值翻转一句话（正负极性标明，如
   `"信任+ → 背叛-"`；验收判据见 `rubrics/scene-value.md` §二）；
4. 细纲以弧为批次成批产出（一次 5–10 章），戴 Architect 帽/spawn 架构师完成，
   过一次 structure-critic 检查（附 `rubrics/scene-value.md`，盯因果链、节拍对位与
   场景五步完整性）再进入写作。

> 附加键是 formats.md 章任务卡的可选扩展，机器不校验其内容，写手照拍执行、
> 深评照 `turn` 验收（判据 `rubrics/scene-value.md` §二）。

## 3. CLI 断言差分（route=traditional 时自动生效）

| 断言 | web | traditional |
|---|---|---|
| `check --unit` hooks_realized.close=false | FAIL（issues 说明可降 WARN） | WARN（同样要求 issues 说明） |
| `check --window` 3 章小爽 / 10 章大爽 | FAIL | WARN（参考信号，不阻塞） |
| 其余全部断言（信封/黑名单/同首句/ngram/台账/连续性） | 不变 | 不变 |

## 4. 全书三遍修订（完稿闸门）

全部章 `approved` 后、宣布完稿前，依次执行；每遍产出问题清单 → 逐条修复走
`revise` 任务（机检+评审照常）：

1. **结构遍**：戴 structure-critic 帽对全书跑所选结构检查单（选用 classic24 时才用其节拍表） + `rubrics/theme.md`
   §四主题贯穿追踪 + `check --project` + 线索台账清账（`ledger promise` 无未回收
   must_not_drop 线）；
2. **场景遍**：抽全书 20% 章深评（关键节拍章必抽），按 `rubrics/scene-value.md` 盯
   `turn` 兑现与场景合法性、按 `rubrics/theme.md` §三扫说教，兼核人物弧一致性；
3. **语言遍**：逐章重跑 `check --unit`（style 黑名单可能已迭代），按
   `rubrics/imagery.md` 验收意象系统纪律与比喻预算；同喻体全书频次、口癖跨章聚集
   由深评抽查。

三遍修订与庭审冷读的读者票：抽 `personas/literary-purist.md` 与
`personas/bookclub-mainstream.md` 双卡同场（前者把语言与主题关，后者把可读性关）。

三遍全绿 → 全书 `tree set-status` 各章保持 approved，book 节点记 decision「完稿」，
导出交付（导出格式按用户要求，协议不约束）。

## 规划方式由作品决定

强规划：先定核心事件、人物转折与收束，再滚动细化。探索式：先定核心冲突、视角、语言与不能违背的边界，试写 1–3 个关键场面，保留发现，再修订设计。TBD 是显式不确定性，不能直接变成正文事实；相关场面需要该信息时先解决。两种方式可切换，变更记入设计决策与影响清单。

细纲是预测而非真理。三遍修订仍可使用，但逐遍检查结构与关系、场景戏剧、语言和意象，不要求每章达到统一爽点或章尾钩比例。作者的主题与叙述距离优先于模板。
