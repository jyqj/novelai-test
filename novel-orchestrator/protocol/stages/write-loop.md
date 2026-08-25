# stage:write — 章循环（产线）配套知识包 · **零知识装载**

| 键 | 值 |
|---|---|
| 阶段 | write：排批→简报→写→机检→轻评→commit→回执（pipeline.md §1；交接谓词 workflow.md §3） |
| 进入 | `novel.py gate write ch_NNNN` 全绿 |
| 退出 | 章 approved（`gate approve` 绿 + `tree set-status`） |
| 叠加 | route=traditional → 另读 `protocol/stages/trad-overlay.md` |
| 本包读者 | 编排者；写手/资料员/轻评只收各自白名单内附件 |

## 本阶段的知识装载 = 0

**knowledge/ 在本阶段对所有角色关闭**（knowledge-orchestration §0.2 硬规则）。
可操作判据已全部蒸馏进 rubrics/ 与项目侧 `tree/style.md`；简报里没有的世界不存在。
「写到一半想查方法论」= 症状，走 diag 阶段（`protocol/stages/diagnose.md`），不在产线内拉块。

## 各棒装载白名单（超出即泄漏，pipeline §5）

| 角色 | 只读这些 | 禁读 |
|---|---|---|
| 编排者 | `protocol/pipeline.md` §1–5、`protocol/workflow.md` §3、章 task.json、gate/check 输出 | knowledge/ 全部 |
| 资料员（T1 审包） | `roles/librarian.md` + 项目仓库（只读，核对简报配料） | knowledge/、skill 侧判据卡（审包不评质量） |
| 写手（T2） | `briefs/ch_NNNN.brief.md` **唯一输入**（roles/writer.md 随 spawn 附） | 项目内其余一切 + knowledge/ + rubrics/ |
| 轻评（T3） | `roles/critic-light.md`、`rubrics/prose-disease.md`、`rubrics/payoff.md`、`rubrics/voice.md`（三卡**所有权=write**，产线自有）、简报、候选、前章尾、机检 NEEDS_REVIEW 清单 | knowledge/、tree/ 原文 |
| 抽取器（CLI / C·D 档帽） | 候选正文 + writeback + aliases（`roles/extractor.md`） | knowledge/ |

## 退出前自查

- 回执落盘（`review add`）且 rev 匹配；`gate approve` 绿。
- 每 5 章 `check --window`；到深评/对账节律 → 转 review 阶段（`protocol/stages/review-cycle.md`）。
