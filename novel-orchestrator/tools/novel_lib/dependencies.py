# -*- coding: utf-8 -*-
"""Content hashes, including source-set changes, for reproducible brief compilation."""
import hashlib
import json
from .common import SKILL_ROOT, ch_num, read


def file_hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def brief_sources(proj, ch_id):
    num = ch_num(ch_id)
    files = {proj.p("config.json"), proj.p("chapters", ch_id + ".task.json")}
    for folder in ("tree", "entities", "threads"):
        for path in proj.p(folder).rglob("*"):
            if path.is_file() and path.suffix in (".md", ".json"):
                files.add(path)
    files.update(proj.facts_files())
    for name in ("lessons.md", "recap.md", "strengths.md"):
        files.add(proj.p("ledgers", name))
    files.add(proj.p("state", "rollup.json"))
    for path in proj.p("chapters").glob("ch_*.meta.json"):
        if ch_num(path.name[:7]) < num:
            files.add(path)
    for n in range(max(1, num - 3), num):
        files.add(proj.p("chapters", "ch_%04d.md" % n))
    result = {str(p.relative_to(proj.root)): file_hash(p) if p.is_file() else None
              for p in sorted(files)}
    for folder, pattern in (("rubrics", "*.md"), ("tools/novel_lib", "*.py"),
                            ("templates", "chapter.meta.json")):
        for p in sorted((SKILL_ROOT / folder).glob(pattern)):
            result["@skill/" + str(p.relative_to(SKILL_ROOT))] = file_hash(p)
    return result


def stale_brief(proj, ch_id):
    path = proj.p("briefs", ch_id + ".manifest.json")
    brief = proj.p("briefs", ch_id + ".brief.md")
    if not path.is_file() or not brief.is_file():
        return ["缺少简报或依赖清单；请重新编译"]
    manifest = json.loads(read(path))
    reasons = []
    if manifest.get("brief_sha256") != file_hash(brief):
        reasons.append("简报正文被直接修改")
    old, new = manifest.get("sources", {}), brief_sources(proj, ch_id)
    reasons.extend(key for key in sorted(old.keys() | new.keys()) if old.get(key) != new.get(key))
    return reasons
