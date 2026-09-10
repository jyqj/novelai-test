# -*- coding: utf-8 -*-
"""commitflow — 唯一写路径：commit（事务日志 + 撤销重放 + 台账回写 + ngram 缓存），
及其共享半边（adopt 复用 txn_* 与 update_ngram_cache）。"""
import datetime
import json
import hashlib
import re

from .common import (NODE_KINDS, NOW, REQUIRED_SECTIONS, cache_fps, ch_num,
                     char_ngrams, cjk_len, die, dump_frontmatter, get_section,
                     git_autocommit, parse_frontmatter, read, split_sections,
                     strip_ch_lines, thread_effective_state, thread_next_state,
                     write, append)
from .checks import check_unit, writeback_ref_errors
from .journal import register_facts
from .project import Project, find_root
from .rollup import update_rollup
from .stagectl import stage_guard


def commit_stage_allowed(ttype, target):
    """commit 的阶段辖区（P7-S）：任务类型 × 目标 → 允许阶段集。
    未知类型返回 None（由 cmd_commit 尾部用法报错兜底）。"""
    if ttype in ("write", "revise"):
        return ("write",)
    if ttype == "review_deep":
        return ("review", "ops")
    if ttype == "revise_rubric":
        return ("review",)
    if ttype in ("design", "revise_design"):
        tgt = str(target or "")
        if tgt.startswith("vol"):
            return ("s4", "vol")
        if tgt.startswith("arc") or tgt.startswith("ch_"):
            return ("arc",)
        return ("s1", "s2", "s3", "s4")
    return None


def unapply_chapter_logs(proj, ch_id):
    """P0-1 撤销半边（revise 前执行）：实体事件日志与线索推进日志剔除本章行；
    last_event_ch 由剩余日志重算；线索 state 由剩余 op 重放；plant_ch 回滚。"""
    touched = []
    for eid, e in proj.entities().items():
        body, removed = strip_ch_lines(e["body"], ch_id)
        if not removed:
            continue
        meta = e["meta"]
        remaining = [int(m.group(1)) for m in
                     re.finditer(r"^-\s*ch_(\d{4})\s*:", body, re.M)]
        meta["last_event_ch"] = max(remaining) if remaining else 0
        meta["updated_at"] = NOW()
        write(e["path"], dump_frontmatter(meta) + "\n" + body.lstrip("\n"))
        touched.append(eid)
    for tid, th in proj.threads().items():
        log = get_section(th["body"], "推进日志") or ""
        if not re.search(r"^-\s*%s\s*:" % ch_id, log, re.M):
            continue
        new_state = thread_effective_state(th, exclude_ch=ch_id)
        body, _ = strip_ch_lines(th["body"], ch_id)
        meta = th["meta"]
        meta["state"] = new_state
        if meta.get("plant_ch") == ch_num(ch_id):
            m = re.search(r"^-\s*ch_(\d{4})\s*:\s*plant\b", body, re.M)
            meta["plant_ch"] = int(m.group(1)) if m else None
        meta["updated_at"] = NOW()
        write(th["path"], dump_frontmatter(meta) + "\n" + body.lstrip("\n"))
        touched.append(tid)
    return touched


