> 当前升级约定：按 `protocol/reliability.md`（同目录为 reliability.md）执行证据回执、历史视图和安全恢复；旧流程中的 pass 要附逐项证据，人工附笔需单独确认保存，不能假定后续 CLI 会替它进入事务。

# serial-ops.md — 连载运营协议(编排者操作手册)

> 依据 spec §5.6/§10;buffer/发布顺序谓词/retcon/卷末 checkpoint 教义收编自 v1 连载手册(v1 已移除,只迁思想不迁机制);格式与 CLI 以 `protocol/formats.md`(F§n)为准。
> **装载契约**:本协议各环节=ops 阶段,零 knowledge/ 装载(白名单见 `protocol/stages/ops-serial.md`);
> 反馈归因需要学理支撑时=编排者转 diag 阶段(`protocol/stages/diagnose.md`),不给运营角色开库。

## 1. buffer 语义与水位动作表

- **ready(存稿)** = `status=approved ∧ 章号 > cursor.last_published` 的章数;真值由 `novel.py status` 的 dashboard/index 给出(F§14),**不手数**。
- 配置:`buffer.target`(默认 3)、`buffer.min_before_publish`(默认 1)(F§13)。
- 教义:发布节奏与写作节奏解耦;存稿章必须是 approved,禁以 drafted 充发布。

| 水位 | 动作 |
|---|---|
| ready ≥ target | 可稳定发布;富余产能投给深评/对账轮/远期设计任务 |
| 1 ≤ ready < target | 优先排 write 批补稿;发布减速;暂停 revise_design 类大改 |
| ready = 0 | 停发或降频;只跑 write 与必要排批;**禁硬写空转章充数** |
| 首发 | ready ≥ min_before_publish 方可首次 publish |
| 结构性堵塞(连章 revise/escalate) | 先深评归因(pipeline.md §4)再动工,不以量补质 |

## 2. publish(发布)

- **连续性谓词**(F§16):发布区间必须构成**自 `last_published+1` 起的连续区间**;乱序/跳章 → novel.py 退出码 1 拒绝并指出缺口章号;无绕过开关。
- **审批**(F§19):`approvals.publish=true` → 呈报区间+各章标题+发布后 buffer 余量,用户当轮确认;`unattended=true` → 照常执行,task note 记 `pending_human_review` 留痕。

```
用户「发布 1–N」/ 计划发布到期:
  novel.py task add publish ch_NNNN --note "至 ch_MMMM"   # 计划性发布入队;用户当轮口头指令可免
  前置自检: novel.py gate publish <ch_from> [<ch_to>]     # 连续性/approved/buffer 谓词试跑,不落盘
            novel.py status(ready/缺口/告警;必要时 novel.py check --window)
  审批(如上)→ novel.py publish <ch_from> [<ch_to>]        # 各章 approved→published(F§16)
  novel.py task done <t>  ;  novel.py status 复核游标与 buffer
拒绝速查: 区间含非 approved 章 | 区间不连续/有缺口 | 首发 buffer 不足 → 按 §1 补稿或改区间重试
```

## 3. retcon(已发布不可变)

教义:`published` 章的正文与既有事实**不可变更**(F§3);v2 **无解锁路径**。一切已发布内容问题在 **facts 层**做向前兼容:后续章按新事实写,旧文一字不动。

```
发现渠道: 轻评/深评问题清单 | 读者反馈(§6) | novel.py fsck / check --project 悬空引用
流程:
  1 编排者写裁决记录 dec_NNN_{slug}.md(F§11:何错/为何不改旧文/选何策略)
      ——附笔,随本任务 commit 前一刻写入,同事务入库(court.md §3 附笔纪律)
  2 novel.py task add retcon <fact_id> --note "<dec_id>"
  3 novel.py retcon <fact_id> --new "<新事实>" --strategy reconcile|fade_out|explicit_fix \
        --decision <dec_id> [--entity char_x ...]
      # CLI 校验: old_fact 存在且未被覆盖 + decision 文件在 court/ 真实存在,全过才落盘
      # 自动: retcons[] 追加 {id, old_fact_id, new_fact, strategy, decision_ref},
      #       旧 fact 填 superseded_by,git 入库
  4 novel.py check --project ; novel.py task done <t>
效果: 旧 fact 填 superseded_by;此后简报第 6 节命中该实体自动连带 retcon 条目(F§9 纪律)
      ——写手无需被通知,包内自带;strategy=explicit_fix 时,编排者在最近一次排批的
      task.json beats 中排入「文内圆回」拍(CLI 会打印此提醒)。
禁: 重写已发布正文 | 删改 facts 既有记录 | 未发布章误走 retcon(未发布 → pipeline.md §2 revise)
   | 对已覆盖 fact 重复 retcon(CLI 拒绝;再改先按 F§9 登记新 fact 再覆盖)
```

## 4. 卷末 checkpoint

触发:卷内最后一章 approved(或用户宣布收卷)。**checkpoint 未完成不开下卷卷庭。**

