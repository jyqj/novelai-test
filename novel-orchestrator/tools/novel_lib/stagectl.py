# -*- coding: utf-8 -*-
"""stagectl — 阶段状态机（P7-S）：state/stage.json 持久化 + stage enter/current +
stage_guard 强制闸门；启发式推断仅作导航核对，不再是阶段的定义。"""
import json

from .common import NOW, SKILL_ROOT, die, git_autocommit, read, write
from .project import Project, find_root, load_queue_promoted, next_task_id

# 阶段目录：id → (名称, 一句话定位, 配套知识包相对路径)
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


def stage_row(sid):
    for row in STAGES:
        if row[0] == sid:
            return row
    return None


# ---------------------------------------------------------------- 持久化状态
def stage_state(proj):
    """读 state/stage.json；不存在或不可解析返回 None。"""
    f = proj.p("state", "stage.json")
    if not f.is_file():
        return None
    try:
        return json.loads(read(f))
    except ValueError:
        return None


def current_stage(proj):
    st = stage_state(proj)
    return (st or {}).get("stage")


def stage_guard(proj, allowed, op):
    """强制阶段闸门（P7-S）：受辖操作执行前校验 state/stage.json。
    - 未进入任何阶段（无 stage.json）→ 拒绝（exit 1），提示 stage enter；
    - 当前阶段 ∉ allowed → 拒绝（exit 1），提示先收口再 stage enter；
    - allowed=None 表示只要求「已进入某阶段」（gate next 用）。
    只判不写；文档契约见 protocol/knowledge-orchestration.md §5。"""
    cur = current_stage(proj)
    if cur is None:
        want = allowed[0] if allowed else infer_stage(proj)[0]
        die("%s 被阶段闸门拒绝：项目尚未进入任何阶段（state/stage.json 缺失）\n"
            "  ↳ 下一步：novel.py stage enter %s（该操作属阶段 %s；先读包 stage show %s）"
            % (op, want, "|".join(allowed) if allowed else "任意", want), 1)
    if allowed and cur not in allowed:
        die("%s 被阶段闸门拒绝：该操作属阶段 %s，当前已进入 %s\n"
            "  ↳ 下一步：当前环节收口后 novel.py stage enter %s；"
            "或回到 %s 阶段的操作面（stage show %s）"
            % (op, "|".join(allowed), cur, allowed[0], cur, cur), 1)


# ---------------------------------------------------------------- 启发式推断
def infer_stage(proj):
    """启发式阶段推断（仅导航核对，不是阶段定义）：court 工作区 > 设计缺口 >
    队首任务类型。返回 (stage_id, 依据一句话)。阶段本身以 state/stage.json 为准。"""
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
    """gate next 末段：已进入阶段 + 配套包 + 启发式核对（不一致时给 enter 提示）。"""
    sid, why = infer_stage(proj)
    cur = current_stage(proj)
    if cur:
        row = stage_row(cur)
        print("当前阶段: %s（%s）— 配套知识包: %s" % (cur, row[1], SKILL_ROOT / row[3]))
        if sid != cur:
            print("  启发式核对: 推断 %s（%s）——若当前环节已收口：stage enter %s"
                  % (sid, why, sid))
    else:
        print("尚未进入任何阶段（state/stage.json 缺失；阶段闸门将拒绝各环节操作）")
        print("  启发式推断: %s（%s）" % (sid, why))
        print("  ↳ 下一步：novel.py stage enter %s" % sid)
    if proj.config.get("route", "web") == "traditional" and (cur or sid) != "diag":
        print("  叠加差分: trad → %s" % (SKILL_ROOT / "protocol/stages/trad-overlay.md"))


# ---------------------------------------------------------------- CLI
def cmd_stage(args):
    """阶段状态机 CLI：list=总表；show <id>=打印配套知识包全文；
    enter <id>=进入阶段（写 state/stage.json，各环节闸门的钥匙）；
    current=读持久化阶段 + 启发式核对（未进入任何阶段时 exit 1）。"""
    if args.stage_cmd == "list":
        print("== stage list（阶段总表；SSOT=protocol/knowledge-orchestration.md）==")
        for sid, name, gist, rel in STAGES:
            print("%-7s %-10s %s" % (sid, name, gist))
            print("        包: %s" % (SKILL_ROOT / rel))
        print("（进环节 = stage enter <id> 后先读包再动工；阶段闸门拒绝跨阶段操作）")
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
    if args.stage_cmd == "enter":
        row = stage_row(args.stage_id)
        if not row:
            die("未知阶段 id：%s（可选：%s）"
                % (args.stage_id, " ".join(r[0] for r in STAGES)))
        proj = Project(find_root(args))
        st = stage_state(proj) or {}
        prev = st.get("stage")
        if prev == args.stage_id:
            print("已在阶段 %s（%s）——无需重复进入" % (args.stage_id, row[1]))
            return 0
        hist = (st.get("history") or [])[-19:]
        hist.append({"from": prev, "to": args.stage_id, "at": NOW()})
        write(proj.p("state", "stage.json"),
              json.dumps({"stage": args.stage_id, "entered_at": NOW(),
                          "history": hist}, ensure_ascii=False, indent=1))
        git_autocommit(proj.root, "[stage] enter %s（自 %s）"
                       % (args.stage_id, prev or "∅"))
        print("已进入阶段 %s（%s）" % (args.stage_id, row[1]))
        print("  先读配套知识包: %s" % (SKILL_ROOT / row[3]))
        sid, why = infer_stage(proj)
        if sid != args.stage_id:
            print("  [核对] 启发式推断: %s（%s）——跨阶段进入请确认上一环节已收口"
                  "（workflow §1）" % (sid, why))
        return 0
    # current
    proj = Project(find_root(args))
    sid, why = infer_stage(proj)
    st = stage_state(proj)
    if not st or not st.get("stage"):
        print("尚未进入任何阶段（state/stage.json 缺失）——阶段闸门将拒绝各环节操作")
        print("  启发式推断: %s（%s）" % (sid, why))
        row = stage_row(sid)
        print("  ↳ 下一步：novel.py stage enter %s（配套知识包: %s）"
              % (sid, SKILL_ROOT / row[3]))
        return 1
    cur = st["stage"]
    row = stage_row(cur)
    print("当前阶段: %s（%s）— 进入于 %s" % (cur, row[1], st.get("entered_at")))
    print("  配套知识包: %s（先读包再动工）" % (SKILL_ROOT / row[3]))
    if sid == cur:
        print("  启发式推断: %s（%s）— 与已进入阶段一致" % (sid, why))
    else:
        print("  启发式推断: %s（%s）— 与已进入阶段不一致；"
              "如当前环节已收口：stage enter %s" % (sid, why, sid))
    if proj.config.get("route", "web") == "traditional" and cur != "diag":
        print("  叠加差分: trad → %s" % (SKILL_ROOT / "protocol/stages/trad-overlay.md"))
    return 0
