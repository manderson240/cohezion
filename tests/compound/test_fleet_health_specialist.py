"""Discriminating tests for the Fleet-Health Specialist (item 36, 2026-06-06).

`FleetHealthSpecialist.snapshot()` composes loop_telemetry (item 25) + marginal_power_w (item 17)
+ deposit_cerebellum_neuron (item 24). Read-only except the single gated cerebellum deposit.

Each test fails a plausible wrong impl:
  - hardcode telemetry instead of reading the live artifacts → T_telemetry,
  - mis-compute marginal power → T_power,
  - deposit on a noisy pattern / skip a stable one → T_noisy / T_stable,
  - write the real graph when a store is injected → T_store (deposit must land in the store),
  - deposit when no routing records are given → T_norecords.
"""

from __future__ import annotations

from cohezion.compound.fleet_health_specialist import FleetHealthSpecialist
from cohezion.compound.loop_telemetry import loop_telemetry


def _stable(task: str = "RERANK", lane: str = "igpu", n: int = 6) -> list[dict]:
    return [{"task_class": task, "lane": lane, "fell_back": False} for _ in range(n)]


def test_telemetry_matches_live_loop_telemetry() -> None:
    snap = FleetHealthSpecialist().snapshot()
    # A hardcoded snapshot would diverge from the live read.
    assert snap.telemetry == loop_telemetry()


def test_marginal_power_computed_from_samples() -> None:
    snap = FleetHealthSpecialist().snapshot(lane_power_samples={"npu": ([1.0, 1.0], [5.0, 5.0])})
    assert snap.lane_power_w["npu"] == 4.0  # mean(load 5) − mean(idle 1)


def test_stable_pattern_deposits_one_neuron_to_injected_store() -> None:
    store: list[dict] = []
    snap = FleetHealthSpecialist().snapshot(routing_records=_stable(), store=store)
    assert snap.cerebellum_deposited is not None
    assert len(store) == 1  # exactly one — landed in the injected store, NOT the real graph
    assert snap.cerebellum_deposited is store[0]


def test_noisy_pattern_deposits_nothing() -> None:
    store: list[dict] = []
    noisy = [{"task_class": "X", "lane": "a", "fell_back": True} for _ in range(6)]
    snap = FleetHealthSpecialist().snapshot(routing_records=noisy, store=store)
    assert snap.cerebellum_deposited is None
    assert store == []


def test_no_routing_records_no_deposit() -> None:
    store: list[dict] = []
    snap = FleetHealthSpecialist().snapshot(store=store)
    assert snap.cerebellum_deposited is None and store == []


def test_store_none_under_pytest_does_not_write_real_graph() -> None:
    # store=None + a stable pattern: item-24's pytest guard makes the deposit a no-op (None),
    # so the real graph is never touched during tests. A wrong impl that hit the graph returns
    # a dict here.
    snap = FleetHealthSpecialist().snapshot(routing_records=_stable(), store=None)
    assert snap.cerebellum_deposited is None
