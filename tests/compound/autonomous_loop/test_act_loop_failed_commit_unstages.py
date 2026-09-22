"""A failed commit must leave neither a staged nor a modified edit behind (correctness C1).

THE DEFECT (2026-09-22, reproduced): ``_commit`` ran ``git add`` then ``git commit``. When the
commit failed (hook, index lock, no identity) the edit stayed STAGED, and the next task's
commit swept it in under its own task id and oracle.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from cohezion.compound.autonomous_loop.act_loop import act_loop


MOD = '"""m."""\n\n\ndef value():\n    return 1\n'


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=repo, check=True, capture_output=True, text=True
    ).stdout


def _repo(root: Path) -> Path:
    repo = root / "repo"
    (repo / "src/pkg").mkdir(parents=True)
    (repo / "tests").mkdir()
    (repo / "src/pkg/__init__.py").write_text("")
    for name in ("a", "b"):
        (repo / f"src/pkg/{name}.py").write_text(MOD)
        (repo / f"tests/test_{name}.py").write_text(
            f"from pkg.{name} import value\n\n\ndef test_v():\n    assert value() == 2\n"
        )
    for c in (
        ["init", "-q"],
        ["config", "user.email", "t@t"],
        ["config", "user.name", "t"],
        ["add", "."],
        ["commit", "-q", "-m", "base"],
    ):
        _git(repo, *c)
    return repo


def _run(repo: Path, tmp_path: Path, name: str) -> dict:
    return act_loop(
        repo=repo,
        file=f"src/pkg/{name}.py",
        targets=["value"],
        oracle=f"tests/test_{name}.py",
        extra_tests=[],
        task="t",
        task_id=f"task-{name}",
        model="m",
        chat=lambda _p: {"text": "```python\ndef value():\n    return 2\n```"},
        python=sys.executable,
        max_iters=1,
        log=tmp_path / "log.jsonl",
        callers=[],
        confirm_repeats=1,
    )


def test_failed_commit_leaves_clean_tree_and_next_commit_is_its_own(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    _git(repo, "config", "user.name", "")  # git refuses an empty ident AFTER `git add`
    res_a = _run(repo, tmp_path, "a")
    assert res_a["status"] != "GREEN", res_a
    assert _git(repo, "status", "--porcelain") == "", "task A left a staged/modified edit"
    assert (repo / "src/pkg/a.py").read_text() == MOD

    _git(repo, "config", "user.name", "t")
    res_b = _run(repo, tmp_path, "b")
    assert res_b["status"] == "GREEN", res_b
    changed = _git(repo, "show", "--name-only", "--format=", "HEAD").split()
    assert changed == ["src/pkg/b.py"], changed
