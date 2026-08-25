# -*- coding: utf-8 -*-
"""status — status 命令：重算 state/index.json 与 state/dashboard.md（可恢复断点）。"""
import json

from .common import (CH_STATUS, NOW, Report, ch_num, git_out, parse_frontmatter,
                     read, write)
from .checks import check_window
from .project import Project, find_root, load_queue_promoted, next_task_id


def cmd_status(args):
    proj = Project(find_root(args))
    # 章级增量：mtime 未变的章直接复用旧 index 条目（formats §14）
    idx_p = proj.p("state", "index.json")
    old_ch = {}
    if idx_p.is_file():
        try:
            for c in json.loads(read(idx_p)).get("chapters", []):
                if "mtime" in c:
                    old_ch[c["id"]] = c
        except ValueError:
            pass
    ch_entries = []
    for f in proj.chapter_files():
        mt = round(f.stat().st_mtime, 3)
        oc = old_ch.get(f.stem)
        if oc and oc.get("mtime") == mt:
            ch_entries.append(oc)
            continue
        meta, _ = parse_frontmatter(read(f))
        meta = meta or {}
        ch_entries.append({"id": f.stem, "status": meta.get("status"),
                           "rev": meta.get("rev"), "parent": meta.get("parent"),
                           "mtime": mt})
    cur = {"last_published": 0, "last_drafted": 0, "last_approved": 0}
    by_status = {}
    for c in ch_entries:
        n = ch_num(c["id"])
        st = c.get("status")
        by_status.setdefault(st or "?", []).append(c["id"])
        if st == "published":
            cur["last_published"] = max(cur["last_published"], n)
        if st in ("drafted", "approved", "published"):
            cur["last_drafted"] = max(cur["last_drafted"], n)
        if st in ("approved", "published"):
            cur["last_approved"] = max(cur["last_approved"], n)
    ready = sum(1 for c in ch_entries if c.get("status") == "approved"
                and ch_num(c["id"]) > cur["last_published"])

    q = load_queue_promoted(proj)
    pend = [t for t in q["tasks"] if t["state"] in ("pending", "running", "blocked")]
    nodes = proj.tree_nodes()
    ents = proj.entities()
    threads = proj.threads()

    # 告警快照（check --window 摘要，进 index.warnings 与 dashboard）
    wrep = Report()
    check_window(proj, wrep)
    warnings = ["[%s] %s" % (l, n) for l, n, _, _ in wrep.items
                if l in ("WARN", "FAIL")]

    last_deep = proj.last_deep_review_ch()
    deep_every = proj.config.get("critic", {}).get("deep_every", 5)
    deep_overdue = (cur["last_drafted"] - last_deep) >= deep_every and cur["last_drafted"] > 0

    idx = {
        "generated_at": NOW(),
        "nodes": [{"id": n["meta"].get("id"), "kind": n["meta"].get("kind"),
                   "status": n["meta"].get("status"), "rev": n["meta"].get("rev"),
                   "parent": n["meta"].get("parent"),
                   "path": str(n["path"].relative_to(proj.root))}
                  for n in nodes],
        "chapters": ch_entries,
        "entities": [{"id": eid, "entity_type": e["meta"].get("entity_type"),
                      "rev": e["meta"].get("rev"),
                      "last_event_ch": e["meta"].get("last_event_ch"),
                      "last_reconcile_ch": e["meta"].get("last_reconcile_ch")}
                     for eid, e in ents.items()],
        "threads": [{"id": tid, "thread_kind": t["meta"].get("thread_kind"),
                     "state": t["meta"].get("state"),
                     "must_not_drop": t["meta"].get("must_not_drop"),
                     "plant_ch": t["meta"].get("plant_ch"),
                     "payoff_planned": t["meta"].get("payoff_planned")}
                    for tid, t in threads.items()],
        "tasks": {"pending": len([t for t in q["tasks"] if t["state"] == "pending"]),
                  "blocked": len([t for t in q["tasks"] if t["state"] == "blocked"]),
                  "head": pend[:5]},
        "cursor": cur, "buffer_ready": ready,
        "last_deep_review_ch": last_deep,
        "warnings": warnings,
    }
    write(idx_p, json.dumps(idx, ensure_ascii=False, indent=1))

    lines = ["# dashboard（生成物，禁手改）", "",
             "- 项目：%s ｜ 生成于 %s" % (proj.config.get("name", proj.root.name), NOW()),
             "- 游标：last_published=%(last_published)d  last_approved=%(last_approved)d"
             "  last_drafted=%(last_drafted)d" % cur,
             "- buffer(ready)=%d（target=%s）" % (ready, proj.config.get("buffer", {}).get("target")),
             "- 深评游标：last_deep_review_ch=%d（deep_every=%d）%s"
             % (last_deep, deep_every,
                "【逾期，先排 review_deep】" if deep_overdue else "")]
    lines += ["", "## 树进度表"]
    vols = sorted({n["meta"].get("id") for n in nodes
                   if n["meta"].get("kind") == "volume"} - {None})
    if vols:
        lines.append("| 卷 | 状态 | 弧 | 章数 |")
        lines.append("|---|---|---|---|")
        for vid in vols:
            vnode = next(n for n in nodes if n["meta"].get("id") == vid)
            arcs = [n["meta"] for n in nodes if n["meta"].get("kind") == "arc"
                    and n["meta"].get("parent") == vid]
            arc_ids = {a.get("id") for a in arcs}
            n_ch = sum(1 for c in ch_entries if c.get("parent") in arc_ids)
            lines.append("| %s | %s | %s | %d |"
                         % (vid, vnode["meta"].get("status"),
                            " ".join("%s[%s]" % (a.get("id"), a.get("status"))
                                     for a in arcs) or "（无）", n_ch))
    else:
        lines.append("- （尚无卷节点）")
    lines += ["", "## 树节点"]
    for n in nodes:
        lines.append("- %s [%s] rev=%s" % (n["meta"].get("id"), n["meta"].get("status"),
                                           n["meta"].get("rev")))
    lines.append("")
    lines.append("## 章（按状态）")
    for st in CH_STATUS:
        if st in by_status:
            ids = by_status[st]
            lines.append("- %s ×%d：%s%s" % (st, len(ids), " ".join(ids[:8]),
                                             " …" if len(ids) > 8 else ""))
    lines.append("")
    lines.append("## 队列头（≤5）")
    if not pend:
        lines.append("- （空）")
    for t in pend[:5]:
        lines.append("- %s %s(%s) [%s] %s" % (t["id"], t["type"], t["target"],
                                              t["state"], t.get("note", "")))
    lines.append("")
    lines.append("## 告警（check --window 摘要）")
    if warnings:
        lines += ["- %s" % w for w in warnings]
    else:
        lines.append("- （无）")
    lines.append("")
    lines.append("## 最近 git 提交")
    log3 = git_out(proj.root, "log", "--oneline", "-3")
    lines += ["- %s" % l for l in log3.splitlines()] if log3 else ["- （无 git 历史）"]
    write(proj.p("state", "dashboard.md"), "\n".join(lines) + "\n")
    print("\n".join(lines))
    print("\n可恢复断点：task next → %s" % (next_task_id(q) or "（队列空）"))
    return 0
