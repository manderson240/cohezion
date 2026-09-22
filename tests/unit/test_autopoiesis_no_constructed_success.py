"""No autopoiesis check may pass by construction (audit 2026-09-21, follow-on to befa8e15f).

Each check below must be able to FAIL on observed state, or report UNKNOWN:
  (1) the constraint "proof" ran on the constant (1.0, 0.0, 1.0), which satisfies a+b-c=0;
  (2) the codebase sweep appended a finding even for a missing file and passed at 0.85;
  (3) tri_silicon built its "after" points as a tight cluster, so Delta S <= 0 always;
  (4) callers with no step function must be told that nothing was executed.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from cohezion.autopoiesis import tri_silicon_engine as tse
from cohezion.flume.loop_goal_refactor_engine import GoalSpecification
from cohezion.physics.my_big_toe_entropy_engine import MyBigTOEEntropyEngine
from cohezion.recursive_trace import tripartite_goal_loop as tgl
from cohezion.recursive_trace.tripartite_goal_loop import (
    TripartiteGoalLoop,
    read_outcome_accounting,
)
from cohezion.reliability.oom_guard import MemoryState


REPO = Path(__file__).resolve().parents[2]


@pytest.fixture(autouse=True)
def _isolate(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ("VAULT_LEARNINGS", "VAULT_RETROS", "VAULT_KANBAN"):
        monkeypatch.setattr(tgl, name, tmp_path / name)
    monkeypatch.setattr(tgl.urllib.request, "urlopen", _raise)
    for meth in ("_sql", "persist_goal"):
        monkeypatch.setattr(
            tgl.DurableSurrealGoalPersistence, meth, lambda *a, **k: _raise(), raising=False
        )


def _raise(*_a, **_k):
    raise OSError("offline in tests")


def _goal() -> GoalSpecification:
    return GoalSpecification(goal_id="nc", title="t", target_metric="m", target_threshold=0.5)


def _loop(accounting=(3.0, 1.0, 4.0), rc=0) -> TripartiteGoalLoop:
    return TripartiteGoalLoop(
        max_depth=1,
        memory_probe=lambda: 24.0,
        outcome_probe=lambda: 1.0,
        accounting_probe=lambda: accounting,
        sweep_runner=lambda name, path: rc,
    )


def _learn(loop: TripartiteGoalLoop):
    sweep = loop.execute_internal_sweep()
    research = loop.execute_frontier_research("t", "initial")
    res, _, _ = loop.execute_experiential_learning(_goal(), 1, "s", True, sweep, research)
    return res


# ---- (1) the constraint check runs on MEASURED counts and can fail -------------------


def test_1_constraint_holds_on_consistent_counts():
    res = _learn(_loop(accounting=(3.0, 1.0, 4.0)))
    assert res.zkfv_verified is True
    assert res.reward == pytest.approx(1.0)  # 0.95 + 0.05 bonus, all checks genuinely passed


def test_1_constraint_FAILS_when_outcomes_do_not_account_for_completed_tasks():
    # 5 completed tasks, only 4 with a recorded outcome: a + b - c = -1 != 0
    res = _learn(_loop(accounting=(3.0, 1.0, 5.0)))
    assert res.zkfv_verified is False
    assert res.reward == pytest.approx(0.95)  # no +0.05 bonus on a failed check


def test_1_unreadable_counts_mean_not_performed_not_pass():
    res = _learn(_loop(accounting=None))
    assert res.zkfv_verified is None
    assert res.zkfv_proof_id == "not-performed"
    assert res.reward == pytest.approx(0.95)


def test_1_accounting_probe_reads_real_records(tmp_path: Path):
    f = tmp_path / "tasks.json"
    f.write_text(
        json.dumps(
            [
                {"done": True, "success": True},
                {"done": True, "success": False},
                {"done": True},  # completed, outcome never recorded
                {"done": False, "success": True},  # not completed: excluded
            ]
        )
    )
    assert read_outcome_accounting(f) == (1.0, 1.0, 3.0)  # 1 + 1 != 3 -> constraint fails
    assert read_outcome_accounting(tmp_path / "missing.json") is None
    empty = tmp_path / "empty.json"
    empty.write_text("[]")
    assert read_outcome_accounting(empty) is None


# ---- (2) the sweep's verdict comes from check exit codes ----------------------------


def test_2_sweep_passes_only_when_every_run_check_exits_zero():
    sweep = _loop(rc=0).execute_internal_sweep()
    assert sweep.passed is True
    assert sweep.integrity_score == 1.0
    assert sweep.checks_evaluated == len(tgl.SWEEP_CHECKS)
    assert sweep.dormant_count == 0


def test_2_sweep_FAILS_when_a_check_exits_nonzero():
    loop = _loop()
    loop.sweep_runner = lambda name, path: 1 if name == "dormancy_scan" else 0
    sweep = loop.execute_internal_sweep()
    assert sweep.passed is False
    assert sweep.integrity_score == pytest.approx(0.5)
    assert sweep.dormant_count is None
    assert any("FAILED" in f for f in sweep.findings)


def test_2_sweep_where_nothing_ran_is_unknown_not_pass():
    sweep = _loop(rc=None).execute_internal_sweep()
    assert sweep.passed is False
    assert sweep.integrity_score is None
    assert sweep.checks_evaluated == 0


def test_2_sweep_paths_are_repo_rooted_not_cwd_relative(monkeypatch, tmp_path):
    seen: list[Path] = []
    monkeypatch.chdir(tmp_path)  # daemons do not run from the repo root
    loop = _loop()
    loop.sweep_runner = lambda name, path: seen.append(path) or 0
    loop.execute_internal_sweep()
    assert seen and all(p.is_absolute() and p.is_file() for p in seen)


def test_2_default_runner_reports_a_real_nonzero_exit(tmp_path: Path):
    bad = tmp_path / "bad.py"
    bad.write_text("raise SystemExit(3)\n")
    assert tgl.run_sweep_check("bad", bad) == 3
    assert tgl.run_sweep_check("missing", tmp_path / "nope.py") is None


# ---- (3) tri_silicon Delta S is computed from MEASURED state -------------------------


def _mem(avail: float) -> MemoryState:
    return MemoryState(available_gb=avail, total_gb=128.0, swap_used_gb=0.0, is_safe=True)


def test_3_observed_state_unknown_when_any_input_unknown():
    assert tse.observed_state([0.5, None], _mem(64.0)) is None
    assert tse.observed_state([], _mem(64.0)) is None
    assert (
        tse.observed_state(
            [0.5], MemoryState(available_gb=1.0, total_gb=0.0, swap_used_gb=0.0, is_safe=True)
        )
        is None
    )


def _engine_with(monkeypatch, rewards_per_cycle, avail_per_call):
    eng = tse.TriSiliconAutopoiesisEngine.__new__(tse.TriSiliconAutopoiesisEngine)
    eng.entropy_engine = MyBigTOEEntropyEngine()
    eng.npu_model = "x"
    eng._prev_state = None
    rewards = iter(rewards_per_cycle)
    mems = iter([_mem(a) for a in avail_per_call])
    eng.execute_npu_phase = lambda c: ("g", 0.0)
    eng.execute_cpu_phase = lambda c, g: {
        "programs_found": 0,
        "converged": False,
        "final_reward": None,
        "rewards": next(rewards),
        "steps_executed": 0,
        "kagg_win_rate": None,
        "latency_ms": 1.0,
    }
    eng.execute_igpu_phase = lambda c, r: (False, "", 0.0)
    eng._persist_to_vault = lambda **k: None
    monkeypatch.setattr(tse.OOMGuard, "get_memory_state", classmethod(lambda cls: next(mems)))
    return eng


def test_3_first_cycle_has_no_delta_s(monkeypatch):
    # get_memory_state is called twice per cycle (safety check + post state)
    eng = _engine_with(monkeypatch, [[0.4]], [64.0, 64.0])
    res = eng.execute_cycle(1)
    assert res.delta_entropy is None
    assert res.autoharness_verified is None


def test_3_delta_s_can_rise_when_measured_state_disperses(monkeypatch):
    # cycle 1: tight state; cycle 2: rewards spread out -> entropy must be able to RISE.
    eng = _engine_with(monkeypatch, [[0.4, 0.4, 0.4], [0.0, 0.95, 0.1]], [64.0, 64.0, 64.0, 8.0])
    eng.execute_cycle(1)
    res = eng.execute_cycle(2)
    assert res.delta_entropy is not None
    assert res.delta_entropy > 0.0
    assert res.autoharness_verified is False
    # ...and it is exactly the entropy change of the MEASURED states, nothing else.
    pre = [[0.4, 0.5]] * 3
    post = [[0.0, 8.0 / 128.0], [0.95, 8.0 / 128.0], [0.1, 8.0 / 128.0]]
    expected = MyBigTOEEntropyEngine().evaluate_transition(
        pre_points=pre,
        post_points=post,
        pre_coherences=[pt[0] for pt in pre],
        post_coherences=[pt[0] for pt in post],
    )
    assert res.delta_entropy == pytest.approx(expected.delta_entropy)


def test_3_constructed_embedding_is_gone():
    assert not hasattr(tse.TriSiliconAutopoiesisEngine, "_extract_grounded_state_embedding")


# ---- (4) no step executed is reported as such ---------------------------------------


def test_4_no_step_function_reports_zero_steps_executed():
    res = _loop().run(_goal())
    assert res.steps_executed == 0
    assert res.converged is False


def test_4_a_step_function_is_counted():
    res = _loop().run(_goal(), lambda g, s: (False, "tried", None))
    assert res.steps_executed == 1


@pytest.mark.parametrize(
    "path",
    [
        "scripts/ops/autonomous_evolution_supervisor.py",
        "scripts/ops/autonomous_overnight_autopoiesis_daemon.py",
        "scripts/ops/start_background_4h_daemon.sh",
    ],
)
def test_4_callers_report_no_step_executed(path: str):
    src = (REPO / path).read_text()
    assert "steps_executed" in src
    assert re.search(r"no step executed", src, re.IGNORECASE)
    assert "succeeded: Converged" not in src  # the 4h daemon logged every cycle as success


def test_4_shell_daemon_embedded_python_compiles():
    sh = (REPO / "scripts/ops/start_background_4h_daemon.sh").read_text()
    body = sh.split("PYEOF' > /tmp/cohezion_4h_runner.py\n", 1)[1].split("\nPYEOF", 1)[0]
    compile(body, "start_background_4h_daemon.sh:PYEOF", "exec")
