# -*- coding: utf-8 -*-
"""structure — 树节点（tree add/show/set-status）与任务队列 CLI（task …）。"""
import json
import re

from .common import (NOW, TASK_TYPES, die, dump_frontmatter, instantiate,
                     parse_frontmatter, read, write)
from .project import (Project, find_root, load_queue_promoted, next_task_id,
                      promote_blocked)


def approval_receipt(proj, ch_id):
    """P0-2（收紧）：drafted→approved 仅认 reviews/ 落盘回执——verdict=pass 且
    rev_reviewed == 章当前 rev。任务 note 自证通道（light=pass 正则）已删除：
    评审结论必须落盘（novel.py review add），闸门不接受口头/note 自我盖章。"""
    p = proj.p("chapters", ch_id + ".md")
    cur_rev = 1
    if p.is_file():
        meta, _ = parse_frontmatter(read(p))
        cur_rev = (meta or {}).get("rev") or 1
    stale = []
    for depth in ("light", "deep"):
        f = proj.p("reviews", "%s.%s.md" % (ch_id, depth))
        if not f.is_file():
            continue
        meta, _ = parse_frontmatter(read(f))
        meta = meta or {}
        if meta.get("verdict") != "pass":
            continue
        if meta.get("rev_reviewed") != cur_rev:
            stale.append("reviews/%s.%s.md rev_reviewed=%s ≠ 章 rev=%s"
                         % (ch_id, depth, meta.get("rev_reviewed"), cur_rev))
            continue
        return "reviews/%s.%s.md verdict=pass rev_reviewed=%s" % (ch_id, depth, cur_rev)
    for s in stale:
        print("[warn] 回执过期：%s（章已 revise，须对当前 rev 复评）" % s)
    return None


def cmd_tree(args):
    proj = Project(find_root(args))
    if args.tree_cmd == "show":
        for n in proj.tree_nodes():
            m = n["meta"]
            print("%-12s %-8s status=%-10s rev=%s" % (m.get("id"), m.get("kind"),
                                                      m.get("status"), m.get("rev")))
        for c in proj.chapters():
            m = c["meta"]
            print("%-12s chapter  status=%-10s rev=%s parent=%s"
                  % (c["id"], m.get("status"), m.get("rev"), m.get("parent")))
        return 0

    if args.tree_cmd == "set-status":
        path = proj.node_path(args.id)
        if not path or not path.is_file():
            die("节点不存在：%s" % args.id)
        meta, body = parse_frontmatter(read(path))
        kind = meta.get("kind")
        old = meta.get("status")
        new = args.status
        legal = {
            "node": {("empty", "draft"), ("draft", "committed"), ("committed", "stale"),
                     ("stale", "committed"), ("stale", "draft"),
                     ("draft", "archived"), ("committed", "archived")},
            "chapter": {("planned", "drafted"), ("drafted", "approved"),
                        ("approved", "published"), ("approved", "drafted"),
                        ("planned", "stale"), ("drafted", "stale"), ("approved", "stale"),
                        ("stale", "planned"), ("stale", "drafted"),
                        ("planned", "archived"), ("drafted", "archived")},
        }
        table = legal["chapter"] if kind == "chapter" else legal["node"]
        if (old, new) not in table:
            die("非法迁移：%s %s→%s（合法表见 protocol/formats.md §3）" % (args.id, old, new), 1)
        if kind == "chapter" and new == "approved":
            receipt = approval_receipt(proj, args.id)
            if not receipt:
                die("approved 需落盘评审回执：reviews/%s.light|deep.md（verdict=pass 且 "
                    "rev_reviewed=章当前 rev）。轻评结论用 novel.py review add 落盘；"
                    "任务 note 与 --evidence 不再是回执通道（P0-2 收紧，pipeline §1 步骤 8）"
                    % args.id, 1)
            meta["approved_evidence"] = receipt + (
                "；" + args.evidence if getattr(args, "evidence", None) else "")
        meta["status"] = new
        meta["updated_at"] = NOW()
        write(path, dump_frontmatter(meta) + "\n" + body.lstrip("\n"))
        print("%s: %s → %s" % (args.id, old, new))
        return 0

    # tree add
    kind, nid, parent = args.kind, args.id, args.parent
    rep = {"[YYYY-MM-DDTHH:MM:SSZ]": NOW()}
    if kind == "volume":
        if not re.match(r"^vol_\d{2}$", nid):
            die("volume id 应为 vol_NN")
        rep["[vol_01]"] = nid
        write(proj.p("tree", nid, "volume.md"), instantiate("volume.md", rep))
    elif kind == "arc":
        m = re.match(r"^arc_(\d{2})_(\d+)$", nid)
        if not m:
            die("arc id 应为 arc_NN_n")
        vol = parent or ("vol_" + m.group(1))
        rep.update({"[arc_01_1]": nid, "[vol_01]": vol})
        write(proj.p("tree", vol, nid + ".md"), instantiate("arc.md", rep))
    elif kind == "chapter":
        if not re.match(r"^ch_\d{4}$", nid):
            die("chapter id 应为 ch_NNNN")
        if not parent:
            die("chapter 需 --parent arc_NN_n")
        rep.update({"[ch_0001]": nid, "[arc_01_1]": parent})
        write(proj.p("chapters", nid + ".md"), instantiate("chapter.md", rep))
        write(proj.p("chapters", nid + ".task.json"), instantiate("chapter.task.json", rep))
    else:
        die("tree add 仅支持 volume|arc|chapter；实体用 entity new，线索用 thread new")
    print("已实例化 %s（%s）" % (nid, kind))
    return 0


