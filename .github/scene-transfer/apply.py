"""One-shot verified transport; this script is not part of the final source tree."""
import hashlib
import json
import lzma
from pathlib import Path
import subprocess
import sys

BASE_TREE = 'd8a4fed265bd9d5c9d894ecbea4f027b5b9cd472'
FINAL_TREE = '752abc3dbef3f9814c1ae06fb35cb39b4894e268'
PAYLOAD_HASH = '7edcdbf8e23485de933be4dac1e4825a033343a9daf1d3d9e9ad6678c0529da7'
root = Path(sys.argv[1]).resolve(strict=True)

def git(*args):
    return subprocess.check_output(['git', '-C', str(root), *args], text=True).strip()

def digest(data):
    return hashlib.sha256(data).hexdigest()

if git('rev-parse', 'HEAD^{tree}') != BASE_TREE or git('status', '--porcelain'):
    raise SystemExit('Refusing a non-baseline or dirty checkout')
parts = b''.join((Path(__file__).parent / ('part-%d.xz' % i)).read_bytes() for i in range(4))
raw = lzma.decompress(parts)
if digest(raw) != PAYLOAD_HASH:
    raise SystemExit('Transport payload hash mismatch')
changes = json.loads(raw.decode('utf-8'))
if not isinstance(changes, list) or len(changes) != 37:
    raise SystemExit('Unexpected change count')
ready = []
seen = set()
for change in changes:
    rel = Path(change['path'])
    if rel.is_absolute() or '..' in rel.parts or rel.parts[0] != 'novel-orchestrator':
        raise SystemExit('Invalid target path')
    path = root / rel
    if not path.resolve().is_relative_to(root) or path.is_symlink() or str(rel) in seen:
        raise SystemExit('Unsafe or duplicate target')
    seen.add(str(rel))
    old_hash = change['old_sha256']
    if old_hash is None:
        if path.exists():
            raise SystemExit('New file already exists: ' + str(rel))
        new = change['content'].encode('utf-8')
    else:
        old = path.read_bytes()
        if digest(old) != old_hash:
            raise SystemExit('Old content mismatch: ' + str(rel))
        lines = old.decode('utf-8').splitlines(keepends=True)
        edits = change['edits']
        end = 0
        for edit in edits:
            start, stop = edit['start'], edit['end']
            if type(start) is not int or type(stop) is not int or not end <= start <= stop <= len(lines):
                raise SystemExit('Invalid/overlapping line edit: ' + str(rel))
            end = stop
        for edit in reversed(edits):
            lines[edit['start']:edit['end']] = edit['text'].splitlines(keepends=True)
        new = ''.join(lines).encode('utf-8')
    if digest(new) != change['new_sha256']:
        raise SystemExit('New content mismatch: ' + str(rel))
    ready.append((path, new))
# Validate the full payload before modifying any source file.
for path, new in ready:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(new)
subprocess.run(['git', '-C', str(root), 'add', '--', 'novel-orchestrator'], check=True)
actual = git('write-tree')
if actual != FINAL_TREE:
    raise SystemExit('Final source tree mismatch: ' + actual)
print('Verified %d files; source tree %s' % (len(ready), actual))
