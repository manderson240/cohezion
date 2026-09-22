"""The ACT loop's oracle outcome is the quality signal for ACT tasks (PQ1).

GREEN (oracle + callers green, confirmed, committed) -> 1.0; EXHAUSTED (the model used its
whole budget and never turned the oracle green) -> 0.0. FLAKY_ORACLE, the instrument
statuses (ROUTER_UNAVAILABLE, RUNNER_BROKEN, VERIFY_TIMEOUT, ADMISSION_REFUSED) and the
non-discriminating ORACLE_ALREADY_GREEN say nothing about the model -> None, not recorded.

The consumer is LoopCoordinator._record_result -- the ONLY reader of this dict (it never
reaches SkillRefiner.refine, which learns from successes only). It records into the
executor's SkillRefiner DifficultyEstimator, the one CompoundExecutor.predict_tier reads.
Nothing here touches :13305: model replies are faked, warmup/consolidation patched out.
"""

from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import numpy as np
import pytest

from cohezion.compound.autonomous_loop import act_loop as al
from cohezion.compound.autonomous_loop import local_executor as le
from cohezion.compound.autonomous_loop.coordinator import (
    LoopConfig,
    LoopCoordinator,
    LoopTask,
    RunReport,
    SprintResult,
)
from cohezion.compound.difficulty_estimator import DifficultyEstimator


ACT_MODEL = "Qwen3.6-35B-A3B-MTP-GGUF"  # mapped to the tier-2 "cpu" engine
_RealExecutor = le.LocalImprovementExecutor  # captured before any test patches the name


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True, check=True)


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


@dataclass
class _Swap:
    ok: bool
    reason: str = "already resident"


def _chat(code: str, model: str = ACT_MODEL):
    def chat(prompt: str) -> dict:
        return {"text": f"```python\n{code}```", "model": model}

    return chat


def _task() -> LoopTask:
    return LoopTask(
        "t-act",
        "make value() return 2",
        "bugfix",
        1,
        "",
        10,
        oracle_test="tests/test_mod.py::test_v",
        edit_file="src/pkg/mod.py",
        edit_targets=["value"],
    )


def _executor(tmp_path: Path, chat) -> le.LocalImprovementExecutor:
    return _RealExecutor(
        act_chat_fn=chat,
        act_max_iters=1,
        act_log_path=tmp_path / "act.jsonl",
        act_python=sys.executable,
        act_admit_fn=lambda _m: _Swap(True),
    )


def _run_coordinator(monkeypatch, tmp_path, repo, chat, estimator) -> None:
    """Real producer -> real LoopCoordinator.run -> the executor's estimator."""
    local = _executor(tmp_path, chat)
    monkeypatch.setattr(le, "warmup_tiers", lambda *a, **k: {})
    monkeypatch.setattr(le, "check_ram", lambda *a, **k: (True, 100.0))
    monkeypatch.setattr(le, "LocalImprovementExecutor", lambda *a, **k: local)
    cfg = LoopConfig(
        worktree_path=str(repo),
        cloud_escalation_threshold=99,
        sprint_duration_seconds=1e9,
        max_tokens=10**9,
    )
    coord = LoopCoordinator(cfg, degradation_detector=MagicMock())
    monkeypatch.setattr(coord, "_consolidate_episodes", lambda _r: None)  # no live LLM
    coord._backlog = [_task()]
    # the daemon passes make_executor(); its lazy SkillRefiner owns the estimator
    cloud = SimpleNamespace(skill_refiner=SimpleNamespace(_difficulty_estimator=estimator))
    coord.run(executor=cloud)


def _records(est: DifficultyEstimator) -> list:
    return list(est._history[("act_loop", "bugfix")])


# ---------------------------------------------------------------------------- ACT quality


def test_green_and_exhausted_reach_the_executors_estimator_with_the_engine(monkeypatch, tmp_path):
    est = DifficultyEstimator()
    good = _make_repo(tmp_path / "g")
    _run_coordinator(monkeypatch, tmp_path, good, _chat("def value():\n    return 2\n"), est)
    bad = _make_repo(tmp_path / "e")
    _run_coordinator(monkeypatch, tmp_path, bad, _chat("def value():\n    return 3\n"), est)
    recs = _records(est)
    assert [r.quality_score for r in recs] == [1.0, 0.0]
    # the mapped engine -- a producer that emitted "act" would be coerced to "cpu" silently,
    # so the unmapped-model test below is what proves this is a mapping, not a coercion
    assert all(r.tier_used == "cpu" for r in recs)


