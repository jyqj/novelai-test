# -*- coding: utf-8 -*-
"""journal — 台账与卡片：entity / thread / ledger 视图 / facts（登记与补录）。"""
import json
import re

from .common import (NOW, THREAD_KINDS, ch_num, die, dump_frontmatter,
                     get_section, git_autocommit, instantiate,
                     parse_elapsed_days, read, split_sections, write)
from .project import Project, find_root
from .rollup import update_rollup


# ---------------------------------------------------------------- entity / thread
def cmd_entity(args):
    proj = Project(find_root(args))
    sub = args.entity_cmd
    if sub == "new":
        m = re.match(r"^(char|item|loc|fac)_[a-z0-9_]+$", args.id)
        if not m:
            die("实体 id 应为 {char|item|loc|fac}_{slug}")
        if proj.p("entities", args.id + ".md").exists():
            die("实体卡已存在，拒绝覆盖", 1)
        etype = m.group(1)
        rep = {"[%s_slug]" % etype: args.id, "[YYYY-MM-DDTHH:MM:SSZ]": NOW()}
        write(proj.p("entities", args.id + ".md"),
              instantiate("entity-%s.md" % etype, rep))
        print("已建卡 %s" % args.id)
        return 0
    ents = proj.entities()
    if sub == "due":
        thr = proj.config.get("reconcile_every", 10)
        due = [e for e, v in ents.items()
               if (v["meta"].get("last_event_ch", 0) or 0)
               - (v["meta"].get("last_reconcile_ch", 0) or 0) >= thr]
        print("\n".join(due) if due else "（无到期实体）")
        return 0
    if args.id not in ents:
        die("实体不存在：%s" % args.id)
    ent = ents[args.id]
    if sub == "show":
        print(read(ent["path"]))
        return 0
    if sub == "log":
        print(get_section(ent["body"], "事件日志") or "（空）")
        return 0
    if sub == "update":
        hp = proj.p("entities", "history", args.id + ".json")
        history = json.loads(read(hp)) if hp.is_file() else []
        old_at = int(ent["meta"].get("last_reconcile_ch") or 0)
        history.append({"chapter": old_at, "status": get_section(ent["body"], "现状") or ""})
        new_text = re.sub(r"^##\s*现状\s*\n+", "", read(args.file).strip())
        out = []
        for t, c in split_sections(ent["body"]):
            out.append("## %s\n\n%s" % (t, new_text if t.startswith("现状") else c))
        meta = ent["meta"]
        meta["last_reconcile_ch"] = proj.cursor()["last_drafted"]
        meta["updated_at"] = NOW()
        meta["rev"] = (meta.get("rev") or 1) + 1
        write(ent["path"], dump_frontmatter(meta) + "\n\n" + "\n\n".join(out) + "\n")
        history.append({"chapter": meta["last_reconcile_ch"], "status": new_text})
        write(hp, json.dumps(history, ensure_ascii=False, indent=1))
        print("现状节已替换，last_reconcile_ch=%d" % meta["last_reconcile_ch"])
        return 0
    return 2


def cmd_thread(args):
    proj = Project(find_root(args))
    if not re.match(r"^thread_[a-z0-9_]+$", args.id):
        die("线索 id 应为 thread_{slug}")
    if proj.p("threads", args.id + ".md").exists():
        die("线索卡已存在，拒绝覆盖", 1)
    rep = {"[thread_slug]": args.id, "[YYYY-MM-DDTHH:MM:SSZ]": NOW()}
    text = instantiate("thread.md", rep)
    if args.kind:
        if args.kind not in THREAD_KINDS:
            die("thread_kind 须为 %s" % "|".join(THREAD_KINDS))
        text = text.replace("thread_kind: fuse", "thread_kind: " + args.kind)
    write(proj.p("threads", args.id + ".md"), text)
    print("已登记线索 %s" % args.id)
    return 0


# ---------------------------------------------------------------- ledger 视图
def cmd_ledger(args):
    proj = Project(find_root(args))
    if args.which == "payoff":
        for r in proj.payoff_rows():
            print("%s %s %-9s realized=%d %s"
                  % (r["chapter"], r["payoff_id"], r["kind"],
                     r["realized"], r["intent"]))
    elif args.which == "promise":
        for tid, t in proj.threads().items():
            m = t["meta"]
            if m.get("thread_kind") == "promise":
                print("%s [%s] must_not_drop=%s plant_ch=%s payoff_planned=%s"
                      % (tid, m.get("state"), m.get("must_not_drop"),
                         m.get("plant_ch"), m.get("payoff_planned")))
    elif args.which == "power":
        for r in proj.power_rows():
            print("%s %s：%s → %s %s（rev%d）"
                  % (r["chapter"], r["entity"], r["from"], r["to"],
                     r["note"], r["rev"]))
        if not proj.power_rows():
            print("（空）")
    else:
        rows = sorted(proj.timeline_rows(),
                      key=lambda r: ch_num(r["chapter"])
                      if re.match(r"^ch_\d{4}$", r["chapter"]) else 0)
        if not rows:
            print("（空）")
        else:
            print("chapter\tstory_date\telapsed\t累计天\tnote")
            cum = 0.0
            for r in rows:
                d = parse_elapsed_days(r["elapsed"])
                cum += d or 0
                print("%s\t%s\t%s\t%s\t%s"
                      % (r["chapter"], r["story_date"] or "-", r["elapsed"] or "-",
                         ("%.1f" % cum) if d is not None else "?（不可解析）",
                         r["note"]))
    return 0


