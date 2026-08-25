#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""阶段×知识编排专项测试（P6-S，stdlib only）。

覆盖两半：
  一、文档契约（knowledge-orchestration.md §4 对账规则的机检半边）
     D1 阶段包齐全且每包 ≤80 行（薄路由纪律）
     D2 设计阶段包 K 池 ≡ knowledge-map 场次标注（含 S4/卷庭双标）
     D3 产线/运营/差分/诊断五包正文零 K-ID（零知识装载的文字面保证）
     D4 rubrics 卡脚注 K-ID 集 ≡ knowledge-map「蒸馏」列（全 ID 逐个列出）
     D5 knowledge-map 111 行 ≡ knowledge/ 锚点集（无死块、无幽灵锚）
     D6 阶段包与 orchestration 引用的 skill 侧路径全部存在（死链扫描）
  二、stage CLI 与 gate next（P6-S 机器半边）
     C1 stage list/show 全阶段可用；未知 id 拒绝
     C2 stage current 阶段推断：s1（book 未 commit）→ 庭审工作区优先（S2/S4）→
        vol/arc 设计缺口 → 队首任务类型映射（review_deep→review、publish→ops）→ write 默认
     C3 gate next 末行附阶段推断与配套包路径
     C4 spoiler 欠账消费：挂账超龄顶出【欠账】项；未超龄不出现

