"""The event bridge must COUNT what it loses.

`DataMeshEventBridge` is described in its own docstring as *"the durable event backbone"*.
Every one of its four failure paths previously swallowed the error at DEBUG and returned
normally, so the in-memory fan-out still succeeded and the system looked healthy while the
durable record silently diverged. Found by a LOCAL Qwen3-Coder-30B audit (6 findings, 6/6
quotes verified, 22 s, $0) and independently by two cloud lanes the same day.

Not raising is deliberate: this is a write-through subscriber inside the event loop, and
raising would take down fan-out for every other consumer. The fix makes loss COUNTABLE, per
the Quarter-on-a-String rule that a guard which cannot register its own failure is not a guard.

Every test here fails against the pre-fix implementation, where the counters did not exist.
"""

from __future__ import annotations

import pytest

from cohezion.data_mesh.event_bridge import DataMeshEventBridge


@pytest.fixture
def bridge():
    return DataMeshEventBridge(surreal_url="http://localhost:59999/sql", timeout=0.05)


class TestLossCountersExist:
    def test_all_four_loss_paths_are_exposed(self, bridge):
        assert set(bridge.loss_counters()) == {
            "write_failures",
            "dropped_events",
            "schema_failures",
            "read_failures",
        }
        assert all(isinstance(v, int) for v in bridge.loss_counters().values())

    def test_schema_failure_is_counted_at_construction(self, bridge):
        """The fixture points at an unreachable URL, so `_ensure_schema` fails during __init__.

        This test exists because of a real regression: inserting `loss_counters()` mid-__init__
        orphaned the `self._ensure_schema()` call behind a `return`, so schema setup silently
        stopped running -- and 23 tests still passed, because none of them exercised it. A
        NON-ZERO count here is the proof that construction actually reaches the schema step.
        """
        assert bridge.schema_failures == 1, "_ensure_schema did not run during __init__"

    def test_the_other_three_paths_start_clean(self, bridge):
        """A consumer must be able to ask 'did we lose anything' without knowing the field
        names -- otherwise adding a fifth loss path silently stops being checked."""
        c = bridge.loss_counters()
        assert c["write_failures"] == 0
        assert c["dropped_events"] == 0
        assert c["read_failures"] == 0


class TestWriteFailureIsCounted:
    @pytest.mark.asyncio
    async def test_unreachable_backend_increments_write_failures(self, bridge):
        """DISCRIMINATING: pre-fix this logged at DEBUG and returned, leaving NO trace that
        the durable record now disagrees with what the fan-out delivered."""
        from cohezion.core.event_bus import Event, EventType

        ev = Event(
            type=EventType.CUSTOM, source="test", timestamp=1.0, payload={"k": "v"}, priority=1
        )
        await bridge._handle(ev)

        assert bridge.write_failures == 1, "a lost write left no countable trace"
        assert bridge.loss_counters()["write_failures"] == 1

    @pytest.mark.asyncio
    async def test_repeated_failures_accumulate(self, bridge):
        """One lost event is an incident; a rising count is an outage. The distinction is only
        available if the counter accumulates rather than latching to a boolean."""
        from cohezion.core.event_bus import Event, EventType

        for _ in range(3):
            await bridge._handle(
                Event(type=EventType.CUSTOM, source="t", timestamp=1.0, payload={}, priority=1)
            )
        assert bridge.write_failures == 3


class TestDroppedEventIsCounted:
    @pytest.mark.asyncio
    async def test_non_numeric_timestamp_increments_dropped_events(self, bridge):
        """The numeric-coercion guard is CORRECT (it prevents raw SQL interpolation) but its
        failure mode was the same silence as the write path. A dropped event is data loss even
        when dropping it was the right call."""
        from cohezion.core.event_bus import Event, EventType

        ev = Event(
            type=EventType.CUSTOM,
            source="t",
            timestamp="not-a-float",  # type: ignore[arg-type]
            payload={},
            priority=1,
        )
        await bridge._handle(ev)

        assert bridge.dropped_events == 1
        assert bridge.write_failures == 0, (
            "a coercion drop must not be miscounted as a write failure"
        )


class TestReadFailureIsCounted:
    def test_replay_since_failure_is_distinguishable_from_empty(self, bridge):
        """DISCRIMINATING and the subtlest of the four: `replay_since` returns [] on error, so
        a caller doing catch-up after a restart cannot tell 'nothing happened' from 'I could
        not find out'. The return stays [] (callers assume a list) -- the counter is what makes
        the two cases distinguishable."""
        out = bridge.replay_since(0.0)

        assert out == [], "contract preserved: still returns a list"
        assert bridge.read_failures == 1, (
            "a failed read is indistinguishable from an empty window without this"
        )
