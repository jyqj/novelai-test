#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""novel.py 端到端冒烟测试（stdlib only，无第三方依赖）。

覆盖绿路径 + 每个机检闸门至少一条负例：
  init 脚手架（含 power/recap/compliance/state/court）
  → design 负例（缺节拒绝）/ --draft 部分落盘（P0-6）/ 正式 commit
  → brief（recap 注入 P1-1、volume_scope/payoff 临近召回 P1-4、§8 power_delta）
  → check --unit 正例 + 负例（黑名单/cast 越权/thread 越权/payoff 章号/缺 spoiler/迁移非法）
  → commit（facts 登记 P0-1、plant_ch 回填 P1-3、power 台账 P1-6）
  → facts 冲突 NEEDS_REVIEW（P0-1）
  → retcon CLI（P0-4）正例 + 3 条负例
  → 队列：blocked 自动解锁（P0-2）、task reset 正/负例
  → set-status approved 回执闸门（P1-5）正/负例
  → publish 正例 + 跳章负例
  → report volume / checkpoint（P0-4）正例 + 待对账负例、下卷 imports 预填
  → check --leak（P0-3 后半）正/负例
  → adopt（P1-9）+ 跨章 12-gram 告警（P1-8）
  → task archive（P1-8）、status 扩展 dashboard（P2-2）、check --window --since
  → check --project 对 decision/review 的机检（P1-2）正/负例

运行：python3 tools/tests/test_smoke.py
成功：打印各步骤 OK 与最终 SMOKE PASS，退出码 0。
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

STEP = [0]


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


CHAPTER_TEXT = """林晚把伞收进门后的陶瓮，雨水顺着伞骨敲出细碎的声响。
柜台后的老人抬起头，浑浊的目光落在她腰间的铜牌上。
「三十年了，」老人说，「拿这块牌子进门的人，你是第二个。」
她的指尖抚过铜牌边缘的缺口。第一个人是她师父，坟头的草已经割过七茬。
老人从柜底取出一只黑木匣，推过来时压低了嗓音：「钥匙在城南，看好你身后。」
门外的雨声忽然停了。
林晚没有回头，先把木匣塞进怀里，才按住了刀柄。
巷口的灯笼在积水里晃出一圈黄晕，两名戴斗笠的汉子立在檐下，草鞋边缘干干净净。
下过整夜雨的街面，不该有干着的鞋。
她拐进米铺后巷，翻上矮墙，身后传来碎瓷般的脚步声。"""

CANDIDATE = """---
id: ch_0001
kind: chapter
status: drafted
rev: 1
parent: arc_01_1
updated_at: 2026-08-24T00:00:00
title: 雨夜取匣
word_count: 0
---

## 正文

%s
""" % CHAPTER_TEXT

WRITEBACK = {
    "summary_after": "林晚凭师父遗留的铜牌从当铺老人手中取得黑木匣，得知钥匙在城南；"
                     "离开时发现两名可疑汉子盯梢，翻墙撤离时被人跟上。",
    "continuity_delta": [{"fact": "林晚取得黑木匣，得知钥匙藏在城南",
                          "entity_ids": ["char_linwan"], "spoiler": 0, "key": "持有"}],
    "time_advance": {"elapsed": "1晚", "story_date": ""},
    "thread_ops": [{"id": "thread_heimuxia", "op": "plant", "note": "木匣线索埋设"},
                   {"id": "thread_heimuxia", "op": "advance",
                    "note": "木匣到手，钥匙位置揭示"}],
    "payoff_realized": ["payoff_0001_1"],
    "hooks_realized": {"open": True, "close": True},
    "cast_actual": ["char_linwan"],
    "power_delta": [{"entity_ids": ["char_linwan"], "from": "持牌孤徒",
                     "to": "入局者", "note": "身份跃迁"}],
    "issues": [],
    "word_count": 330,
}

