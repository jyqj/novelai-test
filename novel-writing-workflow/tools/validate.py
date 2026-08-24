#!/usr/bin/env python3
"""novel-writing-workflow 校验器（python3 stdlib only）。

用法:
  python3 tools/validate.py --skill   <skill_dir>    # 校验 skill 本身（锚点/对账/引用/废弃名/枚举/域计数）
  python3 tools/validate.py --project <project_dir>  # 校验项目实例（信封/枚举/洋葱/脊骨/manifest/id/复合键/记忆与治理字段）
  python3 tools/validate.py --unit <ms.md> --style <style_card.md>  # 单章文本质量机检（taboo/句首/4-gram/字数/末段）
退出码: 0 = 无 FAIL（仅 WARN 也为 0）；1 = 存在 FAIL。frontmatter 为宽松行解析，非完整 YAML。
"""
import argparse, re, sys
from collections import Counter, defaultdict
from pathlib import Path

K_ID_RE = re.compile(r"\bK-([A-Z]+)-(\d{3})\b")
ANCHOR_RE = re.compile(r"<!--\s*(K-[A-Z]+-\d{3})\s*-->")
REG_RE = re.compile(r"^#{1,6}\s*(K-[A-Z]+-\d{3})\b")
RANGE_RE = re.compile(r"\bK-([A-Z]+)-(\d{3})\s*[~–—-]\s*(\d{3})\b")
CONT_RE = re.compile(r"(?:[/+]\d{3})+")  # 紧跟 K-ID 的连写，如 K-X-018/019、011+020

STATUS_SET = ["draft", "review", "canon", "locked", "stale", "archived"]
ONION_KEYS = ["surface", "behavior", "emotion", "belief", "wound"]
THREAD_OPS = ["plant", "advance", "payoff", "tangle"]
ROUTE_SET = ["traditional", "web"]
UNIT_TYPES = ["dialogue", "description", "action", "interior", "exposition"]  # content_blocks/unit_type 五值闭集（D5）
ANCHOR_SET = {"hook", "shock1", "growth1", "midpoint", "growth2",
              "shock2", "growth3", "growth4", "climax", "resolution"}
ASSET_TYPES = {"Status", "Canon", "Manifest", "Decision", "Blueprint", "PlotSpine",
               "SequenceMap", "SceneBeat", "ChapterPlan", "Character", "WorldRule",
               "Thread", "ManuscriptUnit", "Recap"}
ENVELOPE_KEYS = ["id", "type", "rev", "status", "updated_at"]
REQUIRED_ANCHOR_NODES = {0, 6, 8, 12, 16, 18, 19, 22, 23}
APPROVED_BY_SET = {"user", "agent_auto"}
# manifest_root 内 Decision entry 的「open」判定（对齐 asset-types §2.3 可判定定义）：
# open/active := status ∈ {draft, review, canon}（字面 open 兼容未来枚举）；
# locked 长效裁决属例外——entry 带 tags 含 long_term 者留 root 免计，否则与 archived 同视为可迁（D3）
DECISION_OPEN_STATUS = {"open", "draft", "review", "canon"}
DECISION_ROOT_MAX = 20
WORD_BAND = (1700, 5175)     # 2000–4500 ±15%（去空白字符数）
NGRAM_WARN_RATE = 0.02       # 字级 4-gram 重复率阈值
# 末段总结化句式黑名单（内置；命中 → WARN，对接 K-WRITE-020 章尾钩纪律 / AI 正文病防治）
END_SUMMARY_BLACKLIST = ["这一夜", "注定", "谁也没想到", "殊不知", "而这一切", "命运的齿轮",
                         "才刚刚开始", "他不知道的是", "她不知道的是", "没有人注意到",
                         "多年以后", "悄然拉开"]
# 废弃名豁免：行内出现下列关键字视为「废弃/别名/映射」文档语境，非实际使用
EXEMPT_KW = re.compile(r"废弃|别名|旧称|归一|已删|漂移|映射表|映射到|禁止|勿用")
MAX_DETAIL = 20
PIPE_SEP = r"\s*\\?\|\s*"

class Report:
    def __init__(self, quiet):
        self.quiet = quiet
        self.counts = {"PASS": 0, "FAIL": 0, "WARN": 0, "SKIP": 0}

    def add(self, name, ok, details=None, note="", warn=False):
        details = details or []
        if ok is None:
            status = "SKIP"
        elif ok and not details:
            status = "PASS"
        else:
            status = "WARN" if warn else "FAIL"
        self.counts[status] += 1
        if status in ("FAIL", "WARN") or not self.quiet:
            print("[%s] %s%s" % (status, name, " — " + note if note else ""))
        if status in ("FAIL", "WARN"):
            for d in details[:MAX_DETAIL]:
                print("       " + d)
            if len(details) > MAX_DETAIL:
                print("       ... 另 %d 条" % (len(details) - MAX_DETAIL))

    def finish(self):
        code = 1 if self.counts["FAIL"] else 0
        print("SUMMARY: %d PASS / %d FAIL / %d WARN / %d SKIP -> exit %d"
              % (self.counts["PASS"], self.counts["FAIL"], self.counts["WARN"],
                 self.counts["SKIP"], code))
        return code

def read_lines(path):
    try:
        return path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []

def iter_files(root, rels, suffix=".md"):
    """按相对路径列表（目录或文件）产出 (相对名, Path)。"""
    for rel in rels:
        p = root / rel
        if p.is_file():
            yield rel, p
        elif p.is_dir():
            for f in sorted(p.rglob("*" + suffix)):
                yield str(f.relative_to(root)), f

def clean_value(raw):
    """去行内注释与引号的宽松取值。"""
    raw = raw.strip()
    if raw[:1] in "\"'":
        m = re.match(r"(['\"])(.*?)\1", raw)
        if m:
            return m.group(2).strip()
    if raw.startswith("#"):  # 纯注释 = 空值（如 `approved_by:  # 必填…`）
        return ""
    return re.split(r"\s+#", raw, 1)[0].strip()

def parse_frontmatter(lines):
    """宽松 frontmatter：文件首个 --- 块内的顶层 key。返回 {key: (value, lineno)} 或 None。"""
    if not lines or lines[0].strip() != "---":
        return None
    fm = {}
    for i, ln in enumerate(lines[1:], start=2):
        if ln.strip() in ("---", "..."):
            return fm
        m = re.match(r"^([A-Za-z_][\w]*)\s*:\s*(.*)$", ln)
        if m and m.group(1) not in fm:
            fm[m.group(1)] = (clean_value(m.group(2)), i)
    return fm

def parse_topkeys(lines):
    """纯 yaml 文件：列 0 顶层 key（跳过可选 --- 包裹）。"""
    fm = {}
    for i, ln in enumerate(lines, start=1):
        if ln.strip() in ("---", "...") or not ln.strip() or ln.lstrip().startswith("#"):
            continue
        m = re.match(r"^([A-Za-z_][\w]*)\s*:\s*(.*)$", ln)
        if m and m.group(1) not in fm:
            fm[m.group(1)] = (clean_value(m.group(2)), i)
    return fm

