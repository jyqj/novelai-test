# workflow.md — 全生命周期作业主线（L1 总装图）

> 定位：`SKILL.md`（L0 薄路由）之下、各专项协议（court/pipeline/serial-ops/adopt）之上的**主循环脊柱**。
> 回答一个问题：**「现在该干什么、用哪条命令验收、谁来干、按哪张判据卡」**。步骤细节零重复，只指针到专项协议对应节（court=C§n，pipeline=P§n，serial-ops=S§n，formats=F§n）。
> 机器半边：**迷路先跑 `novel.py gate next`**——它按「修账 > 深评逾期 > 实体对账 > 发布缓冲 > 推进」输出优先级剧本，与本文件 §1 各环节一一对应；每个 gate 的 FAIL 都自带「↳ 下一步」修复命令，照做即可回到主线。

## 0. 使用方式（三条）

1. **冷启动/换会话/迷路**：`novel.py status` → `novel.py gate next` → 对照 §1 总图定位所处环节 → 跳到该环节小节按表执行。禁止凭记忆续写。
2. **每个环节四件套**：入口条件（gate 谓词，机器判）→ 动作（CLI + 执行角色/帽子）→ 验收（gate/check 绿）→ 失败去向（明确写在表里，不临场发明）。
3. **模式与档位不改变主线**，只改变「谁来干、哪些验收降级」：solo 帽子映射、traditional 差分、C/D 档损失一律查 §7 三张覆盖表，不散落。
4. **进环节 = `stage enter` + 读包**（P7-S 强制）：每个环节有唯一配套知识包（§1.1 对照表；
   SSOT=`protocol/knowledge-orchestration.md`）。开工顺序钉死：`novel.py stage enter <id>`（写
   `state/stage.json`，是各受辖操作的钥匙）→ 读包 → 按包内「必读/选读池/禁读」装载。
   受辖命令（court open/brief/commit/publish/checkpoint/gate write…全表见 F§15 辖区表）在
   阶段不匹配时**直接拒绝**并给 `stage enter` 修复提示——跨阶段操作不是警告，是不可执行。
   `novel.py stage current` 读持久化阶段（未进入任何阶段时 exit 1）。

## 1. 全生命周期总图

```
init ──书庭 S1–S4──> book/world/style/vol_01 committed          （§2，C§1–3）
   └─> 卷庭 ──> vol_NN committed                                 （§2）
        └─> 弧简流程 ──> arc_NN_n committed                       （§2）
             └─> 排批 ──> ┌────── 章循环 ×N ──────┐               （§3，P§1–3）
                          │ brief→gate write→写手→ │
                          │ check/extract→轻评→    │
                          │ commit→回执→gate       │
                          │ approve→approved       │
                          └──────────┬─────────────┘
              周期回路（§4）：深评采样 · 实体对账 · knowledge 欠账盘点
                          · buffer 水位 → gate publish → publish
             └─ 弧末：check --window + 线索对账 + knowledge query
        └─ 卷末：report → 三态对账 → gate checkpoint → checkpoint → 卷庭（§5）
异常轨（§6）：retcon（已发布修错） · adopt（存量收编） · 读者反馈分诊
            · 蒸馏回路（lessons → revise_rubric → style 黑名单 → 机检生效）
```

**状态机主干**（F§3）：设计节点 `empty→draft→committed`；章 `planned→drafted→approved→published`（published 不可变）；一切迁移由 CLI 校验，`stale` 由 revise_design 波及。

### 1.1 阶段 ↔ 配套知识包（装载契约；SSOT=`protocol/knowledge-orchestration.md`）

| 环节 | 阶段 id | 配套包（protocol/stages/） | 装载要点 |
|---|---|---|---|
| 书庭 S1–S4 | s1–s4 | s1-concept / s2-world / s3-cast / s4-volumes | R0 按包装配；庭审附件从包内 K 池挑 ≤4 块、只取锚点段 |
| 卷庭 | vol | vol-court.md | 上卷报告+K 池 6 块 |
| 弧规划/细纲 | arc | arc-plan.md | 节奏模板检查单+K 池 3 块 |
| 章循环（§3） | write | write-loop.md | **零知识**：写手=简报，轻评=三张判据卡 |
| 周期回路（§4） | review | review-cycle.md | 深评=判据卡 only；欠账盘点走 `knowledge query` CLI，不读库 |
| 发布/卷末（§4–5） | ops | ops-serial.md | 零 K；反馈归因转 diag |
| traditional 差分 | trad | trad-overlay.md | 叠加层：判据卡置换（scene-value/theme/imagery），无 knowledge 豁免 |
| 诊断/学理（§6） | diag | diagnose.md | 唯一可进 knowledge/：包内症状路由→K-ID（只取 diag 专属 33 块池），≤2 块/次，读完即弃 |

