# -*- coding: utf-8 -*-
"""serial_ops — 连载运营：publish / retcon / report volume / checkpoint。"""
import json
import re

from .common import (NOW, RETCON_STRATEGIES, THREAD_LIVE, Report, ch_num, die,
                     dump_frontmatter, get_section, git_autocommit, instantiate,
                     parse_frontmatter, read, replace_section, write)
from .checks import check_window
from .project import Project, find_root
from .stagectl import stage_guard


def publish_problems(proj, frm, to):
    """publish 前置谓词（P3 gate 复用：只判不写）。返回 [(问题, 下一步)]（空 = 可发布）。"""
    probs = []
    cur = proj.cursor()
    if frm != cur["last_published"] + 1:
        probs.append(("连续性谓词失败：应从 ch_%04d 起（当前 last_published=%d），无绕过开关"
                      % (cur["last_published"] + 1, cur["last_published"]),
                      "改区间重试：novel.py publish ch_%04d [ch_to]"
                      % (cur["last_published"] + 1)))
    chs = {ch_num(c["id"]): c for c in proj.chapters()}
    not_ok = [n for n in range(frm, to + 1)
              if n not in chs or chs[n]["meta"].get("status") != "approved"]
    if not_ok:
        probs.append(("区间含非 approved 章：%s" % ["ch_%04d" % n for n in not_ok],
                      "逐章 novel.py gate approve ch_NNNN（FAIL 项自带下一步：评审→"
                      "review add→tree set-status approved），或缩小发布区间"))
    if cur["last_published"] == 0:
        need = proj.config.get("buffer", {}).get("min_before_publish", 1)
        if proj.buffer_ready() < need:
            probs.append(("首发前 ready=%d < min_before_publish=%d"
                          % (proj.buffer_ready(), need),
                          "先攒稿到位：推进 write 批至 approved（serial-ops §1 水位表）"))
    return probs


def cmd_publish(args):
    proj = Project(find_root(args))
    stage_guard(proj, ("ops",), "publish")
    frm = ch_num(args.ch_from)
    to = ch_num(args.ch_to) if args.ch_to else frm
    probs = publish_problems(proj, frm, to)
    if probs:
        die("\n".join("%s\n  ↳ 下一步：%s" % pr for pr in probs), 1)
    chs = {ch_num(c["id"]): c for c in proj.chapters()}
    for n in range(frm, to + 1):
        c = chs[n]
        c["meta"]["status"] = "published"
        c["meta"]["updated_at"] = NOW()
        write(c["path"], dump_frontmatter(c["meta"]) + "\n" + c["body"].lstrip("\n"))
    git_autocommit(proj.root, "[publish] ch_%04d..ch_%04d" % (frm, to))
    print("已发布 ch_%04d..ch_%04d；发布后 buffer ready=%d" % (frm, to, proj.buffer_ready()))
    return 0


