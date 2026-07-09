"""Discriminating tests for the OOM eviction subscriber + pressure driver (2026-06-05).

Backlog item 1. The evictor unloads the LEAST-preferred loaded model on a CRITICAL
*rising* edge — exactly once per rising edge, never on WARNING or sustained CRITICAL.
Each test fails a plausible wrong implementation:
  - an evictor that fires on every event (poll-style) or on WARNING,
  - one that evicts the FIRST or the MOST-preferred model instead of the least,
  - one that crashes when nothing is loaded or when the unloader raises,
  - a driver whose tick() doesn't actually advance the monitor's state.
"""

from __future__ import annotations

from cohezion.platform.memory_pressure import (
    MemoryPressureMonitor,
    PressureLevel,
)
from cohezion.platform.oom_evictor import (
    LoadedModel,
    OOMEvictor,
    PressureDriver,
    install_oom_evictor,
)


def _evictor(loaded: list[LoadedModel]):
    """Build an evictor over a fixed loaded set with a recording unloader."""
    unloaded: list[str] = []

    def unloader(model_id: str) -> bool:
        unloaded.append(model_id)
        return True

    return OOMEvictor(lister=lambda: list(loaded), unloader=unloader), unloaded


def test_evicts_only_on_rising_critical_edge() -> None:
    # Drive a REAL monitor so the rising/sustained/relieved semantics are exercised end-to-end.
    m = MemoryPressureMonitor()
    ev, unloaded = _evictor([LoadedModel("big", priority=90, lane="cpu")])
    m.subscribe(ev.on_event)

    m.evaluate(snapshot=(50.0, 10.0))  # OK == start → no event, no evict
    assert unloaded == []
    m.evaluate(snapshot=(50.0, 60.0))  # → CRITICAL rising → evict once
    assert unloaded == ["big"]
    m.evaluate(snapshot=(50.0, 65.0))  # sustained CRITICAL → NO new event → NO new evict
    assert unloaded == ["big"]
    m.evaluate(snapshot=(50.0, 10.0))  # relieved → no evict
    m.evaluate(snapshot=(50.0, 60.0))  # rising again → evict again
    assert unloaded == ["big", "big"]


def test_evicts_least_preferred_highest_priority_number() -> None:
    # priority: lower == preferred. The victim must be the HIGHEST number (least preferred).
    ev, unloaded = _evictor(
        [
            LoadedModel("preferred", priority=10, lane="npu"),
            LoadedModel("throwaway", priority=90, lane="cpu"),
            LoadedModel("mid", priority=50, lane="igpu"),
        ]
    )
    ev.evict_one()
    assert unloaded == ["throwaway"]  # not "preferred" (min) and not first


def test_warning_edge_does_not_evict() -> None:
    m = MemoryPressureMonitor()
    ev, unloaded = _evictor([LoadedModel("x", priority=50, lane="cpu")])
    m.subscribe(ev.on_event)
    m.evaluate(snapshot=(50.0, 35.0))  # OK → WARNING (rising, but not CRITICAL)
    assert unloaded == []  # only CRITICAL evicts


def test_no_loaded_models_is_noop() -> None:
    ev = OOMEvictor(lister=lambda: [], unloader=lambda _id: True)
    result = ev.evict_one()
    assert result is None
    assert ev.evictions == []


def test_unloader_failure_is_failsoft() -> None:
    def boom(_id: str) -> bool:
        raise RuntimeError("unload failed")

    ev = OOMEvictor(lister=lambda: [LoadedModel("x", priority=50)], unloader=boom)
    # Must NOT raise; records a failed eviction.
    result = ev.evict_one()
    assert result is not None and result.succeeded is False
    assert ev.evictions[-1].succeeded is False


def test_lister_failure_is_failsoft() -> None:
    def boom():
        raise RuntimeError("lemonade down")

    ev = OOMEvictor(lister=boom, unloader=lambda _id: True)
    assert ev.evict_one() is None  # degraded, no crash


def test_driver_tick_advances_monitor_state() -> None:
    m = MemoryPressureMonitor()
    d = PressureDriver(monitor=m)
    assert d.tick(snapshot=(50.0, 10.0)) == PressureLevel.OK
    assert d.tick(snapshot=(50.0, 60.0)) == PressureLevel.CRITICAL
    assert m.current_level == PressureLevel.CRITICAL  # tick() really evaluated


def test_install_wires_evictor_to_monitor() -> None:
    m = MemoryPressureMonitor()
    unloaded: list[str] = []
    ev = install_oom_evictor(
        monitor=m,
        lister=lambda: [LoadedModel("z", priority=70, lane="cpu")],
        unloader=lambda mid: unloaded.append(mid) or True,
    )
    d = PressureDriver(monitor=m)
    d.tick(snapshot=(50.0, 10.0))  # OK
    d.tick(snapshot=(50.0, 60.0))  # CRITICAL rising → installed evictor fires
    assert unloaded == ["z"]
    assert ev.evictions[-1].model_id == "z" and ev.evictions[-1].succeeded
