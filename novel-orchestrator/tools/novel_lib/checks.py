# -*- coding: utf-8 -*-
"""checks — 断言集：check --unit/--leak/--window/--project（含黑名单/日历/指纹）。"""
import json
import re
from pathlib import Path

from .common import (BIG_PAYOFF_KINDS, CH_STATUS, DEC_KEYS, DEC_SECTIONS,
                     DEC_SESSIONS, META_KEYS, NODE_KINDS, NODE_STATUS,
                     REQUIRED_SECTIONS, REVIEW_DEPTHS, REVIEW_KEYS,
                     REVIEW_VERDICTS, THREAD_KINDS, THREAD_LIVE, THREAD_OPS,
                     THREAD_STATES, UNIT_NEEDS_REVIEW, Report, cache_fps,
                     ch_num, char_ngrams, cjk_len, die, get_section, ngram_sim,
                     parse_elapsed_days, parse_frontmatter, parse_story_date,
                     read, sentences_of, split_sections, thread_effective_state,
                     thread_next_state)
from .extract import extract_reconcile
from .project import Project, find_root


# ---------------------------------------------------------------- 黑名单解析
def expand_slash(s):
    """'A/B' 交替展开。二选一且后者更长时视为共尾（眼底/眼中闪过一丝 →
    眼底闪过一丝 + 眼中闪过一丝），否则按独立候选拆分。"""
    s = s.strip()
    if "/" not in s:
        return [s] if s else []
    parts = [p.strip() for p in s.split("/") if p.strip()]
    if len(parts) == 2 and len(parts[1]) > len(parts[0]):
        a, b = parts
        return [a + b[len(a):], b]
    return parts


def entry_patterns(spec):
    """把黑名单条目展开为若干可直接子串匹配的候选（递归展开全角括号组）。"""
    spec = spec.strip()
    m = re.search(r"（([^）]*)）", spec)
    if not m:
        return expand_slash(spec)
    inner = m.group(1)
    prefix, suffix = spec[:m.start()], spec[m.end():]
    if "……" in inner or not inner.strip():
        return entry_patterns(prefix + suffix)
    out = []
    for alt in [a.strip() for a in inner.split("/") if a.strip()]:
        out.extend(entry_patterns(prefix + alt + suffix))
    if len(prefix.strip()) >= 5 and not suffix.strip():
        out.extend(expand_slash(prefix.strip()))
    return out


def parse_taboo_entries(style_body):
    """从 style.md 禁忌节解析黑名单。返回 (全局条目, 末段条目, needs_review 文本条目)。
    条目 = (原文, [替代匹配串], 次数阈值 or None)"""
    sec = get_section(style_body, "口癖与句式禁忌") or ""
    global_e, ending_e, review_e = [], [], []
    bucket = global_e
    for ln in sec.splitlines():
        if "末段总结化" in ln:
            bucket = ending_e
            continue
        if not ln.strip().startswith("- "):
            continue
        entry = ln.strip()[2:].strip()
        raw = entry
        threshold = None
        if "——" in entry:
            spec, rule = entry.split("——", 1)
            m = re.search(r">\s*(\d+)\s*次", rule)
            if m:
                threshold = int(m.group(1))
            entry = spec.strip()
        if entry.startswith("句式级") or "：" in entry:
            review_e.append(raw)
            continue
        pats = entry_patterns(entry)
        if pats:
            bucket.append((raw, pats, threshold))
    return global_e, ending_e, review_e


