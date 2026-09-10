# -*- coding: utf-8 -*-
"""cli — argparse 装配与子命令分发（tools/novel.py 薄壳的唯一入口）。"""
import argparse

from .common import RETCON_STRATEGIES, REVIEW_DEPTHS, REVIEW_VERDICTS
from .bootstrap import cmd_adopt, cmd_init
from .brief import cmd_brief
from .checks import check_project, cmd_check
from .commitflow import cmd_commit
from .court import cmd_court
from .consult import cmd_consult
from .extract import cmd_extract
from .gate import cmd_gate
from .journal import cmd_entity, cmd_facts, cmd_ledger, cmd_thread
from .knowledge import cmd_knowledge
from .project import Project, find_root
from .review import cmd_review
from .rollup import cmd_rollup
from .serial_ops import cmd_checkpoint, cmd_publish, cmd_report, cmd_retcon
from .stagectl import cmd_stage
from .status import cmd_status
from .structure import cmd_task, cmd_tree
from .transactions import cmd_recover, execute


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
    p = sub.add_parser("recover", help="列出未完成事务；按前镜像安全回退")
    p.add_argument("--rollback", action="store_true")

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
    q.add_argument("--issue", "--note", dest="issue", action="append", help="评审摘要（--note 为兼容别名）")
    q.add_argument("--evidence", help="review checklist 产生并经评审逐项填写的 JSON 文件")
    q.add_argument("--lesson", help="教训一行（可选，编排者摘入 lessons）")
    ts.add_parser("list")
    q = ts.add_parser("checklist", help="输出未裁定的结构化评审清单；不会自动通过")
    q.add_argument("ch_id")

    p = sub.add_parser("knowledge",
                       help="知识矩阵 v2（fact×角色/范围×读者）：grant/reveal/scope/query")
    ts = p.add_subparsers(dest="knowledge_cmd", required=True)
    q = ts.add_parser("grant", help="授予知情（known_by 追加；个体 char 或 fac/loc/item 范围）")
    q.add_argument("fact_id")
    q.add_argument("--to", action="append", required=True,
                   help="知情实体（可多次；char 个体或 fac/loc/item 群体，须已登记）")
    q.add_argument("--ch", help="获知场景章号（必填，保存不可变知情快照）")
    q = ts.add_parser("reveal", help="读者揭示：spoiler 1→0（悬念销账）")
    q.add_argument("fact_id")
    q.add_argument("--ch", required=True, help="揭示章号（记 revealed_reader_ch）")
    q = ts.add_parser("scope", help="知情圈维护：add/remove/list（fac/loc/item → char 成员）")
    tss = q.add_subparsers(dest="scope_cmd", required=True)
    for name in ("add", "remove"):
        w = tss.add_parser(name)
        w.add_argument("group", help="fac_/loc_/item_ 群体实体 id")
        w.add_argument("members", nargs="+", metavar="CHAR", help="char_ 成员（可多个）")
    w = tss.add_parser("list")
    w.add_argument("group", nargs="?", help="只看某群体（缺省列全部）")
    q = ts.add_parser("query", help="矩阵视图：--fact/--entity（个体或群体）/默认盘点读者未知欠账")
    q.add_argument("--fact", dest="fact_id")
    q.add_argument("--entity")
    q.add_argument("--at", help="截至此章的知识视图（包含该章）")

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

    p = sub.add_parser("stage", help="阶段状态机：list/show <id>/enter <id>/current"
                                     "（持久化阶段 = 各环节闸门的钥匙）")
    ss = p.add_subparsers(dest="stage_cmd", required=True)
    ss.add_parser("list", help="阶段总表（id+定位+包路径）")
    q = ss.add_parser("show", help="打印某阶段配套知识包全文")
    q.add_argument("stage_id")
    q = ss.add_parser("enter", help="进入阶段（写 state/stage.json；受辖操作的前提）")
    q.add_argument("stage_id")
    ss.add_parser("current", help="读持久化阶段 + 启发式核对（未进入任何阶段时 exit 1）")

    q = ss.add_parser("consult", help="按症状跨阶段借阅 1–2 个知识块并留痕")
    q.add_argument("ids", nargs="+")
    q.add_argument("--reason", required=True)
    q.add_argument("--target", required=True)

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
        "stage": cmd_consult if args.cmd == "stage" and args.stage_cmd == "consult" else cmd_stage, "recover": cmd_recover,
        "fsck": lambda a: check_project(Project(find_root(a))).render("fsck"),
    }
    try:
        if args.cmd in ("init", "recover", "fsck", "check", "extract", "ledger", "gate") \
                or (args.cmd == "stage" and args.stage_cmd not in ("enter", "consult")):
            return dispatch[args.cmd](args)
        return execute(find_root(args), args.cmd, lambda: dispatch[args.cmd](args))
    except (ValueError, OSError, RuntimeError) as exc:
        from .common import die
        die(str(exc), 1)
