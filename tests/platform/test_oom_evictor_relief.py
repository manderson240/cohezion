"""Discriminating tests for OOMEvictor.evict_until_relieved (2026-08-31).

Rebuild of the lost agent-1786851059 fix. The pre-fix evictor was structurally incapable of
relief during a real cascade (its own docstring said sustained-CRITICAL re-evaluations are
no-ops): one eviction per emergency, victim chosen by priority with NO size term, no
re-measurement. Measured consequence on 08-15: ~one 0.38 GB eviction per 18 minutes while
the box died. On 08-31 the box froze at ~10.4 GB available — the WARNING band — so the loop
also takes an explicit ``target_available_gb`` (the guard passes the N3 floor).

Each test kills a plausible wrong implementation:
  - the pre-fix single-shot behaviour (evicts once, never re-measures),
  - a loop with no no-relief stop (shreds the whole fleet when the fleet isn't the culprit),
  - a victim picker with no size tie-break (frees 0.38 GB, leaves 23.3 GB resident),
  - a loop that re-evicts the same victim when the lister lags,
  - an on_event that re-reads memory instead of trusting its caller's snapshot.
"""

from __future__ import annotations

from cohezion.platform.memory_pressure import MemoryPressureMonitor
from cohezion.platform.oom_evictor import (
    MAX_EVICTIONS_PER_EMERGENCY,
    MIN_RELIEF_GB,
    LoadedModel,
    OOMEvictor,
)


def _recording_unloader(sink: list[str], ok: bool = True):
    def unloader(model_id: str) -> bool:
        sink.append(model_id)
        return ok

    return unloader