def cmd_retcon(args):
    """P0-4：retcon CLI 化（serial-ops §3）。旧 fact 填 superseded_by，retcons[] 追加。"""
    proj = Project(find_root(args))
    stage_guard(proj, ("ops",), "retcon")
    if args.strategy not in RETCON_STRATEGIES:
        die("strategy 须为 %s" % "|".join(RETCON_STRATEGIES))
    # 定位旧 fact
    hit_file, hit_data, hit_fact = None, None, None
    for f in proj.facts_files():
        data = json.loads(read(f))
        for x in data.get("facts", []):
            if x.get("id") == args.old_fact_id:
                hit_file, hit_data, hit_fact = f, data, x
                break
        if hit_fact:
            break
    if not hit_fact:
        die("old_fact 不存在：%s（ledgers/facts/*.json 均未命中）" % args.old_fact_id, 1)
    if hit_fact.get("superseded_by"):
        die("%s 已被 %s 覆盖，不可重复 retcon（如需再改，对新事实登记新 fact 后 retcon）"
            % (args.old_fact_id, hit_fact["superseded_by"]), 1)
    # decision 必须真实存在
    dec_hits = [p for p in proj.p("court").glob("dec_*.md")
                if p.stem == args.decision or p.stem.startswith(args.decision)]
    if not dec_hits:
        die("decision 不存在：court/%s*.md（先写裁决记录，serial-ops §3 步骤 1）"
            % args.decision, 1)
    # 分配 ret id（本文件内递增）
    seq = 0
    for r in hit_data.get("retcons", []):
        m = re.match(r"^ret_(\d{3,})$", str(r.get("id", "")))
        if m:
            seq = max(seq, int(m.group(1)))
    rid = "ret_%03d" % (seq + 1)
    entity_ids = args.entity or hit_fact.get("entity_ids", [])
    hit_data.setdefault("retcons", []).append({
        "id": rid, "entity_ids": entity_ids,
        "old_fact_id": args.old_fact_id, "new_fact": args.new,
        "strategy": args.strategy, "decision_ref": dec_hits[0].stem,
    })
    hit_fact["superseded_by"] = rid
    write(hit_file, json.dumps(hit_data, ensure_ascii=False, indent=1))
    git_autocommit(proj.root, "[retcon] %s → %s（%s，%s）"
                   % (args.old_fact_id, rid, args.strategy, dec_hits[0].stem))
    print("retcon 已登记：%s 覆盖 %s（策略 %s，裁决 %s）→ %s"
          % (rid, args.old_fact_id, args.strategy, dec_hits[0].stem,
             hit_file.relative_to(proj.root)))
    if args.strategy == "explicit_fix":
        print("[提醒] explicit_fix：在最近一次排批的 task.json beats 排入「文内圆回」拍"
              "（serial-ops §3）")
    print("此后简报 §6 命中该实体将自动连带 retcon 条目；跑 check --project 复核引用链")
    return 0


def volume_chapters(proj, vol_id):
    return [c for c in proj.chapters() if proj.vol_of_chapter(c["id"]) == vol_id]


