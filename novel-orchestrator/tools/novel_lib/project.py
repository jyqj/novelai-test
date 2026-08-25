# -*- coding: utf-8 -*-
"""project — 项目对象（Project）与任务队列的读写半边。"""
import json
import re
from pathlib import Path

from .common import (NOW, ch_num, dedup_latest_rev, die, parse_frontmatter,
                     read, vol_of_arc, write)


class Project:
    def __init__(self, root):
        self.root = Path(root).resolve()
        cfg = self.root / "config.json"
        if not cfg.is_file():
            die("未找到项目（%s 无 config.json）；用 --root 指定或先 init" % self.root)
        self.config = json.loads(read(cfg))

    # ---- 路径
    def p(self, *parts):
        return self.root.joinpath(*parts)

    # ---- 章
    def chapter_files(self):
        return sorted(self.p("chapters").glob("ch_*.md"))

    def chapters(self):
        out = []
        for f in self.chapter_files():
            meta, body = parse_frontmatter(read(f))
            out.append({"id": f.stem, "meta": meta or {}, "body": body, "path": f})
        return out

    def chapter_meta_json(self, ch_id):
        f = self.p("chapters", ch_id + ".meta.json")
        return json.loads(read(f)) if f.is_file() else None

    def chapter_task(self, ch_id):
        f = self.p("chapters", ch_id + ".task.json")
        return json.loads(read(f)) if f.is_file() else None

    def vol_of_chapter(self, ch_id):
        """章 → 卷 id：优先任务卡 arc，再信封 parent；无从推断时归 vol_01。"""
        task = self.chapter_task(ch_id) or {}
        v = vol_of_arc(task.get("arc"))
        if v:
            return v
        p = self.p("chapters", ch_id + ".md")
        if p.is_file():
            meta, _ = parse_frontmatter(read(p))
            v = vol_of_arc((meta or {}).get("parent"))
        return v or "vol_01"

    # ---- 树节点
    def tree_nodes(self):
        out = []
        for f in [self.p("tree", n) for n in ("book.md", "style.md", "world.md")]:
            if f.is_file():
                meta, body = parse_frontmatter(read(f))
                out.append({"meta": meta or {}, "body": body, "path": f})
        for f in sorted(self.p("tree").glob("vol_*/*.md")):
            meta, body = parse_frontmatter(read(f))
            out.append({"meta": meta or {}, "body": body, "path": f})
        return out

    def node_path(self, node_id):
        if node_id in ("book", "style", "world"):
            return self.p("tree", node_id + ".md")
        m = re.match(r"^vol_(\d{2})$", node_id)
        if m:
            return self.p("tree", node_id, "volume.md")
        m = re.match(r"^arc_(\d{2})_(\d+)$", node_id)
        if m:
            return self.p("tree", "vol_" + m.group(1), node_id + ".md")
        if node_id.startswith("ch_"):
            return self.p("chapters", node_id + ".md")
        return None

    # ---- 实体/线索
    def entities(self):
        out = {}
        for f in sorted(self.p("entities").glob("*.md")):
            meta, body = parse_frontmatter(read(f))
            out[f.stem] = {"meta": meta or {}, "body": body, "path": f}
        return out

    def aliases(self):
        f = self.p("entities", "aliases.json")
        return json.loads(read(f)) if f.is_file() else {}

    def resolve_entity(self, ref):
        ents = self.entities()
        if ref in ents:
            return ref
        return self.aliases().get(ref)

    # ---- 知识矩阵 v2：范围知情（fac/loc/item 知情圈，entities/scopes.json）
    GROUP_PREFIXES = ("fac_", "loc_", "item_")

    def scopes(self):
        f = self.p("entities", "scopes.json")
        return json.loads(read(f)) if f.is_file() else {}

    def expand_knowers(self, known_by):
        """known_by 条目展开为有效知情集合：个体照抄；fac_/loc_/item_ 条目
        并入其知情圈成员（entities/scopes.json；圈空 = 只有群体本身）。"""
        scopes = self.scopes()
        eff = set()
        for k in known_by or []:
            eff.add(k)
            if k.startswith(self.GROUP_PREFIXES):
                eff |= set(scopes.get(k, []))
        return eff

    def threads(self):
        out = {}
        for f in sorted(self.p("threads").glob("thread_*.md")):
            meta, body = parse_frontmatter(read(f))
            out[f.stem] = {"meta": meta or {}, "body": body, "path": f}
        return out

    # ---- 裁决与评审
    def decisions(self):
        out = {}
        for f in sorted(self.p("court").glob("dec_*.md")):
            meta, body = parse_frontmatter(read(f))
            out[f.stem] = {"meta": meta or {}, "body": body, "path": f}
        return out

    def reviews(self):
        out = []
        for f in sorted(self.p("reviews").glob("*.md")):
            meta, body = parse_frontmatter(read(f))
            out.append({"meta": meta or {}, "body": body, "path": f})
        return out

    def last_deep_review_ch(self):
        last = 0
        for r in self.reviews():
            if r["meta"].get("depth") != "deep":
                continue
            m = re.match(r"^ch_(\d{4})$", str(r["meta"].get("chapter") or ""))
            if m:
                last = max(last, int(m.group(1)))
        return last

    # ---- 队列
    def queue(self):
        return json.loads(read(self.p("tasks", "queue.json")))

    def save_queue(self, q):
        write(self.p("tasks", "queue.json"), json.dumps(q, ensure_ascii=False, indent=1))

    def task(self, tid):
        for t in self.queue()["tasks"]:
            if t["id"] == tid:
                return t
        return None

    # ---- 台账（P0-1：(chapter,rev) 语义——文件 append-only，读侧按最大 rev 物化去重；
    #      旧格式无 rev 列的行按 rev=1 兼容）
    def payoff_rows(self, all_revs=False):
        f = self.p("ledgers", "payoff.tsv")
        rows = []
        if f.is_file():
            lines = read(f).splitlines()
            for ln in lines[1:]:
                c = ln.split("\t")
                if len(c) >= 5:
                    rows.append({"chapter": c[0], "payoff_id": c[1], "kind": c[2],
                                 "intent": c[3], "realized": c[4].strip() == "1",
                                 "rev": int(c[5]) if len(c) > 5
                                 and c[5].strip().isdigit() else 1})
        return rows if all_revs else dedup_latest_rev(rows)

    def power_rows(self, all_revs=False):
        f = self.p("ledgers", "power.tsv")
        rows = []
        if f.is_file():
            for ln in read(f).splitlines()[1:]:
                c = ln.split("\t")
                if len(c) >= 4:
                    rows.append({"chapter": c[0], "entity": c[1], "from": c[2],
                                 "to": c[3], "note": c[4] if len(c) > 4 else "",
                                 "rev": int(c[5]) if len(c) > 5
                                 and c[5].strip().isdigit() else 1})
        return rows if all_revs else dedup_latest_rev(rows)

    def timeline_rows(self, all_revs=False):
        f = self.p("ledgers", "timeline.tsv")
        rows = []
        if f.is_file():
            for ln in read(f).splitlines()[1:]:
                c = ln.split("\t")
                if len(c) >= 3:
                    rows.append({"chapter": c[0], "story_date": c[1].strip(),
                                 "elapsed": c[2].strip(),
                                 "note": c[3] if len(c) > 3 else "",
                                 "rev": int(c[4]) if len(c) > 4
                                 and c[4].strip().isdigit() else 1})
        return rows if all_revs else dedup_latest_rev(rows)

    def facts_files(self):
        return sorted(self.p("ledgers", "facts").glob("*.json"))

    def all_facts(self):
        """返回 [(fact_dict, 文件名)]；解析失败的文件跳过（check --project 会另行报 FAIL）。"""
        out = []
        for f in self.facts_files():
            try:
                data = json.loads(read(f))
            except ValueError:
                continue
            for x in data.get("facts", []):
                out.append((x, f.name))
        return out

    def next_fact_seq(self):
        seq = 0
        for x, _ in self.all_facts():
            m = re.match(r"^fact_(\d{4,})$", str(x.get("id", "")))
            if m:
                seq = max(seq, int(m.group(1)))
        return seq + 1

    def ngram_cache(self):
        f = self.p("state", "ngram_cache.json")
        return json.loads(read(f)) if f.is_file() else {}

    # ---- 游标
    def cursor(self):
        pub, drafted, approved = 0, 0, 0
        for c in self.chapters():
            n = ch_num(c["id"])
            st = c["meta"].get("status")
            if st == "published":
                pub = max(pub, n)
            if st in ("drafted", "approved", "published"):
                drafted = max(drafted, n)
            if st in ("approved", "published"):
                approved = max(approved, n)
        return {"last_published": pub, "last_drafted": drafted, "last_approved": approved}

    def buffer_ready(self):
        cur = self.cursor()
        return sum(1 for c in self.chapters()
                   if c["meta"].get("status") == "approved"
                   and ch_num(c["id"]) > cur["last_published"])


