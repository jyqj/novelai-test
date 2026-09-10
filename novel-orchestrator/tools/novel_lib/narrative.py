# -*- coding: utf-8 -*-
"""Typed episodic memory and chapter-relative views (no model or embeddings)."""
import json
import re

from .common import ch_num, get_section

MEMORY_KINDS = {"consequence", "relationship", "promise", "motif", "belief", "emotion", "scene"}


def writeback_errors(wb, text=None):
    if not isinstance(wb, dict):
        return ["writeback 必须为对象"]
    errors = []
    arrays = ("continuity_delta", "thread_ops", "payoff_realized", "cast_actual",
              "issues", "power_delta", "narrative_memory")
    for key in arrays:
        if key in wb and not isinstance(wb[key], list):
            errors.append(key + " 必须为数组")
    for key in ("time_advance", "hooks_realized"):
        if key in wb and not isinstance(wb[key], dict):
            errors.append(key + " 必须为对象")
    if "summary_after" in wb and not isinstance(wb["summary_after"], str):
        errors.append("summary_after 必须为字符串")
    if errors:
        return errors
    for key in ("continuity_delta", "thread_ops", "power_delta", "narrative_memory"):
        if any(not isinstance(d, dict) for d in wb.get(key, [])):
            errors.append(key + " 的元素必须为对象")
    for key in ("cast_actual", "payoff_realized", "issues"):
        if any(not isinstance(d, str) for d in wb.get(key, [])):
            errors.append(key + " 的元素必须为字符串")
    if errors:
        return errors
    for d in wb.get("continuity_delta", []) + wb.get("power_delta", []):
        for key in ("entity_ids", "known_by"):
            if key in d and (not isinstance(d[key], list)
                             or any(not isinstance(v, str) for v in d[key])):
                errors.append(key + " 必须为字符串数组")
    for d in wb.get("continuity_delta", []):
        if not isinstance(d.get("fact"), str) or not d["fact"].strip():
            errors.append("fact 不能为空")
    for item in wb.get("narrative_memory", []):
        if item.get("kind") not in MEMORY_KINDS:
            errors.append("narrative_memory.kind 非法")
        for key in ("text", "evidence"):
            if not isinstance(item.get(key), str) or not item[key].strip():
                errors.append("叙事记忆必须有 " + key)
        for key in ("entity_ids", "thread_ids", "keywords"):
            val = item.get(key, [])
            if not isinstance(val, list) or any(not isinstance(v, str) for v in val):
                errors.append("叙事记忆 %s 必须为字符串数组" % key)
        if text is not None and item.get("evidence") and item["evidence"] not in text:
            errors.append("叙事记忆 evidence 不在本章正文中；不得将计划冒充发生过的事")
    return errors


def reader_knows(fact, at_ch):
    reveal = fact.get("revealed_reader_ch")
    if reveal is not None:
        return int(reveal) <= at_ch
    return not fact.get("spoiler", 0)


def fact_exists(fact, at_ch):
    return int(fact.get("revealed_ch") or 0) <= at_ch


def effective_knowers(proj, fact, at_ch=None):
    """Immutable grant snapshots: leaving a faction does not erase knowledge.

    Legacy facts without events retain current-scope semantics until explicitly
    migrated by a grant; consumers flag that their historical precision is unknown.
    """
    events = fact.get("knowledge_events")
    if events is None:
        return proj.expand_knowers(fact.get("known_by") or [])
    result = set()
    for event in events:
        if at_ch is None or int(event["chapter"]) <= at_ch:
            result.update(event["knowers"])
    return result


def grant_event(proj, fact, recipients, chapter):
    if chapter < int(fact.get("revealed_ch") or 0):
        raise ValueError("获知章不能早于事实登记章")
    if "knowledge_events" not in fact:
        old = fact.get("known_by") or []
        fact["knowledge_events"] = []
        if old:
            # Do NOT silently backdate a legacy current-state grant to book start.
            fact["knowledge_events"].append({"chapter": chapter,
                "knowers": sorted(proj.expand_knowers(old)), "via": sorted(old),
                "legacy_snapshot": True})
    event = {"chapter": chapter, "knowers": sorted(proj.expand_knowers(recipients)),
             "via": sorted(recipients)}
    if event not in fact["knowledge_events"]:
        fact["knowledge_events"].append(event)
    fact["known_by"] = sorted(set(fact.get("known_by") or []) | set(recipients))