def fm_region(lines):
    """frontmatter 区行下标范围 [lo, hi)；无 frontmatter 时宽容地返回全文。"""
    if not lines or lines[0].strip() != "---":
        return 0, len(lines)
    for i in range(1, len(lines)):
        if lines[i].strip() in ("---", "..."):
            return 1, i
    return 1, len(lines)

def yaml_block(lines, lo, hi, key):
    """[lo,hi) 内首个顶层 `key:` 行 → (行下标, 行内余文, [(下标, 行)] 子块)；未找到 → (None, None, [])。"""
    pat = re.compile(r"^(\s*)%s\s*[:：]\s*(.*)$" % key)
    for i in range(lo, hi):
        m = pat.match(lines[i])
        if not m:
            continue
        base, blk = len(m.group(1)), []
        for j in range(i + 1, hi):
            if lines[j].strip() and len(lines[j]) - len(lines[j].lstrip()) <= base:
                break
            blk.append((j, lines[j]))
        return i, m.group(2).strip(), blk
    return None, None, []

def extract_body_lines(lines):
    """提取正文区 [(1-based 行号, 行)]：优先「正文」标题之后，否则 frontmatter 之后；
    跳过标题/围栏/注释行，遇「修订」节或模板页脚即止。"""
    start = 0
    if lines and lines[0].strip() == "---":
        for i in range(1, len(lines)):
            if lines[i].strip() in ("---", "..."):
                start = i + 1
                break
    head = next((i for i in range(start, len(lines))
                 if re.match(r"^#{1,6}\s*(?:\d+[\.、]?\s*)?正文", lines[i])), None)
    if head is not None:
        start = head + 1
    out = []
    for i in range(start, len(lines)):
        ln = lines[i]
        if re.match(r"^#{1,6}\s*修订", ln) or ln.startswith("*template"):
            break
        if re.match(r"^#{1,6}\s", ln) or ln.strip().startswith(("```", "<!--")):
            continue
        out.append((i + 1, ln))
    return out

def nospace(s):
    return re.sub(r"\s+", "", s)

# ---------------- skill 模式 ----------------
def scan_anchors(skill):
    anchors = defaultdict(list)  # K-ID -> [(rel, lineno)]
    for rel, f in iter_files(skill, ["knowledge"]):
        for i, ln in enumerate(read_lines(f), 1):
            for m in ANCHOR_RE.finditer(ln):
                anchors[m.group(1)].append((rel, i))
    return anchors

def scan_registry(skill):
    reg = {}
    for i, ln in enumerate(read_lines(skill / "knowledge-blocks.md"), 1):
        m = REG_RE.match(ln)
        if m and m.group(1) not in reg:
            reg[m.group(1)] = i
    return reg

def scan_refs(skill):
    refs = defaultdict(list)  # K-ID -> [(rel, lineno)]
    for rel, f in iter_files(skill, ["runtime", "phases", "templates", "SKILL.md", "knowledge-index.md"]):
        for i, ln in enumerate(read_lines(f), 1):
            for m in K_ID_RE.finditer(ln):
                refs["K-%s-%s" % (m.group(1), m.group(2))].append((rel, i))
                cont = CONT_RE.match(ln, m.end())  # 仅紧邻连写，避免吞并后续 ID 的后缀
                if cont:
                    for d in re.findall(r"\d{3}", cont.group(0)):
                        refs["K-%s-%s" % (m.group(1), d)].append((rel, i))
            for m in RANGE_RE.finditer(ln):  # K-X-001~020 区间展开
                for n in range(int(m.group(2)), int(m.group(3)) + 1):
                    refs["K-%s-%03d" % (m.group(1), n)].append((rel, i))
    refs.pop("K-FOO-999", None)  # glossary 反例
    return refs

def check_anchor_unique(rep, anchors):
    det = ["%s x%d: %s" % (k, len(v), "; ".join("%s:%d" % t for t in v))
           for k, v in sorted(anchors.items()) if len(v) > 1]
    rep.add("skill.anchor_unique 锚点唯一性", not det, det,
            "knowledge 共 %d 个 K-ID 锚点" % len(anchors))

def check_blocks_recon(rep, anchors, registry):
    det = ["登记无锚点: %s (knowledge-blocks.md:%d)" % (k, registry[k])
           for k in sorted(set(registry) - set(anchors))]
    det += ["有锚点未登记: %s (%s:%d)" % (k, anchors[k][0][0], anchors[k][0][1])
            for k in sorted(set(anchors) - set(registry))]
    rep.add("skill.blocks_recon blocks 对账", not det, det,
            "登记 %d / 锚点 %d" % (len(registry), len(anchors)))

def check_refs_exist(rep, refs, registry):
    det = ["%s 未登记（引用 %d 处，如 %s:%d）"
           % (kid, len(refs[kid]), refs[kid][0][0], refs[kid][0][1])
           for kid in sorted(set(refs) - set(registry))]
    rep.add("skill.refs_exist K-ID 引用存在性", not det, det,
            "引用去重 %d 个 K-ID" % len(refs))

DEPRECATED = [  # (标签, 残留正则, 正式形正则=行内同现则豁免, 目录前缀限定|None=runtime+phases+templates)
    ("trauma 作洋葱键", re.compile(r"\btrauma\s*[:：]"), re.compile(r"\bwound\b"), None),
    ("pay off 含空格", re.compile(r"\bpay\s+off\b"), re.compile(r"\bpayoff\b"), None),
    ("route: hybrid", re.compile(r"\broute\s*[:：]\s*\*?hybrid\b"), re.compile(r"dual_track"), None),
    ("route 枚举含 hybrid", re.compile(r"traditional\s*\\?\|\s*web\s*\\?\|\s*hybrid"),
     re.compile(r"dual_track"), None),
    ("value_in/value_out", re.compile(r"\bvalue_(?:in|out)\b"), re.compile(r"value_start"), None),
    ("hook:{type,note}", re.compile(r"\bhook\s*[:：]\s*\{\s*type"),
     re.compile(r"hooks\s*[:：]\s*\{\s*open"), None),
    ("sequence_id 字段名", re.compile(r"\bsequence_ids?\b"), re.compile(r"sequence_ref"), None),
    ("废弃 type 名", re.compile(r"\b(?:ProseUnit|ThreadMap|ForeshadowLedger)\b"),
     re.compile(r"\bManuscriptUnit\b|\bThread\b"), None),
    # 2026-08-13 修复轮（D2/D5/D1）：
    ("continuity_facts 字段名", re.compile(r"\bcontinuity_facts\s*[:：]"),
     re.compile(r"→\s*`?facts\b"), ("runtime/", "templates/")),
    ("narration 作 content_blocks/unit_type 枚举",
     re.compile(r"(?:content_blocks|unit_type|\btype\b)[^。；;\n]*?`?\bnarration\b"
                r"|\bnarration\b[^。；;\n]*?(?:content_blocks|unit_type)"),
     re.compile(r"\bexposition\b"), None),
    ("publish 默认升 canon 旧语义",
     re.compile(r"publish[^。；;\n]{0,30}(?<![不再没非])(?:晋升|升)\s*[为至到]?\s*[`\*（(]*canon\b"
                r"|canon\s*[（(]\s*默认\s*[)）]"),
     re.compile(r"(?<![不再没非])(?:晋升|升)\s*[为至到]?\s*[`\*（(]*locked\b"), None),
]

