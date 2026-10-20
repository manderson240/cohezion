"""An oracle that cannot RUN is an instrument failure, not a model failure.

THE DEFECT (2026-09-21): run under an interpreter without pytest (system python, or a git
worktree with no .venv so the executor falls back to sys.executable), every oracle run fails
with "No module named pytest". act_loop read that as RED, fed it back to the model, and
returned EXHAUSTED -- blaming the model for a broken test runner.
"""

from __future__ import annotations

import sys
from pathlib import Path

from cohezion.compound.autonomous_loop.act_loop import act_loop


def _repo(root: Path) -> Path:
    repo = root / "repo"
    (repo / "src/pkg").mkdir(parents=True)
    (repo / "tests").mkdir()
    (repo / "src/pkg/__init__.py").write_text("")
    (repo / "src/pkg/mod.py").write_text('"""m."""\n\n\ndef value():\n    return 1\n')
    (repo / "tests/test_mod.py").write_text(
        "from pkg.mod import value\n\n\ndef test_v():\n    assert value() == 2\n"
    )
    return repo


def test_missing_pytest_reports_runner_broken_and_never_calls_model(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    no_pytest = tmp_path / "py_without_pytest"
    # A python whose -m pytest fails exactly like system python here.
    no_pytest.write_text(
        f'#!/bin/sh\nexec {sys.executable} -I -c "import sys; sys.stderr.write(\\"No module named pytest\\\\n\\"); sys.exit(1)" "$@"\n'
    )
    no_pytest.chmod(0o755)
    calls: list[str] = []

    def chat(prompt: str) -> dict:
        calls.append(prompt)
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
        python=str(no_pytest),
        max_iters=3,
        log=tmp_path / "log.jsonl",
        commit=False,
    )
    assert res["status"] == "RUNNER_BROKEN", res
    assert calls == [], "the model must not be asked to fix a test runner it cannot see"


def test_real_red_oracle_still_reaches_the_model(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    calls: list[str] = []

    def chat(prompt: str) -> dict:
        calls.append(prompt)
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
        commit=False,
    )
    assert res["status"] == "GREEN", res
    assert len(calls) == 1