def cmd_task(args):
    proj = Project(find_root(args))
    q = load_queue_promoted(proj)
    sub = args.task_cmd

    if sub == "add":
        if args.type not in TASK_TYPES:
            die("type 须为 %s" % "|".join(TASK_TYPES))
        if args.type == "revise_design" and not args.evidence:
            die("revise_design 必须带 --evidence（并先过 court/ 否决案台账，见 court.md §4）", 1)
        if args.type == "revise_rubric":
            if not args.evidence:
                die("revise_rubric 必须带 --evidence（lessons/review 条目引用——"
                    "蒸馏要有出处，workflow.md §6）", 1)
            if args.target != "style":
                die("revise_rubric 目标仅支持 style（tree/style.md 禁忌黑名单是机检"
                    "唯一登记处；skill 侧 rubrics/ 不随项目改）", 1)
        tid = "t_%06d" % q["next_seq"]
        q["next_seq"] += 1
        q["tasks"].append({"id": tid, "type": args.type, "target": args.target,
                           "state": "blocked" if args.blocked_on else "pending",
                           "blocked_on": args.blocked_on or [], "attempts": 0,
                           "note": args.note or "", "evidence": args.evidence or "",
                           "created_at": NOW(), "updated_at": NOW()})
        proj.save_queue(q)
        print(tid)
        return 0

    if sub == "next":
        tid = next_task_id(q)
        if not tid:
            print("（队列空或全部阻塞）")
            return 0
        t = proj.task(tid)
        print(json.dumps(t, ensure_ascii=False, indent=1))
        # P1-10 深评逾期提醒
        cur = proj.cursor()
        last_deep = proj.last_deep_review_ch()
        deep_every = proj.config.get("critic", {}).get("deep_every", 5)
        if cur["last_drafted"] > 0 and cur["last_drafted"] - last_deep >= deep_every:
            print("[提醒] 深评逾期：last_deep_review_ch=%d，last_drafted=%d，"
                  "deep_every=%d——先排 review_deep（pipeline §4）"
                  % (last_deep, cur["last_drafted"], deep_every))
        return 0

    if sub == "list":
        for t in q["tasks"]:
            if args.state and t["state"] != args.state:
                continue
            print("%s %-13s %-12s [%s] attempts=%d %s"
                  % (t["id"], t["type"], t["target"], t["state"],
                     t.get("attempts", 0), t.get("note", "")))
        return 0

    if sub == "archive":
        keep = args.keep
        done = [t for t in q["tasks"] if t["state"] == "done"]
        if len(done) <= keep:
            print("done 任务 %d 条 ≤ keep=%d，无需归档" % (len(done), keep))
            return 0
        move = done[:-keep] if keep else done
        move_ids = {t["id"] for t in move}
        arch_p = proj.p("tasks", "archive.json")
        arch = json.loads(read(arch_p)) if arch_p.is_file() else {"tasks": []}
        arch["tasks"].extend(move)
        write(arch_p, json.dumps(arch, ensure_ascii=False, indent=1))
        q["tasks"] = [t for t in q["tasks"] if t["id"] not in move_ids]
        proj.save_queue(q)
        print("已归档 %d 条 done 任务 → tasks/archive.json（队列余 %d 条）"
              % (len(move), len(q["tasks"])))
        return 0

    # start / done / fail / reset
    t = proj.task(args.id)
    if not t:
        die("任务不存在：%s" % args.id)
    if sub == "start":
        t["state"] = "running"
    elif sub == "done":
        t["state"] = "done"
    elif sub == "reset":
        if t["state"] not in ("failed", "running"):
            die("task reset 仅接受 failed|running（%s 当前 %s）；blocked 由依赖完成自动解锁"
                % (t["id"], t["state"]), 1)
        t["state"] = "pending"
    elif sub == "fail":
        t["state"] = "failed"
        t["attempts"] = t.get("attempts", 0) + 1
        if t["type"] in ("write", "revise") and t["attempts"] >= 2:
            nid = "t_%06d" % q["next_seq"]
            q["next_seq"] += 1
            q["tasks"].append({"id": nid, "type": "revise_design",
                               "target": t["target"], "state": "pending",
                               "blocked_on": [], "attempts": 0,
                               "note": "自动升级：%s 修订达限" % t["id"],
                               "evidence": "见 %s note：%s" % (t["id"], args.note or ""),
                               "created_at": NOW(), "updated_at": NOW()})
            print("attempts 达限 → 自动追加 revise_design 任务 %s（formats §10）" % nid)
    if args.note:
        t["note"] = (t.get("note", "") + " | " + args.note).strip(" |")
    t["updated_at"] = NOW()
    # 保存（t 是副本，须回写）
    for i, x in enumerate(q["tasks"]):
        if x["id"] == t["id"]:
            q["tasks"][i] = t
    # done 后可能解锁下游 blocked
    if sub == "done":
        promote_blocked(q)
    proj.save_queue(q)
    print("%s → %s" % (t["id"], t["state"]))
    return 0