# ---------------------------------------------------------------- writeback 校验
def writeback_ref_errors(proj, ch_id, wb):
    """P0-3/P2-3 越权机检：writeback 引用的实体/线索必须已登记，线索迁移必须合法。
    返回 FAIL 级错误列表（空 = 合法）。"""
    errs = []
    ents = proj.entities()
    threads = proj.threads()

    def resolve(ref):
        eid = proj.resolve_entity(ref)
        return eid if eid in ents else None

    for i, d in enumerate(wb.get("continuity_delta", []) or []):
        for k in ("fact", "entity_ids", "spoiler"):
            if k not in d:
                errs.append("continuity_delta[%d] 缺 %s（P0-1：spoiler 字段必填）" % (i, k))
        for ref in d.get("entity_ids", []):
            if not resolve(ref):
                errs.append("continuity_delta[%d] 实体「%s」未登记"
                            "（entities/aliases 均无；先 entity new 或补别名）" % (i, ref))
        for ref in d.get("known_by", []) or []:
            if not resolve(ref):
                errs.append("continuity_delta[%d] known_by「%s」未登记"
                            "（知情人必须是已登记实体；先 entity new 或补别名）" % (i, ref))
    for ref in wb.get("cast_actual", []) or []:
        if not resolve(ref):
            errs.append("cast_actual「%s」未登记（写手越权发明实体，或排批缺卡）" % ref)
    sim_state = {}
    for i, op in enumerate(wb.get("thread_ops", []) or []):
        tid = op.get("id")
        if tid not in threads:
            errs.append("thread_ops[%d] 线索「%s」未登记（先 thread new）" % (i, tid))
            continue
        if op.get("op") not in THREAD_OPS:
            errs.append("thread_ops[%d] 非法 op「%s」（枚举 %s）"
                        % (i, op.get("op"), "|".join(THREAD_OPS)))
            continue
        # P0-1：模拟起点 = 剔除本章既往贡献后的重放态（revise 重提交不再被自己的
        # 上一轮 op 卡死，如 payoff 后重提 payoff）
        st = sim_state.get(tid, thread_effective_state(threads[tid], exclude_ch=ch_id))
        nxt = thread_next_state(st, op["op"])
        if nxt is None:
            errs.append("thread_ops[%d] %s：%s 态不可 %s（合法迁移表 formats §8；"
                        "终态线复活需 decision + 新线）" % (i, tid, st, op["op"]))
        else:
            sim_state[tid] = nxt
    for i, d in enumerate(wb.get("power_delta", []) or []):
        if not d.get("to"):
            errs.append("power_delta[%d] 缺 to（迁移后位阶必填）" % i)
        for ref in d.get("entity_ids", []) or []:
            if not resolve(ref):
                errs.append("power_delta[%d] 实体「%s」未登记" % (i, ref))
    return errs


def facts_conflict_scan(proj, num, wb, rep):
    """P0-1：新事实 vs 既有 facts 的同实体冲突扫描（机器只出候选，评审裁定）。"""
    facts = [x for x, _ in proj.all_facts()]
    if not facts:
        return
    conflicts, dups = [], []
    for d in wb.get("continuity_delta", []) or []:
        eids = {proj.resolve_entity(r) for r in d.get("entity_ids", [])} - {None}
        new_fact = d.get("fact", "")
        for x in facts:
            if x.get("superseded_by"):
                continue
            if not (set(x.get("entity_ids", [])) & eids):
                continue
            if x.get("fact") == new_fact:
                if x.get("revealed_ch") != num:
                    dups.append("「%s」已于 ch%s 揭示（%s）"
                                % (new_fact, x.get("revealed_ch"), x.get("id")))
                continue
            if d.get("key") and x.get("key") and d["key"] == x["key"]:
                conflicts.append("同实体同键「%s」：新「%s」 vs %s「%s」（ch%s）"
                                 % (d["key"], new_fact, x.get("id"),
                                    x.get("fact"), x.get("revealed_ch")))
            elif ngram_sim(new_fact, x.get("fact", "")) >= 0.45:
                conflicts.append("高相似疑似矛盾：新「%s」 vs %s「%s」（ch%s）"
                                 % (new_fact, x.get("id"), x.get("fact"),
                                    x.get("revealed_ch")))
    if conflicts:
        rep.add("NEEDS_REVIEW", "facts 冲突候选（同实体矛盾须评审裁定：改稿或走 retcon）",
                conflicts)
    if dups:
        rep.add("WARN", "facts 重复登记候选（同文已在其他章揭示）", dups)


