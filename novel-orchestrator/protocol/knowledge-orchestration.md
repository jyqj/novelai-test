# knowledge-orchestration.md — 阶段×知识装载编排（SSOT）

> 定位：全生命周期被切成若干**阶段（stage）**，每个阶段有且只有一个**配套知识包**
> （`protocol/stages/` 下的薄路由文件）。不默认装载全库；维护归属不等于使用权限。每个
> 知识资产（K 块/判据卡/人设卡/节奏模板）都有且只有一个所有阶段（台账=`knowledge-map.md`，
> 分工见 §4）。「现在处于哪个阶段、该装载什么、装多少、禁装什么」以本文件 + 对应包为准。
> 机器半边（P7-S）：阶段是**持久化状态 + 强制闸门**——`stage enter <id>` 进入（写
> `state/stage.json`），受辖操作在阶段不匹配时被拒（§5；辖区表 F§15）；
> `stage current` 读持久化阶段；`gate next` 末段附阶段与包路径。

## 0. 四条硬规则（先记住再干活）

1. **进阶段 = `stage enter` + 读包**：任何环节开工前，先 `novel.py stage enter <id>`
   （不 enter，受辖操作会被闸门拒绝，§5），再读对应 `protocol/stages/<包>.md`（每包 ≤80 行），
   按包内「必读 / 选读池 / 禁读」装载——**不再「去 knowledge/ 逛逛」**。
2. **默认轻量**：写手只见简报，评审只见判据和证据；知识原文不自动投递给 worker。
3. **默认池外咨询需理由**：庭审默认从本场池选 ≤4 块；出现具体症状，可由编排者执行 `stage consult <K-ID> [<K-ID>] --target <现有任务/节点> --reason <症状>`，单次 ≤2 块，默认字符预算 16000（配置 consult_budget_chars，最大 50000），超限拒绝。咨询记录来源哈希，不改所有权，不切换阶段，不自动进简报。
4. **维护归属唯一，使用允许复用**：默认池保持不重不漏，判据卡/人设/节奏跨阶段引用仍标 `（所有权=<阶段>）` 方便维护。学理可跨阶段适用，不能为了读一块方法论而改写资产所有权。

## 1. 阶段总表（catalog）

| 阶段 id | 名称 | 进入条件 | 退出判据 | 配套包（protocol/stages/） | 本包读者 | K 池 |
|---|---|---|---|---|---|---|
| s1 | 书庭S1·概念庭 | init 完成；`court open S1` | dec_001 暂存 + book 概念节素材齐 | s1-concept.md | 编排者（R0 装配） | 13 块 |
| s2 | 书庭S2·世界庭 | dec_001 在 | dec_002 + world 四节素材齐 | s2-world.md | 编排者（R0） | 11 块 |
| s3 | 书庭S3·人物庭 | dec_002 在 | dec_003 + 主线/阵容素材齐 | s3-cast.md | 编排者（R0） | 14 块 |
| s4 | 书庭S4·分卷庭 | dec_003 在 | dec_004；book/world/style/vol_01 committed | s4-volumes.md | 编排者（R0） | 7 块 |
| vol | 卷庭 | 上卷 checkpoint 完成 | vol_NN 九节 committed | vol-court.md | 编排者（R0） | 6 块 |
| arc | 弧规划（含细纲） | 游标距弧前沿 ≤1 弧 | arc_NN_n 六节 committed | arc-plan.md | 编排者（R0） | 3 块 |
| write | 章循环（产线） | `gate write` 绿 | 章 approved（`gate approve` 绿） | write-loop.md | 编排者/写手/轻评 | 0（默认；可咨询） |
| review | 周期回路 | deep_every 到期 / 弧末 / 卷末 / entity due | 回执与对账落盘 | review-cycle.md | 深评/资料员 | 0（默认判据；可咨询） |
| ops | 连载运营/卷末结账 | buffer 水位 / 发布计划 / 收卷 / 反馈 | publish/checkpoint 过闸 | ops-serial.md | 编排者/数据分析 | 0 |
| trad | 传统路线差分 | `config.route=traditional` | 叠加层，随宿主阶段 | trad-overlay.md | 各角色 | 0（判据卡置换） |
| diag | 诊断/学理深读 | 症状复现 / 阻塞 / 用户求教 | 结论回流后即弃（§6） | diagnose.md | 编排者 | 33 块（专属），≤2/次 |

- s1–s4 / vol / arc 与 `protocol/court.md` §1–2 的庭型场次**同名同义**，不另立体系；
  write / review / ops 对应 `protocol/workflow.md` §3–5 的阶段二/三/四。trad 是叠加差分，不是串行阶段。
- 「K 池」列数字与 `knowledge-map.md` 所有权标注逐块一致（13+11+14+7+6+3+33=87 运行期块，
  另 24 块蒸馏进判据卡；**任何块只属一个池**），由 `tools/tests/test_stage.py` 机检对账（§4）。

## 2. 装载三层模型

| 层 | 何时装 | 装什么 | 预算 |
|---|---|---|---|
| L-run 运行层 | 各角色 spawn / 戴帽即带 | 角色卡 + 该角色判据卡（SKILL §4 契约表） | 卡即预算，不自动装知识全文 |
| L-stage 阶段层 | 阶段入口（编排者装配设计简报时） | 阶段包「必读」+ 从 K 池挑的庭审附件 | ≤4 块/场，只取锚点段 |
| L-diag 诊断层 | diag 默认路由，或任一已进入阶段的有界咨询 | diagnose.md 默认症状路由或已知 K-ID → knowledge-blocks 锚点 | ≤2 块/次，有用操作回流，不整篇保留 |

