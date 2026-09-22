"""ACT commits go to a dedicated worktree on an act/ branch, never main (ops MAJOR 5).

THE DEFECT (2026-09-22): ``worktree_path`` defaulted to ``/tmp/worktree`` -- tmpfs, absent,
and once wired, commits would land on whatever branch that checkout had (main included).
"""

from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

from cohezion.compound.autonomous_loop import local_executor as le
from cohezion.compound.autonomous_loop.coordinator import LoopConfig


@dataclass
class _Task:
    id: str = "t-act"
    description: str = "make value() return 2"
    category: str = "general"
    verification: str = ""
    oracle_test: str = "tests/test_mod.py::test_v"
    edit_file: str = "src/pkg/mod.py"
    edit_targets: list[str] = field(default_factory=lambda: ["value"])


@dataclass
class _Swap:
    ok: bool = True
    reason: str = ""


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=repo, capture_output=True, text=True, check=True
    ).stdout.strip()


def _repo(root: Path) -> Path:
    repo = root / "repo"
    (repo / "src/pkg").mkdir(parents=True)
    (repo / "tests").mkdir()
    (repo / "src/pkg/__init__.py").write_text("")
    (repo / "src/pkg/mod.py").write_text('"""m."""\n\n\ndef value():\n    return 1\n')
    (repo / "tests/test_mod.py").write_text(
        "from pkg.mod import value\n\n\ndef test_v():\n    assert value() == 2\n"
    )
    (repo / ".gitignore").write_text(".cache/\n")
    for c in (
        ["init", "-q", "-b", "main"],
        ["config", "user.email", "t@t"],
        ["config", "user.name", "t"],
        ["add", "."],
        ["commit", "-q", "-m", "base"],
    ):
        _git(repo, *c)
    return repo


def _executor(tmp_path: Path, calls: list[str]) -> le.LocalImprovementExecutor:
    def chat(prompt: str) -> dict:
        calls.append(prompt)
        return {"text": "```python\ndef value():\n    return 2\n```", "model": "fake"}

    return le.LocalImprovementExecutor(
        act_chat_fn=chat,
        act_max_iters=1,
        act_log_path=tmp_path / "act.jsonl",
        act_python=sys.executable,
        act_admit_fn=lambda _m: _Swap(),
    )


def test_default_config_is_not_tmpfs() -> None:
    assert not LoopConfig().worktree_path.startswith("/tmp")


def test_ensure_act_worktree_creates_a_dedicated_branch_once(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    wt = le.ensure_act_worktree(repo)
    assert wt == repo.resolve() / ".cache/act-worktree"
    assert _git(wt, "symbolic-ref", "--short", "HEAD") == "act/loop"
    assert le.ensure_act_worktree(repo) == wt  # idempotent
    assert _git(repo, "symbolic-ref", "--short", "HEAD") == "main"


def test_act_refuses_to_commit_on_main(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    head = _git(repo, "rev-parse", "HEAD")
    calls: list[str] = []
    res = _executor(tmp_path, calls).execute_task(_Task(), str(repo))
    assert res["status"] == le.UNSAFE_WORKTREE and not res["success"], res
    assert calls == [], "no model call for a task that may not commit"
    assert _git(repo, "rev-parse", "HEAD") == head


def test_default_worktree_commits_on_act_branch_not_main(tmp_path: Path, monkeypatch) -> None:
    repo = _repo(tmp_path)
    main_head = _git(repo, "rev-parse", "main")
    monkeypatch.setattr(le, "_DEFAULT_ACT_ROOT", repo)
    res = _executor(tmp_path, []).execute_task(_Task(), "")
    assert res["success"], res
    assert _git(repo, "rev-parse", "main") == main_head
    assert _git(repo, "rev-parse", "--short", "act/loop") == res["commit"]
