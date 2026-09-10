# -*- coding: utf-8 -*-
"""Bounded cross-stage consultation; ownership remains provenance, not a ban."""
import hashlib
import json
import re

from .common import NOW, SKILL_ROOT, die, read, write
from .project import Project, find_root
from .stagectl import stage_state


def cmd_consult(args):
    proj = Project(find_root(args))
    stage = stage_state(proj)
    if not stage or not stage.get("stage"):
        die("先 stage enter；咨询不自动切换工作阶段", 1)
    if not args.reason.strip() or len(args.reason) > 2000:
        die("咨询必须有具体症状/理由（不超过 2000 字符）", 1)
    if not 1 <= len(args.ids) <= 2 or len(set(args.ids)) != len(args.ids):
        die("单次只允许 1–2 个不同知识块", 1)
    target = proj.node_path(args.target)
    if not proj.task(args.target) and not (target and target.is_file()):
        die("--target 必须是现有任务 id 或设计/章节节点", 1)
    for kid in args.ids:
        if not re.fullmatch(r"K-[A-Z]+-\d{3}", kid):
            die("非法知识块 id：" + kid, 1)
    chunks = {}
    for source in sorted((SKILL_ROOT / "knowledge").rglob("*.md")):
        text = read(source)
        anchors = list(re.finditer(r"<!--\s*(K-[A-Z]+-\d{3})\s*-->", text))
        for i, anchor in enumerate(anchors):
            kid = anchor.group(1)
            if kid not in args.ids:
                continue
            if kid in chunks:
                die("知识块主锚不唯一：" + kid, 1)
            end = anchors[i + 1].start() if i + 1 < len(anchors) else len(text)
            excerpt = text[anchor.start():end].strip()
            chunks[kid] = {"source": str(source.relative_to(SKILL_ROOT)),
                           "sha256": hashlib.sha256(excerpt.encode()).hexdigest(),
                           "text": excerpt}
    missing = set(args.ids) - chunks.keys()
    if missing:
        die("找不到知识块：" + ", ".join(sorted(missing)), 1)
    budget = proj.config.get("consult_budget_chars", 16000)
    if not isinstance(budget, int) or budget <= 0 or budget > 50000:
        die("consult_budget_chars 必须为 1–50000 的整数", 1)
    if sum(len(chunk["text"]) for chunk in chunks.values()) > budget:
        die("知识块超过咨询字符预算；缩小选择，不整篇投递或静默截断", 1)
    path = proj.p("state", "knowledge-consults.json")
    history = json.loads(read(path)) if path.is_file() else []
    history.append({"at": NOW(), "stage": stage["stage"], "target": args.target,
                    "reason": args.reason, "sources": {key: {k: v for k, v in value.items() if k != "text"}
                                                        for key, value in chunks.items()}})
    write(path, json.dumps(history[-200:], ensure_ascii=False, indent=1))
    for kid in args.ids:
        print("## %s | %s | sha256=%s\n\n%s\n" %
              (kid, chunks[kid]["source"], chunks[kid]["sha256"], chunks[kid]["text"]))
    print("咨询已留痕；提炼成具体修订建议，原文不自动进入写手简报，也不改知识所有权。")
    return 0
