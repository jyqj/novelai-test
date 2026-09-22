# -*- coding: utf-8 -*-
"""court — 庭审工作区 CLI（P3-2）：open 建场次目录+R0 骨架；status 盘点回合产物；
close 校验裁决落盘后清理中间态（court.md §3 约定的机械半边）。"""
import re

from .common import die, git_autocommit, write, remove
from .project import Project, find_root
from .stagectl import stage_guard


def session_stage_allowed(session):
    """场次代号 → 所属阶段（P7-S court open 闸门）：S1..S4 → s1..s4；
    vol_* → vol；arc_* → arc；adhoc 等自由场次只要求已进入某阶段（None）。"""
    if session in ("S1", "S2", "S3", "S4"):
        return (session.lower(),)
    if session.startswith("vol"):
        return ("vol",)
    if session.startswith("arc"):
        return ("arc",)
    return None


def cmd_court(args):
    """庭审工作区 CLI 化：open 建场次目录+R0 骨架；status 盘点回合产物；
    close 校验裁决落盘后清理中间态（court.md §3 约定的机械半边）。"""
    proj = Project(find_root(args))
    base = proj.p("state", "court")
    session = getattr(args, "session", None)
    if session is not None and not re.fullmatch(r"[A-Za-z0-9_-]+", session):
        die("非法场次 id", 1)
    if args.court_cmd == "open":
        stage_guard(proj, session_stage_allowed(args.session),
                    "court open %s" % args.session)
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
        if not base.is_dir() or not any(f.is_file() for f in base.rglob("*")):
            print("（无进行中场次）")
        for d in sorted(base.iterdir()) if base.is_dir() else []:
            if not d.is_dir() or not any(f.is_file() for f in d.rglob("*")):
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
    for child in d.rglob("*"):
        if child.is_file():
            remove(child)
    git_autocommit(proj.root, "[court] close %s（dec=%s）"
                   % (args.session, " ".join(args.dec)))
    print("场次已清：state/court/%s（裁决 %s 已确认落盘）"
          % (args.session, " ".join(args.dec)))
    print("[提醒] transcript 归档 court/transcripts/（若尚未）；复盘走 dec + git log")
    return 0