```
0 novel.py check --project                 # 先确认全仓一致
1 novel.py report volume vol_NN            # 汇编卷报告 → state/reports/vol_NN.md
    内容: exports 对账底稿(每条预标 [待对账])+线索健康+payoff 统计+战力变化(power 台账)
          +窗口告警快照+checkpoint 前置清单
2 exports 逐条对账: 编辑 state/reports/vol_NN.md(唯一允许手改处,F§14),每条改三态:
    [兑现 ch_NNNN] — 卷内已落实,记支撑章号
    [移交]         — 未兑现且仍要 → checkpoint 自动写入下卷 imports 预填
    [废止 dec_xxx] — 不再兑现 → 先写 dec_NNN(理由+reopen_requires),防幽灵承诺复活
3 卷级深评: novel.py task add review_deep <卷末章> → spawn critic-deep 卷级变体
    (附件改为: 卷蓝图+卷报告+三态对账草案+active threads+ledger 统计+rubrics/power.md;
     判卷弧光兑现/未收线健康/期待账户/战力预算对账/跨卷撞梗)
    → lessons 附笔 → novel.py commit <t> --file <review>(pipeline.md §4 同款)
4 更新 ledgers/recap.md: 追加本卷段落(3–6 行,F§9)——checkpoint 后简报 §2 靠它接续
5 呈报用户确认(卷报告+三态对账+深评要点);unattended=true → 执行+note: pending_human_review
6 novel.py gate checkpoint vol_NN          # 前置谓词试跑(报告/三态/未完稿章),FAIL 即回步骤 1–4
  novel.py task add checkpoint vol_NN → novel.py checkpoint vol_NN → task done <t>
    # F§16 checkpoint 行: 机检 报告存在+三态无残留+卷内无未完稿章;
    # 落盘 卷 checkpoint_at 标记 + 下卷 volume.md(缺则实例化)imports 预填
7 novel.py task add design vol_{N+1} --note "卷庭"    # 开庭规程见 court.md §2/§3
```

## 5. 实体对账轮(reconcile)

节律:每 `reconcile_every` 章(默认 10,F§13)在批间隙跑一次;`novel.py entity due` 非空即应跑。

```
novel.py task add reconcile <游标章> --note "对账轮"
novel.py entity due            # 名单: last_event_ch - last_reconcile_ch ≥ 阈值(F§7)
spawn 资料员(对账变体,见下)→ 逐实体返回新「## 现状」节 + 别名增改清单
for 实体 in 名单:
  novel.py entity update <id> --file <tmp 现状节>   # 仅替换现状节,日志不动;记 last_reconcile_ch(F§7)
别名增改 → 编排者附笔 entities/aliases.json,随本任务事务入库
novel.py task done <t>
```

资料员对账变体 spawn:在 pipeline.md T1 骨架上,任务改为——「对下列实体:把事件日志合并进现状字段(固定键见 formats.md §7);发现别名漂移/新别名列出;产出=每实体一个『## 现状』节 + 别名清单」;其余(角色文件、只读权、通用尾注)不变。

## 6. 读者反馈

收件箱:`data/feedback/`(自由格式;用户或外部脚本投递,编排者只读不整理)。
触发:用户转达「第 X 章读者说…」,或 `novel.py status` 后例行扫收件箱新文件。

```
spawn 数据分析(T-da): 附 新反馈文件、游标与近 10 章清单、reviews/ 近期 verdict 摘要、
    ledger payoff|promise 统计输出
→ 症状报告(最终回复): 症状 | 证据(引反馈原文+章号) | 归因假设 | 建议动作类型
编排者按报告开任务(呈报用户后执行,spec §10):
  设定/结构层问题 → novel.py task add revise_design <node> --evidence "<症状+反馈引用>"
                     # 先过否决案台账(court.md §4),再出影响面报告
  已发布事实错误 → §3 retcon 流程
  未发布章质量   → novel.py task add revise ch_NNNN --note "<反馈要点>"
  文风病复发(同类吐槽/教训 ≥2 次) → novel.py task add revise_rubric style --evidence
                     "<lessons/反馈引用>"   # 蒸馏进 style 黑名单,机检即刻强制(workflow §6)
  无动作         → 症状要点记 task note 归档,不动工(单条差评不足以立项)
```

**T-da 数据分析 spawn 模板**(`<skill根>` = 本 skill 在产品中的实际安装路径,spawn 时填充)
```
你是数据分析。先读:<skill根>/roles/data-analyst.md
附件:data/feedback/ 新文件、游标与章清单、近期评审 verdict 摘要、payoff/promise 统计。
任务:把原始反馈翻译成症状(弃读点/爽点断供/人设崩/设定矛盾/节奏拖沓),逐条给证据与
建议动作类型(revise_design|retcon|revise|无动作);不替编排者做裁决,不给改稿方案。
产出:症状报告,按「症状|证据|归因假设|建议动作」四列逐条列。
[通用尾注:产出只放最终回复;禁止写入任何文件、禁止执行任何写命令。]
```

---

*rev 5 · 2026-08-25 · 装载契约接阶段包(ops=零 K,白名单在 stages/ops-serial.md;归因深读转 diag)(P6-S)。*
*rev 4 · 2026-08-25 · 反馈分诊补 revise_rubric 蒸馏去向;gate 试跑 FAIL 现自带「下一步」修复命令(P4-G)。*
*rev 3 · 2026-08-24 · publish/checkpoint 前置接 gate 谓词试跑(先判后写)。*
*rev 2 · 2026-08-24 · retcon/report/checkpoint 全面 CLI 化;补 recap 维护步骤与 power 对账;与 formats.md rev 2 对齐。*