def check_deprecated(rep, skill):
    det = []
    for rel, f in iter_files(skill, ["runtime", "phases", "templates"]):
        posix = rel.replace("\\", "/")
        for i, ln in enumerate(read_lines(f), 1):
            for label, pat, formal, dirs in DEPRECATED:
                if dirs and not posix.startswith(dirs):
                    continue
                m = pat.search(ln)
                if m and not EXEMPT_KW.search(ln) and not formal.search(ln):
                    det.append("%s:%d: [%s] %s" % (rel, i, label, m.group(0)[:60]))
    rep.add("skill.deprecated_names 废弃名残留", not det, det)

def extract_chain(line, seed, extra_sep=""):
    """从 seed 词起提取枚举链 token 列表（分隔符 |，可选 extra_sep）。无链返回 None。"""
    sep = r"\s*(?:\\?\||%s)\s*" % re.escape(extra_sep) if extra_sep else PIPE_SEP
    m = re.search(r"\b%s\b(?:%s[\w…]+)+" % (seed, sep), line)
    if not m:
        return None
    toks = [t.strip().rstrip("…").strip() for t in re.split(r"\\?\||/", m.group(0))]
    return [t for t in toks if t]

def is_subseq(tokens, canonical):
    it = iter(canonical)
    return all(tok in it for tok in tokens)

def check_enums(rep, skill):
    det = []
    for rel, f in iter_files(skill, ["runtime", "phases", "templates"]):
        for i, ln in enumerate(read_lines(f), 1):
            loc = "%s:%d" % (rel, i)
            toks = extract_chain(ln, "draft")
            if toks and "review" in toks:  # status 枚举声明行
                bad = [t for t in toks if t not in STATUS_SET and t != "null"]
                if bad:
                    det.append("%s: status 枚举含非法值 %s" % (loc, bad))
                elif len(toks) >= 6 and toks[:6] != STATUS_SET:
                    det.append("%s: status 六值顺序/拼写异常 %s" % (loc, toks[:6]))
            toks = extract_chain(ln, "surface", extra_sep="/")
            if toks is not None:  # 洋葱五键声明行
                if not is_subseq(toks, ONION_KEYS):
                    det.append("%s: 洋葱键异常 %s" % (loc, toks))
                elif len(toks) == 4:
                    det.append("%s: 洋葱键缺一 %s" % (loc, toks))
            toks = extract_chain(ln, "plant")
            if toks is not None and not is_subseq(toks, THREAD_OPS):  # Thread op
                det.append("%s: Thread op 异常 %s" % (loc, toks))
            if re.search(r"\broute\s*[:∈=]", ln):  # route 闭集
                toks = extract_chain(ln, "traditional")
                if toks and any(t not in ROUTE_SET and t != "null" for t in toks):
                    det.append("%s: route 枚举异常 %s" % (loc, toks))
            toks = extract_chain(ln, "dialogue")  # unit_type/content_blocks 五值闭集（管道链形）
            if toks and len(set(toks) & set(UNIT_TYPES)) >= 2:
                bad = [t for t in toks
                       if t not in UNIT_TYPES and re.fullmatch(r"[a-z_]+", t) and t != "null"]
                if bad:
                    det.append("%s: unit_type/content_blocks 枚举含闭集外值 %s（五值 %s）"
                               % (loc, bad, "|".join(UNIT_TYPES)))
            m = re.search(r"\{([^{}:：]*\bdialogue\b[^{}:：]*)\}", ln)  # 集合形 {a, b, …}
            if m:
                toks = [t.strip(" `'\"…") for t in re.split(r"[|,，、/\\]", m.group(1)) if t.strip()]
                if len(set(toks) & set(UNIT_TYPES)) >= 2:
                    bad = [t for t in toks if t not in UNIT_TYPES and re.fullmatch(r"[a-z_]+", t)]
                    if bad:
                        det.append("%s: unit_type/content_blocks 集合含闭集外值 %s（五值 %s）"
                                   % (loc, bad, "|".join(UNIT_TYPES)))
    rep.add("skill.enum_spelling 枚举拼写抽查", not det, det)

def check_domain_counts(rep, skill, registry):
    expected, total_decl = {}, None
    row = re.compile(r"^\|\s*`?([A-Z]+)`?\s*\|[^|]*\|\s*(\d{1,3})\s*[–—~-]\s*(\d{1,3})\s*\|")
    for ln in read_lines(skill / "runtime" / "glossary.md"):
        m = row.match(ln)
        if m:
            expected[m.group(1)] = int(m.group(3)) - int(m.group(2)) + 1
        t = re.search(r"合计\s*\*{0,2}(\d+)\*{0,2}\s*块", ln)
        if t:
            total_decl = int(t.group(1))
    if not expected:
        rep.add("skill.domain_counts 域计数", None, note="glossary §7.1 未解析到域范围表，跳过")
        return
    actual = defaultdict(int)
    for kid in registry:
        actual[kid.split("-")[1]] += 1
    det = ["%s: glossary 声明 %d, blocks 登记 %d" % (d, n, actual.get(d, 0))
           for d, n in sorted(expected.items()) if actual.get(d, 0) != n]
    det += ["blocks 出现声明外域 %s (%d 块)" % (d, c)
            for d, c in sorted(actual.items()) if d not in expected]
    if total_decl is not None and sum(expected.values()) != total_decl:
        det.append("glossary 自身不一致: 各域合计 %d ≠ 声明总数 %d"
                   % (sum(expected.values()), total_decl))
    rep.add("skill.domain_counts 域计数", not det, det,
            "glossary 声明 %s 共 %s" % (dict(sorted(expected.items())), total_decl))

def run_skill(skill, rep):
    if not (skill / "knowledge").is_dir():
        rep.add("skill.layout", False, ["%s 下未找到 knowledge/ 目录" % skill])
        return
    anchors, registry = scan_anchors(skill), scan_registry(skill)
    check_anchor_unique(rep, anchors)
    check_blocks_recon(rep, anchors, registry)
    check_refs_exist(rep, scan_refs(skill), registry)
    check_deprecated(rep, skill)
    check_enums(rep, skill)
    check_domain_counts(rep, skill, registry)