# ---------------------------------------------------------------- check --unit
def check_unit(proj, ch_id, candidate=None, writeback=None, rep=None):
    rep = rep or Report()
    num = ch_num(ch_id)
    # 取正文
    if candidate:
        meta, body = parse_frontmatter(read(candidate))
        src = candidate
    else:
        p = proj.p("chapters", ch_id + ".md")
        if not p.is_file():
            rep.add("FAIL", "章文件不存在：%s" % ch_id)
            return rep
        meta, body = parse_frontmatter(read(p))
        src = str(p)
    if meta is None:
        rep.add("FAIL", "信封缺失/不可解析：%s" % src)
        return rep
    if meta.get("kind") != "chapter":
        rep.add("FAIL", "kind 应为 chapter，实为 %s" % meta.get("kind"))
    text = body.split("## 正文", 1)[-1] if "## 正文" in body else body
    n_chars = cjk_len(text)

    # 字数带（任务卡覆盖 config）
    wt = proj.config.get("word_target", [2000, 4500])
    task0 = proj.chapter_task(ch_id)
    if task0 and isinstance(task0.get("word_target"), list) \
            and len(task0["word_target"]) == 2 \
            and all(isinstance(x, int) for x in task0["word_target"]):
        wt = task0["word_target"]
    lo, hi = int(wt[0] * 0.85), int(wt[1] * 1.15)
    if lo <= n_chars <= hi:
        rep.add("PASS", "字数 %d ∈ [%d,%d]" % (n_chars, lo, hi))
    else:
        rep.add("FAIL", "字数 %d 超出 word_target±15%% [%d,%d]" % (n_chars, lo, hi))

    # 黑名单
    style_p = proj.p("tree", "style.md")
    if style_p.is_file():
        _, sbody = parse_frontmatter(read(style_p))
        g, e, rv = parse_taboo_entries(sbody)
        hits = []
        for raw, pats, threshold in g:
            cnt = sum(text.count(p) for p in pats)
            if threshold is not None:
                if cnt > threshold:
                    hits.append("「%s」共 %d 次（阈值 %d）" % (raw, cnt, threshold))
            elif cnt:
                hits.append("「%s」×%d" % (pats[0], cnt))
        if hits:
            rep.add("FAIL", "style 禁忌命中（命中即违规，改写后重检）", hits)
        else:
            rep.add("PASS", "style 禁忌零命中")
        paras = [l.strip() for l in text.splitlines() if l.strip()]
        last_para = paras[-1] if paras else ""
        end_hits = []
        for raw, pats, _ in e:
            for p in pats:
                if p in last_para:
                    end_hits.append("「%s」" % p)
        if end_hits:
            rep.add("FAIL", "末段总结化句式命中", end_hits)
        else:
            rep.add("PASS", "末段无总结腔")
        if rv:
            rep.add("NEEDS_REVIEW", "句式级禁忌条目须评审抽查", rv)
    else:
        rep.add("WARN", "tree/style.md 缺失，跳过黑名单")

    # 连续 3 句同首
    sents = sentences_of(text)
    runs = []
    for i in range(len(sents) - 2):
        heads = {s[:2] for s in sents[i:i + 3]}
        if len(heads) == 1:
            runs.append("…%s…（%s）" % (sents[i][:12], sents[i][:2]))
    if runs:
        rep.add("FAIL", "连续 3 句同首词", sorted(set(runs))[:10])
    else:
        rep.add("PASS", "无连续 3 句同首")

    # 连续 3 段同首（段首重复）
    paras = [l.strip() for l in text.splitlines() if l.strip()]
    pruns = []
    for i in range(len(paras) - 2):
        if len({p[:2] for p in paras[i:i + 3]}) == 1:
            pruns.append(paras[i][:10])
    if pruns:
        rep.add("WARN", "连续 3 段同首（段首重复）", sorted(set(pruns))[:5])

    # 章内 4-gram 重复率
    grams = char_ngrams(text, 4)
    if grams:
        rate = 1 - len(set(grams)) / len(grams)
        if rate > 0.02:
            rep.add("WARN", "章内 4-gram 重复率 %.1f%% > 2%%" % (rate * 100))
        else:
            rep.add("PASS", "章内 4-gram 重复率 %.1f%%" % (rate * 100))

    # 跨章两级指纹：12-gram 精确（套话/自我复读）+ 8-gram 重合率（撞梗嫌疑）
    cache = proj.ngram_cache()
    cand12 = set(char_ngrams(text, 12))
    cand8 = set(char_ngrams(text, 8))
    dup, motif = [], []
    for cid, entry in cache.items():
        if cid == ch_id:
            continue
        inter = cand12 & cache_fps(entry, "n12")
        for s in list(inter)[:3]:
            dup.append("与 %s 重复：「%s…」" % (cid, s))
        fp8 = cache_fps(entry, "n8")
        if cand8 and fp8:
            ratio = len(cand8 & fp8) / len(cand8)
            if ratio > 0.06:
                motif.append("与 %s 的 8-gram 重合率 %.1f%% > 6%%" % (cid, ratio * 100))
    if dup:
        rep.add("WARN", "跨章 12 字级重复（自我复读/套话嫌疑）", dup[:10])
    else:
        rep.add("PASS", "跨章 12-gram 零重复")
    if motif:
        rep.add("WARN", "跨章 8-gram 重合偏高（撞梗/桥段自我复用嫌疑，深评抽查）", motif[:5])

    # writeback / meta.json
    wb = None
    if writeback:
        wb = json.loads(read(writeback))
    else:
        wb = proj.chapter_meta_json(ch_id)
    if wb is None:
        rep.add("FAIL", "缺 writeback/meta.json（回写契约见简报 §8）")
    else:
        missing = [k for k in META_KEYS if k not in wb]
        if missing:
            rep.add("FAIL", "writeback 缺键", missing)
        else:
            rep.add("PASS", "writeback schema 齐全")
        # P0-3/P2-3：越权引用与线索迁移合法性（FAIL 级，阻断 commit）
        ref_errs = writeback_ref_errors(proj, ch_id, wb)
        if ref_errs:
            rep.add("FAIL", "writeback 引用越权/迁移非法（不存在实体/线索一律拒绝落盘）",
                    ref_errs)
        else:
            rep.add("PASS", "writeback 实体/线索引用全部可解析，线索迁移合法")
        # P0-1：facts 冲突扫描
        facts_conflict_scan(proj, num, wb, rep)
        route = proj.config.get("route", "web")
        close_ok = bool(wb.get("hooks_realized", {}).get("close"))
        if not close_ok:
            if route != "web":
                rep.add("WARN", "hooks_realized.close=false（traditional 建议级，须在 issues 说明 turn）")
            elif wb.get("issues"):
                rep.add("WARN", "hooks_realized.close=false，但 issues 已说明（人工裁定）")
            else:
                rep.add("FAIL", "route=web 章尾钩必须落实（close=false 且 issues 未说明）")
        task = proj.chapter_task(ch_id)
        if task:
            quota_n = len(task.get("payoff_quota", []))
            bad = []
            for pid in wb.get("payoff_realized", []):
                m = re.match(r"^payoff_(\d{4})_(\d+)$", pid)
                if not m:
                    bad.append("%s（格式应为 payoff_章号_序）" % pid)
                elif int(m.group(1)) != num:
                    bad.append("%s（章号 %s ≠ 本章 %04d）" % (pid, m.group(1), num))
                elif int(m.group(2)) > max(quota_n, 0):
                    bad.append("%s（序 %s 超 quota=%d）" % (pid, m.group(2), quota_n))
            if bad:
                rep.add("FAIL", "payoff_realized 越界/格式错（⊆ quota，id=payoff_章号_序）", bad)
        wc = wb.get("word_count", 0)
        if isinstance(wc, int) and wc and abs(wc - n_chars) > max(50, n_chars * 0.1):
            rep.add("WARN", "writeback.word_count=%d 与实测 %d 偏差 >10%%" % (wc, n_chars))
        # P2-1：抽取器对账（双记账机器半边——文本实测 vs 写手自报）
        extract_reconcile(proj, ch_id, text, wb, rep)

    for item in UNIT_NEEDS_REVIEW:
        rep.add("NEEDS_REVIEW", item)
    return rep