def cmd_report(args):
    """P0-4：卷报告汇编（serial-ops §4 步骤 1 的机械部分）。
    产出 state/reports/vol_NN.md；exports 行预标 [待对账]，编排者改三态后跑 checkpoint。"""
    proj = Project(find_root(args))
    stage_guard(proj, ("ops",), "report volume")
    vol_id = args.vol_id
    vp = proj.node_path(vol_id)
    if not vp or not vp.is_file():
        die("卷不存在：%s" % vol_id, 1)
    vmeta, vbody = parse_frontmatter(read(vp))
    chs = volume_chapters(proj, vol_id)
    ch_nums = sorted(ch_num(c["id"]) for c in chs)
    by_st = {}
    for c in chs:
        by_st[c["meta"].get("status", "?")] = by_st.get(c["meta"].get("status", "?"), 0) + 1
    words = sum(c["meta"].get("word_count") or 0 for c in chs)

    lines = ["# 卷报告 %s（novel.py report volume 生成）" % vol_id,
             "",
             "- 生成于 %s ｜ 卷状态 %s ｜ 章 %d 篇（%s）｜ 字数合计 %d"
             % (NOW(), vmeta.get("status"),
                len(chs), " ".join("%s×%d" % kv for kv in sorted(by_st.items())), words),
             "- 本文件唯一可编辑处：exports 对账行的三态标注（checkpoint 机检）；其余为生成物",
             "",
             "## exports 对账（把 [待对账] 改为 [兑现 ch_NNNN] | [移交] | [废止 dec_xxx]）",
             ""]
    exports = get_section(vbody, "exports") or ""
    exp_rows = [l.strip()[2:].strip() for l in exports.splitlines()
                if l.strip().startswith("- ") and not l.strip().startswith("- [交付项")]
    if exp_rows:
        lines += ["- [待对账] %s" % r for r in exp_rows]
    else:
        lines.append("- （卷蓝图 exports 节为空——若确无交付项，本节视为已对账）")
    lines += ["", "## 线索健康", ""]
    for tid, t in proj.threads().items():
        m = t["meta"]
        log = get_section(t["body"], "推进日志") or ""
        touched = [int(x.group(1)) for x in re.finditer(r"ch_(\d{4})", log)]
        lines.append("- %s [%s/%s] plant_ch=%s last_touch=%s must_not_drop=%s payoff_planned=%s"
                     % (tid, m.get("thread_kind"), m.get("state"), m.get("plant_ch"),
                        ("ch_%04d" % max(touched)) if touched else "（无）",
                        m.get("must_not_drop"), m.get("payoff_planned")))
    if not proj.threads():
        lines.append("- （无线索）")
    lines += ["", "## payoff 统计（本卷章区间）", ""]
    rows = [r for r in proj.payoff_rows()
            if re.match(r"^ch_\d{4}$", r["chapter"]) and ch_num(r["chapter"]) in set(ch_nums)]
    kinds = {}
    for r in rows:
        if r["realized"]:
            kinds[r["kind"]] = kinds.get(r["kind"], 0) + 1
    lines.append("- 配额 %d ｜ 已兑现 %d（%s）"
                 % (len(rows), sum(1 for r in rows if r["realized"]),
                    " ".join("%s×%d" % kv for kv in sorted(kinds.items())) or "无"))
    lines += ["", "## 战力变化（ledgers/power.tsv 本卷段）", ""]
    prow = [r for r in proj.power_rows()
            if re.match(r"^ch_\d{4}$", r["chapter"]) and ch_num(r["chapter"]) in set(ch_nums)]
    lines += ["- %s %s：%s → %s %s" % (r["chapter"], r["entity"], r["from"], r["to"],
                                        r["note"]) for r in prow] or ["- （无记录）"]
    lines += ["", "## 窗口告警（check --window 快照）", ""]
    wrep = Report()
    check_window(proj, wrep)
    warn = ["- [%s] %s" % (l, n) for l, n, _, _ in wrep.items if l in ("WARN", "FAIL")]
    lines += warn or ["- （全绿）"]
    lines += ["", "## checkpoint 前置清单", "",
              "- [ ] exports 全部标注三态（移交项将预填下卷 imports）",
              "- [ ] ledgers/recap.md 已追加本卷段落（P1-1；brief §2 注入）",
              "- [ ] 卷级深评已落盘 reviews/（serial-ops §4 步骤 3）",
              "- [ ] 废止项已写 dec_NNN（reopen_requires 防幽灵承诺复活）"]
    out = proj.p("state", "reports", vol_id + ".md")
    write(out, "\n".join(lines) + "\n")
    print("\n".join(lines))
    print("\n卷报告已写入：%s" % out.relative_to(proj.root))
    return 0


def checkpoint_problems(proj, vol_id):
    """checkpoint 前置谓词（P3 gate 复用：只判不写）。返回 [(问题, 下一步)]（空 = 可结账）。"""
    probs = []
    vp = proj.node_path(vol_id)
    if not vp or not vp.is_file():
        return [("卷不存在：%s" % vol_id,
                 "novel.py tree add volume %s → 卷庭定稿（court.md §1）" % vol_id)]
    vmeta, _ = parse_frontmatter(read(vp))
    if vmeta.get("status") != "committed":
        probs.append(("卷 %s 状态为 %s，须 committed 才可 checkpoint"
                      % (vol_id, vmeta.get("status")),
                      "卷庭定稿：novel.py task add design %s → commit <t> --file <卷蓝图>"
                      % vol_id))
    rp = proj.p("state", "reports", vol_id + ".md")
    if not rp.is_file():
        probs.append(("卷报告未汇编", "novel.py report volume %s（serial-ops §4 步骤 1）"
                      % vol_id))
    else:
        pending = [l.strip() for l in read(rp).splitlines() if "[待对账]" in l]
        if pending:
            probs.append(("exports 对账未完成，%d 条仍为 [待对账]：\n  %s"
                          % (len(pending), "\n  ".join(pending[:5])),
                          "编辑 %s 逐条标三态 [兑现 ch_NNNN]|[移交]|[废止 dec_xxx]"
                          "（serial-ops §4 步骤 2）" % rp.relative_to(proj.root)))
    bad = [c["id"] for c in volume_chapters(proj, vol_id)
           if c["meta"].get("status") in ("planned", "drafted", "stale")]
    if bad:
        probs.append(("卷内存在未完稿章（须 approved/published/archived）：%s" % " ".join(bad),
                      "逐章收尾：gate approve → set-status approved（不再写的章 "
                      "tree set-status <ch> archived）"))
    return probs


