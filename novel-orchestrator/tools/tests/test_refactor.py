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

运行：python3 tools/tests/test_refactor.py
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
        run(["commit", tid, "--file", str(staged), "-m", "弧定稿"], cwd=proj)
        run(["task", "done", tid], cwd=proj)

        # ---- rev1 提交
        t_w = run(["task", "add", "write", "ch_0001"], cwd=proj).strip().splitlines()[-1]
        run(["task", "start", t_w], cwd=proj)
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
        run(["brief", "ch_0008"], cwd=proj)
        brief = (proj / "briefs/ch_0008.brief.md").read_text(encoding="utf-8")
        must("条目级裁剪" in brief, "P1-2：超预算逐条裁剪并留痕")
        must("## 0 任务卡" in brief and "## 8 回写契约" in brief
             and "声纹速查" in brief and "现状：" in brief,
             "P1-2：must-not-drop 集完整（任务卡/契约/声纹/现状）")
        must("设定要点" not in brief.split("## 附 溯源")[0]
             or "本节超预算裁剪" in brief,
             "P1-2：低分条目（设定要点）先被裁")
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
        run(["gate", "write", "ch_0008"], cwd=proj)
        run(["tree", "add", "chapter", "ch_0009", "--parent", "arc_01_1"], cwd=proj)
        run(["gate", "write", "ch_0009"], cwd=proj, expect=1)  # 未排批+无简报
        run(["gate", "publish", "ch_0005"], cwd=proj, expect=1)  # 连续性谓词
        out = run(["gate", "next"], cwd=proj)
        must("机器版编排剧本" in out, "P3-1：gate next 输出调度剧本")
        run(["gate", "checkpoint", "vol_01"], cwd=proj, expect=1)  # 卷未 committed

        # ---- P3-2：court 工作区
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
        must(not (proj / "state/court/S1").exists(), "P3-2：close 校验 dec 后清场")

        run(["check", "--project"], cwd=proj)
        print("\nREFACTOR PASS：%d 步全绿" % STEP[0])
        return 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
