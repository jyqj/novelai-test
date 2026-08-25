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
import shutil
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
              "publish", "retcon", "checkpoint", "reconcile", "revise_rubric")
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

# 阶段目录（P6-S）：id → (名称, 一句话定位, 配套知识包相对路径)
# SSOT=protocol/knowledge-orchestration.md §1；包内容为准，此表只做定位。
STAGES = (
    ("s1", "书庭S1·概念庭", "主旨/高概念/题材定位", "protocol/stages/s1-concept.md"),
    ("s2", "书庭S2·世界庭", "世界观核心/金手指/力量体系", "protocol/stages/s2-world.md"),
    ("s3", "书庭S3·人物庭", "主线电缆/人物阵容/反派梯队", "protocol/stages/s3-cast.md"),
    ("s4", "书庭S4·分卷庭", "分卷草案/卷1蓝图/style 定稿", "protocol/stages/s4-volumes.md"),
    ("vol", "卷庭", "卷蓝图九节", "protocol/stages/vol-court.md"),
    ("arc", "弧规划", "弧六节+细纲(traditional)", "protocol/stages/arc-plan.md"),
    ("write", "章循环", "排批→简报→写→机检→轻评→commit(零知识装载)",
     "protocol/stages/write-loop.md"),
    ("review", "周期回路", "深评采样/实体对账/knowledge 欠账", "protocol/stages/review-cycle.md"),
    ("ops", "连载运营", "buffer/publish/卷末结账/读者反馈", "protocol/stages/ops-serial.md"),
    ("trad", "传统差分", "叠加层:判据卡置换(scene-value/theme/imagery)",
     "protocol/stages/trad-overlay.md"),
    ("diag", "诊断深读", "症状→K-ID→锚点段(≤2块/次)", "protocol/stages/diagnose.md"),
)

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


def thread_ops_from_log(log_text, exclude_ch=None):
    """从推进日志解析有序 op 流水（`- ch_NNNN: op …`）。exclude_ch 用于 (chapter,rev)
    语义下剔除某章贡献（revise 前置校验/撤销重放）。"""
    ops = []
    for ln in (log_text or "").splitlines():
        m = re.match(r"^-\s*(ch_\d{4})\s*:\s*(plant|advance|payoff|tangle|ready)\b",
                     ln.strip())
        if m and m.group(1) != exclude_ch:
            ops.append(m.group(2))
    return ops


def thread_effective_state(th, exclude_ch=None):
    """双记账读侧：线索状态 = 推进日志 op 有序重放（可排除某章）。
    - dropped 是编排者手工终态（不经 op），直接保留；
    - 日志无任何 op 时回退 frontmatter state（手工校正的 adopt 线）；
    - 排除后日志为空（状态全由被排除章贡献）→ 回放基线 planted。"""
    meta_state = th["meta"].get("state")
    if meta_state == "dropped":
        return "dropped"
    log = get_section(th["body"], "推进日志") or ""
    all_ops = thread_ops_from_log(log)
    if not all_ops:
        return meta_state
    ops = thread_ops_from_log(log, exclude_ch=exclude_ch)
    if not ops:
        return "planted"
    st = "planted"
    for op in ops:
        nxt = thread_next_state(st, op)
        if nxt:
            st = nxt
    return st


def strip_ch_lines(text, ch_id):
    """剔除 `- ch_NNNN: …` 日志行（实体事件日志/线索推进日志的撤销半边）。"""
    kept, removed = [], 0
    for ln in text.splitlines():
        if re.match(r"^-\s*%s\s*:" % ch_id, ln.strip()):
            removed += 1
            continue
        kept.append(ln)
    return "\n".join(kept), removed


def dedup_latest_rev(rows):
    """(chapter, rev) 语义的读侧物化去重：同章多 rev 行只保留最大 rev 的行
    （revise 重提交 = 追加新 rev 行，读侧取代旧行；台账文件本身仍 append-only）。"""
    max_rev = {}
    for r in rows:
        max_rev[r["chapter"]] = max(max_rev.get(r["chapter"], 0), r.get("rev", 1))
    return [r for r in rows if r.get("rev", 1) == max_rev[r["chapter"]]]


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


