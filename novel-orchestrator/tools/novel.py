#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""novel.py — novel-orchestrator 项目 CLI（python3 stdlib only）。

实现 protocol/formats.md 的项目侧文件契约与 §15 CLI 的核心子集：

  init <dir> [--name X]              脚手架 + （可选）git init
  status                             重算 index/dashboard 并打印（可恢复断点）
  tree add <kind> <id> [--parent P]  由模板实例化节点（volume/arc/chapter）
  tree show [id] / tree set-status <id> <status>
  task add <type> <target> [...] / next / list / start / done / fail
  entity new <id> / show <id> / log <id> / due / update <id> --file F
  thread new <id> [--kind K]
  brief <ch_id>                      机械装配十节简报（预算裁剪 + 溯源）
  check --unit <ch> [--candidate F --writeback F] | --window | --project
  commit <task_id> [--chapter F --writeback F] [--file F ...] [-m 摘要]
  publish <ch_from> [<ch_to>]        连续性谓词；approved → published
  ledger payoff|promise|timeline     台账窗口视图
  fsck                               = check --project 别名

退出码：0=通过（可含 WARN/NEEDS_REVIEW）；1=存在 FAIL/校验拒绝；2=用法或环境错误。
主观判定项（遮名指认/智商漂移/关键场面占比等）输出 NEEDS_REVIEW，交由评审角色执行，
本工具不假装通过。frontmatter 为宽松行解析（扁平 key: value + 内联 JSON），非完整 YAML。
"""
import argparse
import datetime
import json
import re
import subprocess
import sys
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent
TEMPLATES = SKILL_ROOT / "templates"

NODE_KINDS = ("book", "volume", "arc", "world", "style")
NODE_STATUS = ("empty", "draft", "committed", "stale", "archived")
CH_STATUS = ("planned", "drafted", "approved", "published", "stale", "archived")
FLAT_STATUS = ("active", "archived")
TASK_TYPES = ("design", "revise_design", "write", "revise", "review_deep",
              "publish", "retcon", "checkpoint", "reconcile")
TASK_STATES = ("pending", "blocked", "running", "done", "failed")
PAYOFF_KINDS = ("dopamine", "upgrade", "reveal", "reversal", "emotion", "humor", "other")
THREAD_OPS = ("plant", "advance", "payoff", "tangle")
THREAD_KINDS = ("fuse", "subplot", "relationship", "mystery", "promise", "other")
THREAD_STATES = ("planted", "active", "tangled", "payoff_ready", "paid_off", "dropped")
BIG_PAYOFF_KINDS = ("upgrade", "reveal", "reversal")

META_KEYS = ("summary_after", "continuity_delta", "time_advance", "thread_ops",
             "payoff_realized", "hooks_realized", "cast_actual", "issues", "word_count")

REQUIRED_SECTIONS = {
    "book": ["主旨与主控思想", "高概念与题材定位", "世界观核心", "金手指与力量体系",
             "主线电缆", "人物主阵容", "反派梯队", "分卷草案", "红线自查结论"],
    "style": ["叙述基准", "口癖与句式禁忌", "比喻与意象纪律", "范文锚"],
    "world": ["核心规则", "力量体系与位阶", "势力格局", "禁忌与红线"],
    "volume": ["卷主旨与价值走向", "卷级冲突结构", "弧划分表", "imports", "exports",
               "阵容变化", "力量与资源预算", "爽点大节奏", "红线与毒点自查结论"],
    "arc": ["弧目标与节奏模板", "因果链", "章分配草案", "线索操作计划",
            "爽点与期待操作表", "出场实体清单"],
}

# 章级 NEEDS_REVIEW 项（必须由评审角色执行的主观判定；对应 rubrics）
UNIT_NEEDS_REVIEW = [
    "人设声纹遮名指认 ≥4/5（rubrics/voice.md §二）",
    "智商漂移两问（rubrics/prose-disease.md §六）",
    "关键场面对话+动作占比 ≥60%（rubrics/prose-disease.md §五）",
    "爽点兑现有效性：触发条件成立、非空转（rubrics/payoff.md §一/§六）",
    "毒点七问与负面节拍降档（rubrics/toxicity.md）",
    "与前章尾 500 字的衔接、与后章任务卡是否顶牛（roles/critic-light.md 四）",
]

CJK_RE = re.compile(r"[\u4e00-\u9fff]")
NOW = lambda: datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


# ---------------------------------------------------------------- 基础解析
def parse_value(raw):
    raw = raw.strip()
    if raw and raw[0] in "[{":
        try:
            return json.loads(raw)
        except (ValueError, TypeError):
            return raw
    if raw == "true":
        return True
    if raw == "false":
        return False
    if raw == "null":
        return None
    if re.fullmatch(r"-?\d+", raw):
        return int(raw)
    return raw


def parse_frontmatter(text):
    """返回 (meta, body)。无合法信封时 meta=None。宽松：扁平 key: value + 内联 JSON。"""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None, text
    meta = {}
    for i, ln in enumerate(lines[1:], start=1):
        if ln.strip() in ("---", "..."):
            return meta, "\n".join(lines[i + 1:])
        m = re.match(r"^([A-Za-z_][\w]*)\s*:\s*(.*)$", ln)
        if m and m.group(1) not in meta:
            meta[m.group(1)] = parse_value(m.group(2))
    return None, text


def dump_frontmatter(meta):
    out = ["---"]
    for k, v in meta.items():
        if isinstance(v, bool):
            s = "true" if v else "false"
        elif v is None:
            s = "null"
        elif isinstance(v, (list, dict)):
            s = json.dumps(v, ensure_ascii=False)
        else:
            s = str(v)
        out.append("%s: %s" % (k, s))
    out.append("---")
    return "\n".join(out)


def split_sections(body):
    """按 '## 标题' 切分正文，返回 [(title, content)] 保序。"""
    secs, title, buf = [], None, []
    for ln in body.splitlines():
        m = re.match(r"^##\s+(.+?)\s*$", ln)
        if m:
            if title is not None:
                secs.append((title, "\n".join(buf).strip()))
            title, buf = m.group(1), []
        elif title is not None:
            buf.append(ln)
    if title is not None:
        secs.append((title, "\n".join(buf).strip()))
    return secs


def get_section(body, name):
    for t, c in split_sections(body):
        if t == name or t.startswith(name):
            return c
    return None


def cjk_len(text):
    return len(re.sub(r"\s", "", text))


def read(path):
    return Path(path).read_text(encoding="utf-8", errors="replace")


def write(path, text):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(p)


def ch_num(ch_id):
    m = re.match(r"^ch_(\d{4})$", ch_id)
    if not m:
        die("非法章 id：%s（应为 ch_NNNN）" % ch_id)
    return int(m.group(1))


def die(msg, code=2):
    print("[错误] %s" % msg, file=sys.stderr)
    sys.exit(code)


def git(root, *args, check=False):
    try:
        r = subprocess.run(["git", "-C", str(root)] + list(args),
                           capture_output=True, text=True, timeout=30)
        if check and r.returncode != 0:
            print("[warn] git %s 失败：%s" % (" ".join(args), r.stderr.strip()[:200]))
        return r.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def git_autocommit(root, msg):
    if not (Path(root) / ".git").exists():
        return
    git(root, "add", "-A")
    git(root, "commit", "-m", msg, "-q")


# ---------------------------------------------------------------- 项目对象
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

    def threads(self):
        out = {}
        for f in sorted(self.p("threads").glob("thread_*.md")):
            meta, body = parse_frontmatter(read(f))
            out[f.stem] = {"meta": meta or {}, "body": body, "path": f}
        return out

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

    # ---- 台账
    def payoff_rows(self):
        f = self.p("ledgers", "payoff.tsv")
        rows = []
        if f.is_file():
            lines = read(f).splitlines()
            for ln in lines[1:]:
                c = ln.split("\t")
                if len(c) >= 5:
                    rows.append({"chapter": c[0], "payoff_id": c[1], "kind": c[2],
                                 "intent": c[3], "realized": c[4].strip() == "1"})
        return rows

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


# ---------------------------------------------------------------- 报告器
class Report:
    LEVELS = ("PASS", "WARN", "FAIL", "NEEDS_REVIEW", "SKIP")

    def __init__(self):
        self.items = []

    def add(self, level, name, details=None):
        assert level in self.LEVELS
        self.items.append((level, name, details or []))

    def render(self, title):
        counts = {k: 0 for k in self.LEVELS}
        print("== %s ==" % title)
        for level, name, details in self.items:
            counts[level] += 1
            if level == "PASS":
                continue
            print("[%s] %s" % (level, name))
            for d in details[:15]:
                print("        %s" % d)
            if len(details) > 15:
                print("        ... 另 %d 条" % (len(details) - 15))
        print("SUMMARY: %d PASS / %d FAIL / %d WARN / %d NEEDS_REVIEW / %d SKIP"
              % (counts["PASS"], counts["FAIL"], counts["WARN"],
                 counts["NEEDS_REVIEW"], counts["SKIP"]))
        return 1 if counts["FAIL"] else 0


# ---------------------------------------------------------------- init
def instantiate(template_name, replacements):
    text = read(TEMPLATES / template_name)
    for k, v in replacements.items():
        text = text.replace(k, v)
    return text


def cmd_init(args):
    root = Path(args.dir).resolve()
    if (root / "config.json").exists():
        die("目标已是项目：%s" % root)
    for d in ("tree", "chapters", "briefs", "entities", "threads", "ledgers/facts",
              "court/transcripts", "reviews", "data/feedback", "tasks", "state", "corpus"):
        (root / d).mkdir(parents=True, exist_ok=True)
    cfg = json.loads(read(TEMPLATES / "config.json"))
    cfg["name"] = args.name or root.name
    write(root / "config.json", json.dumps(cfg, ensure_ascii=False, indent=2))
    rep = {"[YYYY-MM-DDTHH:MM:SSZ]": NOW()}
    for t, dest in (("book.md", "tree/book.md"), ("style.md", "tree/style.md"),
                    ("world.md", "tree/world.md")):
        write(root / dest, instantiate(t, rep))
    write(root / "ledgers/timeline.tsv", "chapter\tstory_date\telapsed\tnote\n")
    write(root / "ledgers/payoff.tsv", "chapter\tpayoff_id\tkind\tintent\trealized\n")
    write(root / "ledgers/lessons.md", "# lessons（一行一课，编排者经 commit 附笔追加）\n")
    write(root / "entities/aliases.json", "{}\n")
    write(root / "tasks/queue.json", json.dumps({"next_seq": 1, "tasks": []}))
    if git(root, "init", "-q"):
        git_autocommit(root, "[init] 项目脚手架")
        print("git 仓库已初始化并完成首次提交")
    else:
        print("[warn] git 不可用，跳过版本化（单写者纪律降级为原子写入）")
    print("项目已创建：%s" % root)
    print("下一步：填写 tree/book.md、tree/world.md、tree/style.md（书庭产出），"
          "然后 tree set-status 置 committed")
    return 0


# ---------------------------------------------------------------- status
def cmd_status(args):
    proj = Project(find_root(args))
    chs = proj.chapters()
    cur = proj.cursor()
    ready = proj.buffer_ready()
    q = proj.queue()
    pend = [t for t in q["tasks"] if t["state"] in ("pending", "running", "blocked")]
    nodes = proj.tree_nodes()

    by_status = {}
    for c in chs:
        by_status.setdefault(c["meta"].get("status", "?"), []).append(c["id"])

    idx = {
        "generated_at": NOW(),
        "nodes": [{"id": n["meta"].get("id"), "kind": n["meta"].get("kind"),
                   "status": n["meta"].get("status"), "rev": n["meta"].get("rev")}
                  for n in nodes],
        "chapters": [{"id": c["id"], "status": c["meta"].get("status"),
                      "rev": c["meta"].get("rev")} for c in chs],
        "tasks": {"pending": len([t for t in q["tasks"] if t["state"] == "pending"]),
                  "blocked": len([t for t in q["tasks"] if t["state"] == "blocked"]),
                  "head": pend[:5]},
        "cursor": cur, "buffer_ready": ready,
    }
    write(proj.p("state", "index.json"), json.dumps(idx, ensure_ascii=False, indent=1))

    lines = ["# dashboard（生成物，禁手改）", "",
             "- 项目：%s ｜ 生成于 %s" % (proj.config.get("name", proj.root.name), NOW()),
             "- 游标：last_published=%(last_published)d  last_approved=%(last_approved)d"
             "  last_drafted=%(last_drafted)d" % cur,
             "- buffer(ready)=%d（target=%s）" % (ready, proj.config.get("buffer", {}).get("target")),
             "", "## 树节点"]
    for n in nodes:
        lines.append("- %s [%s] rev=%s" % (n["meta"].get("id"), n["meta"].get("status"),
                                           n["meta"].get("rev")))
    lines.append("")
    lines.append("## 章（按状态）")
    for st in CH_STATUS:
        if st in by_status:
            ids = by_status[st]
            lines.append("- %s ×%d：%s%s" % (st, len(ids), " ".join(ids[:8]),
                                             " …" if len(ids) > 8 else ""))
    lines.append("")
    lines.append("## 队列头（≤5）")
    if not pend:
        lines.append("- （空）")
    for t in pend[:5]:
        lines.append("- %s %s(%s) [%s] %s" % (t["id"], t["type"], t["target"],
                                              t["state"], t.get("note", "")))
    write(proj.p("state", "dashboard.md"), "\n".join(lines) + "\n")
    print("\n".join(lines))
    print("\n可恢复断点：task next → %s" % (next_task_id(q) or "（队列空）"))
    return 0


def next_task_id(q):
    done = {t["id"] for t in q["tasks"] if t["state"] == "done"}
    for t in q["tasks"]:
        if t["state"] == "pending" and all(b in done for b in t.get("blocked_on", [])):
            return t["id"]
    return None


# ---------------------------------------------------------------- tree
def cmd_tree(args):
    proj = Project(find_root(args))
    if args.tree_cmd == "show":
        for n in proj.tree_nodes():
            m = n["meta"]
            print("%-12s %-8s status=%-10s rev=%s" % (m.get("id"), m.get("kind"),
                                                      m.get("status"), m.get("rev")))
        for c in proj.chapters():
            m = c["meta"]
            print("%-12s chapter  status=%-10s rev=%s parent=%s"
                  % (c["id"], m.get("status"), m.get("rev"), m.get("parent")))
        return 0

    if args.tree_cmd == "set-status":
        path = proj.node_path(args.id)
        if not path or not path.is_file():
            die("节点不存在：%s" % args.id)
        meta, body = parse_frontmatter(read(path))
        kind = meta.get("kind")
        old = meta.get("status")
        new = args.status
        legal = {
            "node": {("empty", "draft"), ("draft", "committed"), ("committed", "stale"),
                     ("stale", "committed"), ("stale", "draft"),
                     ("draft", "archived"), ("committed", "archived")},
            "chapter": {("planned", "drafted"), ("drafted", "approved"),
                        ("approved", "published"), ("approved", "drafted"),
                        ("planned", "stale"), ("drafted", "stale"), ("approved", "stale"),
                        ("stale", "planned"), ("stale", "drafted"),
                        ("planned", "archived"), ("drafted", "archived")},
        }
        table = legal["chapter"] if kind == "chapter" else legal["node"]
        if (old, new) not in table:
            die("非法迁移：%s %s→%s（合法表见 protocol/formats.md §3）" % (args.id, old, new), 1)
        meta["status"] = new
        meta["updated_at"] = NOW()
        write(path, dump_frontmatter(meta) + "\n" + body.lstrip("\n"))
        print("%s: %s → %s" % (args.id, old, new))
        return 0

    # tree add
    kind, nid, parent = args.kind, args.id, args.parent
    rep = {"[YYYY-MM-DDTHH:MM:SSZ]": NOW()}
    if kind == "volume":
        if not re.match(r"^vol_\d{2}$", nid):
            die("volume id 应为 vol_NN")
        rep["[vol_01]"] = nid
        write(proj.p("tree", nid, "volume.md"), instantiate("volume.md", rep))
    elif kind == "arc":
        m = re.match(r"^arc_(\d{2})_(\d+)$", nid)
        if not m:
            die("arc id 应为 arc_NN_n")
        vol = parent or ("vol_" + m.group(1))
        rep.update({"[arc_01_1]": nid, "[vol_01]": vol})
        write(proj.p("tree", vol, nid + ".md"), instantiate("arc.md", rep))
    elif kind == "chapter":
        if not re.match(r"^ch_\d{4}$", nid):
            die("chapter id 应为 ch_NNNN")
        if not parent:
            die("chapter 需 --parent arc_NN_n")
        rep.update({"[ch_0001]": nid, "[arc_01_1]": parent})
        write(proj.p("chapters", nid + ".md"), instantiate("chapter.md", rep))
        write(proj.p("chapters", nid + ".task.json"), instantiate("chapter.task.json", rep))
    else:
        die("tree add 仅支持 volume|arc|chapter；实体用 entity new，线索用 thread new")
    print("已实例化 %s（%s）" % (nid, kind))
    return 0


# ---------------------------------------------------------------- task
def cmd_task(args):
    proj = Project(find_root(args))
    q = proj.queue()
    sub = args.task_cmd

    if sub == "add":
        if args.type not in TASK_TYPES:
            die("type 须为 %s" % "|".join(TASK_TYPES))
        if args.type == "revise_design" and not args.evidence:
            die("revise_design 必须带 --evidence（并先过 court/ 否决案台账，见 court.md §4）", 1)
        tid = "t_%06d" % q["next_seq"]
        q["next_seq"] += 1
        q["tasks"].append({"id": tid, "type": args.type, "target": args.target,
                           "state": "blocked" if args.blocked_on else "pending",
                           "blocked_on": args.blocked_on or [], "attempts": 0,
                           "note": args.note or "", "evidence": args.evidence or "",
                           "created_at": NOW(), "updated_at": NOW()})
        proj.save_queue(q)
        print(tid)
        return 0

    if sub == "next":
        tid = next_task_id(q)
        if not tid:
            print("（队列空或全部阻塞）")
            return 0
        t = proj.task(tid)
        print(json.dumps(t, ensure_ascii=False, indent=1))
        return 0

    if sub == "list":
        for t in q["tasks"]:
            if args.state and t["state"] != args.state:
                continue
            print("%s %-13s %-12s [%s] attempts=%d %s"
                  % (t["id"], t["type"], t["target"], t["state"],
                     t.get("attempts", 0), t.get("note", "")))
        return 0

    # start / done / fail
    t = proj.task(args.id)
    if not t:
        die("任务不存在：%s" % args.id)
    if sub == "start":
        t["state"] = "running"
    elif sub == "done":
        t["state"] = "done"
    elif sub == "fail":
        t["state"] = "failed"
        t["attempts"] = t.get("attempts", 0) + 1
        if t["type"] in ("write", "revise") and t["attempts"] >= 2:
            nid = "t_%06d" % q["next_seq"]
            q["next_seq"] += 1
            q["tasks"].append({"id": nid, "type": "revise_design",
                               "target": t["target"], "state": "pending",
                               "blocked_on": [], "attempts": 0,
                               "note": "自动升级：%s 修订达限" % t["id"],
                               "evidence": "见 %s note：%s" % (t["id"], args.note or ""),
                               "created_at": NOW(), "updated_at": NOW()})
            print("attempts 达限 → 自动追加 revise_design 任务 %s（formats §10）" % nid)
    if args.note:
        t["note"] = (t.get("note", "") + " | " + args.note).strip(" |")
    t["updated_at"] = NOW()
    # 保存（t 是副本，须回写）
    for i, x in enumerate(q["tasks"]):
        if x["id"] == t["id"]:
            q["tasks"][i] = t
    proj.save_queue(q)
    print("%s → %s" % (t["id"], t["state"]))
    return 0


# ---------------------------------------------------------------- entity / thread
def cmd_entity(args):
    proj = Project(find_root(args))
    sub = args.entity_cmd
    if sub == "new":
        m = re.match(r"^(char|item|loc|fac)_[a-z0-9_]+$", args.id)
        if not m:
            die("实体 id 应为 {char|item|loc|fac}_{slug}")
        etype = m.group(1)
        rep = {"[%s_slug]" % etype: args.id, "[YYYY-MM-DDTHH:MM:SSZ]": NOW()}
        write(proj.p("entities", args.id + ".md"),
              instantiate("entity-%s.md" % etype, rep))
        print("已建卡 %s" % args.id)
        return 0
    ents = proj.entities()
    if sub == "due":
        thr = proj.config.get("reconcile_every", 10)
        due = [e for e, v in ents.items()
               if (v["meta"].get("last_event_ch", 0) or 0)
               - (v["meta"].get("last_reconcile_ch", 0) or 0) >= thr]
        print("\n".join(due) if due else "（无到期实体）")
        return 0
    if args.id not in ents:
        die("实体不存在：%s" % args.id)
    ent = ents[args.id]
    if sub == "show":
        print(read(ent["path"]))
        return 0
    if sub == "log":
        print(get_section(ent["body"], "事件日志") or "（空）")
        return 0
    if sub == "update":
        new_text = re.sub(r"^##\s*现状\s*\n+", "", read(args.file).strip())
        out = []
        for t, c in split_sections(ent["body"]):
            out.append("## %s\n\n%s" % (t, new_text if t.startswith("现状") else c))
        meta = ent["meta"]
        meta["last_reconcile_ch"] = proj.cursor()["last_drafted"]
        meta["updated_at"] = NOW()
        meta["rev"] = (meta.get("rev") or 1) + 1
        write(ent["path"], dump_frontmatter(meta) + "\n\n" + "\n\n".join(out) + "\n")
        print("现状节已替换，last_reconcile_ch=%d" % meta["last_reconcile_ch"])
        return 0
    return 2


def cmd_thread(args):
    proj = Project(find_root(args))
    if not re.match(r"^thread_[a-z0-9_]+$", args.id):
        die("线索 id 应为 thread_{slug}")
    rep = {"[thread_slug]": args.id, "[YYYY-MM-DDTHH:MM:SSZ]": NOW()}
    text = instantiate("thread.md", rep)
    if args.kind:
        if args.kind not in THREAD_KINDS:
            die("thread_kind 须为 %s" % "|".join(THREAD_KINDS))
        text = text.replace("thread_kind: fuse", "thread_kind: " + args.kind)
    write(proj.p("threads", args.id + ".md"), text)
    print("已登记线索 %s" % args.id)
    return 0


# ---------------------------------------------------------------- brief
def tail_chars(text, n):
    t = text.strip()
    return t[-n:] if len(t) > n else t


def cmd_brief(args):
    proj = Project(find_root(args))
    ch_id = args.ch_id
    task = proj.chapter_task(ch_id)
    if not task:
        die("缺任务卡 chapters/%s.task.json（先 tree add chapter + 排批补全）" % ch_id, 1)
    budget = proj.config.get("brief_budget_chars", 24000)
    num = ch_num(ch_id)
    prov = []  # (资产, rev, 用途)

    # §1 文风
    style_p = proj.p("tree", "style.md")
    style_meta, style_body = parse_frontmatter(read(style_p))
    s1 = "\n\n".join(filter(None, [
        "### 叙述基准\n" + (get_section(style_body, "叙述基准") or ""),
        "### 口癖与句式禁忌（命中即违规）\n" + (get_section(style_body, "口癖与句式禁忌") or ""),
        "### 比喻与意象纪律\n" + (get_section(style_body, "比喻与意象纪律") or ""),
        "### 范文锚\n" + (get_section(style_body, "范文锚") or ""),
    ]))
    prov.append(("tree/style.md", style_meta.get("rev"), "§1 文风与禁忌"))

    # §2 直接上文
    parts2 = []
    prev_id = "ch_%04d" % (num - 1)
    prev_p = proj.p("chapters", prev_id + ".md")
    if num > 1 and prev_p.is_file():
        _, prev_body = parse_frontmatter(read(prev_p))
        prev_text = prev_body.split("## 正文", 1)[-1]
        parts2.append("### 前章（%s）尾 500 字\n%s" % (prev_id, tail_chars(prev_text, 500)))
        prov.append(("chapters/%s.md" % prev_id, "-", "§2 前章尾"))
    for i in range(max(1, num - 3), num):
        pid = "ch_%04d" % i
        m = proj.chapter_meta_json(pid)
        if m and m.get("summary_after"):
            parts2.append("- %s 概要：%s" % (pid, m["summary_after"]))
            prov.append(("chapters/%s.meta.json" % pid, "-", "§2 summary 链"))
    s2 = "\n\n".join(parts2) or "（首章，无上文）"

    # §3 实体状态卡
    parts3 = []
    ents = proj.entities()
    for ref in task.get("cast", []):
        eid = proj.resolve_entity(ref)
        if not eid or eid not in ents:
            parts3.append("- 【缺卡】%s（资料员应报缺料）" % ref)
            continue
        e = ents[eid]
        setting = get_section(e["body"], "设定") or ""
        setting = "\n".join(setting.splitlines()[:14])
        status_sec = get_section(e["body"], "现状") or ""
        log = get_section(e["body"], "事件日志") or ""
        log_tail = "\n".join([l for l in log.splitlines() if l.strip().startswith("-")][-3:])
        parts3.append("### %s\n设定要点：\n%s\n\n现状：\n%s\n\n最近事件：\n%s"
                      % (eid, setting, status_sec, log_tail or "（无）"))
        prov.append(("entities/%s.md" % eid, e["meta"].get("rev"), "§3 状态卡"))
    s3 = "\n\n".join(parts3) or "（任务卡未列 cast）"

    # §4 活跃线索
    parts4 = []
    threads = proj.threads()
    listed = {t["id"] for t in task.get("threads", [])}
    for tid, th in threads.items():
        m = th["meta"]
        relevant = tid in listed or (m.get("state") in ("planted", "active", "tangled",
                                                        "payoff_ready")
                                     and m.get("must_not_drop"))
        if not relevant:
            continue
        stmt = get_section(th["body"], "陈述") or ""
        log = get_section(th["body"], "推进日志") or ""
        log_tail = "\n".join([l for l in log.splitlines() if l.strip().startswith("-")][-2:])
        parts4.append("- **%s** [%s/%s]%s：%s\n  最近推进：%s"
                      % (tid, m.get("thread_kind"), m.get("state"),
                         "【must_not_drop】" if m.get("must_not_drop") else "",
                         stmt.splitlines()[0] if stmt else "", log_tail or "（无）"))
        prov.append(("threads/%s.md" % tid, m.get("rev"), "§4 线索"))
    s4 = "\n".join(parts4) or "（无活跃线索命中）"

    # §5 弧内位置
    s5 = "（弧计划缺失）"
    arc_id = task.get("arc")
    arc_p = proj.node_path(arc_id) if arc_id else None
    if arc_p and arc_p.is_file():
        arc_meta, arc_body = parse_frontmatter(read(arc_p))
        chain = get_section(arc_body, "因果链") or ""
        alloc = get_section(arc_body, "章分配草案") or ""
        rows = [l for l in alloc.splitlines()
                if re.search(r"ch_\d{4}", l)]
        near = [l for l in rows if any(("ch_%04d" % i) in l
                                       for i in (num - 1, num, num + 1))]
        s5 = "### 弧因果链（%s）\n%s\n\n### 本章前后位置\n%s" % (
            arc_id, chain, "\n".join(near) or "（章分配草案未含本章）")
        prov.append((str(arc_p.relative_to(proj.root)), arc_meta.get("rev"), "§5 弧内位置"))

    # §6 相关事实与设定
    parts6 = []
    cast_ids = {proj.resolve_entity(r) for r in task.get("cast", [])} - {None}
    for f in sorted(proj.p("ledgers", "facts").glob("*.json")):
        data = json.loads(read(f))
        retcons = {r.get("old_fact_id"): r for r in data.get("retcons", [])}
        for fact in data.get("facts", []):
            if set(fact.get("entity_ids", [])) & cast_ids:
                spoiler = "【读者未知，只可潜台词】" if fact.get("spoiler") else ""
                sup = fact.get("superseded_by")
                line = "- %s%s（%s，ch%s）" % (spoiler, fact.get("fact"),
                                              fact.get("id"), fact.get("revealed_ch"))
                if sup:
                    r = retcons.get(fact.get("id"), {})
                    line += "\n  ↳【已被覆盖】新事实：%s（策略 %s，%s）" % (
                        r.get("new_fact", "?"), r.get("strategy", "?"),
                        r.get("decision_ref", "?"))
                parts6.append(line)
        prov.append((str(f.relative_to(proj.root)), "-", "§6 事实"))
    world_p = proj.p("tree", "world.md")
    if world_p.is_file():
        wmeta, wbody = parse_frontmatter(read(world_p))
        parts6.append("### 世界核心规则\n" + (get_section(wbody, "核心规则") or ""))
        prov.append(("tree/world.md", wmeta.get("rev"), "§6 世界规则"))
    s6 = "\n".join(parts6) or "（无相关事实）"

    # §7 写作提示（≤60 行）
    lessons_p = proj.p("ledgers", "lessons.md")
    lessons = [l for l in read(lessons_p).splitlines() if l.startswith("- ")][-5:] \
        if lessons_p.is_file() else []
    s7 = "\n".join([
        "核心纪律速记（全文见 rubrics/prose-disease.md）：",
        "- 每 500 字 ≥1 个新信息或价值变化；章尾钩落最后 150 字内，钩前收束 ≤1 句",
        "- 开篇 300 字内反预期信号；不原地复述上章钩子",
        "- 关键场面禁概述体；打斗远中近推拉、交锋段均句长 ≤15 字",
        "- 禁发明简报外专名；缺料写 issues，不脑补",
        "",
        "近期教训（lessons 台账尾 5 条）：",
    ] + (lessons or ["- （暂无）"]))
    if lessons:
        prov.append(("ledgers/lessons.md", "-", "§7 教训"))

    # §8 回写契约
    s8 = ("提交格式：最终回复两段——【正文】章文件（信封+## 正文）；【writeback】如下 schema 的"
          "JSON 块：\n\n```json\n" + read(TEMPLATES / "chapter.meta.json").strip() + "\n```")

    prev_brief = proj.p("briefs", ch_id + ".brief.md")
    brief_rev = 1
    if prev_brief.is_file():
        m = re.search(r"<!-- brief_rev: (\d+) -->", read(prev_brief))
        brief_rev = (int(m.group(1)) if m else 0) + 1

    sections = {
        "0 任务卡": "```json\n" + json.dumps(task, ensure_ascii=False, indent=1) + "\n```",
        "1 文风与禁忌": s1, "2 直接上文": s2, "3 出场实体状态卡": s3,
        "4 活跃线索": s4, "5 弧内位置": s5, "6 相关事实与设定": s6,
        "7 写作提示": s7, "8 回写契约": s8,
    }
    trimmed = []
    def render():
        head = ["<!-- chapter: %s -->" % ch_id, "<!-- brief_rev: %d -->" % brief_rev,
                "<!-- compiled_at: %s -->" % NOW(), "<!-- budget_chars: %d -->" % budget]
        parts = ["\n".join(head)]
        for name, content in sections.items():
            parts.append("## %s\n\n%s" % (name, content))
        prov_lines = ["| 资产 | rev | 用途 |", "|---|---|---|"]
        prov_lines += ["| %s | %s | %s |" % p for p in prov]
        if trimmed:
            prov_lines.append("| （裁剪） | - | 超预算已裁剪：%s |" % "、".join(trimmed))
        parts.append("## 附 溯源\n\n" + "\n".join(prov_lines))
        return "\n\n".join(parts) + "\n"

    text = render()
    for sec in ("7 写作提示", "6 相关事实与设定", "4 活跃线索"):
        if len(text) <= budget:
            break
        sections[sec] = "（超预算已裁剪；原始来源见溯源表）"
        trimmed.append(sec)
        text = render()
    write(prev_brief, text)
    git_autocommit(proj.root, "[brief] %s rev%d（保证 spawn 前基线干净）" % (ch_id, brief_rev))
    print("简报已生成：briefs/%s.brief.md（%d 字符 / 预算 %d%s）"
          % (ch_id, len(text), budget, "，已裁剪：" + "、".join(trimmed) if trimmed else ""))
    return 0


# ---------------------------------------------------------------- check --unit
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


def sentences_of(text):
    return [s.strip() for s in re.split(r"[。！？!?…\n]+", text) if cjk_len(s) >= 4]


def char_ngrams(text, n):
    chars = "".join(CJK_RE.findall(text))
    return [chars[i:i + n] for i in range(len(chars) - n + 1)]


def check_unit(proj, ch_id, candidate=None, writeback=None, rep=None):
    rep = rep or Report()
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

    # 跨章 12-gram 指纹
    cache = proj.ngram_cache()
    cand12 = set(char_ngrams(text, 12))
    dup = []
    for cid, fps in cache.items():
        if cid == ch_id:
            continue
        inter = cand12 & set(fps)
        for s in list(inter)[:3]:
            dup.append("与 %s 重复：「%s…」" % (cid, s))
    if dup:
        rep.add("WARN", "跨章 12 字级重复（自我复读/套话嫌疑）", dup[:10])
    else:
        rep.add("PASS", "跨章 12-gram 零重复")

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
        route = proj.config.get("route", "web")
        close_ok = bool(wb.get("hooks_realized", {}).get("close"))
        if route == "web" and not close_ok:
            if wb.get("issues"):
                rep.add("WARN", "hooks_realized.close=false，但 issues 已说明（人工裁定）")
            else:
                rep.add("FAIL", "route=web 章尾钩必须落实（close=false 且 issues 未说明）")
        task = proj.chapter_task(ch_id)
        if task:
            quota_n = len(task.get("payoff_quota", []))
            bad = [pid for pid in wb.get("payoff_realized", [])
                   if not re.match(r"^payoff_\d{4}_\d+$", pid)
                   or int(pid.rsplit("_", 1)[1]) > max(quota_n, 0)]
            if bad:
                rep.add("FAIL", "payoff_realized 越界/格式错（⊆ quota，id=payoff_章号_序）", bad)
        wc = wb.get("word_count", 0)
        if isinstance(wc, int) and wc and abs(wc - n_chars) > max(50, n_chars * 0.1):
            rep.add("WARN", "writeback.word_count=%d 与实测 %d 偏差 >10%%" % (wc, n_chars))

    for item in UNIT_NEEDS_REVIEW:
        rep.add("NEEDS_REVIEW", item)
    return rep


# ---------------------------------------------------------------- check --window
def check_window(proj, rep=None):
    rep = rep or Report()
    chs = {ch_num(c["id"]): c for c in proj.chapters()
           if c["meta"].get("status") in ("drafted", "approved", "published")}
    if not chs:
        rep.add("SKIP", "无成稿章，窗口检查跳过")
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

    v3 = []
    for i in nums:
        win = [i, i + 1, i + 2]
        if all(n in chs for n in win):
            if not any(realized.get(n) for n in win):
                v3.append("ch%04d–ch%04d 零已兑现爽点" % (i, i + 2))
    if v3:
        rep.add("FAIL", "3 章小爽窗口破（rubrics/payoff.md §二）", v3)
    else:
        rep.add("PASS", "3 章小爽窗口全绿（%d 章）" % len(nums))

    v10 = []
    for i in nums:
        win = list(range(i, i + 10))
        if all(n in chs for n in win):
            if not any(big.get(n) for n in win):
                v10.append("ch%04d–ch%04d 无处境级释放（upgrade/reveal/reversal）" % (i, i + 9))
    if v10:
        rep.add("FAIL", "10 章大爽窗口破", v10[:5])
    elif len(nums) >= 10:
        rep.add("PASS", "10 章大爽窗口全绿")
    else:
        rep.add("SKIP", "成稿 <10 章，跳过大爽窗口")

    # promise 余额
    threads = proj.threads()
    promises = [t for t in threads.values()
                if t["meta"].get("thread_kind") == "promise"
                and t["meta"].get("state") in ("planted", "active", "tangled", "payoff_ready")]
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

    # 时间线
    tl = proj.p("ledgers", "timeline.tsv")
    neg = []
    if tl.is_file():
        for ln in read(tl).splitlines()[1:]:
            c = ln.split("\t")
            if len(c) >= 3 and c[2].strip().startswith("-"):
                neg.append("%s elapsed=%s" % (c[0], c[2]))
    if neg:
        rep.add("FAIL", "时间线出现负 elapsed", neg)
    else:
        rep.add("PASS", "时间线 elapsed 非负")

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
    if not any(l == "FAIL" and n.startswith("节点") for l, n, _ in rep.items):
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

    # threads 纪律
    th_fails = []
    for tid, t in proj.threads().items():
        m = t["meta"]
        if m.get("thread_kind") not in THREAD_KINDS:
            th_fails.append("%s thread_kind 非法" % tid)
        if m.get("state") not in THREAD_STATES:
            th_fails.append("%s state 非法：%s" % (tid, m.get("state")))
        if m.get("must_not_drop") and m.get("state") == "dropped":
            body = t["body"]
            if not re.search(r"dec_\d{3}", body):
                th_fails.append("%s：must_not_drop 线被 dropped 且无 decision 引用" % tid)
    if th_fails:
        rep.add("FAIL", "线索纪律", th_fails)
    else:
        rep.add("PASS", "线索纪律合规（%d 条）" % len(proj.threads()))

    # facts schema + superseded 引用
    f_fails = []
    for f in sorted(proj.p("ledgers", "facts").glob("*.json")):
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

    # published 连续性
    pub = sorted(ch_num(c["id"]) for c in proj.chapters()
                 if c["meta"].get("status") == "published")
    if pub and pub != list(range(pub[0], pub[0] + len(pub))):
        rep.add("FAIL", "published 章不连续（存在空洞）",
                ["published: %s" % pub])
    elif pub:
        rep.add("PASS", "published 连续（%d–%d）" % (pub[0], pub[-1]))

    # queue targets
    q_fails = []
    known = {c["id"] for c in proj.chapters()} | set(ents) | set(proj.threads()) \
        | {n["meta"].get("id") for n in proj.tree_nodes()}
    for t in proj.queue()["tasks"]:
        tgt = t.get("target", "")
        if tgt and tgt not in known and not tgt.startswith("vol_"):
            q_fails.append("%s target=%s 不存在" % (t["id"], tgt))
    if q_fails:
        rep.add("WARN", "队列 target 悬空", q_fails)
    else:
        rep.add("PASS", "队列 target 全部可解析")
    return rep


def cmd_check(args):
    proj = Project(find_root(args))
    rep = Report()
    if args.unit:
        check_unit(proj, args.unit, args.candidate, args.writeback, rep)
        return rep.render("check --unit %s" % args.unit)
    if args.window:
        check_window(proj, rep)
        return rep.render("check --window")
    check_project(proj, rep)
    return rep.render("check --project")


# ---------------------------------------------------------------- commit
def apply_writeback(proj, ch_id, wb):
    """continuity_delta → 实体事件日志；thread_ops → 推进日志+state；payoff/timeline 台账；ngram。"""
    num = ch_num(ch_id)
    ents = proj.entities()
    warns = []
    for delta in wb.get("continuity_delta", []):
        for ref in delta.get("entity_ids", []):
            eid = proj.resolve_entity(ref)
            if not eid or eid not in ents:
                warns.append("实体 %s 不存在，事件日志未登记（补卡后重跑 reconcile）" % ref)
                continue
            e = ents[eid]
            body = e["body"].rstrip() + "\n- %s: %s\n" % (ch_id, delta.get("fact", ""))
            meta = e["meta"]
            meta["last_event_ch"] = num
            meta["updated_at"] = NOW()
            write(e["path"], dump_frontmatter(meta) + "\n" + body.lstrip("\n"))
            ents = proj.entities()  # 重载，防同章多条
    threads = proj.threads()
    STATE_AFTER = {"plant": "planted", "advance": "active",
                   "tangle": "tangled", "payoff": "paid_off"}
    for op in wb.get("thread_ops", []):
        tid = op.get("id")
        if tid not in threads:
            warns.append("线索 %s 不存在，推进未登记" % tid)
            continue
        t = threads[tid]
        if op.get("op") not in THREAD_OPS:
            warns.append("线索 %s 非法 op：%s" % (tid, op.get("op")))
            continue
        body = t["body"].rstrip() + "\n- %s: %s %s\n" % (ch_id, op["op"], op.get("note", ""))
        meta = t["meta"]
        meta["state"] = STATE_AFTER[op["op"]]
        meta["updated_at"] = NOW()
        write(t["path"], dump_frontmatter(meta) + "\n" + body.lstrip("\n"))
        threads = proj.threads()
    # payoff 台账
    task = proj.chapter_task(ch_id) or {}
    quota = task.get("payoff_quota", [])
    realized = set(wb.get("payoff_realized", []))
    with open(proj.p("ledgers", "payoff.tsv"), "a", encoding="utf-8") as f:
        for i, q in enumerate(quota, 1):
            pid = "payoff_%04d_%d" % (num, i)
            f.write("%s\t%s\t%s\t%s\t%d\n" % (ch_id, pid, q.get("kind", "other"),
                                              q.get("intent", ""), 1 if pid in realized else 0))
    # timeline
    ta = wb.get("time_advance", {})
    with open(proj.p("ledgers", "timeline.tsv"), "a", encoding="utf-8") as f:
        f.write("%s\t%s\t%s\t\n" % (ch_id, ta.get("story_date", ""), ta.get("elapsed", "")))
    return warns


def update_ngram_cache(proj, ch_id, text):
    cache = proj.ngram_cache()
    cache[ch_id] = sorted(set(char_ngrams(text, 12)))
    window = proj.config.get("ngram_window_chapters", 30)
    keys = sorted(cache, key=lambda k: ch_num(k) if re.match(r"ch_\d{4}$", k) else 0)
    for k in keys[:-window]:
        cache.pop(k, None)
    write(proj.p("state", "ngram_cache.json"), json.dumps(cache, ensure_ascii=False))


def route_staged_file(proj, meta):
    """按 staged 文件 meta 决定目标路径（id 驱动）。"""
    kind, fid = meta.get("kind"), meta.get("id", "")
    if kind in ("book", "style", "world"):
        return proj.p("tree", kind + ".md")
    if kind == "volume":
        return proj.p("tree", fid, "volume.md")
    if kind == "arc":
        return proj.node_path(fid)
    if kind == "entity":
        return proj.p("entities", fid + ".md")
    if kind == "thread":
        return proj.p("threads", fid + ".md")
    if kind == "decision":
        return proj.p("court", fid + ".md")
    if kind == "review":
        depth = meta.get("depth", "deep")
        return proj.p("reviews", "%s.%s.md" % (meta.get("chapter", fid), depth))
    return None


def cmd_commit(args):
    proj = Project(find_root(args))
    t = proj.task(args.task_id)
    if not t:
        die("任务不存在：%s" % args.task_id)
    ttype = t["type"]
    msg = args.m or ""

    if ttype in ("write", "revise"):
        if not (args.chapter and args.writeback):
            die("write/revise 需 --chapter <候选章文件> --writeback <json>")
        ch_id = t["target"]
        rep = check_unit(proj, ch_id, args.chapter, args.writeback)
        code = rep.render("commit 前置机检（%s）" % ch_id)
        if code != 0:
            print("[拒绝] 机检不绿，未落盘（问题清单并入修订循环，pipeline §2）")
            return 1
        exist_p = proj.p("chapters", ch_id + ".md")
        old_meta = parse_frontmatter(read(exist_p))[0] if exist_p.is_file() else {}
        if ttype == "revise" and old_meta.get("status") == "published":
            die("published 章不可 revise——走 serial-ops.md §3 retcon", 1)
        cand_meta, cand_body = parse_frontmatter(read(args.chapter))
        wb = json.loads(read(args.writeback))
        text = cand_body.split("## 正文", 1)[-1]
        new_meta = {
            "id": ch_id, "kind": "chapter", "status": "drafted",
            "rev": (old_meta.get("rev") or 0) + 1 if ttype == "revise"
                   else max(old_meta.get("rev") or 1, 1),
            "parent": cand_meta.get("parent") or old_meta.get("parent"),
            "updated_at": NOW(),
            "title": cand_meta.get("title", old_meta.get("title", "")),
            "word_count": cjk_len(text),
        }
        write(exist_p, dump_frontmatter(new_meta) + "\n\n## 正文\n" + text.strip() + "\n")
        write(proj.p("chapters", ch_id + ".meta.json"),
              json.dumps(wb, ensure_ascii=False, indent=1))
        warns = apply_writeback(proj, ch_id, wb)
        update_ngram_cache(proj, ch_id, text)
        for w in warns:
            print("[warn] " + w)
        git_autocommit(proj.root, "[%s] %s(%s): %s" % (args.task_id, ttype, ch_id, msg))
        print("已落盘：%s（status=drafted, rev=%d）+ meta.json + 台账/日志/ngram"
              % (ch_id, new_meta["rev"]))
        return 0

    if ttype in ("design", "revise_design", "review_deep"):
        if not args.file:
            die("%s 需 --file <staged 文件> [...]" % ttype)
        if ttype == "revise_design" and not t.get("evidence"):
            die("revise_design 任务缺 evidence（先过否决案台账，court.md §4）", 1)
        main_done = False
        for fpath in args.file:
            meta, body = parse_frontmatter(read(fpath))
            if meta is None:
                die("staged 文件无信封：%s" % fpath, 1)
            target = route_staged_file(proj, meta)
            if target is None:
                die("无法路由 kind=%s 的文件（id=%s）" % (meta.get("kind"), meta.get("id")), 1)
            if meta.get("kind") in NODE_KINDS:
                req = REQUIRED_SECTIONS.get(meta["kind"], [])
                titles = [x for x, _ in split_sections(body)]
                missing = [s for s in req
                           if not any(x == s or x.startswith(s) for x in titles)]
                empty = [s for s in req
                         if not missing and not (get_section(body, s) or "").strip()]
                if missing or empty:
                    die("design 校验失败 %s：缺节 %s / 空节 %s"
                        % (meta.get("id"), missing, empty), 1)
                meta["status"] = "committed"
                meta["updated_at"] = NOW()
                main_done = True
            if meta.get("kind") == "review" and meta.get("verdict") == "escalate":
                q = proj.queue()
                nid = "t_%06d" % q["next_seq"]
                q["next_seq"] += 1
                q["tasks"].append({"id": nid, "type": "revise_design",
                                   "target": meta.get("chapter", ""), "state": "pending",
                                   "blocked_on": [], "attempts": 0,
                                   "note": "深评 escalate 自动开单",
                                   "evidence": "review %s" % meta.get("id"),
                                   "created_at": NOW(), "updated_at": NOW()})
                proj.save_queue(q)
                print("verdict=escalate → 自动开 revise_design 任务 %s" % nid)
            write(target, dump_frontmatter(meta) + "\n" + body.lstrip("\n"))
            print("已落盘 → %s" % target.relative_to(proj.root))
        if ttype == "revise_design" and main_done:
            # 受影响下游标 stale
            node_id = t["target"]
            stale = []
            for n in proj.tree_nodes():
                if n["meta"].get("parent") == node_id \
                        and n["meta"].get("status") in ("draft", "committed"):
                    n["meta"]["status"] = "stale"
                    n["meta"]["updated_at"] = NOW()
                    write(n["path"], dump_frontmatter(n["meta"]) + "\n" + n["body"].lstrip("\n"))
                    stale.append(n["meta"].get("id"))
            for c in proj.chapters():
                if c["meta"].get("parent") == node_id \
                        and c["meta"].get("status") in ("planned", "drafted", "approved"):
                    c["meta"]["status"] = "stale"
                    c["meta"]["updated_at"] = NOW()
                    write(c["path"], dump_frontmatter(c["meta"]) + "\n" + c["body"].lstrip("\n"))
                    stale.append(c["id"])
            if stale:
                print("下游已标 stale：%s（修复后回原 status）" % " ".join(stale))
        git_autocommit(proj.root, "[%s] %s(%s): %s" % (args.task_id, ttype, t["target"], msg))
        return 0

    die("commit 暂支持 write|revise|design|revise_design|review_deep；"
        "publish 用 publish 命令，reconcile 用 entity update", 2)


# ---------------------------------------------------------------- publish / ledger
def cmd_publish(args):
    proj = Project(find_root(args))
    frm = ch_num(args.ch_from)
    to = ch_num(args.ch_to) if args.ch_to else frm
    cur = proj.cursor()
    if frm != cur["last_published"] + 1:
        die("连续性谓词失败：应从 ch_%04d 起（当前 last_published=%d），无绕过开关"
            % (cur["last_published"] + 1, cur["last_published"]), 1)
    chs = {ch_num(c["id"]): c for c in proj.chapters()}
    not_ok = [n for n in range(frm, to + 1)
              if n not in chs or chs[n]["meta"].get("status") != "approved"]
    if not_ok:
        die("区间含非 approved 章：%s" % ["ch_%04d" % n for n in not_ok], 1)
    if cur["last_published"] == 0:
        need = proj.config.get("buffer", {}).get("min_before_publish", 1)
        if proj.buffer_ready() < need:
            die("首发前 ready=%d < min_before_publish=%d" % (proj.buffer_ready(), need), 1)
    for n in range(frm, to + 1):
        c = chs[n]
        c["meta"]["status"] = "published"
        c["meta"]["updated_at"] = NOW()
        write(c["path"], dump_frontmatter(c["meta"]) + "\n" + c["body"].lstrip("\n"))
    git_autocommit(proj.root, "[publish] ch_%04d..ch_%04d" % (frm, to))
    print("已发布 ch_%04d..ch_%04d；发布后 buffer ready=%d" % (frm, to, proj.buffer_ready()))
    return 0


def cmd_ledger(args):
    proj = Project(find_root(args))
    if args.which == "payoff":
        for r in proj.payoff_rows():
            print("%s %s %-9s realized=%d %s"
                  % (r["chapter"], r["payoff_id"], r["kind"],
                     r["realized"], r["intent"]))
    elif args.which == "promise":
        for tid, t in proj.threads().items():
            m = t["meta"]
            if m.get("thread_kind") == "promise":
                print("%s [%s] must_not_drop=%s plant_ch=%s payoff_planned=%s"
                      % (tid, m.get("state"), m.get("must_not_drop"),
                         m.get("plant_ch"), m.get("payoff_planned")))
    else:
        f = proj.p("ledgers", "timeline.tsv")
        print(read(f) if f.is_file() else "（空）")
    return 0


# ---------------------------------------------------------------- main
def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="novel.py",
        description="novel-orchestrator 项目 CLI（契约见 protocol/formats.md；"
                    "实现覆盖表见 tools/README.md）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="退出码：0=通过（可含 WARN/NEEDS_REVIEW）；1=FAIL/校验拒绝；2=用法错误。\n"
               "典型循环：init → tree add → task add write → brief → (写作) →\n"
               "check --unit --candidate --writeback → commit → check --window →\n"
               "tree set-status approved → publish。未覆盖命令（retcon/checkpoint/report）\n"
               "按 protocol/serial-ops.md 人工执行，见 tools/README.md 覆盖表。")
    ap.add_argument("--root", help="项目根（默认从 cwd 向上探测 config.json+tree/）")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("init", help="脚手架新项目（+git init）")
    p.add_argument("dir")
    p.add_argument("--name")

    sub.add_parser("status", help="重算 index/dashboard 并打印（可恢复断点）")
    sub.add_parser("fsck", help="= check --project")

    p = sub.add_parser("tree", help="树节点：add/show/set-status")
    ts = p.add_subparsers(dest="tree_cmd", required=True)
    q = ts.add_parser("add")
    q.add_argument("kind", choices=["volume", "arc", "chapter"])
    q.add_argument("id")
    q.add_argument("--parent")
    q = ts.add_parser("show")
    q.add_argument("id", nargs="?")
    q = ts.add_parser("set-status")
    q.add_argument("id")
    q.add_argument("status")

    p = sub.add_parser("task", help="任务队列：add/next/list/start/done/fail")
    ts = p.add_subparsers(dest="task_cmd", required=True)
    q = ts.add_parser("add")
    q.add_argument("type")
    q.add_argument("target")
    q.add_argument("--note")
    q.add_argument("--blocked-on", dest="blocked_on", action="append")
    q.add_argument("--evidence")
    ts.add_parser("next")
    q = ts.add_parser("list")
    q.add_argument("--state")
    for name in ("start", "done", "fail"):
        q = ts.add_parser(name)
        q.add_argument("id")
        q.add_argument("--note")

    p = sub.add_parser("entity", help="实体卡：new/show/log/due/update")
    ts = p.add_subparsers(dest="entity_cmd", required=True)
    for name in ("new", "show", "log"):
        q = ts.add_parser(name)
        q.add_argument("id")
    ts.add_parser("due")
    q = ts.add_parser("update")
    q.add_argument("id")
    q.add_argument("--file", required=True)

    p = sub.add_parser("thread", help="线索登记：thread new <id> [--kind]")
    ts = p.add_subparsers(dest="thread_cmd", required=True)
    q = ts.add_parser("new")
    q.add_argument("id")
    q.add_argument("--kind")

    p = sub.add_parser("brief", help="机械装配十节简报（预算裁剪+溯源）")
    p.add_argument("ch_id")

    p = sub.add_parser("check", help="三套断言集：--unit/--window/--project")
    p.add_argument("--unit", metavar="CH_ID")
    p.add_argument("--candidate", help="未落盘候选章文件（staging 机检）")
    p.add_argument("--writeback", help="未落盘 writeback JSON")
    p.add_argument("--window", action="store_true")
    p.add_argument("--project", action="store_true")

    p = sub.add_parser("commit", help="唯一写路径：校验全过才落盘")
    p.add_argument("task_id")
    p.add_argument("--chapter")
    p.add_argument("--writeback")
    p.add_argument("--file", action="append")
    p.add_argument("-m", default="")

    p = sub.add_parser("publish", help="连续性谓词；approved→published")
    p.add_argument("ch_from")
    p.add_argument("ch_to", nargs="?")

    p = sub.add_parser("ledger", help="台账视图：payoff|promise|timeline")
    p.add_argument("which", choices=["payoff", "promise", "timeline"])

    args = ap.parse_args(argv)
    if args.cmd == "check" and not (args.unit or args.window or args.project):
        ap.error("check 需 --unit <ch>|--window|--project 之一")

    dispatch = {
        "init": cmd_init, "status": cmd_status, "tree": cmd_tree, "task": cmd_task,
        "entity": cmd_entity, "thread": cmd_thread, "brief": cmd_brief,
        "check": cmd_check, "commit": cmd_commit, "publish": cmd_publish,
        "ledger": cmd_ledger,
        "fsck": lambda a: check_project(Project(find_root(a))).render("fsck"),
    }
    return dispatch[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
