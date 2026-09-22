#!/usr/bin/env python3
"""Creative-input transport and historical interpretation, not literary grading."""
import json
import unittest

import test_methodology as fixtures
from support import invoke
from novel_lib.common import read, write, parse_frontmatter, dump_frontmatter
from novel_lib.creative import heading_content
from novel_lib.dependencies import stale_brief
from novel_lib.narrative import memory_recall, writeback_errors
from novel_lib.project import Project


class DecisionContextTests(unittest.TestCase):
    setUp = fixtures.MethodologyTests.setUp
    tearDown = fixtures.MethodologyTests.tearDown
    cli = fixtures.MethodologyTests.cli
    save_task = fixtures.MethodologyTests.save_task

    def intent(self):
        p = self.root / 'tree/book.md'
        meta, _ = parse_frontmatter(read(p))
        write(p, dump_frontmatter(meta) + '\n## 主旨与主控思想\n### 阅读体验契约\n'
              '合作不是主角包办，允许伙伴拒绝保护。\n'
              '### 未揭示结局\n幕后黑手是守门人。\n')
        p = self.root / 'tree/vol_01/volume.md'
        meta, _ = parse_frontmatter(read(p))
        write(p, dump_frontmatter(meta) + '\n## 卷主旨与价值走向\n共同决定风险。\n'
              '## imports\n上卷救援成功，但林晚未同意被代作决定。\n'
              '## exports\n未来计划：本卷末离队。\n')
        p = self.root / 'tree/vol_01/arc_01_1.md'
        write(p, read(p) + '\n## 当前创作问题\n拒绝帮助未必是不信任。\n')

    def memory(self, n, text, **extra):
        cid = 'ch_%04d' % n
        item = dict(kind='belief', text=text, evidence=text,
                    entity_ids=['char_linwan'], thread_ids=[], keywords=[])
        item.update(extra)
        write(self.root / ('chapters/' + cid + '.md'),
              dump_frontmatter(dict(id=cid, kind='chapter', status='drafted', rev=1,
                                    parent='arc_01_1')) + '\n## 正文\n' + text)
        write(self.root / ('chapters/' + cid + '.meta.json'),
              json.dumps(dict(summary_after='这一章结束了。', narrative_memory=[item]), ensure_ascii=False))
        return cid + '#0'

    def recall(self, at=10):
        return memory_recall(Project(self.root), self.task, at)

    def test_source_intent_arrives_without_manual_copy_and_not_future_exports(self):
        self.intent()
        self.cli('brief', 'ch_0001')
        brief = read(self.root / 'briefs/ch_0001.brief.md')
        for expected in ['合作不是主角包办', '共同决定风险', '林晚未同意', '拒绝帮助未必', '非已发生事实']:
            self.assertIn(expected, brief)
        for unwanted in ['幕后黑手是守门人', '未来计划：本卷末离队']:
            self.assertNotIn(unwanted, brief)
        self.assertNotIn('creative_brief', self.task)
        manifest = json.loads(read(self.root / 'briefs/ch_0001.manifest.json'))
        self.assertIn('intent:书级体验', manifest['retained'])
        self.assertFalse(stale_brief(Project(self.root), 'ch_0001'))
        p = self.root / 'tree/book.md'
        write(p, read(p).replace('允许伙伴拒绝保护', '尊重协商'))
        self.assertTrue(stale_brief(Project(self.root), 'ch_0001'))

    def test_heading_respects_nested_sections_fences_and_placeholders(self):
        body = '### 阅读体验契约\n[请填写]\n真实约定\n#### 细则\n细则内容\n```\n## 假标题\n```\n### 别节\n秘密'
        content = heading_content(body, '阅读体验契约')
        self.assertIn('细则内容', content)
        self.assertIn('假标题', content)
        self.assertNotIn('请填写', content)
        self.assertNotIn('秘密', content)

    def test_unfilled_legacy_intent_is_reported_not_invented(self):
        self.cli('brief', 'ch_0001')
        brief = read(self.root / 'briefs/ch_0001.brief.md')
        self.assertIn('创作意图待确认', brief)
        self.assertNotIn('### 书级体验【编辑来源', brief)

    def test_required_intent_budget_failure_keeps_previous_brief(self):
        self.intent(); self.cli('brief', 'ch_0001')
        old = read(self.root / 'briefs/ch_0001.brief.md')
        p = self.root / 'tree/book.md'
        write(p, read(p).replace('合作不是主角包办', '约定' * 15000))
        result = invoke(['brief', 'ch_0001'], self.root)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(old, read(self.root / 'briefs/ch_0001.brief.md'))

    def test_context_thread_retrieves_old_promise_before_recent_actor_events(self):
        old = self.memory(1, '旧约定', thread_ids=['thread_help'])
        for n in range(2, 11):
            self.memory(n, '普通事件%d' % n)
        self.task['context_threads'] = ['thread_help']
        result = self.recall()
        self.assertEqual(result[0][3], old)
        self.assertEqual(len(result), 6)

    def test_purpose_keyword_precedes_more_actor_matches(self):
        old = self.memory(1, '曾拒绝帮助', entity_ids=[], keywords=['拒绝原因'])
        self.memory(2, '众人聚会', entity_ids=['char_linwan', 'char_b', 'char_c'])
        self.task.update(context_entities=['char_b', 'char_c'], memory_keywords=['拒绝原因'])
        self.assertEqual(self.recall()[0][3], old)
        result = self.recall()
        self.assertGreater(result[0][1], result[1][1])

    def test_old_reference_brings_later_reinterpretation_but_not_before_cutoff(self):
        old = self.memory(1, '她认为拒绝代表不信任')
        new = self.memory(8, '她发现他是害怕转嫁风险', reinterprets=[old])
        self.task['memory_refs'] = [old]
        before = self.recall(7)
        self.assertNotIn('_interpretation_context', before[0][4])
        after = self.recall(8)
        self.assertTrue(after[0][0])
        self.assertEqual([r for r, _ in after[0][4]['_interpretation_context']], [old, new])
        self.assertEqual(len(after), 1)
        self.assertNotIn('_interpretation_context', json.loads(read(
            self.root / 'chapters/ch_0001.meta.json'))['narrative_memory'][0])

    def test_chain_and_multiple_pinned_refs_form_one_indivisible_context(self):
        old = self.memory(1, '最初解释')
        mid = self.memory(4, '后来解释', reinterprets=[old])
        new = self.memory(8, '再次修正', reinterprets=[mid])
        self.task['memory_refs'] = [old, new]
        result = self.recall()
        self.assertEqual(len(result), 1)
        self.assertTrue(result[0][0])
        self.assertEqual([r for r, _ in result[0][4]['_interpretation_context']], [old, mid, new])

    def test_selected_broken_or_forward_link_is_not_silently_dropped(self):
        self.memory(1, '早期解释', reinterprets=['ch_0008#0'])
        self.memory(8, '后来的事')
        with self.assertRaisesRegex(ValueError, '不是更早'):
            self.recall()
        self.memory(1, '早期解释')
        self.memory(8, '后来解释', reinterprets=['ch_0002#0'])
        with self.assertRaisesRegex(ValueError, '不存在'):
            self.recall()

    def test_reinterpretation_shape_validation_and_legacy_compatibility(self):
        item = dict(kind='belief', text='解释', evidence='原话')
        self.assertEqual(writeback_errors({'narrative_memory': [item]}, '原话'), [])
        item['reinterprets'] = ['not-a-reference']
        self.assertTrue(writeback_errors({'narrative_memory': [item]}, '原话'))

    def test_brief_carries_interpretation_chain_as_one_budget_item(self):
        old = self.memory(1, '她当时以为不受信任')
        new = self.memory(8, '后文澄清：他害怕把风险转嫁给她', reinterprets=[old])
        self.cli('tree', 'add', 'chapter', 'ch_0011', '--parent', 'arc_01_1')
        self.task.update(id='ch_0011', memory_refs=[old])
        self.save_task('ch_0011'); self.cli('brief', 'ch_0011')
        brief = read(self.root / 'briefs/ch_0011.brief.md')
        self.assertIn('后文澄清', brief)
        self.assertIn('解释沿革', brief)
        self.assertIn(new, brief)
        manifest = json.loads(read(self.root / 'briefs/ch_0011.manifest.json'))
        self.assertEqual(len([k for k in manifest['retained'] if k.startswith('memory:')]), 1)

    def test_optional_interpretation_group_is_trimmed_whole(self):
        old = self.memory(1, '旧解释' * 5000)
        self.memory(8, '新解释' * 5000, reinterprets=[old])
        self.cli('tree', 'add', 'chapter', 'ch_0011', '--parent', 'arc_01_1')
        self.task.update(id='ch_0011')
        self.save_task('ch_0011'); self.cli('brief', 'ch_0011')
        manifest = json.loads(read(self.root / 'briefs/ch_0011.manifest.json'))
        self.assertFalse([k for k in manifest['retained'] if k.startswith('memory:')])
        self.assertEqual(len([k for _, k in manifest['trimmed'] if k.startswith('memory:')]), 1)
        brief = read(self.root / 'briefs/ch_0011.brief.md')
        self.assertNotIn('旧解释', brief)
        self.assertNotIn('新解释', brief)

    def test_execution_instructions_do_not_restore_old_methodology(self):
        court = read(fixtures.SKILL / 'protocol/court.md')
        self.assertNotIn('→ 强制定稿', court)
        self.assertNotIn('以主编现稿定稿', court)
        self.assertNotIn('必到、必投票', court)
        analyst = read(fixtures.SKILL / 'roles/data-analyst.md')
        self.assertNotIn('支线超配额', analyst)
        self.assertNotIn('三道弃读门失守', analyst)
        self.assertIn('竞争解释', analyst)


if __name__ == '__main__':
    unittest.main()
