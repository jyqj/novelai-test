# -*- coding: utf-8 -*-
"""rollup — 章→弧→卷摘要卷积（P1-1/P4-R）：brief §2 远程记忆层的数据源。"""
import json
import re

from .common import NOW, git_autocommit, vol_of_arc, write
from .project import Project, find_root


def first_sentence(text, limit=60):
    s = re.split(r"[。！？!?\n]", (text or "").strip())[0].strip()
    return s[:limit] + ("…" if len(s) > limit else "")


def update_rollup(proj):
    """P1-1 自动摘要卷积（章→弧→卷），commit 后全量重算 state/rollup.json。
    弧级 = 各章 summary_after 首句；卷级 = 各弧首末摘要压缩。brief §2 注入为
    远程记忆层——距离越远颗粒越粗，百万字仍可在预算内召回前情。"""
    chs = {}
    for c in proj.chapters():
        if c["meta"].get("status") not in ("drafted", "approved", "published"):
            continue
        mj = proj.chapter_meta_json(c["id"]) or {}
        s = (mj.get("summary_after") or "").strip()
        if not s:
            continue
        arc = (proj.chapter_task(c["id"]) or {}).get("arc") \
            or c["meta"].get("parent") or "arc_?"
        chs[c["id"]] = {"arc": arc, "vol": vol_of_arc(arc) or "vol_01", "summary": s, "memories": mj.get("narrative_memory", [])}
    arcs = {}
    for cid in sorted(chs):
        e = chs[cid]
        arcs.setdefault(e["arc"], {"vol": e["vol"], "chapters": []})["chapters"].append(cid)
    rollup = {"schema_version": 2, "generated_at": NOW(), "arcs": {}, "volumes": {}, "episodes": chs}
    for aid in sorted(arcs):
        a = arcs[aid]
        ids = a["chapters"]
        rollup["arcs"][aid] = {
            "vol": a["vol"], "span": [ids[0], ids[-1]],
            "lines": ["%s：%s" % (cid, chs[cid]["summary"])
                      for cid in ids]}
    for aid in sorted(rollup["arcs"]):
        a = rollup["arcs"][aid]
        head = first_sentence(chs[a["span"][0]]["summary"], 40)
        tail = first_sentence(chs[a["span"][1]]["summary"], 40)
        line = "%s（%s–%s）：%s" % (aid, a["span"][0][3:], a["span"][1][3:],
                                    head if a["span"][0] == a["span"][1]
                                    else head + " ⋯ " + tail)
        rollup["volumes"].setdefault(a["vol"], []).append(line)
    write(proj.p("state", "rollup.json"), json.dumps(rollup, ensure_ascii=False, indent=1))
    return rollup


def cmd_rollup(args):
    """手动重算章→弧→卷摘要卷积。commit/adopt/facts import 已自动重算；本命令用于
    批量手改 meta.json（如 adopt 补录 summary_after、修订摘要链）后的显式对账。"""
    proj = Project(find_root(args))
    rollup = update_rollup(proj)
    n_ch = sum(len(a["lines"]) for a in rollup["arcs"].values())
    git_autocommit(proj.root, "[rollup] 手动重算（%d 章 → %d 弧 → %d 卷）"
                   % (n_ch, len(rollup["arcs"]), len(rollup["volumes"])))
    print("rollup 已重算：%d 章 → %d 弧 → %d 卷 → state/rollup.json"
          % (n_ch, len(rollup["arcs"]), len(rollup["volumes"])))
    for aid in sorted(rollup["arcs"]):
        a = rollup["arcs"][aid]
        print("  %s（%s..%s）%d 行" % (aid, a["span"][0], a["span"][1], len(a["lines"])))
    print("（简报 §2 远程记忆层引用此文件；重编简报后新卷积才进包）")
    return 0
