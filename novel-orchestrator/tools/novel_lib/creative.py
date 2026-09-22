"""Transport editorial intent, without treating a plan as story history."""
import re

from .common import parse_frontmatter, read


def heading_content(body, title):
    """Read one exact Markdown heading, including children, excluding siblings."""
    level, lines, fence = None, [], None
    for line in body.splitlines():
        marker = re.match(r"^\s*(`{3,}|~{3,})", line)
        if marker:
            token = marker.group(1)
            if fence is None:
                fence = token
            elif token[0] == fence[0] and len(token) >= len(fence):
                fence = None
            if level is not None:
                lines.append(line)
            continue
        heading = None if fence else re.match(r"^(#{1,6})\s+(.+?)\s*#*\s*$", line)
        if heading:
            depth, name = len(heading.group(1)), heading.group(2)
            if level is not None and depth <= level:
                break
            if level is None and name == title:
                level = depth
                continue
        if level is not None:
            lines.append(line)
    # Unfilled template instructions are not a book's creative intent.
    return "\n".join(line for line in lines
                     if not re.fullmatch(r"\s*(?:-\s*)?\[.*\]\s*", line)).strip()


def intent_sources(proj, volume, arc):
    """Small, attributed blocks; no whole-book spoilers or automatic interpretation."""
    sources = [(proj.p("tree", "book.md"), "阅读体验契约", "书级体验"),
               (proj.node_path(volume), "卷主旨与价值走向", "本卷方向"),
               (proj.node_path(volume), "imports", "本卷承接"),
               (proj.node_path(arc) if arc else None, "当前创作问题", "本弧问题")]
    blocks, missing = [], []
    for path, heading, label in sources:
        if path is None or not path.is_file():
            missing.append(label)
            continue
        meta, body = parse_frontmatter(read(path))
        content = heading_content(body, heading)
        if not content:
            missing.append(label)
            continue
        source = str(path.relative_to(proj.root))
        blocks.append((label, content, source, (meta or {}).get("rev")))
    return blocks, missing
