# stage:ops — 连载运营 / 卷末结账 配套知识包 · 零 K 装载

| 键 | 值 |
|---|---|
| 阶段 | ops：buffer 水位 · publish · retcon · 卷末 checkpoint · 读者反馈分诊（serial-ops.md 全文） |
| 进入 | 每批章后看水位 / 发布计划到期 / 卷内末章 approved / 反馈收件箱新件 |
| 退出 | `gate publish` / `gate checkpoint` 绿并执行；反馈逐条有任务去向 |
| 叠加 | route=traditional → 本阶段 buffer/publish 整段移除（trad-overlay.md） |
| 本包读者 | 编排者；数据分析只收白名单附件 |

## 装载白名单

| 环节 | 只读这些 | 禁读 |
|---|---|---|
| buffer/publish | `protocol/serial-ops.md` §1–2、`novel.py status`/`gate publish` 输出 | knowledge/ 全部 |
| retcon | `protocol/serial-ops.md` §3、相关 `court/dec_*.md`、`templates/decision.md` | knowledge/ |
| 卷末 checkpoint | `protocol/serial-ops.md` §4、`state/reports/vol_NN.md`、`rubrics/structure.md`（卷级深评时随 review 阶段附） | knowledge/；卷内正文重读（以报告与摘要为准） |
| 读者反馈分诊 | `roles/data-analyst.md`、反馈原文、近期 verdict 摘要、ledger 统计 | knowledge/（归因需要学理支撑 → 编排者转 diag 阶段） |

## 运营知识去哪了

连载流程/爽点工程/毒点运营的**可操作面**已蒸馏进 `protocol/serial-ops.md` 本身与
`rubrics/payoff.md`、`rubrics/toxicity.md`、`rubrics/power.md`；开书商业与免费流模型属
s1 阶段 K 池（开书期用）。运营期出现「为什么掉量/为什么被骂」类归因问题 =
diag 阶段（`protocol/stages/diagnose.md`，症状路由进 `knowledge-index.md` §二/§四），
由编排者深读后转任务，**不给数据分析角色开 knowledge/ 权限**。

## 退出前自查

- publish：连续性谓词 + 审批（formats §19）；checkpoint：三态对账无残留 + recap 已更新。
- checkpoint 完成才可开下卷卷庭（→ vol 阶段）。
