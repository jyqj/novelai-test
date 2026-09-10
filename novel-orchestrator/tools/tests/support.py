"""Hermetic CLI test helpers; synthetic evidence is NEVER production review."""
import contextlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from novel_lib.cli import main
from novel_lib.project import Project
from novel_lib.receipts import checklist


def synthetic_review(root, chapter):
    evidence = checklist(Project(root), chapter)
    evidence["summary"] = "合成测试夹具：只验证回执契约，不代表文学质量评审"
    for finding in evidence["findings"]:
        finding.update(disposition="pass", rationale="合成夹具预设已裁定，用于工程回归；非真实审美结论")
    return evidence


def invoke(args, cwd):
    """Run the public parser in-process, with isolated cwd and test-only identity."""
    out, err = io.StringIO(), io.StringIO()
    old = Path.cwd()
    env = {key: os.environ.get(key) for key in
           ("GIT_AUTHOR_NAME", "GIT_AUTHOR_EMAIL", "GIT_COMMITTER_NAME", "GIT_COMMITTER_EMAIL")}
    try:
        for key in env:
            os.environ[key] = "novel-tests@example.invalid" if key.endswith("EMAIL") else "Novel Regression"
        os.chdir(cwd)
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            try:
                code = main(args)
            except SystemExit as exc:
                code = exc.code
    finally:
        os.chdir(old)
        for key, val in env.items():
            if val is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = val
    return subprocess.CompletedProcess(args, code or 0, out.getvalue(), err.getvalue())


def legacy_fixture_invoke(args, cwd):
    """Legacy scenario suites now explicitly supply synthetic per-check evidence.

    The application still rejects missing/pending evidence; test_integrity covers
    those negative paths using invoke(), which adds nothing to the command.
    """
    if args[:2] == ["review", "add"] and "--evidence" not in args:
        with tempfile.TemporaryDirectory(prefix="novel-review-fixture-") as temp:
            path = Path(temp) / "review.json"
            path.write_text(json.dumps(synthetic_review(Path(cwd), args[2]), ensure_ascii=False), encoding="utf-8")
            return invoke(args + ["--evidence", str(path)], cwd)
    return invoke(args, cwd)


def save_fixture(root):
    """Explicitly commit hand-authored TEST fixture changes, never production data."""
    env = dict(os.environ, GIT_AUTHOR_NAME="Novel Regression", GIT_COMMITTER_NAME="Novel Regression",
               GIT_AUTHOR_EMAIL="novel-tests@example.invalid", GIT_COMMITTER_EMAIL="novel-tests@example.invalid")
    subprocess.run(["git", "-C", str(root), "add", "-A"], check=True, capture_output=True, env=env)
    subprocess.run(["git", "-C", str(root), "commit", "--allow-empty", "-qm", "test fixture"],
                   check=True, capture_output=True, env=env)