# ---------------------------------------------------------------- check --leak
def check_leak(proj, candidate, brief_path, rep=None):
    """P0-3 后半：简报外已登记专名扫描（机器可判部分）。
    未登记的新发明专名机器无法枚举 → NEEDS_REVIEW 交轻评。"""
    rep = rep or Report()
    if not Path(candidate).is_file():
        rep.add("FAIL", "候选文件不存在：%s" % candidate)
        return rep
    if not Path(brief_path).is_file():
        rep.add("FAIL", "简报文件不存在：%s" % brief_path)
        return rep
    _, body = parse_frontmatter(read(candidate))
    text = body.split("## 正文", 1)[-1] if "## 正文" in body else body
    brief = read(brief_path)
    names = {}
    for alias, eid in proj.aliases().items():
        names[str(alias)] = eid
    for eid, e in proj.entities().items():
        for a in e["meta"].get("aliases") or []:
            names[str(a)] = eid
    leaks = []
    scanned = 0
    for name, eid in sorted(names.items()):
        if len(name) < 2 or name.startswith("["):
            continue
        scanned += 1
        if name in text and name not in brief:
            leaks.append("「%s」（%s）出现在正文但简报未投递" % (name, eid))
    if leaks:
        rep.add("FAIL", "简报外已登记专名泄漏（信息沙箱违规，pipeline §5：产物作废重 spawn）",
                leaks)
    else:
        rep.add("PASS", "已登记专名零泄漏（扫描 %d 个别名）" % scanned)
    rep.add("NEEDS_REVIEW",
            "新发明专名/设定无法机械枚举——轻评按 pipeline §5 对照简报人工抽查")
    return rep