## 3. 输入边界：防止混淆，而不是禁止学方法

写手只见审过的简报；方法可以经 creative_brief 给出操作和正反例。编排者及知情编辑可按当前问题 consult，默认不整篇投递知识文件。冷读者只见相应正文，不能因“补课”泄漏未来答案。

阶段包保持薄路由，不复制原文、不新增一套知识归属。默认池只提供省力起点；它不排除其他适用知识。维护期审计可以通读库，普通写作不以“先全库阅读”为前提。

## 4. 三个路由文件的分工（消重契约）

| 文件 | 是什么 | 不是什么 |
|---|---|---|
| 本文件 + `protocol/stages/` | **阶段→装载**的 SSOT（按阶段的视图）；症状→块检索在 diagnose.md 包内 | 不登记单块归属细节 |
| `knowledge-map.md` | **资产→所有权**的台账（按块的视图，111 行，蒸馏/庭审附件/诊断·diag 三类归属；另登记 11 判据卡、9 人设卡、5 节奏模板的所有阶段） | 不作检索入口（按场检索走 stages/ 包） |
| `knowledge-blocks.md` | **K-ID→文件锚点**的唯一解析器（含 L1–L4 读法） | 不做推荐 |

诊断默认从 diagnose.md 症状路由选择；池外可以按确定 K-ID 咨询。默认池对账测试检查维护映射完整性，不证明知识只适用于该阶段。

**对账规则**（`tools/tests/test_stage.py` 机检，改任何一边先跑测试）：
stages/ 各包 K 池 ≡ knowledge-map 所有权标注且**两两不相交**；包内引用路径全部存在；
rubrics 卡脚注 K-ID 集 ≡ map「蒸馏」列；产线三包（write/review/ops）与 trad 包正文零 K 池；
非所有阶段引用卡/人设/节奏必带 `所有权=` 署名（map §卡表为基准）。

## 5. 阶段状态机与闸门（P7-S：阶段是钥匙，不是导航建议）

- **进入 = `novel.py stage enter <id>`**：写项目 `state/stage.json`（stage/entered_at/history，
  F§14）。这是各受辖操作的**前提**——court open、brief、commit、publish、checkpoint、
  gate write… 执行前校验持久化阶段，不匹配 = exit 1 + `stage enter` 修复提示
  （辖区全表 = F§15 阶段闸门辖区表）。
- **`stage current`**：读持久化阶段 + 配套包路径 + 启发式核对（court 工作区 > 设计缺口 >
  队首任务类型）。未进入任何阶段 → exit 1。启发式推断只做**核对与导航**（不一致时提示
  收口后 enter），阶段的定义以 stage.json 为准；歧义以 `protocol/workflow.md` §1 人判为准。
- **迁移纪律**：完成本阶段退出判据（§1 表）后才 enter 下一阶段；`stage enter` 与推断不一致
  时打印核对提醒，跨阶段进入须确认上一环节已收口。误进 = 再 enter 正确阶段（history 留痕）。
- `stage list` / `stage show <id>`：总表 / 打印包全文（spawn/装配前照包取料）。
  `gate next` 末段附已进入阶段与包路径（未进入时打高优先级提醒，advisory 不拒绝）。

## 6. 知识流动的三条回路（谁有权改哪层）

1. **蒸馏回路（运行期）**：教训 ≥2 次复现 → `task add revise_rubric style` → 改**项目侧**
   `tree/style.md`（workflow §6）。skill 侧 `rubrics/*` 是发行物，不随项目改。
2. **判据卡维护（skill 维护期）**：diag 深读结论有普适价值 → 改 rubrics/ 卡正文 + 卡脚注
   K-ID 登记来源 + 跑 test_stage 对账；不把 knowledge 原文抄进协议。
3. **新增知识块**：knowledge/ 原文加 `<!-- K-XXX-NNN -->` 锚 → `knowledge-blocks.md` 登记 →
   `knowledge-map.md` 补所有权行（**指定唯一所有阶段**）→ 若所有权=庭审附件/诊断，同步该
   阶段包 K 池补行 → test_stage 绿。维护时先登记来源与归属；运行期不得凭空发明 K-ID。

---

*rev 3 · 2026-08-25 · 废除全库通用知识：硬规则 4（唯一所有阶段+借用署名）；S4/卷庭双标拆分（7+6）；「仅 learn」33 块转 diag 专属池；全库症状索引文件删除（诊断检索收归 diagnose.md 包内）；对账规则改两两不相交。*
*rev 2 · 2026-08-25 · P7-S 阶段强制闸门：§0 规则 1 与 §5 改版——stage enter 持久化 state/stage.json 为阶段定义，受辖操作阶段不匹配即拒绝（辖区表 F§15）；启发式推断降为核对。*
*rev 1 · 2026-08-25 · 初版：11 阶段目录 + 装载三层模型 + 禁装规则 + 四路由文件分工与机检对账 + stage CLI + 知识流动三回路。*

## 方法使用与维护分离

`methodology/knowledge-policy.md` 规定知识地位与适用范围；methodology 是跨任务操作手册，不新增 K-ID 或默认池。111 块维护映射保留，使用不得以池归属推断学理只适用于该阶段。咨询结论经任务 creative_brief 进入简报 §0，可携操作小例；它不成为故事事实。
