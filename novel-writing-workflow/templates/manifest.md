# Manifest 模板 — 资产注册表（root + 卷分片）

> **本模板实例化** `runtime/asset-types.md` `type: Manifest`。分三类实例：单例 **`manifest_root`**、每卷一片的 **`manifest_units_v{n}`** 与 **`manifest_decisions_v{n}`**。  
> 门禁以 `runtime/phase-contracts.md` 为准；注册/触摸/召回协议见 `runtime/protocol.md`；术语 SSOT `runtime/glossary.md`。  
> `[方括号]` 为占位。禁止绑定具体作品书名/角色名作字段语义；`project.name` 仅工作区显示名。

---

## 0. 分片设计

| 实例 | 承载 | 装载纪律 |
|---|---|---|
| `manifest_root` | `project` 元信息 + 单例/设计资产 entries（Status / Canon 系 / Blueprint / PlotSpine / SequenceMap 系 / Character / WorldRule / Thread / Decision（仅 open/active）/ Recap）+ 分片指针表 `unit_shards` / `decision_shards` | **BOOT 只读 root** |
| `manifest_units_v{n}` | 该卷 SceneBeat / ChapterPlan / ManuscriptUnit 三类 entries | P5 / P6 / write_unit 轮加读**当前卷**分片；禁止全分片装载 |
| `manifest_decisions_v{n}` | 该卷已完结（**非 open**）Decision entries | BOOT_3 不读；`change` / `diagnose` / 审计轮按需加载 |

注册路由：设计/单例资产 → root；章生产线三类 → 所属卷分片；Decision 先注册 root，卷末 volume_checkpoint 把本卷非 open entries 迁入 `manifest_decisions_v{当前卷}`（root 只留 open/active）；开新卷先建分片并把其 id 追加进对应指针表（`unit_shards` / `decision_shards`）。

## 1. manifest_root（YAML）

```yaml
---
id: manifest_root
type: Manifest
rev: 1
status: canon                  # 自身通常 canon；损坏修复时 draft
title: "[工作区资产注册表]"
created_at: "[ISO-8601]"
updated_at: "[ISO-8601]"
depends_on: []
stale_reason: null
tags: []
uri: null
schema_rev: 3                  # 与 asset-types schema_rev 对齐（当前 3）

project:
  name: "[工作区显示名]"
  created_at: "[ISO-8601]"

unit_shards: []                # 卷分片指针表；如 [manifest_units_v1, manifest_units_v2]
decision_shards: []            # Decision 卷分片指针表；如 [manifest_decisions_v1]；迁移规则见 §0

entries:
  - asset_id: manifest_root
    type: Manifest
    rev: 1
    status: canon
    title: "[工作区资产注册表]"
    updated_at: "[ISO-8601]"
    uri: null
    depends_on: []
    tags: []
    phase_home: "*"
  - asset_id: status_project
    type: Status
    rev: 1
    status: canon
    title: "[项目运行时状态]"
    updated_at: "[ISO-8601]"
    uri: null
    depends_on: []
    tags: []
    phase_home: "*"
  # —— 复制此块注册新资产 ——
  - asset_id: "[type_short_slug]"
    type: "[AssetType]"
    rev: 1
    status: draft
    title: "[人读标题]"
    updated_at: "[ISO-8601]"
    uri: null
    depends_on: []             # [{ type, id, min_rev? }]
    tags: []
    phase_home: "[P1|P2|P3|P4|P5|P6|*]"
---
```

## 2. 卷分片：manifest_units_v{n} / manifest_decisions_v{n}（YAML，每卷一片）

```yaml
---
id: manifest_units_v1          # 卷号对齐 Status.web_serial.current_volume；模式 A 单卷 = v1
type: Manifest
rev: 1
status: canon
title: "[vol_01 单元资产分片]"
created_at: "[ISO-8601]"
updated_at: "[ISO-8601]"
depends_on: []
stale_reason: null
tags: [units, vol_01]
uri: null
schema_rev: 3

entries: []                    # 仅 SceneBeat / ChapterPlan / ManuscriptUnit；entry 字段同 §3
---
```

`manifest_decisions_v{n}` 用同一信封（`id: manifest_decisions_v1`、`tags: [decisions, vol_01]`、title 相应改写），`entries` 仅收**非 open** 的 Decision——由卷末 volume_checkpoint 从 root 迁入（web-serial-playbook §9.2）。