def test_exhausted_carries_the_attempting_model(tmp_path):
    repo = _make_repo(tmp_path)
    res = _executor(tmp_path, _chat("def value():\n    return 3\n")).execute_task(
        _task(), str(repo)
    )
    assert res["status"] == "act_exhausted"
    assert res["cascade_quality_score"] == 0.0
    assert res["model"] == ACT_MODEL and res["tier_used"] == "cpu"


def test_unmapped_model_is_not_credited(monkeypatch, tmp_path):
    est = DifficultyEstimator()
    repo = _make_repo(tmp_path)
    chat = _chat("def value():\n    return 2\n", model="some-other-model")
    _run_coordinator(monkeypatch, tmp_path, repo, chat, est)
    assert _records(est) == []


@pytest.mark.parametrize(
    ("act_status", "exec_status"),
    [
        ("FLAKY_ORACLE", "flaky_oracle"),
        ("ROUTER_UNAVAILABLE", "router_unavailable"),
        ("RUNNER_BROKEN", "runner_broken"),
        ("VERIFY_TIMEOUT", "verify_timeout"),
        ("ADMISSION_REFUSED", "admission_refused"),
        ("ORACLE_ALREADY_GREEN", "oracle_already_green"),
    ],
)
def test_non_model_outcomes_are_unknown_distinct_and_never_recorded(
    monkeypatch, tmp_path, act_status, exec_status
):
    monkeypatch.setattr(al, "act_loop", lambda **kw: {"status": act_status, "model": ACT_MODEL})
    repo = _make_repo(tmp_path)
    res = _executor(tmp_path, _chat("")).execute_task(_task(), str(repo))
    assert res["status"] == exec_status
    assert "cascade_quality_score" in res and res["cascade_quality_score"] is None

    est = DifficultyEstimator()
    det = MagicMock()
    coord = LoopCoordinator(LoopConfig(), degradation_detector=det, difficulty_estimator=est)
    report = RunReport()
    coord._record_result(res, _task(), False, 0, report, {}, {}, SprintResult())
    assert _records(est) == []
    assert report.results[-1]["quality_score"] is None
    # an instrument fault is not scored 0.0 for the degradation baseline either
    assert "quality_score" not in det.check_degradation.call_args.args[0]


# ---------------------------------------------------------------------------- JEPA 7.5b


class _WM:
    def __init__(self) -> None:
        self.observed: list[tuple] = []

    def predict_next_state(self, state, action):
        return np.full(12, 0.75)

    def observe(self, desc, predicted, actual):
        self.observed.append((desc, predicted, actual))


def _run_executor(metrics: dict) -> _WM:
    from cohezion.compound.executor import CompoundExecutor
    from cohezion.compound.jepa_gate import JepaGate

    wm = _WM()
    det = MagicMock()
    det.check_degradation.return_value = []
    ex = CompoundExecutor(
        mcp_client=MagicMock(),
        enable_guardrails=False,
        enable_skill_refinement=False,
        enable_alignment_analysis=False,
        degradation_detector=det,
        jepa_gate=JepaGate(world_model=wm),
    )
    ex.execute_task(
        task_description="t",
        skill_name="s",
        operation_type="generate",
        execute_fn=lambda g: ("done", dict(metrics)),
    )
    return wm


@pytest.mark.parametrize(
    "metrics",
    [{}, {"cascade_quality_score": None}, {"cascade_quality_score": None, "quality_score": 0.9}],
)
def test_jepa_is_not_calibrated_against_unknown_quality(metrics):
    assert _run_executor(metrics).observed == []


def test_jepa_is_calibrated_against_measured_quality():
    obs = _run_executor({"cascade_quality_score": 1.0}).observed
    assert len(obs) == 1 and obs[0][2] == 1.0