# ---------------- project 模式 ----------------
ASSET_MD_DIRS = ["canon", "decisions", "design", "cast", "world",
                 "threads", "manuscript", "recaps"]

def scan_project_assets(proj):
    """返回 [(rel, path, fm|None)]，md 用 frontmatter，runtime-state yaml 用顶层键。"""
    assets = [(rel, f, parse_frontmatter(read_lines(f)))
              for rel, f in iter_files(proj, ASSET_MD_DIRS)]
    assets += [(rel, f, parse_topkeys(read_lines(f)))
               for rel, f in iter_files(proj, ["runtime-state"], suffix=".yaml")]
    return assets

def check_envelope(rep, assets):
    if not assets:
        rep.add("project.envelope 信封五字段", None, note="未发现资产文件，跳过")
        return
    det = []
    for rel, _f, fm in assets:
        if fm is None:
            det.append("%s:1: 无 frontmatter 块" % rel)
            continue
        missing = [k for k in ENVELOPE_KEYS if k not in fm or fm[k][0] == ""]
        if missing:
            det.append("%s:1: 缺字段 %s" % (rel, ",".join(missing)))
    rep.add("project.envelope 信封五字段", not det, det, "%d 个资产文件" % len(assets))

def check_project_enums(rep, assets):
    if not assets:
        rep.add("project.enums status/type 枚举", None, note="未发现资产文件，跳过")
        return
    det = []
    for rel, _f, fm in assets:
        if not fm:
            continue
        if "status" in fm and fm["status"][0] not in STATUS_SET:
            det.append("%s:%d: status=%r 不在六值闭集" % (rel, fm["status"][1], fm["status"][0]))
        if "type" in fm and fm["type"][0] not in ASSET_TYPES:
            det.append("%s:%d: type=%r 不在 AssetType 闭集" % (rel, fm["type"][1], fm["type"][0]))
    rep.add("project.enums status/type 枚举", not det, det)

def check_onion(rep, proj):
    files = list(iter_files(proj, ["cast"]))
    if not files:
        rep.add("project.onion 洋葱五键", None, note="cast/ 缺失或为空，跳过")
        return
    det = []
    for rel, f in files:
        lines = read_lines(f)
        found = {}
        onion_at = next((i for i, ln in enumerate(lines)
                         if re.match(r"^\s*onion\s*:\s*$", ln)), None)
        if onion_at is None:
            det.append("%s:1: 未找到 onion: 块" % rel)
            continue
        base = len(lines[onion_at]) - len(lines[onion_at].lstrip())
        for j in range(onion_at + 1, len(lines)):
            ln = lines[j]
            if ln.strip() and (len(ln) - len(ln.lstrip())) <= base:
                break
            m = re.match(r"^\s*(%s)\s*[:：]\s*(.*)$" % "|".join(ONION_KEYS), ln)
            if m:
                found[m.group(1)] = (clean_value(m.group(2)), j + 1)
        missing = [k for k in ONION_KEYS if k not in found]
        empty = [k for k, (v, _l) in found.items() if v in ("", "null", "~", "[]")]
        if missing or empty:
            det.append("%s:%d: 缺键 %s；空值 %s" % (rel, onion_at + 1, missing or "-", empty or "-"))
    rep.add("project.onion 洋葱五键", not det, det, "%d 张人物卡" % len(files))

def parse_spine_nodes(lines):
    nodes, in_nodes, cur = {}, False, None  # id -> [anchor_raw, lineno]
    for i, ln in enumerate(lines, 1):
        if re.match(r"^nodes\s*:", ln):
            in_nodes, cur = True, None
            continue
        if not in_nodes:
            continue
        if re.match(r"^[A-Za-z_]+\s*:", ln) or ln.strip() in ("---", "```"):
            break
        m = re.search(r"-\s*\{\s*id\s*:\s*(\d+)\b", ln)  # 行内式
        if m:
            a = re.search(r"anchor\s*:\s*(\[[^\]]*\]|[\w]+)", ln)
            nodes[int(m.group(1))] = [a.group(1) if a else None, i]
            cur = None
            continue
        m = re.match(r"^\s*-\s*id\s*:\s*(\d+)\s*$", ln)  # 块式
        if m:
            cur = int(m.group(1))
            nodes[cur] = [None, i]
            continue
        if cur is not None:
            a = re.match(r"^\s*anchor\s*:\s*(\[[^\]]*\]|\S+)\s*$", ln)
            if a:
                nodes[cur][0] = a.group(1)
    return nodes

def check_plot_spine(rep, proj):
    f = proj / "design" / "plot_spine.md"
    if not f.is_file():
        rep.add("project.plot_spine 24 节点与锚点", None, note="design/plot_spine.md 缺失，跳过")
        return
    nodes = parse_spine_nodes(read_lines(f))
    det, ids = [], set(nodes)
    if ids != set(range(24)):
        det.append("nodes 计数 %d，缺 %s，多 %s" % (
            len(ids), sorted(set(range(24)) - ids) or "-", sorted(ids - set(range(24))) or "-"))
    for nid in sorted(REQUIRED_ANCHOR_NODES & ids):
        raw, lineno = nodes[nid]
        vals = [v for v in re.findall(r"[\w]+", raw or "") if v != "null"]
        if not vals:
            det.append("design/plot_spine.md:%d: 必保锚点位 %d 未填 anchor" % (lineno, nid))
        else:
            det += ["design/plot_spine.md:%d: 节点 %d 锚点名非法 %r" % (lineno, nid, v)
                    for v in vals if v not in ANCHOR_SET]
    rep.add("project.plot_spine 24 节点与锚点", not det, det)

def parse_manifest_entries(lines):
    entries, cur = [], None
    for i, ln in enumerate(lines, 1):
        m = re.match(r"^(\s*)-\s*asset_id\s*:\s*(\S+)", ln)
        if m:
            cur = {"asset_id": clean_value(m.group(2)), "_line": i, "_indent": len(m.group(1))}
            entries.append(cur)
            continue
        if cur is None:
            continue
        indent = len(ln) - len(ln.lstrip())
        m = re.match(r"^\s+([\w]+)\s*:\s*(.*)$", ln)
        if m and indent > cur["_indent"]:
            cur.setdefault(m.group(1), clean_value(m.group(2)))
        elif ln.strip().startswith(("-", "#")) and indent > cur["_indent"]:
            continue  # 嵌套列表项（如 depends_on 子项），不终止 entry
        elif ln.strip():
            cur = None
    return entries