# ---------------------------------------------------------------- 报告器
class Report:
    LEVELS = ("PASS", "WARN", "FAIL", "NEEDS_REVIEW", "SKIP")

    def __init__(self):
        self.items = []

    def add(self, level, name, details=None, fix=None):
        """fix = 可执行的下一步命令/动作（gate 家族用：FAIL 不只报错，还给修复剧本）。"""
        assert level in self.LEVELS
        self.items.append((level, name, details or [], fix))

    def render(self, title):
        counts = {k: 0 for k in self.LEVELS}
        print("== %s ==" % title)
        for level, name, details, fix in self.items:
            counts[level] += 1
            if level == "PASS":
                continue
            print("[%s] %s" % (level, name))
            for d in details[:15]:
                print("        %s" % d)
            if len(details) > 15:
                print("        ... 另 %d 条" % (len(details) - 15))
            if fix:
                print("        ↳ 下一步：%s" % fix)
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
              "tasks", "state/court", "state/reports", "state/txn", "corpus"):
        (root / d).mkdir(parents=True, exist_ok=True)
    cfg = json.loads(read(TEMPLATES / "config.json"))
    cfg["name"] = args.name or root.name
    write(root / "config.json", json.dumps(cfg, ensure_ascii=False, indent=2))
    rep = {"[YYYY-MM-DDTHH:MM:SSZ]": NOW()}
    for t, dest in (("book.md", "tree/book.md"), ("style.md", "tree/style.md"),
                    ("world.md", "tree/world.md")):
        write(root / dest, instantiate(t, rep))
    write(root / "ledgers/timeline.tsv", "chapter\tstory_date\telapsed\tnote\trev\n")
    write(root / "ledgers/payoff.tsv", "chapter\tpayoff_id\tkind\tintent\trealized\trev\n")
    write(root / "ledgers/power.tsv", "chapter\tentity\tfrom\tto\tnote\trev\n")
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
    warnings = ["[%s] %s" % (l, n) for l, n, _, _ in wrep.items
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
    """P0-2（收紧）：drafted→approved 仅认 reviews/ 落盘回执——verdict=pass 且
    rev_reviewed == 章当前 rev。任务 note 自证通道（light=pass 正则）已删除：
    评审结论必须落盘（novel.py review add），闸门不接受口头/note 自我盖章。"""
    p = proj.p("chapters", ch_id + ".md")
    cur_rev = 1
    if p.is_file():
        meta, _ = parse_frontmatter(read(p))
        cur_rev = (meta or {}).get("rev") or 1
    stale = []
    for depth in ("light", "deep"):
        f = proj.p("reviews", "%s.%s.md" % (ch_id, depth))
        if not f.is_file():
            continue
        meta, _ = parse_frontmatter(read(f))
        meta = meta or {}
        if meta.get("verdict") != "pass":
            continue
        if meta.get("rev_reviewed") != cur_rev:
            stale.append("reviews/%s.%s.md rev_reviewed=%s ≠ 章 rev=%s"
                         % (ch_id, depth, meta.get("rev_reviewed"), cur_rev))
            continue
        return "reviews/%s.%s.md verdict=pass rev_reviewed=%s" % (ch_id, depth, cur_rev)
    for s in stale:
        print("[warn] 回执过期：%s（章已 revise，须对当前 rev 复评）" % s)
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
                die("approved 需落盘评审回执：reviews/%s.light|deep.md（verdict=pass 且 "
                    "rev_reviewed=章当前 rev）。轻评结论用 novel.py review add 落盘；"
                    "任务 note 与 --evidence 不再是回执通道（P0-2 收紧，pipeline §1 步骤 8）"
                    % args.id, 1)
            meta["approved_evidence"] = receipt + (
                "；" + args.evidence if getattr(args, "evidence", None) else "")
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
        if args.type == "revise_rubric":
            if not args.evidence:
                die("revise_rubric 必须带 --evidence（lessons/review 条目引用——"
                    "蒸馏要有出处，workflow.md §6）", 1)
            if args.target != "style":
                die("revise_rubric 目标仅支持 style（tree/style.md 禁忌黑名单是机检"
                    "唯一登记处；skill 侧 rubrics/ 不随项目改）", 1)
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


def voice_block(ent_body):
    """P1-3：从实体『设定』节抽声纹小节（口癖/句式/禁词/例句）——声纹升独立块，
    预算裁剪时与实体『设定要点』解耦（设定可裁，声纹不裁）。"""
    sec = get_section(ent_body, "设定") or ""
    lines, on = [], False
    for ln in sec.splitlines():
        if re.match(r"^-\s*声纹", ln.strip()):
            on = True
            continue
        if on:
            if re.match(r"^- \S", ln):
                break
            if ln.strip() and not ln.strip().startswith("["):
                lines.append(ln.rstrip())
    return "\n".join(lines)


BRIEF_SECTIONS = ("0 任务卡", "1 文风与禁忌", "2 直接上文", "3 出场实体状态卡",
                  "4 活跃线索", "5 弧内位置", "6 相关事实与设定", "7 写作提示",
                  "8 回写契约")

# 条目级优先级（P1-2：分越高越后裁；must=True 永不裁 = must-not-drop 集）
PRIO = {"arc_chain": 62, "arc_rows": 58, "ent_setting_lead": 55, "ent_setting": 50,
        "thread_near": 48, "thread_scope": 45, "world_rules": 44, "rollup_arc": 42,
        "recap": 41, "style_imagery": 40, "rollup_vol": 38, "fact_base": 30,
        "style_anchor": 29, "tips": 25, "lessons": 20}


def cmd_brief(args):
    """P1-2 条目级预算装配：每个条目带优先级与 must-not-drop 标记；超预算逐条
    从最低分裁起（非整节丢弃），裁剪逐项留痕溯源表。"""
    proj = Project(find_root(args))
    ch_id = args.ch_id
    task = proj.chapter_task(ch_id)
    if not task:
        die("缺任务卡 chapters/%s.task.json（先 tree add chapter + 排批补全）" % ch_id, 1)
    budget = proj.config.get("brief_budget_chars", 24000)
    num = ch_num(ch_id)
    route = proj.config.get("route", "web")
    cur_vol = proj.vol_of_chapter(ch_id)
    prov = []   # (资产, rev, 用途)
    items = []  # {sec, key, text, prio, must}

    def add(sec, key, text, prio=50, must=False):
        if text and str(text).strip():
            items.append({"sec": sec, "key": key, "text": str(text).rstrip(),
                          "prio": prio, "must": must})

    # §0 任务卡（must）
    add("0 任务卡", "task.json",
        "```json\n" + json.dumps(task, ensure_ascii=False, indent=1) + "\n```", must=True)

    # §1 文风：基准+禁忌 must；比喻/范文锚可裁
    style_p = proj.p("tree", "style.md")
    style_meta, style_body = parse_frontmatter(read(style_p))
    add("1 文风与禁忌", "叙述基准",
        "### 叙述基准\n" + (get_section(style_body, "叙述基准") or ""), must=True)
    add("1 文风与禁忌", "口癖禁忌",
        "### 口癖与句式禁忌（命中即违规）\n"
        + (get_section(style_body, "口癖与句式禁忌") or ""), must=True)
    add("1 文风与禁忌", "比喻纪律",
        "### 比喻与意象纪律\n" + (get_section(style_body, "比喻与意象纪律") or ""),
        PRIO["style_imagery"])
    add("1 文风与禁忌", "范文锚",
        "### 范文锚\n" + (get_section(style_body, "范文锚") or ""), PRIO["style_anchor"])
    prov.append(("tree/style.md", style_meta.get("rev"), "§1 文风与禁忌"))

    # §2 直接上文：前章尾+summary 链 must；rollup/recap 可裁（P1-1 记忆分层）
    prev_id = "ch_%04d" % (num - 1)
    prev_p = proj.p("chapters", prev_id + ".md")
    has_ctx = False
    if num > 1 and prev_p.is_file():
        _, prev_body = parse_frontmatter(read(prev_p))
        prev_text = prev_body.split("## 正文", 1)[-1]
        add("2 直接上文", "前章尾",
            "### 前章（%s）尾 500 字\n%s" % (prev_id, tail_chars(prev_text, 500)),
            must=True)
        prov.append(("chapters/%s.md" % prev_id, "-", "§2 前章尾"))
        has_ctx = True
    for i in range(max(1, num - 3), num):
        pid = "ch_%04d" % i
        m = proj.chapter_meta_json(pid)
        if m and m.get("summary_after"):
            add("2 直接上文", "summary:%s" % pid,
                "- %s 概要：%s" % (pid, m["summary_after"]), must=True)
            prov.append(("chapters/%s.meta.json" % pid, "-", "§2 summary 链"))
            has_ctx = True
    rollup_p = proj.p("state", "rollup.json")
    if rollup_p.is_file():
        try:
            rollup = json.loads(read(rollup_p))
        except ValueError:
            rollup = {}
        arc_id0 = task.get("arc")
        a = (rollup.get("arcs") or {}).get(arc_id0)
        if a:
            far = [l for l in a["lines"]
                   if int(l[3:7]) < max(1, num - 3)][-10:]
            if far:
                add("2 直接上文", "rollup:arc",
                    "### 本弧前情（rollup 卷积）\n" + "\n".join("- %s" % l for l in far),
                    PRIO["rollup_arc"])
                prov.append(("state/rollup.json", "-", "§2 弧 rollup"))
                has_ctx = True
        vol_lines = []
        for vid in sorted(rollup.get("volumes") or {}):
            for l in rollup["volumes"][vid]:
                if not l.startswith(str(arc_id0)):
                    vol_lines.append("%s ｜ %s" % (vid, l))
        if vol_lines:
            add("2 直接上文", "rollup:vol",
                "### 卷级前情（rollup 卷积）\n"
                + "\n".join("- %s" % l for l in vol_lines[-6:]), PRIO["rollup_vol"])
            prov.append(("state/rollup.json", "-", "§2 卷 rollup"))
            has_ctx = True
    recap_p = proj.p("ledgers", "recap.md")
    if recap_p.is_file():
        rl = [l for l in read(recap_p).splitlines()
              if l.strip() and not l.strip().startswith("#")]
        if rl:
            add("2 直接上文", "recap",
                "### 全局 recap（ledgers/recap.md 尾段）\n" + "\n".join(rl[-12:]),
                PRIO["recap"])
            prov.append(("ledgers/recap.md", "-", "§2 recap"))
            has_ctx = True
    if not has_ctx:
        add("2 直接上文", "empty", "（首章，无上文）", must=True)

    # §3 实体状态卡：声纹速查+现状/最近事件 must；设定要点可裁（P1-3）
    ents = proj.entities()
    voice_lines = []
    cast_list = task.get("cast", [])
    for idx, ref in enumerate(cast_list):
        eid = proj.resolve_entity(ref)
        if not eid or eid not in ents:
            add("3 出场实体状态卡", "缺卡:%s" % ref,
                "- 【缺卡】%s（资料员应报缺料）" % ref, must=True)
            continue
        e = ents[eid]
        status_sec = get_section(e["body"], "现状") or ""
        log = get_section(e["body"], "事件日志") or ""
        log_tail = "\n".join([l for l in log.splitlines()
                              if l.strip().startswith("-")][-3:])
        add("3 出场实体状态卡", "ent:%s:卡" % eid,
            "### %s\n现状：\n%s\n\n最近事件：\n%s"
            % (eid, status_sec, log_tail or "（无）"), must=True)
        setting = get_section(e["body"], "设定") or ""
        setting = "\n".join(setting.splitlines()[:14])
        add("3 出场实体状态卡", "ent:%s:设定" % eid,
            "设定要点（超预算首裁，全文见 entities/%s.md）：\n%s" % (eid, setting),
            PRIO["ent_setting_lead"] if idx == 0 else PRIO["ent_setting"])
        vb = voice_block(e["body"])
        if vb:
            voice_lines.append("**%s**\n%s" % (eid, vb))
        prov.append(("entities/%s.md" % eid, e["meta"].get("rev"), "§3 状态卡"))
    if voice_lines:
        # 声纹速查置于实体卡之前（must——设定可裁而声纹不裁，防千人一腔）
        items.insert(
            next(i for i, it in enumerate(items) if it["sec"] == "3 出场实体状态卡"),
            {"sec": "3 出场实体状态卡", "key": "声纹速查",
             "text": "### 声纹速查（对话守卡依据，rubrics/voice.md）\n\n"
                     + "\n\n".join(voice_lines), "prio": 99, "must": True})
    if not cast_list:
        add("3 出场实体状态卡", "empty", "（任务卡未列 cast）", must=True)

    # §4 活跃线索：listed/must_not_drop 线 must；scope/payoff 临近可裁
    def payoff_near(m):
        pp = m.get("payoff_planned")
        if not pp:
            return False
        if str(pp) == cur_vol:
            return True
        mm = re.match(r"^ch_(\d{4})$", str(pp))
        return bool(mm) and 0 <= int(mm.group(1)) - num <= 15

    threads = proj.threads()
    listed = {t["id"] for t in task.get("threads", [])}
    n_threads = 0
    for tid, th in threads.items():
        m = th["meta"]
        live = m.get("state") in THREAD_LIVE
        scope_hit = cur_vol in (m.get("volume_scope") or [])
        near = payoff_near(m)
        pinned = tid in listed or (live and m.get("must_not_drop"))
        relevant = pinned or (live and (scope_hit or near))
        if not relevant:
            continue
        stmt = get_section(th["body"], "陈述") or ""
        log = get_section(th["body"], "推进日志") or ""
        log_tail = "\n".join([l for l in log.splitlines()
                              if l.strip().startswith("-")][-2:])
        tags = ""
        if m.get("must_not_drop"):
            tags += "【must_not_drop】"
        if near:
            tags += "【payoff 临近：%s】" % m.get("payoff_planned")
        add("4 活跃线索", "thread:%s" % tid,
            "- **%s** [%s/%s]%s：%s\n  最近推进：%s"
            % (tid, m.get("thread_kind"), m.get("state"), tags,
               stmt.splitlines()[0] if stmt else "", log_tail or "（无）"),
            PRIO["thread_near"] if near else PRIO["thread_scope"], must=pinned)
        prov.append(("threads/%s.md" % tid, m.get("rev"), "§4 线索"))
        n_threads += 1
    if not n_threads:
        add("4 活跃线索", "empty", "（无活跃线索命中）", must=True)

    # §5 弧内位置
    arc_id = task.get("arc")
    arc_p = proj.node_path(arc_id) if arc_id else None
    if arc_p and arc_p.is_file():
        arc_meta, arc_body = parse_frontmatter(read(arc_p))
        chain = get_section(arc_body, "因果链") or ""
        alloc = get_section(arc_body, "章分配草案") or ""
        rows = [l for l in alloc.splitlines() if re.search(r"ch_\d{4}", l)]
        near_rows = [l for l in rows if any(("ch_%04d" % i) in l
                                            for i in (num - 1, num, num + 1))]
        add("5 弧内位置", "因果链",
            "### 弧因果链（%s）\n%s" % (arc_id, chain), PRIO["arc_chain"])
        add("5 弧内位置", "前后位置",
            "### 本章前后位置\n" + ("\n".join(near_rows) or "（章分配草案未含本章）"),
            PRIO["arc_rows"])
        prov.append((str(arc_p.relative_to(proj.root)), arc_meta.get("rev"),
                     "§5 弧内位置"))
    else:
        add("5 弧内位置", "empty", "（弧计划缺失）", must=True)

    # §6 相关事实与设定：逐 fact 一条（按 时近+键位+retcon 连带 记分），世界规则单列
    cast_ids = {proj.resolve_entity(r) for r in task.get("cast", [])} - {None}
    n_facts = 0
    for f in proj.facts_files():
        data = json.loads(read(f))
        retcons = {r.get("old_fact_id"): r for r in data.get("retcons", [])}
        for fact in data.get("facts", []):
            if not (set(fact.get("entity_ids", [])) & cast_ids):
                continue
            spoiler = "【读者未知，只可潜台词】" if fact.get("spoiler") else ""
            # P4-K 知识矩阵注入：知情名单 + 本章在场不知情者（写手的硬约束）
            known = fact.get("known_by") or []
            if known:
                spoiler += "【知情仅:%s】" % ",".join(known)
                unaware = sorted(cast_ids - set(known))
                if unaware:
                    spoiler += "【本章出场 %s 不知情——不得由其说破或表现知情】" \
                               % ",".join(unaware)
            sup = fact.get("superseded_by")
            line = "- %s%s（%s，ch%s）" % (spoiler, fact.get("fact"),
                                           fact.get("id"), fact.get("revealed_ch"))
            prio = PRIO["fact_base"]
            rc = fact.get("revealed_ch")
            if isinstance(rc, int) and num - rc <= 30:
                prio += 10
            if fact.get("key"):
                prio += 3
            if sup:
                r = retcons.get(fact.get("id"), {})
                line += "\n  ↳【已被覆盖】新事实：%s（策略 %s，%s）" % (
                    r.get("new_fact", "?"), r.get("strategy", "?"),
                    r.get("decision_ref", "?"))
                prio += 5
            add("6 相关事实与设定", "fact:%s" % fact.get("id"), line, prio)
            n_facts += 1
        prov.append((str(f.relative_to(proj.root)), "-", "§6 事实"))
    world_p = proj.p("tree", "world.md")
    if world_p.is_file():
        wmeta, wbody = parse_frontmatter(read(world_p))
        add("6 相关事实与设定", "世界规则",
            "### 世界核心规则\n" + (get_section(wbody, "核心规则") or ""),
            PRIO["world_rules"])
        prov.append(("tree/world.md", wmeta.get("rev"), "§6 世界规则"))
    if not n_facts and not world_p.is_file():
        add("6 相关事实与设定", "empty", "（无相关事实）", must=True)

    # §7 写作提示（route 选配）+ lessons
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
    add("7 写作提示", "tips", "\n".join(tips), PRIO["tips"])
    lessons_p = proj.p("ledgers", "lessons.md")
    lessons = [l for l in read(lessons_p).splitlines() if l.startswith("- ")][-5:] \
        if lessons_p.is_file() else []
    add("7 写作提示", "lessons",
        "近期教训（lessons 台账尾 5 条）：\n" + "\n".join(lessons or ["- （暂无）"]),
        PRIO["lessons"])
    if lessons:
        prov.append(("ledgers/lessons.md", "-", "§7 教训"))

    # §8 回写契约（must）
    add("8 回写契约", "schema",
        "提交格式：最终回复两段——【正文】章文件（信封+## 正文）；【writeback】如下 schema 的"
        "JSON 块（power_delta 可选，战力/位阶变化时必填；continuity_delta 每条可选 key "
        "字段标注实体状态键位，如「位置」「持有」）：\n\n```json\n"
        + read(TEMPLATES / "chapter.meta.json").strip() + "\n```", must=True)

    prev_brief = proj.p("briefs", ch_id + ".brief.md")
    brief_rev = 1
    if prev_brief.is_file():
        m = re.search(r"<!-- brief_rev: (\d+) -->", read(prev_brief))
        brief_rev = (int(m.group(1)) if m else 0) + 1

    trimmed = []  # (sec, key)

    def render(active):
        head = ["<!-- chapter: %s -->" % ch_id, "<!-- brief_rev: %d -->" % brief_rev,
                "<!-- compiled_at: %s -->" % NOW(), "<!-- budget_chars: %d -->" % budget]
        parts = ["\n".join(head)]
        cut_by_sec = {}
        for sec, key in trimmed:
            cut_by_sec.setdefault(sec, []).append(key)
        for sec in BRIEF_SECTIONS:
            chunks = [it["text"] for it in active if it["sec"] == sec]
            if sec in cut_by_sec:
                chunks.append("（本节超预算裁剪 %d 项：%s——原始来源见溯源表）"
                              % (len(cut_by_sec[sec]), "、".join(cut_by_sec[sec])))
            parts.append("## %s\n\n%s" % (sec, "\n\n".join(chunks) or "（空）"))
        prov_lines = ["| 资产 | rev | 用途 |", "|---|---|---|"]
        seen = set()
        for pr in prov:
            if pr not in seen:
                seen.add(pr)
                prov_lines.append("| %s | %s | %s |" % pr)
        if trimmed:
            prov_lines.append("| （裁剪） | - | 条目级裁剪 %d 项：%s |"
                              % (len(trimmed),
                                 "、".join(k for _, k in trimmed)[:300]))
        parts.append("## 附 溯源\n\n" + "\n".join(prov_lines))
        return "\n\n".join(parts) + "\n"

    active = list(items)
    text = render(active)
    while len(text) > budget:
        droppable = [it for it in active if not it["must"]]
        if not droppable:
            break  # must-not-drop 集已到底线，超预算如实交付
        victim = min(enumerate(droppable),
                     key=lambda x: (x[1]["prio"], -x[0]))[1]
        active.remove(victim)
        trimmed.append((victim["sec"], victim["key"]))
        text = render(active)
    write(prev_brief, text)
    git_autocommit(proj.root, "[brief] %s rev%d（保证 spawn 前基线干净）" % (ch_id, brief_rev))
    print("简报已生成：briefs/%s.brief.md（%d 字符 / 预算 %d%s）"
          % (ch_id, len(text), budget,
             "，条目级裁剪 %d 项" % len(trimmed) if trimmed else ""))
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
    """ngram_cache 条目取指纹；兼容旧版扁平 list（视为 n12）与归档层（n12s 降采样）。"""
    if isinstance(entry, dict):
        if key == "n12":
            return set(entry.get("n12") or entry.get("n12s") or [])
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


# ---------------------------------------------------------------- 故事日历（P2-2）
CN_NUM = {"半": 0.5, "一": 1, "两": 2, "二": 2, "三": 3, "四": 4, "五": 5,
          "六": 6, "七": 7, "八": 8, "九": 9, "十": 10, "数": 3, "几": 3}
UNIT_DAYS = {"年": 360, "月": 30, "旬": 10, "周": 7, "天": 1, "日": 1,
             "夜": 1, "晚": 1, "时辰": 1 / 12.0, "小时": 1 / 24.0, "刻": 1 / 96.0}
ZERO_ELAPSED = ("当天", "同日", "当日", "当夜", "同一天", "片刻", "即时", "紧接", "0")


def cn_num(raw):
    if re.fullmatch(r"\d+(\.\d+)?", raw):
        return float(raw)
    if raw.startswith("十"):
        return 10 + (CN_NUM.get(raw[1:], 0) if len(raw) > 1 else 0)
    if len(raw) == 2 and raw[1] == "十":
        return CN_NUM.get(raw[0], 1) * 10
    if len(raw) == 3 and raw[1] == "十":
        return CN_NUM.get(raw[0], 1) * 10 + CN_NUM.get(raw[2], 0)
    return CN_NUM.get(raw, 0) if len(raw) == 1 else sum(CN_NUM.get(c, 0) for c in raw)


def parse_elapsed_days(s):
    """time_advance.elapsed → 折算天数；无法解析返回 None（游离于故事日历外）。"""
    s = (s or "").strip()
    if not s:
        return 0.0
    if s in ZERO_ELAPSED:
        return 0.0
    total, hit = 0.0, False
    for m in re.finditer(r"(\d+(?:\.\d+)?|[半一两二三四五六七八九十数几]{1,3})\s*个?\s*"
                         r"(时辰|小时|年|月|旬|周|天|日|夜|晚|刻)", s):
        total += cn_num(m.group(1)) * UNIT_DAYS[m.group(2)]
        hit = True
    return total if hit else None


def parse_story_date(s):
    """story_date 断言解析：ISO（2026-08-24）或 中式（三年五月初二 不支持；支持
    NNNN年NN月NN日）→ 可比较元组；解析失败返回 None（不参与单调断言）。"""
    s = (s or "").strip()
    if not s:
        return None
    m = re.fullmatch(r"(\d{1,4})-(\d{1,2})-(\d{1,2})", s)
    if not m:
        m = re.fullmatch(r"(\d{1,4})年(\d{1,2})月(\d{1,2})日?", s)
    return (int(m.group(1)), int(m.group(2)), int(m.group(3))) if m else None


# ---------------------------------------------------------------- 抽取器（P2-1 双记账机器半边）
def extract_observations(proj, text):
    """从正文反向解析可机读观察：已登记专名的出场计数 + 引号内新专名候选。
    这是「写手自报（writeback）↔ 文本实测」双记账的机器半边；语义类观察
    （爽点是否真兑现、线索是否真推进）仍归评审。"""
    names = {}
    for alias, eid in proj.aliases().items():
        names[str(alias)] = eid
    alias_bearing = set()
    for eid, e in proj.entities().items():
        for a in e["meta"].get("aliases") or []:
            names[str(a)] = eid
    for name, eid in names.items():
        if len(name) >= 2:
            alias_bearing.add(eid)
    mentions = {}
    for name, eid in names.items():
        if len(name) < 2 or name.startswith("["):
            continue
        cnt = text.count(name)
        if cnt:
            mentions[eid] = mentions.get(eid, 0) + cnt
    quoted = re.findall(r"[「『]([\u4e00-\u9fff]{2,6})[」』]", text)
    freq = {}
    for q in quoted:
        freq[q] = freq.get(q, 0) + 1
    candidates = sorted(q for q, c in freq.items() if c >= 2 and q not in names)
    return {"mentions": mentions, "name_candidates": candidates,
            "alias_bearing": alias_bearing}


def extract_reconcile(proj, ch_id, text, wb, rep):
    """对账：文本实测出场 vs writeback.cast_actual；剧透事实文本相似泄漏候选。"""
    obs = extract_observations(proj, text)
    cast = {proj.resolve_entity(r) for r in (wb or {}).get("cast_actual", []) or []} \
        - {None}
    undeclared = sorted("%s（正文命中 %d 次）" % (eid, n)
                        for eid, n in obs["mentions"].items() if eid not in cast)
    phantom = sorted(eid for eid in cast
                     if eid in obs["alias_bearing"] and eid not in obs["mentions"])
    if undeclared:
        rep.add("WARN", "抽取器：正文出现已登记实体但 cast_actual 未申报"
                        "（实体日志/对账将漏记；补申报或删越权出场）", undeclared)
    if phantom:
        rep.add("WARN", "抽取器：cast_actual 申报了正文未出现的实体（幽灵出场；"
                        "仅对有已登记别名的实体可判）", phantom)
    if not undeclared and not phantom:
        rep.add("PASS", "抽取器：出场申报与文本实测一致（命中 %d 实体）"
                % len(obs["mentions"]))
    if obs["name_candidates"]:
        rep.add("NEEDS_REVIEW", "抽取器：引号内新专名候选（≥2 次且未登记——"
                                "简报外发明嫌疑，轻评对照简报裁定后 entity new/补别名）",
                obs["name_candidates"][:10])
    # P2-3 剧透泄漏候选：未覆盖 spoiler 事实与正文句子高相似 → 评审裁定
    num = ch_num(ch_id)
    sents = None
    spoilers = [x for x, _ in proj.all_facts()
                if x.get("spoiler") and not x.get("superseded_by")]
    if spoilers:
        leaks = []
        sents = sentences_of(text)
        for x in spoilers:
            if x.get("revealed_ch") == num:
                continue
            for s in sents:
                if ngram_sim(x.get("fact", ""), s) >= 0.5:
                    leaks.append("%s「%s」≈「%s…」" % (x.get("id"), x.get("fact"),
                                                       s[:20]))
                    break
        if leaks:
            rep.add("NEEDS_REVIEW", "抽取器：剧透事实文本相似泄漏候选"
                                    "（读者未知事实疑被明写；评审裁定改潜台词或走揭示）",
                    leaks[:8])
    # P4-K 知识矩阵角色半边：known_by 有限定的事实在正文被明写，而在场角色不在
    # 知情名单 → 角色知识越界候选（谁说破的？他不该知道）——评审裁定：
    # 改写为该角色不知情的演法 / 正文补获知场景并 knowledge grant / 删句。
    guarded = [x for x, _ in proj.all_facts()
               if x.get("known_by") and not x.get("superseded_by")
               and x.get("revealed_ch") != num]
    if guarded and cast:
        if sents is None:
            sents = sentences_of(text)
        overreach = []
        for x in guarded:
            unaware = sorted(cast - set(x["known_by"]))
            if not unaware:
                continue
            for s in sents:
                if ngram_sim(x.get("fact", ""), s) >= 0.5:
                    overreach.append("%s「%s」——在场未知情角色：%s（知情仅 %s）"
                                     % (x.get("id"), x.get("fact"),
                                        ",".join(unaware), ",".join(x["known_by"])))
                    break
        if overreach:
            rep.add("NEEDS_REVIEW", "抽取器：角色知识越界候选（事实被明写而在场角色"
                                    "不在 known_by 名单——评审裁定：改暗写/补获知场景后"
                                    " knowledge grant/删句）", overreach[:8])
    return obs


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


# ---------------------------------------------------------------- commit
def register_facts(proj, ch_id, wb, rev=1):
    """P0-1：commit 时自 continuity_delta 自动分配 fact_id 写入 ledgers/facts/vol_NN.json。
    同文同章去重；rev>1（revise）时先剪除本章上一轮登记的临时事实（未被 retcon 引用、
    未被覆盖者），再按新 writeback 重登——(chapter, rev) 语义的 facts 半边。
    返回新登记的 fact id 列表。"""
    deltas = wb.get("continuity_delta", []) or []
    num = ch_num(ch_id)
    vol = proj.vol_of_chapter(ch_id)
    f = proj.p("ledgers", "facts", vol + ".json")
    data = json.loads(read(f)) if f.is_file() else {"facts": [], "retcons": []}
    pruned = 0
    if rev > 1:
        referenced = {r.get("old_fact_id") for r in data.get("retcons", [])}
        keep = [x for x in data.get("facts", [])
                if not (x.get("revealed_ch") == num and not x.get("superseded_by")
                        and x.get("id") not in referenced)]
        pruned = len(data.get("facts", [])) - len(keep)
        data["facts"] = keep
    if not deltas and not pruned:
        return []
    existing = {(x.get("fact"), x.get("revealed_ch")) for x in data.get("facts", [])}
    seq = 0
    for x, _ in proj.all_facts():
        m = re.match(r"^fact_(\d{4,})$", str(x.get("id", "")))
        if m:
            seq = max(seq, int(m.group(1)))
    for x in data.get("facts", []):
        m = re.match(r"^fact_(\d{4,})$", str(x.get("id", "")))
        if m:
            seq = max(seq, int(m.group(1)))
    seq += 1
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
        # P4-K 知识矩阵：事实 × 角色（known_by）× 读者（spoiler）——who-knows-what 台账
        if d.get("known_by"):
            rec["known_by"] = sorted({proj.resolve_entity(r) or r
                                      for r in d["known_by"]})
        data.setdefault("facts", []).append(rec)
        added.append(rec["id"])
        seq += 1
    write(f, json.dumps(data, ensure_ascii=False, indent=1))
    if pruned:
        added.append("(剪除上一 rev 临时事实 %d 条)" % pruned)
    return added


def unapply_chapter_logs(proj, ch_id):
    """P0-1 撤销半边（revise 前执行）：实体事件日志与线索推进日志剔除本章行；
    last_event_ch 由剩余日志重算；线索 state 由剩余 op 重放；plant_ch 回滚。"""
    touched = []
    for eid, e in proj.entities().items():
        body, removed = strip_ch_lines(e["body"], ch_id)
        if not removed:
            continue
        meta = e["meta"]
        remaining = [int(m.group(1)) for m in
                     re.finditer(r"^-\s*ch_(\d{4})\s*:", body, re.M)]
        meta["last_event_ch"] = max(remaining) if remaining else 0
        meta["updated_at"] = NOW()
        write(e["path"], dump_frontmatter(meta) + "\n" + body.lstrip("\n"))
        touched.append(eid)
    for tid, th in proj.threads().items():
        log = get_section(th["body"], "推进日志") or ""
        if not re.search(r"^-\s*%s\s*:" % ch_id, log, re.M):
            continue
        new_state = thread_effective_state(th, exclude_ch=ch_id)
        body, _ = strip_ch_lines(th["body"], ch_id)
        meta = th["meta"]
        meta["state"] = new_state
        if meta.get("plant_ch") == ch_num(ch_id):
            m = re.search(r"^-\s*ch_(\d{4})\s*:\s*plant\b", body, re.M)
            meta["plant_ch"] = int(m.group(1)) if m else None
        meta["updated_at"] = NOW()
        write(th["path"], dump_frontmatter(meta) + "\n" + body.lstrip("\n"))
        touched.append(tid)
    return touched


def apply_writeback(proj, ch_id, wb, rev=1):
    """continuity_delta → 实体事件日志 + facts 登记；thread_ops → 推进日志+state（合法迁移表）；
    payoff/timeline/power 台账（rev 列，读侧去重）。引用越权 = 硬失败（返回 (False, errors)，
    调用方拒绝落盘）。rev>1 = revise：先撤销本章上一轮日志效应再重放（零双计）。"""
    errs = writeback_ref_errors(proj, ch_id, wb)
    if errs:
        return False, errs
    num = ch_num(ch_id)
    notes = []
    if rev > 1:
        touched = unapply_chapter_logs(proj, ch_id)
        if touched:
            notes.append("revise 撤销重放：已剔除 %s 的上一轮日志行（%s）"
                         % (ch_id, " ".join(touched)))
    ents = proj.entities()
    for delta in wb.get("continuity_delta", []) or []:
        for ref in delta.get("entity_ids", []):
            eid = proj.resolve_entity(ref)
            e = ents[eid]
            body = e["body"].rstrip() + "\n- %s: %s\n" % (ch_id, delta.get("fact", ""))
            meta = e["meta"]
            meta["last_event_ch"] = max(num, meta.get("last_event_ch") or 0)
            meta["updated_at"] = NOW()
            write(e["path"], dump_frontmatter(meta) + "\n" + body.lstrip("\n"))
            ents = proj.entities()  # 重载，防同章多条
    threads = proj.threads()
    for op in wb.get("thread_ops", []) or []:
        tid = op["id"]
        t = threads[tid]
        meta = t["meta"]
        nxt = thread_next_state(meta.get("state"), op["op"])
        body = t["body"].rstrip() + "\n- %s: %s %s\n" % (ch_id, op["op"], op.get("note", ""))
        meta["state"] = nxt
        if op["op"] == "plant" and not meta.get("plant_ch"):
            meta["plant_ch"] = num  # P1-3：plant 回填 plant_ch
        meta["updated_at"] = NOW()
        write(t["path"], dump_frontmatter(meta) + "\n" + body.lstrip("\n"))
        threads = proj.threads()
    # facts 登记（P0-1；revise 先剪后登）
    added = register_facts(proj, ch_id, wb, rev=rev)
    if added:
        notes.append("facts 已登记：%s → ledgers/facts/%s.json"
                     % (" ".join(added), proj.vol_of_chapter(ch_id)))
    # payoff 台账（rev 列）
    task = proj.chapter_task(ch_id) or {}
    quota = task.get("payoff_quota", [])
    realized = set(wb.get("payoff_realized", []))
    with open(proj.p("ledgers", "payoff.tsv"), "a", encoding="utf-8") as f:
        for i, q in enumerate(quota, 1):
            pid = "payoff_%04d_%d" % (num, i)
            f.write("%s\t%s\t%s\t%s\t%d\t%d\n"
                    % (ch_id, pid, q.get("kind", "other"), q.get("intent", ""),
                       1 if pid in realized else 0, rev))
    # timeline（rev 列）
    ta = wb.get("time_advance", {})
    with open(proj.p("ledgers", "timeline.tsv"), "a", encoding="utf-8") as f:
        f.write("%s\t%s\t%s\t\t%d\n"
                % (ch_id, ta.get("story_date", ""), ta.get("elapsed", ""), rev))
    # power 台账（P1-6，可选键；rev 列）
    pd = wb.get("power_delta", []) or []
    if pd:
        pf = proj.p("ledgers", "power.tsv")
        if not pf.is_file():
            write(pf, "chapter\tentity\tfrom\tto\tnote\trev\n")
        with open(pf, "a", encoding="utf-8") as f:
            for d in pd:
                for ref in d.get("entity_ids", []):
                    eid = proj.resolve_entity(ref)
                    f.write("%s\t%s\t%s\t%s\t%s\t%d\n"
                            % (ch_id, eid, d.get("from", ""), d.get("to", ""),
                               d.get("note", ""), rev))
        notes.append("power 台账已追加 %d 行" % sum(len(d.get("entity_ids", [])) for d in pd))
    return True, notes


# ---------------------------------------------------------------- 事务日志（P0-3）
def txn_begin(proj, kind, target, task_id=""):
    """原子提交半边：多文件落盘前写 journal（done=false），全部写完后 txn_end 收口。
    中途崩溃 → journal 残留 done=false，fsck/check --project 报半事务。"""
    tdir = proj.p("state", "txn")
    tdir.mkdir(parents=True, exist_ok=True)
    # 修剪：已完成 journal 只保留最近 20 份
    done = sorted([f for f in tdir.glob("txn_*.json")
                   if json.loads(read(f)).get("done")], key=lambda f: f.name)
    for f in done[:-20]:
        f.unlink()
    txn_id = "txn_%s_%s" % (datetime.datetime.now().strftime("%Y%m%d%H%M%S%f"), target)
    write(tdir / (txn_id + ".json"), json.dumps(
        {"id": txn_id, "kind": kind, "target": target, "task": task_id,
         "started_at": NOW(), "done": False}, ensure_ascii=False, indent=1))
    return txn_id


def txn_end(proj, txn_id):
    f = proj.p("state", "txn", txn_id + ".json")
    if f.is_file():
        data = json.loads(read(f))
        data["done"] = True
        data["completed_at"] = NOW()
        write(f, json.dumps(data, ensure_ascii=False, indent=1))


def update_ngram_cache(proj, ch_id, text):
    """P2-4 分层指纹保留：窗口内两级全量（n12+n8）；窗口外降级为归档层
    （n12s = 12-gram 稳定降采样），12 字级自我复读检测覆盖全史而体积有界。"""
    cache = proj.ngram_cache()
    cache[ch_id] = {"n12": sorted(set(char_ngrams(text, 12))),
                    "n8": sorted(set(char_ngrams(text, 8)))}
    window = proj.config.get("ngram_window_chapters", 30)
    sample = proj.config.get("ngram_archive_sample", 400)
    keys = sorted(cache, key=lambda k: ch_num(k) if re.match(r"ch_\d{4}$", k) else 0)
    for k in keys[:-window]:
        entry = cache.get(k)
        if isinstance(entry, dict) and "n12s" in entry:
            continue  # 已归档
        n12 = sorted(cache_fps(entry, "n12"))
        step = max(1, len(n12) // max(sample, 1))
        cache[k] = {"n12s": n12[::step][:sample]}
    write(proj.p("state", "ngram_cache.json"), json.dumps(cache, ensure_ascii=False))


def first_sentence(text, limit=60):
    s = re.split(r"[。！？!?\n]", (text or "").strip())[0].strip()
    return s[:limit] + ("…" if len(s) > limit else "")


def update_rollup(proj):
    """P1-1 自动摘要卷积（章→弧→卷），commit 后增量重算 state/rollup.json。
    弧级 = 各章 summary_after 首句；卷级 = 各弧首末摘要压缩。brief §2 注入为
    远程记忆层——距离越远颗粒越粗，百万字仍可在预算内召回前情。"""
    chs = {}
    for c in proj.chapters():
        if c["meta"].get("status") not in ("drafted", "approved", "published"):
            continue
        mj = proj.chapter_meta_json(c["id"]) or {}
        s = (mj.get("summary_after") or "").strip()
        if not s:
            continue
        arc = (proj.chapter_task(c["id"]) or {}).get("arc") \
            or c["meta"].get("parent") or "arc_?"
        chs[c["id"]] = {"arc": arc, "vol": vol_of_arc(arc) or "vol_01", "summary": s}
    arcs = {}
    for cid in sorted(chs):
        e = chs[cid]
        arcs.setdefault(e["arc"], {"vol": e["vol"], "chapters": []})["chapters"].append(cid)
    rollup = {"generated_at": NOW(), "arcs": {}, "volumes": {}}
    for aid in sorted(arcs):
        a = arcs[aid]
        ids = a["chapters"]
        rollup["arcs"][aid] = {
            "vol": a["vol"], "span": [ids[0], ids[-1]],
            "lines": ["%s：%s" % (cid, first_sentence(chs[cid]["summary"]))
                      for cid in ids]}
    for aid in sorted(rollup["arcs"]):
        a = rollup["arcs"][aid]
        head = first_sentence(chs[a["span"][0]]["summary"], 40)
        tail = first_sentence(chs[a["span"][1]]["summary"], 40)
        line = "%s（%s–%s）：%s" % (aid, a["span"][0][3:], a["span"][1][3:],
                                    head if a["span"][0] == a["span"][1]
                                    else head + " ⋯ " + tail)
        rollup["volumes"].setdefault(a["vol"], []).append(line)
    write(proj.p("state", "rollup.json"), json.dumps(rollup, ensure_ascii=False, indent=1))
    return rollup


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
        new_rev = (old_meta.get("rev") or 0) + 1 if ttype == "revise" \
            else max(old_meta.get("rev") or 1, 1)
        # 先做回写引用硬校验（引用越权=拒绝，不产生任何写入）
        errs = writeback_ref_errors(proj, ch_id, wb)
        if errs:
            print("[拒绝] writeback 引用越权，未落盘：")
            for e in errs:
                print("  - " + e)
            return 1
        # P0-3：journal → 多文件落盘 → 完成标记（中断可被 fsck 检出）
        txn = txn_begin(proj, ttype, ch_id, args.task_id)
        ok, msgs = apply_writeback(proj, ch_id, wb, rev=new_rev)
        if not ok:  # 双保险（理论不可达：上面已预校验）
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
        update_rollup(proj)
        txn_end(proj, txn)
        for w in msgs:
            print("[info] " + w)
        git_autocommit(proj.root, "[%s] %s(%s): %s" % (args.task_id, ttype, ch_id, msg))
        print("已落盘：%s（status=drafted, rev=%d）+ meta.json + facts/台账/日志/ngram/rollup"
              % (ch_id, new_meta["rev"]))
        return 0

    if ttype in ("design", "revise_design", "review_deep", "revise_rubric"):
        if not args.file:
            die("%s 需 --file <staged 文件> [...]" % ttype)
        if ttype in ("revise_design", "revise_rubric") and not t.get("evidence"):
            die("%s 任务缺 evidence（revise_design 先过否决案台账 court.md §4；"
                "revise_rubric 须引用 lessons/review 条目）" % ttype, 1)
        # P0-3：两遍制——第一遍全量校验（零写入），第二遍才落盘（多文件原子性）
        staged = []
        for fpath in args.file:
            meta, body = parse_frontmatter(read(fpath))
            if meta is None:
                die("staged 文件无信封：%s" % fpath, 1)
            if ttype == "revise_rubric" and meta.get("kind") != "style":
                die("revise_rubric 只接受 kind=style 的 staged 文件（判据蒸馏专用轻量"
                    "路径，不波及树；其他节点走 revise_design）", 1)
            target = route_staged_file(proj, meta)
            if target is None:
                die("无法路由 kind=%s 的文件（id=%s）" % (meta.get("kind"), meta.get("id")), 1)
            if meta.get("kind") in NODE_KINDS and not args.draft:
                req = REQUIRED_SECTIONS.get(meta["kind"], [])
                titles = [x for x, _ in split_sections(body)]
                missing = [s for s in req
                           if not any(x == s or x.startswith(s) for x in titles)]
                empty = [s for s in req
                         if not missing and not (get_section(body, s) or "").strip()]
                if missing or empty:
                    die("design 校验失败 %s：缺节 %s / 空节 %s（全批未落盘）"
                        % (meta.get("id"), missing, empty), 1)
            staged.append((meta, body, target))
        txn = txn_begin(proj, ttype, t["target"], args.task_id)
        main_done = False
        for meta, body, target in staged:
            if ttype == "revise_rubric" and target.is_file():
                # P4-D 蒸馏路径：rev 自动 +1；不递归标 stale（黑名单增补只约束
                # 未来章的 check --unit，不作废既有章）
                old, _ = parse_frontmatter(read(target))
                meta["rev"] = ((old or {}).get("rev") or 0) + 1
            if meta.get("kind") in NODE_KINDS:
                if args.draft:
                    # P0-6：draft 态部分落盘（书庭中间场次可持久化半成品，不算定稿）
                    meta["status"] = "draft"
                    meta["updated_at"] = NOW()
                    write(target, dump_frontmatter(meta) + "\n" + body.lstrip("\n"))
                    print("已 draft 部分落盘 → %s（不算定稿，必需节校验延后到正式 commit）"
                          % target.relative_to(proj.root))
                    continue
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
        if ttype == "revise_rubric":
            print("蒸馏入库：style.md rev+1；新黑名单自下一次 check --unit 起机检生效"
                  "（不波及既有章）；来源 evidence：%s" % t.get("evidence"))
        txn_end(proj, txn)
        git_autocommit(proj.root, "[%s] %s(%s): %s" % (args.task_id, ttype, t["target"], msg))
        return 0

    die("commit 支持 write|revise|design|revise_design|review_deep|revise_rubric；"
        "publish 用 publish，retcon 用 retcon，checkpoint 用 checkpoint，"
        "reconcile 用 entity update", 2)


# ---------------------------------------------------------------- publish / ledger
def publish_problems(proj, frm, to):
    """publish 前置谓词（P3 gate 复用：只判不写）。返回 [(问题, 下一步)]（空 = 可发布）。"""
    probs = []
    cur = proj.cursor()
    if frm != cur["last_published"] + 1:
        probs.append(("连续性谓词失败：应从 ch_%04d 起（当前 last_published=%d），无绕过开关"
                      % (cur["last_published"] + 1, cur["last_published"]),
                      "改区间重试：novel.py publish ch_%04d [ch_to]"
                      % (cur["last_published"] + 1)))
    chs = {ch_num(c["id"]): c for c in proj.chapters()}
    not_ok = [n for n in range(frm, to + 1)
              if n not in chs or chs[n]["meta"].get("status") != "approved"]
    if not_ok:
        probs.append(("区间含非 approved 章：%s" % ["ch_%04d" % n for n in not_ok],
                      "逐章 novel.py gate approve ch_NNNN（FAIL 项自带下一步：评审→"
                      "review add→tree set-status approved），或缩小发布区间"))
    if cur["last_published"] == 0:
        need = proj.config.get("buffer", {}).get("min_before_publish", 1)
        if proj.buffer_ready() < need:
            probs.append(("首发前 ready=%d < min_before_publish=%d"
                          % (proj.buffer_ready(), need),
                          "先攒稿到位：推进 write 批至 approved（serial-ops §1 水位表）"))
    return probs


def cmd_publish(args):
    proj = Project(find_root(args))
    frm = ch_num(args.ch_from)
    to = ch_num(args.ch_to) if args.ch_to else frm
    probs = publish_problems(proj, frm, to)
    if probs:
        die("\n".join("%s\n  ↳ 下一步：%s" % pr for pr in probs), 1)
    chs = {ch_num(c["id"]): c for c in proj.chapters()}
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
        for r in proj.power_rows():
            print("%s %s：%s → %s %s（rev%d）"
                  % (r["chapter"], r["entity"], r["from"], r["to"],
                     r["note"], r["rev"]))
        if not proj.power_rows():
            print("（空）")
    else:
        rows = sorted(proj.timeline_rows(),
                      key=lambda r: ch_num(r["chapter"])
                      if re.match(r"^ch_\d{4}$", r["chapter"]) else 0)
        if not rows:
            print("（空）")
        else:
            print("chapter\tstory_date\telapsed\t累计天\tnote")
            cum = 0.0
            for r in rows:
                d = parse_elapsed_days(r["elapsed"])
                cum += d or 0
                print("%s\t%s\t%s\t%s\t%s"
                      % (r["chapter"], r["story_date"] or "-", r["elapsed"] or "-",
                         ("%.1f" % cum) if d is not None else "?（不可解析）",
                         r["note"]))
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
    warn = ["- [%s] %s" % (l, n) for l, n, _, _ in wrep.items if l in ("WARN", "FAIL")]
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


def checkpoint_problems(proj, vol_id):
    """checkpoint 前置谓词（P3 gate 复用：只判不写）。返回 [(问题, 下一步)]（空 = 可结账）。"""
    probs = []
    vp = proj.node_path(vol_id)
    if not vp or not vp.is_file():
        return [("卷不存在：%s" % vol_id,
                 "novel.py tree add volume %s → 卷庭定稿（court.md §1）" % vol_id)]
    vmeta, _ = parse_frontmatter(read(vp))
    if vmeta.get("status") != "committed":
        probs.append(("卷 %s 状态为 %s，须 committed 才可 checkpoint"
                      % (vol_id, vmeta.get("status")),
                      "卷庭定稿：novel.py task add design %s → commit <t> --file <卷蓝图>"
                      % vol_id))
    rp = proj.p("state", "reports", vol_id + ".md")
    if not rp.is_file():
        probs.append(("卷报告未汇编", "novel.py report volume %s（serial-ops §4 步骤 1）"
                      % vol_id))
    else:
        pending = [l.strip() for l in read(rp).splitlines() if "[待对账]" in l]
        if pending:
            probs.append(("exports 对账未完成，%d 条仍为 [待对账]：\n  %s"
                          % (len(pending), "\n  ".join(pending[:5])),
                          "编辑 %s 逐条标三态 [兑现 ch_NNNN]|[移交]|[废止 dec_xxx]"
                          "（serial-ops §4 步骤 2）" % rp.relative_to(proj.root)))
    bad = [c["id"] for c in volume_chapters(proj, vol_id)
           if c["meta"].get("status") in ("planned", "drafted", "stale")]
    if bad:
        probs.append(("卷内存在未完稿章（须 approved/published/archived）：%s" % " ".join(bad),
                      "逐章收尾：gate approve → set-status approved（不再写的章 "
                      "tree set-status <ch> archived）"))
    return probs


def cmd_checkpoint(args):
    """P0-4：卷末结账（formats §16 checkpoint 行）。
    校验：报告存在 + exports 三态齐 + 卷内无未完稿章；动作：卷标记 + 下卷 imports 预填。"""
    proj = Project(find_root(args))
    vol_id = args.vol_id
    m0 = re.match(r"^vol_(\d{2})$", vol_id)
    if not m0:
        die("卷 id 应为 vol_NN")
    probs = checkpoint_problems(proj, vol_id)
    if probs:
        die("\n".join("%s\n  ↳ 下一步：%s" % pr for pr in probs), 1)
    vp = proj.node_path(vol_id)
    vmeta, vbody = parse_frontmatter(read(vp))
    rp = proj.p("state", "reports", vol_id + ".md")
    rtext = read(rp)

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
    txn = txn_begin(proj, "adopt", ch_id)
    write(exist, dump_frontmatter(new_meta) + "\n\n## 正文\n" + text.strip() + "\n")
    tp = proj.p("chapters", ch_id + ".task.json")
    if not tp.is_file():
        write(tp, instantiate("chapter.task.json",
                              {"[ch_0001]": ch_id,
                               "[arc_01_1]": args.parent or "[arc_01_1]"}))
    mp = proj.p("chapters", ch_id + ".meta.json")
    if not mp.is_file():
        stub = {"summary_after": "", "continuity_delta": [],
                "time_advance": {"elapsed": "", "story_date": ""}, "thread_ops": [],
                "payoff_realized": [], "hooks_realized": {"open": False, "close": False},
                "cast_actual": [],
                "issues": ["adopted：外部文稿收编，writeback 待补录（protocol/adopt.md §3）"],
                "word_count": new_meta["word_count"]}
        write(mp, json.dumps(stub, ensure_ascii=False, indent=1))
    update_ngram_cache(proj, ch_id, text)
    update_rollup(proj)
    txn_end(proj, txn)
    git_autocommit(proj.root, "[adopt] %s ← %s" % (ch_id, src.name))
    print("已收编：%s（status=drafted, %d 字）" % (ch_id, new_meta["word_count"]))
    print("后续（protocol/adopt.md §3）：补 task.json 排批字段 → 补录 writeback"
          "（summary_after/continuity_delta/thread_ops）→ novel.py facts import %s → "
          "check --unit %s → 评审落盘（review add）后 set-status approved"
          % (ch_id, ch_id))
    return 0


# ---------------------------------------------------------------- review（P0-2）
def cmd_review(args):
    """评审回执 CLI 化：轻/深评结论落盘 reviews/（approved 闸门唯一认可的回执载体）。"""
    proj = Project(find_root(args))
    if args.review_cmd == "list":
        for r in proj.reviews():
            m = r["meta"]
            print("%-24s depth=%-5s verdict=%-8s rev_reviewed=%s date=%s"
                  % (r["path"].name, m.get("depth"), m.get("verdict"),
                     m.get("rev_reviewed"), m.get("date")))
        if not proj.reviews():
            print("（无评审单）")
        return 0
    # add
    ch_id = args.ch_id
    ch_num(ch_id)
    p = proj.p("chapters", ch_id + ".md")
    if not p.is_file():
        die("章不存在：%s" % ch_id, 1)
    cmeta, _ = parse_frontmatter(read(p))
    cur_rev = (cmeta or {}).get("rev") or 1
    rev = args.rev if args.rev is not None else cur_rev
    if rev != cur_rev:
        print("[warn] rev_reviewed=%d ≠ 章当前 rev=%d——该回执不会被 approved 闸门认可"
              "（仅存证历史评审）" % (rev, cur_rev))
    issues = args.issue or ["[全章] 无阻塞问题 → 通过"]
    meta = {"id": "review_%s_%s" % (ch_id, args.depth), "kind": "review",
            "chapter": ch_id, "depth": args.depth, "verdict": args.verdict,
            "rev_reviewed": rev, "date": datetime.date.today().isoformat()}
    body = "\n## 问题清单\n\n" + "\n".join("- %s" % i for i in issues) + "\n"
    if args.lesson:
        body += "\n## 教训\n\n- %s\n" % args.lesson
    out = proj.p("reviews", "%s.%s.md" % (ch_id, args.depth))
    write(out, dump_frontmatter(meta) + body)
    git_autocommit(proj.root, "[review] %s %s=%s rev%d"
                   % (ch_id, args.depth, args.verdict, rev))
    print("评审单已落盘：reviews/%s.%s.md（verdict=%s, rev_reviewed=%d）"
          % (ch_id, args.depth, args.verdict, rev))
    if args.verdict == "escalate":
        print("[提醒] escalate：按 pipeline §3 开 revise_design 任务（--evidence 必填）")
    elif args.verdict == "revise":
        print("[提醒] revise：问题清单进修订循环（pipeline §2）")
    return 0


# ---------------------------------------------------------------- facts（P0-4）
def cmd_facts(args):
    """facts 台账工具：import = adopt 补录的机械半边（自各章 meta.json 的
    continuity_delta 分配 fact_id 入账，同文同章去重，可重复执行）。"""
    proj = Project(find_root(args))
    if args.facts_cmd == "list":
        for x, fname in proj.all_facts():
            if args.entity and args.entity not in (x.get("entity_ids") or []):
                continue
            flag = ""
            if x.get("spoiler"):
                flag += "【spoiler】"
            if x.get("known_by"):
                flag += "【知情:%s】" % ",".join(x["known_by"])
            if x.get("superseded_by"):
                flag += "【已覆盖 %s】" % x["superseded_by"]
            print("%-10s ch%-4s %s%s（%s｜%s）"
                  % (x.get("id"), x.get("revealed_ch"), flag, x.get("fact"),
                     ",".join(x.get("entity_ids") or []), fname))
        return 0
    # import
    total = []
    for ch_id in args.ch_ids:
        ch_num(ch_id)
        wb = proj.chapter_meta_json(ch_id)
        if wb is None:
            die("缺 chapters/%s.meta.json（先按 protocol/adopt.md §3 补录 writeback）"
                % ch_id, 1)
        errs = []
        for i, d in enumerate(wb.get("continuity_delta", []) or []):
            for k in ("fact", "entity_ids", "spoiler"):
                if k not in d:
                    errs.append("continuity_delta[%d] 缺 %s" % (i, k))
            for ref in d.get("entity_ids", []):
                if not proj.resolve_entity(ref):
                    errs.append("continuity_delta[%d] 实体「%s」未登记"
                                "（先 entity new/补 aliases）" % (i, ref))
        if errs:
            die("%s 补录校验失败（零入账）：\n  %s" % (ch_id, "\n  ".join(errs)), 1)
        added = register_facts(proj, ch_id, wb)
        total += added
        print("%s：%s" % (ch_id, "登记 " + " ".join(added) if added
                          else "无新事实（已入账或 delta 为空）"))
    # 补录 writeback 后 rollup 一并刷新（adopt 时 summary_after 为空被跳过）
    update_rollup(proj)
    if total:
        git_autocommit(proj.root, "[facts] import %s" % " ".join(args.ch_ids))
    print("facts import 完成：新登记 %d 条；跑 check --project 复核" % len(total))
    return 0


# ---------------------------------------------------------------- knowledge（P4-K）
def locate_fact(proj, fact_id):
    """按 id 定位 fact：返回 (文件路径, 整文件数据, fact 记录)；找不到返回 (None,)*3。"""
    for f in proj.facts_files():
        try:
            data = json.loads(read(f))
        except ValueError:
            continue
        for x in data.get("facts", []):
            if x.get("id") == fact_id:
                return f, data, x
    return None, None, None


def cmd_knowledge(args):
    """P4-K 知识矩阵 CLI（fact × 角色 × 读者）：
    grant  = 授予角色知情（known_by 追加；获知场景写进正文/日志，本命令只记账）
    reveal = 读者揭示（spoiler 1→0，记 revealed_reader_ch——悬念资产销账）
    query  = 矩阵视图：--fact 单条全貌 / --entity 某角色知与不知 / 默认盘点读者未知欠账"""
    proj = Project(find_root(args))
    if args.knowledge_cmd == "grant":
        f, data, x = locate_fact(proj, args.fact_id)
        if not x:
            die("fact 不存在：%s（novel.py facts list 查现有 id）" % args.fact_id, 1)
        if x.get("superseded_by"):
            die("fact %s 已被覆盖（%s）——对新事实操作" % (args.fact_id, x["superseded_by"]), 1)
        ids = []
        for ref in args.to:
            eid = proj.resolve_entity(ref)
            if not eid:
                die("知情人「%s」未登记（先 entity new 或补 aliases）" % ref, 1)
            ids.append(eid)
        x["known_by"] = sorted(set(x.get("known_by") or []) | set(ids))
        write(f, json.dumps(data, ensure_ascii=False, indent=1))
        git_autocommit(proj.root, "[knowledge] grant %s → %s%s"
                       % (args.fact_id, ",".join(sorted(set(ids))),
                          "（%s 获知）" % args.ch if args.ch else ""))
        print("已授予知情：%s known_by=%s" % (args.fact_id, ",".join(x["known_by"])))
        print("[提醒] 获知须有正文/日志支撑（获知场景章号：%s）——账实一致由评审抽查"
              % (args.ch or "未记"))
        return 0
    if args.knowledge_cmd == "reveal":
        f, data, x = locate_fact(proj, args.fact_id)
        if not x:
            die("fact 不存在：%s" % args.fact_id, 1)
        if not x.get("spoiler"):
            die("fact %s 本就读者已知（spoiler=0），无需 reveal" % args.fact_id, 1)
        num = ch_num(args.ch)
        x["spoiler"] = 0
        x["revealed_reader_ch"] = num
        write(f, json.dumps(data, ensure_ascii=False, indent=1))
        git_autocommit(proj.root, "[knowledge] reveal %s @ %s" % (args.fact_id, args.ch))
        print("读者揭示已记账：%s spoiler=0（revealed_reader_ch=%d）；"
              "此后简报不再带【读者未知】约束" % (args.fact_id, num))
        return 0
    # query
    facts = [x for x, _ in proj.all_facts() if not x.get("superseded_by")]
    if args.fact_id:
        f, data, x = locate_fact(proj, args.fact_id)
        if not x:
            die("fact 不存在：%s" % args.fact_id, 1)
        print(json.dumps(x, ensure_ascii=False, indent=1))
        known = x.get("known_by")
        print("读者：%s" % ("未知（spoiler=1，简报带潜台词约束）" if x.get("spoiler")
                            else "已知（ch%s 揭示）" % x.get("revealed_reader_ch",
                                                            x.get("revealed_ch"))))
        print("角色：%s" % ("知情仅 " + ",".join(known) if known
                            else "未建模（known_by 空 = 不设知情约束）"))
        return 0
    if args.entity:
        eid = proj.resolve_entity(args.entity)
        if not eid:
            die("实体未登记：%s" % args.entity, 1)
        about = [x for x in facts if eid in (x.get("entity_ids") or [])]
        knows = [x for x in facts if eid in (x.get("known_by") or [])]
        blind = [x for x in facts if x.get("known_by") and eid not in x["known_by"]]
        print("== knowledge query %s ==" % eid)
        print("关于此实体的事实 %d 条：" % len(about))
        for x in about:
            print("  %-10s %s" % (x["id"], x.get("fact")))
        print("知情 %d 条：" % len(knows))
        for x in knows:
            print("  %-10s %s" % (x["id"], x.get("fact")))
        print("不知情 %d 条（known_by 有限定且不含该实体——正文不得由其说破）：" % len(blind))
        for x in blind:
            print("  %-10s %s（知情仅 %s）" % (x["id"], x.get("fact"),
                                               ",".join(x["known_by"])))
        return 0
    # 默认：读者未知欠账盘点（悬念资产台账）
    spoilers = sorted([x for x in facts if x.get("spoiler")],
                      key=lambda x: x.get("revealed_ch") or 0)
    modeled = [x for x in facts if x.get("known_by")]
    print("== knowledge query（矩阵总览）==")
    print("facts 有效 %d 条；known_by 已建模 %d 条；读者未知（spoiler）%d 条"
          % (len(facts), len(modeled), len(spoilers)))
    for x in spoilers:
        print("  %-10s ch%-4s %s%s" % (x["id"], x.get("revealed_ch"), x.get("fact"),
                                       "（知情仅 %s）" % ",".join(x["known_by"])
                                       if x.get("known_by") else ""))
    if spoilers:
        print("（悬念欠账：埋下未揭示的读者钩子——弧末/卷末逐条决定 继续吊/knowledge "
              "reveal 销账/走 retcon 废止）")
    return 0


# ---------------------------------------------------------------- extract（P2-1）
def cmd_extract(args):
    """抽取器独立入口：正文反向解析 + 与 writeback 对账（双记账机器半边）。"""
    proj = Project(find_root(args))
    ch_id = args.ch_id
    ch_num(ch_id)
    if args.candidate:
        _, body = parse_frontmatter(read(args.candidate))
    else:
        p = proj.p("chapters", ch_id + ".md")
        if not p.is_file():
            die("章不存在且未给 --candidate：%s" % ch_id, 1)
        _, body = parse_frontmatter(read(p))
    text = body.split("## 正文", 1)[-1] if "## 正文" in body else body
    wb = json.loads(read(args.writeback)) if args.writeback \
        else proj.chapter_meta_json(ch_id)
    rep = Report()
    obs = extract_reconcile(proj, ch_id, text, wb or {}, rep)
    print("== 抽取器观察（%s）==" % ch_id)
    for eid, n in sorted(obs["mentions"].items()):
        print("- 出场实测：%s ×%d" % (eid, n))
    for q in obs["name_candidates"]:
        print("- 新专名候选：「%s」" % q)
    if not obs["mentions"] and not obs["name_candidates"]:
        print("- （无已登记别名命中，无新专名候选）")
    return rep.render("extract %s（对账）" % ch_id)


# ---------------------------------------------------------------- rollup（P4-R）
def cmd_rollup(args):
    """手动重算章→弧→卷摘要卷积。commit/adopt/facts import 已自动重算；本命令用于
    批量手改 meta.json（如 adopt 补录 summary_after、修订摘要链）后的显式对账。"""
    proj = Project(find_root(args))
    rollup = update_rollup(proj)
    n_ch = sum(len(a["lines"]) for a in rollup["arcs"].values())
    git_autocommit(proj.root, "[rollup] 手动重算（%d 章 → %d 弧 → %d 卷）"
                   % (n_ch, len(rollup["arcs"]), len(rollup["volumes"])))
    print("rollup 已重算：%d 章 → %d 弧 → %d 卷 → state/rollup.json"
          % (n_ch, len(rollup["arcs"]), len(rollup["volumes"])))
    for aid in sorted(rollup["arcs"]):
        a = rollup["arcs"][aid]
        print("  %s（%s..%s）%d 行" % (aid, a["span"][0], a["span"][1], len(a["lines"])))
    print("（简报 §2 远程记忆层引用此文件；重编简报后新卷积才进包）")
    return 0


# ---------------------------------------------------------------- gate（P3-1）
def gate_write(proj, ch_id, rep):
    """spawn 写手前置闸门：任务卡排批完整 + 弧 committed + 简报新鲜 + 基线干净。
    每条 FAIL 附「下一步」修复命令（P4-G gate UX：闸门即剧本）。"""
    task = proj.chapter_task(ch_id)
    tp = proj.p("chapters", ch_id + ".task.json")
    if not task:
        rep.add("FAIL", "缺任务卡 chapters/%s.task.json" % ch_id,
                fix="novel.py tree add chapter %s --parent <arc_NN_n>，再按 "
                    "pipeline §1 步骤 0 排批补全 task.json" % ch_id)
        return
    ph = []
    for k in ("goal", "beats", "cast"):
        v = task.get(k)
        if not v or (isinstance(v, str) and v.startswith("[")) \
                or (isinstance(v, list) and all(str(x).startswith("[") for x in v)):
            ph.append(k)
    if ph:
        rep.add("FAIL", "任务卡未排批（字段缺失/仍为占位）", ph,
                fix="编排者补全 chapters/%s.task.json 的 %s（从弧计划「章分配草案」"
                    "取料，pipeline §1 步骤 0；quality 档可委派架构师 T0）"
                    % (ch_id, "/".join(ph)))
    else:
        rep.add("PASS", "任务卡排批字段齐全（goal/beats/cast）")
    route = proj.config.get("route", "web")
    hook = task.get("hook") or {}
    if route == "web" and (not hook.get("close") or str(hook.get("close")).startswith("[")):
        rep.add("FAIL", "route=web 章尾钩未排（task.json hook.close 必填）",
                fix="补 chapters/%s.task.json 的 hook.close（一句话钩子，"
                    "pipeline §1 步骤 0）后重跑 gate write" % ch_id)
    if route == "traditional" and not task.get("turn"):
        rep.add("WARN", "traditional 未填 turn（价值翻转一句话，route-traditional §2）")
    arc = task.get("arc")
    arc_p = proj.node_path(arc) if arc and not str(arc).startswith("[") else None
    if not arc_p or not arc_p.is_file():
        rep.add("FAIL", "所属弧不存在或未填：%s" % arc,
                fix="novel.py tree add arc <arc_NN_n> → 弧简流程定稿（court.md §1 弧行）"
                    "→ task.json 填 arc")
    else:
        ameta, _ = parse_frontmatter(read(arc_p))
        if (ameta or {}).get("status") != "committed":
            rep.add("FAIL", "弧 %s 状态 %s ≠ committed"
                    % (arc, (ameta or {}).get("status")),
                    fix="novel.py task add design %s → 弧简流程（court.md §1 弧行）→ "
                        "commit <t> --file <弧定稿>" % arc)
        else:
            rep.add("PASS", "弧 %s 已 committed" % arc)
    bp = proj.p("briefs", ch_id + ".brief.md")
    if not bp.is_file():
        rep.add("FAIL", "简报未编译（写手唯一世界）",
                fix="novel.py brief %s（编译后资料员审包，pipeline §1 步骤 1–3）" % ch_id)
    elif tp.is_file() and bp.stat().st_mtime < tp.stat().st_mtime:
        rep.add("FAIL", "简报早于任务卡（排批后未重编译）",
                fix="novel.py brief %s（重编译，brief_rev+1）" % ch_id)
    else:
        rep.add("PASS", "简报存在且不早于任务卡")
    dirty = git_out(proj.root, "status", "--porcelain")
    if dirty:
        rep.add("FAIL", "工作区不干净（spawn 前基线必须干净，pipeline §5）",
                dirty.splitlines()[:8],
                fix="附笔请在 commit 前一刻写；散落改动先核对再清：git status --porcelain"
                    " → git checkout -- . && git clean -fd（worker 中间稿移项目外）")
    else:
        rep.add("PASS", "git 基线干净")
    cur = proj.cursor()
    last_deep = proj.last_deep_review_ch()
    deep_every = proj.config.get("critic", {}).get("deep_every", 5)
    if cur["last_drafted"] > 0 and cur["last_drafted"] - last_deep >= deep_every:
        rep.add("WARN", "深评逾期（last_deep=%d, last_drafted=%d）"
                % (last_deep, cur["last_drafted"]),
                fix="novel.py task add review_deep ch_%04d（pipeline §4）"
                    % cur["last_drafted"])


def gate_approve(proj, ch_id, rep):
    """approved 前置闸门：章已 drafted + 落盘回执（rev 匹配）+ 机检绿。
    每条 FAIL 附「下一步」修复命令（P4-G）。"""
    p = proj.p("chapters", ch_id + ".md")
    if not p.is_file():
        rep.add("FAIL", "章不存在：%s" % ch_id,
                fix="先走写作链落盘：novel.py commit <t> --chapter … --writeback …"
                    "（pipeline §1 步骤 8）")
        return
    meta, _ = parse_frontmatter(read(p))
    st = (meta or {}).get("status")
    if st != "drafted":
        fixes = {"planned": "章尚未成稿：走 pipeline §1 写作链到 commit",
                 "approved": "已 approved——无需重复；下一步 gate publish",
                 "published": "已 published（不可变）；修错走 serial-ops §3 retcon",
                 "stale": "上游设计已变更：按队列重排 revise 后再评（court.md §4）"}
        rep.add("FAIL", "章状态 %s ≠ drafted（迁移表 formats §3）" % st,
                fix=fixes.get(st, "核对 formats §3 状态机"))
    receipt = approval_receipt(proj, ch_id)
    if receipt:
        rep.add("PASS", "评审回执有效：%s" % receipt)
    else:
        rep.add("FAIL", "缺有效评审回执（verdict=pass 且 rev_reviewed=章当前 rev）",
                fix="先真评审（轻评按 roles/critic-light.md），后落盘回执："
                    "novel.py review add %s --depth light --verdict pass --note <要点>"
                    "（章 revise 过则须对新 rev 复评）" % ch_id)
    n_before = sum(1 for l, _, _, _ in rep.items if l == "FAIL")
    check_unit(proj, ch_id, rep=rep)
    if sum(1 for l, _, _, _ in rep.items if l == "FAIL") > n_before:
        rep.add("FAIL", "机检不绿（上列 FAIL 来自 check --unit）",
                fix="novel.py check --unit %s 复现问题 → 并入修订循环（pipeline §2："
                    "task add revise %s → 写手修订 → commit）" % (ch_id, ch_id))


def cmd_gate_next(proj):
    """机器版编排剧本：按优先级输出下一步该干什么（把「先修账、再评审、再写作」
    的调度纪律从提示词搬进机器）。"""
    recs = []
    prep = Report()
    check_project(proj, prep)
    fails = [n for l, n, _, _ in prep.items if l == "FAIL"]
    if fails:
        recs.append("【修账】check --project 有 FAIL，先修复：%s" % "；".join(fails[:3]))
    cur = proj.cursor()
    last_deep = proj.last_deep_review_ch()
    deep_every = proj.config.get("critic", {}).get("deep_every", 5)
    if cur["last_drafted"] > 0 and cur["last_drafted"] - last_deep >= deep_every:
        recs.append("【深评】逾期（last_deep=%d, last_drafted=%d, deep_every=%d）："
                    "task add review_deep ch_%04d"
                    % (last_deep, cur["last_drafted"], deep_every, cur["last_drafted"]))
    thr = proj.config.get("reconcile_every", 10)
    due = [e for e, v in proj.entities().items()
           if (v["meta"].get("last_event_ch", 0) or 0)
           - (v["meta"].get("last_reconcile_ch", 0) or 0) >= thr]
    if due:
        recs.append("【对账】实体到期 %s：serial-ops §5 对账轮（entity update）"
                    % " ".join(due[:5]))
    # P6-S：spoiler 欠账消费——读者未知事实挂账超龄，顶进调度剧本（workflow §4）
    debt_thr = proj.config.get("spoiler_debt_chapters", 15)
    debts = sorted([x for x, _ in proj.all_facts()
                    if x.get("spoiler") and not x.get("superseded_by")
                    and cur["last_drafted"] - (x.get("revealed_ch") or 0) >= debt_thr],
                   key=lambda x: x.get("revealed_ch") or 0)
    if debts:
        recs.append("【欠账】读者未知 fact %d 条挂账 ≥%d 章（最老 %s，ch%s 埋下）："
                    "knowledge query 盘点后逐条决定 继续吊/reveal 销账/retcon 废止"
                    "（workflow §4）"
                    % (len(debts), debt_thr, debts[0]["id"],
                       debts[0].get("revealed_ch")))
    if proj.config.get("route", "web") == "web" and cur["last_published"] > 0 \
            and proj.buffer_ready() == 0:
        recs.append("【补稿】buffer=0：停发/降频，只跑 write 批（serial-ops §1）")
    q = load_queue_promoted(proj)
    tid = next_task_id(q)
    if tid:
        t = proj.task(tid)
        recs.append("【队列】执行队首 %s：%s(%s) → task start %s"
                    % (tid, t["type"], t["target"], tid))
    else:
        nxt = cur["last_drafted"] + 1
        nid = "ch_%04d" % nxt
        if proj.p("chapters", nid + ".task.json").is_file():
            recs.append("【排批】%s 已有任务卡：task add write %s" % (nid, nid))
        elif any(n["meta"].get("kind") == "arc" and n["meta"].get("status") == "committed"
                 for n in proj.tree_nodes()):
            recs.append("【排批】队列空：从弧计划取料排批 %s（pipeline §1 步骤 0）" % nid)
        else:
            recs.append("【设计】无 committed 弧：开书庭/卷庭/弧规划（court.md §1）")
    print("== gate next（机器版编排剧本）==")
    for i, r in enumerate(recs, 1):
        print("%d. %s" % (i, r))
    print("（依序处置；【修账】未清不得进入写作环）")
    print_stage_hint(proj)
    return 0


def cmd_gate(args):
    proj = Project(find_root(args))
    if args.gate_cmd == "next":
        return cmd_gate_next(proj)
    rep = Report()
    if args.gate_cmd == "write":
        gate_write(proj, args.ch_id, rep)
        return rep.render("gate write %s" % args.ch_id)
    if args.gate_cmd == "approve":
        gate_approve(proj, args.ch_id, rep)
        return rep.render("gate approve %s" % args.ch_id)
    if args.gate_cmd == "publish":
        frm = ch_num(args.ch_from)
        to = ch_num(args.ch_to) if args.ch_to else frm
        probs = publish_problems(proj, frm, to)
        for pr, fix in probs:
            rep.add("FAIL", pr, fix=fix)
        if not probs:
            rep.add("PASS", "publish 前置谓词全过（ch_%04d..ch_%04d 可发布）" % (frm, to))
        return rep.render("gate publish")
    if args.gate_cmd == "checkpoint":
        probs = checkpoint_problems(proj, args.vol_id)
        for pr, fix in probs:
            rep.add("FAIL", pr, fix=fix)
        if not probs:
            rep.add("PASS", "checkpoint 前置谓词全过（%s 可结账）" % args.vol_id)
        return rep.render("gate checkpoint %s" % args.vol_id)
    return 2


# ---------------------------------------------------------------- court（P3-2）
def cmd_court(args):
    """庭审工作区 CLI 化：open 建场次目录+R0 骨架；status 盘点回合产物；
    close 校验裁决落盘后清理中间态（court.md §3 约定的机械半边）。"""
    proj = Project(find_root(args))
    base = proj.p("state", "court")
    if args.court_cmd == "open":
        d = base / args.session
        d.mkdir(parents=True, exist_ok=True)
        stub = d / "r0_brief.md"
        if not stub.exists():
            write(stub, "# R0 设计简报 — %s\n\n- 目标节点: %s\n- 议题与决策清单:\n"
                        "  - [ ] （本场要定什么，逐条）\n- 上游约束: （已 committed 节点/前场暂存稿）\n"
                        "- 兄弟契约: （卷庭附上卷 exports+卷报告）\n- 市场输入: （用户诉求/平台定位）\n"
                        "- 判据附件路径清单: （court.md §2 投递列）\n"
                        "- 相关否决案: （court/dec_* 的「## 否决案」节全文）\n\n"
                        "（装配指引 court.md §3 R0；纪律：transcripts 永不入简报；"
                        "R1–R4 产物按 r1_*.md/r2_*.md… 前缀存本目录）\n"
                  % (args.session, args.node or "（--node 指定）"))
            print("场次已开：state/court/%s/（r0_brief.md 骨架就位）" % args.session)
        else:
            print("场次已存在：state/court/%s/（续场，从现有回合产物恢复）" % args.session)
        for f in sorted(d.iterdir()):
            print("  - %s" % f.name)
        return 0
    if args.court_cmd == "status":
        if not base.is_dir() or not any(base.iterdir()):
            print("（无进行中场次）")
        for d in sorted(base.iterdir()) if base.is_dir() else []:
            if not d.is_dir():
                continue
            files = [f.name for f in sorted(d.iterdir())]
            rounds = {r: len([f for f in files if f.startswith(r)])
                      for r in ("r0", "r1", "r2", "r3", "r4")}
            print("%s：%s ｜ 文件 %d" % (d.name,
                                         " ".join("%s×%d" % kv for kv in rounds.items()
                                                  if kv[1]), len(files)))
        print("court/ 裁决记录 %d 份；transcripts %d 份"
              % (len(proj.decisions()), len(list(proj.p("court", "transcripts").glob("*"))
                                            if proj.p("court", "transcripts").is_dir()
                                            else [])))
        return 0
    # close
    d = base / args.session
    if not d.is_dir():
        die("场次不存在：state/court/%s" % args.session, 1)
    missing = [dec for dec in args.dec
               if not list(proj.p("court").glob(dec + "*.md"))]
    if missing:
        die("裁决未落盘，不得清场：court/%s*.md 缺失（先随定稿 commit 附笔入库）"
            % " ".join(missing), 1)
    shutil.rmtree(d)
    git_autocommit(proj.root, "[court] close %s（dec=%s）"
                   % (args.session, " ".join(args.dec)))
    print("场次已清：state/court/%s（裁决 %s 已确认落盘）"
          % (args.session, " ".join(args.dec)))
    print("[提醒] transcript 归档 court/transcripts/（若尚未）；复盘走 dec + git log")
    return 0


# ---------------------------------------------------------------- stage（P6-S）
def stage_row(sid):
    for row in STAGES:
        if row[0] == sid:
            return row
    return None


def infer_stage(proj):
    """启发式阶段推断（仅导航，不是闸门）：court 工作区 > 设计缺口 > 队首任务类型。
    返回 (stage_id, 依据一句话)。歧义以 protocol/workflow.md §1 人判为准。"""
    base = proj.p("state", "court")
    if base.is_dir():
        sessions = [d.name for d in sorted(base.iterdir()) if d.is_dir()]
        for sid in ("S4", "S3", "S2", "S1"):          # 书庭进行中：最深场次优先
            if sid in sessions:
                return sid.lower(), "庭审工作区有进行中场次 %s（court status 盘点回合）" % sid
        for s in sessions:
            if s.startswith("vol"):
                return "vol", "庭审工作区有进行中卷庭 %s" % s
            if s.startswith("arc"):
                return "arc", "庭审工作区有进行中弧场次 %s" % s
    nodes = proj.tree_nodes()
    status_by_id = {n["meta"].get("id"): n["meta"].get("status") for n in nodes}
    kinds_committed = {n["meta"].get("kind") for n in nodes
                       if n["meta"].get("status") == "committed"}
    if status_by_id.get("book") != "committed":
        return "s1", "book 未 committed（书庭未完成；具体场次以 court status 为准）"
    if "volume" not in kinds_committed:
        return "vol", "无 committed 卷蓝图"
    if "arc" not in kinds_committed:
        return "arc", "无 committed 弧计划"
    q = load_queue_promoted(proj)
    tid = next_task_id(q)
    if tid:
        t = proj.task(tid)
        tgt = str(t.get("target") or "")
        why = "队首 %s：%s(%s)" % (tid, t["type"], tgt)
        if t["type"] in ("design", "revise_design"):
            if tgt.startswith("vol"):
                return "vol", why
            if tgt.startswith("arc"):
                return "arc", why
            return "s1", why + "（book/world/style 级设计 → 书庭）"
        type_stage = {"write": "write", "revise": "write", "review_deep": "review",
                      "reconcile": "review", "revise_rubric": "review",
                      "publish": "ops", "retcon": "ops", "checkpoint": "ops"}
        if t["type"] in type_stage:
            return type_stage[t["type"]], why
    return "write", "设计层齐备且队列无特殊任务 → 产线（队列空则先排批）"


def print_stage_hint(proj):
    sid, why = infer_stage(proj)
    _, name, _, rel = stage_row(sid)
    print("当前阶段推断: %s（%s）— %s" % (sid, name, why))
    print("  配套知识包: %s（先读包再动工；启发式导航，歧义以 workflow §1 为准）"
          % (SKILL_ROOT / rel))
    if proj.config.get("route", "web") == "traditional" and sid != "diag":
        print("  叠加差分: trad → %s" % (SKILL_ROOT / "protocol/stages/trad-overlay.md"))


def cmd_stage(args):
    """阶段导航（只读）：list=总表；show <id>=打印配套知识包全文；current=推断当前阶段。"""
    if args.stage_cmd == "list":
        print("== stage list（阶段总表；SSOT=protocol/knowledge-orchestration.md）==")
        for sid, name, gist, rel in STAGES:
            print("%-7s %-10s %s" % (sid, name, gist))
            print("        包: %s" % (SKILL_ROOT / rel))
        print("（进环节先读包；`stage current` 按项目状态推断所处阶段）")
        return 0
    if args.stage_cmd == "show":
        row = stage_row(args.stage_id)
        if not row:
            die("未知阶段 id：%s（可选：%s）"
                % (args.stage_id, " ".join(r[0] for r in STAGES)))
        p = SKILL_ROOT / row[3]
        if not p.is_file():
            die("阶段包文件缺失：%s（skill 安装不完整）" % p, 1)
        print("# 包路径: %s\n" % p)
        print(read(p))
        return 0
    # current
    proj = Project(find_root(args))
    print_stage_hint(proj)
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

    p = sub.add_parser("ledger", help="台账视图：payoff|promise|timeline|power")
    p.add_argument("which", choices=["payoff", "promise", "timeline", "power"])

    p = sub.add_parser("review", help="评审回执落盘：add/list（approved 闸门唯一回执载体）")
    ts = p.add_subparsers(dest="review_cmd", required=True)
    q = ts.add_parser("add")
    q.add_argument("ch_id")
    q.add_argument("--depth", required=True, choices=list(REVIEW_DEPTHS))
    q.add_argument("--verdict", required=True, choices=list(REVIEW_VERDICTS))
    q.add_argument("--rev", type=int, help="被评审的章 rev（默认=章当前 rev）")
    q.add_argument("--issue", action="append",
                   help="问题清单行（可多值；缺省写「无阻塞问题 → 通过」）")
    q.add_argument("--lesson", help="教训一行（可选，编排者摘入 lessons）")
    ts.add_parser("list")

    p = sub.add_parser("knowledge", help="知识矩阵（fact×角色×读者）：grant/reveal/query")
    ts = p.add_subparsers(dest="knowledge_cmd", required=True)
    q = ts.add_parser("grant", help="授予角色知情（known_by 追加）")
    q.add_argument("fact_id")
    q.add_argument("--to", action="append", required=True,
                   help="知情实体（可多次；须已登记）")
    q.add_argument("--ch", help="获知场景章号（记入 git 消息，便于审计）")
    q = ts.add_parser("reveal", help="读者揭示：spoiler 1→0（悬念销账）")
    q.add_argument("fact_id")
    q.add_argument("--ch", required=True, help="揭示章号（记 revealed_reader_ch）")
    q = ts.add_parser("query", help="矩阵视图：--fact/--entity/默认盘点读者未知欠账")
    q.add_argument("--fact", dest="fact_id")
    q.add_argument("--entity")

    p = sub.add_parser("rollup", help="手动重算摘要卷积（批量改 meta.json/adopt 补录后）")

    p = sub.add_parser("facts", help="facts 台账：import（adopt 补录机械半边）/list")
    ts = p.add_subparsers(dest="facts_cmd", required=True)
    q = ts.add_parser("import")
    q.add_argument("ch_ids", nargs="+", metavar="CH_ID")
    q = ts.add_parser("list")
    q.add_argument("--entity")

    p = sub.add_parser("extract", help="抽取器：正文反向解析+writeback 对账（双记账机器半边）")
    p.add_argument("ch_id")
    p.add_argument("--candidate", help="未落盘候选章文件")
    p.add_argument("--writeback", help="未落盘 writeback JSON")

    p = sub.add_parser("gate", help="闸门家族：next/write/approve/publish/checkpoint（只判不写）")
    gs = p.add_subparsers(dest="gate_cmd", required=True)
    gs.add_parser("next")
    q = gs.add_parser("write")
    q.add_argument("ch_id")
    q = gs.add_parser("approve")
    q.add_argument("ch_id")
    q = gs.add_parser("publish")
    q.add_argument("ch_from")
    q.add_argument("ch_to", nargs="?")
    q = gs.add_parser("checkpoint")
    q.add_argument("vol_id")

    p = sub.add_parser("stage", help="阶段导航：list/show <id>/current（阶段×配套知识包，只读）")
    ss = p.add_subparsers(dest="stage_cmd", required=True)
    ss.add_parser("list", help="阶段总表（id+定位+包路径）")
    q = ss.add_parser("show", help="打印某阶段配套知识包全文")
    q.add_argument("stage_id")
    ss.add_parser("current", help="按项目状态推断当前阶段（需在项目内或 --root）")

    p = sub.add_parser("court", help="庭审工作区：open/status/close（state/court/ 机械管理）")
    cs = p.add_subparsers(dest="court_cmd", required=True)
    q = cs.add_parser("open")
    q.add_argument("session", help="场次代号（S1..S4/vol_NN/arc_NN_n/adhoc_xxx）")
    q.add_argument("--node", help="目标节点 id")
    cs.add_parser("status")
    q = cs.add_parser("close")
    q.add_argument("session")
    q.add_argument("--dec", action="append", required=True,
                   help="本场裁决 id（court/ 中须真实存在；可多值）")

    args = ap.parse_args(argv)
    if args.cmd == "check" and not (args.unit or args.window or args.project or args.leak):
        ap.error("check 需 --unit <ch>|--window|--project|--leak <候选> 之一")

    dispatch = {
        "init": cmd_init, "status": cmd_status, "tree": cmd_tree, "task": cmd_task,
        "entity": cmd_entity, "thread": cmd_thread, "brief": cmd_brief,
        "check": cmd_check, "commit": cmd_commit, "publish": cmd_publish,
        "ledger": cmd_ledger, "retcon": cmd_retcon, "report": cmd_report,
        "checkpoint": cmd_checkpoint, "adopt": cmd_adopt, "review": cmd_review,
        "facts": cmd_facts, "extract": cmd_extract, "gate": cmd_gate,
        "court": cmd_court, "knowledge": cmd_knowledge, "rollup": cmd_rollup,
        "stage": cmd_stage,
        "fsck": lambda a: check_project(Project(find_root(a))).render("fsck"),
    }
    return dispatch[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
