#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""novel.py 端到端冒烟测试（stdlib only，无第三方依赖）。

覆盖绿路径：init → tree add → entity/thread → design commit(弧) → task add write
→ brief → check --unit(候选) → commit(write) → check --window/--project
→ set-status approved → publish；外加两条负例（黑名单命中拒绝、发布连续性拒绝）。

运行：python3 tools/tests/test_smoke.py
成功：打印各步骤 OK 与最终 SMOKE PASS，退出码 0。
"""
import json
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
    return r.stdout


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
                          "entity_ids": ["char_linwan"], "spoiler": 0}],
    "time_advance": {"elapsed": "1晚", "story_date": ""},
    "thread_ops": [{"id": "thread_heimuxia", "op": "advance",
                    "note": "木匣到手，钥匙位置揭示"}],
    "payoff_realized": ["payoff_0001_1"],
    "hooks_realized": {"open": True, "close": True},
    "cast_actual": ["char_linwan"],
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

- thread_heimuxia: ch_0001 advance；ch_0002 tangle（匣内并无钥匙）。

## 爽点与期待操作表

| 章 | kind | intent |
|---|---|---|
| ch_0001 | dopamine | 铜牌身份被认出，老人破例交匣 |

## 出场实体清单

- char_linwan（主）；当铺老人（暂不建卡，出场 <3 章）。
"""


def main():
    tmp = Path(tempfile.mkdtemp(prefix="novel_smoke_"))
    try:
        proj = tmp / "book1"
        run(["init", str(proj), "--name", "冒烟之书"], cwd=tmp)
        must((proj / "config.json").is_file() and (proj / "tree/book.md").is_file(),
             "脚手架目录/config/树节点存在")

        run(["tree", "add", "volume", "vol_01"], cwd=proj)
        run(["tree", "add", "arc", "arc_01_1"], cwd=proj)
        run(["tree", "add", "chapter", "ch_0001", "--parent", "arc_01_1"], cwd=proj)
        run(["entity", "new", "char_linwan"], cwd=proj)
        run(["thread", "new", "thread_heimuxia", "--kind", "mystery"], cwd=proj)

        # 排批：填章任务卡
        (proj / "chapters/ch_0001.task.json").write_text(
            json.dumps(TASK_JSON, ensure_ascii=False, indent=1), encoding="utf-8")

        # 弧设计 commit（design 任务 → 校验必需节 → status=committed）
        tid = run(["task", "add", "design", "arc_01_1"], cwd=proj).strip().splitlines()[-1]
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

        # 候选章 + writeback：机检绿
        cand = tmp / "ch_0001.candidate.md"
        cand.write_text(CANDIDATE, encoding="utf-8")
        wb = tmp / "ch_0001.writeback.json"
        wb.write_text(json.dumps(WRITEBACK, ensure_ascii=False, indent=1), encoding="utf-8")
        run(["check", "--unit", "ch_0001", "--candidate", str(cand),
             "--writeback", str(wb)], cwd=proj)

        # 负例：黑名单命中必须拒绝（exit=1）
        bad = tmp / "ch_0001.bad.md"
        bad.write_text(CANDIDATE.replace(
            "门外的雨声忽然停了。",
            "门外的雨声忽然停了。他嘴角勾起一抹弧度，眸中精光一闪。"), encoding="utf-8")
        run(["check", "--unit", "ch_0001", "--candidate", str(bad),
             "--writeback", str(wb)], cwd=proj, expect=1)

        # commit：落盘 + 回写实体/线索/台账
        run(["commit", tid2, "--chapter", str(cand), "--writeback", str(wb),
             "-m", "首章成稿"], cwd=proj)
        run(["task", "done", tid2], cwd=proj)
        ch = (proj / "chapters/ch_0001.md").read_text(encoding="utf-8")
        must("status: drafted" in ch, "章状态 drafted")
        ent = (proj / "entities/char_linwan.md").read_text(encoding="utf-8")
        must("- ch_0001:" in ent, "实体事件日志已回写")
        th = (proj / "threads/thread_heimuxia.md").read_text(encoding="utf-8")
        must("state: active" in th and "- ch_0001: advance" in th, "线索推进已回写")
        payoff = (proj / "ledgers/payoff.tsv").read_text(encoding="utf-8")
        must("payoff_0001_1" in payoff and "\t1" in payoff, "爽点台账已登记 realized=1")

        # 窗口/全库检查 + 审批 + 发布
        run(["check", "--window"], cwd=proj)
        run(["check", "--project"], cwd=proj)
        run(["status"], cwd=proj)
        run(["tree", "set-status", "ch_0001", "approved"], cwd=proj)
        run(["publish", "ch_0001"], cwd=proj)
        out = run(["status"], cwd=proj)
        must("last_published=1" in out, "游标 last_published=1")

        # 负例：跳章发布必须拒绝
        run(["publish", "ch_0003"], cwd=proj, expect=1)

        print("\nSMOKE PASS：%d 步全绿（含 2 条负例拒绝）" % STEP[0])
        return 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
