# tools/validate.py — 机械化校验器（python3 标准库，无依赖）

## 1. skill 库检

```bash
python3 tools/validate.py --skill <skill_dir>
# 检：knowledge 锚点唯一性 / blocks 三方对账 / K-ID 引用存在性 / 废弃名残留
#（含 continuity_facts: 字段、narration 枚举值、publish 升 canon 旧语义）/
# 枚举拼写（status 六值、unit_type/content_blocks 五值）/ 六域计数（由 glossary §7.1 动态读取，当前口径 111）
```

## 2. project 项目检

```bash
python3 tools/validate.py --project <project_dir>
# 检：信封五字段 / status·type 枚举 / 洋葱五键 / PlotSpine 24 节点 / Manifest 对账 / id 约定 / sequence_ref 复合键
# + canon 分片 facts: 字段名 / retcon 条目 entity_ids / Decision.approved_by ∈ {user, agent_auto}
# + ManuscriptUnit（summary_after 非空、quote 为正文子串、hooks_realized 双键）/ Recap 覆盖游标 / root Decision 载荷与 critic 时效（WARN）
```

## 3. unit 单章文本质量机检

```bash
python3 tools/validate.py --unit projects/<p>/manuscript/ms_0012.md --style projects/<p>/canon/canon_style.md
# 检：canon_style.taboo_list 逐条命中（列出命中行，违规 = FAIL）
# 连续 3 句同首词 / 字级 4-gram 重复率 >2% / 去空白字数超出 2000–4500±15% / 末段总结化句式黑名单（均 WARN）
# 省略 --style 时 taboo 检查记 SKIP，其余照常
```

可加 `--quiet` 只输出 FAIL/WARN 与 summary。

退出码：`0` = 无 FAIL（**仅 WARN 也为 0**）；`1` = 存在任一 FAIL（明细带 文件:行号）。项目模式对缺失目录/文件容错（SKIP 并注明，不 FAIL）。

对应关系：`runtime/writeback-acceptance.md` §1 表中标 **[脚本]** 的项由本工具 `--project` 机器判定（quote 子串校验对应 W7）；环境不可运行时按该文件手工清单。

局限：frontmatter/YAML 为宽松正则行解析（非完整 YAML parser），只保证字段存在性与字面一致性，不校验嵌套结构合法性；废弃名扫描按行内「废弃/别名/映射」语境豁免，存在少量漏报可能；taboo_list 条目自动提取字面变体（括注交替展开、「——」后说明剥离、「xx：」标签式条目不机检），句式级口癖仍需 critic 轮人工/LLM 抽查；句式单一性只实现「连续 3 句同首词」启发式——「同构」（句法骨架级）判定误报率高、经裁决降级不做机检，归 critic 轮按 K-WRITE-018 判据人工/LLM 抽查。

---

## 修订

| rev | 变更 |
|----:|------|
| 1 | 初版：--skill / --project 两模式 |
| 2 | 2026-08-13 修复轮：新增 --unit 文本质量机检与 WARN 级；--skill 废弃名扫描补 continuity_facts:/narration/publish 旧语义，枚举补 unit_type 五值闭集；--project 新增 facts 字段名 / retcon entity_ids / approved_by / root Decision 载荷 / summary_after / quote 子串 / hooks 双键 / Recap 覆盖 / critic 时效九项；第三波收尾：Decision open 判定对齐 asset-types §2.3（locked+long_term 标注免计迁移 WARN），同构启发式降级说明 |
