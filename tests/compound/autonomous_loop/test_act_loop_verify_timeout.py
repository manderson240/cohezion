"""A verify step that TIMES OUT is an instrument failure, not a failed model attempt.

THE DEFECT (2026-09-22): run_tests returned (False, "pytest TIMEOUT") and act_loop scored it
exactly like a RED run -- consuming a model iteration and feeding "pytest TIMEOUT" back to the
model as if its edit had failed the tests. On a loaded box (caller tests measured 76s/run) a
correct edit could be discarded and the loop end EXHAUSTED, blaming the model.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from cohezion.compound.autonomous_loop import act_loop as act_loop_mod
from cohezion.compound.autonomous_loop.act_loop import PYTEST_TIMEOUT, act_loop


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


class _FakeRunner:
    """Scripted run_tests: returns the queued (ok, out) results in order, then green."""

    def __init__(self, results: list[tuple[bool, str]]) -> None:
        self.results = list(results)
        self.calls = 0

    def __call__(self, repo, python, tests, timeout=300):
        self.calls += 1
        return self.results.pop(0) if self.results else (True, "1 passed")


def _run(tmp_path: Path, runner: _FakeRunner, monkeypatch, **kw) -> tuple[dict, list[str], Path]:
    repo = _repo(tmp_path)
    monkeypatch.setattr(act_loop_mod, "run_tests", runner)
    calls: list[str] = []

    def chat(prompt: str) -> dict:
        calls.append(prompt)
        return {"text": "```python\ndef value():\n    return 2\n```"}

    log = tmp_path / "log.jsonl"
    args = {
        "repo": repo,
        "file": "src/pkg/mod.py",
        "targets": ["value"],
        "oracle": "tests/test_mod.py",
        "extra_tests": [],
        "task": "t",
        "task_id": "t1",
        "model": "m",
        "chat": chat,
        "python": sys.executable,
        "max_iters": 1,
        "log": log,
        "commit": False,
        "callers": [],
    }
    args.update(kw)
    return act_loop(**args), calls, log


def _outcomes(log: Path) -> list[str]:
    return [json.loads(line).get("outcome") for line in log.read_text().splitlines()]


def test_timeout_does_not_consume_the_only_model_iteration(tmp_path: Path, monkeypatch) -> None:
    # pre-loop red, then the first verify TIMES OUT, then the retry is green (+2 confirms).
    runner = _FakeRunner([(False, "1 failed"), (False, PYTEST_TIMEOUT)])
    res, calls, log = _run(tmp_path, runner, monkeypatch, max_iters=1)
    # Old behaviour: the timeout was scored RED -> max_iters=1 exhausted -> EXHAUSTED.
    assert res["status"] == "GREEN", res
    assert res["iterations"] == 1
    assert len(calls) == 2, "the timed-out attempt is retried, not charged"
    assert "VERIFY_TIMEOUT" in _outcomes(log)
    assert "RED" not in _outcomes(log)
    assert PYTEST_TIMEOUT not in calls[1], "a timeout must not be fed back as a test failure"


def test_repeated_timeouts_end_with_distinct_status_not_exhausted(
    tmp_path: Path, monkeypatch
) -> None:
    runner = _FakeRunner([(False, "1 failed")] + [(False, PYTEST_TIMEOUT)] * 10)
    res, calls, log = _run(tmp_path, runner, monkeypatch, max_iters=5, max_verify_timeouts=2)
    assert res["status"] == "VERIFY_TIMEOUT", res
    assert res["iterations"] == 0
    assert len(calls) == 3, "bounded by its own budget (2 retries + the one that exceeded it)"
    assert _outcomes(log).count("VERIFY_TIMEOUT") == 3
    assert "return 1" in (tmp_path / "repo/src/pkg/mod.py").read_text(), "edit not left behind"


def test_pre_edit_oracle_timeout_never_calls_the_model(tmp_path: Path, monkeypatch) -> None:
    runner = _FakeRunner([(False, PYTEST_TIMEOUT)])
    res, calls, _ = _run(tmp_path, runner, monkeypatch)
    assert res["status"] == "VERIFY_TIMEOUT", res
    assert calls == []


def test_confirm_repeat_timeout_is_not_reported_as_flaky(tmp_path: Path, monkeypatch) -> None:
    runner = _FakeRunner([(False, "1 failed"), (True, "1 passed"), (False, PYTEST_TIMEOUT)])
    res, _, _ = _run(tmp_path, runner, monkeypatch)
    assert res["status"] == "VERIFY_TIMEOUT", res
    assert "return 1" in (tmp_path / "repo/src/pkg/mod.py").read_text()


def test_real_red_still_consumes_an_iteration(tmp_path: Path, monkeypatch) -> None:
    runner = _FakeRunner([(False, "1 failed"), (False, "assert 1 == 2")])
    res, calls, log = _run(tmp_path, runner, monkeypatch, max_iters=1)
    assert res["status"] == "EXHAUSTED", res
    assert len(calls) == 1
    assert _outcomes(log)[-1] == "RED"


def test_local_executor_surfaces_verify_timeout_distinctly() -> None:
    from cohezion.compound.autonomous_loop.local_executor import _ACT_STATUS

    # Unmapped statuses collapse to "act_error"; a timeout must stay distinguishable.
    assert _ACT_STATUS.get("VERIFY_TIMEOUT") == "verify_timeout"
