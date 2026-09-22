#!/usr/bin/env python3
"""Methodology/transport regression only; no literary-quality claims or model calls."""
import json
import re
import shutil
import tempfile
import unittest
from pathlib import Path

from support import invoke
from novel_lib.common import Report, dump_frontmatter, parse_frontmatter, read, write, get_section
from novel_lib.project import Project
from novel_lib.checks import check_unit, check_window
from novel_lib.gate import gate_write
from novel_lib.dependencies import stale_brief
from test_refactor import ARC_STAGED

SKILL = Path(__file__).resolve().parents[2]


class MethodologyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='novel-methodology-')
        self.base = Path(self.temp.name)
        self.root = self.base / 'book'
        self.cli('init', str(self.root), cwd=self.base)
        shutil.rmtree(self.root / '.git')
        config = json.loads(read(self.root / 'config.json'))
        config.update(word_target=[10, 900], route='web')
        write(self.root / 'config.json', json.dumps(config))
        self.cli('tree', 'add', 'volume', 'vol_01')
        self.cli('tree', 'add', 'arc', 'arc_01_1')
        write(self.root / 'tree/vol_01/arc_01_1.md',
              ARC_STAGED.replace('status: draft', 'status: committed'))
        self.cli('entity', 'new', 'char_linwan')
        self.cli('tree', 'add', 'chapter', 'ch_0001', '--parent', 'arc_01_1')
        self.cli('stage', 'enter', 'write')
        self.task = {'id': 'ch_0001', 'arc': 'arc_01_1', 'goal': '归还铜牌，完整结束',
                     'beats': ['交还', '道别'], 'cast': ['char_linwan'], 'threads': [],
                     'payoff_quota': [], 'hook': {'close': None}}
        self.save_task()

    def tearDown(self):
        self.temp.cleanup()

    def cli(self, *args, cwd=None):
        r = invoke(list(args), cwd or self.root)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        return r.stdout

    def save_task(self, cid='ch_0001'):
        write(self.root / 'chapters' / (cid + '.task.json'),
              json.dumps(self.task, ensure_ascii=False))

    def test_full_closure_does_not_require_a_cliffhanger(self):
        self.cli('brief', 'ch_0001')
        report = Report()
        gate_write(Project(self.root), 'ch_0001', report)
        self.assertFalse([x for x in report.items if x[0] == 'FAIL' and '钩' in x[1]])
        text = self.base / 'draft.md'
        meta = {'id': 'ch_0001', 'kind': 'chapter', 'rev': 1,
                'parent': 'arc_01_1', 'title': '归还'}
        write(text, dump_frontmatter(meta) + '\n\n## 正文\n'
              '林晚把铜牌放回桌上，向老人道了别。雨已经停了，她收起伞，慢慢走回自己的家。')
        wb = {'summary_after': '林晚归还铜牌后回家。', 'continuity_delta': [],
              'time_advance': {'elapsed': '1天', 'story_date': ''}, 'thread_ops': [],
              'payoff_realized': [], 'hooks_realized': {'open': False, 'close': False},
              'cast_actual': ['char_linwan'], 'issues': [], 'word_count': 0}
        wbpath = self.base / 'wb.json'; write(wbpath, json.dumps(wb))
        report = check_unit(Project(self.root), 'ch_0001', text, wbpath)
        self.assertFalse([x for x in report.items if x[0] == 'FAIL'], report.items)

    def test_creative_brief_reaches_writer_and_changes_invalidate_manifest(self):
        self.task['creative_brief'] = {'experience': '安静的重逢',
                                      'reader_state_hypothesis': '编辑假说：读者误以为她已忘记'}
        self.save_task(); self.cli('brief', 'ch_0001')
        brief = read(self.root / 'briefs/ch_0001.brief.md')
        self.assertIn('安静的重逢', brief)
        self.assertIn('编辑假说', brief)
        self.assertFalse(stale_brief(Project(self.root), 'ch_0001'))
        self.task['creative_brief']['experience'] = '有意保留距离的重逢'
        self.save_task()
        self.assertTrue(stale_brief(Project(self.root), 'ch_0001'))

    def test_closed_thread_recalled_as_aftermath_without_new_operation(self):
        self.cli('thread', 'new', 'thread_bell', '--kind', 'promise')
        p = self.root / 'threads/thread_bell.md'
        meta, body = parse_frontmatter(read(p)); meta['state'] = 'paid_off'; meta['plant_ch'] = 1
        body = body.replace('## 回收设计', '## 回收设计\n\n归还铜铃改变了她对导师的理解。')
        body += '\n- ch_0001: plant 铃的约定\n- ch_0001: payoff 约定已完成\n'
        write(p, dump_frontmatter(meta) + '\n' + body)
        self.cli('tree', 'add', 'chapter', 'ch_0002', '--parent', 'arc_01_1')
        self.task.update(id='ch_0002', context_threads=['thread_bell'], threads=[])
        self.save_task('ch_0002'); self.cli('brief', 'ch_0002')
        brief = read(self.root / 'briefs/ch_0002.brief.md')
        self.assertIn('paid_off', brief)
        self.assertIn('归还铜铃改变了她对导师的理解', brief)
        self.assertIn('编辑计划，不是已发生事实', brief)
        self.assertEqual(Project(self.root).threads()['thread_bell']['meta']['state'], 'paid_off')
        self.assertEqual(self.task['threads'], [])

    def test_template_logs_remain_last_and_character_notes_are_reachable(self):
        for filename, heading in [('thread.md', '推进日志'), ('entity-char.md', '事件日志')]:
            headings = re.findall(r'^## (.+)$', read(SKILL / 'templates' / filename), re.M)
            self.assertEqual(headings[-1], heading)
        body = read(SKILL / 'templates/entity-char.md')
        self.assertIn('当前信念与关系动力', get_section(body, '现状'))

    def test_old_windows_do_not_reject_quiet_serial_or_zero_promise_ending(self):
        class QuietProject:
            config = {'route': 'web'}
            def chapters(self):
                return [{'id': 'ch_%04d' % i, 'meta': {'status': 'drafted'}} for i in range(1, 11)]
            def payoff_rows(self): return []
            def threads(self): return {}
            def power_rows(self): return []
            def timeline_rows(self): return []
            def buffer_ready(self): return 0
            def cursor(self): return {'last_published': 0}
        report = check_window(QuietProject())
        self.assertFalse([x for x in report.items if x[0] == 'FAIL'], report.items)
        self.assertTrue(any('归零' in x[1] for x in report.items))
        self.assertTrue(any(x[0] == 'WARN' and '窗口' in x[1] for x in report.items))

    def test_world_facts_remain_protected(self):
        # Reusing an unregistered entity is still a machine error, not an aesthetic exception.
        from novel_lib.checks import writeback_ref_errors
        wb = {'continuity_delta': [{'fact': '新人凭空登场', 'entity_ids': ['char_unknown'], 'spoiler': 0}]}
        self.assertTrue(writeback_ref_errors(Project(self.root), 'ch_0001', wb))


if __name__ == '__main__':
    unittest.main()
