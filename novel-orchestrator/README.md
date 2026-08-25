# novel-orchestrator — 长篇小说全生命周期作业系统

一个可被任意 agent 产品加载的统一 Skill：**开书 → 卷/弧规划 → 章节流水线写作 → 一致性核查 → 连载运营 → 收束**，覆盖百万字网文连载与传统长篇两条路线。

- **Agent 入口**：只读 [`SKILL.md`](SKILL.md)（L0 薄路由），按任务契约表加载最小文件集。
- **人类入口**：本文件 + `protocol/formats.md`（文件与 CLI 契约）。
- 前身 `novel-writing-workflow`（v1）已随技术债清理**移除**；旧项目迁移对照 `protocol/glossary.md` §2 的 v1→v2 映射表。

## 设计概要

三层结构，各司其职：

| 层 | 内容 | 运行期是否加载 |
|---|---|---|
| 协议层 | `protocol/`（主循环/产线/设计庭/连载运营/文件契约/术语）、`modes/`（三模式） | 按任务加载对应章节 |
| 判据与角色层 | `rubrics/`（11 张带阈值判据卡）、`roles/`（12 张角色卡）、`personas/`（9 张）、`rhythm/`、`templates/` | 评审/规划时加载单卡 |
| **阶段编排层** | `protocol/knowledge-orchestration.md`（11 阶段目录+装载硬规则）+ `protocol/stages/`（每阶段一个配套知识包：必读/K 池/禁读） | 阶段入口读对应包（≤80 行）；`novel.py stage current` 导航 |
| 知识层 | `knowledge/`（111 块方法论）+ `knowledge-blocks.md`（锚点）+ `knowledge-map.md`（块级归属台账） | **默认不加载**；庭审附件经阶段包 K 池、诊断经 diag 阶段按块进入 |

三种运行模式（`SKILL.md` §2 路由）：

- **orchestrated**：可 spawn 子代理的产品。编排者只管调度，写手/评审在信息沙箱（十节简报）内工作。
- **solo**：单代理产品的降级路径。同一个 agent 顺序戴「编排者/写手/评审」帽子，庭审降级为 1 提案 + 判据自评 + 抽人设卡。
- **traditional**：传统长篇差分。无 buffer/publish，加细纲工序，全书按 classic24 节拍；自有判据卡（scene-value/theme/imagery）与文学口味人设卡双票制。

宿主能力（能否 spawn × 有无 shell）四档剖面与逐档降级矩阵见 `modes/capability-profiles.md`——任何 agent 产品都能落在四档之一运行本 skill。

## 快速开始（5 分钟绿路径）

需要 python3（仅标准库）。以下命令均已在冒烟测试覆盖（`tools/tests/test_smoke.py`，101 步全绿，含 15 条负例）：

```bash
cd novel-orchestrator
python3 tools/novel.py --help                     # 查看全部子命令

python3 tools/novel.py init ~/my_book --name 我的书   # ① 脚手架（含 git init）
cd ~/my_book
python3 tools/novel.py status                     # 仪表盘 + 可恢复断点
python3 tools/novel.py tree add volume vol_01     # ② 建卷/弧/章骨架
python3 tools/novel.py tree add arc arc_01_1
python3 tools/novel.py tree add chapter ch_0001 --parent arc_01_1
python3 tools/novel.py entity new char_zhu        # 实体卡与线索登记
python3 tools/novel.py thread new thread_main --kind promise
# …（填 chapters/ch_0001.task.json 任务卡：目标/拍/钩/爽点配额/cast）
python3 tools/novel.py task add write ch_0001     # ③ 写作循环
python3 tools/novel.py brief ch_0001              # 机械装配十节简报（预算 24000 字符）
# …（写手按简报产出 候选章.md + writeback.json）
python3 tools/novel.py check --unit ch_0001 --candidate 草稿.md --writeback 回写.json
python3 tools/novel.py commit t_000001 --chapter 草稿.md --writeback 回写.json -m 首章
python3 tools/novel.py check --window             # 3 章小爽/10 章大爽/线索余额/战力频率/故事日历
python3 tools/novel.py task done t_000001
python3 tools/novel.py review add ch_0001 --depth light --verdict pass   # 评审回执落盘 reviews/
python3 tools/novel.py tree set-status ch_0001 approved         # 仅认落盘回执（rev 匹配）才放行
python3 tools/novel.py publish ch_0001            # 连续性谓词，approved→published
python3 tools/novel.py gate next                  # 机器版调度剧本：下一步该干什么（末行附阶段推断）
python3 tools/novel.py stage current              # 当前阶段 + 配套知识包路径（stage list/show 看全目录）
```