运行：python3 tools/tests/test_stage.py
"""
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

TOOLS = Path(__file__).resolve().parent.parent
NOVEL = TOOLS / "novel.py"
SKILL = TOOLS.parent
STEP = [0]

STAGE_FILES = {
    "s1": "s1-concept.md", "s2": "s2-world.md", "s3": "s3-cast.md",
    "s4": "s4-volumes.md", "vol": "vol-court.md", "arc": "arc-plan.md",
    "write": "write-loop.md", "review": "review-cycle.md", "ops": "ops-serial.md",
    "trad": "trad-overlay.md", "diag": "diagnose.md",
}
KID_RE = re.compile(r"K-[A-Z]+-\d{3}")


def run(args, cwd, expect=0):
    r = subprocess.run([sys.executable, str(NOVEL)] + args,
                       cwd=str(cwd), capture_output=True, text=True)
    if r.returncode != expect:
        print("FAILED: novel.py %s\nexit=%d (期望 %d)\n--- stdout ---\n%s\n--- stderr ---\n%s"
              % (" ".join(args), r.returncode, expect, r.stdout, r.stderr))
        sys.exit(1)
    STEP[0] += 1
    print("OK %02d: novel.py %s (exit=%d)" % (STEP[0], " ".join(args[:4]), r.returncode))
    return r.stdout + r.stderr


def must(cond, msg):
    if not cond:
        print("FAILED 断言: " + msg)
        sys.exit(1)
    STEP[0] += 1
    print("OK %02d: %s" % (STEP[0], msg))


def map_rows():
    txt = (SKILL / "knowledge-map.md").read_text(encoding="utf-8")
    return re.findall(r"^\| (K-[A-Z]+-\d{3}) \| [^|]+ \| ([^|]+) \|", txt, re.M)


def staged_node(node_id, kind, sections, parent=None):
    fm = ["---", "id: %s" % node_id, "kind: %s" % kind, "status: draft", "rev: 1"]
    if parent:
        fm.append("parent: %s" % parent)
    fm += ["updated_at: 2026-08-25T00:00:00", "---", ""]
    body = "\n\n".join("## %s\n\n（测试占位内容·%s）" % (s, s) for s in sections)
    return "\n".join(fm) + "\n" + body + "\n"


SECTIONS = {
    "book": ["主旨与主控思想", "高概念与题材定位", "世界观核心", "金手指与力量体系",
             "主线电缆", "人物主阵容", "反派梯队", "分卷草案", "红线自查结论"],
    "volume": ["卷主旨与价值走向", "卷级冲突结构", "弧划分表", "imports", "exports",
               "阵容变化", "力量与资源预算", "爽点大节奏", "红线与毒点自查结论"],
    "arc": ["弧目标与节奏模板", "因果链", "章分配草案", "线索操作计划",
            "爽点与期待操作表", "出场实体清单"],
}


def doc_contract():
    print("---- 一、文档契约 ----")
    stages_dir = SKILL / "protocol" / "stages"
    # D1 包齐全且 ≤80 行
    for sid, fn in STAGE_FILES.items():
        p = stages_dir / fn
        must(p.is_file(), "D1 阶段包存在：%s" % fn)
        n = len(p.read_text(encoding="utf-8").splitlines())
        must(n <= 80, "D1 %s ≤80 行（实测 %d）" % (fn, n))
    extra = {f.name for f in stages_dir.glob("*.md")} - set(STAGE_FILES.values())
    must(not extra, "D1 stages/ 无目录外文件（发现 %s）" % (extra or "无"))

    # D2 设计阶段 K 池对账（map 场次标注 → 期望池）
    rows = map_rows()
    must(len(rows) == 111, "D5 knowledge-map 111 行（实测 %d）" % len(rows))
    pool = {"s1": set(), "s2": set(), "s3": set(), "s4": set(), "vol": set(), "arc": set()}
    for kid, belong in rows:
        b = belong.strip()
        if not b.startswith("庭审附件"):
            continue
        tag = b.split("·", 1)[1]
        if tag == "S1":
            pool["s1"].add(kid)
        elif tag == "S2":
            pool["s2"].add(kid)
        elif tag == "S3":
            pool["s3"].add(kid)
        elif tag == "S4":
            pool["s4"].add(kid)
        elif tag == "S4/卷庭":
            pool["s4"].add(kid)
            pool["vol"].add(kid)
        elif tag == "卷庭":
            pool["vol"].add(kid)
        elif tag == "弧/细纲":
            pool["arc"].add(kid)
        else:
            must(False, "D2 未知场次标注：%s（%s）" % (tag, kid))
    for sid in ("s1", "s2", "s3", "s4", "vol", "arc"):
        got = set(KID_RE.findall((stages_dir / STAGE_FILES[sid]).read_text(encoding="utf-8")))
        must(got == pool[sid],
             "D2 %s K 池 ≡ map 场次标注（%d 块；差异 %s）"
             % (sid, len(pool[sid]), sorted(got ^ pool[sid]) or "无"))

    # D3 五个零装载包正文无 K-ID
    for sid in ("write", "review", "ops", "trad", "diag"):
        got = KID_RE.findall((stages_dir / STAGE_FILES[sid]).read_text(encoding="utf-8"))
        must(not got, "D3 %s 包零 K-ID（发现 %s）" % (sid, got or "无"))

    # D4 rubrics 脚注 ≡ 蒸馏列
    distilled = {k for k, b in rows if "蒸馏" in b}
    found = set()
    for f in (SKILL / "rubrics").glob("*.md"):
        found |= set(KID_RE.findall(f.read_text(encoding="utf-8")))
    must(found == distilled,
         "D4 rubrics 脚注 K-ID ≡ map 蒸馏列（%d 块；差异 %s）"
         % (len(distilled), sorted(found ^ distilled) or "无"))

    # D5 map ↔ knowledge/ 锚点双向一致
    anchors = set()
    for f in (SKILL / "knowledge").rglob("*.md"):
        anchors |= set(re.findall(r"<!-- (K-[A-Z]+-\d{3}) -->", f.read_text(encoding="utf-8")))
    allk = {k for k, _ in rows}
    must(anchors == allk, "D5 knowledge/ 锚点 ≡ map 行（差异 %s）"
         % (sorted(anchors ^ allk) or "无"))

    # D6 引用死链扫描（stages/ 包 + orchestration 内的 skill 侧路径）
    path_re = re.compile(
        r"\b((?:protocol|rubrics|roles|templates|personas|rhythm|modes)/"
        r"[A-Za-z0-9._/\-]+\.(?:md|json|py))\b")
    scan = list(stages_dir.glob("*.md")) + [SKILL / "protocol" / "knowledge-orchestration.md"]
    dead = []
    for f in scan:
        for ref in set(path_re.findall(f.read_text(encoding="utf-8"))):
            if not (SKILL / ref).is_file():
                dead.append("%s → %s" % (f.name, ref))
    must(not dead, "D6 阶段包/编排 SSOT 引用零死链（发现 %s）" % (dead or "无"))


def cli_half():
    print("---- 二、stage CLI 与 gate next ----")
    out = run(["stage", "list"], cwd=SKILL)
    for sid in STAGE_FILES:
        must(("\n%s " % sid) in ("\n" + out), "C1 stage list 含 %s" % sid)
    must("knowledge-orchestration" in out, "C1 stage list 指向编排 SSOT")
    out = run(["stage", "show", "s3"], cwd=SKILL)
    must("K-CONFLICT-006" in out and "s3-cast.md" in out, "C1 stage show s3 打印包全文+路径")
    for sid in STAGE_FILES:
        run(["stage", "show", sid], cwd=SKILL)
    run(["stage", "show", "bogus"], cwd=SKILL, expect=2)

    tmp = Path(tempfile.mkdtemp(prefix="novel_stage_"))
    try:
        proj = tmp / "book_s"
        run(["init", str(proj), "--name", "阶段之书"], cwd=tmp)

        # C2a book 未 committed → s1
        out = run(["stage", "current"], cwd=proj)
        must("推断: s1" in out and "s1-concept.md" in out, "C2 空项目推断 s1")

        # C2b 庭审工作区优先（最深场次）
        run(["court", "open", "S2", "--node", "world"], cwd=proj)
        out = run(["stage", "current"], cwd=proj)
        must("推断: s2" in out, "C2 进行中场次 S2 → s2")
        run(["court", "open", "S4", "--node", "book"], cwd=proj)
        out = run(["stage", "current"], cwd=proj)
        must("推断: s4" in out, "C2 多场并存取最深 → s4")
        shutil.rmtree(proj / "state" / "court")

        # C2c 设计缺口链：book committed → vol；vol committed → arc；arc committed → write
        t = run(["task", "add", "design", "book"], cwd=proj).strip().splitlines()[-1]
        staged = tmp / "book.md"
        staged.write_text(staged_node("book", "book", SECTIONS["book"]), encoding="utf-8")
        run(["commit", t, "--file", str(staged), "-m", "书定稿"], cwd=proj)
        run(["task", "done", t], cwd=proj)
        out = run(["stage", "current"], cwd=proj)
        must("推断: vol" in out and "vol-court.md" in out, "C2 book 已 commit → vol")

        run(["tree", "add", "volume", "vol_01"], cwd=proj)
        t = run(["task", "add", "design", "vol_01"], cwd=proj).strip().splitlines()[-1]
        staged = tmp / "vol.md"
        staged.write_text(staged_node("vol_01", "volume", SECTIONS["volume"], "book"),
                          encoding="utf-8")
        run(["commit", t, "--file", str(staged), "-m", "卷定稿"], cwd=proj)
        run(["task", "done", t], cwd=proj)
        out = run(["stage", "current"], cwd=proj)
        must("推断: arc" in out, "C2 卷已 commit → arc")

        run(["tree", "add", "arc", "arc_01_1"], cwd=proj)
        t = run(["task", "add", "design", "arc_01_1"], cwd=proj).strip().splitlines()[-1]
        staged = tmp / "arc.md"
        staged.write_text(staged_node("arc_01_1", "arc", SECTIONS["arc"], "vol_01"),
                          encoding="utf-8")
        run(["commit", t, "--file", str(staged), "-m", "弧定稿"], cwd=proj)
        run(["task", "done", t], cwd=proj)
        out = run(["stage", "current"], cwd=proj)
        must("推断: write" in out and "write-loop.md" in out, "C2 设计齐备队列空 → write")

        # C2d 队首任务类型映射
        t_r = run(["task", "add", "review_deep", "ch_0001"], cwd=proj).strip().splitlines()[-1]
        out = run(["stage", "current"], cwd=proj)
        must("推断: review" in out, "C2 队首 review_deep → review")
        run(["task", "done", t_r], cwd=proj)

        # C2e traditional 叠加提示
        cfg_p = proj / "config.json"
        cfg = json.loads(cfg_p.read_text(encoding="utf-8"))
        cfg["route"] = "traditional"
        cfg_p.write_text(json.dumps(cfg, ensure_ascii=False, indent=1), encoding="utf-8")
        out = run(["stage", "current"], cwd=proj)
        must("trad-overlay.md" in out, "C2 route=traditional 提示叠加 trad 包")
        cfg["route"] = "web"
        cfg_p.write_text(json.dumps(cfg, ensure_ascii=False, indent=1), encoding="utf-8")

        # C3 gate next 附阶段推断
        out = run(["gate", "next"], cwd=proj)
        must("当前阶段推断" in out and "配套知识包" in out, "C3 gate next 末行附阶段+包路径")

        # C4 spoiler 欠账：手植一条未揭示 fact；阈值 0 → 顶出；默认 15 → 不出现
        facts_p = proj / "ledgers" / "facts" / "vol_01.json"
        facts_p.parent.mkdir(parents=True, exist_ok=True)
        facts_p.write_text(json.dumps({"facts": [{
            "id": "fact_000001", "fact": "匣中信物是师门遗物", "entity_ids": [],
            "key": "知晓", "spoiler": 1, "revealed_ch": 0}]}, ensure_ascii=False),
            encoding="utf-8")
        out = run(["gate", "next"], cwd=proj)
        must("【欠账】" not in out, "C4 未超龄（默认阈值 15）不出欠账项")
        cfg["spoiler_debt_chapters"] = 0
        cfg_p.write_text(json.dumps(cfg, ensure_ascii=False, indent=1), encoding="utf-8")
        out = run(["gate", "next"], cwd=proj)
        must("【欠账】" in out and "fact_000001" in out, "C4 超龄挂账顶出【欠账】项")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main():
    doc_contract()
    cli_half()
    print("\n全部通过：%d 步（文档契约对账 + stage CLI + gate next 欠账/阶段推断）" % STEP[0])


if __name__ == "__main__":
    main()
