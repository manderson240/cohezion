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

from pathlib import Path

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


# --- item 125 wired into the snapshot: persistent_misses from the INJECTED feed/backlog ------

_MISS_FEED = (
    "## Round 1 — d\n| Finding | Verified | Class | Fleet seam | Notes |\n|---|---|---|---|---|\n"
    "| **`synthmiss`** | y | NEW | s | n |\n\n"
    "## Round 2 — d\n| Finding | Verified | Class | Fleet seam | Notes |\n|---|---|---|---|---|\n"
    "| **`synthmiss`** | y | NEW | s | n |\n"
)


def test_persistent_misses_wired_from_injected_paths(tmp_path: Path) -> None:
    feed = tmp_path / "FEED.md"
    feed.write_text(_MISS_FEED)
    backlog = tmp_path / "BACKLOG.md"
    backlog.write_text(
        "| 1 | A | unrelated item | v | additive | TODO |\n"
    )  # synthmiss NOT actioned
    snap = FleetHealthSpecialist().snapshot(feed_path=feed, backlog_path=backlog)
    # 'synthmiss' is a synthetic id absent from the real repo feed: a wrong wiring that called
    # persistently_dropped_findings() with NO args (reading the real files) could never produce it.
    # This exact result proves the injected paths are passed through AND the conjunction flows.
    assert snap.persistent_misses == [("synthmiss", [1, 2])]


def test_persistent_misses_single_round_not_flagged(tmp_path: Path) -> None:
    feed = tmp_path / "FEED1.md"
    feed.write_text(
        "## Round 1 — d\n| Finding | Verified | Class | Fleet seam | Notes |\n|---|---|---|---|---|\n"
        "| **`synthmiss`** | y | NEW | s | n |\n"
    )
    backlog = tmp_path / "BACKLOG1.md"
    backlog.write_text("| 1 | A | unrelated | v | additive | TODO |\n")
    snap = FleetHealthSpecialist().snapshot(feed_path=feed, backlog_path=backlog)
    assert snap.persistent_misses == []  # 1 round -> conjunction excludes (not just "all dropped")