def apply_writeback(proj, ch_id, wb, rev=1):
    """continuity_delta → 实体事件日志 + facts 登记；thread_ops → 推进日志+state（合法迁移表）；
    payoff/timeline/power 台账（rev 列，读侧去重）。引用越权 = 硬失败（返回 (False, errors)，
    调用方拒绝落盘）。rev>1 = revise：先撤销本章上一轮日志效应再重放（零双计）。"""
    errs = writeback_ref_errors(proj, ch_id, wb)
    if errs:
        return False, errs
    num = ch_num(ch_id)
    notes = []
    if rev > 1:
        touched = unapply_chapter_logs(proj, ch_id)
        if touched:
            notes.append("revise 撤销重放：已剔除 %s 的上一轮日志行（%s）"
                         % (ch_id, " ".join(touched)))
    ents = proj.entities()
    for delta in wb.get("continuity_delta", []) or []:
        for ref in delta.get("entity_ids", []):
            eid = proj.resolve_entity(ref)
            e = ents[eid]
            body = e["body"].rstrip() + "\n- %s: %s\n" % (ch_id, delta.get("fact", ""))
            meta = e["meta"]
            meta["last_event_ch"] = max(num, meta.get("last_event_ch") or 0)
            meta["updated_at"] = NOW()
            write(e["path"], dump_frontmatter(meta) + "\n" + body.lstrip("\n"))
            ents = proj.entities()  # 重载，防同章多条
    threads = proj.threads()
    for op in wb.get("thread_ops", []) or []:
        tid = op["id"]
        t = threads[tid]
        meta = t["meta"]
        nxt = thread_next_state(meta.get("state"), op["op"])
        body = t["body"].rstrip() + "\n- %s: %s %s\n" % (ch_id, op["op"], op.get("note", ""))
        meta["state"] = nxt
        if op["op"] == "plant" and not meta.get("plant_ch"):
            meta["plant_ch"] = num  # P1-3：plant 回填 plant_ch
        meta["updated_at"] = NOW()
        write(t["path"], dump_frontmatter(meta) + "\n" + body.lstrip("\n"))
        threads = proj.threads()
    # facts 登记（P0-1；revise 先剪后登）
    added = register_facts(proj, ch_id, wb, rev=rev)
    if added:
        notes.append("facts 已登记：%s → ledgers/facts/%s.json"
                     % (" ".join(added), proj.vol_of_chapter(ch_id)))
    # payoff 台账（rev 列）
    task = proj.chapter_task(ch_id) or {}
    quota = task.get("payoff_quota", [])
    realized = set(wb.get("payoff_realized", []))
    for i, q in enumerate(quota, 1):
        pid = "payoff_%04d_%d" % (num, i)
        append(proj.p("ledgers", "payoff.tsv"),
               "%s\t%s\t%s\t%s\t%d\t%d\n" %
               (ch_id, pid, q.get("kind", "other"), q.get("intent", ""),
                1 if pid in realized else 0, rev))
    ta = wb.get("time_advance", {})
    append(proj.p("ledgers", "timeline.tsv"), "%s\t%s\t%s\t\t%d\n" %
           (ch_id, ta.get("story_date", ""), ta.get("elapsed", ""), rev))
    pd = wb.get("power_delta", []) or []
    if pd:
        pf = proj.p("ledgers", "power.tsv")
        if not pf.is_file():
            write(pf, "chapter\tentity\tfrom\tto\tnote\trev\n")
        for d in pd:
            for ref in d.get("entity_ids", []):
                append(pf, "%s\t%s\t%s\t%s\t%s\t%d\n" %
                       (ch_id, proj.resolve_entity(ref), d.get("from", ""),
                        d.get("to", ""), d.get("note", ""), rev))
        notes.append("power 台账已追加 %d 行" % sum(len(d.get("entity_ids", [])) for d in pd))
    return True, notes


# ---------------------------------------------------------------- 事务日志（P0-3）
def txn_begin(proj, kind, target, task_id=""):
    from .transactions import ACTIVE
    if ACTIVE is None:
        raise RuntimeError("写命令须经 CLI 事务入口执行")
    return ACTIVE.id


def txn_end(proj, txn_id):
    # The outer CLI transaction also covers task consumption and all derived files.
    pass


