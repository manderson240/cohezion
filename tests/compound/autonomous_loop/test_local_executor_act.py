"""Consumption tests: execute_task completes a task ONLY through the ACT loop.

THE DEFECT (2026-09-21): `execute_task` made one chat call and `_judge_quality` judged
the prose. Nothing edited a file or ran a test, so the compound daemon marked tasks done
in ~5 min with no change on disk. Success must now mean: a commit exists AND the task's
oracle test is green. A task without an oracle is `needs_oracle` -- never success.

(a)/(b) drive the REAL splice -> pytest -> commit path in a tmp git repo; only the model
reply is faked (`act_chat_fn`), so they fail if the executor stops consuming act_loop.
"""

from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

import pytest

from cohezion.compound.autonomous_loop import local_executor as le
from cohezion.compound.autonomous_loop.coordinator import LoopTask


@dataclass
class _Task:
    id: str
    description: str
    category: str = "general"
    verification: str = ""
    oracle_test: str = ""
    edit_file: str = ""
    edit_targets: list[str] = field(default_factory=list)


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=repo, capture_output=True, text=True, check=True
    ).stdout


def _make_repo(root: Path) -> Path:
    repo = root / "repo"
    (repo / "src/pkg").mkdir(parents=True)
    (repo / "tests").mkdir()
    (repo / "src/pkg/__init__.py").write_text("")
    (repo / "src/pkg/mod.py").write_text('"""m."""\n\n\ndef value():\n    return 1\n')
    (repo / "tests/test_mod.py").write_text(
        "from pkg.mod import value\n\n\ndef test_v():\n    assert value() == 2\n"
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


def _fake_chat(reply_code: str):
    calls = {"n": 0}

    def chat(prompt: str) -> dict:
        calls["n"] += 1
        return {"text": f"```python\n{reply_code}```", "model": "fake-model"}

    chat.calls = calls  # type: ignore[attr-defined]
    return chat


def _act_task() -> _Task:
    return _Task(
        id="t-act",
        description="make value() return 2",
        oracle_test="tests/test_mod.py::test_v",
        edit_file="src/pkg/mod.py",
        edit_targets=["value"],
    )


def _executor(tmp_path: Path, chat) -> le.LocalImprovementExecutor:
    return le.LocalImprovementExecutor(
        act_chat_fn=chat,
        act_max_iters=2,
        act_log_path=tmp_path / "act.jsonl",
        act_python=sys.executable,
    )


def test_a_correct_edit_is_committed_and_is_success(tmp_path):
    repo = _make_repo(tmp_path)
    chat = _fake_chat("def value():\n    return 2\n")
    res = _executor(tmp_path, chat).execute_task(_act_task(), str(repo))
    assert res["success"] is True
    assert res["status"] == "committed"
    log = _git(repo, "log", "--format=%s")
    assert "[task: t-act]" in log and "fake-model" in log
    assert res["commit"] and _git(repo, "rev-parse", "--short", "HEAD").strip() == res["commit"]
    assert "return 2" in (repo / "src/pkg/mod.py").read_text()


def test_b_wrong_edit_never_commits_and_is_not_success(tmp_path):
    repo = _make_repo(tmp_path)
    head = _git(repo, "rev-parse", "HEAD")
    chat = _fake_chat("def value():\n    return 3\n")
    res = _executor(tmp_path, chat).execute_task(_act_task(), str(repo))
    assert res["success"] is False
    assert res["status"] == "act_exhausted"
    assert _git(repo, "rev-parse", "HEAD") == head
    assert "return 1" in (repo / "src/pkg/mod.py").read_text()  # rolled back
    assert chat.calls["n"] == 2


@pytest.fixture
def _prose_lane(monkeypatch):
    """The prose lane answers confidently and the judge says PASS -- the old success path."""
    calls = {"dev": 0, "judge": 0}

    def fake(base_url, model, prompt, max_tokens=512, timeout=60.0):
        calls["judge" if "QA verifier" in prompt else "dev"] += 1
        content = "PASS" if "QA verifier" in prompt else "Done: fixed the bug and verified it."
        return {"choices": [{"message": {"content": content}}], "usage": {"total_tokens": 10}}

    monkeypatch.setattr(le, "_chat_complete", fake)
    monkeypatch.setattr(le, "_classify_node", lambda _d: "gpu")
    return calls


def test_c_no_oracle_is_needs_oracle_not_success(tmp_path, _prose_lane):
    repo = _make_repo(tmp_path)
    chat = _fake_chat("def value():\n    return 2\n")
    task = _Task(id="t-prose", description="fix the value bug")  # no oracle
    res = _executor(tmp_path, chat).execute_task(task, str(repo))
    assert res["status"] == "needs_oracle"
    assert res["success"] is False
    assert chat.calls["n"] == 0  # the ACT model is never called without an oracle
    assert len(_git(repo, "log", "--oneline").splitlines()) == 1


def test_d_judge_pass_prose_cannot_yield_success_without_commit(tmp_path, _prose_lane):
    """MUTATION TARGET: restoring `success = _judge_quality(...)` must turn this RED."""
    task = _Task(id="t-prose", description="fix the value bug", verification="tests pass")
    res = _executor(tmp_path, _fake_chat("")).execute_task(task, str(tmp_path))
    assert _prose_lane["judge"] == 1  # the judge was consulted and said PASS ...
    assert res["judge_pass"] is True
    assert res["success"] is False  # ... and still no success without a commit
    assert res["returncode"] != 0


def test_partial_act_spec_is_needs_oracle(tmp_path, _prose_lane):
    """An oracle with no edit scope, or no git worktree, cannot drive act_loop."""
    repo = _make_repo(tmp_path)
    chat = _fake_chat("def value():\n    return 2\n")
    t = _act_task()
    t.edit_targets = []
    assert _executor(tmp_path, chat).execute_task(t, str(repo))["status"] == "needs_oracle"
    res = _executor(tmp_path, chat).execute_task(_act_task(), str(tmp_path / "nope"))
    assert res["status"] == "needs_oracle" and res["success"] is False
    assert chat.calls["n"] == 0


def test_loop_task_carries_act_fields_additively():
    old = LoopTask("x", "d", "general", 1, "v", 10)  # pre-existing positional shape
    assert (old.oracle_test, old.edit_file, old.edit_targets) == ("", "", [])
    new = LoopTask("x", "d", "general", 1, "v", 10, oracle_test="tests/t.py::test_a")
    assert new.oracle_test == "tests/t.py::test_a"


def test_e_needs_oracle_never_escalates_to_cloud(monkeypatch, _prose_lane):
    """A task with no oracle must not drift into cloud escalation after 3 'failures'."""
    from unittest.mock import Mock

    from cohezion.compound.autonomous_loop.coordinator import LoopConfig, LoopCoordinator

    monkeypatch.setattr(le, "warmup_tiers", lambda *a, **k: {})
    monkeypatch.setattr(le, "check_ram", lambda *a, **k: (True, 100.0))
    cloud = Mock()
    cloud._started = True
    cloud.execute_task.return_value = {"success": True, "tokens_used": 5}
    cfg = LoopConfig(cloud_escalation_threshold=3, sprint_duration_seconds=1e9, max_tokens=10**9)
    coord = LoopCoordinator(cfg)
    monkeypatch.setattr(coord, "_consolidate_episodes", lambda _r: None)  # no live LLM
    coord._backlog = [LoopTask("t1", "no oracle", "general", 1, "v", 10) for _ in range(4)]
    report = coord.run(executor=cloud)
    assert cloud.execute_task.call_count == 0
    assert report.tasks_completed == 0 and report.tasks_failed == 4