# ---------------------------------------------------------------- facts（P0-4）
def register_facts(proj, ch_id, wb, rev=1):
    """P0-1：commit 时自 continuity_delta 自动分配 fact_id 写入 ledgers/facts/vol_NN.json。
    同文同章去重；rev>1（revise）时先剪除本章上一轮登记的临时事实（未被 retcon 引用、
    未被覆盖者），再按新 writeback 重登——(chapter, rev) 语义的 facts 半边。
    返回新登记的 fact id 列表。"""
    deltas = wb.get("continuity_delta", []) or []
    num = ch_num(ch_id)
    vol = proj.vol_of_chapter(ch_id)
    f = proj.p("ledgers", "facts", vol + ".json")
    data = json.loads(read(f)) if f.is_file() else {"facts": [], "retcons": []}
    pruned = 0
    if rev > 1:
        referenced = {r.get("old_fact_id") for r in data.get("retcons", [])}
        keep = [x for x in data.get("facts", [])
                if not (x.get("revealed_ch") == num and not x.get("superseded_by")
                        and x.get("id") not in referenced)]
        pruned = len(data.get("facts", [])) - len(keep)
        data["facts"] = keep
    if not deltas and not pruned:
        return []
    existing = {(x.get("fact"), x.get("revealed_ch")) for x in data.get("facts", [])}
    seq = 0
    for x, _ in proj.all_facts():
        m = re.match(r"^fact_(\d{4,})$", str(x.get("id", "")))
        if m:
            seq = max(seq, int(m.group(1)))
    for x in data.get("facts", []):
        m = re.match(r"^fact_(\d{4,})$", str(x.get("id", "")))
        if m:
            seq = max(seq, int(m.group(1)))
    seq += 1
    added = []
    for d in deltas:
        key = (d.get("fact"), num)
        if key in existing:
            continue
        existing.add(key)
        rec = {"id": "fact_%04d" % seq, "fact": d.get("fact", ""),
               "entity_ids": sorted({proj.resolve_entity(r) or r
                                     for r in d.get("entity_ids", [])}),
               "revealed_ch": num, "spoiler": d.get("spoiler", 0),
               "superseded_by": None}
        if d.get("key"):
            rec["key"] = d["key"]
        # P4-K 知识矩阵：事实 × 角色（known_by）× 读者（spoiler）——who-knows-what 台账
        if d.get("known_by"):
            rec["known_by"] = sorted({proj.resolve_entity(r) or r
                                      for r in d["known_by"]})
        if rec.get("known_by"):
            rec["knowledge_events"] = [{"chapter": num,
                "knowers": sorted(proj.expand_knowers(rec["known_by"])),
                "via": rec["known_by"][:]}]
        data.setdefault("facts", []).append(rec)
        added.append(rec["id"])
        seq += 1
    write(f, json.dumps(data, ensure_ascii=False, indent=1))
    if pruned:
        added.append("(剪除上一 rev 临时事实 %d 条)" % pruned)
    return added


def cmd_facts(args):
    """facts 台账工具：import = adopt 补录的机械半边（自各章 meta.json 的
    continuity_delta 分配 fact_id 入账，同文同章去重，可重复执行）。"""
    proj = Project(find_root(args))
    if args.facts_cmd == "list":
        for x, fname in proj.all_facts():
            if args.entity and args.entity not in (x.get("entity_ids") or []):
                continue
            flag = ""
            if x.get("spoiler"):
                flag += "【spoiler】"
            if x.get("known_by"):
                flag += "【知情:%s】" % ",".join(x["known_by"])
            if x.get("superseded_by"):
                flag += "【已覆盖 %s】" % x["superseded_by"]
            print("%-10s ch%-4s %s%s（%s｜%s）"
                  % (x.get("id"), x.get("revealed_ch"), flag, x.get("fact"),
                     ",".join(x.get("entity_ids") or []), fname))
        return 0
    # import
    total = []
    for ch_id in args.ch_ids:
        ch_num(ch_id)
        wb = proj.chapter_meta_json(ch_id)
        if wb is None:
            die("缺 chapters/%s.meta.json（先按 protocol/adopt.md §3 补录 writeback）"
                % ch_id, 1)
        errs = []
        for i, d in enumerate(wb.get("continuity_delta", []) or []):
            for k in ("fact", "entity_ids", "spoiler"):
                if k not in d:
                    errs.append("continuity_delta[%d] 缺 %s" % (i, k))
            for ref in d.get("entity_ids", []):
                if not proj.resolve_entity(ref):
                    errs.append("continuity_delta[%d] 实体「%s」未登记"
                                "（先 entity new/补 aliases）" % (i, ref))
        if errs:
            die("%s 补录校验失败（零入账）：\n  %s" % (ch_id, "\n  ".join(errs)), 1)
        added = register_facts(proj, ch_id, wb)
        total += added
        print("%s：%s" % (ch_id, "登记 " + " ".join(added) if added
                          else "无新事实（已入账或 delta 为空）"))
    # 补录 writeback 后 rollup 一并刷新（adopt 时 summary_after 为空被跳过）
    update_rollup(proj)
    if total:
        git_autocommit(proj.root, "[facts] import %s" % " ".join(args.ch_ids))
    print("facts import 完成：新登记 %d 条；跑 check --project 复核" % len(total))
    return 0