class TestReliefLoop:
    def test_evicts_until_target_reached_then_stops(self) -> None:
        # Kills the single-shot impl AND an evict-everything impl: exactly 2 of 3 models go.
        unloaded: list[str] = []
        readings = iter([(6.0, 0.0), (17.0, 0.0)])  # after ev1: still low; after ev2: cleared
        ev = OOMEvictor(
            lister=lambda: [
                LoadedModel("a", priority=90, size_gb=5.0),
                LoadedModel("b", priority=80, size_gb=5.0),
                LoadedModel("c", priority=70, size_gb=5.0),
            ],
            unloader=_recording_unloader(unloaded),
            measure=lambda: next(readings),
        )
        evs = ev.evict_until_relieved(4.0, 0.0, target_available_gb=16.0)
        assert unloaded == ["a", "b"]
        assert len(evs) == 2 and all(e.succeeded for e in evs)

    def test_two_consecutive_no_relief_evictions_stop_the_loop(self) -> None:
        # The incident's own lesson: unloads that buy nothing are evidence the fleet is
        # not the culprit. But ONE no-relief reading cannot distinguish 'freed nothing'
        # from 'something ate what it freed' during a concurrent-allocation cascade, so
        # the loop requires TWO consecutive strikes before giving up.
        unloaded: list[str] = []
        ev = OOMEvictor(
            lister=lambda: [
                LoadedModel("a", priority=90, size_gb=5.0),
                LoadedModel("b", priority=80, size_gb=5.0),
                LoadedModel("c", priority=70, size_gb=5.0),
            ],
            unloader=_recording_unloader(unloaded),
            measure=lambda: (4.0, 0.0),  # zero relief, every time
        )
        evs = ev.evict_until_relieved(4.0, 0.0, target_available_gb=16.0)
        assert unloaded == ["a", "b"]  # two strikes, then stop — never the whole fleet
        assert len(evs) == 2

    def test_single_no_relief_reading_does_not_stop_the_loop(self) -> None:
        # 08-31 scenario: the unload freed 5 GB but a concurrent load ate it, so the
        # delta reads ~0. A single-strike loop stops at the moment eviction is most
        # needed; one recovering reading must reset the strike count.
        unloaded: list[str] = []
        readings = iter([(4.0, 0.0), (9.0, 0.0), (17.0, 0.0)])  # ate / freed / cleared
        ev = OOMEvictor(
            lister=lambda: [
                LoadedModel("a", priority=90, size_gb=5.0),
                LoadedModel("b", priority=80, size_gb=5.0),
                LoadedModel("c", priority=70, size_gb=5.0),
            ],
            unloader=_recording_unloader(unloaded),
            measure=lambda: next(readings),
        )
        evs = ev.evict_until_relieved(4.0, 0.0, target_available_gb=16.0)
        assert unloaded == ["a", "b", "c"]  # strike, recovery, cleared
        assert len(evs) == 3

    def test_swap_pressure_relief_counts_as_relief(self) -> None:
        # A swap-driven emergency can be genuinely relieved without MemAvailable moving.
        # An avail-only relief metric reads that as two strikes and abandons a working
        # cascade mid-emergency.
        unloaded: list[str] = []
        readings = iter([(20.0, 55.0), (20.0, 45.0)])  # avail flat, swap dropping
        ev = OOMEvictor(
            lister=lambda: [
                LoadedModel("a", priority=90, size_gb=5.0),
                LoadedModel("b", priority=80, size_gb=5.0),
            ],
            unloader=_recording_unloader(unloaded),
            measure=lambda: next(readings),
        )
        evs = ev.evict_until_relieved(20.0, 60.0, target_available_gb=16.0)
        # avail >= target throughout, but swap >= 50 keeps it unrelieved until the
        # second eviction drops swap below the rule-5 precursor line.
        assert unloaded == ["a", "b"]
        assert all(e.succeeded for e in evs)

    def test_swap_conjunct_gates_the_target_path(self) -> None:
        # avail is comfortably above target but swap is at the rule-5 OOM precursor —
        # deleting the `swap < SWAP_PRESSURE_PCT` conjunct makes this evict nothing.
        unloaded: list[str] = []
        ev = OOMEvictor(
            lister=lambda: [LoadedModel("a", priority=90, size_gb=5.0)],
            unloader=_recording_unloader(unloaded),
            measure=lambda: (20.0, 10.0),
        )
        evs = ev.evict_until_relieved(20.0, 60.0, target_available_gb=16.0)
        assert unloaded == ["a"]
        assert len(evs) == 1

    def test_max_evictions_cap(self) -> None:
        # Steady small-but-real relief that never clears the target: cap must bound it.
        unloaded: list[str] = []
        victims = [LoadedModel(f"m{i}", priority=90 - i, size_gb=1.0) for i in range(10)]
        avail = {"v": 1.0}

        def measure() -> tuple[float, float]:
            avail["v"] += 2 * MIN_RELIEF_GB
            return (avail["v"], 0.0)

        ev = OOMEvictor(
            lister=lambda: victims,
            unloader=_recording_unloader(unloaded),
            measure=measure,
        )
        evs = ev.evict_until_relieved(1.0, 0.0, target_available_gb=100.0)
        assert len(evs) == MAX_EVICTIONS_PER_EMERGENCY
        assert len(unloaded) == MAX_EVICTIONS_PER_EMERGENCY

    def test_unload_failure_stops_the_loop(self) -> None:
        unloaded: list[str] = []
        ev = OOMEvictor(
            lister=lambda: [
                LoadedModel("a", priority=90, size_gb=5.0),
                LoadedModel("b", priority=80, size_gb=5.0),
            ],
            unloader=_recording_unloader(unloaded, ok=False),
            measure=lambda: (20.0, 0.0),
        )
        evs = ev.evict_until_relieved(4.0, 0.0, target_available_gb=16.0)
        assert len(evs) == 1 and evs[0].succeeded is False
        assert unloaded == ["a"]  # no second attempt after a failed unload

    def test_stale_lister_does_not_reevict_same_victim(self) -> None:
        # /api/v1/health can lag an unload; a static fake models that lag. The loop must
        # track tried victims, not trust the lister to shrink.
        unloaded: list[str] = []
        ev = OOMEvictor(
            lister=lambda: [LoadedModel("only", priority=90, size_gb=5.0)],
            unloader=_recording_unloader(unloaded),
            measure=lambda: (5.0, 0.0),  # good relief each time, target never reached
        )
        evs = ev.evict_until_relieved(1.0, 0.0, target_available_gb=100.0)
        assert unloaded == ["only"]  # exactly once, then victims exhausted
        assert len(evs) == 1

    def test_measure_unavailable_stops_after_one(self) -> None:
        # Cannot verify relief -> conservative single eviction, never a blind loop.
        unloaded: list[str] = []
        ev = OOMEvictor(
            lister=lambda: [
                LoadedModel("a", priority=90, size_gb=5.0),
                LoadedModel("b", priority=80, size_gb=5.0),
            ],
            unloader=_recording_unloader(unloaded),
            measure=lambda: None,
        )
        evs = ev.evict_until_relieved(4.0, 0.0, target_available_gb=16.0)
        assert unloaded == ["a"]
        assert len(evs) == 1

    def test_already_relieved_evicts_nothing(self) -> None:
        unloaded: list[str] = []
        ev = OOMEvictor(
            lister=lambda: [LoadedModel("a", priority=90, size_gb=5.0)],
            unloader=_recording_unloader(unloaded),
            measure=lambda: (50.0, 0.0),
        )
        assert ev.evict_until_relieved(50.0, 0.0, target_available_gb=16.0) == []
        assert unloaded == []


