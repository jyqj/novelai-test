# -*- coding: utf-8 -*-
"""knowledge — 知识矩阵 CLI（P4-K/v2）：fact × 角色 × 读者 + 范围知情圈
（grant/reveal/query/scope）。"""
import json

from .common import ch_num, die, git_autocommit, read, write
from .project import Project, find_root
from .stagectl import stage_guard
from .narrative import effective_knowers, fact_exists, grant_event, reader_knows


def locate_fact(proj, fact_id):
    """按 id 定位 fact：返回 (文件路径, 整文件数据, fact 记录)；找不到返回 (None,)*3。"""
    for f in proj.facts_files():
        try:
            data = json.loads(read(f))
        except ValueError:
            continue
        for x in data.get("facts", []):
            if x.get("id") == fact_id:
                return f, data, x
    return None, None, None


def fmt_knowers(proj, fact, at=None):
    """Display actual event-time knowers, never the group's current membership."""
    known = effective_knowers(proj, fact, at)
    events = fact.get("knowledge_events")
    if events is None:
        return ",".join(sorted(known)) + "（旧记录无历史时间证据）"
    provenance = []
    for event in events:
        if at is not None and event["chapter"] > at:
            continue
        provenance.append("ch_%04d 来源=%s；当时获知=%s" % (
            event["chapter"], ",".join(event.get("via", [])),
            ",".join(event.get("knowers", [])) or "空"))
    return "实际知情：" + ",".join(sorted(known)) + "；" + " | ".join(provenance)



def cmd_scope(proj, args):
    """知识矩阵 v2 范围知情圈：scope add/remove/list——把 char 成员编入
    fac/loc/item 群体的知情圈（entities/scopes.json，novel.py 独占维护）。
    成员表只用于下一次 grant 的快照；不会追溯赋予或撤销历史知识。"""
    if args.scope_cmd == "list":
        scopes = proj.scopes()
        pick = None
        if args.group:
            pick = proj.resolve_entity(args.group)
            if not pick:
                die("群体未登记：%s" % args.group, 1)
            scopes = {pick: scopes.get(pick, [])}
        if not scopes:
            print("（无知情圈；knowledge scope add <fac/loc/item> <char…> 编圈）")
            return 0
        for gid in sorted(scopes):
            print("%-16s %s" % (gid, ",".join(scopes[gid]) or "（空圈）"))
        return 0
    # add / remove 是矩阵改账：限章循环/周期回路阶段
    stage_guard(proj, ("write", "review"), "knowledge scope %s" % args.scope_cmd)
    gid = proj.resolve_entity(args.group)
    if not gid:
        die("群体未登记：%s（先 entity new %s）" % (args.group, args.group), 1)
    if not gid.startswith(Project.GROUP_PREFIXES):
        die("知情圈只挂 fac_/loc_/item_ 群体实体（%s 是个体，直接进 known_by）" % gid, 1)
    members = []
    for ref in args.members:
        mid = proj.resolve_entity(ref)
        if not mid:
            die("成员「%s」未登记（先 entity new 或补 aliases）" % ref, 1)
        if not mid.startswith("char_"):
            die("圈成员须为 char_ 个体（%s）——群体套群体不建模" % mid, 1)
        members.append(mid)
    scopes = proj.scopes()
    cur = set(scopes.get(gid, []))
    if args.scope_cmd == "add":
        cur |= set(members)
    else:  # remove
        miss = sorted(set(members) - cur)
        if miss:
            die("不在 %s 圈内：%s（scope list 查现圈）" % (gid, ",".join(miss)), 1)
        cur -= set(members)
    if cur:
        scopes[gid] = sorted(cur)
    else:
        scopes.pop(gid, None)
    write(proj.p("entities", "scopes.json"),
          json.dumps(scopes, ensure_ascii=False, indent=1))
    git_autocommit(proj.root, "[knowledge] scope %s %s ± %s"
                   % (args.scope_cmd, gid, ",".join(sorted(set(members)))))
    print("知情圈已更新：%s = %s" % (gid, ",".join(sorted(cur)) or "（空圈，已除名）"))
    print("[提醒] 入圈不会自动追溯获得旧秘密；请用带 --ch 的 grant 记录获知。离圈不会遗忘。")
    print("[提醒] 入圈/出圈须有正文/日志支撑（入伙、驻留、易手等场景）——账实一致由评审抽查")
    return 0


