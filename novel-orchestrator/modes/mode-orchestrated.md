> 当前升级约定：按 `protocol/reliability.md`（同目录为 reliability.md）执行证据回执、历史视图和安全恢复；旧流程中的 pass 要附逐项证据，人工附笔需单独确认保存，不能假定后续 CLI 会替它进入事务。

# mode-orchestrated — 多代理编排模式作业手册

适用：产品可 spawn 子代理（Task/subagent 工具）。你（读到本文件的 agent）担任**编排者**，
全程不亲自写正文、不亲自评审——你的产出是：任务、简报、裁决、落盘。

前置：`python3 tools/novel.py --help` 可运行；已按 `SKILL.md` §1 完成能力探测。

## 1. 全书主循环（装配总图）

> 主循环的**逐环节作业表**（入口闸门/CLI/角色/判据/失败去向 + 各棒交接验收谓词）
> 在 `protocol/workflow.md`——本节只给鸟瞰；对表干活以 workflow 为准。

```
init（CLI）
  └─ 书庭 S1→S4（protocol/court.md）→ book/world/style commit
       └─ 卷庭（court §1 vol 行）→ vol_NN commit
            └─ 弧规划（court §1 arc 行,简式）→ arc_NN_n commit
                 └─ 排批：为弧内每章 tree add chapter + 填 task.json
                      └─ 单章产线循环（protocol/pipeline.md §1）×N
                           ├─ 每 deep_every 章：深评采样（pipeline §4）
                           ├─ buffer 水位动作（serial-ops §1）→ publish（§2）
                           └─ 弧末：check --window + 线索对账
                 └─ 卷末 checkpoint（serial-ops §4）→ 下一卷
```

每个箭头处都有 CLI 断点：崩溃/换会话后 `novel.py status` + `task next` 即可恢复，
不需要重读历史会话。

## 2. spawn 纪律（信息沙箱）

1. **spawn prompt = 角色卡 + 附件清单**。模板见 `protocol/pipeline.md` §7 与
   `protocol/court.md` §5；角色的职责/输出契约/禁止事项一律以 `roles/*.md` 原文投递，
   不要转述（转述会丢阈值）。附件构成以当前阶段的配套知识包为准
   （`protocol/stages/`；`novel.py stage current` 打印当前包路径）。
2. **写手只见简报**：先 `novel.py brief ch_NNNN` 生成十节简报，把简报全文作为写手唯一输入。
   写手不得访问项目目录。评审角色只投递「产物 + 对应 rubric 卡 + 简报相关节」。
3. **泄漏检查**（pipeline §5，强制）：每个 worker 返回后，扫描产物中的专名/设定是否超出
   其输入范围；泄漏 → 产物作废重 spawn，并记 lessons。
4. **返回即结构化**：worker 返回必须符合 `SKILL.md` §5 最小回应契约；不合格视为失败，
   计入 `task fail`（2 次自动升级 revise_design）。

## 3. 单章循环速查（与 CLI 的接口点）

| 步 | 动作 | 命令/依据 |
|---|---|---|
| 0 | 会话开工 | `novel.py gate next`（机器剧本：修账/深评/对账欠账先清） |
| 1 | 取任务 | `novel.py task next` → `task start <tid>` |
| 2 | 装配简报 | `novel.py brief ch_NNNN`（条目级预算裁剪并留溯源） |
| 3 | spawn 写手 | 先 `novel.py gate write ch_NNNN`（排批齐/简报在/基线净）；过闸后投 `roles/writer.md` + 简报全文 |
| 4 | 机检候选 | `novel.py check --unit ch_NNNN --candidate 草稿.md --writeback 回写.json`（含抽取器对账） |
| 5 | 轻评审 | spawn `roles/critic-light.md`；裁定机检的 NEEDS_REVIEW 项 |
| 6 | 落盘 | `novel.py commit <tid> --chapter 草稿.md --writeback 回写.json -m …` |
| 7 | 收尾 | `review add ch_NNNN --depth light --verdict pass`（回执落盘）→ `task done <tid>` → `gate approve` → `tree set-status ch_NNNN approved` |
| 8 | 周期项 | 每 5 章 `check --window`；每 `deep_every` 章深评；每 `reconcile_every` 章 `entity due`；弧末/卷末 `knowledge query` 盘点读者未知欠账（workflow §4） |

修订循环、escalate 升级、深评采样的细则不在本文件重复——见 `protocol/pipeline.md` §2–4。

## 4. 设计庭装配

- 庭型/触发/预算：`protocol/court.md` §1–2；回合协议 R0–R4：court §3。
- 提案人（Architect）≥2 名、立场互斥；评审团 = structure-critic + reader（抽 `personas/`
  1–3 张）+ safety-auditor（红线一票升级）；editor 合成裁决。
- 裁决产物走 `novel.py commit <design任务> --file <staged 节点文件> --file <dec_*.md>`：
  CLI 校验必需节非空才置 committed，decision 按 id 自动路由到 `court/`。
- 重开已裁决事项：先查否决案台账（court §4 X7），无 `reopen_requires` 要求的新证据一律拒绝。

## 5. 无人值守与降本

- `unattended=true`：审批点降级为「执行 + note: pending_human_review」（formats §19）。
- 成本档位（config.preset）与各角色模型档位：`protocol/pipeline.md` §6。
- 子代理不可用时**临时**退化：本会话按 `modes/mode-solo.md` 帽子协议顶班，恢复后切回。