def setting_blocks(body):
    """Select complete list blocks, never an arbitrary first-N-lines prefix."""
    blocks = {}
    key, lines = None, []
    for line in (get_section(body, "设定") or "").splitlines():
        if re.match(r"^- \S", line):
            if key:
                blocks[key] = "\n".join(lines)
            key = re.split(r"[:：(（]", line[2:], maxsplit=1)[0].strip()
            lines = [line]
        elif key:
            lines.append(line)
    if key:
        blocks[key] = "\n".join(lines)
    return blocks


def historical_log(body, section, at_ch):
    lines = []
    for line in (get_section(body, section) or "").splitlines():
        match = re.match(r"^-\s*ch_(\d{4})\s*:", line)
        if match and int(match.group(1)) <= at_ch:
            lines.append(line)
    return lines


def memory_recall(proj, task, at_ch, limit=6):
    """Rank whole evidence-backed episodes, not only first/last arc sentences."""
    cast = {proj.resolve_entity(x) or x for x in task.get("cast", [])}
    cast |= set(task.get("context_entities", []))
    tags = set(task.get("memory_keywords", []))
    wanted = set(task.get("memory_refs", []))
    candidates = []
    for chapter in proj.chapters():
        cid = chapter["id"]
        if ch_num(cid) > at_ch or chapter["meta"].get("status") not in ("drafted", "approved", "published"):
            continue
        wb = proj.chapter_meta_json(cid) or {}
        for i, item in enumerate(wb.get("narrative_memory", [])):
            ref = "%s#%d" % (cid, i)
            score = 4 * len(cast & set(item.get("entity_ids", [])))
            score += 5 * len(tags & set(item.get("keywords", [])))
            score += 3 * len({v["id"] if isinstance(v, dict) else v for v in task.get("threads", [])} & set(item.get("thread_ids", [])))
            if ref in wanted or score:
                candidates.append((ref in wanted, score, ch_num(cid), ref, item))
    candidates.sort(key=lambda row: (row[0], row[1], row[2], row[3]), reverse=True)
    selected = [c for c in candidates if c[0]] + [c for c in candidates if not c[0]][:limit]
    missing = wanted - {c[3] for c in selected}
    if missing:
        raise ValueError("必需叙事记忆不存在或来自未来：" + ", ".join(sorted(missing)))
    return selected


def related_facts(proj, task, at_ch):
    cast = {proj.resolve_entity(x) or x for x in task.get("cast", [])}
    relevant = cast | set(task.get("context_entities", []))
    required = set(task.get("fact_refs", []))
    keywords = task.get("memory_keywords", [])
    hits = []
    for fact, path in proj.all_facts():
        if not fact_exists(fact, at_ch):
            continue
        if (fact.get("id") in required or relevant & set(fact.get("entity_ids", []))
                or cast & effective_knowers(proj, fact, at_ch)
                or any(word and word in fact.get("fact", "") for word in keywords)):
            hits.append((fact, proj.p("ledgers", "facts", path)))
    missing = required - {x.get("id") for x, _ in hits}
    if missing:
        raise ValueError("必需事实不存在或来自未来：" + ", ".join(sorted(missing)))
    return hits


def entity_status(proj, entity_id, entity, at_ch):
    current_at = int(entity["meta"].get("last_reconcile_ch") or 0)
    if current_at <= at_ch:
        return get_section(entity["body"], "现状") or ""
    history = proj.p("entities", "history", entity_id + ".json")
    snapshots = json.loads(history.read_text(encoding="utf-8")) if history.is_file() else []
    valid = [s for s in snapshots if s["chapter"] <= at_ch]
    if valid:
        return max(valid, key=lambda s: s["chapter"])["status"]
    return "【历史快照缺失】当前卡已对账至 ch_%04d，不注入未来状态；按下列历史事件补证。" % current_at


def thread_state_at(thread, at_ch):
    from .common import thread_next_state
    full = get_section(thread["body"], "推进日志") or ""
    historical = historical_log(thread["body"], "推进日志", at_ch)
    if not re.search(r"ch_\d{4}", full):
        return thread["meta"].get("state", "planted")
    state = "planted"
    for line in sorted(historical, key=lambda s: int(re.search(r"ch_(\d{4})", s).group(1))):
        match = re.search(r":\s*(plant|advance|payoff|tangle|ready)\b", line)
        if match:
            state = thread_next_state(state, match.group(1)) or state
    return state