def cmd_checkpoint(args):
    """P0-4：卷末结账（formats §16 checkpoint 行）。
    校验：报告存在 + exports 三态齐 + 卷内无未完稿章；动作：卷标记 + 下卷 imports 预填。"""
    proj = Project(find_root(args))
    stage_guard(proj, ("ops",), "checkpoint")
    vol_id = args.vol_id
    m0 = re.match(r"^vol_(\d{2})$", vol_id)
    if not m0:
        die("卷 id 应为 vol_NN")
    probs = checkpoint_problems(proj, vol_id)
    if probs:
        die("\n".join("%s\n  ↳ 下一步：%s" % pr for pr in probs), 1)
    vp = proj.node_path(vol_id)
    vmeta, vbody = parse_frontmatter(read(vp))
    rp = proj.p("state", "reports", vol_id + ".md")
    rtext = read(rp)

    # 卷归档标记
    vmeta["checkpoint_at"] = NOW()
    vmeta["updated_at"] = NOW()
    write(vp, dump_frontmatter(vmeta) + "\n" + vbody.lstrip("\n"))

    # 下卷 imports 预填
    next_vol = "vol_%02d" % (int(m0.group(1)) + 1)
    nvp = proj.p("tree", next_vol, "volume.md")
    handover = [l.strip()[2:].strip() for l in rtext.splitlines()
                if l.strip().startswith("- [移交")]
    for tid, t in proj.threads().items():
        m = t["meta"]
        if m.get("must_not_drop") and m.get("state") in THREAD_LIVE:
            handover.append("[未收线] %s [%s/%s] payoff_planned=%s"
                            % (tid, m.get("thread_kind"), m.get("state"),
                               m.get("payoff_planned")))
    chs = volume_chapters(proj, vol_id)
    if chs:
        last_ch = max(chs, key=lambda c: ch_num(c["id"]))
        mj = proj.chapter_meta_json(last_ch["id"]) or {}
        if mj.get("summary_after"):
            handover.append("[上卷终章 %s] %s" % (last_ch["id"], mj["summary_after"]))
    imports_body = "\n".join("- %s" % h for h in handover) or "- （上卷无移交项）"
    imports_body = ("[novel.py checkpoint %s 预填于 %s；卷庭逐条确认后定稿]\n\n"
                    % (vol_id, NOW())) + imports_body
    if nvp.is_file():
        nmeta, nbody = parse_frontmatter(read(nvp))
        write(nvp, dump_frontmatter(nmeta) + "\n" + replace_section(nbody, "imports",
                                                                    imports_body))
    else:
        text = instantiate("volume.md", {"[vol_01]": next_vol,
                                         "[YYYY-MM-DDTHH:MM:SSZ]": NOW()})
        nmeta, nbody = parse_frontmatter(text)
        write(nvp, dump_frontmatter(nmeta) + "\n" + replace_section(nbody, "imports",
                                                                    imports_body))
        print("下卷骨架已实例化：tree/%s/volume.md（status=empty，卷庭定稿）" % next_vol)
    git_autocommit(proj.root, "[checkpoint] %s 结账；%s imports 预填" % (vol_id, next_vol))

    apr = proj.config.get("approvals", {}).get("checkpoint", True)
    if apr and not proj.config.get("unattended"):
        print("[审批] approvals.checkpoint=true：向用户呈报卷报告+三态对账+深评要点"
              "（formats §19）")
    print("checkpoint 完成：%s 已标记（checkpoint_at），%s imports 已预填" % (vol_id, next_vol))
    print("[提醒] 更新 ledgers/recap.md 本卷段落（P1-1）；开卷庭：task add design %s"
          % next_vol)
    return 0