机器半边：`novel.py stage list|show <id>|enter <id>|current`；`gate next` 末段附已进入阶段与包路径
（未进入时打高优先级提醒）。阶段迁移即 `stage enter`：完成本环节退出判据（§1.1/编排 SSOT §1）后
显式进入下一阶段；`stage enter` 会与启发式推断核对，跨阶段进入须确认上一环节已收口。误进 = 再
enter 正确阶段（`state/stage.json` history 留痕）。典型迁移链:`s1→s2→s3→s4→vol→arc→write⇄ops`
（发布节拍）与 `write→review→write`（周期回路）；trad 是叠加层不占阶段位。

## 2. 阶段一：冷启动与设计层

| 步 | 入口条件 | 动作（CLI + 角色） | 验收 | 失败去向 |
|---|---|---|---|---|
| 0 探测 | 新任务/新会话 | 按 `modes/capability-profiles.md` §0 两问定档（A/B/C/D），route 定 web/traditional | 档位记入首个 task note | 无 shell → C/D：先向用户申明 `manual-check.md` §2 损失 |
| 1 init | 新书 | `novel.py init <dir> --name X` | `status` 可跑 | 环境错误 → 修 python3/git |
| 2 书庭 | init 完成 | `stage enter s1..s4`（逐场进阶段，court open 闸门校验）→ `court open S1..S4`；R0–R4 回合（C§3）：架构师提案 ×2 → 结构/安全/读者评审 → 主编合成 → dec 落盘 | 每场 dec + 节点稿暂存；S4 后 `commit --file` 全定稿（book/world/style/vol_01 → committed） | 红线 blocking → 升级用户（C§4）；中断 → `court status` 续场 |
| 3 卷庭 | 上卷 checkpoint 完成（首卷随书庭） | `stage enter vol` → C§2 卷庭行：附上卷 exports+报告；判据 rubrics/power+redline+payoff | vol_NN 九节 committed | 否决案拦截（C§4 X7） |
| 4 弧规划 | 写作游标距弧前沿 ≤1 弧 | `stage enter arc` → C§1 弧简流程（1 提案+合并评审+主编）；节奏模板选 `rhythm/` 一张 | arc_NN_n 六节 committed | 评审全否 → C§4 处置 |
| 5 排批 | 弧 committed | `stage enter write` → `tree add chapter` + 编排者补全 task.json（goal/beats/hook/payoff_quota/threads/cast，P§1 步骤 0）→ `task add write` | `gate write` 的任务卡谓词过 | 占位未填 → gate write FAIL 自带指引 |

设计庭判据投递按 C§2 每场规格表；templates/ 为唯一骨架来源。**checkpoint 未完成不开下卷卷庭**（S§4）。

## 3. 阶段二：章循环（产线交接契约）

单章时序细则在 P§1；本节钉死**交接契约**——每一棒谁交什么、谁验收、验收谓词是什么。任何一棒验收不过，产物不得向下传递。

