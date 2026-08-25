# knowledge-orchestration.md — 阶段×知识装载编排（SSOT）

> 定位：全生命周期被切成若干**阶段（stage）**，每个阶段有且只有一个**配套知识包**
> （`protocol/stages/` 下的薄路由文件）。「现在处于哪个阶段、该装载什么、装多少、
> 禁装什么」以本文件 + 对应包为准。块级归属台账仍是 `knowledge-map.md`（分工见 §4）。
> 机器半边：`novel.py stage list|show|current`；`gate next` 末行附当前阶段推断。

## 0. 三条硬规则（先记住再干活）

1. **进阶段先读包**：任何环节开工前，先读对应 `protocol/stages/<包>.md`（每包 ≤80 行），
   按包内「必读 / 选读池 / 禁读」装载——**不再「去 knowledge/ 逛逛」**。
2. **产线零知识**：write 阶段（章循环）任何角色不装载 knowledge/ 任何块——写手只见简报，
   评审只见判据卡。这是默认态，不是降级态。
3. **池外不投**：庭审附件只能从本场包的选读池（K 池）中挑（每场 ≤4 块、只取锚点段）；
   要投池外块 = 先改 `knowledge-map.md` 归属（登记变更，见 §6），再投。

## 1. 阶段总表（catalog）

| 阶段 id | 名称 | 进入条件 | 退出判据 | 配套包（protocol/stages/） | 本包读者 | K 池 |
|---|---|---|---|---|---|---|
| s1 | 书庭S1·概念庭 | init 完成；`court open S1` | dec_001 暂存 + book 概念节素材齐 | s1-concept.md | 编排者（R0 装配） | 13 块 |
| s2 | 书庭S2·世界庭 | dec_001 在 | dec_002 + world 四节素材齐 | s2-world.md | 编排者（R0） | 11 块 |
| s3 | 书庭S3·人物庭 | dec_002 在 | dec_003 + 主线/阵容素材齐 | s3-cast.md | 编排者（R0） | 14 块 |
| s4 | 书庭S4·分卷庭 | dec_003 在 | dec_004；book/world/style/vol_01 committed | s4-volumes.md | 编排者（R0） | 8 块 |
| vol | 卷庭 | 上卷 checkpoint 完成 | vol_NN 九节 committed | vol-court.md | 编排者（R0） | 11 块（6 与 s4 共享） |
| arc | 弧规划（含细纲） | 游标距弧前沿 ≤1 弧 | arc_NN_n 六节 committed | arc-plan.md | 编排者（R0） | 3 块 |
| write | 章循环（产线） | `gate write` 绿 | 章 approved（`gate approve` 绿） | write-loop.md | 编排者/写手/轻评 | **0（禁装）** |
| review | 周期回路 | deep_every 到期 / 弧末 / 卷末 / entity due | 回执与对账落盘 | review-cycle.md | 深评/资料员 | 0（判据卡 only） |
| ops | 连载运营/卷末结账 | buffer 水位 / 发布计划 / 收卷 / 反馈 | publish/checkpoint 过闸 | ops-serial.md | 编排者/数据分析 | 0 |
| trad | 传统路线差分 | `config.route=traditional` | 叠加层，随宿主阶段 | trad-overlay.md | 各角色 | 0（判据卡置换） |
| diag | 诊断/学理深读 | 症状复现 / 阻塞 / 用户求教 | 结论回流后即弃（§6） | diagnose.md | 编排者 | 按需 ≤2 块/次 |

- s1–s4 / vol / arc 与 `protocol/court.md` §1–2 的庭型场次**同名同义**，不另立体系；
  write / review / ops 对应 `protocol/workflow.md` §3–5 的阶段二/三/四。trad 是叠加差分，不是串行阶段。
- 「K 池」列数字与 `knowledge-map.md` 场次标注逐块一致，由 `tools/tests/test_stage.py` 机检对账（§4）。

## 2. 装载三层模型