def check_manifest(rep, proj, assets):
    manifests = [(r, f) for r, f in iter_files(proj, ["runtime-state"], suffix=".yaml")
                 if Path(r).name.startswith("manifest")]
    if not manifests:
        rep.add("project.manifest_recon Manifest 对账", None,
                note="runtime-state/manifest*.yaml 缺失，跳过")
        return
    index = {fm["id"][0]: (rel, fm) for rel, _f, fm in assets if fm and "id" in fm}
    det, n = [], 0
    for rel, f in manifests:
        for e in parse_manifest_entries(read_lines(f)):
            n += 1
            loc = "%s:%d" % (rel, e["_line"])
            hit = index.get(e["asset_id"])
            if hit is None:
                det.append("%s: entry %s 找不到对应资产文件" % (loc, e["asset_id"]))
                continue
            arel, fm = hit
            for key in ("rev", "status"):
                ev, av = e.get(key), fm.get(key, ("<缺>", 0))[0]
                if ev is not None and str(ev) != str(av):
                    det.append("%s: %s.%s manifest=%s ≠ 资产(%s)=%s"
                               % (loc, e["asset_id"], key, ev, arel, av))
    rep.add("project.manifest_recon Manifest 对账", not det, det, "%d 条 entry" % n)

def check_id_conventions(rep, proj):
    det, seen = [], False
    for rel, f in iter_files(proj, ["manuscript"]):
        seen = True
        if not re.fullmatch(r"ms_\d{4}\.md", f.name):
            det.append("%s: 文件名不符 ms_{nnnn}.md（四位全局章号）" % rel)
    scenes = proj / "design" / "scenes"
    if scenes.is_dir():
        seen = True
        for f in sorted(scenes.glob("*.md")):
            if not re.fullmatch(r"scene_v\d+_\d{1,2}_\d{2}\.md", f.name):
                det.append("design/scenes/%s: 文件名不符 scene_v{v}_{s}_{nn}.md" % f.name)
    if not seen:
        rep.add("project.id_conventions id 约定", None,
                note="manuscript/ 与 design/scenes/ 均缺失，跳过")
    else:
        rep.add("project.id_conventions id 约定", not det, det)

def check_sequence_ref(rep, proj, assets):
    if not assets:
        rep.add("project.sequence_ref 复合键格式", None, note="未发现资产文件，跳过")
        return
    det, n = [], 0
    for rel, f, _fm in assets:
        lines = read_lines(f)
        for i, ln in enumerate(lines, 1):
            m = re.search(r"\bsequence_ref\s*[:：]\s*(.*)$", ln)
            if not m:
                continue
            n += 1
            rest = re.split(r"\s+#", m.group(1), 1)[0].strip()
            if rest in ("null", "~"):
                continue
            blob = rest or " ".join(x.strip() for x in lines[i:i + 4])  # 块式：看后 4 行
            if not ("volume_id" in blob and "sequence_index" in blob):
                det.append("%s:%d: sequence_ref 缺 volume_id/sequence_index（复合键）" % (rel, i))
    rep.add("project.sequence_ref 复合键格式", not det, det, "%d 处引用" % n)

# —— 2026-08-13 修复轮新增（D8.2）——
def parse_status_meta(proj):
    """runtime-state 下 Status 文件的写作/critic 游标；不可解析的键缺省。返回 dict 或 None。"""
    for rel, f in iter_files(proj, ["runtime-state"], suffix=".yaml"):
        txt = "\n".join(read_lines(f))
        if not (Path(rel).name.startswith("status")
                or re.search(r"^\s*type\s*:\s*Status\b", txt, re.M)):
            continue
        meta = {"rel": rel}
        m = re.search(r"\blast_written(?:_chapter)?\s*:\s*(\d+)", txt)
        if m:
            meta["last_written"] = int(m.group(1))
        else:
            m = re.search(r"\bnext_write_chapter\s*:\s*(\d+)", txt)
            if m:
                meta["last_written"] = int(m.group(1)) - 1  # 由写作游标推导
        m = re.search(r"\blast_critic_chapter\s*:\s*(\d+)", txt)
        if m:
            meta["last_critic"] = int(m.group(1))
        m = re.search(r"every_(\d+)_chapters", txt)
        if m:
            meta["cadence"] = int(m.group(1))
        return meta
    return None

def check_canon_facts(rep, proj):
    """canon_continuity 分片必须用 facts:；canon/ 内任何 continuity_facts: 字段 = FAIL（D2.1）。"""
    files = list(iter_files(proj, ["canon"]))
    if not files:
        rep.add("project.canon_facts 连续性字段名", None, note="canon/ 缺失或为空，跳过")
        return
    det = []
    for rel, f in files:
        lines = read_lines(f)
        lo, hi = fm_region(lines)
        is_shard, has_facts = "canon_continuity" in f.name, False
        for i in range(lo, hi):
            ln = lines[i]
            if ln.lstrip().startswith("#"):
                continue
            if re.match(r"^\s*continuity_facts\s*[:：]", ln):
                det.append("%s:%d: 废弃字段名 continuity_facts:（D2 全库统一为 facts:）" % (rel, i + 1))
            if re.match(r"^facts\s*[:：]", ln):
                has_facts = True
            m = re.match(r"^id\s*:\s*(.+)$", ln)
            if m and clean_value(m.group(1)).startswith("canon_continuity"):
                is_shard = True
        if is_shard and not has_facts:
            det.append("%s: 连续性分片缺顶层 facts: 键" % rel)
    rep.add("project.canon_facts 连续性字段名", not det, det, "%d 个 canon 文件" % len(files))

def check_retcon_entity_ids(rep, proj):
    """retcon_notes 每条必含 entity_ids（D2.3）。"""
    files = list(iter_files(proj, ["canon"]))
    if not files:
        rep.add("project.retcon_entity_ids retcon 条目 entity_ids", None,
                note="canon/ 缺失或为空，跳过")
        return
    det, n = [], 0
    for rel, f in files:
        lines = read_lines(f)
        lo, hi = fm_region(lines)
        at, rest, blk = yaml_block(lines, lo, hi, "retcon_notes")
        if at is None:
            continue
        if rest and rest not in ("[]", "null", "~"):
            n += 1
            if "entity_ids" not in rest:
                det.append("%s:%d: retcon_notes 行内条目缺必填 entity_ids" % (rel, at + 1))
            continue
        items, item_ind = [], None
        for j, ln in blk:
            if not ln.strip() or ln.lstrip().startswith("#"):
                continue
            m = re.match(r"^(\s*)-\s", ln)
            if m and (item_ind is None or len(m.group(1)) == item_ind):
                item_ind = len(m.group(1))
                items.append([j + 1, [ln]])
            elif items:
                items[-1][1].append(ln)
        for start, ls in items:
            n += 1
            if not any("entity_ids" in x for x in ls):
                det.append("%s:%d: retcon 条目缺必填 entity_ids（实体检索键，D2.3）" % (rel, start))
    if n == 0 and not det:
        rep.add("project.retcon_entity_ids retcon 条目 entity_ids", None,
                note="未发现 retcon_notes 条目，跳过")
    else:
        rep.add("project.retcon_entity_ids retcon 条目 entity_ids", not det, det, "%d 条 retcon" % n)

