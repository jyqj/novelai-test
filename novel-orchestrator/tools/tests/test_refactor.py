#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""novel.py 重构回归测试（P0–P3 专项，stdlib only）。

覆盖：
  P0-1 台账 (chapter,rev) 语义：revise 零双计（payoff/power/timeline 读侧去重、
        实体事件日志/线索推进日志撤销重放、终态线 revise 重提交合法、facts 先剪后登）
  P0-2 回执收紧：note 自证通道已死；rev_reviewed 必须等于章当前 rev；review add CLI
  P0-3 原子提交：半事务 journal 残留被 fsck 检出
  P0-4 facts import（adopt 补录机械半边，幂等）
  P1-1 rollup 自动卷积（章→弧→卷）+ brief §2 注入
  P1-2 简报条目级预算裁剪 + must-not-drop 集
  P1-3 声纹速查独立块（设定可裁声纹不裁）
  P2-1 抽取器对账（未申报出场 WARN / 新专名候选 NEEDS_REVIEW）
  P2-2 故事日历（elapsed 数值化累计 + story_date 倒流 FAIL）
  P3-1 gate 家族（write/approve/publish/next）
  P3-2 court 工作区（open/status/close）
  P4-K 知识矩阵（continuity_delta.known_by 登记 / knowledge grant|reveal|query /
        简报知情标记 / 抽取器角色知识越界候选）
  P4-G gate 修复提示（FAIL 附「下一步」可执行命令）
  P4-R rollup CLI（批量手改 meta.json 后手动重算）
  P4-D revise_rubric 蒸馏（lessons → style 黑名单 → 机检生效；无 stale 波及）

运行：python3 tools/tests/test_refactor.py
"""
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from support import legacy_fixture_invoke

TOOLS = Path(__file__).resolve().parent.parent
NOVEL = TOOLS / "novel.py"
STEP = [0]


def run(args, cwd, expect=0):
    r = legacy_fixture_invoke(args, cwd)
    if r.returncode != expect:
        print("FAILED: novel.py %s\nexit=%d (期望 %d)\n--- stdout ---\n%s\n--- stderr ---\n%s"
              % (" ".join(args), r.returncode, expect, r.stdout, r.stderr))
        sys.exit(1)
    STEP[0] += 1
    print("OK %02d: novel.py %s (exit=%d)" % (STEP[0], " ".join(args[:5]), r.returncode))
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

REVISED_TEXT = CHAPTER_TEXT.replace("门外的雨声忽然停了。",
                                    "门外的雨声忽然停了，檐角滴水声也断了。")


def envelope(ch_id, text, title="测试章"):
    return ("---\nid: %s\nkind: chapter\nstatus: drafted\nrev: 1\nparent: arc_01_1\n"
            "updated_at: 2026-08-24T00:00:00\ntitle: %s\nword_count: 0\n---\n\n"
            "## 正文\n\n%s\n" % (ch_id, title, text))


ARC_STAGED = """---
id: arc_01_1
kind: arc
status: draft
rev: 1
parent: vol_01
updated_at: 2026-08-24T00:00:00
---

## 弧目标与节奏模板

弧目标：取匣入局。模板 wave。

## 因果链

验牌 → 取匣 → 盯梢 → 寻钥 → 冲突。

## 章分配草案

| 章 | 因果拍 | 钩 |
|---|---|---|
| ch_0001 | 取匣 | 脚步声 |
| ch_0008 | 寻钥 | 名单现世 |

## 线索操作计划

- thread_main: ch_0001 plant+advance。

## 爽点与期待操作表

| 章 | kind | intent |
|---|---|---|
| ch_0001 | dopamine | 身份被认出 |

## 出场实体清单

