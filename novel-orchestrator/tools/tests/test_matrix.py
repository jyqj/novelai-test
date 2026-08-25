#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""知识矩阵 v2 专项测试（P8-M，stdlib only）。

覆盖：
  M1 scope CLI：知情圈增删查（fac/loc/item → char 成员）+ 类型/登记负例
  M2 阶段闸门：scope add/remove 受辖 write|review（未进阶段被拒）；scope list 不受辖
  M3 grant 范围授予：known_by 收群体条目；空圈提醒；query --fact 圈展开显示
  M4 query 展开：个体经圈知情（标「经 X 圈」）/ 展开后不知情 / 群体视图列圈成员
  M5 简报注入：【知情仅】显示圈成员；在场不知情名单按展开后计算（圈成员不误报）
  M6 抽取器越界：有效知情集=个体+圈展开——圈成员明写不报，圈外在场报 NEEDS_REVIEW；
     入圈后候选消失
  M7 check --project：scopes.json 圈键/成员非法 FAIL；known_by 引用空圈 WARN

运行：python3 tools/tests/test_matrix.py
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
    print("OK %02d: novel.py %s (exit=%d)" % (STEP[0], " ".join(args[:6]), r.returncode))
    return r.stdout + r.stderr


def must(cond, msg):
    if not cond:
        print("FAILED 断言: " + msg)
        sys.exit(1)
    STEP[0] += 1
    print("OK %02d: %s" % (STEP[0], msg))


FACTS = {"facts": [
    {"id": "fact_000001", "fact": "青铜印藏于当铺暗格", "entity_ids": ["char_linwan"],
     "revealed_ch": 1, "spoiler": 1, "superseded_by": None, "key": "知晓"},
    {"id": "fact_000002", "fact": "城南水道每逢子时换防", "entity_ids": ["loc_capital"],
     "revealed_ch": 1, "spoiler": 0, "superseded_by": None},
]}

TASK2 = {
    "id": "ch_0002", "arc": "arc_01_1", "goal": "对峙与试探",
    "beats": ["入城", "对峙", "脱身"],
    "hook": {"open": None, "close": "巷口暗号"},
    "payoff_quota": [], "threads": [],
    "cast": ["char_linwan", "char_member", "char_rival"],
    "word_target": [300, 800],
}

TEXT2 = """林晚贴着墙根走进巷子，斗篷压得很低。
迎面的汉子凑近，声音压得极低。
「青铜印藏于当铺暗格。」
林晚按住他的手腕：「慎言。」
巷口的灯笼晃了三下，是撤离的暗号。"""


def envelope(ch_id, text, title="测试章"):
    return ("---\nid: %s\nkind: chapter\nstatus: drafted\nrev: 1\nparent: arc_01_1\n"
            "updated_at: 2026-08-25T00:00:00\ntitle: %s\nword_count: 0\n---\n\n"
            "## 正文\n\n%s\n" % (ch_id, title, text))