| # | 交接 | 交付物 | 验收人 + 谓词 | 失败去向 |
|---|---|---|---|---|
| 1 | 编排者 → 简报 | `novel.py brief ch` 十节简报（F§6；含 §6 知情/读者未知硬约束） | 资料员（T1）审包：缺料/冗料指令清单 | 编排者修包再审（P§1 步骤 2–3） |
| 2 | 简报 → 写手 | **`novel.py gate write ch` 全绿**（排批齐+弧 committed+简报新鲜+基线净） | 机器谓词；FAIL 附下一步 | 按 FAIL 提示修（排批/brief/清基线） |
| 3 | 写手（T2/写手帽）→ 编排者 | 正文 + writeback JSON 双产出（roles/writer.md 产出契约；known_by 如实申报） | 编排者：结构完整 + 泄漏检查（P§5：git 基线扫描 + `check --leak`） | 泄漏 → 产物作废重 spawn |
| 4 | 双产出 → 抽取器/机检 | `check --unit ch --candidate --writeback`（含抽取器对账+知识越界+facts 冲突，F§17；C/D 档由 extractor 帽按 `roles/extractor.md` 手工对账） | 机器：0 FAIL；NEEDS_REVIEW 打包传下一棒 | FAIL → 修订循环（P§2，计一次） |
| 5 | 机检 → 轻评（T3/轻评帽） | 候选 + 简报 + 前章尾 + NEEDS_REVIEW 清单 | 轻评六判（roles/critic-light.md）：逐条裁定机检主观项 + verdict | revise → P§2；escalate → P§3 |
| 6 | 轻评 pass → commit | `novel.py commit <t> --chapter --writeback` | 机器：check 复跑 + 引用越权拒绝 + 事务包裹（F§16）；副作用=台账/日志/facts/ngram/**rollup** 自动回写 | 拒绝 → 修订循环 |
| 7 | commit → 回执 → approved | `review add ch --depth light --verdict pass` → `gate approve ch` → `tree set-status ch approved` | 机器：drafted + 回执 rev 匹配 + 机检绿；FAIL 附下一步 | 回执过期（章已 revise）→ 复评 |
| 8 | 弧内收尾 | 每 5 章 `check --window`；深评采样（P§4）；lessons 附笔 | 窗口断言绿 | 欠账 → gate next 会顶到队首 |

- **修订**：未发布章 `task add revise` 走同链路（rev+1，撤销重放零双计，旧回执自动失效须复评，F§9/§16）；write/revise 同目标失败 ×2 → 队列自动升级 revise_design（F§10）。**published 章不可 revise**——走 §6 retcon。
- **写手信息沙箱**是本产线的地基：写手只见简报（A/C 档物理隔离；B/D 档帽子协议+泄漏自查）。简报里没有的世界不存在，缺料走 issues。

## 4. 阶段三：周期回路（编排者的「体检表」）

| 回路 | 节律 | 命令/动作 | 验收/去向 |
|---|---|---|---|
| 深评采样 | 每 `deep_every` 章 + 弧末 + 卷末 | `stage enter review` → `task add review_deep` → T4（P§4）；lessons 摘一行入台账；蒸馏（revise_rubric）同属本阶段 | escalate 自动开 revise_design；回路收口后 `stage enter write` 回产线 |
| 实体对账 | `entity due` 非空（每 `reconcile_every` 章） | S§5 对账轮：资料员 B 模式 → `entity update` | 矛盾上报编排者裁决 |
| knowledge 欠账 | 弧末/卷末；超龄欠账（≥`spoiler_debt_chapters` 章未揭示）`gate next` 自动顶出【欠账】项 | `knowledge query`（读者未知欠账盘点）→ 逐条决定：继续吊 / 排「揭示章」进任务卡 + `knowledge reveal` 销账 / 走 retcon 废止 | 长期挂账的悬念 = 期待账户坏账，深评必查 |
| 知情圈对账（矩阵 v2） | 实体对账同轮（资料员对账 entities 时连带） | `knowledge scope list` 对照近章剧情：入伙/驻留/易手已发生而圈未更 → `knowledge scope add\|remove`（正文/日志为据，F§9） | 范围知情（fac/loc/item）的圈成员=矩阵展开口径，圈账错 = 越界扫描失真 |
| buffer 水位 | 每批章后 | `status` 看 ready；按 S§1 水位表动作 | ready=0 → 停发只补稿 |
| 发布 | 计划到期/用户指令 | `stage enter ops` → `gate publish` 试跑 → 审批（F§19）→ `publish`；发完 `stage enter write` 回产线 | FAIL 附下一步（补链/补审） |
| 队列卫生 | 队列 >30 条 | `task archive` | — |

## 5. 阶段四：卷末结账与跨卷

S§4 全流程；闸门视角速查：`stage enter ops` → `check --project` 绿 → `report volume` → **手工三态对账**（report 是唯一允许手改的生成物）→ 卷级深评 → recap 更新 → `gate checkpoint` 试跑（FAIL 附下一步）→ 审批 → `checkpoint`（下卷 imports 自动预填）→ `stage enter vol` 开卷庭（回 §2 步 3）。

## 6. 异常轨与反馈回路

| 轨 | 触发 | 协议 | 机器半边 |
|---|---|---|---|
| retcon | 已发布内容有错 | S§3：旧文一字不动，facts 层向前兼容 | `retcon` CLI 校验 old_fact+decision；简报自动连带 |
| adopt | 存量旧稿/半途接管 | `protocol/adopt.md` | `adopt` + `facts import` + **`rollup`**（批量补录 summary 后手动重算） |
| 读者反馈 | 收件箱新件/用户转达 | S§6：数据分析 T-da 出症状报告 | 按报告开 revise_design / retcon / revise / **revise_rubric** |
| **蒸馏回路** | lessons 台账同类教训 ≥2 条，或深评/反馈点名文风病复发 | 见下 | `task add revise_rubric style --evidence` |

**蒸馏回路（lessons → 判据）**：评审只产教训，不改判据；教训要变成机器强制力，走唯一路径——

```
1 证据：ledgers/lessons.md 摘出同类条目（≥2 次复现才立项，单例不蒸馏）
2 novel.py task add revise_rubric style --evidence "lessons: <条目引用>"
3 编排者（或 editor 帽）改 tree/style.md：口癖黑名单加行 / 意象纪律补条 / 范文锚替换
4 novel.py commit <t> --file <staged style.md>    # 蒸馏专用轻量路径（F§16）：
   evidence 必填；目标限 style；rev 自动 +1；不递归标 stale（只约束未来章）
5 生效即强制：下一章 check --unit 起新黑名单命中=FAIL；写手经简报 §1 自动收到
```

> 界限：`tree/style.md` 是**项目侧**唯一可蒸馏判据登记处；skill 侧 `rubrics/*` 不随项目改（它们是发行物）。需要结构/设定级变更的教训走 revise_design（有 stale 波及，须影响面报告，C§4）。

## 7. 三张覆盖表（模式/路线/档位怎么叠）

### 7.1 solo 帽子映射（B/D 档；纪律见 mode-solo §1）

| 主线环节 | 帽子 | 特别纪律 |
|---|---|---|
| 排批/装简报/commit/裁决 | 编排者帽 | 唯一写者；附笔只在 commit 前一刻 |
| §3 交接 3 写正文 | 写手帽 | 输入白名单=简报全文；摘帽前泄漏自查 |
| §3 交接 4 抽取对账 | CLI（B 档）/ extractor 帽（D 档，roles/extractor.md） | 机检永远先于评审 |
| §3 交接 5 轻评 | critic-light 帽 | 逐条引判据编号；不给不可执行建议 |
| §4 深评 | critic-deep 帽（新会话冷读，mode-solo §4） | 禁读自己的 writeback/轻评单 |
| §2 设计庭 | 三件套降级（mode-solo §3）：1 提案+自我攻击 / 判据自评 / 抽人设卡 | 否决案台账是唯一的「另一个大脑」 |

### 7.2 traditional 差分（叠加层；全文 route-traditional）

| 主线环节 | 差分 |
|---|---|
| §3 章循环 | 细纲工序前置（beats 6–10 拍+scene_intents）；每章必有 turn；章尾钩降建议级 |
| §4 buffer/publish | **整段移除**（无连载发布）；`gate publish` 不使用 |
| §4 深评 | 三遍修订制替代采样深评；判据换 scene-value/theme/imagery |
| §5 卷末 | classic24 全书节拍对账替代爽点大节奏 |

### 7.3 C/D 档降级（无 shell；诚实降级协议 manual-check）

| 主线环节 | 降级 |
|---|---|
| 一切 gate/check/commit 副作用 | 失 → manual-check §1 逐项人工 + 手做台账回写；§2 损失清单**先申明再开工** |
| §3 交接 4 抽取器 | extractor 帽手工对账（roles/extractor.md；低召回，如实标注） |
| §4 knowledge 盘点 | 手翻 `ledgers/facts/*.json` 的 spoiler/known_by 字段 |
| gate next 剧本 | 回到人脑：每会话开工按本文件 §1 总图自查一遍 |

## 8. 主循环军规（十条，违者必出账差）

1. 文件即记忆：没落盘的共识不存在（SKILL 公理 1）。
2. commit 是唯一写路径；published 永不改写。
3. 每个 worker/帽子交接必过其验收谓词；不许「先干了再补检查」。
4. spawn/戴帽前基线必须干净；附笔只在 commit 前一刻写。
5. 机检永远先于评审；评审裁 NEEDS_REVIEW，不复查机器已判项。
6. 回执必须落盘（review add）；revise 后旧回执自动作废。
7. 写手不发明简报外专名；known_by 外的角色不说破事实；spoiler 事实只可潜台词。
8. 同目标失败 ×2 自动升级设计层，勿硬写第 3 次。
9. 教训 ≥2 次复现走蒸馏（revise_rubric）；单例记 lessons 不动判据。
10. 迷路 = `status` + `gate next` + `stage current`，不凭记忆续写；换环节必 `stage enter`
    （阶段闸门会替你拒绝跨阶段操作，别跟它讲道理，去收口）。

---

*rev 4 · 2026-08-25 · P8 批次：知识所有权分区对齐（§1.1 卷庭 K 池 6 块、diag 只取专属 33 块池）+ §4 知情圈对账行（知识矩阵 v2：fac/loc/item 范围知情，F§9）。*
*rev 3 · 2026-08-25 · P7-S 阶段强制闸门：§0 军规改「进环节 = stage enter + 读包」+ §1.1 迁移链与 enter 语义 + §2/§4/§5 各环节动作列前置 stage enter + 军规 10 补 stage current/enter；辖区表见 F§15。*
*rev 2 · 2026-08-25 · 阶段×知识编排：§0 加「进环节先读阶段包」军规 + §1.1 阶段↔配套包对照表 + §4 欠账行接 gate next 超龄顶出；与 protocol/knowledge-orchestration.md、protocol/stages/ 十一包、`novel.py stage` 同批落地（P6-S）。*
*rev 1 · 2026-08-25 · 初版：主循环脊柱 + 交接契约表 + knowledge/蒸馏回路 + solo/traditional/C·D 三覆盖表；与 gate 修复提示（P4-G）、knowledge CLI（P4-K）、rollup（P4-R）、revise_rubric（P4-D）同批落地。*
