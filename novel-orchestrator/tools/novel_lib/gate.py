# -*- coding: utf-8 -*-
"""gate — 闸门家族（P3-1）：next/write/approve/publish/checkpoint（只判不写）。"""

from .common import Report, ch_num, git_out, parse_frontmatter, read
from .checks import check_project, check_unit
from .project import Project, find_root, load_queue_promoted, next_task_id
from .serial_ops import checkpoint_problems, publish_problems
from .stagectl import print_stage_hint
from .structure import approval_receipt


def gate_write(proj, ch_id, rep):
    """spawn 写手前置闸门：任务卡排批完整 + 弧 committed + 简报新鲜 + 基线干净。
    每条 FAIL 附「下一步」修复命令（P4-G gate UX：闸门即剧本）。"""
    task = proj.chapter_task(ch_id)
    tp = proj.p("chapters", ch_id + ".task.json")
    if not task:
        rep.add("FAIL", "缺任务卡 chapters/%s.task.json" % ch_id,
                fix="novel.py tree add chapter %s --parent <arc_NN_n>，再按 "
                    "pipeline §1 步骤 0 排批补全 task.json" % ch_id)
        return
    ph = []
    for k in ("goal", "beats", "cast"):
        v = task.get(k)
        if not v or (isinstance(v, str) and v.startswith("[")) \
                or (isinstance(v, list) and all(str(x).startswith("[") for x in v)):
            ph.append(k)
    if ph:
        rep.add("FAIL", "任务卡未排批（字段缺失/仍为占位）", ph,
                fix="编排者补全 chapters/%s.task.json 的 %s（从弧计划「章分配草案」"
                    "取料，pipeline §1 步骤 0；quality 档可委派架构师 T0）"
                    % (ch_id, "/".join(ph)))
    else:
        rep.add("PASS", "任务卡排批字段齐全（goal/beats/cast）")
    route = proj.config.get("route", "web")
    hook = task.get("hook") or {}
    if route == "web" and (not hook.get("close") or str(hook.get("close")).startswith("[")):
        rep.add("FAIL", "route=web 章尾钩未排（task.json hook.close 必填）",
                fix="补 chapters/%s.task.json 的 hook.close（一句话钩子，"
                    "pipeline §1 步骤 0）后重跑 gate write" % ch_id)
    if route == "traditional" and not task.get("turn"):
        rep.add("WARN", "traditional 未填 turn（价值翻转一句话，route-traditional §2）")
    arc = task.get("arc")
    arc_p = proj.node_path(arc) if arc and not str(arc).startswith("[") else None
    if not arc_p or not arc_p.is_file():
        rep.add("FAIL", "所属弧不存在或未填：%s" % arc,
                fix="novel.py tree add arc <arc_NN_n> → 弧简流程定稿（court.md §1 弧行）"
                    "→ task.json 填 arc")
    else:
        ameta, _ = parse_frontmatter(read(arc_p))
        if (ameta or {}).get("status") != "committed":
            rep.add("FAIL", "弧 %s 状态 %s ≠ committed"
                    % (arc, (ameta or {}).get("status")),
                    fix="novel.py task add design %s → 弧简流程（court.md §1 弧行）→ "
                        "commit <t> --file <弧定稿>" % arc)
        else:
            rep.add("PASS", "弧 %s 已 committed" % arc)
    bp = proj.p("briefs", ch_id + ".brief.md")
    if not bp.is_file():
        rep.add("FAIL", "简报未编译（写手唯一世界）",
                fix="novel.py brief %s（编译后资料员审包，pipeline §1 步骤 1–3）" % ch_id)
    elif tp.is_file() and bp.stat().st_mtime < tp.stat().st_mtime:
        rep.add("FAIL", "简报早于任务卡（排批后未重编译）",
                fix="novel.py brief %s（重编译，brief_rev+1）" % ch_id)
    else:
        rep.add("PASS", "简报存在且不早于任务卡")
    dirty = git_out(proj.root, "status", "--porcelain")
    if dirty:
        rep.add("FAIL", "工作区不干净（spawn 前基线必须干净，pipeline §5）",
                dirty.splitlines()[:8],
                fix="附笔请在 commit 前一刻写；散落改动先核对再清：git status --porcelain"
                    " → git checkout -- . && git clean -fd（worker 中间稿移项目外）")
    else:
        rep.add("PASS", "git 基线干净")
    cur = proj.cursor()
    last_deep = proj.last_deep_review_ch()
    deep_every = proj.config.get("critic", {}).get("deep_every", 5)
    if cur["last_drafted"] > 0 and cur["last_drafted"] - last_deep >= deep_every:
        rep.add("WARN", "深评逾期（last_deep=%d, last_drafted=%d）"
                % (last_deep, cur["last_drafted"]),
                fix="novel.py task add review_deep ch_%04d（pipeline §4）"
                    % cur["last_drafted"])


