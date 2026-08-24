#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""novel.py 长程合成烟测（P2-9 可选项）：模拟 35 章连载全链路。

验证规模化不变量：
  - 每章 write→check→commit→review 回执→approved→publish 全链可循环
  - payoff 3 章/10 章窗口全程保持绿（构造配额与 realized）
  - facts 随章累积且 fact_id 全局递增无碰撞
  - ngram_cache 按 ngram_window_chapters 裁剪（两级指纹）
  - entity due 在 reconcile_every 阈值后出现
  - published 连续性、check --project 全绿、task archive 收缩队列
  - status（章级增量 index）在 35 章规模可重复运行

文本为随机汉字合成（固定 seed），避开黑名单与重复类告警属统计必然而非构造欺骗。
运行：python3 tools/tests/test_longrun.py
"""
import json
import random
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

TOOLS = Path(__file__).resolve().parent.parent
NOVEL = TOOLS / "novel.py"
N_CH = 35
POOL = ("山川湖海风云雷电草木虫鱼刀剑弓马城池关隘商旅僧道灯火桥井坊市炉鼎符纸茶酒"
        "盐铁布帛信函令牌车辙蹄印晨昏星斗霜雪雾雨春秋冬夏南北东西高低远近明暗轻重"
        "缓急走停坐卧问答呼吸看听闻触推拉抬放折断缝补烧煮埋挖抄写读画敲磨洗晒")
KIND_CYCLE = ["dopamine", "upgrade", "emotion", "reveal", "humor", "reversal"]


def run(args, cwd, expect=0):
    r = subprocess.run([sys.executable, str(NOVEL)] + args,
                       cwd=str(cwd), capture_output=True, text=True)
    if r.returncode != expect:
        print("LONGRUN FAILED: novel.py %s\nexit=%d (期望 %d)\n%s\n%s"
              % (" ".join(args[:6]), r.returncode, expect, r.stdout[-2000:], r.stderr[-800:]))
        sys.exit(1)
    return r.stdout


def must(cond, msg):
    if not cond:
        print("LONGRUN FAILED 断言: " + msg)
        sys.exit(1)
    print("OK: " + msg)


def gen_text(seed, n_sent=42):
    rng = random.Random(seed)
    sents = []
    for _ in range(n_sent):
        ln = rng.randint(8, 14)
        sents.append("".join(rng.choice(POOL) for _ in range(ln)) + "。")
    paras, i = [], 0
    while i < len(sents):
        k = rng.randint(2, 4)
        paras.append("".join(sents[i:i + k]))
        i += k
    return "\n".join(paras)


def main():
    tmp = Path(tempfile.mkdtemp(prefix="novel_long_"))
    try:
        proj = tmp / "longbook"
        run(["init", str(proj), "--name", "长程之书"], cwd=tmp)
        cfg = json.loads((proj / "config.json").read_text(encoding="utf-8"))
        cfg["word_target"] = [300, 900]
        cfg["ngram_window_chapters"] = 8
        cfg["reconcile_every"] = 10
        (proj / "config.json").write_text(json.dumps(cfg, ensure_ascii=False, indent=2),
                                          encoding="utf-8")
        run(["tree", "add", "volume", "vol_01"], cwd=proj)
        run(["tree", "add", "arc", "arc_01_1"], cwd=proj)
        run(["tree", "add", "arc", "arc_01_2"], cwd=proj)
        run(["entity", "new", "char_hero"], cwd=proj)
        run(["thread", "new", "thread_main", "--kind", "promise"], cwd=proj)
        run(["thread", "new", "thread_vow", "--kind", "promise"], cwd=proj)

        for n in range(1, N_CH + 1):
            cid = "ch_%04d" % n
            arc = "arc_01_1" if n <= 18 else "arc_01_2"
            run(["tree", "add", "chapter", cid, "--parent", arc], cwd=proj)
            kind = KIND_CYCLE[(n - 1) % len(KIND_CYCLE)]
            task = {"id": cid, "arc": arc, "goal": "第 %d 章推进" % n,
                    "beats": ["起", "承", "转"],
                    "hook": {"open": None, "close": "章尾钩 %d" % n},
                    "payoff_quota": [{"kind": kind, "intent": "第 %d 章兑现" % n}],
                    "threads": [], "cast": ["char_hero"],
                    "word_target": [300, 900]}
            (proj / ("chapters/%s.task.json" % cid)).write_text(
                json.dumps(task, ensure_ascii=False, indent=1), encoding="utf-8")
            tid = run(["task", "add", "write", cid], cwd=proj).strip().splitlines()[-1]
            run(["task", "start", tid], cwd=proj)
            text = gen_text(1000 + n)
            cand = tmp / ("cand_%s.md" % cid)
            cand.write_text("---\nid: %s\nkind: chapter\nstatus: drafted\nrev: 1\n"
                            "parent: %s\nupdated_at: 2026-08-24T00:00:00\n"
                            "title: 第%d章\nword_count: 0\n---\n\n## 正文\n\n%s\n"
                            % (cid, arc, n, text), encoding="utf-8")
            wc = len("".join(text.split()))
            ops = []
            if n == 1:
                ops = [{"id": "thread_main", "op": "plant", "note": "主线埋设"},
                       {"id": "thread_vow", "op": "plant", "note": "誓约埋设"}]
            elif n % 5 == 0:
                ops = [{"id": "thread_main", "op": "advance", "note": "第 %d 章推进" % n},
                       {"id": "thread_vow", "op": "advance", "note": "第 %d 章推进" % n}]
            wb = {"summary_after": "第 %d 章后：主角推进一步。" % n,
                  "continuity_delta": ([{"fact": "第 %d 章主角获得线索甲%d" % (n, n),
                                         "entity_ids": ["char_hero"], "spoiler": 0}]
                                       if n % 3 == 0 else []),
                  "time_advance": {"elapsed": "1天", "story_date": ""},
                  "thread_ops": ops,
                  "payoff_realized": ["payoff_%04d_1" % n],
                  "hooks_realized": {"open": True, "close": True},
                  "cast_actual": ["char_hero"],
                  "power_delta": ([{"entity_ids": ["char_hero"],
                                    "from": "第%d阶" % (n // 12),
                                    "to": "第%d阶" % (n // 12 + 1), "note": "升阶"}]
                                  if n % 12 == 0 else []),
                  "issues": [], "word_count": wc}
            wbf = tmp / ("wb_%s.json" % cid)
            wbf.write_text(json.dumps(wb, ensure_ascii=False), encoding="utf-8")
            run(["commit", tid, "--chapter", str(cand), "--writeback", str(wbf),
                 "-m", "长程第 %d 章" % n], cwd=proj)
            run(["task", "done", tid, "--note", "light=pass"], cwd=proj)
            run(["tree", "set-status", cid, "approved"], cwd=proj)
            run(["publish", cid], cwd=proj)

        # ---- 不变量断言
        out = run(["status"], cwd=proj)
        must("last_published=%d" % N_CH in out, "35 章全部发布，游标一致")
        run(["check", "--window"], cwd=proj)
        run(["check", "--window", "--since", "ch_%04d" % (N_CH - 10)], cwd=proj)
        run(["check", "--project"], cwd=proj)

        cache = json.loads((proj / "state/ngram_cache.json").read_text(encoding="utf-8"))
        must(len(cache) == 8, "ngram_cache 按窗口裁剪至 8 章（实际 %d）" % len(cache))
        must(all(isinstance(v, dict) and "n12" in v and "n8" in v for v in cache.values()),
             "两级指纹（n12+n8）齐全")

        facts = json.loads((proj / "ledgers/facts/vol_01.json").read_text(encoding="utf-8"))
        ids = [f["id"] for f in facts["facts"]]
        must(len(ids) == N_CH // 3 and len(set(ids)) == len(ids),
             "facts 累积 %d 条且 fact_id 无碰撞" % len(ids))

        due = run(["entity", "due"], cwd=proj)
        must("char_hero" in due, "entity due：reconcile_every 阈值后实体到期")

        power = (proj / "ledgers/power.tsv").read_text(encoding="utf-8")
        must(power.count("char_hero") == 2, "power 台账累积 2 次升阶")

        before = len(json.loads((proj / "tasks/queue.json")
                                .read_text(encoding="utf-8"))["tasks"])
        run(["task", "archive", "--keep", "5"], cwd=proj)
        after = len(json.loads((proj / "tasks/queue.json")
                               .read_text(encoding="utf-8"))["tasks"])
        must(after < before and after <= 5, "task archive 收缩队列 %d → %d" % (before, after))

        print("\nLONGRUN PASS：%d 章全链循环 + 规模化不变量全绿" % N_CH)
        return 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
