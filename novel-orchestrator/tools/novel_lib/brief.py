# -*- coding: utf-8 -*-
"""brief — 简报编译器（十节装配 + 条目级预算裁剪 + 知识矩阵注入 + 溯源表）。"""
import json
import re

from .common import (NOW, TEMPLATES, THREAD_LIVE, ch_num, die, get_section,
                     git_autocommit, parse_frontmatter, read, write)
from .project import Project, find_root
from .stagectl import stage_guard
from .narrative import (effective_knowers, entity_status, historical_log,
                        memory_recall, reader_knows, related_facts,
                        setting_blocks, thread_state_at)
from .dependencies import brief_sources, file_hash


def tail_chars(text, n):
    t = text.strip()
    return t[-n:] if len(t) > n else t


def voice_block(ent_body):
    """P1-3：从实体『设定』节抽声纹小节（口癖/句式/禁词/例句）——声纹升独立块，
    预算裁剪时与实体『设定要点』解耦（设定可裁，声纹不裁）。"""
    sec = get_section(ent_body, "设定") or ""
    lines, on = [], False
    for ln in sec.splitlines():
        if re.match(r"^-\s*声纹", ln.strip()):
            on = True
            continue
        if on:
            if re.match(r"^- \S", ln):
                break
            if ln.strip() and not ln.strip().startswith("["):
                lines.append(ln.rstrip())
    return "\n".join(lines)


BRIEF_SECTIONS = ("0 任务卡", "1 文风与禁忌", "2 直接上文", "3 出场实体状态卡",
                  "4 活跃线索", "5 弧内位置", "6 相关事实与设定", "7 写作提示",
                  "8 回写契约")

# 条目级优先级（P1-2：分越高越后裁；must=True 永不裁 = must-not-drop 集）
PRIO = {"arc_chain": 62, "arc_rows": 58, "ent_setting_lead": 55, "ent_setting": 50,
        "thread_near": 48, "thread_scope": 45, "world_rules": 44, "rollup_arc": 42,
        "recap": 41, "style_imagery": 40, "rollup_vol": 38, "fact_base": 30,
        "style_anchor": 72, "tips": 20, "lessons": 55}