def check_decision_approved_by(rep, assets):
    """Decision.approved_by 非空且 ∈ {user, agent_auto}（D6.10；留空 = FAIL）。"""
    decs = [(rel, fm) for rel, _f, fm in assets
            if rel.replace("\\", "/").startswith("decisions/")
            or (fm and fm.get("type", ("",))[0] == "Decision")]
    if not decs:
        rep.add("project.decision_approved_by Decision 授权人", None,
                note="未发现 Decision 资产，跳过")
        return
    det = []
    for rel, fm in decs:
        if not fm or "approved_by" not in fm:
            det.append("%s:1: 缺必填 approved_by（user | agent_auto）" % rel)
            continue
        v, ln = fm["approved_by"]
        if v in ("", "null", "~") or v.startswith("["):
            det.append("%s:%d: approved_by 为空（必填 user | agent_auto；留空即 FAIL）" % (rel, ln))
        elif v not in APPROVED_BY_SET:
            det.append("%s:%d: approved_by=%r 不在 {user, agent_auto}（级别表 asset-types §2.4）"
                       % (rel, ln, v))
    rep.add("project.decision_approved_by Decision 授权人", not det, det, "%d 个 Decision" % len(decs))

def check_manifest_decision_load(rep, proj):
    """manifest_root 非 open Decision entry >20 → WARN，提示迁 manifest_decisions_v{n}（D3）。"""
    root = None
    for rel, f in iter_files(proj, ["runtime-state"], suffix=".yaml"):
        if not Path(rel).name.startswith("manifest"):
            continue
        if Path(rel).name.startswith("manifest_root") \
           or any(re.match(r"^id\s*:\s*manifest_root\b", ln) for ln in read_lines(f)):
            root = (rel, f)
            break
    if root is None:
        rep.add("project.manifest_decision_load root Decision 载荷", None,
                note="manifest_root 缺失，跳过")
        return
    rel, f = root
    dec = [e for e in parse_manifest_entries(read_lines(f))
           if e.get("type") == "Decision" or str(e.get("asset_id", "")).startswith("decision")]
    non_open = [e for e in dec if e.get("status") not in DECISION_OPEN_STATUS
                and "long_term" not in str(e.get("tags", ""))]
    det = []
    if len(non_open) > DECISION_ROOT_MAX:
        det.append("%s: 非 open Decision entry %d 条 > %d：应于 volume_checkpoint 迁入 "
                   "manifest_decisions_v{n} 分片（D3；root 只留 open/active）"
                   % (rel, len(non_open), DECISION_ROOT_MAX))
    rep.add("project.manifest_decision_load root Decision 载荷", not det, det,
            "Decision entry %d 条 / 非 open %d 条" % (len(dec), len(non_open)), warn=True)

def check_ms_summary_after(rep, proj):
    """ManuscriptUnit.summary_after 必填非空（下一章召回第一入口）。"""
    files = list(iter_files(proj, ["manuscript"]))
    if not files:
        rep.add("project.ms_summary_after 写后摘要非空", None, note="manuscript/ 缺失或为空，跳过")
        return
    det = []
    for rel, f in files:
        lines = read_lines(f)
        lo, hi = fm_region(lines)
        at, rest, blk = yaml_block(lines, lo, hi, "summary_after")
        if at is None:
            det.append("%s: 缺必填 summary_after" % rel)
            continue
        rs = (rest or "").strip()
        if rs.startswith(("|", ">")):  # 块标量：看子块有无内容
            if not any(x.strip() for _j, x in blk):
                det.append("%s:%d: summary_after 块标量为空" % (rel, at + 1))
        elif clean_value(rs) in ("", "null", "~"):
            det.append("%s:%d: summary_after 为空（必填：写后摘要 3–8 句）" % (rel, at + 1))
    rep.add("project.ms_summary_after 写后摘要非空", not det, det, "%d 个 unit" % len(files))

def q_val(s):
    """quote: 之后的宽松取值（引号内容优先，否则截到 , } #）。"""
    s = s.strip()
    m = re.match(r'"((?:\\.|[^"\\])*)"', s) or re.match(r"'([^']*)'", s)
    if m:
        return m.group(1)
    return re.split(r"[,}#]", s, 1)[0].strip()

def resolve_body(proj, f, lines, fm):
    """解析 unit 正文：body_uri 外置优先，否则取本文件正文区。返回 (正文 or None, 说明)。"""
    uri = fm.get("body_uri", ("", 0))[0] if fm else ""
    if uri and uri not in ("null", "~"):
        for cand in (f.parent / uri, proj / uri):
            if cand.is_file():
                t = "\n".join(x for _l, x in extract_body_lines(read_lines(cand)))
                if t.strip():
                    return t, "body_uri"
        return None, "body_uri=%s 不可读" % uri
    t = "\n".join(x for _l, x in extract_body_lines(lines))
    return (t, "内嵌正文") if t.strip() else (None, "正文区为空")

def check_ms_evidence_quotes(rep, proj):
    """evidence_checks[].quote 须为正文子串（空白归一后比对）；正文不可读的 unit 跳过。"""
    files = list(iter_files(proj, ["manuscript"]))
    if not files:
        rep.add("project.ms_evidence_quote 摘引为正文子串", None, note="manuscript/ 缺失或为空，跳过")
        return
    det, nq, empty_q, skipped = [], 0, 0, []
    for rel, f in files:
        lines = read_lines(f)
        lo, hi = fm_region(lines)
        at, _rest, blk = yaml_block(lines, lo, hi, "evidence_checks")
        if at is None:
            continue
        quotes = []
        for j, ln in blk:
            for m in re.finditer(r"\bquote\s*[:：]\s*", ln):
                quotes.append((j + 1, q_val(ln[m.end():])))
        if not quotes:
            continue
        body, how = resolve_body(proj, f, lines, parse_frontmatter(lines))
        if body is None:
            skipped.append("%s（%s）" % (rel, how))
            continue
        flat = nospace(body)
        for lineno, q in quotes:
            if not q or q in ("null", "~"):
                empty_q += 1
                continue
            nq += 1
            if nospace(q) not in flat:
                det.append("%s:%d: quote 非正文子串:「%s」" % (rel, lineno, q[:30]))
    note = "校验 %d 条 quote / 空 quote %d 条" % (nq, empty_q)
    if skipped:
        note += "；%d 个 unit 正文不可读未查（如 %s）" % (len(skipped), skipped[0])
    if nq == 0 and not det:
        rep.add("project.ms_evidence_quote 摘引为正文子串", None, note=note + "，跳过")
    else:
        rep.add("project.ms_evidence_quote 摘引为正文子串", not det, det, note)

