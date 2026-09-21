"""The test suite must not write to the shared live SurrealDB through JourneyTracker.

Measured 2026-09-21 (ns cohezion, db main): ~19k of 23,379 ``journey_transition`` rows were
fixtures from this suite ("Same task" x2200, "Test task" x1607, ...); running two
test_journey_tracker tests added 16 live rows. These tests use a fake urlopen, so they
prove the guard without touching the network.
"""

from __future__ import annotations

import os
import urllib.request
from unittest.mock import patch

import pytest

from cohezion.compound.executor import ExecutionResult
from cohezion.compound.journey_tracker import LIVE_PERSIST_ENV, JourneyTracker


class _InlineThread:
    def __init__(self, target=None, daemon=None, **_):
        self._target = target

    def start(self):
        self._target()


def _sql_bodies_after_one_step() -> list[str]:
    bodies: list[str] = []

    def fake_urlopen(req, timeout=None):
        bodies.append(req.data.decode())
        raise RuntimeError("fake: no network")

    result = ExecutionResult(
        success=True,
        output="output",
        metrics={"coherence": 0.85},
        duration_seconds=1.0,
        token_metrics={"cache_hit_rate": 0.7},
    )
    with (
        patch.object(urllib.request, "urlopen", side_effect=fake_urlopen),
        patch("threading.Thread", _InlineThread),
    ):
        JourneyTracker(seed=42).track_execution(result, "isolation probe", "generate")
    return bodies


def test_suite_runs_with_live_writes_disabled():
    """Fails if the conftest session guard is removed."""
    assert os.environ.get(LIVE_PERSIST_ENV) == "0"


def test_disabled_track_execution_sends_nothing():
    assert _sql_bodies_after_one_step() == []


def test_enabled_track_execution_writes_both_tables(monkeypatch: pytest.MonkeyPatch):
    """The other half of the pair: with the guard off the SAME step does write, so the
    empty result above is the guard's doing and not a dead write path."""
    monkeypatch.setenv(LIVE_PERSIST_ENV, "1")
    bodies = _sql_bodies_after_one_step()
    assert any(b.startswith("CREATE journey_transition ") for b in bodies)
    assert any(b.startswith("CREATE hash_chain ") for b in bodies)


def test_disabled_still_advances_in_memory_chain():
    tracker = JourneyTracker(seed=42)
    first = tracker._record_chain_entry("c", {"x": 1})
    second = tracker._record_chain_entry("c", {"x": 2})
    assert first != second
    assert tracker._chain_state["c"]["sequence"] == 2