def main():
    tmp = Path(tempfile.mkdtemp(prefix="novel_matrix_"))
    try:
        proj = tmp / "book_m"
        run(["init", str(proj), "--name", "矩阵之书"], cwd=tmp)
        for eid in ("char_linwan", "char_member", "char_rival", "char_guard",
                    "fac_shadow", "loc_capital", "item_seal"):
            run(["entity", "new", eid], cwd=proj)
        (proj / "entities/aliases.json").write_text(
            json.dumps({"影阁": "fac_shadow", "林晚": "char_linwan"},
                       ensure_ascii=False), encoding="utf-8")

        # M2 阶段闸门：未进任何阶段 → scope add 被拒；scope list 不受辖
        out = run(["knowledge", "scope", "add", "fac_shadow", "char_member"],
                  cwd=proj, expect=1)
        must("阶段闸门" in out and "stage enter" in out,
             "M2 未进阶段 scope add 被拒 + enter 提示")
        out = run(["knowledge", "scope", "list"], cwd=proj)
        must("无知情圈" in out, "M2 scope list 不受辖（空圈提示）")
        run(["stage", "enter", "write"], cwd=proj)

        # M1 scope CLI：类型/登记负例 + 增删查（别名可解析）
        out = run(["knowledge", "scope", "add", "fac_ghost", "char_member"],
                  cwd=proj, expect=1)
        must("群体未登记" in out, "M1 未登记群体被拒")
        out = run(["knowledge", "scope", "add", "char_linwan", "char_member"],
                  cwd=proj, expect=1)
        must("只挂 fac_/loc_/item_" in out, "M1 个体当群体被拒")
        out = run(["knowledge", "scope", "add", "fac_shadow", "loc_capital"],
                  cwd=proj, expect=1)
        must("须为 char_" in out, "M1 非 char 成员被拒")
        run(["knowledge", "scope", "add", "影阁", "char_member", "char_rival"],
            cwd=proj)
        out = run(["knowledge", "scope", "list", "fac_shadow"], cwd=proj)
        must("char_member" in out and "char_rival" in out,
             "M1 scope add 经别名解析入圈")
        out = run(["knowledge", "scope", "remove", "fac_shadow", "char_guard"],
                  cwd=proj, expect=1)
        must("不在 fac_shadow 圈内" in out, "M1 除名非成员被拒")
        run(["knowledge", "scope", "remove", "fac_shadow", "char_rival"], cwd=proj)
        scopes = json.loads((proj / "entities/scopes.json").read_text(encoding="utf-8"))
        must(scopes == {"fac_shadow": ["char_member"]},
             "M1 scopes.json 台账 = {fac_shadow: [char_member]}")

        # M3 grant 范围授予：空圈提醒 + known_by 收群体 + --fact 圈展开显示
        facts_p = proj / "ledgers/facts/vol_01.json"
        facts_p.parent.mkdir(parents=True, exist_ok=True)
        facts_p.write_text(json.dumps(FACTS, ensure_ascii=False), encoding="utf-8")
        out = run(["knowledge", "grant", "fact_000001", "--to", "loc_capital"],
                  cwd=proj)
        must("知情圈为空" in out and "scope add loc_capital" in out,
             "M3 范围授予空圈 → 编圈提醒")
        run(["knowledge", "scope", "add", "loc_capital", "char_guard"], cwd=proj)
        run(["knowledge", "grant", "fact_000001", "--to", "影阁",
             "--to", "char_linwan", "--ch", "ch_0002"], cwd=proj)
        out = run(["knowledge", "query", "--fact", "fact_000001"], cwd=proj)
        must("fac_shadow圈(char_member)" in out and "loc_capital圈(char_guard)" in out
             and "char_linwan" in out,
             "M3 query --fact 知情名单按圈展开显示")

        # M4 query 展开：个体经圈 / 展开后不知情 / 群体视图
        out = run(["knowledge", "query", "--entity", "char_member"], cwd=proj)
        must("所属知情圈：fac_shadow" in out and "知情 1 条" in out
             and "经 fac_shadow 圈" in out,
             "M4 个体经圈知情（标注来源圈）")
        out = run(["knowledge", "query", "--entity", "char_rival"], cwd=proj)
        must("不知情 1 条" in out and "fac_shadow圈(char_member)" in out,
             "M4 圈外个体展开后不知情")
        out = run(["knowledge", "query", "--entity", "fac_shadow"], cwd=proj)
        must("知情圈成员：char_member" in out and "知情 1 条" in out,
             "M4 群体视图列圈成员与知情")

        # M5 简报注入：圈展开显示 + 在场不知情按展开计算
        (proj / "chapters/ch_0002.task.json").write_text(
            json.dumps(TASK2, ensure_ascii=False, indent=1), encoding="utf-8")
        run(["brief", "ch_0002"], cwd=proj)
        brief = (proj / "briefs/ch_0002.brief.md").read_text(encoding="utf-8")
        must("fac_shadow圈(char_member)" in brief,
             "M5 简报【知情仅】按圈展开显示")
        must("char_rival 不知情" in brief and "char_member 不知情" not in brief,
             "M5 在场不知情名单按展开计算（圈成员不误报）")

        # M6 抽取器越界：圈成员明写不报；圈外在场 → NEEDS_REVIEW；入圈后消失
        cand = tmp / "c2.md"
        cand.write_text(envelope("ch_0002", TEXT2, title="对峙"), encoding="utf-8")
        wbf = tmp / "wb2.json"
        wbf.write_text(json.dumps(
            {"cast_actual": ["char_linwan", "char_member", "char_rival"]},
            ensure_ascii=False), encoding="utf-8")
        out = run(["extract", "ch_0002", "--candidate", str(cand),
                   "--writeback", str(wbf)], cwd=proj)
        must("角色知识越界候选" in out and "char_rival" in out,
             "M6 圈外在场角色明写事实 → 越界候选")
        must("在场未知情角色：char_rival（" in out,
             "M6 圈成员 char_member 不误报（有效知情集展开）")
        run(["knowledge", "scope", "add", "fac_shadow", "char_rival"], cwd=proj)
        out = run(["extract", "ch_0002", "--candidate", str(cand),
                   "--writeback", str(wbf)], cwd=proj)
        must("角色知识越界候选" not in out, "M6 scope add 入圈后越界候选消失")

        # M7 check --project：空圈 WARN；圈键/成员非法 FAIL
        run(["knowledge", "grant", "fact_000002", "--to", "item_seal"], cwd=proj)
        out = run(["check", "--project"], cwd=proj)
        must("空知情圈" in out and "item_seal" in out,
             "M7 known_by 引用空知情圈 → WARN")
        good = (proj / "entities/scopes.json").read_text(encoding="utf-8")
        (proj / "entities/scopes.json").write_text(
            json.dumps({"fac_shadow": ["char_ghost"], "thread_x": ["char_linwan"]},
                       ensure_ascii=False), encoding="utf-8")
        out = run(["check", "--project"], cwd=proj, expect=1)
        must("知情圈台账" in out and "char_ghost" in out and "thread_x" in out,
             "M7 圈键/成员非法 → FAIL")
        (proj / "entities/scopes.json").write_text(good, encoding="utf-8")
        run(["check", "--project"], cwd=proj)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("\nMATRIX PASS：%d 步全绿（知识矩阵 v2：范围知情圈全链路）" % STEP[0])


if __name__ == "__main__":
    main()