# ---------------------------------------------------------------- check --window
def check_window(proj, rep=None, since=None):
    rep = rep or Report()
    since_n = ch_num(since) if since else 0
    chs = {ch_num(c["id"]): c for c in proj.chapters()
           if c["meta"].get("status") in ("drafted", "approved", "published")
           and ch_num(c["id"]) >= since_n}
    if not chs:
        rep.add("SKIP", "无成稿章（或 --since 截断后为空），窗口检查跳过")
        return rep
    nums = sorted(chs)
    rows = proj.payoff_rows()
    realized = {}
    big = {}
    for r in rows:
        if r["realized"]:
            n = ch_num(r["chapter"])
            realized[n] = realized.get(n, 0) + 1
            if r["kind"] in BIG_PAYOFF_KINDS:
                big[n] = big.get(n, 0) + 1

    # route=traditional 时窗口纪律降级为建议（modes/route-traditional.md §3）
    win_level = "FAIL" if proj.config.get("route", "web") == "web" else "WARN"
    v3 = []
    for i in nums:
        win = [i, i + 1, i + 2]
        if all(n in chs for n in win):
            if not any(realized.get(n) for n in win):
                v3.append("ch%04d–ch%04d 零已兑现爽点" % (i, i + 2))
    if v3:
        rep.add(win_level, "3 章小爽窗口破（rubrics/payoff.md §二）", v3)
    else:
        rep.add("PASS", "3 章小爽窗口全绿（%d 章）" % len(nums))

    v10 = []
    for i in nums:
        win = list(range(i, i + 10))
        if all(n in chs for n in win):
            if not any(big.get(n) for n in win):
                v10.append("ch%04d–ch%04d 无处境级释放（upgrade/reveal/reversal）" % (i, i + 9))
    if v10:
        rep.add(win_level, "10 章大爽窗口破", v10[:5])
    elif len(nums) >= 10:
        rep.add("PASS", "10 章大爽窗口全绿")
    else:
        rep.add("SKIP", "成稿 <10 章，跳过大爽窗口")

    # promise 余额
    threads = proj.threads()
    promises = [t for t in threads.values()
                if t["meta"].get("thread_kind") == "promise"
                and t["meta"].get("state") in THREAD_LIVE]
    bal = len(promises)
    if len(nums) >= 5:
        if 2 <= bal <= 5:
            rep.add("PASS", "promise 余额 %d ∈ [2,5]" % bal)
        else:
            rep.add("WARN", "promise 余额 %d ∉ [2,5]（期待账户失衡，rubrics/payoff.md §四）" % bal)
    else:
        rep.add("SKIP", "成稿 <5 章，promise 余额仅报告：%d" % bal)

    # promise >15 章无推进
    cur = max(nums)
    stale = []
    for tid, t in threads.items():
        if t["meta"].get("state") not in ("planted", "active", "tangled"):
            continue
        log = get_section(t["body"], "推进日志") or ""
        touched = [int(m.group(1)) for m in re.finditer(r"ch_(\d{4})", log)]
        last = max(touched) if touched else (t["meta"].get("plant_ch") or 0)
        if last and cur - last > 15:
            stale.append("%s 已 %d 章无推进" % (tid, cur - last))
    if stale:
        rep.add("WARN", "线索悬置 >15 章（转对账，防死线）", stale)
    else:
        rep.add("PASS", "无 >15 章悬置线索")

    # P1-6：战力窗口告警（近 10 章同实体 ≥3 次位阶变动 = 升级过快候选）
    power = proj.power_rows()
    if power:
        recent = {}
        for r in power:
            n = ch_num(r["chapter"]) if re.match(r"^ch_\d{4}$", r["chapter"]) else 0
            if cur - 9 <= n <= cur:
                recent[r["entity"]] = recent.get(r["entity"], 0) + 1
        fast = ["%s 近 10 章 %d 次位阶变动（rubrics/power.md §二：默认 ≤1 大阶/卷）"
                % (e, c) for e, c in recent.items() if c >= 3]
        if fast:
            rep.add("WARN", "战力升级过快候选（设定审计按 power 卡核预算）", fast)
        else:
            rep.add("PASS", "战力变动节奏无告警（台账 %d 行）" % len(power))

    # 时间线（P0-1 rev 去重读 + P2-2 故事日历：数值化 elapsed 与 story_date 单调断言）
    trows = sorted(proj.timeline_rows(),
                   key=lambda r: ch_num(r["chapter"])
                   if re.match(r"^ch_\d{4}$", r["chapter"]) else 0)
    neg = ["%s elapsed=%s" % (r["chapter"], r["elapsed"])
           for r in trows if r["elapsed"].startswith("-")]
    if neg:
        rep.add("FAIL", "时间线出现负 elapsed", neg)
    else:
        rep.add("PASS", "时间线 elapsed 非负")
    if trows:
        unparsed, total_days = [], 0.0
        for r in trows:
            d = parse_elapsed_days(r["elapsed"])
            if d is None:
                unparsed.append("%s elapsed=「%s」" % (r["chapter"], r["elapsed"]))
            else:
                total_days += d
        dated = [(r["chapter"], parse_story_date(r["story_date"]), r["story_date"])
                 for r in trows if parse_story_date(r["story_date"])]
        regress = ["%s %s < %s %s" % (c2, s2, c1, s1)
                   for (c1, d1, s1), (c2, d2, s2) in zip(dated, dated[1:]) if d2 < d1]
        if regress:
            rep.add("FAIL", "故事日历：story_date 倒流（时间线断言违例）", regress)
        if unparsed:
            rep.add("WARN", "故事日历：elapsed 不可数值化（游离于日历外，"
                            "写法见 formats §9：如「2天」「一晚」「3个月」）",
                    unparsed[:8])
        if not regress:
            rep.add("PASS", "故事日历：累计 ≈%.1f 天（%d 章；story_date 断言 %d 条单调）"
                    % (total_days, len(trows), len(dated)))

    # buffer 一致性
    ready = proj.buffer_ready()
    target = proj.config.get("buffer", {}).get("target", 3)
    if proj.config.get("route", "web") == "web" and proj.cursor()["last_published"] > 0 \
            and ready == 0:
        rep.add("WARN", "buffer=0（停发或降频；禁硬写空转章充数，serial-ops §1）")
    else:
        rep.add("PASS", "buffer ready=%d（target=%d）" % (ready, target))
    return rep


