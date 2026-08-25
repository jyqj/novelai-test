# -*- coding: utf-8 -*-
"""review — 评审回执 CLI（P0-2）：轻/深评结论落盘 reviews/（approved 闸门唯一回执载体）。"""
import datetime

from .common import (ch_num, die, dump_frontmatter, git_autocommit,
                     parse_frontmatter, read, write)
from .project import Project, find_root
from .stagectl import stage_guard


def cmd_review(args):
    """评审回执 CLI 化：轻/深评结论落盘 reviews/（approved 闸门唯一认可的回执载体）。"""
    proj = Project(find_root(args))
    if args.review_cmd == "list":
        for r in proj.reviews():
            m = r["meta"]
            print("%-24s depth=%-5s verdict=%-8s rev_reviewed=%s date=%s"
                  % (r["path"].name, m.get("depth"), m.get("verdict"),
                     m.get("rev_reviewed"), m.get("date")))
        if not proj.reviews():
            print("（无评审单）")
        return 0
    # add：轻评属章循环收尾；深评属周期回路（卷级深评亦可在运营结账时落盘）
    stage_guard(proj, ("write",) if args.depth == "light" else ("review", "ops"),
                "review add --depth %s" % args.depth)
    ch_id = args.ch_id
    ch_num(ch_id)
    p = proj.p("chapters", ch_id + ".md")
    if not p.is_file():
        die("章不存在：%s" % ch_id, 1)
    cmeta, _ = parse_frontmatter(read(p))
    cur_rev = (cmeta or {}).get("rev") or 1
    rev = args.rev if args.rev is not None else cur_rev
    if rev != cur_rev:
        print("[warn] rev_reviewed=%d ≠ 章当前 rev=%d——该回执不会被 approved 闸门认可"
              "（仅存证历史评审）" % (rev, cur_rev))
    issues = args.issue or ["[全章] 无阻塞问题 → 通过"]
    meta = {"id": "review_%s_%s" % (ch_id, args.depth), "kind": "review",
            "chapter": ch_id, "depth": args.depth, "verdict": args.verdict,
            "rev_reviewed": rev, "date": datetime.date.today().isoformat()}
    body = "\n## 问题清单\n\n" + "\n".join("- %s" % i for i in issues) + "\n"
    if args.lesson:
        body += "\n## 教训\n\n- %s\n" % args.lesson
    out = proj.p("reviews", "%s.%s.md" % (ch_id, args.depth))
    write(out, dump_frontmatter(meta) + body)
    git_autocommit(proj.root, "[review] %s %s=%s rev%d"
                   % (ch_id, args.depth, args.verdict, rev))
    print("评审单已落盘：reviews/%s.%s.md（verdict=%s, rev_reviewed=%d）"
          % (ch_id, args.depth, args.verdict, rev))
    if args.verdict == "escalate":
        print("[提醒] escalate：按 pipeline §3 开 revise_design 任务（--evidence 必填）")
    elif args.verdict == "revise":
        print("[提醒] revise：问题清单进修订循环（pipeline §2）")
    return 0