- char_linwan（主）。
"""

TASK1 = {
    "id": "ch_0001", "arc": "arc_01_1", "goal": "取得黑木匣并暴露",
    "beats": ["验牌", "取匣", "盯梢"],
    "hook": {"open": None, "close": "身后脚步声"},
    "payoff_quota": [{"kind": "dopamine", "intent": "身份被认出"}],
    "threads": [{"id": "thread_main", "op": "advance"}],
    "cast": ["char_linwan"], "word_target": [300, 800],
}

WB_REV1 = {
    "summary_after": "林晚取得黑木匣，得知钥匙在城南；离开时被盯梢。",
    "continuity_delta": [{"fact": "林晚取得黑木匣", "entity_ids": ["char_linwan"],
                          "spoiler": 0, "key": "持有"}],
    "time_advance": {"elapsed": "2天", "story_date": "2026-01-10"},
    "thread_ops": [{"id": "thread_main", "op": "plant", "note": "埋"},
                   {"id": "thread_main", "op": "advance", "note": "推"},
                   {"id": "thread_main", "op": "payoff", "note": "误判提前收线"}],
    "payoff_realized": ["payoff_0001_1"],
    "hooks_realized": {"open": True, "close": True},
    "cast_actual": ["char_linwan"],
    "power_delta": [{"entity_ids": ["char_linwan"], "from": "孤徒", "to": "入局者",
                     "note": "身份跃迁"}],
    "issues": [], "word_count": 330,
}

WB_REV2 = dict(WB_REV1)
WB_REV2 = json.loads(json.dumps(WB_REV1))
WB_REV2["continuity_delta"] = [{"fact": "林晚取得黑木匣并发现匣底暗格",
                                "entity_ids": ["char_linwan"], "spoiler": 0,
                                "key": "持有"}]
WB_REV2["time_advance"] = {"elapsed": "3天", "story_date": "2026-01-12"}
# 修订裁决：本章不收线（终态 op 撤回）——旧实现会被自己上一轮 payoff 卡死
WB_REV2["thread_ops"] = [{"id": "thread_main", "op": "plant", "note": "埋"},
                         {"id": "thread_main", "op": "advance", "note": "推"}]

TEXT3 = """林晚把黑木匣搁在灯下，撬开匣底暗格，一枚青铜印落进掌心。
印面刻着一株并蒂莲，边缘七处缺口，与她贴身收着的半块碎印严丝合缝。
她记得师父下葬那天，棺中少了这半件东西，山门的人只说遗失。
灯芯爆了个花。她把青铜印按回暗格，抹平木屑，像从未打开过。
窗外传来打更声，三更。
她吹熄灯，坐回床沿，刀横在膝上。
今晚不会有人来，但从明天起，城南第七户的每一步都要重新算。
她闭上眼，把白日里当铺老人的每一句话重新过了一遍，
在「看好你身后」四个字上停了很久。
更声敲过四下的时候，她做了决定：先查印，再查人。
青铜印的另一半在她枕下压了七年，明日起，它该出来见光了。
她把碎印塞进护腕内衬，贴着脉搏，那里的皮肤早被磨出一层薄茧。
天亮之前，她还要把当铺到城南的三条巷子在脑子里走通。"""

WB3 = {
    "summary_after": "林晚在匣底暗格发现青铜印，与师父遗印同源；她按下不表。",
    "continuity_delta": [{"fact": "匣中信物是师门遗物",
                          "entity_ids": ["char_linwan"], "spoiler": 1,
                          "key": "知晓", "known_by": ["char_linwan"]}],
    "time_advance": {"elapsed": "1天", "story_date": ""},
    "thread_ops": [],
    "payoff_realized": ["payoff_0003_1"],
    "hooks_realized": {"open": True, "close": True},
    "cast_actual": ["char_linwan"],
    "issues": [], "word_count": 0,
}

VOICE_SETTING = """## 设定

- 欲望: 查清师父死因
- 声纹:
  - 口癖: 「按规矩来」
  - 句式: 短句起手、常省主语
  - 禁词: 从不说「害怕」
  - 例句: 「——先把账算清。」

## 现状

- 位置: 城南当铺
- 状态: 入局者
- 持有: 黑木匣
- 知晓: 钥匙在城南
- 关系现状: 孤身
- 未了承诺: 替师父收尾