# ---------------------------------------------------------------- check --project
def check_project(proj, rep=None):
    rep = rep or Report()
    # 树节点信封 + 必需节
    for n in proj.tree_nodes():
        m, body, path = n["meta"], n["body"], n["path"]
        rel = str(path.relative_to(proj.root))
        probs = []
        for k in ("id", "kind", "status", "rev", "updated_at"):
            if k not in m:
                probs.append("缺 %s" % k)
        if m.get("kind") != "book" and "parent" not in m:
            probs.append("缺 parent")
        if m.get("kind") in NODE_KINDS and m.get("status") not in NODE_STATUS:
            probs.append("status 非法：%s" % m.get("status"))
        req = REQUIRED_SECTIONS.get(m.get("kind"), [])
        titles = [t for t, _ in split_sections(body)]
        for s in req:
            match = [t for t in titles if t == s or t.startswith(s)]
            if not match:
                probs.append("缺必需节「%s」" % s)
            elif m.get("status") == "committed":
                c = get_section(body, s)
                if not (c or "").strip():
                    probs.append("committed 但「%s」为空" % s)
        if probs:
            rep.add("FAIL", "节点 %s（%s）" % (m.get("id"), rel), probs)
    if not any(l == "FAIL" and n.startswith("节点") for l, n, _, _ in rep.items):
        rep.add("PASS", "树节点信封与必需节合规（%d 个）" % len(proj.tree_nodes()))

    # 章三件套 + cast 可解析
    ents = proj.entities()
    aliases = proj.aliases()
    ch_fails = []
    for c in proj.chapters():
        cid, m = c["id"], c["meta"]
        if m.get("status") not in CH_STATUS:
            ch_fails.append("%s status 非法：%s" % (cid, m.get("status")))
        if not proj.p("chapters", cid + ".task.json").is_file():
            ch_fails.append("%s 缺 task.json" % cid)
        if m.get("status") in ("drafted", "approved", "published") \
                and not proj.p("chapters", cid + ".meta.json").is_file():
            ch_fails.append("%s 已成稿但缺 meta.json" % cid)
        task = proj.chapter_task(cid)
        if task:
            for ref in task.get("cast", []):
                if ref.startswith("[") or proj.resolve_entity(ref):
                    continue
                ch_fails.append("%s cast「%s」无法经 entities/aliases 解析" % (cid, ref))
            arc = task.get("arc")
            if arc and not arc.startswith("[") and not (proj.node_path(arc) or Path("/x")).is_file():
                ch_fails.append("%s 所属弧 %s 不存在" % (cid, arc))
    if ch_fails:
        rep.add("FAIL", "章三件套/引用", ch_fails)
    else:
        rep.add("PASS", "章三件套与 cast 引用合规（%d 章）" % len(proj.chapters()))

    # threads 纪律（P1-2：dropped 引用的 decision 必须真实存在）
    decisions = proj.decisions()
    th_fails = []
    for tid, t in proj.threads().items():
        m = t["meta"]
        if m.get("thread_kind") not in THREAD_KINDS:
            th_fails.append("%s thread_kind 非法" % tid)
        if m.get("state") not in THREAD_STATES:
            th_fails.append("%s state 非法：%s" % (tid, m.get("state")))
        if m.get("must_not_drop") and m.get("state") == "dropped":
            refs = re.findall(r"dec_\d{3}[a-z0-9_]*", t["body"])
            if not refs:
                th_fails.append("%s：must_not_drop 线被 dropped 且无 decision 引用" % tid)
            elif not any(any(d.startswith(r) or r.startswith(d.split(".")[0])
                             for d in decisions) for r in refs):
                th_fails.append("%s：dropped 引用的 decision %s 在 court/ 不存在"
                                % (tid, refs))
    if th_fails:
        rep.add("FAIL", "线索纪律", th_fails)
    else:
        rep.add("PASS", "线索纪律合规（%d 条）" % len(proj.threads()))

    # P1-2：decision 键集 + 必需节 + 否决案 reopen_requires
    dec_fails = []
    for did, d in decisions.items():
        m, body = d["meta"], d["body"]
        for k in DEC_KEYS:
            if k not in m:
                dec_fails.append("%s 缺 %s" % (did, k))
        if m.get("kind") not in (None, "decision"):
            dec_fails.append("%s kind 应为 decision" % did)
        sess = str(m.get("session") or "")
        if sess and not sess.startswith("[") and sess not in DEC_SESSIONS:
            dec_fails.append("%s session 非法：%s" % (did, sess))
        titles = [t for t, _ in split_sections(body)]
        for s in DEC_SECTIONS:
            if not any(t == s or t.startswith(s) for t in titles):
                dec_fails.append("%s 缺必需节「%s」" % (did, s))
        veto = get_section(body, "否决案") or ""
        for ln in veto.splitlines():
            ln = ln.strip()
            if ln.startswith("- ") and not ln.startswith("- [") \
                    and "reopen_requires" not in ln:
                dec_fails.append("%s 否决案行缺 reopen_requires：%s" % (did, ln[:40]))
    if dec_fails:
        rep.add("FAIL", "裁决记录（court/dec_*.md，formats §11）", dec_fails)
    elif decisions:
        rep.add("PASS", "裁决记录合规（%d 份）" % len(decisions))

    # P1-2：review 键集 + 必需节
    rev_fails = []
    reviews = proj.reviews()
    for r in reviews:
        m, body = r["meta"], r["body"]
        rid = r["path"].name
        for k in REVIEW_KEYS:
            if k not in m:
                rev_fails.append("%s 缺 %s" % (rid, k))
        if m.get("depth") not in REVIEW_DEPTHS:
            rev_fails.append("%s depth 非法：%s" % (rid, m.get("depth")))
        if m.get("verdict") not in REVIEW_VERDICTS:
            rev_fails.append("%s verdict 非法：%s" % (rid, m.get("verdict")))
        if not any(t.startswith("问题清单") for t, _ in split_sections(body)):
            rev_fails.append("%s 缺「问题清单」节" % rid)
    if rev_fails:
        rep.add("FAIL", "评审单（reviews/*.md，formats §12）", rev_fails)
    elif reviews:
        rep.add("PASS", "评审单合规（%d 份）" % len(reviews))

    # facts schema + superseded 引用
    f_fails = []
    for f in proj.facts_files():
        try:
            data = json.loads(read(f))
        except ValueError as e:
            f_fails.append("%s JSON 解析失败：%s" % (f.name, e))
            continue
        ids = {x.get("id") for x in data.get("facts", [])}
        for x in data.get("facts", []):
            for k in ("id", "fact", "entity_ids", "revealed_ch", "spoiler"):
                if k not in x:
                    f_fails.append("%s %s 缺 %s" % (f.name, x.get("id"), k))
        for r in data.get("retcons", []):
            if r.get("old_fact_id") not in ids:
                f_fails.append("%s retcon %s 指向不存在的 fact" % (f.name, r.get("id")))
            if not r.get("decision_ref"):
                f_fails.append("%s retcon %s 缺 decision_ref" % (f.name, r.get("id")))
    if f_fails:
        rep.add("FAIL", "facts/retcons", f_fails)
    else:
        rep.add("PASS", "facts 台账合规")

    # 知识矩阵 v2：知情圈台账完整性（entities/scopes.json）
    sc_fails = []
    for gid, members in proj.scopes().items():
        if not (gid.startswith(proj.GROUP_PREFIXES) and gid in ents):
            sc_fails.append("知情圈键「%s」不是已登记的 fac/loc/item 实体" % gid)
        for m in members:
            if not (m.startswith("char_") and m in ents):
                sc_fails.append("%s 圈成员「%s」不是已登记的 char 实体" % (gid, m))
    known_groups = set()
    for x, _ in proj.all_facts():
        known_groups |= {k for k in (x.get("known_by") or [])
                         if k.startswith(proj.GROUP_PREFIXES)}
    empty = sorted(known_groups - {g for g, mem in proj.scopes().items() if mem})
    if sc_fails:
        rep.add("FAIL", "知情圈台账（scopes.json）", sc_fails)
    else:
        rep.add("PASS", "知情圈台账合规（%d 圈）" % len(proj.scopes()))
    if empty:
        rep.add("WARN", "known_by 引用了空知情圈（范围授予但无成员——"
                        "knowledge scope add 编圈，否则展开后无人知情）", empty)

    # published 连续性
    pub = sorted(ch_num(c["id"]) for c in proj.chapters()
                 if c["meta"].get("status") == "published")
    if pub and pub != list(range(pub[0], pub[0] + len(pub))):
        rep.add("FAIL", "published 章不连续（存在空洞）",
                ["published: %s" % pub])
    elif pub:
        rep.add("PASS", "published 连续（%d–%d）" % (pub[0], pub[-1]))

    # P0-3：半事务检测（state/txn/ 残留 done=false 的 journal = commit 中断）
    txn_dir = proj.p("state", "txn")
    half = []
    if txn_dir.is_dir():
        for f in sorted(txn_dir.glob("txn_*.json")):
            try:
                d = json.loads(read(f))
            except ValueError:
                half.append("%s 不可解析" % f.name)
                continue
            if not d.get("done"):
                half.append("%s：%s(%s) 始于 %s 未完成"
                            % (d.get("id"), d.get("kind"), d.get("target"),
                               d.get("started_at")))
    if half:
        rep.add("FAIL", "半事务残留（commit 中断；处置：git checkout -- . && git clean -fd "
                        "回滚 → 删除该 journal → 任务回 pending 重跑）", half)
    else:
        rep.add("PASS", "无半事务残留")

    # queue targets
    q_fails = []
    known = {c["id"] for c in proj.chapters()} | set(ents) | set(proj.threads()) \
        | {n["meta"].get("id") for n in proj.tree_nodes()}
    fact_ids = {x.get("id") for x, _ in proj.all_facts()}
    for t in proj.queue()["tasks"]:
        tgt = t.get("target", "")
        if tgt and tgt not in known and tgt not in fact_ids \
                and not tgt.startswith("vol_"):
            q_fails.append("%s target=%s 不存在" % (t["id"], tgt))
    if q_fails:
        rep.add("WARN", "队列 target 悬空", q_fails)
    else:
        rep.add("PASS", "队列 target 全部可解析")
    return rep


def cmd_check(args):
    proj = Project(find_root(args))
    rep = Report()
    if args.leak:
        if not args.brief:
            die("check --leak 需 --brief <简报文件>")
        check_leak(proj, args.leak, args.brief, rep)
        return rep.render("check --leak")
    if args.unit:
        check_unit(proj, args.unit, args.candidate, args.writeback, rep)
        return rep.render("check --unit %s" % args.unit)
    if args.window:
        check_window(proj, rep, since=args.since)
        return rep.render("check --window%s" % (" --since " + args.since if args.since else ""))
    check_project(proj, rep)
    return rep.render("check --project")