连载运营与收编（同样有 CLI，全部在冒烟测试覆盖）：

```bash
python3 tools/novel.py retcon <fact_id> --new "修正后事实" --strategy reconcile \
    --decision dec_XXX                            # 已发布内容修错（facts 作废链）
python3 tools/novel.py report volume vol_01       # 卷末导出对账报告 state/reports/
python3 tools/novel.py checkpoint vol_01          # 卷末结账（报告绿才放行）
python3 tools/novel.py adopt 旧稿.md --as ch_0001 --parent arc_01_1   # 存量旧稿收编
python3 tools/novel.py check --leak 草稿.md --brief briefs/ch_0002.brief.md   # 泄漏扫描
python3 tools/novel.py knowledge query            # 知识矩阵：读者未知欠账盘点（--fact/--entity 细查）
python3 tools/novel.py rollup                     # 批量手改 meta 后重算章→弧→卷摘要
```

复跑测试：`python3 tools/tests/test_smoke.py`（101 步端到端）、
`python3 tools/tests/test_longrun.py`（35 章长程合成 + 中途返修，验证规模化不变量）、
`python3 tools/tests/test_refactor.py`（重构专项回归，140 步）与
`python3 tools/tests/test_stage.py`（stage CLI + 阶段包↔knowledge-map 三方对账 + 引用死链扫描）。

## 一致性核查的三级闸门

1. **机器闸门**（`novel.py check` / `gate`）：信封/必需节/状态机/三件套对账、style 黑名单逐条扫描、连续同首句、章内 4-gram 重复率、跨章分层指纹（窗口内 12 字复读 FAIL 级告警 + 8 字撞梗 WARN，窗口外归档采样覆盖全史）、回写引用越权（未登记实体/线索 FAIL）、**抽取器对账**（正文实测出场 vs 申报、新专名候选、剧透泄漏候选、known_by 角色知识越界候选）、线索状态机迁移表、payoff id 章号匹配、facts 冲突扫描、3 章小爽 / 10 章大爽窗口、promise 余额、战力变更频率、**故事日历**（elapsed 数值化 + story_date 单调）、published 连续性、facts/retcon 引用完整性、decision/review 文件契约、泄漏扫描（`check --leak`）、半事务检出（`fsck`）；gate 试跑每条 FAIL 附可执行修复命令。
2. **角色评审**（LLM 判定，机检输出 `NEEDS_REVIEW` 的项）：声纹遮名指认、智商漂移、爽点有效性、毒点七问、知识边界（剧透/known_by 越界裁定）——按 `rubrics/` 对应卡执行，逐章轻评、抽样深评。
3. **人工审批**（可配置）：开书 commit、卷末 checkpoint、发布、红线上报。

## 目录

见 `SKILL.md` §8 目录速查；每个子目录均有自己的 README 或卡头说明。工具实现覆盖表与已知限制见 `tools/README.md`。

## 已知限制

- 机检不能判定主观质量（是否好看、爽点是否有效）；这些永远走角色评审，工具只保证「不可判项被显式列出」而非假装通过。
- 无 python3 环境属**有损降级**：可人工项与直接丢失能力清单见 `protocol/manual-check.md`，须向用户明示，强烈建议提供 shell。
- 增量章级 index 基于文件 mtime 判断新旧；极端情况（时钟回拨、批量 touch）需 `status` 全量重算兜底（自动发生，仅性能差异）。