TASK_JSON = {
    "id": "ch_0001", "arc": "arc_01_1",
    "goal": "林晚取得黑木匣并暴露于追踪者视野",
    "beats": ["当铺验牌", "取匣与警告", "巷口发现盯梢"],
    "hook": {"open": None, "close": "身后传来脚步声"},
    "payoff_quota": [{"kind": "dopamine", "intent": "铜牌身份被认出，老人破例交匣"}],
    "threads": [{"id": "thread_heimuxia", "op": "advance"}],
    "cast": ["char_linwan"],
    "word_target": [300, 800],
}

ARC_STAGED = """---
id: arc_01_1
kind: arc
status: draft
rev: 1
parent: vol_01
updated_at: 2026-08-24T00:00:00
---

## 弧目标与节奏模板

弧目标：林晚从「持牌孤徒」到「入局者」。模板 wave（波浪推进），高峰间隔 3 章。

## 因果链

铜牌验明身份 → 取得黑木匣 → 盯梢暴露 → 城南寻钥 → 与守钥人冲突。

## 章分配草案

| 章 | 因果拍 | 钩 |
|---|---|---|
| ch_0001 | 取匣+盯梢暴露 | 身后脚步声 |
| ch_0002 | 甩尾+验匣 | 匣内无钥只有名单 |

## 线索操作计划

- thread_heimuxia: ch_0001 plant+advance；ch_0002 tangle（匣内并无钥匙）。

## 爽点与期待操作表

| 章 | kind | intent |
|---|---|---|
| ch_0001 | dopamine | 铜牌身份被认出，老人破例交匣 |

## 出场实体清单

- char_linwan（主）；当铺老人（暂不建卡，出场 <3 章）。
"""

ARC_PARTIAL = """---
id: arc_01_1
kind: arc
status: draft
rev: 1
parent: vol_01
updated_at: 2026-08-24T00:00:00
---

## 弧目标与节奏模板

只有一节的半成品（书庭/弧中间态）。
"""

VOLUME_STAGED = """---
id: vol_01
kind: volume
status: draft
rev: 1
parent: book
updated_at: 2026-08-24T00:00:00
---

## 卷主旨与价值走向

从孤徒到入局者：安全感 → 卷入漩涡。

## 卷级冲突结构

主对手：守钥人集团；压力源：铜牌来历；终局：名单公开，林晚成为各方争夺焦点。

## 弧划分表

| arc_id | 章数预算 | 一句话目标 | 节奏模板 |
|---|---|---|---|
| arc_01_1 | 2 | 取匣入局 | wave |

## imports

- （首卷无继承）

## exports

- 名单到手但钥匙下落成谜（移交下卷主线）
- 林晚身份为守钥人集团知晓

## 阵容变化

- 新增 | char_linwan | 主角入场

## 力量与资源预算

- 位阶起止: 持牌孤徒 → 入局者
- 金手指配额: 无
- 关键资源: 黑木匣（获得）

## 爽点大节奏

- ch_0001 | dopamine | 铜牌身份被认出

## 红线与毒点自查结论

安全审查通过：无红线项。
"""

DEC_GOOD = """---
id: dec_001_matter
kind: decision
node: vol_01
session: adhoc
date: 2026-08-24
status: active
---

## 选项

- A | 架构师 | 维持木匣设定，新事实向前覆盖

## 裁决

选 A：published 章不回改，走 retcon 向前兼容。

## 否决案

- B | 重写旧章成本高且违反不可变纪律 | reopen_requires: 读者大规模误读的定量证据

## 异议

- 结构评审 | 倾向 B | resolution: disagree_and_commit
"""

DEC_BAD = """---
id: dec_002_bad
kind: decision
node: vol_01
date: 2026-08-24
status: active
---

## 选项

- A | 架构师 | 某案

## 裁决

选 A。

## 否决案

- B | 否了但没写重开条件
"""