## 事件日志
"""


def main():
    tmp = Path(tempfile.mkdtemp(prefix="novel_refactor_"))
    try:
        proj = tmp / "book_r"
        run(["init", str(proj), "--name", "重构之书"], cwd=tmp)
        must((proj / "state/txn").is_dir(), "P0-3 脚手架含 state/txn/")
        head = (proj / "ledgers/payoff.tsv").read_text(encoding="utf-8")
        must(head.strip().endswith("rev"), "P0-1 台账表头含 rev 列")

        run(["tree", "add", "volume", "vol_01"], cwd=proj)
        run(["tree", "add", "arc", "arc_01_1"], cwd=proj)
        run(["tree", "add", "chapter", "ch_0001", "--parent", "arc_01_1"], cwd=proj)
        run(["entity", "new", "char_linwan"], cwd=proj)
        run(["thread", "new", "thread_main", "--kind", "mystery"], cwd=proj)
        (proj / "entities/aliases.json").write_text(
            json.dumps({"林晚": "char_linwan"}, ensure_ascii=False), encoding="utf-8")
        # 实体卡注入真实声纹（P1-3 用）
        ent_p = proj / "entities/char_linwan.md"
        ent = ent_p.read_text(encoding="utf-8")
        fm_end = ent.index("---", 4) + 3
        ent_p.write_text(ent[:fm_end] + "\n\n" + VOICE_SETTING, encoding="utf-8")
        (proj / "chapters/ch_0001.task.json").write_text(
            json.dumps(TASK1, ensure_ascii=False, indent=1), encoding="utf-8")
        tid = run(["task", "add", "design", "arc_01_1"], cwd=proj).strip().splitlines()[-1]
        staged = tmp / "arc_staged.md"
        staged.write_text(ARC_STAGED, encoding="utf-8")
        run(["stage", "enter", "arc"], cwd=proj)
        run(["commit", tid, "--file", str(staged), "-m", "弧定稿"], cwd=proj)
        run(["task", "done", tid], cwd=proj)

        # ---- rev1 提交
        t_w = run(["task", "add", "write", "ch_0001"], cwd=proj).strip().splitlines()[-1]
        run(["task", "start", t_w], cwd=proj)
        run(["stage", "enter", "write"], cwd=proj)
        run(["brief", "ch_0001"], cwd=proj)
        cand = tmp / "c1.md"
        cand.write_text(envelope("ch_0001", CHAPTER_TEXT), encoding="utf-8")
        wb1 = tmp / "wb1.json"
        wb1.write_text(json.dumps(WB_REV1, ensure_ascii=False), encoding="utf-8")
        run(["commit", t_w, "--chapter", str(cand), "--writeback", str(wb1),
             "-m", "rev1"], cwd=proj)
        run(["task", "done", t_w], cwd=proj)
        th = (proj / "threads/thread_main.md").read_text(encoding="utf-8")
        must("state: paid_off" in th, "rev1：线索经 payoff 进入终态")
        payoff = (proj / "ledgers/payoff.tsv").read_text(encoding="utf-8")
        must(payoff.count("ch_0001\t") == 1 and payoff.rstrip().endswith("\t1"),
             "rev1：payoff 台账 1 行且带 rev=1 列")

        # ---- P0-1：revise 重提交（含终态线 op 撤回）
        t_r = run(["task", "add", "revise", "ch_0001"], cwd=proj).strip().splitlines()[-1]
        run(["task", "start", t_r], cwd=proj)
        cand2 = tmp / "c2.md"
        cand2.write_text(envelope("ch_0001", REVISED_TEXT), encoding="utf-8")
        wb2 = tmp / "wb2.json"
        wb2.write_text(json.dumps(WB_REV2, ensure_ascii=False), encoding="utf-8")
        # 旧实现：payoff 终态后 advance 模拟非法 → 拒绝；新实现：剔除本章旧贡献后重放 → 合法
        run(["check", "--unit", "ch_0001", "--candidate", str(cand2),
             "--writeback", str(wb2)], cwd=proj)
        run(["commit", t_r, "--chapter", str(cand2), "--writeback", str(wb2),
             "-m", "rev2"], cwd=proj)
        run(["task", "done", t_r], cwd=proj)

        ch = (proj / "chapters/ch_0001.md").read_text(encoding="utf-8")
        must("rev: 2" in ch, "revise：章 rev=2")
        th = (proj / "threads/thread_main.md").read_text(encoding="utf-8")
        must("state: active" in th, "P0-1：终态线撤销重放 → active（payoff 撤回生效）")
        must(th.count("- ch_0001:") == 2 and "payoff" not in
             [l.split()[2] if len(l.split()) > 2 else "" for l in th.splitlines()
              if l.startswith("- ch_0001:")][-1],
             "P0-1：推进日志仅存 rev2 两条 op（旧行已剔除）")
        ent = (proj / "entities/char_linwan.md").read_text(encoding="utf-8")
        must(ent.count("- ch_0001:") == 1 and "匣底暗格" in ent,
             "P0-1：实体事件日志零双计且为 rev2 文本")
        payoff = (proj / "ledgers/payoff.tsv").read_text(encoding="utf-8")
        must(payoff.count("ch_0001\t") == 2, "P0-1：payoff 文件 append-only（两 rev 各一行）")
        out = run(["ledger", "payoff"], cwd=proj)
        must(out.count("payoff_0001_1") == 1, "P0-1：读侧物化去重（仅最新 rev 行）")
        out = run(["ledger", "power"], cwd=proj)
        must(out.count("char_linwan") == 1, "P0-1：power 读侧去重")
        out = run(["ledger", "timeline"], cwd=proj)
        must("3.0" in out and "2026-01-12" in out and "2026-01-10" not in out,
             "P0-1/P2-2：timeline 去重 + 故事日历累计 3.0 天")
        facts = json.loads((proj / "ledgers/facts/vol_01.json").read_text(encoding="utf-8"))
        must(len(facts["facts"]) == 1 and facts["facts"][0]["fact"] == "林晚取得黑木匣并发现匣底暗格"
             and facts["facts"][0]["id"] == "fact_0002",
             "P0-1：facts 先剪后登（旧临时事实剪除，id 不复用）")
        run(["check", "--window"], cwd=proj)
        run(["check", "--project"], cwd=proj)

        # ---- P0-2：回执收紧
        run(["tree", "set-status", "ch_0001", "approved"], cwd=proj, expect=1)
        # note 写入 light=pass（旧自证通道）后 set-status 依然拒绝——通道已死
        run(["task", "done", t_r, "--note", "light=pass"], cwd=proj)
        run(["tree", "set-status", "ch_0001", "approved"], cwd=proj, expect=1)
        must(True, "P0-2：note light=pass 自证通道已死")
        run(["review", "add", "ch_0001", "--depth", "light", "--verdict", "pass",
             "--rev", "1"], cwd=proj)
        run(["tree", "set-status", "ch_0001", "approved"], cwd=proj, expect=1)
        must(True, "P0-2：rev_reviewed=1 ≠ 章 rev=2 → 回执无效被拒")
        run(["review", "add", "ch_0001", "--depth", "light", "--verdict", "pass"],
            cwd=proj)
        out = run(["gate", "approve", "ch_0001"], cwd=proj)
        must("0 FAIL" in out, "P3-1：gate approve 复核回执（0 FAIL）")
        run(["tree", "set-status", "ch_0001", "approved"], cwd=proj)
        ch = (proj / "chapters/ch_0001.md").read_text(encoding="utf-8")
        must("rev_reviewed=2" in ch, "P0-2：approved_evidence 记录 rev 匹配回执")

        # ---- P0-3：半事务检出
        bad_txn = proj / "state/txn/txn_20990101000000000000_ch_9999.json"
        bad_txn.write_text(json.dumps({"id": "txn_x", "kind": "write",
                                       "target": "ch_9999", "started_at": "2099",
                                       "done": False}), encoding="utf-8")
        out = run(["fsck"], cwd=proj, expect=1)
        must("半事务" in out, "P0-3：fsck 检出 done=false journal")
        bad_txn.unlink()
        run(["fsck"], cwd=proj)

        # ---- P0-4：facts import（adopt 补录）
        ext = tmp / "旧稿.txt"
        ext.write_text("城南的巷子比林晚想的深。她数着门牌，在第七户前停下。", encoding="utf-8")
        run(["adopt", str(ext), "--as", "ch_0002", "--parent", "arc_01_1"], cwd=proj)
        mp = proj / "chapters/ch_0002.meta.json"
        stub = json.loads(mp.read_text(encoding="utf-8"))
        stub["summary_after"] = "林晚抵达城南，锁定第七户。"
        stub["continuity_delta"] = [{"fact": "钥匙藏处锁定为城南第七户",
                                     "entity_ids": ["char_linwan"], "spoiler": 1}]
        mp.write_text(json.dumps(stub, ensure_ascii=False, indent=1), encoding="utf-8")
        run(["facts", "import", "ch_0002"], cwd=proj)
        facts = json.loads((proj / "ledgers/facts/vol_01.json").read_text(encoding="utf-8"))
        must(len(facts["facts"]) == 2, "P0-4：facts import 入账")
        run(["facts", "import", "ch_0002"], cwd=proj)
        facts = json.loads((proj / "ledgers/facts/vol_01.json").read_text(encoding="utf-8"))
        must(len(facts["facts"]) == 2, "P0-4：facts import 幂等（重跑零重复）")
        out = run(["facts", "list", "--entity", "char_linwan"], cwd=proj)
        must("spoiler" in out, "facts list 视图含 spoiler 标记")

        # ---- P1-1：rollup + brief 注入
        rollup = json.loads((proj / "state/rollup.json").read_text(encoding="utf-8"))
        must("arc_01_1" in rollup["arcs"] and rollup["arcs"]["arc_01_1"]["span"] ==
             ["ch_0001", "ch_0002"], "P1-1：rollup 弧级卷积（章→弧）")
        must("vol_01" in rollup["volumes"], "P1-1：rollup 卷级卷积（弧→卷）")
        run(["tree", "add", "chapter", "ch_0008", "--parent", "arc_01_1"], cwd=proj)
        task8 = dict(TASK1, id="ch_0008", goal="寻钥",
                     hook={"open": None, "close": "第七户的门开了"})
        (proj / "chapters/ch_0008.task.json").write_text(
            json.dumps(task8, ensure_ascii=False, indent=1), encoding="utf-8")
        run(["brief", "ch_0008"], cwd=proj)
        brief = (proj / "briefs/ch_0008.brief.md").read_text(encoding="utf-8")
        must("本弧前情（rollup" in brief, "P1-1：远章简报注入弧 rollup（远程记忆层）")
        must("声纹速查" in brief and "按规矩来" in brief, "P1-3：声纹独立块入简报 §3")
        must("【读者未知，只可潜台词】" in brief, "P2-3：spoiler 事实带潜台词标记")

        # ---- P1-2：条目级预算裁剪 + must-not-drop
        cfg = json.loads((proj / "config.json").read_text(encoding="utf-8"))
        cfg["brief_budget_chars"] = 2600
        (proj / "config.json").write_text(json.dumps(cfg, ensure_ascii=False, indent=2),
                                          encoding="utf-8")
        before = (proj / "briefs/ch_0008.brief.md").read_bytes()
        out = run(["brief", "ch_0008"], cwd=proj, expect=1)
        must("必需上下文" in out and "超过预算" in out,
             "P1-2：不可裁上下文超预算时拒绝交付，不静默丢失")
        must((proj / "briefs/ch_0008.brief.md").read_bytes() == before,
             "P1-2：预算失败保留上版简报")
        cfg["brief_budget_chars"] = 24000
        (proj / "config.json").write_text(json.dumps(cfg, ensure_ascii=False, indent=2),
                                          encoding="utf-8")

        # ---- P2-1：抽取器
        cand_x = tmp / "cx.md"
        cand_x.write_text(envelope(
            "ch_0008",
            "林晚推开门。屋里的人自称「守钥人」，又一次说出「守钥人」三个字时，"
            "她握紧了刀。"), encoding="utf-8")
        wb_x = tmp / "wbx.json"
        wb_x.write_text(json.dumps({"cast_actual": []}, ensure_ascii=False),
                        encoding="utf-8")
        out = run(["extract", "ch_0008", "--candidate", str(cand_x),
                   "--writeback", str(wb_x)], cwd=proj)
        must("cast_actual 未申报" in out, "P2-1：未申报出场 → WARN")
        must("守钥人" in out and "新专名候选" in out, "P2-1：引号新专名候选 → NEEDS_REVIEW")

        # ---- P2-2：story_date 倒流
        with open(proj / "ledgers/timeline.tsv", "a", encoding="utf-8") as f:
            f.write("ch_0003\t2026-01-05\t1天\t\t1\n")
        out = run(["check", "--window"], cwd=proj, expect=1)
        must("story_date 倒流" in out, "P2-2：故事日历倒流 FAIL")
        tl = (proj / "ledgers/timeline.tsv").read_text(encoding="utf-8").splitlines()
        (proj / "ledgers/timeline.tsv").write_text("\n".join(tl[:-1]) + "\n",
                                                   encoding="utf-8")
        run(["check", "--window"], cwd=proj)

        # ---- P3-1：gate 家族
        run(["brief", "ch_0008"], cwd=proj)  # 基线入库（git 干净）
        # Author-owned fixture changes must be committed explicitly, not absorbed
        # by brief's auto-commit (which now stages only its own outputs).
        from support import save_fixture
        save_fixture(proj)
        run(["gate", "write", "ch_0008"], cwd=proj)
        run(["tree", "add", "chapter", "ch_0009", "--parent", "arc_01_1"], cwd=proj)
        run(["gate", "write", "ch_0009"], cwd=proj, expect=1)  # 未排批+无简报
        run(["stage", "enter", "ops"], cwd=proj)  # publish/checkpoint 闸门属 ops
        run(["gate", "publish", "ch_0005"], cwd=proj, expect=1)  # 连续性谓词
        out = run(["gate", "next"], cwd=proj)
        must("机器版编排剧本" in out, "P3-1：gate next 输出调度剧本")
        run(["gate", "checkpoint", "vol_01"], cwd=proj, expect=1)  # 卷未 committed

        # ---- P3-2：court 工作区（court open S1 属 s1 阶段）
        out = run(["court", "open", "S1", "--node", "book"], cwd=proj, expect=1)
        must("阶段闸门" in out, "P7-S 错阶段（ops）court open S1 被拒")
        run(["stage", "enter", "s1"], cwd=proj)
        run(["court", "open", "S1", "--node", "book"], cwd=proj)
        must((proj / "state/court/S1/r0_brief.md").is_file(), "P3-2：R0 骨架就位")
        out = run(["court", "status"], cwd=proj)
        must("S1" in out, "P3-2：court status 盘点场次")
        run(["court", "close", "S1", "--dec", "dec_001_x"], cwd=proj, expect=1)
        (proj / "court/dec_001_x.md").write_text("""---
