# -*- coding: utf-8 -*-
"""extract — 抽取器（P2-1 双记账机器半边）：正文反向解析 + writeback 对账 +
剧透泄漏候选 + 角色知识越界候选（P4-K）。"""
import json
import re

from .common import Report, ch_num, die, ngram_sim, parse_frontmatter, read, sentences_of
from .project import Project, find_root


def extract_observations(proj, text):
    """从正文反向解析可机读观察：已登记专名的出场计数 + 引号内新专名候选。
    这是「写手自报（writeback）↔ 文本实测」双记账的机器半边；语义类观察
    （爽点是否真兑现、线索是否真推进）仍归评审。"""
    names = {}
    for alias, eid in proj.aliases().items():
        names[str(alias)] = eid
    alias_bearing = set()
    for eid, e in proj.entities().items():
        for a in e["meta"].get("aliases") or []:
            names[str(a)] = eid
    for name, eid in names.items():
        if len(name) >= 2:
            alias_bearing.add(eid)
    mentions = {}
    for name, eid in names.items():
        if len(name) < 2 or name.startswith("["):
            continue
        cnt = text.count(name)
        if cnt:
            mentions[eid] = mentions.get(eid, 0) + cnt
    quoted = re.findall(r"[「『]([\u4e00-\u9fff]{2,6})[」』]", text)
    freq = {}
    for q in quoted:
        freq[q] = freq.get(q, 0) + 1
    candidates = sorted(q for q, c in freq.items() if c >= 2 and q not in names)
    return {"mentions": mentions, "name_candidates": candidates,
            "alias_bearing": alias_bearing}


def extract_reconcile(proj, ch_id, text, wb, rep):
    """对账：文本实测出场 vs writeback.cast_actual；剧透事实文本相似泄漏候选。"""
    obs = extract_observations(proj, text)
    cast = {proj.resolve_entity(r) for r in (wb or {}).get("cast_actual", []) or []} \
        - {None}
    undeclared = sorted("%s（正文命中 %d 次）" % (eid, n)
                        for eid, n in obs["mentions"].items() if eid not in cast)
    phantom = sorted(eid for eid in cast
                     if eid in obs["alias_bearing"] and eid not in obs["mentions"])
    if undeclared:
        rep.add("WARN", "抽取器：正文出现已登记实体但 cast_actual 未申报"
                        "（实体日志/对账将漏记；补申报或删越权出场）", undeclared)
    if phantom:
        rep.add("WARN", "抽取器：cast_actual 申报了正文未出现的实体（幽灵出场；"
                        "仅对有已登记别名的实体可判）", phantom)
    if not undeclared and not phantom:
        rep.add("PASS", "抽取器：出场申报与文本实测一致（命中 %d 实体）"
                % len(obs["mentions"]))
    if obs["name_candidates"]:
        rep.add("NEEDS_REVIEW", "抽取器：引号内新专名候选（≥2 次且未登记——"
                                "简报外发明嫌疑，轻评对照简报裁定后 entity new/补别名）",
                obs["name_candidates"][:10])
    # P2-3 剧透泄漏候选：未覆盖 spoiler 事实与正文句子高相似 → 评审裁定
    num = ch_num(ch_id)
    sents = None
    spoilers = [x for x, _ in proj.all_facts()
                if x.get("spoiler") and not x.get("superseded_by")]
    if spoilers:
        leaks = []
        sents = sentences_of(text)
        for x in spoilers:
            if x.get("revealed_ch") == num:
                continue
            for s in sents:
                if ngram_sim(x.get("fact", ""), s) >= 0.5:
                    leaks.append("%s「%s」≈「%s…」" % (x.get("id"), x.get("fact"),
                                                       s[:20]))
                    break
        if leaks:
            rep.add("NEEDS_REVIEW", "抽取器：剧透事实文本相似泄漏候选"
                                    "（读者未知事实疑被明写；评审裁定改潜台词或走揭示）",
                    leaks[:8])
    # P4-K 知识矩阵角色半边：known_by 有限定的事实在正文被明写，而在场角色不在
    # 知情名单 → 角色知识越界候选（谁说破的？他不该知道）——评审裁定：
    # 改写为该角色不知情的演法 / 正文补获知场景并 knowledge grant / 删句。
    guarded = [x for x, _ in proj.all_facts()
               if x.get("known_by") and not x.get("superseded_by")
               and x.get("revealed_ch") != num]
    if guarded and cast:
        if sents is None:
            sents = sentences_of(text)
        overreach = []
        for x in guarded:
            unaware = sorted(cast - set(x["known_by"]))
            if not unaware:
                continue
            for s in sents:
                if ngram_sim(x.get("fact", ""), s) >= 0.5:
                    overreach.append("%s「%s」——在场未知情角色：%s（知情仅 %s）"
                                     % (x.get("id"), x.get("fact"),
                                        ",".join(unaware), ",".join(x["known_by"])))
                    break
        if overreach:
            rep.add("NEEDS_REVIEW", "抽取器：角色知识越界候选（事实被明写而在场角色"
                                    "不在 known_by 名单——评审裁定：改暗写/补获知场景后"
                                    " knowledge grant/删句）", overreach[:8])
    return obs


def cmd_extract(args):
    """抽取器独立入口：正文反向解析 + 与 writeback 对账（双记账机器半边）。"""
    proj = Project(find_root(args))
    ch_id = args.ch_id
    ch_num(ch_id)
    if args.candidate:
        _, body = parse_frontmatter(read(args.candidate))
    else:
        p = proj.p("chapters", ch_id + ".md")
        if not p.is_file():
            die("章不存在且未给 --candidate：%s" % ch_id, 1)
        _, body = parse_frontmatter(read(p))
    text = body.split("## 正文", 1)[-1] if "## 正文" in body else body
    wb = json.loads(read(args.writeback)) if args.writeback \
        else proj.chapter_meta_json(ch_id)
    rep = Report()
    obs = extract_reconcile(proj, ch_id, text, wb or {}, rep)
    print("== 抽取器观察（%s）==" % ch_id)
    for eid, n in sorted(obs["mentions"].items()):
        print("- 出场实测：%s ×%d" % (eid, n))
    for q in obs["name_candidates"]:
        print("- 新专名候选：「%s」" % q)
    if not obs["mentions"] and not obs["name_candidates"]:
        print("- （无已登记别名命中，无新专名候选）")
    return rep.render("extract %s（对账）" % ch_id)
