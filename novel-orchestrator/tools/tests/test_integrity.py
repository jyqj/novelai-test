#!/usr/bin/env python3
"""Adversarial lifecycle, recovery and historical-memory regression tests.

These are engineering tests; synthetic review evidence is explicitly labelled and
never evidence that a model has written a good novel.
"""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from support import invoke, synthetic_review, save_fixture
from novel_lib.common import dump_frontmatter, parse_frontmatter, read, write, Report
from novel_lib.project import Project
from novel_lib import transactions
from novel_lib.receipts import approval_receipt, checklist
from novel_lib.dependencies import stale_brief
from novel_lib.narrative import effective_knowers, memory_recall, reader_knows
from novel_lib.checks import check_unit
from test_refactor import ARC_STAGED

TOOLS = Path(__file__).resolve().parent.parent
TEXT = "林晚把伞收在门后，雨水敲着地砖。她把铜牌放在桌上，却没有看对面的人。老人转身锁住柜门。"


class IntegrityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="novel-integrity-")
        self.base = Path(self.temp.name)
        self.root = self.base / "book"
        self.run_cli("init", str(self.root), cwd=self.base)
        shutil.rmtree(self.root / ".git")  # Most tests must also work without Git.
        cfg = json.loads(read(self.root / "config.json"))
        cfg.update(word_target=[10, 900], route="traditional")
        write(self.root / "config.json", json.dumps(cfg))
        self.run_cli("tree", "add", "volume", "vol_01")
        self.run_cli("tree", "add", "arc", "arc_01_1")
        write(self.root / "tree/vol_01/arc_01_1.md", ARC_STAGED.replace("status: draft", "status: committed"))
        self.run_cli("entity", "new", "char_linwan")
        self.plan("ch_0001")
        self.run_cli("stage", "enter", "write")
        self.candidate = self.base / "candidate.md"
        self.wbpath = self.base / "writeback.json"
        self.wb = {"summary_after": "铜牌被放到桌上，老人拒绝回答。",
                   "continuity_delta": [{"fact": "林晚带来铜牌", "entity_ids": ["char_linwan"],
                                         "known_by": ["char_linwan"], "spoiler": 0}],
                   "time_advance": {"elapsed": "1天", "story_date": ""}, "thread_ops": [],
                   "payoff_realized": [], "hooks_realized": {"open": True, "close": True},
                   "cast_actual": ["char_linwan"], "issues": [], "word_count": 0}
        self.stage_text()

    def tearDown(self):
        self.assertIsNone(transactions.ACTIVE)
        self.temp.cleanup()

    def run_cli(self, *args, code=0, cwd=None):
        result = invoke(list(args), cwd or self.root)
        self.assertEqual(result.returncode, code, result.stdout + result.stderr)
        return result.stdout + result.stderr

    def plan(self, cid):
        self.run_cli("tree", "add", "chapter", cid, "--parent", "arc_01_1")
        task = {"id": cid, "arc": "arc_01_1", "goal": "拒绝回答", "beats": ["交出铜牌", "锁门"],
                "cast": ["char_linwan"], "threads": [], "payoff_quota": [],
                "hook": {"close": "柜里还有一封信"}}
        write(self.root / "chapters" / (cid + ".task.json"), json.dumps(task, ensure_ascii=False))
        return task

    def stage_text(self, text=TEXT, cid="ch_0001"):
        meta = {"id": cid, "kind": "chapter", "rev": 1, "parent": "arc_01_1", "title": "铜牌"}
        write(self.candidate, dump_frontmatter(meta) + "\n\n## 正文\n" + text)
        write(self.wbpath, json.dumps(self.wb, ensure_ascii=False))

    def task(self, kind="write", cid="ch_0001"):
        return self.run_cli("task", "add", kind, cid).strip().splitlines()[-1]

    def commit(self, task=None):
        task = task or self.task()
        self.run_cli("commit", task, "--chapter", str(self.candidate), "--writeback", str(self.wbpath))
        return task

    def review(self, cid="ch_0001", verdict="pass", depth="light"):
        ev = self.base / "evidence.json"
        write(ev, json.dumps(synthetic_review(self.root, cid), ensure_ascii=False))
        self.run_cli("stage", "enter", "write" if depth == "light" else "review")
        self.run_cli("review", "add", cid, "--depth", depth, "--verdict", verdict, "--evidence", str(ev))
        return ev

    def approve(self, cid="ch_0001"):
        self.review(cid)
        self.run_cli("tree", "set-status", cid, "approved")

    def test_duplicate_creations_do_not_destroy_files(self):
        for command, ident in ((["tree", "add", "chapter"], "ch_0001"),
                               (["tree", "add", "arc"], "arc_01_1"),
                               (["tree", "add", "volume"], "vol_01"),
                               (["entity", "new"], "char_linwan")):
            with self.subTest(ident=ident):
                before = {str(p): p.read_bytes() for p in self.root.rglob("*.md")}
                self.run_cli(*command, ident, code=1)
                self.assertEqual(before, {str(p): p.read_bytes() for p in self.root.rglob("*.md")})
        self.run_cli("thread", "new", "thread_debt")
        self.run_cli("thread", "new", "thread_debt", code=1)

    def test_write_is_first_write_only(self):
        self.commit()
        before = read(self.root / "chapters/ch_0001.md")
        self.run_cli("commit", self.task(), "--chapter", str(self.candidate), "--writeback", str(self.wbpath), code=1)
        self.assertEqual(before, read(self.root / "chapters/ch_0001.md"))

    def test_identical_retry_is_idempotent(self):
        task = self.commit()
        before = {str(p): p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
        self.commit(task)
        self.assertEqual(before, {str(p): p.read_bytes() for p in self.root.rglob("*") if p.is_file()})

    def test_consumed_task_rejects_different_payload(self):
        task = self.commit()
        self.stage_text(TEXT + "柜门又响了一声。")
        self.run_cli("commit", task, "--chapter", str(self.candidate), "--writeback", str(self.wbpath), code=1)
        self.run_cli("task", "start", task, code=1)

    def test_completed_uncommitted_task_cannot_submit(self):
        task = self.task()
        self.run_cli("task", "done", task)
        self.run_cli("commit", task, "--chapter", str(self.candidate), "--writeback", str(self.wbpath), code=1)

    def test_blocked_task_cannot_submit(self):
        parent = self.task("design", "book")
        task = self.run_cli("task", "add", "write", "ch_0001", "--blocked-on", parent).strip().splitlines()[-1]
        self.run_cli("commit", task, "--chapter", str(self.candidate), "--writeback", str(self.wbpath), code=1)

    def test_archived_completed_dependencies_remain_satisfied(self):
        parent = self.task("design", "book")
        self.run_cli("task", "done", parent)
        self.run_cli("task", "archive", "--keep", "0")
        child = self.run_cli("task", "add", "write", "ch_0001", "--blocked-on", parent).strip().splitlines()[-1]
        self.run_cli("task", "list")
        self.assertEqual(Project(self.root).task(child)["state"], "pending")

    def test_candidate_identity_mismatch_rejected(self):
        self.stage_text(cid="ch_0002")
        self.run_cli("commit", self.task(), "--chapter", str(self.candidate), "--writeback", str(self.wbpath), code=1)
        self.assertIsNone(Project(self.root).chapter_meta_json("ch_0001"))

    def test_malformed_writeback_has_no_partial_effects(self):
        for value in ([], {"continuity_delta": "not-array"}, {"continuity_delta": ["not-object"]}):
            with self.subTest(value=value):
                write(self.wbpath, json.dumps(value))
                self.run_cli("commit", self.task(), "--chapter", str(self.candidate), "--writeback", str(self.wbpath), code=1)
                self.assertIsNone(Project(self.root).chapter_meta_json("ch_0001"))

    def test_published_chapter_rejects_write_revise_and_creation(self):
        self.commit()
        self.approve()
        self.run_cli("stage", "enter", "ops")
        self.run_cli("publish", "ch_0001")
        before = read(self.root / "chapters/ch_0001.md")
        self.run_cli("stage", "enter", "write")
        for kind in ("write", "revise"):
            self.run_cli("commit", self.task(kind), "--chapter", str(self.candidate), "--writeback", str(self.wbpath), code=1)
        self.run_cli("tree", "add", "chapter", "ch_0001", "--parent", "arc_01_1", code=1)
        self.run_cli("adopt", str(self.candidate), "--as", "ch_0001", code=1)
        self.assertEqual(before, read(self.root / "chapters/ch_0001.md"))

    def test_published_fingerprint_detects_manual_edit(self):
        self.commit(); self.approve()
        self.run_cli("stage", "enter", "ops"); self.run_cli("publish", "ch_0001")
        path = self.root / "chapters/ch_0001.md"
        write(path, read(path) + "人工修改正文。")
        self.assertIn("已发布正文指纹变化", self.run_cli("fsck", code=1))

    def test_direct_publish_status_transition_is_forbidden(self):
        self.commit(); self.approve()
        self.run_cli("tree", "set-status", "ch_0001", "published", code=1)

    def test_state_transition_runs_mechanical_checks(self):
        self.commit(); self.review()
        cfg = json.loads(read(self.root / "config.json")); cfg["word_target"] = [3000, 5000]
        write(self.root / "config.json", json.dumps(cfg))
        self.run_cli("tree", "set-status", "ch_0001", "approved", code=1)

    def test_no_default_review_pass(self):
        self.commit()
        self.run_cli("review", "add", "ch_0001", "--depth", "light", "--verdict", "pass", code=1)

    def test_pending_or_incomplete_review_evidence_rejected(self):
        self.commit()
        ev = self.base / "evidence.json"
        for mode in ("pending", "missing", "duplicate", "extra-blocker"):
            value = synthetic_review(self.root, "ch_0001")
            if mode == "pending": value["findings"][0]["disposition"] = "pending"
            if mode == "missing": value["findings"] = value["findings"][1:]
            if mode == "duplicate": value["findings"].append(value["findings"][0])
            if mode == "extra-blocker": value["findings"].append({"id": "extra", "disposition": "revise", "rationale": "未解决"})
            write(ev, json.dumps(value))
            self.run_cli("review", "add", "ch_0001", "--depth", "light", "--verdict", "pass", "--evidence", str(ev), code=1)

    def test_same_revision_text_edit_invalidates_receipt(self):
        self.commit(); self.review()
        self.assertTrue(approval_receipt(Project(self.root), "ch_0001"))
        path = self.root / "chapters/ch_0001.md"; write(path, read(path).replace("铜牌", "铁牌"))
        self.assertIsNone(approval_receipt(Project(self.root), "ch_0001"))

    def test_changed_task_or_writeback_invalidates_receipt(self):
        self.commit(); self.review()
        path = self.root / "chapters/ch_0001.meta.json"; value = json.loads(read(path))
        value["summary_after"] = "老人其实答应了。"; write(path, json.dumps(value))
        self.assertIsNone(approval_receipt(Project(self.root), "ch_0001"))

    def test_deep_blocker_overrides_light_pass(self):
        self.commit(); self.review()
        self.review(verdict="escalate", depth="deep")
        self.assertIsNone(approval_receipt(Project(self.root), "ch_0001"))
        self.review(depth="deep")
        self.assertTrue(approval_receipt(Project(self.root), "ch_0001"))
        self.assertTrue(list((self.root / "reviews/history").glob("*.md")))

    def test_publish_revalidates_review_after_approval(self):
        self.commit(); self.approve()
        path = self.root / "chapters/ch_0001.md"; write(path, read(path) + "柜门响了。")
        self.run_cli("stage", "enter", "ops")
        self.run_cli("publish", "ch_0001", code=1)

    def test_revise_bumps_revision_and_invalidates_old_review(self):
        self.commit(); self.approve()
        self.stage_text(TEXT + "他没有回头。")
        self.commit(self.task("revise"))
        meta, _ = parse_frontmatter(read(self.root / "chapters/ch_0001.md"))
        self.assertEqual(meta["rev"], 2)
        self.assertIsNone(approval_receipt(Project(self.root), "ch_0001"))

    def test_staged_traversal_and_duplicate_target_rejected(self):
        self.run_cli("stage", "enter", "s1")
        file = self.base / "bad.md"
        write(file, "---\nid: ../outside\nkind: entity\n---\nBad")
        task = self.task("design", "book")
        self.run_cli("commit", task, "--file", str(file), code=1)
        self.assertFalse((self.root / "outside.md").exists())
        write(file, "---\nid: char_new\nkind: entity\n---\nNew")
        self.run_cli("commit", task, "--file", str(file), "--file", str(file), code=1)
        self.assertFalse((self.root / "entities/char_new.md").exists())

    def test_staged_review_cannot_bypass_evidence(self):
        self.commit(); self.run_cli("stage", "enter", "review")
        path = self.base / "review.md"
        write(path, "---\nid: review_ch_0001_deep\nkind: review\nchapter: ch_0001\ndepth: deep\nverdict: pass\nrev_reviewed: 1\n---\n## 问题清单\n通过")
        self.run_cli("commit", self.task("review_deep"), "--file", str(path), code=1)

    def test_exception_rolls_back_touched_files(self):
        task = self.task()
        before = {str(p): p.read_bytes() for p in self.root.rglob("*") if p.is_file() and "state/txn" not in str(p)}
        original = transactions.atomic_bytes
        failed = [False]
        def fail_once(path, data):
            # safe_path() resolves symlinks (macOS /var/folders -> /private/var), so compare resolved.
            if Path(path) == (self.root / "chapters/ch_0001.md").resolve() and not failed[0]:
                failed[0] = True
                raise OSError("injected write failure")
            return original(path, data)
        with patch.object(transactions, "atomic_bytes", side_effect=fail_once):
            self.run_cli("commit", task, "--chapter", str(self.candidate), "--writeback", str(self.wbpath), code=1)
        after = {str(p): p.read_bytes() for p in self.root.rglob("*") if p.is_file() and "state/txn" not in str(p)}
        self.assertEqual(before, after)
        self.assertFalse(transactions.pending(self.root))
        self.commit(task)

    def crash(self):
        write(self.root / "state/recover-target.txt", "before")
        source = "from pathlib import Path; import os; from novel_lib.transactions import execute; from novel_lib.common import write; r=Path(%r); execute(r,'crash',lambda: (write(r/'state/recover-target.txt','after'),os._exit(71)))" % str(self.root)
        result = subprocess.run([sys.executable, "-c", source], env=dict(os.environ, PYTHONPATH=str(TOOLS)), capture_output=True, timeout=10)
        self.assertEqual(result.returncode, 71, result.stderr)

    def test_process_death_can_be_recovered_and_recovery_is_repeatable(self):
        self.crash()
        self.assertTrue(transactions.pending(self.root))
        self.run_cli("task", "add", "write", "ch_0001", code=1)
        self.run_cli("recover", "--rollback")
        self.run_cli("recover", "--rollback")
        self.assertEqual(read(self.root / "state/recover-target.txt"), "before")

    def test_recovery_preserves_conflicting_author_edit(self):
        self.crash()
        write(self.root / "state/recover-target.txt", "author edit")
        self.run_cli("recover", "--rollback", code=1)
        self.assertEqual(read(self.root / "state/recover-target.txt"), "author edit")

    def test_concurrent_writer_fails_without_mutation(self):
        with transactions.project_lock(self.root):
            result = subprocess.run([sys.executable, str(TOOLS / "novel.py"), "--root", str(self.root),
                                     "task", "add", "write", "ch_0001"], capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 1)
        self.assertIn("另一命令", result.stderr)

    def test_git_does_not_absorb_unrelated_author_file(self):
        subprocess.run(["git", "init", "-q", str(self.root)], check=True)
        save_fixture(self.root)
        write(self.root / "author-notes.md", "Do not stage me")
        self.run_cli("stage", "enter", "review")
        status = subprocess.run(["git", "-C", str(self.root), "status", "--porcelain"], capture_output=True, text=True, check=True).stdout
        self.assertIn("?? author-notes.md", status)

    def test_entity_relationships_not_lost_after_fourteen_lines(self):
        path = self.root / "entities/char_linwan.md"
        write(path, read(path).replace("[关系]", "她感到受辱而不是感激"))
        self.run_cli("brief", "ch_0001")
        self.assertIn("她感到受辱而不是感激", read(self.root / "briefs/ch_0001.brief.md"))

    def test_historical_brief_excludes_future_state_and_fact(self):
        self.commit(); self.plan("ch_0002")
        path = self.root / "entities/char_linwan.md"
        text = read(path).replace("last_reconcile_ch: 0", "last_reconcile_ch: 90")
        text = text.replace("[当前所在]", "未来皇城") + "\n- ch_0090: 她登基了。\n"
        write(path, text)
        facts = self.root / "ledgers/facts/vol_01.json"; data = json.loads(read(facts))
        data["facts"].append({"id": "fact_9999", "fact": "未来秘密", "entity_ids": ["char_linwan"], "revealed_ch": 90, "spoiler": 0})
        write(facts, json.dumps(data, ensure_ascii=False))
        self.run_cli("brief", "ch_0002")
        brief = read(self.root / "briefs/ch_0002.brief.md")
        self.assertNotIn("未来皇城", brief); self.assertNotIn("她登基了", brief); self.assertNotIn("未来秘密", brief)
        self.assertIn("历史快照缺失", brief)

    def test_fact_recall_by_knower_and_required_id_not_only_cast(self):
        self.commit(); task = self.plan("ch_0002")
        factpath = self.root / "ledgers/facts/vol_01.json"; data = json.loads(read(factpath))
        data["facts"][0]["entity_ids"] = ["fac_absent"]
        write(factpath, json.dumps(data, ensure_ascii=False))
        self.run_cli("brief", "ch_0002")
        self.assertIn("林晚带来铜牌", read(self.root / "briefs/ch_0002.brief.md"))
        task["fact_refs"] = ["fact_9999"]; write(self.root / "chapters/ch_0002.task.json", json.dumps(task))
        self.run_cli("brief", "ch_0002", code=1)

    def test_memory_requires_exact_prose_evidence(self):
        self.wb["narrative_memory"] = [{"kind": "relationship", "text": "她感到受辱", "evidence": "并不存在的句子", "entity_ids": ["char_linwan"]}]
        self.stage_text()
        self.run_cli("commit", self.task(), "--chapter", str(self.candidate), "--writeback", str(self.wbpath), code=1)

    def test_recall_preserves_middle_arc_relationship(self):
        self.wb["narrative_memory"] = [{"kind": "relationship", "text": "她觉得交出铜牌是受辱而非求助", "evidence": "却没有看对面的人", "entity_ids": ["char_linwan"]}]
        self.stage_text(); self.commit()
        task = self.plan("ch_0020"); task["memory_refs"] = ["ch_0001#0"]
        write(self.root / "chapters/ch_0020.task.json", json.dumps(task))
        self.run_cli("brief", "ch_0020")
        brief = read(self.root / "briefs/ch_0020.brief.md")
        self.assertIn("受辱而非求助", brief); self.assertIn("ch_0001#0", brief)

    def test_readers_historical_knowledge(self):
        fact = {"spoiler": 0, "revealed_reader_ch": 180}
        self.assertFalse(reader_knows(fact, 50)); self.assertTrue(reader_knows(fact, 180))

    def test_leaving_group_does_not_erase_knowledge(self):
        self.commit()
        self.run_cli("entity", "new", "fac_group"); self.run_cli("entity", "new", "char_peer")
        self.run_cli("knowledge", "scope", "add", "fac_group", "char_peer")
        self.run_cli("knowledge", "grant", "fact_0001", "--to", "fac_group", "--ch", "ch_0002")
        self.run_cli("knowledge", "scope", "remove", "fac_group", "char_peer")
        proj = Project(self.root); fact = proj.all_facts()[0][0]
        self.assertNotIn("char_peer", effective_knowers(proj, fact, 1))
        self.assertIn("char_peer", effective_knowers(proj, fact, 2))

    def test_budget_overflow_preserves_last_good_brief(self):
        self.run_cli("brief", "ch_0001")
        before = read(self.root / "briefs/ch_0001.brief.md")
        cfg = json.loads(read(self.root / "config.json")); cfg["brief_budget_chars"] = 100
        write(self.root / "config.json", json.dumps(cfg))
        self.run_cli("brief", "ch_0001", code=1)
        self.assertEqual(before, read(self.root / "briefs/ch_0001.brief.md"))

    def test_brief_dependency_hash_not_mtime(self):
        self.run_cli("brief", "ch_0001")
        self.assertFalse(stale_brief(Project(self.root), "ch_0001"))
        path = self.root / "tree/world.md"; timestamp = path.stat().st_mtime_ns
        write(path, read(path) + "\n规则变更\n"); os.utime(path, ns=(timestamp, timestamp))
        self.assertIn("tree/world.md", stale_brief(Project(self.root), "ch_0001"))

    def test_brief_source_set_addition_invalidates_manifest(self):
        self.run_cli("brief", "ch_0001")
        self.run_cli("entity", "new", "char_new")
        self.assertIn("entities/char_new.md", stale_brief(Project(self.root), "ch_0001"))

    def test_rhetorical_repetition_is_not_universal_hard_failure(self):
        self.stage_text("她说不要。她说没有。她说不必。雨还在下，门后却无人回答。")
        report = check_unit(Project(self.root), "ch_0001", str(self.candidate), str(self.wbpath))
        self.assertTrue(any(level == "WARN" and "同首" in name for level, name, _, _ in report.items))
        self.assertFalse(any(level == "FAIL" and "同首" in name for level, name, _, _ in report.items))

    def test_bounded_cross_stage_knowledge_consultation(self):
        before = read(TOOLS.parent / "knowledge-map.md")
        out = self.run_cli("stage", "consult", "K-CONCEPT-001", "--target", "ch_0001", "--reason", "人物行动缺少可展开的核心冲突")
        self.assertIn("高概念", out)
        self.assertEqual(before, read(TOOLS.parent / "knowledge-map.md"))
        history = json.loads(read(self.root / "state/knowledge-consults.json"))
        self.assertEqual(history[-1]["stage"], "write")
        self.assertIn("sha256", history[-1]["sources"]["K-CONCEPT-001"])
        self.run_cli("stage", "consult", "K-CONCEPT-001", "K-CONCEPT-002", "K-CONCEPT-003",
                     "--target", "ch_0001", "--reason", "过量阅读", code=1)
        self.run_cli("stage", "consult", "K-GHOST-999", "--target", "ch_0001", "--reason", "缺失知识块", code=1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
