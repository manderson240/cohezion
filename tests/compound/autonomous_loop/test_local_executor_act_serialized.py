"""Concurrent ACT tasks in ONE worktree must not see or commit each other's edits (corr. C2).

THE DEFECT (2026-09-22): ``execute_batch`` runs up to 3 tasks in threads against one worktree.
ACT tasks share its index and files, so each task's pytest ran on the others' half-applied
edits, and one task's commit could contain another task's file.
"""

from __future__ import annotations

import contextlib
import subprocess
import sys
import threading
from dataclasses import dataclass, field
from pathlib import Path

from cohezion.compound.autonomous_loop import local_executor as le


@dataclass
class _Task:
    id: str
    description: str
    category: str = "general"
    verification: str = ""
    oracle_test: str = ""
    edit_file: str = ""
    edit_targets: list[str] = field(default_factory=list)


@dataclass
class _Swap:
    ok: bool = True
    reason: str = ""


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=repo, capture_output=True, text=True, check=True
    ).stdout


ORACLE = """import subprocess

from pkg.{me} import value


def test_v():
    # The OTHER task's file must be exactly as committed: never a half-applied edit.
    dirty = subprocess.run(["git", "diff", "--quiet", "HEAD", "--", "src/pkg/{other}.py"])
    assert dirty.returncode == 0, "saw the other task's uncommitted edit"
    assert value() == 2
"""


def _repo(root: Path) -> Path:
    repo = root / "repo"
    (repo / "src/pkg").mkdir(parents=True)
    (repo / "tests").mkdir()
    (repo / "src/pkg/__init__.py").write_text("")
    for me, other in (("a", "b"), ("b", "a")):
        (repo / f"src/pkg/{me}.py").write_text('"""m."""\n\n\ndef value():\n    return 1\n')
        (repo / f"tests/test_{me}.py").write_text(ORACLE.format(me=me, other=other))
    for c in (
        ["init", "-q"],
        ["config", "user.email", "t@t"],
        ["config", "user.name", "t"],
        ["add", "."],
        ["commit", "-q", "-m", "base"],
        ["checkout", "-q", "-b", "act/test"],  # ACT commits only to an act/ branch
    ):
        _git(repo, *c)
    return repo


def test_two_act_tasks_in_one_worktree_commit_only_their_own_file(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    together = threading.Barrier(2, timeout=3)  # without serialisation both edit at once

    def chat(_prompt: str) -> dict:
        # Serialised: the other task is waiting for the worktree, not for us.
        with contextlib.suppress(threading.BrokenBarrierError):
            together.wait()
        return {"text": "```python\ndef value():\n    return 2\n```", "model": "fake"}

    ex = le.LocalImprovementExecutor(
        act_chat_fn=chat,
        act_max_iters=1,
        act_log_path=tmp_path / "act.jsonl",
        act_python=sys.executable,
        act_admit_fn=lambda _m: _Swap(),
    )
    tasks = [
        _Task(
            id=f"t-{n}",
            description="make value() return 2",
            oracle_test=f"tests/test_{n}.py::test_v",
            edit_file=f"src/pkg/{n}.py",
            edit_targets=["value"],
        )
        for n in ("a", "b")
    ]
    results = ex.execute_batch(tasks, str(repo), max_workers=2)
    assert all(r["success"] for r in results), [(r["task_id"], r["status"]) for r in results]
    commits = _git(repo, "log", "--format=%H", "-2").split()
    touched = sorted(
        tuple(_git(repo, "show", "--name-only", "--format=", c).split()) for c in commits
    )
    assert touched == [("src/pkg/a.py",), ("src/pkg/b.py",)], touched
    assert _git(repo, "status", "--porcelain") == ""