REVIEW_PASS = """---
id: review_ch_0001_light
kind: review
chapter: ch_0001
depth: light
verdict: pass
rev_reviewed: 1
date: 2026-08-24
---

## 问题清单

- [全章] 无阻塞问题 → 通过
"""


def wb_variant(**kw):
    wb = json.loads(json.dumps(WRITEBACK))
    wb.update(kw)
    return wb


def main():
    tmp = Path(tempfile.mkdtemp(prefix="novel_smoke_"))
    try:
        proj = tmp / "book1"
        run(["init", str(proj), "--name", "冒烟之书"], cwd=tmp)
        must((proj / "config.json").is_file() and (proj / "tree/book.md").is_file(),
             "脚手架目录/config/树节点存在")
        must((proj / "ledgers/power.tsv").is_file()
             and (proj / "ledgers/recap.md").is_file()
             and (proj / "data/compliance").is_dir()
             and (proj / "state/court").is_dir()
             and (proj / "state/reports").is_dir(),
             "P1-6/P1-1/P2-8/P0-6 脚手架：power/recap/compliance/state.court/state.reports")
        must("models" not in json.loads((proj / "config.json").read_text(encoding="utf-8")),
             "P2-7 config 无 models 死键")

        run(["tree", "add", "volume", "vol_01"], cwd=proj)
        run(["tree", "add", "arc", "arc_01_1"], cwd=proj)
        run(["tree", "add", "chapter", "ch_0001", "--parent", "arc_01_1"], cwd=proj)
        run(["entity", "new", "char_linwan"], cwd=proj)
        run(["thread", "new", "thread_heimuxia", "--kind", "mystery"], cwd=proj)
        run(["thread", "new", "thread_side", "--kind", "subplot"], cwd=proj)
        # 编排者附笔：别名 + 侧线 volume_scope（P1-4 召回用）
        (proj / "entities/aliases.json").write_text(
            json.dumps({"林晚": "char_linwan"}, ensure_ascii=False), encoding="utf-8")
        side = (proj / "threads/thread_side.md").read_text(encoding="utf-8")
        side = side.replace("volume_scope: []", 'volume_scope: ["vol_01"]')
        (proj / "threads/thread_side.md").write_text(side, encoding="utf-8")
        # recap 附笔（P1-1）
        with open(proj / "ledgers/recap.md", "a", encoding="utf-8") as f:
            f.write("\n- 全书至此：林晚持师父铜牌初入江湖。\n")

        # 排批：填章任务卡
        (proj / "chapters/ch_0001.task.json").write_text(
            json.dumps(TASK_JSON, ensure_ascii=False, indent=1), encoding="utf-8")

        # ---- P0-6：design 缺节拒绝（负例）与 --draft 部分落盘（正例）
        tid = run(["task", "add", "design", "arc_01_1"], cwd=proj).strip().splitlines()[-1]
        partial = tmp / "arc_partial.md"
        partial.write_text(ARC_PARTIAL, encoding="utf-8")
        run(["commit", tid, "--file", str(partial), "-m", "缺节应拒"], cwd=proj, expect=1)
        run(["commit", tid, "--file", str(partial), "--draft", "-m", "中间态部分落盘"],
            cwd=proj)
        must("status: draft" in (proj / "tree/vol_01/arc_01_1.md").read_text(encoding="utf-8"),
             "P0-6 --draft 部分落盘为 draft 态")
        staged = tmp / "arc_staged.md"
        staged.write_text(ARC_STAGED, encoding="utf-8")
        run(["commit", tid, "--file", str(staged), "-m", "弧设计过庭"], cwd=proj)
        out = run(["tree", "show"], cwd=proj)
        must("arc_01_1" in out and "committed" in out, "弧节点已 committed")

        # 写章任务 + 简报
        tid2 = run(["task", "add", "write", "ch_0001"], cwd=proj).strip().splitlines()[-1]
        run(["task", "start", tid2], cwd=proj)
        run(["brief", "ch_0001"], cwd=proj)
        brief = (proj / "briefs/ch_0001.brief.md").read_text(encoding="utf-8")
        must(all(s in brief for s in
                 ("## 0 任务卡", "## 3 出场实体状态卡", "## 8 回写契约", "## 附 溯源")),
             "十节简报关键节齐全")
        must("全局 recap" in brief and "铜牌初入江湖" in brief, "P1-1 recap 注入简报 §2")
        must("thread_side" in brief, "P1-4 volume_scope 命中线索入简报 §4")
        must("power_delta" in brief, "简报 §8 含 power_delta 契约")

        # 候选章 + writeback：机检绿
        cand = tmp / "ch_0001.candidate.md"
        cand.write_text(CANDIDATE, encoding="utf-8")
        wb = tmp / "ch_0001.writeback.json"
        wb.write_text(json.dumps(WRITEBACK, ensure_ascii=False, indent=1), encoding="utf-8")
        run(["check", "--unit", "ch_0001", "--candidate", str(cand),
             "--writeback", str(wb)], cwd=proj)

        # ---- 负例矩阵
        bad = tmp / "ch_0001.bad.md"
        bad.write_text(CANDIDATE.replace(
            "门外的雨声忽然停了。",
            "门外的雨声忽然停了。他嘴角勾起一抹弧度，眸中精光一闪。"), encoding="utf-8")
        run(["check", "--unit", "ch_0001", "--candidate", str(bad),
             "--writeback", str(wb)], cwd=proj, expect=1)  # 黑名单

        wb_ghost_cast = tmp / "wb_ghost_cast.json"
        wb_ghost_cast.write_text(json.dumps(
            wb_variant(cast_actual=["char_linwan", "char_ghost"]),
            ensure_ascii=False), encoding="utf-8")
        run(["check", "--unit", "ch_0001", "--candidate", str(cand),
             "--writeback", str(wb_ghost_cast)], cwd=proj, expect=1)  # P0-3 cast 越权

        wb_ghost_thread = tmp / "wb_ghost_thread.json"
        wb_ghost_thread.write_text(json.dumps(
            wb_variant(thread_ops=[{"id": "thread_ghost", "op": "advance", "note": "x"}]),
            ensure_ascii=False), encoding="utf-8")
        run(["check", "--unit", "ch_0001", "--candidate", str(cand),
             "--writeback", str(wb_ghost_thread)], cwd=proj, expect=1)  # P0-3 thread 越权

        wb_bad_payoff = tmp / "wb_bad_payoff.json"
        wb_bad_payoff.write_text(json.dumps(
            wb_variant(payoff_realized=["payoff_0002_1"]),
            ensure_ascii=False), encoding="utf-8")
        run(["check", "--unit", "ch_0001", "--candidate", str(cand),
             "--writeback", str(wb_bad_payoff)], cwd=proj, expect=1)  # P2-1 章号不符

        wb_no_spoiler = tmp / "wb_no_spoiler.json"
        wb_no_spoiler.write_text(json.dumps(
            wb_variant(continuity_delta=[{"fact": "某事实",
                                          "entity_ids": ["char_linwan"]}]),
            ensure_ascii=False), encoding="utf-8")
        run(["check", "--unit", "ch_0001", "--candidate", str(cand),
             "--writeback", str(wb_no_spoiler)], cwd=proj, expect=1)  # P0-1 缺 spoiler

        wb_bad_ops = tmp / "wb_bad_ops.json"
        wb_bad_ops.write_text(json.dumps(
            wb_variant(thread_ops=[{"id": "thread_heimuxia", "op": "payoff", "note": "收"},
                                   {"id": "thread_heimuxia", "op": "advance", "note": "又推"}]),
            ensure_ascii=False), encoding="utf-8")
        run(["check", "--unit", "ch_0001", "--candidate", str(cand),
             "--writeback", str(wb_bad_ops)], cwd=proj, expect=1)  # P1-3 终态后非法迁移

        # commit：落盘 + 回写实体/线索/facts/台账
        run(["commit", tid2, "--chapter", str(cand), "--writeback", str(wb),
             "-m", "首章成稿"], cwd=proj)
        ch = (proj / "chapters/ch_0001.md").read_text(encoding="utf-8")
        must("status: drafted" in ch, "章状态 drafted")
        ent = (proj / "entities/char_linwan.md").read_text(encoding="utf-8")
        must("- ch_0001:" in ent, "实体事件日志已回写")
        th = (proj / "threads/thread_heimuxia.md").read_text(encoding="utf-8")
        must("state: active" in th and "- ch_0001: advance" in th, "线索推进已回写")
        must("plant_ch: 1" in th, "P1-3 plant 回填 plant_ch")
        facts_p = proj / "ledgers/facts/vol_01.json"
        must(facts_p.is_file(), "P0-1 facts 文件已生成")
        facts = json.loads(facts_p.read_text(encoding="utf-8"))
        must(facts["facts"] and facts["facts"][0]["id"] == "fact_0001"
             and facts["facts"][0]["revealed_ch"] == 1
             and facts["facts"][0].get("key") == "持有",
             "P0-1 fact_0001 自动分配（含 key/revealed_ch）")
        payoff = (proj / "ledgers/payoff.tsv").read_text(encoding="utf-8")
        must("payoff_0001_1" in payoff and "\t1" in payoff, "爽点台账已登记 realized=1")
        power = (proj / "ledgers/power.tsv").read_text(encoding="utf-8")
        must("ch_0001\tchar_linwan\t持牌孤徒\t入局者" in power, "P1-6 power 台账已追加")

        # ---- P1-5 approved 回执闸门：无回执拒绝 → 回执后通过
        run(["tree", "set-status", "ch_0001", "approved"], cwd=proj, expect=1)
        (proj / "reviews/ch_0001.light.md").write_text(REVIEW_PASS, encoding="utf-8")
        run(["task", "done", tid2, "--note", "light=pass"], cwd=proj)
        run(["tree", "set-status", "ch_0001", "approved"], cwd=proj)
        must("approved_evidence" in
             (proj / "chapters/ch_0001.md").read_text(encoding="utf-8"),
             "P1-5 approved 回执已记录")

        # 窗口/全库检查 + 发布
        run(["check", "--window"], cwd=proj)
        run(["check", "--project"], cwd=proj)
        run(["publish", "ch_0001"], cwd=proj)
        out = run(["status"], cwd=proj)
        must("last_published=1" in out, "游标 last_published=1")
        must("树进度表" in out and "告警" in out and "深评游标" in out,
             "P2-2/P1-10 dashboard 扩展节齐全")
        run(["publish", "ch_0003"], cwd=proj, expect=1)  # 负例：跳章发布

        # ---- ch_0002：facts 召回 + 冲突扫描
        run(["tree", "add", "chapter", "ch_0002", "--parent", "arc_01_1"], cwd=proj)
        task2 = dict(TASK_JSON, id="ch_0002",
                     goal="验匣", beats=["甩尾", "开匣", "名单现世"],
                     payoff_quota=[{"kind": "reveal", "intent": "匣内无钥只有名单"}])
        (proj / "chapters/ch_0002.task.json").write_text(
            json.dumps(task2, ensure_ascii=False, indent=1), encoding="utf-8")
        run(["brief", "ch_0002"], cwd=proj)
        brief2 = (proj / "briefs/ch_0002.brief.md").read_text(encoding="utf-8")
        must("黑木匣" in brief2 and "fact_0001" in brief2, "P0-1 brief §6 召回已登记 fact")

        cand2 = tmp / "ch_0002.candidate.md"
        cand2.write_text(CANDIDATE.replace("ch_0001", "ch_0002").replace(
            "林晚把伞收进门后的陶瓮", "回到落脚的柴房，林晚闩死了门"), encoding="utf-8")
        wb_conflict = tmp / "wb_conflict.json"
        wb_conflict.write_text(json.dumps(wb_variant(
            continuity_delta=[{"fact": "林晚失去黑木匣，钥匙并不在城南",
                               "entity_ids": ["char_linwan"], "spoiler": 0,
                               "key": "持有"}],
            payoff_realized=["payoff_0002_1"],
            thread_ops=[{"id": "thread_heimuxia", "op": "tangle", "note": "匣内无钥"}]),
            ensure_ascii=False), encoding="utf-8")
        out = run(["check", "--unit", "ch_0002", "--candidate", str(cand2),
                   "--writeback", str(wb_conflict)], cwd=proj)
        must("facts 冲突候选" in out, "P0-1 同实体同键矛盾 → NEEDS_REVIEW")

        # ---- P0-4 retcon：正例 + 3 负例
        (proj / "court/dec_001_matter.md").write_text(DEC_GOOD, encoding="utf-8")
        run(["retcon", "fact_9999", "--new", "x", "--strategy", "reconcile",
             "--decision", "dec_001_matter"], cwd=proj, expect=1)  # fact 不存在
        run(["retcon", "fact_0001", "--new", "x", "--strategy", "reconcile",
             "--decision", "dec_999"], cwd=proj, expect=1)  # decision 不存在
        run(["retcon", "fact_0001", "--new", "木匣中并无钥匙，只有一份名单",
             "--strategy", "explicit_fix", "--decision", "dec_001_matter"], cwd=proj)
        facts = json.loads(facts_p.read_text(encoding="utf-8"))
        must(facts["facts"][0]["superseded_by"] == "ret_001"
             and facts["retcons"][0]["decision_ref"] == "dec_001_matter",
             "P0-4 retcon 已登记且旧 fact 填 superseded_by")
        run(["retcon", "fact_0001", "--new", "y", "--strategy", "reconcile",
             "--decision", "dec_001_matter"], cwd=proj, expect=1)  # 重复 retcon
        run(["brief", "ch_0002"], cwd=proj)
        brief2 = (proj / "briefs/ch_0002.brief.md").read_text(encoding="utf-8")
        must("已被覆盖" in brief2 and "explicit_fix" in brief2,
             "brief §6 连带 retcon 条目")

        # ---- P0-2 队列：blocked 自动解锁 + reset 正/负例
        t_a = run(["task", "add", "write", "ch_0002"], cwd=proj).strip().splitlines()[-1]
        t_b = run(["task", "add", "design", "vol_01", "--blocked-on", t_a],
                  cwd=proj).strip().splitlines()[-1]
        out = run(["task", "list", "--state", "blocked"], cwd=proj)
        must(t_b in out, "带依赖任务初始为 blocked")
        run(["task", "done", t_a], cwd=proj)
        out = run(["task", "list", "--state", "pending"], cwd=proj)
        must(t_b in out, "P0-2 依赖完成后 blocked 自动 → pending")
        run(["task", "done", tid], cwd=proj)  # 收掉更早的弧设计任务，令 t_b 成为队首
        out = run(["task", "next"], cwd=proj)
        must(t_b in out, "task next 可取出解锁任务")
        run(["task", "reset", t_a], cwd=proj, expect=1)  # 负例：done 不可 reset
        run(["task", "fail", t_b, "--note", "试错"], cwd=proj)
        run(["task", "reset", t_b], cwd=proj)
        out = run(["task", "list", "--state", "pending"], cwd=proj)
        must(t_b in out, "P0-2 task reset：failed → pending")

        # ---- 卷设计 commit → report volume → checkpoint
        volf = tmp / "vol_staged.md"
        volf.write_text(VOLUME_STAGED, encoding="utf-8")
        run(["commit", t_b, "--file", str(volf), "-m", "卷蓝图定稿"], cwd=proj)
        run(["task", "done", t_b], cwd=proj)
        run(["report", "volume", "vol_01"], cwd=proj)
        rp = proj / "state/reports/vol_01.md"
        must(rp.is_file() and "[待对账]" in rp.read_text(encoding="utf-8"),
             "P0-4 卷报告已生成且 exports 预标 [待对账]")
        run(["checkpoint", "vol_01"], cwd=proj, expect=1)  # 负例：三态未标注
        rtext = rp.read_text(encoding="utf-8").replace("[待对账]", "[移交]")
        rp.write_text(rtext, encoding="utf-8")
        run(["tree", "set-status", "ch_0002", "archived"], cwd=proj)  # planned→archived
        run(["checkpoint", "vol_01"], cwd=proj)
        must("checkpoint_at" in (proj / "tree/vol_01/volume.md").read_text(encoding="utf-8"),
             "P0-4 卷已标记 checkpoint_at")
        v2 = (proj / "tree/vol_02/volume.md")
        must(v2.is_file() and "[移交]" in v2.read_text(encoding="utf-8"),
             "P0-4 下卷 imports 已预填移交项")

        # ---- P0-3 后半：check --leak
        brief_clean = tmp / "brief_clean.md"
        brief_clean.write_text("## 3 出场实体状态卡\n\nchar_linwan 的状态卡（不含中文名）。\n",
                               encoding="utf-8")
        run(["check", "--leak", str(cand), "--brief", str(brief_clean)],
            cwd=proj, expect=1)  # 正文用了别名「林晚」但简报未投递
        brief_ok = tmp / "brief_ok.md"
        brief_ok.write_text("## 3 出场实体状态卡\n\n林晚（char_linwan）状态卡。\n",
                            encoding="utf-8")
        run(["check", "--leak", str(cand), "--brief", str(brief_ok)], cwd=proj)

        # ---- P1-9 adopt + P1-8 跨章 12-gram
        ext = tmp / "外部旧稿.txt"
        ext.write_text(CHAPTER_TEXT, encoding="utf-8")  # 与 ch_0001 全文重复
        run(["adopt", str(ext), "--as", "ch_0004", "--parent", "arc_01_1",
             "--title", "旧稿收编"], cwd=proj)
        ch4 = proj / "chapters/ch_0004.md"
        must(ch4.is_file() and "status: drafted" in ch4.read_text(encoding="utf-8")
             and (proj / "chapters/ch_0004.meta.json").is_file(),
             "P1-9 adopt 收编为 drafted + meta stub")
        task4 = dict(TASK_JSON, id="ch_0004")
        (proj / "chapters/ch_0004.task.json").write_text(
            json.dumps(task4, ensure_ascii=False, indent=1), encoding="utf-8")
        out = run(["check", "--unit", "ch_0004"], cwd=proj)
        must("跨章 12 字级重复" in out, "P1-8 两级 ngram：12-gram 复读告警")

        # ---- P1-8 归档 / --since / fsck
        run(["task", "archive", "--keep", "0"], cwd=proj)
        out = run(["task", "list", "--state", "done"], cwd=proj)
        must(t_a not in out, "P1-8 done 任务已归档出队")
        must((proj / "tasks/archive.json").is_file(), "tasks/archive.json 已生成")
        run(["check", "--window", "--since", "ch_0001"], cwd=proj)

        # ---- P1-2：decision/review 机检负例 → 修复
        (proj / "court/dec_002_bad.md").write_text(DEC_BAD, encoding="utf-8")
        run(["check", "--project"], cwd=proj, expect=1)
        (proj / "court/dec_002_bad.md").unlink()
        run(["check", "--project"], cwd=proj)
        run(["fsck"], cwd=proj)

        print("\nSMOKE PASS：%d 步全绿（含 %d 条负例拒绝路径）" % (STEP[0], 15))
        return 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
