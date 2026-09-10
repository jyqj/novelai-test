# -*- coding: utf-8 -*-
"""Content-addressed review evidence. A receipt proves coverage, not literary merit."""
import hashlib
import json

from .common import (SKILL_ROOT, UNIT_NEEDS_REVIEW, ch_num, get_section,
                     parse_frontmatter, read)


def sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def subject_hash(proj, ch_id):
    meta, body = parse_frontmatter(read(proj.p("chapters", ch_id + ".md")))
    # Administrative state changes must not invalidate the reviewed text.
    core = {k: v for k, v in (meta or {}).items()
            if k not in ("status", "updated_at", "approved_evidence", "published_hash")}
    rubric = {str(p.relative_to(SKILL_ROOT)): sha(read(p))
              for p in sorted((SKILL_ROOT / "rubrics").glob("*.md"))}
    payload = {"chapter": core, "body": body.strip(),
               "writeback": proj.chapter_meta_json(ch_id),
               "task": proj.chapter_task(ch_id),
               "style": read(proj.p("tree", "style.md")),
               "rubrics": rubric, "checks": UNIT_NEEDS_REVIEW,
               "quality_config": {k: proj.config.get(k) for k in ("route", "word_target", "aesthetic_profile")},
               "brief": read(proj.p("briefs", ch_id + ".brief.md"))
               if proj.p("briefs", ch_id + ".brief.md").is_file() else None}
    return sha(json.dumps(payload, ensure_ascii=False, sort_keys=True))


def requirements(proj, ch_id):
    from .checks import check_unit
    findings = []
    for level, name, details, _ in check_unit(proj, ch_id).items:
        if level == "NEEDS_REVIEW":
            text = json.dumps([name, sorted(details)], ensure_ascii=False)
            findings.append({"id": "R-" + sha(text)[:16], "check": name,
                             "details": details, "disposition": "pending", "rationale": ""})
    return findings


def checklist(proj, ch_id):
    ch_num(ch_id)
    return {"schema_version": 1, "chapter": ch_id,
            "subject_sha256": subject_hash(proj, ch_id), "summary": "",
            "findings": requirements(proj, ch_id), "strengths": []}


def evidence_errors(proj, ch_id, evidence, verdict):
    errors = []
    if not isinstance(evidence, dict):
        return ["评审 evidence 必须为 JSON 对象"]
    if evidence.get("subject_sha256") != subject_hash(proj, ch_id):
        errors.append("评审对象哈希不匹配；正文/回写/任务/简报/判据已变化，请重新评审")
    if evidence.get("chapter") != ch_id:
        errors.append("评审对象章号不匹配")
    if not isinstance(evidence.get("summary"), str) or not evidence["summary"].strip():
        errors.append("评审 summary 不可为空；不得默认无问题")
    decisions = evidence.get("findings")
    if not isinstance(decisions, list) or not all(isinstance(d, dict) for d in decisions):
        return errors + ["findings 必须为逐项裁定对象数组"]
    ids = [d.get("id") for d in decisions]
    if any(not isinstance(i, str) for i in ids):
        return errors + ["裁定 id 必须为字符串"]
    if len(set(ids)) != len(ids):
        errors.append("裁定 id 重复")
    for d in decisions:
        if d.get("disposition") not in ("pass", "waived", "revise", "escalate"):
            errors.append("非法/未完成裁定：%s" % d.get("id"))
        if not isinstance(d.get("rationale"), str) or not d["rationale"].strip():
            errors.append("每项裁定必须有文字依据：%s" % d.get("id"))
        if verdict == "pass" and d.get("disposition") not in ("pass", "waived"):
            errors.append("pass 不能携带任何未解决项：%s" % d.get("id"))
    indexed = {d.get("id"): d for d in decisions}
    for required in requirements(proj, ch_id):
        d = indexed.get(required["id"], {})
        if d.get("disposition") not in ("pass", "waived", "revise", "escalate"):
            errors.append("待裁定：%s %s" % (required["id"], required["check"]))
        if not str(d.get("rationale", "")).strip():
            errors.append("缺裁定依据：%s" % required["id"])
        if verdict == "pass" and d.get("disposition") not in ("pass", "waived"):
            errors.append("pass 不能携带未解决阻塞项：%s" % required["id"])
    strengths = evidence.get("strengths", [])
    if not isinstance(strengths, list):
        errors.append("strengths 必须为数组")
    else:
        manuscript = read(proj.p("chapters", ch_id + ".md")).split("## 正文", 1)[-1]
        for item in strengths:
            if not isinstance(item, dict) or any(not isinstance(item.get(k), str) or not item[k].strip()
                                                 for k in ("quote", "effect", "scope")):
                errors.append("成功样本必须有 quote/effect/scope")
            elif item["quote"] not in manuscript:
                errors.append("成功样本引用不在被评正文中")
    return errors


def receipt_errors(proj, meta, body):
    ch_id = meta.get("chapter", "")
    if meta.get("depth") not in ("light", "deep") or meta.get("verdict") not in ("pass", "revise", "escalate"):
        return ["非法评审 depth/verdict"]
    if not proj.p("chapters", ch_id + ".md").is_file():
        return ["评审章不存在"]
    try:
        evidence = json.loads(get_section(body, "逐项裁定") or "{}")
    except ValueError:
        return ["逐项裁定节须为纯 JSON 对象"]
    if meta.get("subject_sha256") != evidence.get("subject_sha256"):
        return ["评审信封与证据哈希不一致"]
    return evidence_errors(proj, ch_id, evidence, meta.get("verdict"))


def approval_receipt(proj, ch_id):
    path = proj.p("chapters", ch_id + ".md")
    if not path.is_file():
        return None
    cur, _ = parse_frontmatter(read(path))
    current = subject_hash(proj, ch_id)
    passing = []
    for depth in ("light", "deep"):
        path = proj.p("reviews", "%s.%s.md" % (ch_id, depth))
        if not path.is_file():
            continue
        meta, body = parse_frontmatter(read(path))
        meta = meta or {}
        if meta.get("rev_reviewed") != (cur.get("rev") or 1):
            continue
        # A same-revision blocker survives unrelated rubric/brief changes. Only
        # re-review at that depth or a new manuscript revision can resolve it.
        if meta.get("verdict") in ("revise", "escalate"):
            print("[warn] 阻塞评审未解决：%s=%s" % (path.name, meta["verdict"]))
            return None
        if meta.get("subject_sha256") != current or receipt_errors(proj, meta, body):
            continue
        passing.append("reviews/%s verdict=pass rev_reviewed=%s sha256=%s" %
                       (path.name, cur.get("rev") or 1, current))
    return passing[0] if passing else None