def cmd_knowledge(args):
    """P4-K/v2 知识矩阵 CLI（fact × 角色/范围 × 读者）：
    grant  = 授予知情（known_by 追加；个体 char 或 fac/loc/item 范围——范围按知情圈展开）
    reveal = 读者揭示（spoiler 1→0，记 revealed_reader_ch——悬念资产销账）
    scope  = 知情圈维护（把 char 编入 fac/loc/item 群体的知情圈）
    query  = 矩阵视图：--fact 单条全貌 / --entity 个体或群体知与不知 / 默认盘点读者未知欠账"""
    proj = Project(find_root(args))
    if args.knowledge_cmd == "scope":
        return cmd_scope(proj, args)
    # 矩阵改账属工作流环节内操作：grant=章循环/回路对账；reveal 另可在运营销账
    if args.knowledge_cmd == "grant":
        stage_guard(proj, ("write", "review"), "knowledge grant")
        f, data, x = locate_fact(proj, args.fact_id)
        if not x:
            die("fact 不存在：%s（novel.py facts list 查现有 id）" % args.fact_id, 1)
        if x.get("superseded_by"):
            die("fact %s 已被覆盖（%s）——对新事实操作" % (args.fact_id, x["superseded_by"]), 1)
        ids = []
        scopes = proj.scopes()
        for ref in args.to:
            eid = proj.resolve_entity(ref)
            if not eid:
                die("知情人「%s」未登记（先 entity new 或补 aliases）" % ref, 1)
            if eid.startswith(Project.GROUP_PREFIXES) and not scopes.get(eid):
                print("[提醒] %s 是范围授予但知情圈为空——先 knowledge scope add %s "
                      "<char…> 编圈，否则展开后无人知情" % (eid, eid))
            ids.append(eid)
        if not args.ch:
            die("grant 必须提供 --ch，不能把当前知情状态当作全部历史", 1)
        grant_event(proj, x, ids, ch_num(args.ch))
        write(f, json.dumps(data, ensure_ascii=False, indent=1))
        git_autocommit(proj.root, "[knowledge] grant %s → %s%s"
                       % (args.fact_id, ",".join(sorted(set(ids))),
                          "（%s 获知）" % args.ch if args.ch else ""))
        print("已授予知情：%s known_by=%s" % (args.fact_id, fmt_knowers(proj, x)))
        print("[提醒] 获知须有正文/日志支撑（获知场景章号：%s）——账实一致由评审抽查"
              % (args.ch or "未记"))
        return 0
    if args.knowledge_cmd == "reveal":
        stage_guard(proj, ("write", "review", "ops"), "knowledge reveal")
        f, data, x = locate_fact(proj, args.fact_id)
        if not x:
            die("fact 不存在：%s" % args.fact_id, 1)
        if not x.get("spoiler"):
            die("fact %s 本就读者已知（spoiler=0），无需 reveal" % args.fact_id, 1)
        num = ch_num(args.ch)
        if num < int(x.get("revealed_ch") or 0):
            die("读者揭示不能早于事实登记章", 1)
        x["spoiler"] = 0
        x["revealed_reader_ch"] = num
        write(f, json.dumps(data, ensure_ascii=False, indent=1))
        git_autocommit(proj.root, "[knowledge] reveal %s @ %s" % (args.fact_id, args.ch))
        print("读者揭示已记账：%s spoiler=0（revealed_reader_ch=%d）；"
              "此后简报不再带【读者未知】约束" % (args.fact_id, num))
        return 0
    # query
    at = ch_num(args.at) if getattr(args, "at", None) else None
    facts = [x for x, _ in proj.all_facts()
             if (at is None or fact_exists(x, at))
             and (not x.get("superseded_by") or (at is not None and at < x.get("superseded_at", 0)))]
    if args.fact_id:
        f, data, x = locate_fact(proj, args.fact_id)
        if not x:
            die("fact 不存在：%s" % args.fact_id, 1)
        if at is not None and not fact_exists(x, at):
            die("该事实在所查询章节尚未登记", 1)
        view = dict(x)
        if at is not None:
            view["knowledge_events"] = [e for e in x.get("knowledge_events", []) if e["chapter"] <= at]
            view["known_by"] = sorted(effective_knowers(proj, x, at))
            view["spoiler"] = 0 if reader_knows(x, at) else 1
        print(json.dumps(view, ensure_ascii=False, indent=1))
        known = x.get("known_by")
        print("读者：%s" % ("未知（spoiler=1，简报带潜台词约束）" if not reader_knows(x, at if at is not None else 999999)
                            else "已知（ch%s 揭示）" % x.get("revealed_reader_ch",
                                                            x.get("revealed_ch"))))
        print("角色：%s" % ("知情仅 " + fmt_knowers(proj, x, at) if known
                            else "未建模（known_by 空 = 不设知情约束）"))
        return 0
    if args.entity:
        eid = proj.resolve_entity(args.entity)
        if not eid:
            die("实体未登记：%s" % args.entity, 1)
        groups = sorted(g for g, mem in proj.scopes().items() if eid in mem)
        about = [x for x in facts if eid in (x.get("entity_ids") or [])]
        knows = [x for x in facts if eid in effective_knowers(proj, x, at)]
        blind = [x for x in facts if x.get("known_by")
                 and eid not in effective_knowers(proj, x, at)]
        print("== knowledge query %s ==" % eid)
        if eid.startswith(Project.GROUP_PREFIXES):
            print("知情圈成员：%s" % (",".join(proj.scopes().get(eid, [])) or
                                      "（空圈——knowledge scope add 编圈）"))
        elif groups:
            print("所属知情圈：%s" % ",".join(groups))
        print("关于此实体的事实 %d 条：" % len(about))
        for x in about:
            print("  %-10s %s" % (x["id"], x.get("fact")))
        print("知情 %d 条（含经知情圈展开）：" % len(knows))
        for x in knows:
            via = sorted({g for event in x.get("knowledge_events", [])
                          if (at is None or event["chapter"] <= at)
                          and eid in event.get("knowers", [])
                          for g in event.get("via", [])
                          if g.startswith(Project.GROUP_PREFIXES)})
            print("  %-10s %s%s" % (x["id"], x.get("fact"),
                                    "（经 %s 圈）" % ",".join(via) if via else ""))
        print("不知情 %d 条（known_by 有限定且展开后不含该实体——正文不得由其说破）：" % len(blind))
        for x in blind:
            print("  %-10s %s（知情仅 %s）" % (x["id"], x.get("fact"),
                                               fmt_knowers(proj, x, at)))
        return 0
    # 默认：读者未知欠账盘点（悬念资产台账）
    spoilers = sorted([x for x in facts if not reader_knows(x, at if at is not None else 999999)],
                      key=lambda x: x.get("revealed_ch") or 0)
    modeled = [x for x in facts if x.get("known_by")]
    print("== knowledge query（矩阵总览）==")
    print("facts 有效 %d 条；known_by 已建模 %d 条；读者未知（spoiler）%d 条"
          % (len(facts), len(modeled), len(spoilers)))
    for x in spoilers:
        print("  %-10s ch%-4s %s%s" % (x["id"], x.get("revealed_ch"), x.get("fact"),
                                       "（知情仅 %s）" % fmt_knowers(proj, x, at)
                                       if x.get("known_by") else ""))
    if spoilers:
        print("（悬念欠账：埋下未揭示的读者钩子——弧末/卷末逐条决定 继续吊/knowledge "
              "reveal 销账/走 retcon 废止）")
    return 0