## 3. entry 字段（最小完备，10 键）

| 字段 | 类型 | 必填 | 说明 |
|---|---|:-:|---|
| `asset_id` | string | ✓ | = 资产 `id`，全局唯一 |
| `type` | AssetType | ✓ | 见下方合法 type |
| `rev` | integer | ✓ | 与资产信封一致 |
| `status` | AssetStatus | ✓ | `draft\|review\|canon\|locked\|stale\|archived` |
| `title` | string | ✓ | 人读标签 |
| `updated_at` | datetime | ✓ | 上次 touch 时刻 |
| `uri` | string \| null | — | adapter 填写；协议可空 |
| `depends_on` | list | ✓ | `{type, id, min_rev?}`；无依赖写 `[]` |
| `phase_home` | enum | ✓ | `P1..P6 \| *` |
| `tags` | string[] | — | 检索辅助 |

**合法 `type`**：`Status | Canon | Manifest | Decision | Blueprint | PlotSpine | SequenceMap | SceneBeat | ChapterPlan | Character | WorldRule | Thread | ManuscriptUnit | Recap`  
别名写回归一：`ProseUnit`→`ManuscriptUnit`；`ThreadMap`→`Thread`；禁止注册为独立 type。

## 4. 不变量（AT1–AT4，对齐 asset-types §3.3）

- **AT1** writeback 前 `asset_id ∈ 对应分片 entries`（不存在先 register，禁止 silent orphan）
- **AT2** `entries[].rev` 与资产信封 `rev` 一致，否则 `version_skew`
- **AT3** 删除 → 先 `status=archived`，禁止裸删导致悬空 `depends_on`
- **AT4** `Status` / `Manifest`（root 与各分片）自身占 entry（自描述）

## 5. register / touch / archive

- **register**：确认 `asset_id` 唯一 → 按 §0 路由写入 root 或卷分片 → 该 Manifest 实例 `rev += 1`。
- **touch**（writeback 后必做）：同步 `rev` / `status` / `updated_at` → 实例 `rev += 1`；上游变更致下游失效 → 下游标 `stale` 并 touch（conflict-playbook）。
  - **publish 例外**：publish 为 touch 操作——entry.status 晋升 **`locked`**（发布 = locked，唯一默认），目标资产内容零变更、**资产 rev 不递增**，记 `action: publish`。
- **archive**：目标 `status → archived` + touch；扫描引用方 `depends_on`，悬空则标 `stale` 或经 Decision 解除依赖。
- **query**：常用 filter `types / status_in / phase_home / tag / stale_only`；默认召回排除 `archived`；`stale` 只读展示。

**种子条目（new_project 参考）**：`manifest_root`、`status_project`、`blueprint_main`(P1)、`canon_root`、`canon_style`（scaffold 必建第 6 件，status=draft）、`recap_state`、`plotspine_main`(P2)、`seqmap_v1`(P3)、`manifest_units_v1`（进入 P4 前建）。按需再注册 `canon_continuity_v1`、`char_*`、`world_*`、`thread_*`、`decision_*`、`recap_book`。**不要**预注册未创建资产。

## 6. 正文区

frontmatter 为唯一真值；本节以下为自由撰写区，不作机器对账输入。

---

## 修订

| rev | 变更 |
|----:|------|
| 1 | 初版（单文件 entries + edges） |
| 2 | 2026-08-12 重构落地：分片设计（root + manifest_units_v{n} + unit_shards 指针表，BOOT 只读 root）；entry 瘦身删 recall_priority/content_hash；删 edges 缓存节；不变量编号 M1–M4 → AT1–AT4；type 表补 Recap；publish=touch 例外 |
| 3 | 2026-08-13 修复轮：新增 decision_shards 指针表与 manifest_decisions_v{n} 分片（非 open Decision 卷末迁入，root 只留 open/active；BOOT_3 不读，change/diagnose/审计轮按需加载）；publish 例外统一晋升 locked（唯一默认）；种子表 canon_style 移入必建（scaffold 第 6 件）；schema_rev 占位对齐 3 |

*template_for: Manifest | ids: manifest_root \| manifest_units_v{n} \| manifest_decisions_v{n} | schema_rev: 对齐 asset-types（schema_rev 3） | 通用工程层 · 不绑定具体作品*
