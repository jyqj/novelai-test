> 维护归属与默认池不变；遇具体症状可由编排者 stage consult 有界借阅池外块（见 protocol/knowledge-orchestration.md），不改所有权，不将原文自动投入写手简报。

# stage:review — 周期回路（深评/对账/欠账盘点）配套知识包 · 判据卡 only

| 键 | 值 |
|---|---|
| 阶段 | review：深评采样 · 实体对账 · knowledge 欠账盘点 · 蒸馏回路（workflow.md §4/§6） |
| 进入 | `deep_every` 到期 / 弧末 / 卷末 / `entity due` 非空（gate next 会顶到队首） |
| 退出 | 深评回执与 lessons 落盘；对账 entity update 完成；欠账逐条有去向 |
| 叠加 | route=traditional → 三遍修订制替代采样深评（`protocol/stages/trad-overlay.md`） |
| 本包读者 | 编排者；深评/资料员只收各自白名单内附件 |

## 各棒装载白名单

| 角色 | 只读这些 | 禁读 |
|---|---|---|
| 深评（T4） | `roles/critic-deep.md`、`rubrics/anti-plagiarism.md`（**所有权=review**）、`rubrics/structure.md`（所有权=s3）、`rubrics/payoff.md`（所有权=write）、`rubrics/power.md`（所有权=s2）（四卡必附）、采样窗正文与 meta 摘要、弧/卷计划、ledger 统计 | **knowledge/ 全部**（诊断素材属 diag 阶段，不进评审附件）；自己往期 writeback/轻评单（solo 冷读纪律） |
| 资料员（对账变体） | `roles/librarian.md` + entities/ 与事件日志（serial-ops §5）；对账连带知情圈（`knowledge scope list` 对照剧情，圈变走 scope add/remove） | knowledge/ |
| 编排者 | `novel.py knowledge query` 输出（读者未知欠账，CLI 视图不读库）、`entity due`、lessons 台账 | knowledge/（除非转 diag） |

## 欠账盘点的去向（每条必择一，不许挂着不管）

继续吊（记 task note）/ 排「揭示章」进任务卡 + `knowledge reveal` 销账 / 走 retcon 废止。
`gate next` 会在欠账超龄（config `spoiler_debt_chapters`）时自动顶出【欠账】项。

## 症状复发 → 转 diag，不在本阶段拉块

深评报告点名的复发症状（文风病/结构病/战力崩……）：
- 教训 ≥2 次复现 → 蒸馏回路 `task add revise_rubric style`（workflow §6，动项目侧 style.md）；
- 需要学理归因 → 编排者进 diag 阶段（`protocol/stages/diagnose.md`，≤2 块），
  **不把 knowledge 块塞回深评附件重评**。
