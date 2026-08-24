# capability-profiles — 宿主能力四档与降级矩阵（可移植性 SSOT）

> 本 skill 要能被**任意 agent 产品**加载。宿主差异收敛为两个布尔探测：
> ① 能否 spawn 子代理；② 有无 shell+python3。两两组合 = 四档运行剖面。
> `SKILL.md` §1 三问中的前两问在此展开；第三问（人是否在环）是**正交开关**
> （`unattended`，见 §4），不改变档位。

## 0. 探测方法（进入任务先跑，结果记入首个 task note）

| 探测 | 方法 | 判定 |
|---|---|---|
| spawn | 产品是否提供 Task/subagent 类工具（试列工具清单） | 有 → 多代理；无 → 单代理帽子协议 |
| shell | 尝试 `python3 tools/novel.py --help`（退出码 0） | 成功 → 机检交 CLI；失败 → 有损降级 |

探测结果**会变**（产品升级/会话切换）：每次冷启动重测；档位提升时补跑欠账机检
（`check --project` + `gate next`），档位下降时按 §3 声明损失。

## 1. 四档剖面总表

| 档 | spawn | shell | 模式叠加 | 一句话定位 |
|---|---|---|---|---|
| **A 全量** | ✅ | ✅ | `mode-orchestrated` | 设计目标态：信息沙箱 + 机器闸门全开 |
| **B 单代理** | ❌ | ✅ | `mode-solo` | 帽子协议模拟沙箱；机器闸门全开 |
| **C 无甲板** | ✅ | ❌ | `mode-orchestrated` + `protocol/manual-check.md` | 沙箱在、机检丢：靠人工自查表兜底 |
| **D 底线** | ❌ | ❌ | `mode-solo` + `protocol/manual-check.md` | 双损降级：只剩文件契约与纪律自觉 |

> route（web/traditional）是内容路线，与档位正交：任何档都可叠加
> `modes/route-traditional.md` 差分。

## 2. 各档能力对照（保 / 降 / 失）

| 能力 | A | B | C | D |
|---|---|---|---|---|
| 信息沙箱（写手只见简报） | 保（物理隔离） | 降：帽子协议 + 泄漏自查（mode-solo §1） | 保 | 降：同 B |
| 对抗评审（异族多方案） | 保 | 降：1 提案+判据自评+抽人设卡（mode-solo §3） | 保 | 降：同 B |
| 机检断言集（check --unit/--window/--project） | 保 | 保 | 失→人工表（manual-check §1） | 失→人工表 |
| 抽取器对账/跨章指纹/故事日历 | 保 | 保 | **失**（manual-check §2 明示） | **失** |
| 台账自动回写（commit 副作用） | 保 | 保 | 失→逐项手做（manual-check §1 末段） | 失→逐项手做 |
| 队列自动化/gate 剧本/rollup | 保 | 保 | 失→队列 ≤10 条 + 人脑剧本 | 失→同 C |
| 原子提交/半事务检出 | 保 | 保 | 失→`.bak` 副本纪律 | 失→同 C |
| git 泄漏检查基线 | 保 | 保 | 视宿主（有 git 无 python 也可跑 §git 纪律） | 视宿主 |
| 评审回执落盘（reviews/） | 保（review add） | 保 | 降：手写回执文件（manual-check §1） | 降：同 C |

## 3. 降级声明纪律（C/D 档强制）

1. 项目启动（或档位下降）时，把 `manual-check.md` §2 损失清单**原样呈报用户**，
   不得含糊为「功能略有受限」；unattended 时写入首个 task note。
2. 每章 writeback 的 `issues` 记录人工自查结论（前缀 `manual-check:`）；没写=没查。
3. C/D 档**不承诺**百万字规模一致性——超过 ~200 章仍无 shell 时，应建议用户
   迁移宿主或导出项目到有 shell 的环境跑一次全量 `fsck` 对账。

## 4. 正交开关：人在环（unattended）

| 开关 | 行为 |
|---|---|
| `unattended=false`（默认） | `approvals.*` 命中的动作（书/卷定稿、publish、checkpoint）呈报用户当轮确认；红线一票上报 |
| `unattended=true` | 照常执行 + `note: pending_human_review` 留痕（formats §19）；红线仍**必须停手**——无人可裁时挂起任务，不自我豁免 |

## 5. 档位速查（冷启动决策树）

```
能 spawn？ ──否──→ 能跑 python3？ ──否──→ D：mode-solo + manual-check（§3 声明损失）
   │                    └──是──→ B：mode-solo（机检全开）
   └─是──→ 能跑 python3？ ──否──→ C：mode-orchestrated + manual-check（§3 声明损失）
                        └──是──→ A：mode-orchestrated（设计目标态）
```

任一档就绪后：`route` 按用户意图定（web 默认 / traditional 差分）→ 按
`SKILL.md` §3 冷启动或 §4 契约表进入任务。
