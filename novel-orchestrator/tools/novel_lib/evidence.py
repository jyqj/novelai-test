# -*- coding: utf-8 -*-
"""Exact, chapter-bounded source recall. Textual evidence is not world truth."""
import re

from .common import ch_num, parse_frontmatter, read

_CHAPTER = re.compile(r"ch_[0-9]{4}\Z")
_BODY = re.compile(r"^##[ \t]+正文[ \t]*\r?$", re.M)


def evidence_specs(task):
    """Validate explicit references; no implicit search or new literary rules."""
    refs = task.get("evidence_refs", [])
    if not isinstance(refs, list):
        raise ValueError("task.evidence_refs 必须为对象数组")
    result = []
    for index, ref in enumerate(refs):
        label = "evidence_refs[%d]" % index
        if not isinstance(ref, dict):
            raise ValueError(label + " 必须为对象")
        if set(ref) - {"chapter", "quote", "purpose", "occurrence", "context_chars"}:
            raise ValueError(label + " 含未知字段；请检查引用拼写")
        chapter, quote = ref.get("chapter"), ref.get("quote")
        if not isinstance(chapter, str) or not _CHAPTER.fullmatch(chapter) or ch_num(chapter) < 1:
            raise ValueError(label + ".chapter 必须为 ch_0001 形式的章号")
        if not isinstance(quote, str) or not quote.strip():
            raise ValueError(label + ".quote 必须为非空原文，不做模糊匹配")
        purpose = ref.get("purpose", "回看原文")
        if not isinstance(purpose, str):
            raise ValueError(label + ".purpose 必须为字符串")
        occurrence = ref.get("occurrence")
        if "occurrence" in ref and (type(occurrence) is not int or occurrence < 1):
            raise ValueError(label + ".occurrence 必须为从 1 开始的整数")
        context = ref.get("context_chars", 180)
        if type(context) is not int or not 0 <= context <= 2000:
            raise ValueError(label + ".context_chars 必须为 0..2000 的整数（每侧字符数）")
        result.append({"chapter": chapter, "quote": quote, "purpose": purpose,
                       "occurrence": occurrence, "context_chars": context})
    return result


def evidence_sources(proj, task):
    """Dependency manifest includes distant source text, not just its summary."""
    sources = []
    for spec in evidence_specs(task):
        path = proj.p("chapters", spec["chapter"] + ".md")
        try:
            path.resolve().relative_to(proj.root.resolve())
        except ValueError:
            raise ValueError("原文引用不得越出项目目录") from None
        sources.append(path)
    return sources


def recall_evidence(proj, task, at_ch):
    """Return verified excerpts at or before the reading cutoff, in request order.

    An occurrence is required for duplicate quotes; all explicit evidence is
    required context. The caller applies the existing brief budget atomically.
    """
    result = []
    specs = evidence_specs(task)
    paths = evidence_sources(proj, task)
    for index, (spec, path) in enumerate(zip(specs, paths)):
        cid, quote = spec["chapter"], spec["quote"]
        if ch_num(cid) > at_ch:
            raise ValueError("原文引用不能来自目标章或未来：" + cid)
        if not path.is_file():
            raise ValueError("必需原文不存在：" + cid)
        source = read(path)
        meta, _ = parse_frontmatter(source)
        if meta.get("id") != cid or meta.get("status") not in ("drafted", "approved", "published"):
            raise ValueError("原文来源必须是已写的同名章节，不接受计划或试写：" + cid)
        header = _BODY.search(source)
        if not header:
            raise ValueError("原文章节缺少 正文 节：" + cid)
        offset = header.end()
        text = source[offset:]
        positions, start = [], 0
        while True:
            found = text.find(quote, start)
            if found < 0:
                break
            positions.append(found)
            start = found + 1
        if not positions:
            raise ValueError("引文不在原章节正文，可能已返修：" + cid)
        number = spec["occurrence"]
        if number is None:
            if len(positions) != 1:
                raise ValueError("引文重复，请补 occurrence 指定位置：" + cid)
            number = 1
        if number > len(positions):
            raise ValueError("occurrence 超出引文实际出现次数：" + cid)
        begin = positions[number - 1]
        end = begin + len(quote)
        left = max(0, begin - spec["context_chars"])
        right = min(len(text), end + spec["context_chars"])
        result.append({"key": "evidence:%d" % index,
                       "source": "chapters/" + cid + ".md",
                       "chapter": cid, "status": meta["status"],
                       "line_start": source.count("\n", 0, offset + left) + 1,
                       "line_end": source.count("\n", 0, offset + right - 1) + 1,
                       "quote": quote, "excerpt": text[left:right],
                       "purpose": spec["purpose"], "occurrence": number})
    return result