id: dec_001_x
kind: decision
node: book
session: S1
date: 2026-08-24
status: active
---

## 选项

- A | 架构师 | 某案

## 裁决

选 A。

## 否决案

- B | 不选 | reopen_requires: 新证据

## 异议

- 无 | 无 | resolution: adopted
""", encoding="utf-8")
        run(["court", "close", "S1", "--dec", "dec_001_x"], cwd=proj)
        must(not any((proj / "state/court/S1").rglob("*.md")), "P3-2：close 校验 dec 后删除受控文件")

        # ---- P4-K：知识矩阵（fact × 角色 × 读者）
        run(["entity", "new", "char_rival"], cwd=proj)
        aliases = json.loads((proj / "entities/aliases.json").read_text(encoding="utf-8"))
        aliases["秦九"] = "char_rival"
        (proj / "entities/aliases.json").write_text(
            json.dumps(aliases, ensure_ascii=False), encoding="utf-8")
        run(["tree", "add", "chapter", "ch_0003", "--parent", "arc_01_1"], cwd=proj)
        task3 = dict(TASK1, id="ch_0003", goal="认出匣中信物来历",
                     hook={"open": None, "close": "印记与师父遗物同源"},
                     payoff_quota=[{"kind": "reveal", "intent": "信物来历"}],
                     threads=[])
        (proj / "chapters/ch_0003.task.json").write_text(
            json.dumps(task3, ensure_ascii=False, indent=1), encoding="utf-8")
        t_k = run(["task", "add", "write", "ch_0003"],
                  cwd=proj).strip().splitlines()[-1]
        run(["task", "start", t_k], cwd=proj)
        run(["stage", "enter", "write"], cwd=proj)
        cand3 = tmp / "c3.md"
        cand3.write_text(envelope("ch_0003", TEXT3, title="识物"), encoding="utf-8")
        wb3f = tmp / "wb3.json"
        wb3f.write_text(json.dumps(WB3, ensure_ascii=False), encoding="utf-8")
        run(["commit", t_k, "--chapter", str(cand3), "--writeback", str(wb3f),
             "-m", "知识矩阵样章"], cwd=proj)
        run(["review", "add", "ch_0003", "--depth", "light", "--verdict", "pass"],
            cwd=proj)
        run(["task", "done", t_k], cwd=proj)
        facts = json.loads((proj / "ledgers/facts/vol_01.json").read_text(encoding="utf-8"))
        kf = [x for x in facts["facts"] if x.get("known_by")]
        must(len(kf) == 1 and kf[0]["known_by"] == ["char_linwan"],
             "P4-K：commit 自 continuity_delta.known_by 登记角色知情半边")
        fid = kf[0]["id"]

        # 简报 §6 注入知情约束（cast 含不知情角色 → 硬约束入包）
        task9 = dict(TASK1, id="ch_0009", goal="对峙",
                     hook={"open": None, "close": "秦九亮出令牌"},
                     threads=[], cast=["char_linwan", "char_rival"])
        (proj / "chapters/ch_0009.task.json").write_text(
            json.dumps(task9, ensure_ascii=False, indent=1), encoding="utf-8")
        run(["brief", "ch_0009"], cwd=proj)
        brief9 = (proj / "briefs/ch_0009.brief.md").read_text(encoding="utf-8")
        must("【知情仅:char_linwan】" in brief9,
             "P4-K：简报 §6 注入知情名单标记")
        must("char_rival 不知情" in brief9,
             "P4-K：简报 §6 注入「在场不知情——不得由其说破」硬约束")

        # 抽取器角色知识越界候选（known_by 外角色说破事实 → NEEDS_REVIEW）
        cand4 = tmp / "c4.md"
        cand4.write_text(envelope(
            "ch_0004",
            "秦九冷笑。「匣中信物是师门遗物，你从何处得来？」林晚握紧刀柄。",
            title="对峙"), encoding="utf-8")
        wb4f = tmp / "wb4.json"
        wb4f.write_text(json.dumps({"cast_actual": ["char_linwan", "char_rival"]},
                                   ensure_ascii=False), encoding="utf-8")
        out = run(["extract", "ch_0004", "--candidate", str(cand4),
                   "--writeback", str(wb4f)], cwd=proj)
        must("角色知识越界候选" in out and "char_rival" in out,
             "P4-K：known_by 外角色明写事实 → 越界候选 NEEDS_REVIEW")
        out = run(["knowledge", "query", "--entity", "char_rival"], cwd=proj)
        must("不知情 1 条" in out and "匣中信物是师门遗物" in out,
             "P4-K：knowledge query --entity 输出知/不知两侧")
        run(["knowledge", "grant", fid, "--to", "秦九", "--ch", "ch_0004"], cwd=proj)
        out = run(["extract", "ch_0004", "--candidate", str(cand4),
                   "--writeback", str(wb4f)], cwd=proj)
        must("角色知识越界候选" not in out,
             "P4-K：grant 补授知情后越界候选消失（别名可解析）")
        out = run(["knowledge", "query"], cwd=proj)
        must("known_by 已建模 1 条" in out and fid in out,
             "P4-K：query 总览盘点读者未知欠账")
        run(["knowledge", "reveal", fid, "--ch", "ch_0004"], cwd=proj)
        run(["knowledge", "reveal", fid, "--ch", "ch_0004"], cwd=proj, expect=1)
        must(True, "P4-K：重复 reveal 被拒（已读者已知）")
        out = run(["facts", "list"], cwd=proj)
        fid_line = [l for l in out.splitlines() if l.startswith(fid)][0]
        must("【spoiler】" not in fid_line
             and "【知情:char_linwan,char_rival】" in fid_line,
             "P4-K：reveal 销账后 spoiler 标记消失，知情名单留存")

        # ---- P4-G：gate 修复提示（FAIL 即剧本）
        out = run(["gate", "write", "ch_0004"], cwd=proj, expect=1)
        must("↳ 下一步" in out and "tree add chapter ch_0004" in out,
             "P4-G：缺任务卡 → 下一步给 tree add + 排批指引")
        task4 = dict(TASK1, id="ch_0004", goal="对峙升级",
                     hook={"open": None, "close": "令牌上的名字"}, threads=[])
        (proj / "chapters/ch_0004.task.json").write_text(
            json.dumps(task4, ensure_ascii=False, indent=1), encoding="utf-8")
        out = run(["gate", "write", "ch_0004"], cwd=proj, expect=1)
        must("novel.py brief ch_0004" in out,
             "P4-G：简报未编译 → 下一步给 brief 命令")
        must("禁止全局清理" in out and "git checkout" not in out,
             "P4-G：基线不净 → 下一步保护作者改动而非全局清理")
        out = run(["gate", "approve", "ch_0002"], cwd=proj, expect=1)
        must("review add ch_0002" in out, "P4-G：缺回执 → 下一步给 review add")
        must("机检不绿" in out and "check --unit ch_0002" in out,
             "P4-G：机检 FAIL → 下一步给 check --unit + 修订循环去向")

        # ---- P4-R：rollup CLI（批量手改 meta 后手动重算）
        mp3 = proj / "chapters/ch_0003.meta.json"
        m3 = json.loads(mp3.read_text(encoding="utf-8"))
        m3["summary_after"] = "第 3 章改写后的摘要：信物来历浮出水面。"
        mp3.write_text(json.dumps(m3, ensure_ascii=False, indent=1), encoding="utf-8")
        out = run(["rollup"], cwd=proj)
        must("已重算" in out, "P4-R：rollup 命令输出统计")
        rj = (proj / "state/rollup.json").read_text(encoding="utf-8")
        must("改写后的摘要" in rj, "P4-R：手改 summary_after 经 rollup 进卷积")

        # ---- P4-D：revise_rubric 蒸馏（lessons → style 黑名单 → 机检生效）
        run(["task", "add", "revise_rubric", "style"], cwd=proj, expect=1)
        must(True, "P4-D：revise_rubric 缺 evidence 被拒")
        run(["task", "add", "revise_rubric", "book", "--evidence", "x"],
            cwd=proj, expect=1)
        must(True, "P4-D：revise_rubric 目标限 style（book 被拒）")
        t_rr = run(["task", "add", "revise_rubric", "style", "--evidence",
                    "lessons: ch_0001/ch_0003 轻评两次复现「指节发白」滥用"],
                   cwd=proj).strip().splitlines()[-1]
        style_now = (proj / "tree/style.md").read_text(encoding="utf-8")
        staged_style = tmp / "style_staged.md"
        staged_style.write_text(
            style_now.replace("- 嘴角勾起一抹", "- 指节发白\n- 嘴角勾起一抹", 1),
            encoding="utf-8")
        run(["stage", "enter", "review"], cwd=proj)  # 蒸馏属周期回路
        out = run(["commit", t_rr, "--file", str(staged_style), "-m", "蒸馏黑名单"],
                  cwd=proj)
        must("蒸馏入库" in out, "P4-D：revise_rubric commit 走蒸馏路径")
        run(["task", "done", t_rr], cwd=proj)
        style2 = (proj / "tree/style.md").read_text(encoding="utf-8")
        must("- 指节发白" in style2, "P4-D：style 黑名单已增补")
        ch1 = (proj / "chapters/ch_0001.md").read_text(encoding="utf-8")
        must("status: approved" in ch1, "P4-D：蒸馏不波及既有章（无 stale）")
        cand5 = tmp / "c5.md"
        cand5.write_text(envelope("ch_0003", TEXT3 + "\n她攥紧刀柄，指节发白。",
                                  title="识物"), encoding="utf-8")
        out = run(["check", "--unit", "ch_0003", "--candidate", str(cand5),
                   "--writeback", str(wb3f)], cwd=proj, expect=1)
        must("禁忌命中" in out and "指节发白" in out,
             "P4-D：新黑名单即刻被 check --unit 强制（蒸馏回路闭环）")

        run(["check", "--project"], cwd=proj)
        print("\nREFACTOR PASS：%d 步全绿" % STEP[0])
        return 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
