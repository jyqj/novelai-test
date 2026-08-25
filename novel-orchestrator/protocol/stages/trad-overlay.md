# stage:trad — 传统路线差分 配套知识包（叠加层，不是串行阶段）

| 键 | 值 |
|---|---|
| 阶段 | trad：`config.route=traditional` 时叠加在宿主阶段（s4/arc/write/review）之上的装载差分 |
| 进入 | config.json `"route": "traditional"`（modes/route-traditional.md 全文是规则 SSOT，本包只管装载） |
| 退出 | 随宿主阶段；完稿闸门=三遍修订全绿（route-traditional §4） |
| 本包读者 | 编排者 + 对应宿主阶段角色 |

## 判据卡置换表（装载差分的核心）

| 宿主阶段 | web 默认装载 | traditional 置换/追加 |
|---|---|---|
| s1（概念庭） | personas 网文卡 | 读者代表固定 `personas/literary-purist.md` + `personas/bookclub-mainstream.md` 双卡 |
| s4（分卷庭） | rhythm/ 五选一 | 全书骨架固定 `rhythm/classic24.md`（24 节拍映射卷/弧边界） |
| arc（细纲工序） | 三拍粗批 | 追加 `rubrics/scene-value.md`（场景合法性 + turn 验收；route-traditional §2） |
| write（章循环） | 轻评三卡 | 轻评判据不变；章尾钩降建议级（CLI 已按 route 自动降级，route-traditional §3） |
| review（三遍修订） | 采样深评 | 结构遍加 `rubrics/theme.md`；场景遍加 `rubrics/scene-value.md`；语言遍加 `rubrics/imagery.md` |

## 知识装载纪律（与 web 相同，无豁免）

- 本差分**不新增任何 knowledge/ 权限**：细纲工序可用的 K 块在 arc 阶段包选读池内
  （`protocol/stages/arc-plan.md`）；章循环仍零装载；三遍修订只读判据卡。
- 文学向疑难（主题贯穿/意象系统失灵等）同样走 diag 阶段症状路由，不开后门。

## 退出前自查

- 三遍修订每遍产出问题清单并逐条走 revise 任务（机检+评审照常）；
- 双人设卡同场投票（literary-purist 把语言主题关，bookclub-mainstream 把可读性关）。