def update_ngram_cache(proj, ch_id, text):
    """P2-4 分层指纹保留：窗口内两级全量（n12+n8）；窗口外降级为归档层
    （n12s = 12-gram 稳定降采样），12 字级自我复读检测覆盖全史而体积有界。"""
    cache = proj.ngram_cache()
    cache[ch_id] = {"n12": sorted(set(char_ngrams(text, 12))),
                    "n8": sorted(set(char_ngrams(text, 8)))}
    window = proj.config.get("ngram_window_chapters", 30)
    sample = proj.config.get("ngram_archive_sample", 400)
    keys = sorted(cache, key=lambda k: ch_num(k) if re.match(r"ch_\d{4}$", k) else 0)
    for k in keys[:-window]:
        entry = cache.get(k)
        if isinstance(entry, dict) and "n12s" in entry:
            continue  # 已归档
        n12 = sorted(cache_fps(entry, "n12"))
        step = max(1, len(n12) // max(sample, 1))
        cache[k] = {"n12s": n12[::step][:sample]}
    write(proj.p("state", "ngram_cache.json"), json.dumps(cache, ensure_ascii=False))


def propagate_stale(proj, node_id):
    """P1-7：revise_design 定稿后，受影响下游沿 parent 链递归标 stale（直到章）。"""
    nodes = proj.tree_nodes()
    chs = proj.chapters()
    children = {}
    for n in nodes:
        children.setdefault(n["meta"].get("parent"), []).append(("node", n))
    for c in chs:
        children.setdefault(c["meta"].get("parent"), []).append(("ch", c))
    stale, queue = [], [node_id]
    seen = set()
    while queue:
        cur = queue.pop(0)
        if cur in seen:
            continue
        seen.add(cur)
        for typ, item in children.get(cur, []):
            m = item["meta"]
            if typ == "node":
                iid = m.get("id")
                if m.get("status") in ("draft", "committed"):
                    m["status"] = "stale"
                    m["updated_at"] = NOW()
                    write(item["path"], dump_frontmatter(m) + "\n" + item["body"].lstrip("\n"))
                    stale.append(iid)
                queue.append(iid)
            else:
                if m.get("status") in ("planned", "drafted", "approved"):
                    m["status"] = "stale"
                    m["updated_at"] = NOW()
                    write(item["path"], dump_frontmatter(m) + "\n" + item["body"].lstrip("\n"))
                    stale.append(item["id"])
    return stale


def route_staged_file(proj, meta):
    """Strict ID/kind pairing; no relative paths or arbitrary review targets."""
    kind, fid = meta.get("kind"), str(meta.get("id", ""))
    patterns = {"volume": r"vol_\d{2}", "arc": r"arc_\d{2}_\d+",
                "entity": r"(?:char|item|loc|fac)_[a-z0-9_]+",
                "thread": r"thread_[a-z0-9_]+", "decision": r"dec_[a-zA-Z0-9_.-]+"}
    if kind in ("book", "style", "world"):
        return proj.p("tree", kind + ".md") if fid == kind else None
    if kind == "review":
        ch = str(meta.get("chapter", ""))
        depth = meta.get("depth")
        if not re.fullmatch(r"ch_\d{4}", ch) or depth not in ("light", "deep"):
            return None
        return proj.p("reviews", "%s.%s.md" % (ch, depth))
    if kind not in patterns or not re.fullmatch(patterns[kind], fid):
        return None
    if kind in ("volume", "arc"):
        return proj.node_path(fid)
    directory = {"entity": "entities", "thread": "threads", "decision": "court"}[kind]
    return proj.p(directory, fid + ".md")


def commit_fingerprint(args, task):
    paths = ([args.chapter, args.writeback] if task["type"] in ("write", "revise")
             else args.file or [])
    payload = [task["type"], task["target"], bool(args.draft),
               [read(p) for p in paths if p]]
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False).encode()).hexdigest()


def consume(proj, task_id, fingerprint):
    q = proj.queue()
    for task in q["tasks"]:
        if task["id"] == task_id:
            task["commit_fingerprint"] = fingerprint
            task["committed_at"] = NOW()
    proj.save_queue(q)


