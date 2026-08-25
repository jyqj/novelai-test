# -*- coding: utf-8 -*-
"""knowledge — 知识矩阵 CLI（P4-K）：fact × 角色 × 读者（grant/reveal/query）。"""
import json

from .common import ch_num, die, git_autocommit, read, write
from .project import Project, find_root
from .stagectl import stage_guard


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


def cmd_knowledge(args):
    """P4-K 知识矩阵 CLI（fact × 角色 × 读者）：
    grant  = 授予角色知情（known_by 追加；获知场景写进正文/日志，本命令只记账）
    reveal = 读者揭示（spoiler 1→0，记 revealed_reader_ch——悬念资产销账）
    query  = 矩阵视图：--fact 单条全貌 / --entity 某角色知与不知 / 默认盘点读者未知欠账"""
    proj = Project(find_root(args))
    # 矩阵改账属工作流环节内操作：grant=章循环/回路对账；reveal 另可在运营销账
    if args.knowledge_cmd == "grant":
        stage_guard(proj, ("write", "review"), "knowledge grant")
        f, data, x = locate_fact(proj, args.fact_id)
        if not x:
            die("fact 不存在：%s（novel.py facts list 查现有 id）" % args.fact_id, 1)
        if x.get("superseded_by"):
            die("fact %s 已被覆盖（%s）——对新事实操作" % (args.fact_id, x["superseded_by"]), 1)
        ids = []
        for ref in args.to:
            eid = proj.resolve_entity(ref)
            if not eid:
                die("知情人「%s」未登记（先 entity new 或补 aliases）" % ref, 1)
            ids.append(eid)
        x["known_by"] = sorted(set(x.get("known_by") or []) | set(ids))
        write(f, json.dumps(data, ensure_ascii=False, indent=1))
        git_autocommit(proj.root, "[knowledge] grant %s → %s%s"
                       % (args.fact_id, ",".join(sorted(set(ids))),
                          "（%s 获知）" % args.ch if args.ch else ""))
        print("已授予知情：%s known_by=%s" % (args.fact_id, ",".join(x["known_by"])))
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
        x["spoiler"] = 0
        x["revealed_reader_ch"] = num
        write(f, json.dumps(data, ensure_ascii=False, indent=1))
        git_autocommit(proj.root, "[knowledge] reveal %s @ %s" % (args.fact_id, args.ch))
        print("读者揭示已记账：%s spoiler=0（revealed_reader_ch=%d）；"
              "此后简报不再带【读者未知】约束" % (args.fact_id, num))
        return 0
    # query
    facts = [x for x, _ in proj.all_facts() if not x.get("superseded_by")]
    if args.fact_id:
        f, data, x = locate_fact(proj, args.fact_id)
        if not x:
            die("fact 不存在：%s" % args.fact_id, 1)
        print(json.dumps(x, ensure_ascii=False, indent=1))
        known = x.get("known_by")
        print("读者：%s" % ("未知（spoiler=1，简报带潜台词约束）" if x.get("spoiler")
                            else "已知（ch%s 揭示）" % x.get("revealed_reader_ch",
                                                            x.get("revealed_ch"))))
        print("角色：%s" % ("知情仅 " + ",".join(known) if known
                            else "未建模（known_by 空 = 不设知情约束）"))
        return 0
    if args.entity:
        eid = proj.resolve_entity(args.entity)
        if not eid:
            die("实体未登记：%s" % args.entity, 1)
        about = [x for x in facts if eid in (x.get("entity_ids") or [])]
        knows = [x for x in facts if eid in (x.get("known_by") or [])]
        blind = [x for x in facts if x.get("known_by") and eid not in x["known_by"]]
        print("== knowledge query %s ==" % eid)
        print("关于此实体的事实 %d 条：" % len(about))
        for x in about:
            print("  %-10s %s" % (x["id"], x.get("fact")))
        print("知情 %d 条：" % len(knows))
        for x in knows:
            print("  %-10s %s" % (x["id"], x.get("fact")))
        print("不知情 %d 条（known_by 有限定且不含该实体——正文不得由其说破）：" % len(blind))
        for x in blind:
            print("  %-10s %s（知情仅 %s）" % (x["id"], x.get("fact"),
                                               ",".join(x["known_by"])))
        return 0
    # 默认：读者未知欠账盘点（悬念资产台账）
    spoilers = sorted([x for x in facts if x.get("spoiler")],
                      key=lambda x: x.get("revealed_ch") or 0)
    modeled = [x for x in facts if x.get("known_by")]
    print("== knowledge query（矩阵总览）==")
    print("facts 有效 %d 条；known_by 已建模 %d 条；读者未知（spoiler）%d 条"
          % (len(facts), len(modeled), len(spoilers)))
    for x in spoilers:
        print("  %-10s ch%-4s %s%s" % (x["id"], x.get("revealed_ch"), x.get("fact"),
                                       "（知情仅 %s）" % ",".join(x["known_by"])
                                       if x.get("known_by") else ""))
    if spoilers:
        print("（悬念欠账：埋下未揭示的读者钩子——弧末/卷末逐条决定 继续吊/knowledge "
              "reveal 销账/走 retcon 废止）")
    return 0
