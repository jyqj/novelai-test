# -*- coding: utf-8 -*-
"""common — 共享底座：常量、宽松 frontmatter、节解析、原子写、git、
线索状态机、文本指纹（ngram）、故事日历解析、Report 报告器、模板实例化。"""
import datetime
import json
import re
import subprocess
import sys
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent.parent
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
    "人物声音与行为是否可辨认（按作品审美，不以统一识别率代替判断）",
    "智商漂移两问（rubrics/prose-disease.md §六）",
    "关键场面是否完成其戏剧与情感任务（允许有意概述、留白与静态描写）",
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
    from . import transactions
    data = text.encode("utf-8")
    if transactions.ACTIVE is not None:
        transactions.ACTIVE.write(path, data)
    else:
        transactions.atomic_bytes(path, data)


def remove(path):
    from . import transactions
    if transactions.ACTIVE is not None:
        transactions.ACTIVE.write(path, None)
    else:
        Path(path).unlink(missing_ok=True)


def append(path, text):
    path = Path(path)
    write(path, (read(path) if path.is_file() else "") + text)


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


def git_autocommit(root, msg, paths=None):
    from . import transactions
    if transactions.ACTIVE is not None:
        transactions.ACTIVE.message = msg
        return True
    if not (Path(root) / ".git").exists():
        return False
    # Never absorb unrelated staged files. Caller supplies the precise write set.
    if paths is None:
        print("[warn] 未提供写入清单，跳过自动 Git 提交；请自行检查 git diff")
        return False
    paths = [p for p in paths if not str(p).startswith("state/txn/")]
    if not paths:
        return True
    # Identity is not invented, and a failed commit must not leave staged changes.
    if not git_out(root, "var", "GIT_AUTHOR_IDENT"):
        print("[warn] 未配置 Git 身份；文件已安全写入，未暂存。请配置后自行提交")
        return False
    if git_out(root, "diff", "--cached", "--name-only"):
        print("[warn] 存在作者已暂存改动；跳过自动提交，未改索引")
        return False
    if not git(root, "add", "--", *paths):
        return False
    ok = git(root, "commit", "-m", msg, "-q", "--only", "--", *paths)
    if not ok:
        git(root, "reset", "-q", "--", *paths)
        print("[warn] Git 提交失败；文件已安全写入，已撤回本次暂存")
    return ok


def instantiate(template_name, replacements):
    text = read(TEMPLATES / template_name)
    for k, v in replacements.items():
        text = text.replace(k, v)
    return text


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


# ---------------------------------------------------------------- 文本指纹
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