def gate_approve(proj, ch_id, rep):
    """approved 前置闸门：章已 drafted + 落盘回执（rev 匹配）+ 机检绿。
    每条 FAIL 附「下一步」修复命令（P4-G）。"""
    p = proj.p("chapters", ch_id + ".md")
    if not p.is_file():
        rep.add("FAIL", "章不存在：%s" % ch_id,
                fix="先走写作链落盘：novel.py commit <t> --chapter … --writeback …"
                    "（pipeline §1 步骤 8）")
        return
    meta, _ = parse_frontmatter(read(p))
    st = (meta or {}).get("status")
    if st != "drafted":
        fixes = {"planned": "章尚未成稿：走 pipeline §1 写作链到 commit",
                 "approved": "已 approved——无需重复；下一步 gate publish",
                 "published": "已 published（不可变）；修错走 serial-ops §3 retcon",
                 "stale": "上游设计已变更：按队列重排 revise 后再评（court.md §4）"}
        rep.add("FAIL", "章状态 %s ≠ drafted（迁移表 formats §3）" % st,
                fix=fixes.get(st, "核对 formats §3 状态机"))
    receipt = approval_receipt(proj, ch_id)
    if receipt:
        rep.add("PASS", "评审回执有效：%s" % receipt)
    else:
        rep.add("FAIL", "缺有效评审回执（verdict=pass 且 rev_reviewed=章当前 rev）",
                fix="先真评审（轻评按 roles/critic-light.md），后落盘回执："
                    "novel.py review add %s --depth light --verdict pass --note <要点>"
                    "（章 revise 过则须对新 rev 复评）" % ch_id)
    n_before = sum(1 for l, _, _, _ in rep.items if l == "FAIL")
    check_unit(proj, ch_id, rep=rep)
    if sum(1 for l, _, _, _ in rep.items if l == "FAIL") > n_before:
        rep.add("FAIL", "机检不绿（上列 FAIL 来自 check --unit）",
                fix="novel.py check --unit %s 复现问题 → 并入修订循环（pipeline §2："
                    "task add revise %s → 写手修订 → commit）" % (ch_id, ch_id))


