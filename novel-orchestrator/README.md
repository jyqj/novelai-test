# novel-orchestrator — 长篇小说全生命周期作业系统

一个可被任意 agent 产品加载的统一 Skill：**开书 → 卷/弧规划 → 章节流水线写作 → 一致性核查 → 连载运营 → 收束**，覆盖百万字网文连载与传统长篇两条路线。

- **Agent 入口**：只读 [`SKILL.md`](SKILL.md)（L0 薄路由），按任务契约表加载最小文件集。
- **人类入口**：本文件 + `protocol/formats.md`（文件与 CLI 契约）。
- 前身 `novel-writing-workflow`（v1）已废弃，见 `legacy/README.md` 与迁移映射 `protocol/glossary.md`。

## 设计概要

三层结构，各司其职：

| 层 | 内容 | 运行期是否加载 |
|---|---|---|
| 协议层 | `protocol/`（产线/设计庭/连载运营/文件契约/术语）、`modes/`（三模式） | 按任务加载对应章节 |
| 判据与角色层 | `rubrics/`（8 张带阈值判据卡）、`roles/`（11 张角色卡）、`personas/`、`rhythm/`、`templates/` | 评审/规划时加载单卡 |
| 知识层 | `knowledge/`（111 块方法论）+ `knowledge-blocks.md`（锚点）+ `knowledge-map.md`（归属） | **默认不加载**；诊断/庭审深读才按块进入 |

三种运行模式（`SKILL.md` §2 路由）：

- **orchestrated**：可 spawn 子代理的产品。编排者只管调度，写手/评审在信息沙箱（十节简报）内工作。
- **solo**：单代理产品的降级路径。同一个 agent 顺序戴「编排者/写手/评审」帽子，庭审降级为 1 提案 + 判据自评 + 抽人设卡。
- **traditional**：传统长篇差分。无 buffer/publish，加细纲工序，全书按 classic24 节拍。

## 快速开始（5 分钟绿路径）

需要 python3（仅标准库）。以下命令均已在冒烟测试覆盖（`tools/tests/test_smoke.py`，31 步全绿）：

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
python3 tools/novel.py check --window             # 3 章小爽/10 章大爽/线索余额
python3 tools/novel.py tree set-status ch_0001 approved
python3 tools/novel.py publish ch_0001            # 连续性谓词，approved→published
```

冒烟测试关键输出摘要（真实运行）：

```
OK 16: novel.py check --unit ch_0001 --candidate (exit=0)   # 合规候选放行
OK 17: novel.py check --unit ch_0001 --candidate (exit=1)   # 黑名单命中被拒（负例）
OK 21: 实体事件日志已回写
OK 22: 线索推进已回写
OK 23: 爽点台账已登记 realized=1
OK 31: novel.py publish ch_0003 (exit=1)                    # 跳章发布被拒（负例）
SMOKE PASS：31 步全绿（含 2 条负例拒绝）
```

复跑：`python3 tools/tests/test_smoke.py`。

## 一致性核查的三级闸门

1. **机器闸门**（`novel.py check`）：信封/必需节/状态机/三件套对账、style 黑名单逐条扫描、连续同首句、章内 4-gram 重复率、跨章 12 字指纹、3 章小爽 / 10 章大爽窗口、promise 余额、时间线非负、published 连续性、facts/retcon 引用完整性。
2. **角色评审**（LLM 判定，机检输出 `NEEDS_REVIEW` 的项）：声纹遮名指认、智商漂移、爽点有效性、毒点七问——按 `rubrics/` 对应卡执行，逐章轻评、抽样深评。
3. **人工审批**（可配置）：开书 commit、卷末 checkpoint、发布、红线上报。

## 目录

见 `SKILL.md` §8 目录速查；每个子目录均有自己的 README 或卡头说明。工具实现覆盖表与已知限制见 `tools/README.md`。

## 已知限制

- `retcon / checkpoint / report` 尚无 CLI 子命令，按 `protocol/serial-ops.md` 手工执行（文件契约完备，机检覆盖 facts/retcon 引用完整性）。
- 机检不能判定主观质量（是否好看、爽点是否有效）；这些永远走角色评审，工具只保证「不可判项被显式列出」而非假装通过。
- 无 python3 环境时协议仍可人工执行（`protocol/formats.md` §17 自查清单），但强烈建议提供 shell。
