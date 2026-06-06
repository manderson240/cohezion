"""Discriminating tests for the event-driven memory-pressure monitor (2026-06-05).

The point of the refactor is event-driven, not poll-coupled: an event fires ONLY when the
pressure level transitions. Each test fails a plausible wrong impl:
  - a poll impl that emits an event on every evaluate() (not just transitions),
  - a classifier with wrong/exclusive thresholds,
  - a notifier where one bad subscriber stops the others,
  - loads_blocked that triggers at WARNING (over-blocking) or never (no proactive gate).
"""
from __future__ import annotations

from cohezion.platform.memory_pressure import (
    MemoryPressureMonitor,
    PressureLevel,
    classify_pressure,
    get_pressure_monitor,
)


def test_classify_pressure_thresholds_and_boundaries() -> None:
    assert classify_pressure(50.0, 10.0) == PressureLevel.OK
    assert classify_pressure(50.0, 35.0) == PressureLevel.WARNING   # swap >= 30
    assert classify_pressure(12.0, 10.0) == PressureLevel.WARNING   # avail < 16
    assert classify_pressure(50.0, 60.0) == PressureLevel.CRITICAL  # swap >= 50 (rule-5)
    assert classify_pressure(5.0, 10.0) == PressureLevel.CRITICAL   # avail < 8
    # inclusive swap boundary, exclusive avail boundary
    assert classify_pressure(50.0, 50.0) == PressureLevel.CRITICAL  # swap == 50 → critical
    assert classify_pressure(16.0, 10.0) == PressureLevel.OK        # avail == 16 → not warning
    assert classify_pressure(8.0, 10.0) == PressureLevel.WARNING    # avail == 8 → not critical


def test_event_emitted_only_on_transition_not_every_eval() -> None:
    # THE event-driven contract. A poll impl would emit on each evaluate(); this must emit
    # only when the LEVEL changes.
    m = MemoryPressureMonitor()
    events: list = []
    m.subscribe(events.append)

    m.evaluate(snapshot=(50.0, 10.0))   # OK == starting level → NO event
    assert events == []
    m.evaluate(snapshot=(50.0, 60.0))   # → CRITICAL: one rising event
    assert len(events) == 1 and events[0].level == PressureLevel.CRITICAL and events[0].rising
    m.evaluate(snapshot=(50.0, 65.0))   # still CRITICAL → NO new event
    assert len(events) == 1
    m.evaluate(snapshot=(50.0, 10.0))   # → OK: relieved event
    assert len(events) == 2 and events[1].relieved and not events[1].rising


def test_loads_blocked_only_at_critical() -> None:
    m = MemoryPressureMonitor()
    m.evaluate(snapshot=(50.0, 35.0))   # WARNING
    assert m.loads_blocked() is False   # WARNING must NOT block (over-blocking guard)
    m.evaluate(snapshot=(50.0, 60.0))   # CRITICAL
    assert m.loads_blocked() is True
    m.evaluate(snapshot=(50.0, 5.0))    # OK
    assert m.loads_blocked() is False


def test_bad_subscriber_does_not_break_others() -> None:
    m = MemoryPressureMonitor()
    seen: list = []

    def boom(_event):
        raise RuntimeError("subscriber bug")

    m.subscribe(boom)
    m.subscribe(seen.append)  # must still be called despite boom raising
    m.evaluate(snapshot=(50.0, 60.0))   # transition → notify both
    assert len(seen) == 1 and seen[0].level == PressureLevel.CRITICAL


def test_fail_soft_when_memory_unreadable_holds_level() -> None:
    m = MemoryPressureMonitor()
    m.evaluate(snapshot=(50.0, 60.0))   # CRITICAL
    events_before = m.last_event
    # snapshot=None with psutil patched off would read None; simulate via the public contract:
    # passing an explicit None is not allowed, so patch the reader.
    from unittest.mock import patch

    with patch("cohezion.platform.memory_pressure._read_system_memory", return_value=None):
        level = m.evaluate()
    assert level == PressureLevel.CRITICAL          # held unchanged
    assert m.last_event is events_before            # no new event fired


def test_singleton_is_shared() -> None:
    assert get_pressure_monitor() is get_pressure_monitor()