def check_ms_hooks(rep, proj):
    """hooks_realized 须含 open/close 双键（对齐 ChapterPlan.hooks；web 强制 close）。"""
    files = list(iter_files(proj, ["manuscript"]))
    if not files:
        rep.add("project.ms_hooks_realized 钩子 open/close 双键", None,
                note="manuscript/ 缺失或为空，跳过")
        return
    det = []
    for rel, f in files:
        lines = read_lines(f)
        lo, hi = fm_region(lines)
        at, rest, blk = yaml_block(lines, lo, hi, "hooks_realized")
        if at is None:
            det.append("%s: 缺 hooks_realized（须含 open/close 双键）" % rel)
            continue
        blob = (rest or "") + " " + " ".join(x for _j, x in blk)
        missing = [k for k in ("open", "close") if not re.search(r"\b%s\s*[:：]" % k, blob)]
        if missing:
            det.append("%s:%d: hooks_realized 缺键 %s" % (rel, at + 1, ",".join(missing)))
    rep.add("project.ms_hooks_realized 钩子 open/close 双键", not det, det, "%d 个 unit" % len(files))

def check_recap_coverage(rep, proj, meta):
    """全部 Recap 的 covers_chapters 上界 max ≥ Status.last_written（recap_state 随写作滚动）。"""
    files = list(iter_files(proj, ["recaps"]))
    if not files:
        rep.add("project.recap_coverage Recap 覆盖游标", None, note="recaps/ 缺失或为空，跳过")
        return
    uppers = []
    for rel, f in files:
        for i, ln in enumerate(read_lines(f), 1):
            m = re.search(r"\bcovers_chapters\s*[:：]\s*\[\s*(\d+)\s*,\s*(\d+)\s*\]", ln)
            if m:
                uppers.append((int(m.group(2)), rel, i))
    if not uppers:
        rep.add("project.recap_coverage Recap 覆盖游标", None,
                note="未解析到 covers_chapters: [a, b]，跳过")
        return
    if meta is None or "last_written" not in meta:
        rep.add("project.recap_coverage Recap 覆盖游标", None,
                note="Status.last_written 不可解析，跳过")
        return
    hi, rel, i = max(uppers)
    det = []
    if hi < meta["last_written"]:
        det.append("Recap 覆盖上界 %d（%s:%d）< Status.last_written %d：recap 未跟进写作游标"
                   % (hi, rel, i, meta["last_written"]))
    rep.add("project.recap_coverage Recap 覆盖游标", not det, det,
            "max end=%d / last_written=%d" % (hi, meta["last_written"]))

def check_critic_lag(rep, meta):
    """last_critic_chapter 落后 last_written 超一个 critic_cadence 周期 → WARN（漏跑可检，D6.9）。"""
    if meta is None:
        rep.add("project.critic_lag critic 轮时效", None, note="Status 文件不可解析，跳过")
        return
    need = [k for k in ("last_written", "last_critic", "cadence") if k not in meta]
    if need:
        rep.add("project.critic_lag critic 轮时效", None,
                note="Status 缺 %s，跳过" % ",".join(need))
        return
    lag = meta["last_written"] - meta["last_critic"]
    det = []
    if lag > meta["cadence"]:
        det.append("last_critic_chapter=%d 落后 last_written=%d 共 %d 章 > cadence %d："
                   "critic 轮漏跑（contracts §7.9）"
                   % (meta["last_critic"], meta["last_written"], lag, meta["cadence"]))
    rep.add("project.critic_lag critic 轮时效", not det, det,
            "lag=%d / cadence=%d" % (lag, meta["cadence"]), warn=True)

def run_project(proj, rep):
    assets = scan_project_assets(proj)
    meta = parse_status_meta(proj)
    check_envelope(rep, assets)
    check_project_enums(rep, assets)
    check_onion(rep, proj)
    check_plot_spine(rep, proj)
    check_manifest(rep, proj, assets)
    check_id_conventions(rep, proj)
    check_sequence_ref(rep, proj, assets)
    check_canon_facts(rep, proj)
    check_retcon_entity_ids(rep, proj)
    check_decision_approved_by(rep, assets)
    check_manifest_decision_load(rep, proj)
    check_ms_summary_after(rep, proj)
    check_ms_evidence_quotes(rep, proj)
    check_ms_hooks(rep, proj)
    check_recap_coverage(rep, proj, meta)
    check_critic_lag(rep, meta)

# ---------------- unit 模式（单章文本质量机检，D8.3）----------------
def load_taboo_list(style_path):
    """style-card 的 taboo_list 条目列表；未找到键返回 None。"""
    lines = read_lines(style_path)
    at, rest, blk = yaml_block(lines, 0, len(lines), "taboo_list")
    if at is None:
        return None
    items = []
    if rest and rest not in ("[]",):
        items += [clean_value(x) for x in rest.strip("[]").split(",") if clean_value(x)]
    for _j, ln in blk:
        s = ln.strip()
        if s.startswith("- "):
            items.append(clean_value(s[2:]))
    return [x for x in items if x]

def expand_parens(s):
    """展开「A（x/y）B」括注交替 → [AxB, AyB, AB(主干，≥4字才留)]；（……）只留主干。"""
    m = re.search(r"[（(]([^（）()]*)[)）]", s)
    if not m:
        return [s]
    pre, post = s[:m.start()], s[m.end():]
    alts = [a.strip() for a in re.split(r"[/／]", m.group(1))]
    alts = [a for a in alts if a and a not in ("……", "…", "...")]
    outs = [pre + a + post for a in alts]
    stem = pre + post
    if len(nospace(stem)) >= 4 or not outs:
        outs.append(stem)
    res = []
    for o in outs:
        res.extend(expand_parens(o))
    return res

def taboo_needles(entry):
    """taboo 条目 → (字面检索变体, 命中阈值, 是否可机检)。「——」后为说明；「xx：」标签式条目不机检。"""
    m = re.search(r"[>＞]\s*(\d+)\s*次", entry)
    threshold = int(m.group(1)) if m else 0
    core = entry.split("——")[0].strip()
    if re.match(r"^[^：:]{1,12}[：:]", core):
        return [], threshold, False
    variants = []
    for ex in expand_parens(core):
        for part in re.split(r"[/／]", ex):
            part = nospace(part)
            if len(part) >= 2:
                variants.append(part)
    variants = sorted(set(variants), key=len, reverse=True)
    if variants and len(variants[0]) >= 4:  # 有长变体时丢弃 2 字碎片（如「眼底/眼中闪过一丝」的「眼底」）
        variants = [v for v in variants if len(v) >= 3]
    return variants, threshold, bool(variants)

