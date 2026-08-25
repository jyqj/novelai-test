# -*- coding: utf-8 -*-
"""bootstrap — init 脚手架 / adopt 存量收编（项目进入工作流前的两条入口）。"""
import json
from pathlib import Path

from .common import (NOW, TEMPLATES, ch_num, cjk_len, die, dump_frontmatter,
                     git, git_autocommit, instantiate, parse_frontmatter, read,
                     write)
from .commitflow import txn_begin, txn_end, update_ngram_cache
from .project import Project, find_root
from .rollup import update_rollup


def cmd_init(args):
    root = Path(args.dir).resolve()
    if (root / "config.json").exists():
        die("目标已是项目：%s" % root)
    for d in ("tree", "chapters", "briefs", "entities", "threads", "ledgers/facts",
              "court/transcripts", "reviews", "data/feedback", "data/compliance",
              "tasks", "state/court", "state/reports", "state/txn", "corpus"):
        (root / d).mkdir(parents=True, exist_ok=True)
    cfg = json.loads(read(TEMPLATES / "config.json"))
    cfg["name"] = args.name or root.name
    write(root / "config.json", json.dumps(cfg, ensure_ascii=False, indent=2))
    rep = {"[YYYY-MM-DDTHH:MM:SSZ]": NOW()}
    for t, dest in (("book.md", "tree/book.md"), ("style.md", "tree/style.md"),
                    ("world.md", "tree/world.md")):
        write(root / dest, instantiate(t, rep))
    write(root / "ledgers/timeline.tsv", "chapter\tstory_date\telapsed\tnote\trev\n")
    write(root / "ledgers/payoff.tsv", "chapter\tpayoff_id\tkind\tintent\trealized\trev\n")
    write(root / "ledgers/power.tsv", "chapter\tentity\tfrom\tto\tnote\trev\n")
    write(root / "ledgers/lessons.md", "# lessons（一行一课，编排者经 commit 附笔追加）\n")
    write(root / "ledgers/recap.md",
          "# recap（全局梗概；编排者维护：卷末 checkpoint 必更，期间每 ~10 章可追加）\n"
          "# 每段 3–6 行；novel.py brief 会把本文件尾 12 行注入简报 §2。\n")
    write(root / "entities/aliases.json", "{}\n")
    write(root / "tasks/queue.json", json.dumps({"next_seq": 1, "tasks": []}))
    if git(root, "init", "-q"):
        git_autocommit(root, "[init] 项目脚手架")
        print("git 仓库已初始化并完成首次提交")
    else:
        print("[warn] git 不可用，跳过版本化（单写者纪律降级为原子写入）")
    print("项目已创建：%s" % root)
    print("下一步：填写 tree/book.md、tree/world.md、tree/style.md（书庭产出），"
          "然后 tree set-status 置 committed")
    return 0


def cmd_adopt(args):
    """P1-9：收编外部文稿为项目章（protocol/adopt.md）。"""
    proj = Project(find_root(args))
    ch_id = args.as_id
    num = ch_num(ch_id)
    src = Path(args.file)
    if not src.is_file():
        die("源文件不存在：%s" % src)
    exist = proj.p("chapters", ch_id + ".md")
    if exist.is_file():
        emeta, _ = parse_frontmatter(read(exist))
        if (emeta or {}).get("status") not in (None, "planned"):
            die("%s 已存在且非 planned（status=%s）——收编不覆盖成稿，改用 revise 链路"
                % (ch_id, (emeta or {}).get("status")), 1)
    raw = read(src)
    meta, body = parse_frontmatter(raw)
    text = body.split("## 正文", 1)[-1] if (meta and "## 正文" in body) else raw
    new_meta = {
        "id": ch_id, "kind": "chapter", "status": "drafted", "rev": 1,
        "parent": args.parent or (meta or {}).get("parent") or "",
        "updated_at": NOW(),
        "title": args.title or (meta or {}).get("title", ""),
        "word_count": cjk_len(text),
    }
    txn = txn_begin(proj, "adopt", ch_id)
    write(exist, dump_frontmatter(new_meta) + "\n\n## 正文\n" + text.strip() + "\n")
    tp = proj.p("chapters", ch_id + ".task.json")
    if not tp.is_file():
        write(tp, instantiate("chapter.task.json",
                              {"[ch_0001]": ch_id,
                               "[arc_01_1]": args.parent or "[arc_01_1]"}))
    mp = proj.p("chapters", ch_id + ".meta.json")
    if not mp.is_file():
        stub = {"summary_after": "", "continuity_delta": [],
                "time_advance": {"elapsed": "", "story_date": ""}, "thread_ops": [],
                "payoff_realized": [], "hooks_realized": {"open": False, "close": False},
                "cast_actual": [],
                "issues": ["adopted：外部文稿收编，writeback 待补录（protocol/adopt.md §3）"],
                "word_count": new_meta["word_count"]}
        write(mp, json.dumps(stub, ensure_ascii=False, indent=1))
    update_ngram_cache(proj, ch_id, text)
    update_rollup(proj)
    txn_end(proj, txn)
    git_autocommit(proj.root, "[adopt] %s ← %s" % (ch_id, src.name))
    print("已收编：%s（status=drafted, %d 字）" % (ch_id, new_meta["word_count"]))
    print("后续（protocol/adopt.md §3）：补 task.json 排批字段 → 补录 writeback"
          "（summary_after/continuity_delta/thread_ops）→ novel.py facts import %s → "
          "check --unit %s → 评审落盘（review add）后 set-status approved"
          % (ch_id, ch_id))
    return 0