def cmd_commit(args):
    proj = Project(find_root(args))
    t = proj.task(args.task_id)
    if not t:
        die("任务不存在：%s" % args.task_id)
    fingerprint = commit_fingerprint(args, t)
    if t.get("commit_fingerprint"):
        if t["commit_fingerprint"] == fingerprint:
            print("已提交相同产物；幂等重试，未重复记账")
            return 0
        die("任务已消费；不同产物必须创建新的 revise/design 任务", 1)
    if t["state"] not in ("pending", "running"):
        die("只能提交 pending/running 且依赖已完成的任务", 1)
    ttype = t["type"]
    msg = args.m or ""
    allowed = commit_stage_allowed(ttype, t.get("target"))
    if allowed:
        stage_guard(proj, allowed, "commit %s(%s)" % (ttype, t.get("target")))

    if ttype in ("write", "revise"):
        if not (args.chapter and args.writeback):
            die("write/revise 需 --chapter <候选章文件> --writeback <json>")
        ch_id = t["target"]
        rep = check_unit(proj, ch_id, args.chapter, args.writeback)
        code = rep.render("commit 前置机检（%s）" % ch_id)
        if code != 0:
            print("[拒绝] 机检不绿，未落盘（问题清单并入修订循环，pipeline §2）")
            return 1
        exist_p = proj.p("chapters", ch_id + ".md")
        old_meta = parse_frontmatter(read(exist_p))[0] if exist_p.is_file() else {}
        old_meta = old_meta or {}
        if old_meta.get("status") == "published":
            die("published 章不可改写——走 serial-ops.md §3 retcon", 1)
        if ttype == "write" and (old_meta.get("status") != "planned"
                                 or proj.chapter_meta_json(ch_id) is not None):
            die("write 只接受首次写作的 planned 章；已有正文必须使用 revise", 1)
        if ttype == "revise" and (old_meta.get("status") not in ("drafted", "approved", "stale")
                                  or proj.chapter_meta_json(ch_id) is None):
            die("revise 需要已有未发布正文", 1)
        cand_meta, cand_body = parse_frontmatter(read(args.chapter))
        wb = json.loads(read(args.writeback))
        text = cand_body.split("## 正文", 1)[-1]
        new_rev = (old_meta.get("rev") or 0) + 1 if ttype == "revise" \
            else max(old_meta.get("rev") or 1, 1)
        # 先做回写引用硬校验（引用越权=拒绝，不产生任何写入）
        errs = writeback_ref_errors(proj, ch_id, wb)
        if errs:
            print("[拒绝] writeback 引用越权，未落盘：")
            for e in errs:
                print("  - " + e)
            return 1
        # P0-3：journal → 多文件落盘 → 完成标记（中断可被 fsck 检出）
        txn = txn_begin(proj, ttype, ch_id, args.task_id)
        ok, msgs = apply_writeback(proj, ch_id, wb, rev=new_rev)
        if not ok:  # 双保险（理论不可达：上面已预校验）
            print("[拒绝] writeback 引用越权，未落盘：")
            for e in msgs:
                print("  - " + e)
            return 1
        new_meta = {
            "id": ch_id, "kind": "chapter", "status": "drafted",
            "rev": new_rev,
            "parent": cand_meta.get("parent") or old_meta.get("parent"),
            "updated_at": NOW(),
            "title": cand_meta.get("title", old_meta.get("title", "")),
            "word_count": cjk_len(text),
        }
        write(exist_p, dump_frontmatter(new_meta) + "\n\n## 正文\n" + text.strip() + "\n")
        write(proj.p("chapters", ch_id + ".meta.json"),
              json.dumps(wb, ensure_ascii=False, indent=1))
        update_ngram_cache(proj, ch_id, text)
        update_rollup(proj)
        consume(proj, args.task_id, fingerprint)
        txn_end(proj, txn)
        for w in msgs:
            print("[info] " + w)
        git_autocommit(proj.root, "[%s] %s(%s): %s" % (args.task_id, ttype, ch_id, msg))
        print("已落盘：%s（status=drafted, rev=%d）+ meta.json + facts/台账/日志/ngram/rollup"
              % (ch_id, new_meta["rev"]))
        return 0

    if ttype in ("design", "revise_design", "review_deep", "revise_rubric"):
        if not args.file:
            die("%s 需 --file <staged 文件> [...]" % ttype)
        if ttype in ("revise_design", "revise_rubric") and not t.get("evidence"):
            die("%s 任务缺 evidence（revise_design 先过否决案台账 court.md §4；"
                "revise_rubric 须引用 lessons/review 条目）" % ttype, 1)
        # P0-3：两遍制——第一遍全量校验（零写入），第二遍才落盘（多文件原子性）
        staged = []
        for fpath in args.file:
            meta, body = parse_frontmatter(read(fpath))
            if meta is None:
                die("staged 文件无信封：%s" % fpath, 1)
            if ttype == "revise_rubric" and meta.get("kind") != "style":
                die("revise_rubric 只接受 kind=style 的 staged 文件（判据蒸馏专用轻量"
                    "路径，不波及树；其他节点走 revise_design）", 1)
            target = route_staged_file(proj, meta)
            if target is None:
                die("无法路由 kind=%s 的文件（id=%s）" % (meta.get("kind"), meta.get("id")), 1)
            if meta.get("kind") in NODE_KINDS and not args.draft:
                req = REQUIRED_SECTIONS.get(meta["kind"], [])
                titles = [x for x, _ in split_sections(body)]
                missing = [s for s in req
                           if not any(x == s or x.startswith(s) for x in titles)]
                empty = [s for s in req
                         if not missing and not (get_section(body, s) or "").strip()]
                if missing or empty:
                    die("design 校验失败 %s：缺节 %s / 空节 %s（全批未落盘）"
                        % (meta.get("id"), missing, empty), 1)
            if any(dest == target for _, _, dest in staged):
                die("同批多个产物写入同一目标：%s" % target, 1)
            if meta.get("kind") == "review":
                from .receipts import receipt_errors
                errors = receipt_errors(proj, meta, body)
                if errors:
                    die("评审证据无效：" + "; ".join(errors), 1)
            if ttype == "review_deep" and (meta.get("kind") != "review"
                                           or meta.get("depth") != "deep"
                                           or meta.get("chapter") != t["target"]):
                die("review_deep 只能提交目标章的深评回执", 1)
            if meta.get("kind") in NODE_KINDS and target.is_file():
                previous, _ = parse_frontmatter(read(target))
                meta["rev"] = ((previous or {}).get("rev") or 0) + 1
            staged.append((meta, body, target))
        txn = txn_begin(proj, ttype, t["target"], args.task_id)
        main_done = False
        for meta, body, target in staged:
            if ttype == "revise_rubric" and target.is_file():
                # P4-D 蒸馏路径：rev 自动 +1；不递归标 stale（黑名单增补只约束
                # 未来章的 check --unit，不作废既有章）
                old, _ = parse_frontmatter(read(target))
                meta["rev"] = ((old or {}).get("rev") or 0) + 1
            if meta.get("kind") in NODE_KINDS:
                if args.draft:
                    # P0-6：draft 态部分落盘（书庭中间场次可持久化半成品，不算定稿）
                    meta["status"] = "draft"
                    meta["updated_at"] = NOW()
                    write(target, dump_frontmatter(meta) + "\n" + body.lstrip("\n"))
                    print("已 draft 部分落盘 → %s（不算定稿，必需节校验延后到正式 commit）"
                          % target.relative_to(proj.root))
                    continue
                meta["status"] = "committed"
                meta["updated_at"] = NOW()
                main_done = True
            if meta.get("kind") == "review" and meta.get("verdict") == "escalate":
                q = proj.queue()
                nid = "t_%06d" % q["next_seq"]
                q["next_seq"] += 1
                q["tasks"].append({"id": nid, "type": "revise_design",
                                   "target": meta.get("chapter", ""), "state": "pending",
                                   "blocked_on": [], "attempts": 0,
                                   "note": "深评 escalate 自动开单",
                                   "evidence": "review %s" % meta.get("id"),
                                   "created_at": NOW(), "updated_at": NOW()})
                proj.save_queue(q)
                print("verdict=escalate → 自动开 revise_design 任务 %s" % nid)
            write(target, dump_frontmatter(meta) + "\n" + body.lstrip("\n"))
            print("已落盘 → %s" % target.relative_to(proj.root))
        if ttype == "revise_design" and main_done:
            stale = propagate_stale(proj, t["target"])
            if stale:
                print("下游已递归标 stale：%s（修复后回原 status；影响面报告模板见 court.md §4）"
                      % " ".join(stale))
        if ttype == "revise_rubric":
            print("蒸馏入库：style.md rev+1；新黑名单自下一次 check --unit 起机检生效"
                  "（不波及既有章）；来源 evidence：%s" % t.get("evidence"))
        if not args.draft:
            consume(proj, args.task_id, fingerprint)
        txn_end(proj, txn)
        git_autocommit(proj.root, "[%s] %s(%s): %s" % (args.task_id, ttype, t["target"], msg))
        return 0

    die("commit 支持 write|revise|design|revise_design|review_deep|revise_rubric；"
        "publish 用 publish，retcon 用 retcon，checkpoint 用 checkpoint，"
        "reconcile 用 entity update", 2)
