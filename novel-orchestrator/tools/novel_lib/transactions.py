# -*- coding: utf-8 -*-
"""Single-host writer lock and recoverable, touched-file write-ahead transactions.

No repository-wide snapshot/reset: only paths written through common.write/remove
are journalled. A recovery refuses to overwrite a subsequent, unrecognised edit.
"""
import contextlib
import hashlib
import json
import os
from pathlib import Path
import tempfile
import uuid

ACTIVE = None


def digest(data):
    return hashlib.sha256(data).hexdigest() if data is not None else None


def atomic_bytes(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if data is None:
        path.unlink(missing_ok=True)
        return
    fd, tmp = tempfile.mkstemp(prefix=".novel-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def safe_path(root, relative):
    path = (root / relative).resolve()
    if not path.is_relative_to(root) or path == root or ".git" in path.relative_to(root).parts:
        raise ValueError("transaction path escapes project: %s" % relative)
    return path


@contextlib.contextmanager
def project_lock(root):
    # OS releases advisory locks on process death. No stale PID guessing/unlock.
    base = Path(tempfile.gettempdir()) / "novel-orchestrator-locks"
    base.mkdir(mode=0o700, exist_ok=True)
    lock = base / (digest(str(root.resolve()).encode()) + ".lock")
    with lock.open("a+b") as stream:
        if os.name == "nt":
            import msvcrt
            stream.write(b"\0")
            stream.flush()
            stream.seek(0)
            try:
                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            except OSError as exc:
                raise RuntimeError("项目正在由另一命令写入；本次未执行") from exc
            try:
                yield
            finally:
                stream.seek(0)
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl
            try:
                fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as exc:
                raise RuntimeError("项目正在由另一命令写入；本次未执行") from exc
            try:
                yield
            finally:
                fcntl.flock(stream, fcntl.LOCK_UN)


def pending(root):
    result = []
    for path in sorted((root / "state/txn").glob("txn_*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        if not data.get("done"):
            result.append((path, data))
    return result


class Transaction:
    def __init__(self, root, kind):
        self.root = Path(root).resolve()
        self.id = "txn_" + uuid.uuid4().hex
        self.path = self.root / "state/txn" / (self.id + ".json")
        self.store = self.path.with_suffix(".data")
        self.data = {"id": self.id, "kind": kind, "version": 2,
                     "done": False, "writes": {}}
        self.message = "[%s] project update" % kind

    def save(self):
        atomic_bytes(self.path, json.dumps(self.data, ensure_ascii=False, indent=1).encode())

    def write(self, path, data):
        path = safe_path(self.root, str(Path(path).resolve().relative_to(self.root)))
        rel = str(path.relative_to(self.root))
        current = path.read_bytes() if path.exists() else None
        if current == data:
            return
        entry = self.data["writes"].get(rel)
        if entry is None:
            key = digest(rel.encode())
            entry = {"before": digest(current), "before_file": key + ".before",
                     "after": digest(current), "expected": digest(current)}
            if current is not None:
                atomic_bytes(self.store / entry["before_file"], current)
            self.data["writes"][rel] = entry
        elif digest(current) != entry["after"]:
            raise RuntimeError("事务期间文件被外部修改：%s" % rel)
        # Keep both the old and intended hashes: crash can precede or follow replace.
        entry["expected"] = entry["after"]
        entry["after"] = digest(data)
        self.save()
        atomic_bytes(path, data)

    def finish(self, rollback=False):
        if not self.data["writes"]:
            return []
        if rollback:
            restore(self.root, self.path, self.data)
        else:
            self.data.update(done=True, outcome="committed")
            self.save()
            cleanup_store(self.path)
        return list(self.data["writes"]) + [str(self.path.relative_to(self.root))]


def cleanup_store(path):
    store = path.with_suffix(".data")
    if store.is_dir():
        for child in store.iterdir():
            child.unlink()
        store.rmdir()


def restore(root, journal, data):
    if data.get("version") != 2:
        raise RuntimeError("旧版 journal 没有前镜像，不能自动恢复：%s" % journal.name)
    # Validate ALL paths and all images before restoring any file.
    work = []
    store = journal.with_suffix(".data")
    for rel, entry in data["writes"].items():
        path = safe_path(root, rel)
        current = digest(path.read_bytes() if path.exists() else None)
        if current not in (entry["before"], entry["after"], entry["expected"]):
            raise RuntimeError("恢复冲突；保留作者改动，未回退任何文件：%s" % rel)
        name = entry["before_file"]
        if Path(name).name != name:
            raise ValueError("invalid recovery image path")
        before = (store / name).read_bytes() if entry["before"] is not None else None
        if digest(before) != entry["before"]:
            raise RuntimeError("恢复前镜像损坏：%s" % rel)
        work.append((path, before))
    for path, before in reversed(work):
        atomic_bytes(path, before)
    data.update(done=True, outcome="rolled_back")
    atomic_bytes(journal, json.dumps(data, ensure_ascii=False, indent=1).encode())
    cleanup_store(journal)


def execute(root, kind, action):
    """CLI mutation boundary; nonzero result or exception rolls back all writes."""
    global ACTIVE
    from .common import git_autocommit
    with project_lock(root):
        half = pending(root)
        if half:
            raise RuntimeError("发现未完成事务；先运行 novel.py recover --rollback：%s"
                               % ", ".join(p.name for p, _ in half))
        txn = Transaction(root, kind)
        ACTIVE = txn
        try:
            result = action()
            paths = txn.finish(rollback=bool(result))
        except BaseException:
            txn.finish(rollback=True)
            raise
        finally:
            ACTIVE = None
        if paths and not result:
            git_autocommit(root, txn.message, paths=paths)
        return result


def cmd_recover(args):
    from .project import find_root
    root = find_root(args)
    with project_lock(root):
        for path, data in pending(root):
            print("%s %s" % (path.name, data.get("kind", "legacy")))
            if args.rollback:
                restore(root, path, data)
                print("已恢复本次事务前状态；未触及其他文件")
    return 0