class TestVictimSelection:
    def test_size_breaks_priority_ties(self) -> None:
        # THE 08-15 defect: equal preference, victim was the 0.38 GB model while the
        # 23.3 GB sibling stayed resident. Size is a tie-break, so among equal priority
        # the LARGEST model goes first.
        unloaded: list[str] = []
        ev = OOMEvictor(
            lister=lambda: [
                LoadedModel("tiny", priority=90, size_gb=0.38),
                LoadedModel("huge", priority=90, size_gb=23.3),
            ],
            unloader=_recording_unloader(unloaded),
            measure=lambda: (50.0, 0.0),
        )
        ev.evict_until_relieved(4.0, 0.0, target_available_gb=16.0)
        assert unloaded[0] == "huge"

    def test_priority_still_leads_over_size(self) -> None:
        # Size is a TIE-BREAK only — a preferred (low-priority-number) huge model must
        # survive while a less-preferred small one goes.
        unloaded: list[str] = []
        ev = OOMEvictor(
            lister=lambda: [
                LoadedModel("preferred-huge", priority=10, size_gb=23.3),
                LoadedModel("throwaway-tiny", priority=90, size_gb=0.38),
            ],
            unloader=_recording_unloader(unloaded),
            measure=lambda: (50.0, 0.0),
        )
        ev.evict_until_relieved(4.0, 0.0, target_available_gb=16.0)
        assert unloaded[0] == "throwaway-tiny"


class TestVictimSelectionNaN:
    def test_nan_size_does_not_win_ties(self) -> None:
        # NaN compares False with everything: a naive tuple-max lets whichever candidate
        # is seen first win an equal-priority tie arbitrarily. NaN must lose to a real
        # size, in either listing order.
        for order in ([0, 1], [1, 0]):
            models = [
                LoadedModel("nan-size", priority=90, size_gb=float("nan")),
                LoadedModel("huge", priority=90, size_gb=23.3),
            ]
            unloaded: list[str] = []
            ev = OOMEvictor(
                lister=lambda o=order, m=models: [m[i] for i in o],
                unloader=_recording_unloader(unloaded),
                measure=lambda: (50.0, 0.0),
            )
            ev.evict_until_relieved(4.0, 0.0, target_available_gb=16.0)
            assert unloaded[0] == "huge", f"order {order}: NaN won the tie"


class TestOnEventSeeding:
    def test_on_event_drives_multi_eviction_relief(self) -> None:
        # THE regression this rebuild exists to prevent: the pre-fix on_event performed
        # exactly one eviction per emergency, ever. Reverting on_event to evict_one()
        # must FAIL this test (two evictions are required to clear the event).
        unloaded: list[str] = []
        readings = iter([(6.0, 0.0), (17.0, 0.0)])
        m = MemoryPressureMonitor()
        ev = OOMEvictor(
            lister=lambda: [
                LoadedModel("a", priority=90, size_gb=5.0),
                LoadedModel("b", priority=80, size_gb=5.0),
                LoadedModel("c", priority=70, size_gb=5.0),
            ],
            unloader=_recording_unloader(unloaded),
            measure=lambda: next(readings),
        )
        m.subscribe(ev.on_event)
        m.evaluate(snapshot=(50.0, 10.0))  # OK
        m.evaluate(snapshot=(4.0, 10.0))  # CRITICAL rising
        assert unloaded == ["a", "b"]  # loop ran until the WARNING floor was restored

    def test_on_event_seeds_from_events_own_snapshot(self) -> None:
        # The monitor accepts injected snapshots, so the handler must trust its caller's
        # reading. A wrong impl re-reads live memory: with measure() reporting OK it would
        # evict NOTHING despite a CRITICAL event.
        unloaded: list[str] = []
        m = MemoryPressureMonitor()
        ev = OOMEvictor(
            lister=lambda: [LoadedModel("big", priority=90, size_gb=20.0)],
            unloader=_recording_unloader(unloaded),
            measure=lambda: (50.0, 0.0),  # live memory looks fine — event says otherwise
        )
        m.subscribe(ev.on_event)
        m.evaluate(snapshot=(50.0, 10.0))  # OK
        m.evaluate(snapshot=(4.0, 60.0))  # CRITICAL rising per the injected snapshot
        assert unloaded == ["big"]

    def test_on_event_still_ignores_warning_and_sustained(self) -> None:
        unloaded: list[str] = []
        m = MemoryPressureMonitor()
        ev = OOMEvictor(
            lister=lambda: [LoadedModel("x", priority=50, size_gb=1.0)],
            unloader=_recording_unloader(unloaded),
            measure=lambda: (50.0, 0.0),
        )
        m.subscribe(ev.on_event)
        m.evaluate(snapshot=(50.0, 10.0))  # OK
        m.evaluate(snapshot=(12.0, 10.0))  # WARNING rising — no eviction
        assert unloaded == []
