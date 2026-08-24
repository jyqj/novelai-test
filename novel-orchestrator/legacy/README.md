# legacy/ — v1（novel-writing-workflow）只读存档

**本目录不是入口，任何运行期流程不得从这里加载文件。** 唯一入口 = `../SKILL.md`。

## 这里有什么

v1 skill 的原文存档（入口文件已改名以防误加载）：

- `SKILL-v1.md` / `README-v1.md` — v1 入口与总览（原 `SKILL.md`/`README.md`）
- `runtime/` — v1 契约链（asset-types / phase-contracts / writeback-acceptance / conflict-playbook / web-serial-playbook / project-scaffold / glossary 等）
- `phases/` — v1 六阶段（P1 蓝图 … P6 正文）操作文件
- `templates/` — v1 资产模板（Blueprint/PlotSpine/SceneBeat/Status 等）
- `tools/` — v1 校验器原文（已收编为 `../tools/validate.py`）
- `knowledge-index.md` — v1 原版索引（v2 适配版在 `../knowledge-index.md`）

注意：v1 的 `knowledge/` 与 `knowledge-blocks.md` **不在本目录**——它们未被废弃，
已上收到 orchestrator 根（`../knowledge/`、`../knowledge-blocks.md`）继续服役。

## 什么时候读 legacy

只有三种正当理由：

1. **迁移旧项目**：手上有按 v1 格式（Status/Manifest/Canon 六资产）建的书项目，需要对照
   `../protocol/glossary.md` §2 的 v1→v2 映射逐类搬迁；
2. **考古取证**：v2 某条判据/协议存疑，回溯其在 v1 的原始表述与理由；
3. **补写映射**：发现 glossary 映射表缺项，需要引用 v1 原文补登记。

除此之外出现「读 legacy 才能干活」的情况 = v2 文档有洞，应修 v2 文档（并走
`protocol/court.md` §4 否决案台账流程），而不是把 legacy 当活协议用。

## 纪律

- 只读。不修改、不新增、不删除本目录任何文件。
- 新文档禁止引用 legacy 路径作为规范依据（引用作历史出处除外）。
- v1 术语（P1–P6、Canon、Manifest、ManuscriptUnit…）不得出现在 v2 新写的文档中，
  归一表见 `../protocol/glossary.md`。