def check_unit_taboo(rep, body_lines, style_path):
    if style_path is None:
        rep.add("unit.taboo_list 口癖黑名单", None, note="未提供 --style，跳过")
        return
    if not style_path.is_file():
        rep.add("unit.taboo_list 口癖黑名单", None, note="style 文件不存在: %s，跳过" % style_path)
        return
    taboo = load_taboo_list(style_path)
    if taboo is None:
        rep.add("unit.taboo_list 口癖黑名单", None, note="style-card 未解析到 taboo_list:，跳过")
        return
    if not taboo:
        rep.add("unit.taboo_list 口癖黑名单", None, note="taboo_list 为空，跳过")
        return
    det, unscannable = [], 0
    for entry in taboo:
        variants, threshold, scannable = taboo_needles(entry)
        if not scannable:
            unscannable += 1
            continue
        hits = []  # (行号, 上下文)
        for lineno, ln in body_lines:
            flat, taken = nospace(ln), []  # taken: 已命中跨度，防主干与完整变体重复计数
            for v in variants:  # 变体已按长度降序
                k = flat.find(v)
                while k >= 0:
                    if not any(k < e and k + len(v) > s for s, e in taken):
                        taken.append((k, k + len(v)))
                        hits.append((lineno, flat[max(0, k - 8):k + len(v) + 8]))
                    k = flat.find(v, k + len(v))
        if len(hits) > threshold:
            det.append("「%s」命中 %d 次（阈值 %d）:" % (entry, len(hits), threshold))
            det += ["  L%d: …%s…" % (l, c) for l, c in hits[:6]]
            if len(hits) > 6:
                det.append("  … 另 %d 处" % (len(hits) - 6))
    rep.add("unit.taboo_list 口癖黑名单", not det, det,
            "%d 条黑名单（%d 条句式级未机检）" % (len(taboo), unscannable))

def split_sentences(body_lines):
    """正文 → [(行号, 句)]；句以 。！？!?… 切分，剥句首引号/标点。"""
    sents = []
    for lineno, ln in body_lines:
        for s in re.split(r"[。！？!?…]+", ln):
            s = s.strip().lstrip("「」『』【】“”‘’\"'（）()，,、—―·:：;；-— ")
            if len(s) >= 2:
                sents.append((lineno, s))
    return sents

def check_unit_same_head(rep, sents):
    if len(sents) < 3:
        rep.add("unit.same_head 连续 3 句同首词", None, note="不足 3 句，跳过")
        return
    det, i = [], 0
    while i < len(sents):
        j = i
        while j + 1 < len(sents) and sents[j + 1][1][0] == sents[i][1][0]:
            j += 1
        if j - i + 1 >= 3:
            det.append("L%d–L%d: 连续 %d 句以「%s」开头（%s… / %s… / %s…）"
                       % (sents[i][0], sents[j][0], j - i + 1, sents[i][1][0],
                          sents[i][1][:6], sents[i + 1][1][:6], sents[i + 2][1][:6]))
        i = j + 1
    rep.add("unit.same_head 连续 3 句同首词", not det, det, "%d 句" % len(sents), warn=True)

def check_unit_ngram(rep, body):
    text = re.sub(r"[\W_]+", "", body)
    total = len(text) - 3
    if total < 200:
        rep.add("unit.ngram_repeat 4-gram 重复率", None, note="有效字符不足，样本过短，跳过")
        return
    cnt = Counter(text[i:i + 4] for i in range(total))
    dup = total - len(cnt)
    rate = dup / total
    det = []
    if rate > NGRAM_WARN_RATE:
        top = ["%s×%d" % (g, c) for g, c in cnt.most_common(5) if c > 1]
        det.append("字级 4-gram 重复率 %.2f%% > %.0f%%（重复 %d / 总 %d）；高频: %s"
                   % (rate * 100, NGRAM_WARN_RATE * 100, dup, total, "、".join(top)))
    rep.add("unit.ngram_repeat 4-gram 重复率", not det, det, "%.2f%%" % (rate * 100), warn=True)

def check_unit_length(rep, body):
    n = len(nospace(body))
    det = []
    if not WORD_BAND[0] <= n <= WORD_BAND[1]:
        det.append("去空白字数 %d 超出 [%d, %d]（2000–4500 ±15%%）" % (n, WORD_BAND[0], WORD_BAND[1]))
    rep.add("unit.word_count 字数区间", not det, det, "%d 字" % n, warn=True)

def check_unit_ending(rep, body_lines):
    paras, cur = [], []
    for lineno, ln in body_lines:
        if ln.strip():
            cur.append((lineno, ln.strip()))
        elif cur:
            paras.append(cur)
            cur = []
    if cur:
        paras.append(cur)
    if not paras:
        rep.add("unit.ending_summary 末段总结化句式", None, note="无末段，跳过")
        return
    det = []
    for lineno, ln in paras[-1]:
        for w in END_SUMMARY_BLACKLIST:
            k = ln.find(w)
            if k >= 0:
                det.append("L%d: 命中「%s」: …%s…" % (lineno, w, ln[max(0, k - 6):k + len(w) + 6]))
    rep.add("unit.ending_summary 末段总结化句式", not det, det,
            "内置黑名单 %d 条" % len(END_SUMMARY_BLACKLIST), warn=True)

UNIT_CHECK_NAMES = ["unit.taboo_list 口癖黑名单", "unit.same_head 连续 3 句同首词",
                    "unit.ngram_repeat 4-gram 重复率", "unit.word_count 字数区间",
                    "unit.ending_summary 末段总结化句式"]

def run_unit(unit_path, style_path, rep):
    lines = read_lines(unit_path)
    body_lines = extract_body_lines(lines)
    body = "\n".join(ln for _l, ln in body_lines)
    if not body.strip():
        rep.add("unit.body 正文提取", False,
                ["%s: 未提取到非空正文（frontmatter 后或「正文」标题下均无内容）" % unit_path.name])
        for name in UNIT_CHECK_NAMES:
            rep.add(name, None, note="正文为空，跳过")
        return
    rep.add("unit.body 正文提取", True,
            note="%d 行 / 去空白 %d 字" % (len(body_lines), len(nospace(body))))
    check_unit_taboo(rep, body_lines, style_path)
    check_unit_same_head(rep, split_sentences(body_lines))
    check_unit_ngram(rep, body)
    check_unit_length(rep, body)
    check_unit_ending(rep, body_lines)

def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--skill", metavar="DIR", help="校验 skill 目录本身")
    g.add_argument("--project", metavar="DIR", help="校验项目实例目录（storage adapter 布局）")
    g.add_argument("--unit", metavar="MS_FILE", help="单章文本质量机检（ManuscriptUnit 文件）")
    ap.add_argument("--style", metavar="FILE", help="canon_style 风格卡文件（--unit 时提供 taboo_list）")
    ap.add_argument("--quiet", action="store_true", help="只输出 FAIL/WARN 与 summary")
    args = ap.parse_args()
    rep = Report(args.quiet)
    if args.unit:
        unit = Path(args.unit).expanduser()
        if not unit.is_file():
            print("[FAIL] 文件不存在: %s" % unit)
            return 1
        run_unit(unit, Path(args.style).expanduser() if args.style else None, rep)
        return rep.finish()
    root = Path(args.skill or args.project).expanduser()
    if not root.is_dir():
        print("[FAIL] 目录不存在: %s" % root)
        return 1
    (run_skill if args.skill else run_project)(root, rep)
    return rep.finish()

if __name__ == "__main__":
    sys.exit(main())
