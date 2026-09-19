"""One-shot, tree-bound transfer of inspected methodology edits. No network access."""
from pathlib import Path, PurePosixPath
import base64
import bz2
import hashlib
import json
import subprocess

BASE = 'd29fd450eff951e16cd832791b03ce4ad16a1402'
BASE_TREE = 'f35d5e8f77370a145b897434a9f4b054a9376878'
EXPECTED_TREE = 'd8a4fed265bd9d5c9d894ecbea4f027b5b9cd472'
PAYLOAD_HASH = 'b804302394c5330f33ad39258d8836b419e243f1352cf069be1412d3631834ab'
TRANSFER = '.methodology-transfer'
WORKFLOW = '.github/workflows/apply-methodology-once.yml'

def git(*args):
    return subprocess.check_output(['git', *args])

root = Path(git('rev-parse', '--show-toplevel').decode().strip())
assert Path.cwd().resolve() == root.resolve(), 'Run only at repository root'
assert git('rev-parse', BASE + '^{tree}').decode().strip() == BASE_TREE
changed = set(git('diff', '--name-only', '-z', BASE, 'HEAD').decode().rstrip('\0').split('\0'))
allowed = {TRANSFER + '/apply_once.py', WORKFLOW} | {TRANSFER + '/part%d.b64' % n for n in range(1, 5)}
assert changed == allowed, 'Bootstrap may contain only the six transfer files'
assert not git('status', '--porcelain').strip(), 'Refuse a dirty checkout'
encoded = ''.join((root / TRANSFER / ('part%d.b64' % n)).read_text().strip() for n in range(1, 5))
packed = base64.b64decode(encoded, validate=True)
assert hashlib.sha256(packed).hexdigest() == PAYLOAD_HASH, 'Payload integrity mismatch'
raw = bz2.decompress(packed)
assert len(raw) < 1000000
entries = json.loads(raw)
assert len(entries) == 89
seen = set()
for name, existed, edits in entries:
    path = PurePosixPath(name)
    assert name.startswith('novel-orchestrator/') and '..' not in path.parts and not path.is_absolute()
    assert name not in seen
    seen.add(name)
    target = root / name
    if existed:
        original = git('show', BASE + ':' + name)
        assert target.is_file() and not target.is_symlink() and target.read_bytes() == original
    else:
        assert not target.exists()
        original = b''
    lines = original.decode('utf-8').splitlines(keepends=True)
    previous_end = 0
    for start, end, insert in edits:
        assert isinstance(start, int) and isinstance(end, int) and isinstance(insert, str)
        assert previous_end <= start <= end <= len(lines)
        previous_end = end
    for start, end, insert in reversed(edits):
        lines[start:end] = [insert]
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(''.join(lines).encode('utf-8'))
subprocess.run(['git', 'add', '--', 'novel-orchestrator'], check=True)
subprocess.run(['git', 'rm', '-r', '--', TRANSFER, WORKFLOW], check=True)
actual = git('write-tree').decode().strip()
assert actual == EXPECTED_TREE, 'Final source tree mismatch: ' + actual
subprocess.run(['git', 'diff', '--cached', '--check'], check=True)
print('Verified final tree:', actual)
print('Applied exactly', len(entries), 'skill changes; transfer files excluded from final tree.')
