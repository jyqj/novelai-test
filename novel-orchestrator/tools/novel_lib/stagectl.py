# -*- coding: utf-8 -*-
"""stagectl — 阶段目录 + 阶段导航（P6-S）：list/show/current 与启发式推断。"""
from .common import SKILL_ROOT, die, read
from .project import Project, find_root, load_queue_promoted, next_task_id

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
