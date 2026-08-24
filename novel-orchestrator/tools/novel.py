#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""novel.py — novel-orchestrator 项目 CLI（python3 stdlib only）。

实现 protocol/formats.md 的项目侧文件契约与 §15 CLI：

  init <dir> [--name X]              脚手架 + （可选）git init
  status                             重算 index/dashboard 并打印（可恢复断点；章级增量）
  tree add <kind> <id> [--parent P]  由模板实例化节点（volume/arc/chapter）
  tree show [id] / tree set-status <id> <status> [--evidence E]
  task add <type> <target> [...] / next / list / start / done / fail / reset / archive
  entity new <id> / show <id> / log <id> / due / update <id> --file F
  thread new <id> [--kind K]
  brief <ch_id>                      机械装配十节简报（预算裁剪 + 溯源）
  check --unit <ch> [--candidate F --writeback F] | --window [--since CH] | --project
  check --leak <候选章> --brief <简报>   简报外专名泄漏扫描
  commit <task_id> [--chapter F --writeback F] [--file F ...] [--draft] [-m 摘要]
  publish <ch_from> [<ch_to>]        连续性谓词；approved → published
  retcon <old_fact_id> --new … --strategy … --decision dec_id
  report volume <vol_NN>             汇编卷报告（exports 对账底稿 + 台账统计）
  checkpoint <vol_NN>                卷末结账：校验对账三态 + 下卷 imports 预填
  adopt <file> --as ch_NNNN          收编外部文稿为项目章（protocol/adopt.md）
  ledger payoff|promise|timeline|power   台账窗口视图
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
THREAD_OPS = ("plant", "advance", "payoff", "tangle", "ready")
THREAD_KINDS = ("fuse", "subplot", "relationship", "mystery", "promise", "other")
THREAD_STATES = ("planted", "active", "tangled", "payoff_ready", "paid_off", "dropped")
THREAD_TERMINAL = ("paid_off", "dropped")
THREAD_LIVE = ("planted", "active", "tangled", "payoff_ready")
BIG_PAYOFF_KINDS = ("upgrade", "reveal", "reversal")
RETCON_STRATEGIES = ("reconcile", "fade_out", "explicit_fix")
DEC_SESSIONS = ("S1", "S2", "S3", "S4", "volume", "arc", "adhoc")
REVIEW_DEPTHS = ("light", "deep")
REVIEW_VERDICTS = ("pass", "revise", "escalate")

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

DEC_KEYS = ("id", "kind", "node", "session", "date", "status")
DEC_SECTIONS = ("选项", "裁决", "否决案", "异议")
REVIEW_KEYS = ("id", "kind", "chapter", "depth", "verdict", "rev_reviewed", "date")

