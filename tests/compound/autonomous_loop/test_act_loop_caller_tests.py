"""act_loop must not commit an edit that passes its oracle but breaks a CALLER.

THE GAP (2026-09-21): commit 2b81df1ca (task aeef3b96a6f1) passed its oracle and the
selected module tests, yet made ``oom_guard.pre_load_gate`` raise TypeError when the
router is down. No selected test exercised that caller path. act_loop now auto-adds test
files that import the edited module, or a src module that imports it.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from cohezion.compound.autonomous_loop.act_loop import act_loop, caller_tests


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True, check=True)


def _repo(root: Path) -> Path:
    """A.value() is used by B.doubled(); the oracle tests only A; B's test covers the call."""
    repo = root / "repo"
    (repo / "src/pkg").mkdir(parents=True)
    (repo / "tests").mkdir()
    (repo / "src/pkg/__init__.py").write_text("")
    (repo / "src/pkg/a.py").write_text('"""a."""\n\n\ndef value(x=None):\n    return 1\n')
    (repo / "src/pkg/b.py").write_text(
        '"""b."""\n\nfrom pkg.a import value\n\n\ndef doubled():\n    return 2 * value()\n'
    )
    (repo / "tests/test_a.py").write_text(
        "from pkg.a import value\n\n\ndef test_v():\n    assert value(0) == 2\n"
    )
    (repo / "tests/test_b.py").write_text(
        "from pkg.b import doubled\n\n\ndef test_d():\n    assert doubled() in (2, 4)\n"
    )
    for c in (
        ["init", "-q"],
        ["config", "user.email", "t@t"],
        ["config", "user.name", "t"],
        ["config", "commit.gpgsign", "false"],
        ["add", "."],
        ["commit", "-q", "-m", "base"],
    ):
        _git(repo, *c)
    return repo


# Passes the oracle (value(0) == 2) but drops the default: B's value() call raises TypeError.
_BREAKS_CALLER = "def value(x):\n    return 2\n"
_SAFE = "def value(x=None):\n    return 2\n"


def _run(tmp_path: Path, replies: list[str]) -> tuple[dict, Path]:
    repo = _repo(tmp_path)
    it = iter(replies)

    def chat(prompt: str) -> dict:
        return {"text": f"```python\n{next(it)}```"}

    res = act_loop(
        repo=repo,
        file="src/pkg/a.py",
        targets=["value"],
        oracle="tests/test_a.py",
        extra_tests=[],
        task="make value return 2",
        task_id="t1",
        model="m",
        chat=chat,
        python=sys.executable,
        max_iters=len(replies),
        log=tmp_path / "log.jsonl",
    )
    return res, repo


def _commits(repo: Path) -> int:
    out = subprocess.run(
        ["git", "log", "--oneline"], cwd=repo, capture_output=True, text=True, check=True
    )
    return len(out.stdout.splitlines())


def test_scan_finds_the_one_hop_caller_test(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    assert caller_tests(repo, "src/pkg/a.py", exclude={"tests/test_a.py"}) == ["tests/test_b.py"]


def test_edit_that_breaks_a_caller_is_not_committed(tmp_path: Path) -> None:
    res, repo = _run(tmp_path, [_BREAKS_CALLER])
    assert res["status"] == "EXHAUSTED", res
    assert _commits(repo) == 1
    assert "return 1" in (repo / "src/pkg/a.py").read_text()


def test_caller_safe_edit_is_still_committed(tmp_path: Path) -> None:
    res, repo = _run(tmp_path, [_BREAKS_CALLER, _SAFE])
    assert res["status"] == "GREEN", res
    assert _commits(repo) == 2


def test_prebroken_caller_is_not_held_against_the_model(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    (repo / "tests/test_b.py").write_text(
        "from pkg.b import doubled\n\n\ndef test_d():\n    assert doubled() == 99\n"
    )
    _git(repo, "commit", "-qam", "red caller")

    def chat(prompt: str) -> dict:
        return {"text": f"```python\n{_SAFE}```"}

    res = act_loop(
        repo=repo,
        file="src/pkg/a.py",
        targets=["value"],
        oracle="tests/test_a.py",
        extra_tests=[],
        task="t",
        task_id="t2",
        model="m",
        chat=chat,
        python=sys.executable,
        max_iters=1,
        log=tmp_path / "log.jsonl",
    )
    assert res["status"] == "GREEN", res
