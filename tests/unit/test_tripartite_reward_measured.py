"""The autopoiesis reward must be able to vary (audit 2026-09-21: 1.0 in 189/189 cycles).

Reward inputs are MEASURED (free RAM, loop outcome yield). An unreadable signal yields
UNKNOWN (None), never 1.0; no step function never converges vacuously.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from cohezion.flume.loop_goal_refactor_engine import GoalSpecification
from cohezion.recursive_trace import tripartite_goal_loop as tgl
from cohezion.recursive_trace.tripartite_goal_loop import (
    TripartiteGoalLoop,
    read_available_gb,
    read_loop_yield,
)


@pytest.fixture(autouse=True)
def _isolate(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ("VAULT_LEARNINGS", "VAULT_RETROS", "VAULT_KANBAN"):
        monkeypatch.setattr(tgl, name, tmp_path / name)
    # no network: research phase falls back to its heuristic, persistence is non-fatal
    monkeypatch.setattr(tgl.urllib.request, "urlopen", _raise)
    monkeypatch.setattr(
        tgl.DurableSurrealGoalPersistence, "_sql", lambda *a, **k: _raise(), raising=False
    )


def _raise(*_a, **_k):
    raise OSError("offline in tests")


def _goal(i: int = 0) -> GoalSpecification:
    return GoalSpecification(
        goal_id=f"reward_{i}", title="t", target_metric="m", target_threshold=0.5
    )


def _run(mem, outcome, step_fn=None):
    loop = TripartiteGoalLoop(max_depth=2, memory_probe=lambda: mem, outcome_probe=lambda: outcome)
    return loop.run(_goal(), step_fn)


def test_a_zero_outcome_is_not_max_reward_and_does_not_converge():
    res = _run(24.0, 0.0)
    assert res.final_reward is not None and res.final_reward < 1.0
    assert res.converged is False


def test_a2_no_step_function_never_converges_even_with_perfect_signals():
    res = _run(24.0, 1.0)
    assert res.converged is False
    assert res.final_reward is not None and res.final_reward < 1.0


def test_b_two_measured_states_give_two_rewards():
    ok = lambda g, s: (True, "done", None)  # noqa: E731
    high = _run(24.0, 0.9, ok).final_reward
    low = _run(24.0, 0.3, ok).final_reward
    low_ram = _run(8.0, 0.9, ok).final_reward  # memory_safe needs >= 20 GiB measured
    assert len({high, low, low_ram}) == 3


@pytest.mark.parametrize("mem,outcome", [(None, 0.9), (24.0, None)])
def test_c_unreadable_signal_is_unknown_not_one(mem, outcome):
    res = _run(mem, outcome, lambda g, s: (True, "done", None))
    assert res.final_reward is None


def test_c2_probes_return_none_when_unreadable(tmp_path: Path):
    assert read_available_gb(tmp_path / "missing") is None
    assert read_loop_yield(tasks_path=tmp_path / "missing.json") is None
    empty = tmp_path / "tasks.json"
    empty.write_text("[]")
    assert read_loop_yield(tasks_path=empty) is None  # zero observations != zero yield


def test_probes_measure_real_values(tmp_path: Path):
    now = datetime.now(UTC)
    tasks = [
        {"done": True, "success": True, "completed_at": now.isoformat()},
        {"done": True, "success": False, "completed_at": now.isoformat()},
        {"done": True, "success": True, "completed_at": (now - timedelta(days=30)).isoformat()},
    ]
    f = tmp_path / "tasks.json"
    f.write_text(json.dumps(tasks))
    assert read_loop_yield(window_days=7, tasks_path=f) == 0.5
    mi = tmp_path / "meminfo"
    mi.write_text("MemTotal: 1 kB\nMemAvailable:   20971520 kB\n")
    assert read_available_gb(mi) == pytest.approx(20.0)


def test_twenty_cycle_criterion_on_simulated_measurements():
    """Card pass criterion: >=2 distinct rewards and >=1 converged=False over 20 cycles."""
    rewards, converged = [], []
    for c in range(20):
        mem = 8.0 + 2.0 * c  # free RAM drifting across the 20 GiB floor
        outcome = [0.0, 0.25, 0.5, 0.75, 1.0][c % 5]
        step = lambda g, s, y=outcome: (y >= 0.5, "sim", None)  # noqa: E731
        res = _run(mem, outcome, step)
        rewards.append(res.final_reward)
        converged.append(res.converged)
    assert len(set(rewards)) >= 2
    assert converged.count(False) >= 1