# 章级 NEEDS_REVIEW 项（必须由评审角色执行的主观判定；对应 rubrics）
UNIT_NEEDS_REVIEW = [
    "人设声纹遮名指认 ≥4/5（rubrics/voice.md §二）",
    "智商漂移两问（rubrics/prose-disease.md §六）",
    "关键场面对话+动作占比 ≥60%（rubrics/prose-disease.md §五）",
    "爽点兑现有效性：触发条件成立、非空转（rubrics/payoff.md §一/§六）",
    "毒点七问与负面节拍降档（rubrics/toxicity.md）",
    "与前章尾 500 字的衔接、与后章任务卡是否顶牛（roles/critic-light.md 四）",
    "spoiler>0 事实是否在正文明写泄露（对照简报 §6【读者未知】标记）",
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


def replace_section(body, name, new_content):
    """整节替换（保留其他节与顺序）；找不到该节时原样返回。"""
    out, hit = [], False
    for t, c in split_sections(body):
        if not hit and (t == name or t.startswith(name)):
            out.append("## %s\n\n%s" % (t, new_content))
            hit = True
        else:
            out.append("## %s\n\n%s" % (t, c))
    return ("\n\n".join(out) + "\n") if hit else body


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


def vol_of_arc(arc_id):
    m = re.match(r"^arc_(\d{2})_", str(arc_id or ""))
    return "vol_" + m.group(1) if m else None


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


def git_out(root, *args):
    try:
        r = subprocess.run(["git", "-C", str(root)] + list(args),
                           capture_output=True, text=True, timeout=30)
        return r.stdout.strip() if r.returncode == 0 else ""
    except (OSError, subprocess.TimeoutExpired):
        return ""


def git_autocommit(root, msg):
    if not (Path(root) / ".git").exists():
        return
    git(root, "add", "-A")
    git(root, "commit", "-m", msg, "-q")


# ---------------------------------------------------------------- 线索状态机
def thread_next_state(state, op):
    """formats §8 合法迁移表；非法迁移返回 None（终态 paid_off/dropped 不接受任何 op）。"""
    if state in THREAD_TERMINAL:
        return None
    table = {
        "plant": {"planted": "planted"},
        "advance": {"planted": "active", "active": "active",
                    "tangled": "active", "payoff_ready": "payoff_ready"},
        "tangle": {"planted": "tangled", "active": "tangled",
                   "tangled": "tangled", "payoff_ready": "tangled"},
        "ready": {"planted": "payoff_ready", "active": "payoff_ready",
                  "tangled": "payoff_ready", "payoff_ready": "payoff_ready"},
        "payoff": {"planted": "paid_off", "active": "paid_off",
                   "tangled": "paid_off", "payoff_ready": "paid_off"},
    }
    return table.get(op, {}).get(state)


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

    # ---- 台账（journal 语义：写入带 rev，读取物化最新 rev）
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

    def _read_ledger(self, name, cols_with_rev, cols_legacy):
        f = self.p("ledgers", name)
        if not f.is_file():
            return []
        lines = read(f).splitlines()
        if len(lines) < 2:
            return []
        header = lines[0].split("\t")
        has_rev = "rev" in header
        rows = []
        for ln in lines[1:]:
            c = ln.split("\t")
            if has_rev and len(c) >= len(cols_with_rev):
                rows.append(dict(zip(cols_with_rev, c[:len(cols_with_rev)])))
            elif not has_rev and len(c) >= len(cols_legacy):
                d = dict(zip(cols_legacy, c[:len(cols_legacy)]))
                d["rev"] = "1"
                rows.append(d)
        return materialize_ledger_latest_rev(rows)

    def payoff_rows(self):
        rows = self._read_ledger(
            "payoff.tsv",
            ["chapter", "rev", "payoff_id", "kind", "intent", "realized"],
            ["chapter", "payoff_id", "kind", "intent", "realized"])
        for r in rows:
            r["realized"] = str(r.get("realized", "0")).strip() == "1"
        return rows

    def timeline_rows(self):
        return self._read_ledger(
            "timeline.tsv",
            ["chapter", "rev", "story_date", "elapsed", "note"],
            ["chapter", "story_date", "elapsed", "note"])

    def power_rows(self):
        return self._read_ledger(
            "power.tsv",
            ["chapter", "rev", "entity", "from", "to", "note"],
            ["chapter", "entity", "from", "to", "note"])


def materialize_ledger_latest_rev(rows):
    """物化视图：每章只保留最新 rev 的行。"""
    ch_rev = {}
    for r in rows:
        ch = r["chapter"]
        rev = int(r.get("rev") or 1)
        ch_rev[ch] = max(ch_rev.get(ch, 0), rev)
    return [r for r in rows if int(r.get("rev") or 1) == ch_rev[r["chapter"]]]


def strip_chapter_log_lines(body, ch_id):
    """revise 重提交时剔除同章旧事件行，避免实体/线索日志双计。"""
    pat = re.compile(r"^- %s:.*(?:\n|$)" % re.escape(ch_id), re.M)
    return pat.sub("", body).rstrip()


def ledger_upsert(path, header, chapter, rev, new_lines):
    """台账 journal 语义：替换 (chapter, rev) 的全部行后追加新行。"""
    cols = header.split("\t")
    rows = []
    old_header = ""
    if path.is_file():
        lines = read(path).splitlines()
        if lines:
            old_header = lines[0]
            has_rev = "rev" in old_header.split("\t")
            for ln in lines[1:]:
                c = ln.split("\t")
                if not c or not c[0]:
                    continue
                if has_rev:
                    if c[0] == chapter and len(c) > 1 and c[1] == str(rev):
                        continue
                    rows.append(c)
                else:
                    # 旧格式迁移：无 rev 列视为 rev=1
                    if c[0] == chapter and rev == 1:
                        continue
                    rows.append([c[0], "1"] + c[1:])
    with open(path, "w", encoding="utf-8") as f:
        f.write(header + "\n")
        for c in rows:
            f.write("\t".join(c) + "\n")
        for ln in new_lines:
            f.write(ln + "\n")


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
              "court/transcripts", "reviews", "data/feedback", "data/compliance",
              "tasks", "state/court", "state/reports", "state/staging", "state/digests", "corpus"):
        (root / d).mkdir(parents=True, exist_ok=True)
    cfg = json.loads(read(TEMPLATES / "config.json"))
    cfg["name"] = args.name or root.name
    write(root / "config.json", json.dumps(cfg, ensure_ascii=False, indent=2))
    rep = {"[YYYY-MM-DDTHH:MM:SSZ]": NOW()}
    for t, dest in (("book.md", "tree/book.md"), ("style.md", "tree/style.md"),
                    ("world.md", "tree/world.md")):
        write(root / dest, instantiate(t, rep))
    write(root / "ledgers/timeline.tsv", "chapter\trev\tstory_date\telapsed\tnote\n")
    write(root / "ledgers/payoff.tsv", "chapter\trev\tpayoff_id\tkind\tintent\trealized\n")
    write(root / "ledgers/power.tsv", "chapter\trev\tentity\tfrom\tto\tnote\n")
    write(root / "ledgers/lessons.md", "# lessons（一行一课，编排者经 commit 附笔追加）\n")
    write(root / "ledgers/recap.md",
          "# recap（全局梗概；编排者维护：卷末 checkpoint 必更，期间每 ~10 章可追加）\n"
          "# 每段 3–6 行；novel.py brief 会把本文件尾 12 行注入简报 §2。\n")
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
    # 章级增量：mtime 未变的章直接复用旧 index 条目（formats §14）
    idx_p = proj.p("state", "index.json")
    old_ch = {}
    if idx_p.is_file():
        try:
            for c in json.loads(read(idx_p)).get("chapters", []):
                if "mtime" in c:
                    old_ch[c["id"]] = c
        except ValueError:
            pass
    ch_entries = []
    for f in proj.chapter_files():
        mt = round(f.stat().st_mtime, 3)
        oc = old_ch.get(f.stem)
        if oc and oc.get("mtime") == mt:
            ch_entries.append(oc)
            continue
        meta, _ = parse_frontmatter(read(f))
        meta = meta or {}
        ch_entries.append({"id": f.stem, "status": meta.get("status"),
                           "rev": meta.get("rev"), "parent": meta.get("parent"),
                           "mtime": mt})
    cur = {"last_published": 0, "last_drafted": 0, "last_approved": 0}
    by_status = {}
    for c in ch_entries:
        n = ch_num(c["id"])
        st = c.get("status")
        by_status.setdefault(st or "?", []).append(c["id"])
        if st == "published":
            cur["last_published"] = max(cur["last_published"], n)
        if st in ("drafted", "approved", "published"):
            cur["last_drafted"] = max(cur["last_drafted"], n)
        if st in ("approved", "published"):
            cur["last_approved"] = max(cur["last_approved"], n)
    ready = sum(1 for c in ch_entries if c.get("status") == "approved"
                and ch_num(c["id"]) > cur["last_published"])

    q = load_queue_promoted(proj)
    pend = [t for t in q["tasks"] if t["state"] in ("pending", "running", "blocked")]
    nodes = proj.tree_nodes()
    ents = proj.entities()
    threads = proj.threads()

    # 告警快照（check --window 摘要，进 index.warnings 与 dashboard）
    wrep = Report()
    check_window(proj, wrep)
    warnings = ["[%s] %s" % (l, n) for l, n, _ in wrep.items
                if l in ("WARN", "FAIL")]

    last_deep = proj.last_deep_review_ch()
    deep_every = proj.config.get("critic", {}).get("deep_every", 5)
    deep_overdue = (cur["last_drafted"] - last_deep) >= deep_every and cur["last_drafted"] > 0

    idx = {
        "generated_at": NOW(),
        "nodes": [{"id": n["meta"].get("id"), "kind": n["meta"].get("kind"),
                   "status": n["meta"].get("status"), "rev": n["meta"].get("rev"),
                   "parent": n["meta"].get("parent"),
                   "path": str(n["path"].relative_to(proj.root))}
                  for n in nodes],
        "chapters": ch_entries,
        "entities": [{"id": eid, "entity_type": e["meta"].get("entity_type"),
                      "rev": e["meta"].get("rev"),
                      "last_event_ch": e["meta"].get("last_event_ch"),
                      "last_reconcile_ch": e["meta"].get("last_reconcile_ch")}
                     for eid, e in ents.items()],
        "threads": [{"id": tid, "thread_kind": t["meta"].get("thread_kind"),
                     "state": t["meta"].get("state"),
                     "must_not_drop": t["meta"].get("must_not_drop"),
                     "plant_ch": t["meta"].get("plant_ch"),
                     "payoff_planned": t["meta"].get("payoff_planned")}
                    for tid, t in threads.items()],
        "tasks": {"pending": len([t for t in q["tasks"] if t["state"] == "pending"]),
                  "blocked": len([t for t in q["tasks"] if t["state"] == "blocked"]),
                  "head": pend[:5]},
        "cursor": cur, "buffer_ready": ready,
        "last_deep_review_ch": last_deep,
        "warnings": warnings,
    }
    write(idx_p, json.dumps(idx, ensure_ascii=False, indent=1))

    lines = ["# dashboard（生成物，禁手改）", "",
             "- 项目：%s ｜ 生成于 %s" % (proj.config.get("name", proj.root.name), NOW()),
             "- 游标：last_published=%(last_published)d  last_approved=%(last_approved)d"
             "  last_drafted=%(last_drafted)d" % cur,
             "- buffer(ready)=%d（target=%s）" % (ready, proj.config.get("buffer", {}).get("target")),
             "- 深评游标：last_deep_review_ch=%d（deep_every=%d）%s"
             % (last_deep, deep_every,
                "【逾期，先排 review_deep】" if deep_overdue else "")]
    lines += ["", "## 树进度表"]
    vols = sorted({n["meta"].get("id") for n in nodes
                   if n["meta"].get("kind") == "volume"} - {None})
    if vols:
        lines.append("| 卷 | 状态 | 弧 | 章数 |")
        lines.append("|---|---|---|---|")
        for vid in vols:
            vnode = next(n for n in nodes if n["meta"].get("id") == vid)
            arcs = [n["meta"] for n in nodes if n["meta"].get("kind") == "arc"
                    and n["meta"].get("parent") == vid]
            arc_ids = {a.get("id") for a in arcs}
            n_ch = sum(1 for c in ch_entries if c.get("parent") in arc_ids)
            lines.append("| %s | %s | %s | %d |"
                         % (vid, vnode["meta"].get("status"),
                            " ".join("%s[%s]" % (a.get("id"), a.get("status"))
                                     for a in arcs) or "（无）", n_ch))
    else:
        lines.append("- （尚无卷节点）")
    lines += ["", "## 树节点"]
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
    lines.append("")
    lines.append("## 告警（check --window 摘要）")
    if warnings:
        lines += ["- %s" % w for w in warnings]
    else:
        lines.append("- （无）")
    lines.append("")
    lines.append("## 最近 git 提交")
    log3 = git_out(proj.root, "log", "--oneline", "-3")
    lines += ["- %s" % l for l in log3.splitlines()] if log3 else ["- （无 git 历史）"]
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
def approval_receipt(proj, ch_id):
    """P1-5 hardened：drafted→approved 仅认 reviews/ 落盘文件，且 rev_reviewed 须匹配当前章 rev。"""
    ch_meta = {}
    for c in proj.chapters():
        if c["id"] == ch_id:
            ch_meta = c["meta"]
            break
    current_rev = int(ch_meta.get("rev") or 1)
    for depth in ("light", "deep"):
        f = proj.p("reviews", "%s.%s.md" % (ch_id, depth))
        if f.is_file():
            meta, _ = parse_frontmatter(read(f))
            if (meta or {}).get("verdict") != "pass":
                continue
            rr = (meta or {}).get("rev_reviewed")
            if rr is None or int(rr) != current_rev:
                continue
            return "reviews/%s.%s.md verdict=pass rev_reviewed=%s" % (ch_id, depth, rr)
    return None


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
        if kind == "chapter" and new == "approved":
            receipt = approval_receipt(proj, args.id)
            if not receipt:
                die("approved 需评审 pass 回执：reviews/%s.light|deep.md 须存在、"
                    "verdict=pass 且 rev_reviewed=当前章 rev（pipeline §1 步骤 8）"
                    % args.id, 1)
            meta["approved_evidence"] = receipt
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
    q = load_queue_promoted(proj)
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
        _, gates = gate_check(proj, tid)
        print(json.dumps({**t, "gates": gates}, ensure_ascii=False, indent=1))
        # P1-10 深评逾期提醒
        cur = proj.cursor()
        last_deep = proj.last_deep_review_ch()
        deep_every = proj.config.get("critic", {}).get("deep_every", 5)
        if cur["last_drafted"] > 0 and cur["last_drafted"] - last_deep >= deep_every:
            print("[提醒] 深评逾期：last_deep_review_ch=%d，last_drafted=%d，"
                  "deep_every=%d——先排 review_deep（pipeline §4）"
                  % (last_deep, cur["last_drafted"], deep_every))
        return 0

    if sub == "list":
        for t in q["tasks"]:
            if args.state and t["state"] != args.state:
                continue
            print("%s %-13s %-12s [%s] attempts=%d %s"
                  % (t["id"], t["type"], t["target"], t["state"],
                     t.get("attempts", 0), t.get("note", "")))
        return 0

    if sub == "archive":
        keep = args.keep
        done = [t for t in q["tasks"] if t["state"] == "done"]
        if len(done) <= keep:
            print("done 任务 %d 条 ≤ keep=%d，无需归档" % (len(done), keep))
            return 0
        move = done[:-keep] if keep else done
        move_ids = {t["id"] for t in move}
        arch_p = proj.p("tasks", "archive.json")
        arch = json.loads(read(arch_p)) if arch_p.is_file() else {"tasks": []}
        arch["tasks"].extend(move)
        write(arch_p, json.dumps(arch, ensure_ascii=False, indent=1))
        q["tasks"] = [t for t in q["tasks"] if t["id"] not in move_ids]
        proj.save_queue(q)
        print("已归档 %d 条 done 任务 → tasks/archive.json（队列余 %d 条）"
              % (len(move), len(q["tasks"])))
        return 0

    # start / done / fail / reset
    t = proj.task(args.id)
    if not t:
        die("任务不存在：%s" % args.id)
    if sub == "start":
        t["state"] = "running"
    elif sub == "done":
        t["state"] = "done"
    elif sub == "reset":
        if t["state"] not in ("failed", "running"):
            die("task reset 仅接受 failed|running（%s 当前 %s）；blocked 由依赖完成自动解锁"
                % (t["id"], t["state"]), 1)
        t["state"] = "pending"
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
    # done 后可能解锁下游 blocked
    if sub == "done":
        promote_blocked(q)
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
    route = proj.config.get("route", "web")
    cur_vol = proj.vol_of_chapter(ch_id)
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

    # §2 直接上文（前章尾 + summary 链 + recap 尾段）
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
    recap_p = proj.p("ledgers", "recap.md")
    if recap_p.is_file():
        rl = [l for l in read(recap_p).splitlines()
              if l.strip() and not l.strip().startswith("#")]
        if rl:
            parts2.append("### 全局 recap（ledgers/recap.md 尾段）\n" + "\n".join(rl[-12:]))
            prov.append(("ledgers/recap.md", "-", "§2 recap"))
    # 弧/卷文摘（commit 自动 rollup，protocol/memory.md）
    arc_id = task.get("arc")
    if arc_id and not str(arc_id).startswith("["):
        ap = proj.p("state", "digests", arc_id + ".json")
        if ap.is_file():
            data = json.loads(read(ap))
            sums = data.get("summaries", [])[-8:]
            if sums:
                parts2.append("### 本弧文摘（state/digests/%s.json）\n" % arc_id
                              + "\n".join("- %s：%s" % (s["chapter"], s["summary"]) for s in sums))
                prov.append((str(ap.relative_to(proj.root)), "-", "§2 弧文摘"))
    vp = proj.p("state", "digests", cur_vol + ".json")
    if vp.is_file():
        vdata = json.loads(read(vp))
        vsums = vdata.get("summaries", [])[-5:]
        if vsums:
            parts2.append("### 本卷文摘（state/digests/%s.json）\n" % cur_vol
                          + "\n".join("- %s：%s" % (s["chapter"], s["summary"]) for s in vsums))
            prov.append((str(vp.relative_to(proj.root)), "-", "§2 卷文摘"))
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

    # §4 活跃线索（listed ∪ must_not_drop ∪ volume_scope 命中 ∪ payoff_planned 临近）
    def payoff_near(m):
        pp = m.get("payoff_planned")
        if not pp:
            return False
        if str(pp) == cur_vol:
            return True
        mm = re.match(r"^ch_(\d{4})$", str(pp))
        return bool(mm) and 0 <= int(mm.group(1)) - num <= 15

    parts4 = []
    threads = proj.threads()
    listed = {t["id"] for t in task.get("threads", [])}
    for tid, th in threads.items():
        m = th["meta"]
        live = m.get("state") in THREAD_LIVE
        scope_hit = cur_vol in (m.get("volume_scope") or [])
        near = payoff_near(m)
        relevant = tid in listed or (live and (m.get("must_not_drop")
                                               or scope_hit or near))
        if not relevant:
            continue
        stmt = get_section(th["body"], "陈述") or ""
        log = get_section(th["body"], "推进日志") or ""
        log_tail = "\n".join([l for l in log.splitlines() if l.strip().startswith("-")][-2:])
        tags = ""
        if m.get("must_not_drop"):
            tags += "【must_not_drop】"
        if near:
            tags += "【payoff 临近：%s】" % m.get("payoff_planned")
        parts4.append("- **%s** [%s/%s]%s：%s\n  最近推进：%s"
                      % (tid, m.get("thread_kind"), m.get("state"), tags,
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
    for f in proj.facts_files():
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

    # §7 写作提示（≤60 行；按 route 选配）
    lessons_p = proj.p("ledgers", "lessons.md")
    lessons = [l for l in read(lessons_p).splitlines() if l.startswith("- ")][-5:] \
        if lessons_p.is_file() else []
    if route == "traditional":
        tips = [
            "核心纪律速记（traditional 差分，全文见 modes/route-traditional.md）：",
            "- 按细纲逐拍执行（beats 6–10 拍；scene_intents 标场景/过场）",
            "- 每章必有价值翻转（task.json 的 turn 字段；正负极性要兑现）",
            "- 章尾钩为建议级：close 缺席须在 issues 说明 turn 已落实",
            "- 关键场面禁概述体；每 500 字 ≥1 个新信息或价值变化",
            "- 禁发明简报外专名；缺料写 issues，不脑补",
        ]
    else:
        tips = [
            "核心纪律速记（全文见 rubrics/prose-disease.md）：",
            "- 每 500 字 ≥1 个新信息或价值变化；章尾钩落最后 150 字内，钩前收束 ≤1 句",
            "- 开篇 300 字内反预期信号；不原地复述上章钩子",
            "- 关键场面禁概述体；打斗远中近推拉、交锋段均句长 ≤15 字",
            "- 禁发明简报外专名；缺料写 issues，不脑补",
        ]
    s7 = "\n".join(tips + ["", "近期教训（lessons 台账尾 5 条）："]
                   + (lessons or ["- （暂无）"]))
    if lessons:
        prov.append(("ledgers/lessons.md", "-", "§7 教训"))

    # §8 回写契约
    s8 = ("提交格式：最终回复两段——【正文】章文件（信封+## 正文）；【writeback】如下 schema 的"
          "JSON 块（power_delta 可选，战力/位阶变化时必填；continuity_delta 每条可选 key "
          "字段标注实体状态键位，如「位置」「持有」）：\n\n```json\n"
          + read(TEMPLATES / "chapter.meta.json").strip() + "\n```")

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
    # 条目级预算裁剪（必含集：§0 任务卡、§8 回写契约、must_not_drop 线索、spoiler facts 永不整节丢弃）
    trimmable = [
        ("7 写作提示", False),
        ("6 相关事实与设定", False),
        ("4 活跃线索", False),
        ("3 出场实体状态卡", False),
        ("5 弧内位置", True),
        ("2 直接上文", True),
        ("1 文风与禁忌", True),
    ]
    for sec, allow_full_drop in trimmable:
        if len(text) <= budget:
            break
        if sec == "3 出场实体状态卡":
            slim = []
            for ref in task.get("cast", []):
                eid = proj.resolve_entity(ref)
                if not eid or eid not in ents:
                    slim.append("- 【缺卡】%s" % ref)
                    continue
                e = ents[eid]
                voice = get_section(e["body"], "声纹") or get_section(e["body"], "设定") or ""
                voice_lines = "\n".join(voice.splitlines()[:5])
                slim.append("### %s\n声纹要点：\n%s\n\n现状：\n%s"
                            % (eid, voice_lines or "（见 entities/%s.md）" % eid,
                               get_section(e["body"], "现状") or ""))
            sections[sec] = "\n\n".join(slim) or "（任务卡未列 cast）"
        elif sec == "6 相关事实与设定" and parts6:
            kept, dropped = [], []
            for line in parts6:
                if "【读者未知" in line or "已被覆盖" in line:
                    kept.append(line)
                elif len("\n".join(kept)) + len(line) < budget // 3:
                    kept.append(line)
                else:
                    dropped.append(line[:30])
            sections[sec] = "\n".join(kept) if kept else "（无相关事实）"
            if dropped:
                trimmed.append(sec + " 条目裁剪 %d" % len(dropped))
        elif sec == "4 活跃线索" and parts4:
            must_lines = [l for l in parts4 if "must_not_drop" in l or "payoff 临近" in l]
            other = [l for l in parts4 if l not in must_lines]
            kept = list(must_lines)
            for line in other:
                if len("\n".join(kept)) + len(line) < budget // 4:
                    kept.append(line)
            sections[sec] = "\n".join(kept) if kept else "（无活跃线索命中）"
            if len(kept) < len(parts4):
                trimmed.append(sec + " 条目裁剪")
        elif allow_full_drop:
            sections[sec] = "（条目级裁剪后仍超预算；见 entities/threads/facts 原文件）"
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


def ngram_sim(a, b):
    """字符 2-gram Jaccard 相似度（facts 冲突候选启发）。"""
    A, B = set(char_ngrams(a, 2)), set(char_ngrams(b, 2))
    if not A or not B:
        return 0.0
    return len(A & B) / len(A | B)


def cache_fps(entry, key):
    """ngram_cache 条目取指纹；兼容旧版扁平 list（视为 n12）。"""
    if isinstance(entry, dict):
        return set(entry.get(key, []))
    return set(entry) if key == "n12" else set()


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
        st = sim_state.get(tid, threads[tid]["meta"].get("state"))
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


    if dups:
        rep.add("WARN", "facts 重复登记候选（同文已在其他章揭示）", dups)


def extract_reconcile(proj, text, wb, rep):
    """双记账（机器半边）：正文已登记专名 vs cast_actual 漏报；位阶词命中 vs power_delta 缺报。"""
    if not wb:
        return
    names = {}
    for alias, eid in proj.aliases().items():
        if len(str(alias)) >= 2:
            names[str(alias)] = eid
    for eid, e in proj.entities().items():
        for a in e["meta"].get("aliases") or []:
            if len(str(a)) >= 2:
                names[str(a)] = eid
    declared = set()
    for ref in wb.get("cast_actual", []) or []:
        eid = proj.resolve_entity(ref)
        if eid:
            declared.add(eid)
    mentioned = set()
    for name, eid in names.items():
        if name in text:
            mentioned.add(eid)
    missing = sorted(mentioned - declared)
    if missing:
        rep.add("NEEDS_REVIEW", "extractor 对账：正文出现已登记专名但 cast_actual 漏报",
                missing)
    else:
        rep.add("PASS", "cast_actual 覆盖正文已登记专名")
    world_p = proj.p("tree", "world.md")
    if world_p.is_file():
        _, wbody = parse_frontmatter(read(world_p))
        tiers = re.findall(r"^\|\s*([^|]+?)\s*\|", get_section(wbody, "力量体系与位阶") or "",
                           re.M)
        tiers = [t.strip() for t in tiers if t.strip() and t.strip() not in ("tier", "---")]
        hit_tiers = [t for t in tiers if t and t in text]
        pd_entities = set()
        for d in wb.get("power_delta", []) or []:
            for ref in d.get("entity_ids", []):
                eid = proj.resolve_entity(ref)
                if eid:
                    pd_entities.add(eid)
        if hit_tiers and not pd_entities:
            rep.add("NEEDS_REVIEW", "extractor 对账：正文命中位阶词但 power_delta 空",
                    hit_tiers[:5])
    for d in wb.get("continuity_delta", []) or []:
        if d.get("spoiler") and d.get("fact") and d.get("fact") in text:
            rep.add("NEEDS_REVIEW", "spoiler 事实可能在正文明写",
                    ["fact「%s」" % d.get("fact")[:40]])


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
        extract_reconcile(proj, text, wb, rep)
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

    # 时间线
    neg = []
    for r in proj.timeline_rows():
        elapsed = (r.get("elapsed") or "").strip()
        if elapsed.startswith("-"):
            neg.append("%s elapsed=%s" % (r["chapter"], elapsed))
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
    # 半事务检测（commit journal）
    jp = proj.p("state", "commit_journal.jsonl")
    if jp.is_file():
        pending = {}
        for ln in read(jp).splitlines():
            if not ln.strip():
                continue
            try:
                e = json.loads(ln)
            except ValueError:
                continue
            key = (e.get("chapter"), e.get("rev"))
            if e.get("status") == "started":
                pending[key] = e
            elif e.get("status") in ("completed", "aborted"):
                pending.pop(key, None)
        if pending:
            rep.add("FAIL", "存在未完成 commit 事务（state/commit_journal.jsonl）",
                    ["%s rev=%s task=%s——重跑 commit 或手工对账后追加 aborted 条目"
                     % (k[0], k[1], v.get("task")) for k, v in pending.items()])
        else:
            rep.add("PASS", "commit journal 无半事务")
    return rep


def gate_check(proj, task_id):
    """L4 gate：输出任务前置谓词判定（编排内核化，pipeline gate 注释版配套）。"""
    t = proj.task(task_id)
    if not t:
        return None, [{"gate": "task_exists", "ok": False, "detail": "任务不存在"}]
    results = [{"gate": "task_exists", "ok": True, "detail": t["id"]}]
    if t["state"] == "blocked":
        results.append({"gate": "task_unblocked", "ok": False,
                        "detail": "blocked_on=%s" % t.get("blocked_on")})
        return t, results
    results.append({"gate": "task_unblocked", "ok": True, "detail": t["state"]})
    if t["type"] in ("write", "revise"):
        ch_id = t["target"]
        brief_p = proj.p("briefs", ch_id + ".brief.md")
        task_p = proj.p("chapters", ch_id + ".task.json")
        if not brief_p.is_file():
            results.append({"gate": "brief_exists", "ok": False, "detail": "缺 briefs/%s.brief.md"
                            % ch_id})
        else:
            fresh = not task_p.is_file() or brief_p.stat().st_mtime >= task_p.stat().st_mtime
            results.append({"gate": "brief_fresh", "ok": fresh,
                            "detail": "简报 mtime ≥ 任务卡" if fresh else "简报早于任务卡，须重跑 brief"})
        if t["type"] == "revise":
            ch_meta = next((c["meta"] for c in proj.chapters() if c["id"] == ch_id), {})
            if ch_meta.get("status") == "published":
                results.append({"gate": "not_published", "ok": False,
                                "detail": "published 章不可 revise"})
            else:
                results.append({"gate": "not_published", "ok": True, "detail": "ok"})
        receipt = approval_receipt(proj, ch_id) if t.get("note", "").find("await_approve") >= 0 else None
        if receipt:
            results.append({"gate": "review_receipt", "ok": True, "detail": receipt})
    return t, results


def cmd_gate(args):
    proj = Project(find_root(args))
    t, results = gate_check(proj, args.task_id)
    if not t:
        die("任务不存在：%s" % args.task_id)
    all_ok = all(r["ok"] for r in results)
    print(json.dumps({"task_id": args.task_id, "type": t["type"], "target": t.get("target"),
                      "gates": results, "ready": all_ok}, ensure_ascii=False, indent=2))
    return 0 if all_ok else 1


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


# ---------------------------------------------------------------- commit
def register_facts(proj, ch_id, wb):
    """P0-1：commit 时自 continuity_delta 自动分配 fact_id 写入 ledgers/facts/vol_NN.json。
    同文同章去重（revise 重提交不重复登记）。返回新登记的 fact id 列表。"""
    deltas = wb.get("continuity_delta", []) or []
    if not deltas:
        return []
    num = ch_num(ch_id)
    vol = proj.vol_of_chapter(ch_id)
    f = proj.p("ledgers", "facts", vol + ".json")
    data = json.loads(read(f)) if f.is_file() else {"facts": [], "retcons": []}
    existing = {(x.get("fact"), x.get("revealed_ch")) for x in data.get("facts", [])}
    seq = proj.next_fact_seq()
    added = []
    for d in deltas:
        key = (d.get("fact"), num)
        if key in existing:
            continue
        existing.add(key)
        rec = {"id": "fact_%04d" % seq, "fact": d.get("fact", ""),
               "entity_ids": sorted({proj.resolve_entity(r) or r
                                     for r in d.get("entity_ids", [])}),
               "revealed_ch": num, "spoiler": d.get("spoiler", 0),
               "superseded_by": None}
        if d.get("key"):
            rec["key"] = d["key"]
        data.setdefault("facts", []).append(rec)
        added.append(rec["id"])
        seq += 1
    write(f, json.dumps(data, ensure_ascii=False, indent=1))
    return added


def apply_writeback(proj, ch_id, wb, rev=1):
    """continuity_delta → 实体事件日志 + facts 登记；thread_ops → 推进日志+state（合法迁移表）；
    payoff/timeline/power 台账（(chapter, rev) journal 语义）。引用越权 = 硬失败。"""
    errs = writeback_ref_errors(proj, ch_id, wb)
    if errs:
        return False, errs
    num = ch_num(ch_id)
    ents = proj.entities()
    notes = []
    for delta in wb.get("continuity_delta", []) or []:
        for ref in delta.get("entity_ids", []):
            eid = proj.resolve_entity(ref)
            e = ents[eid]
            body = strip_chapter_log_lines(e["body"], ch_id)
            body = body.rstrip() + "\n- %s: %s\n" % (ch_id, delta.get("fact", ""))
            meta = e["meta"]
            meta["last_event_ch"] = num
            meta["updated_at"] = NOW()
            write(e["path"], dump_frontmatter(meta) + "\n" + body.lstrip("\n"))
            ents = proj.entities()  # 重载，防同章多条
    threads = proj.threads()
    for op in wb.get("thread_ops", []) or []:
        tid = op["id"]
        t = threads[tid]
        meta = t["meta"]
        nxt = thread_next_state(meta.get("state"), op["op"])
        body = strip_chapter_log_lines(t["body"], ch_id)
        body = body.rstrip() + "\n- %s: %s %s\n" % (ch_id, op["op"], op.get("note", ""))
        meta["state"] = nxt
        if op["op"] == "plant" and not meta.get("plant_ch"):
            meta["plant_ch"] = num  # P1-3：plant 回填 plant_ch
        meta["updated_at"] = NOW()
        write(t["path"], dump_frontmatter(meta) + "\n" + body.lstrip("\n"))
        threads = proj.threads()
    # facts 登记（P0-1）
    added = register_facts(proj, ch_id, wb)
    if added:
        notes.append("facts 已登记：%s → ledgers/facts/%s.json"
                     % (" ".join(added), proj.vol_of_chapter(ch_id)))
    # payoff 台账（journal：按 chapter+rev 替换）
    task = proj.chapter_task(ch_id) or {}
    quota = task.get("payoff_quota", [])
    realized = set(wb.get("payoff_realized", []))
    payoff_lines = []
    for i, q in enumerate(quota, 1):
        pid = "payoff_%04d_%d" % (num, i)
        payoff_lines.append("%s\t%d\t%s\t%s\t%s\t%d" % (
            ch_id, rev, pid, q.get("kind", "other"), q.get("intent", ""),
            1 if pid in realized else 0))
    ledger_upsert(proj.p("ledgers", "payoff.tsv"),
                  "chapter\trev\tpayoff_id\tkind\tintent\trealized",
                  ch_id, rev, payoff_lines)
    # timeline
    ta = wb.get("time_advance", {})
    ledger_upsert(proj.p("ledgers", "timeline.tsv"),
                  "chapter\trev\tstory_date\telapsed\tnote",
                  ch_id, rev, ["%s\t%d\t%s\t%s\t" % (
                      ch_id, rev, ta.get("story_date", ""), ta.get("elapsed", ""))])
    # power 台账（P1-6，可选键）
    pd = wb.get("power_delta", []) or []
    if pd:
        power_lines = []
        for d in pd:
            for ref in d.get("entity_ids", []):
                eid = proj.resolve_entity(ref)
                power_lines.append("%s\t%d\t%s\t%s\t%s\t%s" % (
                    ch_id, rev, eid, d.get("from", ""), d.get("to", ""),
                    d.get("note", "")))
        ledger_upsert(proj.p("ledgers", "power.tsv"),
                      "chapter\trev\tentity\tfrom\tto\tnote",
                      ch_id, rev, power_lines)
        notes.append("power 台账已写入 %d 行（rev=%d）" % (len(power_lines), rev))
    return True, notes


def update_ngram_cache(proj, ch_id, text):
    cache = proj.ngram_cache()
    cache[ch_id] = {"n12": sorted(set(char_ngrams(text, 12))),
                    "n8": sorted(set(char_ngrams(text, 8)))}
    window = proj.config.get("ngram_window_chapters", 30)
    keys = sorted(cache, key=lambda k: ch_num(k) if re.match(r"ch_\d{4}$", k) else 0)
    for k in keys[:-window]:
        entry = cache.get(k)
        if isinstance(entry, dict):
            entry["n8"] = []  # 8-gram 滚动窗口；12-gram 全史保留
        elif isinstance(entry, list):
            cache[k] = {"n12": entry, "n8": []}
    write(proj.p("state", "ngram_cache.json"), json.dumps(cache, ensure_ascii=False))


def propagate_stale(proj, node_id):
    """P1-7：revise_design 定稿后，受影响下游沿 parent 链递归标 stale（直到章）。"""
    nodes = proj.tree_nodes()
    chs = proj.chapters()
    children = {}
    for n in nodes:
        children.setdefault(n["meta"].get("parent"), []).append(("node", n))
    for c in chs:
        children.setdefault(c["meta"].get("parent"), []).append(("ch", c))
    stale, queue = [], [node_id]
    seen = set()
    while queue:
        cur = queue.pop(0)
        if cur in seen:
            continue
        seen.add(cur)
        for typ, item in children.get(cur, []):
            m = item["meta"]
            if typ == "node":
                iid = m.get("id")
                if m.get("status") in ("draft", "committed"):
                    m["status"] = "stale"
                    m["updated_at"] = NOW()
                    write(item["path"], dump_frontmatter(m) + "\n" + item["body"].lstrip("\n"))
                    stale.append(iid)
                queue.append(iid)
            else:
                if m.get("status") in ("planned", "drafted", "approved"):
                    m["status"] = "stale"
                    m["updated_at"] = NOW()
                    write(item["path"], dump_frontmatter(m) + "\n" + item["body"].lstrip("\n"))
                    stale.append(item["id"])
    return stale


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


def journal_append(proj, entry):
    jp = proj.p("state", "commit_journal.jsonl")
    with open(jp, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def digest_rollup(proj, ch_id, summary):
    """commit 后自动 rollup 章摘要进弧/卷文摘（protocol/memory.md）。"""
    if not (summary or "").strip():
        return
    arc_id = (proj.chapter_task(ch_id) or {}).get("arc")
    vol = proj.vol_of_chapter(ch_id)
    dig = proj.p("state", "digests")
    dig.mkdir(parents=True, exist_ok=True)
    if arc_id and not arc_id.startswith("["):
        ap = dig / ("%s.json" % arc_id)
        data = json.loads(read(ap)) if ap.is_file() else {"arc": arc_id, "summaries": []}
        data["summaries"] = [s for s in data.get("summaries", [])
                             if s.get("chapter") != ch_id]
        data["summaries"].append({"chapter": ch_id, "summary": summary.strip(),
                                  "updated_at": NOW()})
        write(ap, json.dumps(data, ensure_ascii=False, indent=1))
    vp = dig / ("%s.json" % vol)
    vdata = json.loads(read(vp)) if vp.is_file() else {"volume": vol, "summaries": []}
    vdata["summaries"] = [s for s in vdata.get("summaries", [])
                          if s.get("chapter") != ch_id]
    vdata["summaries"].append({"chapter": ch_id, "summary": summary.strip(),
                               "updated_at": NOW()})
    write(vp, json.dumps(vdata, ensure_ascii=False, indent=1))


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
        new_rev = ((old_meta.get("rev") or 0) + 1 if ttype == "revise"
                   else max(old_meta.get("rev") or 1, 1))
        journal_append(proj, {"status": "started", "task": args.task_id,
                              "chapter": ch_id, "rev": new_rev, "at": NOW()})
        ok, msgs = apply_writeback(proj, ch_id, wb, rev=new_rev)
        if not ok:
            journal_append(proj, {"status": "aborted", "task": args.task_id,
                                  "chapter": ch_id, "rev": new_rev, "at": NOW(),
                                  "reason": "writeback_ref_errors"})
            print("[拒绝] writeback 引用越权，未落盘：")
            for e in msgs:
                print("  - " + e)
            return 1
        new_meta = {
            "id": ch_id, "kind": "chapter", "status": "drafted",
            "rev": new_rev,
            "parent": cand_meta.get("parent") or old_meta.get("parent"),
            "updated_at": NOW(),
            "title": cand_meta.get("title", old_meta.get("title", "")),
            "word_count": cjk_len(text),
        }
        write(exist_p, dump_frontmatter(new_meta) + "\n\n## 正文\n" + text.strip() + "\n")
        write(proj.p("chapters", ch_id + ".meta.json"),
              json.dumps(wb, ensure_ascii=False, indent=1))
        update_ngram_cache(proj, ch_id, text)
        digest_rollup(proj, ch_id, wb.get("summary_after", ""))
        journal_append(proj, {"status": "completed", "task": args.task_id,
                              "chapter": ch_id, "rev": new_rev, "at": NOW()})
        for w in msgs:
            print("[info] " + w)
        git_autocommit(proj.root, "[%s] %s(%s): %s" % (args.task_id, ttype, ch_id, msg))
        print("已落盘：%s（status=drafted, rev=%d）+ meta.json + facts/台账/日志/ngram"
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
                if args.draft:
                    # P0-6：draft 态部分落盘（书庭中间场次可持久化半成品，不算定稿）
                    meta["status"] = "draft"
                    meta["updated_at"] = NOW()
                    write(target, dump_frontmatter(meta) + "\n" + body.lstrip("\n"))
                    print("已 draft 部分落盘 → %s（不算定稿，必需节校验延后到正式 commit）"
                          % target.relative_to(proj.root))
                    continue
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
            stale = propagate_stale(proj, t["target"])
            if stale:
                print("下游已递归标 stale：%s（修复后回原 status；影响面报告模板见 court.md §4）"
                      % " ".join(stale))
        git_autocommit(proj.root, "[%s] %s(%s): %s" % (args.task_id, ttype, t["target"], msg))
        return 0

    die("commit 支持 write|revise|design|revise_design|review_deep；"
        "publish 用 publish，retcon 用 retcon，checkpoint 用 checkpoint，"
        "reconcile 用 entity update", 2)


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
    elif args.which == "power":
        f = proj.p("ledgers", "power.tsv")
        print(read(f) if f.is_file() else "（空）")
    else:
        f = proj.p("ledgers", "timeline.tsv")
        print(read(f) if f.is_file() else "（空）")
    return 0


# ---------------------------------------------------------------- retcon
def cmd_retcon(args):
    """P0-4：retcon CLI 化（serial-ops §3）。旧 fact 填 superseded_by，retcons[] 追加。"""
    proj = Project(find_root(args))
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


# ---------------------------------------------------------------- report / checkpoint
def volume_chapters(proj, vol_id):
    return [c for c in proj.chapters() if proj.vol_of_chapter(c["id"]) == vol_id]


def cmd_report(args):
    """P0-4：卷报告汇编（serial-ops §4 步骤 1 的机械部分）。
    产出 state/reports/vol_NN.md；exports 行预标 [待对账]，编排者改三态后跑 checkpoint。"""
    proj = Project(find_root(args))
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
    warn = ["- [%s] %s" % (l, n) for l, n, _ in wrep.items if l in ("WARN", "FAIL")]
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


def cmd_checkpoint(args):
    """P0-4：卷末结账（formats §16 checkpoint 行）。
    校验：报告存在 + exports 三态齐 + 卷内无未完稿章；动作：卷标记 + 下卷 imports 预填。"""
    proj = Project(find_root(args))
    vol_id = args.vol_id
    m0 = re.match(r"^vol_(\d{2})$", vol_id)
    if not m0:
        die("卷 id 应为 vol_NN")
    vp = proj.node_path(vol_id)
    if not vp or not vp.is_file():
        die("卷不存在：%s" % vol_id, 1)
    vmeta, vbody = parse_frontmatter(read(vp))
    if vmeta.get("status") != "committed":
        die("卷 %s 状态为 %s，须 committed 才可 checkpoint" % (vol_id, vmeta.get("status")), 1)
    rp = proj.p("state", "reports", vol_id + ".md")
    if not rp.is_file():
        die("卷报告未汇编：先跑 novel.py report volume %s（serial-ops §4 步骤 1）" % vol_id, 1)
    rtext = read(rp)
    pending = [l.strip() for l in rtext.splitlines() if "[待对账]" in l]
    if pending:
        die("exports 对账未完成，%d 条仍为 [待对账]（编辑 %s 标注三态后重试）：\n  %s"
        % (len(pending), rp.relative_to(proj.root), "\n  ".join(pending[:5])), 1)
    bad = [c["id"] for c in volume_chapters(proj, vol_id)
           if c["meta"].get("status") in ("planned", "drafted", "stale")]
    if bad:
        die("卷内存在未完稿章（须 approved/published/archived）：%s" % " ".join(bad), 1)

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


# ---------------------------------------------------------------- adopt
def cmd_adopt(args):
    """P1-9：收编外部文稿为项目章（protocol/adopt.md）。"""
    proj = Project(find_root(args))
    ch_id = args.as_id
    num = ch_num(ch_id)
    src = Path(args.file)
    if not src.is_file():
        die("源文件不存在：%s" % src)
    exist = proj.p("chapters", ch_id + ".md")
    if exist.is_file():
        emeta, _ = parse_frontmatter(read(exist))
        if (emeta or {}).get("status") not in (None, "planned"):
            die("%s 已存在且非 planned（status=%s）——收编不覆盖成稿，改用 revise 链路"
                % (ch_id, (emeta or {}).get("status")), 1)
    raw = read(src)
    meta, body = parse_frontmatter(raw)
    text = body.split("## 正文", 1)[-1] if (meta and "## 正文" in body) else raw
    new_meta = {
        "id": ch_id, "kind": "chapter", "status": "drafted", "rev": 1,
        "parent": args.parent or (meta or {}).get("parent") or "",
        "updated_at": NOW(),
        "title": args.title or (meta or {}).get("title", ""),
        "word_count": cjk_len(text),
    }
    write(exist, dump_frontmatter(new_meta) + "\n\n## 正文\n" + text.strip() + "\n")
    tp = proj.p("chapters", ch_id + ".task.json")
    if not tp.is_file():
        write(tp, instantiate("chapter.task.json",
                              {"[ch_0001]": ch_id,
                               "[arc_01_1]": args.parent or "[arc_01_1]"}))
    mp = proj.p("chapters", ch_id + ".meta.json")
    if args.writeback:
        wb_path = Path(args.writeback)
        if not wb_path.is_file():
            die("writeback 不存在：%s" % wb_path)
        wb = json.loads(read(wb_path))
        write(mp, json.dumps(wb, ensure_ascii=False, indent=1))
        ok, msgs = apply_writeback(proj, ch_id, wb, rev=1)
        if not ok:
            die("writeback 引用越权：\n" + "\n".join(msgs), 1)
        for m in msgs:
            print("[info] " + m)
    elif not mp.is_file():
        stub = {"summary_after": "", "continuity_delta": [],
                "time_advance": {"elapsed": "", "story_date": ""}, "thread_ops": [],
                "payoff_realized": [], "hooks_realized": {"open": False, "close": False},
                "cast_actual": [],
                "issues": ["adopted：外部文稿收编，writeback 待补录（protocol/adopt.md §3）"],
                "word_count": new_meta["word_count"]}
        write(mp, json.dumps(stub, ensure_ascii=False, indent=1))
    update_ngram_cache(proj, ch_id, text)
    git_autocommit(proj.root, "[adopt] %s ← %s" % (ch_id, src.name))
    print("已收编：%s（status=drafted, %d 字）" % (ch_id, new_meta["word_count"]))
    print("后续（protocol/adopt.md §3）：补 task.json 排批字段 → 补录 writeback"
          "（summary_after/continuity_delta/thread_ops）→ check --unit %s → "
          "评审后 set-status approved" % ch_id)
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
               "tree set-status approved → publish。卷末：report volume → 三态标注 →\n"
               "checkpoint。已发布内容修错：retcon。外部文稿收编：adopt。")
    ap.add_argument("--root", help="项目根（默认从 cwd 向上探测 config.json+tree/）")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("init", help="脚手架新项目（+git init）")
    p.add_argument("dir")
    p.add_argument("--name")

    sub.add_parser("status", help="重算 index/dashboard 并打印（可恢复断点；章级增量）")
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
    q.add_argument("--evidence", help="approved 需评审 pass 回执（reviews/ 或任务 note 可省）")

    p = sub.add_parser("task", help="任务队列：add/next/list/start/done/fail/reset/archive")
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
    q = ts.add_parser("archive")
    q.add_argument("--keep", type=int, default=20)
    for name in ("start", "done", "fail", "reset"):
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

    p = sub.add_parser("check", help="断言集：--unit/--window/--project/--leak")
    p.add_argument("--unit", metavar="CH_ID")
    p.add_argument("--candidate", help="未落盘候选章文件（staging 机检）")
    p.add_argument("--writeback", help="未落盘 writeback JSON")
    p.add_argument("--window", action="store_true")
    p.add_argument("--since", metavar="CH_ID", help="窗口检查起点（增量）")
    p.add_argument("--project", action="store_true")
    p.add_argument("--leak", metavar="CANDIDATE", help="简报外专名泄漏扫描（需 --brief）")
    p.add_argument("--brief", help="与 --leak 搭配：该章简报文件")

    p = sub.add_parser("commit", help="唯一写路径：校验全过才落盘")
    p.add_argument("task_id")
    p.add_argument("--chapter")
    p.add_argument("--writeback")
    p.add_argument("--file", action="append")
    p.add_argument("--draft", action="store_true",
                   help="design 类：draft 态部分落盘（跳过必需节校验，不算定稿）")
    p.add_argument("-m", default="")

    p = sub.add_parser("publish", help="连续性谓词；approved→published")
    p.add_argument("ch_from")
    p.add_argument("ch_to", nargs="?")

    p = sub.add_parser("retcon", help="已发布事实向前兼容覆盖（serial-ops §3）")
    p.add_argument("old_fact_id")
    p.add_argument("--new", required=True, help="新事实一句话")
    p.add_argument("--strategy", required=True, choices=list(RETCON_STRATEGIES))
    p.add_argument("--decision", required=True, help="裁决记录 id（court/dec_*.md 须存在）")
    p.add_argument("--entity", action="append", help="覆盖实体（默认沿用旧 fact 的 entity_ids）")

    p = sub.add_parser("report", help="汇编报告：report volume <vol_NN>")
    p.add_argument("which", choices=["volume"])
    p.add_argument("vol_id")

    p = sub.add_parser("checkpoint", help="卷末结账：校验对账三态+下卷 imports 预填")
    p.add_argument("vol_id")

    p = sub.add_parser("adopt", help="收编外部文稿为项目章（protocol/adopt.md）")
    p.add_argument("file")
    p.add_argument("--as", dest="as_id", required=True, metavar="CH_ID")
    p.add_argument("--title")
    p.add_argument("--parent", help="所属弧 arc_NN_n（已有弧时填）")
    p.add_argument("--writeback", help="补录 writeback JSON（facts/台账经 apply_writeback 写入）")

    p = sub.add_parser("gate", help="任务前置 gate 谓词判定（L4 编排内核）")
    p.add_argument("task_id")

    p = sub.add_parser("ledger", help="台账视图：payoff|promise|timeline|power")
    p.add_argument("which", choices=["payoff", "promise", "timeline", "power"])

    args = ap.parse_args(argv)
    if args.cmd == "check" and not (args.unit or args.window or args.project or args.leak):
        ap.error("check 需 --unit <ch>|--window|--project|--leak <候选> 之一")

    dispatch = {
        "init": cmd_init, "status": cmd_status, "tree": cmd_tree, "task": cmd_task,
        "entity": cmd_entity, "thread": cmd_thread, "brief": cmd_brief,
        "check": cmd_check, "commit": cmd_commit, "publish": cmd_publish,
        "ledger": cmd_ledger, "retcon": cmd_retcon, "report": cmd_report,
        "checkpoint": cmd_checkpoint, "adopt": cmd_adopt, "gate": cmd_gate,
        "fsck": lambda a: check_project(Project(find_root(a))).render("fsck"),
    }
    return dispatch[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
