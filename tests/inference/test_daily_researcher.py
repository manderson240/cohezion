"""RED tests for the daily researcher orchestrator (4 lanes + fleet_lock + preflight).

The contract:
- DailyResearcher.run_dry_run(lane=None) runs all four lanes in order without
  making any real model loads; each lane returns a DryRunReport.
- DailyResearcher.run(lane=...) acquires fleet_lock:modelload via
  FleetLock.acquire(lock_key, timeout) before touching inference; if the
  lock is held, it waits and times out cleanly with a LockTimeout.
- Each lane method (model_scout, harness_paper, datamesh_synthesis,
  verify_evolve) is callable individually.
- PreflightFleetCheck returns (ok: bool, reasons: list[str]); the
  orchestrator refuses to start if preflight fails.
- The cloud-escalation counter is enforced: ≥5 escalations in a single
  run → the lane refuses further escalation and returns
  CLOUD_BUDGET_EXHAUSTED.
- The experiment counter is enforced: ≥2 experiments in a single run →
  the lane returns EXPERIMENT_BUDGET_EXHAUSTED.
"""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock, patch

import pytest

from cohezion.researcher.daily_researcher import (
    DailyResearcher,
    DryRunReport,
    FleetLock,
    LockTimeout,
    PreflightFleetCheck,
)


# ── Preflight ────────────────────────────────────────────────────────────────


def test_preflight_ok_when_memory_healthy():
    fake_free_output = """               total        used        free      shared  buff/cache   available
Mem:           122Gi        40Gi        80Gi       100Mi       2.0Gi        80Gi
Swap:           39Gi          0B        39Gi
"""
    fake_dmesg = "no faults here\n"
    with patch("subprocess.run") as mock_run:
        # Two subprocess calls: `free` and `dmesg` (rocm-smi is not on
        # PATH in the test venv).
        mock_run.side_effect = [
            MagicMock(stdout=fake_free_output, returncode=0),
            MagicMock(stdout=fake_dmesg, returncode=0),
        ]
        ok, reasons = PreflightFleetCheck.run()
        assert ok is True
        assert reasons == []


def test_preflight_fails_when_memory_low():
    fake_free_output = """               total        used        free      shared  buff/cache   available
Mem:           122Gi       110Gi        10Gi       100Mi       2.0Gi        12Gi
Swap:           39Gi          0B        39Gi
"""
    with (
        patch("subprocess.run") as mock_run,
    ):
        mock_run.return_value = MagicMock(stdout=fake_free_output, returncode=0)
        ok, reasons = PreflightFleetCheck.run()
        assert ok is False
        assert any("memory" in r.lower() or "available" in r.lower() for r in reasons)


def test_preflight_fails_when_gcvm_fault_in_dmesg():
    fake_free_output = """               total        used        free      shared  buff/cache   available
Mem:           122Gi        40Gi        80Gi       100Mi       2.0Gi        80Gi
Swap:           39Gi          0B        39Gi
"""
    fake_dmesg = "[12345.6] amdgpu: GCVM_L2_PROTECTION_FAULT\n"
    with patch("subprocess.run") as mock_run:
        # Two subprocess calls expected: `free` then `dmesg` (rocm-smi is
        # not on PATH in the test venv, so the rocm check is skipped).
        mock_run.side_effect = [
            MagicMock(stdout=fake_free_output, returncode=0),
            MagicMock(stdout=fake_dmesg, returncode=0),
        ]
        ok, reasons = PreflightFleetCheck.run()
        assert ok is False
        assert any("gcvm" in r.lower() or "fault" in r.lower() for r in reasons)


# ── FleetLock: single-flight coordination ────────────────────────────────────


@pytest.mark.asyncio
async def test_fleet_lock_acquire_and_release():
    lock = FleetLock()
    async with lock.acquire("lane-model_scout", timeout=5):
        # second acquire from same key should be impossible within the hold
        with pytest.raises(LockTimeout):
            await lock.acquire("lane-model_scout", timeout=0.1).__aenter__()


@pytest.mark.asyncio
async def test_fleet_lock_waits_for_release():
    """A second acquirer waits for the first to release."""
    lock = FleetLock()
    order: list[str] = []

    async def first():
        async with lock.acquire("lane-x", timeout=5):
            order.append("first-acquired")
            await asyncio.sleep(0.1)
            order.append("first-releasing")

    async def second():
        await asyncio.sleep(0.05)
        async with lock.acquire("lane-x", timeout=5):
            order.append("second-acquired")

    await asyncio.gather(first(), second())
    # second must acquire AFTER first released
    assert order.index("first-releasing") < order.index("second-acquired")


# ── Daily researcher: four lanes runnable individually and as a group ────────


@pytest.mark.asyncio
async def test_run_dry_run_runs_all_four_lanes():
    researcher = DailyResearcher()
    with patch.object(DailyResearcher, "_preflight", return_value=(True, [])):
        reports = await researcher.run_dry_run()
    assert isinstance(reports, dict)
    assert set(reports.keys()) == {
        "model_scout",
        "harness_paper",
        "datamesh_synthesis",
        "verify_evolve",
    }
    for r in reports.values():
        assert isinstance(r, DryRunReport)
        assert r.dry_run is True


@pytest.mark.asyncio
async def test_run_refuses_to_start_if_preflight_fails():
    researcher = DailyResearcher()
    with patch.object(DailyResearcher, "_preflight", return_value=(False, ["low memory"])):
        with pytest.raises(RuntimeError) as exc_info:
            await researcher.run()
        assert "preflight" in str(exc_info.value).lower()


# ── Budgets are enforced ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_cloud_escalation_budget_caps_at_five():
    """The lane refuses the 6th cloud escalation with CLOUD_BUDGET_EXHAUSTED."""
    researcher = DailyResearcher()
    researcher._cloud_escalations_today = 5  # already at cap
    lane = researcher.harness_paper
    result = await lane._attempt_cloud_escalation("synthesis X")
    assert result.status == "CLOUD_BUDGET_EXHAUSTED"


@pytest.mark.asyncio
async def test_experiment_budget_caps_at_two():
    """The lane refuses the 3rd experiment with EXPERIMENT_BUDGET_EXHAUSTED."""
    researcher = DailyResearcher()
    researcher._experiments_today = 2
    lane = researcher.verify_evolve
    result = await lane._run_one_experiment("exp X")
    assert result.status == "EXPERIMENT_BUDGET_EXHAUSTED"
