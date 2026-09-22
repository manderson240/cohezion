"""A single green run can be a fluke; the loop must re-confirm before committing.

THE GAP (2026-09-21, found reading EverMind-AI/Raven's Evolver, which gates promotion on
K=3 paired-significance confirmation, not a single pass): act_loop committed on the FIRST
green run. A flaky oracle (order-dependent, relies on uninitialised state, timing-sensitive)
could pass once by luck and still get committed as a verified fix.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from cohezion.compound.autonomous_loop.act_loop import act_loop


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True, check=True)


def _repo(root: Path, oracle_body: str) -> Path:
    repo = root / "repo"
    (repo / "src/pkg").mkdir(parents=True)
    (repo / "tests").mkdir()
    (repo / "src/pkg/__init__.py").write_text("")
    (repo / "src/pkg/mod.py").write_text('"""m."""\n\n\ndef value():\n    return 1\n')
    (repo / "tests/test_mod.py").write_text(oracle_body)
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


_FLAKY_ORACLE = (
    "import pathlib\n"
    "from pkg.mod import value\n\n\n"
    "def test_v():\n"
    "    c = pathlib.Path(__file__).parent / '.count'\n"
    "    n = int(c.read_text()) if c.exists() else 0\n"
    "    c.write_text(str(n + 1))\n"
    "    # act_loop's pre-loop 'already green?' probe is call n=0 (always red: value()==1).\n"
    "    # Its first real attempt after the model's edit is call n=1: this is the one lucky\n"
    "    # green. Every confirm-repeat call after that is n>=2: red again.\n"
    "    assert value() == 2 and n == 1\n"
)

_STABLE_ORACLE = "from pkg.mod import value\n\n\ndef test_v():\n    assert value() == 2\n"


def test_flaky_oracle_is_not_committed_on_a_single_lucky_pass(tmp_path: Path) -> None:
    repo = _repo(tmp_path, _FLAKY_ORACLE)

    def chat(prompt: str) -> dict:
        return {"text": "```python\ndef value():\n    return 2\n```"}

    res = act_loop(
        repo=repo,
        file="src/pkg/mod.py",
        targets=["value"],
        oracle="tests/test_mod.py",
        extra_tests=[],
        task="t",
        task_id="t1",
        model="m",
        chat=chat,
        python=sys.executable,
        max_iters=2,
        log=tmp_path / "log.jsonl",
        commit=True,
    )
    assert res["status"] == "FLAKY_ORACLE", res
    assert res.get("commit") is None
    log = subprocess.run(
        ["git", "log", "--oneline"], cwd=repo, capture_output=True, text=True
    ).stdout
    assert log.count("\n") == 1, "a flaky-caught candidate must not be committed"
    assert (
        repo.joinpath("src/pkg/mod.py").read_text() == '"""m."""\n\n\ndef value():\n    return 1\n'
    )


def test_stable_oracle_still_commits(tmp_path: Path) -> None:
    repo = _repo(tmp_path, _STABLE_ORACLE)

    def chat(prompt: str) -> dict:
        return {"text": "```python\ndef value():\n    return 2\n```"}

    res = act_loop(
        repo=repo,
        file="src/pkg/mod.py",
        targets=["value"],
        oracle="tests/test_mod.py",
        extra_tests=[],
        task="t",
        task_id="t1",
        model="m",
        chat=chat,
        python=sys.executable,
        max_iters=2,
        log=tmp_path / "log.jsonl",
        commit=True,
    )
    assert res["status"] == "GREEN", res
    assert res["commit"]