| 层 | 何时装 | 装什么 | 预算 |
|---|---|---|---|
| L-run 运行层 | 各角色 spawn / 戴帽即带 | 角色卡 + 该角色判据卡（SKILL §4 契约表） | 卡即预算，无 knowledge/ |
| L-stage 阶段层 | 阶段入口（编排者装配设计简报时） | 阶段包「必读」+ 从 K 池挑的庭审附件 | ≤4 块/场，只取锚点段 |
| L-diag 诊断层 | 仅 diag 阶段 | knowledge-index 症状路由 → K-ID → knowledge-blocks 锚点 | ≤2 块/次，读完即弃 |

## 3. 禁装规则（forbid；违者按泄漏处理，pipeline §5）

1. 写手/轻评/深评的 spawn 附件（或帽内输入白名单）**永不出现 knowledge/ 路径**。
   knowledge-map 标「深评诊断素材」的块属 diag 阶段——由编排者在评审**之后**走症状路由深读，
   不进评审附件（评审只裁判据卡与 NEEDS_REVIEW 项）。
2. 任何简报（章简报/设计简报）不整文件投递 knowledge/ 文件；庭审附件 = 锚点段摘录进设计简报。
3. **不存在「全库速读」阶段**：111 块没有任何一个阶段有权全量装载；「先通读知识库再干活」
   在任何阶段都是违规。
4. 阶段包本身 ≤80 行、只做路由不抄正文（防止包退化成第二知识库）；
   包内 K 池条目 = K-ID + 名称 + 一句「何时挑」，正文一律经锚点回原文取段。

## 4. 四个路由文件的分工（消重契约）

| 文件 | 是什么 | 不是什么 |
|---|---|---|
| 本文件 + `protocol/stages/` | **阶段→装载**的 SSOT（按阶段的视图） | 不登记单块归属细节 |
| `knowledge-map.md` | **块→归属**的台账（按块的视图，111 行；蒸馏/庭审附件/仅 learn 三类） | 不再作按场检索入口（按场检索走 stages/ 包） |
| `knowledge-blocks.md` | **K-ID→文件锚点**的唯一解析器（含 L1–L4 读法） | 不做推荐 |
| `knowledge-index.md` | **症状→K-ID** 检索（仅 diag / 用户求教）；其 P1–P6 流程索引=学习课纲 | 不做运行期路由 |

**对账规则**（`tools/tests/test_stage.py` 机检，改任何一边先跑测试）：
stages/ 各包 K 池 ≡ knowledge-map 场次标注（含 S4/卷庭双标）；包内引用路径全部存在；
rubrics 卡脚注 K-ID 集 ≡ map「蒸馏」列；产线三包（write/review/ops）与 trad/diag 包正文零 K-ID。

## 5. CLI（导航用，只读不写）

- `novel.py stage list`：阶段总表（id + 定位 + 包绝对路径）。
- `novel.py stage show <id>`：打印对应包全文（附解析路径）——spawn/装配前照包取料。
- `novel.py stage current`：按项目状态推断当前阶段（court 工作区 > 设计缺口 > 队首任务类型），
  route=traditional 时提示叠加 trad 包。`gate next` 末行输出同款推断。
- 推断是**启发式导航**，不是闸门；有歧义以 `protocol/workflow.md` §1 人判为准。

## 6. 知识流动的三条回路（谁有权改哪层）

1. **蒸馏回路（运行期）**：教训 ≥2 次复现 → `task add revise_rubric style` → 改**项目侧**
   `tree/style.md`（workflow §6）。skill 侧 `rubrics/*` 是发行物，不随项目改。
2. **判据卡维护（skill 维护期）**：diag 深读结论有普适价值 → 改 rubrics/ 卡正文 + 卡脚注
   K-ID 登记来源 + 跑 test_stage 对账；不把 knowledge 原文抄进协议。
3. **新增知识块**：knowledge/ 原文加 `<!-- K-XXX-NNN -->` 锚 → `knowledge-blocks.md` 登记 →
   `knowledge-map.md` 补归属行 → 若归属=庭审附件，同步对应 `protocol/stages/` 包 K 池补行 →
   test_stage 绿。顺序不可倒置；无归属的块不得被任何阶段引用。

---

*rev 1 · 2026-08-25 · 初版：11 阶段目录 + 装载三层模型 + 禁装规则 + 四路由文件分工与机检对账 + stage CLI + 知识流动三回路。*