def cmd_brief(args):
    """P1-2 条目级预算装配：每个条目带优先级与 must-not-drop 标记；超预算逐条
    从最低分裁起（非整节丢弃），裁剪逐项留痕溯源表。"""
    proj = Project(find_root(args))
    ch_id = args.ch_id
    stage_guard(proj, ("write",), "brief %s" % ch_id)
    task = proj.chapter_task(ch_id)
    if not task:
        die("缺任务卡 chapters/%s.task.json（先 tree add chapter + 排批补全）" % ch_id, 1)
    for field in ("context_entities", "memory_keywords", "fact_refs", "memory_refs"):
        value = task.get(field, [])
        if not isinstance(value, list) or any(not isinstance(v, str) for v in value):
            die("task.%s 必须为字符串数组" % field, 1)
    budget = proj.config.get("brief_budget_chars", 24000)
    if not isinstance(budget, int) or budget <= 0:
        die("brief_budget_chars 必须为正整数", 1)
    num = ch_num(ch_id)
    route = proj.config.get("route", "web")
    cur_vol = proj.vol_of_chapter(ch_id)
    prov = []   # (资产, rev, 用途)
    items = []  # {sec, key, text, prio, must}

    def add(sec, key, text, prio=50, must=False):
        if text and str(text).strip():
            items.append({"sec": sec, "key": key, "text": str(text).rstrip(),
                          "prio": prio, "must": must})

    # §0 任务卡（must）
    add("0 任务卡", "task.json",
        "```json\n" + json.dumps(task, ensure_ascii=False, indent=1) + "\n```", must=True)

    # §1 文风：基准+禁忌 must；比喻/范文锚可裁
    style_p = proj.p("tree", "style.md")
    style_meta, style_body = parse_frontmatter(read(style_p))
    add("1 文风与禁忌", "叙述基准",
        "### 叙述基准\n" + (get_section(style_body, "叙述基准") or ""), must=True)
    add("1 文风与禁忌", "口癖禁忌",
        "### 口癖与句式禁忌（命中即违规）\n"
        + (get_section(style_body, "口癖与句式禁忌") or ""), must=True)
    add("1 文风与禁忌", "比喻纪律",
        "### 比喻与意象纪律\n" + (get_section(style_body, "比喻与意象纪律") or ""),
        PRIO["style_imagery"])
    add("1 文风与禁忌", "范文锚",
        "### 范文锚\n" + (get_section(style_body, "范文锚") or ""), PRIO["style_anchor"])
    prov.append(("tree/style.md", style_meta.get("rev"), "§1 文风与禁忌"))

    # §2 直接上文：前章尾+summary 链 must；rollup/recap 可裁（P1-1 记忆分层）
    prev_id = "ch_%04d" % (num - 1)
    prev_p = proj.p("chapters", prev_id + ".md")
    has_ctx = False
    if num > 1 and prev_p.is_file():
        _, prev_body = parse_frontmatter(read(prev_p))
        prev_text = prev_body.split("## 正文", 1)[-1]
        add("2 直接上文", "前章尾",
            "### 前章（%s）尾 500 字\n%s" % (prev_id, tail_chars(prev_text, 500)),
            must=True)
        prov.append(("chapters/%s.md" % prev_id, "-", "§2 前章尾"))
        has_ctx = True
    for i in range(max(1, num - 3), num):
        pid = "ch_%04d" % i
        m = proj.chapter_meta_json(pid)
        if m and m.get("summary_after"):
            add("2 直接上文", "summary:%s" % pid,
                "- %s 概要：%s" % (pid, m["summary_after"]), must=True)
            prov.append(("chapters/%s.meta.json" % pid, "-", "§2 summary 链"))
            has_ctx = True
    rollup_p = proj.p("state", "rollup.json")
    if rollup_p.is_file():
        try:
            rollup = json.loads(read(rollup_p))
        except ValueError:
            rollup = {}
        arc_id0 = task.get("arc")
        a = (rollup.get("arcs") or {}).get(arc_id0)
        if a:
            far = [l for l in a["lines"]
                   if int(l[3:7]) < max(1, num - 3)][-10:]
            if far:
                add("2 直接上文", "rollup:arc",
                    "### 本弧前情（rollup 卷积）\n" + "\n".join("- %s" % l for l in far),
                    PRIO["rollup_arc"])
                prov.append(("state/rollup.json", "-", "§2 弧 rollup"))
                has_ctx = True
        vol_lines = []
        for vid in sorted(rollup.get("volumes") or {}):
            for l in rollup["volumes"][vid]:
                span = re.search(r"（(\d{4})[–-](\d{4})）", l)
                if span and int(span.group(2)) < num and not l.startswith(str(arc_id0)):
                    vol_lines.append("%s ｜ %s" % (vid, l))
        if vol_lines:
            add("2 直接上文", "rollup:vol",
                "### 卷级前情（rollup 卷积）\n"
                + "\n".join("- %s" % l for l in vol_lines[-6:]), PRIO["rollup_vol"])
            prov.append(("state/rollup.json", "-", "§2 卷 rollup"))
            has_ctx = True
    recap_p = proj.p("ledgers", "recap.md")
    if recap_p.is_file():
        rl = [l for l in read(recap_p).splitlines()
              if l.strip() and not l.strip().startswith("#")]
        if proj.cursor()["last_drafted"] >= num:
            # Unversioned recap cannot be safely projected backward during revision.
            rl = []
        if rl:
            add("2 直接上文", "recap",
                "### 全局 recap（ledgers/recap.md 尾段）\n" + "\n".join(rl[-12:]),
                PRIO["recap"])
            prov.append(("ledgers/recap.md", "-", "§2 recap"))
            has_ctx = True
    if not has_ctx:
        add("2 直接上文", "empty", "（首章，无上文）", must=True)

    # §3 实体状态卡：声纹速查+现状/最近事件 must；设定要点可裁（P1-3）
    ents = proj.entities()
    voice_lines = []
    cast_list = task.get("cast", [])
    for idx, ref in enumerate(cast_list):
        eid = proj.resolve_entity(ref)
        if not eid or eid not in ents:
            add("3 出场实体状态卡", "缺卡:%s" % ref,
                "- 【缺卡】%s（资料员应报缺料）" % ref, must=True)
            continue
        e = ents[eid]
        status_sec = entity_status(proj, eid, e, num - 1)
        log_tail = "\n".join(historical_log(e["body"], "事件日志", num - 1)[-3:])
        add("3 出场实体状态卡", "ent:%s:卡" % eid,
            "### %s\n现状：\n%s\n\n最近事件：\n%s"
            % (eid, status_sec, log_tail or "（无）"), must=True)
        blocks = setting_blocks(e["body"])
        inner = "\n".join(v for k, v in blocks.items() if k in ("欲望", "需要", "洋葱五层", "关系"))
        add("3 出场实体状态卡", "ent:%s:内在与关系" % eid,
            "### 内在驱动与关系（设计约束，不等于当时已发生的变化）\n" + inner, must=True)
        setting = "\n".join(v for k, v in blocks.items() if k not in ("欲望", "需要", "洋葱五层", "关系", "声纹"))
        add("3 出场实体状态卡", "ent:%s:设定" % eid,
            "未来弧光计划（非历史事实，可裁；来源 entities/%s.md）：\n%s" % (eid, setting),
            PRIO["ent_setting_lead"] if idx == 0 else PRIO["ent_setting"])
        vb = voice_block(e["body"])
        if vb:
            voice_lines.append("**%s**\n%s" % (eid, vb))
        prov.append(("entities/%s.md" % eid, e["meta"].get("rev"), "§3 状态卡"))
    if voice_lines:
        # 声纹速查置于实体卡之前（must——设定可裁而声纹不裁，防千人一腔）
        items.insert(
            next(i for i, it in enumerate(items) if it["sec"] == "3 出场实体状态卡"),
            {"sec": "3 出场实体状态卡", "key": "声纹速查",
             "text": "### 声纹速查（对话守卡依据，rubrics/voice.md）\n\n"
                     + "\n\n".join(voice_lines), "prio": 99, "must": True})
    if not cast_list:
        add("3 出场实体状态卡", "empty", "（任务卡未列 cast）", must=True)

    # §4 活跃线索：listed/must_not_drop 线 must；scope/payoff 临近可裁
    def payoff_near(m):
        pp = m.get("payoff_planned")
        if not pp:
            return False
        if str(pp) == cur_vol:
            return True
        mm = re.match(r"^ch_(\d{4})$", str(pp))
        return bool(mm) and 0 <= int(mm.group(1)) - num <= 15

    threads = proj.threads()
    listed = {t["id"] for t in task.get("threads", [])}
    n_threads = 0
    for tid, th in threads.items():
        m = th["meta"]
        state_at = thread_state_at(th, num - 1)
        live = state_at in THREAD_LIVE
        scope_hit = cur_vol in (m.get("volume_scope") or [])
        near = payoff_near(m)
        pinned = tid in listed or (live and m.get("must_not_drop"))
        relevant = pinned or (live and (scope_hit or near))
        if not relevant:
            continue
        stmt = get_section(th["body"], "陈述") or ""
        log_tail = "\n".join(historical_log(th["body"], "推进日志", num - 1)[-2:])
        tags = ""
        if m.get("must_not_drop"):
            tags += "【must_not_drop】"
        if near:
            tags += "【payoff 临近：%s】" % m.get("payoff_planned")
        add("4 活跃线索", "thread:%s" % tid,
            "- **%s** [%s/%s]%s：%s\n  最近推进：%s"
            % (tid, m.get("thread_kind"), state_at, tags,
               stmt.splitlines()[0] if stmt else "", log_tail or "（无）"),
            PRIO["thread_near"] if near else PRIO["thread_scope"], must=pinned)
        prov.append(("threads/%s.md" % tid, m.get("rev"), "§4 线索"))
        n_threads += 1
    if not n_threads:
        add("4 活跃线索", "empty", "（无活跃线索命中）", must=True)

    # §5 弧内位置
    arc_id = task.get("arc")
    arc_p = proj.node_path(arc_id) if arc_id else None
    if arc_p and arc_p.is_file():
        arc_meta, arc_body = parse_frontmatter(read(arc_p))
        chain = get_section(arc_body, "因果链") or ""
        alloc = get_section(arc_body, "章分配草案") or ""
        rows = [l for l in alloc.splitlines() if re.search(r"ch_\d{4}", l)]
        near_rows = [l for l in rows if any(("ch_%04d" % i) in l
                                            for i in (num - 1, num, num + 1))]
        add("5 弧内位置", "因果链",
            "### 弧因果链（%s）\n%s" % (arc_id, chain), PRIO["arc_chain"])
        add("5 弧内位置", "前后位置",
            "### 本章前后位置\n" + ("\n".join(near_rows) or "（章分配草案未含本章）"),
            PRIO["arc_rows"])
        prov.append((str(arc_p.relative_to(proj.root)), arc_meta.get("rev"),
                     "§5 弧内位置"))
    else:
        add("5 弧内位置", "empty", "（弧计划缺失）", must=True)

    # §6 相关事实与设定：逐 fact 一条（按 时近+键位+retcon 连带 记分），世界规则单列
    cast_ids = {proj.resolve_entity(r) for r in task.get("cast", [])} - {None}
    n_facts = 0
    for fact, f in related_facts(proj, task, num - 1):
        spoiler = "【读者未知，只可潜台词】" if not reader_knows(fact, num - 1) else ""
        known = fact.get("known_by") or []
        if known:
            effective = effective_knowers(proj, fact, num - 1)
            spoiler += "【知情仅:%s】" % ",".join(sorted(effective))
            if "knowledge_events" not in fact:
                spoiler += "【旧账无历史快照，知情时点待核验】"
            unaware = sorted(cast_ids - effective)
            if unaware:
                spoiler += "【本章出场 %s 不知情——不得由其说破或表现知情】" % ",".join(unaware)
        line = "- %s%s（%s，ch%s）" % (spoiler, fact.get("fact"), fact.get("id"), fact.get("revealed_ch"))
        if fact.get("superseded_by") and num >= fact.get("superseded_at", 0):
            data = json.loads(read(f))
            retcon = next((r for r in data.get("retcons", []) if r.get("old_fact_id") == fact["id"]), {})
            label = "本章待执行兼容修正，非既往事实" if num == fact.get("superseded_at") else "已被覆盖"
            line += "\n  ↳【%s】新事实：%s（%s）" % (label, retcon.get("new_fact", "?"), str(retcon.get("strategy", "?")) + ", " + str(retcon.get("decision_ref", "?")))
        add("6 相关事实与设定", "fact:%s" % fact.get("id"), line, 65,
            must=fact.get("id") in task.get("fact_refs", []))
        prov.append((str(f.relative_to(proj.root)), "-", "§6 事实"))
        n_facts += 1
    for required, score, _, ref, memory in memory_recall(proj, task, num - 1):
        add("2 直接上文", "memory:" + ref,
            "### 历史叙事记忆 %s [%s]\n%s\n原文依据：%s" %
            (ref, memory["kind"], memory["text"], memory["evidence"]), 75 + score, must=required)
        prov.append(("chapters/%s.meta.json" % ref.split("#")[0], "-", "§2 叙事记忆"))
    world_p = proj.p("tree", "world.md")
    if world_p.is_file():
        wmeta, wbody = parse_frontmatter(read(world_p))
        add("6 相关事实与设定", "世界规则",
            "### 世界核心规则\n" + (get_section(wbody, "核心规则") or ""),
            PRIO["world_rules"])
        prov.append(("tree/world.md", wmeta.get("rev"), "§6 世界规则"))
    if not n_facts and not world_p.is_file():
        add("6 相关事实与设定", "empty", "（无相关事实）", must=True)

    # §7 写作提示（route 选配）+ lessons
    if route == "traditional":
        tips = [
            "核心纪律速记（traditional 差分，全文见 modes/route-traditional.md）：",
            "- 按细纲逐拍执行（beats 6–10 拍；scene_intents 标场景/过场）",
            "- 每章必有价值翻转（task.json 的 turn 字段；正负极性要兑现）",
            "- 章尾钩为建议级：close 缺席须在 issues 说明 turn 已落实",
            "- 场景、概述和静态描写的比例由本书审美与叙述目的决定",
            "- 禁发明简报外专名；缺料写 issues，不脑补",
        ]
    else:
        tips = [
            "核心纪律速记（全文见 rubrics/prose-disease.md）：",
            "- 检查场景是否改变人物处境或读者理解；数字节奏是建议，不是通用合格线",
            "- 承接上章而不重复上章；有意留白、迟缓与复沓可说明艺术理由",
            "- 关键戏按作品的叙述距离完成；动作句长服从清晰度与节奏",
            "- 禁发明简报外专名；缺料写 issues，不脑补",
        ]
    add("7 写作提示", "tips", "\n".join(tips), PRIO["tips"])
    lessons_p = proj.p("ledgers", "lessons.md")
    lessons = [l for l in read(lessons_p).splitlines() if l.startswith("- ")][-5:] \
        if lessons_p.is_file() else []
    add("7 写作提示", "lessons",
        "近期教训（lessons 台账尾 5 条）：\n" + "\n".join(lessons or ["- （暂无）"]),
        PRIO["lessons"])
    if lessons:
        prov.append(("ledgers/lessons.md", "-", "§7 教训"))

    # §8 回写契约（must）
    add("8 回写契约", "schema",
        "提交格式：最终回复两段——【正文】章文件（信封+## 正文）；【writeback】如下 schema 的"
        "JSON 块（power_delta 可选，战力/位阶变化时必填；continuity_delta 每条可选 key "
        "字段标注实体状态键位，如「位置」「持有」）：\n\n```json\n"
        + read(TEMPLATES / "chapter.meta.json").strip() + "\n```", must=True)

    prev_brief = proj.p("briefs", ch_id + ".brief.md")
    brief_rev = 1
    if prev_brief.is_file():
        m = re.search(r"<!-- brief_rev: (\d+) -->", read(prev_brief))
        brief_rev = (int(m.group(1)) if m else 0) + 1

    trimmed = []  # (sec, key)

    def render(active):
        head = ["<!-- chapter: %s -->" % ch_id, "<!-- brief_rev: %d -->" % brief_rev,
                "<!-- compiled_at: %s -->" % NOW(), "<!-- budget_chars: %d -->" % budget]
        parts = ["\n".join(head)]
        cut_by_sec = {}
        for sec, key in trimmed:
            cut_by_sec.setdefault(sec, []).append(key)
        for sec in BRIEF_SECTIONS:
            chunks = [it["text"] for it in active if it["sec"] == sec]
            if sec in cut_by_sec:
                chunks.append("（本节超预算裁剪 %d 项：%s——原始来源见溯源表）"
                              % (len(cut_by_sec[sec]), "、".join(cut_by_sec[sec])))
            parts.append("## %s\n\n%s" % (sec, "\n\n".join(chunks) or "（空）"))
        prov_lines = ["| 资产 | rev | 用途 |", "|---|---|---|"]
        seen = set()
        for pr in prov:
            if pr not in seen:
                seen.add(pr)
                prov_lines.append("| %s | %s | %s |" % pr)
        if trimmed:
            prov_lines.append("| （裁剪） | - | 条目级裁剪 %d 项：%s |"
                              % (len(trimmed),
                                 "、".join(k for _, k in trimmed)[:300]))
        parts.append("## 附 溯源\n\n" + "\n".join(prov_lines))
        return "\n\n".join(parts) + "\n"

    active = list(items)
    text = render(active)
    while len(text) > budget:
        droppable = [it for it in active if not it["must"]]
        if not droppable:
            die("必需上下文 %d 字符仍超过预算 %d；保留上版简报，须压缩任务/拆场或明确提高预算" % (len(text), budget), 1)
        victim = min(enumerate(droppable),
                     key=lambda x: (x[1]["prio"], -x[0]))[1]
        active.remove(victim)
        trimmed.append((victim["sec"], victim["key"]))
        text = render(active)
    write(prev_brief, text)
    manifest = {"schema_version": 1, "chapter": ch_id, "brief_rev": brief_rev,
                "brief_sha256": file_hash(prev_brief), "sources": brief_sources(proj, ch_id),
                "budget_chars": budget, "actual_chars": len(text),
                "retained": [it["key"] for it in active], "trimmed": trimmed}
    write(proj.p("briefs", ch_id + ".manifest.json"), json.dumps(manifest, ensure_ascii=False, indent=1))
    git_autocommit(proj.root, "[brief] %s rev%d（保证 spawn 前基线干净）" % (ch_id, brief_rev))
    print("简报已生成：briefs/%s.brief.md（%d 字符 / 预算 %d%s）"
          % (ch_id, len(text), budget,
             "，条目级裁剪 %d 项" % len(trimmed) if trimmed else ""))
    return 0