def find_root(args):
    if getattr(args, "root", None):
        return Path(args.root)
    cur = Path.cwd()
    for cand in [cur] + list(cur.parents):
        if (cand / "config.json").is_file() and (cand / "tree").is_dir():
            return cand
    die("当前目录不在项目内；用 --root <项目根> 指定")


def promote_blocked(q):
    """依赖已 done 的 blocked 任务自动解锁 → pending。返回被解锁的任务 id 列表。"""
    done = {t["id"] for t in q["tasks"] if t["state"] == "done"}
    changed = []
    for t in q["tasks"]:
        if t["state"] == "blocked" and all(b in done for b in t.get("blocked_on", [])):
            t["state"] = "pending"
            t["updated_at"] = NOW()
            changed.append(t["id"])
    return changed


def load_queue_promoted(proj):
    """读队列并解锁到期 blocked 任务（有变化即落盘）。"""
    q = proj.queue()
    changed = promote_blocked(q)
    if changed:
        proj.save_queue(q)
        print("[queue] 依赖完成，解锁 → pending：%s" % " ".join(changed))
    return q


def next_task_id(q):
    done = {t["id"] for t in q["tasks"] if t["state"] == "done"}
    for t in q["tasks"]:
        if t["state"] == "pending" and all(b in done for b in t.get("blocked_on", [])):
            return t["id"]
    return None
