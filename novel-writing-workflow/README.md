# novel-writing-workflow

通用小说创作**工程化** Skill：薄路由入口 + runtime 契约链 + 只读知识服务。

> **非目标**：文学理论课、单书项目手册。禁止绑定具体书名/角色/作品目录作为规范。

---

## 快速入口

| 你想… | intent | 先读 |
|--------|--------|------|
| 从零开项目 | `new_project` | [`SKILL.md`](SKILL.md) → [`runtime/project-scaffold.md`](runtime/project-scaffold.md)（**强制**） |
| **接管已有大纲/正文** | `new_project` 变体 **adopt** | scaffold **§1.4 Adopt**（逆向注册 + dry-run gate 定位阶段） |
| 从零开**网文** | `new_project`（`route=web`） | scaffold + [`runtime/web-serial-playbook.md`](runtime/web-serial-playbook.md) Fast-Start |
| 推进下一阶段 | `advance` | [`runtime/phase-contracts.md`](runtime/phase-contracts.md)；web 轨叠加 playbook |
| 写某一章/单元 | `write_unit` | 同上 + 目标 `ChapterPlan` |
| **修订/反馈落地** | **revise**（diagnose→Decision→change\|write_unit） | protocol §2.4 + conflict-playbook |
| **发布/定稿第 N 章** | **publish**（write_unit 快径） | protocol §2.4：touch 晋升 **locked** + 用户确认（`auto_publish` 自动发布见 playbook §6.4） |
| **查进度** | **report**（只读快径） | protocol §2.4：零写回 |
| 诊断堵车 | `diagnose` | protocol + [`knowledge-index.md`](knowledge-index.md) |
| 改设定/冲突 | `change` | [`runtime/conflict-playbook.md`](runtime/conflict-playbook.md) |
| 学方法 | `learn` | knowledge-index / blocks（**不写**项目资产） |

**每轮落盘前**（`learn` 除外）：过 [`runtime/writeback-acceptance.md`](runtime/writeback-acceptance.md)。

---

## 目录结构

```
SKILL.md                 # 薄路由入口（intent / BOOT / 阶段索引 / 网文 FS 短节）
README.md                # 本文件
runtime/
  protocol.md            # 总控：BOOT · 状态机 · 召回 · 回写 · BLOCK
  phase-contracts.md     # P1–P6：depends_on / I/O / gate / budget / 硬边界
  asset-types.md         # 资产 type + Manifest（与路径解耦）
  conflict-playbook.md   # detect→classify→decide→record→stale→sync|block
  glossary.md            # 术语 / 枚举唯一 SSOT
  project-scaffold.md    # new_project 强制脚手架
  web-serial-playbook.md # route=web：Fast-Start / 存稿 / 发布就绪 / 连载
  writeback-acceptance.md # DONE 前 writeback 硬验收
phases/01–06-*.md        # 薄操作清单（越界时以 phase-contracts 为准）
templates/               # 资产草稿壳（见下表）
  blueprint.md
  character-sheet.md
  world-setting.md
  status.md              # Status 单例
  manifest.md            # Manifest 注册表
  decision.md            # Decision 裁决留痕
  plot-spine.md          # PlotSpine（节点 0–23）
  chapter-plan.md        # ChapterPlan（hooks / content_blocks）
  …                      # sequence-map / scene-beat / manuscript-unit / thread / canon / recap / style-card 等
knowledge/**             # 111 块只读服务（01–04 + 05-连载运营；按 K-xxx 拉取）
knowledge-index.md       # 仅 diagnose / learn 路由
knowledge-blocks.md      # K-ID 目录
tools/
  validate.py            # 结构校验器（--skill 库检 / --project 项目检）
  README.md              # 用法
```

---

## 运行时管线

```
intent → mode → load_policy → run → writeback-acceptance → writeback
```

原则：**先资产后知识**；有 `knowledge_budget`；感知 `stale`；working/critique 默认无执行权。

### 接线要点

| 条件 | 强制装载 |
|------|----------|
| `intent=new_project` | `project-scaffold.md`（Scaffold Gate） |
| `Status.route=web` 或网文信号 | `web-serial-playbook.md` |
| 任意 intent 有资产写入（非 learn） | `writeback-acceptance.md`（M01–M13） |

### 六阶段（契约链）

| phase | 主产出 | 硬边界（禁止） |
|-------|--------|----------------|
| P1 Blueprint | `Blueprint` | 序列表、场景、章纲、正文 |
| P2 Rough | `PlotSpine`（节点 0–23） | **任何场景级**；节点=标题+一句话价值 |
| P3 Sequence | `SequenceMap` | 章纲、节拍定稿、正文 |
| P4 Detail | `SceneBeat` + Character/World **canon** | 按章内容块章纲、正文成稿 |
| P5 Chapter | `ChapterPlan` | 完整正文；擅改 canon |
| P6 Writing | `ManuscriptUnit` | 静默改 PlotSpine/SequenceMap/设定 |

序列编号：**0–23**（含序列 0 = Hook）。  
洋葱五层：**表象 / 行为 / 情感 / 信念 / 创伤**（id: `surface|behavior|emotion|belief|wound`）。  
资产 status：`draft | review | canon | locked | stale | archived`。

---

## Agent 启动顺序（摘要）

完整定义见 `runtime/protocol.md` §1。

1. 确认 `runtime/` 核心可读（**BOOT 七件套**，含 acceptance 与 web playbook[route=web]；scaffold 按 new_project 装载）  
2. 装载 `glossary` 枚举（不装 knowledge 正文）  
3. 有 Manifest → 读 Manifest + Status  
4. 解析 intent；不明则 ASK  
5. `new_project` → **scaffold**；`route=web` → **web-serial-playbook**  
6. preflight → load_policy → run → **writeback-acceptance** → writeback → report  

**C6**：仅 `diagnose` / `learn` 可打开 `knowledge-index.md`；`knowledge-blocks.md` 作为 K-ID 解析器全 intent 可查（只读），块定位用源文件 `<!-- K-ID -->` 锚点。

**知识预算**：每 phase `core`（必拉，有序）+ `situational`（按触发标签），见 `runtime/phase-contracts.md` §0.4。

---

## 类型别名（写回归一）

| 别名 | 正式 type |
|------|-----------|
| `ProseUnit` | `ManuscriptUnit` |
| `ThreadMap` / `ForeshadowLedger` | `Thread` |

详见 `runtime/asset-types.md` §0.3.1。

---

## 同步副本

若使用 Claude 技能目录，保持与本路径一致：

- 源：`skills/novel-writing-workflow/`
- 副本：`.claude/skills/novel-writing-workflow/`  
  至少同步：`SKILL.md` · `README.md` · `runtime/` · `phases/` · `templates/`

---

## 修订

- **2026-08-12** 深度审计重构：知识库 92 → **106 块**（新增 `knowledge/05-连载运营/`）；新增 `tools/validate.py` 校验器与 `templates/recap.md` / `style-card.md`；runtime 契约对齐（BOOT 七件套、manifest 分片、Recap 记忆层、auto_promote、复合键序列引用）。
- **2026-08-13** 修复轮：知识库 106 → **111 块**（新增内容安全与边界 / 开书商业工程）；publish 语义统一 = touch 晋升 **locked**（发布顺序谓词：连续区间，乱序 BLOCK）；`auto_promote` 增 `p4_canon_seed`；卷末 checkpoint 改人批（user）+ `unattended_mode` 降级协议；`auto_publish` 行为协议（playbook §6.4）；critic 独立子代理四查（contracts §7.9）；各域清单指针化到 writeback-acceptance。
