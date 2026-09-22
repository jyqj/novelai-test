#!/usr/bin/env python3
"""Source transport and instruction consistency; not a literary quality test."""
import json
import unittest
from pathlib import Path

import test_methodology as fixtures
from support import invoke
from novel_lib.common import read, write, dump_frontmatter
from novel_lib.project import Project
from novel_lib.evidence import recall_evidence, evidence_specs
from novel_lib.dependencies import stale_brief

SKILL = Path(__file__).resolve().parents[2]
QUOTE = '门簿上记的是铜铃，不是人。'


class EvidenceTests(unittest.TestCase):
    def setUp(self):
        self.f = fixtures.MethodologyTests()
        self.f.setUp()
        self.addCleanup(self.f.tearDown)
        self.root = self.f.root
        self.source = self.root / 'chapters/ch_0001.md'
        self.source_text = (dump_frontmatter({'id': 'ch_0001', 'kind': 'chapter',
                            'status': 'drafted', 'rev': 1, 'parent': 'arc_01_1'})
                            + '\n## 正文\n雨水滴在桌上。\n' + QUOTE
                            + '\n守门人把那只铜铃重新挂好。\n')
        write(self.source, self.source_text)
        self.f.cli('tree', 'add', 'chapter', 'ch_0020', '--parent', 'arc_01_1')
        self.task = dict(self.f.task, id='ch_0020', evidence_refs=[
            {'chapter': 'ch_0001', 'quote': QUOTE, 'purpose': '重释导师出城记录'}])
        self.save()

    def save(self):
        write(self.root / 'chapters/ch_0020.task.json', json.dumps(self.task, ensure_ascii=False))

    def recall(self):
        return recall_evidence(Project(self.root), self.task, 19)

    def compile(self, success=True):
        self.save()
        r = invoke(['brief', 'ch_0020'], self.root)
        if success:
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        else:
            self.assertNotEqual(r.returncode, 0, r.stdout + r.stderr)
        return r.stdout + r.stderr

    def test_optional_no_refs_preserves_old_tasks(self):
        self.assertEqual(recall_evidence(Project(self.root), {}, 19), [])
        self.task.pop('evidence_refs'); self.compile()
        self.assertNotIn('原文证据 chapters/ch_0001.md', read(self.root / 'briefs/ch_0020.brief.md'))

    def test_distant_quote_and_context_reach_writer(self):
        self.compile()
        brief = read(self.root / 'briefs/ch_0020.brief.md')
        self.assertIn(QUOTE, brief)
        self.assertIn('雨水滴在桌上。', brief)
        self.assertIn('原文证据 chapters/ch_0001.md', brief)
        self.assertIn('不自动等于世界真相或角色知情', brief)
        manifest = json.loads(read(self.root / 'briefs/ch_0020.manifest.json'))
        self.assertIn('chapters/ch_0001.md', manifest['sources'])
        self.assertIn('evidence:0', manifest['retained'])
        self.assertFalse(stale_brief(Project(self.root), 'ch_0020'))

    def test_current_and_future_chapters_rejected(self):
        for cid in ['ch_0020', 'ch_0021']:
            with self.subTest(cid=cid):
                self.task['evidence_refs'][0]['chapter'] = cid
                with self.assertRaisesRegex(ValueError, '未来'):
                    self.recall()

    def test_missing_or_planned_source_rejected(self):
        self.source.unlink()
        with self.assertRaisesRegex(ValueError, '不存在'):
            self.recall()
        write(self.source, self.source_text.replace('status: drafted', 'status: planned'))
        with self.assertRaisesRegex(ValueError, '已写'):
            self.recall()

    def test_frontmatter_is_not_body_evidence(self):
        self.task['evidence_refs'][0]['quote'] = 'status: drafted'
        with self.assertRaisesRegex(ValueError, '不在原章节正文'):
            self.recall()

    def test_duplicate_quote_needs_explicit_occurrence(self):
        write(self.source, self.source_text + '\n多年以后，她又说：' + QUOTE + '\n')
        with self.assertRaisesRegex(ValueError, '重复'):
            self.recall()
        self.task['evidence_refs'][0].update(occurrence=2, context_chars=12)
        item = self.recall()[0]
        self.assertIn('多年以后', item['excerpt'])
        self.assertEqual(item['occurrence'], 2)
        self.task['evidence_refs'][0]['occurrence'] = 3
        with self.assertRaisesRegex(ValueError, '超出'):
            self.recall()

    def test_line_range_is_real_source_location(self):
        self.task['evidence_refs'][0]['context_chars'] = 0
        item = self.recall()[0]
        self.assertEqual(item['excerpt'], QUOTE)
        expected = self.source_text[:self.source_text.index(QUOTE)].count('\n') + 1
        self.assertEqual(item['line_start'], expected)
        self.assertEqual(item['line_end'], expected)

    def test_malformed_refs_fail_clearly(self):
        base = {'chapter': 'ch_0001', 'quote': QUOTE}
        bad = [None, {}, 'chapter', [None], [dict(base, occurrence=True)],
               [dict(base, occurrence=0)], [dict(base, occurrence=None)],
               [dict(base, context_chars=True)], [dict(base, context_chars=2001)],
               [dict(base, chapter='../secrets')], [dict(base, chapter='ch_0000')],
               [dict(base, quote='  ')], [dict(base, purpose=3)],
               [dict(base, context_char=5)]]
        for refs in bad:
            with self.subTest(refs=refs):
                with self.assertRaises(ValueError):
                    evidence_specs({'evidence_refs': refs})

    def test_source_revision_invalidates_even_if_summary_is_unchanged(self):
        self.compile()
        write(self.source, self.source_text.replace('雨水滴在桌上。', '阳光落在桌上。'))
        self.assertIn('chapters/ch_0001.md', stale_brief(Project(self.root), 'ch_0020'))

    def test_removed_quote_does_not_overwrite_previous_brief(self):
        self.compile()
        brief = read(self.root / 'briefs/ch_0020.brief.md')
        manifest = read(self.root / 'briefs/ch_0020.manifest.json')
        write(self.source, self.source_text.replace(QUOTE, '记录已经改过。'))
        self.assertIn('不在原章节正文', self.compile(False))
        self.assertEqual(brief, read(self.root / 'briefs/ch_0020.brief.md'))
        self.assertEqual(manifest, read(self.root / 'briefs/ch_0020.manifest.json'))

    def test_required_evidence_is_not_silently_dropped_for_budget(self):
        self.compile()
        old = read(self.root / 'briefs/ch_0020.brief.md')
        long_quote = '很久以前的一段完整关键回忆。' * 500
        write(self.source, self.source_text + long_quote)
        self.task['evidence_refs'][0]['quote'] = long_quote
        config = json.loads(read(self.root / 'config.json')); config['brief_budget_chars'] = 5000
        write(self.root / 'config.json', json.dumps(config))
        self.assertIn('预算', self.compile(False))
        self.assertEqual(old, read(self.root / 'briefs/ch_0020.brief.md'))

    def test_recall_never_writes_canon_or_knowledge(self):
        paths = [p for folder in ['entities', 'ledgers', 'threads']
                 for p in (self.root / folder).rglob('*') if p.is_file()]
        before = {str(p): p.read_bytes() for p in paths}
        self.recall()
        self.assertEqual(before, {str(p): p.read_bytes() for p in paths})

    def test_runtime_cards_no_longer_reinstate_removed_rules(self):
        architect = read(SKILL / 'roles/architect.md')
        editor = read(SKILL / 'roles/editor.md')
        stage = read(SKILL / 'protocol/stages/write-loop.md')
        for old in ['主线引擎必须 ≥gold', '支线总篇幅 ≤30%', '重要信息至少暗示三次']:
            self.assertNotIn(old, architect)
        self.assertNotIn('强制定稿轮禁止再标 blocking', editor)
        self.assertNotIn('knowledge/ 在本阶段对所有角色关闭', stage)

    def test_example_task_fragment_matches_supported_refs(self):
        fragment = json.loads(read(SKILL / 'examples/bell-evidence-task.json'))
        self.task.update(fragment)
        self.assertEqual(self.recall()[0]['quote'], QUOTE)
        self.compile()
        self.assertIn('已经看见铜铃可以转交', read(self.root / 'briefs/ch_0020.brief.md'))


if __name__ == '__main__':
    unittest.main(verbosity=2)
