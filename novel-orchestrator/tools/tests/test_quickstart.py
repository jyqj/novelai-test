#!/usr/bin/env python3
"""Execute the exact README initialization block from a clean directory."""
import os
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


class QuickstartTests(unittest.TestCase):
    def test_readme_initialization(self):
        readme = (ROOT / 'README.md').read_text(encoding='utf-8')
        block = readme.split('<!-- quickstart-test:start -->')[1].split('<!-- quickstart-test:end -->')[0]
        commands = re.search(r'```bash\n(.*?)```', block, re.S).group(1)
        with tempfile.TemporaryDirectory(prefix='novel-quickstart-') as temp:
            book = Path(temp) / 'new-book'
            env = dict(os.environ, WORKSPACE=str(book), GIT_AUTHOR_NAME='Novel Tests',
                       GIT_AUTHOR_EMAIL='tests@example.invalid', GIT_COMMITTER_NAME='Novel Tests',
                       GIT_COMMITTER_EMAIL='tests@example.invalid')
            result = subprocess.run(['bash', '-euc', commands], cwd=ROOT, env=env,
                                    capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertTrue((book / 'state/court/S1/r0_brief.md').is_file())
            self.assertFalse((book / 'tools').exists())

    def test_reliability_docs_have_no_destructive_reset(self):
        for path in (ROOT / 'protocol').glob('*.md'):
            text = path.read_text(encoding='utf-8')
            self.assertNotIn('git reset --hard', text, str(path))
            self.assertNotIn('git clean -fd', text, str(path))


if __name__ == '__main__':
    unittest.main(verbosity=2)