def cmd_gate_next(proj):
    """机器版编排剧本：按优先级输出下一步该干什么（把「先修账、再评审、再写作」
    的调度纪律从提示词搬进机器）。"""
    recs = []
    prep = Report()
    check_project(proj, prep)
    fails = [n for l, n, _, _ in prep.items if l == "FAIL"]
    if fails:
        recs.append("【修账】check --project 有 FAIL，先修复：%s" % "；".join(fails[:3]))
    cur = proj.cursor()
    last_deep = proj.last_deep_review_ch()
    deep_every = proj.config.get("critic", {}).get("deep_every", 5)
    if cur["last_drafted"] > 0 and cur["last_drafted"] - last_deep >= deep_every:
        recs.append("【深评】逾期（last_deep=%d, last_drafted=%d, deep_every=%d）："
                    "task add review_deep ch_%04d"
                    % (last_deep, cur["last_drafted"], deep_every, cur["last_drafted"]))
    thr = proj.config.get("reconcile_every", 10)
    due = [e for e, v in proj.entities().items()
           if (v["meta"].get("last_event_ch", 0) or 0)
           - (v["meta"].get("last_reconcile_ch", 0) or 0) >= thr]
    if due:
        recs.append("【对账】实体到期 %s：serial-ops §5 对账轮（entity update）"
                    % " ".join(due[:5]))
    # P6-S：spoiler 欠账消费——读者未知事实挂账超龄，顶进调度剧本（workflow §4）
    debt_thr = proj.config.get("spoiler_debt_chapters", 15)
    debts = sorted([x for x, _ in proj.all_facts()
                    if x.get("spoiler") and not x.get("superseded_by")
                    and cur["last_drafted"] - (x.get("revealed_ch") or 0) >= debt_thr],
                   key=lambda x: x.get("revealed_ch") or 0)
    if debts:
        recs.append("【欠账】读者未知 fact %d 条挂账 ≥%d 章（最老 %s，ch%s 埋下）："
                    "knowledge query 盘点后逐条决定 继续吊/reveal 销账/retcon 废止"
                    "（workflow §4）"
                    % (len(debts), debt_thr, debts[0]["id"],
                       debts[0].get("revealed_ch")))
    if proj.config.get("route", "web") == "web" and cur["last_published"] > 0 \
            and proj.buffer_ready() == 0:
        recs.append("【补稿】buffer=0：停发/降频，只跑 write 批（serial-ops §1）")
    q = load_queue_promoted(proj)
    tid = next_task_id(q)
    if tid:
        t = proj.task(tid)
        recs.append("【队列】执行队首 %s：%s(%s) → task start %s"
                    % (tid, t["type"], t["target"], tid))
    else:
        nxt = cur["last_drafted"] + 1
        nid = "ch_%04d" % nxt
        if proj.p("chapters", nid + ".task.json").is_file():
            recs.append("【排批】%s 已有任务卡：task add write %s" % (nid, nid))
        elif any(n["meta"].get("kind") == "arc" and n["meta"].get("status") == "committed"
                 for n in proj.tree_nodes()):
            recs.append("【排批】队列空：从弧计划取料排批 %s（pipeline §1 步骤 0）" % nid)
        else:
            recs.append("【设计】无 committed 弧：开书庭/卷庭/弧规划（court.md §1）")
    print("== gate next（机器版编排剧本）==")
    for i, r in enumerate(recs, 1):
        print("%d. %s" % (i, r))
    print("（依序处置；【修账】未清不得进入写作环）")
    print_stage_hint(proj)
    return 0


def cmd_gate(args):
    proj = Project(find_root(args))
    if args.gate_cmd == "next":
        return cmd_gate_next(proj)
    rep = Report()
    if args.gate_cmd == "write":
        gate_write(proj, args.ch_id, rep)
        return rep.render("gate write %s" % args.ch_id)
    if args.gate_cmd == "approve":
        gate_approve(proj, args.ch_id, rep)
        return rep.render("gate approve %s" % args.ch_id)
    if args.gate_cmd == "publish":
        frm = ch_num(args.ch_from)
        to = ch_num(args.ch_to) if args.ch_to else frm
        probs = publish_problems(proj, frm, to)
        for pr, fix in probs:
            rep.add("FAIL", pr, fix=fix)
        if not probs:
            rep.add("PASS", "publish 前置谓词全过（ch_%04d..ch_%04d 可发布）" % (frm, to))
        return rep.render("gate publish")
    if args.gate_cmd == "checkpoint":
        probs = checkpoint_problems(proj, args.vol_id)
        for pr, fix in probs:
            rep.add("FAIL", pr, fix=fix)
        if not probs:
            rep.add("PASS", "checkpoint 前置谓词全过（%s 可结账）" % args.vol_id)
        return rep.render("gate checkpoint %s" % args.vol_id)
    return 2
